"""
Chat Repository
Database operations for ChatConversations and ChatMessages tables
"""

from typing import Optional, List, Dict, Any
import uuid
from .base_repository import BaseRepository


class ChatRepository(BaseRepository):
    """Repository for chat conversation and message operations."""

    @property
    def table_name(self) -> str:
        return "ChatConversations"

    @property
    def primary_key(self) -> str:
        return "conversation_id"

    # ==================== Conversation Methods ====================

    def create_conversation(
        self,
        session_id: int,
        user_id: Optional[int] = None,
        title: Optional[str] = None,
        language: str = "en"
    ) -> Optional[Dict[str, Any]]:
        """Create a new chat conversation and return it."""
        conversation_code = str(uuid.uuid4())
        query = """
            INSERT INTO ChatConversations
            (conversation_code, session_id, user_id, title, language)
            VALUES (?, ?, ?, ?, ?)
        """
        conversation_id = self.db.insert_and_get_id(
            query,
            (conversation_code, session_id, user_id, title, language)
        )

        # Validate conversation was created
        if not conversation_id or conversation_id <= 0:
            print(f"[ChatRepo] Warning: Failed to create conversation for session {session_id}")
            return None

        return {
            'conversation_id': conversation_id,
            'conversation_code': conversation_code,
            'session_id': session_id,
            'language': language
        }

    def get_conversation_by_code(
        self,
        conversation_code: str
    ) -> Optional[Dict[str, Any]]:
        """Get conversation by its code."""
        query = "SELECT * FROM ChatConversations WHERE conversation_code = ?"
        return self.db.fetch_one(query, (conversation_code,))

    def get_session_conversations(
        self,
        session_id: int
    ) -> List[Dict[str, Any]]:
        """Get all conversations for a research session."""
        query = """
            SELECT cc.*,
                   (SELECT COUNT(*) FROM ChatMessages WHERE conversation_id = cc.conversation_id) as message_count
            FROM ChatConversations cc
            WHERE cc.session_id = ?
            ORDER BY cc.updated_at DESC
        """
        return self.db.fetch_all(query, (session_id,))

    def get_user_conversations(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get all conversations for a user."""
        query = """
            SELECT cc.*, rs.query as research_query
            FROM ChatConversations cc
            JOIN ResearchSessions rs ON cc.session_id = rs.session_id
            WHERE cc.user_id = ?
            ORDER BY cc.updated_at DESC
            OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
        """
        return self.db.fetch_all(query, (user_id, limit))

    def update_conversation_title(
        self,
        conversation_id: int,
        title: str
    ) -> bool:
        """Update conversation title."""
        query = """
            UPDATE ChatConversations
            SET title = ?, updated_at = GETDATE()
            WHERE conversation_id = ?
        """
        rows_affected = self.db.execute(query, (title, conversation_id))
        return rows_affected > 0

    def deactivate_conversation(self, conversation_id: int) -> bool:
        """Deactivate a conversation."""
        query = """
            UPDATE ChatConversations
            SET is_active = 0, updated_at = GETDATE()
            WHERE conversation_id = ?
        """
        rows_affected = self.db.execute(query, (conversation_id,))
        return rows_affected > 0

    # ==================== Message Methods ====================

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        context_used: Optional[List[Dict]] = None,
        context_scores: Optional[List[float]] = None,
        tokens_used: Optional[int] = None
    ) -> int:
        """Add a message to a conversation."""
        query = """
            INSERT INTO ChatMessages
            (conversation_id, role, content, context_used, context_scores, tokens_used)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        message_id = self.db.insert_and_get_id(
            query,
            (
                conversation_id, role, content,
                self.to_json(context_used),
                self.to_json(context_scores),
                tokens_used
            )
        )

        # Update conversation's updated_at timestamp
        self.db.execute(
            "UPDATE ChatConversations SET updated_at = GETDATE() WHERE conversation_id = ?",
            (conversation_id,)
        )

        return message_id

    def add_user_message(
        self,
        conversation_id: int,
        content: str
    ) -> int:
        """Add a user message."""
        return self.add_message(conversation_id, 'user', content)

    def add_assistant_message(
        self,
        conversation_id: int,
        content: str,
        context_used: Optional[List[Dict]] = None,
        context_scores: Optional[List[float]] = None,
        tokens_used: Optional[int] = None
    ) -> int:
        """Add an assistant message with context."""
        return self.add_message(
            conversation_id, 'assistant', content,
            context_used, context_scores, tokens_used
        )

    def get_conversation_messages(
        self,
        conversation_id: int,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all messages in a conversation."""
        if limit:
            query = """
                SELECT * FROM ChatMessages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
            """
            results = self.db.fetch_all(query, (conversation_id, limit))
        else:
            query = """
                SELECT * FROM ChatMessages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
            """
            results = self.db.fetch_all(query, (conversation_id,))

        return [self._parse_message_json(r) for r in results]

    def get_recent_messages(
        self,
        conversation_id: int,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """Get the most recent messages (for context window)."""
        query = """
            SELECT TOP (?) * FROM (
                SELECT * FROM ChatMessages
                WHERE conversation_id = ?
                ORDER BY created_at DESC
            ) sub
            ORDER BY created_at ASC
        """
        results = self.db.fetch_all(query, (count, conversation_id))
        return [self._parse_message_json(r) for r in results]

    def get_message_count(self, conversation_id: int) -> int:
        """Get message count for a conversation."""
        query = "SELECT COUNT(*) as count FROM ChatMessages WHERE conversation_id = ?"
        result = self.db.fetch_one(query, (conversation_id,))
        return result['count'] if result else 0

    def delete_conversation_messages(self, conversation_id: int) -> int:
        """Delete all messages in a conversation."""
        query = "DELETE FROM ChatMessages WHERE conversation_id = ?"
        return self.db.execute(query, (conversation_id,))

    def get_conversation_history_for_llm(
        self,
        conversation_id: int,
        max_messages: int = 20
    ) -> List[Dict[str, str]]:
        """Get conversation history formatted for LLM context."""
        messages = self.get_recent_messages(conversation_id, max_messages)
        return [
            {'role': m['role'], 'content': m['content']}
            for m in messages
            if m['role'] in ('user', 'assistant')
        ]

    def _parse_message_json(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON fields in a message record."""
        if record.get('context_used'):
            record['context_used'] = self.from_json(record['context_used'])
        if record.get('context_scores'):
            record['context_scores'] = self.from_json(record['context_scores'])
        return record
