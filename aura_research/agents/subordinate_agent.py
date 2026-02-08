"""
Subordinate (Analyst) Agent for AURA
Analyzes assigned research papers and extracts key information
"""

from typing import Dict, Any, List
import asyncio
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from openai import RateLimitError, APIError
from .base_agent import BaseAgent, AgentStatus
from ..utils.config import OPENAI_API_KEY, GPT_MODEL, LLM_CALL_TIMEOUT
import json

# Setup logger
logger = logging.getLogger('aura.agents')

# Rate limit retry configuration
MAX_RETRIES = 3
BASE_WAIT_TIME = 60  # seconds


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
            temperature=0.2  # Lower for more precision and consistency
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
            ("system", """You are an ELITE research analyst with PhD-level expertise. Your analysis must be METICULOUS, PRECISE, and SUBSTANTIVE.

CRITICAL REQUIREMENTS:
1. NEVER use generic placeholders like "Main contribution 1" or "Key finding 1"
2. Extract SPECIFIC, CONCRETE information from the paper
3. If information is missing, state "Information not provided in abstract" - DO NOT fabricate
4. Be scholarly, detailed, and precise
5. Think deeply before writing - quality over speed

ANALYSIS FRAMEWORK (ReAct - Reasoning + Acting):

STEP 1 - DEEP READING:
- Read the title and abstract 3 times
- Identify the core research question
- Understand the specific problem being addressed

STEP 2 - CRITICAL THINKING:
- What SPECIFIC claims does this paper make?
- What SPECIFIC methods/approaches are used?
- What SPECIFIC results/findings are presented?
- What makes this research UNIQUE or NOVEL?

STEP 3 - VERIFICATION:
- Can you point to exact phrases from the abstract?
- Are you making inferences or stating facts?
- Is every claim backed by the source material?

STEP 4 - SCHOLARLY SYNTHESIS:
- Synthesize findings in academic language
- Maintain objectivity and precision
- Highlight genuine contributions

OUTPUT REQUIREMENTS:
- Summary: 3-4 sentences with SPECIFIC details from the paper
- Key Points: 5-7 SPECIFIC insights (not generic templates)
- Each point must reference actual content from the abstract
- Use scholarly language with precision
- Extract author names and publication year if mentioned ANYWHERE in the text"""),
            ("user", """ANALYZE THIS RESEARCH PAPER WITH EXTREME PRECISION:

═══════════════════════════════════════════════════════════
TITLE: {title}

ABSTRACT/DESCRIPTION: {snippet}

SOURCE URL: {link}

PUBLICATION INFO: {pub_info}
═══════════════════════════════════════════════════════════

MANDATORY ANALYSIS STEPS:

1. THOUGHT (Deep Reading):
   - What is the EXACT research question or objective?
   - What specific problem does this address?
   - What domain/field is this research in?

2. ACTION (Information Extraction):
   - Extract SPECIFIC methodologies mentioned
   - Extract SPECIFIC findings or results stated
   - Extract SPECIFIC contributions claimed
   - Extract author names if visible in title format (e.g., "Smith et al.")
   - Extract publication year from any source

3. OBSERVATION (Critical Analysis):
   - What are the CONCRETE findings (use exact terms from abstract)?
   - What techniques/algorithms/methods are named?
   - What datasets, experiments, or case studies are mentioned?
   - What metrics or measurements are reported?

4. REFLECTION (Scholarly Assessment):
   - What makes this research novel? (Be specific)
   - What are potential limitations? (Based on what's stated/not stated)
   - How does this advance the field? (Concrete ways)
   - What gaps remain?

OUTPUT IN THIS EXACT JSON FORMAT:
{{
    "summary": "A detailed 3-4 sentence scholarly summary that includes: (1) the specific research problem, (2) the specific methods/approach used, (3) the specific key findings or contributions, and (4) the significance. Use ONLY information from the abstract - be precise and detailed.",

    "key_points": [
        "First SPECIFIC contribution or finding with concrete details from the abstract",
        "Second SPECIFIC contribution - name actual techniques, methods, or approaches mentioned",
        "Third SPECIFIC finding - include metrics, improvements, or results if stated",
        "Fourth SPECIFIC insight about methodology or experimental approach",
        "Fifth SPECIFIC novelty - what exactly is new compared to prior work",
        "Sixth SPECIFIC implication or application domain mentioned",
        "Seventh SPECIFIC limitation or future direction if discussed"
    ],

    "citations": [
        {{
            "title": "{title}",
            "authors": "Extract from title format (e.g., 'Smith et al.') OR from publication info OR 'Information not provided in abstract'",
            "year": "Extract from publication info OR title OR 'Information not provided in abstract'",
            "source": "{link}"
        }}
    ],

    "metadata": {{
        "core_ideas": ["Specific idea 1 from paper", "Specific idea 2 from paper", "Specific idea 3 from paper"],
        "methodology": "Detailed description of the EXACT methods/approach mentioned in the abstract (100+ words if possible, be thorough)",
        "key_findings": ["Specific finding 1 with details", "Specific finding 2 with details", "Specific finding 3 with details"],
        "novelty": "Precise description of what is NEW in this work - reference specific innovations, techniques, or insights mentioned (50+ words)",
        "limitations": ["Specific limitation 1 based on what's not addressed", "Specific limitation 2", "Specific gap noted"],
        "relevance_score": (1-10 based on: novelty + methodological rigor + impact + clarity),
        "reasoning": "Your complete ReAct thought process: what you read, what you extracted, how you verified it, and why you scored it this way (150+ words)",
        "research_domain": "Specific field/subfield (e.g., 'Natural Language Processing', 'Computer Vision', 'Reinforcement Learning')",
        "technical_depth": "Assessment of technical sophistication: 'theoretical', 'applied', 'empirical', or 'survey'",
        "real_content_extracted": true
    }}
}}

CRITICAL REMINDERS:
- NO generic templates - every word must be specific to THIS paper
- If abstract lacks detail, state that clearly but extract what IS there
- Use exact terminology from the paper
- Be scholarly and precise
- Quality and accuracy over everything else""")
        ])

        # Retry loop for rate limit handling
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Analyzing paper: {paper.get('title', 'Unknown')[:50]}...")

                # Run LLM analysis with timeout
                chain = prompt | self.llm
                response = await asyncio.wait_for(
                    chain.ainvoke({
                        "title": paper.get("title", "Unknown"),
                        "snippet": paper.get("snippet", "No description available"),
                        "link": paper.get("link", ""),
                        "pub_info": str(paper.get("publication_info", ""))
                    }),
                    timeout=LLM_CALL_TIMEOUT
                )

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

                logger.info(f"Successfully analyzed paper: {paper.get('title', 'Unknown')[:50]}")
                return analysis

            except asyncio.TimeoutError as e:
                last_error = e
                logger.error(f"LLM call timed out after {LLM_CALL_TIMEOUT}s for paper: {paper.get('title', 'Unknown')[:50]}")
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying timed-out analysis...")
                    await asyncio.sleep(2)
                else:
                    break

            except RateLimitError as e:
                last_error = e
                wait_time = BASE_WAIT_TIME * (attempt + 1)
                logger.warning(
                    f"OpenAI rate limit hit (attempt {attempt + 1}/{MAX_RETRIES}). "
                    f"Waiting {wait_time}s before retry..."
                )
                await asyncio.sleep(wait_time)

            except APIError as e:
                last_error = e
                logger.error(f"OpenAI API error: {e}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = 10 * (attempt + 1)
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    break

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"JSON parsing error: {e}. Retrying...")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2)
                else:
                    break

            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error analyzing paper: {e}")
                break

        # Fallback structure after all retries failed
        error_msg = str(last_error) if last_error else "Unknown error"
        logger.error(f"Failed to analyze paper after {MAX_RETRIES} attempts: {error_msg}")

        return {
            "summary": f"Unable to fully analyze: {paper.get('title', 'Unknown')}. Error: {error_msg}",
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
                "reasoning": f"Error occurred: {error_msg}",
                "error": error_msg
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
            ("system", """You are a SENIOR research synthesizer with exceptional analytical skills.

Your summary must be:
- SPECIFIC and detailed (not generic)
- Based ONLY on actual findings from the analyses
- Scholarly and precise
- Comprehensive yet concise"""),
            ("user", """SYNTHESIZE these paper analyses into a comprehensive summary:

{analyses}

REQUIREMENTS:
1. Identify 3-5 SPECIFIC common themes across papers (use actual terminology from papers)
2. Highlight major CONCRETE contributions (not generic statements)
3. Note methodological patterns with specific examples
4. Identify research gaps or contradictions
5. Write 4-6 sentences that demonstrate deep understanding

Focus on SUBSTANCE - what did you actually learn from these papers?
Use precise language and specific examples from the analyses.""")
        ])

        for attempt in range(MAX_RETRIES):
            try:
                chain = summary_prompt | self.llm
                response = await asyncio.wait_for(
                    chain.ainvoke({
                        "analyses": json.dumps(analyses, indent=2)
                    }),
                    timeout=LLM_CALL_TIMEOUT
                )

                logger.info(f"Successfully created summary for {len(analyses)} analyses")
                return response.content.strip()

            except asyncio.TimeoutError as e:
                logger.error(f"Summary LLM call timed out after {LLM_CALL_TIMEOUT}s")
                if attempt < MAX_RETRIES - 1:
                    logger.info(f"Retrying summary generation...")
                    await asyncio.sleep(2)
                else:
                    break

            except RateLimitError as e:
                wait_time = BASE_WAIT_TIME * (attempt + 1)
                logger.warning(
                    f"Rate limit hit during summary (attempt {attempt + 1}/{MAX_RETRIES}). "
                    f"Waiting {wait_time}s..."
                )
                await asyncio.sleep(wait_time)

            except Exception as e:
                logger.error(f"Summary generation failed: {e}")
                return f"Summary generation failed: {str(e)}"

        return "Summary generation failed after maximum retries"
