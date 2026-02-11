# GEOWISE

**AI-powered geospatial analysis platform that turns natural language into satellite imagery insights.**

GEOWISE combines a multi-agent LLM architecture with real-time satellite data APIs to let users query fires, floods, deforestation, urbanization, air quality, and surface water changes — all through plain English prompts. No GIS expertise required.

> **Status:** Active development. Core features are functional. See [Development Status](#development-status) for details.

---

## Live Demos

| Demo | Description |
|------|-------------|
| [Deforestation & Fire Detection](https://www.linkedin.com/posts/daniyal-khan-7b80b02a6_geoai-remotesensing-satelliteimagery-activity-7403729807953342464-N5ud) | Monitor forest loss and active fires using natural language |
| [Flood Mapping by Prompts](https://www.linkedin.com/posts/daniyal-khan-7b80b02a6_geoai-environment-earthobservation-activity-7407820737220272129-aAHr) | Detect and map flood-affected areas through SAR analysis |
| [Urbanization Analysis](https://www.linkedin.com/posts/daniyal-khan-7b80b02a6_geoai-urbanplanning-satelliteimagery-activity-7412870295830790144-GqYw) | Track urban expansion in any city worldwide (1975–2020) |
| [Water Change Detection](https://www.linkedin.com/posts/daniyal-khan-7b80b02a6_gis-remotesensing-earthobservation-activity-7415769403465764864-EUkZ) | Monitor lake shrinkage, drought, and reservoir levels |

---

## Features

### Fire Detection & Analysis
- Historical fire records (2020–2024) from NASA FIRMS database
- Real-time fire detection (last 1–10 days via VIIRS/MODIS)
- Monthly breakdown, seasonal patterns, and peak fire month identification
- High-intensity fire filtering by FRP (Fire Radiative Power) threshold
- H3 hexagonal aggregation for density heatmaps
- Supported countries: Pakistan, India, Brazil, Indonesia, Bangladesh

### Flood Detection (Sentinel-1 SAR)
- SAR-based change detection (before vs. after backscatter, 10m resolution)
- Optimized pipeline — results in 5–8 seconds
- On-demand population exposure and cropland impact statistics
- On-demand optical imagery (Sentinel-2 RGB, false color, NDWI)
- Presets for rural/riverine, urban, coastal, flash flood, and wetland scenarios
- Pre-configured events: Pakistan 2022 monsoon, Kerala 2018, Bangladesh 2020, Sri Lanka 2025

### Forest Loss & Deforestation Drivers
- Yearly tree cover loss data (2001–2024) from Global Forest Watch
- Trend analysis (increasing / decreasing / stable)
- 7-category deforestation driver classification (WRI/Google DeepMind, 1km resolution):
  agriculture, hard commodities, shifting cultivation, logging, wildfire, settlements, natural disturbance
- Country-level statistics and tile-based map visualization

### Urban Expansion
- Built-up area tracking across 10 epochs (1975–2020) using GHSL data (~38m resolution)
- Growth rate calculation, distance-ring sprawl analysis
- UN SDG 11.3.1 indicator (Land Consumption Rate / Population Growth Rate)
- Time-lapse animation generation
- 15+ pre-configured cities: Dubai, Lahore, Mumbai, Beijing, Tokyo, Cairo, Lagos, London, New York, and more

### Surface Water Changes
- Lake and reservoir monitoring via JRC Global Surface Water (30m resolution)
- HydroLAKES vector boundaries for 1.4M+ water bodies
- Pre-configured famous water bodies: Aral Sea, Lake Chad, Dead Sea, Lake Urmia, Lake Mead, and more

### Air Quality Monitoring
- Pollutant analysis via Sentinel-5P/TROPOMI: NO2, SO2, CO, O3, CH4, HCHO, Aerosol Index
- Pre-configured cities: Lahore, Delhi, Beijing, Mumbai, Dhaka, Cairo, Los Angeles, Mexico City

### Satellite Imagery Search
- ESA WorldCover 10m land use classification (2017–2023) via Microsoft Planetary Computer
- STAC API-based satellite image discovery

### Report Generation
- LLM-generated markdown reports for any analysis
- Anti-hallucination safeguards: only reports numbers present in actual data
- Forbidden phrases list, required verification before writing any statistic

---

## Example Queries

```
# Fires
"How many fires in Pakistan during 2020?"
"What were the peak fire months in India 2021?"
"Show me the most intense fires in Brazil 2020"
"Recent fires in Indonesia"

# Floods
"Detect floods in Sindh Pakistan August 2022"
"Show flood damage in Kerala 2018"

# Forest
"Show deforestation in Brazil"
"What are the drivers of forest loss in Indonesia?"

# Urban
"Show urban expansion in Dubai"
"How has Lahore grown since 1975?"

# Water
"Show water changes in Aral Sea"
"Lake Chad water loss since 1990"

# Air Quality
"Show air pollution in Lahore"
"Check NO2 levels in Beijing 2021"

# Reports
"Generate environmental report for India"
```

---

## Architecture

### Multi-Agent Orchestration

```
User Query (natural language)
        │
        ▼
   Query Agent ─── intent detection (keyword rules + LLM fallback)
        │
        ▼
   Orchestrator ─── routes to intent-specific handler
        │
        ├─→ query_fires          → NASA FIRMS (DB + live API)
        ├─→ query_monthly        → Fire DB monthly aggregation
        ├─→ query_high_frp       → Fire DB FRP filter
        ├─→ query_fires_realtime → NASA FIRMS live API
        ├─→ query_forest         → Global Forest Watch API
        ├─→ query_drivers        → GFW deforestation drivers (GEE tiles)
        ├─→ query_floods         → Google Earth Engine (Sentinel-1 SAR)
        ├─→ query_urban_expansion→ GEE (GHSL built-up layers)
        ├─→ query_surface_water  → GEE (JRC Global Surface Water)
        ├─→ query_air_quality    → GEE (Sentinel-5P/TROPOMI)
        ├─→ query_mpc_images     → Microsoft Planetary Computer (STAC)
        └─→ generate_report      → Groq LLM report generation
        │
        ▼
   Report Agent ─── converts raw data to human-readable markdown
        │
        ▼
   Response (data + map layers + report)
```

### Three-Agent Design

| Agent | Role |
|-------|------|
| **Query Agent** | Parses natural language into structured parameters. Hybrid detection: keyword rules with LLM fallback via Groq. |
| **Analysis Agent** | Plans the analysis approach (simple query, correlation, aggregation). |
| **Report Agent** | Generates markdown reports from raw data with anti-hallucination safeguards. |

### Data Sources

| Source | Data | Resolution | Coverage |
|--------|------|-----------|----------|
| NASA FIRMS | Active fire detection (VIIRS/MODIS) | ~375m | Global, real-time + historical |
| Google Earth Engine | Flood detection (Sentinel-1 SAR) | 10m | Global |
| GEE – Sentinel-2 | Optical flood imagery | 10m | Global |
| GEE – Sentinel-5P | Air quality (TROPOMI) | 5–20km | Global |
| GEE – GHSL | Urban expansion | ~38m | Global, 1975–2020 |
| GEE – JRC Global Surface Water | Water extent/changes | 30m | Global |
| GEE – WRI/DeepMind | Deforestation drivers | 1km | Global, 2001–2024 |
| Global Forest Watch | Tree cover loss | 30m tiles | Global, 2001–2024 |
| Open-Meteo | Historical climate data | 25km | Global, 1940–present (free) |
| Microsoft Planetary Computer | Land use (ESA WorldCover) | 10m | Global, 2017–2023 |
| HydroLAKES | Water body boundaries | Vector | 1.4M+ lakes |

### Tech Stack

**Backend**
- FastAPI (async), SQLAlchemy + aiosqlite, Alembic migrations
- Groq API (Llama 3.3 70B) for LLM inference
- ChromaDB for RAG, sentence-transformers for embeddings
- Google Earth Engine API, Microsoft Planetary Computer
- H3 hexagonal indexing, Shapely, PyProj, Rasterio
- Pandas, NumPy, SciPy for data processing
- Redis (optional, for caching), Celery (optional, for background tasks)

**Frontend**
- Next.js 14, React 18, TypeScript
- MapLibre GL + React Map GL for map rendering
- Zustand for state management, TanStack React Query for data fetching
- Tailwind CSS, Recharts, Lucide icons

---

## Project Structure

```
geowise/
├── backend/
│   ├── app/
│   │   ├── api/v1/            # REST endpoints (fires, forest, floods, query, etc.)
│   │   ├── core/              # Spatial processing, aggregation, caching
│   │   ├── llm/
│   │   │   ├── agents/        # Query, Analysis, and Report agents
│   │   │   ├── graphs/        # LangGraph agent (MPC)
│   │   │   ├── prompts/       # System prompt templates
│   │   │   ├── rag/           # ChromaDB vector store + embeddings
│   │   │   ├── tools/         # LLM tools (urban, water, air quality, MPC)
│   │   │   └── orchestrator.py
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── services/          # External API integrations
│   │   └── utils/             # Logger, validators, exceptions
│   ├── data/                  # Cache, fire metadata
│   ├── migrations/            # Alembic DB migrations
│   ├── tests/                 # pytest test suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/        # Map, Chat, Sidebar, StatsPanel, layer controls
│   │   ├── hooks/             # useFireData, useFloodData, useForestData, etc.
│   │   ├── pages/             # Next.js pages (_app.tsx, index.tsx)
│   │   ├── services/          # API client, fire/flood/GEE/MPC services
│   │   ├── types/             # TypeScript interfaces
│   │   ├── utils/             # Map layer helpers (flood, urban, water, MPC, air quality)
│   │   └── styles/
│   ├── package.json
│   └── tsconfig.json
├── docs/                      # API docs, architecture, DB schema
├── infrastructure/            # Docker, Kubernetes, nginx configs
├── scripts/                   # Deployment and setup scripts
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js 18+
- Google Earth Engine service account (for floods, urban, water, air quality features)
- Redis (optional — app works without it, caching is disabled)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (see Environment Variables below)

# Initialize database
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at `http://localhost:8000/docs`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local:
#   NEXT_PUBLIC_API_URL=http://localhost:8000
#   NEXT_PUBLIC_API_V1=/api/v1

# Start dev server
npm run dev
```

Frontend available at `http://localhost:3000`

### Environment Variables

Create `backend/.env` with the following:

```env
# Required
GROQ_API_KEY=your_groq_api_key           # LLM inference (groq.com)
NASA_FIRMS_API_KEY=your_nasa_firms_key    # Fire data (firms.modaps.eosdis.nasa.gov)

# Optional (have defaults or are free)
GFW_API_KEY=your_gfw_key                 # Global Forest Watch
DATABASE_URL=sqlite+aiosqlite:///./geowise.db
GROQ_MODEL=llama-3.3-70b-versatile
REDIS_URL=redis://localhost:6379/0       # Optional, caching disabled without it

# Google Earth Engine (required for floods, urban, water, air quality)
# Place your service account key as gee-service-account-key.json in the backend/ directory

# Free APIs (no key needed)
OPEN_METEO_BASE_URL=https://archive-api.open-meteo.com/v1/archive
WORLD_BANK_BASE_URL=https://api.worldbank.org/v2
```

---

## API Endpoints

### Natural Language Query
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/query/nl` | Process natural language query (main entry point) |
| POST | `/api/v1/query/rag` | RAG-based question answering |
| GET | `/api/v1/query/examples` | Example queries |

### Fire Detection
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/fires` | Query fires (country, date range, FRP, confidence filters) |
| GET | `/api/v1/fires/live/{country_iso}` | Real-time fires from NASA FIRMS |
| POST | `/api/v1/fires/aggregate` | H3 hexagonal aggregation |
| GET | `/api/v1/fires/stats` | Fire statistics |

### Forest Data
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/forest/loss/{country_iso}` | Yearly tree cover loss |
| GET | `/api/v1/forest/stats/{country_iso}` | Country forest statistics |
| GET | `/api/v1/forest/trend/{country_iso}` | Deforestation trend analysis |
| GET | `/api/v1/forest/tiles` | Forest tile layer config |

### Flood Detection
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/floods/detect` | SAR-based flood detection |
| GET | `/api/v1/floods/detect/quick` | Quick flood detection (GET) |
| GET | `/api/v1/floods/statistics` | On-demand population/cropland impact |
| GET | `/api/v1/floods/optical` | On-demand Sentinel-2 optical imagery |
| GET | `/api/v1/floods/presets` | Available detection presets |

### Satellite Imagery
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/mpc/query` | Query land use from MPC (ESA WorldCover) |
| GET | `/api/v1/mpc/coverage` | Data availability info |

### Map Tiles
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/tiles/fire-density` | Fire density GeoJSON |
| GET | `/api/v1/tiles/heatmap` | Fire heatmap data |
| GET | `/api/v1/tiles/{country_iso}/drivers` | Deforestation driver tiles |

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Backend health check |
| GET | `/api/v1/health` | Detailed system status |

Full interactive docs at `/docs` (Swagger UI) or `/redoc` after starting the server.

---

## Development Status

### Working
- Fire detection (historical + real-time) with H3 aggregation
- Forest loss tracking and deforestation driver classification
- SAR-based flood detection with on-demand statistics and optical imagery
- Urban expansion analysis (1975–2020) with SDG 11.3.1 indicators
- Surface water change monitoring
- Air quality pollutant mapping (Sentinel-5P)
- Satellite imagery search via Microsoft Planetary Computer
- Natural language query interface with multi-agent orchestration
- Interactive map visualization with multiple data layers
- LLM report generation with anti-hallucination safeguards

### Not Working
- **Fire-climate correlation** — currently uses fire brightness as a proxy instead of actual temperature/precipitation data. The Open-Meteo integration is incomplete.

### Not Yet Implemented
- User authentication and authorization
- API rate limiting
- Comprehensive test coverage
- CI/CD pipelines (workflow files exist but are disabled)
- Production deployment hardening

---

## Roadmap

### Near-term
- [ ] Fix fire-climate correlation with real Open-Meteo temperature/precipitation data
- [ ] Docker Compose for single-command deployment
- [ ] Expand historical fire data to more countries
- [ ] API rate limiting and authentication

### Future
- [ ] Integration with **Earth Mirror** — a separate AI platform being built for urban datasets — to unify urban intelligence and environmental monitoring into a single platform

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Push and open a Pull Request

---

## Acknowledgments

- [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) — fire detection data
- [Global Forest Watch](https://www.globalforestwatch.org/) — deforestation monitoring
- [Google Earth Engine](https://earthengine.google.com/) — satellite imagery processing
- [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/) — open geospatial data
- [Open-Meteo](https://open-meteo.com/) — free climate data API
- [Groq](https://groq.com/) — fast LLM inference
- [Uber H3](https://h3geo.org/) — hexagonal spatial indexing

## Contact

Daniyal Khan — [LinkedIn](https://www.linkedin.com/in/daniyal-khan-7b80b02a6/)

Project Link: [github.com/Daniyal-arch/geowise](https://github.com/Daniyal-arch/geowise)
