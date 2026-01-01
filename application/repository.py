"""
Repository Base Class

Provides base repository pattern for data access with CRUD operations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar, Any, Dict

from .entity import Entity

logger = logging.getLogger(__name__)

# Type variable for entity type
T = TypeVar('T', bound=Entity)


class Repository(ABC, Generic[T]):
    """
    Base repository class for data access.
    
    Provides abstract methods for CRUD operations that must be implemented
    by concrete repositories.
    
    Usage:
        class OrderRepository(Repository[Order]):
            def __init__(self, db_session):
                self.db_session = db_session
            
            async def get_by_id(self, entity_id: str) -> Optional[Order]:
                # Implementation
                pass
            
            async def add(self, entity: Order) -> None:
                # Implementation
                pass
    """
    
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """
        Get an entity by its ID.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            Entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_all(self) -> List[T]:
        """
        Get all entities.
        
        Returns:
            List of all entities
        """
        pass
    
    @abstractmethod
    async def add(self, entity: T) -> None:
        """
        Add a new entity.
        
        Args:
            entity: Entity to add
        """
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> None:
        """
        Update an existing entity.
        
        Args:
            entity: Entity to update
        """
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> None:
        """
        Delete an entity by its ID.
        
        Args:
            entity_id: Entity identifier
        """
        pass
    
    async def find(self, **criteria: Any) -> List[T]:
        """
        Find entities matching criteria.
        
        This is a default implementation that can be overridden.
        
        Args:
            criteria: Search criteria
            
        Returns:
            List of matching entities
        """
        logger.warning(
            f"Default find() implementation called. Override this method in {self.__class__.__name__}"
        )
        return []


class InMemoryRepository(Repository[T], Generic[T]):
    """
    In-memory implementation of repository for testing and prototyping.
    
    Stores entities in a dictionary keyed by ID.
    
    Usage:
        repository = InMemoryRepository[Order]()
        order = Order(order_id="123", customer_id="456")
        await repository.add(order)
        found = await repository.get_by_id("123")
    """
    
    def __init__(self):
        """Initialize in-memory repository with empty storage."""
        self._storage: Dict[str, T] = {}
        logger.debug(f"Initialized {self.__class__.__name__}")
    
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID from in-memory storage."""
        entity = self._storage.get(entity_id)
        logger.debug(f"Get by ID {entity_id}: {'Found' if entity else 'Not found'}")
        return entity
    
    async def get_all(self) -> List[T]:
        """Get all entities from in-memory storage."""
        entities = list(self._storage.values())
        logger.debug(f"Get all: Found {len(entities)} entities")
        return entities
    
    async def add(self, entity: T) -> None:
        """Add entity to in-memory storage."""
        if not hasattr(entity, 'id'):
            raise ValueError("Entity must have an 'id' attribute")
        
        entity_id = entity.id
        if entity_id in self._storage:
            raise ValueError(f"Entity with ID {entity_id} already exists")
        
        self._storage[entity_id] = entity
        logger.debug(f"Added entity with ID {entity_id}")
    
    async def update(self, entity: T) -> None:
        """Update entity in in-memory storage."""
        if not hasattr(entity, 'id'):
            raise ValueError("Entity must have an 'id' attribute")
        
        entity_id = entity.id
        if entity_id not in self._storage:
            raise ValueError(f"Entity with ID {entity_id} not found")
        
        self._storage[entity_id] = entity
        logger.debug(f"Updated entity with ID {entity_id}")
    
    async def delete(self, entity_id: str) -> None:
        """Delete entity from in-memory storage."""
        if entity_id not in self._storage:
            raise ValueError(f"Entity with ID {entity_id} not found")
        
        del self._storage[entity_id]
        logger.debug(f"Deleted entity with ID {entity_id}")
    
    async def find(self, **criteria: Any) -> List[T]:
        """
        Find entities matching criteria.
        
        Simple implementation that matches entity attributes.
        """
        results = []
        for entity in self._storage.values():
            match = True
            for key, value in criteria.items():
                if not hasattr(entity, key) or getattr(entity, key) != value:
                    match = False
                    break
            if match:
                results.append(entity)
        
        logger.debug(f"Find with criteria {criteria}: Found {len(results)} entities")
        return results
    
    def clear(self) -> None:
        """Clear all entities from storage."""
        count = len(self._storage)
        self._storage.clear()
        logger.debug(f"Cleared {count} entities from storage")
