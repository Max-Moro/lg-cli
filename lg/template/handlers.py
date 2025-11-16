"""
Internal handlers for modular template engine.

Provides typed interface for plugin interaction with core,
avoiding pollution of external contracts.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .nodes import TemplateNode
from .types import ProcessingContext
from ..types import SectionRef


@runtime_checkable
class TemplateProcessorHandlers(Protocol):
    """
    Protocol for internal template engine handlers.

    Defines typed interface for calling core functions
    from plugins without violating encapsulation.
    """

    def process_ast_node(self, context: ProcessingContext) -> str:
        """
        Processes single AST node with context.

        Args:
            context: Processing context (ProcessingContext)

        Returns:
            Rendered node content
        """
        ...

    def process_section_ref(self, section_ref: SectionRef) -> str:
        """
        Processes section reference.

        Args:
            section_ref: Section reference to process

        Returns:
            Rendered section content
        """
        ...

    def parse_next_node(self, context) -> TemplateNode | None:
        """
        Parses next node from parsing context.

        Applies all registered parsing rules for current position.
        Used for recursive parsing of nested structures.

        Args:
            context: Parsing context (ParsingContext)

        Returns:
            AST node or None if no rule matched
        """
        ...

    def resolve_ast(self, ast, context: str = "") -> list:
        """
        Recursively resolves AST through all registered resolvers.

        Applies all plugin resolvers, processing nested nodes.
        Used by plugins to delegate recursive resolving to core.

        Args:
            ast: AST to resolve
            context: Context for diagnostics

        Returns:
            Resolved AST
        """
        ...


__all__ = ["TemplateProcessorHandlers"]