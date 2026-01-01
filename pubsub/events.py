"""
Event Definitions

Defines specific event types for different domains.
These are subclasses of the base Event class with predefined domain and action.
"""

from dataclasses import dataclass
from typing import Dict, Any

from .event_base import Event


@dataclass
class OrderCreatedEvent(Event):
    """
    Event emitted when a new order is created.
    
    Expected data fields:
        - order_id: str
        - customer_email: str
        - items: list of dict with product_id and quantity
        - total_amount: float
    """
    domain: str = "order"
    action: str = "created"
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(domain="order", action="created", data=data, **kwargs)


@dataclass
class OrderPaidEvent(Event):
    """
    Event emitted when an order payment is completed.
    
    Expected data fields:
        - order_id: str
        - payment_id: str
        - amount: float
        - payment_method: str
    """
    domain: str = "order"
    action: str = "paid"
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(domain="order", action="paid", data=data, **kwargs)


@dataclass
class UserRegisteredEvent(Event):
    """
    Event emitted when a new user registers.
    
    Expected data fields:
        - user_id: str
        - username: str
        - email: str
        - registration_date: str
    """
    domain: str = "user"
    action: str = "registered"
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(domain="user", action="registered", data=data, **kwargs)


@dataclass
class UserUpdatedEvent(Event):
    """
    Event emitted when user profile is updated.
    
    Expected data fields:
        - user_id: str
        - updated_fields: dict
    """
    domain: str = "user"
    action: str = "updated"
    
    def __init__(self, data: Dict[str, Any], **kwargs):
        super().__init__(domain="user", action="updated", data=data, **kwargs)
