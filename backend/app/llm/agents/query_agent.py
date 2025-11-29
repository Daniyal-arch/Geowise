"""Query Understanding Agent - WITH DRIVER DETECTION"""

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
    7. query_drivers - Deforestation drivers (NEW!)
    8. generate_report - Comprehensive reports
    
    FEATURES:
    - Hybrid LLM + rule-based intent detection
    - Prioritized keyword matching
    - Context-aware detection
    - Driver query detection
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
        3. Driver queries (NEW! - causes, drivers, why) 🟢
        4. Fire-Forest correlation (fires + forests together)
        5. Forest-only queries (only forests, no fires)
        6. Fire-Climate correlation (fires + climate, no forests)
        7. Trend analysis (fallback)
        
        Args:
            user_query: Original user query
            parsed: LLM-parsed result
        
        Returns:
            Enhanced parsed result with corrected intent
        """
        query_lower = user_query.lower()
        
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
        
        # 🟢 Pattern 3: Driver queries (NEW!)
        # Detects queries asking about causes/drivers/reasons for deforestation
        driver_keywords = [
            "cause", "causes", "driver", "drivers", "why", "reason", "reasons",
            "what caused", "what's causing", "what is causing", "what causes",
            "show drivers", "show causes", "show me drivers", "show me causes",
            "deforestation cause", "deforestation driver", "forest loss cause",
            "tree loss cause", "agriculture", "logging", "farming", "cattle",
            "palm oil", "soy", "urban", "fire driver"
        ]
        
        # Check if query is asking about drivers/causes
        has_driver_intent = any(keyword in query_lower for keyword in driver_keywords)
        
        # If driver-related keywords detected → query_drivers
        if has_driver_intent:
            logger.info("Rule-based detection: Driver query (causes/drivers)")
            parsed["intent"] = "query_drivers"
            parsed["show_drivers"] = True  # 🟢 Flag for frontend
            return parsed
        
        # Pattern 4: Fire-Forest correlation
        # Detects queries asking about BOTH fires AND forests together
        fire_keywords = ["fire", "fires", "burning", "burnt"]
        forest_keywords = ["forest", "deforestation", "tree loss", "tree cover", "forest loss"]
        
        has_fire = any(keyword in query_lower for keyword in fire_keywords)
        has_forest = any(keyword in query_lower for keyword in forest_keywords)
        
        # If query mentions BOTH fires AND forests → fire-forest correlation
        if has_fire and has_forest:
            logger.info("Rule-based detection: Fire-Forest correlation (fires + forests)")
            parsed["intent"] = "analyze_fire_forest_correlation"
            return parsed
        
        # Pattern 5: Forest/Deforestation queries (ONLY forest, no fires)
        if has_forest and not has_fire:
            logger.info("Rule-based detection: Forest query (forest only)")
            parsed["intent"] = "query_forest"
            return parsed
        
        # Pattern 6: Fire-Climate correlation (fires + climate, NOT forests)
        correlation_keywords = ["correlation", "correlate", "relationship", "impact of", "affect", "influence"]
        climate_keywords = ["climate", "temperature", "weather", "precipitation", "wind"]
        
        has_correlation_intent = any(keyword in query_lower for keyword in correlation_keywords)
        has_climate_context = any(keyword in query_lower for keyword in climate_keywords)
        
        # Correlation if: (correlation keywords) OR (climate + fire keywords)
        if has_correlation_intent or (has_climate_context and has_fire):
            if parsed.get("intent") not in ["query_monthly", "query_high_frp", "query_drivers", "query_forest", "analyze_fire_forest_correlation"]:
                logger.info("Rule-based detection: Fire-Climate correlation")
                parsed["intent"] = "analyze_correlation"
                return parsed
        
        # Pattern 7: Trend analysis queries (FALLBACK)
        trend_keywords = ["trend", "over time", "change over", "historical"]
        if any(keyword in query_lower for keyword in trend_keywords):
            if parsed.get("intent") not in ["query_monthly", "query_high_frp", "query_drivers", "query_forest", "analyze_correlation", "analyze_fire_forest_correlation"]:
                logger.info("Rule-based detection: Trend analysis")
                parsed["intent"] = "generate_report"
                return parsed
        
        # If no specific pattern matched, keep LLM's decision
        logger.info(f"No rule-based override - keeping LLM intent: {parsed.get('intent')}")
        return parsed
    
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