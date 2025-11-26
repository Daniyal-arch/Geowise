"""Debug database query"""
import asyncio
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.database import init_db, database_manager
from sqlalchemy import text


async def debug_query():
    """Test the exact query the orchestrator uses"""
    
    await init_db()
    
    async with database_manager.async_session_maker() as session:
        # Test 1: Raw count
        print("\n1️⃣ Testing: SELECT COUNT(*) FROM fire_detections")
        result = await session.execute(text("SELECT COUNT(*) FROM fire_detections"))
        total = result.scalar()
        print(f"   Result: {total:,} fires")
        
        # Test 2: Count by year
        print("\n2️⃣ Testing: Count fires by year")
        result = await session.execute(
            text("SELECT strftime('%Y', acq_date) as year, COUNT(*) FROM fire_detections GROUP BY year")
        )
        for row in result:
            print(f"   {row[0]}: {row[1]:,} fires")
        
        # Test 3: The EXACT orchestrator query
        print("\n3️⃣ Testing: Orchestrator query (PAK, 2020)")
        result = await session.execute(
            text("""
                SELECT COUNT(*) 
                FROM fire_detections 
                WHERE country = :country 
                AND strftime('%Y', acq_date) = :year
            """),
            {"country": "PAK", "year": "2020"}
        )
        count = result.scalar()
        print(f"   Result: {count:,} fires")
        
        # Test 4: Check what countries exist
        print("\n4️⃣ Testing: What countries exist?")
        result = await session.execute(
            text("SELECT DISTINCT country FROM fire_detections")
        )
        countries = [row[0] for row in result]
        print(f"   Countries: {countries}")
        
        # Test 5: Sample fire record
        print("\n5️⃣ Testing: Show a sample fire record")
        result = await session.execute(
            text("SELECT country, acq_date, strftime('%Y', acq_date) FROM fire_detections LIMIT 1")
        )
        fire = result.fetchone()
        print(f"   Country: {fire[0]}")
        print(f"   Date: {fire[1]}")
        print(f"   Year (extracted): {fire[2]}")


if __name__ == "__main__":
    asyncio.run(debug_query())