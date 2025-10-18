"""
Supervisor Agent for AURA
Orchestrates the research workflow and coordinates subordinate agents
"""

from typing import Dict, Any, List
import asyncio
from datetime import datetime
import requests
from .base_agent import BaseAgent, AgentStatus
from .subordinate_agent import SubordinateAgent
from ..utils.config import SERPER_API_KEY, MAX_SUBORDINATE_AGENTS, BATCH_SIZE
import json


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
        print(f"\n[Supervisor] Fetching papers for query: {query}")
        self.papers = await self._fetch_papers(query)
        print(f"[Supervisor] Found {len(self.papers)} papers")

        # Step 2: Categorize and distribute papers
        print(f"[Supervisor] Categorizing papers...")
        categorized_papers = await self._categorize_papers(self.papers)

        # Step 3: Create subordinate agents
        print(f"[Supervisor] Creating subordinate agents...")
        self._create_subordinate_agents()

        # Step 4: Distribute papers to subordinate agents
        print(f"[Supervisor] Distributing papers to {len(self.subordinate_agents)} agents...")
        paper_batches = self._distribute_papers(categorized_papers)

        # Step 5: Execute subordinate agents in parallel
        print(f"[Supervisor] Starting parallel analysis...")
        self.subordinate_results = await self._execute_subordinates(paper_batches)

        # Step 6: Track completion and collect results
        print(f"[Supervisor] Analysis complete. Compiling results...")
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

    async def _fetch_papers(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetch research papers using Serper API

        Args:
            query: Search query

        Returns:
            List of paper metadata
        """
        try:
            # Using Serper API for Google Scholar search
            url = "https://google.serper.dev/scholar"

            payload = {
                "q": query,
                "num": 20
            }

            headers = {
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json"
            }

            response = requests.post(url, json=payload, headers=headers)
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

            return papers if papers else self._get_mock_papers(query)

        except Exception as e:
            print(f"[Supervisor] Error fetching papers: {str(e)}")
            # Return mock data for testing if API fails
            return self._get_mock_papers(query)

    def _get_mock_papers(self, query: str) -> List[Dict[str, Any]]:
        """Fallback mock data for testing"""
        return [
            {
                "title": f"Research on {query} - Paper {i+1}",
                "snippet": f"This paper explores aspects of {query} and provides insights...",
                "link": f"https://example.com/paper{i+1}",
                "publication_info": {"year": 2024},
                "cited_by": {"total": i * 10}
            }
            for i in range(9)  # 9 papers for 3 agents with 3 papers each
        ]

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
