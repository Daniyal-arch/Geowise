"""
GEOWISE Custom Exceptions
Domain-specific exceptions for geospatial operations and API errors.
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class GEOWISEError(HTTPException):
    """Base exception for all GEOWISE application errors."""
    
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An unexpected error occurred",
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.context = context or {}


# Spatial Operation Exceptions
class SpatialOperationError(GEOWISEError):
    """Raised when spatial operations fail."""
    
    def __init__(
        self, 
        detail: str = "Spatial operation failed",
        operation: Optional[str] = None,
        bbox: Optional[list] = None,
        h3_resolution: Optional[int] = None
    ):
        context = {}
        if operation:
            context["operation"] = operation
        if bbox:
            context["bbox"] = bbox
        if h3_resolution:
            context["h3_resolution"] = h3_resolution
            
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="SPATIAL_OPERATION_ERROR",
            context=context
        )


class InvalidGeometryError(SpatialOperationError):
    """Raised when geometry data is invalid."""
    
    def __init__(self, detail: str = "Invalid geometry provided"):
        super().__init__(
            detail=detail,
            error_code="INVALID_GEOMETRY"
        )


class H3ResolutionError(SpatialOperationError):
    """Raised when H3 resolution is invalid."""
    
    def __init__(self, resolution: int, valid_range: tuple = (0, 15)):
        super().__init__(
            detail=f"H3 resolution {resolution} is invalid. Valid range: {valid_range}",
            error_code="INVALID_H3_RESOLUTION",
            context={"resolution": resolution, "valid_range": valid_range}
        )


# Dataset & External API Exceptions
class DatasetNotFoundError(GEOWISEError):
    """Raised when a requested dataset is not found."""
    
    def __init__(self, dataset_name: str, available_datasets: Optional[list] = None):
        context = {"dataset_name": dataset_name}
        if available_datasets:
            context["available_datasets"] = available_datasets
            
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_name}' not found",
            error_code="DATASET_NOT_FOUND",
            context=context
        )


class ExternalAPIError(GEOWISEError):
    """Raised when external API calls fail."""
    
    def __init__(
        self,
        service: str,
        detail: str = "External API service unavailable",
        status_code: int = status.HTTP_502_BAD_GATEWAY
    ):
        super().__init__(
            status_code=status_code,
            detail=f"{service}: {detail}",
            error_code="EXTERNAL_API_ERROR",
            context={"service": service}
        )


class NASAFIRMSAPIError(ExternalAPIError):
    """Raised when NASA FIRMS API calls fail."""
    
    def __init__(self, detail: str = "NASA FIRMS API unavailable"):
        super().__init__(
            service="NASA_FIRMS",
            detail=detail
        )


class GFWTileError(ExternalAPIError):
    """Raised when Global Forest Watch tile services fail."""
    
    def __init__(self, detail: str = "GFW tile service unavailable"):
        super().__init__(
            service="GFW_TILES",
            detail=detail
        )


# Analysis Exceptions
class CorrelationAnalysisError(GEOWISEError):
    """Raised when correlation analysis fails."""
    
    def __init__(
        self,
        detail: str = "Correlation analysis failed",
        datasets: Optional[list] = None,
        correlation_type: Optional[str] = None
    ):
        context = {}
        if datasets:
            context["datasets"] = datasets
        if correlation_type:
            context["correlation_type"] = correlation_type
            
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="CORRELATION_ANALYSIS_ERROR",
            context=context
        )


# Configuration Exceptions
class ConfigurationError(GEOWISEError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, detail: str = "Configuration error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="CONFIGURATION_ERROR"
        )


# LLM & AI Exceptions
class LLMServiceError(GEOWISEError):
    """Raised when LLM services fail."""
    
    def __init__(self, detail: str = "LLM service error"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="LLM_SERVICE_ERROR"
        )


# Exception handler (will be used in main.py)
async def geowise_exception_handler(request, exc: GEOWISEError):
    """Global exception handler for GEOWISE custom exceptions."""
    from app.utils.logger import get_logger
    logger = get_logger("exceptions")
    
    # Log the error with context
    logger.error(
        f"GEOWISE error: {exc.detail}",
        error_code=exc.error_code,
        status_code=exc.status_code,
        context=exc.context,
        path=request.url.path
    )
    
    # Return structured error response
    error_response = {
        "error": {
            "code": exc.error_code,
            "message": exc.detail,
            "details": exc.context
        }
    }
    
    return error_response