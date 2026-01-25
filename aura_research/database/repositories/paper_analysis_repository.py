"""
Paper Analysis Repository
Database operations for PaperAnalyses table
"""

from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository


class PaperAnalysisRepository(BaseRepository):
    """Repository for paper analysis operations (subordinate agent results)."""

    @property
    def table_name(self) -> str:
        return "PaperAnalyses"

    @property
    def primary_key(self) -> str:
        return "analysis_id"

    def create(
        self,
        paper_id: int,
        session_id: int,
        agent_id: Optional[str] = None,
        summary: Optional[str] = None,
        key_points: Optional[List[str]] = None,
        methodology: Optional[str] = None,
        key_findings: Optional[List[str]] = None,
        novelty: Optional[str] = None,
        limitations: Optional[List[str]] = None,
        relevance_score: Optional[float] = None,
        technical_depth: Optional[str] = None,
        research_domain: Optional[str] = None,
        core_ideas: Optional[List[str]] = None,
        reasoning: Optional[str] = None,
        citations: Optional[List[Dict]] = None
    ) -> int:
        """Create a new paper analysis record."""
        query = """
            INSERT INTO PaperAnalyses
            (paper_id, session_id, agent_id, summary, key_points, methodology,
             key_findings, novelty, limitations, relevance_score, technical_depth,
             research_domain, core_ideas, reasoning, citations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self.db.insert_and_get_id(
            query,
            (
                paper_id, session_id, agent_id, summary,
                self.to_json(key_points), methodology,
                self.to_json(key_findings), novelty,
                self.to_json(limitations), relevance_score, technical_depth,
                research_domain, self.to_json(core_ideas), reasoning,
                self.to_json(citations)
            )
        )

    def create_from_analysis_result(
        self,
        paper_id: int,
        session_id: int,
        analysis: Dict[str, Any],
        agent_id: Optional[str] = None
    ) -> int:
        """Create analysis record from agent result dictionary."""
        metadata = analysis.get('metadata', {})
        return self.create(
            paper_id=paper_id,
            session_id=session_id,
            agent_id=agent_id,
            summary=analysis.get('summary'),
            key_points=analysis.get('key_points'),
            methodology=metadata.get('methodology'),
            key_findings=metadata.get('key_findings'),
            novelty=metadata.get('novelty'),
            limitations=metadata.get('limitations'),
            relevance_score=metadata.get('relevance_score'),
            technical_depth=metadata.get('technical_depth'),
            research_domain=metadata.get('research_domain'),
            core_ideas=metadata.get('core_ideas'),
            reasoning=metadata.get('reasoning'),
            citations=analysis.get('citations')
        )

    def get_by_paper(self, paper_id: int) -> Optional[Dict[str, Any]]:
        """Get analysis for a specific paper."""
        query = "SELECT * FROM PaperAnalyses WHERE paper_id = ?"
        result = self.db.fetch_one(query, (paper_id,))
        return self._parse_json_fields(result) if result else None

    def get_by_session(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all analyses for a session."""
        query = """
            SELECT pa.*, p.title as paper_title, p.authors as paper_authors
            FROM PaperAnalyses pa
            JOIN Papers p ON pa.paper_id = p.paper_id
            WHERE pa.session_id = ?
            ORDER BY pa.relevance_score DESC
        """
        results = self.db.fetch_all(query, (session_id,))
        return [self._parse_json_fields(r) for r in results]

    def get_by_agent(self, session_id: int, agent_id: str) -> List[Dict[str, Any]]:
        """Get analyses by specific agent."""
        query = """
            SELECT * FROM PaperAnalyses
            WHERE session_id = ? AND agent_id = ?
        """
        results = self.db.fetch_all(query, (session_id, agent_id))
        return [self._parse_json_fields(r) for r in results]

    def get_high_relevance(
        self,
        session_id: int,
        min_score: float = 7.0
    ) -> List[Dict[str, Any]]:
        """Get analyses with high relevance score."""
        query = """
            SELECT pa.*, p.title as paper_title
            FROM PaperAnalyses pa
            JOIN Papers p ON pa.paper_id = p.paper_id
            WHERE pa.session_id = ? AND pa.relevance_score >= ?
            ORDER BY pa.relevance_score DESC
        """
        results = self.db.fetch_all(query, (session_id, min_score))
        return [self._parse_json_fields(r) for r in results]

    def get_analysis_count(self, session_id: int) -> int:
        """Get analysis count for a session."""
        query = "SELECT COUNT(*) as count FROM PaperAnalyses WHERE session_id = ?"
        result = self.db.fetch_one(query, (session_id,))
        return result['count'] if result else 0

    def get_average_relevance_score(self, session_id: int) -> Optional[float]:
        """Get average relevance score for a session."""
        query = """
            SELECT AVG(relevance_score) as avg_score
            FROM PaperAnalyses
            WHERE session_id = ? AND relevance_score IS NOT NULL
        """
        result = self.db.fetch_one(query, (session_id,))
        return float(result['avg_score']) if result and result['avg_score'] else None

    def get_all_key_findings(self, session_id: int) -> List[str]:
        """Get all key findings for a session (for synthesis)."""
        query = """
            SELECT key_findings FROM PaperAnalyses
            WHERE session_id = ? AND key_findings IS NOT NULL
        """
        results = self.db.fetch_all(query, (session_id,))
        all_findings = []
        for r in results:
            findings = self.from_json(r.get('key_findings'))
            if findings:
                all_findings.extend(findings)
        return all_findings

    def get_all_methodologies(self, session_id: int) -> List[str]:
        """Get all methodologies for a session."""
        query = """
            SELECT DISTINCT methodology FROM PaperAnalyses
            WHERE session_id = ? AND methodology IS NOT NULL
        """
        results = self.db.fetch_all(query, (session_id,))
        return [r['methodology'] for r in results if r.get('methodology')]

    def _parse_json_fields(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON fields in a record."""
        json_fields = [
            'key_points', 'key_findings', 'limitations',
            'core_ideas', 'citations', 'paper_authors'
        ]
        for field in json_fields:
            if record.get(field):
                record[field] = self.from_json(record[field])
        return record
