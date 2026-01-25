"""
Research API routes for AURA
Handles research orchestration and status tracking
Integrated with SQL Server database
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import logging
from datetime import datetime
from ..utils.image_analyzer import get_image_analyzer
from ..services.db_service import get_db_service

# Setup logger
logger = logging.getLogger('aura.research')

router = APIRouter(prefix="/research", tags=["research"])

# Store active research sessions in memory (for real-time status tracking)
active_sessions: Dict[str, Dict[str, Any]] = {}


class ResearchRequest(BaseModel):
    """Research request model"""
    query: str
    user_id: Optional[int] = None


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


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def run_research_workflow(
    query: str,
    session_id: str,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None
):
    """
    Run the research workflow in the background with database integration

    Args:
        query: Research query
        session_id: Session ID (session_code)
        user_id: Optional user ID
        ip_address: Client IP address
    """
    db_service = get_db_service()

    try:
        # Create database record
        db_session_id = db_service.create_research_session(
            session_code=session_id,
            query=query,
            user_id=user_id,
            ip_address=ip_address
        )

        # Update status: Starting
        active_sessions[session_id]["status"] = "running"
        active_sessions[session_id]["current_step"] = "initializing"
        db_service.update_session_status(session_id, "running", progress=5)

        # Import orchestrator
        from ..agents.orchestrator import AgentOrchestrator

        # Update status: Fetching papers
        active_sessions[session_id]["current_step"] = "fetching_papers"
        db_service.update_session_status(session_id, "fetching", progress=10)
        logger.info(f"Fetching papers for session {session_id}")

        # Create orchestrator
        orchestrator = AgentOrchestrator()

        # Update status: Analyzing
        active_sessions[session_id]["current_step"] = "analyzing"
        db_service.update_session_status(session_id, "analyzing", progress=30)
        logger.info(f"Analyzing papers for session {session_id}")

        # Run research with timeout protection (10 minutes max)
        try:
            result = await asyncio.wait_for(
                orchestrator.execute_research(query, session_id=session_id),
                timeout=600.0  # 10 minutes
            )
        except asyncio.TimeoutError:
            raise Exception("Research workflow timed out after 10 minutes. Please try with a more specific query.")

        # Save papers to database
        papers = orchestrator.supervisor.papers
        if papers:
            db_service.save_papers(session_id, papers)
            active_sessions[session_id]["progress"]["papers_fetched"] = len(papers)

        # Save analyses to database
        all_analyses = orchestrator.supervisor.get_all_analyses()
        if all_analyses:
            for sub_result in orchestrator.supervisor.subordinate_results:
                if sub_result.get("status") == "completed":
                    agent_id = sub_result.get("agent_id")
                    agent_analyses = sub_result.get("result", {}).get("analyses", [])
                    db_service.save_paper_analyses(session_id, agent_analyses, agent_id)

        # Update status: Synthesizing
        active_sessions[session_id]["current_step"] = "synthesizing"
        db_service.update_session_status(session_id, "synthesizing", progress=70)
        logger.info(f"Synthesizing essay for session {session_id}")

        # Small delay to show synthesizing step
        await asyncio.sleep(2)

        # Save essay to database
        essay_data = {
            'title': f"Research on: {query}",
            'essay': result.get('essay'),
            'word_count': result.get('essay_metadata', {}).get('word_count', 0),
            'citation_count': result.get('essay_metadata', {}).get('citations', 0),
            'themes': result.get('synthesis', {}).get('main_themes', [])
        }
        db_service.save_essay(session_id, essay_data, user_id)

        # Complete the session in database
        db_service.complete_research_session(
            session_code=session_id,
            total_papers=result.get("total_papers", 0),
            total_analyzed=result.get("analyses_count", 0),
            user_id=user_id
        )

        # Update status: Completed
        active_sessions[session_id]["status"] = "completed"
        active_sessions[session_id]["current_step"] = "completed"
        active_sessions[session_id]["result"] = result
        active_sessions[session_id]["progress"].update({
            "papers_analyzed": result.get("analyses_count", 0),
            "agents_completed": result.get("agents", {}).get("completed", 0),
            "word_count": result.get("essay_metadata", {}).get("word_count", 0)
        })

        logger.info(f"Research completed for session {session_id}")

    except Exception as e:
        # Update status: Failed
        active_sessions[session_id]["status"] = "failed"
        active_sessions[session_id]["error"] = str(e)

        # Update database
        db_service.fail_research_session(session_id, str(e), user_id)

        logger.error(f"Error in session {session_id}: {str(e)}")


@router.post("/start", response_model=ResearchResponse)
async def start_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    http_request: Request
):
    """
    Start a new research session

    Args:
        request: Research request with query
        background_tasks: FastAPI background tasks
        http_request: HTTP request for client info

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

        # Get client IP
        ip_address = get_client_ip(http_request)

        # Initialize session in memory
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
            "started_at": datetime.now().isoformat(),
            "user_id": request.user_id
        }

        # Start research in background with database integration
        background_tasks.add_task(
            run_research_workflow,
            request.query,
            session_id,
            request.user_id,
            ip_address
        )

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
    # Check in-memory cache first (for active sessions)
    if session_id in active_sessions:
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

    # Check database for historical sessions
    db_service = get_db_service()
    session = db_service.get_session_details(session_id)

    if session:
        return ResearchStatus(
            session_id=session["session_code"],
            query=session["query"],
            status=session["status"],
            current_step="completed" if session["status"] == "completed" else session["status"],
            progress={
                "papers_fetched": session.get("total_papers_found", 0),
                "papers_analyzed": session.get("total_papers_analyzed", 0),
                "agents_completed": session.get("analysis_count", 0),
                "word_count": 0
            },
            result=None,
            error=session.get("error_message")
        )

    raise HTTPException(status_code=404, detail=f"Session {session_id} not found")


@router.get("/sessions")
async def list_research_sessions(user_id: Optional[int] = None):
    """
    List all research sessions (active and completed)

    Args:
        user_id: Optional user ID to filter sessions

    Returns:
        List of session information

    Example:
        ```
        GET /research/sessions
        GET /research/sessions?user_id=1
        ```
    """
    db_service = get_db_service()

    # Get from database
    db_sessions = db_service.get_recent_sessions(user_id=user_id, limit=50)

    sessions = []

    # Add database sessions
    for session in db_sessions:
        sessions.append({
            "session_id": session["session_code"],
            "query": session["query"],
            "status": session["status"],
            "started_at": session["started_at"].isoformat() if session.get("started_at") else None,
            "completed_at": session["completed_at"].isoformat() if session.get("completed_at") else None,
            "papers_found": session.get("total_papers_found", 0),
            "papers_analyzed": session.get("total_papers_analyzed", 0),
            "source": "database"
        })

    # Add any in-memory sessions not in database yet
    for session_id, session_data in active_sessions.items():
        if not any(s["session_id"] == session_id for s in sessions):
            sessions.append({
                "session_id": session_id,
                "query": session_data["query"],
                "status": session_data["status"],
                "started_at": session_data["started_at"],
                "source": "memory"
            })

    # Sort by started_at (newest first)
    sessions.sort(key=lambda x: x.get("started_at", ""), reverse=True)

    return {
        "sessions": sessions,
        "count": len(sessions)
    }


@router.get("/session/{session_id}/details")
async def get_session_details(session_id: str):
    """
    Get detailed information about a research session including papers and analyses

    Args:
        session_id: Research session ID

    Returns:
        Full session details with papers and analyses

    Example:
        ```
        GET /research/session/20251018_133827/details
        ```
    """
    db_service = get_db_service()

    # Get session details
    session = db_service.get_session_details(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # Get related data
    papers = db_service.get_session_papers(session_id)
    analyses = db_service.get_session_analyses(session_id)
    essay = db_service.get_session_essay(session_id)

    return {
        "session": session,
        "papers": papers,
        "analyses": analyses,
        "essay": essay,
        "stats": {
            "paper_count": len(papers),
            "analysis_count": len(analyses),
            "has_essay": essay is not None
        }
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
        return {"message": f"Session {session_id} cleared from memory"}
    else:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found in active sessions")


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
