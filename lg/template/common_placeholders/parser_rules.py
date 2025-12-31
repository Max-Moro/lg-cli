"""
Parsing rules for basic section and template placeholders.

Handles constructs like:
- ${section_name}
- ${tpl:template_name}
- ${ctx:context_name}
- ${@origin:name} (addressed references)
- ${tpl@[origin]:name} (bracketed addressing form)
"""

from __future__ import annotations

from typing import List, Optional

from .nodes import SectionNode, IncludeNode
from ..nodes import TemplateNode
from ..tokens import ParserError
from ..types import PluginPriority, ParsingRule, ParsingContext


def parse_placeholder(context: ParsingContext) -> Optional[TemplateNode]:
    """
    Parses a placeholder ${...}.

    Returns SectionNode or IncludeNode depending on content.
    """
    # Check for placeholder start
    if not context.match("PLACEHOLDER_START"):
        return None

    # Save position for rollback on error
    saved_position = context.position

    try:
        # Consume ${
        context.consume("PLACEHOLDER_START")

        # Parse placeholder content
        node = _parse_placeholder_content(context)

        # Consume }
        context.consume("PLACEHOLDER_END")

        return node

    except (ParserError, Exception):
        # Rollback on error
        context.position = saved_position
        return None


def _parse_placeholder_content(context: ParsingContext) -> TemplateNode:
    """
    Parses placeholder content after ${.

    Determines placeholder type and creates appropriate node.
    """
    # Check for tpl: or ctx: at beginning
    if _check_include_prefix(context):
        return _parse_include_placeholder(context)

    # Check for addressed reference @origin:name
    if context.match("AT"):
        return _parse_addressed_section(context)

    # Regular section
    return _parse_simple_section(context)


def _check_include_prefix(context: ParsingContext) -> bool:
    """Checks if placeholder starts with tpl: or ctx: (including addressed forms tpl@origin:name)."""
    current = context.current()
    if current.type != "IDENTIFIER":
        return False

    # Check that identifier is tpl or ctx
    if current.value not in ["tpl", "ctx"]:
        return False

    # Check token after identifier
    next_token = context.peek(1)
    # Allow both : (local references tpl:name) and @ (addressed references tpl@origin:name)
    return next_token.type in ("COLON", "AT")


def _parse_include_placeholder(context: ParsingContext) -> IncludeNode:
    """
    Parses include placeholder tpl:name or ctx:name.

    Supports addressed forms:
    - tpl@origin:name
    - tpl@[origin]:name
    """
    # Get include type
    kind_token = context.consume("IDENTIFIER")
    kind = kind_token.value

    if kind not in ["tpl", "ctx"]:
        raise ParserError(f"Expected 'tpl' or 'ctx', got '{kind}'", kind_token)

    # Check for addressed reference
    if context.match("AT"):
        # Addressed form: tpl@origin:name or tpl@[origin]:name
        context.advance()  # consume @
        origin, name = _parse_addressed_reference(context)
        return IncludeNode(kind=kind, name=name, origin=origin)

    # Regular form: tpl:name
    context.consume("COLON")
    name = _parse_identifier_path(context)

    return IncludeNode(kind=kind, name=name, origin="self")


def _parse_addressed_section(context: ParsingContext) -> SectionNode:
    """
    Parses addressed section reference @origin:name.
    """
    context.consume("AT")  # consume @
    origin, name = _parse_addressed_reference(context)

    return SectionNode(f"@{origin}:{name}")


def _parse_simple_section(context: ParsingContext) -> SectionNode:
    """
    Parses simple section reference section_name.
    """
    return SectionNode(_parse_identifier_path(context))


def _parse_addressed_reference(context: ParsingContext) -> tuple[str, str]:
    """
    Parses addressed reference origin:name or [origin]:name.

    Returns:
        Tuple (origin, name)
    """
    # Check for bracketed form [origin]:name
    if context.match("LBRACKET"):
        context.advance()  # consume [

        # Parse origin inside brackets (may contain :)
        origin_parts = []
        while not context.match("RBRACKET") and not context.is_at_end():
            token = context.advance()
            origin_parts.append(token.value)

        if context.is_at_end():
            raise ParserError("Expected ']' to close bracketed origin", context.current())

        context.consume("RBRACKET")  # consume ]
        context.consume("COLON")     # consume :

        origin = "".join(origin_parts)
        name = _parse_identifier_path(context)

        return origin, name

    # Regular form origin:name
    origin = _parse_identifier_path(context)
    context.consume("COLON")
    name = _parse_identifier_path(context)

    return origin, name


def _parse_identifier_path(context: ParsingContext) -> str:
    """
    Parses identifier path, which may consist of multiple parts.

    Example: docs/api or simple-name
    """
    if not context.match("IDENTIFIER"):
        raise ParserError("Expected identifier", context.current())

    # Simple version - take one identifier
    token = context.advance()
    return token.value


def get_placeholder_parser_rules() -> List[ParsingRule]:
    """
    Returns parsing rules for placeholders.
    """
    return [
        ParsingRule(
            name="parse_placeholder",
            priority=PluginPriority.PLACEHOLDER,
            parser_func=parse_placeholder
        )
    ]


__all__ = ["get_placeholder_parser_rules"]