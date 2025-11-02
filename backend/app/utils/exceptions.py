# backend/app/utils/exceptions.py
"""
Custom exceptions and error handlers for GEOWISE.

WHY CUSTOM EXCEPTIONS?
-----------------------
1. Better error messages (tell user WHAT went wrong and HOW to fix)
2. Consistent error responses across API
3. Proper HTTP status codes (400 vs 404 vs 500)
4. Can catch specific errors and handle differently

DESIGN PATTERN: Exception Hierarchy
------------------------------------
GeoWiseException (base)
├── DataException (data-related)
│   ├── DataNotFoundError (404)
│   ├── DataFetchError (502/503)
│   └── DataValidationError (422)
├── SpatialException (H3/PostGIS errors)
│   ├── InvalidCoordinatesError (422)
│   └── SpatialOperationError (500)
├── AnalysisException (correlation errors)
│   └── InsufficientDataError (422)
└── ExternalAPIException (NASA/GFW/etc.)
    ├── APIRateLimitError (429)
    └── APITimeoutError (504)
"""

from typing import Any, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from loguru import logger


# ============================================================================
# BASE EXCEPTION
# ============================================================================
class GeoWiseException(Exception):
    """
    Base exception for all GEOWISE errors.
    
    WHY INHERIT FROM Exception?
    - Can catch all GEOWISE errors with single except block
    - Easy to distinguish our errors from library errors
    
    Attributes:
        message: User-friendly error message
        details: Technical details (for logs, not shown to user)
        status_code: HTTP status code (default 500)
    """
    
    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


# ============================================================================
# DATA EXCEPTIONS (4xx errors - client's fault)
# ============================================================================
class DataException(GeoWiseException):
    """Base class for data-related errors."""
    pass


class DataNotFoundError(DataException):
    """
    Raised when requested data doesn't exist.
    
    Example:
        >>> raise DataNotFoundError(
        ...     "fires",
        ...     region="Pakistan",
        ...     date_range="2024-01-01 to 2024-12-31"
        ... )
        # Returns 404 with message: "No fires data found for Pakistan..."
    """
    
    def __init__(self, resource: str, **filters: Any):
        filter_str = ", ".join(f"{k}={v}" for k, v in filters.items())
        message = f"No {resource} data found"
        if filter_str:
            message += f" (filters: {filter_str})"
        
        super().__init__(
            message=message,
            details={"resource": resource, "filters": filters},
            status_code=status.HTTP_404_NOT_FOUND
        )


class DataFetchError(DataException):
    """
    Raised when external API fails to return data.
    
    WHY 502 BAD_GATEWAY?
    - It's not our fault (500)
    - It's not user's fault (400)
    - It's the upstream service's fault (502)
    
    Example:
        >>> raise DataFetchError(
        ...     "NASA FIRMS",
        ...     error="Connection timeout after 30s"
        ... )
    """
    
    def __init__(self, source: str, error: str):
        super().__init__(
            message=f"Failed to fetch data from {source}: {error}",
            details={"source": source, "error": error},
            status_code=status.HTTP_502_BAD_GATEWAY
        )


class DataValidationError(DataException):
    """
    Raised when data fails validation (e.g., invalid GeoJSON).
    
    WHY 422 UNPROCESSABLE_ENTITY?
    - Request was well-formed (not 400)
    - But semantically incorrect (422)
    - Like uploading invalid CSV format
    """
    
    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            message=f"Invalid {field}: {reason}",
            details={"field": field, "value": value, "reason": reason},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


# ============================================================================
# SPATIAL EXCEPTIONS (coordinate/H3 errors)
# ============================================================================
class SpatialException(GeoWiseException):
    """Base class for spatial operation errors."""
    pass


class InvalidCoordinatesError(SpatialException):
    """
    Raised when coordinates are out of valid range.
    
    Valid ranges:
    - Latitude: -90 to 90
    - Longitude: -180 to 180
    """
    
    def __init__(self, lat: Optional[float] = None, lon: Optional[float] = None):
        if lat is not None and (lat < -90 or lat > 90):
            message = f"Latitude {lat} out of range (-90 to 90)"
        elif lon is not None and (lon < -180 or lon > 180):
            message = f"Longitude {lon} out of range (-180 to 180)"
        else:
            message = "Invalid coordinates provided"
        
        super().__init__(
            message=message,
            details={"latitude": lat, "longitude": lon},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class SpatialOperationError(SpatialException):
    """
    Raised when H3 or PostGIS operation fails.
    
    Example:
        >>> raise SpatialOperationError(
        ...     operation="buffer",
        ...     details="Invalid geometry type"
        ... )
    """
    
    def __init__(self, operation: str, details: str):
        super().__init__(
            message=f"Spatial operation '{operation}' failed: {details}",
            details={"operation": operation, "error": details},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# ANALYSIS EXCEPTIONS (correlation/statistics errors)
# ============================================================================
class AnalysisException(GeoWiseException):
    """Base class for analysis errors."""
    pass


class InsufficientDataError(AnalysisException):
    """
    Raised when not enough data points for analysis.
    
    WHY IS THIS NEEDED?
    - Correlation needs minimum 3 data points
    - P-value calculation needs minimum 5 points
    - Better to fail explicitly than return garbage results
    """
    
    def __init__(self, dataset: str, required: int, actual: int):
        super().__init__(
            message=f"Insufficient {dataset} data: need {required} points, got {actual}",
            details={"dataset": dataset, "required": required, "actual": actual},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


# ============================================================================
# EXTERNAL API EXCEPTIONS (NASA FIRMS, GFW, etc.)
# ============================================================================
class ExternalAPIException(GeoWiseException):
    """Base class for external API errors."""
    pass


class APIRateLimitError(ExternalAPIException):
    """
    Raised when hitting API rate limits.
    
    WHY 429 TOO_MANY_REQUESTS?
    - Standard HTTP code for rate limiting
    - Client should retry with backoff
    
    WHY INCLUDE retry_after?
    - Tell client when they can retry
    - Prevents hammering the API
    """
    
    def __init__(self, api_name: str, retry_after: int = 60):
        super().__init__(
            message=f"{api_name} rate limit exceeded. Retry after {retry_after}s",
            details={"api": api_name, "retry_after": retry_after},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class APITimeoutError(ExternalAPIException):
    """
    Raised when external API times out.
    
    WHY 504 GATEWAY_TIMEOUT?
    - We waited, they didn't respond
    - Not our fault, not client's fault
    - Upstream service is slow
    """
    
    def __init__(self, api_name: str, timeout: int):
        super().__init__(
            message=f"{api_name} request timed out after {timeout}s",
            details={"api": api_name, "timeout": timeout},
            status_code=status.HTTP_504_GATEWAY_TIMEOUT
        )


# ============================================================================
# FASTAPI EXCEPTION HANDLERS
# ============================================================================
async def geowise_exception_handler(
    request: Request,
    exc: GeoWiseException
) -> JSONResponse:
    """
    Handle all GeoWise custom exceptions.
    
    WHY SEPARATE HANDLER?
    - Consistent error response format
    - Automatic logging with context
    - Can add correlation IDs, request tracking
    
    Response format:
    {
        "error": {
            "type": "DataNotFoundError",
            "message": "No fires data found...",
            "details": {...},
            "path": "/api/v1/fires",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    }
    """
    
    # Log the error with request context
    logger.bind(
        path=str(request.url.path),
        method=request.method,
        error_type=exc.__class__.__name__,
        status_code=exc.status_code
    ).error(f"Request failed: {exc.message}")
    
    # Build response
    error_response = {
        "error": {
            "type": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
            "path": str(request.url.path),
            # Don't send timestamp in production (timezone issues)
            # Client should use response Date header
        }
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException
) -> JSONResponse:
    """
    Handle FastAPI's built-in HTTPException.
    
    WHY?
    - FastAPI raises HTTPException for 404, 422, etc.
    - We want consistent format with our custom exceptions
    - Better logging
    """
    
    logger.bind(
        path=str(request.url.path),
        method=request.method,
        status_code=exc.status_code
    ).warning(f"HTTP error: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "path": str(request.url.path),
            }
        }
    )


async def validation_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle Pydantic validation errors (422).
    
    WHY SEPARATE HANDLER?
    - Pydantic errors are complex (nested field errors)
    - Need to format them user-friendly
    - Want to log which validation failed
    """
    
    logger.bind(
        path=str(request.url.path),
        method=request.method
    ).warning(f"Validation error: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "type": "ValidationError",
                "message": "Request validation failed",
                "details": str(exc),
                "path": str(request.url.path),
            }
        }
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Catch-all for unexpected errors.
    
    WHY NEEDED?
    - Prevents exposing internal errors to users
    - Logs full traceback for debugging
    - Returns generic 500 error
    
    SECURITY NOTE:
    - Never return exc details to client (information leakage)
    - Log everything, show nothing
    """
    
    logger.bind(
        path=str(request.url.path),
        method=request.method,
        error_type=exc.__class__.__name__
    ).exception(f"Unexpected error: {exc}")
    
    # Generic error for client (don't leak internals!)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "InternalServerError",
                "message": "An unexpected error occurred. Please try again later.",
                "path": str(request.url.path),
            }
        }
    )


# ============================================================================
# REGISTRATION HELPER (used in main.py)
# ============================================================================
def register_exception_handlers(app) -> None:
    """
    Register all exception handlers with FastAPI app.
    
    CALL THIS IN main.py:
        from app.utils.exceptions import register_exception_handlers
        register_exception_handlers(app)
    
    ORDER MATTERS:
    1. Most specific first (GeoWiseException)
    2. Then FastAPI exceptions (HTTPException)
    3. Finally catch-all (Exception)
    """
    
    app.add_exception_handler(GeoWiseException, geowise_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("✅ Exception handlers registered")