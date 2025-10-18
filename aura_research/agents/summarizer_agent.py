"""
Summarizer Agent for AURA
Synthesizes subordinate agent outputs into a cohesive research essay
"""

from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from .base_agent import BaseAgent
from ..utils.config import OPENAI_API_KEY, GPT_MODEL, ESSAYS_DIR
import json
from datetime import datetime
from pathlib import Path


class SummarizerAgent(BaseAgent):
    """
    Agent that synthesizes all research analyses into a cohesive essay
    """

    def __init__(self):
        super().__init__(
            agent_id="summarizer-001",
            name="Summarizer"
        )
        self.llm = ChatOpenAI(
            model=GPT_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=0.5  # Slightly higher for more creative synthesis
        )

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize research analyses into a cohesive essay

        Args:
            task: Contains 'query', 'analyses', 'subordinate_results'

        Returns:
            Essay text and metadata
        """
        query = task.get("query", "")
        analyses = task.get("analyses", [])
        subordinate_results = task.get("subordinate_results", [])

        if not analyses:
            return {
                "essay": "No analyses available to synthesize.",
                "word_count": 0,
                "citations": 0,
                "file_path": None
            }

        print(f"\n[Summarizer] Synthesizing {len(analyses)} analyses into essay...")

        # Step 1: Create structured synthesis
        synthesis = await self._create_synthesis(query, analyses)

        # Step 2: Generate essay sections
        introduction = await self._generate_introduction(query, analyses)
        body = await self._generate_body(synthesis, analyses)
        conclusion = await self._generate_conclusion(query, synthesis)

        # Step 3: Compile complete essay
        essay = self._compile_essay(
            query=query,
            introduction=introduction,
            body=body,
            conclusion=conclusion,
            analyses=analyses
        )

        # Step 4: Save essay to file
        file_path = self._save_essay(query, essay)

        # Step 5: Generate metadata
        metadata = self._generate_metadata(essay, analyses)

        print(f"[Summarizer] Essay generated: {metadata['word_count']} words, {metadata['citations']} citations")

        return {
            "essay": essay,
            "file_path": file_path,
            **metadata
        }

    async def _create_synthesis(
        self,
        query: str,
        analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a structured synthesis of all analyses

        Args:
            query: Research query
            analyses: List of paper analyses

        Returns:
            Structured synthesis with themes and patterns
        """
        synthesis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a research synthesizer. Analyze multiple research paper analyses and identify:
1. Main themes and patterns
2. Key methodologies used
3. Common findings and contradictions
4. Research gaps and future directions
5. Most impactful contributions

Return a structured JSON summary."""),
            ("user", """Research Query: {query}

Analyze these {count} paper analyses and create a structured synthesis:

{analyses}

Provide output in JSON format:
{{
    "main_themes": ["theme1", "theme2", ...],
    "methodologies": ["method1", "method2", ...],
    "key_findings": ["finding1", "finding2", ...],
    "contradictions": ["contradiction1", ...],
    "research_gaps": ["gap1", "gap2", ...],
    "top_contributions": ["contribution1", "contribution2", ...]
}}""")
        ])

        try:
            chain = synthesis_prompt | self.llm
            response = await chain.ainvoke({
                "query": query,
                "count": len(analyses),
                "analyses": json.dumps(analyses[:20], indent=2)  # Limit to prevent token overflow
            })

            content = response.content

            # Extract JSON from markdown if needed
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)

        except Exception as e:
            print(f"[Summarizer] Synthesis error: {str(e)}")
            return {
                "main_themes": ["Analysis in progress"],
                "methodologies": [],
                "key_findings": [],
                "contradictions": [],
                "research_gaps": [],
                "top_contributions": []
            }

    async def _generate_introduction(
        self,
        query: str,
        analyses: List[Dict[str, Any]]
    ) -> str:
        """Generate essay introduction"""
        intro_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an academic writer creating research essay introductions."),
            ("user", """Write a compelling introduction for a research essay on: {query}

Context: This essay synthesizes findings from {count} research papers.

The introduction should:
- Establish the importance of the topic
- Provide context and background
- State the scope of the review
- Preview main themes

Write 2-3 well-structured paragraphs.""")
        ])

        try:
            chain = intro_prompt | self.llm
            response = await chain.ainvoke({
                "query": query,
                "count": len(analyses)
            })
            return response.content.strip()
        except Exception as e:
            return f"Introduction could not be generated: {str(e)}"

    async def _generate_body(
        self,
        synthesis: Dict[str, Any],
        analyses: List[Dict[str, Any]]
    ) -> str:
        """Generate essay body sections"""
        body_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an academic writer. Create a comprehensive body section for a research essay.
Organize content into clear thematic sections with proper citations."""),
            ("user", """Based on this research synthesis, write the main body of the essay:

Main Themes: {themes}
Key Findings: {findings}
Methodologies: {methodologies}
Research Gaps: {gaps}

Number of papers analyzed: {count}

Create 4-6 well-structured paragraphs organized by themes. Include:
- Detailed discussion of each theme
- Supporting evidence from research
- Comparisons and contrasts
- Critical analysis

Use academic tone and proper structure. Reference papers as [Author, Year] or [Paper N] where appropriate.""")
        ])

        try:
            chain = body_prompt | self.llm
            response = await chain.ainvoke({
                "themes": ", ".join(synthesis.get("main_themes", [])),
                "findings": ", ".join(synthesis.get("key_findings", [])[:5]),
                "methodologies": ", ".join(synthesis.get("methodologies", [])),
                "gaps": ", ".join(synthesis.get("research_gaps", [])[:3]),
                "count": len(analyses)
            })
            return response.content.strip()
        except Exception as e:
            return f"Body section could not be generated: {str(e)}"

    async def _generate_conclusion(
        self,
        query: str,
        synthesis: Dict[str, Any]
    ) -> str:
        """Generate essay conclusion"""
        conclusion_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an academic writer creating research essay conclusions."),
            ("user", """Write a conclusion for a research essay on: {query}

Key Themes: {themes}
Main Contributions: {contributions}
Research Gaps: {gaps}

The conclusion should:
- Summarize main findings
- Highlight key contributions
- Discuss implications
- Suggest future research directions

Write 2-3 well-structured paragraphs.""")
        ])

        try:
            chain = conclusion_prompt | self.llm
            response = await chain.ainvoke({
                "query": query,
                "themes": ", ".join(synthesis.get("main_themes", [])),
                "contributions": ", ".join(synthesis.get("top_contributions", [])),
                "gaps": ", ".join(synthesis.get("research_gaps", []))
            })
            return response.content.strip()
        except Exception as e:
            return f"Conclusion could not be generated: {str(e)}"

    def _compile_essay(
        self,
        query: str,
        introduction: str,
        body: str,
        conclusion: str,
        analyses: List[Dict[str, Any]]
    ) -> str:
        """Compile all sections into final essay"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        essay = f"""# Research Essay: {query}

**Generated by AURA Research Assistant**
**Date:** {timestamp}
**Papers Analyzed:** {len(analyses)}

---

## Introduction

{introduction}

---

## Analysis and Findings

{body}

---

## Conclusion

{conclusion}

---

## References

"""
        # Add references
        for i, analysis in enumerate(analyses, 1):
            title = analysis.get("title", "Unknown Title")
            url = analysis.get("source_url", "")
            essay += f"{i}. {title}\n"
            if url:
                essay += f"   {url}\n"

        essay += f"\n---\n\n*This essay was generated by AURA - Autonomous Unified Research Assistant*\n"
        essay += f"*Generated with Claude Code (https://claude.com/claude-code)*\n"

        return essay

    def _save_essay(self, query: str, essay: str) -> str:
        """Save essay to file"""
        # Create filename from query
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = "".join(c if c.isalnum() or c in (' ', '-') else '' for c in query)
        safe_query = safe_query.replace(' ', '_')[:50]  # Limit length

        filename = f"essay_{safe_query}_{timestamp}.md"
        file_path = Path(ESSAYS_DIR) / filename

        # Save essay
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(essay)

        print(f"[Summarizer] Essay saved to: {file_path}")

        return str(file_path)

    def _generate_metadata(self, essay: str, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate essay metadata"""
        word_count = len(essay.split())
        citations = len(analyses)

        return {
            "word_count": word_count,
            "citations": citations,
            "papers_synthesized": len(analyses),
            "timestamp": datetime.now().isoformat()
        }
