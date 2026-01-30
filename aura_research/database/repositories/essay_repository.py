"""
Essay Repository
Database operations for Essays table
"""

from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository


class EssayRepository(BaseRepository):
    """Repository for essay operations (summarizer agent results)."""

    @property
    def table_name(self) -> str:
        return "Essays"

    @property
    def primary_key(self) -> str:
        return "essay_id"

    def create(
        self,
        session_id: int,
        title: Optional[str] = None,
        introduction: Optional[str] = None,
        body: Optional[str] = None,
        conclusion: Optional[str] = None,
        full_content: Optional[str] = None,
        full_content_markdown: Optional[str] = None,
        audio_content: Optional[str] = None,
        references_list: Optional[List[Dict]] = None,
        word_count: Optional[int] = None,
        citation_count: Optional[int] = None,
        synthesis_themes: Optional[List[str]] = None
    ) -> int:
        """Create a new essay record."""
        # Try with audio_content first (standard path when migration is applied)
        try:
            query = """
                INSERT INTO Essays
                (session_id, title, introduction, body, conclusion,
                 full_content, full_content_markdown, audio_content, references_list,
                 word_count, citation_count, synthesis_themes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            return self.db.insert_and_get_id(
                query,
                (
                    session_id, title, introduction, body, conclusion,
                    full_content, full_content_markdown, audio_content,
                    self.to_json(references_list), word_count, citation_count,
                    self.to_json(synthesis_themes)
                )
            )
        except Exception as e:
            error_msg = str(e)
            # Check if error is due to missing audio_content column (defensive fallback)
            if 'audio_content' in error_msg and ('42S22' in error_msg or 'Invalid column' in error_msg):
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"[EssayRepository] audio_content column not found, falling back to legacy schema")
                # Retry without audio_content column
                query = """
                    INSERT INTO Essays
                    (session_id, title, introduction, body, conclusion,
                     full_content, full_content_markdown, references_list,
                     word_count, citation_count, synthesis_themes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                return self.db.insert_and_get_id(
                    query,
                    (
                        session_id, title, introduction, body, conclusion,
                        full_content, full_content_markdown,
                        self.to_json(references_list), word_count, citation_count,
                        self.to_json(synthesis_themes)
                    )
                )
            else:
                # Different error, re-raise
                raise

    def create_from_essay_result(
        self,
        session_id: int,
        essay_data: Dict[str, Any]
    ) -> int:
        """Create essay record from summarizer agent result."""
        return self.create(
            session_id=session_id,
            title=essay_data.get('title'),
            introduction=essay_data.get('introduction'),
            body=essay_data.get('body'),
            conclusion=essay_data.get('conclusion'),
            full_content=essay_data.get('essay') or essay_data.get('full_content'),
            full_content_markdown=essay_data.get('essay_markdown'),
            audio_content=essay_data.get('audio_essay'),  # NEW: store audio-optimized version
            references_list=essay_data.get('references'),
            word_count=essay_data.get('word_count'),
            citation_count=essay_data.get('citation_count'),
            synthesis_themes=essay_data.get('themes') or essay_data.get('synthesis_themes')
        )

    def get_by_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get essay for a specific session."""
        query = "SELECT * FROM Essays WHERE session_id = ?"
        result = self.db.fetch_one(query, (session_id,))
        return self._parse_json_fields(result) if result else None

    def get_essay_content(self, session_id: int) -> Optional[str]:
        """Get just the full essay content."""
        query = "SELECT full_content FROM Essays WHERE session_id = ?"
        result = self.db.fetch_one(query, (session_id,))
        return result['full_content'] if result else None

    def get_essay_markdown(self, session_id: int) -> Optional[str]:
        """Get the markdown version of the essay."""
        query = "SELECT full_content_markdown FROM Essays WHERE session_id = ?"
        result = self.db.fetch_one(query, (session_id,))
        return result['full_content_markdown'] if result else None

    def get_essay_audio_content(self, session_id: int) -> Optional[str]:
        """Get the audio-optimized version of the essay."""
        query = "SELECT audio_content FROM Essays WHERE session_id = ?"
        result = self.db.fetch_one(query, (session_id,))
        return result['audio_content'] if result else None

    def update_essay(
        self,
        session_id: int,
        full_content: str,
        full_content_markdown: Optional[str] = None,
        word_count: Optional[int] = None
    ) -> bool:
        """Update essay content."""
        query = """
            UPDATE Essays
            SET full_content = ?,
                full_content_markdown = ?,
                word_count = ?
            WHERE session_id = ?
        """
        rows_affected = self.db.execute(
            query,
            (full_content, full_content_markdown, word_count, session_id)
        )
        return rows_affected > 0

    def essay_exists(self, session_id: int) -> bool:
        """Check if essay exists for a session."""
        query = "SELECT 1 FROM Essays WHERE session_id = ?"
        result = self.db.fetch_one(query, (session_id,))
        return result is not None

    def get_recent_essays(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent essays with session info."""
        query = """
            SELECT e.*, rs.query as research_query, rs.session_code
            FROM Essays e
            JOIN ResearchSessions rs ON e.session_id = rs.session_id
            ORDER BY e.generated_at DESC
            OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
        """
        results = self.db.fetch_all(query, (limit,))
        return [self._parse_json_fields(r) for r in results]

    def get_essay_stats(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get essay statistics."""
        query = """
            SELECT
                word_count,
                citation_count,
                LEN(introduction) as intro_length,
                LEN(body) as body_length,
                LEN(conclusion) as conclusion_length,
                generated_at
            FROM Essays
            WHERE session_id = ?
        """
        return self.db.fetch_one(query, (session_id,))

    def delete_by_session(self, session_id: int) -> bool:
        """Delete essay for a session."""
        query = "DELETE FROM Essays WHERE session_id = ?"
        rows_affected = self.db.execute(query, (session_id,))
        return rows_affected > 0

    def _parse_json_fields(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON fields in a record."""
        if record.get('references_list'):
            record['references_list'] = self.from_json(record['references_list'])
        if record.get('synthesis_themes'):
            record['synthesis_themes'] = self.from_json(record['synthesis_themes'])
        return record
