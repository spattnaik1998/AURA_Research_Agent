"""
Summarizer Agent for AURA
Synthesizes subordinate agent outputs into a cohesive research essay
"""

from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
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
            temperature=0.4  # Balanced for creative but accurate synthesis
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

        # Initialize RAG vector store immediately
        session_id = self._extract_session_id(file_path)
        rag_initialized = self._initialize_rag_vector_store(session_id, analyses, essay, query)

        # Notify that RAG can be initialized
        self._notify_rag_ready(file_path, analyses)

        return {
            "essay": essay,
            "file_path": file_path,
            "rag_ready": rag_initialized,  # Signal that RAG is actually initialized
            **metadata
        }

    def _extract_session_id(self, file_path: str) -> str:
        """Extract session ID from file path"""
        import re
        match = re.search(r'_(\d{8}_\d{6})\.', file_path)
        if match:
            return match.group(1)
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _initialize_rag_vector_store(
        self,
        session_id: str,
        analyses: List[Dict[str, Any]],
        essay: str,
        query: str
    ) -> bool:
        """
        Initialize RAG vector store immediately after essay generation

        Args:
            session_id: Research session ID
            analyses: List of paper analyses
            essay: Generated essay
            query: Research query

        Returns:
            True if successful, False otherwise
        """
        try:
            from ..rag.vector_store import VectorStoreManager

            print(f"\n[Summarizer] Initializing RAG vector store for session: {session_id}")

            # Create vector store manager
            vector_manager = VectorStoreManager()

            # Initialize from session data directly
            success = vector_manager.initialize_from_session(session_id)

            if success:
                print(f"[Summarizer] ✅ RAG vector store initialized successfully")
                return True
            else:
                print(f"[Summarizer] ⚠️  RAG vector store initialization failed")
                return False

        except Exception as e:
            print(f"[Summarizer] ❌ RAG vector store initialization error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _notify_rag_ready(self, essay_file_path: str, analyses: List[Dict[str, Any]]):
        """
        Notify backend that RAG chatbot can be initialized

        Args:
            essay_file_path: Path to the saved essay
            analyses: List of all analyses for vector store
        """
        print(f"\n{'='*60}")
        print("[Summarizer] RAG INITIALIZATION READY")
        print(f"{'='*60}")
        print(f"Essay saved: {essay_file_path}")
        print(f"Total analyses available: {len(analyses)}")
        print(f"RAG chatbot can now be activated with this content")
        print(f"{'='*60}\n")

        # Create RAG-ready signal file
        rag_signal_path = Path(ESSAYS_DIR) / "rag_ready.signal"
        with open(rag_signal_path, 'w') as f:
            f.write(json.dumps({
                "essay_path": essay_file_path,
                "analyses_count": len(analyses),
                "timestamp": datetime.now().isoformat(),
                "status": "ready"
            }, indent=2))

        print(f"[Summarizer] RAG signal file created: {rag_signal_path}")

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
            ("system", """You are a WORLD-CLASS research synthesizer with expertise in meta-analysis and systematic reviews.

CRITICAL REQUIREMENTS:
1. Extract SPECIFIC themes using actual terminology from the papers
2. Identify CONCRETE methodologies with precise names (algorithms, frameworks, techniques)
3. Synthesize SUBSTANTIVE findings (not generic statements)
4. Be scholarly, precise, and insightful
5. Think like a senior researcher conducting a literature review

Your synthesis will guide the final essay - make it exceptional."""),
            ("user", """CONDUCT A COMPREHENSIVE SYNTHESIS OF RESEARCH FINDINGS

Research Query: {query}
Number of Papers: {count}

═══════════════════════════════════════════════════════════
PAPER ANALYSES:
{analyses}
═══════════════════════════════════════════════════════════

SYNTHESIS REQUIREMENTS:

1. MAIN THEMES (5-8 themes):
   - Identify SPECIFIC recurring topics using exact terminology from papers
   - Example: "Transformer-based architectures for sequence modeling" NOT "deep learning methods"
   - Each theme should be substantive and precise

2. METHODOLOGIES (5-10 specific methods):
   - List EXACT methods, algorithms, frameworks mentioned
   - Examples: "BERT fine-tuning", "Proximal Policy Optimization", "Variational Autoencoders"
   - NOT generic like "machine learning approaches"

3. KEY FINDINGS (8-12 findings):
   - Extract SPECIFIC discoveries, improvements, or insights
   - Include metrics if mentioned (e.g., "achieved 95% accuracy on ImageNet")
   - Each finding should be concrete and informative

4. CONTRADICTIONS (if any):
   - Identify where papers disagree or present conflicting results
   - Be specific about what conflicts and why

5. RESEARCH GAPS (3-7 gaps):
   - What questions remain unanswered?
   - What limitations were noted?
   - What future work was suggested?

6. TOP CONTRIBUTIONS (5-8 contributions):
   - What are the most significant advances from these papers?
   - What novel techniques or insights were introduced?
   - What practical applications were demonstrated?

OUTPUT IN PRECISE JSON FORMAT:
{{
    "main_themes": ["Specific theme 1 with technical detail", "Specific theme 2...", ...],
    "methodologies": ["Exact method 1", "Exact algorithm 2", "Specific framework 3", ...],
    "key_findings": ["Concrete finding 1 with details", "Specific result 2", ...],
    "contradictions": ["Specific contradiction 1 if found", ...],
    "research_gaps": ["Specific gap 1", "Unanswered question 2", ...],
    "top_contributions": ["Major contribution 1 with specifics", "Novel technique 2", ...]
}}

CRITICAL: Every item must be SPECIFIC and SUBSTANTIVE. No generic placeholders.""")
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
            ("system", """You are a distinguished academic writer specializing in research synthesis.

Your introduction must:
- Hook the reader with significance and relevance
- Demonstrate deep understanding of the field
- Use scholarly language with precision
- Set clear expectations for what follows
- Be engaging yet rigorous"""),
            ("user", """WRITE A SCHOLARLY INTRODUCTION for a research synthesis essay

TOPIC: {query}
PAPERS ANALYZED: {count}

INTRODUCTION STRUCTURE (3-4 paragraphs, 300-400 words):

PARAGRAPH 1 - SIGNIFICANCE & CONTEXT:
- Why is this topic critically important?
- What real-world problems or questions does it address?
- What is the current state of knowledge?
- Use compelling but factual language

PARAGRAPH 2 - RESEARCH LANDSCAPE:
- What major approaches or themes exist in this area?
- Who are the key researchers or schools of thought?
- What recent developments have shaped the field?
- Establish breadth of the research reviewed

PARAGRAPH 3 - SCOPE & OBJECTIVES:
- What specific aspects does this synthesis cover?
- What are the key questions addressed?
- What themes will be explored?
- What can readers expect to learn?

WRITING GUIDELINES:
- Use sophisticated academic vocabulary
- Maintain formal scholarly tone
- Be specific and concrete (avoid vague generalizations)
- Support claims with implicit reference to the literature
- Create logical flow between paragraphs
- Engage the reader's interest while maintaining rigor

Write a compelling, scholarly introduction that sets the stage for an exceptional research synthesis.""")
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
            ("system", """You are an EXPERT academic writer with extensive experience in research synthesis and systematic reviews.

Your essay body must:
- Present a coherent narrative organized by themes
- Integrate findings from multiple sources
- Provide critical analysis, not just summary
- Use specific examples and concrete evidence
- Maintain scholarly rigor while being readable
- Include proper academic discourse markers
- Demonstrate synthesis, comparison, and evaluation"""),
            ("user", """WRITE THE MAIN BODY of a comprehensive research synthesis essay

═══════════════════════════════════════════════════════════
SYNTHESIS DATA:

Main Themes: {themes}

Key Findings: {findings}

Methodologies: {methodologies}

Research Gaps: {gaps}

Top Contributions: {contributions}

Papers Analyzed: {count}
═══════════════════════════════════════════════════════════

BODY STRUCTURE (6-8 paragraphs, 800-1200 words):

Organize content into THEMATIC SECTIONS. For each major theme:

1. INTRODUCE THE THEME:
   - Present the theme with context
   - Explain its significance to the research question
   - Preview what will be discussed

2. SYNTHESIZE FINDINGS:
   - Integrate findings from multiple papers
   - Use specific examples and concrete evidence
   - Compare and contrast different approaches
   - Highlight consensus and contradictions

3. ANALYZE CRITICALLY:
   - Evaluate methodological strengths and weaknesses
   - Discuss implications of findings
   - Connect findings to broader research context
   - Identify patterns and trends

4. TRANSITION SMOOTHLY:
   - Use clear transitions between paragraphs
   - Build a logical narrative arc
   - Connect themes to each other where relevant

WRITING REQUIREMENTS:

SPECIFICITY:
- Use actual methodology names and technical terms
- Reference concrete findings (not "studies showed...")
- Include specific examples from the research

ACADEMIC DISCOURSE:
- Use phrases like: "Research demonstrates...", "Studies consistently indicate...", "Emerging evidence suggests...", "While some scholars argue...", "In contrast...", "Moreover...", "Nevertheless..."
- Maintain formal scholarly tone
- Use precise academic vocabulary

SYNTHESIS (NOT SUMMARY):
- DON'T just list what each paper found
- DO integrate findings into coherent themes
- DO compare and contrast approaches
- DO evaluate significance and implications
- DO identify patterns across studies

CRITICAL ANALYSIS:
- Evaluate methodological approaches
- Discuss limitations where relevant
- Identify gaps in current knowledge
- Note contradictions or inconsistencies
- Assess practical implications

CITATIONS:
- Reference findings appropriately
- Use phrases like "research in this area has shown...", "studies have demonstrated...", "evidence indicates..."
- When discussing specific techniques or findings, indicate this is drawn from the reviewed literature

Write a scholarly, well-integrated body that demonstrates DEEP SYNTHESIS and CRITICAL THINKING.""")
        ])

        try:
            chain = body_prompt | self.llm
            response = await chain.ainvoke({
                "themes": "\n- ".join(synthesis.get("main_themes", [])),
                "findings": "\n- ".join(synthesis.get("key_findings", [])),
                "methodologies": "\n- ".join(synthesis.get("methodologies", [])),
                "gaps": "\n- ".join(synthesis.get("research_gaps", [])),
                "contributions": "\n- ".join(synthesis.get("top_contributions", [])),
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
            ("system", """You are an accomplished academic writer specializing in impactful research conclusions.

Your conclusion must:
- Synthesize key insights (not just repeat)
- Emphasize significance and implications
- Provide forward-looking perspective
- Leave reader with clear understanding of contribution
- Maintain scholarly gravitas while being compelling"""),
            ("user", """WRITE A COMPELLING CONCLUSION for a research synthesis essay

═══════════════════════════════════════════════════════════
TOPIC: {query}

KEY THEMES:
{themes}

MAIN CONTRIBUTIONS:
{contributions}

RESEARCH GAPS:
{gaps}

METHODOLOGIES REVIEWED:
{methodologies}
═══════════════════════════════════════════════════════════

CONCLUSION STRUCTURE (3-4 paragraphs, 300-400 words):

PARAGRAPH 1 - SYNTHESIS OF INSIGHTS:
- Synthesize (don't just summarize) the most important findings
- What are the overarching insights from this body of research?
- What patterns or trends emerged across the literature?
- What do these findings collectively tell us?

PARAGRAPH 2 - SIGNIFICANCE & IMPLICATIONS:
- Why do these findings matter?
- What are the theoretical implications?
- What are the practical implications?
- How does this advance the field?
- What problems can now be solved or approached differently?

PARAGRAPH 3 - FUTURE DIRECTIONS:
- What are the most promising avenues for future research?
- What questions remain unanswered?
- What new questions have emerged from this synthesis?
- How might the field evolve based on current trends?

OPTIONAL PARAGRAPH 4 - BROADER IMPACT (if appropriate):
- What is the broader significance beyond the immediate field?
- What interdisciplinary connections exist?
- What societal or practical impact might this research have?

WRITING REQUIREMENTS:

SYNTHESIS (not summary):
- Don't repeat what was already said
- Elevate to higher-level insights
- Connect dots between themes
- Show the bigger picture

FORWARD-LOOKING:
- Be specific about future directions
- Identify concrete research opportunities
- Suggest specific methodological advances needed
- Anticipate emerging trends

IMPACTFUL:
- Emphasize significance without overstating
- Use strong but measured language
- End with a memorable insight
- Leave reader understanding why this matters

SCHOLARLY TONE:
- Maintain academic rigor
- Use sophisticated vocabulary
- Employ proper academic discourse markers
- Balance confidence with appropriate hedging

Write a conclusion that provides closure while opening new horizons. Make it intellectually satisfying and professionally impactful.""")
        ])

        try:
            chain = conclusion_prompt | self.llm
            response = await chain.ainvoke({
                "query": query,
                "themes": "\n- ".join(synthesis.get("main_themes", [])),
                "contributions": "\n- ".join(synthesis.get("top_contributions", [])),
                "gaps": "\n- ".join(synthesis.get("research_gaps", [])),
                "methodologies": "\n- ".join(synthesis.get("methodologies", []))
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
        # Add references - extract from citations in each analysis
        for i, analysis in enumerate(analyses, 1):
            # Try to get citation info from the analysis structure
            citations = analysis.get("citations", [])
            if citations and len(citations) > 0:
                citation = citations[0]
                title = citation.get("title", "Unknown Title")
                authors = citation.get("authors", "Authors not specified")
                year = citation.get("year", "Year not specified")
                url = citation.get("source", "")

                # Format citation
                if authors != "Information not provided in abstract" and year != "Information not provided in abstract":
                    essay += f"{i}. {authors} ({year}). {title}\n"
                else:
                    essay += f"{i}. {title}\n"
                    if authors != "Information not provided in abstract":
                        essay += f"   Authors: {authors}\n"
                    if year != "Information not provided in abstract":
                        essay += f"   Year: {year}\n"
            else:
                # Fallback to analysis-level data
                title = analysis.get("title", analysis.get("summary", "Unknown Title")[:100])
                essay += f"{i}. {title}\n"
                url = analysis.get("source_url", "")

            if url:
                essay += f"   URL: {url}\n"
            essay += "\n"

        essay += f"\n---\n\n*This essay was generated by AURA - Autonomous Unified Research Assistant*\n"
        essay += f"*Generated with Claude Code (https://claude.com/claude-code)*\n"

        return essay

    def _save_essay(self, query: str, essay: str) -> str:
        """Save essay to .txt file"""
        # Create filename from query
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = "".join(c if c.isalnum() or c in (' ', '-') else '' for c in query)
        safe_query = safe_query.replace(' ', '_')[:50]  # Limit length

        # Save as .txt file as specified
        filename = f"essay_{safe_query}_{timestamp}.txt"
        file_path = Path(ESSAYS_DIR) / filename

        # Save essay
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(essay)

        print(f"[Summarizer] Essay saved to: {file_path}")

        # Also save markdown version for better formatting
        md_filename = f"essay_{safe_query}_{timestamp}.md"
        md_file_path = Path(ESSAYS_DIR) / md_filename
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(essay)

        print(f"[Summarizer] Markdown version saved to: {md_file_path}")

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
