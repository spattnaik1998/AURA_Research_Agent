"""
Agent Orchestrator - Main entry point for multi-agent system
"""

from typing import Dict, Any
import asyncio
from .supervisor_agent import SupervisorAgent
from .workflow import ResearchWorkflow
import json
from pathlib import Path
from ..utils.config import ANALYSIS_DIR


class AgentOrchestrator:
    """
    Main orchestrator for AURA multi-agent research system
    Provides high-level interface for research execution
    """

    def __init__(self):
        self.supervisor = SupervisorAgent()
        self.workflow = ResearchWorkflow(self.supervisor)
        self.current_session_id = None

    async def execute_research(self, query: str) -> Dict[str, Any]:
        """
        Execute complete research workflow

        Args:
            query: Research question

        Returns:
            Complete research results
        """
        print(f"\n{'='*60}")
        print(f"AURA Research System - Starting Research")
        print(f"Query: {query}")
        print(f"{'='*60}\n")

        # Execute workflow
        result = await self.workflow.run(query)

        # Save results
        session_id = self._save_results(result)
        result["session_id"] = session_id

        print(f"\n{'='*60}")
        print(f"Research Complete!")
        print(f"Session ID: {session_id}")
        print(f"{'='*60}\n")

        return result

    def _save_results(self, result: Dict[str, Any]) -> str:
        """
        Save research results to storage

        Args:
            result: Research results

        Returns:
            Session ID
        """
        from datetime import datetime

        # Generate session ID
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save to analysis directory
        output_file = Path(ANALYSIS_DIR) / f"research_{session_id}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"[Orchestrator] Results saved to: {output_file}")

        return session_id

    def get_session_results(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve results from a previous session

        Args:
            session_id: Session identifier

        Returns:
            Session results
        """
        result_file = Path(ANALYSIS_DIR) / f"research_{session_id}.json"

        if not result_file.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        with open(result_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    async def get_agent_status(self) -> Dict[str, Any]:
        """
        Get current status of all agents

        Returns:
            Status information
        """
        supervisor_status = self.supervisor.get_status()

        subordinate_statuses = [
            agent.get_status()
            for agent in self.supervisor.subordinate_agents
        ]

        return {
            "supervisor": supervisor_status,
            "subordinates": subordinate_statuses,
            "total_subordinates": len(self.supervisor.subordinate_agents)
        }


# Async helper function for CLI/testing
async def run_research(query: str) -> Dict[str, Any]:
    """
    Helper function to run research from CLI or scripts

    Args:
        query: Research question

    Returns:
        Research results
    """
    orchestrator = AgentOrchestrator()
    return await orchestrator.execute_research(query)


# CLI entry point for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <research_query>")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    result = asyncio.run(run_research(query))

    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    print(f"Query: {result['query']}")
    print(f"Status: {result['status']}")
    print(f"Total Papers: {result['total_papers']}")
    print(f"Analyses Generated: {result['analyses_count']}")
    print(f"Agents Completed: {result['agents']['completed']}/{result['agents']['total']}")
    print("="*60)
