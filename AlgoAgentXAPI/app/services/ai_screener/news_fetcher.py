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
from ...db.models import ScreenerNews, ScreenerRuns
from ...core.config import settings
from ...schemas.screener import ScreenerNewsCreate

logger = logging.getLogger(__name__)


class NewsFetcher:
    """Fetches and normalizes news data from various sources with retry/backoff and health monitoring"""
    
    def __init__(self):
        self.session = None
        self.base_urls = {
            'moneycontrol': 'https://www.moneycontrol.com',
            'economic_times': 'https://economictimes.indiatimes.com',
            'livemint': 'https://www.livemint.com',
            'business_standard': 'https://www.business-standard.com'
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
            logger.info(f"News source {source} health: SUCCESS (total: {self.source_health[source]['success_count']})")
        else:
            self.source_health[source]['failure_count'] += 1
            self.source_health[source]['last_error'] = error
            logger.warning(f"News source {source} health: FAILED (total: {self.source_health[source]['failure_count']}, last_error: {error})")
    
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
    
    async def fetch_moneycontrol_news(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch news from Moneycontrol for a specific symbol with retry and health monitoring"""
        try:
            # Moneycontrol news URL pattern
            url = f"{self.base_urls['moneycontrol']}/news/newsbypeal/{symbol.lower()}"
            
            html = await self._fetch_with_retry(url, 'moneycontrol')
            soup = BeautifulSoup(html, 'html.parser')
            
            # Parse news items
            news_items = []
            news_containers = soup.find_all('div', class_='news_list')
            
            for container in news_containers[:limit]:
                try:
                    title_elem = container.find('h2')
                    date_elem = container.find('span', class_='newsbyline')
                    summary_elem = container.find('p')
                    
                    if title_elem and date_elem:
                        news_item = {
                            'title': title_elem.get_text(strip=True),
                            'summary': summary_elem.get_text(strip=True) if summary_elem else None,
                            'url': title_elem.find('a')['href'] if title_elem.find('a') else None,
                            'source': 'Moneycontrol',
                            'news_date': self._parse_date(date_elem.get_text(strip=True)),
                            'symbol': symbol,
                            'stock_name': symbol  # Will be updated later
                        }
                        news_items.append(news_item)
                except Exception as e:
                    logger.error(f"Error parsing Moneycontrol news item: {e}")
                    continue
            
            self._log_source_health('moneycontrol', True)
            return news_items
            
        except Exception as e:
            logger.error(f"Error fetching Moneycontrol news for {symbol}: {e}")
            return []
    
    async def fetch_economic_times_news(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch news from Economic Times for a specific symbol"""
        try:
            # Economic Times search URL
            search_url = f"{self.base_urls['economic_times']}/searchresult.cms?curpg=1&searchtype=1&query={symbol}"
            
            async with self.session.get(search_url) as response:
                if response.status != 200:
                    logger.warning(f"Economic Times request failed for {symbol}: {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Parse news items
                news_items = []
                news_containers = soup.find_all('div', class_='eachStory')
                
                for container in news_containers[:limit]:
                    try:
                        title_elem = container.find('h3')
                        date_elem = container.find('time')
                        summary_elem = container.find('p')
                        
                        if title_elem and date_elem:
                            news_item = {
                                'title': title_elem.get_text(strip=True),
                                'summary': summary_elem.get_text(strip=True) if summary_elem else None,
                                'url': title_elem.find('a')['href'] if title_elem.find('a') else None,
                                'source': 'Economic Times',
                                'news_date': self._parse_date(date_elem.get_text(strip=True)),
                                'symbol': symbol,
                                'stock_name': symbol  # Will be updated later
                            }
                            news_items.append(news_item)
                    except Exception as e:
                        logger.error(f"Error parsing Economic Times news item: {e}")
                        continue
                
                return news_items
                
        except Exception as e:
            logger.error(f"Error fetching Economic Times news for {symbol}: {e}")
            return []
    
    async def fetch_livemint_news(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch news from Livemint for a specific symbol"""
        try:
            # Livemint search URL
            search_url = f"{self.base_urls['livemint']}/search?q={symbol}"
            
            async with self.session.get(search_url) as response:
                if response.status != 200:
                    logger.warning(f"Livemint request failed for {symbol}: {response.status}")
                    return []
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Parse news items
                news_items = []
                news_containers = soup.find_all('div', class_='story-card')
                
                for container in news_containers[:limit]:
                    try:
                        title_elem = container.find('h2')
                        date_elem = container.find('time')
                        summary_elem = container.find('p')
                        
                        if title_elem and date_elem:
                            news_item = {
                                'title': title_elem.get_text(strip=True),
                                'summary': summary_elem.get_text(strip=True) if summary_elem else None,
                                'url': title_elem.find('a')['href'] if title_elem.find('a') else None,
                                'source': 'Livemint',
                                'news_date': self._parse_date(date_elem.get_text(strip=True)),
                                'symbol': symbol,
                                'stock_name': symbol  # Will be updated later
                            }
                            news_items.append(news_item)
                    except Exception as e:
                        logger.error(f"Error parsing Livemint news item: {e}")
                        continue
                
                return news_items
                
        except Exception as e:
            logger.error(f"Error fetching Livemint news for {symbol}: {e}")
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
    
    async def fetch_all_sources(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch news from all configured sources"""
        if not settings.AI_SCREENER_ENABLED:
            logger.info("AI Screener is disabled")
            return []
        
        tasks = [
            self.fetch_moneycontrol_news(symbol, limit),
            self.fetch_economic_times_news(symbol, limit),
            self.fetch_livemint_news(symbol, limit)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_news = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching from source {i}: {result}")
                continue
            all_news.extend(result)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_news = []
        for news in all_news:
            if news.get('url') and news['url'] not in seen_urls:
                seen_urls.add(news['url'])
                unique_news.append(news)
        
        # Sort by date (newest first)
        unique_news.sort(key=lambda x: x.get('news_date', datetime.now().date()), reverse=True)
        
        return unique_news[:limit]


class NewsFetcherService:
    """Service for fetching and normalizing news data"""
    
    def __init__(self):
        self.fetcher = NewsFetcher()
    
    async def fetch_and_normalize_news(self, symbols: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch and normalize news for multiple symbols"""
        all_news = []
        
        async with self.fetcher as fetcher:
            tasks = [fetcher.fetch_all_sources(symbol, limit) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching news for symbol {symbols[i]}: {result}")
                    continue
                all_news.extend(result)
        
        return all_news
