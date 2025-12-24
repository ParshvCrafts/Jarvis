"""
Data models for JARVIS Smart News Module.

Defines structures for news articles, sources, and digests.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class NewsCategory(Enum):
    """News category."""
    AI = "artificial_intelligence"
    ML = "machine_learning"
    DATA_SCIENCE = "data_science"
    TECH = "technology"
    PROGRAMMING = "programming"
    STARTUPS = "startups"
    FINANCE = "finance"
    SCIENCE = "science"
    BERKELEY = "uc_berkeley"
    GENERAL = "general"


class NewsSource(Enum):
    """News source."""
    NEWSAPI = "newsapi"
    HACKERNEWS = "hackernews"
    REDDIT = "reddit"
    DEVTO = "devto"
    ARXIV = "arxiv"
    RSS = "rss"


@dataclass
class Article:
    """A news article."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    title: str = ""
    description: str = ""
    content: str = ""
    url: str = ""
    
    source: str = ""
    source_type: NewsSource = NewsSource.NEWSAPI
    author: Optional[str] = None
    
    published_at: Optional[datetime] = None
    
    # Categorization
    category: NewsCategory = NewsCategory.GENERAL
    tags: List[str] = field(default_factory=list)
    
    # Engagement
    score: int = 0  # Upvotes, likes, etc.
    comments: int = 0
    
    # For user
    relevance_score: float = 0.0
    read: bool = False
    saved: bool = False
    
    # Media
    image_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "source": self.source,
            "author": self.author,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "category": self.category.value,
            "score": self.score,
            "relevance_score": self.relevance_score,
        }


@dataclass
class RedditPost:
    """A Reddit post."""
    id: str = ""
    title: str = ""
    selftext: str = ""
    url: str = ""
    permalink: str = ""
    
    subreddit: str = ""
    author: str = ""
    
    score: int = 0
    upvote_ratio: float = 0.0
    num_comments: int = 0
    
    created_utc: Optional[datetime] = None
    
    is_self: bool = True
    
    def to_article(self) -> Article:
        """Convert to Article."""
        return Article(
            id=self.id,
            title=self.title,
            description=self.selftext[:500] if self.selftext else "",
            url=f"https://reddit.com{self.permalink}" if self.permalink else self.url,
            source=f"r/{self.subreddit}",
            source_type=NewsSource.REDDIT,
            author=self.author,
            published_at=self.created_utc,
            score=self.score,
            comments=self.num_comments,
        )


@dataclass
class HackerNewsItem:
    """A Hacker News item."""
    id: int = 0
    title: str = ""
    url: str = ""
    text: str = ""
    
    by: str = ""
    score: int = 0
    descendants: int = 0  # Comments
    
    time: Optional[datetime] = None
    type: str = "story"
    
    def to_article(self) -> Article:
        """Convert to Article."""
        return Article(
            id=str(self.id),
            title=self.title,
            description=self.text[:500] if self.text else "",
            url=self.url or f"https://news.ycombinator.com/item?id={self.id}",
            source="Hacker News",
            source_type=NewsSource.HACKERNEWS,
            author=self.by,
            published_at=self.time,
            score=self.score,
            comments=self.descendants,
            category=NewsCategory.TECH,
        )


@dataclass
class DevToArticle:
    """A Dev.to article."""
    id: int = 0
    title: str = ""
    description: str = ""
    url: str = ""
    
    user: str = ""
    tags: List[str] = field(default_factory=list)
    
    positive_reactions_count: int = 0
    comments_count: int = 0
    reading_time_minutes: int = 0
    
    published_at: Optional[datetime] = None
    cover_image: Optional[str] = None
    
    def to_article(self) -> Article:
        """Convert to Article."""
        return Article(
            id=str(self.id),
            title=self.title,
            description=self.description,
            url=self.url,
            source="Dev.to",
            source_type=NewsSource.DEVTO,
            author=self.user,
            published_at=self.published_at,
            score=self.positive_reactions_count,
            comments=self.comments_count,
            tags=self.tags,
            image_url=self.cover_image,
            category=NewsCategory.PROGRAMMING,
        )


@dataclass
class NewsDigest:
    """A weekly news digest."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    week_start: date = field(default_factory=date.today)
    generated_at: datetime = field(default_factory=datetime.now)
    
    # Content
    summary: str = ""
    key_stories: List[Article] = field(default_factory=list)
    
    # By category
    ai_news: List[Article] = field(default_factory=list)
    tech_news: List[Article] = field(default_factory=list)
    research_news: List[Article] = field(default_factory=list)
    
    # Highlights
    top_story: Optional[Article] = None
    trending_topics: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "week_start": self.week_start.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "summary": self.summary,
            "key_stories_count": len(self.key_stories),
            "trending_topics": self.trending_topics,
        }


@dataclass
class NewsInterest:
    """User's news interest."""
    topic: str
    weight: float = 1.0  # Importance weight
    keywords: List[str] = field(default_factory=list)


@dataclass
class CompanyNews:
    """News about a specific company."""
    company: str
    articles: List[Article] = field(default_factory=list)
    sentiment: str = "neutral"  # positive, negative, neutral
    summary: str = ""
    last_updated: datetime = field(default_factory=datetime.now)


# Default interests for a DS/ML student
DEFAULT_INTERESTS = [
    NewsInterest(
        topic="Artificial Intelligence",
        weight=1.0,
        keywords=["ai", "artificial intelligence", "gpt", "llm", "chatgpt", "openai", "anthropic", "gemini"],
    ),
    NewsInterest(
        topic="Machine Learning",
        weight=1.0,
        keywords=["machine learning", "ml", "deep learning", "neural network", "transformer", "pytorch", "tensorflow"],
    ),
    NewsInterest(
        topic="Data Science",
        weight=0.9,
        keywords=["data science", "data analysis", "pandas", "statistics", "visualization"],
    ),
    NewsInterest(
        topic="Python",
        weight=0.8,
        keywords=["python", "python3", "pip", "conda"],
    ),
    NewsInterest(
        topic="Tech Companies",
        weight=0.7,
        keywords=["google", "meta", "amazon", "microsoft", "apple", "nvidia", "openai"],
    ),
    NewsInterest(
        topic="UC Berkeley",
        weight=0.6,
        keywords=["uc berkeley", "berkeley", "cal", "golden bears"],
    ),
]

# Subreddits for news
SUBREDDITS = [
    "MachineLearning",
    "datascience",
    "Python",
    "programming",
    "technology",
    "artificial",
    "berkeley",
]
