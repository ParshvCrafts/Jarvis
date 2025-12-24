"""
Internal API for JARVIS components.

Provides a unified interface for communication between:
- Voice pipeline
- Telegram bot
- IoT controller
- Agent system
- Proactive intelligence

This allows components to trigger actions in other components
without tight coupling.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Awaitable
from datetime import datetime

from loguru import logger


class EventType(Enum):
    """Types of internal events."""
    # Voice events
    WAKE_WORD_DETECTED = "wake_word_detected"
    COMMAND_RECEIVED = "command_received"
    RESPONSE_READY = "response_ready"
    TTS_STARTED = "tts_started"
    TTS_COMPLETED = "tts_completed"
    TTS_INTERRUPTED = "tts_interrupted"
    
    # Authentication events
    USER_AUTHENTICATED = "user_authenticated"
    USER_DEAUTHENTICATED = "user_deauthenticated"
    AUTH_FAILED = "auth_failed"
    
    # IoT events
    DEVICE_DISCOVERED = "device_discovered"
    DEVICE_STATE_CHANGED = "device_state_changed"
    DEVICE_OFFLINE = "device_offline"
    DEVICE_COMMAND_SENT = "device_command_sent"
    DEVICE_COMMAND_RESULT = "device_command_result"
    
    # Telegram events
    TELEGRAM_MESSAGE = "telegram_message"
    TELEGRAM_COMMAND = "telegram_command"
    TELEGRAM_VOICE_NOTE = "telegram_voice_note"
    
    # System events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_ERROR = "system_error"
    
    # Proactive events
    ROUTINE_TRIGGERED = "routine_triggered"
    GEOFENCE_ENTERED = "geofence_entered"
    GEOFENCE_EXITED = "geofence_exited"
    REMINDER_DUE = "reminder_due"


@dataclass
class Event:
    """An internal event."""
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __str__(self) -> str:
        return f"Event({self.event_type.value}, source={self.source})"


EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """
    Central event bus for internal communication.
    
    Allows components to publish and subscribe to events
    without direct dependencies on each other.
    """
    
    def __init__(self):
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []
        self._event_history: List[Event] = []
        self._max_history = 100
    
    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> None:
        """
        Subscribe to a specific event type.
        
        Args:
            event_type: Type of event to subscribe to.
            handler: Async function to call when event occurs.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed handler to {event_type.value}")
    
    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to all events."""
        self._global_handlers.append(handler)
        logger.debug("Subscribed global handler")
    
    def unsubscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> bool:
        """
        Unsubscribe from an event type.
        
        Returns:
            True if handler was found and removed.
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                return True
            except ValueError:
                pass
        return False
    
    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event: Event to publish.
        """
        logger.debug(f"Publishing event: {event}")
        
        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Call specific handlers
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Event handler error for {event.event_type}: {e}")
        
        # Call global handlers
        for handler in self._global_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Global event handler error: {e}")
    
    def publish_sync(self, event: Event) -> None:
        """Publish event synchronously (creates event loop if needed)."""
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self.publish(event))
        except RuntimeError:
            asyncio.run(self.publish(event))
    
    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 10,
    ) -> List[Event]:
        """Get recent events from history."""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]


class ServiceRegistry:
    """
    Registry for internal services.
    
    Allows components to register themselves and be discovered
    by other components.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
    
    def register(self, name: str, service: Any) -> None:
        """Register a service."""
        self._services[name] = service
        logger.debug(f"Registered service: {name}")
    
    def unregister(self, name: str) -> bool:
        """Unregister a service."""
        if name in self._services:
            del self._services[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[Any]:
        """Get a service by name."""
        return self._services.get(name)
    
    def list_services(self) -> List[str]:
        """List all registered services."""
        return list(self._services.keys())


class InternalAPI:
    """
    Unified internal API for JARVIS.
    
    Provides:
    - Event bus for pub/sub communication
    - Service registry for component discovery
    - Helper methods for common operations
    """
    
    def __init__(self):
        self.events = EventBus()
        self.services = ServiceRegistry()
    
    # Convenience methods for common events
    
    async def notify_wake_word(self, wake_word: str, confidence: float) -> None:
        """Notify that wake word was detected."""
        await self.events.publish(Event(
            event_type=EventType.WAKE_WORD_DETECTED,
            data={"wake_word": wake_word, "confidence": confidence},
            source="voice",
        ))
    
    async def notify_command(self, text: str, source: str = "voice") -> None:
        """Notify that a command was received."""
        await self.events.publish(Event(
            event_type=EventType.COMMAND_RECEIVED,
            data={"text": text},
            source=source,
        ))
    
    async def notify_response(self, text: str, for_command: str = "") -> None:
        """Notify that a response is ready."""
        await self.events.publish(Event(
            event_type=EventType.RESPONSE_READY,
            data={"text": text, "for_command": for_command},
            source="agent",
        ))
    
    async def notify_device_state(
        self,
        device_id: str,
        state: str,
        data: Optional[Dict] = None,
    ) -> None:
        """Notify that a device state changed."""
        await self.events.publish(Event(
            event_type=EventType.DEVICE_STATE_CHANGED,
            data={"device_id": device_id, "state": state, **(data or {})},
            source="iot",
        ))
    
    async def notify_user_authenticated(self, user_id: str, method: str) -> None:
        """Notify that a user was authenticated."""
        await self.events.publish(Event(
            event_type=EventType.USER_AUTHENTICATED,
            data={"user_id": user_id, "method": method},
            source="auth",
        ))
    
    async def notify_error(self, error: str, component: str) -> None:
        """Notify of a system error."""
        await self.events.publish(Event(
            event_type=EventType.SYSTEM_ERROR,
            data={"error": error, "component": component},
            source=component,
        ))
    
    # Service shortcuts
    
    def get_voice_pipeline(self):
        """Get the voice pipeline service."""
        return self.services.get("voice_pipeline")
    
    def get_telegram_bot(self):
        """Get the Telegram bot service."""
        return self.services.get("telegram_bot")
    
    def get_iot_controller(self):
        """Get the IoT controller service."""
        return self.services.get("iot_controller")
    
    def get_agent_supervisor(self):
        """Get the agent supervisor service."""
        return self.services.get("agent_supervisor")
    
    def get_auth_manager(self):
        """Get the authentication manager service."""
        return self.services.get("auth_manager")


# Global instance
_api: Optional[InternalAPI] = None


def get_internal_api() -> InternalAPI:
    """Get the global internal API instance."""
    global _api
    if _api is None:
        _api = InternalAPI()
    return _api


def get_event_bus() -> EventBus:
    """Get the global event bus."""
    return get_internal_api().events


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry."""
    return get_internal_api().services
