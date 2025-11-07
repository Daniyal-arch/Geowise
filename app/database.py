"""
GEOWISE Database Configuration
Async SQLAlchemy setup with SQLite for development.
"""
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Get logger
logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.
    
    Why use DeclarativeBase instead of declarative_base()?
    - Newer SQLAlchemy 2.0 style
    - Better type hints and autocompletion
    - Future-proof architecture
    """
    pass


class DatabaseManager:
    """
    Manages database connections and sessions.
    
    Uses async SQLAlchemy for non-blocking database operations.
    This is crucial for FastAPI's async nature.
    """
    
    def __init__(self, database_url: str):
        """
        Initialize database manager with connection URL.
        
        Args:
            database_url: SQLAlchemy connection string
                         Format: sqlite+aiosqlite:///./geowise.db
        """
        self.database_url = database_url
        self.engine = None
        self.async_session_maker = None
        
    async def connect(self) -> None:
        """
        Create database engine and session factory.
        
        Why separate connect method?
        - Allows async initialization
        - Can be called explicitly during app startup
        - Better error handling
        """
        try:
            # Create async engine with connection pooling
            self.engine = create_async_engine(
                self.database_url,
                echo=settings.DEBUG,  # Log SQL queries in debug mode
                future=True,  # Use SQLAlchemy 2.0 style
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,  # Recycle connections every hour
            )
            
            # Create async session factory
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,  # Better for async operations
                autoflush=False,  # We'll handle flushes explicitly
            )
            
            logger.info(
                "Database connection pool initialized",
                database_url=self._mask_database_url(self.database_url),
                debug_mode=settings.DEBUG
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize database connection",
                error=str(e),
                database_url=self._mask_database_url(self.database_url)
            )
            raise
    
    async def disconnect(self) -> None:
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection pool closed")
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session.
        
        Yields:
            AsyncSession: Database session for operations
            
        Usage:
            async with database.get_session() as session:
                result = await session.execute(query)
                
        Why use context manager?
        - Automatic session cleanup
        - Proper transaction handling
        - Exception safety
        """
        if not self.async_session_maker:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()  # Auto-commit if no exceptions
            except Exception:
                await session.rollback()  # Rollback on any exception
                raise
            finally:
                await session.close()  # Always close session
    
    async def create_tables(self) -> None:
        """
        Create all database tables.
        
        In production, we'd use Alembic migrations.
        For development, this creates tables automatically.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
    
    def _mask_database_url(self, url: str) -> str:
        """Mask sensitive information in database URL for logging."""
        if "sqlite" in url:
            return "sqlite+aiosqlite:///./geowise.db"
        return url  # Add more masking logic for other databases


# Global database instance
# This follows the FastAPI dependency injection pattern
database_manager = DatabaseManager(settings.DATABASE_URL)


# FastAPI dependency for database sessions
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides database sessions.
    
    Usage in route handlers:
        @app.get("/fires")
        async def get_fires(db: AsyncSession = Depends(get_db)):
            # Use db session here
            
    Why use dependency injection?
    - Automatic session management per request
    - Proper cleanup even if exceptions occur
    - Testable with mock sessions
    """
    async for session in database_manager.get_session():
        yield session


# Convenience functions for app lifecycle
async def init_db() -> None:
    """Initialize database connection during app startup."""
    await database_manager.connect()
    
    # Create tables in development
    if settings.ENVIRONMENT == "development":
        await database_manager.create_tables()


async def close_db() -> None:
    """Close database connection during app shutdown."""
    await database_manager.disconnect()