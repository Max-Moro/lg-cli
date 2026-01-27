"""
Recursive descent parser for conditional expressions.

Builds an abstract syntax tree (AST) from a sequence of tokens.
Supports operator precedence and parenthesized grouping.

Grammar:
expression     → or_expression
or_expression  → and_expression ("OR" and_expression)*
and_expression → not_expression ("AND" not_expression)*
not_expression → "NOT" not_expression | primary
primary        → tag_condition | tagset_condition | scope_condition | provider_condition | "(" expression ")"

tag_condition      → "tag" ":" IDENTIFIER
tagset_condition   → "TAGSET" ":" IDENTIFIER ":" IDENTIFIER
scope_condition    → "scope" ":" IDENTIFIER
provider_condition → "provider" ":" dotted_identifier
dotted_identifier  → IDENTIFIER ("." IDENTIFIER)*
"""

from __future__ import annotations

from typing import List

from .lexer import ConditionLexer, Token
from .model import (
    Condition,
    ConditionType,
    TagCondition,
    TagSetCondition,
    TagOnlyCondition,
    ScopeCondition,
    TaskCondition,
    ProviderCondition,
    GroupCondition,
    NotCondition,
    BinaryCondition,
)
from ..errors import LGUserError


class ParseError(LGUserError):
    """Error parsing a conditional expression."""

    def __init__(self, message: str, position: int):
        self.message = message
        self.position = position
        super().__init__(f"Parse error at position {position}: {message}")


class ConditionParser:
    """
    Recursive descent parser for conditional expressions.

    Converts a list of tokens into an abstract syntax tree,
    respecting operator precedence and grouping rules.
    """
    
    def __init__(self):
        self.lexer = ConditionLexer()
        self._tokens: List[Token] = []
        self._position = 0
    
    def parse(self, condition_str: str) -> Condition:
        """
        Parse a condition string into an AST.

        Args:
            condition_str: Condition expression string

        Returns:
            Root node of the AST

        Raises:
            ParseError: On syntax error
            ValueError: On tokenization error
        """
        self._tokens = self.lexer.tokenize(condition_str)
        self._position = 0

        if not self._tokens or (len(self._tokens) == 1 and self._tokens[0].type == 'EOF'):
            raise ParseError("Empty condition", 0)

        result = self._parse_expression()

        # Check that we reached the end of input
        if not self._is_at_end():
            current = self._current_token()
            raise ParseError(f"Unexpected token '{current.value}'", current.position)

        return result
    
    def _parse_expression(self) -> Condition:
        """Parse a complete expression (grammar start symbol)."""
        return self._parse_or_expression()

    def _parse_or_expression(self) -> Condition:
        """Parse an expression with OR operator (lowest precedence)."""
        left = self._parse_and_expression()

        while self._match_keyword("OR"):
            right = self._parse_and_expression()
            left = BinaryCondition(left=left, right=right, operator=ConditionType.OR)

        return left

    def _parse_and_expression(self) -> Condition:
        """Parse an expression with AND operator (medium precedence)."""
        left = self._parse_not_expression()

        while self._match_keyword("AND"):
            right = self._parse_not_expression()
            left = BinaryCondition(left=left, right=right, operator=ConditionType.AND)

        return left

    def _parse_not_expression(self) -> Condition:
        """Parse an expression with NOT operator (highest precedence)."""
        if self._match_keyword("NOT"):
            condition = self._parse_not_expression()  # Right associativity for NOT
            return NotCondition(condition=condition)

        return self._parse_primary()

    def _parse_primary(self) -> Condition:
        """Parse a primary expression (atomic conditions and parenthesized groups)."""
        # Parenthesized grouping
        if self._match_symbol("("):
            expr = self._parse_expression()
            if not self._match_symbol(")"):
                raise ParseError("Expected ')' after grouped expression", self._current_position())
            return GroupCondition(condition=expr)

        # tag:name
        if self._match_keyword("tag"):
            return self._parse_tag_condition()

        # TAGSET:set:tag
        if self._match_keyword("TAGSET"):
            return self._parse_tagset_condition()

        # TAGONLY:set:tag
        if self._match_keyword("TAGONLY"):
            return self._parse_tagonly_condition()

        # scope:type
        if self._match_keyword("scope"):
            return self._parse_scope_condition()

        # task (condition without parameters)
        if self._match_keyword("task"):
            return TaskCondition()

        # provider:base-id (dotted identifier)
        if self._match_keyword("provider"):
            return self._parse_provider_condition()

        # If nothing matched, it's an error
        current = self._current_token()
        if current.type == 'EOF':
            raise ParseError("Unexpected end of expression", current.position)
        else:
            raise ParseError(f"Unexpected token '{current.value}'", current.position)
    
    def _parse_tag_condition(self) -> TagCondition:
        """Parse a tag condition: tag:name"""
        if not self._match_symbol(":"):
            raise ParseError("Expected ':' after 'tag'", self._current_position())

        name_token = self._consume_identifier("Expected tag name after 'tag:'")
        return TagCondition(name=name_token.value)

    def _parse_tagset_condition(self) -> TagSetCondition:
        """Parse a tag set condition: TAGSET:set:tag"""
        if not self._match_symbol(":"):
            raise ParseError("Expected ':' after 'TAGSET'", self._current_position())

        set_name_token = self._consume_identifier("Expected set name after 'TAGSET:'")

        if not self._match_symbol(":"):
            raise ParseError("Expected ':' after set name", self._current_position())

        tag_name_token = self._consume_identifier("Expected tag name after set name")

        return TagSetCondition(set_name=set_name_token.value, tag_name=tag_name_token.value)

    def _parse_tagonly_condition(self) -> TagOnlyCondition:
        """Parse exclusive tag condition: TAGONLY:set:tag"""
        if not self._match_symbol(":"):
            raise ParseError("Expected ':' after 'TAGONLY'", self._current_position())

        set_name_token = self._consume_identifier("Expected set name after 'TAGONLY:'")

        if not self._match_symbol(":"):
            raise ParseError("Expected ':' after set name", self._current_position())

        tag_name_token = self._consume_identifier("Expected tag name after set name")

        return TagOnlyCondition(set_name=set_name_token.value, tag_name=tag_name_token.value)

    def _parse_scope_condition(self) -> ScopeCondition:
        """Parse a scope condition: scope:type"""
        if not self._match_symbol(":"):
            raise ParseError("Expected ':' after 'scope'", self._current_position())

        type_token = self._consume_identifier("Expected scope type after 'scope:'")

        # Validate scope type
        if type_token.value not in ("local", "parent"):
            raise ParseError(
                f"Invalid scope type '{type_token.value}'. Expected 'local' or 'parent'",
                type_token.position
            )

        return ScopeCondition(scope_type=type_token.value)

    def _parse_provider_condition(self) -> ProviderCondition:
        """Parse a provider condition: provider:base.id

        Base-id is a dotted identifier (e.g., com.anthropic.claude).
        """
        if not self._match_symbol(":"):
            raise ParseError("Expected ':' after 'provider'", self._current_position())

        # Collect dotted identifier segments
        first_token = self._consume_identifier("Expected provider base-id after 'provider:'")
        parts = [first_token.value]

        while self._match_symbol("."):
            next_token = self._consume_identifier("Expected identifier after '.'")
            parts.append(next_token.value)

        return ProviderCondition(base_id=".".join(parts))

    # Helper methods for working with tokens

    def _current_token(self) -> Token:
        """Return the current token without advancing the position."""
        if self._position >= len(self._tokens):
            # Return EOF if we're past the bounds
            return Token(type='EOF', value='', position=len(self._tokens))
        return self._tokens[self._position]

    def _current_position(self) -> int:
        """Return the current position in the source string."""
        return self._current_token().position

    def _is_at_end(self) -> bool:
        """Check if we have reached the end of tokens."""
        return self._current_token().type == 'EOF'

    def _advance(self) -> Token:
        """Advance the position and return the previous token."""
        if not self._is_at_end():
            self._position += 1
        return self._tokens[self._position - 1] if self._position > 0 else self._current_token()

    def _match_keyword(self, keyword: str) -> bool:
        """Check and consume a keyword."""
        current = self._current_token()
        if current.type == 'KEYWORD' and current.value == keyword:
            self._advance()
            return True
        return False

    def _match_symbol(self, symbol: str) -> bool:
        """Check and consume a symbol."""
        current = self._current_token()
        if current.type == 'SYMBOL' and current.value == symbol:
            self._advance()
            return True
        return False

    def _consume_identifier(self, error_message: str) -> Token:
        """Consume an identifier or raise an error.

        Note: Keywords are also accepted as identifiers since reserved words
        can be valid tag/set names (e.g., TAGONLY:set:tag).
        """
        current = self._current_token()
        if current.type in ('IDENTIFIER', 'KEYWORD'):
            return self._advance()

        raise ParseError(error_message, current.position)