"""
Central component registry for modular template engine.

Manages registration and organization of plugins, tokens, parsing rules,
and AST node handlers.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Type

from .base import TemplatePlugin, PluginList
from .handlers import TemplateProcessorHandlers
from .nodes import TemplateNode
from .protocols import TemplateRegistryProtocol
from .tokens import TokenType
from .types import TokenSpec, ParsingRule, ProcessorRule, ResolverRule, TokenRegistry, ParserRulesRegistry, \
    ProcessorRegistry, ResolverRegistry, TokenContext

logger = logging.getLogger(__name__)


class TemplateRegistry(TemplateRegistryProtocol):
    """
    Centralized registry for all template engine components.

    Manages plugin registration and their components.
    Ensures correct initialization order and dependency resolution.
    """

    def __init__(self):
        """Initializes registry."""

        # Component registries
        self.tokens: TokenRegistry = {}
        self.parser_rules: ParserRulesRegistry = {}
        self.processors: ProcessorRegistry = {}
        self.resolvers: ResolverRegistry = {}

        # Registry of contextual token groups
        self.token_contexts: Dict[str, TokenContext] = {}

        # Registered plugins
        self.plugins: PluginList = []

        # Initialization flag
        self._plugins_initialized = False

        # Register base tokens
        self._register_builtin_tokens()

    def _register_builtin_tokens(self) -> None:
        """Registers built-in tokens independent of plugins."""
        # Token for continuous text (between special constructs)
        # Captures one or more characters that are not start of special constructs
        # Stops before: ${, {%, {#
        text_token = TokenSpec(
            name=TokenType.TEXT.value,
            pattern=re.compile(r'(?:\$(?!\{)|\{(?![%#])|[^${])+'),  # Not $ before {, not { before % or #, or any other character
            priority=1  # Lowest priority - checked last
        )
        self.tokens[TokenType.TEXT.value] = text_token

    def register_plugin(self, plugin: TemplatePlugin) -> None:
        """
        Registers plugin and all its components.

        Args:
            plugin: Plugin to register

        Raises:
            ValueError: If plugin with same name already registered
        """
        if any(p.name == plugin.name for p in self.plugins):
            raise ValueError(f"Plugin '{plugin.name}' already registered")

        # Add plugin to list
        self.plugins.append(plugin)

        # Register plugin components
        self._register_plugin_tokens(plugin)
        self._register_plugin_token_contexts(plugin)
        self._register_plugin_parser_rules(plugin)
        self._register_plugin_processors(plugin)
        self._register_plugin_resolvers(plugin)

    def _register_plugin_tokens(self, plugin: TemplatePlugin) -> None:
        """Registers plugin tokens."""
        for token_spec in plugin.register_tokens():
            if token_spec.name in self.tokens:
                logger.warning(
                    f"Token '{token_spec.name}' from plugin '{plugin.name}' "
                    f"overwrites existing token"
                )
            self.tokens[token_spec.name] = token_spec

    def _register_plugin_token_contexts(self, plugin: TemplatePlugin) -> None:
        """Registers plugin token context groups."""
        for context in plugin.register_token_contexts():
            self.token_contexts[context.name] = context

    def _register_plugin_parser_rules(self, plugin: TemplatePlugin) -> None:
        """Registers plugin parsing rules."""
        for rule in plugin.register_parser_rules():
            if rule.name in self.parser_rules:
                logger.warning(
                    f"Parser rule '{rule.name}' from plugin '{plugin.name}' "
                    f"overwrites existing rule"
                )
            self.parser_rules[rule.name] = rule

    def _register_plugin_processors(self, plugin: TemplatePlugin) -> None:
        """Registers plugin node handlers."""
        for processor_rule in plugin.register_processors():
            node_type = processor_rule.node_type
            if node_type not in self.processors:
                self.processors[node_type] = []
            self.processors[node_type].append(processor_rule)

    def _register_plugin_resolvers(self, plugin: TemplatePlugin) -> None:
        """Registers plugin node resolvers."""
        for resolver_rule in plugin.register_resolvers():
            node_type = resolver_rule.node_type
            if node_type not in self.resolvers:
                self.resolvers[node_type] = []
            self.resolvers[node_type].append(resolver_rule)

    def initialize_plugins(self, handlers: TemplateProcessorHandlers) -> None:
        """
        Initializes all registered plugins.

        Args:
            handlers: Template engine core handlers to pass to plugins

        Called after registering all plugins for setting
        dependencies and final configuration.
        """
        if self._plugins_initialized:
            return

        # Sort plugins by priority
        sorted_plugins = sorted(self.plugins, key=lambda p: p.priority, reverse=True)

        # Set handlers and registry for plugins
        for plugin in sorted_plugins:
            plugin.set_registry(self)
            plugin.set_handlers(handlers)

        # Initialize plugins in priority order (may do additional fine registration)
        for plugin in sorted_plugins:
            plugin.initialize()

        self._plugins_initialized = True

    def get_sorted_parser_rules(self) -> List[ParsingRule]:
        """
        Returns parsing rules sorted by priority.

        Returns:
            List of rules in descending priority order
        """
        active_rules = [rule for rule in self.parser_rules.values() if rule.enabled]
        return sorted(active_rules, key=lambda r: r.priority, reverse=True)

    def get_processors_for_node(self, node_type: Type[TemplateNode]) -> List[ProcessorRule]:
        """
        Returns handlers for specified node type.

        Args:
            node_type: Node type to find handlers for

        Returns:
            List of handlers in descending priority order
        """
        return self.processors.get(node_type, [])

    def get_resolvers_for_node(self, node_type: Type[TemplateNode]) -> List[ResolverRule]:
        """
        Returns resolvers for specified node type.

        Args:
            node_type: Node type to find resolvers for

        Returns:
            List of resolvers in descending priority order
        """
        return self.resolvers.get(node_type, [])

    def get_tokens_by_priority(self) -> List[TokenSpec]:
        """
        Returns tokens sorted by priority.

        Tokens with higher priority are checked first.
        Important for correct recognition of keywords vs identifiers.

        Returns:
            List of token specifications in descending priority order
        """
        return sorted(self.tokens.values(), key=lambda spec: spec.priority, reverse=True)

    def register_tokens_in_context(self, context_name: str, token_names: List[str]) -> None:
        """
        Adds tokens to existing context.

        Args:
            context_name: Name of existing context
            token_names: Names of tokens to add to context

        Raises:
            ValueError: If context not found
        """
        if context_name not in self.token_contexts:
            raise ValueError(f"Token context '{context_name}' not found")

        context = self.token_contexts[context_name]
        # Create new context with updated tokens
        self.token_contexts[context_name] = TokenContext(
            name=context.name,
            open_tokens=context.open_tokens,
            close_tokens=context.close_tokens,
            inner_tokens=context.inner_tokens | set(token_names),
            allow_nesting=context.allow_nesting,
        )

    def get_all_token_contexts(self) -> List[TokenContext]:
        """
        Returns all registered token contexts.

        Returns:
            List of all contexts
        """
        return list(self.token_contexts.values())


__all__ = ["TemplateRegistry"]