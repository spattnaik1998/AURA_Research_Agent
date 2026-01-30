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

        # Step 3: Compile complete essay (both visual and audio versions)
        essay, audio_essay = self._compile_essay(
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
            "audio_essay": audio_essay,  # NEW: audio-optimized version
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
        """Generate essay introduction with Sanguine Vagabond persona"""
        intro_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a highly literate, philosophical essayist with a background in deep tech and political economy. Your prose blends technical proficiency with the gravitas of a classical historian.

Adopt a 'Sanguine Vagabond' persona—curious, traveled, intellectually satiated. Your tone must be authoritative and sophisticated, yet punctuated with moments of earnest gratitude and awe for human ingenuity.

Your writing style:
- Use precise, 'high-church' English vocabulary (vicissitudes, precipice, epitomize, efflorescence)
- Construct long, mellifluous sentences with commas and semi-colons that weave multiple layers
- Always analyze through a 'macro lens' - paradigm shifts, social contract, systemic impacts
- Avoid short, choppy sentences
- Channel the sophistication of Ezra Klein or other distinguished public intellectuals"""),
            ("user", """WRITE AN OPENING ESSAY for a comprehensive research synthesis.

TOPIC: {query}
PAPERS ANALYZED: {count}

OPENING STRUCTURE (3-4 paragraphs, 400-500 words):

PARAGRAPH 1 - THE HUMAN CONDITION & SIGNIFICANCE:
- Begin with the profound human questions or existential stakes at play
- Why does this topic represent a crucial vicissitude in our intellectual or technological journey?
- Frame the research within broader currents of civilization, innovation, or societal evolution
- Use evocative yet precise language that captures both wonder and critical analysis

PARAGRAPH 2 - THE INTELLECTUAL LANDSCAPE:
- Survey the paradigmatic approaches and schools of thought with a historian's eye
- Identify the intellectual lineages, theoretical frameworks, or methodological efflorescence
- Note recent inflection points that have shifted the terrain
- Demonstrate deep familiarity while maintaining narrative momentum

PARAGRAPH 3 - SCOPE & INTELLECTUAL VOYAGE:
- Establish what this synthesis will illuminate and explore
- Frame the investigation as an intellectual journey through the research landscape
- Preview the thematic threads with sophisticated prose
- Set expectations for the depth and breadth of analysis to follow

STYLISTIC REQUIREMENTS:
- Long, flowing sentences that use semi-colons and commas to build complexity
- Sophisticated vocabulary that describes complexity and transition
- No generic academic phrases - be specific and original
- Demonstrate both technical precision and humanistic perspective
- Create a sense of intellectual grandeur without pomposity
- Show genuine appreciation for the ingenuity and effort behind the research

Write an opening that would befit a distinguished public intellectual's essay in a premier publication.""")
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
        """Generate essay body sections with Sanguine Vagabond persona"""
        body_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a distinguished essayist and intellectual historian. Your analysis combines deep technical understanding with classical prose.

Embody the 'Sanguine Vagabond' - authoritative, sophisticated, curious about human achievement. Your writing reveals patterns, paradigm shifts, and systemic insights through long, flowing sentences that build layered arguments.

Write like a premier public intellectual (Ezra Klein, Isaiah Berlin) - technically proficient yet deeply humanistic."""),
            ("user", """WRITE THE ANALYTICAL BODY of a comprehensive research synthesis.

═══════════════════════════════════════════════════════════
SYNTHESIS DATA:

Main Themes: {themes}

Key Findings: {findings}

Methodologies: {methodologies}

Research Gaps: {gaps}

Top Contributions: {contributions}

Papers Analyzed: {count}
═══════════════════════════════════════════════════════════

BODY STRUCTURE (7-10 paragraphs, 1200-1500 words):

Organize as a THEMATIC INTELLECTUAL NARRATIVE. For each major theme:

1. INTRODUCE WITH SYSTEMIC FRAMING:
   - Position the theme within broader paradigmatic shifts or epistemological currents
   - Explain its significance to the human condition, social contract, or technological evolution
   - Use the 'macro lens' - how does this theme epitomize larger patterns?

2. SYNTHESIZE WITH FLOWING PROSE:
   - Weave findings from multiple sources into coherent narrative threads
   - Use long sentences with semi-colons and commas to build complex arguments
   - Compare approaches with sophisticated transitions ("Moreover," "Nevertheless," "In this light,")
   - Highlight consensus and productive tensions

3. ANALYZE CRITICALLY WITH DEPTH:
   - Evaluate methodological approaches with intellectual rigor
   - Discuss implications for theory, practice, and society
   - Identify what these findings reveal about broader intellectual or civilizational questions
   - Note patterns, inflection points, and paradigmatic vicissitudes

4. MAINTAIN NARRATIVE MOMENTUM:
   - Use elegant transitions that connect themes organically
   - Build toward larger insights about the field's trajectory
   - Create a sense of intellectual journey and discovery

STYLISTIC IMPERATIVES:

VOCABULARY:
- Use precise, sophisticated terminology (vicissitudes, precipice, epitomize, efflorescence, paradigm, inflection point)
- Avoid generic academic phrases
- Choose words that convey complexity, transition, and significance

SENTENCE STRUCTURE:
- Long, mellifluous sentences that use commas and semi-colons
- Weave multiple clauses into unified arguments
- Avoid short, choppy sentences
- Create rhythm and flow

ANALYTICAL DEPTH:
- Always seek the macro lens - paradigm shifts, social contract implications, systemic patterns
- Connect technical findings to humanistic concerns
- Show appreciation for human ingenuity while maintaining critical distance
- Identify what research reveals about civilization, progress, or intellectual evolution

INTEGRATION:
- Don't list findings - synthesize into coherent narrative
- Compare and contrast with sophisticated prose
- Build toward larger insights
- Demonstrate deep understanding

Write body paragraphs that demonstrate intellectual sophistication, technical mastery, and humanistic perspective - worthy of a premier publication.""")
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
        """Generate essay conclusion with Sanguine Vagabond persona"""
        conclusion_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an accomplished intellectual essayist bringing closure to a sophisticated analysis.

As the 'Sanguine Vagabond', synthesize insights with gratitude for human achievement while maintaining critical sophistication. Your conclusion should elevate the discussion, connect to broader civilizational questions, and leave readers with profound insights.

Write with the gravitas and eloquence of a premier public intellectual."""),
            ("user", """WRITE A POWERFUL CONCLUSION for this research synthesis.

═══════════════════════════════════════════════════════════
TOPIC: {query}

KEY THEMES: {themes}

MAIN CONTRIBUTIONS: {contributions}

RESEARCH GAPS: {gaps}

METHODOLOGIES REVIEWED: {methodologies}
═══════════════════════════════════════════════════════════

CONCLUSION STRUCTURE (3-4 paragraphs, 400-500 words):

PARAGRAPH 1 - SYNTHESIS AT THE MACRO LEVEL:
- Elevate findings to reveal overarching patterns and paradigmatic shifts
- What do these insights collectively tell us about intellectual evolution, human progress, or systemic change?
- Use long, flowing sentences that weave multiple insights together
- Show both the technical achievement and humanistic significance

PARAGRAPH 2 - CIVILIZATIONAL & SYSTEMIC IMPLICATIONS:
- How do these findings shift paradigms, inform the social contract, or alter our understanding?
- What are the implications for society, technology, policy, or human flourishing?
- Connect technical findings to broader questions of human civilization
- Demonstrate both critical analysis and appreciation for ingenuity

PARAGRAPH 3 - THE HORIZON OF INQUIRY:
- What intellectual vicissitudes lie ahead?
- Where do the most promising avenues of investigation lead?
- What unanswered questions beckon further exploration?
- Frame future directions as part of humanity's ongoing intellectual journey

OPTIONAL PARAGRAPH 4 - THE BROADER VISTA:
- Step back to the widest lens - what does this body of work mean for human understanding?
- Connect to interdisciplinary concerns, philosophical questions, or civilizational challenges
- End with a memorable insight that captures both wonder and wisdom
- Leave readers with a sense of intellectual satisfaction and renewed curiosity

STYLISTIC REQUIREMENTS:

- Long, sophisticated sentences using semi-colons and commas
- High-church vocabulary (vicissitudes, precipice, efflorescence, paradigm)
- Macro lens framing (systemic, paradigmatic, civilizational)
- Balance critical rigor with genuine appreciation for human achievement
- Create sense of intellectual closure while opening new horizons
- End on a note of both gravitas and optimism

Write a conclusion that befits a distinguished essay in a premier intellectual publication - technically precise, humanistically profound, and beautifully written.""")
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

    def _compile_audio_essay(
        self,
        introduction: str,
        body: str,
        conclusion: str
    ) -> str:
        """
        Compile essay sections into audio-optimized prose.

        No headers, no metadata, no dates - just flowing prose suitable
        for professional audio narration (Ezra Klein style).
        """
        # Join sections with simple paragraph breaks
        # No headers, no dates, no "Generated by AURA" - just pure prose
        audio_essay = f"""{introduction}

{body}

{conclusion}"""

        return audio_essay.strip()

    def _compile_essay(
        self,
        query: str,
        introduction: str,
        body: str,
        conclusion: str,
        analyses: List[Dict[str, Any]]
    ) -> tuple:
        """
        Compile all sections into final essay - both visual and audio versions

        Returns:
            Tuple of (visual_essay, audio_essay)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        visual_essay = f"""# Research Essay: {query}

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
                    visual_essay += f"{i}. {authors} ({year}). {title}\n"
                else:
                    visual_essay += f"{i}. {title}\n"
                    if authors != "Information not provided in abstract":
                        visual_essay += f"   Authors: {authors}\n"
                    if year != "Information not provided in abstract":
                        visual_essay += f"   Year: {year}\n"
            else:
                # Fallback to analysis-level data
                title = analysis.get("title", analysis.get("summary", "Unknown Title")[:100])
                visual_essay += f"{i}. {title}\n"
                url = analysis.get("source_url", "")

            if url:
                visual_essay += f"   URL: {url}\n"
            visual_essay += "\n"

        visual_essay += f"\n---\n\n*This essay was generated by AURA - Autonomous Unified Research Assistant*\n"
        visual_essay += f"*Generated with Claude Code (https://claude.com/claude-code)*\n"

        # AUDIO VERSION (for ElevenLabs) - clean prose only
        audio_essay = self._compile_audio_essay(introduction, body, conclusion)

        return visual_essay, audio_essay

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
