import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from sqlalchemy import NullPool, create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

# Create async engine
if settings.DEBUG:
    # Pas de pool en mode debug
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
        echo=settings.DB_ECHO,
        poolclass=NullPool,
    )
else:
    # Avec pool en mode production
    engine = create_async_engine(
        settings.PROD_DB_URL,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
    )

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_session() -> AsyncGenerator[AsyncSession | Any, Any]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database - create tables if not exist"""
    try:
        async with engine.begin() as conn:
            # You can run any initialization here
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


# ------------------------------------------------------------
# SYNC (Celery workers, scripts hors-ligne)
# ------------------------------------------------------------
# Ici on garde l'URL telle quelle (driver psycopg2 / pg8000, etc.),
# car Celery fonctionne mieux avec SQLAlchemy sync.

engine_sync = create_engine(
    settings.DATABASE_URL if settings.DEBUG else settings.PROD_DB_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DB_ECHO,
)


SessionLocalSync = sessionmaker(bind=engine_sync, autoflush=False, autocommit=False)

async def close_db():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")

async def check_db_connection() -> bool:
    """Check if database is healthy"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False