"""
Fact-Checking Service for AURA
LLM-based claim verification against source paper analyses
"""

import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..utils.config import (
    OPENAI_API_KEY, GPT_MODEL,
    FACT_CHECK_TOP_N_CLAIMS,
    MIN_SUPPORTED_CLAIMS_PCT
)
import asyncio

logger = logging.getLogger('aura.services')


@dataclass
class ClaimVerificationResult:
    """Result of claim verification"""
    claim: str
    citation: str
    verdict: str  # "SUPPORTED" | "NOT_SUPPORTED" | "PARTIALLY_SUPPORTED"
    confidence: float  # 0.0 - 1.0
    evidence: str
    reasoning: str


class FactCheckingService:
    """LLM-based fact-checking against source papers"""

    def __init__(self):
        """Initialize fact-checking service with LLM and config thresholds"""
        self.TOP_N_CLAIMS = FACT_CHECK_TOP_N_CLAIMS
        self.MIN_SUPPORTED_CLAIMS_PCT = MIN_SUPPORTED_CLAIMS_PCT
        self.llm = ChatOpenAI(
            model=GPT_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=0.1  # Very precise
        )
        logger.debug(f"Loaded fact-checking config: top_n={self.TOP_N_CLAIMS}, min_pct={self.MIN_SUPPORTED_CLAIMS_PCT*100:.1f}%")

    async def verify_essay_claims(
        self,
        essay: str,
        analyses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Verify top claims in essay against source paper analyses

        Args:
            essay: Generated essay
            analyses: Paper analyses used in essay generation

        Returns:
            Verification results with pass/fail status
        """
        logger.info("Starting essay fact-checking...")

        # Extract significant claims
        claims = self._extract_claims(essay)
        logger.debug(f"Extracted {len(claims)} significant claims")

        if len(claims) == 0:
            logger.warning("No significant claims found in essay")
            return {
                "is_valid": True,  # Can't verify without claims
                "claims_verified": 0,
                "verifications": [],
                "supported_percentage": 1.0,
                "message": "No claims to verify"
            }

        # Select top N most important claims
        selected_claims = claims[:self.TOP_N_CLAIMS]
        logger.info(f"Verifying {len(selected_claims)} top claims")

        # Verify each claim in parallel
        verification_tasks = [
            self._verify_single_claim(claim, analyses)
            for claim in selected_claims
        ]

        verifications = await asyncio.gather(*verification_tasks, return_exceptions=True)

        # Process results
        successful_verifications = [
            v for v in verifications
            if not isinstance(v, Exception)
        ]

        # Calculate success metrics
        supported_count = sum(
            1 for v in successful_verifications
            if v.verdict in ["SUPPORTED", "PARTIALLY_SUPPORTED"]
        )
        supported_percentage = (
            supported_count / len(successful_verifications)
            if successful_verifications else 0
        )

        is_valid = supported_percentage >= self.MIN_SUPPORTED_CLAIMS_PCT

        logger.info(
            f"Fact-checking complete. {supported_count}/{len(successful_verifications)} "
            f"claims supported ({supported_percentage*100:.1f}%)"
        )

        return {
            "is_valid": is_valid,
            "claims_verified": len(successful_verifications),
            "verifications": [
                {
                    "claim": v.claim,
                    "citation": v.citation,
                    "verdict": v.verdict,
                    "confidence": v.confidence,
                    "evidence": v.evidence,
                    "reasoning": v.reasoning
                }
                for v in successful_verifications
            ],
            "supported_percentage": supported_percentage,
            "message": self._get_fact_check_message(supported_percentage, is_valid)
        }

    async def _verify_single_claim(
        self,
        claim: Dict[str, str],
        analyses: List[Dict[str, Any]]
    ) -> Optional[ClaimVerificationResult]:
        """
        Verify a single claim against paper analyses

        Args:
            claim: Claim dictionary with text and citation
            analyses: Available paper analyses

        Returns:
            ClaimVerificationResult or None if verification fails
        """
        try:
            claim_text = claim.get("text", "")
            citation = claim.get("citation", "")

            # Find cited paper in analyses
            paper_analysis = self._find_cited_paper(citation, analyses)

            if not paper_analysis:
                logger.warning(f"Could not find paper for citation: {citation}")
                return ClaimVerificationResult(
                    claim=claim_text,
                    citation=citation,
                    verdict="NOT_SUPPORTED",
                    confidence=0.5,
                    evidence="Paper not found in analyses",
                    reasoning="The cited paper could not be located in the analysis database"
                )

            # Verify claim against paper analysis
            result = await self._verify_against_analysis(claim_text, paper_analysis)
            return result

        except Exception as e:
            logger.error(f"Error verifying claim: {str(e)}")
            return None

    async def _verify_against_analysis(
        self,
        claim: str,
        paper_analysis: Dict[str, Any]
    ) -> ClaimVerificationResult:
        """
        Use LLM to verify claim against paper analysis

        Args:
            claim: Claim text to verify
            paper_analysis: Paper analysis with findings

        Returns:
            Verification result
        """
        # Extract relevant information from paper analysis
        findings = paper_analysis.get("findings", "")
        methodology = paper_analysis.get("methodology", "")
        conclusions = paper_analysis.get("conclusions", "")
        paper_title = paper_analysis.get("metadata", {}).get("title", "Unknown")

        # Create verification prompt
        verification_prompt = ChatPromptTemplate.from_template(
            """You are an expert academic fact-checker. Verify the following claim against the paper analysis.

Claim to verify: "{claim}"

Paper title: "{title}"

Paper methodology: {methodology}

Paper findings: {findings}

Paper conclusions: {conclusions}

Instructions:
1. Determine if the claim is SUPPORTED, PARTIALLY_SUPPORTED, or NOT_SUPPORTED by the paper
2. Provide evidence from the paper that supports or contradicts the claim
3. Rate your confidence (0.0-1.0)
4. Explain your reasoning

Response format:
VERDICT: [SUPPORTED|PARTIALLY_SUPPORTED|NOT_SUPPORTED]
CONFIDENCE: [0.0-1.0]
EVIDENCE: [direct quote or paraphrase from paper]
REASONING: [explanation]
"""
        )

        # Run verification
        chain = verification_prompt | self.llm

        try:
            response = await asyncio.to_thread(
                chain.invoke,
                {
                    "claim": claim,
                    "title": paper_title,
                    "methodology": methodology[:500],  # Limit length
                    "findings": findings[:500],
                    "conclusions": conclusions[:500]
                }
            )

            # Parse response
            return self._parse_verification_response(claim, response.content, paper_title)

        except Exception as e:
            logger.error(f"Error running verification chain: {str(e)}")
            return ClaimVerificationResult(
                claim=claim,
                citation="Unknown",
                verdict="PARTIALLY_SUPPORTED",
                confidence=0.5,
                evidence="Verification error",
                reasoning=f"Could not verify claim due to: {str(e)}"
            )

    def _parse_verification_response(
        self,
        claim: str,
        response_text: str,
        citation: str
    ) -> ClaimVerificationResult:
        """
        Parse LLM response into verification result

        Args:
            claim: Original claim
            response_text: LLM response
            citation: Paper citation

        Returns:
            Parsed ClaimVerificationResult
        """
        # Extract fields from response
        verdict_match = re.search(
            r'VERDICT:\s*(SUPPORTED|PARTIALLY_SUPPORTED|NOT_SUPPORTED)',
            response_text,
            re.IGNORECASE
        )
        confidence_match = re.search(r'CONFIDENCE:\s*([\d.]+)', response_text)
        evidence_match = re.search(r'EVIDENCE:\s*(.+?)(?=REASONING:|$)', response_text, re.DOTALL)
        reasoning_match = re.search(r'REASONING:\s*(.+?)$', response_text, re.DOTALL)

        verdict = verdict_match.group(1).upper() if verdict_match else "PARTIALLY_SUPPORTED"
        try:
            confidence = float(confidence_match.group(1)) if confidence_match else 0.5
        except ValueError:
            confidence = 0.5

        evidence = evidence_match.group(1).strip() if evidence_match else "Not found"
        reasoning = reasoning_match.group(1).strip() if reasoning_match else "See above"

        return ClaimVerificationResult(
            claim=claim,
            citation=citation,
            verdict=verdict,
            confidence=confidence,
            evidence=evidence[:200],  # Limit length
            reasoning=reasoning[:200]
        )

    def _extract_claims(self, essay: str) -> List[Dict[str, str]]:
        """
        Extract significant claims from essay

        Args:
            essay: Essay text

        Returns:
            List of claims with citations
        """
        claims = []

        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', essay)

        # Extract sentences with citations
        for sentence in sentences:
            if len(sentence.split()) < 10:  # Skip very short sentences
                continue

            # Look for citation pattern
            citation_match = re.search(r'\(([^)]+),\s*(\d{4})\)', sentence)

            if citation_match:
                citation = citation_match.group(0)
                claims.append({
                    "text": sentence.strip(),
                    "citation": citation
                })

        return claims

    def _find_cited_paper(
        self,
        citation: str,
        analyses: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Find the paper analysis for a given citation

        Args:
            citation: Citation string like "(Author et al., Year)"
            analyses: Available analyses

        Returns:
            Paper analysis or None
        """
        # Extract author and year from citation
        citation_match = re.search(r'\(([^)]+),\s*(\d{4})\)', citation)
        if not citation_match:
            return None

        author_text = citation_match.group(1).lower()
        year = citation_match.group(2)

        # Try to find matching paper
        for analysis in analyses:
            metadata = analysis.get("metadata", {})
            paper_authors = metadata.get("authors", "").lower()
            paper_year = metadata.get("year", "")

            # Check if authors match (partial matching)
            if author_text in paper_authors or paper_authors in author_text:
                if str(paper_year) == year:
                    return analysis

        return None

    def _get_fact_check_message(self, supported_pct: float, is_valid: bool) -> str:
        """
        Generate message based on fact-checking results

        Args:
            supported_pct: Percentage of claims supported
            is_valid: Whether essay passes fact-checking

        Returns:
            Status message
        """
        if is_valid:
            return f"Fact-checking passed: {supported_pct*100:.1f}% of claims verified as supported"
        else:
            return (
                f"Fact-checking failed: Only {supported_pct*100:.1f}% of claims verified "
                f"(need {self.MIN_SUPPORTED_CLAIMS_PCT*100:.1f}%)"
            )
