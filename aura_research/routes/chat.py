"""
Chat API routes for AURA RAG chatbot
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from ..rag.chatbot import get_chatbot, clear_chatbot


router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    session_id: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    context_used: str
    conversation_id: str
    session_id: str


class ChatHistoryResponse(BaseModel):
    """Chat history response"""
    messages: List[Dict[str, str]]
    conversation_id: str


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send message to RAG chatbot

    Args:
        request: Chat request with message and session_id

    Returns:
        Chat response with answer and context

    Example:
        ```
        POST /chat
        {
            "message": "What are the main findings about machine learning in healthcare?",
            "session_id": "20251018_133827",
            "conversation_id": "user123"
        }
        ```
    """
    try:
        # Get chatbot instance
        chatbot = get_chatbot(request.session_id)

        # Process message
        result = await chatbot.chat(
            message=request.message,
            conversation_id=request.conversation_id
        )

        return ChatResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/history/{session_id}/{conversation_id}", response_model=ChatHistoryResponse)
async def get_history(session_id: str, conversation_id: str = "default"):
    """
    Get conversation history

    Args:
        session_id: Research session ID
        conversation_id: Conversation ID

    Returns:
        List of messages in conversation

    Example:
        ```
        GET /chat/history/20251018_133827/user123
        ```
    """
    try:
        chatbot = get_chatbot(session_id)
        history = chatbot.get_conversation_history(conversation_id)

        return ChatHistoryResponse(
            messages=history,
            conversation_id=conversation_id
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History error: {str(e)}")


@router.delete("/{session_id}")
async def clear_chat_session(session_id: str):
    """
    Clear chatbot instance for session

    Args:
        session_id: Research session ID

    Returns:
        Success message

    Example:
        ```
        DELETE /chat/20251018_133827
        ```
    """
    try:
        clear_chatbot(session_id)
        return {"message": f"Chatbot session {session_id} cleared"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear error: {str(e)}")


@router.get("/sessions")
async def list_sessions():
    """
    List available research sessions

    Returns:
        List of session IDs

    Example:
        ```
        GET /chat/sessions
        ```
    """
    try:
        from pathlib import Path
        from ..utils.config import ANALYSIS_DIR

        analysis_dir = Path(ANALYSIS_DIR)
        sessions = []

        for file in analysis_dir.glob("research_*.json"):
            session_id = file.stem.replace("research_", "")
            sessions.append({
                "session_id": session_id,
                "file": str(file.name)
            })

        return {
            "sessions": sessions,
            "count": len(sessions)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List error: {str(e)}")
