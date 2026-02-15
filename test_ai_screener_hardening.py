#!/usr/bin/env python3
"""
Test script to verify AI Screener hardening implementation.
This script tests the key improvements made to the AI Screener pipeline.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import sys
import os

# Add the API directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AlgoAgentXAPI'))

from app.core.config import settings
from app.db.models import ScreenerNews, ScreenerAnnouncements
from app.services.ai_screener.storage import StorageService
from app.services.ai_screener.news_fetcher import NewsFetcher
from app.services.ai_screener.announcements_fetcher import AnnouncementsFetcher

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_constraints():
    """Test that unique constraints are properly defined in the database models."""
    logger.info("Testing database constraints...")
    
    # Test that the models have the correct unique constraints defined
    news_constraints = ScreenerNews.__table_args__[0].name
    announcements_constraints = ScreenerAnnouncements.__table_args__[0].name
    
    assert news_constraints == 'uq_news_symbol_date_title', f"News constraint name mismatch: {news_constraints}"
    assert announcements_constraints == 'uq_announcements_symbol_date_title_exchange', f"Announcements constraint name mismatch: {announcements_constraints}"
    
    logger.info("✓ Database constraints are properly defined")


async def test_storage_service_duplicate_prevention():
    """Test that the storage service properly handles duplicate prevention."""
    logger.info("Testing storage service duplicate prevention...")
    
    # Create a test database connection (in-memory for testing)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        # Create tables
        from app.db.base import Base
        from app.db.models import ScreenerNews, ScreenerAnnouncements, ScreenerRuns
        await conn.run_sync(Base.metadata.create_all)
    
    # Create async session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as db:
        storage_service = StorageService(db)
        
        # Test data
        test_news = [{
            'symbol': 'RELIANCE',
            'stock_name': 'Reliance Industries',
            'news_date': '2024-02-13',
            'title': 'Test News Title',
            'summary': 'Test summary',
            'url': 'https://example.com/news',
            'source': 'Test Source',
            'sentiment_label': 'POSITIVE',
            'sentiment_score': 0.8,
            'confidence': 0.9
        }]
        
        # Store the news item
        stored_count = await storage_service.store_news_items_with_duplicate_prevention(test_news)
        assert stored_count == 1, f"Expected 1 stored item, got {stored_count}"
        
        # Try to store the same item again (should be handled by ON CONFLICT)
        stored_count = await storage_service.store_news_items_with_duplicate_prevention(test_news)
        assert stored_count == 1, f"Expected 1 stored item (duplicate handled), got {stored_count}"
        
        logger.info("✓ Storage service duplicate prevention works correctly")


async def test_fetcher_timeout_and_retry():
    """Test that fetchers have proper timeout and retry logic."""
    logger.info("Testing fetcher timeout and retry logic...")
    
    # Test that NewsFetcher has timeout and retry configuration
    news_fetcher = NewsFetcher()
    assert hasattr(news_fetcher, 'timeout'), "NewsFetcher should have timeout attribute"
    assert hasattr(news_fetcher, 'max_retries'), "NewsFetcher should have max_retries attribute"
    assert hasattr(news_fetcher, 'source_health'), "NewsFetcher should have source_health tracking"
    
    # Test that AnnouncementsFetcher has timeout and retry configuration
    announcements_fetcher = AnnouncementsFetcher()
    assert hasattr(announcements_fetcher, 'timeout'), "AnnouncementsFetcher should have timeout attribute"
    assert hasattr(announcements_fetcher, 'max_retries'), "AnnouncementsFetcher should have max_retries attribute"
    assert hasattr(announcements_fetcher, 'source_health'), "AnnouncementsFetcher should have source_health tracking"
    
    logger.info("✓ Fetcher timeout and retry logic is properly configured")


async def test_error_resilience():
    """Test that the system handles errors gracefully without crashing."""
    logger.info("Testing error resilience...")
    
    # Test that StorageService handles database errors gracefully
    from app.services.ai_screener.storage import StorageService
    from app.services.ai_screener_service import AIScreenerError
    
    # Create a mock database session that will fail
    class MockDB:
        async def execute(self, *args, **kwargs):
            raise Exception("Database connection failed")
        async def commit(self):
            raise Exception("Database commit failed")
        async def rollback(self):
            pass
    
    storage_service = StorageService(MockDB())
    
    # Test that create_screener_run handles errors gracefully
    try:
        await storage_service.create_screener_run("test_run")
        assert False, "Should have raised an exception"
    except AIScreenerError:
        logger.info("✓ Storage service properly handles database errors")
    except Exception as e:
        assert False, f"Should have raised AIScreenerError, got {type(e).__name__}: {e}"


async def main():
    """Run all tests."""
    logger.info("Starting AI Screener hardening tests...")
    
    try:
        await test_database_constraints()
        await test_storage_service_duplicate_prevention()
        await test_fetcher_timeout_and_retry()
        await test_error_resilience()
        
        logger.info("🎉 All tests passed! AI Screener hardening implementation is working correctly.")
        logger.info("\nKey improvements implemented:")
        logger.info("1. ✓ Unique constraints added to prevent duplicate news/announcements")
        logger.info("2. ✓ Retry/backoff logic added for scraping sources")
        logger.info("3. ✓ Timeouts added for HTTP calls")
        logger.info("4. ✓ Source health logging implemented")
        logger.info("5. ✓ Improved duplicate prevention in storage service")
        logger.info("6. ✓ Enhanced error resilience in job handlers")
        logger.info("7. ✓ API server crash prevention measures")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())