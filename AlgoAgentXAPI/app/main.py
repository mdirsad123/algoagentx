import asyncio
import logging
from contextlib import asynccontextmanager

from .core.logging_config import configure_logging

# Configure logging before importing the rest of the application so modules
# inherit the same quiet production policy.
configure_logging()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1.router import api_router
from .core.config import settings
from .core.redis_manager import redis_manager
from .middleware.security import (
    HealthCheckMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("Starting AlgoAgentX API")
    logger.debug(
        "Database configuration | url=%s | database=%s | host=%s | port=%s | environment=%s",
        settings.masked_database_url,
        settings.database_name,
        settings.database_host,
        settings.database_port,
        settings.env,
    )

    from .db.init_db import init_db
    await init_db()

    redis_available = await redis_manager.initialize()
    if redis_available:
        logger.debug("Redis connection established successfully")
    else:
        logger.error("Redis unavailable; using fallback background execution")

    runner_task = None
    broker_sync_task = None
    # Always start the lightweight auto-runner loop. Per-deployment switches
    # still decide whether any strategy work executes.
    from .services.live.auto_runner_service import auto_runner_loop
    runner_task = asyncio.create_task(auto_runner_loop())
    logger.debug("Live auto runner background loop started")

    if getattr(settings, "live_broker_sync_enabled", True):
        from .services.live.broker_sync_service import broker_sync_loop
        broker_sync_task = asyncio.create_task(broker_sync_loop())
        logger.debug("Live broker sync background loop enabled")
    else:
        logger.debug("Live broker sync background loop disabled")

    try:
        yield
    finally:
        logger.debug("Shutting down AlgoAgentX API")
        if runner_task is not None:
            runner_task.cancel()
            try:
                await runner_task
            except asyncio.CancelledError:
                pass
        if broker_sync_task is not None:
            broker_sync_task.cancel()
            try:
                await broker_sync_task
            except asyncio.CancelledError:
                pass
        await redis_manager.close()


app = FastAPI(
    title="AlgoAgentX API",
    description="AlgoAgentX trading platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(HealthCheckMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

cors_origins = list(
    {
        *settings.allowed_origins,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "AlgoAgentX API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AlgoAgentX API"}


@app.get("/health/redis")
async def redis_health_check():
    try:
        return await redis_manager.health_check()
    except Exception as exc:
        logger.exception("Redis health check failed")
        return {
            "redis_available": False,
            "error": str(exc),
            "message": "Failed to check Redis health",
        }


@app.get("/health/db")
async def database_health_check():
    try:
        from .db.init_db import check_db_connection

        await check_db_connection()
        return {"db_available": True}
    except Exception as exc:
        logger.exception("Database health check failed")
        return {"db_available": False, "error": str(exc)}


@app.get("/ready")
async def readiness_check():
    try:
        redis_health = await redis_manager.health_check()
        redis_available = redis_health.get("redis_available", False)

        if redis_available or not settings.is_production:
            return {
                "status": "ready",
                "service": "AlgoAgentX API",
                "redis_available": redis_available,
                "environment": settings.env,
            }

        return {
            "status": "not_ready",
            "service": "AlgoAgentX API",
            "redis_available": False,
            "message": "Redis is required for production deployment",
        }
    except Exception as exc:
        logger.exception("Readiness check failed")
        return {
            "status": "error",
            "service": "AlgoAgentX API",
            "error": str(exc),
            "message": "Readiness check failed",
        }
