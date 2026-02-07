"""
Topic Classification Service for AURA - WEAK GUARDRAILS VERSION
Pre-screens queries to filter ONLY OBVIOUS non-academic topics
Implements Layer 0 of the quality control system

Philosophy:
- REJECT only obvious garbage (celebrities, entertainment, recipes, product reviews)
- ACCEPT everything else (all STEM topics, science concepts, research methods)
- Let the paper validation layer (Layers 1-2) do the real filtering
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger('aura.services')


@dataclass
class ClassificationResult:
    """Result of topic classification"""
    is_academic: bool
    confidence: float
    category: str
    reasoning: str


class TopicClassificationService:
    """
    Weak guardrails for filtering only OBVIOUS non-academic topics.

    Goal: Reject celebrity bios, entertainment, recipes, product reviews.
    Everything else goes through (even edge cases) to paper validation.
    """

    # RED FLAGS: Clear indicators of non-academic content
    # Only reject if query contains these
    RED_FLAG_CELEBRITIES = {
        "actor", "actress", "celebrity", "singer", "musician", "politician",
        "filmmaker", "director", "producer", "scriptwriter", "comedian",
        "cruise", "asimov", "streep", "hanks", "jolie", "schwarzenegger",
        "gosling", "portman", "dicaprio", "leto", "depp", "pitt"
    }

    RED_FLAG_ENTERTAINMENT = {
        "filmography", "movie", "film", "netflix", "streaming", "cinema",
        "hollywood", "box office", "oscars", "emmy", "grammy",
        "album", "song", "music video", "concert", "tour", "discography"
    }

    RED_FLAG_LIFESTYLE = {
        "recipe", "cooking", "restaurant", "food", "diet", "meal",
        "fashion", "style", "skincare", "makeup", "beauty", "cosmetics",
        "workout", "gym", "fitness", "yoga", "pilates"
    }

    RED_FLAG_PRODUCTS = {
        "iphone", "samsung", "android", "tesla", "laptop", "computer",
        "gadget", "review", "best phones", "top gadgets", "product review"
    }

    RED_FLAG_BUSINESS = {
        "stock price", "market cap", "quarterly earnings", "trading",
        "dividend", "financial results", "earnings report"
    }

    RED_FLAG_NEWS = {
        "breaking news", "today", "latest news", "scandal", "gossip",
        "political scandal", "election results", "ballot"
    }

    RED_FLAG_BIOGRAPHY = {
        "biography", "life story", "personal life", "family history",
        "childhood", "born", "grew up", "high school", "hometown"
    }

    # Combine all red flags for fast lookup
    ALL_RED_FLAGS = (
        RED_FLAG_CELEBRITIES | RED_FLAG_ENTERTAINMENT | RED_FLAG_LIFESTYLE |
        RED_FLAG_PRODUCTS | RED_FLAG_BUSINESS | RED_FLAG_NEWS |
        RED_FLAG_BIOGRAPHY
    )

    def __init__(self):
        """Initialize classification service"""
        pass

    async def classify_query(self, query: str) -> ClassificationResult:
        """
        Classify a query using WEAK GUARDRAILS.

        Only rejects OBVIOUS non-academic topics.
        Accepts everything else to let paper validation be the real filter.

        Args:
            query: The research query to classify

        Returns:
            ClassificationResult with is_academic, confidence, category, reasoning
        """
        return self._classify_with_red_flags(query)

    def _classify_with_red_flags(self, query: str) -> ClassificationResult:
        """
        Simple red-flag detection: reject only obvious non-academic content.

        Strategy:
        1. Check if query contains obvious non-academic red flags
        2. If yes, reject with high confidence
        3. If no, accept (even edge cases go to paper validation)

        Args:
            query: The research query

        Returns:
            ClassificationResult based on red flag matching
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Count red flag matches
        red_flag_matches = len(query_words & self.ALL_RED_FLAGS)

        # Also check for red flag phrases (multi-word patterns)
        red_flag_phrases = [
            "best", "top 10", "review", "how to make", "how to cook",
            "biography of", "life of", "filmography", "discography"
        ]
        phrase_matches = sum(1 for phrase in red_flag_phrases if phrase in query_lower)

        total_red_flags = red_flag_matches + phrase_matches

        # WEAK GUARDRAILS: Only reject if clear non-academic indicators
        if total_red_flags >= 1:
            # Clear non-academic signals detected
            category = self._categorize_red_flags(query_lower)
            confidence = min(0.95, 0.7 + (total_red_flags * 0.1))

            logger.info(
                f"Classification: REJECTED (non-academic)"
                f" | Query: '{query}' | Red flags: {total_red_flags} | Category: {category}"
            )

            return ClassificationResult(
                is_academic=False,
                confidence=confidence,
                category=category,
                reasoning=f"Detected {total_red_flags} non-academic indicator(s): {category}"
            )
        else:
            # No clear non-academic indicators
            # Accept for paper validation to filter
            logger.info(
                f"Classification: ACCEPTED (no red flags)"
                f" | Query: '{query}' | Will validate papers"
            )

            return ClassificationResult(
                is_academic=True,
                confidence=0.95,  # High confidence we should at least TRY
                category="unknown_topic",
                reasoning="No clear non-academic indicators. Proceeding to paper validation."
            )

    def _categorize_red_flags(self, query_lower: str) -> str:
        """Categorize which type of non-academic content was detected"""
        if any(word in query_lower for word in self.RED_FLAG_CELEBRITIES):
            return "celebrity"
        elif any(word in query_lower for word in self.RED_FLAG_ENTERTAINMENT):
            return "entertainment"
        elif any(word in query_lower for word in self.RED_FLAG_LIFESTYLE):
            return "lifestyle"
        elif any(word in query_lower for word in self.RED_FLAG_PRODUCTS):
            return "product_review"
        elif any(word in query_lower for word in self.RED_FLAG_BUSINESS):
            return "business_news"
        elif any(word in query_lower for word in self.RED_FLAG_NEWS):
            return "news"
        elif any(word in query_lower for word in self.RED_FLAG_BIOGRAPHY):
            return "biography"
        else:
            return "other_non_academic"
