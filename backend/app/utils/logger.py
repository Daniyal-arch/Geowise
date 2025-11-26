"""
GEOWISE Structured Logging Configuration
Centralized logging setup for the entire application with structured JSON output.

Why structlog + loguru?
- structlog: Structured logging (JSON in production) for better log analysis
- loguru: Human-readable logs in development with colors and formatting
- Combined: Best of both worlds - development friendliness + production readiness
"""
import sys
import logging
from typing import Any, Dict
from pathlib import Path

import structlog
from loguru import logger

# Project root directory - adjust based on your structure
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def setup_logging(environment: str = "development") -> None:
    """
    Configure structured logging for GEOWISE application.
    
    Args:
        environment: "development" or "production"
        
    Why two different configurations?
    - Development: Human-readable, colored output for debugging
    - Production: JSON format for log aggregation systems (ELK, Datadog)
    """
    
    # Clear any existing loguru handlers
    logger.remove()
    
    if environment == "development":
        # Development: Pretty, colored logs with geospatial context
        logger.add(
            sys.stderr,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level> | "
                "<magenta>extras: {extra}</magenta>"
            ),
            level="DEBUG",
            colorize=True,
            backtrace=True,  # Detailed tracebacks for errors
            diagnose=True,   # Variable values in tracebacks
        )
        
        # Also log to file for persistent storage
        log_file = PROJECT_ROOT / "logs" / "geowise_dev.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message} | {extra}",
            level="INFO",
            rotation="10 MB",  # Rotate when file reaches 10MB
            retention="30 days",  # Keep logs for 30 days
            compression="gz",  # Compress rotated logs
        )
        
    else:
        # Production: Structured JSON logs for log aggregation
        logger.add(
            sys.stdout,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message} | {extra}",
            level="INFO",
            serialize=True,  # Output as JSON
        )
        
        # Error logs to separate file
        error_log_file = PROJECT_ROOT / "logs" / "geowise_errors.log"
        error_log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            error_log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message} | {extra}",
            level="ERROR",
            rotation="50 MB",
            retention="90 days",
            compression="gz",
        )

    # Configure structlog for additional structure
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if environment == "production" else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logger.info(
        "Logging system initialized", 
        environment=environment, 
        log_dir=str(PROJECT_ROOT / "logs")
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance for a specific module.
    
    Args:
        name: Typically __name__ of the calling module
        
    Returns:
        structlog BoundLogger with structured logging capabilities
        
    Why use this instead of direct logging?
    - Consistent logging format across entire application
    - Automatic context attachment (request IDs, spatial bounds, etc.)
    - Easy to add custom processors for geospatial context
    """
    return structlog.get_logger(name)


# Example usage and test
if __name__ == "__main__":
    setup_logging("development")
    test_logger = get_logger(__name__)
    
    # Test different log levels with geospatial context
    test_logger.debug("Debug message with spatial context", bbox=[70.0, 30.0, 80.0, 40.0])
    test_logger.info("Logger system test successful", h3_resolution=9, dataset="fires")
    test_logger.warning("Sample warning", api_call="NASA_FIRMS", retry_count=2)
    
    try:
        # Simulate an error for testing
        raise ValueError("Test error for logging system")
    except Exception as e:
        test_logger.error(
            "Error in spatial operation", 
            error_type=type(e).__name__,
            error_message=str(e),
            spatial_operation="h3_aggregation"
        )