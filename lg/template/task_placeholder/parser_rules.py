"""
Parsing rules for task placeholders.

Handles:
- ${task}
- ${task:prompt:"default text"}
"""

from __future__ import annotations

from typing import List, Optional

from .nodes import TaskNode
from ..nodes import TemplateNode
from ..tokens import ParserError
from ..types import ParsingRule, ParsingContext


def parse_task_placeholder(context: ParsingContext) -> Optional[TemplateNode]:
    """
    Parses task placeholder ${task} or ${task:prompt:"..."}.
    """
    # Check for placeholder start
    if not context.match("PLACEHOLDER_START"):
        return None

    # Save position for rollback
    saved_position = context.position

    # Consume ${
    context.consume("PLACEHOLDER_START")

    # Skip whitespace
    while context.match("WHITESPACE"):
        context.advance()

    # Check for 'task' keyword via IDENTIFIER
    if not context.match("IDENTIFIER"):
        context.position = saved_position
        return None

    task_token = context.current()
    if task_token.value != "task":
        context.position = saved_position
        return None

    # Now we are sure this is a task placeholder
    context.advance()  # Consume 'task'

    # Skip whitespace
    while context.match("WHITESPACE"):
        context.advance()

    # Check for presence of :prompt:"..."
    default_prompt = None
    if context.match("COLON"):
        context.advance()  # Consume :

        # Skip whitespace
        while context.match("WHITESPACE"):
            context.advance()

        # Expect 'prompt'
        if not context.match("IDENTIFIER"):
            raise ParserError("Expected 'prompt' after ':' in task placeholder", context.current())

        prompt_token = context.current()
        if prompt_token.value != "prompt":
            raise ParserError("Expected 'prompt' after ':' in task placeholder", prompt_token)
        context.advance()

        # Skip whitespace
        while context.match("WHITESPACE"):
            context.advance()

        # Expect :
        if not context.match("COLON"):
            raise ParserError("Expected ':' after 'prompt' in task placeholder", context.current())
        context.advance()

        # Skip whitespace
        while context.match("WHITESPACE"):
            context.advance()

        # Expect string literal
        if not context.match("STRING_LITERAL"):
            raise ParserError("Expected string literal after 'prompt:' in task placeholder", context.current())

        string_token = context.advance()
        # Parse string literal (remove quotes and process escape sequences)
        default_prompt = _parse_string_literal(string_token.value)

        # Skip whitespace
        while context.match("WHITESPACE"):
            context.advance()

    # Consume }
    if not context.match("PLACEHOLDER_END"):
        raise ParserError("Expected '}' to close task placeholder", context.current())
    context.consume("PLACEHOLDER_END")
    
    return TaskNode(default_prompt=default_prompt)


def _parse_string_literal(literal: str) -> str:
    """
    Parses string literal, removing quotes and processing escape sequences.

    Args:
        literal: String like "text" with possible escape sequences

    Returns:
        Processed string
    """
    # Remove surrounding quotes
    if literal.startswith('"') and literal.endswith('"'):
        literal = literal[1:-1]

    # Process escape sequences
    result = []
    i = 0
    while i < len(literal):
        if literal[i] == '\\' and i + 1 < len(literal):
            next_char = literal[i + 1]
            if next_char == 'n':
                result.append('\n')
            elif next_char == 't':
                result.append('\t')
            elif next_char == 'r':
                result.append('\r')
            elif next_char == '\\':
                result.append('\\')
            elif next_char == '"':
                result.append('"')
            else:
                # Unknown escape sequence - keep as is
                result.append('\\')
                result.append(next_char)
            i += 2
        else:
            result.append(literal[i])
            i += 1

    return ''.join(result)


def get_task_parser_rules() -> List[ParsingRule]:
    """
    Returns parsing rules for task placeholders.

    Priority higher than normal PLACEHOLDER (95 > 90) so
    task placeholders are processed before general sections.
    """
    return [
        ParsingRule(
            name="parse_task_placeholder",
            priority=95,  # Higher than PLACEHOLDER (90), but lower than DIRECTIVE (100)
            parser_func=parse_task_placeholder
        )
    ]


__all__ = ["get_task_parser_rules"]