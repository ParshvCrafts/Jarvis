"""
Tests for the internal API module.
"""

import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestEventType:
    """Tests for EventType enum."""
    
    def test_all_event_types_exist(self):
        """Test all event types are defined."""
        from src.core.internal_api import EventType
        
        # Voice events
        assert EventType.WAKE_WORD_DETECTED
        assert EventType.COMMAND_RECEIVED
        assert EventType.RESPONSE_READY
        
        # Auth events
        assert EventType.USER_AUTHENTICATED
        assert EventType.AUTH_FAILED
        
        # IoT events
        assert EventType.DEVICE_DISCOVERED
        assert EventType.DEVICE_STATE_CHANGED
        
        # System events
        assert EventType.SYSTEM_STARTUP
        assert EventType.SYSTEM_SHUTDOWN


class TestEvent:
    """Tests for Event dataclass."""
    
    def test_event_creation(self):
        """Test Event can be created."""
        from src.core.internal_api import Event, EventType
        
        event = Event(
            event_type=EventType.COMMAND_RECEIVED,
            data={"text": "hello"},
            source="voice",
        )
        
        assert event.event_type == EventType.COMMAND_RECEIVED
        assert event.data["text"] == "hello"
        assert event.source == "voice"
        assert event.timestamp is not None
    
    def test_event_str(self):
        """Test Event string representation."""
        from src.core.internal_api import Event, EventType
        
        event = Event(
            event_type=EventType.WAKE_WORD_DETECTED,
            source="voice",
        )
        
        assert "wake_word_detected" in str(event)
        assert "voice" in str(event)


class TestEventBus:
    """Tests for EventBus."""
    
    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        """Test subscribing and publishing events."""
        from src.core.internal_api import EventBus, Event, EventType
        
        bus = EventBus()
        received_events = []
        
        async def handler(event):
            received_events.append(event)
        
        bus.subscribe(EventType.COMMAND_RECEIVED, handler)
        
        event = Event(
            event_type=EventType.COMMAND_RECEIVED,
            data={"text": "test"},
        )
        
        await bus.publish(event)
        
        assert len(received_events) == 1
        assert received_events[0].data["text"] == "test"
    
    @pytest.mark.asyncio
    async def test_global_handler(self):
        """Test global handler receives all events."""
        from src.core.internal_api import EventBus, Event, EventType
        
        bus = EventBus()
        received_events = []
        
        async def global_handler(event):
            received_events.append(event)
        
        bus.subscribe_all(global_handler)
        
        await bus.publish(Event(event_type=EventType.COMMAND_RECEIVED))
        await bus.publish(Event(event_type=EventType.WAKE_WORD_DETECTED))
        
        assert len(received_events) == 2
    
    @pytest.mark.asyncio
    async def test_event_history(self):
        """Test event history is maintained."""
        from src.core.internal_api import EventBus, Event, EventType
        
        bus = EventBus()
        
        await bus.publish(Event(event_type=EventType.COMMAND_RECEIVED, data={"n": 1}))
        await bus.publish(Event(event_type=EventType.COMMAND_RECEIVED, data={"n": 2}))
        await bus.publish(Event(event_type=EventType.WAKE_WORD_DETECTED))
        
        history = bus.get_history(limit=10)
        assert len(history) == 3
        
        cmd_history = bus.get_history(EventType.COMMAND_RECEIVED)
        assert len(cmd_history) == 2
    
    def test_unsubscribe(self):
        """Test unsubscribing from events."""
        from src.core.internal_api import EventBus, EventType
        
        bus = EventBus()
        
        async def handler(event):
            pass
        
        bus.subscribe(EventType.COMMAND_RECEIVED, handler)
        assert bus.unsubscribe(EventType.COMMAND_RECEIVED, handler) == True
        assert bus.unsubscribe(EventType.COMMAND_RECEIVED, handler) == False


class TestServiceRegistry:
    """Tests for ServiceRegistry."""
    
    def test_register_and_get(self):
        """Test registering and getting services."""
        from src.core.internal_api import ServiceRegistry
        
        registry = ServiceRegistry()
        
        class MockService:
            name = "test"
        
        service = MockService()
        registry.register("test_service", service)
        
        retrieved = registry.get("test_service")
        assert retrieved is service
        assert retrieved.name == "test"
    
    def test_unregister(self):
        """Test unregistering services."""
        from src.core.internal_api import ServiceRegistry
        
        registry = ServiceRegistry()
        registry.register("test", "value")
        
        assert registry.unregister("test") == True
        assert registry.get("test") is None
        assert registry.unregister("test") == False
    
    def test_list_services(self):
        """Test listing services."""
        from src.core.internal_api import ServiceRegistry
        
        registry = ServiceRegistry()
        registry.register("service1", "value1")
        registry.register("service2", "value2")
        
        services = registry.list_services()
        assert "service1" in services
        assert "service2" in services


class TestInternalAPI:
    """Tests for InternalAPI."""
    
    def test_api_creation(self):
        """Test InternalAPI can be created."""
        from src.core.internal_api import InternalAPI
        
        api = InternalAPI()
        assert api.events is not None
        assert api.services is not None
    
    @pytest.mark.asyncio
    async def test_notify_command(self):
        """Test notify_command helper."""
        from src.core.internal_api import InternalAPI, EventType
        
        api = InternalAPI()
        received = []
        
        async def handler(event):
            received.append(event)
        
        api.events.subscribe(EventType.COMMAND_RECEIVED, handler)
        await api.notify_command("test command", source="test")
        
        assert len(received) == 1
        assert received[0].data["text"] == "test command"
    
    @pytest.mark.asyncio
    async def test_notify_device_state(self):
        """Test notify_device_state helper."""
        from src.core.internal_api import InternalAPI, EventType
        
        api = InternalAPI()
        received = []
        
        async def handler(event):
            received.append(event)
        
        api.events.subscribe(EventType.DEVICE_STATE_CHANGED, handler)
        await api.notify_device_state("light_1", "on", {"brightness": 100})
        
        assert len(received) == 1
        assert received[0].data["device_id"] == "light_1"
        assert received[0].data["state"] == "on"
        assert received[0].data["brightness"] == 100


class TestGlobalAPI:
    """Tests for global API functions."""
    
    def test_get_internal_api(self):
        """Test get_internal_api returns singleton."""
        from src.core.internal_api import get_internal_api
        
        api1 = get_internal_api()
        api2 = get_internal_api()
        
        assert api1 is api2
    
    def test_get_event_bus(self):
        """Test get_event_bus returns event bus."""
        from src.core.internal_api import get_event_bus
        
        bus = get_event_bus()
        assert bus is not None
    
    def test_get_service_registry(self):
        """Test get_service_registry returns registry."""
        from src.core.internal_api import get_service_registry
        
        registry = get_service_registry()
        assert registry is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
