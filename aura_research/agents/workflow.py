"""
LangGraph-based workflow for AURA multi-agent system
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import asyncio
from datetime import datetime
import sys
import io
from ..utils.config import (
    NODE_TIMEOUT_FETCH_PAPERS,
    NODE_TIMEOUT_EXECUTE_AGENTS,
    NODE_TIMEOUT_SYNTHESIZE_ESSAY,
    MAIN_WORKFLOW_TIMEOUT
)
import logging

logger = logging.getLogger('aura.workflow')


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
    essay: str
    audio_essay: str
    essay_file_path: str
    essay_metadata: Dict[str, Any]
    workflow_status: str

    # Metadata
    start_time: str
    end_time: str
    errors: List[str]
    workflow_start_timestamp: float  # For timeout calculations (internal)


class ResearchWorkflow:
    """
    LangGraph workflow orchestrator for multi-agent research
    """

    def __init__(self, supervisor_agent, summarizer_agent):
        """
        Initialize workflow with supervisor and summarizer agents

        Args:
            supervisor_agent: Instance of SupervisorAgent
            summarizer_agent: Instance of SummarizerAgent
        """
        self.supervisor = supervisor_agent
        self.summarizer = summarizer_agent
        self.graph = self._build_graph()

        # Configure stdout for UTF-8 encoding on Windows
        if sys.stdout.encoding != 'utf-8':
            try:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            except Exception as e:
                pass  # Fallback to default encoding if reconfiguration fails

    def _safe_print(self, message: str):
        """Safely print message with Unicode encoding error handling"""
        try:
            print(message)
        except UnicodeEncodeError:
            # If Unicode encoding fails, encode with replacement characters
            print(message.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
        except Exception as e:
            # Final fallback - remove any problematic characters
            print(message.encode('ascii', errors='replace').decode('ascii'))

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
        workflow.add_node("synthesize_essay", self._synthesize_essay_node)
        workflow.add_node("finalize", self._finalize_node)

        # Define edges
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "fetch_papers")
        workflow.add_edge("fetch_papers", "distribute_work")
        workflow.add_edge("distribute_work", "execute_agents")
        workflow.add_edge("execute_agents", "collect_results")
        workflow.add_edge("collect_results", "synthesize_essay")
        workflow.add_edge("synthesize_essay", "finalize")
        workflow.add_edge("finalize", END)

        # Compile graph (note: we bypass this in run() method to avoid LangGraph checkpoint issues)
        return workflow.compile()

    async def _initialize_node(self, state: ResearchState) -> ResearchState:
        """Initialize the workflow"""
        self._safe_print("\n[Workflow] Initializing research workflow...")

        state["start_time"] = datetime.now().isoformat()
        state["workflow_start_timestamp"] = datetime.now().timestamp()  # For timeout calculations
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
        self._safe_print(f"[Workflow] Fetching papers for query: {state['query']}")

        try:
            papers = await asyncio.wait_for(
                self.supervisor._fetch_papers(state["query"]),
                timeout=NODE_TIMEOUT_FETCH_PAPERS
            )
            state["papers"] = papers
            state["total_papers"] = len(papers)
            state["workflow_status"] = "papers_fetched"
            self._safe_print(f"[Workflow] Fetched {len(papers)} papers")
        except asyncio.TimeoutError:
            error_msg = f"Paper fetching timed out after {NODE_TIMEOUT_FETCH_PAPERS}s"
            logger.error(error_msg)
            state["errors"].append(error_msg)
            state["workflow_status"] = "fetch_timeout"
            raise ValueError(error_msg)
        except Exception as e:
            state["errors"].append(f"Paper fetch error: {str(e)}")
            state["workflow_status"] = "fetch_failed"

        return state

    async def _distribute_work_node(self, state: ResearchState) -> ResearchState:
        """Distribute papers to subordinate agents"""
        self._safe_print("[Workflow] Categorizing and distributing papers...")

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
        self._safe_print("[Workflow] Executing subordinate agents in parallel...")

        try:
            results = await asyncio.wait_for(
                self.supervisor._execute_subordinates(state["paper_batches"]),
                timeout=NODE_TIMEOUT_EXECUTE_AGENTS
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
        except asyncio.TimeoutError:
            error_msg = f"Agent execution timed out after {NODE_TIMEOUT_EXECUTE_AGENTS}s"
            logger.warning(error_msg)
            state["errors"].append(error_msg)
            state["workflow_status"] = "agents_timeout"

            # Collect partial results
            results = self.supervisor.subordinate_results
            self._safe_print(f"[Workflow] ⚠️  Timeout: Collected {len(results)} partial results")
        except Exception as e:
            state["errors"].append(f"Execution error: {str(e)}")
            state["workflow_status"] = "execution_failed"

        return state

    async def _collect_results_node(self, state: ResearchState) -> ResearchState:
        """Collect and aggregate results from all agents"""
        self._safe_print("[Workflow] Collecting results from all agents...")

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

    async def _synthesize_essay_node(self, state: ResearchState) -> ResearchState:
        """Synthesize essay from all analyses"""
        self._safe_print("[Workflow] Synthesizing essay from analyses...")

        try:
            # Check remaining time and adjust synthesis timeout
            elapsed_time = datetime.now().timestamp() - state.get("workflow_start_timestamp", 0)
            remaining_time = MAIN_WORKFLOW_TIMEOUT - elapsed_time
            synthesis_timeout = min(NODE_TIMEOUT_SYNTHESIZE_ESSAY, max(30, remaining_time - 10))

            if remaining_time < 30:
                logger.warning(f"⚠️  Only {remaining_time:.0f}s remaining. Skipping essay synthesis.")
                state["errors"].append("Insufficient time for essay synthesis")
                state["workflow_status"] = "synthesis_skipped"
                state["essay"] = "Essay synthesis skipped due to timeout constraints."
                return state

            # Prepare data for summarizer
            summarizer_task = {
                "query": state["query"],
                "analyses": state["all_analyses"],
                "subordinate_results": state["subordinate_results"],
                "_timeout_remaining": remaining_time
            }

            # Execute summarizer agent with dynamic timeout
            try:
                logger.info(f"Executing summarizer with timeout: {synthesis_timeout}s")
                result = await asyncio.wait_for(
                    self.summarizer.execute(summarizer_task),
                    timeout=synthesis_timeout
                )
                logger.info(f"Summarizer returned status: {result.get('status')}")
                if result.get('status') != 'completed':
                    logger.error(f"Summarizer failed! Result: {result}")
                    self._safe_print(f"[ERROR] Summarizer failed: {result.get('error', 'Unknown error')}")

                if result.get("status") == "completed":
                    essay_data = result.get("result", {})
                    logger.info(f"Essay data keys: {list(essay_data.keys())}")
                    logger.info(f"Essay length: {len(essay_data.get('essay', ''))}")

                    state["essay"] = essay_data.get("essay", "")
                    state["audio_essay"] = essay_data.get("audio_essay", "")
                    state["essay_file_path"] = essay_data.get("file_path", "")
                    state["essay_metadata"] = {
                        "word_count": essay_data.get("word_count", 0),
                        "citations": essay_data.get("citations", 0),
                        "papers_synthesized": essay_data.get("papers_synthesized", 0)
                    }
                    state["workflow_status"] = "essay_synthesized"

                    self._safe_print(f"[Workflow] Essay synthesized: {essay_data.get('word_count', 0)} words")
                else:
                    state["errors"].append(f"Summarizer failed: {result.get('error', 'Unknown error')}")
                    state["workflow_status"] = "synthesis_failed"
                    state["essay"] = ""
                    state["essay_file_path"] = ""
                    state["essay_metadata"] = {}
            except UnicodeEncodeError as e:
                logger.error(f"Unicode encoding error during summarizer execution: {e}", exc_info=True)
                state["errors"].append(f"Unicode encoding error: {str(e)}")
                state["workflow_status"] = "synthesis_error"
                # Return empty essay but mark as error rather than crash
                state["essay"] = ""
                state["essay_file_path"] = ""
                state["essay_metadata"] = {}
            except Exception as e:
                logger.error(f"Error in summarizer execution: {e}", exc_info=True)
                state["errors"].append(f"Summarizer error: {str(e)}")
                state["workflow_status"] = "synthesis_error"
                state["essay"] = ""
                state["essay_file_path"] = ""
                state["essay_metadata"] = {}

        except asyncio.TimeoutError:
            error_msg = f"Essay synthesis timed out after {synthesis_timeout:.0f}s"
            logger.warning(error_msg)
            state["errors"].append(error_msg)
            state["workflow_status"] = "synthesis_timeout"
            state["essay"] = "Essay synthesis incomplete due to timeout."
            state["essay_file_path"] = ""
            state["essay_metadata"] = {}
        except Exception as e:
            state["errors"].append(f"Synthesis error: {str(e)}")
            state["workflow_status"] = "synthesis_failed"
            state["essay"] = ""
            state["essay_file_path"] = ""
            state["essay_metadata"] = {}

        return state

    async def _finalize_node(self, state: ResearchState) -> ResearchState:
        """Finalize the workflow"""
        self._safe_print("[Workflow] Finalizing workflow...")

        state["end_time"] = datetime.now().isoformat()
        state["workflow_status"] = "completed"

        self._safe_print(f"[Workflow] Workflow completed successfully")
        self._safe_print(f"[Workflow] Total papers: {state['total_papers']}")
        self._safe_print(f"[Workflow] Analyses generated: {len(state['all_analyses'])}")
        self._safe_print(f"[Workflow] Success rate: {state['completed_agents']}/{state['active_agents']}")

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
        state = {
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
            "errors": [],
            "workflow_start_timestamp": 0.0,  # Will be set in initialize node
            # Add optional fields to avoid LangGraph checkpoint issues
            "paper_batches": [],
            "essay": "",
            "audio_essay": "",
            "essay_file_path": "",
            "essay_metadata": {}
        }

        # Execute workflow manually (bypass LangGraph checkpoint issues)
        try:
            state = await self._initialize_node(state)
            state = await self._fetch_papers_node(state)
            state = await self._distribute_work_node(state)
            state = await self._execute_agents_node(state)
            state = await self._collect_results_node(state)
            state = await self._synthesize_essay_node(state)
            state = await self._finalize_node(state)
        except Exception as e:
            logger.error(f"Workflow execution error: {e}", exc_info=True)
            state["errors"].append(f"Workflow error: {str(e)}")
            state["workflow_status"] = "failed"

        final_state = state

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
            "essay": final_state.get("essay", ""),
            "audio_essay": final_state.get("audio_essay", ""),
            "essay_file_path": final_state.get("essay_file_path", ""),
            "essay_metadata": final_state.get("essay_metadata", {}),
            "execution_time": final_state["end_time"],
            "errors": final_state["errors"]
        }
