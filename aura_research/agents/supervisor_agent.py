"""
Supervisor Agent for AURA
Orchestrates the research workflow and coordinates subordinate agents
"""

from typing import Dict, Any, List
import asyncio
from datetime import datetime
import requests
import logging
import time
from functools import wraps
from .base_agent import BaseAgent, AgentStatus
from .subordinate_agent import SubordinateAgent
from ..utils.config import SERPER_API_KEY, TAVILY_API_KEY, MAX_SUBORDINATE_AGENTS, BATCH_SIZE, ALLOW_MOCK_DATA
from ..services.paper_validation_service import PaperValidationService
from ..services.source_sufficiency_service import SourceSufficiencyService
from ..services.topic_classification_service import TopicClassificationService
from tavily import TavilyClient
import json
import os

# Setup logger
logger = logging.getLogger('aura.agents')


def retry_with_backoff(retries: int = 3, backoff_factor: float = 2.0):
    """
    Retry decorator with exponential backoff for async functions.

    Args:
        retries: Maximum number of retry attempts
        backoff_factor: Multiplier for wait time between retries
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < retries - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"Attempt {attempt + 1}/{retries} failed: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All {retries} attempts failed: {e}")
            raise last_exception
        return wrapper
    return decorator


class SupervisorAgent(BaseAgent):
    """
    Orchestrator agent that coordinates the entire research workflow
    """

    def __init__(self):
        super().__init__(
            agent_id="supervisor-001",
            name="Supervisor"
        )
        self.subordinate_agents: List[SubordinateAgent] = []
        self.papers: List[Dict[str, Any]] = []
        self.subordinate_results: List[Dict[str, Any]] = []
        self.paper_validator = PaperValidationService()
        self.sufficiency_checker = SourceSufficiencyService()
        self.topic_classifier = TopicClassificationService()

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the complete research workflow

        Args:
            task: Contains 'query' (research question)

        Returns:
            Aggregated results from all subordinate agents
        """
        query = task.get("query", "")

        if not query:
            raise ValueError("No research query provided")

        # Step 0: Topic Classification (Layer 0)
        logger.info(f"Classifying query: {query}")
        classification = await self.topic_classifier.classify_query(query)

        if not classification.is_academic:
            from ..utils.error_messages import get_non_academic_query_error
            error_msg = get_non_academic_query_error(
                query,
                classification.category,
                classification.reasoning
            )
            logger.warning(f"Non-academic query rejected: {classification.category}")
            raise ValueError(error_msg)

        logger.info(f"Query classified as academic (confidence: {classification.confidence:.2f})")

        # Step 1: Fetch research papers
        logger.info(f"Fetching papers for query: {query}")
        self.papers = await self._fetch_papers(query)
        logger.info(f"Found {len(self.papers)} papers")

        # Step 2: Categorize and distribute papers
        logger.info("Categorizing papers...")
        categorized_papers = await self._categorize_papers(self.papers)

        # Step 3: Create subordinate agents
        logger.info("Creating subordinate agents...")
        self._create_subordinate_agents()

        # Step 4: Distribute papers to subordinate agents
        logger.info(f"Distributing papers to {len(self.subordinate_agents)} agents...")
        paper_batches = self._distribute_papers(categorized_papers)

        # Step 5: Execute subordinate agents in parallel
        logger.info("Starting parallel analysis...")
        self.subordinate_results = await self._execute_subordinates(paper_batches)

        # Step 6: Track completion and collect results
        logger.info("Analysis complete. Compiling results...")
        completion_status = self._get_completion_status()

        return {
            "query": query,
            "total_papers": len(self.papers),
            "papers_analyzed": sum(r.get("result", {}).get("papers_analyzed", 0)
                                   for r in self.subordinate_results),
            "subordinate_agents": len(self.subordinate_agents),
            "completion_status": completion_status,
            "subordinate_results": self.subordinate_results,
            "timestamp": datetime.now().isoformat()
        }

    @retry_with_backoff(retries=3, backoff_factor=2.0)
    async def _fetch_papers_api(self, query: str) -> List[Dict[str, Any]]:
        """
        Internal method to fetch papers from Serper API with retry support.

        Args:
            query: Search query

        Returns:
            List of paper metadata

        Raises:
            Exception: If API call fails after all retries
        """
        url = "https://google.serper.dev/scholar"

        payload = {
            "q": query,
            "num": 20
        }

        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }

        logger.info(f"Fetching papers from Serper API for query: {query}")

        # Run sync request in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(url, json=payload, headers=headers, timeout=30)
        )

        response.raise_for_status()

        results = response.json()
        papers = []

        # Extract organic results
        for result in results.get("organic", []):
            papers.append({
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "link": result.get("link", ""),
                "publication_info": result.get("publicationInfo", {}),
                "cited_by": {"total": result.get("citedBy", 0)}
            })

        logger.info(f"Successfully fetched {len(papers)} papers from Serper API")
        return papers

    @retry_with_backoff(retries=3, backoff_factor=2.0)
    async def _fetch_papers_tavily(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetch papers from Tavily API as fallback.

        Tavily provides general web search, not academic papers,
        so results are marked with _source='tavily' for special handling.

        Args:
            query: Search query

        Returns:
            List of paper metadata in AURA format

        Raises:
            Exception: If Tavily API fails
        """
        logger.info(f"Fetching from Tavily API as fallback for query: {query}")

        try:
            # Initialize Tavily client
            tavily = TavilyClient(api_key=TAVILY_API_KEY)

            # Run sync request in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: tavily.search(
                    query=f"{query} research paper academic",  # Add academic context
                    max_results=20,
                    topic="general",
                    include_answer=False,
                    include_raw_content=False
                )
            )

            # Transform Tavily results to AURA format
            papers = []
            for item in result.get("results", []):
                # Only include results that look like academic papers
                url = item.get("url", "")
                title = item.get("title", "")

                # Filter for academic domains
                is_academic = any(domain in url.lower() for domain in [
                    'arxiv.org', 'scholar.google', 'doi.org', 'researchgate',
                    'semanticscholar.org', 'pubmed', 'acm.org', 'ieee.org',
                    '.edu/', 'sciencedirect', 'springer', 'wiley', 'nature.com'
                ])

                if is_academic or len(title) > 50:  # Academic titles tend to be descriptive
                    papers.append({
                        "title": title,
                        "snippet": item.get("content", "")[:500],  # Limit snippet length
                        "link": url,
                        "publication_info": {
                            # Mark as web source to signal relaxed validation
                            "publication": "Web Source (Tavily)",
                            "publicationDate": "",
                            "authors": ""
                        },
                        "cited_by": {
                            # Use relevance score as proxy (scale 0-1 to 0-100)
                            "total": int(item.get("score", 0.5) * 100)
                        },
                        "_source": "tavily",  # Mark for special handling
                        "_relevance_score": item.get("score", 0.0)
                    })

            logger.info(f"Tavily returned {len(papers)} results (filtered from {len(result.get('results', []))})")
            return papers

        except Exception as e:
            logger.error(f"Tavily API error: {str(e)}")
            raise

    async def _fetch_papers(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetch and validate research papers using Serper API with Tavily fallback.

        Args:
            query: Search query

        Returns:
            List of validated paper metadata

        Raises:
            ValueError: If both APIs fail or papers cannot be validated
        """
        logger.info(f"Fetching papers for query: {query}")

        papers = None
        serper_error = None

        # Try Serper first (Google Scholar - academic papers)
        try:
            papers = await self._fetch_papers_api(query)

            if not papers:
                raise ValueError("No papers found from Serper API")

            logger.info(f"✓ Fetched {len(papers)} papers from Serper API (Google Scholar)")

        except Exception as e:
            serper_error = str(e)
            logger.warning(f"Serper API failed: {serper_error}")
            logger.info("Attempting Tavily fallback...")

            # Fallback to Tavily (general web search)
            try:
                papers = await self._fetch_papers_tavily(query)

                if not papers:
                    raise ValueError("No papers found from Tavily API")

                logger.info(f"✓ Fetched {len(papers)} papers from Tavily API (fallback)")

            except Exception as tavily_error:
                # Both APIs failed
                logger.error(f"Both APIs failed. Serper: {serper_error}, Tavily: {tavily_error}")
                raise ValueError(
                    f"Unable to fetch papers from any source:\n"
                    f"  - Serper API: {serper_error}\n"
                    f"  - Tavily API: {tavily_error}\n"
                    f"Please check your API keys and try again."
                )

        # Validate papers (Layer 1)
        valid_papers, validation_results = await self.paper_validator.validate_papers(papers)
        logger.info(f"Validation complete: {len(valid_papers)} valid papers")

        # Log validation details
        count_full = sum(1 for r in validation_results if r.get("validation_level") == "full")
        count_doi = sum(1 for r in validation_results if r.get("validation_level") == "doi")
        count_basic = sum(1 for r in validation_results if r.get("validation_level") == "basic")
        logger.info(f"Validation Results:")
        logger.info(f"  - Total: {len(papers)}, Valid: {len(valid_papers)}")
        logger.info(f"  - Full validation: {count_full}, DOI: {count_doi}, Basic: {count_basic}")

        # Check source sufficiency (Layer 2)
        sufficiency = self.sufficiency_checker.check_sufficiency(papers, validation_results)

        if not sufficiency.is_sufficient:
            error_msg = self.sufficiency_checker.get_sufficiency_error_message(sufficiency)
            logger.error(f"Insufficient sources: {error_msg}")
            raise ValueError(error_msg)

        # Log sufficiency details
        logger.info(f"Source Sufficiency Metrics:")
        logger.info(f"  - Effective count: {sufficiency.effective_count:.2f}/{self.sufficiency_checker.MIN_EFFECTIVE_COUNT}")
        logger.info(f"  - Unique venues: {sufficiency.venue_count}/{self.sufficiency_checker.MIN_UNIQUE_VENUES}")
        logger.info(f"  - Recent papers (5y): {sufficiency.recent_papers_count}/{self.sufficiency_checker.MIN_RECENT_PAPERS}")
        logger.info(f"✓ Source sufficiency check passed")

        return valid_papers

    async def _categorize_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Categorize papers based on themes or metadata

        Args:
            papers: List of papers

        Returns:
            Categorized papers (for now, just returns sorted by citations)
        """
        # Simple categorization: sort by citation count
        # In a more advanced implementation, use clustering or LLM-based categorization
        return sorted(
            papers,
            key=lambda p: p.get("cited_by", {}).get("total", 0),
            reverse=True
        )

    def _create_subordinate_agents(self):
        """Create subordinate agents"""
        # Create 3 subordinate agents as specified
        for i in range(3):
            agent = SubordinateAgent(agent_id=f"sub-{i+1:03d}")
            self.subordinate_agents.append(agent)

    def _distribute_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Distribute papers across subordinate agents

        Args:
            papers: Categorized papers

        Returns:
            List of task batches for each agent
        """
        num_agents = len(self.subordinate_agents)
        batch_size = len(papers) // num_agents
        remainder = len(papers) % num_agents

        batches = []
        start_idx = 0

        for i in range(num_agents):
            # Distribute remainder papers to first agents
            current_batch_size = batch_size + (1 if i < remainder else 0)
            end_idx = start_idx + current_batch_size

            batches.append({
                "agent_id": self.subordinate_agents[i].agent_id,
                "papers": papers[start_idx:end_idx]
            })

            start_idx = end_idx

        return batches

    async def _execute_subordinates(
        self,
        paper_batches: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute subordinate agents in parallel

        Args:
            paper_batches: Task batches for each agent

        Returns:
            Results from all agents
        """
        # Create async tasks for parallel execution
        tasks = []
        for i, batch in enumerate(paper_batches):
            agent = self.subordinate_agents[i]
            task = agent.execute(batch)
            tasks.append(task)

        # Execute all agents in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "agent_id": self.subordinate_agents[i].agent_id,
                    "status": "failed",
                    "error": str(result)
                })
            else:
                processed_results.append(result)

        return processed_results

    def _get_completion_status(self) -> Dict[str, Any]:
        """
        Track completion status of all subordinate agents

        Returns:
            Status summary
        """
        total_agents = len(self.subordinate_agents)
        completed = sum(
            1 for r in self.subordinate_results
            if r.get("status") == "completed"
        )
        failed = sum(
            1 for r in self.subordinate_results
            if r.get("status") == "failed"
        )

        return {
            "total_agents": total_agents,
            "completed": completed,
            "failed": failed,
            "success_rate": (completed / total_agents * 100) if total_agents > 0 else 0
        }

    def get_all_analyses(self) -> List[Dict[str, Any]]:
        """
        Get all paper analyses from subordinate agents

        Returns:
            Combined list of all analyses
        """
        all_analyses = []
        for result in self.subordinate_results:
            if result.get("status") == "completed":
                analyses = result.get("result", {}).get("analyses", [])
                all_analyses.extend(analyses)

        return all_analyses
