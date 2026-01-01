# Building Blocks for Event-Driven DDD Architecture

A comprehensive Python framework for building event-driven, Domain-Driven Design (DDD) applications with:
- **Event-Driven Pub/Sub** (RabbitMQ)
- **Remote Procedure Call (RPC)** for cross-platform communication
- **DDD Building Blocks** (Entity, Repository, Unit of Work, Event Bus)
- **Dependency Injection** with auto-registration

## 🎯 Features

### 1. Event-Driven Pub/Sub System
- Modular, reusable components for RabbitMQ integration
- Pattern matching with wildcard support
- Thread-safe design
- Async handler execution

### 2. RPC Support (Cross-Platform)
- JSON-based RPC protocol
- Works with any platform (Python, C#, Java, Go, etc.)
- Request/Response pattern
- Timeout handling

### 3. DDD Building Blocks
- **Entity**: Base class with domain event support
- **Repository**: Abstract CRUD operations with in-memory implementation
- **Unit of Work**: Transaction and event coordination
- **Event Bus**: Domain event publishing
- **DI Container**: Automatic dependency injection with assembly scanning

## 📦 Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Start RabbitMQ
docker-compose up -d
```

## 🚀 Quick Start

### Example 1: Order Management with DDD

```python
from application import Entity, DomainEvent, UnitOfWork, EventBus

# Define entity
class Order(Entity):
    def __init__(self, order_id: str, customer_id: str):
        super().__init__()
        self.id = order_id
        self.customer_id = customer_id
        
        # Raise domain event
        self.raise_event(DomainEvent(
            aggregate_id=self.id,
            event_type="OrderCreated",
            data={"order_id": order_id}
        ))

# Use Unit of Work
event_bus = EventBus()

async with MyUnitOfWork(event_bus) as uow:
    order = Order("ORD-001", "CUST-123")
    uow.register_entity(order)
    await uow.orders.add(order)
    # Commit automatically collects and publishes events
```

Run full example:
```bash
python -m samples.sample1_order_management
```

### Example 2: RPC Communication

**Server:**
```python
from pubsub.rpc import RPCServer
from pubsub.amqp_connection import AMQPConnection, AMQPConfig

# Define RPC method
async def create_user(user_id: str, username: str, email: str) -> dict:
    user = User(user_id, username, email)
    await user_repository.add(user)
    return {"success": True, "user_id": user_id}

# Start server
connection = AMQPConnection(AMQPConfig(host="localhost"))
connection.connect()

server = RPCServer(connection, "user-service")
server.register_method("create_user", create_user)
server.setup()
server.start()
```

**Client:**
```python
from pubsub.rpc import RPCClient

client = RPCClient(connection)
client.setup()

# Call remote method
result = await client.call(
    method="create_user",
    params={"user_id": "001", "username": "alice", "email": "alice@example.com"},
    routing_key="user-service"
)
print(result)  # {"success": True, "user_id": "001"}
```

Run full example:
```bash
# Terminal 1 - Start server
python -m samples.sample2_rpc_user_service server

# Terminal 2 - Run client
python -m samples.sample2_rpc_user_service client
```

## 📚 Architecture

### Module Structure

```
py-building-block/
├── pubsub/                    # Event-Driven Pub/Sub
│   ├── amqp_connection.py    # RabbitMQ connection management
│   ├── event_base.py         # Event and EventHandler protocol
│   ├── handler_registry.py   # Pattern matching & handler invocation
│   ├── publisher.py          # Event publisher
│   ├── subscriber.py         # Event subscriber
│   ├── rpc.py               # RPC Server & Client
│   └── events.py            # Example event types
│
├── application/              # DDD Building Blocks
│   ├── entity.py            # Entity base with domain events
│   ├── repository.py        # Repository pattern (abstract + in-memory)
│   ├── unit_of_work.py     # Unit of Work pattern
│   ├── event_bus.py        # Event Bus for domain events
│   └── di_container.py     # Dependency Injection container
│
├── samples/                 # Sample applications
│   ├── sample1_order_management.py
│   └── sample2_rpc_user_service.py
│
├── tests/                   # Unit tests (62 tests)
└── main.py                 # Integration example
```

## 🧱 DDD Building Blocks

### Entity

Base class for domain entities with event support:

```python
from application import Entity, DomainEvent

class Order(Entity):
    def __init__(self, order_id: str):
        super().__init__()
        self.id = order_id
        self.items = []
    
    def add_item(self, item):
        self.items.append(item)
        self.raise_event(DomainEvent(
            aggregate_id=self.id,
            event_type="OrderItemAdded",
            data={"item": item}
        ))
```

### Repository

Abstract repository with CRUD operations:

```python
from application import Repository
from application.repository import InMemoryRepository

class OrderRepository(InMemoryRepository[Order]):
    async def find_by_customer(self, customer_id: str):
        return await self.find(customer_id=customer_id)
```

### Unit of Work

Manages transactions and domain events:

```python
from application import UnitOfWork, EventBus

class OrderUnitOfWork(UnitOfWork):
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self.orders = OrderRepository()
    
    async def _commit_transaction(self):
        # Commit to database
        pass
    
    async def _rollback_transaction(self):
        # Rollback database
        pass
```

### Event Bus

Publishes domain events to handlers:

```python
from application import EventBus, DomainEvent

event_bus = EventBus()

async def handle_order_created(event: DomainEvent):
    print(f"Order created: {event.data}")

event_bus.subscribe("OrderCreated", handle_order_created)
await event_bus.publish(DomainEvent(event_type="OrderCreated", data={...}))
```

### Dependency Injection

Automatic registration and resolution:

```python
from application import DIContainer

container = DIContainer()

# Manual registration
container.register(EventBus, EventBus(), lifetime='singleton')
container.register(OrderRepository, OrderRepository)

# Automatic registration from module
import my_repositories
container.register_from_module(my_repositories, base_class=Repository)

# Resolve
repo = container.resolve(OrderRepository)
```

## 🔌 RPC (Remote Procedure Call)

### Cross-Platform Communication

RPC uses JSON for message format, enabling communication between:
- Python ↔ C#
- Python ↔ Java
- Python ↔ Go
- Any platform with RabbitMQ support

### Protocol

**Request:**
```json
{
  "method": "create_user",
  "params": {
    "user_id": "001",
    "username": "alice",
    "email": "alice@example.com"
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-01-01T12:00:00Z",
  "timeout": 30
}
```

**Response:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "success": true,
  "result": {
    "user_id": "001",
    "message": "User created"
  },
  "error": null,
  "timestamp": "2026-01-01T12:00:01Z"
}
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=application --cov=pubsub --cov-report=html

# Test results: 62 tests passed
```

## 📖 Samples

### Sample 1: Order Management System

Demonstrates:
- Entity with domain events
- Repository pattern
- Unit of Work
- Event Bus
- Automatic event publishing on commit

```bash
python -m samples.sample1_order_management
```

### Sample 2: User Service with RPC

Demonstrates:
- RPC Server exposing methods
- RPC Client making remote calls
- Cross-platform JSON communication
- Integration with DDD patterns

```bash
# Start server
python -m samples.sample2_rpc_user_service server

# Run client (in another terminal)
python -m samples.sample2_rpc_user_service client
```

## 🎓 Key Concepts

### Domain Events vs Integration Events

**Domain Events** (application layer):
- Internal to the bounded context
- Published via Event Bus
- Handled synchronously during transaction

**Integration Events** (pubsub layer):
- Cross-bounded context communication
- Published to RabbitMQ
- Handled asynchronously

### Unit of Work Pattern

The Unit of Work:
1. Tracks entities during a transaction
2. Collects domain events from entities
3. Commits the transaction
4. Publishes events only if commit succeeds
5. Clears events from entities

```python
async with OrderUnitOfWork(event_bus) as uow:
    order = Order("ORD-001", "CUST-123")
    uow.register_entity(order)  # Track entity
    await uow.orders.add(order)
    # Auto-commits and publishes events on exit
```

### Dependency Injection

Automatic registration similar to C# Assembly scanning:

```python
# C# equivalent:
# Assembly[] assemblies = AppDomain.CurrentDomain.GetAssemblies();
# services.RegisterAssemblyTypes(assemblies);

# Python:
import my_repositories
container.register_from_module(my_repositories, base_class=Repository)
```

## 🔧 Configuration

### RabbitMQ Configuration

```python
from pubsub.amqp_connection import AMQPConfig

config = AMQPConfig(
    host="localhost",
    port=5672,
    username="guest",
    password="guest",
    virtual_host="/",
    connection_attempts=3,
    retry_delay=5
)
```

### RPC Configuration

```python
# Server
server = RPCServer(
    connection=connection,
    queue_name="my-service",     # Unique per service
    exchange_name="rpc_exchange"
)

# Client
client = RPCClient(
    connection=connection,
    exchange_name="rpc_exchange"
)
```

## 🚨 Best Practices

1. **Use separate connections** for publisher and consumer (thread safety)
2. **Register entities with UoW** to track domain events
3. **Always use async/await** for handlers and repository methods
4. **Use DI container** for managing dependencies
5. **Keep domain events internal**, use integration events for external communication
6. **Make RPC methods idempotent** for reliability
7. **Use JSON-serializable types** for cross-platform compatibility

## 📝 License

MIT License

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📧 Support

For questions or issues, please open a GitHub issue.
