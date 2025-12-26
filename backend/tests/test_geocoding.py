"""Test MPC integration with orchestrator"""

import asyncio
from app.llm.orchestrator import orchestrator


async def test_mpc():
    print("\n" + "="*70)
    print("🧪 TESTING MPC INTEGRATION IN ORCHESTRATOR")
    print("="*70)
    
    queries = [
        "Find Sentinel-2 images of Lahore from August 2024",
        "Show me satellite imagery for Dadu District",
        "Search for Landsat data of Sindh Province in 2022",
    ]
    
    for query in queries:
        print(f"\n{'─'*70}")
        print(f"Query: {query}")
        print('─'*70)
        
        result = await orchestrator.process_query(query)
        
        print(f"\nStatus: {result.get('status')}")
        print(f"Intent: {result.get('intent')}")
        
        if result.get('report'):
            print(f"\nReport:\n{result['report'][:500]}...")
        
        if result.get('data'):
            data = result['data']
            print(f"\nImages Found: {data.get('images_found')}")


if __name__ == "__main__":
    asyncio.run(test_mpc())