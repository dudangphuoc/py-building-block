"""
Dependency Injection Container

Provides automatic dependency injection with assembly scanning for
repositories and unit of work classes.
"""

import logging
import inspect
from typing import Any, Callable, Dict, Optional, Type, TypeVar, get_type_hints
from types import ModuleType

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DIContainer:
    """
    Dependency Injection container with automatic registration.
    
    Supports:
    - Manual registration of types and instances
    - Automatic scanning and registration from modules
    - Constructor injection
    - Singleton and transient lifetimes
    
    Usage:
        container = DIContainer()
        
        # Manual registration
        container.register(EventBus, EventBus(), lifetime='singleton')
        container.register(OrderRepository, OrderRepository)
        
        # Automatic registration from module
        import my_repositories
        container.register_from_module(my_repositories)
        
        # Resolve dependencies
        order_repo = container.resolve(OrderRepository)
    """
    
    def __init__(self):
        """Initialize DI container with empty registrations."""
        self._registrations: Dict[Type, Dict[str, Any]] = {}
        self._instances: Dict[Type, Any] = {}
    
    def register(
        self,
        interface: Type[T],
        implementation: Any = None,
        lifetime: str = 'transient'
    ) -> None:
        """
        Register a type with the container.
        
        Args:
            interface: The interface or base type to register
            implementation: The implementation (class or instance)
            lifetime: 'singleton' for single instance, 'transient' for new instance each time
        """
        if implementation is None:
            implementation = interface
        
        self._registrations[interface] = {
            'implementation': implementation,
            'lifetime': lifetime
        }
        
        logger.debug(
            f"Registered {interface.__name__} -> "
            f"{implementation if isinstance(implementation, type) else implementation.__class__.__name__} "
            f"({lifetime})"
        )
    
    def register_instance(self, interface: Type[T], instance: T) -> None:
        """
        Register a singleton instance.
        
        Args:
            interface: The interface type
            instance: The instance to register
        """
        self._registrations[interface] = {
            'implementation': instance,
            'lifetime': 'singleton'
        }
        self._instances[interface] = instance
        logger.debug(f"Registered singleton instance {interface.__name__}")
    
    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve a type from the container.
        
        Args:
            interface: The interface type to resolve
            
        Returns:
            Instance of the requested type
            
        Raises:
            ValueError: If type is not registered
        """
        if interface not in self._registrations:
            raise ValueError(f"Type {interface.__name__} is not registered")
        
        registration = self._registrations[interface]
        implementation = registration['implementation']
        lifetime = registration['lifetime']
        
        # If singleton, return existing instance if available
        if lifetime == 'singleton':
            if interface in self._instances:
                logger.debug(f"Returning singleton instance of {interface.__name__}")
                return self._instances[interface]
            
            # If implementation is already an instance, use it
            if not isinstance(implementation, type):
                self._instances[interface] = implementation
                return implementation
        
        # If implementation is already an instance (not a class), return it
        if not isinstance(implementation, type):
            return implementation
        
        # Create new instance with dependency injection
        instance = self._create_instance(implementation)
        
        # Store singleton instance
        if lifetime == 'singleton':
            self._instances[interface] = instance
        
        logger.debug(f"Created instance of {interface.__name__}")
        return instance
    
    def _create_instance(self, cls: Type[T]) -> T:
        """
        Create instance with constructor injection.
        
        Args:
            cls: Class to instantiate
            
        Returns:
            Instance with dependencies injected
        """
        try:
            # Get constructor signature
            sig = inspect.signature(cls.__init__)
            params = sig.parameters
            
            # Skip 'self' parameter
            param_names = [p for p in params.keys() if p != 'self']
            
            if not param_names:
                # No dependencies, create directly
                return cls()
            
            # Try to get type hints for constructor
            try:
                type_hints = get_type_hints(cls.__init__)
            except Exception:
                type_hints = {}
            
            # Resolve dependencies
            kwargs = {}
            for param_name in param_names:
                param = params[param_name]
                
                # Check if parameter has type annotation
                if param_name in type_hints:
                    param_type = type_hints[param_name]
                    
                    # Try to resolve from container
                    if param_type in self._registrations:
                        kwargs[param_name] = self.resolve(param_type)
                    elif param.default != inspect.Parameter.empty:
                        # Use default value
                        kwargs[param_name] = param.default
                elif param.default != inspect.Parameter.empty:
                    # Use default value
                    kwargs[param_name] = param.default
            
            return cls(**kwargs)
            
        except Exception as e:
            logger.warning(
                f"Failed to auto-inject dependencies for {cls.__name__}: {e}. "
                "Creating instance without dependencies."
            )
            # Fallback: try to create without dependencies
            try:
                return cls()
            except Exception as e2:
                logger.error(f"Failed to create instance of {cls.__name__}: {e2}")
                raise
    
    def register_from_module(
        self,
        module: ModuleType,
        base_class: Optional[Type] = None,
        lifetime: str = 'transient'
    ) -> int:
        """
        Automatically register classes from a module.
        
        This method scans a module for classes and registers them.
        Similar to C#'s Assembly scanning.
        
        Args:
            module: The module to scan
            base_class: Optional base class to filter by
            lifetime: Lifetime for registered types
            
        Returns:
            Number of types registered
        """
        count = 0
        
        # Get all classes from module
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Skip if not defined in this module
            if obj.__module__ != module.__name__:
                continue
            
            # Skip abstract classes
            if inspect.isabstract(obj):
                continue
            
            # Filter by base class if specified
            if base_class is not None:
                if not issubclass(obj, base_class):
                    continue
            
            # Register the class
            self.register(obj, obj, lifetime=lifetime)
            count += 1
        
        logger.info(f"Registered {count} types from module {module.__name__}")
        return count
    
    def register_from_modules(
        self,
        modules: list,
        base_class: Optional[Type] = None,
        lifetime: str = 'transient'
    ) -> int:
        """
        Automatically register classes from multiple modules.
        
        Args:
            modules: List of modules to scan
            base_class: Optional base class to filter by
            lifetime: Lifetime for registered types
            
        Returns:
            Total number of types registered
        """
        total_count = 0
        for module in modules:
            count = self.register_from_module(module, base_class, lifetime)
            total_count += count
        
        logger.info(f"Registered total of {total_count} types from {len(modules)} modules")
        return total_count
    
    def is_registered(self, interface: Type) -> bool:
        """
        Check if a type is registered.
        
        Args:
            interface: Type to check
            
        Returns:
            True if registered, False otherwise
        """
        return interface in self._registrations
    
    def clear(self) -> None:
        """Clear all registrations and instances."""
        self._registrations.clear()
        self._instances.clear()
        logger.debug("Cleared all registrations from DI container")
