"""Report Generation Agent - WITH FLOOD SUPPORT"""

import json
from typing import Dict, Any
from groq import AsyncGroq

from app.config import settings
from app.llm.prompts.system_prompts import REPORT_AGENT_PROMPT
from app.utils.logger import get_logger

import logging

logger = logging.getLogger(__name__)


class ReportAgent:
    """
    Generates natural language reports from analysis results.
    
    SUPPORTED INTENTS:
    - query_fires: Fire statistics and counts
    - query_monthly: Monthly fire breakdown
    - query_high_frp: High intensity fires
    - analyze_correlation: Fire-climate correlation
    - analyze_fire_forest_correlation: Fire-deforestation correlation
    - query_forest: Forest loss data
    - query_drivers: Deforestation drivers
    - query_fires_realtime: Real-time fire detection
    - query_floods: SAR-based flood detection 🌊
    - generate_report: Comprehensive reports
    """
    
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set")
        
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
    
    async def generate_report(self, analysis_result: Dict[str, Any]) -> str:
        """
        Generate natural language report from analysis results.
        
        Args:
            analysis_result: Result from orchestrator analysis
        
        Returns:
            Markdown-formatted report string
        """
        
        if analysis_result.get("status") == "error":
            return self._generate_error_report(analysis_result)
        
        intent = analysis_result.get("intent", "unknown")
        
        # Handle flood queries specially
        if intent == "query_floods":
            return await self._generate_flood_report(analysis_result)
        
        # Standard report generation for other intents
        prompt = REPORT_AGENT_PROMPT.replace(
            "{{results}}", 
            json.dumps(analysis_result, indent=2, default=str)
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an environmental data analyst. Generate clear, accurate reports."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return self._generate_fallback_report(analysis_result)
    
    async def _generate_flood_report(self, result: Dict[str, Any]) -> str:
        """
        Generate flood-specific report based on response level.
        
        Handles:
        - level: 'overview' → Large area, map only, suggests sub-regions
        - level: 'detailed' → Full statistics available
        """
        
        data = result.get("data", {})
        level = result.get("level", "detailed")
        ai_guidance = result.get("ai_guidance", {})
        
        location_name = data.get("location_name", "Unknown")
        country = data.get("country", "")
        area_km2 = data.get("area_km2", 0)
        dates = data.get("dates", {})
        images_used = data.get("images_used", {})
        
        # Format date info
        after_dates = dates.get("after", {})
        date_str = f"{after_dates.get('start', '')} to {after_dates.get('end', '')}"
        
        # ─────────────────────────────────────────────────────────────────────
        # CASE 1: OVERVIEW (Large Area)
        # ─────────────────────────────────────────────────────────────────────
        
        if level == "overview":
            suggestion = data.get("suggestion", {})
            sub_regions = suggestion.get("sub_regions", [])
            next_level = suggestion.get("next_level_type", "district")
            message = suggestion.get("message", "")
            example_query = suggestion.get("example_query", "")
            
            # Build sub-region list
            region_names = [r["name"] for r in sub_regions[:8]]
            regions_str = ", ".join(region_names)
            if len(sub_regions) > 8:
                regions_str += f", and {len(sub_regions) - 8} more"
            
            report = f"""## 🌊 Flood Mapping: {location_name}

### Overview

I've generated a **flood extent map** for {location_name}{f', {country}' if country else ''} covering **{area_km2:,.0f} km²**.

**Analysis Period:** {date_str}
**SAR Images Used:** {images_used.get('before', 0)} (before) / {images_used.get('after', 0)} (after flood)

### ⚠️ Large Area Notice

{message}

The flood visualization is displayed on the map, but detailed impact statistics (population affected, cropland damage, urban flooding) require analysis at a smaller geographic scale.

### 📍 Available {next_level.title()}s

For detailed flood impact analysis, please query one of these {next_level}s:

**{regions_str}**

### 💡 Example Query

Try: *"{example_query}"*

### What You Can See

- 🔴 **Flood Extent Layer** - Areas detected as flooded (red)
- 🔵 **SAR Change Detection** - Backscatter change between periods
- ⚪ **Before/After SAR** - Raw radar imagery comparison
- 🔵 **Permanent Water** - Excluded from flood detection

*Click on a {next_level} name above or type a new query to get detailed statistics.*
"""
            return report
        
        # ─────────────────────────────────────────────────────────────────────
        # CASE 2: DETAILED (Full Statistics)
        # ─────────────────────────────────────────────────────────────────────
        
        else:
            stats = data.get("statistics", {})
            methodology = data.get("methodology", {})
            
            flood_area_km2 = stats.get("flood_area_km2", 0)
            flood_area_ha = stats.get("flood_area_ha", 0)
            exposed_pop = stats.get("exposed_population", 0)
            cropland_ha = stats.get("flooded_cropland_ha", 0)
            urban_ha = stats.get("flooded_urban_ha", 0)
            
            # Calculate percentages
            flood_percent = (flood_area_km2 / area_km2 * 100) if area_km2 > 0 else 0
            
            # Severity assessment
            if flood_percent > 30:
                severity = "🔴 **SEVERE**"
                severity_desc = "Major flooding detected affecting a large portion of the area."
            elif flood_percent > 15:
                severity = "🟠 **SIGNIFICANT**"
                severity_desc = "Significant flooding detected across multiple zones."
            elif flood_percent > 5:
                severity = "🟡 **MODERATE**"
                severity_desc = "Moderate flooding detected in low-lying areas."
            else:
                severity = "🟢 **LIMITED**"
                severity_desc = "Limited flooding detected, mostly in flood-prone zones."
            
            report = f"""## 🌊 Flood Analysis: {location_name}

### Key Findings

| Metric | Value |
|--------|-------|
| **Flood Extent** | {flood_area_km2:,.2f} km² ({flood_area_ha:,.0f} ha) |
| **Area Flooded** | {flood_percent:.1f}% of {location_name} |
| **Population Exposed** | {exposed_pop:,} people |
| **Cropland Flooded** | {cropland_ha:,.0f} hectares |
| **Urban Area Flooded** | {urban_ha:,.0f} hectares |

### Severity Assessment

{severity} - {severity_desc}

### Analysis Details

**Location:** {location_name}{f', {country}' if country else ''}
**Total Area:** {area_km2:,.0f} km²
**Analysis Period:** {date_str}
**SAR Images:** {images_used.get('before', 0)} before / {images_used.get('after', 0)} after

### Methodology

- **Sensor:** {methodology.get('sensor', 'Sentinel-1 SAR')}
- **Technique:** {methodology.get('technique', 'Change detection')}
- **Resolution:** {methodology.get('resolution', '10m')}
- **Threshold:** {methodology.get('threshold', '3.0 dB')}

### Impact Summary

"""
            # Add impact bullets based on data
            if exposed_pop > 100000:
                report += f"- ⚠️ **High population exposure:** Over {exposed_pop:,} people in flood-affected areas\n"
            elif exposed_pop > 10000:
                report += f"- 👥 **Population at risk:** Approximately {exposed_pop:,} people exposed\n"
            elif exposed_pop > 0:
                report += f"- 👥 **Population exposure:** {exposed_pop:,} people in affected zones\n"
            
            if cropland_ha > 10000:
                report += f"- 🌾 **Severe agricultural impact:** {cropland_ha:,.0f} hectares of cropland flooded\n"
            elif cropland_ha > 1000:
                report += f"- 🌾 **Agricultural damage:** {cropland_ha:,.0f} hectares of cropland affected\n"
            elif cropland_ha > 0:
                report += f"- 🌾 **Cropland affected:** {cropland_ha:,.0f} hectares\n"
            
            if urban_ha > 100:
                report += f"- 🏘️ **Urban flooding:** {urban_ha:,.0f} hectares of built-up area inundated\n"
            elif urban_ha > 0:
                report += f"- 🏘️ **Urban areas affected:** {urban_ha:,.0f} hectares\n"
            
            report += """
### Map Layers

Toggle these layers in the map controls:
- 🔴 **Flood Extent** - Detected flood areas
- 🔵 **Change Detection** - SAR backscatter change
- ⚪ **Before/After SAR** - Raw radar comparison
- 🔵 **Permanent Water** - Baseline water bodies

*Data sources: Sentinel-1 SAR, WorldPop 2020, ESA WorldCover 2021, JRC Global Surface Water*
"""
            return report
    
    def _generate_error_report(self, result: Dict[str, Any]) -> str:
        """Generate report for error cases."""
        
        error = result.get("message", result.get("error", "Unknown error"))
        suggestion = result.get("suggestion", "")
        
        report = f"""## ❌ Analysis Error

**Error:** {error}

"""
        if suggestion:
            report += f"**Suggestion:** {suggestion}\n"
        
        return report
    
    def _generate_fallback_report(self, result: Dict[str, Any]) -> str:
        """Generate basic report when LLM fails."""
        
        intent = result.get("intent", "unknown")
        data = result.get("data", {})
        
        report = f"## Analysis Results\n\n"
        report += f"**Intent:** {intent}\n\n"
        
        if data:
            report += "### Data Summary\n\n"
            for key, value in data.items():
                if not isinstance(value, (dict, list)):
                    report += f"- **{key}:** {value}\n"
        
        return report


