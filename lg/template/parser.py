"""
Parser for template engine.

Uses parsing rules from registered plugins to build AST.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from .nodes import TemplateNode, TemplateAST, TextNode
from .registry import TemplateRegistry
from .tokens import Token
from .types import ParsingRule, ParsingContext

logger = logging.getLogger(__name__)


class ModularParser:
    """
    Parser using rules from plugins.

    Applies parsing rules registered in TemplateRegistry
    in priority order to create AST.
    """

    def __init__(self, registry: TemplateRegistry):
        """
        Initializes parser with specified registry.

        Args:
            registry: Component registry (default is global)
        """
        self.registry = registry

    @property
    def parser_rules(self) -> List[ParsingRule]:
        """
        Returns parsing rules sorted by priority.

        Rules are obtained dynamically from registry, allowing
        registration of new rules after parser creation.
        """
        return self.registry.get_sorted_parser_rules()

    def parse(self, tokens: List[Token]) -> TemplateAST:
        """
        Parses tokens into AST using registered rules.

        Args:
            tokens: List of tokens to parse

        Returns:
            Template AST

        Raises:
            ParserError: If parsing error occurs
        """
        context = ParsingContext(tokens)
        ast: List[TemplateNode] = []

        while not context.is_at_end():
            node = self._parse_next_node(context)
            if node:
                ast.append(node)
            else:
                # If no rule matched, try to handle as text
                self._handle_unparsed_token(context, ast)

        return ast
    
    def _parse_next_node(self, context: ParsingContext) -> Optional[TemplateNode]:
        """
        Attempts to apply each parsing rule for current position.

        Public method for use from plugins via handlers.

        Parsing rules should:
        - Return AST node if successful parse
        - Return None if rule doesn't match (position must be reset by rule itself!)
        - Throw ParserError on fatal syntax error

        Args:
            context: Parsing context

        Returns:
            AST node or None if no rule matched

        Raises:
            ParserError: On fatal syntax error
        """
        # Try each rule in priority order
        for rule in self.parser_rules:
            if not rule.enabled:
                continue
            node = rule.parser_func(context)
            if node is not None:
                return node
        return None

    def _handle_unparsed_token(self, context: ParsingContext, ast: List[TemplateNode]) -> None:
        """
        Handles token that couldn't be parsed by rules.

        Args:
            context: Parsing context
            ast: Current AST for adding node
        """
        current_token = context.current()

        # Handle as text
        text_value = current_token.value
        context.advance()

        # Merge with previous TextNode if possible
        if ast and isinstance(ast[-1], TextNode):
            ast[-1] = TextNode(text=ast[-1].text + text_value)
        else:
            ast.append(TextNode(text=text_value))


def parse_template(text: str, registry: TemplateRegistry) -> TemplateAST:
    """
    Convenience function for parsing template from text.

    Args:
        text: Source text of template
        registry: Component registry (if None, creates base one)

    Returns:
        Template AST

    Raises:
        LexerError: If lexical analysis error occurs
        ParserError: If syntax analysis error occurs
    """
    from .lexer import ContextualLexer

    lexer = ContextualLexer(registry)
    tokens = lexer.tokenize(text)

    parser = ModularParser(registry)
    return parser.parse(tokens)


__all__ = ["ModularParser", "parse_template"]