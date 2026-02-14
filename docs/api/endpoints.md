# API Endpoints

> Complete list of all REST API endpoints in GEOWISE.

**Base URL:** `/api/v1`



---

## Query — Natural Language Interface

 

`POST /query/nl`

Main natural language query endpoint. Sends the user's text to the LLM Orchestrator, which parses intent, executes the appropriate analysis, and returns data + an AI-generated report.





`GET /query/examples`

Returns a list of example queries for each supported domain. Used by the frontend to show users what they can ask.



`GET /query/health`

Checks Groq API connectivity. Returns whether the LLM service is reachable and responding.



## Fires — Detection & Analysis



`GET /fires/`

Query fire detections with filters. Supports filtering by country ISO code, date range (`date_start`, `date_end`), minimum FRP, confidence level, and result limit.



`GET /fires/live/{country_iso}`

Fetch real-time fire detections from the NASA FIRMS API for a specific country. Returns fires from the last N days (default: 2 days).

 

`POST /fires/aggregate`

Perform H3 hexagonal spatial aggregation on fire data. Accepts resolution (5-9), country, and date range. Returns aggregated counts, average FRP, and brightness per hexagon.

 

`GET /fires/stats`

Get summary statistics for fire data. Returns total count, average FRP, high-confidence fire count, and date range.

 

---

## Forest — Deforestation Tracking

 

`GET /forest/loss/{country_iso}`

Retrieve yearly tree cover loss data for a country (2001-2024). Returns hectares lost per year from the Global Forest Watch API.

 

`GET /forest/stats/{country_iso}`

Get comprehensive forest statistics for a country. Includes total loss, peak year, trend direction, and average annual loss.

 

`GET /forest/trend/{country_iso}`

Get trend classification for a country's deforestation. Returns one of: INCREASING, DECREASING, or STABLE, based on recent-year analysis.

 

`GET /forest/tiles`

Returns the GFW tile server configuration for rendering forest loss layers on the map.

 

---

## Floods — SAR-Based Detection

 

`POST /floods/detect`

Main flood detection endpoint. Uses Sentinel-1 SAR change detection via Google Earth Engine. Accepts location name, location type, country, date ranges (before/after), and optional buffer. Returns flood extent tiles, flood area in km2, and map center/zoom.

Response time: ~5-8 seconds.

 

`GET /floods/detect/quick`

GET-based flood detection with query parameters instead of a POST body. Same functionality as the POST endpoint but accessible via URL parameters.

 

`GET /floods/statistics`

On-demand detailed statistics for the most recent flood detection. Returns exposed population (WorldPop), flooded cropland (ESA WorldCover), and flooded urban area. Requires a prior flood detection to have been run.

 

`GET /floods/optical`

On-demand optical imagery for the most recent flood detection area. Returns Sentinel-2 tile URLs for true color (RGB), NDWI (water index), and false color composites. Requires a prior flood detection and cloud-free imagery availability.

 

`GET /floods/optical/check`

Check whether cloud-free Sentinel-2 optical imagery is available for the most recent flood detection area. Metadata-only check (fast).

 

`GET /floods/presets`

Returns available flood detection presets with their configurations:

- **rural_riverine** — 2.0 dB threshold, VV polarization
- **urban** — 1.5 dB threshold, VV+VH polarization
- **coastal** — 2.5 dB threshold, VV polarization
- **flash_flood** — 1.8 dB threshold, shorter before window
- **wetland** — 1.2 dB threshold, sensitive to shallow water

 

`GET /floods/admin/{country}`

List all provinces/states for a given country. Used by the frontend for location selection dropdowns.

 

`GET /floods/districts/{country}/{province}`

List all districts within a specific province. Used for drill-down location selection.

 

`GET /floods/health`

Check Google Earth Engine service health. Returns whether GEE is initialized and responding.

 

---

## MPC — Satellite Imagery Search

 

`POST /mpc/query`

Query the Microsoft Planetary Computer for satellite imagery. Searches the ESA WorldCover collection (10m resolution, 11 land use classes) for a given location. Returns STAC items and tile URLs.

 

`GET /mpc/coverage`

Returns data availability information for the Planetary Computer collections.

 

---

## Tiles — Map Layer Generation

 

`GET /tiles/fire-density`

Generate fire density data as H3 hexagonal GeoJSON. Each hexagon contains fire count, average FRP, and brightness. Used for choropleth map layers.

 

`GET /tiles/heatmap`

Generate fire heatmap data as an array of `[latitude, longitude, intensity]` points. Used for heatmap visualization layers.

 

`GET /tiles/{country_iso}/drivers`

Get deforestation driver tile URLs from Google Earth Engine for a specific country. Returns tile URLs for 7 driver categories (commodity-driven, shifting agriculture, forestry, wildfire, urbanization, etc.).

 

---

## Analysis — Correlation

 

`POST /analysis/correlation`

Run spatial correlation analysis between datasets (e.g., fire-temperature, fire-deforestation). Uses H3 hexagonal spatial joins and scipy statistical methods (Pearson, Spearman).

 

---

## Health — System Status

 

`GET /health/`

System health check. Returns service name, version, and overall status.
