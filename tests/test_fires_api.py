"""
Test FireDetection model with ACTUAL NASA FIRMS data - SQLite Compatible
"""

import asyncio
import sys
import os
from datetime import datetime
import h3

# Add backend to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.models.fires import FireDetection
from app.database import DatabaseManager, Base
from app.config import settings
from sqlalchemy import select


class NASAFirmsTest:
    def __init__(self):
        self.test_fire_data = [
            {
                'latitude': 24.60966,
                'longitude': 67.68450,
                'bright_ti4': 335.25,
                'scan': 0.63,
                'track': 0.72,
                'acq_date': '2025-11-01',
                'acq_time': '746',
                'satellite': 'N',
                'instrument': 'VIIRS',
                'confidence': 'n',
                'version': '2.0NRT',
                'bright_ti5': 303.58,
                'frp': 3.80,
                'daynight': 'D'
            }
        ]
        
        # Use a fresh database manager with test database
        self.db_manager = DatabaseManager("sqlite+aiosqlite:///./test_geowise.db")
    
    def get_h3_function(self):
        """Get the correct H3 function based on installed version"""
        if hasattr(h3, 'latlng_to_cell'):
            return h3.latlng_to_cell
        elif hasattr(h3, 'geo_to_h3'):
            return h3.geo_to_h3
        else:
            raise AttributeError("No compatible H3 function found")
    
    async def test_basic_fire_creation(self):
        """Test basic fire creation without database"""
        try:
            print("🚀 Step 1: Testing basic FireDetection creation...")
            
            fire_data = self.test_fire_data[0]
            
            # Test H3 function directly
            h3_func = self.get_h3_function()
            print(f"✅ Using H3 function: {h3_func.__name__}")
            
            latitude = fire_data['latitude']
            longitude = fire_data['longitude']
            
            h3_9 = h3_func(latitude, longitude, 9)
            print(f"✅ H3 function works: {h3_9}")
            
            # Create fire instance
            clean_data = {k: v for k, v in fire_data.items() 
                         if k not in ['latitude', 'longitude']}
            
            fire = FireDetection(
                latitude=latitude,
                longitude=longitude,
                **clean_data
            )
            
            print(f"✅ Fire creation SUCCESS:")
            print(f"   - Location: {fire.latitude}, {fire.longitude}")
            print(f"   - H3_9: {fire.h3_index_9}")
            print(f"   - Brightness: {fire.brightness}")
            print(f"   - FRP: {fire.frp}")
            
            return True
                
        except Exception as e:
            print(f"❌ Basic test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_database_operations(self):
        """Test database operations with SQLite"""
        try:
            print("\n🚀 Step 2: Testing SQLite database operations...")
            print(f"📁 Database URL: {self.db_manager.database_url}")
            
            # Create test fire
            fire_data = self.test_fire_data[0]
            clean_data = {k: v for k, v in fire_data.items() 
                         if k not in ['latitude', 'longitude']}
            
            test_fire = FireDetection(
                latitude=fire_data['latitude'],
                longitude=fire_data['longitude'],
                **clean_data
            )
            
            # Connect to SQLite database
            await self.db_manager.connect()
            await self.db_manager.create_tables()
            print("✅ Database connected and tables created")
            
            # Use the session properly
            async with self.db_manager.async_session_maker() as session:
                # Add and commit
                session.add(test_fire)
                await session.commit()
                print("✅ Fire saved to SQLite database!")
                
                # Query to verify
                result = await session.execute(select(FireDetection))
                saved_fires = result.scalars().all()
                print(f"📊 Total fires in database: {len(saved_fires)}")
                
                if saved_fires:
                    fire = saved_fires[0]
                    print(f"📋 Retrieved fire:")
                    print(f"   - ID: {fire.id}")
                    print(f"   - Location: {fire.latitude}, {fire.longitude}")
                    print(f"   - FRP: {fire.frp}")
                    print(f"   - H3_9: {fire.h3_index_9}")
                    return True
                else:
                    print("❌ No fires found in database")
                    return False
                    
        except Exception as e:
            print(f"❌ Database operation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await self.db_manager.disconnect()


async def main():
    """Run the NASA FIRMS integration test"""
    print("=" * 60)
    print("🚀 STARTING NASA FIRMS TEST - SQLite Version")
    print("=" * 60)
    
    # Show current configuration
    print(f"🔧 Configuration:")
    print(f"   - DATABASE_URL: {settings.DATABASE_URL}")
    print(f"   - ENVIRONMENT: {settings.ENVIRONMENT}")
    print(f"   - DEBUG: {settings.DEBUG}")
    
    # Check H3 installation
    print("\n🔍 Checking H3 installation...")
    try:
        h3_version = getattr(h3, '__version__', 'Unknown')
        print(f"H3 version: {h3_version}")
        
        # Test H3 function
        if hasattr(h3, 'latlng_to_cell'):
            test_h3 = h3.latlng_to_cell(24.60966, 67.68450, 9)
            print(f"✅ H3 v4+ compatible (latlng_to_cell): {test_h3}")
        else:
            test_h3 = h3.geo_to_h3(24.60966, 67.68450, 9)
            print(f"✅ H3 v3 compatible (geo_to_h3): {test_h3}")
            
    except Exception as e:
        print(f"❌ H3 check failed: {e}")
        return
    
    tester = NASAFirmsTest()
    
    # Run tests
    basic_success = await tester.test_basic_fire_creation()
    db_success = await tester.test_database_operations() if basic_success else False
    
    print("\n" + "=" * 60)
    if basic_success and db_success:
        print("🎉 ALL TESTS PASSED! SQLite fire model works.")
    else:
        print("❌ TESTS FAILED!")
        if not basic_success:
            print("   - Basic fire creation failed")
        if not db_success:
            print("   - Database operations failed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())