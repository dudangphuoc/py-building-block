"""
Tests for Application Layer - Entity and DomainEvent
"""

import pytest

from application.entity import Entity, DomainEvent


class TestDomainEvent:
    """Tests for DomainEvent class."""
    
    def test_domain_event_creation(self):
        """Test creating a domain event."""
        event = DomainEvent(
            aggregate_id="123",
            event_type="TestEvent",
            data={"key": "value"}
        )
        
        assert event.aggregate_id == "123"
        assert event.event_type == "TestEvent"
        assert event.data == {"key": "value"}
        assert event.event_id is not None
        assert event.occurred_at is not None
    
    def test_domain_event_requires_event_type(self):
        """Test that event_type is required."""
        with pytest.raises(ValueError, match="event_type is required"):
            DomainEvent()
    
    def test_domain_event_defaults(self):
        """Test default values for domain event."""
        event = DomainEvent(event_type="TestEvent")
        
        assert event.aggregate_id == ""
        assert event.data == {}
        assert event.event_id is not None
        assert event.occurred_at is not None


class TestOrder(Entity):
    """Test entity for testing Entity base class."""
    
    def __init__(self, order_id: str):
        super().__init__()
        self.id = order_id
        self.items = []
    
    def add_item(self, item: str):
        """Add item and raise event."""
        self.items.append(item)
        self.raise_event(DomainEvent(
            aggregate_id=self.id,
            event_type="ItemAdded",
            data={"item": item}
        ))


class TestEntity:
    """Tests for Entity base class."""
    
    def test_entity_initialization(self):
        """Test entity initialization."""
        order = TestOrder("ORD-123")
        
        assert order.id == "ORD-123"
        assert len(order.get_domain_events()) == 0
    
    def test_entity_raise_event(self):
        """Test raising domain events."""
        order = TestOrder("ORD-123")
        
        order.raise_event(DomainEvent(
            aggregate_id=order.id,
            event_type="TestEvent",
            data={"test": "data"}
        ))
        
        events = order.get_domain_events()
        assert len(events) == 1
        assert events[0].event_type == "TestEvent"
        assert events[0].aggregate_id == "ORD-123"
    
    def test_entity_multiple_events(self):
        """Test raising multiple events."""
        order = TestOrder("ORD-123")
        
        order.add_item("item1")
        order.add_item("item2")
        order.add_item("item3")
        
        events = order.get_domain_events()
        assert len(events) == 3
        assert all(e.event_type == "ItemAdded" for e in events)
    
    def test_entity_clear_events(self):
        """Test clearing domain events."""
        order = TestOrder("ORD-123")
        
        order.add_item("item1")
        order.add_item("item2")
        
        assert len(order.get_domain_events()) == 2
        
        order.clear_domain_events()
        
        assert len(order.get_domain_events()) == 0
    
    def test_entity_equality(self):
        """Test entity equality by ID."""
        order1 = TestOrder("ORD-123")
        order2 = TestOrder("ORD-123")
        order3 = TestOrder("ORD-456")
        
        assert order1 == order2
        assert order1 != order3
    
    def test_entity_hash(self):
        """Test entity hashing."""
        order1 = TestOrder("ORD-123")
        order2 = TestOrder("ORD-123")
        
        # Should have same hash
        assert hash(order1) == hash(order2)
        
        # Should work in sets
        order_set = {order1, order2}
        assert len(order_set) == 1
