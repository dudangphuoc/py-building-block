"""
Entity Base with Domain Events

Provides base classes for domain entities that can raise and track domain events.
"""

import logging
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class DomainEvent:
    """
    Base class for domain events.
    
    Domain events represent something that happened in the domain that
    domain experts care about.
    
    Attributes:
        event_id: Unique identifier for this event
        occurred_at: When the event occurred
        aggregate_id: ID of the aggregate that raised the event
        event_type: Type of the event (e.g., "OrderCreated")
        data: Event payload data
    """
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    aggregate_id: str = ""
    event_type: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate required fields after initialization."""
        if not self.event_type:
            raise ValueError("event_type is required")


class Entity(ABC):
    """
    Base class for domain entities.
    
    An entity has:
    - A unique identity that persists across its lifecycle
    - The ability to raise domain events
    - Mutable state
    
    Usage:
        class Order(Entity):
            def __init__(self, order_id: str, customer_id: str):
                super().__init__()
                self.id = order_id
                self.customer_id = customer_id
                self.items = []
                
            def add_item(self, item):
                self.items.append(item)
                self.raise_event(DomainEvent(
                    aggregate_id=self.id,
                    event_type="OrderItemAdded",
                    data={"item": item}
                ))
    """
    
    def __init__(self):
        """Initialize entity with empty domain events list."""
        self._domain_events: List[DomainEvent] = []
    
    def raise_event(self, event: DomainEvent) -> None:
        """
        Raise a domain event.
        
        Args:
            event: Domain event to raise
        """
        logger.debug(f"Entity raised event: {event.event_type} (ID: {event.event_id})")
        self._domain_events.append(event)
    
    def get_domain_events(self) -> List[DomainEvent]:
        """
        Get all domain events raised by this entity.
        
        Returns:
            List of domain events
        """
        return self._domain_events.copy()
    
    def clear_domain_events(self) -> None:
        """Clear all domain events."""
        logger.debug(f"Clearing {len(self._domain_events)} domain events")
        self._domain_events.clear()
    
    def __eq__(self, other: object) -> bool:
        """
        Compare entities by identity.
        
        Two entities are equal if they have the same type and ID.
        """
        if not isinstance(other, Entity):
            return False
        return type(self) == type(other) and hasattr(self, 'id') and hasattr(other, 'id') and self.id == other.id
    
    def __hash__(self) -> int:
        """
        Hash entity by type and ID.
        
        Required for using entities in sets and as dict keys.
        """
        if hasattr(self, 'id'):
            return hash((type(self), self.id))
        return hash(type(self))
