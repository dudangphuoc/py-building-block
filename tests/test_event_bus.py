"""
Tests for Event Bus
"""

import pytest

from application.event_bus import EventBus
from application.entity import DomainEvent


class TestEventBus:
    """Tests for EventBus class."""
    
    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        """Test subscribing and publishing events."""
        bus = EventBus()
        events_received = []
        
        async def handler(event: DomainEvent):
            events_received.append(event)
        
        bus.subscribe("TestEvent", handler)
        
        event = DomainEvent(event_type="TestEvent", data={"key": "value"})
        await bus.publish(event)
        
        assert len(events_received) == 1
        assert events_received[0].event_type == "TestEvent"
    
    @pytest.mark.asyncio
    async def test_multiple_handlers(self):
        """Test multiple handlers for same event type."""
        bus = EventBus()
        handler1_calls = []
        handler2_calls = []
        
        async def handler1(event: DomainEvent):
            handler1_calls.append(event)
        
        async def handler2(event: DomainEvent):
            handler2_calls.append(event)
        
        bus.subscribe("TestEvent", handler1)
        bus.subscribe("TestEvent", handler2)
        
        event = DomainEvent(event_type="TestEvent")
        await bus.publish(event)
        
        assert len(handler1_calls) == 1
        assert len(handler2_calls) == 1
    
    @pytest.mark.asyncio
    async def test_publish_without_handlers(self):
        """Test publishing event with no handlers."""
        bus = EventBus()
        
        event = DomainEvent(event_type="TestEvent")
        # Should not raise exception
        await bus.publish(event)
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test unsubscribing a handler."""
        bus = EventBus()
        calls = []
        
        async def handler(event: DomainEvent):
            calls.append(event)
        
        bus.subscribe("TestEvent", handler)
        
        event1 = DomainEvent(event_type="TestEvent")
        await bus.publish(event1)
        
        assert len(calls) == 1
        
        # Unsubscribe
        bus.unsubscribe("TestEvent", handler)
        
        event2 = DomainEvent(event_type="TestEvent")
        await bus.publish(event2)
        
        # Should still be 1, not 2
        assert len(calls) == 1
    
    @pytest.mark.asyncio
    async def test_publish_all(self):
        """Test publishing multiple events."""
        bus = EventBus()
        events_received = []
        
        async def handler(event: DomainEvent):
            events_received.append(event)
        
        bus.subscribe("Event1", handler)
        bus.subscribe("Event2", handler)
        
        events = [
            DomainEvent(event_type="Event1"),
            DomainEvent(event_type="Event2"),
        ]
        
        await bus.publish_all(events)
        
        assert len(events_received) == 2
    
    @pytest.mark.asyncio
    async def test_handler_error_isolation(self):
        """Test that handler errors don't stop other handlers."""
        bus = EventBus()
        handler1_calls = []
        handler2_calls = []
        
        async def failing_handler(event: DomainEvent):
            raise Exception("Handler failed")
        
        async def success_handler(event: DomainEvent):
            handler2_calls.append(event)
        
        bus.subscribe("TestEvent", failing_handler)
        bus.subscribe("TestEvent", success_handler)
        
        event = DomainEvent(event_type="TestEvent")
        await bus.publish(event)
        
        # Success handler should still be called
        assert len(handler2_calls) == 1
    
    def test_get_handler_count(self):
        """Test getting handler count for event type."""
        bus = EventBus()
        
        async def handler1(event):
            pass
        
        async def handler2(event):
            pass
        
        assert bus.get_handler_count("TestEvent") == 0
        
        bus.subscribe("TestEvent", handler1)
        assert bus.get_handler_count("TestEvent") == 1
        
        bus.subscribe("TestEvent", handler2)
        assert bus.get_handler_count("TestEvent") == 2
    
    def test_clear_handlers(self):
        """Test clearing handlers."""
        bus = EventBus()
        
        async def handler(event):
            pass
        
        bus.subscribe("Event1", handler)
        bus.subscribe("Event2", handler)
        
        # Clear specific event type
        bus.clear_handlers("Event1")
        assert bus.get_handler_count("Event1") == 0
        assert bus.get_handler_count("Event2") == 1
        
        # Clear all
        bus.clear_handlers()
        assert bus.get_handler_count("Event2") == 0
