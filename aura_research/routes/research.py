"""
Research API routes for AURA
Handles research orchestration and status tracking
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime
from ..utils.image_analyzer import get_image_analyzer

router = APIRouter(prefix="/research", tags=["research"])

# Store active research sessions in memory
active_sessions: Dict[str, Dict[str, Any]] = {}


class ResearchRequest(BaseModel):
    """Research request model"""
    query: str


class ImageAnalysisRequest(BaseModel):
    """Image analysis request model"""
    image_data: str  # Base64 encoded image with data:image prefix


class ImageAnalysisResponse(BaseModel):
    """Image analysis response model"""
    query: str
    message: str


class ResearchResponse(BaseModel):
    """Research response model"""
    session_id: str
    status: str
    message: str


class ResearchStatus(BaseModel):
    """Research status model"""
    session_id: str
    query: str
    status: str
    current_step: str
    progress: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


async def run_research_workflow(query: str, session_id: str):
    """
    Run the research workflow in the background

    Args:
        query: Research query
        session_id: Session ID
    """
    try:
        # Update status: Starting
        active_sessions[session_id]["status"] = "running"
        active_sessions[session_id]["current_step"] = "initializing"

        # Import orchestrator
        from ..agents.orchestrator import AgentOrchestrator

        # Update status: Fetching papers
        active_sessions[session_id]["current_step"] = "fetching_papers"
        print(f"[Research API] Fetching papers for session {session_id}")

        # Create orchestrator
        orchestrator = AgentOrchestrator()

        # Update status: Analyzing
        active_sessions[session_id]["current_step"] = "analyzing"
        print(f"[Research API] Analyzing papers for session {session_id}")

        # Run research with timeout protection (10 minutes max)
        try:
            result = await asyncio.wait_for(
                orchestrator.execute_research(query),
                timeout=600.0  # 10 minutes
            )
        except asyncio.TimeoutError:
            raise Exception("Research workflow timed out after 10 minutes. Please try with a more specific query.")

        # Update status: Synthesizing
        active_sessions[session_id]["current_step"] = "synthesizing"
        print(f"[Research API] Synthesizing essay for session {session_id}")

        # Small delay to show synthesizing step
        await asyncio.sleep(2)

        # Update status: Completed
        active_sessions[session_id]["status"] = "completed"
        active_sessions[session_id]["current_step"] = "completed"
        active_sessions[session_id]["result"] = result
        active_sessions[session_id]["progress"].update({
            "papers_analyzed": result.get("analyses_count", 0),
            "agents_completed": result.get("agents", {}).get("completed", 0),
            "word_count": result.get("essay_metadata", {}).get("word_count", 0)
        })

        print(f"[Research API] Research completed for session {session_id}")

    except Exception as e:
        # Update status: Failed
        active_sessions[session_id]["status"] = "failed"
        active_sessions[session_id]["error"] = str(e)
        print(f"[Research API] Error in session {session_id}: {str(e)}")


@router.post("/start", response_model=ResearchResponse)
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """
    Start a new research session

    Args:
        request: Research request with query
        background_tasks: FastAPI background tasks

    Returns:
        Research response with session ID

    Example:
        ```
        POST /research/start
        {
            "query": "machine learning in healthcare"
        }
        ```
    """
    try:
        # Generate session ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = timestamp

        # Initialize session
        active_sessions[session_id] = {
            "session_id": session_id,
            "query": request.query,
            "status": "starting",
            "current_step": "initializing",
            "progress": {
                "papers_fetched": 0,
                "papers_analyzed": 0,
                "agents_completed": 0,
                "word_count": 0
            },
            "result": None,
            "error": None,
            "started_at": datetime.now().isoformat()
        }

        # Start research in background
        background_tasks.add_task(run_research_workflow, request.query, session_id)

        return ResearchResponse(
            session_id=session_id,
            status="started",
            message=f"Research started for query: {request.query}"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start research: {str(e)}")


@router.get("/status/{session_id}", response_model=ResearchStatus)
async def get_research_status(session_id: str):
    """
    Get status of a research session

    Args:
        session_id: Research session ID

    Returns:
        Research status with progress information

    Example:
        ```
        GET /research/status/20251018_133827
        ```
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    session = active_sessions[session_id]

    return ResearchStatus(
        session_id=session["session_id"],
        query=session["query"],
        status=session["status"],
        current_step=session["current_step"],
        progress=session["progress"],
        result=session["result"],
        error=session["error"]
    )


@router.get("/sessions")
async def list_research_sessions():
    """
    List all research sessions (active and completed)

    Returns:
        List of session information

    Example:
        ```
        GET /research/sessions
        ```
    """
    sessions = []

    for session_id, session_data in active_sessions.items():
        sessions.append({
            "session_id": session_id,
            "query": session_data["query"],
            "status": session_data["status"],
            "started_at": session_data["started_at"]
        })

    return {
        "sessions": sessions,
        "count": len(sessions)
    }


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """
    Clear a research session from memory

    Args:
        session_id: Research session ID

    Returns:
        Success message

    Example:
        ```
        DELETE /research/session/20251018_133827
        ```
    """
    if session_id in active_sessions:
        del active_sessions[session_id]
        return {"message": f"Session {session_id} cleared"}
    else:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")


@router.post("/analyze-image", response_model=ImageAnalysisResponse)
async def analyze_image(request: ImageAnalysisRequest):
    """
    Analyze an image and extract a research query using GPT-4o Vision

    Args:
        request: Image analysis request with base64 encoded image

    Returns:
        Extracted research query

    Example:
        ```
        POST /research/analyze-image
        {
            "image_data": "data:image/png;base64,iVBORw0KGgo..."
        }
        ```
    """
    try:
        # Get image analyzer instance
        analyzer = get_image_analyzer()

        # Extract query from image
        query = analyzer.extract_research_query(request.image_data)

        return ImageAnalysisResponse(
            query=query,
            message="Successfully extracted research query from image"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")
