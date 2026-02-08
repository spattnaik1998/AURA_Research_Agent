#!/usr/bin/env python
"""
Inspect the actual structure of papers from Serper API
"""

import asyncio
import requests
import json
from aura_research.utils.config import SERPER_API_KEY

async def inspect():
    url = "https://google.serper.dev/scholar"

    payload = {
        "q": "Backpropagation",
        "num": 3
    }

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    print("\n" + "="*70)
    print("INSPECTING SERPER API RESPONSE STRUCTURE")
    print("="*70)

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    results = response.json()

    print(f"\nTotal papers in response: {len(results.get('organic', []))}")

    for i, result in enumerate(results.get("organic", [])[:2]):
        print(f"\n[Paper {i+1}]")
        print(f"  Keys: {list(result.keys())}")

        for key, value in result.items():
            value_type = type(value).__name__
            if isinstance(value, dict):
                print(f"  {key} ({value_type}): {list(value.keys())}")
            elif isinstance(value, str):
                print(f"  {key} ({value_type}): {value[:60]}...")
            else:
                print(f"  {key} ({value_type}): {value}")

    # Now let's see what the supervisor agent creates
    print("\n" + "="*70)
    print("TRANSFORMED PAPER FORMAT")
    print("="*70)

    for i, result in enumerate(results.get("organic", [])[:2]):
        paper = {
            "title": result.get("title", ""),
            "snippet": result.get("snippet", ""),
            "link": result.get("link", ""),
            "publication_info": result.get("publicationInfo", {}),
            "cited_by": {"total": result.get("citedBy", 0)}
        }

        print(f"\n[Paper {i+1}]")
        print(f"  publication_info type: {type(paper['publication_info'])}")
        print(f"  publication_info value: {paper['publication_info']}")

        if isinstance(paper['publication_info'], dict):
            print(f"  publication_info keys: {list(paper['publication_info'].keys())}")
        else:
            print(f"  ERROR: publication_info is {type(paper['publication_info']).__name__}, not dict!")

if __name__ == "__main__":
    asyncio.run(inspect())
