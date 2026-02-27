from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .api.v1.router import api_router
from .core.config import settings
from .core.redis_manager import redis_manager
from .middleware.security import SecurityHeadersMiddleware, RequestIDMiddleware, HealthCheckMiddleware
import logging
import sys

logger = logging.getLogger(__name__)

# Configure logging to print to stdout for Fly.io visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("=" * 60)
    logger.info("Starting AlgoAgentX API...")
    logger.info("=" * 60)
    
    # Print database diagnostic info
    logger.info("[DIAGNOSTIC] Database Configuration:")
    logger.info(f"  - Masked URL: {settings.masked_database_url}")
    logger.info(f"  - Database: {settings.database_name}")
    logger.info(f"  - Host: {settings.database_host}")
    logger.info(f"  - Port: {settings.database_port}")
    logger.info(f"  - Environment: {settings.env}")
    logger.info("-" * 60)
    
    # Initialize database
    from .db.init_db import init_db
    await init_db()
    
    # Initialize Redis connection
    redis_available = await redis_manager.initialize()
    if redis_available:
        logger.info("[REDIS] Connection established successfully")
    else:
        logger.warning("[REDIS] Unavailable - using fallback background execution")
    
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Shutting down AlgoAgentX API...")
    await redis_manager.close()


# Create FastAPI app with lifespan
app = FastAPI(
    title="AlgoAgentX API",
    description="Read-only API for AlgoAgentX trading platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add middleware in correct order (last added, first executed)
app.add_middleware(HealthCheckMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Add CORS middleware with environment-specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "AlgoAgentX API"}


@app.get("/health/redis")
async def redis_health_check():
    """
    Redis health check endpoint
    """
    try:
        health_status = await redis_manager.health_check()
        return health_status
    except Exception as e:
        return {
            "redis_available": False,
            "error": str(e),
            "message": "Failed to check Redis health"
        }


@app.get("/health/db")
async def database_health_check():
    """
    Database health check endpoint
    """
    try:
        from .db.init_db import check_db_connection
        await check_db_connection()
        return {"db_available": True}
    except Exception as e:
        return {
            "db_available": False,
            "error": str(e)
        }


@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {"message": "AlgoAgentX API", "version": "1.0.0"}


@app.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes/Docker health checks
    This endpoint checks if the application is ready to serve traffic
    """
    try:
        # Check Redis connection
        redis_health = await redis_manager.health_check()
        redis_available = redis_health.get("redis_available", False)
        
        # In a more complex application, you might also check:
        # - Database connectivity
        # - External service dependencies
        # - Cache connections
        
        if redis_available or not settings.is_production:
            return {
                "status": "ready",
                "service": "AlgoAgentX API",
                "redis_available": redis_available,
                "environment": settings.env
            }
        else:
            return {
                "status": "not_ready",
                "service": "AlgoAgentX API",
                "redis_available": False,
                "message": "Redis is required for production deployment"
            }
    except Exception as e:
        return {
            "status": "error",
            "service": "AlgoAgentX API",
            "error": str(e),
            "message": "Readiness check failed"
        }
