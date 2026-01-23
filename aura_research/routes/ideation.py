"""
Ideation API Routes
Research question generation and proposal building
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import os
from ..ideation.question_generator import QuestionGenerator
from ..utils.config import ANALYSIS_DIR

router = APIRouter(prefix="/ideation", tags=["ideation"])

# In-memory cache for generated questions
questions_cache = {}


class RefineQuestionRequest(BaseModel):
    """Request model for question refinement"""
    question: str
    feedback: str


@router.post("/generate-questions/{session_id}")
async def generate_questions(
    session_id: str,
    num_questions: int = 15,
    include_gaps: bool = True
):
    """
    Generate research questions from a completed research session

    Args:
        session_id: Research session ID
        num_questions: Number of questions to generate (default 15)
        include_gaps: Whether to identify gaps first (default True)

    Returns:
        Generated questions with gaps and scores
    """
    try:
        # Load session data
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

        # Cache the results
        questions_cache[session_id] = result

        return {
            "success": True,
            "session_id": session_id,
            "data": result
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session file not found")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Question generation failed: {str(e)}"
        )


@router.get("/questions/{session_id}")
async def get_questions(session_id: str):
    """
    Retrieve previously generated questions for a session

    Args:
        session_id: Research session ID

    Returns:
        Previously generated questions
    """
    if session_id in questions_cache:
        return {
            "success": True,
            "session_id": session_id,
            "data": questions_cache[session_id],
            "cached": True
        }
    else:
        raise HTTPException(
            status_code=404,
            detail="No questions found for this session. Generate questions first."
        )


@router.get("/gaps/{session_id}")
async def get_gaps(session_id: str):
    """
    Get identified research gaps for a session

    Args:
        session_id: Research session ID

    Returns:
        Research gaps identified
    """
    if session_id in questions_cache:
        data = questions_cache[session_id]
        return {
            "success": True,
            "session_id": session_id,
            "gaps": data.get("gaps_identified", []),
            "total_gaps": len(data.get("gaps_identified", []))
        }
    else:
        raise HTTPException(
            status_code=404,
            detail="No gaps found. Generate questions first to identify gaps."
        )


@router.post("/refine-question/{session_id}")
async def refine_question(
    session_id: str,
    request: RefineQuestionRequest
):
    """
    Refine a research question based on user feedback

    Args:
        session_id: Research session ID
        request: Question and feedback

    Returns:
        Refined question variations
    """
    try:
        # Get research context from cache
        if session_id not in questions_cache:
            raise HTTPException(
                status_code=404,
                detail="Session not found in cache. Generate questions first."
            )

        research_context = questions_cache[session_id].get("research_summary", {})

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

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Question refinement failed: {str(e)}"
        )


@router.get("/questions/{session_id}/by-type")
async def get_questions_by_type(session_id: str):
    """
    Get questions grouped by type

    Args:
        session_id: Research session ID

    Returns:
        Questions grouped by type
    """
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
        "types": list(grouped.keys())
    }


@router.get("/questions/{session_id}/top")
async def get_top_questions(session_id: str, limit: int = 5):
    """
    Get top-ranked questions by overall score

    Args:
        session_id: Research session ID
        limit: Number of top questions to return

    Returns:
        Top-ranked questions
    """
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
        "limit": limit
    }


@router.delete("/cache/{session_id}")
async def clear_questions_cache(session_id: str):
    """
    Clear cached question data for a session

    Args:
        session_id: Research session ID

    Returns:
        Success message
    """
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
async def get_question_stats(session_id: str):
    """
    Get statistics about generated questions

    Args:
        session_id: Research session ID

    Returns:
        Statistics about questions
    """
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
        }
    }
