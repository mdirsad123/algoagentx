#!/usr/bin/env python3
"""
Test script to verify AI Screener modules can be imported and instantiated
in a FastAPI container environment.
"""

import sys
import os
import asyncio
import logging

# Add the AlgoAgentXAPI directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AlgoAgentXAPI'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all AI Screener modules can be imported successfully."""
    logger.info("Testing AI Screener module imports...")
    
    try:
        # Test core modules
        from app.services.ai_screener.news_fetcher import NewsFetcher, NewsFetcherService
        logger.info("✓ NewsFetcher modules imported successfully")
        
        from app.services.ai_screener.announcements_fetcher import AnnouncementsFetcher, AnnouncementsFetcherService
        logger.info("✓ AnnouncementsFetcher modules imported successfully")
        
        from app.services.ai_screener.sentiment_engine import SentimentEngine, SentimentEngineService
        logger.info("✓ SentimentEngine modules imported successfully")
        
        from app.services.ai_screener.storage import StorageService, StorageServiceFactory
        logger.info("✓ StorageService modules imported successfully")
        
        # Test configuration
        from app.core.config import settings
        logger.info("✓ Configuration imported successfully")
        logger.info(f"  - AI Screener Enabled: {settings.ai_screener_enabled}")
        logger.info(f"  - AI Screener Sources: {settings.ai_screener_sources_list}")
        logger.info(f"  - AI Screener Top N: {settings.ai_screener_top_n}")
        
        return True
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during import: {e}")
        return False

def test_instantiation():
    """Test that modules can be instantiated without errors."""
    logger.info("Testing module instantiation...")
    
    try:
        from app.services.ai_screener.news_fetcher import NewsFetcher, NewsFetcherService
        from app.services.ai_screener.announcements_fetcher import AnnouncementsFetcher, AnnouncementsFetcherService
        from app.services.ai_screener.sentiment_engine import SentimentEngine, SentimentEngineService
        from app.services.ai_screener.storage import StorageService, StorageServiceFactory
        
        # Test service instantiation
        news_fetcher_service = NewsFetcherService()
        logger.info("✓ NewsFetcherService instantiated successfully")
        
        announcements_fetcher_service = AnnouncementsFetcherService()
        logger.info("✓ AnnouncementsFetcherService instantiated successfully")
        
        sentiment_engine_service = SentimentEngineService()
        logger.info("✓ SentimentEngineService instantiated successfully")
        
        # Test engine instantiation
        sentiment_engine = SentimentEngine()
        logger.info("✓ SentimentEngine instantiated successfully")
        
        # Test fetcher instantiation (without context manager)
        news_fetcher = NewsFetcher()
        logger.info("✓ NewsFetcher instantiated successfully")
        
        announcements_fetcher = AnnouncementsFetcher()
        logger.info("✓ AnnouncementsFetcher instantiated successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during instantiation: {e}")
        return False

def test_config_validation():
    """Test configuration validation methods."""
    logger.info("Testing configuration validation...")
    
    try:
        from app.core.config import settings
        
        # Test AI screener validation
        settings.validate_ai_screener_requirements()
        logger.info("✓ AI Screener configuration validation passed")
        
        # Test environment detection
        logger.info(f"✓ Environment detection: development={settings.is_development}, production={settings.is_production}, staging={settings.is_staging}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during config validation: {e}")
        return False

async def test_async_context_managers():
    """Test that async context managers work correctly."""
    logger.info("Testing async context managers...")
    
    try:
        from app.services.ai_screener.news_fetcher import NewsFetcher
        from app.services.ai_screener.announcements_fetcher import AnnouncementsFetcher
        
        # Test NewsFetcher context manager
        async with NewsFetcher() as news_fetcher:
            logger.info("✓ NewsFetcher async context manager works")
        
        # Test AnnouncementsFetcher context manager
        async with AnnouncementsFetcher() as announcements_fetcher:
            logger.info("✓ AnnouncementsFetcher async context manager works")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during async context manager test: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("Starting AI Screener module tests...")
    
    tests_passed = 0
    total_tests = 4
    
    # Test imports
    if test_imports():
        tests_passed += 1
    
    # Test instantiation
    if test_instantiation():
        tests_passed += 1
    
    # Test config validation
    if test_config_validation():
        tests_passed += 1
    
    # Test async context managers
    if asyncio.run(test_async_context_managers()):
        tests_passed += 1
    
    # Summary
    logger.info(f"Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        logger.info("🎉 All tests passed! AI Screener modules are ready for FastAPI container environment.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())