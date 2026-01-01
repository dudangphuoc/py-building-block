"""
Tests for Unit of Work
"""

import pytest

from application.entity import Entity, DomainEvent
from application.event_bus import EventBus
from application.unit_of_work import InMemoryUnitOfWork


class TestEntity(Entity):
    """Test entity for unit of work tests."""
    
    def __init__(self, entity_id: str):
        super().__init__()
        self.id = entity_id
    
    def do_something(self):
        """Perform action that raises event."""
        self.raise_event(DomainEvent(
            aggregate_id=self.id,
            event_type="SomethingDone",
            data={"entity_id": self.id}
        ))


class TestUnitOfWork:
    """Tests for Unit of Work."""
    
    @pytest.mark.asyncio
    async def test_register_entity(self):
        """Test registering entity for tracking."""
        uow = InMemoryUnitOfWork()
        entity = TestEntity("123")
        
        uow.register_entity(entity)
        
        # Entity should be tracked
        assert entity in uow._entities_with_events
    
    @pytest.mark.asyncio
    async def test_collect_events(self):
        """Test collecting events from entities."""
        uow = InMemoryUnitOfWork()
        
        entity1 = TestEntity("1")
        entity2 = TestEntity("2")
        
        entity1.do_something()
        entity2.do_something()
        entity2.do_something()
        
        uow.register_entity(entity1)
        uow.register_entity(entity2)
        
        events = uow.collect_events()
        
        assert len(events) == 3
        assert all(e.event_type == "SomethingDone" for e in events)
    
    @pytest.mark.asyncio
    async def test_commit_publishes_events(self):
        """Test that commit publishes events via event bus."""
        event_bus = EventBus()
        published_events = []
        
        async def handler(event: DomainEvent):
            published_events.append(event)
        
        event_bus.subscribe("SomethingDone", handler)
        
        uow = InMemoryUnitOfWork(event_bus)
        entity = TestEntity("123")
        entity.do_something()
        
        uow.register_entity(entity)
        
        await uow.commit()
        
        # Event should be published
        assert len(published_events) == 1
        assert published_events[0].event_type == "SomethingDone"
    
    @pytest.mark.asyncio
    async def test_commit_clears_events(self):
        """Test that commit clears events from entities."""
        uow = InMemoryUnitOfWork()
        entity = TestEntity("123")
        entity.do_something()
        
        assert len(entity.get_domain_events()) == 1
        
        uow.register_entity(entity)
        await uow.commit()
        
        # Events should be cleared
        assert len(entity.get_domain_events()) == 0
    
    @pytest.mark.asyncio
    async def test_rollback_clears_events(self):
        """Test that rollback clears events without publishing."""
        event_bus = EventBus()
        published_events = []
        
        async def handler(event: DomainEvent):
            published_events.append(event)
        
        event_bus.subscribe("SomethingDone", handler)
        
        uow = InMemoryUnitOfWork(event_bus)
        entity = TestEntity("123")
        entity.do_something()
        
        uow.register_entity(entity)
        await uow.rollback()
        
        # No events should be published
        assert len(published_events) == 0
        
        # Events should be cleared
        assert len(entity.get_domain_events()) == 0
    
    @pytest.mark.asyncio
    async def test_context_manager_auto_commit(self):
        """Test that context manager auto-commits on success."""
        event_bus = EventBus()
        published_events = []
        
        async def handler(event: DomainEvent):
            published_events.append(event)
        
        event_bus.subscribe("SomethingDone", handler)
        
        async with InMemoryUnitOfWork(event_bus) as uow:
            entity = TestEntity("123")
            entity.do_something()
            uow.register_entity(entity)
        
        # Should auto-commit and publish events
        assert len(published_events) == 1
    
    @pytest.mark.asyncio
    async def test_context_manager_auto_rollback_on_exception(self):
        """Test that context manager auto-rolls back on exception."""
        event_bus = EventBus()
        published_events = []
        
        async def handler(event: DomainEvent):
            published_events.append(event)
        
        event_bus.subscribe("SomethingDone", handler)
        
        try:
            async with InMemoryUnitOfWork(event_bus) as uow:
                entity = TestEntity("123")
                entity.do_something()
                uow.register_entity(entity)
                
                # Raise exception
                raise RuntimeError("Test error")
        except RuntimeError:
            pass
        
        # No events should be published due to rollback
        assert len(published_events) == 0
    
    @pytest.mark.asyncio
    async def test_double_commit(self):
        """Test that double commit is handled gracefully."""
        uow = InMemoryUnitOfWork()
        entity = TestEntity("123")
        entity.do_something()
        
        uow.register_entity(entity)
        
        await uow.commit()
        await uow.commit()  # Should not raise
    
    @pytest.mark.asyncio
    async def test_commit_without_event_bus(self):
        """Test commit works without event bus."""
        uow = InMemoryUnitOfWork(event_bus=None)
        entity = TestEntity("123")
        entity.do_something()
        
        uow.register_entity(entity)
        
        # Should not raise even without event bus
        await uow.commit()
        
        # Events should still be cleared
        assert len(entity.get_domain_events()) == 0
