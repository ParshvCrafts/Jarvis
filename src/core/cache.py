"""
Multi-Level Intelligent Caching System for JARVIS.

Provides:
- Level 1: In-memory LRU cache (fastest)
- Level 2: SQLite persistent cache (survives restart)
- Level 3: Semantic cache with embeddings (similar queries)
- Response templates for common queries

Features:
- Automatic TTL-based expiration
- Semantic similarity matching
- Smart cache invalidation
- Cache statistics and monitoring

Usage:
    cache = IntelligentCache(config)
    
    # Check cache
    result = await cache.get(query)
    if result:
        return result
    
    # Store result
    await cache.set(query, response, category="weather")
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sqlite3
import time
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from loguru import logger

# Optional: sentence-transformers for semantic caching
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    SentenceTransformer = None
    np = None


class CacheCategory(Enum):
    """Categories for cache TTL management."""
    STATIC = "static"           # Definitions, how-tos (7 days)
    WEATHER = "weather"         # Weather queries (30 minutes)
    NEWS = "news"               # News queries (1 hour)
    SYSTEM = "system"           # System status (no cache)
    IOT = "iot"                 # IoT state (5 minutes)
    CALENDAR = "calendar"       # Calendar/schedule (15 minutes)
    GENERAL = "general"         # General queries (1 hour)
    CONVERSATION = "conversation"  # Conversation context (session)


# TTL in seconds for each category
CATEGORY_TTL = {
    CacheCategory.STATIC: 7 * 24 * 3600,      # 7 days
    CacheCategory.WEATHER: 30 * 60,            # 30 minutes
    CacheCategory.NEWS: 60 * 60,               # 1 hour
    CacheCategory.SYSTEM: 0,                   # No cache
    CacheCategory.IOT: 5 * 60,                 # 5 minutes
    CacheCategory.CALENDAR: 15 * 60,           # 15 minutes
    CacheCategory.GENERAL: 60 * 60,            # 1 hour
    CacheCategory.CONVERSATION: 30 * 60,       # 30 minutes
}


@dataclass
class CacheConfig:
    """Configuration for the caching system."""
    # General
    enabled: bool = True
    
    # Level 1: Memory cache
    memory_cache_size: int = 100
    memory_cache_ttl: int = 3600  # 1 hour default
    
    # Level 2: SQLite cache
    sqlite_enabled: bool = True
    sqlite_max_entries: int = 10000
    sqlite_cleanup_interval: int = 3600  # 1 hour
    
    # Level 3: Semantic cache
    semantic_enabled: bool = True
    semantic_threshold: float = 0.92  # Similarity threshold
    semantic_model: str = "all-MiniLM-L6-v2"
    semantic_cache_size: int = 1000
    
    # Response templates
    templates_enabled: bool = True
    
    # Database path
    cache_dir: Optional[Path] = None


@dataclass
class CacheEntry:
    """A cached response entry."""
    key: str
    value: str
    category: CacheCategory
    created_at: float
    expires_at: float
    access_count: int = 0
    last_accessed: float = 0.0
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at == 0:
            return False  # Never expires
        return time.time() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "category": self.category.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "metadata": self.metadata,
        }


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    memory_hits: int = 0
    sqlite_hits: int = 0
    semantic_hits: int = 0
    template_hits: int = 0
    evictions: int = 0
    
    @property
    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": round(self.hit_ratio, 3),
            "memory_hits": self.memory_hits,
            "sqlite_hits": self.sqlite_hits,
            "semantic_hits": self.semantic_hits,
            "template_hits": self.template_hits,
            "evictions": self.evictions,
        }


class LRUCache:
    """
    Thread-safe LRU cache with TTL support.
    
    Level 1 cache - fastest, in-memory.
    """
    
    def __init__(self, max_size: int = 100, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache."""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check expiration
            if entry.is_expired:
                del self._cache[key]
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.access_count += 1
            entry.last_accessed = time.time()
            
            return entry
    
    def set(
        self,
        key: str,
        value: str,
        category: CacheCategory = CacheCategory.GENERAL,
        ttl: Optional[int] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CacheEntry:
        """Set entry in cache."""
        with self._lock:
            # Calculate TTL
            if ttl is None:
                ttl = CATEGORY_TTL.get(category, self.default_ttl)
            
            now = time.time()
            entry = CacheEntry(
                key=key,
                value=value,
                category=category,
                created_at=now,
                expires_at=now + ttl if ttl > 0 else 0,
                embedding=embedding,
                metadata=metadata or {},
            )
            
            # Evict if at capacity
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            
            self._cache[key] = entry
            return entry
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> int:
        """Clear all entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def cleanup_expired(self) -> int:
        """Remove expired entries."""
        with self._lock:
            expired = [k for k, v in self._cache.items() if v.is_expired]
            for key in expired:
                del self._cache[key]
            return len(expired)
    
    @property
    def size(self) -> int:
        return len(self._cache)


class SQLiteCache:
    """
    SQLite-based persistent cache.
    
    Level 2 cache - survives restarts.
    """
    
    def __init__(
        self,
        db_path: Path,
        max_entries: int = 10000,
        cleanup_interval: int = 3600,
    ):
        self.db_path = db_path
        self.max_entries = max_entries
        self.cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL,
                    embedding BLOB,
                    metadata TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON cache(category)")
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache."""
        self._maybe_cleanup()
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM cache WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Check expiration
            if row["expires_at"] > 0 and time.time() > row["expires_at"]:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                return None
            
            # Update access stats
            conn.execute(
                "UPDATE cache SET access_count = access_count + 1, last_accessed = ? WHERE key = ?",
                (time.time(), key)
            )
            
            # Parse embedding if present
            embedding = None
            if row["embedding"] and EMBEDDINGS_AVAILABLE:
                embedding = np.frombuffer(row["embedding"], dtype=np.float32).tolist()
            
            return CacheEntry(
                key=row["key"],
                value=row["value"],
                category=CacheCategory(row["category"]),
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                access_count=row["access_count"],
                last_accessed=row["last_accessed"] or 0,
                embedding=embedding,
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )
    
    def set(
        self,
        key: str,
        value: str,
        category: CacheCategory = CacheCategory.GENERAL,
        ttl: Optional[int] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set entry in cache."""
        if ttl is None:
            ttl = CATEGORY_TTL.get(category, 3600)
        
        now = time.time()
        expires_at = now + ttl if ttl > 0 else 0
        
        # Serialize embedding
        embedding_blob = None
        if embedding and EMBEDDINGS_AVAILABLE:
            embedding_blob = np.array(embedding, dtype=np.float32).tobytes()
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache 
                (key, value, category, created_at, expires_at, embedding, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                key,
                value,
                category.value,
                now,
                expires_at,
                embedding_blob,
                json.dumps(metadata) if metadata else None,
            ))
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            return cursor.rowcount > 0
    
    def clear(self) -> int:
        """Clear all entries."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM cache")
            return cursor.rowcount
    
    def clear_category(self, category: CacheCategory) -> int:
        """Clear entries in a category."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM cache WHERE category = ?",
                (category.value,)
            )
            return cursor.rowcount
    
    def _maybe_cleanup(self) -> None:
        """Run cleanup if interval has passed."""
        if time.time() - self._last_cleanup > self.cleanup_interval:
            self._cleanup()
            self._last_cleanup = time.time()
    
    def _cleanup(self) -> int:
        """Remove expired entries and enforce max size."""
        with self._get_connection() as conn:
            # Remove expired
            cursor = conn.execute(
                "DELETE FROM cache WHERE expires_at > 0 AND expires_at < ?",
                (time.time(),)
            )
            expired = cursor.rowcount
            
            # Enforce max size
            count = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            if count > self.max_entries:
                excess = count - self.max_entries
                conn.execute("""
                    DELETE FROM cache WHERE key IN (
                        SELECT key FROM cache ORDER BY last_accessed ASC LIMIT ?
                    )
                """, (excess,))
            
            return expired
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            by_category = {}
            for row in conn.execute("SELECT category, COUNT(*) FROM cache GROUP BY category"):
                by_category[row[0]] = row[1]
            
            return {
                "total_entries": total,
                "max_entries": self.max_entries,
                "by_category": by_category,
            }


class SemanticCache:
    """
    Semantic similarity cache using embeddings.
    
    Level 3 cache - finds similar queries.
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        threshold: float = 0.92,
        max_entries: int = 1000,
    ):
        self.model_name = model_name
        self.threshold = threshold
        self.max_entries = max_entries
        
        self._model: Optional[SentenceTransformer] = None
        self._embeddings: Dict[str, Tuple[List[float], CacheEntry]] = {}
        self._lock = Lock()
    
    def _get_model(self) -> Optional[SentenceTransformer]:
        """Lazy load the embedding model."""
        if not EMBEDDINGS_AVAILABLE:
            return None
        
        if self._model is None:
            try:
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded semantic cache model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to load semantic model: {e}")
                return None
        
        return self._model
    
    def _compute_embedding(self, text: str) -> Optional[List[float]]:
        """Compute embedding for text."""
        model = self._get_model()
        if model is None:
            return None
        
        try:
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Embedding computation failed: {e}")
            return None
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not EMBEDDINGS_AVAILABLE:
            return 0.0
        
        a_arr = np.array(a)
        b_arr = np.array(b)
        
        dot = np.dot(a_arr, b_arr)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot / (norm_a * norm_b)
    
    def find_similar(self, query: str) -> Optional[Tuple[CacheEntry, float]]:
        """
        Find a semantically similar cached entry.
        
        Args:
            query: Query text to match.
            
        Returns:
            Tuple of (entry, similarity) or None if no match.
        """
        if not EMBEDDINGS_AVAILABLE:
            return None
        
        query_embedding = self._compute_embedding(query)
        if query_embedding is None:
            return None
        
        best_match: Optional[Tuple[CacheEntry, float]] = None
        
        with self._lock:
            for key, (embedding, entry) in self._embeddings.items():
                if entry.is_expired:
                    continue
                
                similarity = self._cosine_similarity(query_embedding, embedding)
                
                if similarity >= self.threshold:
                    if best_match is None or similarity > best_match[1]:
                        best_match = (entry, similarity)
        
        return best_match
    
    def add(self, key: str, entry: CacheEntry) -> bool:
        """Add entry with embedding."""
        if not EMBEDDINGS_AVAILABLE:
            return False
        
        embedding = self._compute_embedding(key)
        if embedding is None:
            return False
        
        with self._lock:
            # Evict if at capacity
            while len(self._embeddings) >= self.max_entries:
                # Remove oldest
                oldest_key = next(iter(self._embeddings))
                del self._embeddings[oldest_key]
            
            entry.embedding = embedding
            self._embeddings[key] = (embedding, entry)
        
        return True
    
    def clear(self) -> int:
        """Clear all entries."""
        with self._lock:
            count = len(self._embeddings)
            self._embeddings.clear()
            return count


class ResponseTemplates:
    """
    Pre-computed response templates for common queries.
    
    Provides instant responses without LLM calls.
    """
    
    def __init__(self):
        self._templates: Dict[str, Callable[[], str]] = {}
        self._patterns: List[Tuple[re.Pattern, Callable[[re.Match], str]]] = []
        
        self._register_default_templates()
    
    def _register_default_templates(self) -> None:
        """Register default response templates."""
        # Time-based greetings
        def greeting_response() -> str:
            hour = datetime.now().hour
            if 5 <= hour < 12:
                return "Good morning! How can I help you today?"
            elif 12 <= hour < 17:
                return "Good afternoon! What can I do for you?"
            elif 17 <= hour < 21:
                return "Good evening! How may I assist you?"
            else:
                return "Hello! I'm here to help, even at this late hour."
        
        # Current time
        def time_response() -> str:
            now = datetime.now()
            return f"The current time is {now.strftime('%I:%M %p')}."
        
        # Current date
        def date_response() -> str:
            now = datetime.now()
            return f"Today is {now.strftime('%A, %B %d, %Y')}."
        
        # Help response
        def help_response() -> str:
            return (
                "I can help you with many things:\n"
                "• Answer questions and have conversations\n"
                "• Search the web for information\n"
                "• Control smart home devices\n"
                "• Open applications and take screenshots\n"
                "• Help with coding and Git operations\n"
                "• Set reminders and check your schedule\n"
                "Just ask me anything!"
            )
        
        # Register exact matches
        self._templates["hello"] = greeting_response
        self._templates["hi"] = greeting_response
        self._templates["hey"] = greeting_response
        self._templates["good morning"] = greeting_response
        self._templates["good afternoon"] = greeting_response
        self._templates["good evening"] = greeting_response
        
        self._templates["what time is it"] = time_response
        self._templates["what's the time"] = time_response
        self._templates["current time"] = time_response
        self._templates["time"] = time_response
        
        self._templates["what's today's date"] = date_response
        self._templates["what date is it"] = date_response
        self._templates["what day is it"] = date_response
        self._templates["today's date"] = date_response
        
        self._templates["help"] = help_response
        self._templates["what can you do"] = help_response
        self._templates["what are your capabilities"] = help_response
        
        # Register pattern matches
        self._patterns.append((
            re.compile(r"what time is it in (\w+)", re.IGNORECASE),
            lambda m: f"I'd need to look up the timezone for {m.group(1)}. Let me check..."
        ))
    
    def get(self, query: str) -> Optional[str]:
        """
        Get template response for query.
        
        Args:
            query: User query.
            
        Returns:
            Template response or None.
        """
        # Normalize query
        normalized = query.lower().strip()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Check exact matches
        if normalized in self._templates:
            return self._templates[normalized]()
        
        # Check patterns
        for pattern, handler in self._patterns:
            match = pattern.match(normalized)
            if match:
                return handler(match)
        
        return None
    
    def register(self, key: str, response: Union[str, Callable[[], str]]) -> None:
        """Register a custom template."""
        if callable(response):
            self._templates[key.lower()] = response
        else:
            self._templates[key.lower()] = lambda r=response: r


class IntelligentCache:
    """
    Multi-level intelligent caching system.
    
    Combines:
    - Level 1: In-memory LRU cache
    - Level 2: SQLite persistent cache
    - Level 3: Semantic similarity cache
    - Response templates
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self.stats = CacheStats()
        
        # Initialize cache levels
        self._memory_cache = LRUCache(
            max_size=self.config.memory_cache_size,
            default_ttl=self.config.memory_cache_ttl,
        )
        
        self._sqlite_cache: Optional[SQLiteCache] = None
        if self.config.sqlite_enabled and self.config.cache_dir:
            self.config.cache_dir.mkdir(parents=True, exist_ok=True)
            self._sqlite_cache = SQLiteCache(
                db_path=self.config.cache_dir / "response_cache.db",
                max_entries=self.config.sqlite_max_entries,
            )
        
        self._semantic_cache: Optional[SemanticCache] = None
        if self.config.semantic_enabled and EMBEDDINGS_AVAILABLE:
            self._semantic_cache = SemanticCache(
                model_name=self.config.semantic_model,
                threshold=self.config.semantic_threshold,
                max_entries=self.config.semantic_cache_size,
            )
        
        self._templates: Optional[ResponseTemplates] = None
        if self.config.templates_enabled:
            self._templates = ResponseTemplates()
    
    def _normalize_key(self, query: str) -> str:
        """Normalize query for cache key."""
        # Lowercase
        key = query.lower().strip()
        # Remove extra whitespace
        key = re.sub(r'\s+', ' ', key)
        # Remove common filler words
        fillers = ["please", "can you", "could you", "would you", "jarvis"]
        for filler in fillers:
            key = key.replace(filler, "")
        key = key.strip()
        # Hash for consistent key length
        return hashlib.md5(key.encode()).hexdigest()
    
    async def get(
        self,
        query: str,
        check_templates: bool = True,
        check_semantic: bool = True,
    ) -> Optional[str]:
        """
        Get cached response for query.
        
        Args:
            query: User query.
            check_templates: Whether to check response templates.
            check_semantic: Whether to check semantic cache.
            
        Returns:
            Cached response or None.
        """
        if not self.config.enabled:
            return None
        
        # Level 0: Response templates (instant)
        if check_templates and self._templates:
            response = self._templates.get(query)
            if response:
                self.stats.hits += 1
                self.stats.template_hits += 1
                logger.debug(f"Template cache hit for: {query[:50]}")
                return response
        
        key = self._normalize_key(query)
        
        # Level 1: Memory cache
        entry = self._memory_cache.get(key)
        if entry:
            self.stats.hits += 1
            self.stats.memory_hits += 1
            logger.debug(f"Memory cache hit for: {query[:50]}")
            return entry.value
        
        # Level 2: SQLite cache
        if self._sqlite_cache:
            entry = self._sqlite_cache.get(key)
            if entry:
                # Promote to memory cache
                self._memory_cache.set(
                    key, entry.value, entry.category,
                    embedding=entry.embedding,
                )
                self.stats.hits += 1
                self.stats.sqlite_hits += 1
                logger.debug(f"SQLite cache hit for: {query[:50]}")
                return entry.value
        
        # Level 3: Semantic cache
        if check_semantic and self._semantic_cache:
            result = self._semantic_cache.find_similar(query)
            if result:
                entry, similarity = result
                self.stats.hits += 1
                self.stats.semantic_hits += 1
                logger.debug(f"Semantic cache hit (similarity={similarity:.3f}) for: {query[:50]}")
                return entry.value
        
        self.stats.misses += 1
        return None
    
    async def set(
        self,
        query: str,
        response: str,
        category: CacheCategory = CacheCategory.GENERAL,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Cache a response.
        
        Args:
            query: Original query.
            response: Response to cache.
            category: Cache category for TTL.
            ttl: Optional custom TTL.
            metadata: Optional metadata.
        """
        if not self.config.enabled:
            return
        
        # Don't cache system queries
        if category == CacheCategory.SYSTEM:
            return
        
        key = self._normalize_key(query)
        
        # Level 1: Memory cache
        entry = self._memory_cache.set(
            key, response, category, ttl, metadata=metadata
        )
        
        # Level 2: SQLite cache
        if self._sqlite_cache:
            self._sqlite_cache.set(
                key, response, category, ttl, metadata=metadata
            )
        
        # Level 3: Semantic cache
        if self._semantic_cache:
            # Use original query for semantic matching
            semantic_entry = CacheEntry(
                key=query,
                value=response,
                category=category,
                created_at=entry.created_at,
                expires_at=entry.expires_at,
                metadata=metadata or {},
            )
            self._semantic_cache.add(query, semantic_entry)
    
    async def invalidate(
        self,
        query: Optional[str] = None,
        category: Optional[CacheCategory] = None,
    ) -> int:
        """
        Invalidate cache entries.
        
        Args:
            query: Specific query to invalidate.
            category: Category to invalidate.
            
        Returns:
            Number of entries invalidated.
        """
        count = 0
        
        if query:
            key = self._normalize_key(query)
            if self._memory_cache.delete(key):
                count += 1
            if self._sqlite_cache and self._sqlite_cache.delete(key):
                count += 1
        
        if category:
            if self._sqlite_cache:
                count += self._sqlite_cache.clear_category(category)
        
        return count
    
    async def clear(self) -> int:
        """Clear all caches."""
        count = 0
        count += self._memory_cache.clear()
        if self._sqlite_cache:
            count += self._sqlite_cache.clear()
        if self._semantic_cache:
            count += self._semantic_cache.clear()
        
        # Reset stats
        self.stats = CacheStats()
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self.stats.to_dict()
        stats["memory_cache_size"] = self._memory_cache.size
        
        if self._sqlite_cache:
            stats["sqlite_stats"] = self._sqlite_cache.get_stats()
        
        stats["semantic_available"] = self._semantic_cache is not None
        stats["templates_available"] = self._templates is not None
        
        return stats


# Singleton instance
_cache: Optional[IntelligentCache] = None


def get_cache(config: Optional[CacheConfig] = None) -> IntelligentCache:
    """Get or create the global cache instance."""
    global _cache
    if _cache is None:
        _cache = IntelligentCache(config)
    return _cache


async def cached_response(
    query: str,
    generator: Callable[[], str],
    category: CacheCategory = CacheCategory.GENERAL,
    ttl: Optional[int] = None,
) -> str:
    """
    Convenience function for cache-or-generate pattern.
    
    Args:
        query: User query.
        generator: Function to generate response if not cached.
        category: Cache category.
        ttl: Optional TTL.
        
    Returns:
        Cached or generated response.
    """
    cache = get_cache()
    
    # Try cache first
    response = await cache.get(query)
    if response:
        return response
    
    # Generate response
    response = generator()
    
    # Cache it
    await cache.set(query, response, category, ttl)
    
    return response
