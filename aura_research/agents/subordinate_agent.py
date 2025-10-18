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
        Analyze a single research paper using ReAct framework

        Args:
            paper: Paper metadata (title, snippet, link, etc.)

        Returns:
            Structured analysis with summary, key_points, and citations
        """
        # ReAct Framework: Reasoning + Acting
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert research analyst using the ReAct (Reasoning + Acting) framework.

For each paper, follow this process:
1. THOUGHT: Analyze the research significance and context
2. ACTION: Extract key information systematically
3. OBSERVATION: Identify patterns, findings, and contributions
4. REFLECTION: Assess novelty, impact, and limitations

Output a structured JSON with:
- summary: Concise 2-3 sentence overview
- key_points: List of main contributions and findings
- citations: Proper citation information
- metadata: Analysis details"""),
            ("user", """Analyze this research paper using ReAct reasoning:

Title: {title}
Abstract/Summary: {snippet}
Source: {link}

Follow the ReAct framework:

THOUGHT: What is the significance of this research?
ACTION: Extract the core contributions and methodology
OBSERVATION: What are the key findings and results?
REFLECTION: What is novel and what gaps exist?

Output in this JSON format:
{{
    "summary": "Brief 2-3 sentence overview of the paper",
    "key_points": [
        "Main contribution 1",
        "Main contribution 2",
        "Key finding 1",
        "Methodology insight",
        "Novel aspect"
    ],
    "citations": [
        {{
            "title": "paper title",
            "authors": "if available, else 'Not specified'",
            "year": "if available, else 'Not specified'",
            "source": "{link}"
        }}
    ],
    "metadata": {{
        "core_ideas": ["idea1", "idea2"],
        "methodology": "brief description",
        "key_findings": ["finding1", "finding2"],
        "novelty": "what's new",
        "limitations": ["limitation1", "limitation2"],
        "relevance_score": 8,
        "reasoning": "Your ReAct thought process summary"
    }}
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

            # Ensure required structure
            if "summary" not in analysis:
                # Convert old format to new format if needed
                analysis = {
                    "summary": f"Analysis of {paper.get('title', 'Unknown')}",
                    "key_points": analysis.get("core_ideas", []) + analysis.get("key_findings", []),
                    "citations": [{
                        "title": paper.get("title", "Unknown"),
                        "authors": "Not specified",
                        "year": "Not specified",
                        "source": paper.get("link", "")
                    }],
                    "metadata": {
                        "core_ideas": analysis.get("core_ideas", []),
                        "methodology": analysis.get("methodology", ""),
                        "key_findings": analysis.get("key_findings", []),
                        "novelty": analysis.get("novelty", ""),
                        "limitations": analysis.get("gaps", []),
                        "relevance_score": analysis.get("relevance_score", 0),
                        "reasoning": "ReAct framework applied"
                    }
                }

            return analysis

        except Exception as e:
            # Fallback structure with new format
            return {
                "summary": f"Unable to fully analyze: {paper.get('title', 'Unknown')}. Error: {str(e)}",
                "key_points": [
                    "Analysis encountered an error",
                    "Paper information partially available"
                ],
                "citations": [{
                    "title": paper.get("title", "Unknown"),
                    "authors": "Not specified",
                    "year": "Not specified",
                    "source": paper.get("link", "")
                }],
                "metadata": {
                    "core_ideas": [],
                    "methodology": "Could not extract",
                    "key_findings": [],
                    "novelty": "Could not assess",
                    "limitations": ["Analysis failed"],
                    "relevance_score": 0,
                    "reasoning": f"Error occurred: {str(e)}",
                    "error": str(e)
                }
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
