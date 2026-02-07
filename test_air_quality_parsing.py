
import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.llm.agents.query_agent import QueryAgent
from app.utils.logger import get_logger

# Mock logger to avoid clutter
import logging
logging.basicConfig(level=logging.INFO)

async def test_air_quality_parsing():
    agent = QueryAgent()
    
    test_queries = [
        "Show air pollution in Lahore",
        "Check NO2 levels in Beijing 2021",
        "Compare air quality in Delhi 2019 vs 2020",
        "Show me smog levels in Los Angeles with CO and Ozone",
        "Is the air quality good in Karachi?"
    ]
    
    print("\n🧪 TESTING AIR QUALITY QUERY PARSING\n")
    
    for query in test_queries:
        print(f"Query: '{query}'")
        try:
            result = await agent.parse_query(query)
            print(f"Intent: {result.get('intent')}")
            print(f"Params: {result.get('parameters')}")
            
            if result.get('intent') == 'query_air_quality':
                print("✅ PASSED")
            else:
                print("❌ FAILED - Incorrect Intent")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_air_quality_parsing())
