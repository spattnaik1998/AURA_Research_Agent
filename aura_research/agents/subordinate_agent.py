"""
Subordinate (Analyst) Agent for AURA
Analyzes assigned research papers and extracts key information
"""

from typing import Dict, Any, List
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .base_agent import BaseAgent, AgentStatus
from ..utils.config import OPENAI_API_KEY, GPT_MODEL
import json


class SubordinateAgent(BaseAgent):
    """
    Analyst agent that independently analyzes research papers
    """

    def __init__(self, agent_id: str):
        super().__init__(
            agent_id=agent_id,
            name=f"Analyst-{agent_id}"
        )
        self.llm = ChatOpenAI(
            model=GPT_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=0.3
        )

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze assigned research papers

        Args:
            task: Contains 'papers' (list of paper data)

        Returns:
            Structured analysis in JSON format
        """
        papers = task.get("papers", [])

        if not papers:
            return {
                "agent_id": self.agent_id,
                "analysis": [],
                "summary": "No papers assigned"
            }

        # Analyze each paper
        analyses = []
        for paper in papers:
            analysis = await self._analyze_paper(paper)
            analyses.append(analysis)

        # Create aggregate summary
        summary = await self._create_summary(analyses)

        return {
            "agent_id": self.agent_id,
            "papers_analyzed": len(papers),
            "analyses": analyses,
            "summary": summary
        }

    async def _analyze_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single research paper

        Args:
            paper: Paper metadata (title, snippet, link, etc.)

        Returns:
            Structured analysis
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert research analyst. Analyze the given research paper information and extract:
1. Core ideas and main contributions
2. Methodology or approach used
3. Key findings and results
4. Novel aspects or innovations
5. Research gaps or limitations mentioned

Provide a structured JSON analysis."""),
            ("user", """Analyze this research paper:

Title: {title}
Summary: {snippet}
Source: {link}

Provide detailed analysis in the following JSON format:
{{
    "title": "paper title",
    "core_ideas": ["idea1", "idea2", ...],
    "methodology": "brief description",
    "key_findings": ["finding1", "finding2", ...],
    "novelty": "what's new or innovative",
    "gaps": ["gap1", "gap2", ...],
    "relevance_score": 0-10
}}""")
        ])

        try:
            # Run LLM analysis
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "title": paper.get("title", "Unknown"),
                "snippet": paper.get("snippet", "No description available"),
                "link": paper.get("link", "")
            })

            # Parse JSON response
            content = response.content

            # Extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            analysis = json.loads(content)
            analysis["source_url"] = paper.get("link", "")

            return analysis

        except Exception as e:
            # Fallback structure if parsing fails
            return {
                "title": paper.get("title", "Unknown"),
                "core_ideas": ["Analysis failed"],
                "methodology": "Error occurred",
                "key_findings": [],
                "novelty": "Could not analyze",
                "gaps": [],
                "relevance_score": 0,
                "error": str(e),
                "source_url": paper.get("link", "")
            }

    async def _create_summary(self, analyses: List[Dict[str, Any]]) -> str:
        """
        Create summary of all analyzed papers

        Args:
            analyses: List of paper analyses

        Returns:
            Concise summary text
        """
        if not analyses:
            return "No analyses to summarize"

        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a research synthesizer. Create a concise summary of the analyzed papers."),
            ("user", """Based on these paper analyses, provide a brief 2-3 sentence summary of the key themes and findings:

{analyses}

Focus on common patterns, major contributions, and overall research direction.""")
        ])

        try:
            chain = summary_prompt | self.llm
            response = await chain.ainvoke({
                "analyses": json.dumps(analyses, indent=2)
            })

            return response.content.strip()

        except Exception as e:
            return f"Summary generation failed: {str(e)}"
