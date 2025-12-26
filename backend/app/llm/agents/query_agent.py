"""Query Understanding Agent - WITH DRIVER & FLOOD DETECTION"""

import json
import re
from typing import Dict, Any, Optional
from groq import AsyncGroq

from app.config import settings
from app.llm.prompts.system_prompts import QUERY_AGENT_PROMPT
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QueryAgent:
    """
    Understands natural language queries and extracts parameters
    
    SUPPORTED QUERY TYPES:
    1. query_fires - General fire queries
    2. query_monthly - Monthly fire breakdown
    3. query_high_frp - High intensity fires
    4. analyze_correlation - Fire-climate correlation
    5. analyze_fire_forest_correlation - Fire-deforestation correlation
    6. query_forest - Forest/deforestation only
    7. query_drivers - Deforestation drivers 
    8. query_fires_realtime - Real-time fire detection
    9. query_floods - SAR-based flood detection 🌊
    10. generate_report - Comprehensive reports

    
    FEATURES:
    - Hybrid LLM + rule-based intent detection
    - Prioritized keyword matching
    - Context-aware detection
    - Driver query detection
    - Flood query detection with date extraction
    - Fallback year extraction
    """
    
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set in environment")
        
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
    
    async def parse_query(self, user_query: str) -> Dict[str, Any]:
        """
        Parse natural language query into structured parameters
        
        Args:
            user_query: Natural language query from user
        
        Returns:
            Dict with intent and parameters
        """
        
        prompt = QUERY_AGENT_PROMPT.replace("{{query}}", user_query)
        
        try:
            # Step 1: Get LLM's initial parse
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a geospatial query parser. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON from markdown if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(content)
            
            # Step 2: Enhance with rule-based detection
            parsed = self._enhance_intent_detection(user_query, parsed)
            
            # Step 3: Fallback year extraction
            if "parameters" in parsed and "year" not in parsed["parameters"]:
                year = self._extract_year(user_query)
                if year:
                    parsed["parameters"]["year"] = year
            
            # Step 4: Extract min_frp for high FRP queries
            if parsed.get("intent") == "query_high_frp":
                if "parameters" not in parsed:
                    parsed["parameters"] = {}
                if "min_frp" not in parsed["parameters"]:
                    parsed["parameters"]["min_frp"] = self._extract_frp_threshold(user_query)
            
            logger.info(f"Query parsed: {parsed.get('intent')} | Parameters: {parsed.get('parameters')}")
            return parsed
            
        except Exception as e:
            logger.error(f"Query parsing failed: {e}")
            return {
                "intent": "unknown",
                "parameters": {},
                "error": str(e)
            }
    
    def _enhance_intent_detection(self, user_query: str, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance intent detection with rule-based patterns
        
        DETECTION ORDER (Priority):
        1. Monthly queries (most specific)
        2. High FRP queries (most specific)
        3. Driver queries (causes, drivers, why)
        4. Flood queries 🌊 (NEW!)
        5. Real-time fire queries
        6. Fire-Forest correlation (fires + forests together)
        7. Forest-only queries (only forests, no fires)
        8. Fire-Climate correlation (fires + climate, no forests)
        9. Trend analysis (fallback)
        
        Args:
            user_query: Original user query
            parsed: LLM-parsed result
        
        Returns:
            Enhanced parsed result with corrected intent
        """
        query_lower = user_query.lower()
            # ═══════════════════════════════════════════════════════════════════════
        # DEBUG: Check what LLM returned and what we're detecting
        # ═══════════════════════════════════════════════════════════════════════
        logger.info(f"🔍 DEBUG _enhance_intent_detection")
        logger.info(f"   Query: {query_lower}")
        logger.info(f"   LLM returned intent: {parsed.get('intent')}")
        logger.info(f"   LLM returned params: {parsed.get('parameters')}")
        # Pattern 1: Monthly breakdown queries (HIGHEST PRIORITY)
        monthly_keywords = ["peak", "highest", "most", "monthly", "month", "breakdown", "per month"]
        if any(keyword in query_lower for keyword in monthly_keywords):
            logger.info("Rule-based detection: Monthly breakdown query")
            parsed["intent"] = "query_monthly"
            return parsed
        
        # Pattern 2: High FRP fire queries (VERY SPECIFIC)
        high_frp_keywords = [
            "high frp", "intense fires", "severe fires", "strong fires", "strongest fires",
            "extreme fires", "powerful fires", "hottest fires", "biggest fires"
        ]
        if any(keyword in query_lower for keyword in high_frp_keywords):
            logger.info("Rule-based detection: High FRP query")
            parsed["intent"] = "query_high_frp"
            return parsed
        
        # Pattern 3: Driver queries
        driver_keywords = [
            "cause", "causes", "driver", "drivers", "why", "reason", "reasons",
            "what caused", "what's causing", "what is causing", "what causes",
            "show drivers", "show causes", "show me drivers", "show me causes",
            "deforestation cause", "deforestation driver", "forest loss cause",
            "tree loss cause", "agriculture", "logging", "farming", "cattle",
            "palm oil", "soy", "fire driver"
        ]
        
        has_driver_intent = any(keyword in query_lower for keyword in driver_keywords)
        
        if has_driver_intent:
            logger.info("Rule-based detection: Driver query (causes/drivers)")
            parsed["intent"] = "query_drivers"
            parsed["show_drivers"] = True
            return parsed
        
        # ═══════════════════════════════════════════════════════════════════════
        # Pattern 4: FLOOD QUERIES 🌊
        # ═══════════════════════════════════════════════════════════════════════
        flood_keywords = [
            # Direct flood terms
            "flood", "floods", "flooding", "flooded",
            "inundation", "inundated", "inundate",
            "underwater", "submerged", "waterlogged",
            # Event types
            "deluge", "flash flood", "river flood", "monsoon flood",
            "cyclone flood", "typhoon flood", "hurricane flood",
            "storm surge", "overflow", "overflowed",
            # Analysis terms
            "flood extent", "flood map", "flood detection", "flood analysis",
            "water extent", "flood damage", "flood impact",
            # SAR specific
            "sar flood", "sentinel flood", "radar flood"
        ]
        
        has_flood_intent = any(keyword in query_lower for keyword in flood_keywords)
        
        if has_flood_intent:
            logger.info("Rule-based detection: Flood query 🌊")
            parsed["intent"] = "query_floods"
            parsed["parameters"] = parsed.get("parameters", {})
            flood_params = self._extract_flood_parameters(user_query)
            parsed["parameters"].update(flood_params)
            return parsed
        # ═══════════════════════════════════════════════════════════════════════
        # ═══════════════════════════════════════════════════════════════════════
        # Pattern 4.1: MPC SATELLITE IMAGERY QUERIES 🛰️
        # ═══════════════════════════════════════════════════════════════════════
        mpc_keywords = [
            "sentinel-2", "sentinel 2", "landsat", "satellite imagery",
            "satellite images", "satellite data", "hls", "harmonized landsat",
            "optical satellite", "multispectral", "find images", "search images",
            "available images", "planetary computer", "mpc"
        ]

        has_mpc_intent = any(keyword in query_lower for keyword in mpc_keywords)

        if has_mpc_intent:
            logger.info("Rule-based detection: MPC satellite imagery query 🛰️")
            parsed["intent"] = "query_mpc_images"
            # Extract MPC-specific parameters
            parsed["parameters"] = parsed.get("parameters", {})
            mpc_params = self._extract_mpc_parameters(user_query)
            parsed["parameters"].update(mpc_params)
            return parsed
        # Add after flood detection pattern (around line 120):

        # ═══════════════════════════════════════════════════════════════════════
        # Pattern 4.2: URBAN EXPANSION QUERIES 🏙️
        # ═══════════════════════════════════════════════════════════════════════

        urban_keywords = [
            "urban", "city growth", "city expansion", "urban expansion",
            "urban growth", "urbanization", "urbanisation", "built-up",
            "built up", "sprawl", "urban sprawl", "city sprawl",
            "how has", "grown", "expanded", "expansion",
            "settlement", "development", "urban development"
        ]

        city_indicators = [
            "city", "cities", "town", "metropolitan", "metro"
        ]

        has_urban_intent = any(keyword in query_lower for keyword in urban_keywords)
        has_city_context = any(keyword in query_lower for keyword in city_indicators)

        # Also check for known city names
        known_cities = [
            "dubai", "lahore", "karachi", "mumbai", "delhi", "beijing",
            "shanghai", "tokyo", "singapore", "riyadh", "london", "paris",
            "new york", "los angeles", "cairo", "lagos"
        ]
        has_city_name = any(city in query_lower for city in known_cities)

        if has_urban_intent or (has_city_context and has_city_name):
            logger.info("Rule-based detection: Urban expansion query 🏙️")
            parsed["intent"] = "query_urban_expansion"
            parsed["parameters"] = parsed.get("parameters", {})
            urban_params = self._extract_urban_parameters(user_query)
            parsed["parameters"].update(urban_params)
            return parsed
        
        # ═══════════════════════════════════════════════════════════════════════════
        # Pattern 4.3: SURFACE WATER QUERIES 💧
        # ═══════════════════════════════════════════════════════════════════════════

        water_keywords = [
            # Water body terms
            "lake", "sea", "reservoir", "dam", "river", "delta",
            "water body", "water level", "water extent",
            # Analysis terms
            "water change", "water loss", "shrinking", "drying",
            "dried up", "water area", "surface water",
            # Specific phenomena
            "drought impact", "water retreat", "shoreline change"
        ]

        known_water_bodies = [
            "aral", "chad", "urmia", "dead sea", "mead", "powell",
            "poopo", "balkhash", "turkana", "titicaca", "victoria",
            "nasser", "three gorges", "indus delta", "ganges delta",
            "mekong delta", "caspian", "salton"
        ]

        has_water_keyword = any(keyword in query_lower for keyword in water_keywords)
        has_water_body = any(wb in query_lower for wb in known_water_bodies)

        if has_water_keyword or has_water_body:
            logger.info("Rule-based detection: Surface water query 💧")
            parsed["intent"] = "query_surface_water"
            parsed["parameters"] = parsed.get("parameters", {})
            water_params = self._extract_water_parameters(user_query)
            parsed["parameters"].update(water_params)
            return parsed
        # ═══════════════════════════════════════════════════════════════════════
        # Pattern 5: Real-time fire queries
        realtime_keywords = ["real-time", "realtime", "live", "current", "today", "now", "active"]
        fire_keywords_simple = ["fire", "fires", "burning"]
        if any(rt in query_lower for rt in realtime_keywords) and any(f in query_lower for f in fire_keywords_simple):
            logger.info("Rule-based detection: Real-time fire query")
            parsed["intent"] = "query_fires_realtime"
            return parsed
        
        # Pattern 6: Fire-Forest correlation
        fire_keywords = ["fire", "fires", "burning", "burnt"]
        forest_keywords = ["forest", "deforestation", "tree loss", "tree cover", "forest loss"]
        
        has_fire = any(keyword in query_lower for keyword in fire_keywords)
        has_forest = any(keyword in query_lower for keyword in forest_keywords)
        
        if has_fire and has_forest:
            logger.info("Rule-based detection: Fire-Forest correlation (fires + forests)")
            parsed["intent"] = "analyze_fire_forest_correlation"
            return parsed
        
        # Pattern 7: Forest/Deforestation queries (ONLY forest, no fires)
        if has_forest and not has_fire:
            logger.info("Rule-based detection: Forest query (forest only)")
            parsed["intent"] = "query_forest"
            return parsed
        
        # Pattern 8: Fire-Climate correlation (fires + climate, NOT forests)
        correlation_keywords = ["correlation", "correlate", "relationship", "impact of", "affect", "influence"]
        climate_keywords = ["climate", "temperature", "weather", "precipitation", "wind"]
        
        has_correlation_intent = any(keyword in query_lower for keyword in correlation_keywords)
        has_climate_context = any(keyword in query_lower for keyword in climate_keywords)
        
        if has_correlation_intent or (has_climate_context and has_fire):
            if parsed.get("intent") not in ["query_monthly", "query_high_frp", "query_drivers", 
                                             "query_floods", "query_forest", "analyze_fire_forest_correlation"]:
                logger.info("Rule-based detection: Fire-Climate correlation")
                parsed["intent"] = "analyze_correlation"
                return parsed
        
        # Pattern 9: Trend analysis queries (FALLBACK)
        trend_keywords = ["trend", "over time", "change over", "historical"]
        if any(keyword in query_lower for keyword in trend_keywords):
            if parsed.get("intent") not in ["query_monthly", "query_high_frp", "query_drivers", 
                                             "query_floods", "query_forest", "analyze_correlation", 
                                             "analyze_fire_forest_correlation", "query_fires_realtime"]:
                logger.info("Rule-based detection: Trend analysis")
                parsed["intent"] = "generate_report"
                return parsed
        
        # If no specific pattern matched, keep LLM's decision
        logger.info(f"No rule-based override - keeping LLM intent: {parsed.get('intent')}")
        return parsed
    
    def _extract_flood_parameters(self, user_query: str) -> Dict[str, Any]:
        """
        Extract flood detection parameters from natural language query.
        
        Extracts:
        - location_name: Name of place/region
        - location_type: country, province, district, river
        - country: Country for disambiguation
        - buffer_km: Buffer for rivers (if mentioned)
        - Dates: Before/after periods from known events or explicit dates
        """
        query_lower = user_query.lower()
        params = {}
        
        # ─────────────────────────────────────────────────────────────────────
        # KNOWN FLOOD EVENTS (with pre-configured dates)
        # ─────────────────────────────────────────────────────────────────────
        known_events = {
            # Pakistan 2022 Monsoon Floods
            ("pakistan", "2022"): {
                "before_start": "2022-06-01", "before_end": "2022-07-15",
                "after_start": "2022-08-25", "after_end": "2022-09-05",
                "country": "Pakistan"
            },
            ("sindh", "2022"): {
                "before_start": "2022-06-01", "before_end": "2022-07-15",
                "after_start": "2022-08-25", "after_end": "2022-09-05",
                "location_name": "Sindh", "location_type": "province", "country": "Pakistan"
            },
            ("punjab", "2022", "pakistan"): {
                "before_start": "2022-06-01", "before_end": "2022-07-15",
                "after_start": "2022-08-25", "after_end": "2022-09-05",
                "location_name": "Punjab", "location_type": "province", "country": "Pakistan"
            },
            ("indus", "2022"): {
                "before_start": "2022-06-01", "before_end": "2022-07-15",
                "after_start": "2022-08-25", "after_end": "2022-09-05",
                "location_name": "Indus", "location_type": "river", "country": "Pakistan", "buffer_km": 25
            },
            
            # Sri Lanka Cyclone Ditwah 2025
            ("sri lanka", "2025"): {
                "before_start": "2025-09-01", "before_end": "2025-10-31",
                "after_start": "2025-11-28", "after_end": "2025-12-05",
                "country": "Sri Lanka"
            },
            ("ditwah",): {
                "before_start": "2025-09-01", "before_end": "2025-10-31",
                "after_start": "2025-11-28", "after_end": "2025-12-05",
                "country": "Sri Lanka"
            },
            ("kelani",): {
                "before_start": "2025-09-01", "before_end": "2025-10-31",
                "after_start": "2025-11-28", "after_end": "2025-12-05",
                "location_name": "Kelani", "location_type": "river", "country": "Sri Lanka", "buffer_km": 15
            },
            
            # Kerala 2018 Floods
            ("kerala", "2018"): {
                "before_start": "2018-07-01", "before_end": "2018-07-31",
                "after_start": "2018-08-15", "after_end": "2018-08-25",
                "location_name": "Kerala", "location_type": "province", "country": "India"
            },
            
            # Bangladesh 2020
            ("bangladesh", "2020"): {
                "before_start": "2020-05-01", "before_end": "2020-06-15",
                "after_start": "2020-07-01", "after_end": "2020-07-31",
                "country": "Bangladesh"
            },
        }
        
        # Check for known events
        for keywords, event_params in known_events.items():
            if all(kw in query_lower for kw in keywords):
                logger.info(f"Matched known flood event: {keywords}")
                params.update(event_params)
                break
        
        # ─────────────────────────────────────────────────────────────────────
        # LOCATION TYPE DETECTION
        # ─────────────────────────────────────────────────────────────────────
        if "location_type" not in params:
            # River detection
            river_keywords = ["river", "nadi", "tributary", "stream"]
            if any(kw in query_lower for kw in river_keywords):
                params["location_type"] = "river"
                if "buffer_km" not in params:
                    params["buffer_km"] = 25  # Default river buffer
            
            # District detection
            elif "district" in query_lower:
                params["location_type"] = "district"
            
            # Province/State detection
            elif any(kw in query_lower for kw in ["province", "state", "region"]):
                params["location_type"] = "province"
            
            # Country detection (if country name mentioned alone)
            elif any(kw in query_lower for kw in ["country", "nation"]):
                params["location_type"] = "country"
        
        # ─────────────────────────────────────────────────────────────────────
        # COUNTRY DETECTION (for disambiguation)
        # ─────────────────────────────────────────────────────────────────────
        if "country" not in params:
            country_patterns = {
                "pakistan": "Pakistan",
                "india": "India",
                "bangladesh": "Bangladesh",
                "sri lanka": "Sri Lanka",
                "nepal": "Nepal",
                "thailand": "Thailand",
                "vietnam": "Viet Nam",
                "indonesia": "Indonesia",
                "philippines": "Philippines",
                "myanmar": "Myanmar",
                "china": "China",
                "brazil": "Brazil",
                "australia": "Australia",
            }
            
            for pattern, country_name in country_patterns.items():
                if pattern in query_lower:
                    params["country"] = country_name
                    break
        
        # ─────────────────────────────────────────────────────────────────────
        # LOCATION NAME EXTRACTION
        # ─────────────────────────────────────────────────────────────────────
        if "location_name" not in params:
            # Try to extract location name from common patterns
            # Pattern: "floods in <location>"
            location_patterns = [
                r'floods?\s+in\s+([a-zA-Z\s]+?)(?:\s+(?:district|province|state|region|river|from|during|in\s+\d{4})|\s*$)',
                r'flooding\s+in\s+([a-zA-Z\s]+?)(?:\s+(?:district|province|state|region|river|from|during|in\s+\d{4})|\s*$)',
                r'flood\s+(?:extent|map|detection|analysis)\s+(?:in|for|of)\s+([a-zA-Z\s]+?)(?:\s+(?:district|province|state|region|river|from|during|in\s+\d{4})|\s*$)',
                r'([a-zA-Z\s]+?)\s+(?:floods?|flooding)',
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, query_lower)
                if match:
                    location = match.group(1).strip()
                    # Clean up common words
                    location = re.sub(r'\b(the|show|detect|analyze|what|areas|were)\b', '', location).strip()
                    if location and len(location) > 2:
                        params["location_name"] = location.title()
                        break
        
        # ─────────────────────────────────────────────────────────────────────
        # YEAR/DATE EXTRACTION (if not from known event)
        # ─────────────────────────────────────────────────────────────────────
        if "after_start" not in params:
            # Try to extract year
            year_match = re.search(r'\b(20\d{2})\b', user_query)
            
            if year_match:
                year = year_match.group(1)
                
                # Try to extract month
                month_patterns = {
                    'january': '01', 'february': '02', 'march': '03', 'april': '04',
                    'may': '05', 'june': '06', 'july': '07', 'august': '08',
                    'september': '09', 'october': '10', 'november': '11', 'december': '12',
                    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                    'jun': '06', 'jul': '07', 'aug': '08', 'sep': '09',
                    'oct': '10', 'nov': '11', 'dec': '12'
                }
                
                month = None
                for month_name, month_num in month_patterns.items():
                    if month_name in query_lower:
                        month = month_num
                        break
                
                if month:
                    # Specific month mentioned
                    before_month = int(month) - 2
                    before_year = int(year)
                    if before_month <= 0:
                        before_month += 12
                        before_year -= 1
                    
                    end_month = int(month)
                    if end_month == 1:
                        before_end_month = 12
                        before_end_year = int(year) - 1
                    else:
                        before_end_month = end_month - 1
                        before_end_year = int(year)
                    
                    params["before_start"] = f"{before_year}-{str(before_month).zfill(2)}-01"
                    params["before_end"] = f"{before_end_year}-{str(before_end_month).zfill(2)}-28"
                    params["after_start"] = f"{year}-{month}-01"
                    params["after_end"] = f"{year}-{month}-28"
                else:
                    # Just year - assume monsoon season (Jul-Sep for South Asia)
                    params["before_start"] = f"{year}-05-01"
                    params["before_end"] = f"{year}-06-30"
                    params["after_start"] = f"{year}-07-15"
                    params["after_end"] = f"{year}-09-15"
                
                params["year"] = int(year)
        
        # ─────────────────────────────────────────────────────────────────────
        # BUFFER EXTRACTION (if mentioned)
        # ─────────────────────────────────────────────────────────────────────
        buffer_match = re.search(r'(\d+)\s*(?:km|kilometer|kilometres?)\s*(?:buffer|radius|around)?', query_lower)
        if buffer_match and "buffer_km" not in params:
            params["buffer_km"] = float(buffer_match.group(1))
        
        return params
    def _extract_urban_parameters(self, user_query: str) -> Dict[str, Any]:
        """Extract urban expansion parameters from query."""
        
        query_lower = user_query.lower()
        params = {}
        
        # Extract city name
        known_cities = {
            "dubai": "Dubai", "lahore": "Lahore", "karachi": "Karachi",
            "islamabad": "Islamabad", "mumbai": "Mumbai", "delhi": "Delhi",
            "beijing": "Beijing", "shanghai": "Shanghai", "tokyo": "Tokyo",
            "singapore": "Singapore", "riyadh": "Riyadh", "london": "London",
            "paris": "Paris", "new york": "New York", "los angeles": "Los Angeles",
            "cairo": "Cairo", "lagos": "Lagos", "nairobi": "Nairobi",
            "johannesburg": "Johannesburg", "sao paulo": "São Paulo"
        }
        
        for city_key, city_name in known_cities.items():
            if city_key in query_lower:
                params["location_name"] = city_name
                break
        
        # Extract years
        years = re.findall(r'\b(19[789]\d|20[012]\d)\b', user_query)
        
        if len(years) >= 2:
            params["start_year"] = int(min(years))
            params["end_year"] = int(max(years))
        elif len(years) == 1:
            year = int(years[0])
            if year < 2000:
                params["start_year"] = year
                params["end_year"] = 2020
            else:
                params["start_year"] = 1975
                params["end_year"] = year
        else:
            params["start_year"] = 1975
            params["end_year"] = 2020
        
        # Check for animation request
        if any(kw in query_lower for kw in ["animation", "animate", "timelapse", "time-lapse", "gif"]):
            params["include_animation"] = True
        
        return params
    def _extract_mpc_parameters(self, user_query: str) -> Dict[str, Any]:
        """
        Extract MPC search parameters from natural language query.
        
        Extracts:
        - location_name: Place name
        - start_date, end_date: Date range
        - collection: Satellite collection
        """
        query_lower = user_query.lower()
        params = {}
        
        # Extract dates
        year_match = re.search(r'\b(20\d{2})\b', user_query)
        
        if year_match:
            year = year_match.group(1)
            
            # Month patterns
            month_patterns = {
                'january': '01', 'february': '02', 'march': '03', 'april': '04',
                'may': '05', 'june': '06', 'july': '07', 'august': '08',
                'september': '09', 'october': '10', 'november': '11', 'december': '12',
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'jun': '06', 'jul': '07', 'aug': '08', 'sep': '09',
                'oct': '10', 'nov': '11', 'dec': '12'
            }
            
            month = None
            for month_name, month_num in month_patterns.items():
                if month_name in query_lower:
                    month = month_num
                    break
            
            if month:
                # Specific month
                params["start_date"] = f"{year}-{month}-01"
                params["end_date"] = f"{year}-{month}-28"
            else:
                # Whole year
                params["start_date"] = f"{year}-01-01"
                params["end_date"] = f"{year}-12-31"
            
            params["year"] = int(year)
        
        # Extract location
        location_patterns = [
            r'images?\s+of\s+([a-zA-Z\s]+?)(?:\s+from|\s+in\s+\d{4}|\s*$)',
            r'imagery\s+for\s+([a-zA-Z\s]+?)(?:\s+from|\s+in\s+\d{4}|\s*$)',
            r'data\s+(?:of|for)\s+([a-zA-Z\s]+?)(?:\s+from|\s+in\s+\d{4}|\s*$)',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, query_lower)
            if match:
                location = match.group(1).strip()
                # Clean up
                location = re.sub(r'\b(the|show|find|search|get)\b', '', location).strip()
                if location and len(location) > 2:
                    params["location_name"] = location.title()
                    break
        
        return params
    def _extract_year(self, user_query: str) -> Optional[int]:
        """
        Extract year from query using regex fallback
        
        Args:
            user_query: User's natural language query
        
        Returns:
            Extracted year or None
        """
        year_match = re.search(r'\b(20\d{2})\b', user_query)
        if year_match:
            year = int(year_match.group(1))
            logger.info(f"Regex extracted year: {year}")
            return year
        return None
    
    def _extract_frp_threshold(self, user_query: str) -> int:
        """
        Extract FRP threshold from query or use default
        
        Args:
            user_query: User's query
        
        Returns:
            FRP threshold in MW
        """
        frp_patterns = [
            r'above (\d+)',
            r'over (\d+)',
            r'> ?(\d+)',
            r'greater than (\d+)',
            r'more than (\d+)',
            r'frp.*?(\d+)',
        ]
        
        for pattern in frp_patterns:
            match = re.search(pattern, user_query.lower())
            if match:
                threshold = int(match.group(1))
                logger.info(f"Extracted FRP threshold: {threshold} MW")
                return threshold
        
        logger.info("Using default FRP threshold: 100 MW")
        return 100

    def _extract_water_parameters(self, user_query: str) -> Dict[str, Any]:
        """Extract surface water parameters from query."""
        
        query_lower = user_query.lower()
        params = {}
        
        # Known water bodies mapping
        water_bodies = {
            "aral": "Aral Sea", "aral sea": "Aral Sea",
            "chad": "Lake Chad", "lake chad": "Lake Chad",
            "urmia": "Lake Urmia", "lake urmia": "Lake Urmia",
            "dead sea": "Dead Sea",
            "mead": "Lake Mead", "lake mead": "Lake Mead",
            "powell": "Lake Powell", "lake powell": "Lake Powell",
            "poopo": "Lake Poopo", "lake poopo": "Lake Poopo",
            "balkhash": "Lake Balkhash", "lake balkhash": "Lake Balkhash",
            "turkana": "Lake Turkana", "lake turkana": "Lake Turkana",
            "titicaca": "Lake Titicaca", "lake titicaca": "Lake Titicaca",
            "victoria": "Lake Victoria", "lake victoria": "Lake Victoria",
            "nasser": "Lake Nasser", "lake nasser": "Lake Nasser",
            "three gorges": "Three Gorges",
            "indus delta": "Indus Delta",
            "ganges delta": "Ganges Delta",
            "mekong delta": "Mekong Delta",
            "caspian": "Caspian Sea", "caspian sea": "Caspian Sea",
            "salton": "Salton Sea", "salton sea": "Salton Sea"
        }
        
        # Find water body name
        for key, name in water_bodies.items():
            if key in query_lower:
                params["location_name"] = name
                break
        
        # Extract years
        years = re.findall(r'\\b(19[89]\\d|20[012]\\d)\\b', user_query)
        
        if len(years) >= 2:
            params["start_year"] = int(min(years))
            params["end_year"] = int(max(years))
        elif len(years) == 1:
            year = int(years[0])
            if year < 2000:
                params["start_year"] = year
                params["end_year"] = 2021
            else:
                params["start_year"] = 1984
                params["end_year"] = year
        else:
            params["start_year"] = 1984
            params["end_year"] = 2021
        
        # Check for animation request
        if any(kw in query_lower for kw in ["animation", "animate", "timelapse", "time-lapse", "gif", "over time"]):
            params["include_animation"] = True
        else:
            params["include_animation"] = True  # Default to true
        
        # Check for slow animation request
        if any(kw in query_lower for kw in ["slow", "slowly", "detailed"]):
            params["animation_fps"] = 0.5
        else:
            params["animation_fps"] = 1.0
        
        return params