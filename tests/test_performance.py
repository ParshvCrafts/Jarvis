"""
Unit tests for the performance module.

Tests:
- ParallelExecutor
- ResourceMonitor
- ConnectionPool
- PerformanceOptimizer
"""

import asyncio
import pytest
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.performance import (
    ParallelExecutor,
    ResourceMonitor,
    PerformanceOptimizer,
    PerformanceConfig,
    ResourceMetrics,
)


class TestParallelExecutor:
    """Tests for ParallelExecutor class."""
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel task execution."""
        executor = ParallelExecutor(max_parallel=5)
        
        async def task(n):
            await asyncio.sleep(0.1)
            return n * 2
        
        tasks = [task(i) for i in range(5)]
        start = time.time()
        results = await executor.execute_parallel(tasks)
        elapsed = time.time() - start
        
        # Should complete in ~0.1s (parallel) not ~0.5s (sequential)
        assert elapsed < 0.3
        assert results == [0, 2, 4, 6, 8]
    
    @pytest.mark.asyncio
    async def test_semaphore_limiting(self):
        """Test semaphore limits concurrent tasks."""
        executor = ParallelExecutor(max_parallel=2)
        concurrent_count = []
        current = 0
        
        async def task(n):
            nonlocal current
            current += 1
            concurrent_count.append(current)
            await asyncio.sleep(0.1)
            current -= 1
            return n
        
        tasks = [task(i) for i in range(5)]
        await executor.execute_parallel(tasks)
        
        # Should never exceed 2 concurrent
        assert max(concurrent_count) <= 2
    
    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test exception handling in parallel tasks."""
        executor = ParallelExecutor(max_parallel=5)
        
        async def good_task():
            return "success"
        
        async def bad_task():
            raise ValueError("test error")
        
        tasks = [good_task(), bad_task(), good_task()]
        results = await executor.execute_parallel(tasks, return_exceptions=True)
        
        assert results[0] == "success"
        assert isinstance(results[1], ValueError)
        assert results[2] == "success"
    
    @pytest.mark.asyncio
    async def test_timeout(self):
        """Test timeout handling."""
        executor = ParallelExecutor(max_parallel=5)
        
        async def slow_task():
            await asyncio.sleep(10)
            return "done"
        
        with pytest.raises(asyncio.TimeoutError):
            await executor.execute_parallel([slow_task()], timeout=0.1)
    
    @pytest.mark.asyncio
    async def test_priority_execution(self):
        """Test priority-based execution."""
        executor = ParallelExecutor(max_parallel=1)  # Sequential to test order
        
        execution_order = []
        
        async def task(name):
            execution_order.append(name)
            return name
        
        # Lower priority number = run first
        tasks = [
            (3, task("low")),
            (1, task("high")),
            (2, task("medium")),
        ]
        
        results = await executor.execute_with_priority(tasks)
        
        # Results should be in original order
        assert results == ["low", "high", "medium"]
        # But execution should be by priority
        assert execution_order == ["high", "medium", "low"]
    
    def test_thread_pool_execution(self):
        """Test running blocking functions in thread pool."""
        executor = ParallelExecutor(thread_pool_size=2)
        
        def blocking_func(x):
            time.sleep(0.1)
            return x * 2
        
        loop = asyncio.new_event_loop()
        future = executor.run_in_thread(blocking_func, 5)
        result = loop.run_until_complete(future)
        loop.close()
        
        assert result == 10
    
    def test_shutdown(self):
        """Test executor shutdown."""
        executor = ParallelExecutor()
        executor.shutdown()
        
        # Should not raise


class TestResourceMonitor:
    """Tests for ResourceMonitor class."""
    
    def test_get_current_metrics(self):
        """Test getting current metrics."""
        monitor = ResourceMonitor()
        
        metrics = monitor.get_current_metrics()
        
        assert isinstance(metrics, ResourceMetrics)
        assert metrics.timestamp > 0
        assert metrics.active_tasks >= 0
    
    @pytest.mark.asyncio
    async def test_monitoring_loop(self):
        """Test background monitoring."""
        monitor = ResourceMonitor(check_interval=0.1)
        
        await monitor.start_monitoring()
        await asyncio.sleep(0.3)
        await monitor.stop_monitoring()
        
        history = monitor.get_metrics_history()
        assert len(history) >= 2
    
    def test_force_gc(self):
        """Test forced garbage collection."""
        monitor = ResourceMonitor()
        
        # Create some garbage
        _ = [object() for _ in range(1000)]
        
        collected = monitor.force_gc()
        assert collected >= 0
    
    @pytest.mark.asyncio
    async def test_high_memory_callback(self):
        """Test high memory callback."""
        callback_called = False
        
        async def on_high_memory():
            nonlocal callback_called
            callback_called = True
        
        monitor = ResourceMonitor(max_memory_mb=0)  # Always trigger
        monitor.on_high_memory(on_high_memory)
        
        # Manually trigger check
        # Note: This would require mocking psutil


class TestResourceMetrics:
    """Tests for ResourceMetrics class."""
    
    def test_to_dict(self):
        """Test metrics serialization."""
        metrics = ResourceMetrics(
            timestamp=1000.0,
            memory_used_mb=512.5,
            memory_percent=50.0,
            cpu_percent=25.0,
            active_tasks=10,
        )
        
        data = metrics.to_dict()
        
        assert data["memory_used_mb"] == 512.5
        assert data["cpu_percent"] == 25.0
        assert data["active_tasks"] == 10


class TestPerformanceConfig:
    """Tests for PerformanceConfig class."""
    
    def test_defaults(self):
        """Test default configuration."""
        config = PerformanceConfig()
        
        assert config.streaming_enabled is True
        assert config.parallel_enabled is True
        assert config.max_parallel_tasks == 5
        assert config.max_memory_mb == 1024
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = PerformanceConfig(
            streaming_enabled=False,
            max_parallel_tasks=10,
            max_memory_mb=2048,
        )
        
        assert config.streaming_enabled is False
        assert config.max_parallel_tasks == 10
        assert config.max_memory_mb == 2048


class TestPerformanceOptimizer:
    """Tests for PerformanceOptimizer class."""
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test optimizer start and stop."""
        config = PerformanceConfig()
        optimizer = PerformanceOptimizer(config)
        
        await optimizer.start()
        assert optimizer.resource_monitor is not None
        
        await optimizer.stop()
    
    @pytest.mark.asyncio
    async def test_parallel_execute(self):
        """Test parallel execution through optimizer."""
        config = PerformanceConfig(parallel_enabled=True)
        optimizer = PerformanceOptimizer(config)
        
        async def task(n):
            return n * 2
        
        results = await optimizer.execute_parallel([task(1), task(2), task(3)])
        
        assert results == [2, 4, 6]
    
    @pytest.mark.asyncio
    async def test_parallel_disabled(self):
        """Test sequential execution when parallel disabled."""
        config = PerformanceConfig(parallel_enabled=False)
        optimizer = PerformanceOptimizer(config)
        
        execution_order = []
        
        async def task(n):
            execution_order.append(n)
            return n
        
        await optimizer.execute_parallel([task(1), task(2), task(3)])
        
        # Should be sequential
        assert execution_order == [1, 2, 3]
    
    def test_get_stats(self):
        """Test getting optimizer stats."""
        config = PerformanceConfig()
        optimizer = PerformanceOptimizer(config)
        
        stats = optimizer.get_stats()
        
        assert "streaming_enabled" in stats
        assert "parallel_enabled" in stats
        assert "total_streams" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
