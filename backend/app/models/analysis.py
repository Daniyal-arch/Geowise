"""
GEOWISE - Analysis Results Model (SQLite Compatible)
app/models/analysis.py

Stores cached results of spatial correlation analyses to avoid expensive recomputation.

WHY THIS MODEL:
- Spatial correlations are computationally expensive (5-10 seconds)
- Results are deterministic for same inputs (region + datasets + timeframe)
- Caching results improves API response time by 100-1000x
- Enables historical analysis tracking

ARCHITECTURE:
- SQLite compatible (no PostGIS required)
- Stores results as JSON for flexibility
- Indexes for fast lookup by analysis type and region
- Includes statistical measures (correlation coefficient, p-value)
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Index, Text, Boolean
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import json
from typing import Dict, List, Optional, Any

from app.database import Base


class AnalysisResult(Base):
    """
    Cached spatial correlation analysis results.
    
    Example Use Cases:
    1. Fire-Temperature Correlation: "Do fires occur more in hot areas?"
    2. Fire-Deforestation Correlation: "Are fires increasing in deforested regions?"
    3. Climate-Forest Correlation: "Does rainfall affect forest loss rates?"
    
    WHY CACHE:
    - First request: 5-10 seconds (fetch data + compute correlation)
    - Cached request: 0.01 seconds (database lookup)
    - Performance improvement: 500-1000x faster
    """
    __tablename__ = "analysis_results"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
                index=True, comment="Unique analysis identifier")
    
    # Analysis metadata
    analysis_type = Column(String(50), nullable=False, index=True,
                          comment="Type of analysis: fire_temperature, fire_deforestation, climate_forest")
    
    analysis_name = Column(String(200), nullable=True,
                          comment="Human-readable analysis name")
    
    # Region definition
    region_type = Column(String(50), nullable=False,
                        comment="Type of region: bbox, country, h3_cells, custom")
    
    region_identifier = Column(String(200), nullable=False, index=True,
                              comment="Region identifier: lat_min,lon_min,lat_max,lon_max OR country_iso OR h3_indexes")
    
    region_name = Column(String(200), nullable=True,
                        comment="Human-readable region name (e.g., 'Pakistan', 'Punjab Province')")
    
    # Spatial resolution
    h3_resolution = Column(Integer, nullable=False,
                          comment="H3 resolution used for analysis (5=20km, 6=3km, 9=174m)")
    
    # Datasets involved
    primary_dataset = Column(String(50), nullable=False,
                            comment="Primary dataset: fires, forest, climate")
    
    secondary_dataset = Column(String(50), nullable=False,
                              comment="Secondary dataset to correlate with")
    
    datasets_json = Column(Text, nullable=True,
                          comment="JSON array of all datasets involved: ['fires', 'climate', 'forest']")
    
    # Time period
    start_date = Column(DateTime, nullable=False, index=True,
                       comment="Analysis start date")
    
    end_date = Column(DateTime, nullable=False, index=True,
                     comment="Analysis end date")
    
    temporal_resolution = Column(String(20), nullable=True,
                                comment="Temporal aggregation: daily, weekly, monthly, yearly")
    
    # Statistical results
    correlation_coefficient = Column(Float, nullable=True,
                                    comment="Pearson correlation coefficient (-1 to 1)")
    
    p_value = Column(Float, nullable=True,
                    comment="Statistical significance (p < 0.05 is significant)")
    
    r_squared = Column(Float, nullable=True,
                      comment="Coefficient of determination (0 to 1)")
    
    sample_size = Column(Integer, nullable=True,
                        comment="Number of spatial cells analyzed")
    
    is_significant = Column(Boolean, default=False,
                           comment="True if p_value < 0.05")
    
    # Detailed results (stored as JSON)
    results_json = Column(Text, nullable=True,
                         comment="Full analysis results as JSON")
    
    # Summary and insights
    summary = Column(Text, nullable=True,
                    comment="Human-readable summary of findings")
    
    key_findings = Column(Text, nullable=True,
                         comment="JSON array of key findings")
    
    # Visualization data
    visualization_data = Column(Text, nullable=True,
                               comment="JSON data for charts/maps")
    
    # Analysis parameters
    parameters_json = Column(Text, nullable=True,
                            comment="JSON of analysis parameters (filters, thresholds, etc.)")
    
    # System metadata
    computation_time_seconds = Column(Float, nullable=True,
                                     comment="Time taken to compute analysis")
    
    cache_hit = Column(Boolean, default=False,
                      comment="True if result was from cache")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                       comment="When analysis was first created")
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                       onupdate=func.now(),
                       comment="When analysis was last updated")
    
    accessed_at = Column(DateTime(timezone=True), server_default=func.now(),
                        comment="Last time this result was accessed")
    
    access_count = Column(Integer, default=0,
                         comment="Number of times this result was accessed")
    
    # Composite indexes for fast lookups
    __table_args__ = (
        # Find analyses by type and region
        Index('idx_analysis_type_region', 'analysis_type', 'region_identifier'),
        
        # Find analyses by datasets
        Index('idx_analysis_datasets', 'primary_dataset', 'secondary_dataset'),
        
        # Find analyses by time period
        Index('idx_analysis_dates', 'start_date', 'end_date'),
        
        # Find significant results
        Index('idx_analysis_significant', 'is_significant', 'correlation_coefficient'),
        
        # Find recent analyses
        Index('idx_analysis_created', 'created_at'),
    )
    
    def __repr__(self):
        return (f"<AnalysisResult("
                f"type={self.analysis_type}, "
                f"region={self.region_identifier}, "
                f"correlation={self.correlation_coefficient:.3f} if self.correlation_coefficient else 'N/A', "
                f"significant={self.is_significant})>")
    
    @property
    def datasets(self) -> List[str]:
        """Get list of datasets involved in analysis."""
        if self.datasets_json:
            return json.loads(self.datasets_json)
        return [self.primary_dataset, self.secondary_dataset]
    
    @datasets.setter
    def datasets(self, value: List[str]):
        """Set datasets as JSON array."""
        self.datasets_json = json.dumps(value)
    
    @property
    def results(self) -> Dict[str, Any]:
        """Parse results JSON."""
        if self.results_json:
            return json.loads(self.results_json)
        return {}
    
    @results.setter
    def results(self, value: Dict[str, Any]):
        """Store results as JSON."""
        self.results_json = json.dumps(value)
    
    @property
    def parameters(self) -> Dict[str, Any]:
        """Parse parameters JSON."""
        if self.parameters_json:
            return json.loads(self.parameters_json)
        return {}
    
    @parameters.setter
    def parameters(self, value: Dict[str, Any]):
        """Store parameters as JSON."""
        self.parameters_json = json.dumps(value)
    
    @property
    def visualization(self) -> Dict[str, Any]:
        """Parse visualization data JSON."""
        if self.visualization_data:
            return json.loads(self.visualization_data)
        return {}
    
    @visualization.setter
    def visualization(self, value: Dict[str, Any]):
        """Store visualization data as JSON."""
        self.visualization_data = json.dumps(value)
    
    def record_access(self) -> None:
        """Record that this analysis was accessed (for cache analytics)."""
        self.accessed_at = datetime.now()
        self.access_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert analysis to dictionary for API responses.
        
        Returns:
            Dict with all analysis data including parsed JSON fields
        """
        return {
            "id": self.id,
            "analysis_type": self.analysis_type,
            "analysis_name": self.analysis_name,
            "region": {
                "type": self.region_type,
                "identifier": self.region_identifier,
                "name": self.region_name
            },
            "spatial_resolution": {
                "h3_resolution": self.h3_resolution,
                "approximate_cell_size": self._get_h3_cell_size(self.h3_resolution)
            },
            "datasets": self.datasets,
            "time_period": {
                "start_date": self.start_date.isoformat() if self.start_date else None,
                "end_date": self.end_date.isoformat() if self.end_date else None,
                "temporal_resolution": self.temporal_resolution
            },
            "statistics": {
                "correlation_coefficient": self.correlation_coefficient,
                "p_value": self.p_value,
                "r_squared": self.r_squared,
                "sample_size": self.sample_size,
                "is_significant": self.is_significant
            },
            "results": self.results,
            "summary": self.summary,
            "key_findings": json.loads(self.key_findings) if self.key_findings else [],
            "visualization": self.visualization,
            "metadata": {
                "computation_time": self.computation_time_seconds,
                "cache_hit": self.cache_hit,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "accessed_at": self.accessed_at.isoformat() if self.accessed_at else None,
                "access_count": self.access_count
            }
        }
    
    @staticmethod
    def _get_h3_cell_size(resolution: int) -> str:
        """Get approximate H3 cell size for human-readable output."""
        sizes = {
            0: "~4,357 km",
            1: "~609 km",
            2: "~86 km",
            3: "~12 km",
            4: "~1.7 km",
            5: "~252 m",
            6: "~36 m",
            7: "~5 m",
            8: "~0.7 m",
            9: "~0.1 m (10 cm)",
            10: "~15 mm",
            11: "~2 mm",
            12: "~0.3 mm",
            13: "~0.04 mm",
            14: "~0.006 mm",
            15: "~0.0009 mm"
        }
        return sizes.get(resolution, f"Resolution {resolution}")
    
    @classmethod
    def create_cache_key(cls,
                        analysis_type: str,
                        region_identifier: str,
                        datasets: List[str],
                        start_date: datetime,
                        end_date: datetime,
                        h3_resolution: int) -> str:
        """
        Generate a unique cache key for an analysis.
        
        Used to check if an analysis with same parameters already exists.
        
        Args:
            analysis_type: Type of analysis
            region_identifier: Region identifier
            datasets: List of datasets
            start_date: Start date
            end_date: End date
            h3_resolution: H3 resolution
        
        Returns:
            Unique cache key string
        """
        datasets_str = "_".join(sorted(datasets))
        date_str = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        
        return f"{analysis_type}_{region_identifier}_{datasets_str}_{date_str}_h3{h3_resolution}"
    
    @classmethod
    async def find_cached_analysis(cls,
                            session,
                            analysis_type: str,
                            region_identifier: str,
                            start_date: datetime,
                            end_date: datetime,
                            h3_resolution: int) -> Optional['AnalysisResult']:
        """
        Find existing cached analysis with same parameters.
        
        Args:
            session: AsyncSession database session
            analysis_type: Type of analysis
            region_identifier: Region identifier
            start_date: Start date
            end_date: End date
            h3_resolution: H3 resolution
        
        Returns:
            AnalysisResult if found, None otherwise
        """
        from sqlalchemy import select
        
        stmt = select(cls).filter(
            cls.analysis_type == analysis_type,
            cls.region_identifier == region_identifier,
            cls.start_date == start_date,
            cls.end_date == end_date,
            cls.h3_resolution == h3_resolution
        )
        
        result = await session.execute(stmt)
        return result.scalars().first()


# Example usage and testing
if __name__ == "__main__":
    """
    Example: Creating an analysis result
    """
    
    # Example analysis result
    analysis = AnalysisResult(
        analysis_type="fire_temperature",
        analysis_name="Fire-Temperature Correlation in Pakistan (Jan 2025)",
        region_type="country",
        region_identifier="PAK",
        region_name="Pakistan",
        h3_resolution=5,
        primary_dataset="fires",
        secondary_dataset="climate",
        start_date=datetime(2025, 1, 1),
        end_date=datetime(2025, 1, 31),
        temporal_resolution="daily",
        correlation_coefficient=0.73,
        p_value=0.001,
        r_squared=0.53,
        sample_size=125,
        is_significant=True,
        computation_time_seconds=7.5
    )
    
    # Set datasets
    analysis.datasets = ["fires", "climate"]
    
    # Set results
    analysis.results = {
        "cells_analyzed": 125,
        "cells_with_fires": 45,
        "average_temperature": 28.5,
        "fire_intensity_avg": 12.3,
        "correlation_details": {
            "method": "pearson",
            "confidence_interval": [0.65, 0.81]
        }
    }
    
    # Set summary
    analysis.summary = (
        "Strong positive correlation (r=0.73, p<0.001) between fire occurrence "
        "and temperature. Fires are significantly more likely in areas with "
        "temperatures above 30°C."
    )
    
    # Set key findings
    analysis.key_findings = json.dumps([
        "73% correlation between fire density and maximum temperature",
        "45 out of 125 grid cells (36%) had fire detections",
        "Average temperature in fire-affected areas: 32.1°C vs 26.8°C in non-fire areas",
        "Statistical significance: p < 0.001 (highly significant)"
    ])
    
    print("✅ Analysis Result Model Test")
    print(f"   Type: {analysis.analysis_type}")
    print(f"   Region: {analysis.region_name}")
    print(f"   Correlation: {analysis.correlation_coefficient}")
    print(f"   Significant: {analysis.is_significant}")
    print(f"   Datasets: {analysis.datasets}")
    print(f"\n   Summary: {analysis.summary}")