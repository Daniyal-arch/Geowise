"""
GEOWISE - Minimal Analysis Model Test (Standalone)
Run this directly with: python tests/test_analysis_minimal.py

This is a simplified test that doesn't require pytest or complex imports.
Just verifies the analysis.py model works correctly.
"""

import sys
import os
import asyncio
from datetime import datetime

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import from app
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Import Base from your actual database module
from app.database import Base

# Import the model (it already uses the correct Base)
from app.models.analysis import AnalysisResult


async def run_tests():
    """Run basic tests on AnalysisResult model."""
    
    print("🧪 GEOWISE Analysis Model - Minimal Test Suite")
    print("=" * 70)
    print()
    
    # Create in-memory test database
    print("📦 Setting up test database...")
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session maker
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    print("✅ Test database ready\n")
    
    # TEST 1: Create Analysis
    print("-" * 70)
    print("TEST 1: Create and Save Analysis")
    print("-" * 70)
    
    async with async_session_maker() as session:
        try:
            analysis = AnalysisResult(
                analysis_type="fire_temperature",
                analysis_name="Test Analysis",
                region_type="country",
                region_identifier="PAK",
                region_name="Pakistan",
                h3_resolution=5,
                primary_dataset="fires",
                secondary_dataset="climate",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 1, 31),
                correlation_coefficient=0.73,
                p_value=0.001,
                is_significant=True
            )
            
            # Set empty results (good practice)
            analysis.results = {}
            
            session.add(analysis)
            await session.commit()
            
            print(f"✅ Created analysis: {analysis.id}")
            print(f"   Type: {analysis.analysis_type}")
            print(f"   Region: {analysis.region_name}")
            print(f"   Correlation: {analysis.correlation_coefficient}")
            print()
            
            saved_id = analysis.id
            
        except Exception as e:
            print(f"❌ TEST 1 FAILED: {e}")
            return False
    
    # TEST 2: Retrieve Analysis
    print("-" * 70)
    print("TEST 2: Retrieve Analysis by ID")
    print("-" * 70)
    
    async with async_session_maker() as session:
        try:
            result = await session.get(AnalysisResult, saved_id)
            
            if result is None:
                print("❌ TEST 2 FAILED: Analysis not found")
                return False
            
            print(f"✅ Retrieved analysis: {result.id}")
            print(f"   Type: {result.analysis_type}")
            print(f"   Correlation: {result.correlation_coefficient}")
            print()
            
        except Exception as e:
            print(f"❌ TEST 2 FAILED: {e}")
            return False
    
    # TEST 3: JSON Properties
    print("-" * 70)
    print("TEST 3: JSON Properties (datasets, results)")
    print("-" * 70)
    
    async with async_session_maker() as session:
        try:
            analysis = AnalysisResult(
                analysis_type="test_json",
                region_type="country",
                region_identifier="TEST",
                h3_resolution=5,
                primary_dataset="fires",
                secondary_dataset="climate",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 1, 31)
            )
            
            # Test datasets property
            analysis.datasets = ["fires", "climate", "forest"]
            
            # Test results property
            analysis.results = {
                "correlation": 0.73,
                "cells": 125,
                "details": {"method": "pearson"}
            }
            
            session.add(analysis)
            await session.commit()
            
            # Retrieve and verify
            result = await session.get(AnalysisResult, analysis.id)
            
            if result.datasets != ["fires", "climate", "forest"]:
                print(f"❌ Datasets mismatch: {result.datasets}")
                return False
            
            if result.results["correlation"] != 0.73:
                print(f"❌ Results mismatch: {result.results}")
                return False
            
            print(f"✅ JSON properties work correctly")
            print(f"   Datasets: {result.datasets}")
            print(f"   Results keys: {list(result.results.keys())}")
            print()
            
        except Exception as e:
            print(f"❌ TEST 3 FAILED: {e}")
            return False
    
    # TEST 4: Cache Lookup
    print("-" * 70)
    print("TEST 4: Cache Lookup")
    print("-" * 70)
    
    async with async_session_maker() as session:
        try:
            # Create analysis with specific parameters
            start_date = datetime(2025, 2, 1)
            end_date = datetime(2025, 2, 28)
            
            analysis = AnalysisResult(
                analysis_type="fire_temperature",
                region_type="country",
                region_identifier="IND",
                h3_resolution=5,
                primary_dataset="fires",
                secondary_dataset="climate",
                start_date=start_date,
                end_date=end_date,
                correlation_coefficient=0.85
            )
            
            session.add(analysis)
            await session.commit()
            
            # Try to find it
            cached = await AnalysisResult.find_cached_analysis(
                session,
                "fire_temperature",
                "IND",
                start_date,
                end_date,
                5
            )
            
            if cached is None:
                print("❌ Cache lookup failed: Should have found analysis")
                return False
            
            if cached.id != analysis.id:
                print("❌ Cache lookup failed: Wrong analysis returned")
                return False
            
            print(f"✅ Cache lookup works")
            print(f"   Found analysis: {cached.id}")
            print(f"   Correlation: {cached.correlation_coefficient}")
            print()
            
        except Exception as e:
            print(f"❌ TEST 4 FAILED: {e}")
            return False
    
    # TEST 5: Cache Key Generation
    print("-" * 70)
    print("TEST 5: Cache Key Generation")
    print("-" * 70)
    
    try:
        key1 = AnalysisResult.create_cache_key(
            "fire_temperature",
            "PAK",
            ["fires", "climate"],
            datetime(2025, 1, 1),
            datetime(2025, 1, 31),
            5
        )
        
        key2 = AnalysisResult.create_cache_key(
            "fire_temperature",
            "PAK",
            ["fires", "climate"],
            datetime(2025, 1, 1),
            datetime(2025, 1, 31),
            5
        )
        
        key3 = AnalysisResult.create_cache_key(
            "fire_temperature",
            "IND",  # Different region
            ["fires", "climate"],
            datetime(2025, 1, 1),
            datetime(2025, 1, 31),
            5
        )
        
        if key1 != key2:
            print(f"❌ Same parameters should generate same key")
            print(f"   Key 1: {key1}")
            print(f"   Key 2: {key2}")
            return False
        
        if key1 == key3:
            print(f"❌ Different parameters should generate different keys")
            return False
        
        print(f"✅ Cache key generation works")
        print(f"   Same params: {key1[:50]}...")
        print(f"   Diff params: {key3[:50]}...")
        print()
        
    except Exception as e:
        print(f"❌ TEST 5 FAILED: {e}")
        return False
    
    # TEST 6: to_dict() Conversion
    print("-" * 70)
    print("TEST 6: to_dict() API Response Conversion")
    print("-" * 70)
    
    async with async_session_maker() as session:
        try:
            analysis = AnalysisResult(
                analysis_type="fire_temperature",
                analysis_name="API Test",
                region_type="country",
                region_identifier="PAK",
                region_name="Pakistan",
                h3_resolution=5,
                primary_dataset="fires",
                secondary_dataset="climate",
                start_date=datetime(2025, 1, 1),
                end_date=datetime(2025, 1, 31),
                correlation_coefficient=0.73,
                p_value=0.001,
                is_significant=True
            )
            
            analysis.datasets = ["fires", "climate"]
            analysis.results = {"test": "data"}
            
            session.add(analysis)
            await session.commit()
            
            # Convert to dict
            result_dict = analysis.to_dict()
            
            # Verify structure
            required_keys = ["id", "analysis_type", "region", "datasets", 
                           "statistics", "metadata"]
            
            for key in required_keys:
                if key not in result_dict:
                    print(f"❌ Missing key in to_dict(): {key}")
                    return False
            
            if result_dict["statistics"]["correlation_coefficient"] != 0.73:
                print(f"❌ Incorrect correlation in to_dict()")
                return False
            
            print(f"✅ to_dict() conversion works")
            print(f"   Keys: {list(result_dict.keys())}")
            print(f"   Region name: {result_dict['region']['name']}")
            print()
            
        except Exception as e:
            print(f"❌ TEST 6 FAILED: {e}")
            return False
    
    # Cleanup
    await engine.dispose()
    
    return True


def main():
    """Run all tests."""
    try:
        success = asyncio.run(run_tests())
        
        print("=" * 70)
        if success:
            print("✅ ALL TESTS PASSED!")
            print()
            print("Your analysis.py model is working correctly.")
            print("Ready to move to Phase 3 (Pydantic Schemas)!")
        else:
            print("❌ SOME TESTS FAILED")
            print()
            print("Check the error messages above.")
        print("=" * 70)
        
        return 0 if success else 1
        
    except Exception as e:
        print("=" * 70)
        print(f"❌ FATAL ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())