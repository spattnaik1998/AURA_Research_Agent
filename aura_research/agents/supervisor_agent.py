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
from ..utils.config import SERPER_API_KEY, MAX_SUBORDINATE_AGENTS, BATCH_SIZE, ALLOW_MOCK_DATA
from ..services.paper_validation_service import PaperValidationService
from ..services.source_sufficiency_service import SourceSufficiencyService
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

    async def _fetch_papers(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetch and validate research papers using Serper API with NO fallback.

        Args:
            query: Search query

        Returns:
            List of validated paper metadata

        Raises:
            ValueError: If papers cannot be fetched or validated
        """
        logger.info(f"Fetching papers for query: {query}")

        try:
            # Fetch from Serper API
            papers = await self._fetch_papers_api(query)

            if not papers:
                raise ValueError(
                    "No papers found. Your search query returned no results. "
                    "Please try different keywords or a broader search term."
                )

            logger.info(f"Fetched {len(papers)} papers from Serper API")

            # Validate papers (Layer 1)
            valid_papers, validation_results = await self.paper_validator.validate_papers(papers)
            logger.info(f"Validation complete: {len(valid_papers)} valid papers")

            # Check source sufficiency (Layer 2)
            sufficiency = self.sufficiency_checker.check_sufficiency(papers, validation_results)

            if not sufficiency.is_sufficient:
                # Generate detailed error message
                from ..utils.error_messages import get_insufficient_papers_error
                error_msg = self.sufficiency_checker.get_sufficiency_error_message(sufficiency)
                logger.error(f"Insufficient sources: {error_msg}")
                raise ValueError(error_msg)

            logger.info(f"Source sufficiency check passed. Effective score: {sufficiency.effective_count:.2f}")

            return valid_papers

        except Exception as e:
            logger.error(f"Paper fetching/validation failed: {str(e)}")
            # Do NOT fall back to mock data
            raise ValueError(
                f"Unable to fetch and validate academic papers: {str(e)}\n"
                f"No mock data will be generated. Please check your query and try again."
            )

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
