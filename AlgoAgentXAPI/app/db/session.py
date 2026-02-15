from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from ..core.config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Set to True for SQL logging in development
    future=True,
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
