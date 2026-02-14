# GeoWise AI — Orchestration & Query Routing

The orchestrator is the central coordination layer of GeoWise. It receives raw natural language from the API, determines what the user is asking for, dispatches to the appropriate data service, and assembles a structured response. This document explains how that process works and why it is designed the way it is.

---

## The Hybrid Intent Detection Problem

The most consequential design decision in the system is how to classify user queries into one of fourteen analysis intents. Two obvious approaches exist: use a large language model, or use a rule-based keyword matcher. Both have meaningful failure modes.

A pure LLM approach handles ambiguous, creatively phrased queries well, but is unreliable for strict classification. During development, flood queries were occasionally misclassified as fire queries because both involve urgent, location-specific events described in similar language. The LLM's probabilistic nature means the same query can produce different intents across runs, which is unacceptable for a system where the wrong intent routes to an entirely different data source.

A pure keyword system is deterministic and fast but brittle. A query like *"How has water coverage changed in Balochistan after last summer's rains?"* contains no obvious flood keyword, but clearly warrants a surface water analysis. Keyword matching would either miss it entirely or route it incorrectly.

The solution is a two-pass hybrid. The LLM runs first and provides a classification. A deterministic keyword override then inspects the original query text. If clear domain keywords are present, the keyword system wins regardless of what the LLM returned. If no keywords match, the LLM's decision stands. This means the LLM handles the long tail of nuanced queries while the keyword layer provides a reliable safety net for common, unambiguous patterns.

---

## Stage 1: Query Agent

The QueryAgent sends the user's query to Groq using the `llama-3.3-70b-versatile` model at temperature 0.1. The low temperature is deliberate — this task requires consistent, structured output, not creative variation. The prompt (`QUERY_AGENT_PROMPT`, 544 lines) provides the model with a complete intent taxonomy, per-domain parameter extraction rules, and over thirty few-shot examples covering all six environmental domains. The model returns JSON containing an intent name and a parameters dictionary.

After the LLM response is received, the `_enhance_intent_detection()` method runs the keyword override. It evaluates the query against an ordered priority chain and replaces the LLM's intent if a keyword match is found at a higher priority level.

### The Priority Chain

The ordering of this chain is itself a design choice. Consider the query *"What caused the flooding in Pakistan?"* — it contains both flood keywords ("flooding") and driver keywords ("caused"). Without ordering, the result is undefined. The chain resolves this by checking drivers before floods: a causal question about a flood event should retrieve deforestation and land-use driver data, not SAR inundation maps.

| Priority | Pattern | Sample Keywords | Resulting Intent | Match Type |
|----------|---------|----------------|-----------------|------------|
| 1 | Monthly breakdown | peak, highest, per month | `query_monthly` | Simple |
| 2 | Fire intensity | intense fires, severe, extreme | `query_high_frp` | Simple |
| 3 | Drivers | cause, driver, why, agriculture, logging | `query_drivers` | Simple |
| 4 | Floods | flood, inundation, submerged, deluge | `query_floods` | Simple |
| 5 | Satellite imagery | sentinel-2, landsat, planetary computer | `query_mpc_images` | Simple |
| 6 | Urban expansion | urban, sprawl, city growth, built-up | `query_urban_expansion` | Simple |
| 7 | Surface water | lake, reservoir, dam, water level | `query_surface_water` | Simple |
| 8 | Air quality | air quality, NO2, SO2, smog | `query_air_quality` | Simple |
| 9 | Real-time fire | realtime **and** fire | `query_fires_realtime` | Compound |
| 10 | Fire-forest correlation | fire **and** forest | `analyze_fire_forest_correlation` | Compound |
| 11 | Forest only | forest **without** fire keywords | `query_forest` | Exclusive |

Three distinct matching strategies appear in the chain. Simple matching triggers on any keyword from a list. Compound matching requires keywords from two separate lists to both be present — this prevents a query about forest fires from being routed to the forest-only handler. Exclusive matching requires one keyword set to be present and another to be absent — this is how the system distinguishes a pure forest query from a fire-forest correlation query.

### Parameter Extraction

Intent classification is only half of what the QueryAgent does. Each domain also needs structured parameters: location names, date ranges, thresholds, and identifiers. After intent detection, domain-specific extractors enrich the result.

The flood extractor is the most complex. It first checks the query against a dictionary of known historical flood events. If the query mentions ("sindh", "2022") or ("kerala", "2018"), it injects pre-validated SAR date ranges rather than relying on the model to infer appropriate before/after periods for change detection. This matters because SAR flood detection is sensitive to date selection — using the correct monsoon window for Pakistan versus the correct southwest monsoon timing for Kerala requires domain knowledge that the LLM may not apply consistently. Pre-configured dates, validated against UNOSAT flood records, are more reliable than inferred ones.

If no known event matches, the extractor attempts to infer dates from the query text: a month-year combination produces a two-month pre-event window, and a year alone defaults to the South Asian monsoon season (May–June before, July–September after). It also infers location type from place name patterns — provincial names like "Sindh" or "Punjab" are typed as provinces, country names become country-level queries, and river names trigger a 25 km buffer analysis.

Other extractors are simpler. The urban extractor pulls a city name via regex and defaults to the full GHSL epoch range (1975–2020). The water extractor maintains a lookup of fifteen pre-configured water bodies including the Aral Sea, Lake Chad, and the Dead Sea, falling back to Nominatim geocoding for unlisted locations. The air quality extractor detects pollutant names and handles year-over-year comparison requests. A fallback regex (`r'\b(20\d{2})\b'`) catches any four-digit year that the LLM missed in its parameter extraction.

---

## Stage 2: Orchestrator Routing

Before the QueryAgent runs at all, the orchestrator checks for three fast-path patterns where intent detection would be redundant.

The **MPC fast path** triggers on keywords like `sentinel-2`, `landsat`, and `planetary computer`. These words are domain-exclusive — they appear in no other category — so routing to `_query_mpc_images()` without LLM involvement saves the full parsing round-trip.

The **statistics fast path** handles queries like "show statistics" or "population impact" following a flood analysis. These only make sense in the context of a previous flood result, and their meaning is entirely determined by that cached context, not by the query text itself. Routing them through the QueryAgent would produce a confident but contextually wrong intent.

The **optical fast path** handles requests for Sentinel-2 optical imagery following a SAR flood detection. The same caching logic applies.

The reasoning behind these fast paths is not purely about performance, though they do save the ~500 ms LLM call. The more important reason is correctness: follow-up queries in a stateful conversation cannot be parsed in isolation without losing their meaning.

### Lazy Loading for Flood Queries

Flood analysis has a layered cost structure. The initial SAR change detection — geocoding the area, loading Sentinel-1 imagery for two composite periods, applying the threshold, and generating tile URLs — takes five to eight seconds. Computing population exposure from WorldPop and cropland impact from ESA land cover adds another ten to fifteen seconds on top of that. Sentinel-2 optical imagery retrieval adds more still.

Most users want the flood extent map first. The additional statistics are valuable but secondary. The orchestrator therefore returns the SAR result immediately, caches it in `self._last_flood_result`, and includes a hint in the response suggesting that the user say "show statistics" for impact data. Subsequent requests for statistics or optical imagery use the cached flood boundary to constrain the computation without repeating the SAR processing.

This pattern — fast first response, on-demand enrichment — reduces perceived latency by roughly sixty percent on the most common query path.

---

## Stage 3: Report Generation

After a handler returns data, the orchestrator passes the result to the ReportAgent before building the final response:

```python
if result.get("status") != "error":
    report = await self.report_agent.generate_report(result)
    result["report"] = report
```

The ReportAgent calls Groq a second time with the `REPORT_AGENT_PROMPT` (~185 lines), injecting the raw result dictionary as context. The most important property of this prompt is what it prohibits.

LLMs have a strong tendency to generate plausible-sounding statistics when given geospatial data — correlation coefficients, percentage changes, significance levels — even when those values were never computed. The report prompt addresses this with explicit forbidden phrases: the model is instructed never to write "The correlation coefficient was 0.XX" unless a `correlations` key exists in the result, never to claim "XX% higher than last year" unless comparison data was provided, and never to use phrases like "statistical analysis shows" unless statistics were actually returned by the handler. When data is absent, the required phrasing is: *"Data insufficient to determine [X]."*

Domain-specific report templates structure the output differently per analysis type — flood reports foreground extent and methodology, urban reports foreground growth metrics and the SDG 11.3.1 indicator, fire reports foreground count and seasonal context — but the anti-hallucination constraint applies uniformly.

---

## A Complete Request Trace

Walking through a concrete example illustrates how the stages interact.

**Query:** *"Show floods in Sindh Pakistan 2022"*

The orchestrator first checks the fast paths. The query contains no MPC keywords, no flood follow-up phrases, and no optical request phrases. It falls through to the standard path.

The QueryAgent calls Groq. The model returns `{ "intent": "query_floods", "parameters": { "location_name": "Sindh" } }`. The keyword override confirms this — "flood" is present at priority 4 — and does not override. The flood parameter extractor then runs: it finds both "sindh" and "2022" in the query, matches the known event dictionary, and injects the validated SAR date windows (`before: 2022-06-01 to 2022-07-15`, `after: 2022-08-25 to 2022-09-05`). It also sets `location_type: "province"` and `country: "Pakistan"`.

The orchestrator routes to `_query_floods()`. Validation passes. The flood service geocodes "Sindh, Pakistan" to retrieve the province boundary, loads Sentinel-1 GRD imagery for both date windows, computes median backscatter composites, calculates the difference image, applies the 2.0 dB threshold, generates XYZ tile URLs for the flood extent and change detection layers, and computes total inundated area. The result is cached.

The ReportAgent receives the result. It reports the `flood_area_km2` value that exists in the data. It does not generate population estimates — those are not in the result — and suggests that the user request statistics if they want impact assessment.

The final response carries the intent, tile URLs, statistics, rendered markdown report, and follow-up hints.

---

## Prompt Engineering

The system uses four prompt templates, all in `app/llm/prompts/system_prompts.py`.

`QUERY_AGENT_PROMPT` (544 lines) is the most complex. Its structure — intent table first, then per-domain extraction rules, then grouped few-shot examples, then edge case handling — reflects a deliberate ordering: the model reads the taxonomy before seeing examples, which produces more consistent classification than presenting examples first. The prompt also includes negative examples: it explicitly tells the model what to return when asked about earthquakes, weather forecasting, or other unsupported domains, rather than leaving that behavior unspecified.

`ANALYSIS_AGENT_PROMPT` (~60 lines) asks the model to generate an execution plan — which data source to use, which method to apply, and in what order — given a set of structured parameters. This is intentionally lightweight: most of the routing logic lives in the orchestrator's handler methods rather than in this plan.

`REPORT_AGENT_PROMPT` (~185 lines) is discussed above. Its core property is the explicit enumeration of prohibited behaviors. This is more reliable than asking the model to "be accurate" in general terms.

`RAG_CONTEXT_PROMPT` (~20 lines) is used by the separate RAG endpoint. It instructs the model to answer exclusively from retrieved context and to explicitly acknowledge when the context does not contain sufficient information to answer the question.

---

## File Structure

```
app/
├── api/v1/
│   └── query.py              — POST /api/v1/query/nl (entry point)
│
└── llm/
    ├── orchestrator.py        — LLMOrchestrator.process_query()
    ├── agents/
    │   ├── query_agent.py     — intent detection (LLM + keyword override)
    │   ├── analysis_agent.py  — execution planning
    │   └── report_agent.py    — report generation
    ├── prompts/
    │   └── system_prompts.py  — all four prompt templates
    ├── tools/
    │   ├── urban_expansion_tool.py   — GEE GHSL (1975–2020)
    │   ├── surface_water_tool.py     — GEE JRC Water
    │   ├── air_quality_tool.py       — GEE Sentinel-5P TROPOMI
    │   └── mpc_search_tool.py        — MS Planetary Computer STAC
    ├── services/
    │   ├── flood_service.py          — GEE Sentinel-1 SAR
    │   ├── nasa_firms.py             — NASA FIRMS live API
    │   └── geocoding_service.py      — Nominatim geocoding
    ├── models/
    │   ├── forest.py                 — Global Forest Watch API
    │   └── climate.py                — Open-Meteo + correlation
    ├── core/
    │   ├── spatial.py                — H3 indexing (res 5 and 9)
    │   ├── aggregation.py            — H3 spatial aggregation
    │   ├── correlation.py            — scipy Pearson / Spearman
    │   └── tile_generator.py         — GeoJSON + heatmap output
    ├── database.py                   — async SQLite (aiosqlite)
    └── rag/
        ├── embeddings.py             — sentence-transformers (MiniLM-L6)
        └── vector_store.py           — ChromaDB
```
