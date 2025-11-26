"""
GEOWISE Models Package
Centralized import location for all database models and service classes.

WHY THIS FILE:
- Single import location: `from app.models import FireDetection, ForestMonitor`
- Cleaner code: No need to remember which file each model is in
- Easier refactoring: Can reorganize files without breaking imports
- Clear API: Shows what's available at a glance

ARCHITECTURE:
- Database Models: FireDetection, FireAggregation, AnalysisResult
- Service Classes: ForestMonitor, ClimateMonitor
"""

# Database Models (SQLAlchemy)
from app.models.fires import FireDetection, FireAggregation
from app.models.analysis import AnalysisResult

# Service Classes (External API integrations)
from app.models.forest import ForestMonitor
from app.models.climate import ClimateMonitor

# Export all models and services
__all__ = [
    # Fire data models
    "FireDetection",        # Individual fire detection records with H3 indexing
    "FireAggregation",      # Pre-aggregated fire statistics at H3 resolutions
    
    # Analysis models
    "AnalysisResult",       # Cached spatial correlation analysis results
    
    # Service classes
    "ForestMonitor",        # Global Forest Watch integration
    "ClimateMonitor",       # Open-Meteo climate data integration
]

# Example usage:
# from app.models import FireDetection, ForestMonitor, AnalysisResult
# 
# # Use fire model
# fire = FireDetection(latitude=30.5, longitude=70.5, frp=12.5, ...)
# 
# # Use forest service
# forest_service = ForestMonitor()
# stats = forest_service.get_country_forest_stats("PAK")
# 
# # Use analysis model
# analysis = AnalysisResult(analysis_type="fire_temperature", ...)