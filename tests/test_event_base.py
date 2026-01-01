"""
Tests for Event Base Module
"""

import json
import pytest
from datetime import datetime

from pubsub.event_base import Event, EventSerializer


class TestEvent:
    """Tests for Event class."""
    
    def test_event_creation_with_defaults(self):
        """Test creating an event with auto-generated fields."""
        event = Event(
            domain="test",
            action="created",
            data={"key": "value"}
        )
        
        assert event.domain == "test"
        assert event.action == "created"
        assert event.data == {"key": "value"}
        assert event.event_id is not None
        assert event.timestamp is not None
        assert event.version == "1.0"
    
    def test_event_creation_with_custom_fields(self):
        """Test creating an event with custom fields."""
        custom_id = "custom-event-id"
        custom_timestamp = "2026-01-01T12:00:00"
        
        event = Event(
            domain="test",
            action="updated",
            data={"status": "active"},
            event_id=custom_id,
            timestamp=custom_timestamp,
            version="2.0"
        )
        
        assert event.event_id == custom_id
        assert event.timestamp == custom_timestamp
        assert event.version == "2.0"
    
    def test_get_routing_key(self):
        """Test routing key generation."""
        event = Event(
            domain="order",
            action="created",
            data={}
        )
        
        assert event.get_routing_key() == "order.created"


class TestEventSerializer:
    """Tests for EventSerializer class."""
    
    def test_to_json(self):
        """Test serializing an event to JSON."""
        event = Event(
            domain="test",
            action="action",
            data={"field": "value"},
            event_id="test-id",
            timestamp="2026-01-01T00:00:00",
            version="1.0"
        )
        
        json_str = EventSerializer.to_json(event)
        data = json.loads(json_str)
        
        assert data["domain"] == "test"
        assert data["action"] == "action"
        assert data["data"]["field"] == "value"
        assert data["event_id"] == "test-id"
        assert data["timestamp"] == "2026-01-01T00:00:00"
        assert data["version"] == "1.0"
    
    def test_from_json(self):
        """Test deserializing an event from JSON."""
        json_str = json.dumps({
            "domain": "test",
            "action": "action",
            "data": {"field": "value"},
            "event_id": "test-id",
            "timestamp": "2026-01-01T00:00:00",
            "version": "1.0"
        })
        
        event = EventSerializer.from_json(json_str)
        
        assert event.domain == "test"
        assert event.action == "action"
        assert event.data["field"] == "value"
        assert event.event_id == "test-id"
        assert event.timestamp == "2026-01-01T00:00:00"
        assert event.version == "1.0"
    
    def test_from_json_with_missing_optional_fields(self):
        """Test deserializing JSON with missing optional fields."""
        json_str = json.dumps({
            "domain": "test",
            "action": "action",
            "data": {"field": "value"}
        })
        
        event = EventSerializer.from_json(json_str)
        
        assert event.domain == "test"
        assert event.action == "action"
        assert event.data["field"] == "value"
        assert event.event_id is not None  # Auto-generated
        assert event.timestamp is not None  # Auto-generated
        assert event.version == "1.0"  # Default
    
    def test_from_json_with_missing_required_fields(self):
        """Test that deserializing without required fields raises error."""
        json_str = json.dumps({
            "domain": "test"
            # Missing action and data
        })
        
        with pytest.raises(ValueError, match="Missing required fields"):
            EventSerializer.from_json(json_str)
    
    def test_from_json_with_invalid_json(self):
        """Test that invalid JSON raises error."""
        with pytest.raises(ValueError, match="Invalid JSON format"):
            EventSerializer.from_json("not valid json")
    
    def test_to_json_with_non_serializable_data(self):
        """Test that non-JSON-serializable data raises error."""
        event = Event(
            domain="test",
            action="action",
            data={"datetime": datetime.now()}  # datetime is not JSON-serializable
        )
        
        with pytest.raises(TypeError, match="JSON-serializable"):
            EventSerializer.to_json(event)
    
    def test_roundtrip_serialization(self):
        """Test that serialization and deserialization preserve data."""
        original_event = Event(
            domain="order",
            action="created",
            data={
                "order_id": "ORD-123",
                "amount": 99.99,
                "items": [{"id": 1, "qty": 2}]
            },
            event_id="evt-123",
            timestamp="2026-01-01T12:00:00",
            version="1.0"
        )
        
        json_str = EventSerializer.to_json(original_event)
        restored_event = EventSerializer.from_json(json_str)
        
        assert restored_event.domain == original_event.domain
        assert restored_event.action == original_event.action
        assert restored_event.data == original_event.data
        assert restored_event.event_id == original_event.event_id
        assert restored_event.timestamp == original_event.timestamp
        assert restored_event.version == original_event.version
