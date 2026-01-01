"""
Sample 1: Order Management System with DDD

This sample demonstrates:
- Domain-Driven Design with Entity, Repository, and Unit of Work
- Domain events and Event Bus
- Automatic dependency injection
- CRUD operations on Order entities

Run: python -m samples.sample1_order_management
"""

import asyncio
import logging

from application import Entity, DomainEvent, Repository, UnitOfWork, EventBus, DIContainer
from application.repository import InMemoryRepository
from application.unit_of_work import InMemoryUnitOfWork

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# Domain Entities
class Order(Entity):
    """Order entity with domain events."""
    
    def __init__(self, order_id: str, customer_id: str, total_amount: float):
        super().__init__()
        self.id = order_id
        self.customer_id = customer_id
        self.total_amount = total_amount
        self.status = "pending"
        self.items = []
        
        # Raise domain event
        self.raise_event(DomainEvent(
            aggregate_id=self.id,
            event_type="OrderCreated",
            data={
                "order_id": order_id,
                "customer_id": customer_id,
                "total_amount": total_amount
            }
        ))
    
    def add_item(self, product_id: str, quantity: int, price: float):
        """Add item to order."""
        item = {
            "product_id": product_id,
            "quantity": quantity,
            "price": price
        }
        self.items.append(item)
        self.total_amount += price * quantity
        
        # Raise domain event
        self.raise_event(DomainEvent(
            aggregate_id=self.id,
            event_type="OrderItemAdded",
            data={
                "order_id": self.id,
                "product_id": product_id,
                "quantity": quantity,
                "price": price
            }
        ))
    
    def confirm(self):
        """Confirm the order."""
        if self.status != "pending":
            raise ValueError(f"Cannot confirm order in status: {self.status}")
        
        self.status = "confirmed"
        
        # Raise domain event
        self.raise_event(DomainEvent(
            aggregate_id=self.id,
            event_type="OrderConfirmed",
            data={
                "order_id": self.id,
                "total_amount": self.total_amount
            }
        ))
    
    def complete(self):
        """Complete the order."""
        if self.status != "confirmed":
            raise ValueError(f"Cannot complete order in status: {self.status}")
        
        self.status = "completed"
        
        # Raise domain event
        self.raise_event(DomainEvent(
            aggregate_id=self.id,
            event_type="OrderCompleted",
            data={
                "order_id": self.id
            }
        ))
    
    def __repr__(self):
        return f"Order(id={self.id}, customer={self.customer_id}, total={self.total_amount}, status={self.status})"


# Repository
class OrderRepository(InMemoryRepository[Order]):
    """Repository for Order entities."""
    
    async def find_by_customer(self, customer_id: str):
        """Find orders by customer ID."""
        return await self.find(customer_id=customer_id)
    
    async def find_by_status(self, status: str):
        """Find orders by status."""
        return await self.find(status=status)


# Unit of Work
class OrderUnitOfWork(InMemoryUnitOfWork):
    """Unit of Work for order operations."""
    
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self.orders = OrderRepository()


# Event Handlers
async def handle_order_created(event: DomainEvent):
    """Handle OrderCreated event."""
    logger.info(f"✓ Event Handler: Order created - {event.data.get('order_id')}")
    logger.info(f"  Customer: {event.data.get('customer_id')}")
    logger.info(f"  Total: ${event.data.get('total_amount')}")


async def handle_order_item_added(event: DomainEvent):
    """Handle OrderItemAdded event."""
    logger.info(f"✓ Event Handler: Item added to order - {event.data.get('order_id')}")
    logger.info(f"  Product: {event.data.get('product_id')}")
    logger.info(f"  Quantity: {event.data.get('quantity')}")


async def handle_order_confirmed(event: DomainEvent):
    """Handle OrderConfirmed event."""
    logger.info(f"✓ Event Handler: Order confirmed - {event.data.get('order_id')}")
    logger.info(f"  Final total: ${event.data.get('total_amount')}")


async def handle_order_completed(event: DomainEvent):
    """Handle OrderCompleted event."""
    logger.info(f"✓ Event Handler: Order completed - {event.data.get('order_id')}")


async def main():
    """Main demonstration function."""
    logger.info("=" * 60)
    logger.info("Sample 1: Order Management System with DDD")
    logger.info("=" * 60)
    
    # Setup Event Bus
    logger.info("\n[1] Setting up Event Bus")
    event_bus = EventBus()
    event_bus.subscribe("OrderCreated", handle_order_created)
    event_bus.subscribe("OrderItemAdded", handle_order_item_added)
    event_bus.subscribe("OrderConfirmed", handle_order_confirmed)
    event_bus.subscribe("OrderCompleted", handle_order_completed)
    
    # Setup DI Container
    logger.info("\n[2] Setting up Dependency Injection")
    container = DIContainer()
    container.register_instance(EventBus, event_bus)
    container.register(OrderRepository, OrderRepository(), lifetime='singleton')
    container.register(OrderUnitOfWork, OrderUnitOfWork)
    
    # Create Order using Unit of Work
    logger.info("\n[3] Creating new order with Unit of Work")
    async with OrderUnitOfWork(event_bus) as uow:
        # Create order
        order = Order(
            order_id="ORD-001",
            customer_id="CUST-123",
            total_amount=0.0
        )
        
        # Register entity with UoW to track events
        uow.register_entity(order)
        
        # Add items
        order.add_item("PROD-001", 2, 29.99)
        order.add_item("PROD-002", 1, 49.99)
        
        # Confirm order
        order.confirm()
        
        # Save to repository
        await uow.orders.add(order)
        
        # Commit will automatically collect and publish events
        logger.info("\n[4] Committing Unit of Work (events will be published)")
    
    # Query orders
    logger.info("\n[5] Querying orders from repository")
    orders_repo = OrderRepository()
    await orders_repo.add(order)  # Add to standalone repo for querying
    
    all_orders = await orders_repo.get_all()
    logger.info(f"Total orders: {len(all_orders)}")
    
    for ord in all_orders:
        logger.info(f"  - {ord}")
    
    # Find by customer
    customer_orders = await orders_repo.find_by_customer("CUST-123")
    logger.info(f"\nOrders for customer CUST-123: {len(customer_orders)}")
    
    # Update order and publish more events
    logger.info("\n[6] Updating order and completing it")
    async with OrderUnitOfWork(event_bus) as uow:
        # Get order and register it
        retrieved_order = await orders_repo.get_by_id("ORD-001")
        if retrieved_order:
            uow.register_entity(retrieved_order)
            retrieved_order.complete()
            await orders_repo.update(retrieved_order)
    
    # Final state
    logger.info("\n[7] Final order state")
    final_order = await orders_repo.get_by_id("ORD-001")
    logger.info(f"Order status: {final_order.status}")
    logger.info(f"Order items: {len(final_order.items)}")
    logger.info(f"Total amount: ${final_order.total_amount}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Sample 1 completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
