#!/usr/bin/env python
"""
Debug why essay is empty/0 words
"""

import asyncio
import logging
from aura_research.agents.orchestrator import AgentOrchestrator
import json

logging.basicConfig(level=logging.WARNING)

async def test():
    print("\n" + "="*70)
    print("DEBUGGING ESSAY GENERATION")
    print("="*70 + "\n")

    orchestrator = AgentOrchestrator()

    try:
        result = await orchestrator.execute_research("machine learning")

        # Check the essay
        essay = result.get('essay', '')
        print(f"[Essay Content Type]: {type(essay)}")
        print(f"[Essay Length]: {len(essay)} characters")

        if essay:
            print(f"\n[First 500 chars of essay]:")
            print(essay[:500])
            print("\n[Last 200 chars of essay]:")
            print(essay[-200:])
        else:
            print("[Essay is empty or None]")

        # Check metadata
        metadata = result.get('essay_metadata', {})
        print(f"\n[Metadata]:")
        print(f"  Word count: {metadata.get('word_count', 'N/A')}")
        print(f"  Citations: {metadata.get('citations', 'N/A')}")

        # Check if file was saved
        file_path = result.get('essay_file_path', '')
        print(f"\n[File Path]: {file_path}")

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                print(f"[File Content Length]: {len(file_content)} characters")
                if file_content:
                    print(f"[File First 300 chars]:")
                    print(file_content[:300])
            except Exception as e:
                print(f"[Error reading file]: {e}")

        # Print full result structure
        print(f"\n[Full Result Keys]:")
        print(json.dumps({k: type(v).__name__ if not isinstance(v, (str, int, float, bool, type(None))) else v
                         for k, v in result.items()}, indent=2, default=str)[:1000])

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
