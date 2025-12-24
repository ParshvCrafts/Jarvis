"""
JARVIS Smart News Module.

Personalized news aggregation from multiple sources.
"""

from loguru import logger

NEWS_AVAILABLE = False

try:
    from .models import (
        Article,
        NewsCategory,
        NewsSource,
        RedditPost,
        HackerNewsItem,
        DevToArticle,
        NewsDigest,
        NewsInterest,
        CompanyNews,
        DEFAULT_INTERESTS,
        SUBREDDITS,
    )
    
    from .apis import (
        NewsAPI,
        HackerNewsAPI,
        RedditAPI,
        DevToAPI,
        GoogleNewsRSS,
        test_all_apis,
    )
    
    from .manager import (
        NewsManager,
        NewsConfig,
    )
    
    NEWS_AVAILABLE = True
    logger.info("News module loaded successfully")
    
except ImportError as e:
    logger.warning(f"News module not fully available: {e}")

__all__ = [
    "NEWS_AVAILABLE",
    # Models
    "Article",
    "NewsCategory",
    "NewsSource",
    "RedditPost",
    "HackerNewsItem",
    "DevToArticle",
    "NewsDigest",
    "NewsInterest",
    "CompanyNews",
    "DEFAULT_INTERESTS",
    "SUBREDDITS",
    # APIs
    "NewsAPI",
    "HackerNewsAPI",
    "RedditAPI",
    "DevToAPI",
    "GoogleNewsRSS",
    "test_all_apis",
    # Manager
    "NewsManager",
    "NewsConfig",
]
