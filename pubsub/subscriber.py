"""
Subscriber Module

Provides EventSubscriber for consuming events from RabbitMQ queues.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from .amqp_connection import AMQPConnection
from .event_base import EventSerializer
from .handler_registry import HandlerRegistry

logger = logging.getLogger(__name__)


@dataclass
class QueueConfig:
    """Configuration for queue declaration."""
    durable: bool = True
    exclusive: bool = False
    auto_delete: bool = False
    arguments: Optional[Dict[str, Any]] = None


class EventSubscriber:
    """
    Subscribes to events from a RabbitMQ queue and dispatches them to handlers.
    
    Note: Uses asyncio.run() to invoke async handlers. This works when running
    in a separate thread. For fully async applications, consider using aio-pika.
    """
    
    def __init__(
        self,
        connection: AMQPConnection,
        queue_name: str,
        handler_registry: HandlerRegistry,
        exchange_name: str,
        queue_config: Optional[QueueConfig] = None,
        prefetch_count: int = 1
    ):
        """
        Initialize the event subscriber.
        
        Args:
            connection: AMQP connection to use
            queue_name: Name of the queue to consume from
            handler_registry: Registry containing event handlers
            exchange_name: Name of the exchange to bind to
            queue_config: Queue configuration options
            prefetch_count: Number of unacknowledged messages per consumer
        """
        self.connection = connection
        self.queue_name = queue_name
        self.handler_registry = handler_registry
        self.exchange_name = exchange_name
        self.queue_config = queue_config or QueueConfig()
        self.prefetch_count = prefetch_count
        logger.info(f"EventSubscriber initialized for queue '{queue_name}'")
    
    def setup_queue(self, routing_key: str = "#") -> None:
        """
        Declare queue and bind it to the exchange.
        
        Args:
            routing_key: Routing key pattern for binding (default: "#" matches all)
            
        Raises:
            RuntimeError: If connection is not established
        """
        if not self.connection.is_connected():
            raise RuntimeError(
                "AMQP connection is not established. Call connect() first."
            )
        
        # Declare queue
        logger.info(f"Setting up queue '{self.queue_name}'")
        self.connection.declare_queue(
            queue_name=self.queue_name,
            durable=self.queue_config.durable,
            exclusive=self.queue_config.exclusive,
            auto_delete=self.queue_config.auto_delete,
            arguments=self.queue_config.arguments
        )
        
        # Bind queue to exchange
        self.connection.bind_queue(
            queue_name=self.queue_name,
            exchange_name=self.exchange_name,
            routing_key=routing_key
        )
        
        # Set QoS (prefetch count)
        self.connection.channel.basic_qos(prefetch_count=self.prefetch_count)
        logger.info(f"Queue '{self.queue_name}' setup complete with prefetch_count={self.prefetch_count}")
    
    def start_consuming(self) -> None:
        """
        Start consuming messages from the queue.
        
        This is a blocking call that will continue until interrupted.
        
        Raises:
            RuntimeError: If connection is not established
        """
        if not self.connection.is_connected():
            raise RuntimeError(
                "AMQP connection is not established. Call connect() first."
            )
        
        logger.info(f"Starting to consume from queue '{self.queue_name}'")
        
        # Register consumer callback
        self.connection.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=self._on_message,
            auto_ack=False  # Manual acknowledgment
        )
        
        try:
            logger.info("Consumer started. Waiting for messages...")
            self.connection.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping consumer...")
            self.connection.channel.stop_consuming()
        except Exception as e:
            logger.error(f"Error during consumption: {e}", exc_info=True)
            raise
    
    def _on_message(self, ch, method, properties, body):
        """
        Callback for processing received messages.
        
        Args:
            ch: Channel
            method: Method frame
            properties: Message properties
            body: Message body
        """
        try:
            # Decode message
            message_str = body.decode('utf-8')
            logger.info(
                f"Received message from queue '{self.queue_name}' "
                f"with routing key '{method.routing_key}'"
            )
            logger.debug(f"Message body: {message_str}")
            
            # Deserialize event
            event = EventSerializer.from_json(message_str)
            logger.info(f"Deserialized event {event.event_id} ({event.get_routing_key()})")
            
            # Invoke handlers
            # Note: asyncio.run() creates a new event loop for this invocation
            # This works in a separate thread but may not work if an event loop already exists
            result = asyncio.run(self.handler_registry.invoke_all(event))
            
            # Check results and acknowledge
            if result.failed_count == 0:
                logger.info(f"All handlers succeeded for event {event.event_id}, acknowledging message")
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                logger.warning(
                    f"{result.failed_count} handler(s) failed for event {event.event_id}, "
                    f"rejecting message (requeue=False)"
                )
                # Reject and don't requeue (could send to DLQ if configured)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                
        except Exception as e:
            logger.error(
                f"Error processing message from queue '{self.queue_name}': {e}",
                exc_info=True
            )
            # Reject message and don't requeue on error
            try:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            except Exception as nack_error:
                logger.error(f"Failed to nack message: {nack_error}")
