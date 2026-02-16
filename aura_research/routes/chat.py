"""
Chat API routes for AURA RAG chatbot
Integrated with SQL Server database
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from ..rag.chatbot import get_chatbot, clear_chatbot
from ..services.db_service import get_db_service
from ..services.auth_service import get_auth_service
from ..utils.rate_limiter import limiter

security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/chat", tags=["chat"])


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


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    session_id: str
    conversation_id: Optional[str] = None
    language: Optional[str] = "English"
    # Note: user_id is now extracted from JWT token, not from request body


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    context_used: str
    conversation_id: str
    session_id: str
    db_conversation_id: Optional[int] = None


class ChatHistoryResponse(BaseModel):
    """Chat history response"""
    messages: List[Dict[str, str]]
    conversation_id: str


@router.post("/", response_model=ChatResponse)
@limiter.limit("50/hour")
async def chat(
    body: ChatRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Send message to RAG chatbot (requires authentication and session ownership)

    Args:
        request: Chat request with message and session_id
        current_user: Authenticated user from JWT token

    Returns:
        Chat response with answer and context

    Example:
        ```
        POST /chat
        Authorization: Bearer <token>
        {
            "message": "What are the main findings about machine learning in healthcare?",
            "session_id": "20251018_133827",
            "conversation_id": "user123"
        }
        ```
    """
    try:
        db_service = get_db_service()
        user_id = current_user["user_id"]

        # Verify the user owns this session
        if not verify_session_access(body.session_id, user_id, db_service):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this session"
            )

        # Get or create conversation in database (non-fatal)
        db_conv = None
        language_code = _get_language_code(body.language)

        if body.session_id:
            try:
                db_conv = db_service.get_or_create_conversation(
                    session_code=body.session_id,
                    conversation_code=body.conversation_id,
                    user_id=user_id,
                    language=language_code
                )
            except Exception as e:
                print(f"[Chat] Warning: Failed to create conversation in DB: {e}")

        # Get chatbot instance
        chatbot = get_chatbot(body.session_id)

        # Process message
        result = await chatbot.chat(
            message=body.message,
            conversation_id=body.conversation_id,
            language=body.language or "English"
        )

        # Save messages to database (non-fatal if it fails)
        # Validate conversation_id is valid (> 0)
        if db_conv and db_conv.get('conversation_id', 0) > 0:
            try:
                # Save user message
                db_service.save_chat_message(
                    conversation_id=db_conv['conversation_id'],
                    role='user',
                    content=body.message,
                    user_id=user_id
                )

                # Save assistant response
                db_service.save_chat_message(
                    conversation_id=db_conv['conversation_id'],
                    role='assistant',
                    content=result['response'],
                    context_used=_parse_context(result.get('context_used', '')),
                    user_id=user_id
                )
            except Exception as db_error:
                print(f"[Chat] Warning: Failed to save messages to DB: {db_error}")

        response = ChatResponse(**result)
        if db_conv and db_conv.get('conversation_id', 0) > 0:
            response.db_conversation_id = db_conv['conversation_id']

        return response

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/history/{session_id}/{conversation_id}", response_model=ChatHistoryResponse)
async def get_history(
    session_id: str,
    conversation_id: str = "default",
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get conversation history (requires authentication and session ownership)

    Args:
        session_id: Research session ID
        conversation_id: Conversation ID
        current_user: Authenticated user from JWT token

    Returns:
        List of messages in conversation

    Example:
        ```
        GET /chat/history/20251018_133827/user123
        Authorization: Bearer <token>
        ```
    """
    try:
        db_service = get_db_service()
        user_id = current_user["user_id"]

        # Verify ownership
        if not verify_session_access(session_id, user_id, db_service):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this session"
            )

        # Try to get from database first
        db_conv = db_service.chat.get_conversation_by_code(conversation_id)
        if db_conv:
            messages = db_service.get_conversation_history(db_conv['conversation_id'])
            formatted_messages = [
                {'role': m['role'], 'content': m['content']}
                for m in messages
            ]
            return ChatHistoryResponse(
                messages=formatted_messages,
                conversation_id=conversation_id
            )

        # Fallback to in-memory history
        chatbot = get_chatbot(session_id)
        history = chatbot.get_conversation_history(conversation_id)

        return ChatHistoryResponse(
            messages=history,
            conversation_id=conversation_id
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History error: {str(e)}")


@router.delete("/{session_id}")
async def clear_chat_session(
    session_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Clear chatbot instance for session (requires authentication and ownership)

    Args:
        session_id: Research session ID
        current_user: Authenticated user from JWT token

    Returns:
        Success message

    Example:
        ```
        DELETE /chat/20251018_133827
        Authorization: Bearer <token>
        ```
    """
    try:
        db_service = get_db_service()
        user_id = current_user["user_id"]

        # Verify ownership
        if not verify_session_access(session_id, user_id, db_service):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this session"
            )

        clear_chatbot(session_id)
        return {"message": f"Chatbot session {session_id} cleared"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear error: {str(e)}")


@router.get("/sessions")
async def list_sessions(
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    List available research sessions for the authenticated user

    Args:
        current_user: Authenticated user from JWT token

    Returns:
        List of sessions with session_id, query, and timestamp (only user's own sessions)

    Example:
        ```
        GET /chat/sessions
        Authorization: Bearer <token>
        ```
    """
    try:
        db_service = get_db_service()
        user_id = current_user["user_id"]

        print(f"[Chat Sessions] Request for user_id: {user_id}")

        # Get only the current user's completed sessions
        db_sessions = db_service.get_completed_sessions(limit=50, user_id=user_id)
        print(f"[Chat Sessions] Found {len(db_sessions)} sessions for user {user_id}")

        sessions = []
        for session in db_sessions:
            # Get conversation count for this session
            session_db_id = db_service.get_session_id(session['session_code'])
            conversations = []
            if session_db_id:
                conversations = db_service.chat.get_session_conversations(session_db_id)

            # Format date
            formatted_date = session['session_code']
            if session.get('completed_at'):
                formatted_date = session['completed_at'].strftime("%B %d, %Y at %I:%M %p")
            elif session.get('started_at'):
                formatted_date = session['started_at'].strftime("%B %d, %Y at %I:%M %p")

            sessions.append({
                "session_id": session['session_code'],
                "query": session['query'],
                "date": formatted_date,
                "status": session['status'],
                "conversation_count": len(conversations),
                "has_essay": bool(session.get('has_essay', 0))
            })

        return {
            "sessions": sessions,
            "count": len(sessions)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List error: {str(e)}")


@router.get("/conversations/{session_id}")
async def list_conversations(
    session_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    List all conversations for a research session (requires authentication and ownership)

    Args:
        session_id: Research session ID
        current_user: Authenticated user from JWT token

    Returns:
        List of conversations

    Example:
        ```
        GET /chat/conversations/20251018_133827
        Authorization: Bearer <token>
        ```
    """
    try:
        db_service = get_db_service()
        user_id = current_user["user_id"]

        # Verify ownership
        if not verify_session_access(session_id, user_id, db_service):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this session"
            )

        conversations = db_service.get_session_conversations(session_id)

        return {
            "session_id": session_id,
            "conversations": conversations,
            "count": len(conversations)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing conversations: {str(e)}")


async def _get_file_based_sessions() -> List[Dict]:
    """Fallback to file-based session listing"""
    from pathlib import Path
    from ..utils.config import ANALYSIS_DIR
    import json
    from datetime import datetime

    analysis_dir = Path(ANALYSIS_DIR)
    sessions = []

    for file in sorted(analysis_dir.glob("research_*.json"), reverse=True):
        session_id = file.stem.replace("research_", "")

        try:
            with open(file, 'r', encoding='utf-8') as f:
                research_data = json.load(f)

            query = research_data.get("query", "Unknown Query")

            try:
                timestamp = datetime.strptime(session_id, "%Y%m%d_%H%M%S")
                formatted_date = timestamp.strftime("%B %d, %Y at %I:%M %p")
            except:
                formatted_date = session_id

            sessions.append({
                "session_id": session_id,
                "query": query,
                "date": formatted_date,
                "file": str(file.name),
                "source": "file"
            })
        except Exception as e:
            print(f"[Chat] Error reading session file {file}: {str(e)}")
            sessions.append({
                "session_id": session_id,
                "query": "Error loading query",
                "date": session_id,
                "file": str(file.name),
                "source": "file"
            })

    return sessions


def _get_language_code(language: Optional[str]) -> str:
    """Convert language name to code"""
    language_map = {
        'English': 'en',
        'French': 'fr',
        'Chinese': 'zh',
        'Russian': 'ru'
    }
    return language_map.get(language, 'en')


def _parse_context(context_str: str) -> Optional[List[Dict]]:
    """Parse context string into list of context chunks"""
    if not context_str:
        return None

    # Split context into chunks
    chunks = context_str.split('\n\n')
    return [{'text': chunk.strip()} for chunk in chunks if chunk.strip()]
