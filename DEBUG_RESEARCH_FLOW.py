#!/usr/bin/env python3
"""
Debug script to diagnose why "No analysis to synthesize" error occurs
Tests each stage of the research pipeline
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_config():
    """Test 1: Verify configuration is loaded"""
    print("\n" + "="*70)
    print("TEST 1: Configuration Loading")
    print("="*70)

    try:
        from aura_research.utils.config import SERPER_API_KEY, OPENAI_API_KEY

        if not SERPER_API_KEY:
            print("ERROR: SERPER_API_KEY is not set")
            return False
        else:
            print(f"✓ SERPER_API_KEY is configured: {SERPER_API_KEY[:10]}...")

        if not OPENAI_API_KEY:
            print("ERROR: OPENAI_API_KEY is not set")
            return False
        else:
            print(f"✓ OPENAI_API_KEY is configured: {OPENAI_API_KEY[:10]}...")

        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False


async def test_paper_fetching():
    """Test 2: Verify paper fetching from Serper API"""
    print("\n" + "="*70)
    print("TEST 2: Paper Fetching from Serper API")
    print("="*70)

    try:
        from aura_research.agents.supervisor_agent import SupervisorAgent

        supervisor = SupervisorAgent()
        query = "machine learning"  # Simple test query

        print(f"Fetching papers for query: '{query}'...")
        papers = await supervisor._fetch_papers(query)

        if not papers:
            print("ERROR: No papers returned from Serper API")
            return False
        else:
            print(f"✓ Successfully fetched {len(papers)} papers")
            print(f"  Sample paper: {papers[0].get('title', 'Unknown')[:80]}...")
            return True

    except Exception as e:
        print(f"ERROR during paper fetching: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_subordinate_analysis():
    """Test 3: Verify subordinate agents can analyze papers"""
    print("\n" + "="*70)
    print("TEST 3: Subordinate Agent Analysis")
    print("="*70)

    try:
        from aura_research.agents.supervisor_agent import SupervisorAgent
        from aura_research.agents.subordinate_agent import SubordinateAgent

        supervisor = SupervisorAgent()
        query = "machine learning"

        # Fetch papers
        print("Fetching papers...")
        papers = await supervisor._fetch_papers(query)
        print(f"✓ Fetched {len(papers)} papers")

        # Create and test one subordinate agent
        print("Creating subordinate agent...")
        agent = SubordinateAgent(agent_id="test-001")

        batch = {
            "agent_id": agent.agent_id,
            "papers": papers[:3]  # Test with first 3 papers
        }

        print(f"Analyzing {len(batch['papers'])} papers...")
        result = await agent.execute(batch)

        if result.get("status") != "completed":
            print(f"ERROR: Agent analysis failed with status: {result.get('status')}")
            print(f"  Error: {result.get('error')}")
            return False
        else:
            analyses = result.get("result", {}).get("analyses", [])
            print(f"✓ Agent analysis completed")
            print(f"  Generated {len(analyses)} analyses")
            if analyses:
                print(f"  Sample analysis summary: {analyses[0].get('summary', 'N/A')[:100]}...")
            return True

    except Exception as e:
        print(f"ERROR during agent analysis: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_workflow():
    """Test 4: Run full research workflow"""
    print("\n" + "="*70)
    print("TEST 4: Full Research Workflow")
    print("="*70)

    try:
        from aura_research.agents.orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator()
        query = "neural networks"

        print(f"Running full workflow for query: '{query}'...")
        result = await orchestrator.execute_research(query)

        print(f"Workflow Status: {result.get('status')}")
        print(f"  Total Papers: {result.get('total_papers')}")
        print(f"  Analyses Count: {result.get('analyses_count')}")
        print(f"  Agents Completed: {result.get('agents', {}).get('completed')}/{result.get('agents', {}).get('total')}")

        if result.get('errors'):
            print(f"  Errors: {result['errors']}")
            return False
        else:
            # Check if essay was generated
            if result.get('essay'):
                print(f"✓ Essay generated successfully ({len(result.get('essay', ''))} chars)")
                return True
            else:
                print("ERROR: No essay generated")
                return False

    except Exception as e:
        print(f"ERROR during workflow: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("AURA RESEARCH PIPELINE DIAGNOSTIC")
    print("="*70)
    print("Testing each stage of the research pipeline...")

    results = {
        "Configuration": await test_config(),
        "Paper Fetching": await test_paper_fetching() if await test_config() else False,
        "Subordinate Analysis": await test_subordinate_analysis() if await test_paper_fetching() else False,
        "Full Workflow": await test_full_workflow() if await test_subordinate_analysis() else False
    }

    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        symbol = "[✓]" if passed else "[✗]"
        print(f"{symbol} {test_name}: {status}")

    # Find first failure point
    for test_name, passed in results.items():
        if not passed:
            print(f"\nFirst failure at: {test_name}")
            break

    print("="*70)

    return all(results.values())


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
