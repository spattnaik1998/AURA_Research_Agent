"""
Audit Log Repository
Database operations for AuditLog table
"""

from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository


class AuditLogRepository(BaseRepository):
    """Repository for audit log operations."""

    @property
    def table_name(self) -> str:
        return "AuditLog"

    @property
    def primary_key(self) -> str:
        return "log_id"

    def log_action(
        self,
        action: str,
        user_id: Optional[int] = None,
        session_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """Log an action to the audit log."""
        query = """
            INSERT INTO AuditLog
            (user_id, session_id, action, entity_type, entity_id,
             details, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self.db.insert_and_get_id(
            query,
            (
                user_id, session_id, action, entity_type, entity_id,
                self.to_json(details), ip_address, user_agent
            )
        )

    def log_research_started(
        self,
        session_id: int,
        user_id: Optional[int] = None,
        query: str = None,
        ip_address: Optional[str] = None
    ) -> int:
        """Log research session started."""
        return self.log_action(
            action='research_started',
            user_id=user_id,
            session_id=session_id,
            entity_type='research_session',
            entity_id=session_id,
            details={'query': query},
            ip_address=ip_address
        )

    def log_research_completed(
        self,
        session_id: int,
        user_id: Optional[int] = None,
        papers_count: int = 0,
        analyses_count: int = 0
    ) -> int:
        """Log research session completed."""
        return self.log_action(
            action='research_completed',
            user_id=user_id,
            session_id=session_id,
            entity_type='research_session',
            entity_id=session_id,
            details={
                'papers_count': papers_count,
                'analyses_count': analyses_count
            }
        )

    def log_research_failed(
        self,
        session_id: int,
        error_message: str,
        user_id: Optional[int] = None
    ) -> int:
        """Log research session failed."""
        return self.log_action(
            action='research_failed',
            user_id=user_id,
            session_id=session_id,
            entity_type='research_session',
            entity_id=session_id,
            details={'error': error_message}
        )

    def log_essay_generated(
        self,
        session_id: int,
        essay_id: int,
        word_count: int = 0,
        user_id: Optional[int] = None
    ) -> int:
        """Log essay generation."""
        return self.log_action(
            action='essay_generated',
            user_id=user_id,
            session_id=session_id,
            entity_type='essay',
            entity_id=essay_id,
            details={'word_count': word_count}
        )

    def log_chat_message(
        self,
        session_id: int,
        conversation_id: int,
        message_role: str,
        user_id: Optional[int] = None
    ) -> int:
        """Log chat message sent."""
        return self.log_action(
            action='chat_message',
            user_id=user_id,
            session_id=session_id,
            entity_type='conversation',
            entity_id=conversation_id,
            details={'role': message_role}
        )

    def log_graph_built(
        self,
        session_id: int,
        nodes_count: int = 0,
        edges_count: int = 0,
        user_id: Optional[int] = None
    ) -> int:
        """Log graph building."""
        return self.log_action(
            action='graph_built',
            user_id=user_id,
            session_id=session_id,
            entity_type='graph',
            details={
                'nodes_count': nodes_count,
                'edges_count': edges_count
            }
        )

    def log_questions_generated(
        self,
        session_id: int,
        questions_count: int = 0,
        gaps_count: int = 0,
        user_id: Optional[int] = None
    ) -> int:
        """Log question generation."""
        return self.log_action(
            action='questions_generated',
            user_id=user_id,
            session_id=session_id,
            entity_type='ideation',
            details={
                'questions_count': questions_count,
                'gaps_count': gaps_count
            }
        )

    def log_user_login(
        self,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> int:
        """Log user login."""
        return self.log_action(
            action='user_login',
            user_id=user_id,
            entity_type='user',
            entity_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

    def log_user_logout(
        self,
        user_id: int,
        ip_address: Optional[str] = None
    ) -> int:
        """Log user logout."""
        return self.log_action(
            action='user_logout',
            user_id=user_id,
            entity_type='user',
            entity_id=user_id,
            ip_address=ip_address
        )

    def log_user_registered(
        self,
        user_id: int,
        username: str,
        ip_address: Optional[str] = None
    ) -> int:
        """Log user registration."""
        return self.log_action(
            action='user_registered',
            user_id=user_id,
            entity_type='user',
            entity_id=user_id,
            details={'username': username},
            ip_address=ip_address
        )

    def get_user_activity(
        self,
        user_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get activity log for a user."""
        query = """
            SELECT * FROM AuditLog
            WHERE user_id = ?
            ORDER BY created_at DESC
            OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
        """
        results = self.db.fetch_all(query, (user_id, limit))
        for r in results:
            if r.get('details'):
                r['details'] = self.from_json(r['details'])
        return results

    def get_session_activity(
        self,
        session_id: int
    ) -> List[Dict[str, Any]]:
        """Get activity log for a research session."""
        query = """
            SELECT * FROM AuditLog
            WHERE session_id = ?
            ORDER BY created_at ASC
        """
        results = self.db.fetch_all(query, (session_id,))
        for r in results:
            if r.get('details'):
                r['details'] = self.from_json(r['details'])
        return results

    def get_recent_actions(
        self,
        action_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent actions, optionally filtered by type."""
        if action_type:
            query = """
                SELECT al.*, u.username
                FROM AuditLog al
                LEFT JOIN Users u ON al.user_id = u.user_id
                WHERE al.action = ?
                ORDER BY al.created_at DESC
                OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
            """
            results = self.db.fetch_all(query, (action_type, limit))
        else:
            query = """
                SELECT al.*, u.username
                FROM AuditLog al
                LEFT JOIN Users u ON al.user_id = u.user_id
                ORDER BY al.created_at DESC
                OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
            """
            results = self.db.fetch_all(query, (limit,))

        for r in results:
            if r.get('details'):
                r['details'] = self.from_json(r['details'])
        return results

    def get_action_counts(
        self,
        user_id: Optional[int] = None,
        days: int = 7
    ) -> Dict[str, int]:
        """Get action counts for analytics."""
        if user_id:
            query = """
                SELECT action, COUNT(*) as count
                FROM AuditLog
                WHERE user_id = ?
                  AND created_at >= DATEADD(day, -?, GETDATE())
                GROUP BY action
            """
            results = self.db.fetch_all(query, (user_id, days))
        else:
            query = """
                SELECT action, COUNT(*) as count
                FROM AuditLog
                WHERE created_at >= DATEADD(day, -?, GETDATE())
                GROUP BY action
            """
            results = self.db.fetch_all(query, (days,))

        return {r['action']: r['count'] for r in results}
