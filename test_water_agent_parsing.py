import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.app.llm.agents.query_agent import QueryAgent

# Mock settings if needed
from backend.app.config import settings
if not settings.GROQ_API_KEY:
    print("Warning: GROQ_API_KEY not set")

async def test_parsing():
    try:
        agent = QueryAgent()
        
        queries = [
            "Show water changes in Aral Sea",
            "Lake Chad water loss since 1990",
            "Dead Sea shrinking animation",
            "Show slow animation of Lake Urmia drying"
        ]
        
        print("Testing Query Agent Parsing for Surface Water...")
        for q in queries:
            result = await agent.parse_query(q)
            print(f"\nQuery: {q}")
            print(f"Intent: {result.get('intent')}")
            print(f"Params: {result.get('parameters')}")
            
            if result.get('intent') == 'query_surface_water':
                print("✅ Intent matched")
            else:
                print(f"❌ Intent mismatch: {result.get('intent')}")

    except Exception as e:
        print(f"Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_parsing())
