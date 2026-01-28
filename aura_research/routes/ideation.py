"""
Ideation API Routes
Research question generation and proposal building
Integrated with SQL Server database
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import os
from ..ideation.question_generator import QuestionGenerator
from ..utils.config import ANALYSIS_DIR
from ..services.db_service import get_db_service
from ..services.auth_service import get_auth_service

security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/ideation", tags=["ideation"])


# ==================== Authentication Helpers ====================

async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Require valid authentication. Raises 401 if not authenticated."""
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


def verify_session_access(session_id: str, user_id: int, db_service) -> bool:
    """Verify that a user has access to a session."""
    return db_service.verify_session_ownership(session_id, user_id)

# In-memory cache for generated questions (for fast access)
questions_cache = {}


class RefineQuestionRequest(BaseModel):
    """Request model for question refinement"""
    question: str
    feedback: str


@router.post("/generate-questions/{session_id}")
async def generate_questions(
    session_id: str,
    num_questions: int = 15,
    include_gaps: bool = True,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Generate research questions from a completed research session
    (requires authentication and ownership)

    Args:
        session_id: Research session ID
        num_questions: Number of questions to generate (default 15)
        include_gaps: Whether to identify gaps first (default True)
        current_user: Authenticated user from JWT token

    Returns:
        Generated questions with gaps and scores
    """
    db_service = get_db_service()
    user_id = current_user["user_id"]

    # Verify ownership
    if not verify_session_access(session_id, user_id, db_service):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this session"
        )

    try:
        # Try to load session data from database first
        session = db_service.get_session_details(session_id)

        if session:
            # Get analyses and essay from database
            analyses = db_service.get_session_analyses(session_id)
            essay = db_service.get_session_essay(session_id)

            session_data = {
                'query': session['query'],
                'analyses': analyses,
                'essay': essay.get('full_content') if essay else None,
                'subordinate_results': [{'result': {'analyses': analyses}}]
            }
        else:
            # Fallback to file-based data
            session_file = os.path.join(ANALYSIS_DIR, f"research_{session_id}.json")

            if not os.path.exists(session_file):
                raise HTTPException(status_code=404, detail="Research session not found")

            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

        # Generate questions
        generator = QuestionGenerator()
        result = await generator.generate_questions(
            session_data,
            num_questions=num_questions,
            include_gaps=include_gaps
        )

        # Save to database
        db_service.save_ideation_results(session_id, result, user_id)

        # Cache the results
        questions_cache[session_id] = result

        return {
            "success": True,
            "session_id": session_id,
            "data": result,
            "stats": {
                "questions_generated": len(result.get('questions', [])),
                "gaps_identified": len(result.get('gaps_identified', []))
            }
        }

    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session file not found")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Question generation failed: {str(e)}"
        )


@router.get("/questions/{session_id}")
async def get_questions(
    session_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Retrieve previously generated questions for a session
    (requires authentication and ownership)

    Args:
        session_id: Research session ID
        current_user: Authenticated user from JWT token

    Returns:
        Previously generated questions
    """
    db_service = get_db_service()
    user_id = current_user["user_id"]

    # Verify ownership
    if not verify_session_access(session_id, user_id, db_service):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this session"
        )

    # Check cache first
    if session_id in questions_cache:
        return {
            "success": True,
            "session_id": session_id,
            "data": questions_cache[session_id],
            "source": "cache"
        }

    # Check database
    questions = db_service.get_session_questions(session_id)
    gaps = db_service.get_session_gaps(session_id)

    if questions or gaps:
        result = {
            'questions': questions,
            'gaps_identified': gaps
        }
        questions_cache[session_id] = result
        return {
            "success": True,
            "session_id": session_id,
            "data": result,
            "source": "database"
        }

    raise HTTPException(
        status_code=404,
        detail="No questions found for this session. Generate questions first."
    )


@router.get("/gaps/{session_id}")
async def get_gaps(
    session_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get identified research gaps for a session
    (requires authentication and ownership)

    Args:
        session_id: Research session ID
        current_user: Authenticated user from JWT token

    Returns:
        Research gaps identified
    """
    db_service = get_db_service()
    user_id = current_user["user_id"]

    # Verify ownership
    if not verify_session_access(session_id, user_id, db_service):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this session"
        )

    # Check cache first
    if session_id in questions_cache:
        data = questions_cache[session_id]
        return {
            "success": True,
            "session_id": session_id,
            "gaps": data.get("gaps_identified", []),
            "total_gaps": len(data.get("gaps_identified", [])),
            "source": "cache"
        }

    # Check database
    gaps = db_service.get_session_gaps(session_id)
    if gaps:
        return {
            "success": True,
            "session_id": session_id,
            "gaps": gaps,
            "total_gaps": len(gaps),
            "source": "database"
        }

    raise HTTPException(
        status_code=404,
        detail="No gaps found. Generate questions first to identify gaps."
    )


@router.post("/refine-question/{session_id}")
async def refine_question(
    session_id: str,
    request: RefineQuestionRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Refine a research question based on user feedback
    (requires authentication and ownership)

    Args:
        session_id: Research session ID
        request: Question and feedback
        current_user: Authenticated user from JWT token

    Returns:
        Refined question variations
    """
    db_service = get_db_service()
    user_id = current_user["user_id"]

    # Verify ownership
    if not verify_session_access(session_id, user_id, db_service):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this session"
        )

    try:
        # Get research context
        research_context = {}

        if session_id in questions_cache:
            research_context = questions_cache[session_id].get("research_summary", {})
        else:
            # Try to get from database
            session = db_service.get_session_details(session_id)
            if session:
                research_context = {
                    'query': session['query'],
                    'analyses_count': session.get('analysis_count', 0)
                }

        if not research_context:
            raise HTTPException(
                status_code=404,
                detail="Session not found. Generate questions first."
            )

        # Refine question
        generator = QuestionGenerator()
        result = await generator.refine_question(
            request.question,
            request.feedback,
            research_context
        )

        return {
            "success": True,
            "session_id": session_id,
            "refinement": result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Question refinement failed: {str(e)}"
        )


@router.get("/questions/{session_id}/by-type")
async def get_questions_by_type(
    session_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get questions grouped by type
    (requires authentication and ownership)

    Args:
        session_id: Research session ID
        current_user: Authenticated user from JWT token

    Returns:
        Questions grouped by type
    """
    db_service = get_db_service()
    user_id = current_user["user_id"]

    # Verify ownership
    if not verify_session_access(session_id, user_id, db_service):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this session"
        )

    # Try database first
    grouped = db_service.ideation.get_questions_grouped_by_type(
        db_service.get_session_id(session_id) or 0
    )

    if grouped:
        return {
            "success": True,
            "session_id": session_id,
            "grouped_questions": grouped,
            "types": list(grouped.keys()),
            "source": "database"
        }

    # Fallback to cache
    if session_id not in questions_cache:
        raise HTTPException(
            status_code=404,
            detail="No questions found for this session"
        )

    data = questions_cache[session_id]
    questions = data.get("questions", [])

    # Group by type
    grouped = {}
    for question in questions:
        q_type = question.get("type", "other")
        if q_type not in grouped:
            grouped[q_type] = []
        grouped[q_type].append(question)

    return {
        "success": True,
        "session_id": session_id,
        "grouped_questions": grouped,
        "types": list(grouped.keys()),
        "source": "cache"
    }


@router.get("/questions/{session_id}/top")
async def get_top_questions(
    session_id: str,
    limit: int = 5,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get top-ranked questions by overall score
    (requires authentication and ownership)

    Args:
        session_id: Research session ID
        limit: Number of top questions to return
        current_user: Authenticated user from JWT token

    Returns:
        Top-ranked questions
    """
    db_service = get_db_service()
    user_id = current_user["user_id"]

    # Verify ownership
    if not verify_session_access(session_id, user_id, db_service):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this session"
        )

    # Try database first
    db_session_id = db_service.get_session_id(session_id)
    if db_session_id:
        top_questions = db_service.ideation.get_top_questions(db_session_id, limit)
        if top_questions:
            return {
                "success": True,
                "session_id": session_id,
                "top_questions": top_questions,
                "limit": limit,
                "source": "database"
            }

    # Fallback to cache
    if session_id not in questions_cache:
        raise HTTPException(
            status_code=404,
            detail="No questions found for this session"
        )

    data = questions_cache[session_id]
    questions = data.get("questions", [])

    # Already sorted by score in generator
    top_questions = questions[:limit]

    return {
        "success": True,
        "session_id": session_id,
        "top_questions": top_questions,
        "limit": limit,
        "source": "cache"
    }


@router.delete("/cache/{session_id}")
async def clear_questions_cache(
    session_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Clear cached question data for a session
    (requires authentication and ownership)

    Args:
        session_id: Research session ID
        current_user: Authenticated user from JWT token

    Returns:
        Success message
    """
    db_service = get_db_service()
    user_id = current_user["user_id"]

    # Verify ownership
    if not verify_session_access(session_id, user_id, db_service):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this session"
        )

    if session_id in questions_cache:
        del questions_cache[session_id]
        return {
            "success": True,
            "message": f"Questions cache cleared for session {session_id}"
        }
    else:
        return {
            "success": True,
            "message": "No cached questions found for this session"
        }


@router.get("/stats/{session_id}")
async def get_question_stats(
    session_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get statistics about generated questions
    (requires authentication and ownership)

    Args:
        session_id: Research session ID
        current_user: Authenticated user from JWT token

    Returns:
        Statistics about questions
    """
    db_service = get_db_service()
    user_id = current_user["user_id"]

    # Verify ownership
    if not verify_session_access(session_id, user_id, db_service):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this session"
        )

    # Try database first
    db_session_id = db_service.get_session_id(session_id)
    if db_session_id:
        stats = db_service.ideation.get_question_stats(db_session_id)
        if stats and stats.get('total_questions', 0) > 0:
            # Get top question
            top_questions = db_service.ideation.get_top_questions(db_session_id, 1)
            gaps = db_service.get_session_gaps(session_id)

            return {
                "success": True,
                "session_id": session_id,
                "statistics": {
                    "total_questions": stats['total_questions'],
                    "total_gaps": len(gaps),
                    "question_types": stats['question_types'],
                    "average_overall_score": float(stats['avg_overall_score']) if stats.get('avg_overall_score') else 0,
                    "average_scores": {
                        "novelty": float(stats['avg_novelty']) if stats.get('avg_novelty') else 0,
                        "feasibility": float(stats['avg_feasibility']) if stats.get('avg_feasibility') else 0,
                        "impact": float(stats['avg_impact']) if stats.get('avg_impact') else 0
                    },
                    "highest_scored": top_questions[0] if top_questions else None,
                    "max_score": float(stats['max_score']) if stats.get('max_score') else 0,
                    "min_score": float(stats['min_score']) if stats.get('min_score') else 0
                },
                "source": "database"
            }

    # Fallback to cache
    if session_id not in questions_cache:
        raise HTTPException(
            status_code=404,
            detail="No questions found for this session"
        )

    data = questions_cache[session_id]
    questions = data.get("questions", [])

    # Calculate statistics
    total = len(questions)

    # Average scores
    avg_scores = {
        "novelty": 0,
        "feasibility": 0,
        "clarity": 0,
        "impact": 0,
        "specificity": 0
    }

    if questions:
        for question in questions:
            scores = question.get("scores", {})
            for key in avg_scores.keys():
                avg_scores[key] += scores.get(key, 0)

        for key in avg_scores.keys():
            avg_scores[key] = round(avg_scores[key] / total, 2)

    # Count by type
    type_counts = {}
    for question in questions:
        q_type = question.get("type", "other")
        type_counts[q_type] = type_counts.get(q_type, 0) + 1

    # Average overall score
    avg_overall = round(
        sum(q.get("overall_score", 0) for q in questions) / total if total > 0 else 0,
        2
    )

    return {
        "success": True,
        "session_id": session_id,
        "statistics": {
            "total_questions": total,
            "total_gaps": len(data.get("gaps_identified", [])),
            "average_scores": avg_scores,
            "average_overall_score": avg_overall,
            "questions_by_type": type_counts,
            "highest_scored": questions[0] if questions else None,
            "most_feasible": max(
                questions,
                key=lambda q: q.get("scores", {}).get("feasibility", 0)
            ) if questions else None
        },
        "source": "cache"
    }
