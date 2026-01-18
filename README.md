# GEOWISE - Geospatial AI Platform

An intelligent geospatial analysis platform that leverages Large Language Models (LLMs) to analyze satellite imagery and environmental data through natural language prompts.

> **Note:** This project is under active development. Some features are experimental and the platform is not yet production-ready. See [Development Status](#development-status) for details.

## Overview

GEOWISE combines the power of LLMs with geospatial data APIs to enable environmental analysis, monitoring, and insights through simple text prompts. Users can perform complex satellite imagery analysis, deforestation tracking, fire detection, flood mapping, urbanization monitoring, and climate correlation analysis without writing code.

## Current Capabilities

### Fire Detection & Analysis
- **Historical Fire Data (2020-2024)**: Query fire counts, statistics, and locations from NASA FIRMS database
- **Real-time Fire Detection**: Last 7 days of fire data from NASA FIRMS API
- **Monthly Breakdown**: Analyze peak fire months and seasonal patterns
- **High-Intensity Fires**: Find fires by FRP (Fire Radiative Power) threshold
- **Supported Countries**: Pakistan (PAK), India (IND), Brazil (BRA), Indonesia (IDN), Bangladesh (BGD)

### Fire-Climate Correlation
- **Statistical Analysis**: Real Pearson correlation coefficients using scipy (not AI approximations)
- **Temperature Correlation**: Analyze relationship between fires and temperature
- **Precipitation Correlation**: Analyze relationship between fires and rainfall
- **P-value Significance**: Statistical significance testing for correlations

### Forest Loss Tracking
- **Yearly Deforestation Data (2001-2024)**: From Global Forest Watch
- **Trend Analysis**: Identify increasing/decreasing/stable deforestation trends
- **Country-level Statistics**: Total forest loss, peak years, recent changes

### Additional Features
- **Climate Data Integration**: Historical weather data from Open-Meteo (1940-present)
- **Interactive Map Visualization**: MapLibre GL with multiple data layers
- **Air Quality Monitoring**: Real-time air quality index data
- **Flood Risk Visualization**: Flood-affected area mapping
- **Urban Change Detection**: Track urbanization patterns

## Example Queries

GEOWISE understands natural language queries like:

```
# Fire Analysis
"How many fires in Pakistan during 2020?"
"What were the peak fire months in India 2021?"
"Show me the most intense fires in Brazil 2020"
"Recent fires in Indonesia" (last 7 days)

# Climate Correlation
"Analyze fire and temperature correlation in Pakistan 2020"
"How do fires correlate with precipitation in Indonesia 2021?"

# Forest Loss
"Show deforestation in Brazil"
"Forest loss trend in Indonesia"

# Environmental Reports
"Generate environmental report for India"
```

## Live Demos

Check out these real-world applications:

1. **[Deforestation Analysis & Real-time Fire Detection](https://www.linkedin.com/posts/daniyal-khan-7b80b02a6_geoai-remotesensing-satelliteimagery-activity-7403729807953342464-N5ud)** - Monitor forest loss and active fires using natural language prompts

2. **[Flood Mapping by Prompts](https://www.linkedin.com/posts/daniyal-khan-7b80b02a6_geoai-environment-earthobservation-activity-7407820737220272129-aAHr)** - Detect and map flood-affected areas through AI-driven analysis

3. **[Urbanization Change Analysis](https://www.linkedin.com/posts/daniyal-khan-7b80b02a6_geoai-urbanplanning-satelliteimagery-activity-7412870295830790144-GqYw)** - Track urban expansion and development in any city worldwide

4. **[Water Change Detection](https://www.linkedin.com/posts/daniyal-khan-7b80b02a6_gis-remotesensing-earthobservation-activity-7415769403465764864-EUkZ)** - Monitor water body changes, drought conditions, and reservoir levels

## Architecture

### Backend Stack
- **Framework**: FastAPI with async/await support
- **Database**: SQLite with SQLAlchemy ORM and Alembic migrations
- **LLM Integration**: Groq API with Llama 3.3 70B model
- **Vector Database**: ChromaDB for RAG (Retrieval-Augmented Generation)
- **Geospatial**: H3, Shapely, Rasterio, GeoJSON, PyProj
- **Data Processing**: Pandas, NumPy, SciPy, Scikit-learn
- **Task Queue**: Celery with Redis
- **Caching**: Redis for performance optimization

### Frontend Stack
- **Framework**: Next.js 14 with React 18
- **Mapping**: MapLibre GL and React Map GL
- **State Management**: Zustand
- **Data Fetching**: TanStack React Query, Axios
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Icons**: Lucide React

### Multi-Agent Architecture
- **Query Agent**: Parses natural language queries into structured parameters with intent detection
- **Analysis Agent**: Plans the best analysis approach based on query parameters
- **Report Agent**: Generates human-readable insights with strict anti-hallucination rules

### Project Structure

```
geowise/
├── app/                    # Backend application
│   ├── api/v1/            # REST API endpoints
│   ├── core/              # Spatial & aggregation logic
│   ├── llm/               # LLM integration layer
│   │   ├── agents/        # AI agents (query, analysis, report)
│   │   ├── prompts/       # Prompt templates
│   │   ├── rag/           # RAG implementation
│   │   └── orchestrator.py # LLM orchestration
│   ├── models/            # SQLAlchemy database models
│   ├── schemas/           # Pydantic schemas for validation
│   ├── services/          # External API integrations
│   │   ├── gfw.py        # Global Forest Watch
│   │   ├── nasa_firms.py # NASA Fire data
│   │   ├── open_meteo.py # Climate data
│   │   └── worldbank.py  # World Bank indicators
│   ├── utils/             # Utility functions
│   ├── config.py          # Configuration management
│   ├── database.py        # Database setup
│   └── main.py            # FastAPI application entry
├── frontend/              # Next.js frontend
│   ├── src/
│   │   ├── app/          # Next.js 14 app directory
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom React hooks
│   │   └── lib/          # Frontend utilities
│   └── public/           # Static assets
├── data/                  # Data storage
├── logs/                  # Application logs
├── migrations/            # Database migrations
├── scripts/               # Utility scripts
├── tests/                 # Test suite
└── requirements.txt       # Python dependencies
```

## Installation

### Prerequisites
- Python 3.9+
- Node.js 18+
- Redis (for caching and background tasks)
- Git

### Backend Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd geowise
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
# LLM Configuration
GROQ_API_KEY=your_groq_api_key_here

# External APIs (optional)
NASA_FIRMS_API_KEY=your_nasa_firms_key
GFW_API_KEY=your_gfw_key

# Database
DATABASE_URL=sqlite+aiosqlite:///./geowise.db

# Redis
REDIS_URL=redis://localhost:6379/0
```

5. Initialize database:
```bash
alembic upgrade head
```

6. Start the backend server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment:
```bash
cp .env.example .env.local
```

Edit `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

4. Start development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## API Endpoints

### Natural Language Query
- `POST /api/v1/query/nl` - Submit natural language query (AI-powered)
- `POST /api/v1/query/rag` - RAG-based question answering

### Fire Data
- `GET /api/v1/fires` - Query fire detections
- `POST /api/v1/fires/aggregation` - Aggregate fires by H3 cells

### Forest Data
- `GET /api/v1/forest/loss/{country}` - Forest loss data
- `GET /api/v1/forest/stats/{country}` - Forest statistics
- `GET /api/v1/forest/trend/{country}` - Deforestation trend analysis

### Analysis
- `POST /api/v1/analysis/correlation` - Spatial correlation analysis

### Other
- `GET /api/v1/climate/*` - Climate data endpoints
- `GET /api/v1/tiles/*` - Map tile servers
- `GET /health` - Health check

See full API documentation at `/docs` after starting the server.

## Data Sources

GEOWISE integrates with multiple authoritative data sources:

| Source | Data Type | Coverage |
|--------|-----------|----------|
| NASA FIRMS | Active fire detection (MODIS/VIIRS) | Global, Real-time + Historical |
| Global Forest Watch | Deforestation & forest change | Global, 2001-2024 |
| Open-Meteo | Historical weather & climate | Global, 1940-present |
| World Bank | Environmental & socioeconomic indicators | Global |

## Technology Highlights

### H3 Spatial Indexing
Uses Uber's H3 hexagonal hierarchical spatial index for:
- Efficient spatial queries
- Multi-resolution analysis (Resolution 5 ~20km for analysis, Resolution 9 ~174m for display)
- Fast aggregations and visualizations

### RAG Pipeline
Implements Retrieval-Augmented Generation for:
- Context-aware responses
- Domain-specific knowledge integration
- Improved accuracy in geospatial analysis

### Anti-Hallucination Measures
The Report Agent includes strict rules to prevent AI from inventing statistics:
- Only reports numbers that exist in actual data
- Forbidden phrases list for unverified claims
- Required verification before writing any statistic
- Uses scipy.stats for real statistical calculations (not AI approximations)

## Development Status

This project is under active development. Current status:

### Working Features
- Fire detection queries (historical and real-time)
- Monthly fire breakdown analysis
- High FRP fire identification
- Fire-climate correlation with real statistics
- Forest loss data and trends
- Interactive map visualization
- Natural language query interface

### In Progress / Experimental
- Air quality monitoring
- Flood risk visualization
- Urban change detection
- Water change detection
- Multi-year comparison reports

### Not Yet Implemented
- Docker containerization and Docker Compose setup
- Production deployment configurations
- Kubernetes manifests
- CI/CD pipelines
- Comprehensive test coverage
- Rate limiting for API endpoints
- User authentication and authorization

## Roadmap

### Near-term
- [ ] Docker images and Docker Compose for easy deployment
- [ ] Production deployment guide (AWS/GCP/Azure)
- [ ] Comprehensive test suite
- [ ] API rate limiting and authentication
- [ ] Expanded country support for historical data

### Mid-term
- [ ] Integration with Sentinel Hub for high-resolution imagery
- [ ] Real-time alerting system for fire/flood events
- [ ] Batch processing for large-scale analysis
- [ ] Advanced visualization tools (3D terrain, time-series animations)

### Long-term
- [ ] Support for custom ML models and analysis pipelines
- [ ] Collaborative analysis and sharing features
- [ ] Mobile application
- [ ] Multi-language support

## Development

### Running Tests
```bash
# Backend tests
pytest

# Frontend tests
cd frontend
npm test
```

### Code Quality
```bash
# Format Python code
black app/ tests/

# Lint frontend
cd frontend
npm run lint
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- NASA FIRMS for fire detection data
- Global Forest Watch for deforestation monitoring
- Open-Meteo for climate data
- Groq for fast LLM inference
- Uber H3 team for spatial indexing

## Contact

Daniyal Khan - [LinkedIn](https://www.linkedin.com/in/daniyal-khan-7b80b02a6/)

Project Link: [https://github.com/Daniyal-arch/geowise](https://github.com/Daniyal-arch/geowise)

---

Made with passion for environmental monitoring and AI-powered geospatial analysis.
