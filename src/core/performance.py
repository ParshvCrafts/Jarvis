"""
Performance Optimization Module for JARVIS.

Provides:
- Streaming LLM responses with sentence-chunked TTS
- Parallel processing for independent operations
- Connection pooling and keep-alive
- Resource monitoring and optimization

Usage:
    optimizer = PerformanceOptimizer(config)
    
    # Streaming response
    async for sentence in optimizer.stream_response(query):
        await tts.speak(sentence)
    
    # Parallel agent execution
    results = await optimizer.parallel_execute([task1, task2, task3])
"""

from __future__ import annotations

import asyncio
import gc
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

from loguru import logger

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from .streaming import (
    StreamingResponseHandler,
    StreamingTTSQueue,
    StreamMetrics,
    SentenceChunk,
)


T = TypeVar("T")


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization."""
    # Streaming
    streaming_enabled: bool = True
    min_sentence_length: int = 10
    max_buffer_sentences: int = 5
    
    # Parallel processing
    parallel_enabled: bool = True
    max_parallel_tasks: int = 5
    thread_pool_size: int = 4
    
    # Connection pooling
    connection_pool_size: int = 10
    connection_timeout: float = 30.0
    keepalive_timeout: float = 60.0
    
    # Resource limits
    max_memory_mb: int = 1024
    gc_threshold_mb: int = 512
    idle_gc_interval: float = 300.0  # 5 minutes
    
    # Timeouts
    default_timeout: float = 30.0
    streaming_timeout: float = 120.0


@dataclass
class ResourceMetrics:
    """System resource metrics."""
    timestamp: float = field(default_factory=time.time)
    memory_used_mb: float = 0.0
    memory_percent: float = 0.0
    cpu_percent: float = 0.0
    active_tasks: int = 0
    active_connections: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "memory_used_mb": round(self.memory_used_mb, 2),
            "memory_percent": round(self.memory_percent, 2),
            "cpu_percent": round(self.cpu_percent, 2),
            "active_tasks": self.active_tasks,
            "active_connections": self.active_connections,
        }


class ConnectionPool:
    """
    HTTP connection pool for efficient API calls.
    
    Maintains persistent connections to reduce latency.
    """
    
    def __init__(
        self,
        pool_size: int = 10,
        timeout: float = 30.0,
        keepalive_timeout: float = 60.0,
    ):
        self.pool_size = pool_size
        self.timeout = timeout
        self.keepalive_timeout = keepalive_timeout
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create the shared session."""
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp not available")
        
        async with self._lock:
            if self._session is None or self._session.closed:
                connector = aiohttp.TCPConnector(
                    limit=self.pool_size,
                    keepalive_timeout=self.keepalive_timeout,
                    enable_cleanup_closed=True,
                )
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                self._session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                )
            return self._session
    
    async def close(self) -> None:
        """Close the connection pool."""
        async with self._lock:
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
    
    @asynccontextmanager
    async def request(
        self,
        method: str,
        url: str,
        **kwargs,
    ):
        """Make a request using the pool."""
        session = await self.get_session()
        async with session.request(method, url, **kwargs) as response:
            yield response


class ParallelExecutor:
    """
    Executes tasks in parallel with resource management.
    
    Features:
    - Async task parallelization
    - Thread pool for CPU-bound operations
    - Cancellation support
    - Error aggregation
    """
    
    def __init__(
        self,
        max_parallel: int = 5,
        thread_pool_size: int = 4,
    ):
        self.max_parallel = max_parallel
        self.thread_pool_size = thread_pool_size
        
        self._semaphore = asyncio.Semaphore(max_parallel)
        self._thread_pool = ThreadPoolExecutor(max_workers=thread_pool_size)
        self._active_tasks: List[asyncio.Task] = []
    
    async def execute_parallel(
        self,
        tasks: List[Coroutine[Any, Any, T]],
        timeout: Optional[float] = None,
        return_exceptions: bool = True,
    ) -> List[Union[T, Exception]]:
        """
        Execute multiple async tasks in parallel.
        
        Args:
            tasks: List of coroutines to execute.
            timeout: Optional timeout for all tasks.
            return_exceptions: If True, return exceptions instead of raising.
            
        Returns:
            List of results (or exceptions if return_exceptions=True).
        """
        async def wrapped_task(coro: Coroutine) -> Any:
            async with self._semaphore:
                return await coro
        
        wrapped = [wrapped_task(t) for t in tasks]
        
        try:
            if timeout:
                results = await asyncio.wait_for(
                    asyncio.gather(*wrapped, return_exceptions=return_exceptions),
                    timeout=timeout,
                )
            else:
                results = await asyncio.gather(*wrapped, return_exceptions=return_exceptions)
            
            return results
            
        except asyncio.TimeoutError:
            logger.warning(f"Parallel execution timed out after {timeout}s")
            raise
    
    async def execute_with_priority(
        self,
        tasks: List[Tuple[int, Coroutine[Any, Any, T]]],
        timeout: Optional[float] = None,
    ) -> List[T]:
        """
        Execute tasks with priority ordering.
        
        Args:
            tasks: List of (priority, coroutine) tuples. Lower priority = run first.
            timeout: Optional timeout.
            
        Returns:
            Results in original order.
        """
        # Sort by priority
        indexed_tasks = [(i, p, t) for i, (p, t) in enumerate(tasks)]
        indexed_tasks.sort(key=lambda x: x[1])
        
        # Execute in priority order
        results = [None] * len(tasks)
        coros = [t for _, _, t in indexed_tasks]
        
        executed = await self.execute_parallel(coros, timeout)
        
        # Restore original order
        for (orig_idx, _, _), result in zip(indexed_tasks, executed):
            results[orig_idx] = result
        
        return results
    
    def run_in_thread(
        self,
        func: Callable[..., T],
        *args,
        **kwargs,
    ) -> asyncio.Future[T]:
        """
        Run a blocking function in the thread pool.
        
        Args:
            func: Blocking function to run.
            *args: Positional arguments.
            **kwargs: Keyword arguments.
            
        Returns:
            Future with the result.
        """
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(
            self._thread_pool,
            lambda: func(*args, **kwargs),
        )
    
    def cancel_all(self) -> None:
        """Cancel all active tasks."""
        for task in self._active_tasks:
            if not task.done():
                task.cancel()
        self._active_tasks.clear()
    
    def shutdown(self) -> None:
        """Shutdown the executor."""
        self.cancel_all()
        self._thread_pool.shutdown(wait=False)


class ResourceMonitor:
    """
    Monitors system resources and triggers optimization.
    
    Features:
    - Memory usage tracking
    - CPU usage tracking
    - Automatic garbage collection
    - Resource alerts
    """
    
    def __init__(
        self,
        max_memory_mb: int = 1024,
        gc_threshold_mb: int = 512,
        check_interval: float = 10.0,
    ):
        self.max_memory_mb = max_memory_mb
        self.gc_threshold_mb = gc_threshold_mb
        self.check_interval = check_interval
        
        self._metrics_history: List[ResourceMetrics] = []
        self._max_history = 100
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._on_high_memory: Optional[Callable[[], Coroutine]] = None
        self._on_high_cpu: Optional[Callable[[], Coroutine]] = None
    
    def get_current_metrics(self) -> ResourceMetrics:
        """Get current resource metrics."""
        metrics = ResourceMetrics()
        
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            memory_info = process.memory_info()
            
            metrics.memory_used_mb = memory_info.rss / (1024 * 1024)
            metrics.memory_percent = process.memory_percent()
            metrics.cpu_percent = process.cpu_percent(interval=0.1)
        
        metrics.active_tasks = len(asyncio.all_tasks())
        
        return metrics
    
    async def start_monitoring(self) -> None:
        """Start background resource monitoring."""
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring:
            try:
                metrics = self.get_current_metrics()
                self._metrics_history.append(metrics)
                
                # Trim history
                if len(self._metrics_history) > self._max_history:
                    self._metrics_history = self._metrics_history[-self._max_history:]
                
                # Check thresholds
                if metrics.memory_used_mb > self.gc_threshold_mb:
                    logger.debug(f"Memory above threshold ({metrics.memory_used_mb:.1f}MB), running GC")
                    gc.collect()
                
                if metrics.memory_used_mb > self.max_memory_mb:
                    logger.warning(f"Memory critical ({metrics.memory_used_mb:.1f}MB)")
                    if self._on_high_memory:
                        await self._on_high_memory()
                
                if metrics.cpu_percent > 90:
                    logger.warning(f"CPU critical ({metrics.cpu_percent:.1f}%)")
                    if self._on_high_cpu:
                        await self._on_high_cpu()
                
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(self.check_interval)
    
    def force_gc(self) -> int:
        """Force garbage collection."""
        return gc.collect()
    
    def get_metrics_history(self) -> List[Dict[str, Any]]:
        """Get metrics history."""
        return [m.to_dict() for m in self._metrics_history]
    
    def on_high_memory(self, callback: Callable[[], Coroutine]) -> None:
        """Set callback for high memory condition."""
        self._on_high_memory = callback
    
    def on_high_cpu(self, callback: Callable[[], Coroutine]) -> None:
        """Set callback for high CPU condition."""
        self._on_high_cpu = callback


class PerformanceOptimizer:
    """
    Main performance optimization coordinator.
    
    Integrates:
    - Streaming response handling
    - Parallel execution
    - Connection pooling
    - Resource monitoring
    """
    
    def __init__(self, config: Optional[PerformanceConfig] = None):
        self.config = config or PerformanceConfig()
        
        # Initialize components
        self.parallel_executor = ParallelExecutor(
            max_parallel=self.config.max_parallel_tasks,
            thread_pool_size=self.config.thread_pool_size,
        )
        
        self.resource_monitor = ResourceMonitor(
            max_memory_mb=self.config.max_memory_mb,
            gc_threshold_mb=self.config.gc_threshold_mb,
        )
        
        self.connection_pool: Optional[ConnectionPool] = None
        if AIOHTTP_AVAILABLE:
            self.connection_pool = ConnectionPool(
                pool_size=self.config.connection_pool_size,
                timeout=self.config.connection_timeout,
                keepalive_timeout=self.config.keepalive_timeout,
            )
        
        self._streaming_handler: Optional[StreamingResponseHandler] = None
        self._tts_queue: Optional[StreamingTTSQueue] = None
        
        # Metrics
        self._total_streams = 0
        self._total_parallel_executions = 0
        self._stream_metrics: List[StreamMetrics] = []
    
    async def start(self) -> None:
        """Start the optimizer."""
        await self.resource_monitor.start_monitoring()
        logger.info("Performance optimizer started")
    
    async def stop(self) -> None:
        """Stop the optimizer."""
        await self.resource_monitor.stop_monitoring()
        
        if self.connection_pool:
            await self.connection_pool.close()
        
        self.parallel_executor.shutdown()
        logger.info("Performance optimizer stopped")
    
    async def stream_llm_response(
        self,
        stream: AsyncIterator[str],
        tts_callback: Optional[Callable[[str], Coroutine[Any, Any, None]]] = None,
    ) -> AsyncIterator[SentenceChunk]:
        """
        Process a streaming LLM response with optional TTS.
        
        Args:
            stream: Async iterator of LLM tokens.
            tts_callback: Optional async function to speak sentences.
            
        Yields:
            SentenceChunk for each complete sentence.
        """
        if not self.config.streaming_enabled:
            # Fallback: collect all tokens and yield as single chunk
            full_text = ""
            async for token in stream:
                full_text += token
            
            yield SentenceChunk(text=full_text, index=0, is_final=True)
            return
        
        handler = StreamingResponseHandler(
            tts_callback=tts_callback,
            min_sentence_length=self.config.min_sentence_length,
            max_buffer_sentences=self.config.max_buffer_sentences,
        )
        
        self._streaming_handler = handler
        self._total_streams += 1
        
        try:
            async for chunk in handler.process_stream(stream, start_tts=True):
                yield chunk
        finally:
            self._stream_metrics.append(handler.metrics)
            self._streaming_handler = None
    
    async def execute_parallel(
        self,
        tasks: List[Coroutine[Any, Any, T]],
        timeout: Optional[float] = None,
    ) -> List[Union[T, Exception]]:
        """
        Execute tasks in parallel.
        
        Args:
            tasks: List of coroutines to execute.
            timeout: Optional timeout.
            
        Returns:
            List of results.
        """
        if not self.config.parallel_enabled or len(tasks) == 1:
            # Sequential execution
            results = []
            for task in tasks:
                try:
                    result = await task
                    results.append(result)
                except Exception as e:
                    results.append(e)
            return results
        
        self._total_parallel_executions += 1
        return await self.parallel_executor.execute_parallel(
            tasks,
            timeout=timeout or self.config.default_timeout,
        )
    
    def interrupt_stream(self) -> None:
        """Interrupt the current streaming response."""
        if self._streaming_handler:
            self._streaming_handler.interrupt()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        recent_metrics = self._stream_metrics[-10:] if self._stream_metrics else []
        
        avg_ttfs = 0.0
        if recent_metrics:
            ttfs_values = [m.time_to_first_sentence for m in recent_metrics if m.time_to_first_sentence > 0]
            if ttfs_values:
                avg_ttfs = sum(ttfs_values) / len(ttfs_values)
        
        return {
            "total_streams": self._total_streams,
            "total_parallel_executions": self._total_parallel_executions,
            "avg_time_to_first_sentence_ms": round(avg_ttfs, 2),
            "resource_metrics": self.resource_monitor.get_current_metrics().to_dict(),
            "streaming_enabled": self.config.streaming_enabled,
            "parallel_enabled": self.config.parallel_enabled,
        }


# Singleton instance
_optimizer: Optional[PerformanceOptimizer] = None


def get_performance_optimizer(config: Optional[PerformanceConfig] = None) -> PerformanceOptimizer:
    """Get or create the global performance optimizer."""
    global _optimizer
    if _optimizer is None:
        _optimizer = PerformanceOptimizer(config)
    return _optimizer


async def init_performance_optimizer(config: Optional[PerformanceConfig] = None) -> PerformanceOptimizer:
    """Initialize and start the global performance optimizer."""
    optimizer = get_performance_optimizer(config)
    await optimizer.start()
    return optimizer
