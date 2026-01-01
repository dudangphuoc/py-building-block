"""
Unit of Work Pattern

Provides the Unit of Work pattern for managing transactions and collecting domain events.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from .entity import Entity, DomainEvent
from .event_bus import EventBus

logger = logging.getLogger(__name__)


class UnitOfWork(ABC):
    """
    Abstract base class for Unit of Work pattern.
    
    Unit of Work:
    - Maintains a list of objects affected by a business transaction
    - Coordinates the writing out of changes
    - Collects domain events from entities
    - Publishes events after successful commit
    
    Usage:
        class MyUnitOfWork(UnitOfWork):
            def __init__(self, db_session, event_bus):
                super().__init__(event_bus)
                self.db_session = db_session
                self.orders = OrderRepository(db_session)
                
            async def _commit_transaction(self) -> None:
                await self.db_session.commit()
            
            async def _rollback_transaction(self) -> None:
                await self.db_session.rollback()
        
        async with MyUnitOfWork(db_session, event_bus) as uow:
            order = Order(...)
            await uow.orders.add(order)
            await uow.commit()  # Automatically collects and publishes events
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize Unit of Work.
        
        Args:
            event_bus: Event bus for publishing domain events. If None, events won't be published.
        """
        self._event_bus = event_bus
        self._committed = False
        self._entities_with_events: List[Entity] = []
    
    def register_entity(self, entity: Entity) -> None:
        """
        Register an entity to track its domain events.
        
        Args:
            entity: Entity to track
        """
        if entity not in self._entities_with_events:
            self._entities_with_events.append(entity)
            logger.debug(f"Registered entity {entity.__class__.__name__} for event tracking")
    
    def collect_events(self) -> List[DomainEvent]:
        """
        Collect all domain events from tracked entities.
        
        Returns:
            List of domain events
        """
        events = []
        for entity in self._entities_with_events:
            entity_events = entity.get_domain_events()
            events.extend(entity_events)
            logger.debug(
                f"Collected {len(entity_events)} events from entity {entity.__class__.__name__}"
            )
        
        logger.info(f"Collected total of {len(events)} domain events")
        return events
    
    async def commit(self) -> None:
        """
        Commit the unit of work.
        
        This method:
        1. Collects domain events from all tracked entities
        2. Commits the transaction (implemented by subclass)
        3. Publishes collected events (if commit succeeds)
        4. Clears events from entities
        """
        if self._committed:
            logger.warning("Unit of Work already committed")
            return
        
        # Collect events before committing
        events = self.collect_events()
        logger.info(f"Committing Unit of Work with {len(events)} domain events")
        
        try:
            # Commit the transaction (implemented by subclass)
            await self._commit_transaction()
            self._committed = True
            logger.info("Transaction committed successfully")
            
            # Publish events after successful commit
            if self._event_bus and events:
                logger.info(f"Publishing {len(events)} domain events")
                await self._event_bus.publish_all(events)
            
            # Clear events from entities
            for entity in self._entities_with_events:
                entity.clear_domain_events()
            
        except Exception as e:
            logger.error(f"Error committing Unit of Work: {e}", exc_info=True)
            await self.rollback()
            raise
    
    async def rollback(self) -> None:
        """
        Rollback the unit of work.
        
        This method:
        1. Rolls back the transaction (implemented by subclass)
        2. Clears collected events
        """
        logger.info("Rolling back Unit of Work")
        
        try:
            await self._rollback_transaction()
            
            # Clear events without publishing them
            for entity in self._entities_with_events:
                entity.clear_domain_events()
            
            logger.info("Transaction rolled back successfully")
        except Exception as e:
            logger.error(f"Error rolling back Unit of Work: {e}", exc_info=True)
            raise
    
    @abstractmethod
    async def _commit_transaction(self) -> None:
        """
        Commit the underlying transaction.
        
        Must be implemented by concrete Unit of Work classes.
        """
        pass
    
    @abstractmethod
    async def _rollback_transaction(self) -> None:
        """
        Rollback the underlying transaction.
        
        Must be implemented by concrete Unit of Work classes.
        """
        pass
    
    async def __aenter__(self):
        """Support async context manager."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Handle async context manager exit."""
        if exc_type is not None:
            # Exception occurred, rollback
            await self.rollback()
        elif not self._committed:
            # No exception but not committed, auto-commit
            await self.commit()


class InMemoryUnitOfWork(UnitOfWork):
    """
    In-memory implementation of Unit of Work for testing.
    
    This implementation simulates transaction behavior without
    requiring a real database.
    
    Usage:
        event_bus = EventBus()
        async with InMemoryUnitOfWork(event_bus) as uow:
            order = Order(...)
            uow.register_entity(order)
            # ... do work ...
            # Events automatically collected and published on exit
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        """Initialize in-memory unit of work."""
        super().__init__(event_bus)
        self._transaction_active = False
    
    async def _commit_transaction(self) -> None:
        """Simulate committing a transaction."""
        logger.debug("InMemoryUnitOfWork: Committing transaction")
        self._transaction_active = False
    
    async def _rollback_transaction(self) -> None:
        """Simulate rolling back a transaction."""
        logger.debug("InMemoryUnitOfWork: Rolling back transaction")
        self._transaction_active = False
