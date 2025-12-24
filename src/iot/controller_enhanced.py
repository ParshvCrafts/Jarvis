"""
Enhanced IoT Controller for JARVIS.

Production-ready controller with:
- Command queue with retry logic
- State tracking and synchronization
- Graceful offline handling
- Event bus integration
- Device caching with TTL
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from loguru import logger

from .esp32_enhanced import (
    DeviceInfo,
    DeviceType,
    DeviceState,
    CommandResult,
    DeviceDiscovery,
    SecureDeviceClient,
    EnhancedESP32Controller,
    ZEROCONF_AVAILABLE,
)


class CommandPriority(Enum):
    """Priority levels for queued commands."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class QueuedCommand:
    """A command waiting to be executed."""
    device_id: str
    endpoint: str
    data: Optional[Dict[str, Any]] = None
    method: str = "POST"
    priority: CommandPriority = CommandPriority.NORMAL
    max_retries: int = 3
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    callback: Optional[Callable[[CommandResult], None]] = None
    
    def __lt__(self, other):
        """For priority queue ordering."""
        return self.priority.value > other.priority.value


@dataclass
class DeviceStateCache:
    """Cached state for a device."""
    device_id: str
    state: Dict[str, Any] = field(default_factory=dict)
    last_updated: float = 0.0
    last_command: str = ""
    command_count: int = 0
    error_count: int = 0
    
    @property
    def is_stale(self) -> bool:
        """Check if cache is stale (older than 60 seconds)."""
        return time.time() - self.last_updated > 60
    
    def update(self, new_state: Dict[str, Any]) -> None:
        """Update cached state."""
        self.state.update(new_state)
        self.last_updated = time.time()


class ProductionIoTController:
    """
    Production-ready IoT controller.
    
    Features:
    - Command queue with priority and retry
    - Device state caching and synchronization
    - Offline command queuing
    - Event bus integration
    - Graceful degradation
    """
    
    STATE_FILE = "iot_state.json"
    
    def __init__(
        self,
        shared_secret: str,
        data_dir: Optional[Path] = None,
        auto_discover: bool = True,
        max_queue_size: int = 100,
        retry_delay: float = 2.0,
        state_sync_interval: int = 30,
    ):
        """
        Initialize production IoT controller.
        
        Args:
            shared_secret: Shared secret for device authentication.
            data_dir: Directory for state persistence.
            auto_discover: Enable automatic device discovery.
            max_queue_size: Maximum commands in queue.
            retry_delay: Delay between retries in seconds.
            state_sync_interval: Interval for state synchronization.
        """
        self.shared_secret = shared_secret
        self.data_dir = data_dir or Path("data")
        self.max_queue_size = max_queue_size
        self.retry_delay = retry_delay
        self.state_sync_interval = state_sync_interval
        
        # Core controller
        self._controller = EnhancedESP32Controller(
            shared_secret=shared_secret,
            auto_discover=auto_discover,
        )
        
        # Command queue
        self._command_queue: deque = deque(maxlen=max_queue_size)
        self._processing = False
        self._queue_task: Optional[asyncio.Task] = None
        
        # State cache
        self._state_cache: Dict[str, DeviceStateCache] = {}
        self._sync_task: Optional[asyncio.Task] = None
        
        # Offline command storage
        self._offline_commands: List[QueuedCommand] = []
        
        # Event callbacks
        self._on_device_online: Optional[Callable[[DeviceInfo], None]] = None
        self._on_device_offline: Optional[Callable[[DeviceInfo], None]] = None
        self._on_state_change: Optional[Callable[[str, Dict], None]] = None
        self._on_command_result: Optional[Callable[[str, CommandResult], None]] = None
        
        # Load persisted state
        self._load_state()
        
        logger.info("Production IoT controller initialized")
    
    def _load_state(self) -> None:
        """Load persisted device state."""
        state_path = self.data_dir / self.STATE_FILE
        
        if state_path.exists():
            try:
                with open(state_path, "r") as f:
                    data = json.load(f)
                
                for device_id, state_data in data.get("devices", {}).items():
                    self._state_cache[device_id] = DeviceStateCache(
                        device_id=device_id,
                        state=state_data.get("state", {}),
                        last_updated=state_data.get("last_updated", 0),
                    )
                
                logger.info(f"Loaded state for {len(self._state_cache)} devices")
            except Exception as e:
                logger.warning(f"Failed to load IoT state: {e}")
    
    def _save_state(self) -> None:
        """Persist device state."""
        state_path = self.data_dir / self.STATE_FILE
        
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            data = {
                "devices": {
                    device_id: {
                        "state": cache.state,
                        "last_updated": cache.last_updated,
                    }
                    for device_id, cache in self._state_cache.items()
                }
            }
            
            with open(state_path, "w") as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save IoT state: {e}")
    
    def set_callbacks(
        self,
        on_device_online: Optional[Callable[[DeviceInfo], None]] = None,
        on_device_offline: Optional[Callable[[DeviceInfo], None]] = None,
        on_state_change: Optional[Callable[[str, Dict], None]] = None,
        on_command_result: Optional[Callable[[str, CommandResult], None]] = None,
    ) -> None:
        """Set event callbacks."""
        self._on_device_online = on_device_online
        self._on_device_offline = on_device_offline
        self._on_state_change = on_state_change
        self._on_command_result = on_command_result
    
    # =========================================================================
    # Device Management
    # =========================================================================
    
    def add_device(
        self,
        device_id: str,
        ip_address: str,
        device_type: DeviceType,
        name: Optional[str] = None,
        port: int = 80,
    ) -> DeviceInfo:
        """Manually add a device."""
        device = self._controller.add_device(device_id, ip_address, device_type, name, port)
        
        # Initialize state cache
        if device_id not in self._state_cache:
            self._state_cache[device_id] = DeviceStateCache(device_id=device_id)
        
        return device
    
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """Get device by ID."""
        return self._controller.get_device(device_id)
    
    def get_all_devices(self) -> List[DeviceInfo]:
        """Get all registered devices."""
        return self._controller.get_all_devices()
    
    def get_online_devices(self) -> List[DeviceInfo]:
        """Get all online devices."""
        return self._controller.get_online_devices()
    
    def get_device_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get cached state for a device."""
        cache = self._state_cache.get(device_id)
        return cache.state if cache else None
    
    # =========================================================================
    # Command Queue
    # =========================================================================
    
    def queue_command(
        self,
        device_id: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        method: str = "POST",
        priority: CommandPriority = CommandPriority.NORMAL,
        callback: Optional[Callable[[CommandResult], None]] = None,
    ) -> bool:
        """
        Queue a command for execution.
        
        Args:
            device_id: Target device ID.
            endpoint: API endpoint.
            data: Request data.
            method: HTTP method.
            priority: Command priority.
            callback: Callback for result.
            
        Returns:
            True if queued successfully.
        """
        if len(self._command_queue) >= self.max_queue_size:
            logger.warning("Command queue full, dropping oldest command")
            self._command_queue.popleft()
        
        command = QueuedCommand(
            device_id=device_id,
            endpoint=endpoint,
            data=data,
            method=method,
            priority=priority,
            callback=callback,
        )
        
        # Insert by priority
        inserted = False
        for i, existing in enumerate(self._command_queue):
            if command.priority.value > existing.priority.value:
                self._command_queue.insert(i, command)
                inserted = True
                break
        
        if not inserted:
            self._command_queue.append(command)
        
        logger.debug(f"Queued command for {device_id}: {endpoint}")
        return True
    
    async def _process_queue(self) -> None:
        """Process command queue."""
        while self._processing:
            if not self._command_queue:
                await asyncio.sleep(0.1)
                continue
            
            command = self._command_queue.popleft()
            
            # Check if device is online
            device = self.get_device(command.device_id)
            if not device:
                logger.warning(f"Device not found: {command.device_id}")
                if command.callback:
                    command.callback(CommandResult(False, "Device not found"))
                continue
            
            if not device.is_online:
                # Store for later if device is offline
                if command.retry_count < command.max_retries:
                    command.retry_count += 1
                    self._offline_commands.append(command)
                    logger.info(f"Device offline, queued for retry: {command.device_id}")
                else:
                    logger.warning(f"Max retries reached for offline device: {command.device_id}")
                    if command.callback:
                        command.callback(CommandResult(False, "Device offline"))
                continue
            
            # Execute command
            result = await self._controller.client.send_command(
                device, command.endpoint, command.data, command.method
            )
            
            if result.success:
                # Update state cache
                self._update_state_cache(command.device_id, command.endpoint, command.data, result)
                
                if command.callback:
                    command.callback(result)
                
                if self._on_command_result:
                    self._on_command_result(command.device_id, result)
            else:
                # Retry on failure
                if command.retry_count < command.max_retries:
                    command.retry_count += 1
                    self._command_queue.append(command)
                    logger.info(f"Command failed, retrying ({command.retry_count}/{command.max_retries})")
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error(f"Command failed after {command.max_retries} retries: {result.message}")
                    if command.callback:
                        command.callback(result)
            
            await asyncio.sleep(0.05)  # Small delay between commands
    
    def _update_state_cache(
        self,
        device_id: str,
        endpoint: str,
        data: Optional[Dict],
        result: CommandResult,
    ) -> None:
        """Update state cache after command."""
        if device_id not in self._state_cache:
            self._state_cache[device_id] = DeviceStateCache(device_id=device_id)
        
        cache = self._state_cache[device_id]
        cache.command_count += 1
        cache.last_command = endpoint
        
        # Update state based on command
        if "/light" in endpoint and data:
            state = data.get("state")
            if state == "on":
                cache.state["light_on"] = True
            elif state == "off":
                cache.state["light_on"] = False
            elif state == "toggle":
                cache.state["light_on"] = not cache.state.get("light_on", False)
        
        elif "/door" in endpoint and data:
            action = data.get("action")
            if action == "unlock":
                cache.state["locked"] = False
            elif action == "lock":
                cache.state["locked"] = True
        
        # Update from response
        if result.data:
            cache.update(result.data)
        
        # Notify state change
        if self._on_state_change:
            self._on_state_change(device_id, cache.state)
        
        # Persist state
        self._save_state()
    
    # =========================================================================
    # High-Level Commands
    # =========================================================================
    
    async def light_on(self, device_id: str) -> CommandResult:
        """Turn light on."""
        device = self.get_device(device_id)
        if not device:
            return CommandResult(False, f"Device not found: {device_id}")
        
        result = await self._controller.light_on(device_id)
        self._update_state_cache(device_id, "/light", {"state": "on"}, result)
        return result
    
    async def light_off(self, device_id: str) -> CommandResult:
        """Turn light off."""
        device = self.get_device(device_id)
        if not device:
            return CommandResult(False, f"Device not found: {device_id}")
        
        result = await self._controller.light_off(device_id)
        self._update_state_cache(device_id, "/light", {"state": "off"}, result)
        return result
    
    async def light_toggle(self, device_id: str) -> CommandResult:
        """Toggle light state."""
        device = self.get_device(device_id)
        if not device:
            return CommandResult(False, f"Device not found: {device_id}")
        
        result = await self._controller.light_toggle(device_id)
        self._update_state_cache(device_id, "/light", {"state": "toggle"}, result)
        return result
    
    async def door_unlock(self, device_id: str, duration: int = 3) -> CommandResult:
        """Unlock door."""
        device = self.get_device(device_id)
        if not device:
            return CommandResult(False, f"Device not found: {device_id}")
        
        result = await self._controller.door_unlock(device_id, duration)
        self._update_state_cache(device_id, "/door", {"action": "unlock"}, result)
        return result
    
    async def door_lock(self, device_id: str) -> CommandResult:
        """Lock door."""
        device = self.get_device(device_id)
        if not device:
            return CommandResult(False, f"Device not found: {device_id}")
        
        result = await self._controller.door_lock(device_id)
        self._update_state_cache(device_id, "/door", {"action": "lock"}, result)
        return result
    
    async def get_device_status(self, device_id: str) -> CommandResult:
        """Get device status."""
        device = self.get_device(device_id)
        if not device:
            return CommandResult(False, f"Device not found: {device_id}")
        
        result = await self._controller.client.send_command(device, "/status", method="GET")
        
        if result.success:
            self._update_state_cache(device_id, "/status", None, result)
        
        return result
    
    # =========================================================================
    # State Synchronization
    # =========================================================================
    
    async def sync_all_devices(self) -> Dict[str, bool]:
        """
        Synchronize state with all devices.
        
        Returns:
            Dict mapping device_id to sync success.
        """
        results = {}
        
        for device in self.get_all_devices():
            try:
                result = await self.get_device_status(device.device_id)
                results[device.device_id] = result.success
                
                if result.success:
                    device.state = DeviceState.ONLINE
                    device.last_seen = time.time()
                    
                    if self._on_device_online:
                        self._on_device_online(device)
                else:
                    if device.state == DeviceState.ONLINE:
                        device.state = DeviceState.OFFLINE
                        if self._on_device_offline:
                            self._on_device_offline(device)
                            
            except Exception as e:
                logger.error(f"Sync failed for {device.device_id}: {e}")
                results[device.device_id] = False
        
        return results
    
    async def _sync_loop(self) -> None:
        """Periodic state synchronization loop."""
        while self._processing:
            await asyncio.sleep(self.state_sync_interval)
            
            try:
                await self.sync_all_devices()
                
                # Retry offline commands
                if self._offline_commands:
                    commands_to_retry = self._offline_commands.copy()
                    self._offline_commands.clear()
                    
                    for cmd in commands_to_retry:
                        device = self.get_device(cmd.device_id)
                        if device and device.is_online:
                            self._command_queue.append(cmd)
                            
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start(self) -> None:
        """Start the controller."""
        if self._processing:
            return
        
        self._processing = True
        
        # Start command queue processor
        self._queue_task = asyncio.create_task(self._process_queue())
        
        # Start state sync loop
        self._sync_task = asyncio.create_task(self._sync_loop())
        
        # Initial sync
        await self.sync_all_devices()
        
        logger.info("Production IoT controller started")
    
    async def stop(self) -> None:
        """Stop the controller."""
        self._processing = False
        
        if self._queue_task:
            self._queue_task.cancel()
            try:
                await self._queue_task
            except asyncio.CancelledError:
                pass
        
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        
        # Save final state
        self._save_state()
        
        # Stop discovery
        self._controller.discovery.stop()
        
        logger.info("Production IoT controller stopped")
    
    def start_sync(self) -> None:
        """Start controller synchronously."""
        asyncio.run(self.start())
    
    def stop_sync(self) -> None:
        """Stop controller synchronously."""
        asyncio.run(self.stop())
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary of all device statuses."""
        devices = self.get_all_devices()
        online = self.get_online_devices()
        
        return {
            "total_devices": len(devices),
            "online_devices": len(online),
            "offline_devices": len(devices) - len(online),
            "queued_commands": len(self._command_queue),
            "offline_commands": len(self._offline_commands),
            "devices": [
                {
                    "id": d.device_id,
                    "name": d.name,
                    "type": d.device_type.value,
                    "online": d.is_online,
                    "ip": d.ip_address,
                    "state": self._state_cache.get(d.device_id, DeviceStateCache(d.device_id)).state,
                }
                for d in devices
            ],
        }
    
    def find_device_by_name(self, name: str) -> Optional[DeviceInfo]:
        """Find device by name (case-insensitive partial match)."""
        name_lower = name.lower()
        
        for device in self.get_all_devices():
            if name_lower in device.name.lower() or name_lower in device.device_id.lower():
                return device
        
        return None
    
    def find_devices_by_type(self, device_type: DeviceType) -> List[DeviceInfo]:
        """Find all devices of a specific type."""
        return [d for d in self.get_all_devices() if d.device_type == device_type]
