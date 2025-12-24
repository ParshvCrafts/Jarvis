"""IoT modules for JARVIS."""

from loguru import logger

# Enhanced module (canonical) - with graceful fallback
try:
    from .esp32_enhanced import (
        EnhancedESP32Controller,
        SecureDeviceClient,
        DeviceDiscovery,
        DeviceInfo,
        DeviceType,
        DeviceState,
        CommandResult,
    )
except ImportError as e:
    logger.warning(f"Enhanced IoT controller not available: {e}")
    EnhancedESP32Controller = None
    SecureDeviceClient = None
    DeviceDiscovery = None
    DeviceInfo = None
    DeviceType = None
    DeviceState = None
    CommandResult = None

# Production controller with queue and state tracking
try:
    from .controller_enhanced import (
        ProductionIoTController,
        CommandPriority,
        QueuedCommand,
        DeviceStateCache,
    )
except ImportError as e:
    logger.warning(f"Production IoT controller not available: {e}")
    ProductionIoTController = None
    CommandPriority = None
    QueuedCommand = None
    DeviceStateCache = None

# Legacy alias for backwards compatibility
try:
    from .esp32_controller import ESP32Controller as LegacyESP32Controller
except ImportError:
    LegacyESP32Controller = None

__all__ = [
    # Production (recommended)
    "ProductionIoTController",
    "CommandPriority",
    "QueuedCommand",
    "DeviceStateCache",
    # Enhanced
    "EnhancedESP32Controller",
    "SecureDeviceClient",
    "DeviceDiscovery",
    "DeviceInfo",
    "DeviceType",
    "DeviceState",
    "CommandResult",
    # Legacy (deprecated)
    "LegacyESP32Controller",
]
