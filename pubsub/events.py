"""
Event Definitions

Defines specific event types for different domains.
These are subclasses of the base Event class with predefined domain and action.
"""

from typing import Dict, Any

from .event_base import Event


class OrderCreatedEvent(Event):
    """
    Event emitted when a new order is created.
    
    Expected data fields:
        - order_id: str
        - customer_email: str
        - items: list of dict with product_id and quantity
        - total_amount: float
    """
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(domain="order", action="created", data=data, **kwargs)


class OrderPaidEvent(Event):
    """
    Event emitted when an order payment is completed.
    
    Expected data fields:
        - order_id: str
        - payment_id: str
        - amount: float
        - payment_method: str
    """
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(domain="order", action="paid", data=data, **kwargs)


class UserRegisteredEvent(Event):
    """
    Event emitted when a new user registers.
    
    Expected data fields:
        - user_id: str
        - username: str
        - email: str
        - registration_date: str
    """
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(domain="user", action="registered", data=data, **kwargs)


class UserUpdatedEvent(Event):
    """
    Event emitted when user profile is updated.
    
    Expected data fields:
        - user_id: str
        - updated_fields: dict
    """
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(domain="user", action="updated", data=data, **kwargs)
