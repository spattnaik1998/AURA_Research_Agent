"""
Paper Repository
Database operations for Papers table
"""

from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository


class PaperRepository(BaseRepository):
    """Repository for research paper operations."""

    @property
    def table_name(self) -> str:
        return "Papers"

    @property
    def primary_key(self) -> str:
        return "paper_id"

    def create(
        self,
        session_id: int,
        title: str,
        authors: Optional[List[str]] = None,
        abstract: Optional[str] = None,
        publication_year: Optional[int] = None,
        source: Optional[str] = None,
        url: Optional[str] = None,
        citation_count: int = 0,
        category: Optional[str] = None
    ) -> int:
        """Create a new paper record and return the paper_id."""
        query = """
            INSERT INTO Papers
            (session_id, title, authors, abstract, publication_year,
             source, url, citation_count, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self.db.insert_and_get_id(
            query,
            (
                session_id, title, self.to_json(authors), abstract,
                publication_year, source, url, citation_count, category
            )
        )

    def create_many(self, session_id: int, papers: List[Dict]) -> int:
        """Bulk insert papers for a session."""
        query = """
            INSERT INTO Papers
            (session_id, title, authors, abstract, publication_year,
             source, url, citation_count, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params_list = [
            (
                session_id,
                p.get('title', 'Untitled'),
                self.to_json(p.get('authors')),
                p.get('abstract') or p.get('snippet'),
                p.get('publication_year') or p.get('year'),
                p.get('source') or p.get('publicationInfo'),
                p.get('url') or p.get('link'),
                p.get('citation_count') or p.get('citedBy', 0),
                p.get('category')
            )
            for p in papers
        ]
        return self.db.execute_many(query, params_list)

    def get_by_session(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all papers for a session."""
        query = """
            SELECT * FROM Papers
            WHERE session_id = ?
            ORDER BY citation_count DESC
        """
        results = self.db.fetch_all(query, (session_id,))
        for r in results:
            if r.get('authors'):
                r['authors'] = self.from_json(r['authors'])
        return results

    def get_by_category(
        self,
        session_id: int,
        category: str
    ) -> List[Dict[str, Any]]:
        """Get papers by category within a session."""
        query = """
            SELECT * FROM Papers
            WHERE session_id = ? AND category = ?
            ORDER BY citation_count DESC
        """
        results = self.db.fetch_all(query, (session_id, category))
        for r in results:
            if r.get('authors'):
                r['authors'] = self.from_json(r['authors'])
        return results

    def get_high_impact_papers(
        self,
        session_id: int,
        min_citations: int = 10
    ) -> List[Dict[str, Any]]:
        """Get papers with high citation count."""
        query = """
            SELECT * FROM Papers
            WHERE session_id = ? AND citation_count >= ?
            ORDER BY citation_count DESC
        """
        results = self.db.fetch_all(query, (session_id, min_citations))
        for r in results:
            if r.get('authors'):
                r['authors'] = self.from_json(r['authors'])
        return results

    def get_paper_count(self, session_id: int) -> int:
        """Get paper count for a session."""
        query = "SELECT COUNT(*) as count FROM Papers WHERE session_id = ?"
        result = self.db.fetch_one(query, (session_id,))
        return result['count'] if result else 0

    def update_category(self, paper_id: int, category: str) -> bool:
        """Update paper category."""
        query = "UPDATE Papers SET category = ? WHERE paper_id = ?"
        rows_affected = self.db.execute(query, (category, paper_id))
        return rows_affected > 0

    def delete_by_session(self, session_id: int) -> int:
        """Delete all papers for a session."""
        query = "DELETE FROM Papers WHERE session_id = ?"
        return self.db.execute(query, (session_id,))
