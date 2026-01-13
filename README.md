# GEOWISE - Geospatial AI Platform

An intelligent geospatial analysis platform that leverages Large Language Models (LLMs) to analyze satellite imagery and environmental data through natural language prompts.

## Overview

GEOWISE combines the power of LLMs with geospatial data APIs to enable environmental analysis, monitoring, and insights through simple text prompts. Users can perform complex satellite imagery analysis, deforestation tracking, flood mapping, urbanization monitoring, and water change detection without writing code.

## Key Features

- **Natural Language Processing**: Interact with satellite data using simple text prompts
- **Multi-Source Data Integration**: Integrates NASA FIRMS, Global Forest Watch, Open-Meteo, and World Bank APIs
- **AI-Powered Analysis**: Uses Groq LLM (Llama 3.3 70B) for intelligent query interpretation and analysis
- **H3 Spatial Indexing**: Efficient geospatial operations using Uber's H3 hexagonal grid system
- **Real-time Environmental Monitoring**: Track fires, deforestation, floods, and climate changes
- **Interactive Web Interface**: Modern Next.js frontend with MapLibre GL for visualization
- **RESTful API**: FastAPI-powered backend with async support

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

### Project Structure

```
geowise/
├── app/                    # Backend application
│   ├── api/               # API routes and endpoints
│   ├── core/              # Core business logic
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

## Usage

### Example Queries

GEOWISE understands natural language queries like:

- "Show me deforestation in the Amazon rainforest over the last year"
- "Detect active fires in California from the past week"
- "Analyze flood risk areas in Pakistan during monsoon season"
- "Track urban expansion in Dubai from 2020 to 2024"
- "Monitor water levels in Lake Mead over the past 5 years"
- "What is the air quality index in New Delhi?"
- "Compare forest cover loss between Brazil and Indonesia"

### API Endpoints

Key API endpoints include:

- `POST /api/v1/query` - Submit natural language query
- `GET /api/v1/analysis/{id}` - Retrieve analysis results
- `GET /api/v1/reports/{id}` - Get generated reports
- `GET /health` - Health check endpoint

See full API documentation at `/docs` after starting the server.

## Data Sources

GEOWISE integrates with multiple authoritative data sources:

- **NASA FIRMS**: Active fire detection from MODIS and VIIRS satellites
- **Global Forest Watch**: Deforestation and forest change data
- **Open-Meteo**: Historical and current climate data
- **World Bank**: Environmental and socioeconomic indicators
- **Sentinel Hub**: (Coming soon) High-resolution satellite imagery

## Technology Highlights

### H3 Spatial Indexing
Uses Uber's H3 hexagonal hierarchical spatial index for:
- Efficient spatial queries
- Multi-resolution analysis (1km to 25km grids)
- Fast aggregations and visualizations

### RAG Pipeline
Implements Retrieval-Augmented Generation for:
- Context-aware responses
- Domain-specific knowledge integration
- Improved accuracy in geospatial analysis

### Agent Architecture
Multi-agent system with specialized roles:
- **Query Agent**: Interprets user intent and extracts parameters
- **Analysis Agent**: Processes geospatial data and generates insights
- **Report Agent**: Creates human-readable summaries and visualizations

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

## Deployment

### Docker Deployment
```bash
# Build and run with docker-compose
docker-compose up -d
```

### Production Considerations
- Use PostgreSQL instead of SQLite for production
- Enable HTTPS and proper CORS settings
- Set up Redis with persistence
- Configure proper logging and monitoring
- Use environment-specific configurations
- Implement rate limiting for API endpoints

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Roadmap

- [ ] Integration with Sentinel Hub for high-resolution imagery
- [ ] Support for custom ML models and analysis pipelines
- [ ] Collaborative analysis and sharing features
- [ ] Mobile application
- [ ] Real-time alerting system
- [ ] Advanced visualization tools (3D terrain, time-series animations)
- [ ] Multi-language support
- [ ] Batch processing for large-scale analysis

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

Project Link: [https://github.com/Daniyal-arch/geowise](https://github.com/yourusername/geowise)

---

Made with passion for environmental monitoring and AI-powered geospatial analysis.
