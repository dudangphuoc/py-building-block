## Project: Python Event-Driven Pub/Sub (RabbitMQ, MediatR-like)

### 🎯 Architecture Goals
- Build Event-Driven Pub/Sub system with **Python + RabbitMQ**
- **Building Blocks** architecture: domain-agnostic, testable, reusable components
- Behavior similar to **MediatR (.NET)** - in-process messaging with async handlers

### 🧱 Module Structure (Actual)
```
pubsub/                    # Core building blocks (infrastructure)
  ├── amqp_connection.py   # Pika wrapper, connection/channel management
  ├── event_base.py        # Event, EventHandler protocol, EventSerializer
  ├── handler_registry.py  # Pattern matching & handler invocation
  ├── publisher.py         # EventPublisher - sends events to exchange
  ├── subscriber.py        # EventSubscriber - consumes from queue
  ├── events.py            # Concrete event types (OrderCreated, UserRegistered)
  └── handlers.py          # Example handlers (SendEmail, UpdateInventory)

main.py                    # Integration example
tests/                     # Unit tests (no RabbitMQ required)
docker-compose.yml         # RabbitMQ 3.12 with management UI
```

### 🚫 Critical Rules
- **DO NOT** mix infrastructure (`pubsub/amqp_*`, `publisher`, `subscriber`) with business logic
- **DO NOT** hardcode domain-specific logic in building blocks (`amqp_connection`, `event_base`, `handler_registry`, `publisher`, `subscriber`)
- **DO NOT** use `asyncio.run()` inside an async context - only use when no event loop exists
- **DO NOT** share `pika.BlockingConnection` between publisher/consumer or threads
- **DO NOT** modify event structure - it MUST have: `domain`, `action`, `data`, `event_id`, `timestamp`, `version`

### 📐 Component Design Patterns

#### Event (`event_base.Event`)
```python
@dataclass
class Event:
    domain: str          # "order", "user", etc.
    action: str          # "created", "paid", etc.
    data: Dict[str, Any] # MUST be JSON-serializable
    event_id: str        # auto-generated UUID
    timestamp: str       # auto-generated ISO8601
    version: str = "1.0"
    
    def get_routing_key(self) -> str:
        return f"{self.domain}.{self.action}"  # e.g., "order.created"
```
**Example**: See [pubsub/events.py](pubsub/events.py) for `OrderCreatedEvent`, `UserRegisteredEvent`

#### Handler (`event_base.EventHandler` protocol)
```python
class EventHandler(Protocol):
    async def handle(self, event: Event) -> None: ...
```
- **Single Responsibility**: Each handler does ONE thing (e.g., SendEmail, UpdateInventory)
- **Domain-agnostic**: Handlers don't know about AMQP/RabbitMQ
- **Async required**: All handlers MUST be `async def handle(event)`
- **Example**: See [pubsub/handlers.py](pubsub/handlers.py#L17-L83) - `SendEmailHandler`, `UpdateInventoryHandler`

#### Handler Registry (`handler_registry.HandlerRegistry`)
- **Wildcard patterns** using `fnmatch`:
  - `"order.*"` → matches `order.created`, `order.paid`, etc.
  - `"*.created"` → matches `order.created`, `user.created`, etc.
  - `"#"` or `"*"` → matches all events
- **Registry behavior**:
  - `subscribe(pattern, handler)` - register handler for pattern
  - `find_handlers(routing_key)` - get all matching handlers
  - `invoke_all(event)` - execute all handlers, isolated error handling
- **Error isolation**: If one handler fails, others still execute
- **Example**: [main.py](main.py#L68-L74) shows registration

#### AMQP Connection (`amqp_connection.AMQPConnection`)
**Critical threading constraint**: `pika.BlockingConnection` is **NOT thread-safe**
- **MUST** create separate connections for publisher and subscriber ([main.py](main.py#L49-L50))
- **MUST** call `declare_exchange()` before publishing ([main.py](main.py#L55-L59))
- **MUST** call `setup_queue()` before consuming ([main.py](main.py#L95))
- **MUST** `ack` or `nack` every message ([pubsub/subscriber.py](pubsub/subscriber.py#L117-L145))

#### Publisher (`publisher.EventPublisher`)
```python
publisher = EventPublisher(
    connection=publisher_connection,  # Dedicated connection
    exchange_name="events"
)
publisher.publish(order_event)  # Auto-serializes, routes by event.get_routing_key()
```

#### Subscriber (`subscriber.EventSubscriber`)
```python
subscriber = EventSubscriber(
    connection=subscriber_connection,  # Separate from publisher!
    queue_name="my-service-queue",
    handler_registry=registry,
    exchange_name="events",
    queue_config=QueueConfig(durable=True, exclusive=False),
    prefetch_count=1
)
subscriber.setup_queue(routing_key="#")  # Bind with pattern
subscriber.start_consuming()  # Blocking call - run in thread
```
**Threading pattern**: Run subscriber in daemon thread ([main.py](main.py#L98-L101))

### 🔧 Development Workflows

#### Run Demo
```bash
docker-compose up -d          # Start RabbitMQ
python main.py                # Run integration example
```
**What it does**: Publishes 3 events (OrderCreated, OrderPaid, UserRegistered), processes via handlers, logs everything

#### Run Tests (No RabbitMQ required)
```bash
pytest tests/                 # All tests
pytest tests/test_handler_registry.py  # Registry tests only
```
**Test philosophy**: Unit tests mock handlers, test pattern matching, invocation logic. No actual AMQP connections.

#### RabbitMQ Management UI
- URL: `http://localhost:15672`
- Credentials: `guest` / `guest`
- **Use for**: Verify exchanges, queues, bindings, message rates

### 🐛 Common Bugs & Debugging

#### Problem: "Connection is not established"
**Cause**: Forgot to call `connection.connect()`  
**Fix**: Always call `connect()` before `declare_exchange()` or `setup_queue()`

#### Problem: Messages not consumed
**Checklist**:
1. Exchange declared? `declare_exchange(exchange_name, "topic", durable=True)`
2. Queue declared & bound? `setup_queue(routing_key="#")`
3. Routing key matches pattern? Check RabbitMQ UI → Queues → Bindings
4. Consumer started? `start_consuming()` must be called

#### Problem: Infinite requeue loop
**Cause**: Message `nack`'d with `requeue=True` but handler always fails  
**Fix**: 
- Implement Dead Letter Queue (DLQ) in `queue_config.arguments`
- OR: `nack(requeue=False)` after N retries

#### Problem: "asyncio.run() cannot be called from a running event loop"
**Cause**: Calling `asyncio.run()` inside async function  
**Fix**: In [pubsub/subscriber.py](pubsub/subscriber.py#L117-L130), we use `asyncio.run()` because subscriber runs in a separate thread (no existing loop). DO NOT change this pattern.

#### Problem: "Event data is not JSON-serializable"
**Cause**: `event.data` contains objects like `datetime`, `Decimal`, or custom classes  
**Fix**: Convert to JSON-safe types (str, int, float, list, dict) before creating Event

### 🧪 Testing Patterns

#### Mock Handlers ([tests/test_handler_registry.py](tests/test_handler_registry.py#L9-L33))
```python
class MockSuccessHandler:
    async def handle(self, event: Event) -> None:
        pass  # Test success path

class MockFailureHandler:
    async def handle(self, event: Event) -> None:
        raise Exception("Intentional failure")  # Test error handling
```

#### Test Pattern Matching
```python
registry.subscribe("order.*", handler)
handlers = registry.find_handlers("order.created")  # Should match
handlers = registry.find_handlers("user.created")   # Should NOT match
```

#### Test Invocation (see [tests/test_handler_registry.py](tests/test_handler_registry.py))
- Test `invoke_all()` with success/failure handlers
- Verify `HandlerInvocationResult` counts
- Ensure one handler's failure doesn't block others

### 📚 Key Files to Read
- [pubsub/event_base.py](pubsub/event_base.py) - Core abstractions (Event, EventHandler, EventSerializer)
- [pubsub/handler_registry.py](pubsub/handler_registry.py) - Pattern matching logic
- [main.py](main.py) - Complete integration example showing proper connection management
- [tests/test_handler_registry.py](tests/test_handler_registry.py) - Testing patterns

---