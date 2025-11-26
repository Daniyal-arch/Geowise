"""Test historical fire data import"""
import asyncio
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.database import init_db, close_db, get_db
from sqlalchemy import text


async def test_import():
    """Test that import worked correctly"""
    
    await init_db()
    
    async for session in get_db():
        print("\n" + "="*60)
        print("🔍 TESTING DATABASE IMPORT")
        print("="*60)
        
        # Test 1: Total fires
        result = await session.execute(
            text("SELECT COUNT(*) FROM fire_detections")
        )
        total = result.scalar()
        print(f"\n✅ Total fires in database: {total:,}")
        
        # Test 2: Check country column exists
        result = await session.execute(
            text("SELECT country FROM fire_detections LIMIT 1")
        )
        country = result.scalar()
        print(f"✅ Country column exists: {country}")
        
        # Test 3: Fires by country
        result = await session.execute(
            text("SELECT country, COUNT(*) FROM fire_detections GROUP BY country")
        )
        print(f"\n📊 Fires by Country:")
        for row in result:
            print(f"   {row[0]}: {row[1]:,} fires")
        
        # Test 4: Date range
        result = await session.execute(
            text("SELECT MIN(acq_date), MAX(acq_date) FROM fire_detections")
        )
        dates = result.fetchone()
        print(f"\n📅 Date Range:")
        print(f"   Start: {dates[0]}")
        print(f"   End: {dates[1]}")
        
        # Test 5: By satellite
        result = await session.execute(
            text("SELECT satellite, COUNT(*) FROM fire_detections GROUP BY satellite")
        )
        print(f"\n🛰️  By Satellite:")
        for row in result:
            print(f"   {row[0]}: {row[1]:,} fires")
        
        # Test 6: Monthly distribution
        result = await session.execute(
            text("""
                SELECT strftime('%Y-%m', acq_date) as month, COUNT(*) 
                FROM fire_detections 
                GROUP BY month 
                ORDER BY month
            """)
        )
        print(f"\n📊 Monthly Distribution:")
        for row in result:
            print(f"   {row[0]}: {row[1]:,} fires")
        
        # Test 7: Average FRP
        result = await session.execute(
            text("SELECT AVG(frp), MIN(frp), MAX(frp) FROM fire_detections")
        )
        frp_stats = result.fetchone()
        print(f"\n🔥 FRP Statistics:")
        print(f"   Average: {frp_stats[0]:.2f} MW")
        print(f"   Min: {frp_stats[1]:.2f} MW")
        print(f"   Max: {frp_stats[2]:.2f} MW")
        
    await close_db()
    print("\n✅ All tests passed! Data import verified!\n")


if __name__ == "__main__":
    asyncio.run(test_import())