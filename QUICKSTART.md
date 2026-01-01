# Quick Start Guide

## Installation & Setup

```bash
# 1. Clone the repository
git clone https://github.com/dudangphuoc/py-building-block.git
cd py-building-block

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start RabbitMQ (for RPC and Pub/Sub examples)
docker-compose up -d

# 4. Verify RabbitMQ is running
# Management UI: http://localhost:15672 (guest/guest)
```

## Run Examples

### Example 1: DDD Order Management (No RabbitMQ required)

```bash
python -m samples.sample1_order_management
```

**What it demonstrates:**
- Creating entities with domain events
- Using Repository pattern for data access
- Unit of Work coordinating transactions
- Event Bus publishing domain events
- Full DDD workflow

**Expected output:**
```
✓ Event Handler: Order created - ORD-001
  Customer: CUST-123
  Total: $0.0
✓ Event Handler: Item added to order - ORD-001
  Product: PROD-001
  Quantity: 2
...
```

### Example 2: RPC User Service (Requires RabbitMQ)

**Terminal 1 - Start RPC Server:**
```bash
python -m samples.sample2_rpc_user_service server
```

**Terminal 2 - Run RPC Client:**
```bash
python -m samples.sample2_rpc_user_service client
```

**What it demonstrates:**
- RPC Server handling remote calls
- RPC Client making requests
- JSON-based cross-platform protocol
- Integration with DDD patterns

## Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/test_entity.py -v

# Run with coverage
pytest tests/ --cov=application --cov=pubsub --cov-report=html
```

**Expected result:** 62 tests pass

## Basic Usage Examples

### 1. Create an Entity with Domain Events

```python
from application import Entity, DomainEvent

class Order(Entity):
    def __init__(self, order_id: str, customer_id: str):
        super().__init__()
        self.id = order_id
        self.customer_id = customer_id
        
        # Raise domain event
        self.raise_event(DomainEvent(
            aggregate_id=self.id,
            event_type="OrderCreated",
            data={"order_id": order_id, "customer_id": customer_id}
        ))
    
    def add_item(self, product_id: str, quantity: int):
        self.items.append({"product_id": product_id, "quantity": quantity})
        
        self.raise_event(DomainEvent(
            aggregate_id=self.id,
            event_type="OrderItemAdded",
            data={"product_id": product_id, "quantity": quantity}
        ))

# Create order
order = Order("ORD-001", "CUST-123")

# Domain events are automatically tracked
events = order.get_domain_events()
print(f"Events raised: {len(events)}")  # 1 event
```

### 2. Use Repository

```python
from application.repository import InMemoryRepository

# Create repository
class OrderRepository(InMemoryRepository[Order]):
    async def find_by_customer(self, customer_id: str):
        return await self.find(customer_id=customer_id)

# Use repository
repo = OrderRepository()
await repo.add(order)

# Query
order = await repo.get_by_id("ORD-001")
customer_orders = await repo.find_by_customer("CUST-123")
all_orders = await repo.get_all()
```

### 3. Use Unit of Work with Event Bus

```python
from application import EventBus
from application.unit_of_work import InMemoryUnitOfWork

# Setup event bus
event_bus = EventBus()

async def handle_order_created(event: DomainEvent):
    print(f"Order created: {event.data}")

event_bus.subscribe("OrderCreated", handle_order_created)

# Use Unit of Work
async with InMemoryUnitOfWork(event_bus) as uow:
    order = Order("ORD-001", "CUST-123")
    uow.register_entity(order)
    
    # Do more work...
    
    # Commit automatically publishes events
    await uow.commit()
```

### 4. Use Dependency Injection

```python
from application import DIContainer, EventBus

container = DIContainer()

# Register singleton
event_bus = EventBus()
container.register_instance(EventBus, event_bus)

# Register transient
container.register(OrderRepository, OrderRepository)

# Automatic registration from module
import my_repositories
container.register_from_module(
    my_repositories,
    base_class=Repository,
    lifetime='transient'
)

# Resolve
repo = container.resolve(OrderRepository)
```

### 5. Create RPC Server

```python
from pubsub.amqp_connection import AMQPConnection, AMQPConfig
from pubsub.rpc import RPCServer

# Setup connection
config = AMQPConfig(host="localhost", port=5672)
connection = AMQPConnection(config)
connection.connect()

# Create server
server = RPCServer(connection, "my-service")

# Register methods
async def add_numbers(a: int, b: int) -> int:
    return a + b

server.register_method("add", add_numbers)

# Start server
server.setup()
server.start()  # Blocking call
```

### 6. Make RPC Calls

```python
from pubsub.rpc import RPCClient

# Setup client
client = RPCClient(connection)
client.setup()

# Make call
result = await client.call(
    method="add",
    params={"a": 5, "b": 3},
    routing_key="my-service",
    timeout=10
)

print(result)  # 8
```

## Common Patterns

### Pattern 1: Create Entity + Save with Events

```python
async with OrderUnitOfWork(event_bus) as uow:
    # Create entity (raises events)
    order = Order("ORD-001", "CUST-123")
    
    # Register for event tracking
    uow.register_entity(order)
    
    # Save to repository
    await uow.orders.add(order)
    
    # Commit automatically publishes events
```

### Pattern 2: Update Entity + Publish Events

```python
async with OrderUnitOfWork(event_bus) as uow:
    # Get entity
    order = await uow.orders.get_by_id("ORD-001")
    
    # Register it
    uow.register_entity(order)
    
    # Make changes (raises events)
    order.add_item("PROD-001", 2)
    
    # Update
    await uow.orders.update(order)
    
    # Commit publishes events
```

### Pattern 3: Cross-Service Communication via RPC

**Service A (Client):**
```python
result = await rpc_client.call(
    method="create_user",
    params={"user_id": "001", "username": "alice"},
    routing_key="user-service"
)
```

**Service B (Server):**
```python
async def create_user(user_id: str, username: str) -> dict:
    user = User(user_id, username)
    await user_repository.add(user)
    return {"success": True, "user_id": user_id}

rpc_server.register_method("create_user", create_user)
```

## Troubleshooting

### RabbitMQ Connection Issues

```bash
# Check if RabbitMQ is running
docker ps | grep rabbitmq

# Restart RabbitMQ
docker-compose restart

# Check logs
docker logs rabbitmq
```

### Test Failures

```bash
# Run tests with verbose output
pytest tests/ -v -s

# Run single test
pytest tests/test_entity.py::TestEntity::test_entity_raise_event -v
```

### Module Import Issues

```bash
# Make sure you're in the project root
cd /path/to/py-building-block

# Run as module
python -m samples.sample1_order_management

# NOT: python samples/sample1_order_management.py
```

## Next Steps

1. **Study the samples**: Read through `samples/sample1_order_management.py` and `samples/sample2_rpc_user_service.py`
2. **Read the tests**: Tests in `tests/` folder show all usage patterns
3. **Read the README**: Full documentation in `README.md`
4. **Build your own**: Start with a simple entity and repository

## Resources

- **README.md**: Complete documentation
- **IMPLEMENTATION_SUMMARY.md**: Technical implementation details
- **samples/**: Working example applications
- **tests/**: Unit tests showing usage patterns

## Support

For issues or questions:
1. Check existing GitHub issues
2. Read the documentation
3. Create a new issue with details

Happy coding! 🚀
