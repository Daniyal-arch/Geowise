# GeoWise AI — Backend Architecture

GeoWise translates natural language queries into satellite-derived environmental analysis. The backend is a FastAPI application organized around a central LLM orchestrator that coordinates intent detection, service dispatch, and report generation across six environmental domains: fire, deforestation, floods, urban expansion, surface water, and air quality.

This document covers the system's structure, the reasoning behind key design decisions, and the tradeoffs involved. It is intended as a technical reference for contributors and reviewers.

---

## Architecture at a Glance

The system has three logical layers. The **API layer** (`app/api/v1/`) receives HTTP requests and delegates to the orchestrator. The **orchestration layer** (`app/llm/`) handles intent detection, routes queries to the appropriate service, and generates reports. The **data layer** comprises an async SQLite database, a ChromaDB vector store, and a set of external API clients.

```
Frontend (Next.js / MapLibre)
        │  HTTP/JSON
        ▼
FastAPI Backend
├── REST API          (/api/v1/* — 30+ endpoints across 8 route groups)
└── LLM Orchestrator
    ├── QueryAgent    (intent detection — Groq Llama 3.3 70B)
    ├── AnalysisAgent (execution planning)
    ├── ReportAgent   (report generation with anti-hallucination rules)
    └── LLM Tools     (GEE-powered analysis: floods, urban, water, air quality)
        │
        ├── Google Earth Engine   (Sentinel-1, Sentinel-5P, GHSL, JRC Water)
        ├── NASA FIRMS            (real-time fire detections)
        ├── Global Forest Watch   (tree cover loss and deforestation drivers)
        ├── Open-Meteo            (historical climate data)
        └── MS Planetary Computer (ESA WorldCover satellite tiles)
```

SQLite (via `aiosqlite`) stores ingested fire detections and cached correlation results. ChromaDB stores embeddings for the RAG pipeline. Redis provides optional query caching that degrades gracefully when unavailable.

---

## The Three-Stage Pipeline

Every natural language query, regardless of domain, follows the same processing path.

**Stage 1 — Intent Detection.** The QueryAgent sends the raw query to Groq with a 544-line prompt containing an intent taxonomy, parameter extraction rules, and over thirty few-shot examples spanning all six domains. The LLM returns structured JSON. A deterministic keyword override then validates the result: if domain-specific keywords are present and contradict the LLM's classification, the keyword system wins. This hybrid approach is discussed in detail in the orchestration document.

**Stage 2 — Routing and Execution.** The orchestrator matches the detected intent to one of fourteen handler methods and dispatches to the appropriate external service. Some handlers query SQLite directly; others call Google Earth Engine, NASA FIRMS, or the Global Forest Watch API. The orchestrator also checks for three fast-path shortcuts before running the LLM at all — more on this below.

**Stage 3 — Report Generation.** Raw service results pass through the ReportAgent, which calls Groq a second time with a separate 185-line prompt. This prompt enforces strict anti-hallucination rules: the model is explicitly instructed never to write statistical claims unless the corresponding data exists in the results object. If a value is absent, the report says so rather than inventing a number.

---

## Intent Routing

The orchestrator maps each intent to a handler, service, and external API:

| Intent | Handler | External API |
|--------|---------|-------------|
| `query_fires` | `_query_fires()` | SQLite (local fire database) |
| `query_fires_realtime` | `_query_fires_realtime()` | NASA FIRMS REST API |
| `query_monthly` | `_query_monthly_breakdown()` | SQLite (GROUP BY month) |
| `query_high_frp` | `_query_high_frp_fires()` | SQLite (WHERE frp >= threshold) |
| `query_forest` | `_query_forest_loss()` | Global Forest Watch API |
| `query_drivers` | `_query_forest_drivers()` | GFW + GEE tile server |
| `query_floods` | `_query_floods()` | Google Earth Engine (Sentinel-1 SAR) |
| `query_urban_expansion` | `_query_urban_expansion()` | Google Earth Engine (GHSL) |
| `query_surface_water` | `_query_surface_water()` | Google Earth Engine (JRC Water) |
| `query_air_quality` | `_query_air_quality()` | Google Earth Engine (Sentinel-5P) |
| `query_mpc_images` | `_query_mpc_images()` | Microsoft Planetary Computer STAC |
| `analyze_correlation` | `_analyze_historical_correlation()` | Open-Meteo + SQLite + scipy |
| `analyze_fire_forest_correlation` | `_analyze_fire_forest_spatial_h3()` | SQLite + GFW (H3 spatial join) |
| `generate_report` | `_generate_report()` | Multi-source aggregation |

### Fast Paths

Before the QueryAgent runs, the orchestrator checks for three patterns where the intent is unambiguous enough that calling the LLM would be wasteful.

The first fast path handles Microsoft Planetary Computer queries. Keywords like `sentinel-2`, `landsat`, or `planetary computer` never appear in other domains, so the orchestrator routes directly to `_query_mpc_images()` without parsing.

The second and third fast paths handle flood follow-up queries. Initial SAR flood detection takes five to eight seconds. Adding population exposure and cropland impact calculations would push that to twenty seconds or more, and most users want the flood map first. The solution is lazy loading: the orchestrator caches the flood result in `self._last_flood_result`, and when the user says "show statistics" or "show optical," the follow-up handlers read from the cache rather than reprocessing. This cuts perceived latency by roughly sixty percent.

---

## External Integrations

**Google Earth Engine** is the most complex integration and handles four distinct analysis types. Flood detection uses Sentinel-1 GRD imagery with SAR change detection: the system composites backscatter for a "before" period and an "after" period, computes the difference, and applies a 2.0 dB threshold (validated against UNOSAT flood records) to identify inundated areas. Urban expansion uses the JRC GHSL dataset across ten epochs from 1975 to 2020 and computes the UN SDG 11.3.1 land consumption indicator. Air quality uses Sentinel-5P TROPOMI for six pollutants. Surface water uses the JRC Global Surface Water dataset with pre-configured lookups for fifteen named water bodies including the Aral Sea, Lake Chad, and Lake Mead.

**NASA FIRMS** provides near-real-time fire detections via a CSV endpoint. The system stores ingested detections in SQLite with H3 indexes pre-computed at four resolutions (5, 6, 9, and 12) to support multi-scale spatial aggregation without repeated computation.

**Global Forest Watch** provides yearly tree cover loss statistics and a driver breakdown (agriculture, logging, wildfire, etc.) via REST endpoints that accept SQL-style queries. Responses are cached in memory with a one-hour TTL to avoid redundant API calls within a session.

**Open-Meteo** provides historical climate data back to 1940 and requires no authentication. It is used for fire-climate correlation analysis via scipy's Pearson and Spearman implementations.

---

## Database Design

The primary table is `fire_detections`, which stores one row per detected fire with latitude, longitude, brightness temperature, fire radiative power (FRP), confidence level, and acquisition date. H3 cell indices at four resolutions are computed on insert and stored as indexed columns. This means spatial aggregation queries — the most common read pattern — never touch raw coordinates; they group and filter on pre-computed string keys. A composite index on `(country, acq_date)` covers the majority of filter conditions.

The `analysis_results` table provides a persistent cache for correlation computations. Pearson correlation across a full country-year dataset can take several seconds; storing the result with an access counter means repeat queries are answered from the database rather than recomputed. The cache key is an MD5 hash of the sorted parameter dictionary.

SQLite was chosen for development simplicity. The async driver (`aiosqlite`) prevents blocking the event loop, but SQLite's single-writer limitation means this configuration is appropriate for demonstration and research use rather than concurrent production workloads.

---

## Core Modules

The `core/` directory contains four utility modules that the orchestrator and services share.

`spatial.py` wraps the Uber H3 library with version compatibility for both v3 and v4. It provides coordinate-to-cell conversion, boundary polygon generation, bounding box filling, and fire point aggregation into hexagonal bins. The system uses resolution 9 (approximately 174 m per cell) for map display and resolution 5 (approximately 25 km per cell) for statistical correlation, the latter being the minimum area at which Pearson correlation across environmental variables is statistically meaningful.

`aggregation.py` handles SQL-level aggregation: GROUP BY H3 cell to produce hexagonal fire density maps, and GROUP BY time period for trend analysis.

`correlation.py` wraps scipy's statistical functions — Pearson, Spearman, and linear regression — with a domain-specific interface for fire-temperature and fire-forest spatial analysis.

`tile_generator.py` converts H3 aggregations into GeoJSON FeatureCollections and heatmap arrays for frontend consumption.

---

## RAG Pipeline

The system includes a retrieval-augmented generation pipeline for document-grounded Q&A. Queries are embedded using `all-MiniLM-L6-v2` (384-dimensional vectors) and matched against a ChromaDB collection via cosine similarity. Retrieved context is injected into a separate prompt template that instructs the model to answer exclusively from the provided passages and to acknowledge when the context is insufficient. This pipeline is separate from the main analysis flow and is accessed via the `/api/v1/query/rag` endpoint.

---

## Caching

Three caching mechanisms operate at different granularities. Redis caches full query results with configurable TTLs (default one hour) using MD5-hashed parameter keys. The Global Forest Watch client maintains an in-memory dict cache for the duration of a server process. The `analysis_results` database table provides permanent storage for expensive correlation results. The system is designed so that Redis failure produces a warning log but does not interrupt operation.

---

## Known Limitations

A few areas are incomplete or constrained by design choices made for development speed.

The fire-climate correlation handler currently correlates fire count against brightness temperature, which are both derived from the same MODIS/VIIRS sensor. The Open-Meteo client exists and is functional, but it has not been wired into the correlation handler, so this analysis does not yet measure fire activity against independent atmospheric temperature data.

All API endpoints are unauthenticated. Adding authentication middleware is straightforward with FastAPI's dependency injection system but has not been prioritized for the current research context.

The climate endpoints (`/climate/temperature`, `/climate/precipitation`) have route definitions but no implementation behind them.

GEE authentication via service account incurs a five to ten second cold start on the first request after the server initializes. Subsequent requests within the same process use the cached authenticated client.

Sentinel-5P TROPOMI data begins in 2018, which limits air quality analysis to the post-launch period.
