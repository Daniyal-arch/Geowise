"""Query Understanding Agent"""

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
    
    ENHANCEMENTS:
    - Hybrid LLM + rule-based intent detection
    - Prioritized keyword matching to prevent intent confusion
    - Detects monthly breakdown queries
    - Detects high FRP fire queries
    - Detects historical correlation queries
    - Detects forest/deforestation queries
    - Fallback year extraction with regex
    
    CRITICAL FIX:
    - Forest keywords checked BEFORE correlation keywords
    - Prevents "analyze tree cover loss" from triggering correlation
    - More specific keyword matching with context awareness
    """
    
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set in environment")
        
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
    
    async def parse_query(self, user_query: str) -> Dict[str, Any]:
        """
        Parse natural language query into structured parameters
        
        WHY HYBRID APPROACH:
        - LLM handles complex natural language understanding
        - Rule-based logic catches specific patterns LLM might miss
        - Fallback regex ensures year extraction even if LLM fails
        - More reliable than pure LLM or pure rules alone
        
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
            
            # Step 2: Enhance with rule-based detection (IMPROVED ORDER)
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
        
        WHY THIS IS NEEDED:
        - LLMs sometimes miss specific keywords
        - Rule-based logic provides a safety net
        - Ensures consistent handling of common queries
        
        CRITICAL FIX - NEW DETECTION ORDER:
        1. Monthly queries (most specific)
        2. High FRP queries (most specific)
        3. Forest queries (CHECK BEFORE CORRELATION!) ← NEW POSITION
        4. Correlation queries (only if not forest-related)
        5. Trend analysis (fallback)
        
        WHY THIS ORDER:
        - Prevents "analyze tree cover loss" from triggering correlation
        - Checks for forest keywords BEFORE checking correlation keywords
        - More specific patterns matched first
        
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
            return parsed  # Early return - most specific
        
        # Pattern 2: High FRP fire queries (VERY SPECIFIC)
        high_frp_keywords = [
            "high frp", "intense fires", "severe fires", "strong fires", "strongest fires",
            "extreme fires", "powerful fires", "hottest fires", "biggest fires"
        ]
        if any(keyword in query_lower for keyword in high_frp_keywords):
            logger.info("Rule-based detection: High FRP query")
            parsed["intent"] = "query_high_frp"
            return parsed  # Early return
        
        # Pattern 3: Forest/Deforestation queries (CHECK BEFORE CORRELATION!)
        # This is critical - we check for forest keywords BEFORE correlation
        forest_keywords = [
            "forest", "deforestation", "tree loss", "tree cover",
            "forest loss", "deforestation trend", "yearly forest",
            "tree cover loss", "forest data", "tree cover data"
        ]
        
        # Check if query is about forests
        has_forest_context = any(keyword in query_lower for keyword in forest_keywords)
        
        if has_forest_context:
            # It's definitely a forest query - set intent and return
            logger.info("Rule-based detection: Forest/Deforestation query (forest context detected)")
            parsed["intent"] = "query_forest"
            return parsed  # Early return - prevents correlation trigger
        
        # Pattern 4: Correlation analysis queries (ONLY if NOT forest-related)
        # We only reach here if no forest keywords were found
        correlation_keywords = [
            "correlation", "correlate", "relationship",
            "impact of", "affect", "influence"
        ]
        
        # Additional check: if query mentions climate/temperature AND fires (not forests)
        climate_keywords = ["climate", "temperature", "weather", "precipitation", "wind"]
        fire_keywords = ["fire", "fires", "burning"]
        
        has_correlation_intent = any(keyword in query_lower for keyword in correlation_keywords)
        has_climate_context = any(keyword in query_lower for keyword in climate_keywords)
        has_fire_context = any(keyword in query_lower for keyword in fire_keywords)
        
        # Correlation if: (correlation keywords) OR (climate + fire keywords)
        if has_correlation_intent or (has_climate_context and has_fire_context):
            # Only set to correlation if not already a specific query type
            if parsed.get("intent") not in ["query_monthly", "query_high_frp", "query_forest"]:
                logger.info("Rule-based detection: Correlation analysis")
                parsed["intent"] = "analyze_correlation"
                return parsed
        
        # Pattern 5: Trend analysis queries (FALLBACK)
        trend_keywords = ["trend", "over time", "change over", "historical"]
        if any(keyword in query_lower for keyword in trend_keywords):
            if parsed.get("intent") not in ["query_monthly", "query_high_frp", "query_forest", "analyze_correlation"]:
                logger.info("Rule-based detection: Trend analysis")
                parsed["intent"] = "generate_report"
                return parsed
        
        # If no specific pattern matched, keep LLM's decision
        logger.info(f"No rule-based override - keeping LLM intent: {parsed.get('intent')}")
        return parsed
    
    def _extract_year(self, user_query: str) -> Optional[int]:
        """
        Extract year from query using regex fallback
        
        WHY FALLBACK EXTRACTION:
        - LLMs sometimes miss explicit years in queries
        - Regex provides a reliable fallback
        - Ensures year is captured for historical queries
        
        PATTERN:
        - Matches 4-digit years starting with 20 (2000-2099)
        - Example: "fires in Pakistan 2020" → extracts 2020
        
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
        
        WHY CUSTOM THRESHOLDS:
        - Users may specify "fires above 200 MW"
        - Default to 100 MW for "high intensity"
        - Allows flexible querying
        
        PATTERNS:
        - "above 150" → 150
        - "frp > 200" → 200
        - "more than 100" → 100
        - Default: 100 MW
        
        Args:
            user_query: User's query
        
        Returns:
            FRP threshold in MW
        """
        # Try to extract explicit FRP value
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
        
        # Default threshold for "high intensity" fires
        logger.info("Using default FRP threshold: 100 MW")
        return 100