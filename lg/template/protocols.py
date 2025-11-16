"""
Protocols for modular template engine.

Defines interfaces for plugin interaction with core components.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, List


@runtime_checkable
class TemplateRegistryProtocol(Protocol):
    """
    Protocol for template engine registry for use in plugins.

    Defines methods that plugins can use for:
    - Extending token contexts
    - Analyzing registered plugins
    - Getting information about other system components
    """

    def register_tokens_in_context(self, context_name: str, token_names: List[str]) -> None:
        """
        Adds tokens to existing context.

        Args:
            context_name: Name of existing context
            token_names: Names of tokens to add to context

        Raises:
            ValueError: If context not found
        """
        ...


__all__ = ["TemplateRegistryProtocol"]