# Event-Driven Pub/Sub System with Python & RabbitMQ

A modular, reusable Event-Driven Pub/Sub system built with Python and RabbitMQ, following Building-Block architecture principles.

## Features

- **Modular Architecture**: Each component (connection, events, handlers, publisher, subscriber) is independent and reusable
- **Pattern Matching**: Flexible wildcard-based routing with fnmatch support
- **Thread-Safe Design**: Separate connections for publisher and consumer to avoid Pika thread-safety issues
- **Error Handling**: Comprehensive error handling with handler isolation and Dead Letter Queue support
- **Async Support**: Async handler invocation with proper exception handling
- **Type Safety**: Full type hints and protocols for better code quality
- **Extensible**: Easy to add new event types and handlers

## Architecture

The system follows a Building-Block architecture with these independent modules:

1. **AMQP Connection** (`amqp_connection.py`): Manages RabbitMQ connections, channels, and basic AMQP operations
2. **Event Base** (`event_base.py`): Defines Event class, EventHandler protocol, and EventSerializer
3. **Handler Registry** (`handler_registry.py`): Manages handler registration and invocation with pattern matching
4. **Publisher** (`publisher.py`): Publishes events to RabbitMQ exchange
5. **Subscriber** (`subscriber.py`): Consumes events from queues and dispatches to handlers
6. **Handlers** (`handlers.py`): Example business logic handlers
7. **Events** (`events.py`): Predefined event types for different domains

## Installation

### Prerequisites

- Python 3.8+
- Docker and Docker Compose (for RabbitMQ)

### Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start RabbitMQ:
```bash
docker-compose up -d
```

3. Verify RabbitMQ is running:
- AMQP: `localhost:5672`
- Management UI: `http://localhost:15672` (guest/guest)

## Usage

### Quick Start

Run the example:
```bash
python main.py
```

This will:
1. Connect to RabbitMQ
2. Setup handlers for order and user events
3. Publish example events
4. Process them through registered handlers
5. Log all activities

### Creating Custom Events

```python
from pubsub.event_base import Event
from pubsub.events import OrderCreatedEvent

# Using predefined event
event = OrderCreatedEvent(
    data={
        "order_id": "ORD-123",
        "customer_email": "customer@example.com",
        "items": [{"product_id": "PROD-001", "quantity": 2}],
        "total_amount": 99.99
    }
)

# Or create custom event
event = Event(
    domain="payment",
    action="processed",
    data={"payment_id": "PAY-456", "amount": 99.99}
)
```

### Creating Custom Handlers

```python
from pubsub.event_base import Event

class CustomHandler:
    async def handle(self, event: Event) -> None:
        # Your business logic here
        print(f"Processing: {event.domain}.{event.action}")
        # Do something with event.data
```

### Registering Handlers

```python
from pubsub.handler_registry import HandlerRegistry

registry = HandlerRegistry()

# Exact match
registry.subscribe("order.created", OrderHandler())

# Wildcard patterns
registry.subscribe("order.*", AllOrdersHandler())      # All order events
registry.subscribe("*.created", AllCreatedHandler())   # All created events
registry.subscribe("*", LoggingHandler())              # All events
```

### Publishing Events

```python
from pubsub.amqp_connection import AMQPConfig, AMQPConnection
from pubsub.publisher import EventPublisher

# Setup connection
config = AMQPConfig(host="localhost", port=5672)
connection = AMQPConnection(config)
connection.connect()

# Declare exchange
connection.declare_exchange("events", exchange_type="topic", durable=True)

# Create publisher
publisher = EventPublisher(connection, "events")

# Publish event
publisher.publish(event)
```

### Subscribing to Events

```python
from pubsub.subscriber import EventSubscriber, QueueConfig

# Create subscriber
subscriber = EventSubscriber(
    connection=connection,
    queue_name="my-service-queue",
    handler_registry=registry,
    exchange_name="events",
    queue_config=QueueConfig(durable=True),
    prefetch_count=1
)

# Setup queue with routing pattern
subscriber.setup_queue(routing_key="#")  # Receive all events

# Start consuming (blocking call)
subscriber.start_consuming()
```

## Testing

Run tests:
```bash
pytest tests/
```

Run tests with coverage:
```bash
pytest tests/ --cov=pubsub --cov-report=html
```

Run tests with verbose output:
```bash
pytest tests/ -v
```

## Configuration

### AMQP Configuration

```python
from pubsub.amqp_connection import AMQPConfig

config = AMQPConfig(
    host="localhost",           # RabbitMQ host
    port=5672,                  # AMQP port
    username="guest",           # Username
    password="guest",           # Password
    virtual_host="/",           # Virtual host
    connection_attempts=3,      # Retry attempts
    retry_delay=5,              # Delay between retries (seconds)
    heartbeat=600,              # Heartbeat interval (seconds)
    blocked_connection_timeout=300  # Timeout for blocked connections
)
```

### Queue Configuration

```python
from pubsub.subscriber import QueueConfig

queue_config = QueueConfig(
    durable=True,        # Queue survives broker restart
    exclusive=False,     # Queue can be used by multiple connections
    auto_delete=False,   # Queue is not deleted when unused
    arguments=None       # Optional queue arguments (e.g., for DLQ)
)
```

## Important Notes

### Thread Safety

Pika's `BlockingConnection` is **NOT thread-safe** except for `add_callback_threadsafe()`. 

**Solution**: Use separate connections for publisher and consumer threads:

```python
# Create two connections
publisher_connection = AMQPConnection(config)
subscriber_connection = AMQPConnection(config)

publisher_connection.connect()
subscriber_connection.connect()
```

For fully async applications, consider using [aio-pika](https://github.com/mosquito/aio-pika).

### Message Acknowledgment

The subscriber automatically handles message acknowledgment:
- **All handlers succeed**: Message is acknowledged (`basic_ack`)
- **Any handler fails**: Message is rejected without requeue (`basic_nack` with `requeue=False`)

For retry logic, configure a Dead Letter Queue (DLQ) in RabbitMQ.

### Queue Naming

Each service should use a **unique queue name** to avoid sharing queues unintentionally. Use service-specific prefixes:

```python
subscriber = EventSubscriber(
    queue_name="order-service-queue",  # Unique per service
    # ...
)
```

### Serialization

All data in `Event.data` must be **JSON-serializable**:
- ✅ Strings, numbers, lists, dicts, booleans, None
- ❌ datetime objects, custom classes, functions

Convert non-serializable objects before creating events:

```python
from datetime import datetime

# ❌ This will fail
event = Event(domain="test", action="test", data={"time": datetime.now()})

# ✅ This works
event = Event(domain="test", action="test", data={"time": datetime.now().isoformat()})
```

## Examples

### E-commerce Order Flow

```python
# 1. Order Created
order_event = OrderCreatedEvent(data={
    "order_id": "ORD-123",
    "customer_email": "customer@example.com",
    "items": [{"product_id": "PROD-001", "quantity": 2}]
})
publisher.publish(order_event)

# Handlers triggered:
# - SendEmailHandler: Send order confirmation email
# - UpdateInventoryHandler: Reduce stock
# - LogAnalyticsHandler: Track order metrics

# 2. Payment Processed
payment_event = OrderPaidEvent(data={
    "order_id": "ORD-123",
    "payment_id": "PAY-456",
    "amount": 99.99
})
publisher.publish(payment_event)

# Handlers triggered:
# - SendEmailHandler: Send payment confirmation
# - LogAnalyticsHandler: Track payment metrics
```

## Best Practices

1. **One Connection Per Thread**: Always use separate connections for different threads
2. **Error Handling**: Implement proper error handling in handlers to prevent cascading failures
3. **Dead Letter Queues**: Configure DLQs for failed messages to prevent loss
4. **Monitoring**: Use RabbitMQ Management UI to monitor queues and exchanges
5. **Logging**: Enable appropriate logging levels to track event flow
6. **Prefetch Count**: Set appropriate `prefetch_count` to control consumer load
7. **Queue Durability**: Use durable queues and persistent messages for reliability
8. **Version Events**: Use the `version` field for schema evolution

## Troubleshooting

### Connection Issues

```bash
# Check if RabbitMQ is running
docker ps | grep rabbitmq

# Check RabbitMQ logs
docker logs rabbitmq

# Restart RabbitMQ
docker-compose restart
```

### Thread Safety Issues

If you see errors like "connection closed" or "channel closed unexpectedly":
- Ensure you're using separate connections for publisher and consumer
- Don't share connections across threads

### Messages Not Being Consumed

- Verify queue is properly bound to exchange
- Check routing keys match patterns
- Ensure subscriber is running
- Check RabbitMQ Management UI for queue status

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
