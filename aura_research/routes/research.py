"""
Research API routes for AURA
Handles research orchestration and status tracking
Integrated with SQL Server database
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from ..utils.image_analyzer import get_image_analyzer
from ..services.db_service import get_db_service
from ..services.auth_service import get_auth_service
from ..services.audio_service import get_audio_service
from ..utils.config import MAIN_WORKFLOW_TIMEOUT

security = HTTPBearer(auto_error=False)

# Setup logger
logger = logging.getLogger('aura.research')

router = APIRouter(prefix="/research", tags=["research"])

# Store active research sessions in memory (for real-time status tracking)
active_sessions: Dict[str, Dict[str, Any]] = {}


# ==================== Authentication Helpers ====================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Get current user from JWT token (optional).
    Returns None if no token or invalid token.
    """
    if not credentials:
        return None

    auth_service = get_auth_service()
    return auth_service.get_current_user(credentials.credentials)


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Require valid authentication.
    Raises 401 if not authenticated.
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    auth_service = get_auth_service()
    user = auth_service.get_current_user(credentials.credentials)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


def verify_session_access(
    session_id: str,
    user_id: int,
    db_service
) -> bool:
    """
    Verify that a user has access to a session.
    Users can only access their own sessions.
    """
    return db_service.verify_session_ownership(session_id, user_id)


class ResearchRequest(BaseModel):
    """Research request model"""
    query: str
    source_type: str = "text"  # 'text' or 'image'
    source_metadata: Optional[Dict[str, Any]] = None  # JSON metadata for image source
    # Note: user_id is now extracted from JWT token, not from request body


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
    ip_address: Optional[str] = None,
    source_type: str = "text",
    source_metadata: Optional[Dict[str, Any]] = None
):
    """
    Run the research workflow in the background with database integration

    Args:
        query: Research query
        session_id: Session ID (session_code)
        user_id: Optional user ID
        ip_address: Client IP address
        source_type: Source of query ('text' or 'image')
        source_metadata: Optional JSON metadata for source
    """
    db_service = get_db_service()

    try:
        # Create database record
        db_session_id = db_service.create_research_session(
            session_code=session_id,
            query=query,
            user_id=user_id,
            ip_address=ip_address,
            source_type=source_type,
            source_metadata=source_metadata
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

        # Run research with timeout protection (5 minutes max)
        try:
            result = await asyncio.wait_for(
                orchestrator.execute_research(query, session_id=session_id),
                timeout=MAIN_WORKFLOW_TIMEOUT  # 5 minutes
            )
        except asyncio.TimeoutError:
            logger.warning(f"Research workflow timed out after {MAIN_WORKFLOW_TIMEOUT}s")
            raise Exception(
                f"Research workflow timed out after {MAIN_WORKFLOW_TIMEOUT // 60} minutes. "
                f"Try a more specific query or check session status for partial results."
            )

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
            'audio_essay': result.get('audio_essay'),  # NEW: audio-optimized version
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
    http_request: Request,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Start a new research session (requires authentication)

    Args:
        request: Research request with query
        background_tasks: FastAPI background tasks
        http_request: HTTP request for client info
        current_user: Authenticated user from JWT token

    Returns:
        Research response with session ID

    Example:
        ```
        POST /research/start
        Authorization: Bearer <token>
        {
            "query": "machine learning in healthcare"
        }
        ```
    """
    try:
        # Get user_id from authenticated token
        user_id = current_user["user_id"]

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
            "user_id": user_id
        }

        # Start research in background with database integration
        background_tasks.add_task(
            run_research_workflow,
            request.query,
            session_id,
            user_id,
            ip_address,
            request.source_type,
            request.source_metadata
        )

        return ResearchResponse(
            session_id=session_id,
            status="started",
            message=f"Research started for query: {request.query}"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start research: {str(e)}")


@router.get("/status/{session_id}", response_model=ResearchStatus)
async def get_research_status(
    session_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get status of a research session (requires authentication and ownership)

    Args:
        session_id: Research session ID
        current_user: Authenticated user from JWT token

    Returns:
        Research status with progress information

    Example:
        ```
        GET /research/status/20251018_133827
        Authorization: Bearer <token>
        ```
    """
    db_service = get_db_service()
    user_id = current_user["user_id"]

    # Check in-memory cache first (for active sessions)
    if session_id in active_sessions:
        session = active_sessions[session_id]
        # Verify ownership for in-memory sessions
        if session.get("user_id") != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this session"
            )
        return ResearchStatus(
            session_id=session["session_id"],
            query=session["query"],
            status=session["status"],
            current_step=session["current_step"],
            progress=session["progress"],
            result=session["result"],
            error=session["error"]
        )

    # Verify ownership for database sessions
    if not verify_session_access(session_id, user_id, db_service):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this session"
        )

    # Check database for historical sessions
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
async def list_research_sessions(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    List research sessions for the authenticated user (active and completed)

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        List of session information for the current user only

    Example:
        ```
        GET /research/sessions
        Authorization: Bearer <token>
        ```
    """
    db_service = get_db_service()
    user_id = current_user["user_id"]

    # Get only the current user's sessions from database
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

    # Add any in-memory sessions for this user not in database yet
    for session_id, session_data in active_sessions.items():
        # Only include sessions owned by the current user
        if session_data.get("user_id") == user_id:
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
async def get_session_details(
    session_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get detailed information about a research session including papers and analyses
    (requires authentication and ownership)

    Args:
        session_id: Research session ID
        current_user: Authenticated user from JWT token

    Returns:
        Full session details with papers and analyses

    Example:
        ```
        GET /research/session/20251018_133827/details
        Authorization: Bearer <token>
        ```
    """
    db_service = get_db_service()
    user_id = current_user["user_id"]

    # Verify ownership
    if not verify_session_access(session_id, user_id, db_service):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this session"
        )

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


@router.post("/session/{session_id}/generate-audio")
async def generate_audio(
    session_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Generate audio from essay text using ElevenLabs API (requires authentication and ownership)

    Args:
        session_id: Research session ID
        current_user: Authenticated user from JWT token

    Returns:
        Status message with audio metadata

    Example:
        ```
        POST /research/session/20251018_133827/generate-audio
        Authorization: Bearer <token>
        ```
    """
    user_id = current_user["user_id"]
    db_service = get_db_service()
    audio_service = get_audio_service()

    # Verify session ownership
    if not db_service.verify_session_ownership(session_id, user_id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this session"
        )

    # Check if essay exists
    essay = db_service.get_session_essay(session_id)
    if not essay:
        raise HTTPException(
            status_code=404,
            detail="No essay found for this session"
        )

    # Get essay content - prefer audio_content, fallback to full_content
    essay_text = essay.get("audio_content") or essay.get("full_content")
    if not essay_text or not essay_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Essay content is empty"
        )

    try:
        # Generate audio
        result = await audio_service.generate_audio(
            text=essay_text,
            session_id=db_service.get_session_id(session_id),
            voice_id=None  # Use default voice
        )

        # Save metadata to database
        audio_filename = Path(result["audio_path"]).name
        db_service.create_audio_record(
            session_code=session_id,
            audio_filename=audio_filename,
            file_size_bytes=result["file_size"],
            user_id=user_id
        )

        return {
            "status": "success",
            "message": "Audio generated successfully",
            "audio_path": result["audio_path"],
            "file_size": result["file_size"]
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        if "rate limit" in str(e).lower():
            raise HTTPException(status_code=429, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")


@router.get("/session/{session_id}/audio")
async def get_audio(
    session_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get and stream audio file for a session (requires authentication and ownership)

    Args:
        session_id: Research session ID
        current_user: Authenticated user from JWT token

    Returns:
        Audio file as MP3

    Example:
        ```
        GET /research/session/20251018_133827/audio
        Authorization: Bearer <token>
        ```
    """
    user_id = current_user["user_id"]
    db_service = get_db_service()
    audio_service = get_audio_service()

    # Verify session ownership
    if not db_service.verify_session_ownership(session_id, user_id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this session"
        )

    # Get audio metadata
    audio_metadata = db_service.get_session_audio(session_id)
    if not audio_metadata:
        raise HTTPException(
            status_code=404,
            detail="No audio found for this session"
        )

    # Get audio file path
    session_id_int = db_service.get_session_id(session_id)
    audio_path = audio_service.get_audio_path(session_id_int)

    if not audio_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Audio file not found"
        )

    # Update last access time
    db_service.update_audio_access_time(session_id)

    # Return audio file
    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg",
        filename=audio_path.name
    )


@router.get("/session/{session_id}/audio/status")
async def get_audio_status(
    session_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Check if audio exists for a session (requires authentication and ownership)

    Args:
        session_id: Research session ID
        current_user: Authenticated user from JWT token

    Returns:
        Status with exists flag and metadata

    Example:
        ```
        GET /research/session/20251018_133827/audio/status
        Authorization: Bearer <token>
        ```
    """
    user_id = current_user["user_id"]
    db_service = get_db_service()

    # Verify session ownership
    if not db_service.verify_session_ownership(session_id, user_id):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this session"
        )

    # Check if audio exists
    exists = db_service.audio_exists(session_id)
    metadata = None

    if exists:
        metadata = db_service.get_session_audio(session_id)

    return {
        "exists": exists,
        "metadata": metadata
    }


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Clear a research session from memory (requires authentication and ownership)

    Args:
        session_id: Research session ID
        current_user: Authenticated user from JWT token

    Returns:
        Success message

    Example:
        ```
        DELETE /research/session/20251018_133827
        Authorization: Bearer <token>
        ```
    """
    user_id = current_user["user_id"]

    if session_id in active_sessions:
        # Verify ownership
        if active_sessions[session_id].get("user_id") != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to delete this session"
            )
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
