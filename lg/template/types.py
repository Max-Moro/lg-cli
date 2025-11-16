from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from re import Pattern
from typing import Callable, Optional, Type, List, Dict
from typing import Set

from .nodes import TemplateNode
from .tokens import Token, TokenType, TokenTypeName, ParserError


class PluginPriority(enum.IntEnum):
    """Priorities for determining parsing rules application order."""

    # Special constructs must be processed before plain text
    DIRECTIVE = 100      # Directives {% ... %}
    PLACEHOLDER = 90     # Placeholders ${ ... }
    COMMENT = 80        # Comments {# ... #}
    TEXT = 10           # Plain text (lowest priority)


@dataclass
class TokenSpec:
    """
    Token specification for registration in lexer.
    """
    name: str                    # Token name (e.g., "PLACEHOLDER_START")
    pattern: Pattern[str]        # Compiled regular expression
    priority: int = 50           # Priority (higher = checked first)


@dataclass
class ParsingRule:
    """
    Parsing rule for registration in parser.
    """
    name: str                    # Rule name
    priority: int                # Application priority
    parser_func: Callable[[ParsingContext], Optional[TemplateNode]]  # Parsing function
    enabled: bool = True        # Whether rule is enabled


@dataclass
class ProcessingContext:
    """
    AST node processing context.

    Provides plugins access to processing state without violating encapsulation.
    """
    ast: List[TemplateNode]  # Current AST
    node_index: int          # Index of node being processed

    def get_node(self) -> TemplateNode:
        """Returns current node being processed."""
        return self.ast[self.node_index]


@dataclass
class ProcessorRule:
    """
    Rule for processing AST nodes.
    """
    node_type: Type[TemplateNode]  # Type of node this rule processes
    processor_func: Callable[[ProcessingContext], str]  # Processing function


@dataclass
class ResolverRule:
    """
    Rule for resolving AST nodes.
    """
    node_type: Type[TemplateNode]  # Type of node this rule resolves
    resolver_func: Callable[[TemplateNode, str], TemplateNode]  # Resolving function (node, context) -> resolved_node


class ParsingContext:
    """
    Context for token parsing.

    Provides methods for navigating tokens and managing position
    during syntax analysis.
    """

    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
        self.length = len(tokens)

        # Stack for saving/restoring position
        self._position_stack: List[int] = []

    def current(self) -> Token:
        """Returns current token."""
        if self.position >= self.length:
            # Return EOF token
            return Token(TokenType.EOF.value, "", self.position, 0, 0)
        return self.tokens[self.position]

    def peek(self, offset: int = 1) -> Token:
        """Returns token at specified offset from current position."""
        pos = self.position + offset
        if pos >= self.length:
            return Token(TokenType.EOF.value, "", pos, 0, 0)
        return self.tokens[pos]

    def advance(self) -> Token:
        """Advances to next token and returns previous."""
        current = self.current()
        if self.position < self.length:
            self.position += 1
        return current

    def is_at_end(self) -> bool:
        """Checks if end of tokens reached."""
        return self.position >= self.length or self.current().type == TokenType.EOF.value

    def match(self, *token_types: TokenTypeName) -> bool:
        """Checks if current token matches one of specified types."""
        return self.current().type in token_types

    def consume(self, expected_type: TokenTypeName) -> Token:
        """
        Consumes token of expected type.

        Raises:
            ParserError: If token doesn't match expected type
        """
        current = self.current()
        if current.type != expected_type:
            raise ParserError(
                f"Expected {expected_type}, got {current.type}",
                current
            )
        return self.advance()


logger = logging.getLogger(__name__)

@dataclass
class TokenContext:
    """
    Context for tokenization with groups of related tokens.

    Defines scope of specific set of tokens,
    allowing collision prevention and performance improvement.
    """
    name: str  # Unique context name
    open_tokens: Set[str]  # Tokens that open context
    close_tokens: Set[str]  # Tokens that close context
    inner_tokens: Set[str]  # Tokens allowed only in this context
    allow_nesting: bool = False  # Allows/disallows nested contexts
    priority: int = 50  # Priority (for conflict resolution)

    def __post_init__(self):
        """Validates context settings."""
        if not self.name:
            raise ValueError("Token context name cannot be empty")

        if not self.open_tokens and not self.close_tokens:
            raise ValueError(f"Context '{self.name}' must have at least open or close tokens")

        # Check for intersections between token sets
        if self.open_tokens & self.close_tokens:
            overlapping = self.open_tokens & self.close_tokens
            logger.warning(
                f"Context '{self.name}' has overlapping open/close tokens: {overlapping}"
            )


TokenRegistry = Dict[str, TokenSpec]
ParserRulesRegistry = Dict[str, ParsingRule]
ProcessorRegistry = Dict[Type[TemplateNode], List[ProcessorRule]]
ResolverRegistry = Dict[Type[TemplateNode], List[ResolverRule]]


__all__ = [
    "PluginPriority",
    "TokenSpec",
    "ParsingRule",
    "ProcessingContext",
    "ProcessorRule",
    "ResolverRule",
    "ParsingContext",
    "TokenContext",
    "TokenRegistry",
    "ParserRulesRegistry",
    "ProcessorRegistry",
    "ResolverRegistry",
]
