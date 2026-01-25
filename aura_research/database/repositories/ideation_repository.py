"""
Ideation Repository
Database operations for ResearchGaps and ResearchQuestions tables
"""

from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository


class IdeationRepository(BaseRepository):
    """Repository for research gaps and question generation operations."""

    @property
    def table_name(self) -> str:
        return "ResearchQuestions"

    @property
    def primary_key(self) -> str:
        return "question_id"

    # ==================== Research Gaps Methods ====================

    def create_gap(
        self,
        session_id: int,
        gap_type: str,
        title: str,
        description: Optional[str] = None,
        evidence: Optional[List[str]] = None,
        priority_score: Optional[float] = None
    ) -> int:
        """Create a new research gap."""
        query = """
            INSERT INTO ResearchGaps
            (session_id, gap_type, title, description, evidence, priority_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        return self.db.insert_and_get_id(
            query,
            (session_id, gap_type, title, description, self.to_json(evidence), priority_score)
        )

    def create_gaps_bulk(
        self,
        session_id: int,
        gaps: List[Dict]
    ) -> int:
        """Bulk insert research gaps."""
        query = """
            INSERT INTO ResearchGaps
            (session_id, gap_type, title, description, evidence, priority_score)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params_list = [
            (
                session_id,
                g.get('type') or g.get('gap_type'),
                g.get('title'),
                g.get('description'),
                self.to_json(g.get('evidence')),
                g.get('priority_score')
            )
            for g in gaps
        ]
        return self.db.execute_many(query, params_list)

    def get_gaps_by_session(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all research gaps for a session."""
        query = """
            SELECT * FROM ResearchGaps
            WHERE session_id = ?
            ORDER BY priority_score DESC
        """
        results = self.db.fetch_all(query, (session_id,))
        for r in results:
            if r.get('evidence'):
                r['evidence'] = self.from_json(r['evidence'])
        return results

    def get_gaps_by_type(
        self,
        session_id: int,
        gap_type: str
    ) -> List[Dict[str, Any]]:
        """Get research gaps by type."""
        query = """
            SELECT * FROM ResearchGaps
            WHERE session_id = ? AND gap_type = ?
            ORDER BY priority_score DESC
        """
        results = self.db.fetch_all(query, (session_id, gap_type))
        for r in results:
            if r.get('evidence'):
                r['evidence'] = self.from_json(r['evidence'])
        return results

    def get_gap_by_id(self, gap_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific research gap."""
        query = "SELECT * FROM ResearchGaps WHERE gap_id = ?"
        result = self.db.fetch_one(query, (gap_id,))
        if result and result.get('evidence'):
            result['evidence'] = self.from_json(result['evidence'])
        return result

    # ==================== Research Questions Methods ====================

    def create_question(
        self,
        session_id: int,
        question_type: str,
        question_text: str,
        gap_id: Optional[int] = None,
        rationale: Optional[str] = None,
        score_novelty: Optional[float] = None,
        score_feasibility: Optional[float] = None,
        score_clarity: Optional[float] = None,
        score_impact: Optional[float] = None,
        score_specificity: Optional[float] = None,
        suggested_methods: Optional[List[str]] = None,
        related_concepts: Optional[List[str]] = None
    ) -> int:
        """Create a new research question."""
        # Calculate overall score
        scores = [s for s in [score_novelty, score_feasibility, score_clarity,
                              score_impact, score_specificity] if s is not None]
        score_overall = sum(scores) / len(scores) if scores else None

        query = """
            INSERT INTO ResearchQuestions
            (session_id, gap_id, question_type, question_text, rationale,
             score_novelty, score_feasibility, score_clarity, score_impact,
             score_specificity, score_overall, suggested_methods, related_concepts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self.db.insert_and_get_id(
            query,
            (
                session_id, gap_id, question_type, question_text, rationale,
                score_novelty, score_feasibility, score_clarity, score_impact,
                score_specificity, score_overall,
                self.to_json(suggested_methods), self.to_json(related_concepts)
            )
        )

    def create_questions_bulk(
        self,
        session_id: int,
        questions: List[Dict],
        gap_id: Optional[int] = None
    ) -> int:
        """Bulk insert research questions."""
        query = """
            INSERT INTO ResearchQuestions
            (session_id, gap_id, question_type, question_text, rationale,
             score_novelty, score_feasibility, score_clarity, score_impact,
             score_specificity, score_overall, suggested_methods, related_concepts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params_list = []
        for q in questions:
            scores = q.get('scores', {})
            score_values = [
                scores.get('novelty'), scores.get('feasibility'),
                scores.get('clarity'), scores.get('impact'), scores.get('specificity')
            ]
            valid_scores = [s for s in score_values if s is not None]
            score_overall = sum(valid_scores) / len(valid_scores) if valid_scores else None

            params_list.append((
                session_id,
                q.get('gap_id') or gap_id,
                q.get('type') or q.get('question_type'),
                q.get('question') or q.get('question_text'),
                q.get('rationale'),
                scores.get('novelty'),
                scores.get('feasibility'),
                scores.get('clarity'),
                scores.get('impact'),
                scores.get('specificity'),
                score_overall,
                self.to_json(q.get('suggested_methods')),
                self.to_json(q.get('related_concepts'))
            ))

        return self.db.execute_many(query, params_list)

    def get_questions_by_session(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all research questions for a session."""
        query = """
            SELECT rq.*, rg.title as gap_title, rg.gap_type
            FROM ResearchQuestions rq
            LEFT JOIN ResearchGaps rg ON rq.gap_id = rg.gap_id
            WHERE rq.session_id = ?
            ORDER BY rq.score_overall DESC
        """
        results = self.db.fetch_all(query, (session_id,))
        return [self._parse_question_json(r) for r in results]

    def get_questions_by_type(
        self,
        session_id: int,
        question_type: str
    ) -> List[Dict[str, Any]]:
        """Get questions by type."""
        query = """
            SELECT * FROM ResearchQuestions
            WHERE session_id = ? AND question_type = ?
            ORDER BY score_overall DESC
        """
        results = self.db.fetch_all(query, (session_id, question_type))
        return [self._parse_question_json(r) for r in results]

    def get_questions_by_gap(self, gap_id: int) -> List[Dict[str, Any]]:
        """Get questions linked to a specific gap."""
        query = """
            SELECT * FROM ResearchQuestions
            WHERE gap_id = ?
            ORDER BY score_overall DESC
        """
        results = self.db.fetch_all(query, (gap_id,))
        return [self._parse_question_json(r) for r in results]

    def get_top_questions(
        self,
        session_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top-ranked questions by overall score."""
        query = """
            SELECT * FROM ResearchQuestions
            WHERE session_id = ? AND score_overall IS NOT NULL
            ORDER BY score_overall DESC
            OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
        """
        results = self.db.fetch_all(query, (session_id, limit))
        return [self._parse_question_json(r) for r in results]

    def get_question_stats(self, session_id: int) -> Dict[str, Any]:
        """Get question statistics for a session."""
        query = """
            SELECT
                COUNT(*) as total_questions,
                COUNT(DISTINCT question_type) as question_types,
                AVG(score_overall) as avg_overall_score,
                AVG(score_novelty) as avg_novelty,
                AVG(score_feasibility) as avg_feasibility,
                AVG(score_impact) as avg_impact,
                MAX(score_overall) as max_score,
                MIN(score_overall) as min_score
            FROM ResearchQuestions
            WHERE session_id = ?
        """
        return self.db.fetch_one(query, (session_id,))

    def get_questions_grouped_by_type(
        self,
        session_id: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get questions grouped by type."""
        query = """
            SELECT * FROM ResearchQuestions
            WHERE session_id = ?
            ORDER BY question_type, score_overall DESC
        """
        results = self.db.fetch_all(query, (session_id,))

        grouped = {}
        for r in results:
            q_type = r.get('question_type', 'other')
            if q_type not in grouped:
                grouped[q_type] = []
            grouped[q_type].append(self._parse_question_json(r))

        return grouped

    def update_question_scores(
        self,
        question_id: int,
        novelty: Optional[float] = None,
        feasibility: Optional[float] = None,
        clarity: Optional[float] = None,
        impact: Optional[float] = None,
        specificity: Optional[float] = None
    ) -> bool:
        """Update question scores."""
        # Get current scores
        current = self.get_by_id(question_id)
        if not current:
            return False

        # Merge with new scores
        scores = {
            'novelty': novelty or current.get('score_novelty'),
            'feasibility': feasibility or current.get('score_feasibility'),
            'clarity': clarity or current.get('score_clarity'),
            'impact': impact or current.get('score_impact'),
            'specificity': specificity or current.get('score_specificity')
        }

        valid_scores = [v for v in scores.values() if v is not None]
        score_overall = sum(valid_scores) / len(valid_scores) if valid_scores else None

        query = """
            UPDATE ResearchQuestions
            SET score_novelty = ?, score_feasibility = ?, score_clarity = ?,
                score_impact = ?, score_specificity = ?, score_overall = ?
            WHERE question_id = ?
        """
        rows_affected = self.db.execute(
            query,
            (scores['novelty'], scores['feasibility'], scores['clarity'],
             scores['impact'], scores['specificity'], score_overall, question_id)
        )
        return rows_affected > 0

    def gaps_exist(self, session_id: int) -> bool:
        """Check if gaps exist for a session."""
        query = "SELECT 1 FROM ResearchGaps WHERE session_id = ?"
        result = self.db.fetch_one(query, (session_id,))
        return result is not None

    def questions_exist(self, session_id: int) -> bool:
        """Check if questions exist for a session."""
        query = "SELECT 1 FROM ResearchQuestions WHERE session_id = ?"
        result = self.db.fetch_one(query, (session_id,))
        return result is not None

    def delete_ideation_by_session(self, session_id: int) -> Dict[str, int]:
        """Delete all ideation data for a session."""
        questions_deleted = self.db.execute(
            "DELETE FROM ResearchQuestions WHERE session_id = ?",
            (session_id,)
        )
        gaps_deleted = self.db.execute(
            "DELETE FROM ResearchGaps WHERE session_id = ?",
            (session_id,)
        )
        return {
            'questions_deleted': questions_deleted,
            'gaps_deleted': gaps_deleted
        }

    def _parse_question_json(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Parse JSON fields in a question record."""
        if record.get('suggested_methods'):
            record['suggested_methods'] = self.from_json(record['suggested_methods'])
        if record.get('related_concepts'):
            record['related_concepts'] = self.from_json(record['related_concepts'])
        return record
