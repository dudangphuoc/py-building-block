"""
Event Bus for Publishing Domain Events

Provides an event bus for publishing domain events to handlers.
"""

import logging
from typing import Any, Callable, Dict, List
import asyncio

from .entity import DomainEvent

logger = logging.getLogger(__name__)


class EventBus:
    """
    Event bus for publishing domain events.
    
    The event bus maintains handlers for different event types and
    dispatches events to appropriate handlers.
    
    Usage:
        bus = EventBus()
        
        async def handle_order_created(event: DomainEvent):
            print(f"Order created: {event.data}")
        
        bus.subscribe("OrderCreated", handle_order_created)
        await bus.publish(DomainEvent(event_type="OrderCreated", data={...}))
    """
    
    def __init__(self):
        """Initialize event bus with empty handlers."""
        self._handlers: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_type: str, handler: Callable[[DomainEvent], Any]) -> None:
        """
        Subscribe a handler to an event type.
        
        Args:
            event_type: Type of event to handle
            handler: Async function that handles the event
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed handler {handler.__name__} to event type {event_type}")
    
    def unsubscribe(self, event_type: str, handler: Callable[[DomainEvent], Any]) -> None:
        """
        Unsubscribe a handler from an event type.
        
        Args:
            event_type: Type of event
            handler: Handler to remove
        """
        if event_type in self._handlers:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
                logger.debug(f"Unsubscribed handler {handler.__name__} from event type {event_type}")
    
    async def publish(self, event: DomainEvent) -> None:
        """
        Publish a domain event to all subscribed handlers.
        
        Args:
            event: Domain event to publish
        """
        handlers = self._handlers.get(event.event_type, [])
        
        if not handlers:
            logger.debug(f"No handlers for event type: {event.event_type}")
            return
        
        logger.info(f"Publishing event {event.event_type} (ID: {event.event_id}) to {len(handlers)} handlers")
        
        # Execute all handlers
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
                logger.debug(f"Handler {handler.__name__} processed event {event.event_id}")
            except Exception as e:
                logger.error(
                    f"Error in handler {handler.__name__} for event {event.event_type}: {e}",
                    exc_info=True
                )
    
    async def publish_all(self, events: List[DomainEvent]) -> None:
        """
        Publish multiple domain events.
        
        Args:
            events: List of domain events to publish
        """
        for event in events:
            await self.publish(event)
    
    def get_handler_count(self, event_type: str) -> int:
        """
        Get the number of handlers for an event type.
        
        Args:
            event_type: Type of event
            
        Returns:
            Number of handlers
        """
        return len(self._handlers.get(event_type, []))
    
    def clear_handlers(self, event_type: str = None) -> None:
        """
        Clear handlers for a specific event type or all event types.
        
        Args:
            event_type: Event type to clear handlers for, or None to clear all
        """
        if event_type:
            if event_type in self._handlers:
                del self._handlers[event_type]
                logger.debug(f"Cleared handlers for event type {event_type}")
        else:
            self._handlers.clear()
            logger.debug("Cleared all event handlers")
