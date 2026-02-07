import asyncio
import os
import sys

# Add app to path
sys.path.append(os.getcwd())

from app.llm.tools.urban_expansion_tool import analyze_urban_expansion

async def main():
    print("Testing analyze_urban_expansion...")
    try:
        result = await analyze_urban_expansion.ainvoke({
            "location_name": "Dubai",
            "start_year": 1990,
            "end_year": 2020,
            "buffer_km": 10.0,
            "palette": "neon",
            "include_animation": False,
            "include_population": True
        })
        print("Result:", result)
    except Exception as e:
        print("Error encountered:")
        print(e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
