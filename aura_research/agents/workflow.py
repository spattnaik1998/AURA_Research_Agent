"""
LangGraph-based workflow for AURA multi-agent system
"""

from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import asyncio
from datetime import datetime


class ResearchState(TypedDict, total=False):
    """
    State object for the research workflow
    Tracks the entire process from query to completion
    """
    # Input
    query: str

    # Papers
    papers: List[Dict[str, Any]]
    total_papers: int
    paper_batches: List[Dict[str, Any]]

    # Agent tracking
    subordinate_results: List[Dict[str, Any]]
    active_agents: int
    completed_agents: int
    failed_agents: int

    # Results
    all_analyses: List[Dict[str, Any]]
    workflow_status: str

    # Metadata
    start_time: str
    end_time: str
    errors: List[str]


class ResearchWorkflow:
    """
    LangGraph workflow orchestrator for multi-agent research
    """

    def __init__(self, supervisor_agent):
        """
        Initialize workflow with supervisor agent

        Args:
            supervisor_agent: Instance of SupervisorAgent
        """
        self.supervisor = supervisor_agent
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow

        Returns:
            Compiled state graph
        """
        # Create workflow graph
        workflow = StateGraph(ResearchState)

        # Add nodes
        workflow.add_node("initialize", self._initialize_node)
        workflow.add_node("fetch_papers", self._fetch_papers_node)
        workflow.add_node("distribute_work", self._distribute_work_node)
        workflow.add_node("execute_agents", self._execute_agents_node)
        workflow.add_node("collect_results", self._collect_results_node)
        workflow.add_node("finalize", self._finalize_node)

        # Define edges
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "fetch_papers")
        workflow.add_edge("fetch_papers", "distribute_work")
        workflow.add_edge("distribute_work", "execute_agents")
        workflow.add_edge("execute_agents", "collect_results")
        workflow.add_edge("collect_results", "finalize")
        workflow.add_edge("finalize", END)

        # Compile graph
        return workflow.compile()

    async def _initialize_node(self, state: ResearchState) -> ResearchState:
        """Initialize the workflow"""
        print("\n[Workflow] Initializing research workflow...")

        state["start_time"] = datetime.now().isoformat()
        state["workflow_status"] = "initialized"
        state["papers"] = []
        state["subordinate_results"] = []
        state["all_analyses"] = []
        state["errors"] = []
        state["active_agents"] = 0
        state["completed_agents"] = 0
        state["failed_agents"] = 0

        return state

    async def _fetch_papers_node(self, state: ResearchState) -> ResearchState:
        """Fetch research papers"""
        print(f"[Workflow] Fetching papers for query: {state['query']}")

        try:
            papers = await self.supervisor._fetch_papers(state["query"])
            state["papers"] = papers
            state["total_papers"] = len(papers)
            state["workflow_status"] = "papers_fetched"
            print(f"[Workflow] Fetched {len(papers)} papers")
        except Exception as e:
            state["errors"].append(f"Paper fetch error: {str(e)}")
            state["workflow_status"] = "fetch_failed"

        return state

    async def _distribute_work_node(self, state: ResearchState) -> ResearchState:
        """Distribute papers to subordinate agents"""
        print("[Workflow] Categorizing and distributing papers...")

        try:
            # Categorize papers
            categorized_papers = await self.supervisor._categorize_papers(
                state["papers"]
            )

            # Create subordinate agents
            self.supervisor._create_subordinate_agents()
            state["active_agents"] = len(self.supervisor.subordinate_agents)

            # Distribute papers
            paper_batches = self.supervisor._distribute_papers(categorized_papers)
            state["paper_batches"] = paper_batches
            state["workflow_status"] = "work_distributed"

            print(f"[Workflow] Work distributed to {state['active_agents']} agents")
        except Exception as e:
            state["errors"].append(f"Distribution error: {str(e)}")
            state["workflow_status"] = "distribution_failed"

        return state

    async def _execute_agents_node(self, state: ResearchState) -> ResearchState:
        """Execute subordinate agents in parallel"""
        print("[Workflow] Executing subordinate agents in parallel...")

        try:
            results = await self.supervisor._execute_subordinates(
                state["paper_batches"]
            )
            state["subordinate_results"] = results
            state["workflow_status"] = "agents_executed"

            # Count completion status
            state["completed_agents"] = sum(
                1 for r in results if r.get("status") == "completed"
            )
            state["failed_agents"] = sum(
                1 for r in results if r.get("status") == "failed"
            )

            print(f"[Workflow] Agents completed: {state['completed_agents']}/{state['active_agents']}")
        except Exception as e:
            state["errors"].append(f"Execution error: {str(e)}")
            state["workflow_status"] = "execution_failed"

        return state

    async def _collect_results_node(self, state: ResearchState) -> ResearchState:
        """Collect and aggregate results from all agents"""
        print("[Workflow] Collecting results from all agents...")

        try:
            all_analyses = []
            for result in state["subordinate_results"]:
                if result.get("status") == "completed":
                    analyses = result.get("result", {}).get("analyses", [])
                    all_analyses.extend(analyses)

            state["all_analyses"] = all_analyses
            state["workflow_status"] = "results_collected"

            print(f"[Workflow] Collected {len(all_analyses)} analyses")
        except Exception as e:
            state["errors"].append(f"Collection error: {str(e)}")
            state["workflow_status"] = "collection_failed"

        return state

    async def _finalize_node(self, state: ResearchState) -> ResearchState:
        """Finalize the workflow"""
        print("[Workflow] Finalizing workflow...")

        state["end_time"] = datetime.now().isoformat()
        state["workflow_status"] = "completed"

        print(f"[Workflow] Workflow completed successfully")
        print(f"[Workflow] Total papers: {state['total_papers']}")
        print(f"[Workflow] Analyses generated: {len(state['all_analyses'])}")
        print(f"[Workflow] Success rate: {state['completed_agents']}/{state['active_agents']}")

        return state

    async def run(self, query: str) -> Dict[str, Any]:
        """
        Execute the complete research workflow

        Args:
            query: Research question

        Returns:
            Final state with all results
        """
        # Initialize state
        initial_state: ResearchState = {
            "query": query,
            "papers": [],
            "total_papers": 0,
            "subordinate_results": [],
            "active_agents": 0,
            "completed_agents": 0,
            "failed_agents": 0,
            "all_analyses": [],
            "workflow_status": "pending",
            "start_time": "",
            "end_time": "",
            "errors": []
        }

        # Execute workflow
        final_state = await self.graph.ainvoke(initial_state)

        return {
            "query": final_state["query"],
            "status": final_state["workflow_status"],
            "total_papers": final_state["total_papers"],
            "analyses_count": len(final_state["all_analyses"]),
            "agents": {
                "total": final_state["active_agents"],
                "completed": final_state["completed_agents"],
                "failed": final_state["failed_agents"]
            },
            "analyses": final_state["all_analyses"],
            "subordinate_results": final_state["subordinate_results"],
            "execution_time": final_state["end_time"],
            "errors": final_state["errors"]
        }
