"""
Image Analyzer using GPT-4o Vision
Extracts research queries from uploaded images
"""

from typing import Dict
import base64
import re
from openai import OpenAI
from .config import OPENAI_API_KEY


class ImageAnalyzer:
    """
    Analyzes images using GPT-4o Vision to extract research intent
    """

    def __init__(self):
        """Initialize OpenAI client"""
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def extract_research_query(self, image_data: str) -> str:
        """
        Extract research query from image using GPT-4o Vision

        Args:
            image_data: Base64 encoded image data (with data:image prefix)

        Returns:
            Extracted research query string

        Raises:
            ValueError: If image analysis fails
        """
        try:
            # Prepare the vision prompt
            system_prompt = """You are an expert research assistant that analyzes images to extract research topics and queries.

Your task is to carefully examine the provided image and extract a clear, focused research query that could be used for academic literature search.

The image might contain:
- Screenshots of academic papers or articles
- Diagrams, charts, or figures from research
- Handwritten notes about research topics
- Mind maps or concept maps
- Presentations or slides about research
- Book pages or textbook content
- Whiteboards with research ideas
- Any visual content related to academic or scientific topics

INSTRUCTIONS:
1. Analyze the image thoroughly
2. Identify the main research topic, concept, or question
3. Extract a clear, concise research query (5-15 words)
4. Focus on the core academic/scientific topic
5. Make it suitable for academic paper search
6. If multiple topics are present, focus on the most prominent one

OUTPUT FORMAT:
Return ONLY the research query as plain text, without any explanation or additional text.

EXAMPLES OF GOOD QUERIES:
- "machine learning applications in medical diagnosis"
- "quantum computing algorithms for optimization"
- "climate change impact on coral reef ecosystems"
- "neural network architectures for natural language processing"
- "CRISPR gene editing ethical considerations"

If the image contains no clear research topic, return: "general academic research on [main visible topic]"
"""

            # Make API call to GPT-4o Vision
            response = self.client.chat.completions.create(
                model="gpt-4o",  # GPT-4o supports vision
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please analyze this image and extract a research query suitable for academic literature search:"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_data,
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=150,
                temperature=0.3  # Lower temperature for more focused extraction
            )

            # Extract query from response
            query = response.choices[0].message.content.strip()

            # Clean up the query
            query = self._clean_query(query)

            # Validate query length
            if len(query) < 5:
                raise ValueError("Extracted query too short")

            if len(query) > 200:
                # Truncate if too long
                query = query[:200].rsplit(' ', 1)[0] + "..."

            print(f"[ImageAnalyzer] Extracted query: {query}")
            return query

        except Exception as e:
            print(f"[ImageAnalyzer] Error analyzing image: {str(e)}")
            raise ValueError(f"Failed to analyze image: {str(e)}")

    def _clean_query(self, query: str) -> str:
        """
        Clean and format the extracted query

        Args:
            query: Raw extracted query

        Returns:
            Cleaned query string
        """
        # Remove quotes if present
        query = query.strip('"\'')

        # Remove common prefixes
        prefixes_to_remove = [
            "Research query:",
            "Query:",
            "Search for:",
            "Topic:",
            "Research topic:",
        ]

        for prefix in prefixes_to_remove:
            if query.lower().startswith(prefix.lower()):
                query = query[len(prefix):].strip()

        # Remove trailing punctuation except important ones
        query = query.rstrip('.,;:')

        # Capitalize first letter
        if query:
            query = query[0].upper() + query[1:]

        return query


# Singleton instance
_image_analyzer = None


def get_image_analyzer() -> ImageAnalyzer:
    """
    Get or create image analyzer instance

    Returns:
        ImageAnalyzer instance
    """
    global _image_analyzer
    if _image_analyzer is None:
        _image_analyzer = ImageAnalyzer()
    return _image_analyzer
