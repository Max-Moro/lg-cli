"""
Parsing rules for Markdown placeholders.

Handles constructs like:
- ${md:path}
- ${md:path#anchor}
- ${md:path,level:3,strip_h1:true}
- ${md@origin:path}
- ${md@[origin]:path}
- ${md:docs/*}
- ${md:path,if:tag:python}
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from .nodes import MarkdownFileNode
from ..nodes import TemplateNode
from ..tokens import ParserError
from ..types import PluginPriority, ParsingRule, ParsingContext


def parse_md_placeholder(context: ParsingContext) -> Optional[TemplateNode]:
    """
    Parse MD placeholder ${md:...}.

    Returns MarkdownFileNode if MD placeholder is recognized, otherwise None.
    """
    # Check placeholder start
    if not context.match("PLACEHOLDER_START"):
        return None

    # Save position for rollback
    saved_position = context.position

    # Consume ${
    context.consume("PLACEHOLDER_START")

    # Check 'md' prefix via IDENTIFIER
    if not context.match("IDENTIFIER"):
        context.position = saved_position
        return None

    first_token = context.current()
    if first_token.value != 'md':
        context.position = saved_position
        return None

    # Now we are sure this is an MD placeholder - all errors below should propagate!
    context.advance()  # Consume 'md'

    # Parse placeholder content (do NOT catch exceptions - let them propagate)
    node = _parse_md_content(context)

    # Consume }
    context.consume("PLACEHOLDER_END")

    return node


def _parse_md_content(context: ParsingContext) -> MarkdownFileNode:
    """
    Parse MD placeholder content after 'md'.

    Determines type (simple/addressed) and creates MarkdownFileNode.
    """
    # Check if this is addressed inclusion or simple
    if context.match("AT"):
        # Addressed inclusion: md@origin:path[,params...]
        return _parse_addressed_md(context)
    elif context.match("COLON"):
        # Simple inclusion: md:path[,params...]
        return _parse_simple_md(context)
    else:
        raise ParserError(f"Expected ':' or '@' after 'md'", context.current())


def _parse_simple_md(context: ParsingContext) -> MarkdownFileNode:
    """
    Parse simple MD inclusion: md:path[#anchor][,params...]
    """
    context.consume("COLON")  # Consume :

    # Parse path, anchor and parameters
    path, anchor, params = _parse_path_anchor_params(context)

    # Determine if path contains globs
    is_glob = _path_contains_globs(path)

    return MarkdownFileNode(
        path=path,
        origin=None,  # For ordinary md: origin is not set
        heading_level=params.get('level'),
        strip_h1=params.get('strip_h1'),
        anchor=anchor,
        condition=params.get('if'),
        is_glob=is_glob
    )


def _parse_addressed_md(context: ParsingContext) -> MarkdownFileNode:
    """
    Parse addressed MD inclusion: md@origin:path[#anchor][,params...]
    or md@[origin]:path[#anchor][,params...]
    """
    context.consume("AT")  # Consume @

    # Parse origin
    origin = _parse_origin(context)

    # Consume :
    context.consume("COLON")

    # Parse path, anchor and parameters
    path, anchor, params = _parse_path_anchor_params(context)

    # Determine if path contains globs
    is_glob = _path_contains_globs(path)

    return MarkdownFileNode(
        path=path,
        origin=origin,
        heading_level=params.get('level'),
        strip_h1=params.get('strip_h1'),
        anchor=anchor,
        condition=params.get('if'),
        is_glob=is_glob
    )


def _parse_origin(context: ParsingContext) -> str:
    """
    Parse origin in addressed MD placeholder.

    Supports:
    - origin (simple form)
    - [origin] (bracketed form for paths with colons)
    """
    # Check bracketed form
    if context.match("LBRACKET"):
        context.advance()  # Consume [

        # Collect origin inside brackets
        origin_parts = []
        while not context.match("RBRACKET") and not context.is_at_end():
            token = context.advance()
            origin_parts.append(token.value)

        if context.is_at_end():
            raise ParserError("Expected ']' to close bracketed origin", context.current())

        context.consume("RBRACKET")  # Consume ]

        return "".join(origin_parts)

    # Simple form - collect until colon
    origin_parts = []
    while not context.match("COLON") and not context.is_at_end():
        # Stop on special tokens
        if context.match("PLACEHOLDER_END", "COMMA", "HASH"):
            break
        token = context.advance()
        origin_parts.append(token.value)

    if not origin_parts:
        raise ParserError("Empty origin in MD reference", context.current())

    return "".join(origin_parts)


def _parse_path_anchor_params(context: ParsingContext) -> Tuple[str, Optional[str], dict]:
    """
    Parse path, anchor and parameters from current position.

    Format: path[#anchor][,param:value,...]

    Returns:
        Tuple (path, anchor, params_dict)
    """
    # Parse path
    path = _parse_file_path(context)

    # Parse anchor if present
    anchor = None
    if context.match("HASH"):
        context.advance()  # Consume #
        anchor = _parse_anchor(context)

    # Parse parameters if present
    params = {}
    while context.match("COMMA"):
        context.advance()  # Consume ,

        param_name, param_value = _parse_parameter(context)
        params[param_name] = param_value

    return path, anchor, params


def _parse_file_path(context: ParsingContext) -> str:
    """
    Parse file path including support for globs and slashes.

    Returns:
        Path string (e.g., "docs/api" or "docs/*.md")
    """
    path_parts = []

    while not context.is_at_end():
        current = context.current()

        # Stop on special tokens
        if current.type in ("HASH", "COMMA", "PLACEHOLDER_END"):
            break

        # Add token to path
        if current.type in ("IDENTIFIER", "GLOB_STAR", "TEXT"):
            path_parts.append(current.value)
            context.advance()
        elif current.value in ("/", ".", "-", "_"):
            # Allowed characters in path
            path_parts.append(current.value)
            context.advance()
        else:
            # Unexpected token - stop
            break

    if not path_parts:
        raise ParserError("Expected file path", context.current())

    return "".join(path_parts)


def _parse_anchor(context: ParsingContext) -> str:
    """
    Parse anchor after #.

    Returns:
        Anchor string (heading name)
    """
    anchor_parts = []

    while not context.is_at_end():
        current = context.current()

        # Stop on delimiters
        if current.type in ("COMMA", "PLACEHOLDER_END"):
            break

        # Add token to anchor
        anchor_parts.append(current.value)
        context.advance()

    if not anchor_parts:
        raise ParserError("Expected anchor name after '#'", context.current())

    return "".join(anchor_parts).strip()


def _parse_parameter(context: ParsingContext) -> Tuple[str, Any]:
    """
    Parse a single parameter of the form name:value.

    Returns:
        Tuple (param_name, param_value)
    """
    # Skip whitespace before parameter name
    while context.match("WHITESPACE"):
        context.advance()

    # Parse parameter name via IDENTIFIER (including 'if')
    if not context.match("IDENTIFIER"):
        raise ParserError("Expected parameter name", context.current())

    param_token = context.advance()
    param_name = param_token.value

    # Consume colon
    context.consume("COLON")

    # Skip whitespace after colon
    while context.match("WHITESPACE"):
        context.advance()

    # Parse parameter value
    if param_name == 'if':
        # For 'if' collect everything until comma or end as condition
        param_value = _parse_condition_value(context)
    elif param_name == 'level':
        # Numeric parameters
        param_value = _parse_number_value(context)
    elif param_name == 'strip_h1':
        # Boolean parameters
        param_value = _parse_bool_value(context)
    elif param_name == 'anchor':
        # Anchor for partial inclusion
        param_value = _parse_string_value(context)
        if not param_value.strip():
            raise ParserError("Anchor cannot be empty", param_token)
    else:
        # Unknown parameter - raise error
        raise ParserError(
            f"Unknown parameter '{param_name}'. Supported parameters: level, strip_h1, if, anchor",
            param_token
        )

    return param_name, param_value


def _parse_condition_value(context: ParsingContext) -> str:
    """
    Parse condition value for 'if' parameter.

    Collects all tokens until comma or end of placeholder.
    """
    value_parts = []

    while not context.is_at_end():
        current = context.current()

        # Stop on delimiters
        if current.type in ("COMMA", "PLACEHOLDER_END"):
            break

        # Add space before token (if not first and not special)
        if value_parts and current.value not in (":", "(", ")"):
            prev_value = value_parts[-1] if value_parts else ""
            if prev_value not in (":", "(", ")"):
                value_parts.append(" ")

        value_parts.append(current.value)
        context.advance()

    if not value_parts:
        raise ParserError("Expected condition value after 'if:'", context.current())

    return "".join(value_parts)


def _parse_number_value(context: ParsingContext) -> int:
    """Parse numeric parameter value."""
    if not context.match("NUMBER"):
        raise ParserError("Expected number value", context.current())

    token = context.advance()
    try:
        value = int(token.value)
        # Validate range for level (must be between 1 and 6)
        if not 1 <= value <= 6:
            raise ParserError(f"Level must be between 1 and 6, got {value}", token)
        return value
    except ValueError:
        raise ParserError(f"Invalid number: {token.value}", token)


def _parse_bool_value(context: ParsingContext) -> bool:
    """Parse boolean parameter value."""
    current = context.current()

    if current.type == "BOOL_TRUE":
        context.advance()
        return True
    elif current.type == "BOOL_FALSE":
        context.advance()
        return False
    elif current.type == "NUMBER":
        # Numbers 1 and 0 as boolean values
        value = current.value
        context.advance()
        if value == "1":
            return True
        elif value == "0":
            return False
        else:
            raise ParserError(f"Boolean number must be 0 or 1, got '{value}'", current)
    elif current.type == "IDENTIFIER":
        # Fallback for regular identifiers
        value = current.value.lower()
        context.advance()
        if value in ("true", "yes"):
            return True
        elif value in ("false", "no"):
            return False

    raise ParserError(f"Expected boolean value (true/false/1/0/yes/no)", current)


def _parse_string_value(context: ParsingContext) -> str:
    """Parse string parameter value."""
    value_parts = []

    # Collect value until comma or end, including possible colons
    while not context.is_at_end():
        current = context.current()

        # Stop on delimiters
        if current.type in ("COMMA", "PLACEHOLDER_END"):
            break

        value_parts.append(current.value)
        context.advance()

    if not value_parts:
        raise ParserError("Expected parameter value", context.current())

    return "".join(value_parts)


def _path_contains_globs(path: str) -> bool:
    """
    Check if path contains glob patterns.

    Args:
        path: Path to check

    Returns:
        True if path contains glob metacharacters (*, ?, [)
    """
    return '*' in path or '?' in path or '[' in path


def get_md_parser_rules() -> List[ParsingRule]:
    """
    Return parsing rules for MD placeholders.
    """
    return [
        ParsingRule(
            name="parse_md_placeholder",
            priority=PluginPriority.PLACEHOLDER,  # Same priority as regular placeholders
            parser_func=parse_md_placeholder
        )
    ]


__all__ = ["get_md_parser_rules"]
