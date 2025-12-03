"""NASA FIRMS Fire Data Model - SQLite Compatible"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Index, Text
from sqlalchemy.sql import func
import h3
from app.database import Base
import uuid
from datetime import datetime


class FireDetection(Base):
    """NASA FIRMS fire detection record with multi-resolution H3 indexing."""
    __tablename__ = "fire_detections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), 
                index=True, comment="Unique fire detection identifier")
    
    # Spatial location
    latitude = Column(Float, nullable=False, comment="Latitude in decimal degrees")
    longitude = Column(Float, nullable=False, comment="Longitude in decimal degrees")
    
    # Country identifier (NEW - for historical data organization)
    country = Column(String(3), nullable=True, index=True, comment="ISO 3166-1 alpha-3 country code")
    
    # Multi-resolution H3 indexing
    h3_index_12 = Column(String(15), nullable=False, index=True)
    h3_index_9 = Column(String(15), nullable=False, index=True)
    h3_index_6 = Column(String(15), nullable=False, index=True)
    h3_index_5 = Column(String(15), nullable=False, index=True)
    
    # Fire intensity metrics
    brightness = Column(Float, nullable=False)
    bright_ti5 = Column(Float)
    frp = Column(Float)
    
    # Detection metadata
    confidence = Column(String(1))
    scan = Column(Float)
    track = Column(Float)
    
    # Satellite information
    satellite = Column(String(10))
    instrument = Column(String(10))
    version = Column(String(10))
    
    # Temporal information
    acq_date = Column(DateTime, nullable=False, index=True)
    acq_time = Column(String(4))
    daynight = Column(String(1))
    
    # System fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), 
                       onupdate=func.now())
    
    raw_data = Column(Text)

    __table_args__ = (
        Index('idx_fires_h3_9_date', 'h3_index_9', 'acq_date'),
        Index('idx_fires_h3_5_date', 'h3_index_5', 'acq_date'),
        Index('idx_fires_frp_date', 'frp', 'acq_date'),
        Index('idx_fires_location', 'latitude', 'longitude'),
        Index('idx_fires_country_year', 'country', 'acq_date'),  # NEW - for historical queries
    )

    def __init__(self, latitude: float, longitude: float, **kwargs):
        if 'id' not in kwargs:
         self.id = str(uuid.uuid4())
        
        self.latitude = latitude
        self.longitude = longitude
        
        # Generate H3 indexes
        if hasattr(h3, 'latlng_to_cell'):
            self.h3_index_12 = h3.latlng_to_cell(latitude, longitude, 12)
            self.h3_index_9 = h3.latlng_to_cell(latitude, longitude, 9)
            self.h3_index_6 = h3.latlng_to_cell(latitude, longitude, 6)
            self.h3_index_5 = h3.latlng_to_cell(latitude, longitude, 5)
        else:
            self.h3_index_12 = h3.geo_to_h3(latitude, longitude, 12)
            self.h3_index_9 = h3.geo_to_h3(latitude, longitude, 9)
            self.h3_index_6 = h3.geo_to_h3(latitude, longitude, 6)
            self.h3_index_5 = h3.geo_to_h3(latitude, longitude, 5)
        
        # Field mapping for NASA CSV compatibility
        field_mapping = {
            'bright_ti4': 'brightness',
        }
        
        # Process kwargs
        for key, value in kwargs.items():
            if key in ['latitude', 'longitude']:
                continue
                
            model_field = field_mapping.get(key, key)
            
            if model_field == 'acq_date' and isinstance(value, str):
                try:
                    value = datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    pass
            
            if hasattr(self, model_field):
                setattr(self, model_field, value)

    @property
    def year(self) -> int:
        """Extract year from acquisition date."""
        return self.acq_date.year if self.acq_date else None

    def __repr__(self):
        return f"<FireDetection(id={self.id}, country={self.country}, lat={self.latitude}, lon={self.longitude}, date={self.acq_date})>"

    def to_geojson(self) -> dict:
        """Convert to GeoJSON feature."""
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.longitude, self.latitude]
            },
            "properties": {
                "id": str(self.id),
                "country": self.country,
                "brightness": self.brightness,
                "frp": self.frp,
                "confidence": self.confidence,
                "acq_date": self.acq_date.isoformat() if self.acq_date else None,
                "acq_time": self.acq_time,
                "satellite": self.satellite,
                "h3_index_9": self.h3_index_9,
                "h3_index_5": self.h3_index_5
            }
        }
    
    @classmethod
    def from_nasa_csv_row(cls, row: dict) -> 'FireDetection':
        """Create FireDetection from NASA CSV row."""
        latitude = float(row['latitude'])
        longitude = float(row['longitude'])
        fire_data = row.copy()
        fire_data.pop('latitude', None)
        fire_data.pop('longitude', None)
        return cls(latitude=latitude, longitude=longitude, **fire_data)


class FireAggregation(Base):
    """Pre-aggregated fire statistics at H3 grid resolutions."""
    __tablename__ = "fire_aggregations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    h3_index = Column(String(15), nullable=False, index=True)
    resolution = Column(Integer, nullable=False, index=True)
    aggregation_date = Column(DateTime, nullable=False, index=True)
    aggregation_period = Column(String(10), nullable=False)
    fire_count = Column(Integer, default=0)
    total_frp = Column(Float)
    avg_frp = Column(Float)
    max_frp = Column(Float)
    avg_brightness = Column(Float)
    high_confidence_count = Column(Integer, default=0)
    nominal_confidence_count = Column(Integer, default=0)
    low_confidence_count = Column(Integer, default=0)
    centroid_lat = Column(Float)
    centroid_lon = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), 
                       onupdate=func.now())

    def __repr__(self):
        return f"<FireAggregation(h3={self.h3_index}, date={self.aggregation_date}, count={self.fire_count})>"