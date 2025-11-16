"""
Kotlin-specific literal handling.
Includes support for collections (listOf, mapOf, setOf) and string templates.
"""

from __future__ import annotations

from ..context import ProcessingContext
from ..tree_sitter_support import Node, TreeSitterDocument

# Kotlin collection functions that create literal data
KOTLIN_COLLECTION_FUNCTIONS = {
    "listOf", "mutableListOf", "arrayListOf",
    "setOf", "mutableSetOf", "hashSetOf", "linkedSetOf",
    "mapOf", "mutableMapOf", "hashMapOf", "linkedMapOf",
}


def is_collection_literal(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if node is a Kotlin collection function call.

    Args:
        node: Node to check
        doc: Tree-sitter document

    Returns:
        True if this is a listOf/mapOf/setOf call, etc.
    """
    if node.type != "call_expression":
        return False

    # Look for function name (first child identifier)
    for child in node.children:
        if child.type == "identifier":
            func_name = doc.get_node_text(child)
            return func_name in KOTLIN_COLLECTION_FUNCTIONS

    return False


def get_collection_type(node: Node, doc: TreeSitterDocument) -> str:
    """
    Determine collection type (list, map, set).

    Args:
        node: Collection call node
        doc: Tree-sitter document

    Returns:
        Collection type ("list", "map", "set") or "collection"
    """
    for child in node.children:
        if child.type == "identifier":
            func_name = doc.get_node_text(child)
            if "list" in func_name.lower():
                return "list"
            elif "map" in func_name.lower():
                return "map"
            elif "set" in func_name.lower():
                return "set"

    return "collection"


def get_value_arguments_node(node: Node) -> Node | None:
    """
    Find value_arguments node in function call.

    Args:
        node: call_expression node

    Returns:
        value_arguments node or None
    """
    for child in node.children:
        if child.type == "value_arguments":
            return child
    return None


def process_kotlin_collection_literal(
    context: ProcessingContext,
    node: Node,
    max_tokens: int
) -> None:
    """
    Process Kotlin collection literal (listOf/mapOf/setOf).

    Apply smart content trimming while preserving structure.

    Args:
        context: Processing context
        node: call_expression node
        max_tokens: Maximum number of tokens
    """
    # Get full call text
    full_text = context.doc.get_node_text(node)
    token_count = context.tokenizer.count_text(full_text)

    # If does not exceed limit - skip
    if token_count <= max_tokens:
        return

    # Determine collection type
    collection_type = get_collection_type(node, context.doc)

    # Find arguments
    value_args = get_value_arguments_node(node)
    if not value_args:
        return

    # Get all value_argument nodes
    arguments = [child for child in value_args.children if child.type == "value_argument"]

    if not arguments:
        return

    # Calculate how many arguments we can keep
    # Reserve tokens for function name, brackets and placeholder
    func_name_text = full_text.split('(')[0]
    overhead = context.tokenizer.count_text(func_name_text + '("…")')
    content_budget = max(10, max_tokens - overhead)

    # Determine if this is multiline call (before argument selection)
    is_multiline = '\n' in full_text

    # Select arguments that fit in budget
    included_args = []
    current_tokens = 0

    for arg in arguments:
        arg_text = context.doc.get_node_text(arg)
        arg_tokens = context.tokenizer.count_text(arg_text + ", ")

        if current_tokens + arg_tokens <= content_budget:
            included_args.append(arg)
            current_tokens += arg_tokens
        else:
            break

    # If we cannot include any argument - use only placeholder
    if not included_args:
        start_char, end_char = context.doc.get_node_range(node)

        # Form minimal replacement - placeholder only
        if is_multiline:
            # Multiline format
            base_indent = _get_line_indent_at_position(context.raw_text, start_char)
            element_indent = base_indent + "    "
            placeholder = '"…"' if collection_type in ("list", "set") else '"…" to "…"'
            replacement = f'{func_name_text}(\n{element_indent}{placeholder}\n{base_indent})'
        else:
            # Single-line format
            placeholder = '"…"' if collection_type in ("list", "set") else '"…" to "…"'
            replacement = f'{func_name_text}({placeholder})'

        context.editor.add_replacement(
            start_char, end_char, replacement,
            edit_type="literal_trimmed"
        )

        _add_savings_comment(context, node, full_text, replacement, collection_type)

        # Update metrics
        context.metrics.mark_element_removed("literal")
        context.metrics.add_chars_saved(len(full_text) - len(replacement))
        return

    # Form replacement with included arguments and placeholder
    start_char, end_char = context.doc.get_node_range(node)

    if is_multiline:
        # Multiline format
        replacement = _build_multiline_replacement(
            context, node, func_name_text, included_args, collection_type
        )
    else:
        # Single-line format
        replacement = _build_inline_replacement(
            context, included_args, func_name_text, collection_type
        )

    # Apply replacement
    context.editor.add_replacement(
        start_char, end_char, replacement,
        edit_type="literal_trimmed"
    )

    # Add savings comment
    _add_savings_comment(context, node, full_text, replacement, collection_type)

    # Update metrics
    context.metrics.mark_element_removed("literal")
    context.metrics.add_chars_saved(len(full_text) - len(replacement))


def _build_inline_replacement(
    context: ProcessingContext,
    included_args: list[Node],
    func_name: str,
    collection_type: str
) -> str:
    """Build single-line replacement for collection."""
    args_texts = []
    for arg in included_args:
        arg_text = context.doc.get_node_text(arg)
        args_texts.append(arg_text)

    # Add placeholder
    placeholder = '"…"' if collection_type in ("list", "set") else '"…" to "…"'
    args_texts.append(placeholder)

    return f'{func_name}({", ".join(args_texts)})'


def _build_multiline_replacement(
    context: ProcessingContext,
    node: Node,
    func_name: str,
    included_args: list[Node],
    collection_type: str
) -> str:
    """Build multiline replacement for collection with proper indentation."""
    # Base indentation (indentation of line where call starts)
    start_byte = node.start_byte
    base_indent = _get_line_indent_at_position(context.raw_text, start_byte)

    # Element indentation (determine from first argument or add 4 spaces)
    if included_args:
        element_indent = _detect_element_indent(context, included_args[0])
    else:
        element_indent = base_indent + "    "

    # Form lines
    result_lines = [f'{func_name}(']

    for i, arg in enumerate(included_args):
        arg_text = context.doc.get_node_text(arg)
        # Ensure each element has a comma
        if not arg_text.strip().endswith(','):
            arg_text = arg_text + ','
        result_lines.append(f'{element_indent}{arg_text}')

    # Add placeholder (no trailing comma - Kotlin trailing comma is optional)
    placeholder = '"…"' if collection_type in ("list", "set") else '"…" to "…"'
    result_lines.append(f'{element_indent}{placeholder}')
    result_lines.append(f'{base_indent})')

    return '\n'.join(result_lines)


def _get_line_indent_at_position(text: str, byte_pos: int) -> str:
    """
    Get indentation of line where byte position is located.

    Args:
        text: Source text
        byte_pos: Byte position

    Returns:
        String with indentation (spaces/tabs)
    """
    # Find line start
    line_start = text.rfind('\n', 0, byte_pos)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1  # Skip the \n character itself

    # Collect indentation
    indent = ""
    for i in range(line_start, len(text)):
        if text[i] in ' \t':
            indent += text[i]
        else:
            break

    return indent


def _detect_element_indent(context: ProcessingContext, arg_node: Node) -> str:
    """Determine element indentation from argument position."""
    return _get_line_indent_at_position(context.raw_text, arg_node.start_byte)


def _add_savings_comment(
    context: ProcessingContext,
    node: Node,
    original_text: str,
    replacement: str,
    collection_type: str
) -> None:
    """Add token savings comment after literal."""

    # Calculate token savings
    original_tokens = context.tokenizer.count_text(original_text)
    replacement_tokens = context.tokenizer.count_text(replacement)
    saved_tokens = original_tokens - replacement_tokens

    # If no savings - don't add comment
    if saved_tokens <= 0:
        return

    # Determine literal type for comment
    literal_type_name = {
        "list": "array",
        "set": "set",
        "map": "object",
        "collection": "collection"
    }.get(collection_type, "literal")

    # Form comment text
    comment_text = f" // literal {literal_type_name} (−{saved_tokens} tokens)"

    # Find end of literal and place for comment insertion
    end_char = node.end_byte

    # Check what comes after literal
    text_after = context.raw_text[end_char:min(end_char + 100, len(context.raw_text))]

    # Look for end of line or semicolon
    # If closing bracket or comma after literal, insert after it
    for i, char in enumerate(text_after):
        if char in ('\n', '\r'):
            insertion_offset = i
            break
        elif char == ';':
            insertion_offset = i + 1
            break
        elif char == ',':
            insertion_offset = i + 1
            break
        elif char == ')':
            _ = i + 1  # Continue scanning for ; or , after )
            continue
    else:
        # If not found newline in first 100 characters, insert immediately
        insertion_offset = min(20, len(text_after))

    insertion_pos = end_char + insertion_offset

    # Add comment
    context.editor.add_insertion(
        insertion_pos,
        comment_text,
        edit_type="literal_comment"
    )


def process_kotlin_literals(context: ProcessingContext, max_tokens: int | None) -> None:
    """
    Process Kotlin-specific literals (collections).

    This method is called via hook from base LiteralOptimizer
    to process Kotlin-specific constructs.

    Args:
        context: Processing context
        max_tokens: Maximum number of tokens for literal
    """
    if max_tokens is None:
        return

    # Find all function calls, excluding nested ones
    def find_top_level_collection_calls(node: Node, inside_collection: bool = False):
        """
        Find only top-level collection function calls.
        Does not recurse inside found collections to avoid double processing.
        """
        calls = []

        # If this is a collection
        if is_collection_literal(node, context.doc):
            # If we are NOT inside another collection - add it
            if not inside_collection:
                calls.append(node)
                # Now mark that we are inside collection for children
                inside_collection = True

        # Recursively walk children
        for child in node.children:
            calls.extend(find_top_level_collection_calls(child, inside_collection))

        return calls

    # Find only top-level collection literals
    collection_calls = find_top_level_collection_calls(context.doc.root_node)

    # Process each call
    for call_node in collection_calls:
        process_kotlin_collection_literal(context, call_node, max_tokens)
