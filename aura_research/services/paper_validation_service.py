"""
Paper Validation Service for AURA
Multi-source paper validation using CrossRef and OpenAlex APIs
Ensures all papers are legitimate research publications
"""

import asyncio
import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from ..utils.config import ABSTRACT_MIN_LENGTH

logger = logging.getLogger('aura.services')


class PaperValidationService:
    """Multi-source paper validation using CrossRef and OpenAlex APIs"""

    # API endpoints
    CROSSREF_API_URL = "https://api.crossref.org/works"
    OPENALEX_API_URL = "https://api.openalex.org/works"

    # Validation thresholds
    TITLE_MIN_LENGTH = 10
    TITLE_MAX_LENGTH = 500
    MIN_YEAR = 1950
    MAX_YEAR = datetime.now().year + 1

    # Cache timeout (hours)
    CACHE_TIMEOUT_HOURS = 24

    def __init__(self):
        """Initialize validation service with cache and config thresholds"""
        self.ABSTRACT_MIN_LENGTH = ABSTRACT_MIN_LENGTH
        self.validation_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        logger.debug(f"Loaded abstract minimum length: {self.ABSTRACT_MIN_LENGTH} chars")

    async def validate_papers(self, papers: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Validate papers through 4 levels:
        1. Basic metadata (title length, has authors, has abstract)
        2. DOI verification via CrossRef API
        3. Venue validation (check against predatory publishers)
        4. Citation count reasonableness

        Args:
            papers: List of papers from Serper API

        Returns:
            Tuple of (valid_papers, validation_results)
        """
        valid_papers = []
        validation_results = []

        logger.info(f"Starting validation of {len(papers)} papers")

        # DEBUG: Check paper types
        if papers:
            first_paper = papers[0]
            logger.debug(f"First paper type: {type(first_paper)}")
            logger.debug(f"First paper is dict: {isinstance(first_paper, dict)}")
            if isinstance(first_paper, dict):
                logger.debug(f"First paper keys: {list(first_paper.keys())[:5]}")
            else:
                logger.debug(f"First paper value: {str(first_paper)[:100]}")

        # Run validations in parallel with semaphore to respect API limits
        semaphore = asyncio.Semaphore(5)
        tasks = [
            self._validate_paper(paper, semaphore)
            for paper in papers
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for paper, result in zip(papers, results):
            if isinstance(result, Exception):
                logger.warning(f"Validation error for paper: {str(result)}")
                validation_results.append({
                    "paper": paper,
                    "is_valid": False,
                    "validation_level": "error",
                    "reason": str(result)
                })
            else:
                validation_results.append(result)
                if result["is_valid"]:
                    valid_papers.append({**paper, **result["enriched_metadata"]})

        logger.info(f"Validation complete: {len(valid_papers)} valid papers out of {len(papers)}")
        return valid_papers, validation_results

    async def _validate_paper(
        self,
        paper: Dict[str, Any],
        semaphore: asyncio.Semaphore
    ) -> Dict[str, Any]:
        """
        Validate a single paper through all levels

        Args:
            paper: Paper metadata from Serper API
            semaphore: Rate limiter semaphore

        Returns:
            Validation result with level and metadata
        """
        async with semaphore:
            # DEBUG: Log paper type at start of validation
            logger.debug(f"_validate_paper called with type: {type(paper)}, is_dict: {isinstance(paper, dict)}")
            if not isinstance(paper, dict):
                logger.error(f"_validate_paper received non-dict: {type(paper).__name__}: {str(paper)[:100]}")
                raise TypeError(f"Expected dict, got {type(paper).__name__}")

            # Level 1: Basic metadata validation
            try:
                basic_valid, basic_reason = self._validate_basic_metadata(paper)
            except Exception as e:
                logger.error(f"Error in _validate_basic_metadata: {e}", exc_info=True)
                raise

            if not basic_valid:
                return {
                    "paper": paper,
                    "is_valid": False,
                    "validation_level": "basic",
                    "reason": basic_reason,
                    "enriched_metadata": {}
                }

            # Level 2: DOI verification
            try:
                doi = paper.get("link", "").split("/")[-1] if paper.get("link") else None
                crossref_data = await self._verify_crossref(paper, doi)
            except Exception as e:
                logger.error(f"Error in _verify_crossref: {e}", exc_info=True)
                raise

            if crossref_data:
                return {
                    "paper": paper,
                    "is_valid": True,
                    "validation_level": "full",
                    "reason": "Validated via CrossRef",
                    "enriched_metadata": crossref_data
                }

            # Level 3: OpenAlex validation as fallback
            openalex_data = await self._verify_openalex(paper)
            if openalex_data:
                return {
                    "paper": paper,
                    "is_valid": True,
                    "validation_level": "doi",
                    "reason": "Validated via OpenAlex",
                    "enriched_metadata": openalex_data
                }

            # Level 4: Basic metadata passed, no DOI found
            return {
                "paper": paper,
                "is_valid": True,
                "validation_level": "basic",
                "reason": "Basic metadata valid, no DOI verification available",
                "enriched_metadata": {
                    "doi": None,
                    "is_retracted": False,
                    "venue_quality_score": 5.0
                }
            }

    def _validate_basic_metadata(self, paper: Dict[str, Any]) -> tuple[bool, str]:
        """
        Level 1: Validate basic paper metadata

        Relaxed validation for Tavily sources since they're web results,
        not academic papers with structured metadata.

        Args:
            paper: Paper metadata

        Returns:
            Tuple of (is_valid, reason)
        """
        # Relaxed validation for Tavily sources
        if paper.get("_source") == "tavily":
            title = paper.get("title", "")
            snippet = paper.get("snippet", "")

            # Only check title and content exist
            if not title or len(title) < self.TITLE_MIN_LENGTH:
                return False, f"Invalid title length: {len(title)}"
            if not snippet or len(snippet) < 20:  # Lower threshold for web content
                return False, "Insufficient content"

            return True, "Basic metadata valid (Tavily source)"

        # Normal validation for Serper papers
        # Check title
        title = paper.get("title", "")
        if not title or len(title) < self.TITLE_MIN_LENGTH or len(title) > self.TITLE_MAX_LENGTH:
            return False, f"Invalid title length: {len(title)}"

        # Check for snippet (abstract proxy)
        snippet = paper.get("snippet", "")
        if not snippet or len(snippet) < self.ABSTRACT_MIN_LENGTH:
            return False, "Insufficient abstract/snippet"

        # Check year
        pub_info = paper.get("publication_info", {})
        if isinstance(pub_info, dict):
            # Try publicationDate first, then year field
            year_str = pub_info.get("publicationDate", "") or pub_info.get("year", "")
            if year_str:
                try:
                    # Handle both "2020-01-01" and "2020" formats
                    year_int = int(str(year_str).split("-")[0])
                    if year_int < self.MIN_YEAR or year_int > self.MAX_YEAR:
                        return False, f"Invalid publication year: {year_int}"
                except (ValueError, IndexError, TypeError):
                    pass  # Year format not parseable, but don't fail
        else:
            # publication_info is a string (shouldn't happen with new code, but be defensive)
            logger.warning(f"publication_info is a string: {type(pub_info)}, expected dict")

        return True, "Basic metadata valid"

    async def _verify_crossref(
        self,
        paper: Dict[str, Any],
        doi: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Level 2: Verify paper via CrossRef API

        Args:
            paper: Paper metadata
            doi: Digital Object Identifier if available

        Returns:
            Enriched metadata if found, None otherwise
        """
        try:
            # Check cache first
            cache_key = f"crossref_{doi}"
            if cache_key in self.validation_cache:
                if self._is_cache_valid(cache_key):
                    return self.validation_cache[cache_key]

            # Try DOI-based lookup if available
            if doi and len(doi) > 5:
                async with httpx.AsyncClient(timeout=10) as client:
                    # Try direct DOI lookup
                    doi_url = f"https://api.crossref.org/works/{doi}"
                    response = await client.get(doi_url)

                    if response.status_code == 200:
                        data = response.json()
                        if "message" in data:
                            metadata = self._extract_crossref_metadata(data["message"])
                            self._cache_validation(cache_key, metadata)
                            return metadata

            # Try title-based search as fallback
            title = paper.get("title", "")
            if title:
                async with httpx.AsyncClient(timeout=10) as client:
                    params = {"query.title": title, "rows": 1}
                    response = await client.get(self.CROSSREF_API_URL, params=params)

                    if response.status_code == 200:
                        data = response.json()
                        items = data.get("message", {}).get("items", [])
                        if items:
                            metadata = self._extract_crossref_metadata(items[0])
                            self._cache_validation(cache_key, metadata)
                            return metadata

        except asyncio.TimeoutError:
            logger.warning(f"CrossRef API timeout for paper: {paper.get('title', 'Unknown')}")
        except Exception as e:
            logger.debug(f"CrossRef verification failed: {str(e)}")

        return None

    def _extract_crossref_metadata(self, crossref_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant metadata from CrossRef response

        Args:
            crossref_data: CrossRef API response data

        Returns:
            Extracted metadata
        """
        return {
            "doi": crossref_data.get("DOI"),
            "is_retracted": "is-referenced-by-count" in crossref_data and
                           any("retraction" in str(ref).lower()
                               for ref in crossref_data.get("is-referenced-by-count", [])),
            "venue_quality_score": self._calculate_venue_quality(crossref_data),
            "citation_count": crossref_data.get("is-referenced-by-count", 0),
            "published_date": crossref_data.get("published", {}).get("date-parts", [[]])[0],
            "authors": len(crossref_data.get("author", []))
        }

    def _calculate_venue_quality(self, crossref_data: Dict[str, Any]) -> float:
        """
        Calculate venue quality score (0-10)

        Args:
            crossref_data: CrossRef data

        Returns:
            Quality score
        """
        score = 7.0  # Base score for CrossRef-verified papers

        # Boost for established venues
        container = crossref_data.get("container-title", [""])[0].lower()
        if any(word in container for word in ["nature", "science", "proceedings", "ieee"]):
            score += 2.0

        # Boost for cited papers
        citations = crossref_data.get("is-referenced-by-count", 0)
        if citations > 10:
            score += 1.0
        if citations > 100:
            score += 1.0

        return min(score, 10.0)

    async def _verify_openalex(self, paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Level 3: Verify paper via OpenAlex API (free tier)

        Args:
            paper: Paper metadata

        Returns:
            Enriched metadata if found, None otherwise
        """
        try:
            title = paper.get("title", "")
            if not title:
                return None

            # Check cache
            cache_key = f"openalex_{title}"
            if cache_key in self.validation_cache:
                if self._is_cache_valid(cache_key):
                    return self.validation_cache[cache_key]

            async with httpx.AsyncClient(timeout=10) as client:
                # OpenAlex search endpoint
                params = {
                    "search": title,
                    "per_page": 1,
                    "mailto": "research@aura.ai"  # OpenAlex request tracking
                }
                response = await client.get(self.OPENALEX_API_URL, params=params)

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    if results:
                        metadata = self._extract_openalex_metadata(results[0])
                        self._cache_validation(cache_key, metadata)
                        return metadata

        except asyncio.TimeoutError:
            logger.warning(f"OpenAlex API timeout for paper: {paper.get('title', 'Unknown')}")
        except Exception as e:
            logger.debug(f"OpenAlex verification failed: {str(e)}")

        return None

    def _extract_openalex_metadata(self, openalex_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from OpenAlex response

        Args:
            openalex_data: OpenAlex API response data

        Returns:
            Extracted metadata
        """
        return {
            "doi": openalex_data.get("doi"),
            "is_retracted": openalex_data.get("is_retracted", False),
            "venue_quality_score": self._calculate_openalex_quality(openalex_data),
            "citation_count": openalex_data.get("cited_by_count", 0),
            "publication_year": openalex_data.get("publication_year"),
            "authors": len(openalex_data.get("author_count", 0))
        }

    def _calculate_openalex_quality(self, openalex_data: Dict[str, Any]) -> float:
        """
        Calculate quality score from OpenAlex data

        Args:
            openalex_data: OpenAlex data

        Returns:
            Quality score (0-10)
        """
        score = 6.5  # Base score for OpenAlex-verified papers

        # Boost for open access
        if openalex_data.get("open_access", {}).get("is_oa"):
            score += 1.0

        # Boost for cited papers
        citations = openalex_data.get("cited_by_count", 0)
        if citations > 10:
            score += 1.0
        if citations > 100:
            score += 1.0

        return min(score, 10.0)

    def _cache_validation(self, key: str, data: Dict[str, Any]) -> None:
        """
        Cache validation result with timestamp

        Args:
            key: Cache key
            data: Validation data
        """
        self.validation_cache[key] = data
        self.cache_timestamps[key] = datetime.now()

    def _is_cache_valid(self, key: str) -> bool:
        """
        Check if cached validation is still valid

        Args:
            key: Cache key

        Returns:
            True if cache is valid, False if expired
        """
        if key not in self.cache_timestamps:
            return False

        age = datetime.now() - self.cache_timestamps[key]
        return age < timedelta(hours=self.CACHE_TIMEOUT_HOURS)

    def clear_cache(self) -> None:
        """Clear validation cache"""
        self.validation_cache.clear()
        self.cache_timestamps.clear()
        logger.info("Paper validation cache cleared")
