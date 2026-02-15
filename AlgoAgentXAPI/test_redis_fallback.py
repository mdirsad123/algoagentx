#!/usr/bin/env python3
"""
Test script to verify Redis connection and fallback functionality.
"""

import asyncio
import logging
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.redis_manager import redis_manager
from app.core.config import settings
from app.celery_app import is_celery_available

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_redis_connection():
    """Test Redis connection and fallback logic."""
    print("=== Redis Connection Test ===")
    print(f"Redis URL from config: {settings.redis_url}")
    print(f"Redis host: {settings.redis_host}")
    print(f"Redis port: {settings.redis_port}")
    print(f"Redis DB: {settings.redis_db}")
    print()

    # Test Redis initialization
    print("Testing Redis initialization...")
    redis_available = await redis_manager.initialize()
    print(f"Redis available: {redis_available}")
    print()

    # Test Redis health check
    print("Testing Redis health check...")
    health_status = await redis_manager.health_check()
    print(f"Health status: {health_status}")
    print()

    # Test Celery availability
    print("Testing Celery availability...")
    celery_available = is_celery_available()
    print(f"Celery available: {celery_available}")
    print()

    # Summary
    print("=== Test Summary ===")
    if redis_available:
        print("✅ Redis connection successful - Celery will use Redis backend")
    else:
        print("⚠️  Redis connection failed - Celery will use memory backend")
        print("   FastAPI BackgroundTasks will be used for job execution")

    if celery_available:
        print("✅ Celery is available for task execution")
    else:
        print("❌ Celery is not available")

    return redis_available, celery_available


async def test_job_submission_fallback():
    """Test job submission with fallback logic."""
    print("\n=== Job Submission Fallback Test ===")

    try:
        from app.services.background_service import BackgroundService
        from fastapi import BackgroundTasks

        # Create a mock background tasks object
        background_tasks = BackgroundTasks()

        # Test job submission
        print("Testing job submission with fallback...")
        job_id = await BackgroundService.submit_backtest_job(
            user_id="test-user-123",
            strategy_id="test-strategy",
            instrument_id=1,
            timeframe="1h",
            start_date="2024-01-01",
            end_date="2024-01-31",
            capital=100000.0,
            background_tasks=background_tasks
        )

        print(f"✅ Job submitted successfully with ID: {job_id}")

        # Check if Redis was used or fallback was triggered
        if redis_manager.is_available:
            print("✅ Redis was used for job submission")
        else:
            print("✅ Fallback to FastAPI BackgroundTasks was used")

    except Exception as e:
        print(f"❌ Job submission failed: {e}")
        return False

    return True


async def main():
    """Main test function."""
    print("Starting Redis and fallback tests...\n")

    # Test Redis connection
    redis_ok, celery_ok = await test_redis_connection()

    # Test job submission fallback
    job_ok = await test_job_submission_fallback()

    print("\n=== Final Results ===")
    print(f"Redis connection: {'✅ PASS' if redis_ok else '❌ FAIL'}")
    print(f"Celery availability: {'✅ PASS' if celery_ok else '❌ FAIL'}")
    print(f"Job submission fallback: {'✅ PASS' if job_ok else '❌ FAIL'}")

    if redis_ok and celery_ok and job_ok:
        print("\n🎉 All tests passed! Redis fallback system is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the configuration.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)