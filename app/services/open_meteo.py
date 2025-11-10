# backend/app/services/open_meteo.py
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import h3
from sqlalchemy.orm import Session
from app.models.climate import ClimateData

class OpenMeteoService:
    """Service to retrieve and process climate data from Open-Meteo API"""
    
    def __init__(self):
        self.base_url = "https://archive-api.open-meteo.com/v1/archive"
        self.timeout = 30
    
    def get_climate_variable_groups(self) -> Dict[str, List[str]]:
        """Return climate variables grouped for efficient API calls"""
        return {
            "core_weather": [
                "temperature_2m_max", "temperature_2m_min", 
                "precipitation_sum", "relative_humidity_2m_mean"
            ],
            "wind_soil": [
                "windspeed_10m_max", "soil_moisture_0_7cm"
            ],
            "energy": [
                "shortwave_radiation_sum", "et0_fao_evapotranspiration"
            ]
        }
    
    def fetch_climate_data(self, lat: float, lon: float, 
                         start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """Fetch climate data using multiple API calls to avoid limits"""
        
        all_dataframes = []
        
        for group_name, variables in self.get_climate_variable_groups().items():
            variable_string = ",".join(variables)
            
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": start_date,
                "end_date": end_date,
                "daily": variable_string,
                "timezone": "UTC"
            }
            
            print(f"🌤️ Fetching {group_name} data...")
            
            try:
                response = requests.get(self.base_url, params=params, timeout=self.timeout)
                
                if response.status_code == 200:
                    data = response.json()
                    daily_data = data.get("daily", {})
                    
                    if daily_data.get("time"):
                        # Create DataFrame for this variable group
                        group_df = pd.DataFrame({"date": pd.to_datetime(daily_data["time"])})
                        
                        # Map API variable names to database column names
                        column_mapping = {
                            "temperature_2m_max": "temperature_max",
                            "temperature_2m_min": "temperature_min", 
                            "precipitation_sum": "precipitation",
                            "relative_humidity_2m_mean": "humidity",
                            "windspeed_10m_max": "wind_speed_max",
                            "soil_moisture_0_7cm": "soil_moisture_0_7cm",
                            "shortwave_radiation_sum": "solar_radiation",
                            "et0_fao_evapotranspiration": "evapotranspiration"
                        }
                        
                        for api_var, db_var in column_mapping.items():
                            if api_var in daily_data:
                                group_df[db_var] = daily_data[api_var]
                        
                        all_dataframes.append(group_df)
                        print(f"   ✅ Retrieved {len(daily_data['time'])} days")
                    else:
                        print(f"   ⚠️ No data in response")
                else:
                    print(f"   ❌ API Error: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Request failed: {e}")
        
        # Merge all dataframes
        if all_dataframes:
            merged_df = all_dataframes[0]
            for df in all_dataframes[1:]:
                merged_df = pd.merge(merged_df, df, on="date", how="outer")
            
            # Add location metadata
            merged_df["latitude"] = lat
            merged_df["longitude"] = lon
            
            print(f"✅ Combined {len(all_dataframes)} data groups → {len(merged_df)} total records")
            return merged_df
        else:
            print("❌ No climate data retrieved")
            return None
    
    def save_climate_data(self, db: Session, climate_df: pd.DataFrame) -> List[ClimateData]:
        """Save climate data to database"""
        
        climate_objects = []
        
        for _, row in climate_df.iterrows():
            # Create ClimateData object
            climate_obj = ClimateData(
                latitude=row["latitude"],
                longitude=row["longitude"],
                date=row["date"].date(),
                temperature_max=row.get("temperature_max"),
                temperature_min=row.get("temperature_min"),
                precipitation=row.get("precipitation"),
                humidity=row.get("humidity"),
                wind_speed_max=row.get("wind_speed_max"),
                soil_moisture_0_7cm=row.get("soil_moisture_0_7cm"),
                solar_radiation=row.get("solar_radiation"),
                evapotranspiration=row.get("evapotranspiration")
            )
            
            # Calculate fire risk
            climate_obj.calculate_fire_risk()
            
            climate_objects.append(climate_obj)
        
        # Bulk save to database
        db.add_all(climate_objects)
        db.commit()
        
        print(f"💾 Saved {len(climate_objects)} climate records to database")
        return climate_objects

# TEST THE COMPLETE WORKFLOW
def test_climate_workflow():
    """Test the complete climate data workflow"""
    
    service = OpenMeteoService()
    
    # Test parameters
    lat, lon = 33.6844, 73.0479  # Islamabad
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)  # Just 7 days for testing
    
    print("🚀 TESTING COMPLETE CLIMATE WORKFLOW")
    print("=" * 50)
    
    # 1. Fetch data
    climate_df = service.fetch_climate_data(lat, lon, 
                                          start_date.strftime("%Y-%m-%d"),
                                          end_date.strftime("%Y-%m-%d"))
    
    if climate_df is not None:
        print(f"\n📊 Retrieved Data Summary:")
        print(f"   Records: {len(climate_df)}")
        print(f"   Variables: {list(climate_df.columns)}")
        print(f"\n📋 Sample Data:")
        print(climate_df.head())
        
        # 2. Calculate fire risk (demonstration)
        print(f"\n🔥 Fire Risk Calculation Demo:")
        for _, row in climate_df.iterrows():
            # Create temporary object to calculate risk
            temp_obj = ClimateData(
                latitude=row["latitude"],
                longitude=row["longitude"], 
                date=row["date"].date(),
                temperature_max=row.get("temperature_max"),
                humidity=row.get("humidity"),
                precipitation=row.get("precipitation")
            )
            temp_obj.calculate_fire_risk()
            print(f"   {row['date'].date()}: {temp_obj.fire_risk_level} "
                  f"(Index: {temp_obj.fire_risk_index:.3f})")
        
        # Save to CSV for inspection
        climate_df.to_csv('climate_workflow_test.csv', index=False)
        print(f"\n💾 Saved: climate_workflow_test.csv")
        
        return climate_df
    
    return None

# Run the test
test_result = test_climate_workflow()