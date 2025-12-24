"""
Health Monitoring and Crash Recovery for JARVIS.

Provides:
- Component health checks
- Automatic restart of failed components
- Graceful degradation
- Alert notifications
- State persistence for recovery
"""

from __future__ import annotations

import asyncio
import json
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Awaitable

from loguru import logger


class ComponentStatus(Enum):
    """Status of a monitored component."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    STARTING = "starting"
    STOPPED = "stopped"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheck:
    """Result of a health check."""
    component: str
    status: ComponentStatus
    message: str = ""
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """An alert notification."""
    level: AlertLevel
    component: str
    message: str
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "component": self.component,
            "message": self.message,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
        }


@dataclass
class ComponentConfig:
    """Configuration for a monitored component."""
    name: str
    health_check: Callable[[], Awaitable[HealthCheck]]
    restart_func: Optional[Callable[[], Awaitable[bool]]] = None
    critical: bool = False
    check_interval: int = 30
    max_failures: int = 3
    restart_delay: int = 5
    
    # Runtime state
    failure_count: int = 0
    last_check: Optional[HealthCheck] = None
    restart_count: int = 0


class HealthMonitor:
    """
    Monitors health of JARVIS components.
    
    Features:
    - Periodic health checks
    - Automatic restart on failure
    - Alert notifications
    - Graceful degradation
    - State persistence
    """
    
    STATE_FILE = "health_state.json"
    
    def __init__(
        self,
        data_dir: Optional[Path] = None,
        check_interval: int = 30,
        alert_callback: Optional[Callable[[Alert], Awaitable[None]]] = None,
    ):
        """
        Initialize health monitor.
        
        Args:
            data_dir: Directory for state persistence.
            check_interval: Default check interval in seconds.
            alert_callback: Async callback for alerts.
        """
        self.data_dir = data_dir or Path("data")
        self.check_interval = check_interval
        self.alert_callback = alert_callback
        
        self._components: Dict[str, ComponentConfig] = {}
        self._alerts: List[Alert] = []
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        self._load_state()
    
    def _load_state(self) -> None:
        """Load persisted state."""
        state_path = self.data_dir / self.STATE_FILE
        
        if state_path.exists():
            try:
                with open(state_path, "r") as f:
                    data = json.load(f)
                
                # Restore alerts
                for alert_data in data.get("alerts", []):
                    self._alerts.append(Alert(
                        level=AlertLevel(alert_data["level"]),
                        component=alert_data["component"],
                        message=alert_data["message"],
                        timestamp=alert_data["timestamp"],
                        acknowledged=alert_data["acknowledged"],
                    ))
                
                logger.info("Loaded health monitor state")
            except Exception as e:
                logger.warning(f"Failed to load health state: {e}")
    
    def _save_state(self) -> None:
        """Persist state."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        state_path = self.data_dir / self.STATE_FILE
        
        try:
            data = {
                "alerts": [a.to_dict() for a in self._alerts[-100:]],  # Keep last 100
                "components": {
                    name: {
                        "failure_count": cfg.failure_count,
                        "restart_count": cfg.restart_count,
                        "last_status": cfg.last_check.status.value if cfg.last_check else None,
                    }
                    for name, cfg in self._components.items()
                },
            }
            
            with open(state_path, "w") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save health state: {e}")
    
    def register_component(
        self,
        name: str,
        health_check: Callable[[], Awaitable[HealthCheck]],
        restart_func: Optional[Callable[[], Awaitable[bool]]] = None,
        critical: bool = False,
        check_interval: Optional[int] = None,
        max_failures: int = 3,
    ) -> None:
        """
        Register a component for monitoring.
        
        Args:
            name: Component name.
            health_check: Async function returning HealthCheck.
            restart_func: Async function to restart component.
            critical: If True, system cannot function without this.
            check_interval: Check interval in seconds.
            max_failures: Failures before restart attempt.
        """
        self._components[name] = ComponentConfig(
            name=name,
            health_check=health_check,
            restart_func=restart_func,
            critical=critical,
            check_interval=check_interval or self.check_interval,
            max_failures=max_failures,
        )
        
        logger.info(f"Registered component for monitoring: {name}")
    
    def unregister_component(self, name: str) -> None:
        """Unregister a component."""
        if name in self._components:
            del self._components[name]
            logger.info(f"Unregistered component: {name}")
    
    async def check_component(self, name: str) -> HealthCheck:
        """
        Run health check for a specific component.
        
        Args:
            name: Component name.
            
        Returns:
            HealthCheck result.
        """
        if name not in self._components:
            return HealthCheck(
                component=name,
                status=ComponentStatus.UNKNOWN,
                message="Component not registered",
            )
        
        config = self._components[name]
        start_time = time.time()
        
        try:
            check = await config.health_check()
            check.latency_ms = (time.time() - start_time) * 1000
            
            config.last_check = check
            
            if check.status == ComponentStatus.HEALTHY:
                config.failure_count = 0
            else:
                config.failure_count += 1
                
                if config.failure_count >= config.max_failures:
                    await self._handle_failure(config)
            
            return check
            
        except Exception as e:
            config.failure_count += 1
            
            check = HealthCheck(
                component=name,
                status=ComponentStatus.UNHEALTHY,
                message=f"Health check failed: {e}",
                latency_ms=(time.time() - start_time) * 1000,
            )
            config.last_check = check
            
            if config.failure_count >= config.max_failures:
                await self._handle_failure(config)
            
            return check
    
    async def check_all(self) -> Dict[str, HealthCheck]:
        """
        Run health checks for all components.
        
        Returns:
            Dict mapping component name to HealthCheck.
        """
        results = {}
        
        for name in self._components:
            results[name] = await self.check_component(name)
        
        self._save_state()
        return results
    
    async def _handle_failure(self, config: ComponentConfig) -> None:
        """Handle component failure."""
        logger.warning(f"Component failure: {config.name} (failures: {config.failure_count})")
        
        # Create alert
        alert = Alert(
            level=AlertLevel.CRITICAL if config.critical else AlertLevel.ERROR,
            component=config.name,
            message=f"Component unhealthy after {config.failure_count} failures",
        )
        await self._send_alert(alert)
        
        # Attempt restart if available
        if config.restart_func:
            logger.info(f"Attempting to restart: {config.name}")
            
            await asyncio.sleep(config.restart_delay)
            
            try:
                success = await config.restart_func()
                
                if success:
                    config.failure_count = 0
                    config.restart_count += 1
                    
                    await self._send_alert(Alert(
                        level=AlertLevel.INFO,
                        component=config.name,
                        message=f"Component restarted successfully (restart #{config.restart_count})",
                    ))
                else:
                    await self._send_alert(Alert(
                        level=AlertLevel.CRITICAL,
                        component=config.name,
                        message="Restart failed",
                    ))
                    
            except Exception as e:
                logger.error(f"Restart failed for {config.name}: {e}")
                await self._send_alert(Alert(
                    level=AlertLevel.CRITICAL,
                    component=config.name,
                    message=f"Restart exception: {e}",
                ))
    
    async def _send_alert(self, alert: Alert) -> None:
        """Send an alert notification."""
        self._alerts.append(alert)
        
        logger.log(
            "WARNING" if alert.level in [AlertLevel.WARNING, AlertLevel.ERROR] else "INFO",
            f"[{alert.level.value.upper()}] {alert.component}: {alert.message}"
        )
        
        if self.alert_callback:
            try:
                await self.alert_callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self.check_all()
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def start(self) -> None:
        """Start health monitoring."""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        logger.info("Health monitor started")
    
    async def stop(self) -> None:
        """Stop health monitoring."""
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        self._save_state()
        logger.info("Health monitor stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        components = {}
        overall_status = ComponentStatus.HEALTHY
        
        for name, config in self._components.items():
            if config.last_check:
                components[name] = {
                    "status": config.last_check.status.value,
                    "message": config.last_check.message,
                    "latency_ms": config.last_check.latency_ms,
                    "failure_count": config.failure_count,
                    "restart_count": config.restart_count,
                    "critical": config.critical,
                }
                
                if config.last_check.status == ComponentStatus.UNHEALTHY:
                    if config.critical:
                        overall_status = ComponentStatus.UNHEALTHY
                    elif overall_status == ComponentStatus.HEALTHY:
                        overall_status = ComponentStatus.DEGRADED
            else:
                components[name] = {
                    "status": ComponentStatus.UNKNOWN.value,
                    "critical": config.critical,
                }
        
        return {
            "overall_status": overall_status.value,
            "components": components,
            "active_alerts": len([a for a in self._alerts if not a.acknowledged]),
            "timestamp": time.time(),
        }
    
    def get_alerts(self, unacknowledged_only: bool = False) -> List[Alert]:
        """Get alerts."""
        if unacknowledged_only:
            return [a for a in self._alerts if not a.acknowledged]
        return self._alerts.copy()
    
    def acknowledge_alert(self, index: int) -> bool:
        """Acknowledge an alert by index."""
        if 0 <= index < len(self._alerts):
            self._alerts[index].acknowledged = True
            return True
        return False


# Pre-built health check functions

async def check_llm_health() -> HealthCheck:
    """Check LLM availability."""
    try:
        from .llm import LLMManager
        
        llm = LLMManager()
        # Simple test
        response = await llm.generate("Say 'ok'", max_tokens=10)
        
        if response and response.content:
            return HealthCheck(
                component="llm",
                status=ComponentStatus.HEALTHY,
                message=f"LLM responding (provider: {response.provider})",
            )
        else:
            return HealthCheck(
                component="llm",
                status=ComponentStatus.UNHEALTHY,
                message="LLM returned empty response",
            )
    except Exception as e:
        return HealthCheck(
            component="llm",
            status=ComponentStatus.UNHEALTHY,
            message=str(e),
        )


async def check_voice_health() -> HealthCheck:
    """Check voice pipeline health."""
    try:
        import sounddevice as sd
        
        # Check for audio devices
        devices = sd.query_devices()
        input_devices = [d for d in devices if d["max_input_channels"] > 0]
        output_devices = [d for d in devices if d["max_output_channels"] > 0]
        
        if not input_devices:
            return HealthCheck(
                component="voice",
                status=ComponentStatus.DEGRADED,
                message="No input devices found",
            )
        
        if not output_devices:
            return HealthCheck(
                component="voice",
                status=ComponentStatus.DEGRADED,
                message="No output devices found",
            )
        
        return HealthCheck(
            component="voice",
            status=ComponentStatus.HEALTHY,
            message=f"Audio OK ({len(input_devices)} in, {len(output_devices)} out)",
            details={
                "input_devices": len(input_devices),
                "output_devices": len(output_devices),
            },
        )
    except ImportError:
        return HealthCheck(
            component="voice",
            status=ComponentStatus.UNHEALTHY,
            message="sounddevice not installed",
        )
    except Exception as e:
        return HealthCheck(
            component="voice",
            status=ComponentStatus.UNHEALTHY,
            message=str(e),
        )


async def check_iot_health() -> HealthCheck:
    """Check IoT controller health."""
    try:
        from ..iot import ProductionIoTController
        
        # This would need the actual controller instance
        return HealthCheck(
            component="iot",
            status=ComponentStatus.HEALTHY,
            message="IoT module available",
        )
    except ImportError:
        return HealthCheck(
            component="iot",
            status=ComponentStatus.DEGRADED,
            message="IoT module not available",
        )


async def check_memory_health() -> HealthCheck:
    """Check memory usage."""
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        
        if memory.percent > 90:
            status = ComponentStatus.UNHEALTHY
            message = f"Memory critical: {memory.percent}%"
        elif memory.percent > 75:
            status = ComponentStatus.DEGRADED
            message = f"Memory high: {memory.percent}%"
        else:
            status = ComponentStatus.HEALTHY
            message = f"Memory OK: {memory.percent}%"
        
        return HealthCheck(
            component="memory",
            status=status,
            message=message,
            details={
                "percent": memory.percent,
                "available_gb": memory.available / (1024**3),
            },
        )
    except ImportError:
        return HealthCheck(
            component="memory",
            status=ComponentStatus.UNKNOWN,
            message="psutil not installed",
        )


async def check_disk_health(path: str = ".") -> HealthCheck:
    """Check disk space."""
    try:
        import psutil
        
        disk = psutil.disk_usage(path)
        
        if disk.percent > 95:
            status = ComponentStatus.UNHEALTHY
            message = f"Disk critical: {disk.percent}%"
        elif disk.percent > 85:
            status = ComponentStatus.DEGRADED
            message = f"Disk high: {disk.percent}%"
        else:
            status = ComponentStatus.HEALTHY
            message = f"Disk OK: {disk.percent}%"
        
        return HealthCheck(
            component="disk",
            status=status,
            message=message,
            details={
                "percent": disk.percent,
                "free_gb": disk.free / (1024**3),
            },
        )
    except ImportError:
        return HealthCheck(
            component="disk",
            status=ComponentStatus.UNKNOWN,
            message="psutil not installed",
        )


# Global instance
_monitor: Optional[HealthMonitor] = None


def get_health_monitor(data_dir: Optional[Path] = None) -> HealthMonitor:
    """Get the global health monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = HealthMonitor(data_dir)
    return _monitor
