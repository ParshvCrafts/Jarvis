"""
Performance Integration Module for JARVIS.

Integrates all Phase 5 performance optimization components:
- Streaming LLM responses with sentence-chunked TTS
- Multi-level intelligent caching
- Parallel execution for agents
- Performance dashboard with live metrics
- Predictive command system

This module provides a unified interface for jarvis_unified.py to use
all performance features without directly managing each component.

Usage:
    perf = PerformanceIntegration(config)
    await perf.start()
    
    # Streaming response with TTS
    response = await perf.stream_and_speak(llm_router, messages, tts)
    
    # Cached agent execution
    response = await perf.cached_agent_call(agent, query)
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Coroutine, Dict, List, Optional, Union

from loguru import logger

from .streaming import (
    StreamingResponseHandler,
    StreamingTTSQueue,
    StreamMetrics,
    SentenceChunk,
    StreamState,
)
from .performance import (
    PerformanceOptimizer,
    PerformanceConfig,
    ParallelExecutor,
    ResourceMonitor,
)
from .cache import (
    IntelligentCache,
    CacheConfig,
    CacheCategory,
    get_cache,
)
from .dashboard import (
    PerformanceDashboard,
    DashboardConfig,
    MetricsCollector,
    get_dashboard,
)
from .llm import Message, LLMResponse


@dataclass
class IntegrationConfig:
    """Configuration for performance integration."""
    # Streaming
    streaming_enabled: bool = True
    min_sentence_length: int = 10
    max_buffer_sentences: int = 5
    
    # Caching
    cache_enabled: bool = True
    cache_dir: Optional[Path] = None
    semantic_cache_enabled: bool = True
    semantic_threshold: float = 0.92
    
    # Parallel execution
    parallel_enabled: bool = True
    max_parallel_tasks: int = 5
    
    # Dashboard
    dashboard_enabled: bool = True
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8080
    
    # Predictive
    predictive_enabled: bool = True
    prediction_db_path: Optional[Path] = None
    
    # Resource monitoring
    max_memory_mb: int = 1024
    gc_threshold_mb: int = 512


class StreamingLLMIntegration:
    """
    Integrates streaming LLM responses with TTS.
    
    Provides sentence-by-sentence TTS while LLM is still generating.
    """
    
    def __init__(
        self,
        min_sentence_length: int = 10,
        max_buffer_sentences: int = 5,
        metrics_collector: Optional[MetricsCollector] = None,
    ):
        self.min_sentence_length = min_sentence_length
        self.max_buffer_sentences = max_buffer_sentences
        self.metrics_collector = metrics_collector
        
        self._current_handler: Optional[StreamingResponseHandler] = None
        self._is_streaming = False
    
    async def stream_response(
        self,
        llm_router,
        messages: List[Message],
        tts_speak: Optional[Callable[[str], Coroutine[Any, Any, None]]] = None,
        on_sentence: Optional[Callable[[str], None]] = None,
        **llm_kwargs,
    ) -> tuple[str, StreamMetrics]:
        """
        Stream LLM response with optional TTS.
        
        Args:
            llm_router: The LLM router to use for streaming.
            messages: Chat messages to send.
            tts_speak: Optional async function to speak each sentence.
            on_sentence: Optional callback for each sentence.
            **llm_kwargs: Additional arguments for LLM.
            
        Returns:
            Tuple of (full_response, metrics).
        """
        start_time = time.time()
        
        # Create streaming handler
        self._current_handler = StreamingResponseHandler(
            tts_callback=tts_speak,
            min_sentence_length=self.min_sentence_length,
            max_buffer_sentences=self.max_buffer_sentences,
        )
        
        self._is_streaming = True
        full_response = ""
        
        try:
            # Get async stream from LLM router
            stream = llm_router.astream(messages, **llm_kwargs)
            
            # Process stream through handler
            async for chunk in self._current_handler.process_stream(stream):
                if on_sentence:
                    on_sentence(chunk.text)
            
            full_response = self._current_handler.full_response
            metrics = self._current_handler.metrics
            
            # Record metrics
            if self.metrics_collector:
                self.metrics_collector.record_latency("llm", metrics.total_time)
                if metrics.time_to_first_sentence > 0:
                    self.metrics_collector.record_latency("ttfs", metrics.time_to_first_sentence)
            
            return full_response, metrics
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            # Fall back to non-streaming
            try:
                response = await llm_router.agenerate(messages, **llm_kwargs)
                full_response = response.content
                
                # Speak the full response if TTS available
                if tts_speak:
                    await tts_speak(full_response)
                
                # Create fallback metrics
                metrics = StreamMetrics()
                metrics.start_time = start_time
                metrics.end_time = time.time()
                metrics.total_sentences = 1
                metrics.total_characters = len(full_response)
                
                return full_response, metrics
                
            except Exception as fallback_error:
                logger.error(f"Fallback generation also failed: {fallback_error}")
                raise
        
        finally:
            self._is_streaming = False
            self._current_handler = None
    
    def interrupt(self) -> None:
        """Interrupt current streaming."""
        if self._current_handler:
            self._current_handler.interrupt()
    
    @property
    def is_streaming(self) -> bool:
        return self._is_streaming


class CacheIntegration:
    """
    Integrates intelligent caching with agent system.
    
    Provides cache-first query handling with semantic matching.
    """
    
    def __init__(
        self,
        cache: IntelligentCache,
        metrics_collector: Optional[MetricsCollector] = None,
    ):
        self.cache = cache
        self.metrics_collector = metrics_collector
    
    async def cached_query(
        self,
        query: str,
        generator: Callable[[], Coroutine[Any, Any, str]],
        category: CacheCategory = CacheCategory.GENERAL,
        skip_cache: bool = False,
    ) -> tuple[str, bool]:
        """
        Execute query with caching.
        
        Args:
            query: User query.
            generator: Async function to generate response if not cached.
            category: Cache category for TTL.
            skip_cache: If True, skip cache lookup.
            
        Returns:
            Tuple of (response, was_cached).
        """
        # Check if this query type should skip cache
        if skip_cache or category == CacheCategory.SYSTEM:
            response = await generator()
            return response, False
        
        # Try cache first
        cached = await self.cache.get(query)
        if cached:
            logger.debug(f"Cache hit for: {query[:50]}...")
            return cached, True
        
        # Generate response
        start_time = time.time()
        response = await generator()
        latency = (time.time() - start_time) * 1000
        
        # Record metrics
        if self.metrics_collector:
            self.metrics_collector.record_latency("agent", latency)
        
        # Cache the response
        await self.cache.set(query, response, category)
        
        return response, False
    
    def classify_query_category(self, query: str) -> CacheCategory:
        """
        Classify query into cache category.
        
        Args:
            query: User query.
            
        Returns:
            Appropriate cache category.
        """
        query_lower = query.lower()
        
        # System/IoT commands - don't cache
        if any(kw in query_lower for kw in [
            "turn on", "turn off", "lock", "unlock", "open app",
            "take screenshot", "volume", "brightness"
        ]):
            return CacheCategory.SYSTEM
        
        # Weather queries
        if any(kw in query_lower for kw in ["weather", "temperature", "forecast", "rain"]):
            return CacheCategory.WEATHER
        
        # News queries
        if any(kw in query_lower for kw in ["news", "headlines", "latest"]):
            return CacheCategory.NEWS
        
        # Calendar/schedule
        if any(kw in query_lower for kw in ["calendar", "schedule", "meeting", "appointment"]):
            return CacheCategory.CALENDAR
        
        # IoT status
        if any(kw in query_lower for kw in ["device status", "devices online", "iot"]):
            return CacheCategory.IOT
        
        # Static knowledge
        if any(kw in query_lower for kw in [
            "what is", "define", "explain", "how to", "how do",
            "meaning of", "definition"
        ]):
            return CacheCategory.STATIC
        
        return CacheCategory.GENERAL
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()


class CommandPredictor:
    """
    Predicts next likely commands based on history.
    
    Uses pattern analysis to pre-warm services and cache.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path
        self._command_history: List[tuple[str, float]] = []
        self._sequence_patterns: Dict[str, List[str]] = {}
        self._time_patterns: Dict[int, List[str]] = {}  # hour -> commands
        self._initialized = False
    
    def log_command(self, command: str) -> None:
        """Log a command for pattern analysis."""
        now = time.time()
        hour = time.localtime(now).tm_hour
        
        # Add to history
        self._command_history.append((command, now))
        
        # Trim history to last 1000 commands
        if len(self._command_history) > 1000:
            self._command_history = self._command_history[-1000:]
        
        # Update time patterns
        if hour not in self._time_patterns:
            self._time_patterns[hour] = []
        self._time_patterns[hour].append(command)
        
        # Update sequence patterns (what follows what)
        if len(self._command_history) >= 2:
            prev_command = self._command_history[-2][0]
            prev_key = self._normalize_command(prev_command)
            if prev_key not in self._sequence_patterns:
                self._sequence_patterns[prev_key] = []
            self._sequence_patterns[prev_key].append(command)
    
    def _normalize_command(self, command: str) -> str:
        """Normalize command for pattern matching."""
        # Simple normalization - could be enhanced
        return command.lower().strip()[:50]
    
    def predict_next(self, current_command: Optional[str] = None) -> List[str]:
        """
        Predict next likely commands.
        
        Args:
            current_command: Current command for sequence prediction.
            
        Returns:
            List of predicted commands (most likely first).
        """
        predictions = []
        
        # Time-based predictions
        hour = time.localtime().tm_hour
        if hour in self._time_patterns:
            time_commands = self._time_patterns[hour]
            # Count frequency
            freq = {}
            for cmd in time_commands:
                key = self._normalize_command(cmd)
                freq[key] = freq.get(key, 0) + 1
            # Sort by frequency
            sorted_cmds = sorted(freq.items(), key=lambda x: x[1], reverse=True)
            predictions.extend([cmd for cmd, _ in sorted_cmds[:3]])
        
        # Sequence-based predictions
        if current_command:
            key = self._normalize_command(current_command)
            if key in self._sequence_patterns:
                seq_commands = self._sequence_patterns[key]
                freq = {}
                for cmd in seq_commands:
                    norm = self._normalize_command(cmd)
                    freq[norm] = freq.get(norm, 0) + 1
                sorted_cmds = sorted(freq.items(), key=lambda x: x[1], reverse=True)
                predictions.extend([cmd for cmd, _ in sorted_cmds[:3]])
        
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for p in predictions:
            if p not in seen:
                seen.add(p)
                unique.append(p)
        
        return unique[:5]
    
    def get_prefetch_actions(self) -> List[str]:
        """
        Get actions to pre-fetch based on predictions.
        
        Returns:
            List of action types to pre-warm.
        """
        predictions = self.predict_next()
        actions = []
        
        for pred in predictions:
            if "weather" in pred:
                actions.append("weather")
            elif "calendar" in pred or "schedule" in pred:
                actions.append("calendar")
            elif "news" in pred:
                actions.append("news")
            elif "light" in pred or "device" in pred:
                actions.append("iot")
        
        return list(set(actions))


class ProactiveCacheManager:
    """
    Manages proactive cache pre-fetching.
    
    Pre-fetches data based on:
    - Time of day (morning weather, calendar)
    - Predicted commands
    - Idle time availability
    """
    
    def __init__(
        self,
        cache_integration: CacheIntegration,
        predictor: CommandPredictor,
        prefetch_interval: float = 300.0,  # 5 minutes
    ):
        self.cache = cache_integration
        self.predictor = predictor
        self.prefetch_interval = prefetch_interval
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._prefetch_callbacks: Dict[str, Callable[[], Coroutine[Any, Any, str]]] = {}
        self._last_prefetch: Dict[str, float] = {}
    
    def register_prefetch(
        self,
        action_type: str,
        callback: Callable[[], Coroutine[Any, Any, str]],
    ) -> None:
        """
        Register a prefetch callback for an action type.
        
        Args:
            action_type: Type of action (weather, calendar, news, etc.)
            callback: Async function that fetches and returns data.
        """
        self._prefetch_callbacks[action_type] = callback
    
    async def start(self) -> None:
        """Start the proactive cache manager."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._prefetch_loop())
        logger.info("Proactive cache manager started")
    
    async def stop(self) -> None:
        """Stop the proactive cache manager."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Proactive cache manager stopped")
    
    async def _prefetch_loop(self) -> None:
        """Background loop for proactive pre-fetching."""
        while self._running:
            try:
                await self._do_prefetch()
                await asyncio.sleep(self.prefetch_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Prefetch error: {e}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _do_prefetch(self) -> None:
        """Execute prefetch based on predictions and time."""
        now = time.time()
        hour = time.localtime(now).tm_hour
        
        # Get predicted actions
        actions = self.predictor.get_prefetch_actions()
        
        # Add time-based actions
        if 6 <= hour <= 9:  # Morning
            if "weather" not in actions:
                actions.append("weather")
            if "calendar" not in actions:
                actions.append("calendar")
        
        # Execute prefetch for each action
        for action in actions:
            # Skip if recently prefetched
            last = self._last_prefetch.get(action, 0)
            if now - last < self.prefetch_interval:
                continue
            
            # Check if callback registered
            if action not in self._prefetch_callbacks:
                continue
            
            try:
                callback = self._prefetch_callbacks[action]
                result = await callback()
                
                # Cache the result
                category = self._action_to_category(action)
                query = self._action_to_query(action)
                await self.cache.cache.set(query, result, category)
                
                self._last_prefetch[action] = now
                logger.debug(f"Prefetched: {action}")
                
            except Exception as e:
                logger.warning(f"Prefetch failed for {action}: {e}")
    
    def _action_to_category(self, action: str) -> CacheCategory:
        """Map action type to cache category."""
        mapping = {
            "weather": CacheCategory.WEATHER,
            "calendar": CacheCategory.CALENDAR,
            "news": CacheCategory.NEWS,
            "iot": CacheCategory.IOT,
        }
        return mapping.get(action, CacheCategory.GENERAL)
    
    def _action_to_query(self, action: str) -> str:
        """Map action type to cache query key."""
        mapping = {
            "weather": "what is the weather",
            "calendar": "what is on my calendar",
            "news": "what is the news",
            "iot": "device status",
        }
        return mapping.get(action, action)


class PerformanceIntegration:
    """
    Main integration class for all performance features.
    
    Provides unified interface for jarvis_unified.py.
    """
    
    def __init__(self, config: Optional[IntegrationConfig] = None):
        self.config = config or IntegrationConfig()
        
        # Initialize components
        self._streaming: Optional[StreamingLLMIntegration] = None
        self._cache_integration: Optional[CacheIntegration] = None
        self._parallel_executor: Optional[ParallelExecutor] = None
        self._dashboard: Optional[PerformanceDashboard] = None
        self._resource_monitor: Optional[ResourceMonitor] = None
        self._predictor: Optional[CommandPredictor] = None
        self._metrics_collector: Optional[MetricsCollector] = None
        self._proactive_cache: Optional[ProactiveCacheManager] = None
        
        self._started = False
    
    async def start(self) -> None:
        """Start all performance components."""
        if self._started:
            return
        
        logger.info("Starting performance integration...")
        
        # Initialize metrics collector
        self._metrics_collector = MetricsCollector()
        
        # Initialize streaming
        if self.config.streaming_enabled:
            self._streaming = StreamingLLMIntegration(
                min_sentence_length=self.config.min_sentence_length,
                max_buffer_sentences=self.config.max_buffer_sentences,
                metrics_collector=self._metrics_collector,
            )
            logger.info("Streaming integration initialized")
        
        # Initialize cache
        if self.config.cache_enabled:
            cache_config = CacheConfig(
                enabled=True,
                cache_dir=self.config.cache_dir,
                semantic_enabled=self.config.semantic_cache_enabled,
                semantic_threshold=self.config.semantic_threshold,
            )
            cache = get_cache(cache_config)
            self._cache_integration = CacheIntegration(
                cache=cache,
                metrics_collector=self._metrics_collector,
            )
            logger.info("Cache integration initialized")
        
        # Initialize parallel executor
        if self.config.parallel_enabled:
            self._parallel_executor = ParallelExecutor(
                max_parallel=self.config.max_parallel_tasks,
            )
            logger.info("Parallel executor initialized")
        
        # Initialize resource monitor
        self._resource_monitor = ResourceMonitor(
            max_memory_mb=self.config.max_memory_mb,
            gc_threshold_mb=self.config.gc_threshold_mb,
        )
        await self._resource_monitor.start_monitoring()
        logger.info("Resource monitor started")
        
        # Initialize predictor
        if self.config.predictive_enabled:
            self._predictor = CommandPredictor(
                db_path=self.config.prediction_db_path,
            )
            logger.info("Command predictor initialized")
        
        # Initialize dashboard
        if self.config.dashboard_enabled:
            dashboard_config = DashboardConfig(
                enabled=True,
                host=self.config.dashboard_host,
                port=self.config.dashboard_port,
            )
            self._dashboard = get_dashboard(dashboard_config)
            self._dashboard.metrics = self._metrics_collector
            
            # Connect data sources
            self._dashboard.set_resource_monitor(self._resource_monitor)
            if self._cache_integration:
                self._dashboard.set_cache(self._cache_integration.cache)
            
            await self._dashboard.start()
            logger.info(f"Dashboard started at http://{self.config.dashboard_host}:{self.config.dashboard_port}/dashboard")
        
        # Initialize proactive cache manager
        if self.config.predictive_enabled and self._cache_integration and self._predictor:
            self._proactive_cache = ProactiveCacheManager(
                cache_integration=self._cache_integration,
                predictor=self._predictor,
            )
            await self._proactive_cache.start()
            logger.info("Proactive cache manager started")
        
        self._started = True
        logger.info("Performance integration started")
    
    async def stop(self) -> None:
        """Stop all performance components."""
        if not self._started:
            return
        
        logger.info("Stopping performance integration...")
        
        if self._proactive_cache:
            await self._proactive_cache.stop()
        
        if self._dashboard:
            await self._dashboard.stop()
        
        if self._resource_monitor:
            await self._resource_monitor.stop_monitoring()
        
        if self._parallel_executor:
            self._parallel_executor.shutdown()
        
        self._started = False
        logger.info("Performance integration stopped")
    
    async def stream_and_speak(
        self,
        llm_router,
        messages: List[Message],
        tts_speak: Optional[Callable[[str], Coroutine[Any, Any, None]]] = None,
        **llm_kwargs,
    ) -> str:
        """
        Stream LLM response with TTS.
        
        Args:
            llm_router: LLM router for generation.
            messages: Chat messages.
            tts_speak: Async TTS function.
            **llm_kwargs: Additional LLM arguments.
            
        Returns:
            Full response text.
        """
        if not self._streaming or not self.config.streaming_enabled:
            # Fall back to non-streaming
            response = await llm_router.agenerate(messages, **llm_kwargs)
            if tts_speak:
                await tts_speak(response.content)
            return response.content
        
        response, metrics = await self._streaming.stream_response(
            llm_router, messages, tts_speak, **llm_kwargs
        )
        
        return response
    
    async def cached_agent_call(
        self,
        query: str,
        agent_func: Callable[[], Coroutine[Any, Any, str]],
        category: Optional[CacheCategory] = None,
    ) -> str:
        """
        Execute agent with caching.
        
        Args:
            query: User query.
            agent_func: Async function to call agent.
            category: Optional cache category.
            
        Returns:
            Response text.
        """
        if not self._cache_integration or not self.config.cache_enabled:
            return await agent_func()
        
        # Auto-classify if category not provided
        if category is None:
            category = self._cache_integration.classify_query_category(query)
        
        response, was_cached = await self._cache_integration.cached_query(
            query, agent_func, category
        )
        
        return response
    
    async def parallel_execute(
        self,
        tasks: List[Coroutine[Any, Any, Any]],
        timeout: Optional[float] = None,
    ) -> List[Any]:
        """
        Execute tasks in parallel.
        
        Args:
            tasks: List of coroutines to execute.
            timeout: Optional timeout.
            
        Returns:
            List of results.
        """
        if not self._parallel_executor or not self.config.parallel_enabled:
            # Sequential execution
            results = []
            for task in tasks:
                try:
                    result = await task
                    results.append(result)
                except Exception as e:
                    results.append(e)
            return results
        
        return await self._parallel_executor.execute_parallel(tasks, timeout)
    
    def log_command(self, command: str) -> None:
        """Log command for prediction."""
        if self._predictor:
            self._predictor.log_command(command)
    
    def get_predictions(self, current_command: Optional[str] = None) -> List[str]:
        """Get predicted next commands."""
        if self._predictor:
            return self._predictor.predict_next(current_command)
        return []
    
    def interrupt_streaming(self) -> None:
        """Interrupt current streaming response."""
        if self._streaming:
            self._streaming.interrupt()
    
    def record_latency(self, category: str, value_ms: float) -> None:
        """Record a latency measurement."""
        if self._metrics_collector:
            self._metrics_collector.record_latency(category, value_ms)
    
    def record_error(self, error: str, component: str = "unknown") -> None:
        """Record an error."""
        if self._metrics_collector:
            self._metrics_collector.record_error(error, component)
        if self._dashboard:
            self._dashboard.record_error(error, component)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = {
            "streaming_enabled": self.config.streaming_enabled,
            "cache_enabled": self.config.cache_enabled,
            "parallel_enabled": self.config.parallel_enabled,
            "dashboard_enabled": self.config.dashboard_enabled,
        }
        
        if self._cache_integration:
            stats["cache"] = self._cache_integration.get_stats()
        
        if self._resource_monitor:
            stats["resources"] = self._resource_monitor.get_current_metrics().to_dict()
        
        return stats
    
    @property
    def is_streaming(self) -> bool:
        """Check if currently streaming."""
        return self._streaming.is_streaming if self._streaming else False
    
    def register_prefetch(
        self,
        action_type: str,
        callback: Callable[[], Coroutine[Any, Any, str]],
    ) -> None:
        """
        Register a prefetch callback for proactive caching.
        
        Args:
            action_type: Type of action (weather, calendar, news, etc.)
            callback: Async function that fetches and returns data.
        """
        if self._proactive_cache:
            self._proactive_cache.register_prefetch(action_type, callback)


# Singleton instance
_integration: Optional[PerformanceIntegration] = None


def get_performance_integration(config: Optional[IntegrationConfig] = None) -> PerformanceIntegration:
    """Get or create the global performance integration."""
    global _integration
    if _integration is None:
        _integration = PerformanceIntegration(config)
    return _integration


async def init_performance_integration(config: Optional[IntegrationConfig] = None) -> PerformanceIntegration:
    """Initialize and start the global performance integration."""
    integration = get_performance_integration(config)
    await integration.start()
    return integration
