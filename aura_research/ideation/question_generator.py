"""
Research Question Generator for AURA
Generates intelligent, novel research questions from completed research analyses
"""

from typing import Dict, Any, List
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import json
from ..utils.config import OPENAI_API_KEY, GPT_MODEL


class QuestionGenerator:
    """
    Generates research questions from research session data
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model=GPT_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=0.7  # Higher for creativity
        )

        # Question type templates
        self.question_types = {
            "exploratory": "What is the relationship between {concept_a} and {concept_b}?",
            "explanatory": "Why does {concept_a} lead to {concept_b}?",
            "comparative": "How do {concept_a} and {concept_b} differ in their effects on {concept_c}?",
            "predictive": "Can {concept_a} predict {concept_b} better than {concept_c}?",
            "evaluative": "How effective is {concept_a} for achieving {concept_b}?",
            "design": "How can we design {concept_a} to optimize {concept_b}?",
            "causal": "What is the causal mechanism between {concept_a} and {concept_b}?",
            "integrative": "How can {concept_a} and {concept_b} be integrated to address {concept_c}?"
        }

    async def generate_questions(
        self,
        session_data: Dict[str, Any],
        num_questions: int = 15,
        include_gaps: bool = True
    ) -> Dict[str, Any]:
        """
        Generate research questions from a research session

        Args:
            session_data: Complete research session results
            num_questions: Number of questions to generate
            include_gaps: Whether to identify gaps first

        Returns:
            Dictionary with questions, gaps, and metadata
        """
        # Extract research summary
        research_summary = self._extract_research_summary(session_data)

        # Identify research gaps
        gaps = []
        if include_gaps:
            gaps = await self._identify_gaps(research_summary)

        # Generate questions for each gap
        questions = await self._generate_questions_from_gaps(
            research_summary,
            gaps,
            num_questions
        )

        # Score and rank questions
        scored_questions = await self._score_questions(questions, research_summary)

        return {
            "query": session_data.get("query", "Unknown"),
            "gaps_identified": gaps,
            "questions": scored_questions,
            "total_questions": len(scored_questions),
            "research_summary": research_summary
        }

    def _extract_research_summary(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key information from research session"""
        summary = {
            "query": session_data.get("query", ""),
            "total_papers": session_data.get("total_papers", 0),
            "papers_analyzed": session_data.get("papers_analyzed", 0),
            "key_concepts": [],
            "methodologies": [],
            "findings": [],
            "domains": []
        }

        # Extract from subordinate results
        subordinate_results = session_data.get("subordinate_results", [])

        for result in subordinate_results:
            if result.get("status") == "completed":
                analyses = result.get("result", {}).get("analyses", [])

                for analysis in analyses:
                    metadata = analysis.get("metadata", {})

                    # Collect concepts
                    core_ideas = metadata.get("core_ideas", [])
                    summary["key_concepts"].extend(core_ideas)

                    # Collect methodologies
                    methodology = metadata.get("methodology", "")
                    if methodology:
                        summary["methodologies"].append(methodology)

                    # Collect findings
                    key_findings = metadata.get("key_findings", [])
                    summary["findings"].extend(key_findings)

                    # Collect domains
                    domain = metadata.get("research_domain", "")
                    if domain and domain != "Unknown":
                        summary["domains"].append(domain)

        # Deduplicate
        summary["key_concepts"] = list(set(summary["key_concepts"]))[:10]
        summary["domains"] = list(set(summary["domains"]))

        return summary

    async def _identify_gaps(self, research_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify research gaps from the literature

        Returns:
            List of identified gaps with types and descriptions
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an EXPERT research strategist with a PhD and extensive publication record.

Your task is to identify SPECIFIC, ACTIONABLE research gaps from a literature review.

CRITICAL REQUIREMENTS:
1. Gaps must be SPECIFIC and CONCRETE (not vague like "more research needed")
2. Each gap should be FEASIBLE to address in a research project
3. Identify gaps across multiple dimensions:
   - Methodological gaps (methods not yet applied)
   - Theoretical gaps (theories not yet integrated)
   - Empirical gaps (populations/contexts not yet studied)
   - Practical gaps (applications not yet explored)
   - Integration gaps (fields/concepts not yet connected)

4. For each gap, provide:
   - Type (methodological/theoretical/empirical/practical/integration)
   - Clear description (2-3 sentences)
   - Why it matters (significance)
   - Feasibility estimate (easy/moderate/challenging)

OUTPUT FORMAT: Return ONLY valid JSON, no markdown.
"""),
            ("user", """Analyze this research summary and identify 5-8 SPECIFIC research gaps:

RESEARCH QUERY: {query}

KEY CONCEPTS FOUND:
{concepts}

METHODOLOGIES USED:
{methodologies}

KEY FINDINGS:
{findings}

RESEARCH DOMAINS:
{domains}

Identify gaps that are:
1. Not addressed by existing papers
2. Potentially high-impact
3. Feasible to research
4. Specific and actionable

Return JSON in this EXACT format:
{{
    "gaps": [
        {{
            "id": "gap_1",
            "type": "methodological|theoretical|empirical|practical|integration",
            "title": "Brief title of the gap",
            "description": "Specific description of what is missing (2-3 sentences)",
            "significance": "Why this gap matters and what impact filling it would have",
            "feasibility": "easy|moderate|challenging",
            "potential_impact": "high|medium|low"
        }}
    ]
}}""")
        ])

        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "query": research_summary.get("query", "Unknown"),
                "concepts": "\n".join(f"- {c}" for c in research_summary.get("key_concepts", [])[:10]),
                "methodologies": "\n".join(f"- {m[:200]}" for m in research_summary.get("methodologies", [])[:5]),
                "findings": "\n".join(f"- {f}" for f in research_summary.get("findings", [])[:10]),
                "domains": ", ".join(research_summary.get("domains", ["General"]))
            })

            content = response.content

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)
            return result.get("gaps", [])

        except Exception as e:
            print(f"Error identifying gaps: {str(e)}")
            # Return default gaps
            return [{
                "id": "gap_1",
                "type": "empirical",
                "title": "Further empirical validation needed",
                "description": "Current research could benefit from additional empirical studies in diverse contexts.",
                "significance": "Would strengthen the generalizability of findings",
                "feasibility": "moderate",
                "potential_impact": "medium"
            }]

    async def _generate_questions_from_gaps(
        self,
        research_summary: Dict[str, Any],
        gaps: List[Dict[str, Any]],
        num_questions: int
    ) -> List[Dict[str, Any]]:
        """
        Generate specific research questions from identified gaps
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a WORLD-CLASS research question designer with expertise in crafting impactful, innovative research questions.

Your task is to generate EXCELLENT research questions that:
1. Are SPECIFIC and TESTABLE (can actually be researched)
2. Are NOVEL (not already answered in the literature)
3. Are CLEAR and WELL-SCOPED (not too broad or too narrow)
4. Have SIGNIFICANT POTENTIAL IMPACT
5. Are FEASIBLE to investigate

QUESTION TYPES TO USE:
- Exploratory: "What is the relationship between X and Y?"
- Explanatory: "Why does X lead to Y?" / "What mechanisms explain X?"
- Comparative: "How do X and Y differ in their effects on Z?"
- Predictive: "Can X predict Y?" / "To what extent does X influence Y?"
- Evaluative: "How effective is X for achieving Y?"
- Design: "How can we design/optimize X to achieve Y?"
- Causal: "What is the causal effect of X on Y?"
- Integrative: "How can theories/methods from X and Y be combined?"

CRITICAL QUALITY CRITERIA:
✓ Use specific terms from the research domain (no generic placeholders)
✓ Include measurable/observable constructs
✓ Scope appropriately (not "all contexts" but specific contexts)
✓ Imply a clear methodology
✓ Build on existing knowledge while advancing it

OUTPUT: Return ONLY valid JSON, no markdown."""),
            ("user", """Generate {num_questions} HIGH-QUALITY research questions based on these gaps:

RESEARCH QUERY: {query}

IDENTIFIED GAPS:
{gaps}

KEY CONCEPTS FROM LITERATURE:
{concepts}

RESEARCH DOMAINS:
{domains}

For each question, provide:
- The question itself (clear, specific, testable)
- Question type (exploratory/explanatory/comparative/predictive/evaluative/design/causal/integrative)
- Which gap it addresses
- Rationale (why this question matters)
- Suggested methodology approach
- Expected novelty (what's new)
- Scope (specific context/population/setting)

Return JSON in this EXACT format:
{{
    "questions": [
        {{
            "id": "q_1",
            "question": "The actual research question (specific and testable)",
            "type": "exploratory|explanatory|comparative|predictive|evaluative|design|causal|integrative",
            "addresses_gap": "gap_id from the gaps provided",
            "rationale": "Why this question is important and what it would contribute",
            "methodology_suggestion": "Brief description of how this could be studied",
            "novelty": "What makes this question novel/innovative",
            "scope": "Specific context, population, or setting for the study",
            "variables": ["key variable 1", "key variable 2", "key variable 3"]
        }}
    ]
}}

Generate questions that span different types and address multiple gaps.""")
        ])

        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "num_questions": num_questions,
                "query": research_summary.get("query", "Unknown"),
                "gaps": json.dumps(gaps, indent=2),
                "concepts": ", ".join(research_summary.get("key_concepts", [])[:15]),
                "domains": ", ".join(research_summary.get("domains", ["General"]))
            })

            content = response.content

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)
            return result.get("questions", [])

        except Exception as e:
            print(f"Error generating questions: {str(e)}")
            return []

    async def _score_questions(
        self,
        questions: List[Dict[str, Any]],
        research_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Score and rank questions by quality criteria
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert research evaluator who scores research questions on multiple criteria.

Score each question on a scale of 1-10 for:
1. NOVELTY: How original/innovative is this question?
2. FEASIBILITY: How practical is it to actually research this?
3. CLARITY: How clear and well-defined is the question?
4. IMPACT: What is the potential impact of answering this question?
5. SPECIFICITY: How specific and testable is the question?

Return ONLY valid JSON, no markdown."""),
            ("user", """Score these research questions:

{questions}

Return JSON in this EXACT format:
{{
    "scored_questions": [
        {{
            "question_id": "q_1",
            "scores": {{
                "novelty": 8,
                "feasibility": 7,
                "clarity": 9,
                "impact": 8,
                "specificity": 8
            }},
            "overall_score": 8.0,
            "strengths": ["strength 1", "strength 2"],
            "potential_challenges": ["challenge 1", "challenge 2"]
        }}
    ]
}}""")
        ])

        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "questions": json.dumps(questions, indent=2)
            })

            content = response.content

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)
            scores_by_id = {
                item["question_id"]: item
                for item in result.get("scored_questions", [])
            }

            # Merge scores with questions
            for question in questions:
                q_id = question.get("id", "")
                if q_id in scores_by_id:
                    question["scores"] = scores_by_id[q_id].get("scores", {})
                    question["overall_score"] = scores_by_id[q_id].get("overall_score", 0)
                    question["strengths"] = scores_by_id[q_id].get("strengths", [])
                    question["potential_challenges"] = scores_by_id[q_id].get("potential_challenges", [])
                else:
                    question["scores"] = {
                        "novelty": 5,
                        "feasibility": 5,
                        "clarity": 5,
                        "impact": 5,
                        "specificity": 5
                    }
                    question["overall_score"] = 5.0

            # Sort by overall score
            questions.sort(key=lambda q: q.get("overall_score", 0), reverse=True)

            return questions

        except Exception as e:
            print(f"Error scoring questions: {str(e)}")
            # Return questions with default scores
            for question in questions:
                question["scores"] = {
                    "novelty": 5,
                    "feasibility": 5,
                    "clarity": 5,
                    "impact": 5,
                    "specificity": 5
                }
                question["overall_score"] = 5.0
            return questions

    async def refine_question(
        self,
        question: str,
        feedback: str,
        research_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Refine a research question based on user feedback

        Args:
            question: Original research question
            feedback: User's feedback or refinement request
            research_context: Context from research summary

        Returns:
            Refined question with alternatives
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert research question consultant.

Your task is to refine research questions based on user feedback while maintaining:
- Specificity and clarity
- Testability
- Novelty
- Appropriate scope

Provide 3 refined variations of the question."""),
            ("user", """Refine this research question based on the feedback:

ORIGINAL QUESTION: {question}

USER FEEDBACK: {feedback}

RESEARCH CONTEXT: {context}

Return JSON with 3 refined variations:
{{
    "refined_questions": [
        {{
            "question": "Refined version 1",
            "rationale": "Why this refinement addresses the feedback",
            "changes_made": "What was changed and why"
        }},
        {{
            "question": "Refined version 2",
            "rationale": "Why this refinement addresses the feedback",
            "changes_made": "What was changed and why"
        }},
        {{
            "question": "Refined version 3",
            "rationale": "Why this refinement addresses the feedback",
            "changes_made": "What was changed and why"
        }}
    ]
}}""")
        ])

        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "question": question,
                "feedback": feedback,
                "context": json.dumps(research_context, indent=2)
            })

            content = response.content

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)

        except Exception as e:
            print(f"Error refining question: {str(e)}")
            return {
                "refined_questions": [{
                    "question": question,
                    "rationale": "Original question maintained",
                    "changes_made": "No changes due to processing error"
                }]
            }
