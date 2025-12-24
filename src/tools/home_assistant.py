"""
Home Assistant Integration for JARVIS - Phase 7

Provides smart home control via Home Assistant REST API (FREE, self-hosted).

Features:
- List all entities (lights, switches, sensors, etc.)
- Control devices (turn on/off, set brightness, etc.)
- Get entity states
- Call Home Assistant services

Setup:
1. Install Home Assistant (https://www.home-assistant.io/)
2. Create a Long-Lived Access Token in HA profile
3. Configure URL and token in settings.yaml

API Documentation: https://developers.home-assistant.io/docs/api/rest
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx
from loguru import logger


class EntityDomain(Enum):
    """Home Assistant entity domains."""
    LIGHT = "light"
    SWITCH = "switch"
    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    CLIMATE = "climate"
    COVER = "cover"
    FAN = "fan"
    LOCK = "lock"
    MEDIA_PLAYER = "media_player"
    AUTOMATION = "automation"
    SCENE = "scene"
    SCRIPT = "script"
    INPUT_BOOLEAN = "input_boolean"
    INPUT_NUMBER = "input_number"
    UNKNOWN = "unknown"


@dataclass
class HAEntity:
    """Represents a Home Assistant entity."""
    entity_id: str
    state: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    last_changed: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    
    @property
    def domain(self) -> EntityDomain:
        """Get entity domain."""
        domain_str = self.entity_id.split(".")[0]
        try:
            return EntityDomain(domain_str)
        except ValueError:
            return EntityDomain.UNKNOWN
    
    @property
    def name(self) -> str:
        """Get friendly name."""
        return self.attributes.get("friendly_name", self.entity_id)
    
    @property
    def is_on(self) -> bool:
        """Check if entity is on."""
        return self.state.lower() in ["on", "open", "unlocked", "home", "playing"]
    
    @property
    def brightness(self) -> Optional[int]:
        """Get brightness (0-255 from HA, converted to 0-100)."""
        brightness = self.attributes.get("brightness")
        if brightness is not None:
            return int(brightness / 255 * 100)
        return None
    
    @property
    def temperature(self) -> Optional[float]:
        """Get temperature for sensors/climate."""
        if self.domain == EntityDomain.CLIMATE:
            return self.attributes.get("current_temperature")
        elif self.domain == EntityDomain.SENSOR:
            try:
                return float(self.state)
            except ValueError:
                return None
        return None
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "HAEntity":
        """Create entity from API response."""
        last_changed = None
        last_updated = None
        
        if "last_changed" in data:
            try:
                last_changed = datetime.fromisoformat(data["last_changed"].replace("Z", "+00:00"))
            except Exception:
                pass
        
        if "last_updated" in data:
            try:
                last_updated = datetime.fromisoformat(data["last_updated"].replace("Z", "+00:00"))
            except Exception:
                pass
        
        return cls(
            entity_id=data.get("entity_id", ""),
            state=data.get("state", "unknown"),
            attributes=data.get("attributes", {}),
            last_changed=last_changed,
            last_updated=last_updated,
        )
    
    def format_status(self) -> str:
        """Format entity status for display."""
        domain = self.domain
        
        if domain == EntityDomain.LIGHT:
            if self.is_on:
                brightness = self.brightness
                if brightness is not None:
                    return f"💡 **{self.name}**: On ({brightness}%)"
                return f"💡 **{self.name}**: On"
            return f"⚫ **{self.name}**: Off"
        
        elif domain == EntityDomain.SWITCH:
            return f"🔌 **{self.name}**: {'On' if self.is_on else 'Off'}"
        
        elif domain == EntityDomain.SENSOR:
            unit = self.attributes.get("unit_of_measurement", "")
            return f"📊 **{self.name}**: {self.state} {unit}"
        
        elif domain == EntityDomain.BINARY_SENSOR:
            device_class = self.attributes.get("device_class", "")
            if device_class == "door":
                return f"🚪 **{self.name}**: {'Open' if self.is_on else 'Closed'}"
            elif device_class == "motion":
                return f"🏃 **{self.name}**: {'Detected' if self.is_on else 'Clear'}"
            return f"📍 **{self.name}**: {'On' if self.is_on else 'Off'}"
        
        elif domain == EntityDomain.CLIMATE:
            current = self.attributes.get("current_temperature")
            target = self.attributes.get("temperature")
            hvac = self.state
            return f"🌡️ **{self.name}**: {current}° (target: {target}°) - {hvac}"
        
        elif domain == EntityDomain.LOCK:
            return f"🔒 **{self.name}**: {'Locked' if not self.is_on else 'Unlocked'}"
        
        elif domain == EntityDomain.COVER:
            position = self.attributes.get("current_position", "")
            if position:
                return f"🪟 **{self.name}**: {position}% open"
            return f"🪟 **{self.name}**: {'Open' if self.is_on else 'Closed'}"
        
        elif domain == EntityDomain.FAN:
            speed = self.attributes.get("percentage", "")
            if speed and self.is_on:
                return f"🌀 **{self.name}**: On ({speed}%)"
            return f"🌀 **{self.name}**: {'On' if self.is_on else 'Off'}"
        
        elif domain == EntityDomain.MEDIA_PLAYER:
            media = self.attributes.get("media_title", "")
            if media and self.is_on:
                return f"🎵 **{self.name}**: Playing - {media}"
            return f"🎵 **{self.name}**: {self.state}"
        
        else:
            return f"**{self.name}**: {self.state}"


class HomeAssistantService:
    """
    Home Assistant service for JARVIS.
    
    Provides smart home control via the Home Assistant REST API.
    Requires a running Home Assistant instance with a Long-Lived Access Token.
    """
    
    def __init__(
        self,
        url: str = "http://homeassistant.local:8123",
        token: str = "",
        timeout: int = 30,
    ):
        """
        Initialize Home Assistant service.
        
        Args:
            url: Home Assistant URL (e.g., http://homeassistant.local:8123)
            token: Long-Lived Access Token
            timeout: Request timeout in seconds
        """
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._entities_cache: Dict[str, HAEntity] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 60  # seconds
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.url,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def is_available(self) -> bool:
        """Check if Home Assistant is available."""
        if not self.token:
            return False
        
        try:
            client = await self._get_client()
            response = await client.get("/api/")
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Home Assistant not available: {e}")
            return False
    
    async def get_states(self, force_refresh: bool = False) -> List[HAEntity]:
        """
        Get all entity states.
        
        Args:
            force_refresh: Force refresh even if cache is valid
            
        Returns:
            List of HAEntity objects
        """
        # Check cache
        if not force_refresh and self._cache_time:
            age = (datetime.now() - self._cache_time).total_seconds()
            if age < self._cache_ttl and self._entities_cache:
                return list(self._entities_cache.values())
        
        try:
            client = await self._get_client()
            response = await client.get("/api/states")
            response.raise_for_status()
            
            entities = []
            for data in response.json():
                entity = HAEntity.from_api_response(data)
                entities.append(entity)
                self._entities_cache[entity.entity_id] = entity
            
            self._cache_time = datetime.now()
            return entities
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to get states: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to get states: {e}")
            return []
    
    async def get_entity(self, entity_id: str) -> Optional[HAEntity]:
        """Get a specific entity by ID."""
        try:
            client = await self._get_client()
            response = await client.get(f"/api/states/{entity_id}")
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            entity = HAEntity.from_api_response(response.json())
            self._entities_cache[entity_id] = entity
            return entity
            
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
            return None
    
    async def get_entity_by_name(self, name: str) -> Optional[HAEntity]:
        """Get entity by friendly name (case-insensitive)."""
        entities = await self.get_states()
        name_lower = name.lower()
        
        for entity in entities:
            if entity.name.lower() == name_lower or name_lower in entity.name.lower():
                return entity
        
        return None
    
    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Call a Home Assistant service.
        
        Args:
            domain: Service domain (e.g., "light", "switch")
            service: Service name (e.g., "turn_on", "turn_off")
            entity_id: Target entity ID
            data: Additional service data
            
        Returns:
            True if successful
        """
        try:
            client = await self._get_client()
            
            payload = data or {}
            if entity_id:
                payload["entity_id"] = entity_id
            
            response = await client.post(
                f"/api/services/{domain}/{service}",
                json=payload,
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error(f"Failed to call service {domain}.{service}: {e}")
            return False
    
    async def turn_on(
        self,
        entity_id: str,
        brightness: Optional[int] = None,
        color_temp: Optional[int] = None,
    ) -> bool:
        """Turn on an entity."""
        domain = entity_id.split(".")[0]
        data = {}
        
        if brightness is not None and domain == "light":
            data["brightness_pct"] = brightness
        if color_temp is not None and domain == "light":
            data["color_temp"] = color_temp
        
        return await self.call_service(domain, "turn_on", entity_id, data if data else None)
    
    async def turn_off(self, entity_id: str) -> bool:
        """Turn off an entity."""
        domain = entity_id.split(".")[0]
        return await self.call_service(domain, "turn_off", entity_id)
    
    async def toggle(self, entity_id: str) -> bool:
        """Toggle an entity."""
        domain = entity_id.split(".")[0]
        return await self.call_service(domain, "toggle", entity_id)
    
    async def set_climate_temperature(
        self,
        entity_id: str,
        temperature: float,
        hvac_mode: Optional[str] = None,
    ) -> bool:
        """Set climate/thermostat temperature."""
        data = {"temperature": temperature}
        if hvac_mode:
            data["hvac_mode"] = hvac_mode
        return await self.call_service("climate", "set_temperature", entity_id, data)
    
    async def lock(self, entity_id: str) -> bool:
        """Lock a lock entity."""
        return await self.call_service("lock", "lock", entity_id)
    
    async def unlock(self, entity_id: str) -> bool:
        """Unlock a lock entity."""
        return await self.call_service("lock", "unlock", entity_id)


# Singleton instance
_ha_service: Optional[HomeAssistantService] = None


def get_home_assistant_service(
    url: str = "http://homeassistant.local:8123",
    token: str = "",
) -> HomeAssistantService:
    """Get or create Home Assistant service singleton."""
    global _ha_service
    if _ha_service is None:
        _ha_service = HomeAssistantService(url=url, token=token)
    return _ha_service


# =============================================================================
# Tool Functions for Agent Integration
# =============================================================================

async def list_ha_entities(domain: Optional[str] = None) -> str:
    """
    List Home Assistant entities.
    
    Args:
        domain: Optional filter by domain (light, switch, sensor, etc.)
        
    Returns:
        Formatted list of entities
    """
    try:
        service = get_home_assistant_service()
        
        if not await service.is_available():
            return "Home Assistant not available. Check URL and token in settings."
        
        entities = await service.get_states()
        
        if domain:
            entities = [e for e in entities if e.domain.value == domain]
        
        if not entities:
            return f"No entities found{' for domain: ' + domain if domain else ''}."
        
        # Group by domain
        by_domain: Dict[EntityDomain, List[HAEntity]] = {}
        for entity in entities:
            if entity.domain not in by_domain:
                by_domain[entity.domain] = []
            by_domain[entity.domain].append(entity)
        
        lines = [f"**Home Assistant Entities** ({len(entities)} total)\n"]
        
        for entity_domain, domain_entities in sorted(by_domain.items(), key=lambda x: x[0].value):
            lines.append(f"\n**{entity_domain.value.replace('_', ' ').title()}s** ({len(domain_entities)}):")
            for entity in domain_entities[:10]:  # Limit per domain
                lines.append(f"  {entity.format_status()}")
            if len(domain_entities) > 10:
                lines.append(f"  ... and {len(domain_entities) - 10} more")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Failed to list entities: {e}")
        return f"Failed to list entities: {e}"


async def control_ha_entity(
    entity_name: str,
    action: str,
    value: Optional[str] = None,
) -> str:
    """
    Control a Home Assistant entity.
    
    Args:
        entity_name: Entity name or ID
        action: "on", "off", "toggle", "brightness", "temperature", "lock", "unlock"
        value: Optional value for brightness (0-100) or temperature
        
    Returns:
        Result message
    """
    try:
        service = get_home_assistant_service()
        
        if not await service.is_available():
            return "Home Assistant not available. Check configuration."
        
        # Find entity
        if "." in entity_name:
            entity = await service.get_entity(entity_name)
        else:
            entity = await service.get_entity_by_name(entity_name)
        
        if entity is None:
            return f"Entity '{entity_name}' not found."
        
        action = action.lower()
        
        if action == "on":
            brightness = int(value) if value else None
            success = await service.turn_on(entity.entity_id, brightness=brightness)
            return f"✅ Turned on {entity.name}" if success else f"❌ Failed"
        
        elif action == "off":
            success = await service.turn_off(entity.entity_id)
            return f"✅ Turned off {entity.name}" if success else f"❌ Failed"
        
        elif action == "toggle":
            success = await service.toggle(entity.entity_id)
            return f"✅ Toggled {entity.name}" if success else f"❌ Failed"
        
        elif action == "brightness" and value:
            brightness = int(value)
            success = await service.turn_on(entity.entity_id, brightness=brightness)
            return f"✅ Set {entity.name} brightness to {brightness}%" if success else f"❌ Failed"
        
        elif action == "temperature" and value:
            temp = float(value)
            success = await service.set_climate_temperature(entity.entity_id, temp)
            return f"✅ Set {entity.name} to {temp}°" if success else f"❌ Failed"
        
        elif action == "lock":
            success = await service.lock(entity.entity_id)
            return f"✅ Locked {entity.name}" if success else f"❌ Failed"
        
        elif action == "unlock":
            success = await service.unlock(entity.entity_id)
            return f"✅ Unlocked {entity.name}" if success else f"❌ Failed"
        
        else:
            return f"Unknown action: {action}"
        
    except Exception as e:
        logger.error(f"Failed to control entity: {e}")
        return f"Failed to control entity: {e}"


async def get_ha_entity_status(entity_name: str) -> str:
    """
    Get status of a Home Assistant entity.
    
    Args:
        entity_name: Entity name or ID
        
    Returns:
        Entity status
    """
    try:
        service = get_home_assistant_service()
        
        if not await service.is_available():
            return "Home Assistant not available."
        
        if "." in entity_name:
            entity = await service.get_entity(entity_name)
        else:
            entity = await service.get_entity_by_name(entity_name)
        
        if entity is None:
            return f"Entity '{entity_name}' not found."
        
        return entity.format_status()
        
    except Exception as e:
        logger.error(f"Failed to get entity status: {e}")
        return f"Failed to get entity status: {e}"


# Home Assistant tool definitions
HOME_ASSISTANT_TOOLS = [
    {
        "name": "list_ha_entities",
        "description": "List all Home Assistant smart home entities. Use this to see available devices.",
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Filter by domain: light, switch, sensor, climate, lock, cover, fan",
                    "enum": ["light", "switch", "sensor", "binary_sensor", "climate", "lock", "cover", "fan", "media_player"]
                }
            },
            "required": []
        },
        "function": list_ha_entities,
    },
    {
        "name": "control_ha_entity",
        "description": "Control a Home Assistant entity (turn on/off, set brightness, etc.)",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "Entity name or ID (e.g., 'Living Room Light' or 'light.living_room')"
                },
                "action": {
                    "type": "string",
                    "description": "Action to perform",
                    "enum": ["on", "off", "toggle", "brightness", "temperature", "lock", "unlock"]
                },
                "value": {
                    "type": "string",
                    "description": "Value for brightness (0-100) or temperature"
                }
            },
            "required": ["entity_name", "action"]
        },
        "function": control_ha_entity,
    },
    {
        "name": "get_ha_entity_status",
        "description": "Get the current status of a Home Assistant entity.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_name": {
                    "type": "string",
                    "description": "Entity name or ID"
                }
            },
            "required": ["entity_name"]
        },
        "function": get_ha_entity_status,
    },
]
