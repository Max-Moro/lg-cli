"""
Parsing rules for adaptive constructs in templates.

Handles directives {% ... %}, comments {# ... #},
conditional blocks if-elif-else, mode blocks mode-endmode.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from .nodes import ConditionalBlockNode, ElifBlockNode, ElseBlockNode, ModeBlockNode, CommentNode
from ..nodes import TemplateNode
from ..tokens import ParserError
from ..types import PluginPriority, ParsingRule, ParsingContext

# Callable type for recursive parsing
ParseNextNodeFunc = Callable[[ParsingContext], Optional[TemplateNode]]


class AdaptiveParserRules:
    """
    Parsing rules class for adaptive constructs.

    Encapsulates all parsing rules with access to the recursive
    parsing functor through instance state.
    """

    def __init__(self, parse_next_node: ParseNextNodeFunc):
        """
        Initializes parsing rules.

        Args:
            parse_next_node: Functor for recursive parsing of the next node
        """
        self.parse_next_node = parse_next_node
    
    def parse_directive(self, context: ParsingContext) -> Optional[TemplateNode]:
        """
        Parses a directive {% ... %}.

        Can be a condition (if), a mode, or their termination.
        Recursively processes nested directives.
        """
        # Check for directive start
        if not context.match("DIRECTIVE_START"):
            return None


        # Consume {%
        context.consume("DIRECTIVE_START")

        # Collect directive content tokens
        content_tokens = []
        while not context.is_at_end() and not context.match("DIRECTIVE_END"):
            content_tokens.append(context.advance())

        if context.is_at_end():
            raise ParserError("Unexpected end of tokens, expected %}", context.current())

        # Consume %}
        context.consume("DIRECTIVE_END")

        # Parse directive content
        return self._parse_directive_content(content_tokens, context)


    def _parse_directive_content(self, content_tokens: List, context: ParsingContext) -> TemplateNode:
        """Parses directive content based on tokens."""
        if not content_tokens:
            raise ParserError("Empty directive", context.current())

        # Skip whitespace at the beginning
        non_whitespace_tokens = [t for t in content_tokens if t.type != "WHITESPACE"]
        if not non_whitespace_tokens:
            raise ParserError("Empty directive (only whitespace)", context.current())

        first_token = non_whitespace_tokens[0]
        keyword = first_token.value.lower()

        if keyword == 'if':
            return self._parse_if_directive(content_tokens, context)
        elif keyword == 'elif':
            raise ParserError("elif without if", first_token)
        elif keyword == 'else':
            # Standalone else should not appear (processed within if)
            raise ParserError("else without if", first_token)
        elif keyword == 'mode':
            return self._parse_mode_directive(content_tokens, context)
        elif keyword == 'endif':
            raise ParserError("endif without if", first_token)
        elif keyword == 'endmode':
            raise ParserError("endmode without mode", first_token)
        else:
            raise ParserError(f"Unknown directive: {first_token.value}", first_token)


    def _parse_if_directive(self, content_tokens: List, context: ParsingContext) -> ConditionalBlockNode:
        """
        Parses a conditional directive {% if condition %} with elif and else support.
        """
        # Skip whitespace and find 'if'
        non_whitespace = [t for t in content_tokens if t.type != "WHITESPACE"]
        if not non_whitespace or non_whitespace[0].value.lower() != 'if':
            raise ParserError("Expected 'if' keyword", content_tokens[0] if content_tokens else context.current())

        # Extract condition (all tokens after 'if', excluding leading and trailing whitespace)
        # Find index of first 'if' token
        if_index = -1
        for i, t in enumerate(content_tokens):
            if t.type == "IDENTIFIER" and t.value.lower() == "if":
                if_index = i
                break

        if if_index == -1 or if_index + 1 >= len(content_tokens):
            raise ParserError("Missing condition in if directive", content_tokens[0] if content_tokens else context.current())

        # Take all tokens after 'if', excluding leading whitespace
        condition_tokens = content_tokens[if_index + 1:]
        # Remove leading whitespace
        while condition_tokens and condition_tokens[0].type == "WHITESPACE":
            condition_tokens = condition_tokens[1:]

        if not condition_tokens:
            raise ParserError("Missing condition in if directive", content_tokens[if_index])

        condition_text = self._reconstruct_condition_text(condition_tokens)

        # Parse condition using condition parser
        try:
            from ...conditions.parser import ConditionParser
            condition_parser = ConditionParser()
            condition_ast = condition_parser.parse(condition_text)
        except Exception as e:
            raise ParserError(f"Invalid condition: {e}", content_tokens[0])

        # Parse condition body until elif, else or endif
        body_nodes = []
        elif_blocks = []
        else_block = None
        found_end = False

        while not context.is_at_end():
            # Check if we encountered endif, elif or else
            if self._check_directive_keyword(context, 'endif'):
                self._consume_directive_keyword(context, 'endif')
                found_end = True
                break
            elif self._check_directive_keyword(context, 'elif'):
                # Parse elif blocks
                elif_blocks.extend(self._parse_elif_blocks(context))
                # After parsing all elif blocks, check for else
                if self._check_directive_keyword(context, 'else'):
                    self._consume_directive_keyword(context, 'else')
                    else_block = self._parse_else_block(context)
                self._consume_directive_keyword(context, 'endif')
                found_end = True
                break
            elif self._check_directive_keyword(context, 'else'):
                self._consume_directive_keyword(context, 'else')
                else_block = self._parse_else_block(context)
                self._consume_directive_keyword(context, 'endif')
                found_end = True
                break

            # Parse next node (recursively apply all parsing rules)
            # use functor to call parser
            node = self.parse_next_node(context)
            if node:
                body_nodes.append(node)
            else:
                # If unable to parse node, treat as text
                token = context.advance()
                from ..nodes import TextNode
                body_nodes.append(TextNode(text=token.value))

        if not found_end:
            raise ParserError("Unexpected end of tokens, expected {% endif %}", content_tokens[0])

        return ConditionalBlockNode(
            condition_text=condition_text,
            body=body_nodes,
            elif_blocks=elif_blocks,
            else_block=else_block,
            condition_ast=condition_ast
        )


    def _parse_elif_blocks(self, context: ParsingContext) -> List[ElifBlockNode]:
        """
        Parses a sequence of elif blocks.
        """
        elif_blocks = []

        while self._check_directive_keyword(context, 'elif'):
            # Consume {%
            context.consume("DIRECTIVE_START")

            # Collect elif directive content tokens
            content_tokens = []
            while not context.is_at_end() and not context.match("DIRECTIVE_END"):
                content_tokens.append(context.advance())

            # Consume %}
            context.consume("DIRECTIVE_END")

            # Parse elif directive content
            elif_block = self._parse_single_elif_directive(content_tokens, context)
            elif_blocks.append(elif_block)

        return elif_blocks

    def _parse_single_elif_directive(self, content_tokens: List, context: ParsingContext) -> ElifBlockNode:
        """Parses a single elif directive from already extracted content tokens."""
        # Skip whitespace at the beginning
        non_whitespace = [t for t in content_tokens if t.type != "WHITESPACE"]
        if not non_whitespace or non_whitespace[0].value.lower() != 'elif':
            raise ParserError("Expected 'elif' keyword", content_tokens[0] if content_tokens else context.current())

        # Find index of first 'elif' token
        elif_index = -1
        for i, t in enumerate(content_tokens):
            if t.type == "IDENTIFIER" and t.value.lower() == "elif":
                elif_index = i
                break

        if elif_index == -1 or elif_index + 1 >= len(content_tokens):
            raise ParserError("Missing condition in elif directive", content_tokens[0])

        # Take all tokens after 'elif', excluding leading whitespace
        condition_tokens = content_tokens[elif_index + 1:]
        while condition_tokens and condition_tokens[0].type == "WHITESPACE":
            condition_tokens = condition_tokens[1:]

        if not condition_tokens:
            raise ParserError("Missing condition in elif directive", content_tokens[elif_index])

        condition_text = self._reconstruct_condition_text(condition_tokens)

        # Parse condition using condition parser
        try:
            from ...conditions.parser import ConditionParser
            condition_parser = ConditionParser()
            condition_ast = condition_parser.parse(condition_text)
        except Exception as e:
            raise ParserError(f"Invalid elif condition: {e}", content_tokens[0])

        # Parse elif block body
        elif_body = []
        while not context.is_at_end():
            if (self._check_directive_keyword(context, 'elif') or
                self._check_directive_keyword(context, 'else') or
                self._check_directive_keyword(context, 'endif')):
                break

            # Parse next node - nested directives are processed recursively
            node = self.parse_next_node(context)
            if node:
                elif_body.append(node)
            else:
                # If unable to parse node, treat as text
                token = context.advance()
                from ..nodes import TextNode
                elif_body.append(TextNode(text=token.value))

        return ElifBlockNode(
            condition_text=condition_text,
            body=elif_body,
            condition_ast=condition_ast
        )


    def _parse_else_block(self, context: ParsingContext) -> ElseBlockNode:
        """Parses else block body."""
        else_body = []

        while not context.is_at_end():
            if self._check_directive_keyword(context, 'endif'):
                break

            node = self.parse_next_node(context)
            if node:
                else_body.append(node)
            else:
                # If unable to parse node, treat as text
                token = context.advance()
                from ..nodes import TextNode
                else_body.append(TextNode(text=token.value))

        return ElseBlockNode(body=else_body)

    def _parse_mode_directive(self, content_tokens: List, context: ParsingContext) -> ModeBlockNode:
        """
        Parses a mode directive {% mode modeset:mode %}.
        """
        # Expected format: mode modeset:mode_name
        if len(content_tokens) < 2:
            raise ParserError("Missing mode specification in mode directive", content_tokens[0])

        # Find index of 'mode' token
        mode_index = -1
        for i, t in enumerate(content_tokens):
            if t.type == "IDENTIFIER" and t.value.lower() == "mode":
                mode_index = i
                break

        if mode_index == -1 or mode_index + 1 >= len(content_tokens):
            raise ParserError("Missing mode specification in mode directive", content_tokens[0])

        # Take all tokens after 'mode', excluding leading whitespace
        mode_spec_tokens = content_tokens[mode_index + 1:]
        while mode_spec_tokens and mode_spec_tokens[0].type == "WHITESPACE":
            mode_spec_tokens = mode_spec_tokens[1:]

        if not mode_spec_tokens:
            raise ParserError("Missing mode specification in mode directive", content_tokens[mode_index])

        # Collect mode specification without whitespace
        mode_spec = ''.join(t.value for t in mode_spec_tokens if t.type != "WHITESPACE")

        # Parse mode specification (format: modeset:mode)
        if ':' not in mode_spec:
            raise ParserError(
                f"Invalid mode specification '{mode_spec}'. Expected format: modeset:mode",
                content_tokens[1]
            )

        parts = mode_spec.split(':', 1)
        modeset = parts[0].strip()
        mode = parts[1].strip()

        if not modeset or not mode:
            raise ParserError(
                f"Invalid mode specification '{mode_spec}'. Both modeset and mode must be non-empty",
                content_tokens[1]
            )

        # Parse mode block body until endmode
        body_nodes = []
        found_end = False

        while not context.is_at_end():
            if self._check_directive_keyword(context, 'endmode'):
                self._consume_directive_keyword(context, 'endmode')
                found_end = True
                break

            node = self.parse_next_node(context)
            if node:
                body_nodes.append(node)
            else:
                # If unable to parse node, treat as text
                token = context.advance()
                from ..nodes import TextNode
                body_nodes.append(TextNode(text=token.value))

        if not found_end:
            raise ParserError("Unexpected end of tokens, expected {% endmode %}", content_tokens[0])

        return ModeBlockNode(
            modeset=modeset,
            mode=mode,
            body=body_nodes
        )


    def parse_comment(self, context: ParsingContext) -> Optional[TemplateNode]:
        """
        Parses a comment {# ... #}.
        """
        # Check for comment start
        if not context.match("COMMENT_START"):
            return None

        # Save position for rollback on error
        saved_position = context.position

        try:
            # Consume {#
            context.consume("COMMENT_START")

            # Collect comment text
            comment_parts = []
            while not context.is_at_end() and not context.match("COMMENT_END"):
                comment_parts.append(context.advance().value)

            if context.is_at_end():
                raise ParserError("Unexpected end of tokens, expected #}", context.current())

            # Consume #}
            context.consume("COMMENT_END")

            comment_text = ''.join(comment_parts)
            return CommentNode(text=comment_text)

        except (ParserError, Exception):
            # Rollback on error
            context.position = saved_position
            return None

    # Helper methods

    def _reconstruct_condition_text(self, tokens: List) -> str:
        """
        Reconstructs condition text from tokens with proper spacing.
        """
        if not tokens:
            return ""

        parts = []
        for i, token in enumerate(tokens):
            # Add space before token if not first and not special character that should stick
            if i > 0:
                prev_token = tokens[i - 1]
                # Do NOT add space before or after colon :
                # Do NOT add space before or after parentheses ( )
                if not (token.value in [":", "(", ")"] or
                       prev_token.value in [":", "(", ")"]):
                    parts.append(" ")

            parts.append(token.value)

        return ''.join(parts)

    def _check_directive_keyword(self, context: ParsingContext, keyword: str) -> bool:
        """
        Checks if the next construct is a directive with the specified keyword.

        Checks sequence: {% [WHITESPACE] keyword ... %}
        """
        if not context.match("DIRECTIVE_START"):
            return False

        # Look ahead, skipping whitespace
        offset = 1
        while True:
            token = context.peek(offset)

            # Reached end
            if token.type == "EOF":
                return False

            # Found non-whitespace token
            if token.type != "WHITESPACE":
                # Check if it's the required keyword
                return token.type == "IDENTIFIER" and token.value.lower() == keyword

            # Skip whitespace
            offset += 1

    def _consume_directive_keyword(self, context: ParsingContext, keyword: str) -> None:
        """
        Consumes a directive with the specified keyword.
        """
        context.consume("DIRECTIVE_START")

        # Collect tokens until %}
        found_keyword = False
        while not context.is_at_end() and not context.match("DIRECTIVE_END"):
            token = context.advance()
            if token.value.lower() == keyword:
                found_keyword = True

        if not found_keyword:
            raise ParserError(f"Expected '{keyword}' directive", context.current())

        context.consume("DIRECTIVE_END")


def get_adaptive_parser_rules(parse_next_node: ParseNextNodeFunc) -> List[ParsingRule]:
    """
    Returns parsing rules for adaptive constructs.

    Args:
        parse_next_node: Functor for recursive parsing of the next node

    Returns:
        List of parsing rules with bound functor
    """
    rules_instance = AdaptiveParserRules(parse_next_node)

    return [
        ParsingRule(
            name="parse_directive",
            priority=PluginPriority.DIRECTIVE,
            parser_func=rules_instance.parse_directive
        ),
        ParsingRule(
            name="parse_comment",
            priority=PluginPriority.COMMENT,
            parser_func=rules_instance.parse_comment
        )
    ]


__all__ = ["AdaptiveParserRules", "ParseNextNodeFunc", "get_adaptive_parser_rules"]

