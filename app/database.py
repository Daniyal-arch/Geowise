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
    """Base class for all SQLAlchemy models."""
    pass


class DatabaseManager:
    """Manages database connections and sessions for SQLite."""
    
    def __init__(self, database_url: str):
        # FORCE SQLite URL to prevent PostgreSQL dialect
        if "postgresql" in database_url or "asyncpg" in database_url:
            logger.warning("PostgreSQL URL detected, forcing SQLite for development")
            self.database_url = "sqlite+aiosqlite:///./geowise.db"
        else:
            self.database_url = database_url
            
        self.engine = None
        self.async_session_maker = None
        
    async def connect(self) -> None:
        """Create SQLite database engine and session factory."""
        try:
            # Force SQLite dialect explicitly
            if not self.database_url.startswith("sqlite+aiosqlite"):
                self.database_url = "sqlite+aiosqlite:///./geowise.db"
            
            # Create async engine for SQLite
            self.engine = create_async_engine(
                self.database_url,
                echo=settings.DEBUG,
                future=True,
                connect_args={"check_same_thread": False}  # Required for async SQLite
            )
            
            # Create async session factory
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            
            logger.info(
                "✅ SQLite database initialized",
                database_url="sqlite+aiosqlite:///./geowise.db",
                debug_mode=settings.DEBUG
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize SQLite database: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session."""
        if not self.async_session_maker:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def create_tables(self) -> None:
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


# Global database instance
database_manager = DatabaseManager(settings.DATABASE_URL)


# FastAPI dependency for database sessions
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides database sessions."""
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