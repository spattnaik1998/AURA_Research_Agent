"""
Topic Classification Service for AURA
Pre-screens queries to filter non-academic topics before expensive API calls
Implements Layer 0 of the quality control system
"""

import logging
from typing import Dict, Any
from dataclasses import dataclass
from openai import OpenAI
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger('aura.services')


@dataclass
class ClassificationResult:
    """Result of topic classification"""
    is_academic: bool
    confidence: float
    category: str
    reasoning: str


class TopicClassificationService:
    """Pre-screen queries to filter non-academic topics"""

    ACADEMIC_KEYWORDS = {
        "learning", "research", "study", "theory", "analysis", "method",
        "algorithm", "system", "model", "process", "mechanism", "framework",
        "cell", "protein", "gene", "molecule", "neural", "network",
        "statistical", "mathematical", "computational", "empirical",
        "experiment", "evaluation", "hypothesis", "analysis", "optimization"
    }

    NON_ACADEMIC_KEYWORDS = {
        "actor", "actress", "celebrity", "author", "singer", "politician", "musician",
        "filmography", "biography", "movie", "film", "book", "novel", "album",
        "company", "brand", "product", "stock", "price", "review", "best", "top",
        "restaurant", "recipe", "lifestyle", "entertainment", "gossip", "scandal",
        "features", "cruise", "asimov", "pizza", "iphone", "tesla", "netflix"
    }

    def __init__(self):
        """Initialize classification service"""
        self.client = OpenAI()
        self.model = "gpt-4o"
        self.confidence_threshold = 0.6
        self.executor = ThreadPoolExecutor(max_workers=2)

    async def classify_query(self, query: str) -> ClassificationResult:
        """
        Classify a query as academic or non-academic.

        Args:
            query: The research query to classify

        Returns:
            ClassificationResult with is_academic, confidence, category, and reasoning
        """
        try:
            # Try LLM classification first
            result = await self._classify_with_llm(query)
            logger.info(
                f"LLM Classification: is_academic={result.is_academic}, "
                f"confidence={result.confidence:.2f}, category={result.category}"
            )
            return result
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}. Falling back to keyword heuristics.")
            # Fall back to keyword heuristics
            return self._classify_with_keywords(query)

    async def _classify_with_llm(self, query: str) -> ClassificationResult:
        """
        Classify query using GPT-4o with temperature=0.0 for consistency.

        Args:
            query: The research query

        Returns:
            ClassificationResult from LLM
        """
        prompt = f"""Classify the following query as either ACADEMIC or NON-ACADEMIC research.

Query: "{query}"

Respond in valid JSON format with these fields:
- is_academic (boolean): true if this is an academic/research topic, false otherwise
- confidence (number): 0.0 to 1.0, how certain you are
- category (string): e.g. "scientific_concept", "research_methodology", "biology", "mathematics", "celebrity", "entertainment", "person_biography", "product_review"
- reasoning (string): 1-2 sentences explaining the classification

ACADEMIC topics include:
- Scientific concepts (quantum entanglement, thermodynamics, photosynthesis)
- Research methodologies (reinforcement learning, CRISPR, machine learning)
- Biological/Medical topics (mitochondrial function, DNA replication, immunology)
- Engineering topics (neural networks, algorithms, systems design)
- Mathematical/Statistical concepts
- Any peer-reviewed research area

NON-ACADEMIC topics include:
- People (celebrities, politicians, authors as biographical subjects)
- Entertainment (movies, books, music as entertainment products)
- Products/Companies (reviews, stock prices, business news)
- Lifestyle/Entertainment (recipes, restaurants, travel guides)
- Current events/news (unless research-focused)

Example academic queries:
✓ "Transformer architecture in natural language processing"
✓ "CRISPR off-target effects in gene editing"
✓ "Attention mechanisms in neural networks"
✓ "Mitochondrial dysfunction in aging"

Example non-academic queries:
✗ "Tom Cruise filmography"
✗ "Isaac Asimov biography"
✗ "Best pizza in New York"
✗ "iPhone 15 features"

Return ONLY valid JSON, no other text."""

        # Run synchronous OpenAI call in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            self.executor,
            lambda: self.client.chat.completions.create(
                model=self.model,
                max_tokens=300,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}]
            )
        )

        response_text = response.choices[0].message.content
        logger.debug(f"LLM response: {response_text}")

        try:
            data = json.loads(response_text)
            return ClassificationResult(
                is_academic=data.get("is_academic", True),
                confidence=float(data.get("confidence", 0.5)),
                category=data.get("category", "unknown"),
                reasoning=data.get("reasoning", "")
            )
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise ValueError(f"Invalid LLM response format: {response_text}")

    def _classify_with_keywords(self, query: str) -> ClassificationResult:
        """
        Classify query using keyword heuristics as fallback.

        Args:
            query: The research query

        Returns:
            ClassificationResult based on keyword matching
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Count keyword matches
        academic_matches = len(query_words & self.ACADEMIC_KEYWORDS)
        non_academic_matches = len(query_words & self.NON_ACADEMIC_KEYWORDS)

        # Determine classification
        if non_academic_matches > academic_matches:
            category = self._determine_non_academic_category(query_lower)
            confidence = min(0.9, 0.5 + (non_academic_matches * 0.15))
            return ClassificationResult(
                is_academic=False,
                confidence=confidence,
                category=category,
                reasoning=f"Query matches non-academic keywords: {non_academic_matches} matches."
            )
        elif academic_matches > 0:
            category = "scientific_concept"
            confidence = min(0.9, 0.5 + (academic_matches * 0.15))
            return ClassificationResult(
                is_academic=True,
                confidence=confidence,
                category=category,
                reasoning=f"Query matches academic keywords: {academic_matches} matches."
            )
        else:
            # Default to academic (conservative approach)
            return ClassificationResult(
                is_academic=True,
                confidence=0.5,
                category="unknown",
                reasoning="No clear academic/non-academic indicators found. Defaulting to academic."
            )

    def _determine_non_academic_category(self, query_lower: str) -> str:
        """Determine specific non-academic category"""
        if any(word in query_lower for word in ["actor", "actress", "singer", "musician", "celebrity"]):
            return "celebrity"
        elif any(word in query_lower for word in ["movie", "film", "book", "novel", "album"]):
            return "entertainment"
        elif any(word in query_lower for word in ["stock", "price", "company", "brand", "product"]):
            return "business/product"
        elif any(word in query_lower for word in ["restaurant", "recipe", "food", "restaurant"]):
            return "lifestyle"
        else:
            return "other_non_academic"
