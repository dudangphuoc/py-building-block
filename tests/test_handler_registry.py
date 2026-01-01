"""
Tests for Handler Registry Module
"""

import pytest

from pubsub.event_base import Event
from pubsub.handler_registry import HandlerRegistry


class MockSuccessHandler:
    """Mock handler that always succeeds."""
    
    async def handle(self, event: Event) -> None:
        """Handle event successfully."""
        pass


class MockFailureHandler:
    """Mock handler that always fails."""
    
    async def handle(self, event: Event) -> None:
        """Handle event with failure."""
        raise Exception("Handler failed intentionally")


class MockConditionalHandler:
    """Mock handler that succeeds for specific events."""
    
    def __init__(self, required_action: str):
        self.required_action = required_action
    
    async def handle(self, event: Event) -> None:
        """Handle event conditionally."""
        if event.action != self.required_action:
            raise Exception(f"Expected action '{self.required_action}', got '{event.action}'")


class TestHandlerRegistry:
    """Tests for HandlerRegistry class."""
    
    def test_subscribe_handler(self):
        """Test registering a handler."""
        registry = HandlerRegistry()
        handler = MockSuccessHandler()
        
        registry.subscribe("test.*", handler)
        
        assert "test.*" in registry.handlers
        assert handler in registry.handlers["test.*"]
    
    def test_subscribe_multiple_handlers_same_pattern(self):
        """Test registering multiple handlers for the same pattern."""
        registry = HandlerRegistry()
        handler1 = MockSuccessHandler()
        handler2 = MockSuccessHandler()
        
        registry.subscribe("test.*", handler1)
        registry.subscribe("test.*", handler2)
        
        assert len(registry.handlers["test.*"]) == 2
        assert handler1 in registry.handlers["test.*"]
        assert handler2 in registry.handlers["test.*"]
    
    def test_subscribe_handlers_different_patterns(self):
        """Test registering handlers for different patterns."""
        registry = HandlerRegistry()
        handler1 = MockSuccessHandler()
        handler2 = MockSuccessHandler()
        
        registry.subscribe("order.*", handler1)
        registry.subscribe("user.*", handler2)
        
        assert len(registry.handlers) == 2
        assert "order.*" in registry.handlers
        assert "user.*" in registry.handlers
    
    def test_find_handlers_exact_match(self):
        """Test finding handlers with exact pattern match."""
        registry = HandlerRegistry()
        handler = MockSuccessHandler()
        
        registry.subscribe("order.created", handler)
        
        handlers = registry.find_handlers("order.created")
        
        assert len(handlers) == 1
        assert handler in handlers
    
    def test_find_handlers_wildcard_suffix(self):
        """Test finding handlers with wildcard suffix (e.g., order.*)."""
        registry = HandlerRegistry()
        handler = MockSuccessHandler()
        
        registry.subscribe("order.*", handler)
        
        # Should match
        assert len(registry.find_handlers("order.created")) == 1
        assert len(registry.find_handlers("order.updated")) == 1
        assert len(registry.find_handlers("order.deleted")) == 1
        
        # Should not match
        assert len(registry.find_handlers("user.created")) == 0
    
    def test_find_handlers_wildcard_prefix(self):
        """Test finding handlers with wildcard prefix (e.g., *.created)."""
        registry = HandlerRegistry()
        handler = MockSuccessHandler()
        
        registry.subscribe("*.created", handler)
        
        # Should match
        assert len(registry.find_handlers("order.created")) == 1
        assert len(registry.find_handlers("user.created")) == 1
        assert len(registry.find_handlers("product.created")) == 1
        
        # Should not match
        assert len(registry.find_handlers("order.updated")) == 0
    
    def test_find_handlers_wildcard_all(self):
        """Test finding handlers with catch-all wildcard (*)."""
        registry = HandlerRegistry()
        handler = MockSuccessHandler()
        
        registry.subscribe("*", handler)
        
        # Should match everything
        assert len(registry.find_handlers("order.created")) == 1
        assert len(registry.find_handlers("user.updated")) == 1
        assert len(registry.find_handlers("anything")) == 1
    
    def test_find_handlers_multiple_patterns_match(self):
        """Test finding handlers when multiple patterns match."""
        registry = HandlerRegistry()
        handler1 = MockSuccessHandler()
        handler2 = MockSuccessHandler()
        handler3 = MockSuccessHandler()
        
        registry.subscribe("order.*", handler1)
        registry.subscribe("*.created", handler2)
        registry.subscribe("*", handler3)
        
        # All three patterns should match "order.created"
        handlers = registry.find_handlers("order.created")
        
        assert len(handlers) == 3
        assert handler1 in handlers
        assert handler2 in handlers
        assert handler3 in handlers
    
    def test_find_handlers_no_match(self):
        """Test finding handlers when no patterns match."""
        registry = HandlerRegistry()
        handler = MockSuccessHandler()
        
        registry.subscribe("order.*", handler)
        
        handlers = registry.find_handlers("user.created")
        
        assert len(handlers) == 0
    
    @pytest.mark.asyncio
    async def test_invoke_all_single_success_handler(self):
        """Test invoking a single successful handler."""
        registry = HandlerRegistry()
        handler = MockSuccessHandler()
        
        registry.subscribe("test.action", handler)
        
        event = Event(domain="test", action="action", data={})
        result = await registry.invoke_all(event)
        
        assert result.success_count == 1
        assert result.failed_count == 0
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_invoke_all_multiple_success_handlers(self):
        """Test invoking multiple successful handlers."""
        registry = HandlerRegistry()
        handler1 = MockSuccessHandler()
        handler2 = MockSuccessHandler()
        handler3 = MockSuccessHandler()
        
        registry.subscribe("test.*", handler1)
        registry.subscribe("test.*", handler2)
        registry.subscribe("*", handler3)
        
        event = Event(domain="test", action="action", data={})
        result = await registry.invoke_all(event)
        
        assert result.success_count == 3
        assert result.failed_count == 0
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_invoke_all_single_failure_handler(self):
        """Test invoking a single failing handler."""
        registry = HandlerRegistry()
        handler = MockFailureHandler()
        
        registry.subscribe("test.action", handler)
        
        event = Event(domain="test", action="action", data={})
        result = await registry.invoke_all(event)
        
        assert result.success_count == 0
        assert result.failed_count == 1
        assert len(result.errors) == 1
        assert "MockFailureHandler" in result.errors[0]["handler"]
    
    @pytest.mark.asyncio
    async def test_invoke_all_mixed_handlers(self):
        """Test invoking mix of successful and failing handlers."""
        registry = HandlerRegistry()
        success_handler = MockSuccessHandler()
        failure_handler = MockFailureHandler()
        
        registry.subscribe("test.*", success_handler)
        registry.subscribe("test.*", failure_handler)
        
        event = Event(domain="test", action="action", data={})
        result = await registry.invoke_all(event)
        
        assert result.success_count == 1
        assert result.failed_count == 1
        assert len(result.errors) == 1
    
    @pytest.mark.asyncio
    async def test_invoke_all_no_handlers(self):
        """Test invoking when no handlers match."""
        registry = HandlerRegistry()
        handler = MockSuccessHandler()
        
        registry.subscribe("order.*", handler)
        
        event = Event(domain="user", action="created", data={})
        result = await registry.invoke_all(event)
        
        assert result.success_count == 0
        assert result.failed_count == 0
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_invoke_all_error_isolation(self):
        """Test that handler failures don't stop other handlers."""
        registry = HandlerRegistry()
        
        # Register handlers in specific order
        success_handler1 = MockSuccessHandler()
        failure_handler = MockFailureHandler()
        success_handler2 = MockSuccessHandler()
        
        registry.subscribe("test.*", success_handler1)
        registry.subscribe("test.*", failure_handler)
        registry.subscribe("test.*", success_handler2)
        
        event = Event(domain="test", action="action", data={})
        result = await registry.invoke_all(event)
        
        # Both success handlers should execute despite the failure
        assert result.success_count == 2
        assert result.failed_count == 1
