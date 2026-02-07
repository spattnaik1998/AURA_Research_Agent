"""
Source Sufficiency Service for AURA
Validates that essay sources meet minimum quality and quantity requirements
"""

import logging
from typing import Dict, Any, List, Set
from dataclasses import dataclass

logger = logging.getLogger('aura.services')


@dataclass
class SufficiencyResult:
    """Result of sufficiency check"""
    is_sufficient: bool
    papers_count: int
    validated_papers_count: int
    effective_count: float
    venue_count: int
    recent_papers_count: int
    issues: List[str]
    recommendations: List[str]


class SourceSufficiencyService:
    """Validates source sufficiency for essay generation"""

    # Minimum requirements
    MIN_VALID_PAPERS = 5
    MIN_UNIQUE_VENUES = 3
    MIN_RECENT_PAPERS = 2  # Within last 5 years
    MIN_EFFECTIVE_COUNT = 4.0  # Weighted sum

    # Validation level weights
    VALIDATION_LEVEL_WEIGHTS = {
        "full": 1.0,      # Full validation with CrossRef
        "doi": 0.9,       # DOI verified via CrossRef (increased from 0.8)
        "basic": 0.7      # Basic metadata only (increased from 0.5)
    }

    def __init__(self):
        """Initialize sufficiency service"""
        pass

    def check_sufficiency(
        self,
        papers: List[Dict[str, Any]],
        validation_results: List[Dict[str, Any]]
    ) -> SufficiencyResult:
        """
        Check if papers meet minimum sufficiency requirements

        Args:
            papers: Original list of papers from API
            validation_results: Results from paper validation service

        Returns:
            SufficiencyResult with detailed analysis
        """
        issues = []
        recommendations = []

        # Count valid papers
        valid_papers = [
            r for r in validation_results
            if r.get("is_valid", False)
        ]
        validated_count = len(valid_papers)

        logger.info(f"Checking sufficiency: {validated_count} valid papers out of {len(papers)}")

        # Check 1: Minimum paper count
        if validated_count < self.MIN_VALID_PAPERS:
            issues.append(f"Only {validated_count} validated papers (need {self.MIN_VALID_PAPERS})")
            recommendations.append("Try a more specific or broader search query")
            recommendations.append("Use different keywords or combine related concepts")

        # Check 2: Venue diversity
        venues = self._extract_venues(valid_papers)
        if len(venues) < self.MIN_UNIQUE_VENUES:
            issues.append(f"Only {len(venues)} unique venues (need {self.MIN_UNIQUE_VENUES})")
            recommendations.append("Search includes papers from limited publication venues")
            recommendations.append("Consider searching for related topics to diversify sources")

        # Check 3: Recency check
        recent_count = self._count_recent_papers(valid_papers)
        if recent_count < self.MIN_RECENT_PAPERS:
            issues.append(f"Only {recent_count} recent papers from last 5 years (need {self.MIN_RECENT_PAPERS})")
            recommendations.append("Include papers from recent research")

        # Check 4: Calculate effective count with validation weights
        effective_count = self._calculate_effective_count(valid_papers, validation_results)
        if effective_count < self.MIN_EFFECTIVE_COUNT:
            issues.append(f"Effective paper count {effective_count:.1f} (need {self.MIN_EFFECTIVE_COUNT})")
            recommendations.append("Papers lack sufficient validation or academic standing")

        is_sufficient = (
            validated_count >= self.MIN_VALID_PAPERS and
            len(venues) >= self.MIN_UNIQUE_VENUES and
            recent_count >= self.MIN_RECENT_PAPERS and
            effective_count >= self.MIN_EFFECTIVE_COUNT
        )

        logger.info(f"Sufficiency check: {'PASS' if is_sufficient else 'FAIL'}")
        if issues:
            for issue in issues:
                logger.warning(f"  - {issue}")

        return SufficiencyResult(
            is_sufficient=is_sufficient,
            papers_count=len(papers),
            validated_papers_count=validated_count,
            effective_count=effective_count,
            venue_count=len(venues),
            recent_papers_count=recent_count,
            issues=issues,
            recommendations=recommendations
        )

    def _extract_venues(self, valid_papers: List[Dict[str, Any]]) -> Set[str]:
        """
        Extract unique publication venues from papers

        Args:
            valid_papers: List of validated papers

        Returns:
            Set of unique venue names
        """
        venues = set()

        for paper in valid_papers:
            # Try publication info from Serper API
            pub_info = paper.get("publication_info", {})
            publication_name = pub_info.get("publication", "")

            if publication_name and publication_name.strip():
                # Normalize venue name (handle arXiv separately)
                venue = publication_name.strip()
                if venue.lower().startswith("arxiv"):
                    venue = "arXiv"
                venues.add(venue)
                continue

            # Try enriched metadata from validation
            enriched = paper.get("_enriched_metadata", {})
            if enriched:
                # Could extract from CrossRef/OpenAlex data
                # For now, use publication name if available
                pass

            # Fallback: extract from link domain
            link = paper.get("link", "")
            if link:
                try:
                    domain = link.split("/")[2]
                    # Normalize arXiv URLs
                    if "arxiv" in domain.lower():
                        venues.add("arXiv")
                    elif domain not in ["example.com", "unknown"]:
                        venues.add(domain)
                except (IndexError, ValueError):
                    pass

        logger.debug(f"Found {len(venues)} unique venues: {venues}")
        return venues

    def _count_recent_papers(self, valid_papers: List[Dict[str, Any]]) -> int:
        """
        Count papers from last 5 years

        Args:
            valid_papers: List of validated papers

        Returns:
            Number of recent papers
        """
        from datetime import datetime

        current_year = datetime.now().year
        min_year = current_year - 5
        recent_count = 0

        for paper in valid_papers:
            year = self._extract_year(paper)
            if year and year >= min_year:
                recent_count += 1

        logger.debug(f"Found {recent_count} papers from last 5 years")
        return recent_count

    def _extract_year(self, paper: Dict[str, Any]) -> int:
        """
        Extract publication year from paper

        Args:
            paper: Paper metadata

        Returns:
            Year as integer, or None if not found
        """
        # Try publication info first
        pub_info = paper.get("publication_info", {})
        year_str = pub_info.get("publicationDate", "")

        if year_str:
            try:
                return int(year_str.split("-")[0])
            except (ValueError, IndexError):
                pass

        # Try enriched metadata
        enriched = paper.get("_enriched_metadata", {})
        if "published_date" in enriched:
            published_date = enriched["published_date"]
            if isinstance(published_date, list) and len(published_date) > 0:
                try:
                    return int(published_date[0])
                except (ValueError, IndexError):
                    pass

        return None

    def _calculate_effective_count(
        self,
        valid_papers: List[Dict[str, Any]],
        validation_results: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate weighted effective paper count

        Weights papers by validation level and relevance:
        - Full validation: 1.0 weight
        - DOI validation: 0.8 weight
        - Basic validation: 0.5 weight

        Args:
            valid_papers: List of validated papers
            validation_results: Validation results

        Returns:
            Weighted effective count
        """
        effective_count = 0.0

        for paper in valid_papers:
            # Find corresponding validation result
            validation = None
            for result in validation_results:
                if result.get("paper") == paper:
                    validation = result
                    break

            if not validation:
                # Use basic weight if no validation found
                weight = self.VALIDATION_LEVEL_WEIGHTS["basic"]
            else:
                level = validation.get("validation_level", "basic")
                weight = self.VALIDATION_LEVEL_WEIGHTS.get(level, 0.5)

            # Boost weight for highly cited papers
            citation_count = paper.get("cited_by", {}).get("total", 0)
            citation_boost = 1.0
            if citation_count > 50:
                citation_boost = 1.2
            if citation_count > 500:
                citation_boost = 1.5

            effective_weight = weight * citation_boost
            effective_count += effective_weight

        logger.debug(f"Calculated effective paper count: {effective_count:.2f}")
        return effective_count

    def get_sufficiency_error_message(self, result: SufficiencyResult) -> str:
        """
        Generate user-friendly error message for insufficient sources

        Args:
            result: SufficiencyResult from check_sufficiency

        Returns:
            Formatted error message
        """
        message = (
            f"\n❌ Insufficient Academic Material\n"
            f"{'='*50}\n\n"
            f"Papers Found: {result.papers_count}\n"
            f"Papers Validated: {result.validated_papers_count} (need {self.MIN_VALID_PAPERS})\n"
            f"Unique Venues: {result.venue_count} (need {self.MIN_UNIQUE_VENUES})\n"
            f"Recent Papers (5y): {result.recent_papers_count} (need {self.MIN_RECENT_PAPERS})\n"
            f"Effective Score: {result.effective_count:.1f} (need {self.MIN_EFFECTIVE_COUNT})\n\n"
        )

        if result.issues:
            message += "Issues:\n"
            for issue in result.issues:
                message += f"  • {issue}\n"
            message += "\n"

        if result.recommendations:
            message += "Suggestions:\n"
            for rec in result.recommendations:
                message += f"  • {rec}\n"
            message += "\n"

        message += (
            "AURA maintains strict quality standards and requires sufficient\n"
            "validated academic sources before generating essays.\n"
            f"{'='*50}\n"
        )

        return message
