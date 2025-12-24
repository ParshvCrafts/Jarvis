"""
Integration tests for the performance integration module.

Tests:
- StreamingLLMIntegration
- CacheIntegration
- CommandPredictor
- PerformanceIntegration end-to-end
"""

import asyncio
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.performance_integration import (
    PerformanceIntegration,
    IntegrationConfig,
    StreamingLLMIntegration,
    CacheIntegration,
    CommandPredictor,
    get_performance_integration,
)
from core.cache import IntelligentCache, CacheConfig, CacheCategory


class TestStreamingLLMIntegration:
    """Tests for StreamingLLMIntegration class."""
    
    @pytest.mark.asyncio
    async def test_stream_response(self):
        """Test streaming response processing."""
        integration = StreamingLLMIntegration(min_sentence_length=5)
        
        # Mock LLM router
        mock_router = MagicMock()
        
        async def mock_stream(*args, **kwargs):
            for token in ["Hello", " ", "world", ".", " ", "How", " ", "are", " ", "you", "?", " "]:
                yield token
        
        mock_router.astream = mock_stream
        
        # Mock messages
        messages = [MagicMock()]
        
        response, metrics = await integration.stream_response(
            mock_router, messages
        )
        
        assert "Hello world" in response
        assert metrics.total_tokens > 0
    
    @pytest.mark.asyncio
    async def test_stream_with_tts(self):
        """Test streaming with TTS callback."""
        integration = StreamingLLMIntegration(min_sentence_length=5)
        
        spoken = []
        
        async def mock_tts(text):
            spoken.append(text)
        
        mock_router = MagicMock()
        
        async def mock_stream(*args, **kwargs):
            for token in ["First", " ", "sentence", ".", " ", "Second", " ", "one", ".", " "]:
                yield token
        
        mock_router.astream = mock_stream
        
        await integration.stream_response(
            mock_router, [MagicMock()], tts_speak=mock_tts
        )
        
        # Wait for TTS processing
        await asyncio.sleep(0.2)
        
        assert len(spoken) >= 1
    
    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        """Test fallback to non-streaming on error."""
        integration = StreamingLLMIntegration()
        
        mock_router = MagicMock()
        
        async def failing_stream(*args, **kwargs):
            raise RuntimeError("Stream failed")
            yield  # Make it a generator
        
        mock_router.astream = failing_stream
        
        # Mock fallback
        mock_response = MagicMock()
        mock_response.content = "Fallback response"
        
        async def mock_generate(*args, **kwargs):
            return mock_response
        
        mock_router.agenerate = mock_generate
        
        response, metrics = await integration.stream_response(
            mock_router, [MagicMock()]
        )
        
        assert response == "Fallback response"
    
    def test_interrupt(self):
        """Test stream interruption."""
        integration = StreamingLLMIntegration()
        
        # Should not raise when no active stream
        integration.interrupt()


class TestCacheIntegration:
    """Tests for CacheIntegration class."""
    
    @pytest.mark.asyncio
    async def test_cached_query_miss(self):
        """Test cache miss triggers generator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = IntelligentCache(CacheConfig(
                enabled=True,
                cache_dir=Path(tmpdir),
                templates_enabled=False,
                semantic_enabled=False,
            ))
            integration = CacheIntegration(cache)
            
            generator_called = False
            
            async def generator():
                nonlocal generator_called
                generator_called = True
                return "generated response"
            
            response, was_cached = await integration.cached_query(
                "test query", generator
            )
            
            assert generator_called
            assert response == "generated response"
            assert was_cached is False
    
    @pytest.mark.asyncio
    async def test_cached_query_hit(self):
        """Test cache hit returns cached value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = IntelligentCache(CacheConfig(
                enabled=True,
                cache_dir=Path(tmpdir),
                templates_enabled=False,
                semantic_enabled=False,
            ))
            integration = CacheIntegration(cache)
            
            # First call - cache miss
            async def generator():
                return "generated response"
            
            await integration.cached_query("test query", generator)
            
            # Second call - should be cache hit
            generator_called = False
            
            async def generator2():
                nonlocal generator_called
                generator_called = True
                return "new response"
            
            response, was_cached = await integration.cached_query(
                "test query", generator2
            )
            
            assert not generator_called
            assert response == "generated response"
            assert was_cached is True
    
    @pytest.mark.asyncio
    async def test_skip_cache(self):
        """Test skip_cache parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = IntelligentCache(CacheConfig(
                enabled=True,
                cache_dir=Path(tmpdir),
                templates_enabled=False,
                semantic_enabled=False,
            ))
            integration = CacheIntegration(cache)
            
            async def generator():
                return "response"
            
            response, was_cached = await integration.cached_query(
                "test query", generator, skip_cache=True
            )
            
            assert was_cached is False
    
    def test_classify_query_weather(self):
        """Test weather query classification."""
        cache = MagicMock()
        integration = CacheIntegration(cache)
        
        category = integration.classify_query_category("What's the weather like?")
        assert category == CacheCategory.WEATHER
    
    def test_classify_query_system(self):
        """Test system command classification."""
        cache = MagicMock()
        integration = CacheIntegration(cache)
        
        category = integration.classify_query_category("Turn on the lights")
        assert category == CacheCategory.SYSTEM
    
    def test_classify_query_static(self):
        """Test static knowledge classification."""
        cache = MagicMock()
        integration = CacheIntegration(cache)
        
        category = integration.classify_query_category("What is machine learning?")
        assert category == CacheCategory.STATIC
    
    def test_classify_query_general(self):
        """Test general query classification."""
        cache = MagicMock()
        integration = CacheIntegration(cache)
        
        category = integration.classify_query_category("Tell me a joke")
        assert category == CacheCategory.GENERAL


class TestCommandPredictor:
    """Tests for CommandPredictor class."""
    
    def test_log_command(self):
        """Test command logging."""
        predictor = CommandPredictor()
        
        predictor.log_command("turn on lights")
        predictor.log_command("play music")
        
        assert len(predictor._command_history) == 2
    
    def test_time_patterns(self):
        """Test time-based pattern tracking."""
        predictor = CommandPredictor()
        
        predictor.log_command("good morning")
        predictor.log_command("weather")
        
        hour = time.localtime().tm_hour
        assert hour in predictor._time_patterns
        assert len(predictor._time_patterns[hour]) == 2
    
    def test_sequence_patterns(self):
        """Test sequence pattern tracking."""
        predictor = CommandPredictor()
        
        predictor.log_command("turn on lights")
        predictor.log_command("play music")
        predictor.log_command("turn on lights")
        predictor.log_command("play music")
        
        # "turn on lights" should predict "play music"
        predictions = predictor.predict_next("turn on lights")
        
        assert len(predictions) > 0
    
    def test_predict_next_empty(self):
        """Test prediction with no history."""
        predictor = CommandPredictor()
        
        predictions = predictor.predict_next()
        
        assert predictions == []
    
    def test_get_prefetch_actions(self):
        """Test prefetch action generation."""
        predictor = CommandPredictor()
        
        predictor.log_command("what's the weather")
        predictor.log_command("show calendar")
        
        actions = predictor.get_prefetch_actions()
        
        # Should include weather and calendar
        assert "weather" in actions or "calendar" in actions
    
    def test_history_limit(self):
        """Test command history limit."""
        predictor = CommandPredictor()
        
        for i in range(1500):
            predictor.log_command(f"command {i}")
        
        # Should be trimmed to 1000
        assert len(predictor._command_history) == 1000


class TestPerformanceIntegration:
    """Tests for PerformanceIntegration class."""
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test integration start and stop."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IntegrationConfig(
                cache_dir=Path(tmpdir),
                dashboard_enabled=False,  # Disable for test
                semantic_cache_enabled=False,
            )
            integration = PerformanceIntegration(config)
            
            await integration.start()
            assert integration._started is True
            
            await integration.stop()
            assert integration._started is False
    
    @pytest.mark.asyncio
    async def test_cached_agent_call(self):
        """Test cached agent call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = IntegrationConfig(
                cache_dir=Path(tmpdir),
                cache_enabled=True,
                dashboard_enabled=False,
                semantic_cache_enabled=False,
            )
            integration = PerformanceIntegration(config)
            await integration.start()
            
            call_count = 0
            
            async def agent_func():
                nonlocal call_count
                call_count += 1
                return "agent response"
            
            # First call
            response1 = await integration.cached_agent_call("test query", agent_func)
            
            # Second call - should be cached
            response2 = await integration.cached_agent_call("test query", agent_func)
            
            assert response1 == "agent response"
            assert response2 == "agent response"
            assert call_count == 1  # Only called once
            
            await integration.stop()
    
    @pytest.mark.asyncio
    async def test_parallel_execute(self):
        """Test parallel execution."""
        config = IntegrationConfig(
            parallel_enabled=True,
            dashboard_enabled=False,
        )
        integration = PerformanceIntegration(config)
        await integration.start()
        
        async def task(n):
            return n * 2
        
        results = await integration.parallel_execute([task(1), task(2), task(3)])
        
        assert results == [2, 4, 6]
        
        await integration.stop()
    
    @pytest.mark.asyncio
    async def test_parallel_disabled(self):
        """Test sequential execution when parallel disabled."""
        config = IntegrationConfig(
            parallel_enabled=False,
            dashboard_enabled=False,
        )
        integration = PerformanceIntegration(config)
        
        async def task(n):
            return n * 2
        
        results = await integration.parallel_execute([task(1), task(2)])
        
        assert results == [2, 4]
    
    def test_log_command(self):
        """Test command logging for prediction."""
        config = IntegrationConfig(
            predictive_enabled=True,
            dashboard_enabled=False,
        )
        integration = PerformanceIntegration(config)
        integration._predictor = CommandPredictor()
        
        integration.log_command("test command")
        
        assert len(integration._predictor._command_history) == 1
    
    def test_get_predictions(self):
        """Test getting predictions."""
        config = IntegrationConfig(
            predictive_enabled=True,
            dashboard_enabled=False,
        )
        integration = PerformanceIntegration(config)
        integration._predictor = CommandPredictor()
        
        integration.log_command("lights on")
        integration.log_command("play music")
        integration.log_command("lights on")
        integration.log_command("play music")
        
        predictions = integration.get_predictions("lights on")
        
        assert len(predictions) > 0
    
    def test_get_stats(self):
        """Test getting stats."""
        config = IntegrationConfig(dashboard_enabled=False)
        integration = PerformanceIntegration(config)
        
        stats = integration.get_stats()
        
        assert "streaming_enabled" in stats
        assert "cache_enabled" in stats
        assert "parallel_enabled" in stats
    
    def test_record_latency(self):
        """Test latency recording."""
        config = IntegrationConfig(dashboard_enabled=False)
        integration = PerformanceIntegration(config)
        integration._metrics_collector = MagicMock()
        
        integration.record_latency("llm", 500.0)
        
        integration._metrics_collector.record_latency.assert_called_once_with("llm", 500.0)


class TestIntegrationConfig:
    """Tests for IntegrationConfig class."""
    
    def test_defaults(self):
        """Test default configuration."""
        config = IntegrationConfig()
        
        assert config.streaming_enabled is True
        assert config.cache_enabled is True
        assert config.parallel_enabled is True
        assert config.dashboard_enabled is True
        assert config.predictive_enabled is True
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = IntegrationConfig(
            streaming_enabled=False,
            cache_enabled=False,
            max_parallel_tasks=10,
            dashboard_port=9000,
        )
        
        assert config.streaming_enabled is False
        assert config.cache_enabled is False
        assert config.max_parallel_tasks == 10
        assert config.dashboard_port == 9000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
