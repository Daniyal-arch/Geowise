"""Report Generation Agent - WITH FLOOD SUPPORT (v5.2 Fixed)"""

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
    - query_floods: SAR-based flood detection 
    - flood_statistics: On-demand population/cropland stats 
    - flood_optical: On-demand optical imagery 
    - query_mpc_images: Satellite imagery search
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
        
        # v5.2: Handle flood follow-up intents
        if intent == "flood_statistics":
            return self._generate_flood_statistics_report(analysis_result)
        if intent == "query_urban_expansion":
           return self._generate_urban_expansion_report(analysis_result)
        if intent == "flood_optical":
            return self._generate_flood_optical_report(analysis_result)
        
        if intent == "query_surface_water":
            return self._generate_surface_water_report(analysis_result)
        #  Handle MPC queries
        if intent == "query_mpc_images":
            return self._generate_mpc_report(analysis_result)
        
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
    def _generate_urban_expansion_report(self, result: Dict[str, Any]) -> str:
        """Generate report for urban expansion analysis."""
        
        data = result.get("data", {})
        
        location_name = data.get("location_name", "Unknown")
        country = data.get("country", "")
        start_year = data.get("start_year", 1975)
        end_year = data.get("end_year", 2020)
        stats = data.get("statistics", {})
        population = data.get("population", {})
        animation = data.get("animation", {})
        
        # Extract statistics
        area_start = stats.get("area_start_ha", 0)
        area_end = stats.get("area_end_ha", 0)
        growth_percent = stats.get("growth_percent", 0)
        annual_rate = stats.get("annual_growth_rate", 0)
        multiplier = stats.get("growth_multiplier", 0)
        
        # Determine growth category
        if multiplier >= 20:
            growth_category = "🚀 **EXPLOSIVE**"
            growth_desc = "One of the fastest-growing cities in the world"
        elif multiplier >= 10:
            growth_category = "📈 **RAPID**"
            growth_desc = "Exceptional urban expansion over the analysis period"
        elif multiplier >= 5:
            growth_category = "📊 **SIGNIFICANT**"
            growth_desc = "Strong urban growth trajectory"
        elif multiplier >= 2:
            growth_category = "📉 **MODERATE**"
            growth_desc = "Steady urban development"
        else:
            growth_category = "➡️ **STABLE**"
            growth_desc = "Limited expansion, relatively stable urban footprint"
        
        report = f"""## 🏙️ Urban Expansion Analysis: {location_name}

    ### Overview

    Analysis of urban growth in **{location_name}, {country}** from **{start_year}** to **{end_year}**.

    ### Key Findings

    | Metric | {start_year} | {end_year} | Change |
    |--------|------|------|--------|
    | **Built-up Area** | {area_start:,.0f} ha | {area_end:,.0f} ha | +{stats.get('absolute_growth_ha', 0):,.0f} ha |
    | **Growth** | - | - | **{growth_percent:.1f}%** |

    ### Growth Assessment

    {growth_category} - {growth_desc}

    - **{multiplier:.0f}x expansion** since {start_year}
    - **{annual_rate:.1f}%** average annual growth rate
    - From {area_start:,.0f} hectares to {area_end:,.0f} hectares

    """
        
        # Add population if available
        if population:
            pop_start = population.get("population_start", 0)
            pop_end = population.get("population_end", 0)
            pop_growth = population.get("population_growth_percent", 0)
            density_start = population.get("density_start_per_ha", 0)
            density_end = population.get("density_end_per_ha", 0)
            
            report += f"""### Population Trends

    | Metric | {population.get('start_year', 'Start')} | {population.get('end_year', 'End')} |
    |--------|------|------|
    | **Population** | {pop_start:,} | {pop_end:,} |
    | **Growth** | - | **+{pop_growth:.1f}%** |
    | **Density** | {density_start:.0f}/ha | {density_end:.0f}/ha |

    """
            
            # Density analysis
            if density_end < density_start * 0.8:
                report += "📉 **Urban Sprawl Detected**: Population density is decreasing, indicating horizontal expansion rather than densification.\n\n"
            elif density_end > density_start * 1.2:
                report += "📈 **Densification Trend**: Population density is increasing, indicating vertical growth and intensification.\n\n"
            else:
                report += "➡️ **Balanced Growth**: Urban expansion and population growth are roughly proportional.\n\n"
        
        # Animation info
        if animation and animation.get("gif_url"):
            report += f"""### 🎬 Animation

    A timelapse animation showing {animation.get('frame_count', 0)} frames from {start_year} to {end_year} is available.

    [Click to view/download GIF]({animation.get('gif_url')})

    """
        
        report += f"""### Map Layers

    Toggle these layers to explore:
    - 🟠 **Built-up {end_year}** - Current urban density
    - 🔵 **Urbanization Timeline** - When each area became urban
    - 🔴 **New Urban** - Areas that urbanized during analysis period

    ### Methodology

    - **Data Source**: JRC Global Human Settlement Layer (GHSL) P2023A
    - **Resolution**: 100 meters
    - **Sensor**: Landsat + Sentinel composite
    - **Urban Definition**: >500 sq m built surface per pixel

    *Analysis generated from GHSL Built-up Surface (GHS_BUILT_S) and Population (GHS_POP) datasets.*
    """
        
        return report
    async def _generate_flood_report(self, result: Dict[str, Any]) -> str:
        """
        Generate flood-specific report based on response level.
        
        v5.2: Initial report shows ONLY flood extent, NOT population/cropland
        
        Handles:
        - level: 'overview' → Large area, map only, suggests sub-regions
        - level: 'detailed' → Flood extent only (stats on-demand)
        """
        
        data = result.get("data", {})
        level = result.get("level", "detailed")
        ai_guidance = result.get("ai_guidance", {})
        
        location_name = data.get("location_name", "Unknown")
        country = data.get("country", "")
        province = data.get("province", "")
        area_km2 = data.get("area_km2", 0)
        dates = data.get("dates", {})
        images_used = data.get("images_used", {})
        
        # Format date info
        before_dates = dates.get("before", {})
        after_dates = dates.get("after", {})
        before_str = f"{before_dates.get('start', 'N/A')} to {before_dates.get('end', 'N/A')}"
        after_str = f"{after_dates.get('start', 'N/A')} to {after_dates.get('end', 'N/A')}"
        
        # Location string
        location_parts = [location_name]
        if province:
            location_parts.append(province)
        if country:
            location_parts.append(country)
        location_str = ", ".join(location_parts)
        
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

I've generated a **flood extent map** for {location_str} covering **{area_km2:,.0f} km²**.

**Analysis Period:**
- Pre-flood: {before_str}
- Post-flood: {after_str}
- SAR Images: {images_used.get('before', 0)} before / {images_used.get('after', 0)} after

### ⚠️ Large Area Notice

{message}

The flood visualization is displayed on the map, but detailed impact statistics (population affected, cropland damage) require analysis at a smaller geographic scale.

### 📍 Available {next_level.title()}s

For detailed flood impact analysis, please query one of these {next_level}s:

**{regions_str}**

### 💡 Example Query

Try: *"{example_query}"*

### What You Can See

- 🔴 **Flood Extent** - Detected flooded areas
- 🔵 **SAR Change** - Backscatter difference
- ⚪ **SAR Before/After** - Raw radar imagery
- 🔵 **Permanent Water** - Excluded from detection

*Click on a {next_level} name above or type a new query to get detailed statistics.*
"""
            return report
        
        # ─────────────────────────────────────────────────────────────────────
        # CASE 2: DETAILED (Small Area) - v5.2 FIXED: NO POPULATION/CROPLAND
        # ─────────────────────────────────────────────────────────────────────
        
        else:
            stats = data.get("statistics", {})
            methodology = data.get("methodology", {})
            optical_avail = data.get("optical_availability", {})
            
            flood_area_km2 = stats.get("flood_area_km2", 0)
            flood_area_ha = stats.get("flood_area_ha", 0)
            
            # Calculate flood percentage
            flood_percent = (flood_area_km2 / area_km2 * 100) if area_km2 > 0 else 0
            
            # Severity assessment based on % flooded
            if flood_percent > 30:
                severity = " **SEVERE**"
                severity_desc = "Major flooding detected affecting a large portion of the area."
            elif flood_percent > 15:
                severity = " **SIGNIFICANT**"
                severity_desc = "Significant flooding detected across multiple zones."
            elif flood_percent > 5:
                severity = " **MODERATE**"
                severity_desc = "Moderate flooding detected in low-lying areas."
            else:
                severity = " **LIMITED**"
                severity_desc = "Limited flooding detected, mostly in flood-prone zones."
            
            # Build the report - NO POPULATION/CROPLAND
            report = f"""##  Flood Detection Complete

### Location
**{location_str}**
- Total Area: {area_km2:,.0f} km²

### Analysis Period
- **Pre-flood baseline:** {before_str}
- **Post-flood period:** {after_str}
- **SAR images analyzed:** {images_used.get('before', 0)} before, {images_used.get('after', 0)} after

### Key Findings

| Metric | Value |
|--------|-------|
| **Flood Extent** | {flood_area_km2:,.2f} km² ({flood_area_ha:,.0f} ha) |
| **Area Flooded** | {flood_percent:.1f}% of {location_name} |

### Severity Assessment

{severity} - {severity_desc}

### Analysis Details

- **Detection Method:** Sentinel-1 SAR Change Detection
- **Resolution:** {methodology.get('resolution', '10m')}
- **Threshold:** {methodology.get('threshold', '-3dB backscatter reduction')}
- **Data Source:** European Space Agency Copernicus

### Map Layers Available

Toggle these layers in the sidebar:
-  **Flood Extent** - Detected flood areas
-  **SAR Change** - Backscatter difference visualization
-  **SAR Before/After** - Raw radar imagery comparison
-  **Permanent Water** - Baseline water bodies (excluded from detection)

---

###  Get More Details

"""
            # Add follow-up hints
            report += "- Type **\"show statistics\"** to load population & cropland impact data\n"
            
            if optical_avail.get("available"):
                report += "- Type **\"show optical\"** to add Sentinel-2 satellite imagery\n"
            else:
                report += f"- Optical imagery: {optical_avail.get('message', 'Not available for this period')}\n"
            
            report += "\n*Data sources: Sentinel-1 SAR, WorldPop 2020, ESA WorldCover 2021, JRC Global Surface Water*"
            
            return report
    
    # =========================================================================
    # v5.2: FLOOD STATISTICS REPORT (On-Demand)
    # =========================================================================
    
    def _generate_flood_statistics_report(self, result: Dict[str, Any]) -> str:
        """Generate report for on-demand flood statistics."""
        
        data = result.get("data", {})
        stats = data.get("statistics", data)
        location_name = data.get("location_name", "the area")
        
        exposed_pop = stats.get("exposed_population", 0)
        cropland_ha = stats.get("flooded_cropland_ha", 0)
        urban_ha = stats.get("flooded_urban_ha", 0)
        
        report = f"""##  Impact Statistics Loaded

### Population Exposure

**{exposed_pop:,} people** are located in flood-affected areas of {location_name}.

"""
        # Add context based on population
        if exposed_pop > 100000:
            report += " **High population exposure** - This represents a significant humanitarian concern requiring immediate attention.\n\n"
        elif exposed_pop > 10000:
            report += "This represents moderate population exposure in the affected region.\n\n"
        elif exposed_pop > 0:
            report += "Population exposure is relatively limited in this area.\n\n"
        else:
            report += "No significant population centers detected in the flooded zones.\n\n"
        
        report += f"""### Agricultural Impact

**{cropland_ha:,.0f} hectares** of cropland affected by flooding.

"""
        if cropland_ha > 10000:
            report += " **Severe agricultural impact** - Potential food security and economic implications.\n\n"
        elif cropland_ha > 1000:
            report += "Moderate agricultural damage detected in the flood zone.\n\n"
        elif cropland_ha > 0:
            report += "Limited cropland affected.\n\n"
        
        report += f"""### Urban Areas

**{urban_ha:,.0f} hectares** of built-up/urban land flooded.

"""
        if urban_ha > 100:
            report += " Urban flooding detected - infrastructure and property damage likely.\n\n"
        
        report += """### Summary

"""
        # Generate summary based on all stats
        if exposed_pop > 50000 or cropland_ha > 5000:
            report += f"The flooding in {location_name} has caused **significant humanitarian and economic impact**, affecting {exposed_pop:,} people and {cropland_ha:,.0f} hectares of agricultural land.\n\n"
        else:
            report += f"The flooding in {location_name} shows **moderate impact** with {exposed_pop:,} people in affected areas and {cropland_ha:,.0f} hectares of cropland flooded.\n\n"
        
        report += """---

💡 Type **\"show optical\"** to view before/after satellite imagery

*Data sources: WorldPop 2020 (population), ESA WorldCover 2021 (land cover)*
"""
        
        return report
    
    # =========================================================================
    # v5.2: FLOOD OPTICAL REPORT (On-Demand)
    # =========================================================================
    
    def _generate_flood_optical_report(self, result: Dict[str, Any]) -> str:
        """Generate report for on-demand optical imagery."""
        
        data = result.get("data", {})
        tiles = data.get("tiles", {})
        location_name = data.get("location_name", "the area")
        layer_descriptions = data.get("layer_descriptions", {})
        
        # Count available layers
        available_layers = [k for k, v in tiles.items() if v]
        
        report = f"""##  Optical Imagery Loaded

Sentinel-2 satellite imagery has been added to the map for {location_name}.

### Available Layers

| Layer | Description | Status |
|-------|-------------|--------|
"""
        
        layer_info = {
            "optical_before": (" Optical Before", "Pre-flood true color imagery"),
            "optical_after": (" Optical After", "Post-flood true color imagery"),
            "false_color_after": (" False Color", "Vegetation=red, Water=dark blue"),
            "ndwi_after": (" NDWI", "Water index (bright=water, dark=land)")
        }
        
        for key, (name, desc) in layer_info.items():
            if tiles.get(key):
                report += f"| {name} | {desc} |  Loaded |\n"
            else:
                report += f"| {name} | {desc} | Not available |\n"
        
        report += f"""
### Viewing Tips

1. **Compare Before/After:** Toggle between optical before and after to see flood impact
2. **False Color:** Vegetation appears red, water appears dark blue - flooded vegetation shows as dark
3. **NDWI Index:** Water bodies appear bright white, making flood extent clearly visible
4. **Layer Opacity:** Use the sidebar sliders to adjust transparency and overlay with SAR data

### How to Use

- Toggle layers using the **sidebar controls** on the left
- Combine with SAR flood extent layer for validation
- False color is excellent for identifying flooded agricultural areas

*{len(available_layers)} optical layer(s) loaded from Sentinel-2 (ESA Copernicus)*
"""
        
        return report
    
    # =========================================================================
    # ERROR & FALLBACK REPORTS
    # =========================================================================
    # =========================================================================
    # MPC SATELLITE IMAGERY REPORT
    # =========================================================================

    def _generate_mpc_report(self, result: Dict[str, Any]) -> str:
        """Generate report for MPC satellite imagery search."""
        
        data = result.get("data", {})
        
        location = data.get("location", "Unknown")
        collection = data.get("collection", "")
        images_found = data.get("images_found", 0)
        area_km2 = data.get("area_km2", 0)
        
        # Collection names
        collection_names = {
            "sentinel-2-l2a": "Sentinel-2 Level-2A",
            "landsat-c2-l2": "Landsat Collection 2 Level-2",
            "hls": "Harmonized Landsat Sentinel-2 (HLS)"
        }
        
        collection_display = collection_names.get(collection, collection)
        
        # Get date range
        query_params = data.get("query_params", {})
        date_range = query_params.get("dates", "N/A")
        
        report = f"""## 🛰️ Satellite Imagery Search Results

    ### Location
    **{location}** ({area_km2:,.0f} km²)

    ### Search Parameters
    - **Collection:** {collection_display}
    - **Date Range:** {date_range}
    - **Max Cloud Cover:** 30%
    - **Images Found:** {images_found}

    """
        
        images = data.get("images", [])
        
        if images:
            # Get best image (lowest cloud)
            best_image = min(images, key=lambda x: x.get("cloud_cover", 100))
            
            report += f"""### 🌟 Best Image
    - **Date:** {best_image.get("datetime", "").split("T")[0]}
    - **Cloud Cover:** {best_image.get("cloud_cover", 0):.1f}%
    - **ID:** {best_image.get("id")}

    """
            
            # Show recent images (last 10)
            recent_images = sorted(images, key=lambda x: x.get("datetime", ""), reverse=True)[:10]
            
            report += """### 📅 Recent Images

    | Date | Cloud Cover |
    |------|-------------|
    """
            
            for img in recent_images:
                date_str = img.get("datetime", "").split("T")[0] if img.get("datetime") else "N/A"
                cloud = img.get("cloud_cover")
                cloud_str = f"{cloud:.1f}%" if cloud is not None else "N/A"
                
                report += f"| {date_str} | {cloud_str} |\n"
        
        report += f"""
    ---

    *Satellite imagery loaded on map. Use layer controls to switch between Natural Color, False Color, and NDVI.*
    *Data source: Microsoft Planetary Computer*
    """
        
        return report
    def _generate_error_report(self, result: Dict[str, Any]) -> str:
        """Generate report for error cases."""
        
        error = result.get("message", result.get("error", "Unknown error"))
        suggestion = result.get("suggestion", "")
        
        report = f"""##  Analysis Error

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

    def _generate_surface_water_report(self, result: Dict[str, Any]) -> str:
        """Generate report for surface water analysis."""
        
        data = result.get("data", {})
        
        location_name = data.get("location_name", "Unknown")
        country = data.get("country", "")
        water_type = data.get("water_body_type", "water body")
        description = data.get("description", "")
        start_year = data.get("start_year", 1984)
        end_year = data.get("end_year", 2021)
        stats = data.get("statistics", {})
        animation = data.get("animation")
        time_series = data.get("time_series", [])
        
        # Extract statistics
        max_extent = stats.get("max_extent_km2", 0)
        current_total = stats.get("current_total_km2", 0)
        lost_water = stats.get("lost_water_km2", 0)
        new_water = stats.get("new_water_km2", 0)
        net_change = stats.get("net_change_km2", 0)
        loss_percent = stats.get("loss_percent", 0)
        current_percent = stats.get("current_vs_max_percent", 0)
        
        # Determine change category
        if loss_percent >= 75:
            change_category = "🚨 **CRITICAL**"
            change_desc = "Catastrophic water loss - environmental disaster"
        elif loss_percent >= 50:
            change_category = "⚠️ **SEVERE**"
            change_desc = "Major water loss - urgent concern"
        elif loss_percent >= 25:
            change_category = "📉 **SIGNIFICANT**"
            change_desc = "Notable water reduction"
        elif net_change < 0:
            change_category = "📊 **MODERATE LOSS**"
            change_desc = "Some water loss detected"
        elif net_change > 0:
            change_category = "📈 **GROWING**"
            change_desc = "Water area has increased"
        else:
            change_category = "➡️ **STABLE**"
            change_desc = "Relatively stable water extent"
        
        report = f"""## 💧 Surface Water Analysis: {location_name}

### Overview

Analysis of water changes in **{location_name}** ({country}) from **{start_year}** to **{end_year}**.

{f'*{description}*' if description else ''}

### Key Statistics

| Metric | Value |
|--------|-------|
| **Maximum Historical Extent** | {max_extent:,.0f} km² |
| **Current Water Area** | {current_total:,.0f} km² |
| **Water Lost** | {lost_water:,.0f} km² |
| **Water Gained** | {new_water:,.0f} km² |
| **Net Change** | {net_change:+,.0f} km² |

### Change Assessment

{change_category} - {change_desc}

- **{loss_percent:.1f}%** of historical water lost
- Currently at **{current_percent:.1f}%** of maximum extent
- {f'Lost {lost_water:,.0f} km² since {start_year}' if lost_water > 0 else 'No significant loss'}

"""
        
        # Add time series summary if available
        if time_series and len(time_series) >= 2:
            first_year = time_series[0]
            last_year = time_series[-1]
            
            if first_year.get("water_area_km2") and last_year.get("water_area_km2"):
                series_change = last_year["water_area_km2"] - first_year["water_area_km2"]
                series_pct = (series_change / first_year["water_area_km2"] * 100) if first_year["water_area_km2"] > 0 else 0
                
                report += f"""### Time Series ({first_year['year']} → {last_year['year']})

| Year | Water Area |
|------|------------|
| **{first_year['year']}** | {first_year['water_area_km2']:,.0f} km² |
| **{last_year['year']}** | {last_year['water_area_km2']:,.0f} km² |
| **Change** | {series_change:+,.0f} km² ({series_pct:+.1f}%) |

"""
        
        # Add animation info
        if animation and animation.get("gif_url"):
            report += f"""### 🎬 Animation

A timelapse animation showing {animation.get('frame_count', 0)} frames from {start_year} to {end_year} is available.

[Click to view/download GIF]({animation.get('gif_url')})

**Animation speed:** {animation.get('fps', 1)} fps ({' slower' if animation.get('fps', 1) < 1 else 'normal'})

"""
        
        report += f"""### Map Layers

Toggle these layers to explore:
- 💧 **Current Water** - Water present >50% of the time
- 👻 **Maximum Extent** - Largest historical water area
- 🔴 **Lost Water** - Areas that were water, now dry
- 🟢 **New Water** - Areas that were dry, now water
- 📊 **Water Occurrence** - Percentage of time water was present
- 📅 **Seasonality** - Months per year with water

### Methodology

- **Data Source**: JRC Global Surface Water (GSW) v1.4
- **Resolution**: 30 meters (Landsat-derived)
- **Temporal Coverage**: 1984-2021 (37 years)
- **Water Detection**: Landsat surface reflectance classification

*Analysis generated from {end_year - start_year + 1} years of satellite observations.*
"""
        
        return report