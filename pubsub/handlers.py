"""
Example Event Handlers

Demonstrates how to implement event handlers for different business logic scenarios.
These handlers are domain-agnostic and only contain business logic.
"""

import logging
from typing import Dict, Any

from .event_base import Event

logger = logging.getLogger(__name__)


class SendEmailHandler:
    """
    Handler for sending email notifications.
    
    This is a mock implementation. In a real system, this would integrate
    with an email service like SendGrid, AWS SES, etc.
    """
    
    async def handle(self, event: Event) -> None:
        """
        Send email based on event data.
        
        Args:
            event: Event containing email details
        """
        logger.info(
            f"[SendEmailHandler] Processing event {event.event_id} "
            f"({event.domain}.{event.action})"
        )
        
        # Extract email details from event data
        email_data = self._extract_email_data(event)
        
        # Simulate sending email
        logger.info(f"[SendEmailHandler] Sending email to {email_data.get('to', 'unknown')}")
        logger.info(f"[SendEmailHandler] Subject: {email_data.get('subject', 'N/A')}")
        logger.debug(f"[SendEmailHandler] Body: {email_data.get('body', 'N/A')}")
        
        # In a real implementation:
        # await email_service.send(
        #     to=email_data['to'],
        #     subject=email_data['subject'],
        #     body=email_data['body']
        # )
        
        logger.info(f"[SendEmailHandler] Email sent successfully for event {event.event_id}")
    
    def _extract_email_data(self, event: Event) -> Dict[str, Any]:
        """Extract email-related data from event."""
        data = event.data
        
        # Different event types may have different data structures
        if event.domain == "order" and event.action == "created":
            return {
                "to": data.get("customer_email", "customer@example.com"),
                "subject": f"Order Confirmation - {data.get('order_id', 'N/A')}",
                "body": f"Thank you for your order! Order ID: {data.get('order_id', 'N/A')}"
            }
        elif event.domain == "user" and event.action == "registered":
            return {
                "to": data.get("email", "user@example.com"),
                "subject": "Welcome!",
                "body": f"Welcome {data.get('username', 'User')}! Thank you for registering."
            }
        else:
            return {
                "to": data.get("email", "default@example.com"),
                "subject": f"Notification: {event.domain}.{event.action}",
                "body": f"Event: {event.domain}.{event.action}"
            }


class UpdateInventoryHandler:
    """
    Handler for updating inventory after order events.
    
    This is a mock implementation. In a real system, this would integrate
    with an inventory management system.
    """
    
    async def handle(self, event: Event) -> None:
        """
        Update inventory based on order events.
        
        Args:
            event: Event containing order details
        """
        logger.info(
            f"[UpdateInventoryHandler] Processing event {event.event_id} "
            f"({event.domain}.{event.action})"
        )
        
        # Only process order-related events
        if event.domain != "order":
            logger.debug(
                f"[UpdateInventoryHandler] Skipping non-order event: {event.domain}.{event.action}"
            )
            return
        
        # Extract order items
        items = event.data.get("items", [])
        
        if not items:
            logger.warning(
                f"[UpdateInventoryHandler] No items found in event {event.event_id}"
            )
            return
        
        # Update inventory for each item
        for item in items:
            product_id = item.get("product_id")
            quantity = item.get("quantity", 0)
            
            logger.info(
                f"[UpdateInventoryHandler] Reducing inventory for product {product_id} "
                f"by {quantity} units"
            )
            
            # In a real implementation:
            # await inventory_service.reduce_stock(
            #     product_id=product_id,
            #     quantity=quantity
            # )
        
        logger.info(
            f"[UpdateInventoryHandler] Inventory updated successfully for event {event.event_id}"
        )


class LogAnalyticsHandler:
    """
    Handler for logging analytics events.
    
    This is a mock implementation. In a real system, this would send data
    to an analytics platform like Google Analytics, Mixpanel, etc.
    """
    
    async def handle(self, event: Event) -> None:
        """
        Log analytics data for the event.
        
        Args:
            event: Event to log
        """
        logger.info(
            f"[LogAnalyticsHandler] Processing event {event.event_id} "
            f"({event.domain}.{event.action})"
        )
        
        # Prepare analytics data
        analytics_data = {
            "event_type": f"{event.domain}.{event.action}",
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "properties": event.data
        }
        
        logger.info(f"[LogAnalyticsHandler] Logging analytics: {analytics_data}")
        
        # In a real implementation:
        # await analytics_service.track(
        #     event_type=analytics_data['event_type'],
        #     properties=analytics_data['properties'],
        #     timestamp=analytics_data['timestamp']
        # )
        
        logger.info(
            f"[LogAnalyticsHandler] Analytics logged successfully for event {event.event_id}"
        )
