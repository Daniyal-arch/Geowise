"""
GEOWISE - Forest Monitor Tests (SQLite Compatible)
tests/test_forest.py

Tests the ForestMonitor class with real GFW API calls.
No database mocking needed - tests actual API integration.

WHY THESE TESTS:
- Verify API connectivity
- Validate data structure
- Ensure error handling works
- Test business logic (trend analysis)
"""

import unittest
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.forest import ForestMonitor


class TestForestMonitor(unittest.TestCase):
    """
    Test suite for ForestMonitor
    
    NOTE: These are INTEGRATION tests, not unit tests
    - They make real API calls to GFW
    - They require internet connection
    - They test the actual data pipeline
    """
    
    @classmethod
    def setUpClass(cls):
        """
        Set up test fixtures
        
        WHY classmethod:
        - Runs once before all tests
        - Shares ForestMonitor instance across tests
        - More efficient than creating new instance per test
        """
        cls.monitor = ForestMonitor()
        print("\n" + "="*70)
        print("🧪 RUNNING FOREST MONITOR TESTS")
        print("="*70)
    
    def test_01_initialization(self):
        """Test ForestMonitor initialization"""
        self.assertIsNotNone(self.monitor)
        self.assertIsNotNone(self.monitor.gfw_api_key)
        self.assertEqual(self.monitor.base_url, "https://data-api.globalforestwatch.org")
        print(f"✅ Initialization: API Key loaded")
    
    def test_02_health_check(self):
        """Test API health check"""
        health = self.monitor.health_check()
        
        self.assertIsNotNone(health)
        self.assertIn("status", health)
        self.assertIn("api_accessible", health)
        
        print(f"✅ Health Check: API Status = {health['status']}")
        
        # Skip remaining tests if API is not accessible
        if not health['api_accessible']:
            self.skipTest("GFW API not accessible")
    
    def test_03_get_country_geostore(self):
        """Test getting country geostore"""
        geostore = self.monitor.get_country_geostore("PAK")
        
        self.assertIsNotNone(geostore, "Geostore should not be None")
        self.assertIn("id", geostore)
        self.assertIn("attributes", geostore)
        
        # Verify geostore has geometry
        attributes = geostore.get("attributes", {})
        self.assertIn("geojson", attributes)
        
        print(f"✅ Geostore: ID = {geostore['id']}")
    
    def test_04_get_yearly_tree_loss(self):
        """Test fetching yearly tree loss data"""
        data = self.monitor.get_yearly_tree_loss("PAK")
        
        self.assertIsNotNone(data, "Data should not be None")
        self.assertIn("yearly_data", data)
        
        yearly_data = data["yearly_data"]
        self.assertIsInstance(yearly_data, list)
        self.assertGreater(len(yearly_data), 0, "Should have at least 1 year of data")
        
        # Verify data structure
        first_year = yearly_data[0]
        self.assertIn("year", first_year)
        self.assertIn("loss_ha", first_year)
        
        print(f"✅ Yearly Data: Got {len(yearly_data)} years")
        print(f"   Range: {yearly_data[0]['year']} to {yearly_data[-1]['year']}")
    
    def test_05_get_yearly_tree_loss_with_filters(self):
        """Test yearly data with year filters"""
        # Get data for 2020-2024 only
        data = self.monitor.get_yearly_tree_loss("PAK", start_year=2020, end_year=2024)
        
        self.assertIsNotNone(data)
        yearly_data = data["yearly_data"]
        
        # Verify all years are within range
        for item in yearly_data:
            year = item["year"]
            self.assertGreaterEqual(year, 2020)
            self.assertLessEqual(year, 2024)
        
        print(f"✅ Filtered Data: Got {len(yearly_data)} years (2020-2024)")
    
    def test_06_get_country_forest_stats(self):
        """Test fetching complete forest statistics"""
        stats = self.monitor.get_country_forest_stats("PAK")
        
        self.assertIsNotNone(stats, "Stats should not be None")
        self.assertIn("country_iso", stats)
        self.assertIn("country_name", stats)
        self.assertIn("geostore_id", stats)
        self.assertIn("tree_cover_loss", stats)
        
        # Verify tree cover loss data
        if stats["tree_cover_loss"]:
            loss = stats["tree_cover_loss"]
            self.assertIn("total_loss_ha", loss)
            self.assertIn("recent_year", loss)
            self.assertIn("yearly_data", loss)
            
            print(f"✅ Forest Stats: {stats['country_name']}")
            print(f"   Total Loss: {loss['total_loss_ha']:,.0f} ha")
            print(f"   Recent Year: {loss['recent_year']}")
        else:
            print("⚠️ No tree cover loss data available")
    
    def test_07_analyze_deforestation_trend(self):
        """Test deforestation trend analysis"""
        trend = self.monitor.analyze_deforestation_trend("PAK")
        
        self.assertIsNotNone(trend)
        self.assertIn("country_iso", trend)
        self.assertIn("trend", trend)
        
        # Trend should be one of: INCREASING, DECREASING, STABLE, NO_DATA, INSUFFICIENT_DATA
        valid_trends = ["INCREASING", "DECREASING", "STABLE", "NO_DATA", "INSUFFICIENT_DATA"]
        self.assertIn(trend["trend"], valid_trends)
        
        if trend["trend"] not in ["NO_DATA", "INSUFFICIENT_DATA"]:
            self.assertIn("severity", trend)
            self.assertIn("change_percent", trend)
            print(f"✅ Trend Analysis: {trend['trend']} ({trend['severity']})")
            print(f"   Change: {trend['change_percent']}%")
        else:
            print(f"✅ Trend: {trend['trend']}")
    
    def test_08_get_tile_configuration(self):
        """Test getting tile configuration"""
        config = self.monitor.get_tile_configuration()
        
        self.assertIsNotNone(config)
        self.assertIn("tile_layers", config)
        
        tile_layers = config["tile_layers"]
        self.assertGreater(len(tile_layers), 0, "Should have at least 1 tile layer")
        
        # Verify tile structure
        for layer_id, layer_info in tile_layers.items():
            self.assertIn("url", layer_info)
            self.assertIn("description", layer_info)
            self.assertIn("min_zoom", layer_info)
            self.assertIn("max_zoom", layer_info)
        
        print(f"✅ Tile Config: {len(tile_layers)} layers available")
    
    def test_09_get_tile_configuration_filtered(self):
        """Test getting specific tile layers"""
        config = self.monitor.get_tile_configuration(layers=["tree_cover_loss"])
        
        self.assertIsNotNone(config)
        tile_layers = config["tile_layers"]
        self.assertEqual(len(tile_layers), 1)
        self.assertIn("tree_cover_loss", tile_layers)
        
        print(f"✅ Filtered Tiles: Got 1 layer")
    
    def test_10_get_available_countries(self):
        """Test getting available countries"""
        countries = self.monitor.get_available_countries()
        
        self.assertIsInstance(countries, list)
        self.assertGreater(len(countries), 0)
        self.assertIn("PAK", countries)
        
        print(f"✅ Available Countries: {len(countries)} countries")
    
    def test_11_invalid_country(self):
        """Test handling of invalid country code"""
        stats = self.monitor.get_country_forest_stats("INVALID")
        
        # Should return None for invalid country
        self.assertIsNone(stats)
        print("✅ Invalid Country: Handled correctly")
    
    def test_12_multiple_countries(self):
        """Test getting data for multiple countries"""
        countries = ["PAK", "IND", "BGD"]
        results = {}
        
        for country in countries:
            stats = self.monitor.get_country_forest_stats(country)
            if stats and stats.get("tree_cover_loss"):
                results[country] = stats["tree_cover_loss"]["total_loss_ha"]
        
        self.assertGreater(len(results), 0, "Should get data for at least one country")
        print(f"✅ Multiple Countries: Got data for {len(results)} countries")
        for country, loss in results.items():
            print(f"   {country}: {loss:,.0f} ha")


def run_tests():
    """
    Run all tests with detailed output
    
    WHY THIS FUNCTION:
    - Allows running tests from command line: python test_forest.py
    - Provides summary statistics
    - Returns exit code for CI/CD integration
    """
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestForestMonitor)
    
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