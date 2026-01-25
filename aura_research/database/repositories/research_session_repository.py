"""
Research Session Repository
Database operations for ResearchSessions table
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from .base_repository import BaseRepository


class ResearchSessionRepository(BaseRepository):
    """Repository for research session operations."""

    @property
    def table_name(self) -> str:
        return "ResearchSessions"

    @property
    def primary_key(self) -> str:
        return "session_id"

    def create(
        self,
        session_code: str,
        query: str,
        user_id: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """Create a new research session and return the session_id."""
        sql = """
            INSERT INTO ResearchSessions
            (session_code, user_id, query, status, progress, metadata)
            VALUES (?, ?, ?, 'pending', 0, ?)
        """
        return self.db.insert_and_get_id(
            sql,
            (session_code, user_id, query, self.to_json(metadata))
        )

    def get_by_session_code(self, session_code: str) -> Optional[Dict[str, Any]]:
        """Get session by session code."""
        query = "SELECT * FROM ResearchSessions WHERE session_code = ?"
        result = self.db.fetch_one(query, (session_code,))
        if result and result.get('metadata'):
            result['metadata'] = self.from_json(result['metadata'])
        return result

    def update_status(
        self,
        session_id: int,
        status: str,
        progress: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update session status and progress."""
        if progress is not None:
            query = """
                UPDATE ResearchSessions
                SET status = ?, progress = ?, error_message = ?
                WHERE session_id = ?
            """
            params = (status, progress, error_message, session_id)
        else:
            query = """
                UPDATE ResearchSessions
                SET status = ?, error_message = ?
                WHERE session_id = ?
            """
            params = (status, error_message, session_id)

        rows_affected = self.db.execute(query, params)
        return rows_affected > 0

    def mark_completed(
        self,
        session_id: int,
        total_papers_found: int,
        total_papers_analyzed: int
    ) -> bool:
        """Mark session as completed."""
        query = """
            UPDATE ResearchSessions
            SET status = 'completed',
                progress = 100,
                total_papers_found = ?,
                total_papers_analyzed = ?,
                completed_at = GETDATE()
            WHERE session_id = ?
        """
        rows_affected = self.db.execute(
            query,
            (total_papers_found, total_papers_analyzed, session_id)
        )
        return rows_affected > 0

    def mark_failed(self, session_id: int, error_message: str) -> bool:
        """Mark session as failed with error message."""
        query = """
            UPDATE ResearchSessions
            SET status = 'failed',
                error_message = ?,
                completed_at = GETDATE()
            WHERE session_id = ?
        """
        rows_affected = self.db.execute(query, (error_message, session_id))
        return rows_affected > 0

    def get_user_sessions(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get all sessions for a user."""
        query = """
            SELECT * FROM ResearchSessions
            WHERE user_id = ?
            ORDER BY started_at DESC
            OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
        """
        return self.db.fetch_all(query, (user_id, limit))

    def get_recent_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent research sessions."""
        query = """
            SELECT * FROM ResearchSessions
            ORDER BY started_at DESC
            OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
        """
        return self.db.fetch_all(query, (limit,))

    def get_completed_sessions(
        self,
        limit: int = 20,
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get completed research sessions.

        Args:
            limit: Maximum number of sessions to return
            user_id: If provided, only return sessions for this user.
                     If None, returns all completed sessions (for backwards compatibility).

        Returns:
            List of completed sessions
        """
        if user_id is not None:
            query = """
                SELECT rs.*,
                    CASE WHEN EXISTS (SELECT 1 FROM Essays WHERE session_id = rs.session_id)
                         THEN 1 ELSE 0 END as has_essay
                FROM ResearchSessions rs
                WHERE rs.status = 'completed' AND rs.user_id = ?
                ORDER BY rs.completed_at DESC
                OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
            """
            return self.db.fetch_all(query, (user_id, limit))
        else:
            query = """
                SELECT rs.*,
                    CASE WHEN EXISTS (SELECT 1 FROM Essays WHERE session_id = rs.session_id)
                         THEN 1 ELSE 0 END as has_essay
                FROM ResearchSessions rs
                WHERE rs.status = 'completed'
                ORDER BY rs.completed_at DESC
                OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
            """
            return self.db.fetch_all(query, (limit,))

    def get_session_with_details(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get session with paper count and essay status."""
        query = """
            SELECT
                rs.*,
                (SELECT COUNT(*) FROM Papers WHERE session_id = rs.session_id) as paper_count,
                (SELECT COUNT(*) FROM PaperAnalyses WHERE session_id = rs.session_id) as analysis_count,
                CASE WHEN EXISTS (SELECT 1 FROM Essays WHERE session_id = rs.session_id)
                     THEN 1 ELSE 0 END as has_essay
            FROM ResearchSessions rs
            WHERE rs.session_id = ?
        """
        result = self.db.fetch_one(query, (session_id,))
        if result and result.get('metadata'):
            result['metadata'] = self.from_json(result['metadata'])
        return result

    def search_sessions(self, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search sessions by query text."""
        query = """
            SELECT * FROM ResearchSessions
            WHERE query LIKE ?
            ORDER BY started_at DESC
            OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
        """
        return self.db.fetch_all(query, (f"%{search_term}%", limit))

    def delete_session_cascade(self, session_id: int) -> bool:
        """Delete session and all related data (CASCADE handles this)."""
        query = "DELETE FROM ResearchSessions WHERE session_id = ?"
        rows_affected = self.db.execute(query, (session_id,))
        return rows_affected > 0
