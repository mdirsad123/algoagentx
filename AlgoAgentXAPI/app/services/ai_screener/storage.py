import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert, delete, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from uuid import uuid4
from ...db.models import ScreenerNews, ScreenerAnnouncements, ScreenerRuns
from ...core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Service for storing AI screener results in database with improved duplicate prevention and error handling"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_screener_run(self, run_type: str, status: str = "RUNNING", meta: Optional[Dict] = None) -> str:
        """Create a new screener run record with error resilience"""
        try:
            run_id = str(uuid4())
            
            run_data = {
                'id': run_id,
                'run_type': run_type,
                'status': status,
                'started_at': datetime.utcnow(),
                'meta': meta or {}
            }
            
            await self.db.execute(
                insert(ScreenerRuns).values(**run_data)
            )
            await self.db.commit()
            
            logger.info(f"Created screener run {run_id} for {run_type}")
            return run_id
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error creating screener run: {e}")
            raise Exception(f"Failed to create screener run: {e}")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Unexpected error creating screener run: {e}")
            raise Exception(f"Failed to create screener run: {e}")
    
    async def store_news_items_with_duplicate_prevention(self, news_items: List[Dict[str, Any]], run_id: Optional[str] = None) -> int:
        """Store news items with improved duplicate prevention using unique constraints"""
        if not news_items:
            return 0
        
        stored_count = 0
        failed_count = 0
        
        for news in news_items:
            try:
                # Use INSERT ... ON CONFLICT DO UPDATE for PostgreSQL
                # This leverages the unique constraint we added
                news_data = {
                    'symbol': news['symbol'],
                    'stock_name': news['stock_name'],
                    'news_date': news['news_date'],
                    'title': news['title'],
                    'summary': news.get('summary'),
                    'url': news['url'],
                    'source': news['source'],
                    'sentiment_label': news['sentiment_label'],
                    'sentiment_score': news['sentiment_score'],
                    'confidence': news.get('confidence')
                }
                
                # Try to insert, update on conflict
                stmt = insert(ScreenerNews).values(**news_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['symbol', 'news_date', 'title'],
                    set_={
                        'summary': stmt.excluded.summary,
                        'sentiment_label': stmt.excluded.sentiment_label,
                        'sentiment_score': stmt.excluded.sentiment_score,
                        'confidence': stmt.excluded.confidence,
                        'stock_name': stmt.excluded.stock_name
                    }
                )
                
                await self.db.execute(stmt)
                stored_count += 1
                
            except IntegrityError as e:
                # This should not happen with ON CONFLICT, but handle it gracefully
                logger.warning(f"Duplicate news item detected (should be handled by ON CONFLICT): {news.get('url', 'unknown')}")
                stored_count += 1  # Count as stored since it already exists
            except SQLAlchemyError as e:
                logger.error(f"Database error storing news item {news.get('url', 'unknown')}: {e}")
                failed_count += 1
                continue  # Continue with next item
            except Exception as e:
                logger.error(f"Unexpected error storing news item {news.get('url', 'unknown')}: {e}")
                failed_count += 1
                continue  # Continue with next item
        
        try:
            await self.db.commit()
            logger.info(f"Stored {stored_count} news items (failed: {failed_count})")
            return stored_count
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error committing news items: {e}")
            raise Exception(f"Failed to store news items: {e}")
    
    async def update_screener_run_status(self, run_id: str, status: str, finished_at: Optional[datetime] = None, error: Optional[str] = None) -> None:
        """Update screener run status"""
        try:
            update_data = {
                'status': status,
                'finished_at': finished_at or datetime.utcnow()
            }
            
            if error:
                update_data['error'] = error
            
            await self.db.execute(
                update(ScreenerRuns)
                .where(ScreenerRuns.id == run_id)
                .values(**update_data)
            )
            await self.db.commit()
            
            logger.info(f"Updated screener run {run_id} status to {status}")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating screener run status: {e}")
            raise Exception(f"Failed to update screener run status: {e}")
    
    async def store_news_items(self, news_items: List[Dict[str, Any]], run_id: Optional[str] = None) -> int:
        """Store news items in database"""
        if not news_items:
            return 0
        
        try:
            stored_count = 0
            
            for news in news_items:
                try:
                    # Check if news already exists (based on URL)
                    existing = await self.db.execute(
                        select(ScreenerNews).where(ScreenerNews.url == news['url'])
                    )
                    existing_news = existing.scalar_one_or_none()
                    
                    if existing_news:
                        # Update existing news
                        await self.db.execute(
                            update(ScreenerNews)
                            .where(ScreenerNews.id == existing_news.id)
                            .values(
                                title=news['title'],
                                summary=news.get('summary'),
                                sentiment_label=news['sentiment_label'],
                                sentiment_score=news['sentiment_score'],
                                confidence=news.get('confidence'),
                                news_date=news['news_date']
                            )
                        )
                    else:
                        # Insert new news
                        news_data = {
                            'symbol': news['symbol'],
                            'stock_name': news['stock_name'],
                            'news_date': news['news_date'],
                            'title': news['title'],
                            'summary': news.get('summary'),
                            'url': news['url'],
                            'source': news['source'],
                            'sentiment_label': news['sentiment_label'],
                            'sentiment_score': news['sentiment_score'],
                            'confidence': news.get('confidence')
                        }
                        
                        await self.db.execute(
                            insert(ScreenerNews).values(**news_data)
                        )
                    
                    stored_count += 1
                    
                except Exception as e:
                    logger.error(f"Error storing news item {news.get('url', 'unknown')}: {e}")
                    continue  # Continue with next item
            
            await self.db.commit()
            
            logger.info(f"Stored {stored_count} news items")
            return stored_count
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error storing news items: {e}")
            raise Exception(f"Failed to store news items: {e}")
    
    async def store_announcements(self, announcements: List[Dict[str, Any]], run_id: Optional[str] = None) -> int:
        """Store announcements in database"""
        if not announcements:
            return 0
        
        try:
            stored_count = 0
            
            for announcement in announcements:
                try:
                    # Check if announcement already exists (based on URL)
                    existing = await self.db.execute(
                        select(ScreenerAnnouncements).where(ScreenerAnnouncements.url == announcement['url'])
                    )
                    existing_announcement = existing.scalar_one_or_none()
                    
                    if existing_announcement:
                        # Update existing announcement
                        await self.db.execute(
                            update(ScreenerAnnouncements)
                            .where(ScreenerAnnouncements.id == existing_announcement.id)
                            .values(
                                title=announcement['title'],
                                category=announcement.get('category'),
                                announce_date=announcement['announce_date']
                            )
                        )
                    else:
                        # Insert new announcement
                        announcement_data = {
                            'symbol': announcement['symbol'],
                            'stock_name': announcement['stock_name'],
                            'exchange': announcement['exchange'],
                            'announce_date': announcement['announce_date'],
                            'title': announcement['title'],
                            'url': announcement['url'],
                            'category': announcement.get('category')
                        }
                        
                        await self.db.execute(
                            insert(ScreenerAnnouncements).values(**announcement_data)
                        )
                    
                    stored_count += 1
                    
                except Exception as e:
                    logger.error(f"Error storing announcement {announcement.get('url', 'unknown')}: {e}")
                    continue  # Continue with next item
            
            await self.db.commit()
            
            logger.info(f"Stored {stored_count} announcements")
            return stored_count
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error storing announcements: {e}")
            raise Exception(f"Failed to store announcements: {e}")
    
    async def get_latest_news(self, symbol: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get latest news items"""
        try:
            query = select(ScreenerNews)
            
            if symbol:
                query = query.where(ScreenerNews.symbol == symbol)
            
            query = query.order_by(ScreenerNews.news_date.desc()).limit(limit)
            
            result = await self.db.execute(query)
            news_items = result.scalars().all()
            
            return [
                {
                    'id': str(news.id),
                    'symbol': news.symbol,
                    'stock_name': news.stock_name,
                    'news_date': news.news_date,
                    'title': news.title,
                    'summary': news.summary,
                    'url': news.url,
                    'source': news.source,
                    'sentiment_label': news.sentiment_label,
                    'sentiment_score': news.sentiment_score,
                    'confidence': news.confidence,
                    'created_at': news.created_at
                }
                for news in news_items
            ]
            
        except Exception as e:
            logger.error(f"Error getting latest news: {e}")
            return []
    
    async def get_latest_announcements(self, symbol: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get latest announcements"""
        try:
            query = select(ScreenerAnnouncements)
            
            if symbol:
                query = query.where(ScreenerAnnouncements.symbol == symbol)
            
            query = query.order_by(ScreenerAnnouncements.announce_date.desc()).limit(limit)
            
            result = await self.db.execute(query)
            announcements = result.scalars().all()
            
            return [
                {
                    'id': str(announcement.id),
                    'symbol': announcement.symbol,
                    'stock_name': announcement.stock_name,
                    'exchange': announcement.exchange,
                    'announce_date': announcement.announce_date,
                    'title': announcement.title,
                    'url': announcement.url,
                    'category': announcement.category,
                    'created_at': announcement.created_at
                }
                for announcement in announcements
            ]
            
        except Exception as e:
            logger.error(f"Error getting latest announcements: {e}")
            return []
    
    async def cleanup_old_data(self, days_to_keep: int = 30) -> None:
        """Clean up old screener data"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Delete old news
            await self.db.execute(
                delete(ScreenerNews).where(ScreenerNews.created_at < cutoff_date)
            )
            
            # Delete old announcements
            await self.db.execute(
                delete(ScreenerAnnouncements).where(ScreenerAnnouncements.created_at < cutoff_date)
            )
            
            # Delete old runs
            await self.db.execute(
                delete(ScreenerRuns).where(ScreenerRuns.started_at < cutoff_date)
            )
            
            await self.db.commit()
            
            logger.info(f"Cleaned up screener data older than {days_to_keep} days")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error cleaning up old data: {e}")


class StorageServiceFactory:
    """Factory for creating storage service instances"""
    
    @staticmethod
    def create_storage_service(db: AsyncSession) -> StorageService:
        """Create and return a storage service instance"""
        return StorageService(db)
