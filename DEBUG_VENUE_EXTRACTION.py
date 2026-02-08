#!/usr/bin/env python
"""
Debug venue extraction
"""

import asyncio
from aura_research.agents.supervisor_agent import SupervisorAgent
from aura_research.services.source_sufficiency_service import SourceSufficiencyService

async def test():
    supervisor = SupervisorAgent()
    sufficiency = SourceSufficiencyService()

    # Fetch and validate papers
    print("\nFetching papers...")
    try:
        papers = await supervisor._fetch_papers("Backpropagation")
        print(f"Got {len(papers)} papers")
    except Exception as e:
        # Bypass sufficiency check for this test
        papers_raw = await supervisor._fetch_papers_api("Backpropagation")
        print(f"Got {len(papers_raw)} papers from API (before validation)")

        # Validate manually
        valid_papers, validation_results = await supervisor.paper_validator.validate_papers(papers_raw)
        print(f"Validated {len(valid_papers)} papers")

        papers = valid_papers

    # Now test venue extraction
    print(f"\n[Venue Extraction Debug]")
    for i, paper in enumerate(papers[:3]):
        print(f"\nPaper {i+1}: {paper.get('title', 'N/A')[:50]}")
        print(f"  publication_info: {paper.get('publication_info')}")

        pub_info = paper.get("publication_info", {})
        print(f"  pub_info type: {type(pub_info)}")
        if isinstance(pub_info, dict):
            print(f"  pub_info keys: {list(pub_info.keys())}")
            publication_name = pub_info.get("publication", "") or pub_info.get("journal", "") or pub_info.get("publisher", "")
            print(f"  publication_name: '{publication_name}'")
        else:
            print(f"  ERROR: pub_info is not a dict!")

        # Test year extraction
        year = paper.get("year")
        print(f"  year field: {year}")

if __name__ == "__main__":
    asyncio.run(test())
