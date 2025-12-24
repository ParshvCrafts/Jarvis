# JARVIS Performance Baseline

This document establishes expected performance metrics and benchmarking procedures for JARVIS.

## Target Performance Metrics

### Response Latency

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| Time to First Audio (streaming) | < 1.0s | < 2.0s | > 3.0s |
| End-to-End Response | < 3.0s | < 5.0s | > 8.0s |
| Wake Word Detection | < 100ms | < 200ms | > 500ms |
| STT Processing | < 500ms | < 1.0s | > 2.0s |
| TTS Generation | < 300ms | < 500ms | > 1.0s |

### Cache Performance

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| Cache Hit Ratio | > 60% | > 40% | < 20% |
| Memory Cache Lookup | < 1ms | < 5ms | > 10ms |
| SQLite Cache Lookup | < 10ms | < 50ms | > 100ms |
| Semantic Cache Lookup | < 100ms | < 200ms | > 500ms |

### Resource Usage

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| Idle Memory | < 500MB | < 800MB | > 1GB |
| Active Memory | < 1GB | < 1.5GB | > 2GB |
| Idle CPU | < 5% | < 10% | > 20% |
| Active CPU | < 50% | < 70% | > 90% |

### Stability

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| Memory Growth (8hr) | < 50MB | < 100MB | > 200MB |
| Uptime | > 99% | > 95% | < 90% |
| Error Rate | < 1% | < 5% | > 10% |

## Benchmarking Procedures

### Quick Performance Check

```bash
# Run the benchmark script
python scripts/benchmark.py

# Expected output includes:
# - LLM response times per provider
# - Cache hit/miss statistics
# - Memory usage before/after
```

### Manual Latency Test

```python
import time
from src.core.performance_integration import get_performance_integration

perf = get_performance_integration()

# Test cache
start = time.time()
# ... run query
elapsed = (time.time() - start) * 1000
print(f"Query latency: {elapsed:.1f}ms")
```

### Dashboard Monitoring

1. Start JARVIS: `python run.py --text`
2. Open dashboard: `http://localhost:8080/dashboard`
3. Monitor real-time metrics:
   - Latency charts (STT, LLM, TTS, E2E)
   - Cache hit ratio
   - Memory/CPU usage
   - Error log

## Performance Optimization Checklist

### Before Deployment

- [ ] Run benchmark script
- [ ] Verify cache is enabled
- [ ] Check streaming is working
- [ ] Confirm dashboard shows live data
- [ ] Test with expected query volume

### Ongoing Monitoring

- [ ] Check dashboard daily for anomalies
- [ ] Review cache hit ratio weekly
- [ ] Monitor memory growth over time
- [ ] Check error logs for patterns

## Configuration for Optimal Performance

### Recommended Settings (settings.yaml)

```yaml
performance:
  streaming:
    enabled: true
    min_sentence_length: 10
  parallel:
    enabled: true
    max_tasks: 5
  resources:
    max_memory_mb: 1024
    gc_threshold_mb: 512

cache:
  enabled: true
  memory:
    size: 100
  sqlite:
    enabled: true
  semantic:
    enabled: true
    threshold: 0.92

dashboard:
  enabled: true
  port: 8080
```

### Low-Memory Configuration

For systems with limited RAM (< 4GB):

```yaml
cache:
  memory:
    size: 50
  semantic:
    enabled: false  # Saves ~500MB

performance:
  resources:
    max_memory_mb: 512
    gc_threshold_mb: 256
```

### High-Performance Configuration

For systems with ample resources:

```yaml
cache:
  memory:
    size: 500
  semantic:
    enabled: true
    cache_size: 5000

performance:
  parallel:
    max_tasks: 10
    thread_pool_size: 8
```

## Troubleshooting Performance Issues

### Slow Responses

1. Check LLM provider status in dashboard
2. Verify streaming is enabled
3. Check cache hit ratio (should be > 40%)
4. Review network latency to LLM providers

### High Memory Usage

1. Check for memory leaks in dashboard
2. Reduce cache sizes
3. Disable semantic cache
4. Lower `max_memory_mb` to trigger earlier GC

### Low Cache Hit Ratio

1. Verify cache is enabled
2. Check query patterns (unique queries won't cache)
3. Consider enabling semantic cache for similar queries
4. Review TTL settings for your use case

## Reference Hardware

These benchmarks were established on:

- **CPU**: Intel Core i7-10700 (8 cores)
- **RAM**: 16GB DDR4
- **Storage**: NVMe SSD
- **OS**: Windows 11
- **Python**: 3.11

Adjust expectations based on your hardware capabilities.

---

*JARVIS v2.0.0 - Phase 5.6 Performance Baseline*
