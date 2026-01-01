"""
Publisher Module

Provides EventPublisher for publishing events to RabbitMQ exchange.
"""

import logging
from typing import Optional, Callable

import pika

from .amqp_connection import AMQPConnection
from .event_base import Event, EventSerializer

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Publishes events to a RabbitMQ exchange.
    
    Handles serialization, routing, and error handling for event publishing.
    """
    
    def __init__(
        self,
        connection: AMQPConnection,
        exchange_name: str,
        routing_key_formatter: Optional[Callable[[Event], str]] = None
    ):
        """
        Initialize the event publisher.
        
        Args:
            connection: AMQP connection to use
            exchange_name: Name of the exchange to publish to
            routing_key_formatter: Optional custom function to generate routing keys
        """
        self.connection = connection
        self.exchange_name = exchange_name
        self.routing_key_formatter = routing_key_formatter or (lambda e: e.get_routing_key())
        logger.info(f"EventPublisher initialized for exchange '{exchange_name}'")
    
    def publish(self, event: Event) -> None:
        """
        Publish an event to the exchange.
        
        Args:
            event: Event to publish
            
        Raises:
            RuntimeError: If connection is not established
            Exception: If publishing fails
        """
        if not self.connection.is_connected():
            raise RuntimeError(
                "AMQP connection is not established. Call connect() first."
            )
        
        try:
            # Serialize event to JSON
            message_body = EventSerializer.to_json(event)
            
            # Generate routing key
            routing_key = self.routing_key_formatter(event)
            
            # Create message properties (persistent delivery)
            properties = pika.BasicProperties(
                delivery_mode=2,  # Persistent
                content_type="application/json",
                content_encoding="utf-8"
            )
            
            # Publish message
            logger.info(
                f"Publishing event {event.event_id} to exchange '{self.exchange_name}' "
                f"with routing key '{routing_key}'"
            )
            
            self.connection.channel.basic_publish(
                exchange=self.exchange_name,
                routing_key=routing_key,
                body=message_body.encode('utf-8'),
                properties=properties
            )
            
            logger.info(f"Event {event.event_id} published successfully")
            
        except Exception as e:
            error_msg = (
                f"Failed to publish event {event.event_id} to exchange "
                f"'{self.exchange_name}': {str(e)}"
            )
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg) from e
