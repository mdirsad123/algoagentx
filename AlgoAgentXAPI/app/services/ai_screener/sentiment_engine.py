import logging
from typing import List, Dict, Optional, Any
from ...core.config import settings

logger = logging.getLogger(__name__)


class SentimentEngine:
    """Simple sentiment analysis engine for news and announcements"""
    
    def __init__(self):
        # Simple keyword-based sentiment analysis
        self.positive_words = {
            'buy', 'bullish', 'up', 'increase', 'growth', 'profit', 'win', 'success', 
            'positive', 'strong', 'good', 'great', 'excellent', 'outperform', 'upgrade',
            'acquire', 'expand', 'launch', 'partnership', 'deal', 'contract'
        }
        self.negative_words = {
            'sell', 'bearish', 'down', 'decrease', 'loss', 'drop', 'fall', 'decline',
            'negative', 'weak', 'bad', 'poor', 'miss', 'downgrade', 'cut', 'warn',
            'cancel', 'suspend', 'delay', 'problem', 'issue', 'risk'
        }
    
    def analyze_text_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text using keyword-based approach
        Returns: {
            'sentiment_label': str,
            'sentiment_score': float,
            'confidence': float
        }
        """
        if not text or not text.strip():
            return {
                'sentiment_label': 'NEUTRAL',
                'sentiment_score': 0.0,
                'confidence': 0.5
            }
        
        # Convert to lowercase for analysis
        text_lower = text.lower()
        words = text_lower.split()
        
        # Count positive and negative words
        positive_count = sum(1 for word in words if word in self.positive_words)
        negative_count = sum(1 for word in words if word in self.negative_words)
        
        # Calculate sentiment score (-1 to 1)
        total_sentiment_words = positive_count + negative_count
        if total_sentiment_words == 0:
            score = 0.0
            confidence = 0.1  # Low confidence for neutral text
        else:
            score = (positive_count - negative_count) / total_sentiment_words
            confidence = min(1.0, total_sentiment_words / 10.0)  # Confidence based on number of sentiment words
        
        # Determine sentiment label
        sentiment_label = self._get_sentiment_label(score)
        
        return {
            'sentiment_label': sentiment_label,
            'sentiment_score': round(score, 4),
            'confidence': round(confidence, 4)
        }
    
    def _get_sentiment_label(self, score: float) -> str:
        """Convert sentiment score to label"""
        if score >= 0.6:
            return 'VERY_POSITIVE'
        elif score >= 0.2:
            return 'POSITIVE'
        elif score >= -0.2:
            return 'NEUTRAL'
        elif score >= -0.6:
            return 'NEGATIVE'
        else:
            return 'VERY_NEGATIVE'
    
    def analyze_news_sentiment(self, news_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze sentiment for a list of news items"""
        if not settings.AI_SCREENER_ENABLED:
            logger.info("AI Screener is disabled")
            return news_items
        
        analyzed_news = []
        
        for news in news_items:
            try:
                # Combine title and summary for analysis
                text_to_analyze = news.get('title', '')
                if news.get('summary'):
                    text_to_analyze += ' ' + news['summary']
                
                sentiment_result = self.analyze_text_sentiment(text_to_analyze)
                
                # Add sentiment analysis to news item
                analyzed_news_item = {
                    **news,
                    **sentiment_result
                }
                
                analyzed_news.append(analyzed_news_item)
                
            except Exception as e:
                logger.error(f"Error analyzing sentiment for news: {e}")
                # Add neutral sentiment if analysis fails
                analyzed_news_item = {
                    **news,
                    'sentiment_label': 'NEUTRAL',
                    'sentiment_score': 0.0,
                    'confidence': 0.0
                }
                analyzed_news.append(analyzed_news_item)
        
        return analyzed_news
    
    def analyze_announcement_sentiment(self, announcements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze sentiment for a list of announcements"""
        if not settings.AI_SCREENER_ENABLED:
            logger.info("AI Screener is disabled")
            return announcements
        
        analyzed_announcements = []
        
        for announcement in announcements:
            try:
                # Use title for analysis
                text_to_analyze = announcement.get('title', '')
                
                sentiment_result = self.analyze_text_sentiment(text_to_analyze)
                
                # Add sentiment analysis to announcement
                analyzed_announcement = {
                    **announcement,
                    **sentiment_result
                }
                
                analyzed_announcements.append(analyzed_announcement)
                
            except Exception as e:
                logger.error(f"Error analyzing sentiment for announcement: {e}")
                # Add neutral sentiment if analysis fails
                analyzed_announcement = {
                    **announcement,
                    'sentiment_label': 'NEUTRAL',
                    'sentiment_score': 0.0,
                    'confidence': 0.0
                }
                analyzed_announcements.append(analyzed_announcement)
        
        return analyzed_announcements


class SentimentEngineService:
    """Service for sentiment analysis"""
    
    def __init__(self):
        self.engine = SentimentEngine()
    
    def analyze_news_sentiment(self, news_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze sentiment for news items"""
        return self.engine.analyze_news_sentiment(news_items)
    
    def analyze_announcement_sentiment(self, announcements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze sentiment for announcements"""
        return self.engine.analyze_announcement_sentiment(announcements)
