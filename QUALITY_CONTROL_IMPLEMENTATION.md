# AURA Academic Rigor Guardrails - Implementation Guide

## Overview

This document describes the implementation of the 7-layer academic quality control system for AURA Research Agent. This system ensures that all generated essays are grounded in verified academic sources and meet rigorous quality standards.

## Architecture

### 7 Layers of Quality Control

```
┌─────────────────────────────────────────┐
│  Layer 7: Mock Data Elimination          │
│  (No fallback to fake papers)            │
├─────────────────────────────────────────┤
│  Layer 6: Enhanced Guardrail Prompts     │
│  (Stricter LLM requirements)             │
├─────────────────────────────────────────┤
│  Layer 5: Fact-Checking Service          │
│  (Verify claims against sources)         │
├─────────────────────────────────────────┤
│  Layer 4: Citation Verification          │
│  (Match citations to references)         │
├─────────────────────────────────────────┤
│  Layer 3: Quality Scoring System         │
│  (6-dimension quality assessment)        │
├─────────────────────────────────────────┤
│  Layer 2: Source Sufficiency Checks      │
│  (Minimum 5 validated papers)            │
├─────────────────────────────────────────┤
│  Layer 1: Paper Validation Service       │
│  (CrossRef/OpenAlex verification)        │
└─────────────────────────────────────────┘
```

## File Structure

### New Services

```
aura_research/services/
├── paper_validation_service.py       (Layer 1)
├── source_sufficiency_service.py     (Layer 2)
├── quality_scoring_service.py        (Layer 3)
├── citation_verification_service.py  (Layer 4)
└── fact_checking_service.py          (Layer 5)
```

### Modified Files

```
aura_research/
├── agents/
│   ├── supervisor_agent.py          (Integrated Layer 1 & 2)
│   ├── summarizer_agent.py          (Integrated Layer 3, 4, 5)
│   └── workflow.py                  (Passes validation errors)
└── utils/
    ├── config.py                    (Added quality control constants)
    └── error_messages.py            (New: user-friendly error messages)
```

### Database

```
database/migrations/
└── 004_add_quality_control_tables.sql
    ├── PaperValidation
    ├── EssayQualityMetrics
    ├── CitationVerification
    ├── FactCheckingResults
    ├── QualityControlSummary
    └── PaperValidationCache
```

## Layer 1: Paper Validation Service

**File**: `aura_research/services/paper_validation_service.py`

### Purpose
Verify that papers from Serper API are legitimate research publications.

### Validation Levels

1. **Basic Validation** (0.5 weight)
   - Title length: 10-500 characters
   - Has snippet/abstract: >50 chars
   - Publication year: 1950-present
   - Has citations data

2. **DOI Verification** (0.8 weight)
   - Query CrossRef API for DOI
   - Extract: publication venue, authors, citations
   - Check retraction status

3. **OpenAlex Validation** (0.8 weight)
   - Query OpenAlex API (free tier)
   - Extract: DOI, retraction status, citation count
   - Calculate venue quality score

4. **Full Validation** (1.0 weight)
   - Successful CrossRef verification
   - Complete metadata enrichment
   - Highest confidence validation

### Key Methods

```python
async def validate_papers(self, papers: List[Dict]) -> tuple[List[Dict], List[Dict]]
    """Returns (valid_papers, validation_results)"""

async def _verify_crossref(self, paper, doi) -> Dict
    """Verify via CrossRef API"""

async def _verify_openalex(self, paper) -> Dict
    """Verify via OpenAlex API as fallback"""

def _validate_basic_metadata(self, paper) -> tuple[bool, str]
    """Check basic paper metadata"""
```

### Configuration

```python
MIN_TITLE_LENGTH = 10
MAX_TITLE_LENGTH = 500
ABSTRACT_MIN_LENGTH = 50
MIN_YEAR = 1950
CACHE_TIMEOUT_HOURS = 24
```

### API Endpoints

- **CrossRef**: `https://api.crossref.org/works/{DOI}`
- **OpenAlex**: `https://api.openalex.org/works`

Both are free with no API key required.

## Layer 2: Source Sufficiency Checks

**File**: `aura_research/services/source_sufficiency_service.py`

### Purpose
Reject essays when source material is insufficient.

### Sufficiency Criteria

1. **Minimum Papers**: ≥5 validated papers
2. **Venue Diversity**: Papers from ≥3 different venues
3. **Recency**: ≥2 papers from last 5 years
4. **Effective Count**: Weighted sum ≥4.0

### Effective Count Formula

```
effective_count = sum(paper.validation_level_weight * citation_boost)

Weights:
  - Full validation: 1.0
  - DOI validation: 0.8
  - Basic validation: 0.5

Citation boost:
  - >50 citations: 1.2x
  - >500 citations: 1.5x
```

### Integration Point

**Modified**: `supervisor_agent.py` lines 175-214

```python
async def _fetch_papers(self, query: str) -> List[Dict]:
    # 1. Fetch from Serper API
    papers = await self._fetch_papers_api(query)

    # 2. Validate papers (Layer 1)
    valid_papers, validation_results = await self.paper_validator.validate_papers(papers)

    # 3. Check sufficiency (Layer 2)
    sufficiency = self.sufficiency_checker.check_sufficiency(papers, validation_results)

    if not sufficiency.is_sufficient:
        raise ValueError(sufficiency_error_message)

    return valid_papers
```

### Error Handling

When insufficiency is detected, the system raises an error with detailed message:

```
Papers Found: 3
Papers Validated: 2 (need 5)
Issues:
  • Only 2 validated papers (need 5)
  • Limited diversity in venues

Suggestions:
  • Try a more specific search
  • Use different keywords
  • Combine related concepts
```

## Layer 3: Quality Scoring System

**File**: `aura_research/services/quality_scoring_service.py`

### Purpose
Automated assessment of essay quality with rejection threshold.

### Quality Dimensions

| Dimension | Weight | Metric |
|-----------|--------|--------|
| Citation Density | 20% | ~1 per 175 words |
| Source Diversity | 15% | Unique authors/venues |
| Academic Language | 15% | Hedging, passive voice |
| Structural Coherence | 15% | Intro-body-conclusion flow |
| Evidence-Based Claims | 20% | Claims within 2 sentences of citations |
| Citation Accuracy | 15% | Format consistency |

### Scoring Thresholds

- **Rejected**: < 5.0
- **Needs Review**: 5.0 - 6.5
- **Good**: 6.5 - 8.0
- **Excellent**: ≥ 8.0

### Integration Point

**Modified**: `summarizer_agent.py` after essay compilation

```python
# Score essay quality
quality_result = await self.quality_scorer.score_essay(essay, analyses)

if quality_result["overall_score"] < MIN_QUALITY_SCORE:
    if self.regeneration_attempts < MAX_ESSAY_REGENERATION_ATTEMPTS:
        # Attempt regeneration
        return await self.run(task)
    else:
        raise ValueError(low_quality_error)
```

### NLP Features

Uses spaCy (en_core_web_sm) to analyze:
- Hedging language (suggests, may, appears)
- Passive voice constructions
- Absolute statements (is definitely, is clearly)
- Sentence structure and transitions

## Layer 4: Citation Verification Service

**File**: `aura_research/services/citation_verification_service.py`

### Purpose
Ensure all in-text citations match the reference list exactly.

### Verification Checks

1. **Orphan Citations**: Citations without matching references
2. **Unused References**: References not cited in text
3. **Citation Mismatches**: Author/year discrepancies
4. **Format Consistency**: All citations in (Author et al., Year) format

### Citation Format

Supported formats:
- `(Author et al., Year)`
- `(FirstAuthor et al., Year)`
- `(Author, Year)`

### Integration Point

**Modified**: `summarizer_agent.py` after quality scoring

```python
# Verify citations
citation_result = await self.citation_verifier.verify_citations(essay)

if not citation_result.is_valid:
    if regeneration_attempts < MAX_ATTEMPTS:
        return await self.run(task)  # Regenerate
    else:
        raise ValueError(citation_error)
```

### Requirements

- 100% accuracy required (no orphan citations allowed)
- All in-text citations must have references
- All major references should be cited

## Layer 5: Fact-Checking Service

**File**: `aura_research/services/fact_checking_service.py`

### Purpose
Verify claims in essay are supported by source papers.

### Fact-Checking Process

1. **Extract Claims**: Top 10-15 significant claims from essay
2. **Find Papers**: Locate cited papers in analyses
3. **Verify Claims**: Use LLM to compare claim against paper analysis
4. **Verdict**: SUPPORTED | PARTIALLY_SUPPORTED | NOT_SUPPORTED

### Verdicts

- **SUPPORTED**: Claim directly matches paper findings
- **PARTIALLY_SUPPORTED**: Claim loosely matches paper findings
- **NOT_SUPPORTED**: Claim contradicts or is not found in paper

### Threshold

Minimum 85% of claims must be SUPPORTED or PARTIALLY_SUPPORTED.

### Integration Point

**Modified**: `summarizer_agent.py` after citation verification

```python
# Run fact-checking
fact_check_result = await self.fact_checker.verify_essay_claims(essay, analyses)

if not fact_check_result["is_valid"]:
    if regeneration_attempts < MAX_ATTEMPTS:
        return await self.run(task)  # Regenerate with stricter prompts
    else:
        raise ValueError(fact_check_error)
```

## Layer 6: Enhanced Guardrail Prompts

**Purpose**: Strengthen academic integrity requirements in LLM prompts.

### Modified System Prompts

All essay generation prompts (introduction, body, conclusion) now include:

```
CRITICAL ACADEMIC INTEGRITY REQUIREMENTS:
1. EVERY factual claim MUST be supported by specific citations
2. Use ONLY information from provided paper references
3. If you cannot find supporting evidence, DO NOT include it
4. Use hedging language: suggests, may, appears, indicates
5. Never extrapolate beyond what papers explicitly state
6. Citation format MUST be (Author et al., Year)
7. Do not invent or approximate citations
8. If references insufficient, state this rather than generate unsupported content
```

### Modified Files

- `summarizer_agent.py` lines 342-375 (Introduction prompt)
- `summarizer_agent.py` lines 498-542 (Body prompt)
- `summarizer_agent.py` lines 580-622 (Conclusion prompt)

## Layer 7: Mock Data Elimination

**Purpose**: Remove all fallback to fake papers.

### Changes Made

**Modified**: `supervisor_agent.py` lines 175-214

**Removed**:
- `DEBUG_MODE` fallback logic
- `_get_mock_papers()` method
- All mock data generation

**Added**:
- Immediate error if no papers found
- Clear error messages
- No silent failures

### Integration

```python
async def _fetch_papers(self, query: str) -> List[Dict]:
    try:
        papers = await self._fetch_papers_api(query)
        if not papers:
            raise ValueError("No papers found")

        # Validate and check sufficiency
        valid_papers, validation_results = await self.paper_validator.validate_papers(papers)
        sufficiency = self.sufficiency_checker.check_sufficiency(papers, validation_results)

        if not sufficiency.is_sufficient:
            raise ValueError(error_message)

        return valid_papers
    except Exception as e:
        # DO NOT FALL BACK TO MOCK DATA
        raise ValueError(f"Unable to fetch papers: {str(e)}")
```

## Configuration

**File**: `aura_research/utils/config.py`

```python
# Paper Validation
CROSSREF_API_URL = "https://api.crossref.org/works"
OPENALEX_API_URL = "https://api.openalex.org/works"
MIN_VALID_PAPERS = 5
VALIDATION_CACHE_HOURS = 24

# Source Sufficiency
MIN_UNIQUE_VENUES = 3
MIN_RECENT_PAPERS = 2
MIN_EFFECTIVE_COUNT = 4.0

# Quality Scoring
MIN_QUALITY_SCORE = 5.0
FLAG_QUALITY_SCORE = 6.5
EXCELLENT_QUALITY_SCORE = 8.0
CITATION_DENSITY_TARGET = 0.0057
MAX_ESSAY_REGENERATION_ATTEMPTS = 2

# Academic Rigor
STRICT_MODE = True
ALLOW_MOCK_DATA = False  # CRITICAL
```

## Error Messages

**File**: `aura_research/utils/error_messages.py`

User-friendly error messages for:
- Insufficient papers
- Low essay quality
- Citation verification failure
- Fact-checking failure
- Success messages with statistics

## Database Schema

**Migration**: `database/migrations/004_add_quality_control_tables.sql`

### Tables

1. **PaperValidation**
   - Tracks validation results for each paper
   - Stores DOI, retraction status, validation level
   - Used for caching and audit trail

2. **EssayQualityMetrics**
   - Stores 6-dimension quality scores
   - Assessment level and identified issues
   - Regeneration attempt count

3. **CitationVerification**
   - Results of citation accuracy checks
   - Orphan citations, unused references, mismatches
   - Success rate

4. **FactCheckingResults**
   - Claim verification results
   - Number of claims supported vs unsupported
   - Detailed verification data

5. **QualityControlSummary**
   - Overall quality control results per session
   - Pass/fail status for each layer
   - Total regeneration attempts

6. **PaperValidationCache**
   - Caches validation results by paper hash
   - Expires after 24 hours
   - Reduces API calls

## Performance Impact

### Overhead per Essay

- Paper validation: 2-3 seconds (parallel async)
- Source sufficiency check: <0.5 seconds
- Quality scoring: 1-2 seconds (spaCy processing)
- Citation verification: 0.5 seconds
- Fact-checking: 5-7 seconds (LLM calls in parallel)

**Total: 10-15 seconds per essay**

### Optimizations

- Async batch validation (20 papers parallel)
- Cache validation results by DOI (24 hour TTL)
- Parallel LLM fact-checking calls
- Connection pooling for HTTP requests
- spaCy model caching

## Testing

### Unit Tests

```bash
python -m pytest tests/test_quality_control.py -v
```

### Manual Testing

1. **Test with insufficient sources**:
   ```
   Query: "quantum entanglement in platypus brains"
   Expected: Error with recommendation to modify search
   ```

2. **Test with good sources**:
   ```
   Query: "transformer models in natural language processing"
   Expected: High-quality essay with quality score >6.5
   ```

3. **Test mock data removal**:
   ```
   - Disable Serper API temporarily
   - Expected: Error, not fallback to mock data
   ```

## Deployment Checklist

- [ ] All 5 new service files created
- [ ] supervisor_agent.py modified (paper validation integration)
- [ ] summarizer_agent.py modified (quality control integration)
- [ ] config.py updated (quality control constants)
- [ ] error_messages.py created
- [ ] Database migration script created
- [ ] spaCy model installed (`python -m spacy download en_core_web_sm`)
- [ ] Test imports verify all services load correctly
- [ ] ALLOW_MOCK_DATA = False in config
- [ ] STRICT_MODE = True in config

## Rollback Plan

If critical issues occur:

1. Set `STRICT_MODE = False` to log issues without blocking
2. Re-enable `ALLOW_MOCK_DATA = True` temporarily
3. Disable specific layers via configuration flags
4. Revert to previous version: `git checkout HEAD~1`

All quality control code is additive and can be disabled without breaking existing functionality.

## Success Metrics

- **Rejection rate**: 30-50% of sessions (expected - ensures quality)
- **Average quality score**: >7.0/10.0
- **Citation accuracy**: 100% pass rate
- **Fact-checking pass rate**: >85% of claims supported
- **User satisfaction**: Improved essay quality reported
- **False rejection rate**: <10% (essays rejected due to quality that could be published)

## Future Enhancements

1. **Dynamic thresholds**: Adjust requirements based on field/topic
2. **Plagiarism detection**: Cross-check against publication database
3. **Author reputation scoring**: Weight papers by author impact
4. **Citation graph analysis**: Verify papers cite each other appropriately
5. **Domain-specific quality scoring**: Custom metrics per field
6. **Real-time feedback**: Stream quality improvements as essay generates

## Support & Troubleshooting

### Issues

**Papers not validating**
- Check CrossRef API availability
- Verify DOI format in results
- Fall back to basic validation

**Quality score too low**
- Review LLM temperature (currently 0.3)
- Increase citation density target
- Use more recent papers

**Citation verification fails**
- Check citation format in prompts
- Review reference section extraction logic
- Validate paper reference data

**Fact-checking times out**
- Increase asyncio timeout values
- Run smaller batch of claims
- Use cheaper LLM model for initial checks

## References

- CrossRef API Docs: https://github.com/CrossRef/rest-api-doc
- OpenAlex API Docs: https://docs.openalex.org/
- spaCy Documentation: https://spacy.io/
- Academic Writing Standards: https://owl.purdue.edu/
