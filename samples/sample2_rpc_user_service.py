"""
Sample 2: User Service with RPC Communication

This sample demonstrates:
- RPC Server for handling remote procedure calls
- RPC Client for making calls to remote services
- Cross-platform communication (JSON-based)
- Integration with DDD (Entity, Repository, UnitOfWork)
- Communication between microservices

Run:
1. Start RabbitMQ: docker-compose up -d
2. Terminal 1 - Start server: python -m samples.sample2_rpc_user_service server
3. Terminal 2 - Run client: python -m samples.sample2_rpc_user_service client
"""

import asyncio
import logging
import sys
import threading
import time

from pubsub.amqp_connection import AMQPConfig, AMQPConnection
from pubsub.rpc import RPCServer, RPCClient
from application import Entity, DomainEvent, EventBus
from application.repository import InMemoryRepository
from application.unit_of_work import InMemoryUnitOfWork

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# Domain Entity
class User(Entity):
    """User entity."""
    
    def __init__(self, user_id: str, username: str, email: str):
        super().__init__()
        self.id = user_id
        self.username = username
        self.email = email
        self.active = True
        
        # Raise domain event
        self.raise_event(DomainEvent(
            aggregate_id=self.id,
            event_type="UserCreated",
            data={
                "user_id": user_id,
                "username": username,
                "email": email
            }
        ))
    
    def deactivate(self):
        """Deactivate user account."""
        self.active = False
        self.raise_event(DomainEvent(
            aggregate_id=self.id,
            event_type="UserDeactivated",
            data={"user_id": self.id}
        ))
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "active": self.active
        }
    
    def __repr__(self):
        return f"User(id={self.id}, username={self.username}, email={self.email}, active={self.active})"


# Repository
class UserRepository(InMemoryRepository[User]):
    """Repository for User entities."""
    
    async def find_by_username(self, username: str):
        """Find user by username."""
        results = await self.find(username=username)
        return results[0] if results else None
    
    async def find_by_email(self, email: str):
        """Find user by email."""
        results = await self.find(email=email)
        return results[0] if results else None


# Global repository instance for RPC handlers
user_repository = UserRepository()
event_bus = EventBus()


# RPC Method Handlers
async def create_user(user_id: str, username: str, email: str) -> dict:
    """
    RPC method to create a user.
    
    This can be called from any platform (Python, C#, Java, Go, etc.).
    """
    logger.info(f"RPC: Creating user - {username}")
    
    # Create user entity
    user = User(user_id=user_id, username=username, email=email)
    
    # Save to repository
    await user_repository.add(user)
    
    # Publish domain events
    for event in user.get_domain_events():
        await event_bus.publish(event)
    user.clear_domain_events()
    
    logger.info(f"RPC: User created successfully - {user_id}")
    return {"success": True, "user_id": user_id, "message": "User created"}


async def get_user(user_id: str) -> dict:
    """
    RPC method to get a user by ID.
    
    Returns user data as JSON-compatible dict.
    """
    logger.info(f"RPC: Getting user - {user_id}")
    
    user = await user_repository.get_by_id(user_id)
    
    if not user:
        logger.warning(f"RPC: User not found - {user_id}")
        return {"success": False, "message": "User not found"}
    
    logger.info(f"RPC: User retrieved - {user.username}")
    return {
        "success": True,
        "user": user.to_dict()
    }


async def list_users() -> dict:
    """
    RPC method to list all users.
    
    Returns list of users.
    """
    logger.info("RPC: Listing all users")
    
    users = await user_repository.get_all()
    
    return {
        "success": True,
        "count": len(users),
        "users": [user.to_dict() for user in users]
    }


async def update_user_email(user_id: str, new_email: str) -> dict:
    """
    RPC method to update user email.
    """
    logger.info(f"RPC: Updating email for user - {user_id}")
    
    user = await user_repository.get_by_id(user_id)
    
    if not user:
        return {"success": False, "message": "User not found"}
    
    user.email = new_email
    await user_repository.update(user)
    
    return {"success": True, "message": "Email updated"}


async def deactivate_user(user_id: str) -> dict:
    """
    RPC method to deactivate a user.
    """
    logger.info(f"RPC: Deactivating user - {user_id}")
    
    user = await user_repository.get_by_id(user_id)
    
    if not user:
        return {"success": False, "message": "User not found"}
    
    user.deactivate()
    await user_repository.update(user)
    
    # Publish domain events
    for event in user.get_domain_events():
        await event_bus.publish(event)
    user.clear_domain_events()
    
    return {"success": True, "message": "User deactivated"}


# Event Handlers
async def handle_user_created(event: DomainEvent):
    """Handle UserCreated event."""
    logger.info(f"📧 Event: User created - {event.data.get('username')}")


async def handle_user_deactivated(event: DomainEvent):
    """Handle UserDeactivated event."""
    logger.info(f"📧 Event: User deactivated - {event.data.get('user_id')}")


def run_server():
    """Run the RPC server."""
    logger.info("=" * 60)
    logger.info("Starting RPC Server - User Service")
    logger.info("=" * 60)
    
    # Setup event bus
    event_bus.subscribe("UserCreated", handle_user_created)
    event_bus.subscribe("UserDeactivated", handle_user_deactivated)
    
    # Setup AMQP connection
    config = AMQPConfig(
        host="localhost",
        port=5672,
        username="guest",
        password="guest"
    )
    
    connection = AMQPConnection(config)
    connection.connect()
    
    # Setup RPC server
    server = RPCServer(
        connection=connection,
        queue_name="user-service",
        exchange_name="rpc_exchange"
    )
    
    # Register RPC methods
    server.register_method("create_user", create_user)
    server.register_method("get_user", get_user)
    server.register_method("list_users", list_users)
    server.register_method("update_user_email", update_user_email)
    server.register_method("deactivate_user", deactivate_user)
    
    # Setup and start server
    server.setup()
    
    logger.info("RPC Server is ready and listening for requests...")
    logger.info("Available methods:")
    logger.info("  - create_user(user_id, username, email)")
    logger.info("  - get_user(user_id)")
    logger.info("  - list_users()")
    logger.info("  - update_user_email(user_id, new_email)")
    logger.info("  - deactivate_user(user_id)")
    logger.info("\nPress Ctrl+C to stop")
    logger.info("=" * 60)
    
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("\nStopping RPC Server...")
        server.stop()
        connection.close()
        logger.info("Server stopped")


async def run_client():
    """Run the RPC client to make sample calls."""
    logger.info("=" * 60)
    logger.info("Running RPC Client - Making Remote Calls")
    logger.info("=" * 60)
    
    # Setup AMQP connection
    config = AMQPConfig(
        host="localhost",
        port=5672,
        username="guest",
        password="guest"
    )
    
    connection = AMQPConnection(config)
    connection.connect()
    
    # Setup RPC client
    client = RPCClient(
        connection=connection,
        exchange_name="rpc_exchange"
    )
    client.setup()
    
    # Start processing responses in background
    def process_responses():
        while True:
            connection.channel.connection.process_data_events(time_limit=0.1)
            time.sleep(0.1)
    
    response_thread = threading.Thread(target=process_responses, daemon=True)
    response_thread.start()
    
    try:
        # Test 1: Create users
        logger.info("\n[1] Creating users via RPC")
        
        result = await client.call(
            method="create_user",
            params={"user_id": "USER-001", "username": "alice", "email": "alice@example.com"},
            routing_key="user-service",
            timeout=10
        )
        logger.info(f"✓ Result: {result}")
        
        await asyncio.sleep(1)
        
        result = await client.call(
            method="create_user",
            params={"user_id": "USER-002", "username": "bob", "email": "bob@example.com"},
            routing_key="user-service",
            timeout=10
        )
        logger.info(f"✓ Result: {result}")
        
        await asyncio.sleep(1)
        
        # Test 2: List users
        logger.info("\n[2] Listing all users via RPC")
        result = await client.call(
            method="list_users",
            params={},
            routing_key="user-service",
            timeout=10
        )
        logger.info(f"✓ Found {result.get('count')} users")
        for user in result.get('users', []):
            logger.info(f"  - {user}")
        
        await asyncio.sleep(1)
        
        # Test 3: Get specific user
        logger.info("\n[3] Getting specific user via RPC")
        result = await client.call(
            method="get_user",
            params={"user_id": "USER-001"},
            routing_key="user-service",
            timeout=10
        )
        logger.info(f"✓ User details: {result.get('user')}")
        
        await asyncio.sleep(1)
        
        # Test 4: Update user email
        logger.info("\n[4] Updating user email via RPC")
        result = await client.call(
            method="update_user_email",
            params={"user_id": "USER-001", "new_email": "alice.new@example.com"},
            routing_key="user-service",
            timeout=10
        )
        logger.info(f"✓ Result: {result}")
        
        await asyncio.sleep(1)
        
        # Test 5: Deactivate user
        logger.info("\n[5] Deactivating user via RPC")
        result = await client.call(
            method="deactivate_user",
            params={"user_id": "USER-002"},
            routing_key="user-service",
            timeout=10
        )
        logger.info(f"✓ Result: {result}")
        
        await asyncio.sleep(1)
        
        # Test 6: List users again
        logger.info("\n[6] Listing users after updates")
        result = await client.call(
            method="list_users",
            params={},
            routing_key="user-service",
            timeout=10
        )
        for user in result.get('users', []):
            logger.info(f"  - {user}")
        
        logger.info("\n" + "=" * 60)
        logger.info("RPC Client completed successfully!")
        logger.info("All remote calls work across platforms!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error in RPC client: {e}", exc_info=True)
    finally:
        client.close()
        connection.close()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m samples.sample2_rpc_user_service server  # Start RPC server")
        print("  python -m samples.sample2_rpc_user_service client  # Run RPC client")
        sys.exit(1)
    
    mode = sys.argv[1]
    
    if mode == "server":
        run_server()
    elif mode == "client":
        asyncio.run(run_client())
    else:
        print(f"Unknown mode: {mode}")
        print("Use 'server' or 'client'")
        sys.exit(1)


if __name__ == "__main__":
    main()
