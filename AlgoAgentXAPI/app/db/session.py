from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ..core.config import settings

# Create async engine with safe long-running query tolerance.
# Broker/SMTP/Redis external timeouts are intentionally not changed here.
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Set to True for SQL logging in development
    future=True,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_timeout=60,
    connect_args={"command_timeout": 600} if settings.database_url.startswith("postgresql+asyncpg") else {},
)

# Create async session factory
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncSession:
    """
    Dependency to get async database session
    """
    session = async_session()
    try:
        yield session
    finally:
        await session.close()
