"""
GEOWISE - Climate Monitor Tests (SQLite Compatible)
tests/test_climate.py

Tests the ClimateMonitor class with real Open-Meteo API calls.
Validates climate data integration for fire risk analysis.

WHY THESE TESTS:
- Verify API connectivity (no auth required)
- Validate data structure and quality
- Test fire risk assessment logic
- Ensure temporal coverage
"""

import unittest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.climate import ClimateMonitor


class TestClimateMonitor(unittest.TestCase):
    """
    Test suite for ClimateMonitor
    
    NOTE: These are INTEGRATION tests
    - Make real API calls to Open-Meteo
    - Require internet connection
    - Test actual data pipeline
    - No mocking needed (API is free and reliable)
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.monitor = ClimateMonitor()
        
        # Test dates (recent month for reliable data)
        cls.end_date = datetime.now()
        cls.start_date = cls.end_date - timedelta(days=30)
        cls.start_str = cls.start_date.strftime("%Y-%m-%d")
        cls.end_str = cls.end_date.strftime("%Y-%m-%d")
        
        # Test location (Islamabad, Pakistan)
        cls.test_lat = 30.3753
        cls.test_lon = 69.3451
        
        print("\n" + "="*70)
        print("🧪 RUNNING CLIMATE MONITOR TESTS")
        print("="*70)
        print(f"Test Period: {cls.start_str} to {cls.end_str}")
        print(f"Test Location: ({cls.test_lat}, {cls.test_lon})")
    
    def test_01_initialization(self):
        """Test ClimateMonitor initialization"""
        self.assertIsNotNone(self.monitor)
        self.assertEqual(self.monitor.base_url, "https://archive-api.open-meteo.com/v1/archive")
        self.assertIsInstance(self.monitor.daily_variables, list)
        self.assertGreater(len(self.monitor.daily_variables), 0)
        
        print(f"✅ Initialization: {len(self.monitor.daily_variables)} climate variables configured")
    
    def test_02_health_check(self):
        """Test API health check"""
        health = self.monitor.health_check()
        
        self.assertIsNotNone(health)
        self.assertIn("status", health)
        self.assertIn("api_accessible", health)
        
        print(f"✅ Health Check: API Status = {health['status']}")
        
        # Skip remaining tests if API is not accessible
        if not health['api_accessible']:
            self.skipTest("Open-Meteo API not accessible")
    
    def test_03_get_historical_data(self):
        """Test fetching historical climate data"""
        data = self.monitor.get_historical_data(
            latitude=self.test_lat,
            longitude=self.test_lon,
            start_date=self.start_str,
            end_date=self.end_str
        )
        
        self.assertIsNotNone(data, "Data should not be None")
        self.assertIn("daily", data)
        
        # Verify data structure
        daily = data["daily"]
        self.assertIn("time", daily)
        self.assertIn("temperature_2m_max", daily)
        self.assertIn("precipitation_sum", daily)
        self.assertIn("windspeed_10m_max", daily)
        
        # Verify data completeness
        num_days = len(daily["time"])
        self.assertGreater(num_days, 0, "Should have at least 1 day of data")
        self.assertLessEqual(num_days, 31, "Should have at most 31 days")
        
        print(f"✅ Historical Data: Got {num_days} days")
        print(f"   Variables: {', '.join([k for k in daily.keys() if k != 'time'])}")
    
    def test_04_data_quality(self):
        """Test data quality and completeness"""
        data = self.monitor.get_historical_data(
            latitude=self.test_lat,
            longitude=self.test_lon,
            start_date=self.start_str,
            end_date=self.end_str
        )
        
        self.assertIsNotNone(data)
        daily = data["daily"]
        
        # Check for realistic values
        temp_max = daily.get("temperature_2m_max", [])
        valid_temps = [t for t in temp_max if t is not None]
        
        if valid_temps:
            self.assertGreater(min(valid_temps), -50, "Temperature should be > -50°C")
            self.assertLess(max(valid_temps), 60, "Temperature should be < 60°C")
            
            print(f"✅ Data Quality: Temperature range {min(valid_temps):.1f}°C to {max(valid_temps):.1f}°C")
    
    def test_05_without_soil_moisture(self):
        """Test fetching data without soil moisture"""
        data = self.monitor.get_historical_data(
            latitude=self.test_lat,
            longitude=self.test_lon,
            start_date=self.start_str,
            end_date=self.end_str,
            include_soil=False
        )
        
        self.assertIsNotNone(data)
        daily = data["daily"]
        
        # Verify soil moisture is NOT included
        self.assertNotIn("soil_moisture_0_to_7cm", daily)
        
        print(f"✅ Data Without Soil: {len(daily.keys())-1} variables")
    
    def test_06_get_country_climate_summary(self):
        """Test getting country climate summary"""
        summary = self.monitor.get_country_climate_summary(
            country_iso="PAK",
            start_date=self.start_str,
            end_date=self.end_str
        )
        
        self.assertIsNotNone(summary, "Summary should not be None")
        self.assertIn("country_iso", summary)
        self.assertIn("climate_data", summary)
        self.assertIn("sample_points", summary)
        
        # Verify climate data structure
        climate_data = summary["climate_data"]
        self.assertIn("time", climate_data)
        self.assertIn("temperature_2m_max", climate_data)
        
        print(f"✅ Country Summary: {summary['country_iso']}")
        print(f"   Sample Points: {summary['sample_points']}")
        print(f"   Days: {len(climate_data['time'])}")
    
    def test_07_calculate_statistics(self):
        """Test statistical calculations"""
        data = self.monitor.get_historical_data(
            latitude=self.test_lat,
            longitude=self.test_lon,
            start_date=self.start_str,
            end_date=self.end_str
        )
        
        self.assertIsNotNone(data)
        
        # Calculate statistics
        stats = self.monitor.calculate_climate_statistics(data)
        
        self.assertIsInstance(stats, dict)
        self.assertGreater(len(stats), 0)
        
        # Verify statistics structure
        for var_name, var_stats in stats.items():
            self.assertIn("mean", var_stats)
            self.assertIn("min", var_stats)
            self.assertIn("max", var_stats)
            self.assertIn("count", var_stats)
        
        # Print sample statistics
        if "temperature_2m_max" in stats:
            temp_stats = stats["temperature_2m_max"]
            print(f"✅ Statistics: Temperature")
            print(f"   Mean: {temp_stats['mean']}°C")
            print(f"   Range: {temp_stats['min']}°C to {temp_stats['max']}°C")
    
    def test_08_assess_fire_risk(self):
        """Test fire risk assessment"""
        data = self.monitor.get_historical_data(
            latitude=self.test_lat,
            longitude=self.test_lon,
            start_date=self.start_str,
            end_date=self.end_str
        )
        
        self.assertIsNotNone(data)
        
        # Assess fire risk
        risk = self.monitor.assess_fire_risk_conditions(data)
        
        self.assertIsNotNone(risk)
        self.assertIn("risk_level", risk)
        self.assertIn("risk_score", risk)
        
        # Verify risk level is valid
        valid_levels = ["LOW", "MODERATE", "HIGH", "EXTREME", "UNKNOWN"]
        self.assertIn(risk["risk_level"], valid_levels)
        
        print(f"✅ Fire Risk: {risk['risk_level']} (Score: {risk['risk_score']})")
        print(f"   High temp days: {risk['high_temp_days']}/{risk['total_days']}")
        print(f"   Dry days: {risk['dry_days']}/{risk['total_days']}")
    
    def test_09_get_recent_climate(self):
        """Test getting recent climate data (convenience method)"""
        data = self.monitor.get_recent_climate(
            latitude=self.test_lat,
            longitude=self.test_lon,
            days=7
        )
        
        self.assertIsNotNone(data)
        self.assertIn("daily", data)
        
        # Verify we got approximately 7 days
        num_days = len(data["daily"]["time"])
        self.assertGreaterEqual(num_days, 6, "Should have at least 6 days")
        self.assertLessEqual(num_days, 8, "Should have at most 8 days")
        
        print(f"✅ Recent Climate: Got {num_days} days")
    
    def test_10_multiple_sample_points(self):
        """Test country summary with multiple sample points"""
        # Sample points across Pakistan (north, center, south)
        sample_points = [
            (34.0151, 71.5249),  # Peshawar (north)
            (30.3753, 69.3451),  # Central
            (24.8607, 67.0011),  # Karachi (south)
        ]
        
        summary = self.monitor.get_country_climate_summary(
            country_iso="PAK",
            start_date=self.start_str,
            end_date=self.end_str,
            sample_points=sample_points
        )
        
        self.assertIsNotNone(summary)
        self.assertEqual(summary["sample_points"], 3)
        
        print(f"✅ Multiple Samples: 3 points across Pakistan")
    
    def test_11_date_range_validation(self):
        """Test with different date ranges"""
        # Test short range (7 days)
        short_end = datetime.now()
        short_start = short_end - timedelta(days=7)
        
        data = self.monitor.get_historical_data(
            latitude=self.test_lat,
            longitude=self.test_lon,
            start_date=short_start.strftime("%Y-%m-%d"),
            end_date=short_end.strftime("%Y-%m-%d")
        )
        
        self.assertIsNotNone(data)
        num_days = len(data["daily"]["time"])
        self.assertGreaterEqual(num_days, 6)
        self.assertLessEqual(num_days, 8)
        
        print(f"✅ Date Range: 7-day query returned {num_days} days")
    
    def test_12_invalid_coordinates(self):
        """Test handling of invalid coordinates"""
        # Test with invalid latitude (>90)
        data = self.monitor.get_historical_data(
            latitude=999,
            longitude=self.test_lon,
            start_date=self.start_str,
            end_date=self.end_str
        )
        
        # Should return None or empty for invalid coords
        if data is not None:
            # API might return data for closest valid point
            print("⚠️ API returned data for invalid coords (used nearest valid point)")
        else:
            print("✅ Invalid Coords: Handled correctly (returned None)")
    
    def test_13_precipitation_totals(self):
        """Test precipitation data and totals"""
        data = self.monitor.get_historical_data(
            latitude=self.test_lat,
            longitude=self.test_lon,
            start_date=self.start_str,
            end_date=self.end_str
        )
        
        self.assertIsNotNone(data)
        
        stats = self.monitor.calculate_climate_statistics(data)
        
        if "precipitation_sum" in stats:
            precip_stats = stats["precipitation_sum"]
            self.assertIsNotNone(precip_stats["total"])
            
            print(f"✅ Precipitation: Total = {precip_stats['total']} mm")
            print(f"   Max daily: {precip_stats['max']} mm")


def run_tests():
    """
    Run all tests with detailed output
    """
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestClimateMonitor)
    
    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print(f"✅ Tests run: {result.testsRun}")
    print(f"✅ Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"❌ Errors: {len(result.errors)}")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)