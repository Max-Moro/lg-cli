"""
Kotlin function body optimization.
Handles KDoc preservation when stripping function bodies.
"""
from typing import Optional

from ..context import ProcessingContext
from ..optimizations import FunctionBodyOptimizer
from ..tree_sitter_support import Node


def remove_function_body_with_kdoc(
        root_optimizer: FunctionBodyOptimizer,
        context: ProcessingContext,
        func_def: Optional[Node],
        body_node: Node,
        func_type: str
) -> None:
    """
    Remove Kotlin function bodies while preserving KDoc.

    KDoc can be in two places:
    1. Before function as previous sibling (standard case)
    2. Inside function body as first element (non-standard, but possible)

    Args:
        root_optimizer: Universal function body optimizer
        context: Processing context with document access
        func_def: function_declaration node (can be None for lambda)
        body_node: Function body node
        func_type: Function type ("function" or "method")
    """
    # For lambda there is no KDoc, use standard handling
    if func_def is None or func_def.type != "function_declaration":
        return root_optimizer.remove_function_body(context, body_node, func_type)

    # 1. Check for KDoc before function (standard case)
    kdoc_before = _find_kdoc_before_function(func_def, context)

    if kdoc_before is not None:
        # KDoc is outside, just remove body
        # KDoc will be preserved automatically
        return root_optimizer.remove_function_body(context, body_node, func_type)

    # 2. Check for KDoc inside function body
    kdoc_inside = _find_kdoc_in_body(body_node, context)

    if kdoc_inside is None:
        # No KDoc at all - remove body normally
        return root_optimizer.remove_function_body(context, body_node, func_type)

    # KDoc inside body - remove only part after it
    return _remove_function_body_preserve_kdoc(root_optimizer, context, kdoc_inside, body_node, func_type)


def _find_kdoc_before_function(func_node: Node, context: ProcessingContext) -> Optional[Node]:
    """
    Find KDoc comment directly before function.

    KDoc should be block_comment starting with /** and located
    directly before function_declaration.

    Args:
        func_node: function_declaration node
        context: Processing context

    Returns:
        block_comment node with KDoc or None
    """
    parent = func_node.parent
    if not parent:
        return None

    # Find index of current function among siblings
    siblings = parent.children
    func_index = None
    for i, sibling in enumerate(siblings):
        if sibling == func_node:
            func_index = i
            break

    if func_index is None or func_index == 0:
        return None

    # Check previous sibling
    prev_sibling = siblings[func_index - 1]

    if prev_sibling.type == "block_comment":
        # Check if it is KDoc (starts with /**)
        text = context.doc.get_node_text(prev_sibling)
        if text.startswith("/**"):
            return prev_sibling

    return None


def _find_kdoc_in_body(body_node: Node, context: ProcessingContext) -> Optional[Node]:
    """
    Find KDoc comment at start of function body.

    Args:
        body_node: function_body node
        context: Processing context

    Returns:
        block_comment node with KDoc or None
    """
    # Function body in Kotlin is function_body -> block -> statements
    # Look for first block inside function_body
    block_node = None
    for child in body_node.children:
        if child.type == "block":
            block_node = child
            break

    if not block_node:
        return None

    # Look for first block_comment in block
    for child in block_node.children:
        # Skip opening brace {
        if child.type in ("{", "}"):
            continue

        # If first significant node is block_comment, check it
        if child.type == "block_comment":
            text = context.doc.get_node_text(child)
            if text.startswith("/**"):
                return child

        # If we encounter something else - KDoc should be first
        break

    return None


def _remove_function_body_preserve_kdoc(
        root_optimizer: FunctionBodyOptimizer,
        context: ProcessingContext,
        kdoc_node: Node,
        body_node: Node,
        func_type: str
) -> None:
    """
    Remove function body while preserving KDoc inside it.

    Args:
        root_optimizer: Universal function body optimizer
        context: Processing context
        kdoc_node: KDoc comment node
        body_node: Function body node
        func_type: Function type
    """
    # Get ranges
    body_start_char, body_end_char = context.doc.get_node_range(body_node)
    kdoc_end_char = context.doc.byte_to_char_position(kdoc_node.end_byte)

    # Check if there is code after KDoc
    if kdoc_end_char >= body_end_char:
        # No code after KDoc - keep only KDoc and closing brace
        return None

    # Calculate what to remove (from end of KDoc to end of body)
    removal_start = kdoc_end_char
    removal_end = body_end_char

    # Check if there is anything to remove
    removal_start_line = context.doc.get_line_number(removal_start)
    body_end_line = context.doc.get_line_range(body_node)[1]
    lines_removed = max(0, body_end_line - removal_start_line + 1)

    if lines_removed <= 0:
        # Nothing to remove after KDoc
        return None

    # Determine correct indentation based on function type
    indent_prefix = _get_indent_prefix(func_type)

    # Use common helper with proper formatting
    return root_optimizer.apply_function_body_removal(
        context=context,
        start_char=removal_start,
        end_char=removal_end,
        func_type=func_type,
        placeholder_prefix=indent_prefix
    )


def _get_indent_prefix(func_type: str) -> str:
    """
    Determine correct indentation for placeholder based on function type.

    Args:
        func_type: Function type ("method" or "function")

    Returns:
        String with correct indentation for placeholder
    """
    if func_type == "method":
        return "\n        "  # Class method: 8 spaces
    else:
        return "\n    "      # Top-level function: 4 spaces

