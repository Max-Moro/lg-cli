"""
Base interfaces and abstractions for modular template engine.

Defines base classes and interfaces that plugins must implement
for integration into the template system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .handlers import TemplateProcessorHandlers
from .protocols import TemplateRegistryProtocol
# Import custom types
from .types import PluginPriority, TokenSpec, ParsingRule, ProcessorRule, ResolverRule, TokenContext


class TemplatePlugin(ABC):
    """
    Base interface for template engine plugins.

    Each plugin must implement this interface to register
    its components in the template system.
    """

    def __init__(self):
        """Initializes the plugin."""
        self._handlers: Optional[TemplateProcessorHandlers] = None
        self._registry: Optional[TemplateRegistryProtocol] = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the plugin name."""
        pass

    @property
    @abstractmethod
    def priority(self) -> PluginPriority:
        """Returns the plugin priority."""
        pass
    
    def set_handlers(self, handlers: TemplateProcessorHandlers) -> None:
        """
        Sets the template engine core handlers.

        Args:
            handlers: Internal handlers for calling core functions
        """
        self._handlers = handlers
    
    @property
    def handlers(self) -> TemplateProcessorHandlers:
        """
        Returns the template engine core handlers.

        Returns:
            Handlers for calling core functions
        """
        assert self._handlers is not None, "Handlers must be set before use"
        return self._handlers
    
    def set_registry(self, registry: TemplateRegistryProtocol) -> None:
        """
        Sets the template engine registry for the plugin.

        Args:
            registry: Registry for accessing context extensions
        """
        self._registry = registry
    
    @property
    def registry(self) -> TemplateRegistryProtocol:
        """
        Returns the template engine registry.

        Returns:
            Registry for calling context extension functions
        """
        assert self._registry is not None, "Registry must be set before use"
        return self._registry
    
    @abstractmethod
    def register_tokens(self) -> List[TokenSpec]:
        """
        Registers tokens that the lexer should recognize.

        Returns:
            List of token specifications
        """
        pass

    def register_token_contexts(self) -> List[TokenContext]:
        """
        Registers contextual token groups.

        Returns:
            List of token contexts
        """
        return []

    @abstractmethod
    def register_parser_rules(self) -> List[ParsingRule]:
        """
        Registers parsing rules for creating AST nodes.

        Returns:
            List of parsing rules
        """
        pass

    @abstractmethod
    def register_processors(self) -> List[ProcessorRule]:
        """
        Registers handlers for AST nodes.

        Returns:
            List of processor rules
        """
        pass
    
    def register_resolvers(self) -> List[ResolverRule]:
        """
        Registers resolvers for AST nodes.

        Returns:
            List of resolver rules
        """
        return []

    def initialize(self) -> None:
        """
        Initializes the plugin after all components are registered.

        Called after all plugins have registered their components.
        Can be used for setting up dependencies between plugins.
        """
        pass


# Type aliases for convenience
PluginList = List[TemplatePlugin]

__all__ = [
    "TemplatePlugin",
    "PluginList"
]