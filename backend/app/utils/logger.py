# backend/app/utils/logger.py
"""
Structured logging system for GEOWISE using loguru.

WHY LOGURU?
-----------
- Better than standard logging: automatic JSON formatting, rotation, colored output
- Thread-safe and async-safe (critical for FastAPI)
- Zero configuration for structured logs
- Better stack traces with variable values
- Easy filtering by level/module

WHAT THIS PROVIDES:
-------------------
1. Structured JSON logs for production (machine-readable)
2. Colored console logs for development (human-readable)
3. Automatic log rotation (prevents disk filling)
4. Request ID tracking for distributed tracing
5. Performance timing decorators
"""

import sys
import logging
from pathlib import Path
from typing import Any, Callable, Optional
from functools import wraps
import time
from loguru import logger
from contextvars import ContextVar

# ============================================================================
# CONTEXT VARIABLES (Thread-safe storage for request-specific data)
# ============================================================================
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


# ============================================================================
# LOG CONFIGURATION
# ============================================================================
class LogConfig:
    """Centralized logging configuration."""
    
    CONSOLE_LEVEL = "DEBUG"
    FILE_LEVEL = "INFO"
    
    LOG_DIR = Path("logs")
    LOG_FILE = LOG_DIR / "geowise.log"
    ERROR_FILE = LOG_DIR / "errors.log"
    
    ROTATION = "500 MB"
    RETENTION = "10 days"
    COMPRESSION = "zip"
    
    CONSOLE_FORMAT = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level> | "
        "{extra}"
    )
    
    FILE_FORMAT = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message} | "
        "{extra}"
    )


# ============================================================================
# LOGGER SETUP
# ============================================================================
def setup_logging(
    console_level: str = LogConfig.CONSOLE_LEVEL,
    file_level: str = LogConfig.FILE_LEVEL,
    log_file: Path = LogConfig.LOG_FILE,
    error_file: Path = LogConfig.ERROR_FILE,
) -> None:
    """Configure the logger with console and file handlers."""
    
    LogConfig.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    
    # Console handler
    logger.add(
        sys.stdout,
        format=LogConfig.CONSOLE_FORMAT,
        level=console_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # File handler
    logger.add(
        log_file,
        format=LogConfig.FILE_FORMAT,
        level=file_level,
        rotation=LogConfig.ROTATION,
        retention=LogConfig.RETENTION,
        compression=LogConfig.COMPRESSION,
        backtrace=True,
        diagnose=True,
    )
    
    # Error-only handler
    logger.add(
        error_file,
        format=LogConfig.FILE_FORMAT,
        level="ERROR",
        rotation=LogConfig.ROTATION,
        retention=LogConfig.RETENTION,
        compression=LogConfig.COMPRESSION,
        backtrace=True,
        diagnose=True,
    )
    
    # Intercept stdlib logging
    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            
            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )
    
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    for logger_name in ["uvicorn", "uvicorn.access", "sqlalchemy", "httpx"]:
        logging.getLogger(logger_name).handlers = [InterceptHandler()]
    
    logger.info("🚀 Logging system initialized")


def set_request_id(request_id: str) -> None:
    """Set request ID for current context."""
    request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """Get current request ID from context."""
    return request_id_var.get()


def log_with_context(**kwargs: Any) -> None:
    """Add custom fields to log entry."""
    request_id = get_request_id()
    if request_id:
        kwargs["request_id"] = request_id
    return logger.bind(**kwargs)


def log_execution_time(func: Optional[Callable] = None, *, level: str = "INFO") -> Callable:
    """Decorator to log function execution time."""
    
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            logger.log(level, f"▶️  {fn.__name__} started")
            
            try:
                result = await fn(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                logger.log(level, f"✅ {fn.__name__} completed in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                logger.error(f"❌ {fn.__name__} failed after {elapsed:.2f}s: {e}")
                raise
        
        @wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            logger.log(level, f"▶️  {fn.__name__} started")
            
            try:
                result = fn(*args, **kwargs)
                elapsed = time.perf_counter() - start_time
                logger.log(level, f"✅ {fn.__name__} completed in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start_time
                logger.error(f"❌ {fn.__name__} failed after {elapsed:.2f}s: {e}")
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(fn):
            return async_wrapper
        else:
            return sync_wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)


def log_error_with_context(
    error: Exception,
    context: dict[str, Any],
    level: str = "ERROR"
) -> None:
    """Log an error with additional context."""
    logger.bind(**context).log(
        level,
        f"{error.__class__.__name__}: {str(error)}"
    )