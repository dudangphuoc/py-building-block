"""
Main Integration Example

Demonstrates how to use the Event-Driven Pub/Sub system.
Sets up connections, publishers, subscribers, and handlers.
"""

import logging
import threading
import time

from pubsub.amqp_connection import AMQPConfig, AMQPConnection
from pubsub.handler_registry import HandlerRegistry
from pubsub.publisher import EventPublisher
from pubsub.subscriber import EventSubscriber, QueueConfig
from pubsub.events import OrderCreatedEvent, OrderPaidEvent, UserRegisteredEvent
from pubsub.event_base import Event


# Define simple inline handlers
class SimpleLogHandler:
    """Simple handler that logs events."""
    async def handle(self, event: Event) -> None:
        logger.info(f"[SimpleLogHandler] Processing {event.domain}.{event.action} - ID: {event.event_id}")
        logger.info(f"[SimpleLogHandler] Event data: {event.data}")


class OrderHandler:
    """Handler specifically for order events."""
    async def handle(self, event: Event) -> None:
        logger.info(f"[OrderHandler] Processing order event: {event.action}")
        if event.action == "created":
            logger.info(f"[OrderHandler] New order: {event.data.get('order_id')}")
        elif event.action == "paid":
            logger.info(f"[OrderHandler] Order paid: {event.data.get('order_id')}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """
    Main function demonstrating the Event-Driven Pub/Sub system.
    
    Note: This example uses two separate connections - one for publishing
    and one for consuming - to avoid thread-safety issues with Pika's
    BlockingConnection.
    """
    
    # Configuration
    exchange_name = "events"
    
    # Step 1: Setup AMQP connections
    logger.info("=== Setting up AMQP connections ===")
    
    # Create configuration
    config = AMQPConfig(
        host="localhost",
        port=5672,
        username="guest",
        password="guest"
    )
    
    # Create separate connections for publisher and subscriber
    # This is necessary because Pika's BlockingConnection is not thread-safe
    publisher_connection = AMQPConnection(config)
    subscriber_connection = AMQPConnection(config)
    
    try:
        # Connect both
        publisher_connection.connect()
        subscriber_connection.connect()
        
        # Declare exchange (only need to do this once)
        publisher_connection.declare_exchange(
            exchange_name=exchange_name,
            exchange_type="topic",
            durable=True
        )
        
        # Step 2: Setup Handler Registry
        logger.info("=== Setting up Handler Registry ===")
        registry = HandlerRegistry()
        
        # Register handlers with patterns
        registry.subscribe("order.*", SimpleLogHandler())
        registry.subscribe("order.*", OrderHandler())
        registry.subscribe("user.*", SimpleLogHandler())
        
        # Step 3: Setup Publisher
        logger.info("=== Setting up Publisher ===")
        publisher = EventPublisher(
            connection=publisher_connection,
            exchange_name=exchange_name
        )
        
        # Step 4: Setup Subscriber
        logger.info("=== Setting up Subscriber ===")
        subscriber = EventSubscriber(
            connection=subscriber_connection,
            queue_name="example-service-queue",
            handler_registry=registry,
            exchange_name=exchange_name,
            queue_config=QueueConfig(
                durable=True,
                exclusive=False,
                auto_delete=False
            ),
            prefetch_count=1
        )
        
        # Setup queue with pattern to receive all events
        subscriber.setup_queue(routing_key="#")
        
        # Step 5: Start Subscriber in a separate thread
        logger.info("=== Starting Subscriber ===")
        consumer_thread = threading.Thread(
            target=subscriber.start_consuming,
            daemon=True
        )
        consumer_thread.start()
        
        # Give subscriber time to start
        time.sleep(2)
        
        # Step 6: Publish some events
        logger.info("=== Publishing Events ===")
        
        # Publish OrderCreatedEvent
        order_event = OrderCreatedEvent(
            data={
                "order_id": "ORD-12345",
                "customer_email": "customer@example.com",
                "items": [
                    {"product_id": "PROD-001", "quantity": 2},
                    {"product_id": "PROD-002", "quantity": 1}
                ],
                "total_amount": 149.99
            }
        )
        publisher.publish(order_event)
        logger.info(f"Published: {order_event.get_routing_key()}")
        
        # Wait a bit
        time.sleep(1)
        
        # Publish OrderPaidEvent
        payment_event = OrderPaidEvent(
            data={
                "order_id": "ORD-12345",
                "payment_id": "PAY-67890",
                "amount": 149.99,
                "payment_method": "credit_card"
            }
        )
        publisher.publish(payment_event)
        logger.info(f"Published: {payment_event.get_routing_key()}")
        
        # Wait a bit
        time.sleep(1)
        
        # Publish UserRegisteredEvent
        user_event = UserRegisteredEvent(
            data={
                "user_id": "USER-001",
                "username": "john_doe",
                "email": "john@example.com",
                "registration_date": "2026-01-01"
            }
        )
        publisher.publish(user_event)
        logger.info(f"Published: {user_event.get_routing_key()}")
        
        # Step 7: Wait for handlers to process events
        logger.info("=== Waiting for events to be processed ===")
        time.sleep(3)
        
        logger.info("=== Demo completed successfully ===")
        
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        raise
    finally:
        # Step 8: Cleanup
        logger.info("=== Cleaning up ===")
        publisher_connection.close()
        subscriber_connection.close()
        logger.info("Connections closed")


if __name__ == "__main__":
    main()
