"""
Quality Scoring Service for AURA
Automated essay quality assessment with rejection threshold
"""

import logging
import re
from typing import Dict, Any, List
import spacy
from ..utils.config import (
    MIN_QUALITY_SCORE,
    FLAG_QUALITY_SCORE,
    EXCELLENT_QUALITY_SCORE,
    CITATION_DENSITY_TARGET,
    QUALITY_ISSUE_THRESHOLD,
    CITATION_DENSITY_TOLERANCE
)

logger = logging.getLogger('aura.services')


class QualityScoringService:
    """Automated quality assessment for academic essays"""

    # Quality thresholds (imported from config for centralization)
    REJECTION_THRESHOLD = MIN_QUALITY_SCORE
    FLAG_THRESHOLD = FLAG_QUALITY_SCORE
    EXCELLENT_THRESHOLD = EXCELLENT_QUALITY_SCORE

    # Citation metrics (imported from config for centralization)
    CITATION_DENSITY_TARGET = CITATION_DENSITY_TARGET
    CITATION_DENSITY_TOLERANCE = CITATION_DENSITY_TOLERANCE

    # Dimension weights
    DIMENSION_WEIGHTS = {
        "citation_density": 0.20,
        "source_diversity": 0.15,
        "academic_language": 0.15,
        "structural_coherence": 0.15,
        "evidence_based_claims": 0.20,
        "citation_accuracy": 0.15
    }

    def __init__(self):
        """Initialize quality scoring service with NLP model"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("SpaCy model loaded successfully")
        except OSError:
            logger.warning("SpaCy model not found. Installing...")
            import os
            os.system("python -m spacy download en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")

    async def score_essay(
        self,
        essay: str,
        analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Score essay quality across 6 dimensions

        Args:
            essay: Generated essay text
            analyses: Paper analyses used in essay generation

        Returns:
            Quality score and detailed metrics
        """
        logger.info("Starting essay quality assessment...")

        # Extract components
        citation_count = len(self._extract_citations(essay))
        word_count = len(essay.split())

        # Score each dimension
        scores = {
            "citation_density": self._score_citation_density(
                citation_count, word_count
            ),
            "source_diversity": self._score_source_diversity(
                self._extract_citations(essay), analyses
            ),
            "academic_language": self._score_academic_language(essay),
            "structural_coherence": self._score_structural_coherence(essay),
            "evidence_based_claims": self._score_evidence_based_claims(essay),
            "citation_accuracy": self._score_citation_accuracy(essay)
        }

        # Calculate overall score
        overall_score = self._calculate_overall_score(scores)

        logger.info(f"Essay quality assessment complete. Overall score: {overall_score:.1f}/10.0")

        return {
            "overall_score": overall_score,
            "scores": scores,
            "citation_count": citation_count,
            "word_count": word_count,
            "assessment": self._get_assessment_level(overall_score),
            "issues": self._identify_quality_issues(scores)
        }

    def _extract_citations(self, text: str) -> List[str]:
        """
        Extract in-text citations in format (Author et al., Year) or (Author, Year)

        Args:
            text: Essay text

        Returns:
            List of extracted citations
        """
        # Pattern: (Author(s), Year) or (Author et al., Year)
        pattern = r'\(([^)]*et al\.|[^)]*),\s*(\d{4})\)'
        matches = re.findall(pattern, text)
        citations = [f"({author}, {year})" for author, year in matches]
        return citations

    def _score_citation_density(self, citation_count: int, word_count: int) -> float:
        """
        Score citation density (citations per word)

        Target: 1 citation per 175 words (~0.0057)

        Args:
            citation_count: Number of citations
            word_count: Total words in essay

        Returns:
            Score 0-10
        """
        if word_count == 0:
            return 0.0

        actual_density = citation_count / word_count
        target_density = self.CITATION_DENSITY_TARGET

        # Perfect score if within tolerance
        if abs(actual_density - target_density) < self.CITATION_DENSITY_TOLERANCE:
            return 10.0

        # Score decreases for deviation from target
        deviation_ratio = abs(actual_density - target_density) / target_density
        score = max(0, 10.0 - (deviation_ratio * 50))

        return min(score, 10.0)

    def _score_source_diversity(
        self,
        citations: List[str],
        analyses: List[Dict[str, Any]]
    ) -> float:
        """
        Score diversity of sources cited

        Args:
            citations: List of extracted citations
            analyses: Available paper analyses

        Returns:
            Score 0-10
        """
        if not citations:
            return 0.0

        # Extract unique authors from citations
        unique_authors = set()
        for citation in citations:
            # Extract author name before comma
            match = re.search(r'\(([^,]+)', citation)
            if match:
                author = match.group(1).strip()
                unique_authors.add(author)

        # Extract unique venues from analyses
        unique_venues = set()
        for analysis in analyses:
            metadata = analysis.get("metadata", {})
            venue = metadata.get("venue", "Unknown")
            if venue and venue != "Unknown":
                unique_venues.add(venue)

        # Diversity score based on unique sources
        diversity_ratio = len(unique_authors) / len(citations) if citations else 0
        venue_ratio = len(unique_venues) / len(analyses) if analyses else 0

        score = (diversity_ratio + venue_ratio) / 2 * 10
        return min(score, 10.0)

    def _score_academic_language(self, essay: str) -> float:
        """
        Score academic tone and language quality

        Looks for:
        - Hedging language: suggests, may, appears, indicates, etc.
        - Passive voice usage
        - Proper terminology
        - Absence of absolute statements without citations

        Args:
            essay: Essay text

        Returns:
            Score 0-10
        """
        # Process with spaCy
        doc = self.nlp(essay)

        # Count hedging language
        hedging_words = {
            "suggests", "may", "appears", "indicates", "implies",
            "could", "might", "seems", "potentially", "arguably",
            "arguably", "arguably"
        }
        hedging_count = sum(
            1 for token in doc if token.text.lower() in hedging_words
        )

        # Count passive voice constructions
        passive_count = sum(
            1 for token in doc
            if token.dep_ in ["auxpass", "aux"] and token.head.pos_ == "VERB"
        )

        # Count absolute statements (high confidence issues)
        absolute_phrases = ["is definitely", "is certainly", "is clearly", "is obviously"]
        absolute_count = sum(
            1 for phrase in absolute_phrases
            if phrase in essay.lower()
        )

        # Sentence count for averaging
        sentence_count = len(list(doc.sents))

        # Calculate scores
        hedging_score = min((hedging_count / max(sentence_count, 1)) * 2, 10)
        passive_score = min((passive_count / max(sentence_count, 1)) * 2, 10)
        absolute_penalty = min(absolute_count * 2, 10)

        # Combine: good hedging and passive, low absolutes
        score = ((hedging_score * 0.4) + (passive_score * 0.3) + (10 - absolute_penalty * 0.3))
        return max(0, min(score, 10.0))

    def _score_structural_coherence(self, essay: str) -> float:
        """
        Score structural coherence and logical flow

        Checks for:
        - Proper intro-body-conclusion structure
        - Paragraph organization
        - Transition words

        Args:
            essay: Essay text

        Returns:
            Score 0-10
        """
        lines = essay.strip().split('\n')

        # Check for major sections
        section_markers = {
            "introduction": 0,
            "literature review": 0,
            "discussion": 0,
            "conclusion": 0,
            "analysis": 0
        }

        intro_found = False
        conclusion_found = False

        for line in lines:
            line_lower = line.lower()
            if "introduction" in line_lower:
                intro_found = True
            if "conclusion" in line_lower:
                conclusion_found = True

        # Check for transition words
        transition_words = {
            "furthermore", "however", "therefore", "thus", "moreover",
            "additionally", "in addition", "in contrast", "consequently",
            "subsequently", "meanwhile", "although", "whereas", "while"
        }

        transition_count = sum(
            1 for word in transition_words
            if word in essay.lower()
        )

        # Calculate score
        section_score = (intro_found + conclusion_found) * 3  # Up to 6 points
        transition_score = min(transition_count / 2, 4)  # Up to 4 points

        score = section_score + transition_score
        return min(score, 10.0)

    def _score_evidence_based_claims(self, essay: str) -> float:
        """
        Score how well claims are supported by citations

        Requirement: Major claims should have citations within 2 sentences

        Args:
            essay: Essay text

        Returns:
            Score 0-10
        """
        doc = self.nlp(essay)
        sentences = list(doc.sents)

        supported_sentences = 0
        total_significant_sentences = 0

        for i, sent in enumerate(sentences):
            text = sent.text

            # Skip short sentences (likely not main claims)
            if len(text.split()) < 10:
                continue

            total_significant_sentences += 1

            # Check for citations in this sentence or next 2
            citation_found = False
            for j in range(i, min(i + 3, len(sentences))):
                if self._extract_citations(sentences[j].text):
                    citation_found = True
                    break

            if citation_found:
                supported_sentences += 1

        if total_significant_sentences == 0:
            return 5.0  # Neutral score if no major claims detected

        support_ratio = supported_sentences / total_significant_sentences
        score = support_ratio * 10

        return min(score, 10.0)

    def _score_citation_accuracy(self, essay: str) -> float:
        """
        Score citation format accuracy and consistency

        Checks for:
        - Proper parenthetical citation format
        - Consistent formatting
        - No orphan citations

        Args:
            essay: Essay text

        Returns:
            Score 0-10
        """
        # Extract all citations
        citations = self._extract_citations(essay)

        if not citations:
            return 5.0  # Can't assess accuracy with no citations

        # Check format consistency
        format_pattern = r'\([^)]+,\s*\d{4}\)'
        properly_formatted = len(re.findall(format_pattern, essay))

        format_ratio = properly_formatted / len(citations) if citations else 0

        # Check for obvious format errors
        error_patterns = [
            r'\([^)]*,\s*[^\d][^\)]*\)',  # Non-year after comma
            r'\(\s*[^\)]*\s*\)',            # Empty parentheses
        ]

        error_count = sum(len(re.findall(pattern, essay)) for pattern in error_patterns)

        # Calculate score
        score = (format_ratio * 8) + (10 - min(error_count, 10))
        return min(max(score, 0), 10.0) / 2  # Average the two components

    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """
        Calculate overall score as weighted average

        Args:
            scores: Dictionary of dimension scores

        Returns:
            Overall score 0-10
        """
        overall = sum(
            scores.get(dimension, 0) * weight
            for dimension, weight in self.DIMENSION_WEIGHTS.items()
        )
        return overall

    def _get_assessment_level(self, score: float) -> str:
        """
        Get assessment level based on score

        Args:
            score: Overall quality score

        Returns:
            Assessment level string
        """
        if score >= self.EXCELLENT_THRESHOLD:
            return "excellent"
        elif score >= self.FLAG_THRESHOLD:
            return "good"
        elif score >= self.REJECTION_THRESHOLD:
            return "acceptable_with_review"
        else:
            return "rejected"

    def _identify_quality_issues(self, scores: Dict[str, float]) -> List[str]:
        """
        Identify quality issues from scores

        Args:
            scores: Dimension scores

        Returns:
            List of identified issues
        """
        issues = []
        issue_threshold = QUALITY_ISSUE_THRESHOLD  # Imported from config for centralization

        dimension_descriptions = {
            "citation_density": "Citation density too low or too high",
            "source_diversity": "Limited diversity in cited sources",
            "academic_language": "Academic tone needs improvement",
            "structural_coherence": "Essay structure could be improved",
            "evidence_based_claims": "Some claims lack sufficient citations",
            "citation_accuracy": "Citation format inconsistencies detected"
        }

        for dimension, score in scores.items():
            if score < issue_threshold:
                issues.append(dimension_descriptions.get(dimension, dimension))

        return issues
