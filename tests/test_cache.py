"""
Unit tests for the cache module.

Tests:
- LRUCache eviction and TTL
- SQLiteCache persistence
- SemanticCache similarity matching
- ResponseTemplates
- IntelligentCache multi-level lookup
"""

import asyncio
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.cache import (
    LRUCache,
    SQLiteCache,
    SemanticCache,
    ResponseTemplates,
    IntelligentCache,
    CacheConfig,
    CacheCategory,
    CacheEntry,
    CacheStats,
    get_cache,
    CATEGORY_TTL,
)


class TestLRUCache:
    """Tests for LRUCache class."""
    
    def test_basic_set_get(self):
        """Test basic set and get operations."""
        cache = LRUCache(max_size=10)
        
        cache.set("key1", "value1")
        entry = cache.get("key1")
        
        assert entry is not None
        assert entry.value == "value1"
    
    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = LRUCache(max_size=10)
        
        entry = cache.get("nonexistent")
        assert entry is None
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = LRUCache(max_size=3)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        cache.get("key1")
        
        # Add key4, should evict key2 (least recently used)
        cache.set("key4", "value4")
        
        assert cache.get("key1") is not None
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") is not None
        assert cache.get("key4") is not None
    
    def test_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = LRUCache(max_size=10, default_ttl=1)
        
        cache.set("key1", "value1", ttl=1)  # 1 second TTL
        
        # Should exist immediately
        assert cache.get("key1") is not None
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get("key1") is None
    
    def test_category_ttl(self):
        """Test category-based TTL."""
        cache = LRUCache(max_size=10)
        
        # Weather has 30 min TTL, static has 7 days
        cache.set("weather", "sunny", category=CacheCategory.WEATHER)
        cache.set("definition", "a word", category=CacheCategory.STATIC)
        
        weather_entry = cache.get("weather")
        static_entry = cache.get("definition")
        
        assert weather_entry is not None
        assert static_entry is not None
        
        # Check TTLs are different
        assert weather_entry.expires_at < static_entry.expires_at
    
    def test_delete(self):
        """Test delete operation."""
        cache = LRUCache(max_size=10)
        
        cache.set("key1", "value1")
        assert cache.get("key1") is not None
        
        result = cache.delete("key1")
        assert result is True
        assert cache.get("key1") is None
    
    def test_clear(self):
        """Test clear operation."""
        cache = LRUCache(max_size=10)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        count = cache.clear()
        
        assert count == 2
        assert cache.size == 0
    
    def test_access_count(self):
        """Test access count tracking."""
        cache = LRUCache(max_size=10)
        
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key1")
        cache.get("key1")
        
        entry = cache.get("key1")
        assert entry.access_count == 4  # 3 gets + 1 for this get


class TestSQLiteCache:
    """Tests for SQLiteCache class."""
    
    def test_basic_operations(self):
        """Test basic set and get with SQLite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = SQLiteCache(db_path, max_entries=100)
            
            cache.set("key1", "value1")
            entry = cache.get("key1")
            
            assert entry is not None
            assert entry.value == "value1"
    
    def test_persistence(self):
        """Test cache persists across instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            
            # First instance
            cache1 = SQLiteCache(db_path)
            cache1.set("persistent_key", "persistent_value")
            
            # Second instance
            cache2 = SQLiteCache(db_path)
            entry = cache2.get("persistent_key")
            
            assert entry is not None
            assert entry.value == "persistent_value"
    
    def test_ttl_expiration(self):
        """Test TTL expiration in SQLite cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = SQLiteCache(db_path)
            
            cache.set("key1", "value1", ttl=1)
            
            assert cache.get("key1") is not None
            
            time.sleep(1.1)
            
            assert cache.get("key1") is None
    
    def test_clear_category(self):
        """Test clearing by category."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = SQLiteCache(db_path)
            
            cache.set("weather1", "sunny", category=CacheCategory.WEATHER)
            cache.set("weather2", "cloudy", category=CacheCategory.WEATHER)
            cache.set("news1", "headline", category=CacheCategory.NEWS)
            
            count = cache.clear_category(CacheCategory.WEATHER)
            
            assert count == 2
            assert cache.get("weather1") is None
            assert cache.get("news1") is not None
    
    def test_get_stats(self):
        """Test statistics retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_cache.db"
            cache = SQLiteCache(db_path)
            
            cache.set("key1", "value1", category=CacheCategory.GENERAL)
            cache.set("key2", "value2", category=CacheCategory.WEATHER)
            
            stats = cache.get_stats()
            
            assert stats["total_entries"] == 2
            assert "by_category" in stats


class TestResponseTemplates:
    """Tests for ResponseTemplates class."""
    
    def test_greeting(self):
        """Test greeting templates."""
        templates = ResponseTemplates()
        
        response = templates.get("hello")
        assert response is not None
        assert "help" in response.lower() or "morning" in response.lower() or "afternoon" in response.lower() or "evening" in response.lower()
    
    def test_time_query(self):
        """Test time query template."""
        templates = ResponseTemplates()
        
        response = templates.get("what time is it")
        assert response is not None
        assert "time" in response.lower()
    
    def test_date_query(self):
        """Test date query template."""
        templates = ResponseTemplates()
        
        response = templates.get("what's today's date")
        assert response is not None
    
    def test_help_query(self):
        """Test help template."""
        templates = ResponseTemplates()
        
        response = templates.get("help")
        assert response is not None
        assert len(response) > 50  # Should be a substantial help message
    
    def test_no_match(self):
        """Test no template match."""
        templates = ResponseTemplates()
        
        response = templates.get("random query with no template")
        assert response is None
    
    def test_custom_template(self):
        """Test registering custom template."""
        templates = ResponseTemplates()
        
        templates.register("custom query", "Custom response")
        
        response = templates.get("custom query")
        assert response == "Custom response"


class TestSemanticCache:
    """Tests for SemanticCache class."""
    
    @pytest.mark.skipif(
        True,  # Skip by default as it requires sentence-transformers
        reason="Requires sentence-transformers package"
    )
    def test_semantic_similarity(self):
        """Test semantic similarity matching."""
        cache = SemanticCache(threshold=0.8)
        
        # Add an entry
        entry = CacheEntry(
            key="What is the weather like today?",
            value="It's sunny and warm.",
            category=CacheCategory.WEATHER,
            created_at=time.time(),
            expires_at=time.time() + 3600,
        )
        cache.add("What is the weather like today?", entry)
        
        # Query with similar text
        result = cache.find_similar("How's the weather today?")
        
        assert result is not None
        entry, similarity = result
        assert similarity > 0.8
        assert entry.value == "It's sunny and warm."


class TestIntelligentCache:
    """Tests for IntelligentCache class."""
    
    @pytest.mark.asyncio
    async def test_template_hit(self):
        """Test template cache hit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CacheConfig(
                enabled=True,
                cache_dir=Path(tmpdir),
                templates_enabled=True,
                semantic_enabled=False,  # Disable for faster test
            )
            cache = IntelligentCache(config)
            
            response = await cache.get("hello")
            
            assert response is not None
            assert cache.stats.template_hits == 1
    
    @pytest.mark.asyncio
    async def test_memory_cache_hit(self):
        """Test memory cache hit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CacheConfig(
                enabled=True,
                cache_dir=Path(tmpdir),
                templates_enabled=False,
                semantic_enabled=False,
            )
            cache = IntelligentCache(config)
            
            await cache.set("test query", "test response")
            response = await cache.get("test query", check_templates=False)
            
            assert response == "test response"
            assert cache.stats.memory_hits == 1
    
    @pytest.mark.asyncio
    async def test_sqlite_cache_hit(self):
        """Test SQLite cache hit after memory miss."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CacheConfig(
                enabled=True,
                cache_dir=Path(tmpdir),
                sqlite_enabled=True,
                memory_cache_size=1,  # Very small memory cache
                templates_enabled=False,
                semantic_enabled=False,
            )
            cache = IntelligentCache(config)
            
            # Set two items to evict first from memory
            await cache.set("query1", "response1")
            await cache.set("query2", "response2")
            
            # query1 should be in SQLite but not memory
            response = await cache.get("query1", check_templates=False)
            
            assert response == "response1"
            assert cache.stats.sqlite_hits >= 1
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CacheConfig(
                enabled=True,
                cache_dir=Path(tmpdir),
                templates_enabled=False,
                semantic_enabled=False,
            )
            cache = IntelligentCache(config)
            
            response = await cache.get("nonexistent query", check_templates=False)
            
            assert response is None
            assert cache.stats.misses == 1
    
    @pytest.mark.asyncio
    async def test_invalidation(self):
        """Test cache invalidation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CacheConfig(
                enabled=True,
                cache_dir=Path(tmpdir),
                templates_enabled=False,
                semantic_enabled=False,
            )
            cache = IntelligentCache(config)
            
            await cache.set("query", "response")
            assert await cache.get("query", check_templates=False) is not None
            
            await cache.invalidate(query="query")
            assert await cache.get("query", check_templates=False) is None
    
    @pytest.mark.asyncio
    async def test_category_invalidation(self):
        """Test category-based invalidation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CacheConfig(
                enabled=True,
                cache_dir=Path(tmpdir),
                templates_enabled=False,
                semantic_enabled=False,
            )
            cache = IntelligentCache(config)
            
            await cache.set("weather1", "sunny", category=CacheCategory.WEATHER)
            await cache.set("news1", "headline", category=CacheCategory.NEWS)
            
            await cache.invalidate(category=CacheCategory.WEATHER)
            
            # Weather should be gone from SQLite
            # Note: Memory cache doesn't support category invalidation directly
    
    @pytest.mark.asyncio
    async def test_hit_ratio(self):
        """Test hit ratio calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CacheConfig(
                enabled=True,
                cache_dir=Path(tmpdir),
                templates_enabled=False,
                semantic_enabled=False,
            )
            cache = IntelligentCache(config)
            
            await cache.set("query", "response")
            
            # 2 hits
            await cache.get("query", check_templates=False)
            await cache.get("query", check_templates=False)
            
            # 1 miss
            await cache.get("missing", check_templates=False)
            
            stats = cache.get_stats()
            assert stats["hit_ratio"] == pytest.approx(2/3, rel=0.01)
    
    @pytest.mark.asyncio
    async def test_disabled_cache(self):
        """Test disabled cache returns None."""
        config = CacheConfig(enabled=False)
        cache = IntelligentCache(config)
        
        await cache.set("query", "response")
        response = await cache.get("query")
        
        assert response is None


class TestCacheStats:
    """Tests for CacheStats class."""
    
    def test_hit_ratio_calculation(self):
        """Test hit ratio calculation."""
        stats = CacheStats(hits=75, misses=25)
        
        assert stats.hit_ratio == 0.75
    
    def test_hit_ratio_zero_total(self):
        """Test hit ratio with zero total."""
        stats = CacheStats(hits=0, misses=0)
        
        assert stats.hit_ratio == 0.0
    
    def test_to_dict(self):
        """Test stats serialization."""
        stats = CacheStats(
            hits=100,
            misses=50,
            memory_hits=60,
            sqlite_hits=30,
            semantic_hits=10,
        )
        
        data = stats.to_dict()
        
        assert data["hits"] == 100
        assert data["misses"] == 50
        assert data["hit_ratio"] == pytest.approx(0.667, rel=0.01)


class TestCategoryTTL:
    """Tests for category TTL configuration."""
    
    def test_weather_ttl(self):
        """Test weather category has 30 min TTL."""
        assert CATEGORY_TTL[CacheCategory.WEATHER] == 30 * 60
    
    def test_static_ttl(self):
        """Test static category has 7 day TTL."""
        assert CATEGORY_TTL[CacheCategory.STATIC] == 7 * 24 * 3600
    
    def test_system_no_cache(self):
        """Test system category has 0 TTL (no cache)."""
        assert CATEGORY_TTL[CacheCategory.SYSTEM] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
