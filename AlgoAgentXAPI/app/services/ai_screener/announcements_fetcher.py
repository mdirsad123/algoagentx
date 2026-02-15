import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ..ai_screener_service import AIScreenerError
from ...db.models import ScreenerAnnouncements, ScreenerRuns
from ...core.config import settings
from ...schemas.screener import ScreenerAnnouncementsCreate

logger = logging.getLogger(__name__)


class AnnouncementsFetcher:
    """Fetches and normalizes announcements from NSE/BSE with retry/backoff and health monitoring"""
    
    def __init__(self):
        self.session = None
        self.base_urls = {
            'nse': 'https://www.nseindia.com',
            'bse': 'https://www.bseindia.com'
        }
        # Source health tracking
        self.source_health = {source: {'success_count': 0, 'failure_count': 0, 'last_error': None} for source in self.base_urls.keys()}
        self.max_retries = 3
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
            timeout=self.timeout
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _log_source_health(self, source: str, success: bool, error: Optional[str] = None):
        """Log source health for monitoring"""
        if success:
            self.source_health[source]['success_count'] += 1
            self.source_health[source]['last_error'] = None
            logger.info(f"Announcements source {source} health: SUCCESS (total: {self.source_health[source]['success_count']})")
        else:
            self.source_health[source]['failure_count'] += 1
            self.source_health[source]['last_error'] = error
            logger.warning(f"Announcements source {source} health: FAILED (total: {self.source_health[source]['failure_count']}, last_error: {error})")
    
    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
 reraise=True
    )
    async def _fetch_with_retry(self, url: str, source: str) -> str:
        """Fetch URL with retry logic and timeout"""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"HTTP {response.status} for {url}"
                    )
                return await response.text()
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout error fetching {url}: {e}")
            self._log_source_health(source, False, f"Timeout: {e}")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"Client error fetching {url}: {e}")
            self._log_source_health(source, False, f"ClientError: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            self._log_source_health(source, False, f"Unexpected: {e}")
            raise
    
    async def fetch_nse_announcements(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch announcements from NSE for a specific symbol with retry and health monitoring"""
        try:
            # NSE announcements URL pattern
            url = f"{self.base_urls['nse']}/company-announcements?symbol={symbol}"
            
            html = await self._fetch_with_retry(url, 'nse')
            soup = BeautifulSoup(html, 'html.parser')
            
            # Parse announcements
            announcements = []
            announcement_containers = soup.find_all('div', class_='announcements')
            
            for container in announcement_containers[:limit]:
                try:
                    title_elem = container.find('h3')
                    date_elem = container.find('span', class_='date')
                    category_elem = container.find('span', class_='category')
                    
                    if title_elem and date_elem:
                        announcement = {
                            'title': title_elem.get_text(strip=True),
                            'url': title_elem.find('a')['href'] if title_elem.find('a') else None,
                            'category': category_elem.get_text(strip=True) if category_elem else None,
                            'announce_date': self._parse_date(date_elem.get_text(strip=True)),
                            'exchange': 'NSE',
                            'symbol': symbol,
                            'stock_name': symbol  # Will be updated later
                        }
                        announcements.append(announcement)
                except Exception as e:
                    logger.error(f"Error parsing NSE announcement: {e}")
                    continue
            
            self._log_source_health('nse', True)
            return announcements
            
        except Exception as e:
            logger.error(f"Error fetching NSE announcements for {symbol}: {e}")
            return []
    
    async def fetch_bse_announcements(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch announcements from BSE for a specific symbol"""
        try:
            # BSE announcements URL pattern
            url = f"{self.base_urls['bse']}/stock-share-price/SiteSearch.aspx?CompanySearch={symbol}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"BSE request failed for {symbol}: {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Parse announcements
                announcements = []
                announcement_containers = soup.find_all('div', class_='announcement-item')
                
                for container in announcement_containers[:limit]:
                    try:
                        title_elem = container.find('h3')
                        date_elem = container.find('span', class_='date')
                        category_elem = container.find('span', class_='category')
                        
                        if title_elem and date_elem:
                            announcement = {
                                'title': title_elem.get_text(strip=True),
                                'url': title_elem.find('a')['href'] if title_elem.find('a') else None,
                                'category': category_elem.get_text(strip=True) if category_elem else None,
                                'announce_date': self._parse_date(date_elem.get_text(strip=True)),
                                'exchange': 'BSE',
                                'symbol': symbol,
                                'stock_name': symbol  # Will be updated later
                            }
                            announcements.append(announcement)
                    except Exception as e:
                        logger.error(f"Error parsing BSE announcement: {e}")
                        continue
                
                return announcements
                
        except Exception as e:
            logger.error(f"Error fetching BSE announcements for {symbol}: {e}")
            return []
    
    def _parse_date(self, date_str: str) -> datetime.date:
        """Parse date string into date object"""
        try:
            # Handle various date formats
            if 'ago' in date_str.lower():
                return datetime.now().date()
            elif 'today' in date_str.lower():
                return datetime.now().date()
            elif 'yesterday' in date_str.lower():
                return datetime.now().date() - timedelta(days=1)
            else:
                # Try to parse as standard date format
                for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']:
                    try:
                        return datetime.strptime(date_str, fmt).date()
                    except ValueError:
                        continue
                
                # Default to today if parsing fails
                return datetime.now().date()
        except Exception:
            return datetime.now().date()
    
    async def fetch_all_exchanges(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch announcements from all exchanges"""
        if not settings.AI_SCREENER_ENABLED:
            logger.info("AI Screener is disabled")
            return []
        
        tasks = [
            self.fetch_nse_announcements(symbol, limit),
            self.fetch_bse_announcements(symbol, limit)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_announcements = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching from exchange {i}: {result}")
                continue
            all_announcements.extend(result)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_announcements = []
        for announcement in all_announcements:
            if announcement.get('url') and announcement['url'] not in seen_urls:
                seen_urls.add(announcement['url'])
                unique_announcements.append(announcement)
        
        # Sort by date (newest first)
        unique_announcements.sort(key=lambda x: x.get('announce_date', datetime.now().date()), reverse=True)
        
        return unique_announcements[:limit]


class AnnouncementsFetcherService:
    """Service for fetching and normalizing announcements data"""
    
    def __init__(self):
        self.fetcher = AnnouncementsFetcher()
    
    async def fetch_and_normalize_announcements(self, symbols: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch and normalize announcements for multiple symbols"""
        all_announcements = []
        
        async with self.fetcher as fetcher:
            tasks = [fetcher.fetch_all_exchanges(symbol, limit) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching announcements for symbol {symbols[i]}: {result}")
                    continue
                all_announcements.extend(result)
        
        return all_announcements
