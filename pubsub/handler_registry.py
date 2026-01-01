"""
Handler Registry Module

Manages registration and invocation of event handlers with pattern matching support.
Supports wildcard patterns for flexible event routing.
"""

import fnmatch
import logging
from dataclasses import dataclass
from typing import List, Dict

from .event_base import Event, EventHandler

logger = logging.getLogger(__name__)


@dataclass
class HandlerInvocationResult:
    """Result of invoking handlers for an event."""
    success_count: int = 0
    failed_count: int = 0
    errors: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class HandlerRegistry:
    """
    Registry for event handlers with pattern matching support.
    
    Supports wildcard patterns using fnmatch:
    - "order.*" matches "order.created", "order.updated", etc.
    - "*.created" matches "order.created", "user.created", etc.
    - "*" matches all events
    """
    
    def __init__(self):
        """Initialize the handler registry."""
        self.handlers: Dict[str, List[EventHandler]] = {}
        logger.info("HandlerRegistry initialized")
    
    def subscribe(self, pattern: str, handler: EventHandler) -> None:
        """
        Register a handler for events matching the given pattern.
        
        Args:
            pattern: Pattern to match against routing keys (supports wildcards)
            handler: Handler to invoke for matching events
        """
        if pattern not in self.handlers:
            self.handlers[pattern] = []
        
        self.handlers[pattern].append(handler)
        logger.info(f"Registered handler {handler.__class__.__name__} for pattern '{pattern}'")
    
    def find_handlers(self, routing_key: str) -> List[EventHandler]:
        """
        Find all handlers matching the given routing key.
        
        Args:
            routing_key: Routing key to match (e.g., "order.created")
            
        Returns:
            List of matching handlers
        """
        matching_handlers = []
        
        for pattern, pattern_handlers in self.handlers.items():
            if fnmatch.fnmatch(routing_key, pattern):
                matching_handlers.extend(pattern_handlers)
                logger.debug(
                    f"Pattern '{pattern}' matches routing key '{routing_key}' "
                    f"({len(pattern_handlers)} handlers)"
                )
        
        logger.debug(
            f"Found {len(matching_handlers)} handler(s) for routing key '{routing_key}'"
        )
        return matching_handlers
    
    async def invoke_all(self, event: Event) -> HandlerInvocationResult:
        """
        Invoke all handlers matching the event's routing key.
        
        Handlers are invoked sequentially. If a handler fails, the error is caught
        and logged, but other handlers will still be invoked.
        
        Args:
            event: Event to handle
            
        Returns:
            HandlerInvocationResult with success/failure counts and error details
        """
        routing_key = event.get_routing_key()
        handlers = self.find_handlers(routing_key)
        
        result = HandlerInvocationResult()
        
        if not handlers:
            logger.warning(f"No handlers found for event {event.event_id} ({routing_key})")
            return result
        
        logger.info(
            f"Invoking {len(handlers)} handler(s) for event {event.event_id} ({routing_key})"
        )
        
        for handler in handlers:
            handler_name = handler.__class__.__name__
            try:
                logger.debug(f"Invoking handler {handler_name}")
                await handler.handle(event)
                result.success_count += 1
                logger.debug(f"Handler {handler_name} completed successfully")
            except Exception as e:
                result.failed_count += 1
                error_msg = f"Handler {handler_name} failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                result.errors.append({
                    "handler": handler_name,
                    "error": str(e)
                })
        
        logger.info(
            f"Handler invocation complete for event {event.event_id}: "
            f"{result.success_count} succeeded, {result.failed_count} failed"
        )
        
        return result
