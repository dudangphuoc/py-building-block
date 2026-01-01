"""
AMQP Connection Module

This module provides a wrapper around Pika for managing RabbitMQ connections.
Handles connection setup, channel creation, and basic AMQP operations.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

import pika
from pika.adapters.blocking_connection import BlockingChannel

logger = logging.getLogger(__name__)


@dataclass
class AMQPConfig:
    """Configuration for AMQP connection."""
    host: str = "localhost"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    virtual_host: str = "/"
    connection_attempts: int = 3
    retry_delay: int = 5
    heartbeat: int = 600
    blocked_connection_timeout: int = 300


class AMQPConnection:
    """
    Manages AMQP connection and provides methods for basic AMQP operations.
    
    Note: Pika's BlockingConnection is NOT thread-safe except for add_callback_threadsafe().
    If you need multi-threading, create separate connections for each thread,
    or consider using aio-pika for async operations.
    """
    
    def __init__(self, config: AMQPConfig):
        """
        Initialize AMQP connection manager.
        
        Args:
            config: AMQP connection configuration
        """
        self.config = config
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[BlockingChannel] = None
        
    def connect(self) -> None:
        """
        Establish connection to RabbitMQ with retry logic.
        
        Raises:
            Exception: If connection fails after all retry attempts
        """
        credentials = pika.PlainCredentials(
            self.config.username,
            self.config.password
        )
        
        parameters = pika.ConnectionParameters(
            host=self.config.host,
            port=self.config.port,
            virtual_host=self.config.virtual_host,
            credentials=credentials,
            heartbeat=self.config.heartbeat,
            blocked_connection_timeout=self.config.blocked_connection_timeout
        )
        
        for attempt in range(self.config.connection_attempts):
            try:
                logger.info(
                    f"Attempting to connect to RabbitMQ at {self.config.host}:{self.config.port} "
                    f"(attempt {attempt + 1}/{self.config.connection_attempts})"
                )
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                logger.info("Successfully connected to RabbitMQ")
                return
            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.config.connection_attempts - 1:
                    logger.info(f"Retrying in {self.config.retry_delay} seconds...")
                    time.sleep(self.config.retry_delay)
                else:
                    logger.error("All connection attempts failed")
                    raise
    
    def declare_exchange(
        self,
        exchange_name: str,
        exchange_type: str = "topic",
        durable: bool = True,
        auto_delete: bool = False,
        internal: bool = False,
        arguments: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Declare an exchange.
        
        Args:
            exchange_name: Name of the exchange
            exchange_type: Type of exchange (direct, topic, fanout, headers)
            durable: Whether the exchange survives broker restart
            auto_delete: Whether the exchange is deleted when no longer used
            internal: Whether the exchange is used for internal routing
            arguments: Optional arguments for exchange declaration
        """
        if not self.channel:
            raise RuntimeError("Channel not initialized. Call connect() first.")
        
        logger.info(f"Declaring exchange '{exchange_name}' (type: {exchange_type})")
        self.channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=exchange_type,
            durable=durable,
            auto_delete=auto_delete,
            internal=internal,
            arguments=arguments or {}
        )
        logger.info(f"Exchange '{exchange_name}' declared successfully")
    
    def declare_queue(
        self,
        queue_name: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False,
        arguments: Optional[Dict[str, Any]] = None
    ) -> pika.frame.Method:
        """
        Declare a queue.
        
        Args:
            queue_name: Name of the queue
            durable: Whether the queue survives broker restart
            exclusive: Whether the queue is used by only one connection
            auto_delete: Whether the queue is deleted when no longer used
            arguments: Optional arguments for queue declaration
            
        Returns:
            Method frame from queue declaration
        """
        if not self.channel:
            raise RuntimeError("Channel not initialized. Call connect() first.")
        
        logger.info(f"Declaring queue '{queue_name}'")
        result = self.channel.queue_declare(
            queue=queue_name,
            durable=durable,
            exclusive=exclusive,
            auto_delete=auto_delete,
            arguments=arguments or {}
        )
        logger.info(f"Queue '{queue_name}' declared successfully")
        return result
    
    def bind_queue(
        self,
        queue_name: str,
        exchange_name: str,
        routing_key: str = "",
        arguments: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Bind a queue to an exchange with a routing key.
        
        Args:
            queue_name: Name of the queue
            exchange_name: Name of the exchange
            routing_key: Routing key pattern
            arguments: Optional arguments for binding
        """
        if not self.channel:
            raise RuntimeError("Channel not initialized. Call connect() first.")
        
        logger.info(
            f"Binding queue '{queue_name}' to exchange '{exchange_name}' "
            f"with routing key '{routing_key}'"
        )
        self.channel.queue_bind(
            queue=queue_name,
            exchange=exchange_name,
            routing_key=routing_key,
            arguments=arguments or {}
        )
        logger.info("Queue bound successfully")
    
    def close(self) -> None:
        """Close the connection gracefully."""
        if self.channel and self.channel.is_open:
            logger.info("Closing channel")
            self.channel.close()
        
        if self.connection and self.connection.is_open:
            logger.info("Closing connection")
            self.connection.close()
        
        logger.info("Connection closed")
    
    def is_connected(self) -> bool:
        """
        Check if connection is active.
        
        Returns:
            True if connected, False otherwise
        """
        return (
            self.connection is not None 
            and self.connection.is_open 
            and self.channel is not None 
            and self.channel.is_open
        )
