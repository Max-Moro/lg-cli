"""
Go-specific literal handling.
Handles composite_literal properly to preserve type information.
"""

from __future__ import annotations

from ..context import ProcessingContext
from ..tree_sitter_support import Node, TreeSitterDocument


def get_literal_value_node(composite_node: Node) -> Node | None:
    """
    Get literal_value child from composite_literal node.

    Args:
        composite_node: composite_literal node

    Returns:
        literal_value node or None
    """
    for child in composite_node.children:
        if child.type == "literal_value":
            return child
    return None


def get_type_node(composite_node: Node) -> Node | None:
    """
    Get type child from composite_literal node.

    Args:
        composite_node: composite_literal node

    Returns:
        Type node (slice_type, map_type, etc.) or None
    """
    for child in composite_node.children:
        if child.type in ("slice_type", "map_type", "struct_type", "type_identifier", "qualified_type"):
            return child
    return None


def has_keyed_elements(literal_value_node: Node) -> bool:
    """
    Check if literal_value contains keyed_element nodes (struct literals).

    Args:
        literal_value_node: literal_value node

    Returns:
        True if contains keyed_element (struct literal), False otherwise (slice/map)
    """
    for child in literal_value_node.children:
        if child.type == "keyed_element":
            return True
    return False


def process_go_composite_literal(
    context: ProcessingContext,
    composite_node: Node,
    max_tokens: int
) -> None:
    """
    Process Go composite_literal properly.

    Only processes the literal_value part, preserving type information.

    Args:
        context: Processing context
        composite_node: composite_literal node
        max_tokens: Maximum number of tokens
    """
    # Get full composite text
    full_text = context.doc.get_node_text(composite_node)
    token_count = context.tokenizer.count_text(full_text)

    # If does not exceed limit - skip
    if token_count <= max_tokens:
        return

    # Get type and literal_value nodes
    type_node = get_type_node(composite_node)
    literal_value_node = get_literal_value_node(composite_node)

    if not type_node or not literal_value_node:
        return

    # Determine if this is a struct literal (has keyed_element)
    is_struct_literal = has_keyed_elements(literal_value_node)

    # Get texts
    type_text = context.doc.get_node_text(type_node)
    literal_value_text = context.doc.get_node_text(literal_value_node)

    # Determine if this is multiline
    is_multiline = '\n' in literal_value_text

    # Parse elements from literal_value (skip opening and closing braces)
    inner_content = literal_value_text.strip()
    if inner_content.startswith('{') and inner_content.endswith('}'):
        inner_content = inner_content[1:-1].strip()

    # Parse elements
    elements = _parse_elements(inner_content)

    if not elements:
        return

    # Calculate budget
    overhead = context.tokenizer.count_text(f'{type_text}{{"…"}}')
    content_budget = max(10, max_tokens - overhead)

    # Select elements that fit
    included_elements = []
    current_tokens = 0

    for elem in elements:
        elem_tokens = context.tokenizer.count_text(elem + ", ")

        if current_tokens + elem_tokens <= content_budget:
            included_elements.append(elem)
            current_tokens += elem_tokens
        else:
            break

    # Build replacement
    if is_struct_literal:
        # For struct literals, DON'T add placeholder element - just truncate
        # Struct literals need field names, can't use "…" placeholder
        if not included_elements:
            # No elements fit - show just type with empty body
            if is_multiline:
                base_indent = _get_line_indent_at_position(context.raw_text, composite_node.start_byte)
                replacement = f'{type_text}{{\n{base_indent}}}'
            else:
                replacement = f'{type_text}{{}}'
        else:
            # Show included elements without placeholder
            if is_multiline:
                base_indent = _get_line_indent_at_position(context.raw_text, composite_node.start_byte)
                element_indent = base_indent + "\t"

                result_lines = [f'{type_text}{{']
                for elem in included_elements:
                    # Ensure comma
                    if not elem.strip().endswith(','):
                        elem = elem + ','
                    result_lines.append(f'{element_indent}{elem}')
                result_lines.append(f'{base_indent}}}')
                replacement = '\n'.join(result_lines)
            else:
                joined = ", ".join(included_elements)
                replacement = f'{type_text}{{{joined}}}'
    else:
        # For slice/map literals, add "…" placeholder element
        if not included_elements:
            # Only placeholder
            if is_multiline:
                base_indent = _get_line_indent_at_position(context.raw_text, composite_node.start_byte)
                element_indent = base_indent + "\t"
                replacement = f'{type_text}{{\n{element_indent}"…",\n{base_indent}}}'
            else:
                replacement = f'{type_text}{{"…"}}'
        else:
            # Included elements + placeholder
            if is_multiline:
                base_indent = _get_line_indent_at_position(context.raw_text, composite_node.start_byte)
                element_indent = base_indent + "\t"

                result_lines = [f'{type_text}{{']
                for elem in included_elements:
                    # Ensure comma
                    if not elem.strip().endswith(','):
                        elem = elem + ','
                    result_lines.append(f'{element_indent}{elem}')
                result_lines.append(f'{element_indent}"…",')
                result_lines.append(f'{base_indent}}}')
                replacement = '\n'.join(result_lines)
            else:
                joined = ", ".join(included_elements)
                replacement = f'{type_text}{{{joined}, "…"}}'

    # Apply replacement
    start_char, end_char = context.doc.get_node_range(composite_node)
    context.editor.add_replacement(
        start_char, end_char, replacement,
        edit_type="literal_trimmed"
    )

    # Add savings comment
    _add_savings_comment(context, composite_node, full_text, replacement)

    # Update metrics
    context.metrics.mark_element_removed("literal")
    context.metrics.add_chars_saved(len(full_text) - len(replacement))


def _parse_elements(content: str) -> list[str]:
    """
    Parse elements from literal content.
    Simple comma-separated parsing with nesting awareness.
    """
    if not content.strip():
        return []

    elements = []
    current_element = ""
    depth = 0
    in_string = False
    string_char = None

    i = 0
    while i < len(content):
        char = content[i]

        # Handle strings
        if char in ('"', '`') and not in_string:
            in_string = True
            string_char = char
            current_element += char
        elif char == string_char and in_string:
            # Check for escaping
            if i > 0 and content[i-1] != '\\':
                in_string = False
                string_char = None
            current_element += char
        elif in_string:
            current_element += char
        # Handle nesting outside strings
        elif char in ('{', '[', '('):
            depth += 1
            current_element += char
        elif char in ('}', ']', ')'):
            depth -= 1
            current_element += char
        elif char == ',' and depth == 0:
            # Found top-level separator
            if current_element.strip():
                elements.append(current_element.strip())
            current_element = ""
        else:
            current_element += char

        i += 1

    # Add last element
    if current_element.strip():
        elements.append(current_element.strip())

    return elements


def _get_line_indent_at_position(text: str, byte_pos: int) -> str:
    """Get indentation of line where byte position is located."""
    line_start = text.rfind('\n', 0, byte_pos)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1

    indent = ""
    for i in range(line_start, len(text)):
        if text[i] in ' \t':
            indent += text[i]
        else:
            break

    return indent


def _add_savings_comment(
    context: ProcessingContext,
    node: Node,
    original_text: str,
    replacement: str
) -> None:
    """Add token savings comment after literal."""

    original_tokens = context.tokenizer.count_text(original_text)
    replacement_tokens = context.tokenizer.count_text(replacement)
    saved_tokens = original_tokens - replacement_tokens

    if saved_tokens <= 0:
        return

    comment_text = f" // literal array (−{saved_tokens} tokens)"

    end_char = node.end_byte
    text_after = context.raw_text[end_char:min(end_char + 100, len(context.raw_text))]

    insertion_offset = 0
    for i, char in enumerate(text_after):
        if char in ('\n', '\r'):
            insertion_offset = i
            break
    else:
        insertion_offset = min(20, len(text_after))

    insertion_pos = end_char + insertion_offset

    context.editor.add_insertion(
        insertion_pos,
        comment_text,
        edit_type="literal_comment"
    )


def process_go_literals(context: ProcessingContext, max_tokens: int | None) -> None:
    """
    Process Go-specific literals (composite_literal).

    This method is called via hook from base LiteralOptimizer
    to process Go-specific constructs.

    Args:
        context: Processing context
        max_tokens: Maximum number of tokens for literal
    """
    if max_tokens is None:
        return

    # Find all composite_literal nodes
    def find_composite_literals(node: Node):
        """Find all composite_literal nodes recursively."""
        literals = []

        if node.type == "composite_literal":
            literals.append(node)

        # Recursively walk children
        for child in node.children:
            literals.extend(find_composite_literals(child))

        return literals

    # Find all composite literals
    composite_literals = find_composite_literals(context.doc.root_node)

    # Process each literal
    for lit_node in composite_literals:
        process_go_composite_literal(context, lit_node, max_tokens)
