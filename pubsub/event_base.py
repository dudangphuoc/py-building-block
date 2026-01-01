"""
Event Base Module

Defines the base Event class, EventHandler protocol, and EventSerializer.
Provides the foundation for creating and handling domain events.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Protocol
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """
    Base class for all events in the system.
    
    Attributes:
        domain: The domain this event belongs to (e.g., "order", "user")
        action: The action that occurred (e.g., "created", "updated")
        data: Event payload data (must be JSON-serializable)
        event_id: Unique identifier for this event (auto-generated)
        timestamp: When the event occurred (auto-generated)
        version: Event schema version for compatibility
    """
    domain: str
    action: str
    data: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "1.0"
    
    def __post_init__(self):
        """Initialize event_id and timestamp if not provided."""
        if not self.event_id:
            self.event_id = str(uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def get_routing_key(self) -> str:
        """
        Generate routing key for this event.
        
        Returns:
            Routing key in format "domain.action"
        """
        return f"{self.domain}.{self.action}"


class EventHandler(Protocol):
    """
    Protocol for event handlers.
    
    All event handlers must implement the async handle method.
    """
    
    async def handle(self, event: Event) -> None:
        """
        Handle an event.
        
        Args:
            event: The event to handle
            
        Raises:
            Exception: If handling fails
        """
        ...


class EventSerializer:
    """
    Serializer for converting Events to/from JSON.
    
    Handles JSON serialization with proper handling of datetime fields.
    """
    
    @staticmethod
    def to_json(event: Event) -> str:
        """
        Serialize an event to JSON string.
        
        Args:
            event: Event to serialize
            
        Returns:
            JSON string representation of the event
            
        Raises:
            TypeError: If event data contains non-JSON-serializable objects
        """
        try:
            event_dict = asdict(event)
            json_str = json.dumps(event_dict, ensure_ascii=False)
            logger.debug(f"Serialized event {event.event_id}: {json_str}")
            return json_str
        except TypeError as e:
            logger.error(f"Failed to serialize event {event.event_id}: {e}")
            raise TypeError(
                f"Event data must be JSON-serializable. "
                f"Ensure all values in 'data' are JSON-compatible types. Error: {e}"
            )
    
    @staticmethod
    def from_json(json_str: str) -> Event:
        """
        Deserialize an event from JSON string.
        
        Args:
            json_str: JSON string to deserialize
            
        Returns:
            Event object
            
        Raises:
            ValueError: If JSON is invalid or missing required fields
        """
        try:
            event_dict = json.loads(json_str)
            
            # Validate required fields
            required_fields = {"domain", "action", "data"}
            missing_fields = required_fields - set(event_dict.keys())
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            # Create Event object
            event = Event(
                domain=event_dict["domain"],
                action=event_dict["action"],
                data=event_dict["data"],
                event_id=event_dict.get("event_id", str(uuid4())),
                timestamp=event_dict.get("timestamp", datetime.now(timezone.utc).isoformat()),
                version=event_dict.get("version", "1.0")
            )
            
            logger.debug(f"Deserialized event {event.event_id}")
            return event
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {e}")
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            logger.error(f"Failed to deserialize event: {e}")
            raise
