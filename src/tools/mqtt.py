"""
MQTT Smart Home Service for JARVIS - Phase 7

Provides smart home control via MQTT protocol (FREE, open standard).

Features:
- Publish messages to MQTT topics
- Subscribe to topics for state updates
- Control smart home devices (lights, switches, sensors)
- Compatible with Tasmota, Zigbee2MQTT, Home Assistant

Setup:
1. Install an MQTT broker (Mosquitto recommended)
2. Configure broker address in settings.yaml
3. Connect your smart devices to the broker

MQTT Broker Installation:
- Windows: https://mosquitto.org/download/
- Docker: docker run -p 1883:1883 eclipse-mosquitto
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum

from loguru import logger

# MQTT client (optional)
try:
    import paho.mqtt.client as mqtt
    from paho.mqtt.client import MQTTMessage
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logger.debug("paho-mqtt not installed. Install with: pip install paho-mqtt")
    mqtt = None
    MQTTMessage = None


class DeviceType(Enum):
    """Types of smart home devices."""
    LIGHT = "light"
    SWITCH = "switch"
    SENSOR = "sensor"
    THERMOSTAT = "thermostat"
    LOCK = "lock"
    COVER = "cover"  # Blinds, curtains
    FAN = "fan"
    UNKNOWN = "unknown"


@dataclass
class SmartDevice:
    """Represents a smart home device."""
    id: str
    name: str
    device_type: DeviceType
    topic: str
    state: Dict[str, Any] = field(default_factory=dict)
    last_seen: Optional[datetime] = None
    available: bool = True
    
    @property
    def is_on(self) -> bool:
        """Check if device is on (for switches/lights)."""
        state = self.state.get("state", self.state.get("POWER", "OFF"))
        return str(state).upper() in ["ON", "1", "TRUE"]
    
    @property
    def brightness(self) -> Optional[int]:
        """Get brightness level (for dimmable lights)."""
        return self.state.get("brightness", self.state.get("Dimmer"))
    
    @property
    def temperature(self) -> Optional[float]:
        """Get temperature (for sensors/thermostats)."""
        return self.state.get("temperature", self.state.get("Temperature"))
    
    @property
    def humidity(self) -> Optional[float]:
        """Get humidity (for sensors)."""
        return self.state.get("humidity", self.state.get("Humidity"))
    
    def format_status(self) -> str:
        """Format device status for display."""
        status_icon = "🟢" if self.available else "🔴"
        
        if self.device_type == DeviceType.LIGHT:
            state = "💡 On" if self.is_on else "⚫ Off"
            if self.brightness is not None:
                state += f" ({self.brightness}%)"
        elif self.device_type == DeviceType.SWITCH:
            state = "🔌 On" if self.is_on else "⚫ Off"
        elif self.device_type == DeviceType.SENSOR:
            parts = []
            if self.temperature is not None:
                parts.append(f"🌡️ {self.temperature}°")
            if self.humidity is not None:
                parts.append(f"💧 {self.humidity}%")
            state = " | ".join(parts) if parts else "No data"
        elif self.device_type == DeviceType.THERMOSTAT:
            temp = self.state.get("current_temperature", self.temperature)
            target = self.state.get("target_temperature", self.state.get("setpoint"))
            state = f"🌡️ {temp}° (target: {target}°)" if temp else "No data"
        elif self.device_type == DeviceType.LOCK:
            locked = self.state.get("locked", self.state.get("state")) == "locked"
            state = "🔒 Locked" if locked else "🔓 Unlocked"
        else:
            state = str(self.state) if self.state else "Unknown"
        
        return f"{status_icon} **{self.name}**: {state}"


class MQTTService:
    """
    MQTT service for smart home control.
    
    Provides device discovery, state tracking, and control via MQTT.
    Compatible with common smart home platforms.
    """
    
    # Common topic patterns for device discovery
    DISCOVERY_TOPICS = [
        "homeassistant/+/+/config",  # Home Assistant discovery
        "tasmota/discovery/+/config",  # Tasmota discovery
        "zigbee2mqtt/bridge/devices",  # Zigbee2MQTT devices
    ]
    
    # Common command topics
    TASMOTA_CMD = "cmnd/{device}/Power"
    ZIGBEE_SET = "zigbee2mqtt/{device}/set"
    
    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: str = "jarvis_mqtt",
    ):
        """
        Initialize MQTT service.
        
        Args:
            broker: MQTT broker hostname
            port: MQTT broker port
            username: Optional username for authentication
            password: Optional password for authentication
            client_id: MQTT client ID
        """
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.client_id = client_id
        
        self._client: Optional[mqtt.Client] = None
        self._connected = False
        self._devices: Dict[str, SmartDevice] = {}
        self._subscriptions: Set[str] = set()
        self._message_callbacks: Dict[str, List[Callable]] = {}
        self._state_cache: Dict[str, Dict[str, Any]] = {}
    
    def _create_client(self) -> Optional[mqtt.Client]:
        """Create MQTT client."""
        if not MQTT_AVAILABLE:
            logger.error("paho-mqtt not installed")
            return None
        
        try:
            client = mqtt.Client(client_id=self.client_id)
            
            if self.username and self.password:
                client.username_pw_set(self.username, self.password)
            
            client.on_connect = self._on_connect
            client.on_disconnect = self._on_disconnect
            client.on_message = self._on_message
            
            return client
        except Exception as e:
            logger.error(f"Failed to create MQTT client: {e}")
            return None
    
    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection."""
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
            self._connected = True
            
            # Resubscribe to topics
            for topic in self._subscriptions:
                client.subscribe(topic)
        else:
            logger.error(f"MQTT connection failed with code {rc}")
            self._connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection."""
        logger.warning(f"Disconnected from MQTT broker (code {rc})")
        self._connected = False
    
    def _on_message(self, client, userdata, msg: MQTTMessage):
        """Handle incoming MQTT messages."""
        topic = msg.topic
        try:
            # Try to parse as JSON
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = msg.payload.decode()
        
        logger.debug(f"MQTT message: {topic} = {payload}")
        
        # Update state cache
        self._state_cache[topic] = {
            "payload": payload,
            "timestamp": datetime.now(),
        }
        
        # Update device states
        self._update_device_state(topic, payload)
        
        # Call registered callbacks
        if topic in self._message_callbacks:
            for callback in self._message_callbacks[topic]:
                try:
                    callback(topic, payload)
                except Exception as e:
                    logger.error(f"Callback error for {topic}: {e}")
    
    def _update_device_state(self, topic: str, payload: Any):
        """Update device state from MQTT message."""
        # Find matching device
        for device_id, device in self._devices.items():
            if topic.startswith(device.topic) or device.topic in topic:
                if isinstance(payload, dict):
                    device.state.update(payload)
                else:
                    device.state["state"] = payload
                device.last_seen = datetime.now()
                device.available = True
                break
    
    async def connect(self) -> bool:
        """Connect to MQTT broker."""
        if self._connected:
            return True
        
        if self._client is None:
            self._client = self._create_client()
        
        if self._client is None:
            return False
        
        try:
            self._client.connect(self.broker, self.port, keepalive=60)
            self._client.loop_start()
            
            # Wait for connection
            for _ in range(50):  # 5 seconds timeout
                if self._connected:
                    return True
                await asyncio.sleep(0.1)
            
            logger.error("MQTT connection timeout")
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MQTT broker."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
    
    def is_available(self) -> bool:
        """Check if MQTT service is available."""
        return MQTT_AVAILABLE and self._connected
    
    async def publish(
        self,
        topic: str,
        payload: Any,
        retain: bool = False,
        qos: int = 0,
    ) -> bool:
        """
        Publish a message to an MQTT topic.
        
        Args:
            topic: MQTT topic
            payload: Message payload (will be JSON encoded if dict)
            retain: Whether to retain the message
            qos: Quality of Service level
            
        Returns:
            True if published successfully
        """
        if not await self.connect():
            return False
        
        try:
            if isinstance(payload, dict):
                payload = json.dumps(payload)
            elif not isinstance(payload, str):
                payload = str(payload)
            
            result = self._client.publish(topic, payload, qos=qos, retain=retain)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
            
        except Exception as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            return False
    
    async def subscribe(
        self,
        topic: str,
        callback: Optional[Callable] = None,
    ) -> bool:
        """
        Subscribe to an MQTT topic.
        
        Args:
            topic: MQTT topic (supports wildcards + and #)
            callback: Optional callback function(topic, payload)
            
        Returns:
            True if subscribed successfully
        """
        if not await self.connect():
            return False
        
        try:
            result = self._client.subscribe(topic)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                self._subscriptions.add(topic)
                
                if callback:
                    if topic not in self._message_callbacks:
                        self._message_callbacks[topic] = []
                    self._message_callbacks[topic].append(callback)
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to subscribe to {topic}: {e}")
            return False
    
    def register_device(
        self,
        device_id: str,
        name: str,
        device_type: DeviceType,
        topic: str,
    ) -> SmartDevice:
        """
        Register a smart home device.
        
        Args:
            device_id: Unique device identifier
            name: Human-readable device name
            device_type: Type of device
            topic: Base MQTT topic for the device
            
        Returns:
            Registered SmartDevice
        """
        device = SmartDevice(
            id=device_id,
            name=name,
            device_type=device_type,
            topic=topic,
        )
        self._devices[device_id] = device
        return device
    
    def get_device(self, device_id: str) -> Optional[SmartDevice]:
        """Get a device by ID."""
        return self._devices.get(device_id)
    
    def get_device_by_name(self, name: str) -> Optional[SmartDevice]:
        """Get a device by name (case-insensitive)."""
        name_lower = name.lower()
        for device in self._devices.values():
            if device.name.lower() == name_lower or name_lower in device.name.lower():
                return device
        return None
    
    def list_devices(self) -> List[SmartDevice]:
        """List all registered devices."""
        return list(self._devices.values())
    
    async def turn_on(self, device: SmartDevice) -> bool:
        """Turn on a device."""
        if device.device_type in [DeviceType.LIGHT, DeviceType.SWITCH, DeviceType.FAN]:
            # Try common command formats
            success = await self.publish(f"{device.topic}/set", {"state": "ON"})
            if not success:
                success = await self.publish(f"cmnd/{device.id}/Power", "ON")
            return success
        return False
    
    async def turn_off(self, device: SmartDevice) -> bool:
        """Turn off a device."""
        if device.device_type in [DeviceType.LIGHT, DeviceType.SWITCH, DeviceType.FAN]:
            success = await self.publish(f"{device.topic}/set", {"state": "OFF"})
            if not success:
                success = await self.publish(f"cmnd/{device.id}/Power", "OFF")
            return success
        return False
    
    async def set_brightness(self, device: SmartDevice, brightness: int) -> bool:
        """Set brightness for a dimmable light."""
        if device.device_type == DeviceType.LIGHT:
            brightness = max(0, min(100, brightness))
            return await self.publish(
                f"{device.topic}/set",
                {"brightness": brightness}
            )
        return False
    
    async def set_temperature(self, device: SmartDevice, temperature: float) -> bool:
        """Set target temperature for a thermostat."""
        if device.device_type == DeviceType.THERMOSTAT:
            return await self.publish(
                f"{device.topic}/set",
                {"temperature": temperature}
            )
        return False


# Singleton instance
_mqtt_service: Optional[MQTTService] = None


def get_mqtt_service(
    broker: str = "localhost",
    port: int = 1883,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> MQTTService:
    """Get or create MQTT service singleton."""
    global _mqtt_service
    if _mqtt_service is None:
        _mqtt_service = MQTTService(
            broker=broker,
            port=port,
            username=username,
            password=password,
        )
    return _mqtt_service


# =============================================================================
# Tool Functions for Agent Integration
# =============================================================================

async def list_smart_devices() -> str:
    """
    List all registered smart home devices.
    
    Returns:
        Formatted list of devices and their states
    """
    try:
        service = get_mqtt_service()
        
        if not MQTT_AVAILABLE:
            return "MQTT service not available. Install paho-mqtt: pip install paho-mqtt"
        
        devices = service.list_devices()
        
        if not devices:
            return "No smart home devices registered. Add devices in settings.yaml or use device discovery."
        
        lines = [f"**Smart Home Devices** ({len(devices)} devices)\n"]
        
        # Group by type
        by_type: Dict[DeviceType, List[SmartDevice]] = {}
        for device in devices:
            if device.device_type not in by_type:
                by_type[device.device_type] = []
            by_type[device.device_type].append(device)
        
        for device_type, type_devices in by_type.items():
            lines.append(f"\n**{device_type.value.title()}s:**")
            for device in type_devices:
                lines.append(device.format_status())
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Failed to list devices: {e}")
        return f"Failed to list devices: {e}"


async def control_device(
    device_name: str,
    action: str,
    value: Optional[str] = None,
) -> str:
    """
    Control a smart home device.
    
    Args:
        device_name: Name of the device
        action: "on", "off", "toggle", "brightness", "temperature"
        value: Optional value for brightness (0-100) or temperature
        
    Returns:
        Result message
    """
    try:
        service = get_mqtt_service()
        
        if not await service.connect():
            return "Failed to connect to MQTT broker. Check your configuration."
        
        device = service.get_device_by_name(device_name)
        if device is None:
            available = [d.name for d in service.list_devices()]
            if available:
                return f"Device '{device_name}' not found. Available devices: {', '.join(available)}"
            return f"Device '{device_name}' not found. No devices registered."
        
        action = action.lower()
        
        if action == "on":
            success = await service.turn_on(device)
            return f"✅ Turned on {device.name}" if success else f"❌ Failed to turn on {device.name}"
        
        elif action == "off":
            success = await service.turn_off(device)
            return f"✅ Turned off {device.name}" if success else f"❌ Failed to turn off {device.name}"
        
        elif action == "toggle":
            if device.is_on:
                success = await service.turn_off(device)
                return f"✅ Turned off {device.name}" if success else f"❌ Failed"
            else:
                success = await service.turn_on(device)
                return f"✅ Turned on {device.name}" if success else f"❌ Failed"
        
        elif action == "brightness" and value:
            try:
                brightness = int(value)
                success = await service.set_brightness(device, brightness)
                return f"✅ Set {device.name} brightness to {brightness}%" if success else f"❌ Failed"
            except ValueError:
                return f"Invalid brightness value: {value}. Use a number 0-100."
        
        elif action == "temperature" and value:
            try:
                temp = float(value)
                success = await service.set_temperature(device, temp)
                return f"✅ Set {device.name} temperature to {temp}°" if success else f"❌ Failed"
            except ValueError:
                return f"Invalid temperature value: {value}"
        
        else:
            return f"Unknown action: {action}. Use: on, off, toggle, brightness, temperature"
        
    except Exception as e:
        logger.error(f"Failed to control device: {e}")
        return f"Failed to control device: {e}"


async def get_device_status(device_name: str) -> str:
    """
    Get the status of a smart home device.
    
    Args:
        device_name: Name of the device
        
    Returns:
        Device status
    """
    try:
        service = get_mqtt_service()
        
        device = service.get_device_by_name(device_name)
        if device is None:
            return f"Device '{device_name}' not found."
        
        return device.format_status()
        
    except Exception as e:
        logger.error(f"Failed to get device status: {e}")
        return f"Failed to get device status: {e}"


# MQTT tool definitions for agent system
MQTT_TOOLS = [
    {
        "name": "list_smart_devices",
        "description": "List all smart home devices and their current states. Use this when the user asks about their smart home or devices.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "function": list_smart_devices,
    },
    {
        "name": "control_device",
        "description": "Control a smart home device (turn on/off, set brightness, etc.). Use this when the user wants to control lights, switches, or other devices.",
        "parameters": {
            "type": "object",
            "properties": {
                "device_name": {
                    "type": "string",
                    "description": "Name of the device to control"
                },
                "action": {
                    "type": "string",
                    "description": "Action: 'on', 'off', 'toggle', 'brightness', 'temperature'",
                    "enum": ["on", "off", "toggle", "brightness", "temperature"]
                },
                "value": {
                    "type": "string",
                    "description": "Value for brightness (0-100) or temperature (optional)"
                }
            },
            "required": ["device_name", "action"]
        },
        "function": control_device,
    },
    {
        "name": "get_device_status",
        "description": "Get the current status of a specific smart home device.",
        "parameters": {
            "type": "object",
            "properties": {
                "device_name": {
                    "type": "string",
                    "description": "Name of the device"
                }
            },
            "required": ["device_name"]
        },
        "function": get_device_status,
    },
]
