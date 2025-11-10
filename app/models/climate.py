"""
GEOWISE - Climate Data Integration (SQLite Compatible)
app/models/climate.py

Integrates Open-Meteo climate data for environmental analysis.
Provides historical weather data (ERA5 reanalysis) at ~25km resolution.

WHY OPEN-METEO:
- Free, no API key required
- High-quality ERA5 reanalysis data
- Simple REST API
- Historical data from 1940 to present
- Perfect for correlation analysis with fire/forest data

RESOLUTION NOTE:
- Native resolution: ~25km grid (coarsest of all datasets)
- This becomes the ANALYSIS resolution for correlations
- Fire/Forest data must be aggregated UP to 25km for valid statistics
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


class ClimateMonitor:
    """
    Open-Meteo Climate Data Integration
    
    Provides access to:
    1. Historical daily weather data (temperature, precipitation, wind)
    2. Soil moisture data (important for fire risk)
    3. Time series for trend analysis
    
    ARCHITECTURE NOTE:
    - This is a SERVICE class (like ForestMonitor)
    - Fetches data on-demand from Open-Meteo API
    - Results can be cached in SQLite for performance
    - No spatial database required
    
    DATA SCOPE (per project requirements):
    - Temperature: 2m max/min (°C)
    - Precipitation: Daily sum (mm)
    - Wind Speed: 10m max (km/h)
    - Soil Moisture: 0-7cm depth (m³/m³)
    """
    
    def __init__(self):
        """
        Initialize Climate Monitor
        
        WHY NO API KEY:
        - Open-Meteo is free and doesn't require authentication
        - Rate limits are generous for non-commercial use
        - Perfect for research/development
        """
        self.base_url = "https://archive-api.open-meteo.com/v1/archive"
        self.forecast_url = "https://api.open-meteo.com/v1/forecast"
        
        # Climate variables we're tracking (per project scope)
        # Using GUARANTEED working variables based on testing
        self.daily_variables = [
            "temperature_2m_max",           # Max temperature (°C)
            "temperature_2m_min",           # Min temperature (°C) 
            "precipitation_sum",            # Total precipitation (mm)
            "windspeed_10m_max",            # Max wind speed (km/h)
            "relative_humidity_2m_mean",    # Mean relative humidity (%)
        ]
        
        # Soil moisture - OPTIONAL (not always available)
        # Only include if specifically requested
        self.optional_variables = [
            "soil_moisture_0_to_7cm"   # Surface soil moisture (m³/m³)
        ]
        
        logger.info("Open-Meteo ClimateMonitor initialized (SQLite mode)")
    
    def get_historical_data(self, 
                           latitude: float,
                           longitude: float,
                           start_date: str,
                           end_date: str,
                           include_soil: bool = False) -> Optional[Dict]:
        """
        Get historical climate data for a location
        
        Args:
            latitude: Latitude (-90 to 90)
            longitude: Longitude (-180 to 180)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            include_soil: Include soil moisture data (default: False - not always available)
        
        Returns:
            Dict with daily time series data
        
        TESTED & WORKING:
        - Successfully retrieved 31 days for Pakistan
        - Core variables (temp, precip, wind, humidity) always available
        - Soil moisture optional (not in all regions/dates)
        """
        try:
            # Build variable list (core variables always included)
            variables = self.daily_variables.copy()
            
            # Optionally add soil moisture (may not always work)
            if include_soil:
                variables.extend(self.optional_variables)
            
            # Build request parameters
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date,
                "end_date": end_date,
                "daily": ",".join(variables),
                "timezone": "UTC"  # Use UTC for consistency
            }
            
            logger.info(f"Fetching climate data for ({latitude}, {longitude})")
            logger.info(f"Date range: {start_date} to {end_date}")
            
            response = requests.get(
                self.base_url,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response
                if "daily" not in data:
                    logger.error("No daily data in response")
                    return None
                
                logger.info(f"✅ Got {len(data['daily']['time'])} days of climate data")
                return data
                
            else:
                logger.error(f"API error: {response.status_code}")
                logger.error(f"Response: {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching climate data: {str(e)}")
            return None
    
    def get_country_climate_summary(self,
                                   country_iso: str,
                                   start_date: str,
                                   end_date: str,
                                   sample_points: Optional[List[Tuple[float, float]]] = None) -> Optional[Dict]:
        """
        Get climate summary for a country
        
        Args:
            country_iso: 3-letter ISO code (for reference only)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            sample_points: List of (lat, lon) tuples to sample
                          If None, uses country center
        
        Returns:
            Dict with aggregated climate statistics
        
        WHY SAMPLING:
        - Countries are large areas (Pakistan = 881,913 km²)
        - 25km resolution means ~1,400 grid cells for Pakistan
        - Sampling key points gives representative data efficiently
        - For detailed analysis, use multiple sample points
        
        DEFAULT COUNTRY CENTERS (can be expanded):
        """
        # Default country centers (expand as needed)
        country_centers = {
            "PAK": (30.3753, 69.3451),   # Pakistan (Islamabad area)
            "IND": (20.5937, 78.9629),   # India (geographic center)
            "BGD": (23.6850, 90.3563),   # Bangladesh (Dhaka)
            "AFG": (33.9391, 67.7100),   # Afghanistan (Kabul)
            "IDN": (-0.7893, 113.9213),  # Indonesia (geographic center)
            "BRA": (-14.2350, -51.9253), # Brazil (Brasília area)
        }
        
        if sample_points is None:
            # Use country center
            if country_iso not in country_centers:
                logger.error(f"No default center for {country_iso}")
                return None
            
            sample_points = [country_centers[country_iso]]
        
        try:
            all_data = []
            
            # Fetch data for each sample point
            for i, (lat, lon) in enumerate(sample_points):
                logger.info(f"Sampling point {i+1}/{len(sample_points)}: ({lat}, {lon})")
                
                data = self.get_historical_data(lat, lon, start_date, end_date)
                if data:
                    all_data.append(data)
            
            if not all_data:
                logger.error("No data retrieved for any sample points")
                return None
            
            # Aggregate data across sample points
            aggregated = self._aggregate_climate_data(all_data)
            
            return {
                "country_iso": country_iso,
                "start_date": start_date,
                "end_date": end_date,
                "sample_points": len(sample_points),
                "coordinates": sample_points,
                "climate_data": aggregated,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting country climate summary: {str(e)}")
            return None
    
    def _aggregate_climate_data(self, data_list: List[Dict]) -> Dict:
        """
        Aggregate climate data from multiple points
        
        WHY AGGREGATION:
        - Multiple sample points need to be combined
        - Takes average across all points for each day
        - Provides regional climate summary
        """
        if not data_list:
            return {}
        
        # Get time series from first dataset
        base_data = data_list[0]["daily"]
        time_series = base_data["time"]
        
        # Initialize aggregated data
        aggregated = {"time": time_series}
        
        # For each variable, average across all sample points
        variables = [v for v in base_data.keys() if v != "time"]
        
        for var in variables:
            values = []
            for data in data_list:
                if var in data["daily"]:
                    values.append(data["daily"][var])
            
            # Average across sample points
            if values:
                aggregated[var] = [
                    sum(v[i] for v in values if v[i] is not None) / len([v for v in values if v[i] is not None])
                    if any(v[i] is not None for v in values) else None
                    for i in range(len(time_series))
                ]
        
        return aggregated
    
    def calculate_climate_statistics(self, climate_data: Dict) -> Dict:
        """
        Calculate statistical summaries from climate data
        
        Returns:
            Dict with min, max, mean, total for each variable
        
        WHY STATISTICS:
        - Needed for correlation analysis
        - Identifies extreme events (heat waves, droughts)
        - Provides context for fire risk assessment
        """
        daily = climate_data.get("daily", {})
        stats = {}
        
        for var_name, values in daily.items():
            if var_name == "time":
                continue
            
            # Filter out None values
            valid_values = [v for v in values if v is not None]
            
            if not valid_values:
                stats[var_name] = {
                    "count": 0,
                    "mean": None,
                    "min": None,
                    "max": None,
                    "total": None
                }
                continue
            
            stats[var_name] = {
                "count": len(valid_values),
                "mean": round(sum(valid_values) / len(valid_values), 2),
                "min": round(min(valid_values), 2),
                "max": round(max(valid_values), 2),
                "total": round(sum(valid_values), 2) if "precipitation" in var_name else None
            }
        
        return stats
    
    def assess_fire_risk_conditions(self, climate_data: Dict) -> Dict:
        """
        Assess fire risk based on climate conditions
        
        Returns:
            Dict with risk assessment and contributing factors
        
        FIRE RISK FACTORS:
        - High temperature (>30°C increases risk)
        - Low precipitation (<1mm/day increases risk)
        - High wind speed (>20 km/h spreads fires)
        - Low soil moisture (<0.2 m³/m³ increases risk)
        """
        daily = climate_data.get("daily", {})
        
        if not daily or "time" not in daily:
            return {"risk_level": "UNKNOWN", "message": "Insufficient data"}
        
        # Calculate risk factors
        temp_max = daily.get("temperature_2m_max", [])
        precip = daily.get("precipitation_sum", [])
        wind = daily.get("windspeed_10m_max", [])
        soil = daily.get("soil_moisture_0_to_7cm", [])
        
        # Count high-risk days
        high_temp_days = sum(1 for t in temp_max if t and t > 30)
        dry_days = sum(1 for p in precip if p is not None and p < 1)
        windy_days = sum(1 for w in wind if w and w > 20)
        low_soil_days = sum(1 for s in soil if s and s < 0.2)
        
        total_days = len(daily["time"])
        
        # Calculate risk score (0-100)
        risk_score = (
            (high_temp_days / total_days) * 25 +
            (dry_days / total_days) * 35 +
            (windy_days / total_days) * 20 +
            (low_soil_days / total_days if soil else 0) * 20
        )
        
        # Determine risk level
        if risk_score > 70:
            risk_level = "EXTREME"
        elif risk_score > 50:
            risk_level = "HIGH"
        elif risk_score > 30:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"
        
        return {
            "risk_level": risk_level,
            "risk_score": round(risk_score, 1),
            "total_days": total_days,
            "high_temp_days": high_temp_days,
            "dry_days": dry_days,
            "windy_days": windy_days,
            "low_soil_moisture_days": low_soil_days,
            "assessment": f"{risk_level} fire risk conditions detected"
        }
    
    def get_recent_climate(self, 
                          latitude: float,
                          longitude: float,
                          days: int = 30) -> Optional[Dict]:
        """
        Get recent climate data (convenience method)
        
        Args:
            latitude: Latitude
            longitude: Longitude
            days: Number of days to retrieve (default: 30)
        
        Returns:
            Dict with recent climate data
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        return self.get_historical_data(
            latitude,
            longitude,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
    
    def health_check(self) -> Dict:
        """
        Check if the Open-Meteo API is accessible
        
        Returns:
            Dict with API health status
        """
        try:
            # Test with a simple query (Islamabad, Pakistan, last 7 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            params = {
                "latitude": 30.3753,
                "longitude": 69.3451,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "daily": "temperature_2m_max"
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            api_healthy = response.status_code == 200
            
            return {
                "status": "healthy" if api_healthy else "unhealthy",
                "status_code": response.status_code,
                "api_accessible": api_healthy,
                "base_url": self.base_url,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "api_accessible": False,
                "timestamp": datetime.now().isoformat()
            }