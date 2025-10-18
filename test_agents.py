"""
Test script for AURA multi-agent system
"""

import asyncio
import sys
sys.path.insert(0, 'aura_research')

from aura_research.agents.orchestrator import AgentOrchestrator


async def test_multi_agent_system():
    """Test the multi-agent research system"""

    print("\n" + "="*70)
    print("AURA Multi-Agent System Test")
    print("="*70 + "\n")

    # Create orchestrator
    orchestrator = AgentOrchestrator()

    # Test query
    test_query = "machine learning in healthcare"

    print(f"Test Query: {test_query}\n")

    # Execute research
    result = await orchestrator.execute_research(test_query)

    # Display results
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70)
    print(f"\nQuery: {result['query']}")
    print(f"Status: {result['status']}")
    print(f"Session ID: {result['session_id']}")
    print(f"\nPapers Found: {result['total_papers']}")
    print(f"Analyses Generated: {result['analyses_count']}")
    print(f"\nAgent Statistics:")
    print(f"  - Total Agents: {result['agents']['total']}")
    print(f"  - Completed: {result['agents']['completed']}")
    print(f"  - Failed: {result['agents']['failed']}")

    # Show sample analyses
    if result['analyses']:
        print(f"\nSample Analysis (first paper):")
        first_analysis = result['analyses'][0]
        print(f"  Title: {first_analysis.get('title', 'N/A')}")
        print(f"  Core Ideas: {first_analysis.get('core_ideas', [])[:2]}")
        print(f"  Relevance Score: {first_analysis.get('relevance_score', 'N/A')}/10")

    # Show agent execution details
    print(f"\nSubordinate Agent Details:")
    for i, sub_result in enumerate(result['subordinate_results']):
        print(f"\n  Agent {i+1} ({sub_result['agent_id']}):")
        print(f"    Status: {sub_result['status']}")
        print(f"    Execution Time: {sub_result.get('execution_time', 0):.2f}s")
        if sub_result['status'] == 'completed':
            papers_analyzed = sub_result['result']['papers_analyzed']
            print(f"    Papers Analyzed: {papers_analyzed}")

    # Show essay details
    if result.get('essay_file_path'):
        print(f"\n\nEssay Generated:")
        print(f"  File Path: {result['essay_file_path']}")
        print(f"  Word Count: {result['essay_metadata'].get('word_count', 0)}")
        print(f"  Citations: {result['essay_metadata'].get('citations', 0)}")
        print(f"  Papers Synthesized: {result['essay_metadata'].get('papers_synthesized', 0)}")

    if result.get('errors'):
        print(f"\nErrors encountered: {result['errors']}")

    print("\n" + "="*70)
    print("Test Complete!")
    print("="*70 + "\n")

    return result


if __name__ == "__main__":
    # Run test
    asyncio.run(test_multi_agent_system())
