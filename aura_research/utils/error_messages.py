"""
User-friendly error messages for AURA quality control system
"""


def get_non_academic_query_error(query: str, category: str, reasoning: str) -> str:
    """Generate error message for non-academic queries"""
    return f"""
❌ Non-Academic Query Detected
{'='*60}

Your query: "{query}"
Detected category: {category}

{reasoning}

AURA is designed for academic research topics such as:
  • Scientific concepts (e.g., "quantum entanglement", "photosynthesis")
  • Research methodologies (e.g., "reinforcement learning", "CRISPR")
  • Biological/medical topics (e.g., "mitochondrial function", "immunology")
  • Engineering & CS topics (e.g., "neural networks", "algorithms")
  • Mathematical concepts (e.g., "calculus", "linear algebra")
  • Peer-reviewed research areas

Examples of Academic Queries (✓ Will Work):
  ✓ "Transformer architecture in natural language processing"
  ✓ "CRISPR gene editing mechanisms and off-target effects"
  ✓ "Attention mechanisms in neural networks"
  ✓ "Mitochondrial dysfunction in aging"
  ✓ "Reinforcement learning with human feedback"

Examples of Non-Academic Queries (✗ Will Not Work):
  ✗ "Tom Cruise filmography"
  ✗ "Isaac Asimov biography"
  ✗ "Best pizza in New York"
  ✗ "iPhone 15 features and reviews"
  ✗ "Tesla stock price"

If you believe this is an academic topic, try rephrasing to be more
specific about the research aspect. For example:
  • Instead of "Tom Cruise" → "Actor biographies in cinema"
  • Instead of "Isaac Asimov" → "Science fiction as prediction"
  • Instead of "Best pizza" → "Flour fermentation in bread baking"

{'='*60}
"""


def get_insufficient_papers_error(count: int, required: int) -> str:
    """Generate error for insufficient papers"""
    return f"""
❌ No Academic Material Available for This Query
{'='*60}

Papers Found: {count}
Papers Required: {required}

The AURA research system requires sufficient validated academic papers
before generating an essay. Your search returned insufficient material
that meets our rigorous quality standards.

Suggestions to Improve Your Search:
  • Try a more specific research question
  • Use different keywords or terminology
  • Combine multiple related concepts
  • Search for broader topic areas
  • Consult a librarian for better search terms

AURA maintains strict quality standards to ensure all essays are
grounded in credible, verified academic sources.

{'='*60}
"""


def get_low_quality_essay_error(score: float, threshold: float, issues: list) -> str:
    """Generate error for low quality essay"""
    issues_text = "\n  • ".join(issues) if issues else "Citation and evidence issues"

    return f"""
❌ Essay Quality Below Academic Standards
{'='*60}

Quality Score: {score:.1f}/10.0
Minimum Required: {threshold:.1f}/10.0

Quality Issues Detected:
  • {issues_text}

The essay did not meet AURA's strict academic rigor standards.
This could be due to:
  - Insufficient or weak citations
  - Unclear or non-academic language
  - Weak structural coherence
  - Unsupported claims
  - Citation formatting errors

What This Means:
The system attempted to regenerate the essay with stricter requirements,
but quality standards could not be met. This suggests the available
source material may not be sufficient for a rigorous essay on this topic.

Recommendations:
  • Try a different research query
  • Search for papers from more recent years
  • Look for papers from highly-cited authors
  • Focus on papers from prestigious venues (Nature, Science, IEEE, etc.)

AURA is designed to generate only high-quality academic essays backed by
verified sources. When quality cannot be assured, we prefer to fail rather
than produce potentially unreliable content.

{'='*60}
"""


def get_citation_verification_failed_error(
    orphan_count: int,
    unused_count: int,
    mismatch_count: int,
    orphan_examples: list = None,
    unused_examples: list = None
) -> str:
    """Generate error for citation verification failure"""
    message = f"""
❌ Citation Verification Failed
{'='*60}

Citation Accuracy Issues:
  • {orphan_count} citations without matching references
  • {unused_count} references not cited in essay
  • {mismatch_count} author/year mismatches

What This Means:
The essay contains citations that don't properly match the reference list.
This violates academic integrity standards and makes it impossible to
trace claims back to their sources.

Examples of Problems:
"""

    if orphan_examples:
        message += "\nOrphan Citations (no matching reference):\n"
        for example in orphan_examples[:3]:
            message += f"  • {example}\n"

    if unused_examples:
        message += "\nUnused References (listed but not cited):\n"
        for example in unused_examples[:3]:
            message += f"  • {example[:70]}...\n"

    message += f"""

AURA requires 100% citation accuracy to ensure academic integrity.
The essay has been rejected and the system will regenerate with corrections.

If the problem persists, it suggests the source materials may be
inconsistent or the search query needs to be refined.

{'='*60}
"""

    return message


def get_fact_check_failed_error(supported_pct: float, required_pct: float) -> str:
    """Generate error for fact-checking failure"""
    return f"""
❌ Fact-Checking Failed
{'='*60}

Claims Verified: {supported_pct*100:.1f}%
Minimum Required: {required_pct*100:.1f}%

Verification Issue:
Several claims in the essay could not be verified against the source papers.
This indicates a disconnect between the generated essay and the actual
research findings from the cited papers.

What This Means:
  • The essay makes assertions not directly supported by the papers
  • The LLM may have overinterpreted or extrapolated from the sources
  • The papers may not be relevant to the specific claims made

Quality Control Action:
This is a critical quality control mechanism. Rather than publish an
essay with unsupported claims, AURA rejects it and attempts regeneration
with stricter verification.

If failures persist:
  • The source papers may not be suitable for the research question
  • Try a different search query
  • Ensure your research question is specific enough

AURA's fact-checking system ensures essays are grounded in actual
research findings, not AI hallucinations.

{'='*60}
"""


def get_success_message(
    papers_count: int,
    quality_score: float,
    word_count: int,
    citation_count: int
) -> str:
    """Generate success message after essay generation"""
    return f"""
✅ Essay Generated Successfully
{'='*60}

Essay Statistics:
  • Word Count: {word_count}
  • Citations: {citation_count}
  • Source Papers: {papers_count}
  • Quality Score: {quality_score:.1f}/10.0

Quality Verification:
  ✓ All papers validated
  ✓ Sources sufficiently diverse
  ✓ Essay quality meets standards
  ✓ All citations verified
  ✓ Claims fact-checked and supported

This essay has passed AURA's comprehensive 7-layer academic quality
control system and is backed by verified research papers.

{'='*60}
"""


def get_system_error(error_type: str, details: str = "") -> str:
    """Generate error for system issues"""
    return f"""
⚠️  System Error
{'='*60}

Error Type: {error_type}

Details: {details}

AURA encountered an unexpected error while processing your request.
This could be due to:
  • API connectivity issues
  • Invalid database configuration
  • System resource limitations
  • Temporary service disruption

Recommended Actions:
  1. Try again in a few moments
  2. Verify your API keys are configured
  3. Check your internet connection
  4. Contact support if the problem persists

{'='*60}
"""
