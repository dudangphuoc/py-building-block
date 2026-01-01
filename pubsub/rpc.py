"""
RPC (Remote Procedure Call) Support

Provides RPC functionality for calling remote procedures across services
and platforms (Python, C#, Java, Go, etc.).

Uses JSON-based message format for cross-platform compatibility.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
import asyncio

from .amqp_connection import AMQPConnection
from .event_base import Event

logger = logging.getLogger(__name__)


@dataclass
class RPCRequest:
    """
    RPC request message.
    
    Attributes:
        method: Name of the method to call
        params: Parameters for the method
        request_id: Unique identifier for this request
        timestamp: When the request was created
        timeout: Timeout in seconds (default: 30)
    """
    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    timeout: int = 30
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(asdict(self), ensure_ascii=False)
    
    @staticmethod
    def from_json(json_str: str) -> 'RPCRequest':
        """Deserialize from JSON."""
        data = json.loads(json_str)
        return RPCRequest(
            method=data['method'],
            params=data.get('params', {}),
            request_id=data.get('request_id', str(uuid.uuid4())),
            timestamp=data.get('timestamp', datetime.now(timezone.utc).isoformat()),
            timeout=data.get('timeout', 30)
        )


@dataclass
class RPCResponse:
    """
    RPC response message.
    
    Attributes:
        request_id: ID of the request this responds to
        success: Whether the call succeeded
        result: Result data if successful
        error: Error message if failed
        timestamp: When the response was created
    """
    request_id: str
    success: bool = True
    result: Any = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(asdict(self), ensure_ascii=False)
    
    @staticmethod
    def from_json(json_str: str) -> 'RPCResponse':
        """Deserialize from JSON."""
        data = json.loads(json_str)
        return RPCResponse(
            request_id=data['request_id'],
            success=data.get('success', True),
            result=data.get('result'),
            error=data.get('error'),
            timestamp=data.get('timestamp', datetime.now(timezone.utc).isoformat())
        )


class RPCServer:
    """
    RPC Server for handling remote procedure calls.
    
    Listens for RPC requests on a queue and executes registered methods.
    
    Usage:
        server = RPCServer(connection, "my-rpc-server")
        
        async def add_numbers(a: int, b: int) -> int:
            return a + b
        
        server.register_method("add", add_numbers)
        server.start()
    """
    
    def __init__(
        self,
        connection: AMQPConnection,
        queue_name: str,
        exchange_name: str = "rpc_exchange"
    ):
        """
        Initialize RPC server.
        
        Args:
            connection: AMQP connection
            queue_name: Queue name for receiving RPC requests
            exchange_name: Exchange name for RPC
        """
        self.connection = connection
        self.queue_name = queue_name
        self.exchange_name = exchange_name
        self._methods: Dict[str, Callable] = {}
        self._running = False
    
    def register_method(self, name: str, handler: Callable) -> None:
        """
        Register a method that can be called via RPC.
        
        Args:
            name: Method name
            handler: Async function to handle the call
        """
        self._methods[name] = handler
        logger.info(f"Registered RPC method: {name}")
    
    def setup(self) -> None:
        """Setup exchange and queue for RPC."""
        # Declare exchange
        self.connection.declare_exchange(
            exchange_name=self.exchange_name,
            exchange_type="direct",
            durable=True
        )
        
        # Declare queue
        self.connection.channel.queue_declare(
            queue=self.queue_name,
            durable=True
        )
        
        # Bind queue to exchange
        self.connection.channel.queue_bind(
            exchange=self.exchange_name,
            queue=self.queue_name,
            routing_key=self.queue_name
        )
        
        logger.info(f"RPC Server setup complete: queue={self.queue_name}")
    
    def start(self) -> None:
        """Start listening for RPC requests."""
        if not self.connection.channel:
            raise RuntimeError("Connection not established")
        
        self._running = True
        logger.info(f"RPC Server starting on queue: {self.queue_name}")
        
        # Setup consumer
        self.connection.channel.basic_qos(prefetch_count=1)
        self.connection.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=self._handle_request
        )
        
        try:
            self.connection.channel.start_consuming()
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self) -> None:
        """Stop the RPC server."""
        self._running = False
        if self.connection.channel:
            self.connection.channel.stop_consuming()
        logger.info("RPC Server stopped")
    
    def _handle_request(self, ch, method_frame, properties, body):
        """Handle incoming RPC request."""
        try:
            # Parse request
            request = RPCRequest.from_json(body.decode('utf-8'))
            logger.info(f"Received RPC request: {request.method} (ID: {request.request_id})")
            
            # Execute method
            response = asyncio.run(self._execute_method(request))
            
            # Send response
            if properties.reply_to:
                ch.basic_publish(
                    exchange='',
                    routing_key=properties.reply_to,
                    properties=properties,
                    body=response.to_json().encode('utf-8')
                )
                logger.info(f"Sent RPC response for request {request.request_id}")
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method_frame.delivery_tag)
            
        except Exception as e:
            logger.error(f"Error handling RPC request: {e}", exc_info=True)
            # Reject message
            ch.basic_nack(delivery_tag=method_frame.delivery_tag, requeue=False)
    
    async def _execute_method(self, request: RPCRequest) -> RPCResponse:
        """Execute the requested method."""
        try:
            # Check if method exists
            if request.method not in self._methods:
                return RPCResponse(
                    request_id=request.request_id,
                    success=False,
                    error=f"Method '{request.method}' not found"
                )
            
            # Get method handler
            handler = self._methods[request.method]
            
            # Execute handler
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**request.params)
            else:
                result = handler(**request.params)
            
            # Return success response
            return RPCResponse(
                request_id=request.request_id,
                success=True,
                result=result
            )
            
        except Exception as e:
            logger.error(f"Error executing method {request.method}: {e}", exc_info=True)
            return RPCResponse(
                request_id=request.request_id,
                success=False,
                error=str(e)
            )


class RPCClient:
    """
    RPC Client for making remote procedure calls.
    
    Sends RPC requests and waits for responses.
    
    Usage:
        client = RPCClient(connection)
        client.setup()
        
        result = await client.call("add", {"a": 5, "b": 3}, routing_key="math-service")
        print(result)  # 8
    """
    
    def __init__(
        self,
        connection: AMQPConnection,
        exchange_name: str = "rpc_exchange"
    ):
        """
        Initialize RPC client.
        
        Args:
            connection: AMQP connection
            exchange_name: Exchange name for RPC
        """
        self.connection = connection
        self.exchange_name = exchange_name
        self._response_queue = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._consumer_tag = None
    
    def setup(self) -> None:
        """Setup exchange and response queue for RPC."""
        # Declare exchange
        self.connection.declare_exchange(
            exchange_name=self.exchange_name,
            exchange_type="direct",
            durable=True
        )
        
        # Declare exclusive response queue
        result = self.connection.channel.queue_declare(
            queue='',
            exclusive=True
        )
        self._response_queue = result.method.queue
        
        # Start consuming responses
        self._consumer_tag = self.connection.channel.basic_consume(
            queue=self._response_queue,
            on_message_callback=self._handle_response,
            auto_ack=True
        )
        
        logger.info(f"RPC Client setup complete: response_queue={self._response_queue}")
    
    async def call(
        self,
        method: str,
        params: Dict[str, Any],
        routing_key: str,
        timeout: int = 30
    ) -> Any:
        """
        Make an RPC call.
        
        Args:
            method: Method name to call
            params: Method parameters
            routing_key: Routing key (target service queue)
            timeout: Timeout in seconds
            
        Returns:
            Result from the remote method
            
        Raises:
            TimeoutError: If request times out
            RuntimeError: If RPC call fails
        """
        # Create request
        request = RPCRequest(
            method=method,
            params=params,
            timeout=timeout
        )
        
        logger.info(f"Making RPC call: {method} (ID: {request.request_id})")
        
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request.request_id] = future
        
        # Send request
        import pika
        self.connection.channel.basic_publish(
            exchange=self.exchange_name,
            routing_key=routing_key,
            properties=pika.BasicProperties(
                reply_to=self._response_queue,
                correlation_id=request.request_id,
                content_type='application/json'
            ),
            body=request.to_json().encode('utf-8')
        )
        
        # Wait for response with timeout
        try:
            # Process events synchronously to handle responses
            # Note: In production, consider using aio-pika for fully async RabbitMQ
            start_time = asyncio.get_event_loop().time()
            while not future.done():
                self.connection.channel.connection.process_data_events(time_limit=0.1)
                await asyncio.sleep(0.01)
                
                # Check timeout
                if asyncio.get_event_loop().time() - start_time > timeout:
                    raise asyncio.TimeoutError()
            
            response = future.result()
            
            if response.success:
                logger.info(f"RPC call succeeded: {method} (ID: {request.request_id})")
                return response.result
            else:
                logger.error(f"RPC call failed: {method} - {response.error}")
                raise RuntimeError(f"RPC call failed: {response.error}")
                
        except asyncio.TimeoutError:
            logger.error(f"RPC call timed out: {method} (ID: {request.request_id})")
            self._pending_requests.pop(request.request_id, None)
            raise TimeoutError(f"RPC call timed out after {timeout} seconds")
    
    def _handle_response(self, ch, method_frame, properties, body):
        """Handle incoming RPC response."""
        try:
            # Parse response
            response = RPCResponse.from_json(body.decode('utf-8'))
            
            # Find pending request
            correlation_id = properties.correlation_id or response.request_id
            future = self._pending_requests.pop(correlation_id, None)
            
            if future and not future.done():
                future.set_result(response)
                logger.debug(f"Received RPC response for request {correlation_id}")
            
        except Exception as e:
            logger.error(f"Error handling RPC response: {e}", exc_info=True)
    
    def close(self) -> None:
        """Close the RPC client."""
        if self._consumer_tag and self.connection.channel:
            self.connection.channel.basic_cancel(self._consumer_tag)
        logger.info("RPC Client closed")
