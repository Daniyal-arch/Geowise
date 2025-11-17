"""LLM Orchestrator - Main AI Controller"""

from typing import Dict, Any, Optional
from datetime import date, datetime
import pandas as pd
from scipy.stats import pearsonr

from app.llm.agents import QueryAgent, AnalysisAgent, ReportAgent
from app.llm.rag import vector_store
from app.database import get_db, database_manager
from app.core.aggregation import fire_aggregator
from app.core.correlation import correlation_analyzer
from app.services.nasa_firms import NASAFIRMSService
from app.models.forest import ForestMonitor
from app.models.climate import ClimateMonitor, ClimateService
from app.config import settings
from app.utils.logger import get_logger
from sqlalchemy import text

logger = get_logger(__name__)


class LLMOrchestrator:
    """
    Main AI orchestrator that coordinates all agents
    
    Flow:
    1. User query → QueryAgent (parse intent & parameters)
    2. Parameters → AnalysisAgent (plan analysis)
    3. Execute analysis (fetch data, run correlations)
    4. Results → ReportAgent (generate insights)
    5. Return to user
    
    ENHANCEMENTS:
    - Monthly fire breakdown queries
    - High FRP fire identification
    - Real statistical correlation analysis (not AI-invented)
    - Historical climate data integration
    """
    
    def __init__(self):
        self.query_agent = QueryAgent()
        self.analysis_agent = AnalysisAgent()
        self.report_agent = ReportAgent()
        self.nasa_service = NASAFIRMSService(api_key=settings.NASA_FIRMS_API_KEY)
        self.forest_monitor = ForestMonitor()
        self.climate_monitor = ClimateMonitor()  # Legacy support
        self.climate_service = ClimateService()  # New comprehensive service
    
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process natural language query end-to-end"""
        
        logger.info(f"Processing query: {user_query}")
        
        # Step 1: Parse query
        parsed = await self.query_agent.parse_query(user_query)
        
        if parsed.get("error"):
            return {
                "status": "error",
                "message": "Failed to understand query",
                "error": parsed["error"]
            }
        
        intent = parsed.get("intent")
        parameters = parsed.get("parameters", {})
        
        logger.info(f"Intent: {intent}, Parameters: {parameters}")
        
        # Step 2: Execute based on intent
        if intent == "query_fires":
            result = await self._query_fires(parameters)

        elif intent == "query_monthly":
            country = parameters.get("country_iso")
            year = parameters.get("year", 2020)
            result = await self._query_monthly_breakdown(country, year)

        elif intent == "query_high_frp":
            country = parameters.get("country_iso")
            year = parameters.get("year", 2020)
            min_frp = parameters.get("min_frp", 100)
            result = await self._query_high_frp_fires(country, year, min_frp)

        elif intent == "analyze_correlation":
            # Check if year is specified for historical correlation
            year = parameters.get("year")
            if year and year < 2025:
                result = await self._analyze_historical_correlation(
                    parameters.get("country_iso"),
                    year
                )
            else:
                result = await self._analyze_correlation(parameters)

        elif intent == "query_forest":
            country = parameters.get("country_iso")
            result = await self._query_forest_loss(country)

        elif intent == "generate_report":
            result = await self._generate_report(parameters)

        else:
            result = {"status": "error", "message": f"Unknown intent: {intent}"}
        
        # Step 3: Generate natural language report
        if result.get("status") != "error":
            report = await self.report_agent.generate_report(result)
            result["report"] = report
        
        return result
    
    async def _query_fires(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Query fire data based on parameters"""
        
        country_iso = parameters.get("country_iso")
        year = parameters.get("year")
        
        logger.info(f"=== _query_fires called ===")
        logger.info(f"Parameters: {parameters}")
        logger.info(f"Country: {country_iso}, Year: {year}")
        
        if not country_iso:
            return {"status": "error", "message": "Country code required"}
        
        try:
            # Historical query
            if year and year < 2025:
                logger.info(f"Historical query branch: {country_iso} {year}")
                
                async with database_manager.async_session_maker() as session:
                    logger.info("Session created successfully")
                    
                    # Get fire count
                    query_sql = """
                        SELECT COUNT(*) 
                        FROM fire_detections 
                        WHERE country = :country 
                        AND strftime('%Y', acq_date) = :year
                    """
                    params = {"country": country_iso, "year": str(year)}
                    
                    logger.info(f"Executing query with params: {params}")
                    
                    result = await session.execute(text(query_sql), params)
                    total_fires = result.scalar()
                    
                    logger.info(f"!!! RESULT: {total_fires} fires !!!")
                    
                    if total_fires is None or total_fires == 0:
                        logger.error(f"Zero or None fires returned!")
                        await session.commit()
                        return {
                            "status": "error",
                            "message": f"No fires found for {country_iso} in {year}"
                        }
                    
                    logger.info(f"Proceeding to get sample fires...")
                    
                    # Get sample fires
                    result = await session.execute(
                        text("""
                            SELECT latitude, longitude, frp, confidence, acq_date, brightness
                            FROM fire_detections 
                            WHERE country = :country 
                            AND strftime('%Y', acq_date) = :year
                            LIMIT 10
                        """),
                        {"country": country_iso, "year": str(year)}
                    )
                    sample_fires = result.fetchall()
                    logger.info(f"Got {len(sample_fires)} sample fires")
                    
                    # Get statistics
                    result = await session.execute(
                        text("""
                            SELECT 
                                AVG(frp) as avg_frp,
                                MAX(frp) as max_frp,
                                AVG(brightness) as avg_brightness,
                                MIN(acq_date) as min_date,
                                MAX(acq_date) as max_date,
                                COUNT(DISTINCT strftime('%m', acq_date)) as months_with_fires
                            FROM fire_detections 
                            WHERE country = :country 
                            AND strftime('%Y', acq_date) = :year
                        """),
                        {"country": country_iso, "year": str(year)}
                    )
                    stats = result.fetchone()
                    logger.info(f"Got stats: {stats}")
                    
                    await session.commit()
                    logger.info("Session committed")
                    
                    # Build result
                    result_data = {
                        "status": "success",
                        "intent": "query_fires",
                        "data": {
                            "country": country_iso,
                            "year": year,
                            "fire_count": total_fires,
                            "data_source": "historical_database",
                            "statistics": {
                                "avg_frp": round(stats[0], 2) if stats[0] else 0,
                                "max_frp": round(stats[1], 2) if stats[1] else 0,
                                "avg_brightness": round(stats[2], 2) if stats[2] else 0,
                                "date_range": {
                                    "start": str(stats[3]) if stats[3] else None,
                                    "end": str(stats[4]) if stats[4] else None
                                },
                                "months_with_fires": stats[5] if stats[5] else 0
                            },
                            "sample_fires": [
                                {
                                    "latitude": float(f[0]),
                                    "longitude": float(f[1]),
                                    "frp": float(f[2]) if f[2] else 0,
                                    "confidence": f[3],
                                    "date": str(f[4]),
                                    "brightness": float(f[5]) if f[5] else 0
                                }
                                for f in sample_fires
                            ]
                        }
                    }
                    
                    logger.info(f"✅ Returning successful result with {total_fires} fires")
                    return result_data
                    
            # Real-time query (no year or year >= 2025)
            else:
                logger.info("Real-time query branch")
                async with self.nasa_service:
                    fires = await self.nasa_service.get_fires_by_country(country_iso, days=7)
                
                if not fires:
                    return {
                        "status": "error",
                        "message": f"No fires detected in {country_iso} (last 7 days)"
                    }
                
                avg_frp = sum(f.frp for f in fires if f.frp) / len([f for f in fires if f.frp]) if fires else 0
                avg_brightness = sum(f.brightness for f in fires if f.brightness) / len(fires)
                
                return {
                    "status": "success",
                    "intent": "query_fires",
                    "data": {
                        "country": country_iso,
                        "fire_count": len(fires),
                        "data_source": "nasa_firms_api",
                        "time_range": "last_7_days",
                        "statistics": {
                            "avg_frp": round(avg_frp, 2),
                            "avg_brightness": round(avg_brightness, 2)
                        },
                        "sample_fires": [
                            {
                                "latitude": f.latitude,
                                "longitude": f.longitude,
                                "frp": f.frp,
                                "brightness": f.brightness,
                                "confidence": f.confidence,
                                "datetime": f.acq_datetime.isoformat()
                            }
                            for f in fires[:10]
                        ]
                    }
                }
                
        except Exception as e:
            logger.error(f"Fire query failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
    
    async def _query_monthly_breakdown(self, country_iso: str, year: int) -> Dict[str, Any]:
        """
        Query monthly fire breakdown from historical database
        
        WHY THIS METHOD:
        - Queries actual monthly data from database
        - Returns real fire counts per month
        - Identifies peak fire months based on actual data
        - No AI approximations - just database aggregation
        
        Args:
            country_iso: 3-letter ISO code (e.g., 'PAK')
            year: Year to analyze (e.g., 2020)
        
        Returns:
            Dict with monthly breakdown and peak months
        """
        if not country_iso:
            return {"status": "error", "message": "Country code required"}
        
        try:
            logger.info(f"Querying monthly breakdown for {country_iso} {year}")
            
            async with database_manager.async_session_maker() as session:
                # Query monthly fire counts with statistics
                query_sql = """
                    SELECT 
                        strftime('%m', acq_date) as month,
                        COUNT(*) as fire_count,
                        AVG(frp) as avg_frp,
                        MAX(frp) as max_frp,
                        AVG(brightness) as avg_brightness
                    FROM fire_detections
                    WHERE country = :country
                    AND strftime('%Y', acq_date) = :year
                    GROUP BY strftime('%m', acq_date)
                    ORDER BY strftime('%m', acq_date)
                """
                
                result = await session.execute(
                    text(query_sql),
                    {"country": country_iso, "year": str(year)}
                )
                monthly_data = result.fetchall()
                
                await session.commit()
                
                if not monthly_data:
                    return {
                        "status": "error",
                        "message": f"No fire data found for {country_iso} in {year}"
                    }
                
                # Month names for better readability
                month_names = [
                    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
                ]
                
                # Format monthly data
                monthly_breakdown = [
                    {
                        "month": month_names[int(row[0]) - 1],
                        "month_number": int(row[0]),
                        "fire_count": int(row[1]),
                        "avg_frp": round(float(row[2]), 2) if row[2] else 0,
                        "max_frp": round(float(row[3]), 2) if row[3] else 0,
                        "avg_brightness": round(float(row[4]), 2) if row[4] else 0
                    }
                    for row in monthly_data
                ]
                
                # Find peak months (top 3 by fire count)
                peak_months = sorted(
                    monthly_breakdown,
                    key=lambda x: x["fire_count"],
                    reverse=True
                )[:3]
                
                # Calculate total fires
                total_fires = sum(m["fire_count"] for m in monthly_breakdown)
                
                logger.info(f"✅ Monthly breakdown: {len(monthly_breakdown)} months, {total_fires} total fires")
                
                return {
                    "status": "success",
                    "intent": "query_monthly",
                    "data": {
                        "country": country_iso,
                        "year": year,
                        "total_fires": total_fires,
                        "months_analyzed": len(monthly_breakdown),
                        "monthly_breakdown": monthly_breakdown,
                        "peak_months": [
                            {
                                "month": m["month"],
                                "fire_count": m["fire_count"],
                                "percentage": round((m["fire_count"] / total_fires) * 100, 1)
                            }
                            for m in peak_months
                        ],
                        "data_source": "historical_database"
                    }
                }
                
        except Exception as e:
            logger.error(f"Monthly breakdown query failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
    
    async def _query_high_frp_fires(self, country_iso: str, year: int, min_frp: float = 100) -> Dict[str, Any]:
        """
        Query high FRP (Fire Radiative Power) fires from historical database
        
        WHY THIS METHOD:
        - Identifies the most intense fires
        - Queries actual FRP values from database
        - Returns top fires sorted by intensity
        - No API calls - uses historical data
        
        FRP CONTEXT:
        - FRP measures fire intensity in Megawatts (MW)
        - Typical fire: 5-50 MW
        - High intensity fire: 100+ MW
        - Extreme fire: 500+ MW
        
        Args:
            country_iso: 3-letter ISO code
            year: Year to analyze
            min_frp: Minimum FRP threshold (default: 100 MW)
        
        Returns:
            Dict with high FRP fire statistics and locations
        """
        if not country_iso:
            return {"status": "error", "message": "Country code required"}
        
        try:
            logger.info(f"Querying high FRP fires for {country_iso} {year} (min_frp={min_frp})")
            
            async with database_manager.async_session_maker() as session:
                # Count high FRP fires
                count_sql = """
                    SELECT COUNT(*)
                    FROM fire_detections
                    WHERE country = :country
                    AND strftime('%Y', acq_date) = :year
                    AND frp >= :min_frp
                """
                
                result = await session.execute(
                    text(count_sql),
                    {"country": country_iso, "year": str(year), "min_frp": min_frp}
                )
                high_frp_count = result.scalar()
                
                # Get top 20 highest FRP fires
                top_fires_sql = """
                    SELECT 
                        latitude,
                        longitude,
                        frp,
                        brightness,
                        confidence,
                        acq_date,
                        satellite
                    FROM fire_detections
                    WHERE country = :country
                    AND strftime('%Y', acq_date) = :year
                    AND frp >= :min_frp
                    ORDER BY frp DESC
                    LIMIT 20
                """
                
                result = await session.execute(
                    text(top_fires_sql),
                    {"country": country_iso, "year": str(year), "min_frp": min_frp}
                )
                top_fires = result.fetchall()
                
                # Get FRP statistics for context
                stats_sql = """
                    SELECT 
                        AVG(frp) as avg_frp,
                        MAX(frp) as max_frp,
                        MIN(frp) as min_frp
                    FROM fire_detections
                    WHERE country = :country
                    AND strftime('%Y', acq_date) = :year
                    AND frp >= :min_frp
                """
                
                result = await session.execute(
                    text(stats_sql),
                    {"country": country_iso, "year": str(year), "min_frp": min_frp}
                )
                stats = result.fetchone()
                
                await session.commit()
                
                if high_frp_count == 0:
                    return {
                        "status": "success",
                        "intent": "query_high_frp",
                        "data": {
                            "country": country_iso,
                            "year": year,
                            "min_frp": min_frp,
                            "high_frp_count": 0,
                            "message": f"No fires with FRP >= {min_frp} MW found"
                        }
                    }
                
                logger.info(f"✅ Found {high_frp_count} high FRP fires")
                
                return {
                    "status": "success",
                    "intent": "query_high_frp",
                    "data": {
                        "country": country_iso,
                        "year": year,
                        "min_frp": min_frp,
                        "high_frp_count": high_frp_count,
                        "statistics": {
                            "avg_frp": round(float(stats[0]), 2) if stats[0] else 0,
                            "max_frp": round(float(stats[1]), 2) if stats[1] else 0,
                            "min_frp": round(float(stats[2]), 2) if stats[2] else 0
                        },
                        "top_fires": [
                            {
                                "latitude": float(f[0]),
                                "longitude": float(f[1]),
                                "frp": round(float(f[2]), 2),
                                "brightness": round(float(f[3]), 2) if f[3] else 0,
                                "confidence": f[4],
                                "date": str(f[5]),
                                "satellite": f[6]
                            }
                            for f in top_fires
                        ],
                        "data_source": "historical_database"
                    }
                }
                
        except Exception as e:
            logger.error(f"High FRP query failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
    
    async def _analyze_historical_correlation(self, country_iso: str, year: int) -> Dict[str, Any]:
        """
        Analyze correlation between fires and climate using REAL statistics
        
        WHY THIS METHOD IS CRITICAL:
        - Uses scipy.stats.pearsonr for REAL correlation coefficients
        - Queries actual monthly fire data from database
        - Fetches real climate data from Open-Meteo
        - NO AI-invented statistics - all calculations are mathematical
        
        CORRELATION ANALYSIS:
        1. Get monthly fire counts from database
        2. Fetch monthly climate data (temperature, precipitation, etc.)
        3. Calculate Pearson correlation coefficient + p-value
        4. Return actual statistical significance
        
        Args:
            country_iso: 3-letter ISO code
            year: Year to analyze (must be historical, < 2025)
        
        Returns:
            Dict with real correlation statistics and monthly data
        """
        if not country_iso:
            return {"status": "error", "message": "Country code required"}
        
        if not year or year >= 2025:
            return {
                "status": "error",
                "message": "Historical year required for correlation analysis (< 2025)"
            }
        
        try:
            logger.info(f"Analyzing historical correlation for {country_iso} {year}")
            
            # Step 1: Get monthly fire data from database
            async with database_manager.async_session_maker() as session:
                query_sql = """
                    SELECT 
                        strftime('%m', acq_date) as month,
                        COUNT(*) as fire_count,
                        AVG(frp) as avg_frp,
                        AVG(brightness) as avg_brightness
                    FROM fire_detections
                    WHERE country = :country
                    AND strftime('%Y', acq_date) = :year
                    GROUP BY strftime('%m', acq_date)
                    ORDER BY strftime('%m', acq_date)
                """
                
                result = await session.execute(
                    text(query_sql),
                    {"country": country_iso, "year": str(year)}
                )
                fire_data = result.fetchall()
                await session.commit()
            
            if not fire_data:
                return {
                    "status": "error",
                    "message": f"No fire data found for {country_iso} in {year}"
                }
            
            # Create monthly fire dataframe
            fire_df = pd.DataFrame(
                fire_data,
                columns=["month", "fire_count", "avg_frp", "avg_brightness"]
            )
            fire_df["month"] = fire_df["month"].astype(int)
            
            # Step 2: Get country centroid for climate data
            country_centers = {
                "PAK": (30.3753, 69.3451),
                "IND": (20.5937, 78.9629),
                "BGD": (23.6850, 90.3563),
                "IDN": (-0.7893, 113.9213),
                "BRA": (-14.2350, -51.9253),
            }
            
            if country_iso not in country_centers:
                return {
                    "status": "error",
                    "message": f"No climate data available for {country_iso}"
                }
            
            lat, lon = country_centers[country_iso]
            
            # Step 3: Fetch monthly climate data using ClimateService
            logger.info(f"Fetching climate data for {country_iso} at ({lat}, {lon})")
            
            climate_data = self.climate_service.get_monthly_climate(
                latitude=lat,
                longitude=lon,
                year=year
            )
            
            if not climate_data or "monthly_data" not in climate_data:
                return {
                    "status": "error",
                    "message": "Failed to fetch climate data"
                }
            
            # Create climate dataframe
            climate_df = pd.DataFrame(climate_data["monthly_data"])
            
            # Step 4: Merge fire and climate data
            merged_df = fire_df.merge(climate_df, on="month", how="inner")
            
            if len(merged_df) < 3:
                return {
                    "status": "error",
                    "message": "Insufficient data for correlation analysis (need at least 3 months)"
                }
            
            # Step 5: Calculate REAL Pearson correlations using scipy
            correlations = {}
            
            # Temperature correlation
            if "avg_temp_max" in merged_df.columns:
                try:
                    coef, p_value = pearsonr(
                        merged_df["fire_count"],
                        merged_df["avg_temp_max"]
                    )
                    correlations["temperature"] = {
                        "coefficient": round(float(coef), 3),
                        "p_value": round(float(p_value), 4),
                        "significant": bool(p_value < 0.05)  # Convert to native Python bool
                    }
                except Exception as e:
                    logger.error(f"Temperature correlation failed: {e}")
            
            # Precipitation correlation
            if "total_precipitation" in merged_df.columns:
                try:
                    coef, p_value = pearsonr(
                        merged_df["fire_count"],
                        merged_df["total_precipitation"]
                    )
                    correlations["precipitation"] = {
                        "coefficient": round(float(coef), 3),
                        "p_value": round(float(p_value), 4),
                        "significant": bool(p_value < 0.05)  # Convert to native Python bool
                    }
                except Exception as e:
                    logger.error(f"Precipitation correlation failed: {e}")
            
            # Wind speed correlation
            if "avg_windspeed" in merged_df.columns:
                try:
                    coef, p_value = pearsonr(
                        merged_df["fire_count"],
                        merged_df["avg_windspeed"]
                    )
                    correlations["wind_speed"] = {
                        "coefficient": round(float(coef), 3),
                        "p_value": round(float(p_value), 4),
                        "significant": bool(p_value < 0.05)  # Convert to native Python bool
                    }
                except Exception as e:
                    logger.error(f"Wind speed correlation failed: {e}")
            
            # Month names for output
            month_names = [
                "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
            ]
            
            # Step 6: Format monthly data for output
            monthly_combined = [
                {
                    "month": month_names[int(row["month"]) - 1],
                    "month_number": int(row["month"]),
                    "fire_count": int(row["fire_count"]),
                    "avg_frp": round(float(row["avg_frp"]), 2) if row["avg_frp"] else 0,
                    "avg_temp_max": round(float(row["avg_temp_max"]), 2) if "avg_temp_max" in row else None,
                    "total_precipitation": round(float(row["total_precipitation"]), 2) if "total_precipitation" in row else None,
                    "avg_windspeed": round(float(row["avg_windspeed"]), 2) if "avg_windspeed" in row else None
                }
                for _, row in merged_df.iterrows()
            ]
            
            logger.info(f"✅ Correlation analysis complete: {len(correlations)} correlations calculated")
            
            return {
                "status": "success",
                "intent": "analyze_correlation",
                "data": {
                    "country": country_iso,
                    "year": year,
                    "analysis_type": "historical_correlation",
                    "correlations": correlations,
                    "monthly_data": monthly_combined,
                    "months_analyzed": len(monthly_combined),
                    "location": {"latitude": lat, "longitude": lon},
                    "data_sources": {
                        "fires": "historical_database",
                        "climate": "open_meteo_era5"
                    },
                    "note": "All correlation coefficients calculated using scipy.stats.pearsonr"
                }
            }
            
        except Exception as e:
            logger.error(f"Historical correlation analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    async def _query_forest_loss(self, country_iso: str) -> Dict[str, Any]:
        """
        Query yearly forest loss data from Global Forest Watch
        
        WHY THIS METHOD:
        - Fetches real yearly deforestation data (2001-2024)
        - Returns complete time series for trend analysis
        - Includes trend assessment (INCREASING/DECREASING/STABLE)
        - Data from GFW GADM TCL Change dataset
        
        Args:
            country_iso: 3-letter ISO code (e.g., 'PAK', 'BRA', 'IDN')
        
        Returns:
            Dict with yearly forest loss data and trend analysis
        """
        if not country_iso:
            return {"status": "error", "message": "Country code required"}
        
        try:
            logger.info(f"Querying forest loss for {country_iso}")
            
            # Get forest data from GFW
            forest_stats = self.forest_monitor.get_country_forest_stats(country_iso)
            
            if not forest_stats or not forest_stats.get("tree_cover_loss"):
                return {
                    "status": "error",
                    "message": f"No forest data available for {country_iso}"
                }
            
            # Get trend analysis
            trend_analysis = self.forest_monitor.analyze_deforestation_trend(country_iso)
            
            tree_loss = forest_stats["tree_cover_loss"]
            yearly_data = tree_loss["yearly_data"]
            
            # Format yearly data for better readability
            formatted_yearly = [
                {
                    "year": int(item["year"]),
                    "loss_ha": round(float(item["loss_ha"]), 2)
                }
                for item in yearly_data
            ]
            
            # Calculate some useful statistics
            recent_5_years = formatted_yearly[-5:]
            early_5_years = formatted_yearly[:5]
            
            recent_avg = sum(y["loss_ha"] for y in recent_5_years) / len(recent_5_years)
            early_avg = sum(y["loss_ha"] for y in early_5_years) / len(early_5_years)
            
            logger.info(f"✅ Retrieved {len(formatted_yearly)} years of forest data")
            
            return {
                "status": "success",
                "intent": "query_forest",
                "data": {
                    "country": country_iso,
                    "country_name": forest_stats.get("country_name"),
                    "summary": {
                        "total_loss_ha": round(tree_loss["total_loss_ha"], 2),
                        "years_available": tree_loss["years_available"],
                        "data_range": tree_loss["data_range"],
                        "recent_year": tree_loss["recent_year"],
                        "recent_loss_ha": round(tree_loss["recent_loss_ha"], 2)
                    },
                    "yearly_data": formatted_yearly,
                    "trend_analysis": {
                        "trend": trend_analysis.get("trend"),
                        "severity": trend_analysis.get("severity"),
                        "change_percent": trend_analysis.get("change_percent"),
                        "recent_avg_loss_ha": round(recent_avg, 2),
                        "early_avg_loss_ha": round(early_avg, 2),
                        "analysis_period": f"{early_5_years[0]['year']}-{recent_5_years[-1]['year']}"
                    },
                    "peak_loss_year": max(formatted_yearly, key=lambda x: x["loss_ha"]),
                    "lowest_loss_year": min(formatted_yearly, key=lambda x: x["loss_ha"]),
                    "data_source": "global_forest_watch",
                    "dataset": "GADM TCL Change (UMD)"
                }
            }
            
        except Exception as e:
            logger.error(f"Forest query failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    async def _analyze_correlation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Run correlation analysis with climate data (recent data, legacy method)"""
        
        country_iso = parameters.get("country_iso")
        
        if not country_iso:
            return {"status": "error", "message": "Country code required"}
        
        try:
            # Get fire data
            async with self.nasa_service:
                fires = await self.nasa_service.get_fires_by_country(country_iso, days=7)
            
            if not fires:
                return {"status": "error", "message": f"No fire data for {country_iso}"}
            
            # Calculate centroid of fire locations for climate data
            avg_lat = sum(f.latitude for f in fires) / len(fires)
            avg_lon = sum(f.longitude for f in fires) / len(fires)
            
            # Get climate data
            climate_data = None
            try:
                from datetime import date, timedelta
                
                end_date = date.today()
                start_date = end_date - timedelta(days=7)
                
                raw_climate = self.climate_monitor.get_historical_data(
                    latitude=avg_lat,
                    longitude=avg_lon,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    include_soil=False
                )
                
                if raw_climate:
                    stats = self.climate_monitor.calculate_climate_statistics(raw_climate)
                    
                    climate_data = {
                        "avg_temperature_c": stats.get("temperature_2m_max", {}).get("mean"),
                        "max_temperature_c": stats.get("temperature_2m_max", {}).get("max"),
                        "min_temperature_c": stats.get("temperature_2m_min", {}).get("min"),
                        "total_precipitation_mm": stats.get("precipitation_sum", {}).get("total"),
                        "avg_humidity_percent": stats.get("relative_humidity_2m_mean", {}).get("mean"),
                        "max_windspeed_kmh": stats.get("windspeed_10m_max", {}).get("max"),
                        "days_analyzed": 7,
                        "location": {"lat": round(avg_lat, 4), "lon": round(avg_lon, 4)}
                    }
                    
                    logger.info(f"Climate data calculated: {climate_data}")
                else:
                    climate_data = {"error": "Failed to fetch climate data"}
                
            except Exception as e:
                logger.error(f"Could not fetch climate data: {e}")
                import traceback
                traceback.print_exc()
                climate_data = {"error": str(e)}
            
            # Get forest data
            forest_stats = self.forest_monitor.get_country_forest_stats(country_iso)
            
            # Calculate fire statistics
            avg_frp = sum(f.frp for f in fires if f.frp) / len([f for f in fires if f.frp]) if fires else 0
            avg_brightness = sum(f.brightness for f in fires if f.brightness) / len(fires)
            
            return {
                "status": "success",
                "intent": "analyze_correlation",
                "data": {
                    "country": country_iso,
                    "fire_statistics": {
                        "total_fires": len(fires),
                        "avg_frp": round(avg_frp, 2),
                        "avg_brightness": round(avg_brightness, 2),
                        "fire_centroid": {"lat": round(avg_lat, 4), "lon": round(avg_lon, 4)}
                    },
                    "climate_conditions": climate_data,
                    "forest_loss": {
                        "total_loss_ha": forest_stats.get("tree_cover_loss", {}).get("total_loss_ha", 0) if forest_stats else 0,
                        "recent_year": forest_stats.get("tree_cover_loss", {}).get("recent_year", "N/A") if forest_stats else "N/A",
                        "recent_loss_ha": forest_stats.get("tree_cover_loss", {}).get("recent_loss_ha", 0) if forest_stats else 0
                    },
                    "analysis_type": "climate_fire_correlation",
                    "note": "Recent data correlation (last 7 days)"
                }
            }
            
        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
    
    async def _generate_report(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive report"""
        
        country_iso = parameters.get("country_iso")
        
        if not country_iso:
            return {"status": "error", "message": "Country code required"}
        
        try:
            # Gather all data
            async with self.nasa_service:
                fires = await self.nasa_service.get_fires_by_country(country_iso, days=7)
            
            forest_stats = self.forest_monitor.get_country_forest_stats(country_iso)
            forest_trend = self.forest_monitor.analyze_deforestation_trend(country_iso)
            
            return {
                "status": "success",
                "intent": "generate_report",
                "data": {
                    "country": country_iso,
                    "fire_summary": {
                        "total_fires": len(fires),
                        "avg_frp": sum(f.frp for f in fires if f.frp) / len([f for f in fires if f.frp]) if fires else 0
                    },
                    "forest_summary": forest_stats,
                    "forest_trend": forest_trend
                }
            }
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def query_with_rag(self, question: str) -> str:
        """Answer question using RAG"""
        
        relevant_docs = vector_store.search(question, n_results=3)
        
        if not relevant_docs:
            return "I don't have enough context to answer this question."
        
        context = "\n\n".join([doc["document"] for doc in relevant_docs])
        
        from app.llm.prompts.system_prompts import RAG_CONTEXT_PROMPT
        from groq import AsyncGroq
        
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        
        prompt = RAG_CONTEXT_PROMPT.replace("{{context}}", context).replace("{{question}}", question)
        
        response = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Answer based only on the provided context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        return response.choices[0].message.content


# Global orchestrator instance
orchestrator = LLMOrchestrator()