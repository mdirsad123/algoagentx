from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from ..core.config import settings

# Create async engine with safe long-running query tolerance.
# Broker/SMTP/Redis external timeouts are intentionally not changed here.
connect_args = {}
if settings.database_url.startswith("postgresql+asyncpg"):
    connect_args = {
        "command_timeout": 14400,
        # Fail fast during a transient Docker DNS/network outage.  The old
        # asyncpg default could leave browser requests hanging for ~60-90s.
        "timeout": max(3, int(settings.db_connect_timeout_seconds)),
    }

engine = create_async_engine(
    settings.database_url,
    echo=False,  # Set to True for SQL logging in development
    future=True,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=max(1, int(settings.db_pool_size)),
    max_overflow=max(0, int(settings.db_max_overflow)),
    pool_timeout=max(3, int(settings.db_pool_timeout_seconds)),
    connect_args=connect_args,
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
