#!/usr/bin/env python
"""
Diagnose why essay is empty - test complete pipeline
"""

import asyncio
import logging
from aura_research.agents.orchestrator import AgentOrchestrator

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(levelname)s - %(message)s'
)

async def diagnose():
    print("\n" + "="*70)
    print("DIAGNOSING EMPTY ESSAY ISSUE")
    print("="*70 + "\n")

    orchestrator = AgentOrchestrator()

    try:
        print("[1] Starting research for 'machine learning'...\n")
        result = await orchestrator.execute_research("machine learning")

        print("\n" + "="*70)
        print("RESEARCH RESULTS")
        print("="*70)

        print(f"\n[Query]: {result.get('query')}")
        print(f"[Status]: {result.get('status')}")
        print(f"[Total Papers]: {result.get('total_papers')}")
        print(f"[Analyses Count]: {result.get('analyses_count')}")

        agents = result.get('agents', {})
        print(f"[Agents]: {agents.get('completed')}/{agents.get('total')} completed")

        essay = result.get('essay', '')
        print(f"[Essay Length]: {len(essay)} characters")

        if essay:
            print(f"\n[ESSAY PREVIEW (first 500 chars)]:")
            print(essay[:500])
            print("\n✓ Essay generated successfully!")
        else:
            print("\n✗ ESSAY IS EMPTY!")
            print(f"\n[Full Result]:")
            import json
            print(json.dumps(result, indent=2, default=str))

        # Check errors
        errors = result.get('errors', [])
        if errors:
            print(f"\n[ERRORS]:")
            for error in errors:
                print(f"  - {error}")

        return result

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        print("\n[FULL TRACEBACK]:")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(diagnose())

    if result and result.get('essay'):
        print(f"\n✓ SUCCESS: Pipeline working correctly")
    else:
        print(f"\n✗ FAILED: Check errors above for details")
