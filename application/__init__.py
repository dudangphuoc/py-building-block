"""
Application Layer - DDD Building Blocks

This module provides Domain-Driven Design (DDD) building blocks:
- Entity: Base class for domain entities with event support
- Repository: Base class for data access patterns
- UnitOfWork: Pattern for managing transactions and events
- EventBus: For publishing domain events
- DI Container: For automatic dependency injection
"""

from .entity import Entity, DomainEvent
from .repository import Repository
from .unit_of_work import UnitOfWork
from .event_bus import EventBus
from .di_container import DIContainer

__all__ = [
    "Entity",
    "DomainEvent",
    "Repository",
    "UnitOfWork",
    "EventBus",
    "DIContainer",
]
