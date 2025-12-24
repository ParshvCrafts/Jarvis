"""
Performance Dashboard for JARVIS.

Provides a lightweight web-based dashboard for monitoring:
- Response latency metrics
- Cache hit/miss statistics
- Resource usage (CPU, memory)
- Component health status
- Recent errors and alerts

Usage:
    dashboard = PerformanceDashboard(port=8080)
    await dashboard.start()
    # Access at http://localhost:8080/dashboard
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None
    WebSocket = None


@dataclass
class LatencyMetric:
    """A latency measurement."""
    name: str
    value_ms: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DashboardConfig:
    """Dashboard configuration."""
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8080
    update_interval: float = 2.0  # seconds
    max_history: int = 100
    alert_latency_threshold_ms: float = 5000.0
    alert_memory_threshold_percent: float = 80.0
    alert_cache_hit_threshold: float = 0.5


class MetricsCollector:
    """
    Collects and aggregates performance metrics.
    
    Provides time-series data for dashboard visualization.
    """
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        
        # Latency metrics
        self._latencies: Dict[str, List[LatencyMetric]] = {
            "stt": [],
            "llm": [],
            "tts": [],
            "e2e": [],
        }
        
        # Resource metrics
        self._resource_history: List[Dict[str, Any]] = []
        
        # Cache metrics
        self._cache_history: List[Dict[str, Any]] = []
        
        # Error log
        self._errors: List[Dict[str, Any]] = []
        
        # Alerts
        self._alerts: List[Dict[str, Any]] = []
    
    def record_latency(
        self,
        category: str,
        value_ms: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a latency measurement."""
        if category not in self._latencies:
            self._latencies[category] = []
        
        metric = LatencyMetric(
            name=category,
            value_ms=value_ms,
            metadata=metadata or {},
        )
        
        self._latencies[category].append(metric)
        
        # Trim history
        if len(self._latencies[category]) > self.max_history:
            self._latencies[category] = self._latencies[category][-self.max_history:]
    
    def record_resource_metrics(self, metrics: Dict[str, Any]) -> None:
        """Record resource usage metrics."""
        metrics["timestamp"] = time.time()
        self._resource_history.append(metrics)
        
        if len(self._resource_history) > self.max_history:
            self._resource_history = self._resource_history[-self.max_history:]
    
    def record_cache_metrics(self, metrics: Dict[str, Any]) -> None:
        """Record cache statistics."""
        metrics["timestamp"] = time.time()
        self._cache_history.append(metrics)
        
        if len(self._cache_history) > self.max_history:
            self._cache_history = self._cache_history[-self.max_history:]
    
    def record_error(self, error: str, component: str = "unknown") -> None:
        """Record an error."""
        self._errors.append({
            "timestamp": time.time(),
            "component": component,
            "error": error,
        })
        
        if len(self._errors) > self.max_history:
            self._errors = self._errors[-self.max_history:]
    
    def add_alert(self, level: str, message: str, component: str = "system") -> None:
        """Add an alert."""
        self._alerts.append({
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "component": component,
        })
        
        if len(self._alerts) > 50:
            self._alerts = self._alerts[-50:]
    
    def get_latency_stats(self, category: str) -> Dict[str, Any]:
        """Get latency statistics for a category."""
        metrics = self._latencies.get(category, [])
        if not metrics:
            return {"avg": 0, "min": 0, "max": 0, "count": 0}
        
        values = [m.value_ms for m in metrics]
        return {
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "count": len(values),
            "recent": values[-10:],
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics for dashboard."""
        return {
            "timestamp": time.time(),
            "latencies": {
                cat: self.get_latency_stats(cat)
                for cat in self._latencies
            },
            "resources": self._resource_history[-1] if self._resource_history else {},
            "resource_history": self._resource_history[-20:],
            "cache": self._cache_history[-1] if self._cache_history else {},
            "cache_history": self._cache_history[-20:],
            "errors": self._errors[-10:],
            "alerts": self._alerts[-10:],
        }


# HTML template for dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JARVIS Performance Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0f;
            color: #e0e0e0;
            min-height: 100vh;
        }
        .header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 20px;
            border-bottom: 1px solid #2a2a4a;
        }
        .header h1 {
            color: #00d4ff;
            font-size: 24px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .header h1::before {
            content: "◉";
            color: #00ff88;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .status-bar {
            display: flex;
            gap: 20px;
            margin-top: 10px;
            font-size: 14px;
        }
        .status-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #00ff88;
        }
        .status-dot.warning { background: #ffaa00; }
        .status-dot.error { background: #ff4444; }
        .container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            padding: 20px;
        }
        .card {
            background: #1a1a2e;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #2a2a4a;
        }
        .card h2 {
            color: #00d4ff;
            font-size: 16px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }
        .metric {
            background: #0a0a1a;
            padding: 15px;
            border-radius: 8px;
        }
        .metric-label {
            font-size: 12px;
            color: #888;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #00d4ff;
        }
        .metric-value.good { color: #00ff88; }
        .metric-value.warning { color: #ffaa00; }
        .metric-value.error { color: #ff4444; }
        .chart-container {
            height: 200px;
            margin-top: 15px;
        }
        .error-list {
            max-height: 200px;
            overflow-y: auto;
        }
        .error-item {
            padding: 10px;
            background: #0a0a1a;
            border-radius: 6px;
            margin-bottom: 8px;
            font-size: 13px;
            border-left: 3px solid #ff4444;
        }
        .error-time {
            color: #666;
            font-size: 11px;
        }
        .alert-item {
            padding: 10px;
            background: #0a0a1a;
            border-radius: 6px;
            margin-bottom: 8px;
            font-size: 13px;
        }
        .alert-item.warning { border-left: 3px solid #ffaa00; }
        .alert-item.error { border-left: 3px solid #ff4444; }
        .alert-item.info { border-left: 3px solid #00d4ff; }
        .progress-bar {
            height: 8px;
            background: #0a0a1a;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d4ff, #00ff88);
            transition: width 0.3s ease;
        }
        .progress-fill.warning {
            background: linear-gradient(90deg, #ffaa00, #ff8800);
        }
        .progress-fill.error {
            background: linear-gradient(90deg, #ff4444, #ff0000);
        }
        .last-update {
            text-align: right;
            font-size: 12px;
            color: #666;
            padding: 10px 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>JARVIS Performance Dashboard</h1>
        <div class="status-bar">
            <div class="status-item">
                <div class="status-dot" id="ws-status"></div>
                <span id="ws-status-text">Connecting...</span>
            </div>
            <div class="status-item">
                <span>Uptime: <span id="uptime">--</span></span>
            </div>
        </div>
    </div>
    
    <div class="container">
        <!-- Latency Card -->
        <div class="card">
            <h2>⚡ Response Latency</h2>
            <div class="metric-grid">
                <div class="metric">
                    <div class="metric-label">STT (Speech-to-Text)</div>
                    <div class="metric-value" id="latency-stt">--</div>
                </div>
                <div class="metric">
                    <div class="metric-label">LLM Response</div>
                    <div class="metric-value" id="latency-llm">--</div>
                </div>
                <div class="metric">
                    <div class="metric-label">TTS (Text-to-Speech)</div>
                    <div class="metric-value" id="latency-tts">--</div>
                </div>
                <div class="metric">
                    <div class="metric-label">End-to-End</div>
                    <div class="metric-value" id="latency-e2e">--</div>
                </div>
            </div>
            <div class="chart-container">
                <canvas id="latency-chart"></canvas>
            </div>
        </div>
        
        <!-- Cache Card -->
        <div class="card">
            <h2>💾 Cache Statistics</h2>
            <div class="metric-grid">
                <div class="metric">
                    <div class="metric-label">Hit Ratio</div>
                    <div class="metric-value" id="cache-ratio">--</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Total Hits</div>
                    <div class="metric-value" id="cache-hits">--</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Memory Cache</div>
                    <div class="metric-value" id="cache-memory">--</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Semantic Hits</div>
                    <div class="metric-value" id="cache-semantic">--</div>
                </div>
            </div>
            <div class="chart-container">
                <canvas id="cache-chart"></canvas>
            </div>
        </div>
        
        <!-- Resources Card -->
        <div class="card">
            <h2>📊 System Resources</h2>
            <div class="metric">
                <div class="metric-label">Memory Usage</div>
                <div class="metric-value" id="memory-usage">--</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="memory-bar" style="width: 0%"></div>
                </div>
            </div>
            <div class="metric" style="margin-top: 15px;">
                <div class="metric-label">CPU Usage</div>
                <div class="metric-value" id="cpu-usage">--</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="cpu-bar" style="width: 0%"></div>
                </div>
            </div>
            <div class="chart-container">
                <canvas id="resource-chart"></canvas>
            </div>
        </div>
        
        <!-- Alerts Card -->
        <div class="card">
            <h2>🔔 Alerts & Errors</h2>
            <div class="error-list" id="alerts-list">
                <div class="alert-item info">No alerts</div>
            </div>
        </div>
    </div>
    
    <div class="last-update">Last update: <span id="last-update">--</span></div>
    
    <script>
        // Charts
        let latencyChart, cacheChart, resourceChart;
        const maxDataPoints = 20;
        
        // Initialize charts
        function initCharts() {
            const chartOptions = {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { display: false },
                    y: { 
                        beginAtZero: true,
                        grid: { color: '#2a2a4a' },
                        ticks: { color: '#888' }
                    }
                },
                plugins: { legend: { display: false } },
                elements: {
                    line: { tension: 0.4 },
                    point: { radius: 0 }
                }
            };
            
            latencyChart = new Chart(document.getElementById('latency-chart'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'E2E Latency',
                        data: [],
                        borderColor: '#00d4ff',
                        backgroundColor: 'rgba(0, 212, 255, 0.1)',
                        fill: true
                    }]
                },
                options: chartOptions
            });
            
            cacheChart = new Chart(document.getElementById('cache-chart'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Hit Ratio',
                        data: [],
                        borderColor: '#00ff88',
                        backgroundColor: 'rgba(0, 255, 136, 0.1)',
                        fill: true
                    }]
                },
                options: {...chartOptions, scales: {...chartOptions.scales, y: {...chartOptions.scales.y, max: 1}}}
            });
            
            resourceChart = new Chart(document.getElementById('resource-chart'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Memory',
                            data: [],
                            borderColor: '#00d4ff',
                            fill: false
                        },
                        {
                            label: 'CPU',
                            data: [],
                            borderColor: '#ff8800',
                            fill: false
                        }
                    ]
                },
                options: {...chartOptions, scales: {...chartOptions.scales, y: {...chartOptions.scales.y, max: 100}}}
            });
        }
        
        // Update dashboard
        function updateDashboard(data) {
            // Update latencies
            const latencies = data.latencies || {};
            updateMetric('latency-stt', latencies.stt?.avg, 'ms', 1000);
            updateMetric('latency-llm', latencies.llm?.avg, 'ms', 2000);
            updateMetric('latency-tts', latencies.tts?.avg, 'ms', 500);
            updateMetric('latency-e2e', latencies.e2e?.avg, 'ms', 3000);
            
            // Update cache
            const cache = data.cache || {};
            const hitRatio = cache.hit_ratio || 0;
            document.getElementById('cache-ratio').textContent = (hitRatio * 100).toFixed(1) + '%';
            document.getElementById('cache-ratio').className = 'metric-value ' + (hitRatio > 0.6 ? 'good' : hitRatio > 0.3 ? 'warning' : 'error');
            document.getElementById('cache-hits').textContent = cache.hits || 0;
            document.getElementById('cache-memory').textContent = cache.memory_hits || 0;
            document.getElementById('cache-semantic').textContent = cache.semantic_hits || 0;
            
            // Update resources
            const resources = data.resources || {};
            const memPercent = resources.memory_percent || 0;
            const cpuPercent = resources.cpu_percent || 0;
            
            document.getElementById('memory-usage').textContent = (resources.memory_used_mb || 0).toFixed(0) + ' MB';
            document.getElementById('memory-usage').className = 'metric-value ' + (memPercent > 80 ? 'error' : memPercent > 60 ? 'warning' : 'good');
            document.getElementById('memory-bar').style.width = memPercent + '%';
            document.getElementById('memory-bar').className = 'progress-fill ' + (memPercent > 80 ? 'error' : memPercent > 60 ? 'warning' : '');
            
            document.getElementById('cpu-usage').textContent = cpuPercent.toFixed(1) + '%';
            document.getElementById('cpu-usage').className = 'metric-value ' + (cpuPercent > 80 ? 'error' : cpuPercent > 60 ? 'warning' : 'good');
            document.getElementById('cpu-bar').style.width = cpuPercent + '%';
            document.getElementById('cpu-bar').className = 'progress-fill ' + (cpuPercent > 80 ? 'error' : cpuPercent > 60 ? 'warning' : '');
            
            // Update charts
            updateChart(latencyChart, latencies.e2e?.recent || []);
            
            const cacheHistory = data.cache_history || [];
            updateChart(cacheChart, cacheHistory.map(c => c.hit_ratio || 0));
            
            const resourceHistory = data.resource_history || [];
            updateResourceChart(resourceHistory);
            
            // Update alerts
            updateAlerts(data.alerts || [], data.errors || []);
            
            // Update timestamp
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
        }
        
        function updateMetric(id, value, unit, threshold) {
            const el = document.getElementById(id);
            if (value !== undefined && value !== null) {
                el.textContent = value.toFixed(0) + ' ' + unit;
                el.className = 'metric-value ' + (value > threshold ? 'error' : value > threshold * 0.7 ? 'warning' : 'good');
            }
        }
        
        function updateChart(chart, data) {
            chart.data.labels = data.map((_, i) => i);
            chart.data.datasets[0].data = data;
            chart.update('none');
        }
        
        function updateResourceChart(history) {
            resourceChart.data.labels = history.map((_, i) => i);
            resourceChart.data.datasets[0].data = history.map(h => h.memory_percent || 0);
            resourceChart.data.datasets[1].data = history.map(h => h.cpu_percent || 0);
            resourceChart.update('none');
        }
        
        function updateAlerts(alerts, errors) {
            const list = document.getElementById('alerts-list');
            const items = [...alerts, ...errors.map(e => ({...e, level: 'error'}))];
            items.sort((a, b) => b.timestamp - a.timestamp);
            
            if (items.length === 0) {
                list.innerHTML = '<div class="alert-item info">No alerts</div>';
                return;
            }
            
            list.innerHTML = items.slice(0, 10).map(item => {
                const time = new Date(item.timestamp * 1000).toLocaleTimeString();
                const level = item.level || 'info';
                const message = item.message || item.error || 'Unknown';
                return `<div class="alert-item ${level}">
                    <div class="error-time">${time} - ${item.component || 'system'}</div>
                    ${message}
                </div>`;
            }).join('');
        }
        
        // WebSocket connection
        let ws;
        let reconnectAttempts = 0;
        
        function connect() {
            const wsUrl = `ws://${window.location.host}/ws`;
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                document.getElementById('ws-status').className = 'status-dot';
                document.getElementById('ws-status-text').textContent = 'Connected';
                reconnectAttempts = 0;
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onclose = () => {
                document.getElementById('ws-status').className = 'status-dot error';
                document.getElementById('ws-status-text').textContent = 'Disconnected';
                
                // Reconnect with backoff
                const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
                reconnectAttempts++;
                setTimeout(connect, delay);
            };
            
            ws.onerror = () => {
                document.getElementById('ws-status').className = 'status-dot warning';
                document.getElementById('ws-status-text').textContent = 'Error';
            };
        }
        
        // Initialize
        initCharts();
        connect();
    </script>
</body>
</html>
"""


class PerformanceDashboard:
    """
    Web-based performance dashboard for JARVIS.
    
    Provides real-time metrics visualization via WebSocket.
    """
    
    def __init__(self, config: Optional[DashboardConfig] = None):
        self.config = config or DashboardConfig()
        self.metrics = MetricsCollector(max_history=self.config.max_history)
        
        self._app: Optional[FastAPI] = None
        self._server_task: Optional[asyncio.Task] = None
        self._update_task: Optional[asyncio.Task] = None
        self._websockets: List[WebSocket] = []
        self._running = False
        self._start_time = time.time()
        
        # External metric sources
        self._resource_monitor = None
        self._cache = None
        self._performance_optimizer = None
    
    def set_resource_monitor(self, monitor) -> None:
        """Set the resource monitor for metrics."""
        self._resource_monitor = monitor
    
    def set_cache(self, cache) -> None:
        """Set the cache for metrics."""
        self._cache = cache
    
    def set_performance_optimizer(self, optimizer) -> None:
        """Set the performance optimizer for metrics."""
        self._performance_optimizer = optimizer
    
    def _create_app(self) -> FastAPI:
        """Create the FastAPI application."""
        if not FASTAPI_AVAILABLE:
            raise RuntimeError("FastAPI not available. Install with: pip install fastapi uvicorn")
        
        app = FastAPI(title="JARVIS Performance Dashboard")
        
        @app.get("/", response_class=HTMLResponse)
        @app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard():
            return DASHBOARD_HTML
        
        @app.get("/api/metrics")
        async def get_metrics():
            return JSONResponse(self._collect_metrics())
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self._websockets.append(websocket)
            
            try:
                while True:
                    # Keep connection alive
                    await websocket.receive_text()
            except WebSocketDisconnect:
                pass
            finally:
                if websocket in self._websockets:
                    self._websockets.remove(websocket)
        
        return app
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect all metrics from sources."""
        metrics = self.metrics.get_all_metrics()
        
        # Add resource metrics
        if self._resource_monitor:
            try:
                resource_metrics = self._resource_monitor.get_current_metrics()
                metrics["resources"] = resource_metrics.to_dict()
                self.metrics.record_resource_metrics(resource_metrics.to_dict())
            except Exception as e:
                logger.debug(f"Failed to get resource metrics: {e}")
        
        # Add cache metrics
        if self._cache:
            try:
                cache_stats = self._cache.get_stats()
                metrics["cache"] = cache_stats
                self.metrics.record_cache_metrics(cache_stats)
            except Exception as e:
                logger.debug(f"Failed to get cache metrics: {e}")
        
        # Add performance optimizer stats
        if self._performance_optimizer:
            try:
                perf_stats = self._performance_optimizer.get_stats()
                metrics["performance"] = perf_stats
            except Exception as e:
                logger.debug(f"Failed to get performance stats: {e}")
        
        # Add uptime
        metrics["uptime_seconds"] = time.time() - self._start_time
        
        return metrics
    
    async def _broadcast_metrics(self) -> None:
        """Broadcast metrics to all connected WebSocket clients."""
        while self._running:
            try:
                metrics = self._collect_metrics()
                
                # Check for alerts
                self._check_alerts(metrics)
                
                # Broadcast to all clients
                disconnected = []
                for ws in self._websockets:
                    try:
                        await ws.send_json(metrics)
                    except Exception:
                        disconnected.append(ws)
                
                # Remove disconnected clients
                for ws in disconnected:
                    if ws in self._websockets:
                        self._websockets.remove(ws)
                
                await asyncio.sleep(self.config.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dashboard broadcast error: {e}")
                await asyncio.sleep(self.config.update_interval)
    
    def _check_alerts(self, metrics: Dict[str, Any]) -> None:
        """Check metrics and generate alerts."""
        # Check latency
        e2e_latency = metrics.get("latencies", {}).get("e2e", {}).get("avg", 0)
        if e2e_latency > self.config.alert_latency_threshold_ms:
            self.metrics.add_alert(
                "warning",
                f"High latency detected: {e2e_latency:.0f}ms",
                "latency"
            )
        
        # Check memory
        memory_percent = metrics.get("resources", {}).get("memory_percent", 0)
        if memory_percent > self.config.alert_memory_threshold_percent:
            self.metrics.add_alert(
                "warning",
                f"High memory usage: {memory_percent:.1f}%",
                "resources"
            )
        
        # Check cache hit ratio
        cache_ratio = metrics.get("cache", {}).get("hit_ratio", 1)
        if cache_ratio < self.config.alert_cache_hit_threshold:
            self.metrics.add_alert(
                "info",
                f"Low cache hit ratio: {cache_ratio:.1%}",
                "cache"
            )
    
    async def start(self) -> None:
        """Start the dashboard server."""
        if not self.config.enabled:
            logger.info("Dashboard disabled in config")
            return
        
        if not FASTAPI_AVAILABLE:
            logger.warning("FastAPI not available, dashboard disabled")
            return
        
        self._app = self._create_app()
        self._running = True
        self._start_time = time.time()
        
        # Start broadcast task
        self._update_task = asyncio.create_task(self._broadcast_metrics())
        
        # Start server
        config = uvicorn.Config(
            self._app,
            host=self.config.host,
            port=self.config.port,
            log_level="warning",
        )
        server = uvicorn.Server(config)
        self._server_task = asyncio.create_task(server.serve())
        
        logger.info(f"Dashboard started at http://{self.config.host}:{self.config.port}/dashboard")
    
    async def stop(self) -> None:
        """Stop the dashboard server."""
        self._running = False
        
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
        
        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
        
        # Close all WebSocket connections
        for ws in self._websockets:
            try:
                await ws.close()
            except Exception:
                pass
        self._websockets.clear()
        
        logger.info("Dashboard stopped")
    
    def record_latency(self, category: str, value_ms: float) -> None:
        """Record a latency measurement."""
        self.metrics.record_latency(category, value_ms)
    
    def record_error(self, error: str, component: str = "unknown") -> None:
        """Record an error."""
        self.metrics.record_error(error, component)


# Singleton instance
_dashboard: Optional[PerformanceDashboard] = None


def get_dashboard(config: Optional[DashboardConfig] = None) -> PerformanceDashboard:
    """Get or create the global dashboard instance."""
    global _dashboard
    if _dashboard is None:
        _dashboard = PerformanceDashboard(config)
    return _dashboard


async def init_dashboard(config: Optional[DashboardConfig] = None) -> PerformanceDashboard:
    """Initialize and start the global dashboard."""
    dashboard = get_dashboard(config)
    await dashboard.start()
    return dashboard
