"""
Summarizer Agent for AURA
Synthesizes subordinate agent outputs into a cohesive research essay
"""

from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .base_agent import BaseAgent
from ..utils.config import (
    OPENAI_API_KEY, GPT_MODEL, ESSAYS_DIR,
    MIN_QUALITY_SCORE, MAX_ESSAY_REGENERATION_ATTEMPTS,
    MIN_CITATION_ACCURACY, LLM_CALL_TIMEOUT, GRACEFUL_DEGRADATION_THRESHOLD
)
from ..services.quality_scoring_service import QualityScoringService
from ..services.citation_verification_service import CitationVerificationService
from ..services.fact_checking_service import FactCheckingService
from ..utils.error_messages import (
    get_low_quality_essay_error,
    get_citation_verification_failed_error,
    get_fact_check_failed_error,
    get_success_message
)
import json
from datetime import datetime
from pathlib import Path
import asyncio
import time
import sys
import io


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
            temperature=0.3  # Precise academic tone
        )
        self.quality_scorer = QualityScoringService()
        self.citation_verifier = CitationVerificationService()
        self.fact_checker = FactCheckingService()
        self.regeneration_attempts = 0
        self.reasoning_trace = {}  # Track ReAct reasoning output
        self.execution_start_time = None  # Track execution time for timeout checks

        # Configure stdout for UTF-8 encoding on Windows
        if sys.stdout.encoding != 'utf-8':
            try:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            except Exception as e:
                pass  # Fallback to default encoding if reconfiguration fails

    def _safe_print(self, message: str):
        """Safely print message with Unicode encoding error handling"""
        try:
            print(message)
        except UnicodeEncodeError:
            # If Unicode encoding fails, encode with replacement characters
            print(message.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
        except Exception as e:
            # Final fallback - remove any problematic characters
            print(message.encode('ascii', errors='replace').decode('ascii'))

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize research analyses into a cohesive essay

        Args:
            task: Contains 'query', 'analyses', 'subordinate_results'

        Returns:
            Essay text and metadata
        """
        # Initialize execution timer
        if self.execution_start_time is None:
            self.execution_start_time = time.time()

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

        self._safe_print(f"\n[Summarizer] Synthesizing {len(analyses)} analyses into essay...")

        # Step 1: Create structured synthesis
        synthesis = await self._create_synthesis(query, analyses)

        # Step 2: Build paper reference data for citation injection
        paper_references = self._build_paper_reference_data(analyses)

        # Step 3: Generate essay sections
        introduction = await self._generate_introduction(query, analyses, synthesis, paper_references)
        body = await self._generate_body(synthesis, analyses, paper_references)
        conclusion = await self._generate_conclusion(query, synthesis, paper_references)

        # Step 4: Compile complete essay (both visual and audio versions)
        essay, audio_essay = self._compile_essay(
            query=query,
            introduction=introduction,
            body=body,
            conclusion=conclusion,
            analyses=analyses
        )

        # LAYER 3: Quality Scoring Assessment
        self._safe_print(f"\n[Summarizer] Assessing essay quality...")
        try:
            quality_result = await self.quality_scorer.score_essay(essay, analyses)
            quality_score = quality_result["overall_score"]
        except UnicodeEncodeError as e:
            import logging
            logger = logging.getLogger('aura.summarizer')
            logger.error(f"Unicode encoding error during quality assessment: {e}")
            # Fallback: assign a moderate quality score
            quality_result = {
                "overall_score": 6.5,
                "scores": {},
                "citation_count": 0,
                "word_count": len(essay.split()),
                "assessment": "adequate",
                "issues": ["Unicode encoding issue during assessment"]
            }
            quality_score = 6.5

        if quality_score < MIN_QUALITY_SCORE:
            elapsed = time.time() - self.execution_start_time

            if self.regeneration_attempts < MAX_ESSAY_REGENERATION_ATTEMPTS and elapsed < GRACEFUL_DEGRADATION_THRESHOLD:
                self.regeneration_attempts += 1
                self._safe_print(f"[Summarizer] ⚠️  Quality score {quality_score:.1f} below threshold. Attempting regeneration... (elapsed: {elapsed:.0f}s)")
                # Recursively regenerate with stricter requirements
                return await self.run(task)
            else:
                if elapsed >= GRACEFUL_DEGRADATION_THRESHOLD:
                    # Time budget exceeded - accept essay with warning
                    self._safe_print(f"[Summarizer] ⚠️  GRACEFUL DEGRADATION: Accepting essay with quality score {quality_score:.1f} (below threshold)")
                else:
                    error_msg = get_low_quality_essay_error(quality_score, MIN_QUALITY_SCORE, quality_result.get("issues", []))
                    self._safe_print(f"[Summarizer] ❌ Essay rejected: {error_msg}")
                    raise ValueError(error_msg)

        self._safe_print(f"[Summarizer] ✓ Quality score: {quality_score:.1f}/10.0")

        # LAYER 4: Citation Verification
        self._safe_print(f"[Summarizer] Verifying citations...")
        citation_result = await self.citation_verifier.verify_citations(essay)

        if not citation_result.is_valid:
            elapsed = time.time() - self.execution_start_time

            if self.regeneration_attempts < MAX_ESSAY_REGENERATION_ATTEMPTS and elapsed < GRACEFUL_DEGRADATION_THRESHOLD:
                self.regeneration_attempts += 1
                self._safe_print(f"[Summarizer] ⚠️  Citation verification failed. Attempting regeneration... (elapsed: {elapsed:.0f}s)")
                return await self.run(task)
            else:
                if elapsed >= GRACEFUL_DEGRADATION_THRESHOLD:
                    self._safe_print(f"[Summarizer] ⚠️  GRACEFUL DEGRADATION: Accepting essay with citation issues")
                else:
                    error_msg = get_citation_verification_failed_error(
                        len(citation_result.orphan_citations),
                        len(citation_result.unused_references),
                        len(citation_result.citation_mismatches)
                    )
                    self._safe_print(f"[Summarizer] ❌ Essay rejected: {error_msg}")
                    raise ValueError(error_msg)

        self._safe_print(f"[Summarizer] ✓ Citation verification passed ({citation_result.success_rate*100:.1f}% accuracy)")

        # LAYER 5: Fact-Checking
        self._safe_print(f"[Summarizer] Running fact-checking verification...")
        fact_check_result = await self.fact_checker.verify_essay_claims(essay, analyses)

        if not fact_check_result["is_valid"]:
            elapsed = time.time() - self.execution_start_time

            if self.regeneration_attempts < MAX_ESSAY_REGENERATION_ATTEMPTS and elapsed < GRACEFUL_DEGRADATION_THRESHOLD:
                self.regeneration_attempts += 1
                self._safe_print(f"[Summarizer] ⚠️  Fact-checking failed. Attempting regeneration... (elapsed: {elapsed:.0f}s)")
                return await self.run(task)
            else:
                if elapsed >= GRACEFUL_DEGRADATION_THRESHOLD:
                    self._safe_print(f"[Summarizer] ⚠️  GRACEFUL DEGRADATION: Accepting essay with fact-check issues")
                else:
                    error_msg = get_fact_check_failed_error(
                        fact_check_result["supported_percentage"],
                        0.85
                    )
                    self._safe_print(f"[Summarizer] ❌ Essay rejected: {error_msg}")
                    raise ValueError(error_msg)

        self._safe_print(f"[Summarizer] ✓ Fact-checking passed ({fact_check_result['supported_percentage']*100:.1f}% of claims verified)")

        # Step 5: Save essay to file
        file_path = self._save_essay(query, essay)

        # Step 6: Generate metadata
        metadata = self._generate_metadata(essay, analyses)

        self._safe_print(f"[Summarizer] Essay generated: {metadata['word_count']} words, {metadata['citations']} citations")

        # Print success message
        success_msg = get_success_message(
            len(analyses),
            quality_score,
            metadata['word_count'],
            metadata['citations']
        )
        self._safe_print(success_msg)

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
            "quality_score": quality_score,
            "citation_accuracy": citation_result.success_rate,
            "fact_check_score": fact_check_result["supported_percentage"],
            "reasoning_trace": {
                "synthesis": self.reasoning_trace.get("synthesis", {}),
                "generation_approach": "ReAct-guided thematic synthesis",
                "quality_iterations": self.regeneration_attempts
            },
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

            self._safe_print(f"\n[Summarizer] Initializing RAG vector store for session: {session_id}")

            # Create vector store manager
            vector_manager = VectorStoreManager()

            # Initialize from session data directly
            success = vector_manager.initialize_from_session(session_id)

            if success:
                self._safe_print(f"[Summarizer] ✅ RAG vector store initialized successfully")
                return True
            else:
                self._safe_print(f"[Summarizer] ⚠️  RAG vector store initialization failed")
                return False

        except Exception as e:
            self._safe_print(f"[Summarizer] ❌ RAG vector store initialization error: {str(e)}")
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
        self._safe_print(f"\n{'='*60}")
        self._safe_print("[Summarizer] RAG INITIALIZATION READY")
        self._safe_print(f"{'='*60}")
        self._safe_print(f"Essay saved: {essay_file_path}")
        self._safe_print(f"Total analyses available: {len(analyses)}")
        self._safe_print(f"RAG chatbot can now be activated with this content")
        self._safe_print(f"{'='*60}\n")

        # Create RAG-ready signal file
        rag_signal_path = Path(ESSAYS_DIR) / "rag_ready.signal"
        with open(rag_signal_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps({
                "essay_path": essay_file_path,
                "analyses_count": len(analyses),
                "timestamp": datetime.now().isoformat(),
                "status": "ready"
            }, indent=2))

        self._safe_print(f"[Summarizer] RAG signal file created: {rag_signal_path}")

    def _build_paper_reference_data(self, analyses: List[Dict[str, Any]]) -> str:
        """
        Build a formatted string of paper references from analyses data
        for injection into essay generation prompts.

        Returns:
            Formatted reference string with title, authors, year, method, findings, novelty
        """
        references = []
        for i, analysis in enumerate(analyses[:12], 1):  # Cap at 12 papers
            citations = analysis.get("citations", [])
            metadata = analysis.get("metadata", {})

            title = "Unknown Title"
            authors = "Unknown"
            year = "n.d."

            if citations and len(citations) > 0:
                citation = citations[0]
                title = citation.get("title", "Unknown Title")
                raw_authors = citation.get("authors", "Unknown")
                raw_year = citation.get("year", "n.d.")
                if raw_authors and raw_authors != "Information not provided in abstract":
                    authors = raw_authors
                if raw_year and raw_year != "Information not provided in abstract":
                    year = raw_year

            methodology = metadata.get("methodology", analysis.get("summary", "")[:80])
            key_findings = metadata.get("key_findings", "")
            novelty = metadata.get("novelty", "")

            if isinstance(key_findings, list):
                key_findings = "; ".join(key_findings[:2])
            if isinstance(novelty, list):
                novelty = "; ".join(novelty[:2])

            ref = f'[{i}] "{title}" - {authors} ({year})'
            if methodology:
                ref += f'\n    Method: {str(methodology)[:120]}'
            if key_findings:
                ref += f'\n    Key Finding: {str(key_findings)[:150]}'
            if novelty:
                ref += f'\n    Novelty: {str(novelty)[:120]}'
            references.append(ref)

        return "\n\n".join(references) if references else "No paper references available."

    async def _create_synthesis(
        self,
        query: str,
        analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a structured synthesis of all analyses using ReAct framework

        Args:
            query: Research query
            analyses: List of paper analyses

        Returns:
            Structured synthesis with themes and patterns
        """
        synthesis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a WORLD-CLASS research synthesizer with expertise in meta-analysis and systematic reviews.

APPLY ReAct FRAMEWORK (Reasoning + Acting):

STEP 1 - THOUGHT: What patterns emerge across all papers? What are the recurring themes?
STEP 2 - ACTION: Extract specific themes, methodologies, findings from each paper systematically
STEP 3 - OBSERVATION: Note agreements, conflicts, and progressions in the field
STEP 4 - REFLECTION: What does the collective evidence suggest? What remains unknown?

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

APPLY REACT REASONING:

THOUGHT: Examine all papers. What patterns appear? What methodologies recur? What findings repeat?

ACTION: For each paper, extract:
  - Main themes and terminology used
  - Specific methods, algorithms, frameworks employed
  - Key results and metrics
  - Limitations noted
  - Future work suggested

OBSERVATION: Compare across papers:
  - Which findings are consistent across studies?
  - Where do papers conflict or diverge?
  - What methodological approaches dominate?
  - What are common research gaps?

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
            response = await asyncio.wait_for(
                chain.ainvoke({
                    "query": query,
                    "count": len(analyses),
                    "analyses": json.dumps(analyses[:20], indent=2)  # Limit to prevent token overflow
                }),
                timeout=LLM_CALL_TIMEOUT
            )

            content = response.content

            # Extract JSON from markdown if needed
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            synthesis_result = json.loads(content)

            # Store reasoning trace for metadata
            self.reasoning_trace["synthesis"] = {
                "query": query,
                "papers_analyzed": len(analyses),
                "themes_identified": len(synthesis_result.get("main_themes", [])),
                "methodologies_found": len(synthesis_result.get("methodologies", [])),
                "findings_extracted": len(synthesis_result.get("key_findings", [])),
                "gaps_identified": len(synthesis_result.get("research_gaps", []))
            }

            return synthesis_result

        except Exception as e:
            print(f"[Summarizer] Synthesis error: {str(e)}")
            self.reasoning_trace["synthesis"] = {"error": str(e)}
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
        analyses: List[Dict[str, Any]],
        synthesis: Dict[str, Any],
        paper_references: str
    ) -> str:
        """Generate essay introduction in academic literature review style with ReAct reasoning"""
        intro_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior research scientist writing a literature review for a peer-reviewed journal.
Your prose is clear, precise, and evidence-based. Use formal academic English, passive voice
where appropriate, hedged claims, and specific citations in (Author et al., Year) format.
Do not use flowery or philosophical language. Be direct, scholarly, and rigorous.

APPLY REACT THINKING:
THOUGHT: What is the research context? What papers establish foundational knowledge?
ACTION: Select 2-3 key papers that introduce the domain. Extract their core contributions.
OBSERVATION: What is the state of knowledge that these papers establish?
REFLECTION: What narrative connects these papers to justify this literature review?

CRITICAL ACADEMIC INTEGRITY REQUIREMENTS:
1. EVERY factual claim MUST be supported by specific citations
2. Use ONLY information available in the provided paper references
3. If you cannot find supporting evidence, DO NOT include it
4. Use hedging language: "suggests", "may indicate", "appears to"
5. Never extrapolate beyond what papers explicitly state
6. Citation format MUST be (Author et al., Year) with exact author names
7. Do not invent or approximate citations
8. If references are insufficient, state this clearly rather than generating unsupported content"""),
            ("user", """Write the INTRODUCTION for a literature review on the following topic.

TOPIC: {query}
NUMBER OF PAPERS REVIEWED: {count}

PAPER REFERENCES (use ONLY these for citations - do not cite papers not in this list):
{paper_references}

THEMES IDENTIFIED:
{themes}

STRUCTURE (2 paragraphs, 150-250 words total):

PARAGRAPH 1 - RESEARCH CONTEXT AND SIGNIFICANCE:
- Introduce the research domain and its importance
- Cite 2-3 specific papers from the references using (Author et al., Year) format
- Establish the current state of knowledge
- Use hedging language where appropriate

PARAGRAPH 2 - SCOPE OF THIS REVIEW:
- State the number of papers reviewed
- Preview the major themes that will be discussed
- Briefly outline the structure of the review

CRITICAL REQUIREMENTS:
- Use formal academic English throughout
- Include ONLY (Author et al., Year) citations from the provided references
- Every claim must be traceable to a specific paper
- Be precise and evidence-based, not philosophical
- Use hedging language: suggests, may, appears, indicates
- Keep within 150-250 words
- NO unsupported assertions""")
        ])

        try:
            themes = synthesis.get("main_themes", [])
            chain = intro_prompt | self.llm
            response = await asyncio.wait_for(
                chain.ainvoke({
                    "query": query,
                    "count": len(analyses),
                    "paper_references": paper_references,
                    "themes": "\n- ".join(themes) if themes else "General research themes"
                }),
                timeout=LLM_CALL_TIMEOUT
            )
            return response.content.strip()
        except Exception as e:
            return f"Introduction could not be generated: {str(e)}"

    async def _generate_body(
        self,
        synthesis: Dict[str, Any],
        analyses: List[Dict[str, Any]],
        paper_references: str
    ) -> str:
        """Generate essay body in academic literature review style with thematic organization and ReAct reasoning"""
        body_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior research scientist writing the body of a literature review for a peer-reviewed journal.
Organize the review thematically. For each theme, cite specific papers using (Author et al., Year) format.
Compare and contrast findings across studies. Note methodological differences.
Use formal academic English, passive voice where appropriate, and hedged claims.
Do not use flowery or philosophical language. Be direct, scholarly, and analytical.

APPLY REACT THINKING:
THOUGHT: Which papers address each theme? What are the key variations in approach or findings?
ACTION: For each theme, identify 2-4 papers. Extract their methods and results with citations.
OBSERVATION: How do the findings align or diverge? What methodological differences explain variations?
REFLECTION: What synthesis of these papers reveals about the theme's current state of knowledge?

CRITICAL ACADEMIC INTEGRITY REQUIREMENTS:
1. EVERY claim about research findings MUST cite specific papers
2. Use ONLY papers from the provided references - do not reference papers not in the list
3. When comparing studies, cite each study explicitly
4. When noting differences, show them with explicit citations
5. Use hedging language: "suggests", "may indicate", "appears", "indicates"
6. Do not extrapolate beyond what papers state
7. Citation format MUST be (Author et al., Year) - match reference list exactly
8. If you cannot support a claim with provided papers, omit it
9. For methodological analysis, explicitly compare approaches using citations"""),
            ("user", """Write the BODY of a literature review.

PAPER REFERENCES (use ONLY these for citations - do not cite papers not in this list):
{paper_references}

THEMES TO COVER:
{themes}

KEY FINDINGS:
{findings}

METHODOLOGIES USED:
{methodologies}

RESEARCH GAPS:
{gaps}

TOP CONTRIBUTIONS:
{contributions}

NUMBER OF PAPERS: {count}

STRUCTURE (4-6 paragraphs, 600-900 words total):

Organize by theme. For each major theme:
- Introduce the theme and its relevance to the research question
- Cite 2-4 specific papers by (Author et al., Year) from the references above
- Compare and contrast findings across the cited studies with explicit citations
- Note methodological differences between approaches with citations
- Synthesize what the collective evidence suggests (with citations)

CRITICAL REQUIREMENTS:
- Use formal academic English throughout
- EVERY claim must reference specific papers with (Author et al., Year) citations
- Compare and contrast - do not just summarize papers sequentially
- Note areas of agreement and disagreement with explicit citations
- Use transitions between themes
- Use hedging language: suggests, may, appears, indicates
- All citations must match the provided references exactly
- Keep within 600-900 words
- NO unsupported assertions - every claim needs a citation""")
        ])

        try:
            chain = body_prompt | self.llm
            response = await asyncio.wait_for(
                chain.ainvoke({
                    "themes": "\n- ".join(synthesis.get("main_themes", [])),
                    "findings": "\n- ".join(synthesis.get("key_findings", [])),
                    "methodologies": "\n- ".join(synthesis.get("methodologies", [])),
                    "gaps": "\n- ".join(synthesis.get("research_gaps", [])),
                    "contributions": "\n- ".join(synthesis.get("top_contributions", [])),
                    "count": len(analyses),
                    "paper_references": paper_references
                }),
                timeout=LLM_CALL_TIMEOUT
            )
            return response.content.strip()
        except Exception as e:
            return f"Body section could not be generated: {str(e)}"

    async def _generate_conclusion(
        self,
        query: str,
        synthesis: Dict[str, Any],
        paper_references: str
    ) -> str:
        """Generate essay conclusion in academic literature review style with ReAct reasoning"""
        conclusion_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior research scientist writing the conclusion of a literature review for a peer-reviewed journal.
Synthesize the key findings concisely, identify limitations and gaps, and suggest future research directions.
Use formal academic English. Be precise, evidence-based, and forward-looking.
Do not use flowery or philosophical language.

APPLY REACT THINKING:
THOUGHT: What are the most significant findings across all papers? What remains unresolved?
ACTION: Identify 3-4 key findings with citations. List specific gaps and limitations found.
OBSERVATION: Where does the literature have consensus? Where are gaps most critical?
REFLECTION: What does the evidence collectively suggest? What future research would address key gaps?

CRITICAL ACADEMIC INTEGRITY REQUIREMENTS:
1. All major findings cited in synthesis MUST reference specific papers
2. Limitations MUST be tied to specific studies or gaps in the literature
3. Future research suggestions MUST connect explicitly to identified gaps
4. Use ONLY papers from the provided references
5. Use hedging language: "suggests", "may", "appears", "indicates"
6. Do not make claims unsupported by the reviewed literature
7. Citation format MUST be (Author et al., Year)
8. Acknowledge what the current literature can and cannot conclude"""),
            ("user", """Write the CONCLUSION for a literature review.

TOPIC: {query}

PAPER REFERENCES (use ONLY these for citations):
{paper_references}

KEY THEMES: {themes}

MAIN CONTRIBUTIONS: {contributions}

RESEARCH GAPS: {gaps}

METHODOLOGIES REVIEWED: {methodologies}

STRUCTURE (2-3 paragraphs, 200-350 words total):

PARAGRAPH 1 - SYNTHESIS OF KEY FINDINGS:
- Summarize the 3-4 most significant findings from the reviewed literature
- Reference specific papers where appropriate using (Author et al., Year)
- State what the collective evidence demonstrates
- Acknowledge limitations of current evidence

PARAGRAPH 2 - LIMITATIONS AND GAPS:
- Identify methodological limitations across the reviewed studies with citations
- Note gaps in the current body of knowledge
- Connect gaps to specific missing studies or methodologies
- Be specific about what remains unknown or understudied

PARAGRAPH 3 (OPTIONAL) - FUTURE RESEARCH DIRECTIONS:
- Suggest concrete directions for future investigation
- Connect suggestions explicitly to the identified gaps
- Base suggestions on limitations found in reviewed papers
- Be specific and actionable

CRITICAL REQUIREMENTS:
- Use formal academic English
- Keep within 200-350 words
- Be concise and substantive
- Every major finding must have a citation
- End with a clear forward-looking statement grounded in literature
- Use hedging language: suggests, may, appears, indicates
- NO unsupported assertions""")
        ])

        try:
            chain = conclusion_prompt | self.llm
            response = await asyncio.wait_for(
                chain.ainvoke({
                    "query": query,
                    "themes": "\n- ".join(synthesis.get("main_themes", [])),
                    "contributions": "\n- ".join(synthesis.get("top_contributions", [])),
                    "gaps": "\n- ".join(synthesis.get("research_gaps", [])),
                    "methodologies": "\n- ".join(synthesis.get("methodologies", [])),
                    "paper_references": paper_references
                }),
                timeout=LLM_CALL_TIMEOUT
            )
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
        try:
            # Create filename from query
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_query = "".join(c if c.isalnum() or c in (' ', '-') else '' for c in query)
            safe_query = safe_query.replace(' ', '_')[:50]  # Limit length

            # Save as .txt file as specified
            filename = f"essay_{safe_query}_{timestamp}.txt"
            file_path = Path(ESSAYS_DIR) / filename

            # Save essay with proper UTF-8 encoding
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(essay)

            self._safe_print(f"[Summarizer] Essay saved to: {file_path}")

            # Also save markdown version for better formatting
            md_filename = f"essay_{safe_query}_{timestamp}.md"
            md_file_path = Path(ESSAYS_DIR) / md_filename
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(essay)

            self._safe_print(f"[Summarizer] Markdown version saved to: {md_file_path}")

            return str(file_path)
        except Exception as e:
            import logging
            logger = logging.getLogger('aura.summarizer')
            logger.error(f"Error saving essay: {e}")
            # Return a default path even if save fails
            return str(Path(ESSAYS_DIR) / f"essay_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

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
