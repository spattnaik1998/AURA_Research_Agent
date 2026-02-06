"""
Citation Verification Service for AURA
Ensures all in-text citations match references exactly
"""

import logging
import re
from typing import Dict, Any, List, Set, Tuple
from dataclasses import dataclass

logger = logging.getLogger('aura.services')


@dataclass
class CitationVerificationResult:
    """Result of citation verification"""
    is_valid: bool
    total_citations: int
    total_references: int
    orphan_citations: List[str]  # Citations without matching references
    unused_references: List[str]  # References not cited in text
    citation_mismatches: List[Tuple[str, str]]  # (citation, reference) pairs that don't match
    success_rate: float


class CitationVerificationService:
    """Verifies citation accuracy and consistency"""

    # Citation format patterns
    CITATION_PATTERN = r'\(([^)]*et al\.|[^)]*),\s*(\d{4})\)'
    REFERENCE_SECTION_PATTERN = r'(?:^|\n)(References?|Bibliography|Citations?)\s*(?:\n|$)'

    def __init__(self):
        """Initialize citation verification service"""
        pass

    async def verify_citations(self, essay: str) -> CitationVerificationResult:
        """
        Verify all citations match references

        Args:
            essay: Generated essay with citations and references

        Returns:
            CitationVerificationResult with detailed analysis
        """
        logger.info("Starting citation verification...")

        # Extract in-text citations
        citations = self._extract_citations(essay)
        logger.debug(f"Extracted {len(citations)} in-text citations")

        # Extract references
        references = self._extract_references(essay)
        logger.debug(f"Extracted {len(references)} references")

        # Compare and identify mismatches
        orphan_citations = self._find_orphan_citations(citations, references)
        unused_references = self._find_unused_references(citations, references)
        mismatches = self._find_citation_mismatches(citations, references)

        # Calculate success rate
        total_issues = len(orphan_citations) + len(unused_references) + len(mismatches)
        success_rate = 1.0 if total_issues == 0 else max(0, 1.0 - (total_issues / max(len(citations), 1)))

        is_valid = (
            len(orphan_citations) == 0 and
            len(mismatches) == 0 and
            len(unused_references) == 0
        )

        logger.info(f"Citation verification complete. Valid: {is_valid}")
        if orphan_citations:
            logger.warning(f"Found {len(orphan_citations)} orphan citations")
        if unused_references:
            logger.warning(f"Found {len(unused_references)} unused references")
        if mismatches:
            logger.warning(f"Found {len(mismatches)} citation mismatches")

        return CitationVerificationResult(
            is_valid=is_valid,
            total_citations=len(citations),
            total_references=len(references),
            orphan_citations=orphan_citations,
            unused_references=unused_references,
            citation_mismatches=mismatches,
            success_rate=success_rate
        )

    def _extract_citations(self, essay: str) -> List[Dict[str, str]]:
        """
        Extract in-text citations in format (Author et al., Year) or (Author, Year)

        Args:
            essay: Essay text

        Returns:
            List of citation dictionaries with author and year
        """
        citations = []
        pattern = r'\(([^)]*?(?:et al\.)?[^)]*?),\s*(\d{4})\)'

        for match in re.finditer(pattern, essay):
            author_part = match.group(1).strip()
            year = match.group(2)

            # Normalize author part
            if "et al" in author_part:
                # Extract first author
                first_author = author_part.split("et al")[0].strip()
                author_part = f"{first_author} et al."
            else:
                # Keep as is, but clean up spaces
                author_part = " ".join(author_part.split())

            citation = {
                "author": author_part,
                "year": year,
                "full": f"({author_part}, {year})",
                "position": match.start()
            }

            citations.append(citation)

        return citations

    def _extract_references(self, essay: str) -> List[Dict[str, str]]:
        """
        Extract reference list from essay

        Args:
            essay: Essay text

        Returns:
            List of reference dictionaries
        """
        references = []

        # Find References section
        ref_section_match = re.search(
            self.REFERENCE_SECTION_PATTERN,
            essay,
            re.IGNORECASE | re.MULTILINE
        )

        if not ref_section_match:
            logger.warning("No References section found in essay")
            return references

        # Extract everything after References header
        ref_start = ref_section_match.end()
        ref_text = essay[ref_start:]

        # Split by line breaks and parse each reference
        ref_lines = ref_text.strip().split('\n')

        for line in ref_lines:
            if not line.strip():
                continue

            # Try to extract author and year from reference
            # Standard formats: "Author, A. (Year)..." or "Author et al. (Year)..."
            author_year_pattern = r'^([^(]*?)(?:\s*\(\s*(\d{4})\s*\))?'

            match = re.search(author_year_pattern, line)
            if match:
                author_part = match.group(1).strip()
                year = match.group(2) if match.group(2) else None

                # Clean author part
                # Remove "and" and standardize
                author_part = author_part.replace(" and ", " & ")

                if author_part and year:
                    reference = {
                        "author": author_part,
                        "year": year,
                        "full_text": line.strip(),
                        "normalized_author": self._normalize_author_name(author_part)
                    }
                    references.append(reference)

        logger.debug(f"Extracted {len(references)} references")
        return references

    def _normalize_author_name(self, author_str: str) -> str:
        """
        Normalize author name for comparison

        Args:
            author_str: Author name string

        Returns:
            Normalized author name
        """
        # Remove periods and extra spaces
        normalized = re.sub(r'[.\s]+', ' ', author_str).strip()

        # Handle "et al" variants
        normalized = re.sub(r'et\s+al\.?', 'et al', normalized, flags=re.IGNORECASE)

        return normalized.lower()

    def _find_orphan_citations(
        self,
        citations: List[Dict[str, str]],
        references: List[Dict[str, str]]
    ) -> List[str]:
        """
        Find citations that don't have matching references

        Args:
            citations: List of in-text citations
            references: List of references

        Returns:
            List of orphan citation strings
        """
        orphans = []

        for citation in citations:
            # Try to find matching reference
            found = False

            for reference in references:
                # Compare normalized author and year
                citation_author_norm = self._normalize_author_name(citation["author"])
                ref_author_norm = self._normalize_author_name(reference["author"])

                if (citation_author_norm == ref_author_norm and
                    citation["year"] == reference["year"]):
                    found = True
                    break

            if not found:
                orphans.append(citation["full"])

        return orphans

    def _find_unused_references(
        self,
        citations: List[Dict[str, str]],
        references: List[Dict[str, str]]
    ) -> List[str]:
        """
        Find references that aren't cited in the text

        Args:
            citations: List of in-text citations
            references: List of references

        Returns:
            List of unused reference texts
        """
        unused = []

        for reference in references:
            # Check if this reference is cited
            cited = False

            for citation in citations:
                citation_author_norm = self._normalize_author_name(citation["author"])
                ref_author_norm = self._normalize_author_name(reference["author"])

                if (citation_author_norm == ref_author_norm and
                    citation["year"] == reference["year"]):
                    cited = True
                    break

            if not cited:
                unused.append(reference["full_text"])

        return unused

    def _find_citation_mismatches(
        self,
        citations: List[Dict[str, str]],
        references: List[Dict[str, str]]
    ) -> List[Tuple[str, str]]:
        """
        Find citations where author/year don't match references exactly

        Args:
            citations: List of in-text citations
            references: List of references

        Returns:
            List of (citation, reference) mismatch tuples
        """
        mismatches = []

        for citation in citations:
            citation_author_norm = self._normalize_author_name(citation["author"])
            citation_year = citation["year"]

            for reference in references:
                ref_author_norm = self._normalize_author_name(reference["author"])
                ref_year = reference["year"]

                # Year must match exactly
                if citation_year != ref_year:
                    continue

                # Author normalization helps, but track mismatches
                if citation_author_norm != ref_author_norm:
                    # Check if it's a close match (e.g., different abbreviations)
                    if self._authors_similar(citation_author_norm, ref_author_norm):
                        mismatches.append((citation["full"], reference["full_text"]))
                        break

        return mismatches

    def _authors_similar(self, author1: str, author2: str) -> bool:
        """
        Check if two author strings are similar (for alias detection)

        Args:
            author1: First normalized author string
            author2: Second normalized author string

        Returns:
            True if similar, False otherwise
        """
        # Extract initials
        initials1 = ''.join(c for c in author1 if c.isupper())
        initials2 = ''.join(c for c in author2 if c.isupper())

        # Check if initials match (indicates same author, different format)
        if initials1 and initials2 and initials1 == initials2:
            return True

        # Check Levenshtein distance for typos
        from difflib import SequenceMatcher
        ratio = SequenceMatcher(None, author1, author2).ratio()
        return ratio > 0.85

    def get_verification_error_message(self, result: CitationVerificationResult) -> str:
        """
        Generate user-friendly error message for citation verification failure

        Args:
            result: CitationVerificationResult

        Returns:
            Formatted error message
        """
        message = (
            f"\n❌ Citation Verification Failed\n"
            f"{'='*50}\n\n"
            f"Total Citations: {result.total_citations}\n"
            f"Total References: {result.total_references}\n"
            f"Success Rate: {result.success_rate*100:.1f}%\n\n"
        )

        if result.orphan_citations:
            message += f"Orphan Citations ({len(result.orphan_citations)}):\n"
            for citation in result.orphan_citations[:5]:  # Show first 5
                message += f"  • {citation}\n"
            if len(result.orphan_citations) > 5:
                message += f"  ... and {len(result.orphan_citations) - 5} more\n"
            message += "\n"

        if result.unused_references:
            message += f"Unused References ({len(result.unused_references)}):\n"
            for reference in result.unused_references[:5]:  # Show first 5
                message += f"  • {reference[:80]}...\n"
            if len(result.unused_references) > 5:
                message += f"  ... and {len(result.unused_references) - 5} more\n"
            message += "\n"

        message += (
            "AURA requires 100% citation accuracy.\n"
            "The essay has been rejected and will be regenerated with corrections.\n"
            f"{'='*50}\n"
        )

        return message
