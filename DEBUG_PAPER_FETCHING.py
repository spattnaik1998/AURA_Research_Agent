#!/usr/bin/env python
"""
Debug tool to diagnose paper fetching issues
"""

import asyncio
import sys
import logging
from aura_research.agents.supervisor_agent import SupervisorAgent
from aura_research.utils.config import SERPER_API_KEY, TAVILY_API_KEY

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('debug')

async def test_paper_fetching():
    """Test paper fetching with detailed diagnostics"""

    print("\n" + "="*70)
    print("PAPER FETCHING DIAGNOSTIC TOOL")
    print("="*70)

    # Test 1: Check API keys
    print("\n[1] API KEY CONFIGURATION")
    print("-" * 70)

    if SERPER_API_KEY:
        print(f"[OK] SERPER_API_KEY is configured")
        print(f"     First 20 chars: {SERPER_API_KEY[:20]}...")
    else:
        print(f"[ERROR] SERPER_API_KEY is NOT configured")

    if TAVILY_API_KEY:
        print(f"[OK] TAVILY_API_KEY is configured")
        print(f"     First 20 chars: {TAVILY_API_KEY[:20]}...")
    else:
        print(f"[ERROR] TAVILY_API_KEY is NOT configured")

    # Test 2: Try fetching papers
    print("\n[2] PAPER FETCHING TEST")
    print("-" * 70)

    supervisor = SupervisorAgent()
    queries = [
        "Backpropagation",
        "neural networks",
        "machine learning",
        "transformer architecture"
    ]

    for query in queries:
        print(f"\nTesting query: '{query}'")
        try:
            papers = await supervisor._fetch_papers(query)
            print(f"  [OK] Successfully fetched {len(papers)} papers")

            if papers:
                print(f"  First paper: {papers[0].get('title', 'No title')[:60]}...")
                print(f"  Citation count: {papers[0].get('cited_by', {}).get('total', 0)}")
            else:
                print(f"  WARNING: Papers fetched but list is empty!")

        except Exception as e:
            print(f"  [ERROR] ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

    # Test 3: Test individual APIs
    print("\n[3] INDIVIDUAL API TESTS")
    print("-" * 70)

    query_test = "Backpropagation"

    # Test Serper
    print(f"\nTesting Serper API with query: '{query_test}'")
    try:
        papers_serper = await supervisor._fetch_papers_api(query_test)
        print(f"  [OK] Serper API returned {len(papers_serper)} papers")
    except Exception as e:
        print(f"  [ERROR] Serper API failed: {str(e)}")

    # Test Tavily
    print(f"\nTesting Tavily API with query: '{query_test}'")
    try:
        papers_tavily = await supervisor._fetch_papers_tavily(query_test)
        print(f"  [OK] Tavily API returned {len(papers_tavily)} papers")
    except Exception as e:
        print(f"  [ERROR] Tavily API failed: {str(e)}")

    # Test 4: Test validation
    print("\n[4] VALIDATION TEST")
    print("-" * 70)

    if papers:
        print(f"\nValidating {len(papers)} papers...")
        valid_papers, results = await supervisor.paper_validator.validate_papers(papers)
        print(f"  Valid papers: {len(valid_papers)}")
        print(f"  Invalid papers: {len(papers) - len(valid_papers)}")

        for i, result in enumerate(results[:3]):
            print(f"\n  Paper {i+1}:")
            print(f"    Title: {result.get('title', 'N/A')[:60]}...")
            print(f"    Valid: {result.get('is_valid')}")
            print(f"    Level: {result.get('validation_level', 'N/A')}")
            print(f"    Reason: {result.get('validation_reason', 'N/A')}")

    print("\n" + "="*70)
    print("DIAGNOSTIC COMPLETE")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(test_paper_fetching())
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
