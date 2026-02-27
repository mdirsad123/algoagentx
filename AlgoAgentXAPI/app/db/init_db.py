"""Database initialization and health check functions."""
import logging
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from .session import engine
from .base import Base
from ..core.config import settings

logger = logging.getLogger(__name__)


async def check_db_connection() -> None:
    """
    Check if database connection is available.
    Raises exception if connection fails.
    """
    try:
        async with engine.begin() as conn:
            # Simple connectivity test
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()  # fetchone() is synchronous, don't await
            logger.info("Database connection check: SUCCESS")
    except Exception as e:
        logger.error(f"Database connection check: FAILED - {str(e)}")
        raise


async def ensure_tables_created() -> None:
    """
    Ensure all tables are created in the database.
    This imports all models and creates tables if they don't exist.
    """
    try:
        # Import models to ensure they are registered with Base.metadata
        from . import models  # This imports all models via __init__.py
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables creation: SUCCESS")
    except Exception as e:
        logger.error(f"Database tables creation: FAILED - {str(e)}")
        raise


async def init_db() -> None:
    """
    Initialize database connection and ensure tables exist.
    
    Behavior:
    - Production: Check connection, fail fast if DB unavailable
    - Development: Check connection, auto-create tables if needed
    """
    try:
        # First, test basic connectivity
        await check_db_connection()
        
        # If we're in development, auto-create tables
        if settings.is_development:
            try:
                await ensure_tables_created()
                logger.info("Development mode: Tables ensured to exist")
            except Exception as e:
                logger.error(f"Failed to create tables in development: {str(e)}")
                # In development, we continue but log the issue
                logger.warning("Continuing startup despite table creation failure")
        else:
            logger.info("Production mode: Skipping auto table creation")
            
    except Exception as e:
        error_msg = f"Database initialization failed: {str(e)}"
        logger.error(error_msg)
        
        if settings.is_production:
            # In production, fail fast
            logger.critical("Production environment: Failing startup due to DB issues")
            raise
        else:
            # In development, log warning but continue
            logger.warning("Development environment: Continuing startup with DB warning")
            logger.warning("DATABASE_URL may not be reachable - endpoints will likely return 503")