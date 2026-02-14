# Orchestrator Query Routing Architecture

> Interview-ready deep dive into how GEOWISE routes natural language queries to geospatial services.

---

## 1. High-Level Architecture (The 3-Stage Pipeline)

```
 ┌──────────────────────────────────────────────────────────────────────────┐
 │  USER: "Show floods in Sindh Pakistan 2022"                             │
 └──────────────────────────┬───────────────────────────────────────────────┘
                            │
                            ▼
 ┌──────────────────────────────────────────────────────────────────────────┐
 │                    STAGE 1: INTENT DETECTION                             │
 │                    (QueryAgent — Hybrid Approach)                        │
 │                                                                          │
 │  ┌─────────────────────┐     ┌──────────────────────────────┐           │
 │  │   LLM Parser        │     │   Rule-Based Override        │           │
 │  │   (Groq Llama 3.3)  │────▶│   (Priority Keyword Chain)   │           │
 │  │                     │     │                              │           │
 │  │  temp=0.1           │     │  11-level priority system    │           │
 │  │  max_tokens=500     │     │  First match wins            │           │
 │  │  Returns JSON       │     │  Overrides LLM if needed     │           │
 │  └─────────────────────┘     └──────────────┬───────────────┘           │
 │                                              │                           │
 │  Output: { intent: "query_floods", parameters: { location, dates... } } │
 └──────────────────────────────────────────────┬───────────────────────────┘
                                                │
                                                ▼
 ┌──────────────────────────────────────────────────────────────────────────┐
 │                    STAGE 2: INTENT ROUTING                               │
 │                    (Orchestrator — process_query)                        │
 │                                                                          │
 │  intent ──▶ if/elif chain ──▶ Handler Method ──▶ External Service       │
 │                                                                          │
 │  "query_floods"  ──▶  _query_floods()  ──▶  GEE Sentinel-1 SAR         │
 │  "query_fires"   ──▶  _query_fires()   ──▶  SQLite Database            │
 │  "query_urban"   ──▶  _query_urban()   ──▶  GEE GHSL Dataset           │
 │  ... 14 intents total                                                    │
 └──────────────────────────────────────────────┬───────────────────────────┘
                                                │
                                                ▼
 ┌──────────────────────────────────────────────────────────────────────────┐
 │                    STAGE 3: REPORT GENERATION                            │
 │                    (ReportAgent — Anti-Hallucination Prompt)             │
 │                                                                          │
 │  Raw data ──▶ Groq LLM + REPORT_AGENT_PROMPT ──▶ Markdown Report       │
 │                                                                          │
 │  Rules: NEVER invent statistics, forbidden phrases, verify before write  │
 └──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Stage 1 Deep Dive: Hybrid Intent Detection

This is the most interview-worthy design decision. The system uses **LLM + Rules** together, not either/or.

### Why Hybrid?

```
 Problem: LLMs are great at understanding language, but unreliable for classification.

 Example Failure:
   User: "Show me flooding in Sindh"
   LLM returns: { "intent": "query_fires" }    ← WRONG! LLM confused by geospatial context

 Solution: Let LLM try first, then override with deterministic keyword matching.
```

### The Two-Step Flow

```
 ┌────────────────────────────────────────────────────────────────────┐
 │                    QueryAgent.parse_query()                        │
 │                                                                    │
 │  STEP 1: LLM PARSE                                                │
 │  ┌──────────────────────────────────────────────────────────────┐ │
 │  │  System: "You are a geospatial query parser. Return ONLY     │ │
 │  │          valid JSON."                                         │ │
 │  │                                                               │ │
 │  │  User: QUERY_AGENT_PROMPT (544 lines!) with:                  │ │
 │  │    • Intent table (11 intents)                                │ │
 │  │    • Parameter extraction rules                               │ │
 │  │    • 30+ few-shot examples                                    │ │
 │  │    • Handling rules for unclear queries                       │ │
 │  │    • {{query}} replaced with user's actual text               │ │
 │  │                                                               │ │
 │  │  Model: Groq Llama 3.3 70B Versatile                         │ │
 │  │  Temperature: 0.1 (near-deterministic)                        │ │
 │  │  Max Tokens: 500                                              │ │
 │  │                                                               │ │
 │  │  Output: JSON with intent + parameters                        │ │
 │  └──────────────────────────────────────────────────────────────┘ │
 │                          │                                         │
 │                          ▼                                         │
 │  STEP 2: KEYWORD OVERRIDE (Safety Net)                             │
 │  ┌──────────────────────────────────────────────────────────────┐ │
 │  │  _enhance_intent_detection(query, llm_result)                │ │
 │  │                                                               │ │
 │  │  Priority-ordered keyword chain:                              │ │
 │  │  if "monthly/peak/highest" → force query_monthly              │ │
 │  │  elif "intense/severe fires" → force query_high_frp           │ │
 │  │  elif "cause/driver/why" → force query_drivers                │ │
 │  │  elif "flood/inundation" → force query_floods                 │ │
 │  │  elif "sentinel-2/landsat" → force query_mpc_images           │ │
 │  │  elif "urban/sprawl" → force query_urban_expansion            │ │
 │  │  elif "lake/reservoir" → force query_surface_water            │ │
 │  │  elif "air quality/no2" → force query_air_quality             │ │
 │  │  elif "realtime" + "fire" → force query_fires_realtime        │ │
 │  │  elif "fire" + "forest" → force fire_forest_correlation       │ │
 │  │  elif "forest" only → force query_forest                      │ │
 │  │  else → KEEP LLM's decision                                  │ │
 │  └──────────────────────────────────────────────────────────────┘ │
 │                          │                                         │
 │                          ▼                                         │
 │  STEP 3: FALLBACK YEAR EXTRACTION                                  │
 │  ┌──────────────────────────────────────────────────────────────┐ │
 │  │  Regex: r'\b(20\d{2})\b'                                     │ │
 │  │  If LLM missed the year, regex catches it                    │ │
 │  └──────────────────────────────────────────────────────────────┘ │
 │                          │                                         │
 │                          ▼                                         │
 │  STEP 4: DOMAIN-SPECIFIC PARAMETER EXTRACTION                      │
 │  ┌──────────────────────────────────────────────────────────────┐ │
 │  │  Each intent has its own extractor:                           │ │
 │  │  • _extract_flood_parameters()  → known events + date logic  │ │
 │  │  • _extract_urban_parameters()  → city name + year range     │ │
 │  │  • _extract_water_parameters()  → water body lookup          │ │
 │  │  • _extract_air_quality_parameters() → pollutant detection   │ │
 │  │  • _extract_frp_threshold()     → numeric threshold parse    │ │
 │  └──────────────────────────────────────────────────────────────┘ │
 └────────────────────────────────────────────────────────────────────┘
```

### Priority Chain — Why Order Matters

```
 Example: "What caused the floods in Pakistan?"

 Without priority:
   ✗ "floods" matches → query_floods
   ✗ "caused" matches → query_drivers
   Which one wins?

 With priority chain (drivers = priority 3, floods = priority 4):
   ✓ "caused" matches FIRST at priority 3 → query_drivers
   ✓ Flood keywords never even get checked

 ┌─────┬──────────────────┬──────────────────────┬──────────────────────┐
 │  #  │ Pattern Name     │ Keywords (samples)   │ Intent Assigned      │
 ├─────┼──────────────────┼──────────────────────┼──────────────────────┤
 │  1  │ Monthly          │ peak, highest,       │ query_monthly        │
 │     │                  │ monthly, per month   │                      │
 ├─────┼──────────────────┼──────────────────────┼──────────────────────┤
 │  2  │ High FRP         │ intense fires,       │ query_high_frp       │
 │     │                  │ severe, extreme      │                      │
 ├─────┼──────────────────┼──────────────────────┼──────────────────────┤
 │  3  │ Drivers          │ cause, driver, why,  │ query_drivers        │
 │     │                  │ agriculture, logging │                      │
 ├─────┼──────────────────┼──────────────────────┼──────────────────────┤
 │  4  │ Floods           │ flood, inundation,   │ query_floods         │
 │     │                  │ submerged, deluge    │                      │
 ├─────┼──────────────────┼──────────────────────┼──────────────────────┤
 │ 4.1 │ MPC Satellite    │ sentinel-2, landsat, │ query_mpc_images     │
 │     │                  │ planetary computer   │                      │
 ├─────┼──────────────────┼──────────────────────┼──────────────────────┤
 │ 4.2 │ Urban Expansion  │ urban, sprawl, city  │ query_urban_expansion│
 │     │                  │ growth, built-up     │                      │
 ├─────┼──────────────────┼──────────────────────┼──────────────────────┤
 │ 4.3 │ Surface Water    │ lake, reservoir,     │ query_surface_water  │
 │     │                  │ water level, dam     │                      │
 ├─────┼──────────────────┼──────────────────────┼──────────────────────┤
 │ 4.4 │ Air Quality      │ air quality, no2,    │ query_air_quality    │
 │     │                  │ smog, pollution      │                      │
 ├─────┼──────────────────┼──────────────────────┼──────────────────────┤
 │  5  │ Realtime Fire    │ realtime + fire      │ query_fires_realtime │
 │     │ (compound)       │ (BOTH required)      │                      │
 ├─────┼──────────────────┼──────────────────────┼──────────────────────┤
 │  6  │ Fire+Forest      │ fire + forest        │ fire_forest_         │
 │     │ (compound)       │ (BOTH required)      │ correlation          │
 ├─────┼──────────────────┼──────────────────────┼──────────────────────┤
 │  7  │ Forest Only      │ forest but NOT fire  │ query_forest         │
 │     │ (exclusive)      │ (subtraction logic)  │                      │
 ├─────┼──────────────────┼──────────────────────┼──────────────────────┤
 │  8  │ Fire+Climate     │ correlation +        │ analyze_correlation  │
 │     │ (guarded)        │ climate keywords     │ (with guard clause)  │
 ├─────┼──────────────────┼──────────────────────┼──────────────────────┤
 │  9  │ Trends           │ trend, over time     │ generate_report      │
 │     │ (fallback)       │ (lowest priority)    │ (catch-all)          │
 └─────┴──────────────────┴──────────────────────┴──────────────────────┘

 Note the 3 different matching strategies:
 ┌──────────────┬────────────────────────────────────────────────────┐
 │ Simple       │ ANY keyword in list → match (priorities 1-4.4)    │
 │ Compound     │ Keywords from TWO lists BOTH present (5, 6)       │
 │ Exclusive    │ One set present AND another set ABSENT (7)        │
 └──────────────┴────────────────────────────────────────────────────┘
```

---

## 3. Stage 2 Deep Dive: Orchestrator Routing

### Pre-Parse Fast Paths (Before LLM even runs)

```
 ┌────────────────────────────────────────────────────────────────────┐
 │           orchestrator.process_query(user_query)                   │
 │                                                                    │
 │  query_lower = user_query.lower()                                  │
 │                                                                    │
 │  ┌────────────────────────────────────────────────────────────┐   │
 │  │  FAST PATH 1: MPC Query                                    │   │
 │  │  _is_mpc_query() checks for "sentinel-2", "landsat", etc. │   │
 │  │  → Skips QueryAgent entirely → direct to _query_mpc()     │   │
 │  └────────────────────────────────────────────────────────────┘   │
 │                          │ NO                                      │
 │                          ▼                                         │
 │  ┌────────────────────────────────────────────────────────────┐   │
 │  │  FAST PATH 2: Flood Follow-Up ("show statistics")          │   │
 │  │  _is_statistics_request() checks trigger phrases            │   │
 │  │  → Uses cached _last_flood_result from previous query      │   │
 │  │  → Calls flood_service.get_detailed_statistics()           │   │
 │  └────────────────────────────────────────────────────────────┘   │
 │                          │ NO                                      │
 │                          ▼                                         │
 │  ┌────────────────────────────────────────────────────────────┐   │
 │  │  FAST PATH 3: Optical Follow-Up ("show optical")           │   │
 │  │  _is_optical_request() checks trigger phrases               │   │
 │  │  → Uses cached _last_flood_result                          │   │
 │  │  → Calls flood_service.get_optical_tiles()                 │   │
 │  └────────────────────────────────────────────────────────────┘   │
 │                          │ NO                                      │
 │                          ▼                                         │
 │  ┌────────────────────────────────────────────────────────────┐   │
 │  │  STANDARD PATH: Full LLM parsing pipeline                  │   │
 │  │  parsed = await self.query_agent.parse_query(user_query)   │   │
 │  └────────────────────────────────────────────────────────────┘   │
 └────────────────────────────────────────────────────────────────────┘

 Why fast paths?
 ┌──────────────────────────────────────────────────────────────────┐
 │ 1. Performance: Skip the 500ms LLM call when intent is obvious  │
 │ 2. Stateful follow-ups: "show statistics" only makes sense      │
 │    AFTER a flood query — needs cached context, not fresh parse  │
 │ 3. MPC queries have clear trigger words that never overlap      │
 └──────────────────────────────────────────────────────────────────┘
```

### The Intent → Handler → Service → External API Map

```
 ┌──────────────────────┐    ┌──────────────────────┐    ┌───────────────────────┐    ┌──────────────────────┐
 │     INTENT           │    │   HANDLER METHOD     │    │   SERVICE / TOOL      │    │   EXTERNAL API       │
 │   (from QueryAgent)  │───▶│  (in orchestrator)   │───▶│   (file called)       │───▶│   (HTTP/SDK call)    │
 ├──────────────────────┤    ├──────────────────────┤    ├───────────────────────┤    ├──────────────────────┤
 │                      │    │                      │    │                       │    │                      │
 │ query_fires          │───▶│ _query_fires()       │───▶│ Direct SQL in         │───▶│ SQLite (aiosqlite)   │
 │                      │    │                      │    │ orchestrator.py       │    │ Local DB             │
 │                      │    │                      │    │                       │    │                      │
 │ query_monthly        │───▶│ _query_monthly_      │───▶│ Direct SQL            │───▶│ SQLite               │
 │                      │    │  breakdown()         │    │ GROUP BY month        │    │ Local DB             │
 │                      │    │                      │    │                       │    │                      │
 │ query_high_frp       │───▶│ _query_high_frp_     │───▶│ Direct SQL            │───▶│ SQLite               │
 │                      │    │  fires()             │    │ WHERE frp > threshold │    │ Local DB             │
 │                      │    │                      │    │                       │    │                      │
 │ query_fires_realtime │───▶│ _query_fires_        │───▶│ services/             │───▶│ NASA FIRMS API       │
 │                      │    │  realtime()          │    │ nasa_firms.py         │    │ REST (CSV response)  │
 │                      │    │                      │    │                       │    │                      │
 │ query_floods         │───▶│ _query_floods()      │───▶│ services/             │───▶│ Google Earth Engine  │
 │                      │    │                      │    │ flood_service.py      │    │ Python SDK (ee)      │
 │                      │    │                      │    │                       │    │ Sentinel-1 SAR       │
 │                      │    │                      │    │                       │    │                      │
 │ query_urban_         │───▶│ _query_urban_        │───▶│ llm/tools/urban_      │───▶│ Google Earth Engine  │
 │ expansion            │    │  expansion()         │    │ expansion_tool.py     │    │ GHSL dataset         │
 │                      │    │                      │    │                       │    │                      │
 │ query_surface_water  │───▶│ _query_surface_      │───▶│ llm/tools/surface_    │───▶│ Google Earth Engine  │
 │                      │    │  water()             │    │ water_tool.py         │    │ JRC Global Water     │
 │                      │    │                      │    │                       │    │                      │
 │ query_air_quality    │───▶│ _query_air_          │───▶│ llm/tools/air_        │───▶│ Google Earth Engine  │
 │                      │    │  quality()           │    │ quality_tool.py       │    │ Sentinel-5P TROPOMI  │
 │                      │    │                      │    │                       │    │                      │
 │ query_mpc_images     │───▶│ _query_mpc_images()  │───▶│ llm/tools/mpc_        │───▶│ MS Planetary Computer│
 │                      │    │                      │    │ search_tool.py        │    │ STAC API             │
 │                      │    │                      │    │                       │    │                      │
 │ query_forest         │───▶│ _query_forest_loss() │───▶│ models/forest.py      │───▶│ Global Forest Watch  │
 │                      │    │                      │    │ ForestMonitor         │    │ REST API             │
 │                      │    │                      │    │                       │    │                      │
 │ query_drivers        │───▶│ _query_forest_       │───▶│ models/forest.py      │───▶│ GFW Drivers API      │
 │                      │    │  drivers()           │    │ ForestMonitor         │    │ REST API             │
 │                      │    │                      │    │                       │    │                      │
 │ analyze_correlation  │───▶│ _analyze_historical_ │───▶│ models/climate.py     │───▶│ Open-Meteo API       │
 │                      │    │  correlation()       │    │ + scipy.pearsonr      │    │ + SQLite fires       │
 │                      │    │                      │    │                       │    │                      │
 │ analyze_fire_forest_ │───▶│ _analyze_fire_forest │───▶│ H3 spatial join       │───▶│ SQLite + GFW         │
 │ correlation          │    │  _spatial_h3()       │    │ in orchestrator       │    │ (dual source)        │
 │                      │    │                      │    │                       │    │                      │
 │ generate_report      │───▶│ _generate_report()   │───▶│ Multi-source          │───▶│ All above combined   │
 │                      │    │                      │    │ aggregation           │    │                      │
 │                      │    │                      │    │                       │    │                      │
 │ suggest_alternatives │───▶│ (handled in report   │───▶│ No external call      │───▶│ LLM generates        │
 │                      │    │  agent directly)     │    │                       │    │ suggestions          │
 └──────────────────────┘    └──────────────────────┘    └───────────────────────┘    └──────────────────────┘
```

### Stateful Follow-Up Pattern (v5.2 Design)

```
 ┌──────────────────────────────────────────────────────────────────────────┐
 │  CONVERSATION FLOW:                                                      │
 │                                                                          │
 │  Turn 1: "Show floods in Dadu district 2022"                            │
 │    ├── Full pipeline: QueryAgent → _query_floods() → GEE                │
 │    ├── Returns: tiles + flood_area_km2                                   │
 │    └── CACHES result in self._last_flood_result                         │
 │                                                                          │
 │  Turn 2: "show statistics"                                               │
 │    ├── Fast path: _is_statistics_request() → TRUE                       │
 │    ├── Skips QueryAgent entirely (no LLM call!)                         │
 │    ├── Uses cached _last_flood_result                                   │
 │    └── Calls flood_service.get_detailed_statistics()                    │
 │         └── Returns: exposed_population, flooded_cropland, urban_impact │
 │                                                                          │
 │  Turn 3: "show optical"                                                  │
 │    ├── Fast path: _is_optical_request() → TRUE                          │
 │    ├── Checks cached result for optical_availability                    │
 │    └── Calls flood_service.get_optical_tiles()                          │
 │         └── Returns: Sentinel-2 RGB, NDWI, False Color tiles            │
 │                                                                          │
 │  WHY THIS DESIGN:                                                        │
 │  ┌────────────────────────────────────────────────────────────────────┐  │
 │  │ Initial flood detection takes ~5-8 seconds (SAR processing)       │  │
 │  │ Adding population/cropland analysis would add ~10-15 seconds      │  │
 │  │ Users often only want the map, not all statistics                  │  │
 │  │                                                                    │  │
 │  │ Solution: Lazy loading                                             │  │
 │  │ • Fast first response (just tiles + area)                         │  │
 │  │ • On-demand statistics (only if user asks)                        │  │
 │  │ • On-demand optical (only if user asks)                           │  │
 │  └────────────────────────────────────────────────────────────────────┘  │
 └──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Stage 3 Deep Dive: Prompt Architecture

### Four System Prompts

```
 ┌────────────────────────────────────────────────────────────────────┐
 │                    PROMPT ARCHITECTURE                              │
 │                    (system_prompts.py)                              │
 │                                                                    │
 │  ┌──────────────────────────────────────────────────────────────┐ │
 │  │  1. QUERY_AGENT_PROMPT (544 lines)                           │ │
 │  │     Purpose: Parse natural language → structured JSON         │ │
 │  │     Technique: Few-shot learning with 30+ examples           │ │
 │  │     Variable: {{query}}                                       │ │
 │  │                                                               │ │
 │  │  Structure:                                                   │ │
 │  │  ┌─ Dataset capabilities table (6 datasets)                  │ │
 │  │  ├─ Intent table (11 intents with required params)           │ │
 │  │  ├─ Parameter extraction rules (standard + per-domain)       │ │
 │  │  ├─ Examples grouped by domain:                              │ │
 │  │  │   ├─ Fire examples (3)                                    │ │
 │  │  │   ├─ Forest examples (2)                                  │ │
 │  │  │   ├─ Flood examples (4)                                   │ │
 │  │  │   ├─ Urban examples (6)                                   │ │
 │  │  │   ├─ Water examples (4)                                   │ │
 │  │  │   └─ Air quality examples (4)                             │ │
 │  │  ├─ Unclear query handling (5 examples with suggestions)     │ │
 │  │  ├─ Available cities list                                    │ │
 │  │  ├─ Known flood events with pre-configured dates             │ │
 │  │  └─ Important rules (8 rules)                                │ │
 │  └──────────────────────────────────────────────────────────────┘ │
 │                                                                    │
 │  ┌──────────────────────────────────────────────────────────────┐ │
 │  │  2. ANALYSIS_AGENT_PROMPT (~60 lines)                        │ │
 │  │     Purpose: Determine analysis approach from parameters      │ │
 │  │     Variable: {{parameters}}                                  │ │
 │  │     Output: analysis plan JSON (type, source, method, steps) │ │
 │  └──────────────────────────────────────────────────────────────┘ │
 │                                                                    │
 │  ┌──────────────────────────────────────────────────────────────┐ │
 │  │  3. REPORT_AGENT_PROMPT (~185 lines)                         │ │
 │  │     Purpose: Generate markdown report from raw data           │ │
 │  │     Variable: {{results}}                                     │ │
 │  │                                                               │ │
 │  │  Anti-Hallucination Engineering:                              │ │
 │  │  ┌────────────────────────────────────────────────────────┐  │ │
 │  │  │ FORBIDDEN PHRASES:                                     │  │ │
 │  │  │  ✗ "The correlation coefficient was 0.XX"              │  │ │
 │  │  │  ✗ "The p-value indicates significance"                │  │ │
 │  │  │  ✗ "This is XX% higher than last year"                 │  │ │
 │  │  │  ✗ "Statistical analysis shows..."                     │  │ │
 │  │  │                                                        │  │ │
 │  │  │ REQUIRED VERIFICATION:                                 │  │ │
 │  │  │  Before writing ANY number → verify in {{results}}     │  │ │
 │  │  │  Before claiming correlation → check "correlations"    │  │ │
 │  │  │  If uncertain → "Data insufficient to determine [X]"   │  │ │
 │  │  └────────────────────────────────────────────────────────┘  │ │
 │  │                                                               │ │
 │  │  Domain-specific report templates:                            │ │
 │  │  • General: Key Findings → Significance → Context → Actions  │ │
 │  │  • Floods: Extent → Impact → Methodology → Recommendations   │ │
 │  │  • Urban: Growth → Assessment → Population → Visualization   │ │
 │  │  • Suggestions: Acknowledge → Alternatives → Encourage       │ │
 │  └──────────────────────────────────────────────────────────────┘ │
 │                                                                    │
 │  ┌──────────────────────────────────────────────────────────────┐ │
 │  │  4. RAG_CONTEXT_PROMPT (~20 lines)                           │ │
 │  │     Purpose: Answer from ChromaDB retrieved context           │ │
 │  │     Variables: {{context}}, {{question}}                      │ │
 │  │     Rule: Answer based ONLY on provided context               │ │
 │  └──────────────────────────────────────────────────────────────┘ │
 └────────────────────────────────────────────────────────────────────┘
```

---

## 5. Domain-Specific Parameter Extractors

### Flood Parameter Extraction (Most Complex)

```
 ┌────────────────────────────────────────────────────────────────────┐
 │           _extract_flood_parameters(user_query)                    │
 │                                                                    │
 │  LAYER 1: KNOWN EVENT MATCHING                                     │
 │  ┌──────────────────────────────────────────────────────────────┐ │
 │  │  Dictionary of (keyword_tuple) → pre-configured dates        │ │
 │  │                                                               │ │
 │  │  ("pakistan", "2022") → {                                     │ │
 │  │    before: Jun 1 - Jul 15, 2022                               │ │
 │  │    after:  Aug 25 - Sep 5, 2022                               │ │
 │  │  }                                                            │ │
 │  │                                                               │ │
 │  │  ("sindh", "2022") → same dates + location_name="Sindh"      │ │
 │  │  ("kerala", "2018") → Kerala-specific dates                   │ │
 │  │  ("ditwah") → Sri Lanka cyclone dates (just 1 keyword!)      │ │
 │  │                                                               │ │
 │  │  Match logic: ALL keywords in tuple must be in query          │ │
 │  └──────────────────────────────────────────────────────────────┘ │
 │                          │ no match?                                │
 │                          ▼                                         │
 │  LAYER 2: LOCATION TYPE INFERENCE                                  │
 │  ┌──────────────────────────────────────────────────────────────┐ │
 │  │  "river/nadi/tributary" → type=river, buffer=25km            │ │
 │  │  "district"             → type=district                      │ │
 │  │  "province/state"       → type=province                      │ │
 │  │  "country/nation"       → type=country                       │ │
 │  └──────────────────────────────────────────────────────────────┘ │
 │                          │                                         │
 │                          ▼                                         │
 │  LAYER 3: COUNTRY DETECTION                                        │
 │  ┌──────────────────────────────────────────────────────────────┐ │
 │  │  "pakistan" → "Pakistan"                                      │ │
 │  │  "india"   → "India"                                         │ │
 │  │  "vietnam" → "Viet Nam" (official UN spelling)               │ │
 │  │  ... 13 countries mapped                                     │ │
 │  └──────────────────────────────────────────────────────────────┘ │
 │                          │                                         │
 │                          ▼                                         │
 │  LAYER 4: LOCATION NAME EXTRACTION                                 │
 │  ┌──────────────────────────────────────────────────────────────┐ │
 │  │  Regex patterns tried in order:                               │ │
 │  │  1. "floods in <location>"                                    │ │
 │  │  2. "flooding in <location>"                                  │ │
 │  │  3. "flood detection/map/analysis in/for/of <location>"      │ │
 │  │  4. "<location> floods"                                       │ │
 │  └──────────────────────────────────────────────────────────────┘ │
 │                          │                                         │
 │                          ▼                                         │
 │  LAYER 5: DATE INFERENCE (if not from known event)                 │
 │  ┌──────────────────────────────────────────────────────────────┐ │
 │  │  If month + year mentioned:                                   │ │
 │  │    before = 2 months prior                                    │ │
 │  │    after  = specified month                                   │ │
 │  │                                                               │ │
 │  │  If only year mentioned:                                      │ │
 │  │    Assumes monsoon season (South Asia default):               │ │
 │  │    before = May 1 - Jun 30                                    │ │
 │  │    after  = Jul 15 - Sep 15                                   │ │
 │  └──────────────────────────────────────────────────────────────┘ │
 └────────────────────────────────────────────────────────────────────┘
```

---

## 6. Complete Request Trace (Walk-Through)

```
 USER: "Show floods in Sindh Pakistan 2022"
 ════════════════════════════════════════════════════════════════════════

 ① ENTRY: orchestrator.process_query("Show floods in Sindh Pakistan 2022")
    │
    ├── Fast path checks: MPC? NO. Statistics? NO. Optical? NO.
    │
    ▼
 ② QUERY AGENT: query_agent.parse_query("Show floods in Sindh Pakistan 2022")
    │
    ├── LLM Call to Groq:
    │   System: "You are a geospatial query parser. Return ONLY valid JSON."
    │   User: QUERY_AGENT_PROMPT (544 lines) with query substituted
    │   Model: llama-3.3-70b-versatile, temp=0.1
    │
    │   LLM returns: { "intent": "query_floods", "parameters": { "location_name": "Sindh" } }
    │
    ├── Keyword Override:
    │   "flood" found in query → confirms query_floods (no override needed this time)
    │
    │   _extract_flood_parameters():
    │     Known event match: ("sindh", "2022") both in query → YES!
    │     Injects: before_start="2022-06-01", before_end="2022-07-15"
    │              after_start="2022-08-25",  after_end="2022-09-05"
    │              location_name="Sindh", location_type="province", country="Pakistan"
    │
    │   Final parsed:
    │   {
    │     "intent": "query_floods",
    │     "parameters": {
    │       "location_name": "Sindh",
    │       "location_type": "province",
    │       "country": "Pakistan",
    │       "before_start": "2022-06-01",
    │       "before_end": "2022-07-15",
    │       "after_start": "2022-08-25",
    │       "after_end": "2022-09-05"
    │     }
    │   }
    │
    ▼
 ③ INTENT ROUTER: intent == "query_floods"
    │
    ├── Calls: _query_floods(parameters)
    │
    ├── Validation:
    │   ✓ location_name = "Sindh"
    │   ✓ all 4 date fields present
    │
    ├── Location type already set = "province"
    │
    ▼
 ④ SERVICE CALL: flood_service.detect_flood(
       location_name="Sindh", location_type="province",
       country="Pakistan",
       before_start="2022-06-01", before_end="2022-07-15",
       after_start="2022-08-25", after_end="2022-09-05"
    )
    │
    ├── GEE SDK:
    │   1. Geocode "Sindh, Pakistan" → get province boundary
    │   2. Load Sentinel-1 GRD collection (VV polarization)
    │   3. Composite BEFORE images (Jun 1 - Jul 15)
    │   4. Composite AFTER images (Aug 25 - Sep 5)
    │   5. Change detection: after_VV - before_VV
    │   6. Threshold: difference > 2.0 dB = FLOOD
    │   7. Generate XYZ tile URLs for map display
    │   8. Calculate flood_area_km2
    │
    ├── Returns: { success: true, tiles: {...}, statistics: { flood_area_km2: 47320 }, ... }
    │
    ▼
 ⑤ RESPONSE BUILD: orchestrator builds response_data dict
    │
    ├── level = "detailed" (province is manageable area)
    ├── tiles = { flood_extent, change_detection, sar_before, sar_after, permanent_water }
    ├── statistics = { flood_area_km2: 47320, flood_area_ha: 4732000 }
    ├── follow_up_hints = ["Say 'show statistics' for population impact"]
    │
    ├── Caches: self._last_flood_result = result  (for follow-up queries)
    │
    ▼
 ⑥ REPORT AGENT: report_agent.generate_report(result)
    │
    ├── LLM Call to Groq:
    │   System: "You are a geospatial query parser..." (reused)
    │   User: REPORT_AGENT_PROMPT with {{results}} = actual data
    │
    │   Anti-hallucination active:
    │   ✓ Only reports flood_area_km2 that exists in data
    │   ✓ Does NOT invent population numbers (not calculated yet)
    │   ✓ Mentions "Say 'show statistics' for impact assessment"
    │
    │   Returns: Markdown report with extent summary, methodology, recommendations
    │
    ▼
 ⑦ FINAL RESPONSE: Sent back to FastAPI → Frontend
    {
      "status": "success",
      "intent": "query_floods",
      "level": "detailed",
      "data": { tiles, statistics, center, zoom, ... },
      "report": "## Flood Analysis: Sindh, Pakistan\n\n...",
      "ai_guidance": { follow_up_hints: [...] }
    }
```

---

## 7. File Dependency Graph

```
 backend/app/
 │
 ├── api/v1/query.py              ← HTTP endpoint: POST /api/v1/query
 │     │
 │     └── calls ─────────────────────────────────────────────────┐
 │                                                                 │
 ├── llm/orchestrator.py          ← LLMOrchestrator.process_query()
 │     │
 │     ├── llm/agents/query_agent.py    ← Intent detection (Groq LLM + keywords)
 │     │     └── llm/prompts/system_prompts.py  ← QUERY_AGENT_PROMPT
 │     │
 │     ├── llm/agents/analysis_agent.py ← Analysis planning
 │     │     └── llm/prompts/system_prompts.py  ← ANALYSIS_AGENT_PROMPT
 │     │
 │     ├── llm/agents/report_agent.py   ← Report generation
 │     │     └── llm/prompts/system_prompts.py  ← REPORT_AGENT_PROMPT
 │     │
 │     ├── services/flood_service.py    ← GEE Sentinel-1 SAR processing
 │     ├── services/nasa_firms.py       ← NASA FIRMS real-time fires
 │     │
 │     ├── llm/tools/urban_expansion_tool.py  ← GEE GHSL analysis
 │     ├── llm/tools/surface_water_tool.py    ← GEE JRC Water
 │     ├── llm/tools/air_quality_tool.py      ← GEE Sentinel-5P
 │     ├── llm/tools/mpc_search_tool.py       ← MS Planetary Computer STAC
 │     │
 │     ├── models/forest.py             ← Global Forest Watch API
 │     ├── models/climate.py            ← Open-Meteo API + correlation
 │     │
 │     ├── core/aggregation.py          ← H3 hexagonal spatial aggregation
 │     ├── core/spatial.py              ← H3 indexing (res 5=25km, res 9=174m)
 │     ├── core/correlation.py          ← Pearson correlation engine
 │     │
 │     └── database.py                  ← async SQLite (aiosqlite)
 │           └── fire_detections table
 │           └── fire_aggregations table
 │           └── analysis_results table
```

---

## 8. Interview Talking Points

### "Walk me through a request lifecycle"
Use Section 6 above — trace from user input through all 7 steps.

### "Why hybrid intent detection instead of pure LLM?"
> "LLMs are great at understanding natural language but unreliable for strict classification. In testing, the LLM would sometimes classify flood queries as fire queries because both are geospatial. The keyword override acts as a deterministic safety net — it's a priority-ordered chain where the first keyword match wins. This gives us the best of both worlds: LLM flexibility for ambiguous queries, rule-based reliability for clear ones."

### "Why not use a classification model instead?"
> "A fine-tuned classifier would require training data for each intent and retraining when adding new domains. The keyword approach lets me add a new domain (like air quality) by just adding a new priority level — no model retraining needed. The LLM handles the long tail of ambiguous queries that keywords miss."

### "How do you prevent hallucination in reports?"
> "Three techniques: (1) Forbidden phrases — the prompt explicitly lists sentences the LLM must never generate unless data supports them. (2) Required verification — before writing ANY number, verify it exists in the results dict. (3) Graceful degradation — if a statistic is missing, say 'Data insufficient' rather than inventing one."

### "Why lazy-loading for flood statistics?"
> "Initial SAR flood detection takes 5-8 seconds. Adding population/cropland overlays adds another 10-15 seconds. Most users just want the flood extent map first. So we return the fast result immediately and cache it — if the user asks 'show statistics', we compute the expensive overlays on-demand from the cached result. This cuts perceived latency by 60%."

### "How do you handle unknown/unsupported queries?"
> "The prompt includes a `suggest_alternatives` intent with 5 examples. If the LLM can't map a query to a known domain, it returns structured suggestions with example queries the user can copy-paste. The Report Agent then formats these into a friendly response. The system never returns a bare error."
