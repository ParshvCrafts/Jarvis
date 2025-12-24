#!/usr/bin/env python3
"""
JARVIS Performance Benchmark Suite

Measures latency and throughput for critical paths:
- Wake word detection
- Speech-to-text
- Intent classification
- Agent execution
- LLM response time
- TTS generation
- End-to-end response time

Usage:
    python scripts/benchmark.py [--iterations N] [--output FILE] [--quick]

Options:
    --iterations N   Number of iterations per benchmark (default: 10)
    --output FILE    Output JSON file (default: data/benchmarks/results.json)
    --quick          Run quick benchmarks only (fewer iterations)
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class BenchmarkResult:
    """Result of a single benchmark."""
    name: str
    category: str
    iterations: int
    times_ms: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_count(self) -> int:
        return len(self.times_ms)
    
    @property
    def error_count(self) -> int:
        return len(self.errors)
    
    @property
    def min_ms(self) -> float:
        return min(self.times_ms) if self.times_ms else 0
    
    @property
    def max_ms(self) -> float:
        return max(self.times_ms) if self.times_ms else 0
    
    @property
    def avg_ms(self) -> float:
        return statistics.mean(self.times_ms) if self.times_ms else 0
    
    @property
    def median_ms(self) -> float:
        return statistics.median(self.times_ms) if self.times_ms else 0
    
    @property
    def p95_ms(self) -> float:
        if len(self.times_ms) < 2:
            return self.max_ms
        sorted_times = sorted(self.times_ms)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]
    
    @property
    def stddev_ms(self) -> float:
        return statistics.stdev(self.times_ms) if len(self.times_ms) > 1 else 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "iterations": self.iterations,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "statistics": {
                "min_ms": round(self.min_ms, 2),
                "max_ms": round(self.max_ms, 2),
                "avg_ms": round(self.avg_ms, 2),
                "median_ms": round(self.median_ms, 2),
                "p95_ms": round(self.p95_ms, 2),
                "stddev_ms": round(self.stddev_ms, 2),
            },
            "raw_times_ms": [round(t, 2) for t in self.times_ms],
            "errors": self.errors[:5],  # Limit errors
            "metadata": self.metadata,
        }


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results."""
    name: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    results: List[BenchmarkResult] = field(default_factory=list)
    system_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "system_info": self.system_info,
            "summary": self._get_summary(),
            "results": [r.to_dict() for r in self.results],
        }
    
    def _get_summary(self) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.success_count > 0)
        
        return {
            "total_benchmarks": total,
            "successful": passed,
            "failed": total - passed,
            "total_iterations": sum(r.iterations for r in self.results),
        }


class PerformanceBenchmark:
    """
    Performance benchmark runner for JARVIS.
    
    Measures latency for all critical paths and generates
    detailed reports with statistics.
    """
    
    # Target latencies (in milliseconds)
    TARGETS = {
        "wake_word_detection": 100,
        "stt_transcription": 1000,
        "intent_classification": 200,
        "llm_simple_query": 2000,
        "llm_complex_query": 5000,
        "tts_generation": 500,
        "end_to_end_simple": 3000,
        "end_to_end_complex": 8000,
    }
    
    def __init__(self, iterations: int = 10, verbose: bool = True):
        self.iterations = iterations
        self.verbose = verbose
        self.suite = BenchmarkSuite(name="JARVIS Performance Benchmarks")
        self._collect_system_info()
    
    def _collect_system_info(self) -> None:
        """Collect system information."""
        import platform
        
        self.suite.system_info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
        }
        
        try:
            import psutil
            mem = psutil.virtual_memory()
            self.suite.system_info["total_ram_gb"] = round(mem.total / (1024**3), 1)
            self.suite.system_info["cpu_count"] = psutil.cpu_count()
        except ImportError:
            pass
        
        try:
            import torch
            self.suite.system_info["cuda_available"] = torch.cuda.is_available()
            if torch.cuda.is_available():
                self.suite.system_info["cuda_device"] = torch.cuda.get_device_name(0)
        except ImportError:
            self.suite.system_info["cuda_available"] = False
    
    def _log(self, message: str) -> None:
        """Log message if verbose."""
        if self.verbose:
            print(message)
    
    async def _run_benchmark(
        self,
        name: str,
        category: str,
        func: Callable,
        iterations: Optional[int] = None,
        warmup: int = 1,
        **metadata,
    ) -> BenchmarkResult:
        """Run a single benchmark."""
        iterations = iterations or self.iterations
        result = BenchmarkResult(
            name=name,
            category=category,
            iterations=iterations,
            metadata=metadata,
        )
        
        self._log(f"  Running: {name} ({iterations} iterations)")
        
        # Warmup runs
        for _ in range(warmup):
            try:
                if asyncio.iscoroutinefunction(func):
                    await func()
                else:
                    func()
            except Exception:
                pass
        
        # Actual benchmark runs
        for i in range(iterations):
            gc.collect()  # Clean up before each run
            
            try:
                start = time.perf_counter()
                
                if asyncio.iscoroutinefunction(func):
                    await func()
                else:
                    func()
                
                elapsed_ms = (time.perf_counter() - start) * 1000
                result.times_ms.append(elapsed_ms)
                
            except Exception as e:
                result.errors.append(str(e))
        
        # Log result
        if result.success_count > 0:
            target = self.TARGETS.get(name, float("inf"))
            status = "✓" if result.avg_ms <= target else "⚠"
            self._log(f"    {status} avg={result.avg_ms:.1f}ms, p95={result.p95_ms:.1f}ms")
        else:
            self._log(f"    ✗ Failed: {result.errors[0] if result.errors else 'Unknown'}")
        
        return result
    
    # =========================================================================
    # LLM Benchmarks
    # =========================================================================
    
    async def benchmark_llm_simple(self) -> BenchmarkResult:
        """Benchmark simple LLM query."""
        try:
            from src.core.llm import LLMManager
            llm = LLMManager()
        except ImportError:
            return BenchmarkResult(
                name="llm_simple_query",
                category="llm",
                iterations=0,
                errors=["LLM manager not available"],
            )
        
        async def run():
            await llm.generate("Say 'ok'", max_tokens=10)
        
        return await self._run_benchmark(
            name="llm_simple_query",
            category="llm",
            func=run,
            query="Say 'ok'",
        )
    
    async def benchmark_llm_complex(self) -> BenchmarkResult:
        """Benchmark complex LLM query."""
        try:
            from src.core.llm import LLMManager
            llm = LLMManager()
        except ImportError:
            return BenchmarkResult(
                name="llm_complex_query",
                category="llm",
                iterations=0,
                errors=["LLM manager not available"],
            )
        
        async def run():
            await llm.generate(
                "Explain the concept of recursion in programming with an example.",
                max_tokens=200,
            )
        
        return await self._run_benchmark(
            name="llm_complex_query",
            category="llm",
            func=run,
            iterations=5,  # Fewer iterations for complex queries
        )
    
    # =========================================================================
    # Voice Benchmarks
    # =========================================================================
    
    async def benchmark_stt(self) -> BenchmarkResult:
        """Benchmark speech-to-text."""
        try:
            from src.voice import EnhancedSpeechToText
            import numpy as np
            
            stt = EnhancedSpeechToText()
            # Generate 2 seconds of random audio
            audio = np.random.randn(32000).astype(np.float32) * 0.1
        except ImportError as e:
            return BenchmarkResult(
                name="stt_transcription",
                category="voice",
                iterations=0,
                errors=[f"STT not available: {e}"],
            )
        
        def run():
            stt.transcribe(audio, sample_rate=16000)
        
        return await self._run_benchmark(
            name="stt_transcription",
            category="voice",
            func=run,
            iterations=5,
            audio_duration_s=2.0,
        )
    
    async def benchmark_tts(self) -> BenchmarkResult:
        """Benchmark text-to-speech generation."""
        try:
            from src.voice import TextToSpeech
            tts = TextToSpeech()
        except ImportError as e:
            return BenchmarkResult(
                name="tts_generation",
                category="voice",
                iterations=0,
                errors=[f"TTS not available: {e}"],
            )
        
        def run():
            # Generate but don't play
            tts.generate_audio("Hello, this is a test of the text to speech system.")
        
        return await self._run_benchmark(
            name="tts_generation",
            category="voice",
            func=run,
            text_length=50,
        )
    
    async def benchmark_vad(self) -> BenchmarkResult:
        """Benchmark voice activity detection."""
        try:
            from src.voice import EnhancedSileroVAD
            import numpy as np
            
            vad = EnhancedSileroVAD()
            # 100ms audio chunk
            audio = np.random.randn(1600).astype(np.float32) * 0.1
        except ImportError as e:
            return BenchmarkResult(
                name="vad_detection",
                category="voice",
                iterations=0,
                errors=[f"VAD not available: {e}"],
            )
        
        def run():
            vad.is_speech(audio)
        
        return await self._run_benchmark(
            name="vad_detection",
            category="voice",
            func=run,
            iterations=100,  # VAD should be very fast
            chunk_ms=100,
        )
    
    # =========================================================================
    # Agent Benchmarks
    # =========================================================================
    
    async def benchmark_intent_classification(self) -> BenchmarkResult:
        """Benchmark intent classification."""
        try:
            from src.agents import EnhancedSupervisor
            supervisor = EnhancedSupervisor()
        except ImportError:
            try:
                from src.agents import AgentSupervisor
                supervisor = AgentSupervisor()
            except ImportError as e:
                return BenchmarkResult(
                    name="intent_classification",
                    category="agent",
                    iterations=0,
                    errors=[f"Supervisor not available: {e}"],
                )
        
        queries = [
            "What time is it?",
            "Search for Python tutorials",
            "Open Chrome",
            "Turn on the lights",
        ]
        
        async def run():
            for query in queries:
                await supervisor.classify_intent(query)
        
        return await self._run_benchmark(
            name="intent_classification",
            category="agent",
            func=run,
            queries_per_iteration=len(queries),
        )
    
    # =========================================================================
    # Memory Benchmarks
    # =========================================================================
    
    async def benchmark_memory_add(self) -> BenchmarkResult:
        """Benchmark memory add operation."""
        try:
            from src.memory import ConversationMemory
            memory = ConversationMemory()
        except ImportError as e:
            return BenchmarkResult(
                name="memory_add",
                category="memory",
                iterations=0,
                errors=[f"Memory not available: {e}"],
            )
        
        def run():
            memory.add_message("user", "Test message for benchmarking")
            memory.add_message("assistant", "Response message for benchmarking")
        
        result = await self._run_benchmark(
            name="memory_add",
            category="memory",
            func=run,
            iterations=100,
        )
        
        memory.clear()
        return result
    
    async def benchmark_memory_search(self) -> BenchmarkResult:
        """Benchmark memory search operation."""
        try:
            from src.memory import VectorMemory
            memory = VectorMemory()
            
            # Add some test data
            for i in range(100):
                memory.add(f"Test document {i} about topic {i % 10}")
        except ImportError as e:
            return BenchmarkResult(
                name="memory_search",
                category="memory",
                iterations=0,
                errors=[f"Vector memory not available: {e}"],
            )
        
        def run():
            memory.search("topic 5", k=5)
        
        return await self._run_benchmark(
            name="memory_search",
            category="memory",
            func=run,
            iterations=50,
        )
    
    # =========================================================================
    # End-to-End Benchmarks
    # =========================================================================
    
    async def benchmark_e2e_simple(self) -> BenchmarkResult:
        """Benchmark simple end-to-end query."""
        try:
            from src.core.llm import LLMManager
            from src.memory import ConversationMemory
            
            llm = LLMManager()
            memory = ConversationMemory()
        except ImportError as e:
            return BenchmarkResult(
                name="end_to_end_simple",
                category="e2e",
                iterations=0,
                errors=[f"Components not available: {e}"],
            )
        
        async def run():
            query = "What is 2+2?"
            memory.add_message("user", query)
            response = await llm.generate(query, max_tokens=20)
            memory.add_message("assistant", response.content)
        
        result = await self._run_benchmark(
            name="end_to_end_simple",
            category="e2e",
            func=run,
            iterations=5,
            query="What is 2+2?",
        )
        
        memory.clear()
        return result
    
    async def benchmark_e2e_with_tools(self) -> BenchmarkResult:
        """Benchmark end-to-end with tool usage."""
        try:
            from src.agents import EnhancedSupervisor
            supervisor = EnhancedSupervisor()
        except ImportError as e:
            return BenchmarkResult(
                name="end_to_end_with_tools",
                category="e2e",
                iterations=0,
                errors=[f"Supervisor not available: {e}"],
            )
        
        async def run():
            await supervisor.process("What time is it?")
        
        return await self._run_benchmark(
            name="end_to_end_with_tools",
            category="e2e",
            func=run,
            iterations=3,
        )
    
    # =========================================================================
    # Run All Benchmarks
    # =========================================================================
    
    async def run_all(self, quick: bool = False) -> BenchmarkSuite:
        """Run all benchmarks."""
        self._log("\n" + "=" * 60)
        self._log("  JARVIS PERFORMANCE BENCHMARKS")
        self._log("=" * 60)
        self._log(f"  Iterations: {self.iterations}")
        self._log(f"  Quick mode: {quick}")
        self._log("=" * 60 + "\n")
        
        if quick:
            self.iterations = max(1, self.iterations // 3)
        
        # LLM Benchmarks
        self._log("[LLM Benchmarks]")
        self.suite.results.append(await self.benchmark_llm_simple())
        if not quick:
            self.suite.results.append(await self.benchmark_llm_complex())
        
        # Voice Benchmarks
        self._log("\n[Voice Benchmarks]")
        self.suite.results.append(await self.benchmark_vad())
        self.suite.results.append(await self.benchmark_stt())
        self.suite.results.append(await self.benchmark_tts())
        
        # Agent Benchmarks
        self._log("\n[Agent Benchmarks]")
        self.suite.results.append(await self.benchmark_intent_classification())
        
        # Memory Benchmarks
        self._log("\n[Memory Benchmarks]")
        self.suite.results.append(await self.benchmark_memory_add())
        self.suite.results.append(await self.benchmark_memory_search())
        
        # End-to-End Benchmarks
        self._log("\n[End-to-End Benchmarks]")
        self.suite.results.append(await self.benchmark_e2e_simple())
        if not quick:
            self.suite.results.append(await self.benchmark_e2e_with_tools())
        
        return self.suite
    
    def print_summary(self) -> None:
        """Print benchmark summary."""
        print("\n" + "=" * 60)
        print("  BENCHMARK SUMMARY")
        print("=" * 60)
        
        # Group by category
        categories = {}
        for result in self.suite.results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)
        
        for category, results in categories.items():
            print(f"\n[{category.upper()}]")
            
            for result in results:
                target = self.TARGETS.get(result.name, float("inf"))
                
                if result.success_count > 0:
                    status = "✓" if result.avg_ms <= target else "⚠"
                    target_str = f"(target: {target}ms)" if target != float("inf") else ""
                    print(f"  {status} {result.name}")
                    print(f"      avg: {result.avg_ms:.1f}ms, p95: {result.p95_ms:.1f}ms {target_str}")
                else:
                    print(f"  ✗ {result.name}: FAILED")
        
        # Overall summary
        summary = self.suite._get_summary()
        print(f"\n{'=' * 60}")
        print(f"  Total: {summary['total_benchmarks']} benchmarks")
        print(f"  Successful: {summary['successful']}")
        print(f"  Failed: {summary['failed']}")
        print("=" * 60)
    
    def save_results(self, path: Optional[Path] = None) -> Path:
        """Save results to JSON file."""
        if path is None:
            output_dir = PROJECT_ROOT / "data" / "benchmarks"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = output_dir / f"benchmark_{timestamp}.json"
        
        with open(path, "w") as f:
            json.dump(self.suite.to_dict(), f, indent=2)
        
        return path
    
    def check_targets(self) -> Tuple[int, int]:
        """Check how many benchmarks meet targets."""
        met = 0
        total = 0
        
        for result in self.suite.results:
            if result.name in self.TARGETS and result.success_count > 0:
                total += 1
                if result.avg_ms <= self.TARGETS[result.name]:
                    met += 1
        
        return met, total


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="JARVIS Performance Benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--iterations", "-n",
        type=int,
        default=10,
        help="Number of iterations per benchmark",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output JSON file path",
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Run quick benchmarks (fewer iterations)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark(
        iterations=args.iterations,
        verbose=not args.quiet,
    )
    
    await benchmark.run_all(quick=args.quick)
    benchmark.print_summary()
    
    # Save results
    output_path = Path(args.output) if args.output else None
    saved_path = benchmark.save_results(output_path)
    print(f"\nResults saved to: {saved_path}")
    
    # Check targets
    met, total = benchmark.check_targets()
    if total > 0:
        print(f"Targets met: {met}/{total} ({met/total*100:.0f}%)")
    
    # Exit code based on target achievement
    sys.exit(0 if met == total else 1)


if __name__ == "__main__":
    asyncio.run(main())
