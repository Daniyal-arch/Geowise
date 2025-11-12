"""
Custom exception hierarchy for GEOWISE application.

WHY CUSTOM EXCEPTIONS:
- Better error handling: Catch specific errors, not generic Exception
- Structured logging: Each exception includes context for debugging
- HTTP status codes: Automatically map to FastAPI responses
- User-friendly messages: Clear error messages for API consumers

ARCHITECTURE:
- GEOWISEError: Base class (extends HTTPException)
- Domain-specific exceptions: Database, spatial, API, validation errors
- Automatic logging: All exceptions log with context before raising
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class GEOWISEError(HTTPException):
    """
    Base exception class for all GEOWISE errors.
    
    Extends FastAPI's HTTPException to automatically return proper HTTP responses.
    All custom exceptions inherit from this base class.
    
    Features:
    - Automatic HTTP status code mapping
    - Structured error details (context dictionary)
    - Consistent error response format
    - Integrated with FastAPI exception handlers
    """
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize GEOWISE error.
        
        Args:
            message: Human-readable error message
            status_code: HTTP status code (default: 500)
            details: Additional context (field names, values, etc.)
        """
        self.message = message
        self.details = details or {}
        
        # FastAPI HTTPException requires 'detail' parameter
        super().__init__(
            status_code=status_code,
            detail={
                "error": self.__class__.__name__,
                "message": message,
                "details": self.details,
            }
        )
    
    def __str__(self) -> str:
        """String representation for logging."""
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message


# ============================================================================
# DATABASE ERRORS
# ============================================================================

class DatabaseError(GEOWISEError):
    """Database operation failed."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class RecordNotFoundError(GEOWISEError):
    """Requested database record not found."""
    
    def __init__(self, resource: str, identifier: Any, details: Optional[Dict] = None):
        message = f"{resource} not found: {identifier}"
        details = details or {}
        details.update({"resource": resource, "identifier": str(identifier)})
        
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class DuplicateRecordError(GEOWISEError):
    """Attempted to create duplicate record."""
    
    def __init__(self, resource: str, identifier: Any, details: Optional[Dict] = None):
        message = f"{resource} already exists: {identifier}"
        details = details or {}
        details.update({"resource": resource, "identifier": str(identifier)})
        
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


# ============================================================================
# SPATIAL OPERATION ERRORS
# ============================================================================

class SpatialOperationError(GEOWISEError):
    """Spatial computation or geometry operation failed."""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict] = None):
        details = details or {}
        if operation:
            details["operation"] = operation
        
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class InvalidGeometryError(SpatialOperationError):
    """Invalid or malformed geometry data."""
    
    def __init__(self, message: str, geometry_type: Optional[str] = None, details: Optional[Dict] = None):
        details = details or {}
        if geometry_type:
            details["geometry_type"] = geometry_type
        
        super().__init__(
            message=message,
            operation="geometry_validation",
            details=details,
        )


class H3IndexError(SpatialOperationError):
    """H3 hexagon indexing operation failed."""
    
    def __init__(self, message: str, h3_resolution: Optional[int] = None, details: Optional[Dict] = None):
        details = details or {}
        if h3_resolution is not None:
            details["h3_resolution"] = h3_resolution
        
        super().__init__(
            message=message,
            operation="h3_indexing",
            details=details,
        )


# ============================================================================
# EXTERNAL API ERRORS
# ============================================================================

class ExternalAPIError(GEOWISEError):
    """External API request failed."""
    
    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        response_body: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        details = details or {}
        if service_name:
            details["service"] = service_name
        if response_body:
            details["response"] = response_body[:500]  # Truncate long responses
        
        super().__init__(
            message=message,
            status_code=status_code,
            details=details,
        )


class NASAFIRMSAPIError(ExternalAPIError):
    """NASA FIRMS API request failed."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            service_name="NASA FIRMS",
            details=details,
        )


class GFWAPIError(ExternalAPIError):
    """Global Forest Watch API request failed."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            service_name="Global Forest Watch",
            details=details,
        )


class OpenMeteoAPIError(ExternalAPIError):
    """Open-Meteo API request failed."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            service_name="Open-Meteo",
            details=details,
        )


class WorldBankAPIError(ExternalAPIError):
    """World Bank API request failed."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            service_name="World Bank",
            details=details,
        )


class APITimeoutError(ExternalAPIError):
    """External API request timed out."""
    
    def __init__(self, message: str, service_name: Optional[str] = None, timeout_seconds: Optional[int] = None):
        details = {}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        
        super().__init__(
            message=message,
            service_name=service_name,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            details=details,
        )


class RateLimitExceededError(ExternalAPIError):
    """External API rate limit exceeded."""
    
    def __init__(self, message: str, service_name: Optional[str] = None, retry_after: Optional[int] = None):
        details = {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        
        super().__init__(
            message=message,
            service_name=service_name,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


# ============================================================================
# DATA VALIDATION ERRORS
# ============================================================================

class DataValidationError(GEOWISEError):
    """Input data validation failed."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict] = None,
    ):
        details = details or {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class InvalidDateRangeError(DataValidationError):
    """Invalid date range (start > end, future dates, etc.)."""
    
    def __init__(self, message: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
        details = {}
        if start_date:
            details["start_date"] = start_date
        if end_date:
            details["end_date"] = end_date
        
        super().__init__(
            message=message,
            field="date_range",
            details=details,
        )


class InvalidBoundingBoxError(DataValidationError):
    """Invalid bounding box coordinates."""
    
    def __init__(self, message: str, bbox: Optional[Dict] = None):
        super().__init__(
            message=message,
            field="bbox",
            details={"bbox": bbox} if bbox else None,
        )


# ============================================================================
# CORRELATION ANALYSIS ERRORS
# ============================================================================

class CorrelationAnalysisError(GEOWISEError):
    """Correlation analysis computation failed."""
    
    def __init__(
        self,
        message: str,
        analysis_type: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        details = details or {}
        if analysis_type:
            details["analysis_type"] = analysis_type
        
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class InsufficientDataError(CorrelationAnalysisError):
    """Not enough data points for statistical analysis."""
    
    def __init__(
        self,
        message: str,
        required_points: Optional[int] = None,
        available_points: Optional[int] = None,
        details: Optional[Dict] = None,
    ):
        details = details or {}
        if required_points is not None:
            details["required_points"] = required_points
        if available_points is not None:
            details["available_points"] = available_points
        
        super().__init__(
            message=message,
            details=details,
        )


# ============================================================================
# CACHE ERRORS
# ============================================================================

class CacheError(GEOWISEError):
    """Cache operation failed."""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict] = None):
        details = details or {}
        if operation:
            details["operation"] = operation
        
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


# ============================================================================
# TILE GENERATION ERRORS
# ============================================================================

class TileGenerationError(GEOWISEError):
    """Map tile generation failed."""
    
    def __init__(
        self,
        message: str,
        tile_coords: Optional[tuple] = None,
        details: Optional[Dict] = None,
    ):
        details = details or {}
        if tile_coords:
            details["tile_coords"] = {"z": tile_coords[0], "x": tile_coords[1], "y": tile_coords[2]}
        
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


# ============================================================================
# LLM ERRORS
# ============================================================================

class LLMError(GEOWISEError):
    """LLM operation failed."""
    
    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        details = details or {}
        if model:
            details["model"] = model
        
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class PromptError(LLMError):
    """Prompt generation or validation failed."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            details=details,
        )


class RAGError(LLMError):
    """RAG (Retrieval-Augmented Generation) operation failed."""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            details=details,
        )


# ============================================================================
# GLOBAL EXCEPTION HANDLER (for FastAPI)
# ============================================================================

async def geowise_exception_handler(request, exc: GEOWISEError):
    """
    Global exception handler for FastAPI.
    
    Catches all GEOWISEError exceptions and returns structured JSON responses.
    Automatically logs exceptions with full context.
    
    Usage in main.py:
        from app.utils.exceptions import GEOWISEError, geowise_exception_handler
        
        app.add_exception_handler(GEOWISEError, geowise_exception_handler)
    """
    from app.utils.logger import get_logger
    
    logger = get_logger(__name__)
    
    # Log the error with full context
    logger.error(
        f"Exception: {exc.__class__.__name__}",
        extra={
            "error_type": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
            "status_code": exc.status_code,
            "path": str(request.url),
            "method": request.method,
        },
    )
    
    # Return structured error response
    return exc