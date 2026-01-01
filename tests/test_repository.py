"""
Tests for Repository
"""

import pytest

from application.entity import Entity, DomainEvent
from application.repository import InMemoryRepository


class TestEntity(Entity):
    """Test entity for repository tests."""
    
    def __init__(self, entity_id: str, name: str):
        super().__init__()
        self.id = entity_id
        self.name = name
        self.value = 0


class TestInMemoryRepository:
    """Tests for InMemoryRepository."""
    
    @pytest.mark.asyncio
    async def test_add_and_get_by_id(self):
        """Test adding and retrieving entity."""
        repo = InMemoryRepository[TestEntity]()
        
        entity = TestEntity("123", "test")
        await repo.add(entity)
        
        retrieved = await repo.get_by_id("123")
        
        assert retrieved is not None
        assert retrieved.id == "123"
        assert retrieved.name == "test"
    
    @pytest.mark.asyncio
    async def test_add_duplicate_fails(self):
        """Test that adding duplicate ID fails."""
        repo = InMemoryRepository[TestEntity]()
        
        entity1 = TestEntity("123", "test1")
        await repo.add(entity1)
        
        entity2 = TestEntity("123", "test2")
        
        with pytest.raises(ValueError, match="already exists"):
            await repo.add(entity2)
    
    @pytest.mark.asyncio
    async def test_get_all(self):
        """Test getting all entities."""
        repo = InMemoryRepository[TestEntity]()
        
        await repo.add(TestEntity("1", "first"))
        await repo.add(TestEntity("2", "second"))
        await repo.add(TestEntity("3", "third"))
        
        all_entities = await repo.get_all()
        
        assert len(all_entities) == 3
    
    @pytest.mark.asyncio
    async def test_update(self):
        """Test updating entity."""
        repo = InMemoryRepository[TestEntity]()
        
        entity = TestEntity("123", "original")
        await repo.add(entity)
        
        # Update entity
        entity.name = "updated"
        await repo.update(entity)
        
        # Retrieve and verify
        retrieved = await repo.get_by_id("123")
        assert retrieved.name == "updated"
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_fails(self):
        """Test that updating non-existent entity fails."""
        repo = InMemoryRepository[TestEntity]()
        
        entity = TestEntity("123", "test")
        
        with pytest.raises(ValueError, match="not found"):
            await repo.update(entity)
    
    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting entity."""
        repo = InMemoryRepository[TestEntity]()
        
        entity = TestEntity("123", "test")
        await repo.add(entity)
        
        # Delete
        await repo.delete("123")
        
        # Should not be found
        retrieved = await repo.get_by_id("123")
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_fails(self):
        """Test that deleting non-existent entity fails."""
        repo = InMemoryRepository[TestEntity]()
        
        with pytest.raises(ValueError, match="not found"):
            await repo.delete("123")
    
    @pytest.mark.asyncio
    async def test_find(self):
        """Test finding entities by criteria."""
        repo = InMemoryRepository[TestEntity]()
        
        await repo.add(TestEntity("1", "alice"))
        await repo.add(TestEntity("2", "bob"))
        await repo.add(TestEntity("3", "alice"))
        
        # Find by name
        results = await repo.find(name="alice")
        
        assert len(results) == 2
        assert all(e.name == "alice" for e in results)
    
    @pytest.mark.asyncio
    async def test_find_no_match(self):
        """Test finding with no matches."""
        repo = InMemoryRepository[TestEntity]()
        
        await repo.add(TestEntity("1", "alice"))
        
        results = await repo.find(name="bob")
        
        assert len(results) == 0
    
    def test_clear(self):
        """Test clearing repository."""
        repo = InMemoryRepository[TestEntity]()
        
        # Use asyncio.run for async operations in sync test
        import asyncio
        asyncio.run(repo.add(TestEntity("1", "test")))
        asyncio.run(repo.add(TestEntity("2", "test")))
        
        repo.clear()
        
        all_entities = asyncio.run(repo.get_all())
        assert len(all_entities) == 0
    
    @pytest.mark.asyncio
    async def test_add_requires_id(self):
        """Test that add requires entity to have id."""
        repo = InMemoryRepository[TestEntity]()
        
        class EntityWithoutId(Entity):
            def __init__(self):
                super().__init__()
        
        entity = EntityWithoutId()
        
        with pytest.raises(ValueError, match="must have an 'id' attribute"):
            await repo.add(entity)
