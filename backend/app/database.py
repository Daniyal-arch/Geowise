# backend/app/database.py
"""
Async database connection with SQLAlchemy 2.0 and PostGIS support.

WHY ASYNC DATABASE?
-------------------
1. Non-blocking I/O (FastAPI's async requests don't wait for DB)
2. Better scalability (handle 100+ concurrent requests)
3. Connection pooling (reuse connections efficiently)
4. FastAPI recommendation (async everywhere)

DESIGN PATTERN: Session per Request
------------------------------------
- Each API request gets its own DB session
- Session auto-closed after request (even if error)
- Prevents connection leaks
- Implemented via FastAPI Dependency Injection

TECH STACK:
-----------
- SQLAlchemy 2.0: Modern async ORM
- asyncpg: Fastest PostgreSQL driver for Python
- PostGIS: Spatial queries (ST_Distance, ST_Within, etc.)
- GeoAlchemy2: SQLAlchemy + PostGIS integration
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import event
from loguru import logger

from app.config import settings


# ============================================================================
# BASE MODEL (All models inherit from this)
# ============================================================================
# WHY DECLARATIVE_BASE?
# - All ORM models must inherit from this
# - Provides SQLAlchemy magic methods (__init__, etc.)
# - Tracks all models for migrations
Base = declarative_base()


# ============================================================================
# DATABASE ENGINE
# ============================================================================
def create_engine() -> AsyncEngine:
    """
    Create async SQLAlchemy engine with connection pooling.
    
    ENGINE vs SESSION:
    - Engine: Connection factory (created once)
    - Session: Actual connection (created per request)
    
    CONNECTION POOL:
    - Pre-creates connections (fast)
    - Reuses connections (efficient)
    - Limits concurrent connections (prevents DB overload)
    
    Returns:
        AsyncEngine: Configured database engine
    """
    
    # ========================================================================
    # POOL CONFIGURATION
    # ========================================================================
    # WHY DIFFERENT POOLS FOR DEV/PROD?
    # - Development: NullPool (no pooling, easier debugging)
    # - Production: QueuePool (connection reuse, performance)
    
    if settings.is_development:
        # NullPool: Creates new connection for each request
        # WHY?
        # - Easy to debug (no connection reuse)
        # - See exactly when connections open/close
        # - Don't need to restart server to drop connections
        pool_class = NullPool
        logger.debug("Using NullPool (no connection pooling)")
    else:
        # QueuePool: Maintains pool of reusable connections
        # WHY?
        # - Much faster (reuse connections)
        # - Handles concurrent requests efficiently
        # - Production standard
        pool_class = AsyncAdaptedQueuePool
        logger.debug(
            f"Using QueuePool (size={settings.DB_POOL_SIZE}, "
            f"max_overflow={settings.DB_MAX_OVERFLOW})"
        )
    
    # ========================================================================
    # CREATE ENGINE
    # ========================================================================
    engine = create_async_engine(
        settings.DATABASE_URL,
        
        # Connection pool settings
        poolclass=pool_class,
        pool_size=settings.DB_POOL_SIZE if not settings.is_development else 0,
        max_overflow=settings.DB_MAX_OVERFLOW if not settings.is_development else 0,
        
        # Pool recycling
        # WHY RECYCLE?
        # - PostgreSQL closes idle connections after timeout
        # - Prevents "connection closed" errors
        # - Recycle before PostgreSQL timeout (typically 1 hour)
        pool_recycle=3600,  # 1 hour
        
        # Pre-ping connections
        # WHY?
        # - Check if connection is alive before using
        # - Prevents "server closed connection" errors
        # - Small performance cost, but worth it
        pool_pre_ping=True,
        
        # Logging
        echo=settings.DB_ECHO_SQL,  # Log all SQL (dev only!)
        
        # Connection arguments
        # WHY server_settings?
        # - Set timezone to UTC (avoid timezone bugs)
        # - Set statement timeout (prevent long-running queries)
        connect_args={
            "server_settings": {
                "application_name": f"{settings.PROJECT_NAME}_async",
                "jit": "off",  # Disable JIT (slight performance hit, but stable)
            },
            "command_timeout": 60,  # Query timeout (60 seconds)
        },
    )
    
    return engine


# ============================================================================
# SESSION FACTORY
# ============================================================================
# WHY SEPARATE FACTORY?
# - Engine created once (expensive)
# - Sessions created per request (cheap with pooling)
# - Clean separation of concerns

engine = create_engine()

# AsyncSessionLocal: Factory that creates sessions
# WHY THIS NAME?
# - Convention from SQLAlchemy docs
# - "Local" means thread-local (though we're async, not threaded)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    
    # Session configuration
    expire_on_commit=False,  # Keep objects accessible after commit
    autocommit=False,        # Manual transaction control
    autoflush=False,         # Manual flush control
)


# ============================================================================
# DEPENDENCY INJECTION (FastAPI)
# ============================================================================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.
    
    USAGE IN ROUTES:
    ----------------
    ```python
    from fastapi import Depends
    from app.database import get_db
    
    @app.get("/fires")
    async def get_fires(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Fire))
        return result.scalars().all()
    ```
    
    WHAT HAPPENS:
    1. Request comes in
    2. FastAPI calls get_db()
    3. New session created from pool
    4. Session injected into route function
    5. Route uses session
    6. After route finishes (even if error), session closed
    
    WHY ASYNC GENERATOR?
    - yield creates context manager
    - Code before yield = setup
    - Code after yield = cleanup
    - Cleanup runs even if route raises exception
    
    Yields:
        AsyncSession: Database session for this request
    """
    
    async with AsyncSessionLocal() as session:
        try:
            logger.debug("📂 Database session opened")
            yield session
            
        except Exception as e:
            # Rollback on error
            await session.rollback()
            logger.error(f"❌ Database error, rolling back: {e}")
            raise
            
        finally:
            # Always close session (returns connection to pool)
            await session.close()
            logger.debug("📂 Database session closed")


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================
async def init_db() -> None:
    """
    Initialize database with PostGIS and H3 extensions.
    
    CALL THIS AT STARTUP (in main.py):
    -----------------------------------
    ```python
    @app.on_event("startup")
    async def startup():
        await init_db()
    ```
    
    WHAT IT DOES:
    1. Enables PostGIS extension (spatial queries)
    2. Enables H3 extension (hexagonal indexing)
    3. Creates all tables (if they don't exist)
    
    WHY NOT ALEMBIC?
    - This is for extensions (must be superuser)
    - Alembic is for schema changes
    - Extensions enabled once, schema changes many times
    """
    
    async with engine.begin() as conn:
        logger.info("🔧 Initializing database extensions...")
        
        # ====================================================================
        # ENABLE POSTGIS
        # ====================================================================
        # WHY POSTGIS?
        # - Spatial queries (ST_Distance, ST_Buffer, ST_Intersects)
        # - Spatial indexes (fast geometric searches)
        # - Geography types (lat/lon on sphere)
        await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        logger.success("✅ PostGIS extension enabled")
        
        # ====================================================================
        # ENABLE H3
        # ====================================================================
        # WHY H3?
        # - Hexagonal grid system (better than squares)
        # - Hierarchical (aggregate res 9 → res 6 → res 5)
        # - No edge effects (squares have 4 types of neighbors)
        await conn.execute("CREATE EXTENSION IF NOT EXISTS h3;")
        logger.success("✅ H3 extension enabled")
        
        # ====================================================================
        # CREATE TABLES (Development only)
        # ====================================================================
        # WHY if is_development?
        # - Production: Use Alembic migrations (controlled)
        # - Development: Auto-create tables (convenient)
        if settings.is_development:
            logger.info("📋 Creating tables...")
            await conn.run_sync(Base.metadata.create_all)
            logger.success("✅ Tables created")


async def close_db() -> None:
    """
    Close database connections.
    
    CALL THIS AT SHUTDOWN (in main.py):
    ------------------------------------
    ```python
    @app.on_event("shutdown")
    async def shutdown():
        await close_db()
    ```
    
    WHAT IT DOES:
    - Closes all connections in pool
    - Releases database resources
    - Graceful shutdown
    
    WHY NEEDED?
    - Without this: Connections stay open (resource leak)
    - With this: Clean shutdown, DB happy
    """
    
    logger.info("🔌 Closing database connections...")
    await engine.dispose()
    logger.success("✅ Database connections closed")


# ============================================================================
# DATABASE HEALTH CHECK
# ============================================================================
async def check_db_health() -> bool:
    """
    Check if database is accessible.
    
    USAGE:
    ------
    ```python
    @app.get("/health")
    async def health_check():
        db_ok = await check_db_health()
        return {"database": "ok" if db_ok else "error"}
    ```
    
    WHAT IT CHECKS:
    1. Can connect to database?
    2. PostGIS available?
    3. H3 available?
    
    Returns:
        bool: True if database is healthy
    """
    
    try:
        async with engine.begin() as conn:
            # Check basic connection
            await conn.execute("SELECT 1;")
            
            # Check PostGIS
            result = await conn.execute(
                "SELECT PostGIS_Version();"
            )
            postgis_version = result.scalar()
            logger.debug(f"PostGIS version: {postgis_version}")
            
            # Check H3
            result = await conn.execute(
                "SELECT h3_get_resolution('8928308280fffff');"
            )
            h3_works = result.scalar() == 9
            logger.debug(f"H3 working: {h3_works}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return False


# ============================================================================
# SESSION EVENTS (Advanced monitoring)
# ============================================================================
# Track active sessions for debugging
_active_sessions = 0

@event.listens_for(AsyncSessionLocal, "after_begin")
def receive_after_begin(session, transaction, connection):
    """Log when session begins transaction."""
    global _active_sessions
    _active_sessions += 1
    logger.debug(f"📊 Active sessions: {_active_sessions}")


@event.listens_for(AsyncSessionLocal, "after_commit")
def receive_after_commit(session):
    """Log successful commits."""
    logger.debug("✅ Transaction committed")


@event.listens_for(AsyncSessionLocal, "after_rollback")
def receive_after_rollback(session):
    """Log rollbacks."""
    logger.warning("⚠️  Transaction rolled back")


@event.listens_for(engine.sync_engine, "close")
def receive_close(dbapi_conn, connection_record):
    """Log when connection closed."""
    global _active_sessions
    _active_sessions -= 1
    logger.debug(f"📊 Active sessions: {_active_sessions}")


# ============================================================================
# USAGE EXAMPLE (FOR REFERENCE - REMOVE IN PRODUCTION)
# ============================================================================
if __name__ == "__main__":
    """
    Test database connection.
    
    HOW TO RUN:
    -----------
    PS> python backend/app/database.py
    
    REQUIREMENTS:
    -------------
    1. PostgreSQL running (docker-compose up -d postgres)
    2. .env file configured
    3. PostGIS + H3 extensions available
    """
    
    import asyncio
    
    async def test():
        # Initialize
        await init_db()
        
        # Health check
        healthy = await check_db_health()
        print(f"Database healthy: {healthy}")
        
        # Test session
        async for session in get_db():
            result = await session.execute("SELECT 'Hello GEOWISE!'")
            print(result.scalar())
        
        # Cleanup
        await close_db()
    
    asyncio.run(test())