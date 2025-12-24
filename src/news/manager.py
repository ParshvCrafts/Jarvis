"""
News Manager for JARVIS Smart News Module.

Main orchestrator for personalized news, digests, and company tracking.
"""

import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .models import (
    Article, NewsCategory, NewsSource,
    NewsDigest, NewsInterest, CompanyNews,
    DEFAULT_INTERESTS, SUBREDDITS
)
from .apis import (
    NewsAPI, HackerNewsAPI, RedditAPI, DevToAPI, GoogleNewsRSS
)


@dataclass
class NewsConfig:
    """Configuration for news manager."""
    db_path: str = "data/news.db"
    
    # Interests
    interests: List[NewsInterest] = None
    
    # Sources
    use_newsapi: bool = True
    use_hackernews: bool = True
    use_reddit: bool = True
    use_devto: bool = True
    
    # Settings
    max_articles: int = 20
    digest_day: str = "sunday"
    
    def __post_init__(self):
        if self.interests is None:
            self.interests = DEFAULT_INTERESTS


class NewsManager:
    """
    Main manager for news functionality.
    
    Features:
    - Personalized news feed
    - Multiple source aggregation
    - Company news tracking
    - Weekly digest generation
    - Article saving
    - Relevance ranking
    """
    
    def __init__(
        self,
        config: Optional[NewsConfig] = None,
        llm_router: Optional[Any] = None,
    ):
        self.config = config or NewsConfig()
        self.llm_router = llm_router
        
        # Initialize APIs
        self.newsapi = NewsAPI()
        self.hackernews = HackerNewsAPI()
        self.reddit = RedditAPI()
        self.devto = DevToAPI()
        self.google_news = GoogleNewsRSS()
        
        # Initialize database
        self._init_db()
        
        logger.info("News Manager initialized")
    
    def _init_db(self):
        """Initialize SQLite database."""
        Path(self.config.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS saved_articles (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                url TEXT,
                source TEXT,
                author TEXT,
                published_at TEXT,
                category TEXT,
                score INTEGER,
                saved_at TEXT,
                read INTEGER DEFAULT 0
            );
            
            CREATE TABLE IF NOT EXISTS news_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                articles JSON,
                fetched_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS weekly_digests (
                id TEXT PRIMARY KEY,
                week_start TEXT,
                summary TEXT,
                key_stories JSON,
                generated_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS company_tracking (
                company TEXT PRIMARY KEY,
                last_checked TEXT,
                article_count INTEGER DEFAULT 0
            );
            
            CREATE INDEX IF NOT EXISTS idx_saved_date ON saved_articles(saved_at);
        """)
        
        conn.commit()
        conn.close()
    
    # =========================================================================
    # News Fetching
    # =========================================================================
    
    async def get_tech_news(self, limit: int = 10) -> List[Article]:
        """Get technology news from multiple sources."""
        all_articles = []
        
        # NewsAPI headlines
        if self.config.use_newsapi and self.newsapi.is_configured:
            articles = await self.newsapi.get_headlines(
                category="technology",
                page_size=limit,
            )
            all_articles.extend(articles)
        
        # Hacker News
        if self.config.use_hackernews:
            articles = await self.hackernews.get_top_stories(limit=limit)
            all_articles.extend(articles)
        
        # Rank and deduplicate
        return self._rank_articles(all_articles)[:limit]
    
    async def get_ai_news(self, limit: int = 10) -> List[Article]:
        """Get AI/ML specific news."""
        all_articles = []
        
        # Search NewsAPI for AI
        if self.newsapi.is_configured:
            articles = await self.newsapi.search(
                query="artificial intelligence OR machine learning OR GPT OR LLM",
                from_date=datetime.now() - timedelta(days=7),
                page_size=limit,
            )
            all_articles.extend(articles)
        
        # Reddit ML subreddit
        if self.config.use_reddit:
            articles = await self.reddit.get_subreddit_posts(
                "MachineLearning",
                limit=limit,
            )
            all_articles.extend(articles)
        
        # Dev.to AI tag
        if self.config.use_devto:
            articles = await self.devto.get_articles(tag="ai", per_page=limit)
            all_articles.extend(articles)
        
        return self._rank_articles(all_articles)[:limit]
    
    async def get_data_science_news(self, limit: int = 10) -> List[Article]:
        """Get data science news."""
        all_articles = []
        
        # Reddit datascience
        if self.config.use_reddit:
            articles = await self.reddit.get_subreddit_posts(
                "datascience",
                limit=limit,
            )
            all_articles.extend(articles)
        
        # Dev.to datascience tag
        if self.config.use_devto:
            articles = await self.devto.get_articles(tag="datascience", per_page=limit)
            all_articles.extend(articles)
        
        return self._rank_articles(all_articles)[:limit]
    
    async def get_reddit_top(
        self,
        subreddit: str = "MachineLearning",
        limit: int = 10,
    ) -> List[Article]:
        """Get top posts from a subreddit."""
        return await self.reddit.get_subreddit_posts(subreddit, sort="hot", limit=limit)
    
    async def get_hackernews_top(self, limit: int = 10) -> List[Article]:
        """Get top Hacker News stories."""
        return await self.hackernews.get_top_stories(limit=limit)
    
    async def get_personalized_feed(self, limit: int = 20) -> List[Article]:
        """Get personalized news feed based on interests."""
        all_articles = []
        
        # Fetch from multiple sources
        tasks = []
        
        # Tech news
        tech = await self.get_tech_news(limit=10)
        all_articles.extend(tech)
        
        # AI news
        ai = await self.get_ai_news(limit=10)
        all_articles.extend(ai)
        
        # Reddit aggregation
        reddit = await self.reddit.get_multiple_subreddits(limit_per_sub=3)
        all_articles.extend(reddit)
        
        # Rank by relevance to interests
        ranked = self._rank_by_interests(all_articles)
        
        # Deduplicate
        seen_titles = set()
        unique = []
        for article in ranked:
            title_key = article.title.lower()[:50]
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique.append(article)
        
        return unique[:limit]
    
    def _rank_articles(self, articles: List[Article]) -> List[Article]:
        """Rank articles by score and recency."""
        now = datetime.now()
        
        for article in articles:
            # Base score from engagement
            base_score = article.score
            
            # Recency bonus
            if article.published_at:
                hours_old = (now - article.published_at).total_seconds() / 3600
                recency_bonus = max(0, 100 - hours_old * 2)
            else:
                recency_bonus = 0
            
            article.relevance_score = base_score + recency_bonus
        
        return sorted(articles, key=lambda a: a.relevance_score, reverse=True)
    
    def _rank_by_interests(self, articles: List[Article]) -> List[Article]:
        """Rank articles by relevance to user interests."""
        for article in articles:
            score = 0
            text = f"{article.title} {article.description}".lower()
            
            for interest in self.config.interests:
                for keyword in interest.keywords:
                    if keyword.lower() in text:
                        score += interest.weight * 10
            
            # Add base engagement score
            score += min(article.score / 10, 50)
            
            article.relevance_score = score
        
        return sorted(articles, key=lambda a: a.relevance_score, reverse=True)
    
    # =========================================================================
    # Company News
    # =========================================================================
    
    async def get_company_news(
        self,
        company: str,
        limit: int = 5,
    ) -> CompanyNews:
        """Get news about a specific company."""
        articles = []
        
        # Search NewsAPI
        if self.newsapi.is_configured:
            results = await self.newsapi.search(
                query=company,
                from_date=datetime.now() - timedelta(days=7),
                page_size=limit,
            )
            articles.extend(results)
        
        # Google News RSS
        results = await self.google_news.search(company, limit=limit)
        articles.extend(results)
        
        # Deduplicate
        seen = set()
        unique = []
        for a in articles:
            if a.title not in seen:
                seen.add(a.title)
                unique.append(a)
        
        # Analyze sentiment (simple keyword-based)
        sentiment = self._analyze_sentiment(unique)
        
        return CompanyNews(
            company=company,
            articles=unique[:limit],
            sentiment=sentiment,
            last_updated=datetime.now(),
        )
    
    def _analyze_sentiment(self, articles: List[Article]) -> str:
        """Simple sentiment analysis based on keywords."""
        positive_words = ["growth", "success", "profit", "launch", "innovation", "expanding", "hiring"]
        negative_words = ["layoff", "decline", "loss", "lawsuit", "controversy", "cut", "fired"]
        
        positive_count = 0
        negative_count = 0
        
        for article in articles:
            text = f"{article.title} {article.description}".lower()
            
            for word in positive_words:
                if word in text:
                    positive_count += 1
            
            for word in negative_words:
                if word in text:
                    negative_count += 1
        
        if positive_count > negative_count + 2:
            return "positive"
        elif negative_count > positive_count + 2:
            return "negative"
        return "neutral"
    
    # =========================================================================
    # Weekly Digest
    # =========================================================================
    
    async def generate_weekly_digest(self) -> NewsDigest:
        """Generate a weekly news digest."""
        digest = NewsDigest(
            week_start=date.today() - timedelta(days=7),
        )
        
        # Gather news from the week
        ai_news = await self.get_ai_news(limit=10)
        tech_news = await self.get_tech_news(limit=10)
        
        digest.ai_news = ai_news[:5]
        digest.tech_news = tech_news[:5]
        
        # Key stories (top by score)
        all_stories = ai_news + tech_news
        all_stories.sort(key=lambda a: a.score, reverse=True)
        digest.key_stories = all_stories[:5]
        
        if digest.key_stories:
            digest.top_story = digest.key_stories[0]
        
        # Extract trending topics
        digest.trending_topics = self._extract_topics(all_stories)
        
        # Generate summary
        digest.summary = self._generate_summary(digest)
        
        # Save to database
        self._save_digest(digest)
        
        return digest
    
    def _extract_topics(self, articles: List[Article]) -> List[str]:
        """Extract trending topics from articles."""
        topic_counts = {}
        
        keywords = [
            "AI", "GPT", "LLM", "ChatGPT", "OpenAI", "Google", "Meta",
            "Python", "Machine Learning", "Data Science", "Neural Network",
            "Startup", "Funding", "Apple", "Microsoft", "NVIDIA",
        ]
        
        for article in articles:
            text = f"{article.title} {article.description}"
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    topic_counts[keyword] = topic_counts.get(keyword, 0) + 1
        
        # Sort by count
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        return [topic for topic, count in sorted_topics[:5]]
    
    def _generate_summary(self, digest: NewsDigest) -> str:
        """Generate a text summary of the digest."""
        lines = [
            f"Week of {digest.week_start.strftime('%B %d, %Y')}",
            "",
        ]
        
        if digest.trending_topics:
            lines.append(f"Trending: {', '.join(digest.trending_topics)}")
            lines.append("")
        
        if digest.top_story:
            lines.append(f"Top Story: {digest.top_story.title}")
        
        return "\n".join(lines)
    
    def _save_digest(self, digest: NewsDigest):
        """Save digest to database."""
        import json
        
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO weekly_digests (id, week_start, summary, key_stories, generated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            digest.id,
            digest.week_start.isoformat(),
            digest.summary,
            json.dumps([a.to_dict() for a in digest.key_stories]),
            digest.generated_at.isoformat(),
        ))
        
        conn.commit()
        conn.close()
    
    # =========================================================================
    # Article Management
    # =========================================================================
    
    def save_article(self, article: Article) -> bool:
        """Save an article for later."""
        try:
            conn = sqlite3.connect(self.config.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO saved_articles
                (id, title, description, url, source, author, published_at, category, score, saved_at, read)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article.id,
                article.title,
                article.description,
                article.url,
                article.source,
                article.author,
                article.published_at.isoformat() if article.published_at else None,
                article.category.value,
                article.score,
                datetime.now().isoformat(),
                0,
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Failed to save article: {e}")
            return False
    
    def get_saved_articles(self, limit: int = 20) -> List[Dict]:
        """Get saved articles."""
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM saved_articles ORDER BY saved_at DESC LIMIT ?
        """, (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        articles = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return articles
    
    # =========================================================================
    # Voice Command Handler
    # =========================================================================
    
    async def handle_command(self, command: str) -> str:
        """Handle voice commands for news."""
        command_lower = command.lower()
        
        # Tech news
        if "tech news" in command_lower:
            articles = await self.get_tech_news(limit=5)
            return self._format_articles("Tech News", articles)
        
        # AI news
        if "ai news" in command_lower or "ml news" in command_lower:
            articles = await self.get_ai_news(limit=5)
            return self._format_articles("AI/ML News", articles)
        
        # Data science news
        if "data science" in command_lower:
            articles = await self.get_data_science_news(limit=5)
            return self._format_articles("Data Science News", articles)
        
        # Hacker News
        if "hacker news" in command_lower or "hackernews" in command_lower:
            articles = await self.get_hackernews_top(limit=5)
            return self._format_articles("Hacker News Top", articles)
        
        # Reddit
        if "reddit" in command_lower:
            import re
            sub_match = re.search(r'r/(\w+)', command_lower)
            subreddit = sub_match.group(1) if sub_match else "MachineLearning"
            articles = await self.get_reddit_top(subreddit, limit=5)
            return self._format_articles(f"r/{subreddit} Top Posts", articles)
        
        # Company news
        if "news about" in command_lower or "news for" in command_lower:
            import re
            company_match = re.search(r'(?:about|for)\s+(\w+)', command_lower)
            if company_match:
                company = company_match.group(1).title()
                news = await self.get_company_news(company)
                return self._format_company_news(news)
            return "Please specify a company: 'News about Google'"
        
        # Weekly digest
        if "digest" in command_lower or "weekly" in command_lower:
            digest = await self.generate_weekly_digest()
            return self._format_digest(digest)
        
        # General news
        if "news" in command_lower:
            articles = await self.get_personalized_feed(limit=5)
            return self._format_articles("Your News Feed", articles)
        
        return (
            "News commands:\n"
            "  - 'Tech news today'\n"
            "  - 'AI news this week'\n"
            "  - 'Show me r/MachineLearning'\n"
            "  - 'News about Google'\n"
            "  - 'Weekly news digest'"
        )
    
    def _format_articles(self, title: str, articles: List[Article]) -> str:
        """Format articles for display."""
        if not articles:
            return f"📰 No {title.lower()} found."
        
        lines = [f"📰 **{title}:**", ""]
        
        for i, article in enumerate(articles[:5], 1):
            source = f" ({article.source})" if article.source else ""
            score = f" ⬆️{article.score}" if article.score > 0 else ""
            lines.append(f"{i}. {article.title}{source}{score}")
        
        return "\n".join(lines)
    
    def _format_company_news(self, news: CompanyNews) -> str:
        """Format company news for display."""
        sentiment_emoji = {
            "positive": "📈",
            "negative": "📉",
            "neutral": "➡️",
        }
        
        lines = [
            f"📰 **News about {news.company}:** {sentiment_emoji.get(news.sentiment, '')}",
            "",
        ]
        
        if not news.articles:
            lines.append("No recent news found.")
        else:
            for article in news.articles[:5]:
                lines.append(f"  • {article.title}")
        
        return "\n".join(lines)
    
    def _format_digest(self, digest: NewsDigest) -> str:
        """Format weekly digest for display."""
        lines = [
            f"📰 **Weekly News Digest**",
            f"*Week of {digest.week_start.strftime('%B %d')}*",
            "",
        ]
        
        if digest.trending_topics:
            lines.append(f"**Trending:** {', '.join(digest.trending_topics)}")
            lines.append("")
        
        if digest.key_stories:
            lines.append("**Top Stories:**")
            for story in digest.key_stories[:5]:
                lines.append(f"  • {story.title}")
        
        return "\n".join(lines)
    
    def get_briefing_summary(self) -> str:
        """Get news summary for daily briefing."""
        # This would be called synchronously, so we return cached data
        # In practice, you'd want to cache the latest news
        return "📰 Check 'AI news' for latest updates"
    
    # =========================================================================
    # Status
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get news module status."""
        saved = len(self.get_saved_articles(limit=100))
        
        return {
            "newsapi_configured": self.newsapi.is_configured,
            "sources_enabled": sum([
                self.config.use_newsapi,
                self.config.use_hackernews,
                self.config.use_reddit,
                self.config.use_devto,
            ]),
            "saved_articles": saved,
            "interests": len(self.config.interests),
        }
    
    def get_status_summary(self) -> str:
        """Get formatted status summary."""
        status = self.get_status()
        
        lines = [
            "📰 **News Module Status**",
            "",
            f"{'✅' if status['newsapi_configured'] else '⚠️'} NewsAPI configured",
            f"📡 {status['sources_enabled']} sources enabled",
            f"📚 {status['saved_articles']} saved articles",
            f"🎯 {status['interests']} interest topics",
        ]
        
        return "\n".join(lines)
