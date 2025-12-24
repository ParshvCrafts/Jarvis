"""
News API integrations for JARVIS Smart News Module.

Integrates with NewsAPI, HackerNews, Reddit, and Dev.to.
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from .models import (
    Article, NewsCategory, NewsSource,
    RedditPost, HackerNewsItem, DevToArticle,
    SUBREDDITS
)


class NewsAPI:
    """
    NewsAPI integration for headlines and articles.
    
    Free tier: 100 requests/day
    Docs: https://newsapi.org/docs
    """
    
    BASE_URL = "https://newsapi.org/v2"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("NEWS_API_KEY", "")
    
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)
    
    async def get_headlines(
        self,
        category: str = "technology",
        country: str = "us",
        query: Optional[str] = None,
        page_size: int = 10,
    ) -> List[Article]:
        """Get top headlines."""
        if not self.is_configured:
            logger.warning("NewsAPI not configured")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                params = {
                    "apiKey": self.api_key,
                    "category": category,
                    "country": country,
                    "pageSize": page_size,
                }
                
                if query:
                    params["q"] = query
                
                response = await client.get(
                    f"{self.BASE_URL}/top-headlines",
                    params=params,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_articles(data.get("articles", []))
                else:
                    logger.error(f"NewsAPI error: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"NewsAPI error: {e}")
            return []
    
    async def search(
        self,
        query: str,
        from_date: Optional[datetime] = None,
        sort_by: str = "relevancy",
        page_size: int = 10,
    ) -> List[Article]:
        """Search for articles."""
        if not self.is_configured:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                params = {
                    "apiKey": self.api_key,
                    "q": query,
                    "sortBy": sort_by,
                    "pageSize": page_size,
                    "language": "en",
                }
                
                if from_date:
                    params["from"] = from_date.isoformat()
                
                response = await client.get(
                    f"{self.BASE_URL}/everything",
                    params=params,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_articles(data.get("articles", []))
                
                return []
                
        except Exception as e:
            logger.error(f"NewsAPI search error: {e}")
            return []
    
    def _parse_articles(self, articles: List[Dict]) -> List[Article]:
        """Parse NewsAPI articles."""
        parsed = []
        
        for article in articles:
            try:
                published = None
                if article.get("publishedAt"):
                    published = datetime.fromisoformat(
                        article["publishedAt"].replace("Z", "+00:00")
                    )
                
                parsed.append(Article(
                    title=article.get("title", ""),
                    description=article.get("description", ""),
                    content=article.get("content", ""),
                    url=article.get("url", ""),
                    source=article.get("source", {}).get("name", ""),
                    source_type=NewsSource.NEWSAPI,
                    author=article.get("author"),
                    published_at=published,
                    image_url=article.get("urlToImage"),
                ))
            except Exception as e:
                logger.debug(f"Error parsing article: {e}")
                continue
        
        return parsed


class HackerNewsAPI:
    """
    Hacker News API integration.
    
    Free, no rate limit.
    Docs: https://github.com/HackerNews/API
    """
    
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    async def get_top_stories(self, limit: int = 20) -> List[Article]:
        """Get top stories from Hacker News."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Get top story IDs
                response = await client.get(f"{self.BASE_URL}/topstories.json")
                
                if response.status_code != 200:
                    return []
                
                story_ids = response.json()[:limit]
                
                # Fetch each story
                articles = []
                for story_id in story_ids:
                    item = await self._get_item(client, story_id)
                    if item:
                        articles.append(item.to_article())
                
                return articles
                
        except Exception as e:
            logger.error(f"HackerNews error: {e}")
            return []
    
    async def get_best_stories(self, limit: int = 20) -> List[Article]:
        """Get best stories from Hacker News."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.BASE_URL}/beststories.json")
                
                if response.status_code != 200:
                    return []
                
                story_ids = response.json()[:limit]
                
                articles = []
                for story_id in story_ids:
                    item = await self._get_item(client, story_id)
                    if item:
                        articles.append(item.to_article())
                
                return articles
                
        except Exception as e:
            logger.error(f"HackerNews error: {e}")
            return []
    
    async def _get_item(
        self,
        client: httpx.AsyncClient,
        item_id: int,
    ) -> Optional[HackerNewsItem]:
        """Get a single item."""
        try:
            response = await client.get(f"{self.BASE_URL}/item/{item_id}.json")
            
            if response.status_code == 200:
                data = response.json()
                
                if not data or data.get("type") != "story":
                    return None
                
                return HackerNewsItem(
                    id=data.get("id", 0),
                    title=data.get("title", ""),
                    url=data.get("url", ""),
                    text=data.get("text", ""),
                    by=data.get("by", ""),
                    score=data.get("score", 0),
                    descendants=data.get("descendants", 0),
                    time=datetime.fromtimestamp(data.get("time", 0)) if data.get("time") else None,
                    type=data.get("type", "story"),
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"Error fetching HN item {item_id}: {e}")
            return None


class RedditAPI:
    """
    Reddit API integration (using public JSON endpoints).
    
    No API key needed for public subreddits.
    """
    
    BASE_URL = "https://www.reddit.com"
    
    def __init__(self):
        self.headers = {
            "User-Agent": "JARVIS/1.0 (Personal Assistant)"
        }
    
    async def get_subreddit_posts(
        self,
        subreddit: str,
        sort: str = "hot",
        limit: int = 10,
    ) -> List[Article]:
        """Get posts from a subreddit."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.BASE_URL}/r/{subreddit}/{sort}.json",
                    params={"limit": limit},
                    headers=self.headers,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    posts = data.get("data", {}).get("children", [])
                    
                    articles = []
                    for post in posts:
                        post_data = post.get("data", {})
                        reddit_post = RedditPost(
                            id=post_data.get("id", ""),
                            title=post_data.get("title", ""),
                            selftext=post_data.get("selftext", ""),
                            url=post_data.get("url", ""),
                            permalink=post_data.get("permalink", ""),
                            subreddit=post_data.get("subreddit", ""),
                            author=post_data.get("author", ""),
                            score=post_data.get("score", 0),
                            upvote_ratio=post_data.get("upvote_ratio", 0),
                            num_comments=post_data.get("num_comments", 0),
                            created_utc=datetime.fromtimestamp(post_data.get("created_utc", 0)),
                            is_self=post_data.get("is_self", True),
                        )
                        articles.append(reddit_post.to_article())
                    
                    return articles
                
                return []
                
        except Exception as e:
            logger.error(f"Reddit API error: {e}")
            return []
    
    async def get_multiple_subreddits(
        self,
        subreddits: List[str] = None,
        limit_per_sub: int = 5,
    ) -> List[Article]:
        """Get posts from multiple subreddits."""
        subreddits = subreddits or SUBREDDITS
        
        all_articles = []
        for subreddit in subreddits:
            articles = await self.get_subreddit_posts(subreddit, limit=limit_per_sub)
            all_articles.extend(articles)
        
        # Sort by score
        all_articles.sort(key=lambda a: a.score, reverse=True)
        
        return all_articles


class DevToAPI:
    """
    Dev.to API integration.
    
    Free, no API key needed for reading.
    Docs: https://developers.forem.com/api
    """
    
    BASE_URL = "https://dev.to/api"
    
    async def get_articles(
        self,
        tag: Optional[str] = None,
        top: Optional[int] = None,
        per_page: int = 10,
    ) -> List[Article]:
        """Get articles from Dev.to."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                params = {"per_page": per_page}
                
                if tag:
                    params["tag"] = tag
                if top:
                    params["top"] = top  # Days (1, 7, 30, 365, infinity)
                
                response = await client.get(
                    f"{self.BASE_URL}/articles",
                    params=params,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_articles(data)
                
                return []
                
        except Exception as e:
            logger.error(f"Dev.to API error: {e}")
            return []
    
    def _parse_articles(self, articles: List[Dict]) -> List[Article]:
        """Parse Dev.to articles."""
        parsed = []
        
        for article in articles:
            try:
                published = None
                if article.get("published_at"):
                    published = datetime.fromisoformat(
                        article["published_at"].replace("Z", "+00:00")
                    )
                
                devto = DevToArticle(
                    id=article.get("id", 0),
                    title=article.get("title", ""),
                    description=article.get("description", ""),
                    url=article.get("url", ""),
                    user=article.get("user", {}).get("username", ""),
                    tags=article.get("tag_list", []),
                    positive_reactions_count=article.get("positive_reactions_count", 0),
                    comments_count=article.get("comments_count", 0),
                    reading_time_minutes=article.get("reading_time_minutes", 0),
                    published_at=published,
                    cover_image=article.get("cover_image"),
                )
                parsed.append(devto.to_article())
                
            except Exception as e:
                logger.debug(f"Error parsing Dev.to article: {e}")
                continue
        
        return parsed


class GoogleNewsRSS:
    """
    Google News RSS feed parser.
    
    Free, no API key needed.
    """
    
    BASE_URL = "https://news.google.com/rss"
    
    async def search(self, query: str, limit: int = 10) -> List[Article]:
        """Search Google News."""
        try:
            import xml.etree.ElementTree as ET
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search",
                    params={"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"},
                )
                
                if response.status_code == 200:
                    root = ET.fromstring(response.text)
                    
                    articles = []
                    for item in root.findall(".//item")[:limit]:
                        title = item.find("title")
                        link = item.find("link")
                        pub_date = item.find("pubDate")
                        source = item.find("source")
                        
                        articles.append(Article(
                            title=title.text if title is not None else "",
                            url=link.text if link is not None else "",
                            source=source.text if source is not None else "Google News",
                            source_type=NewsSource.RSS,
                            published_at=self._parse_date(pub_date.text) if pub_date is not None else None,
                        ))
                    
                    return articles
                
                return []
                
        except Exception as e:
            logger.error(f"Google News RSS error: {e}")
            return []
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse RSS date format."""
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception:
            return None


async def test_all_apis() -> Dict[str, bool]:
    """Test all news APIs."""
    results = {}
    
    # NewsAPI
    newsapi = NewsAPI()
    if newsapi.is_configured:
        articles = await newsapi.get_headlines(page_size=1)
        results["newsapi"] = len(articles) > 0
    else:
        results["newsapi"] = False
    
    # HackerNews
    hn = HackerNewsAPI()
    articles = await hn.get_top_stories(limit=1)
    results["hackernews"] = len(articles) > 0
    
    # Reddit
    reddit = RedditAPI()
    articles = await reddit.get_subreddit_posts("technology", limit=1)
    results["reddit"] = len(articles) > 0
    
    # Dev.to
    devto = DevToAPI()
    articles = await devto.get_articles(per_page=1)
    results["devto"] = len(articles) > 0
    
    return results
