"""
Rust-specific literal handling.
Includes support for vec! macro literals.
"""

from __future__ import annotations

import re
from typing import Optional

from ..context import ProcessingContext
from ..optimizations.literals import DefaultLiteralHandler, LiteralInfo
from ..tree_sitter_support import Node, TreeSitterDocument


class RustLiteralHandler(DefaultLiteralHandler):
    """Handler for Rust-specific literal processing."""

    def analyze_literal_structure(
        self, stripped: str, is_multiline: bool, language: str
    ) -> Optional[LiteralInfo]:
        """Analyze Rust raw string literals (r#"..."#, r##"..."##, etc.)."""
        if not stripped.startswith('r'):
            return None  # Not a raw string, use generic logic

        match = re.match(r'^(r#+)"', stripped)
        if not match:
            return None  # Not a valid raw string format

        opening = match.group(0)  # e.g., r#"
        hash_count = len(match.group(1)) - 1  # subtract 'r' from r#
        closing = '"' + '#' * hash_count  # e.g., "#

        start_pos = len(opening)
        end_pos = stripped.rfind(closing)
        if end_pos > start_pos:
            content = stripped[start_pos:end_pos]
            return LiteralInfo("string", opening, closing, content, is_multiline, language)

        return None  # Failed to parse, fallback to generic


def is_vec_macro(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if node is a vec! macro invocation.

    Args:
        node: Node to check
        doc: Tree-sitter document

    Returns:
        True if this is a vec! macro call
    """
    if node.type != "macro_invocation":
        return False

    # Look for macro name (first child is macro field)
    macro_field = node.child_by_field_name("macro")
    if macro_field and macro_field.type == "identifier":
        macro_name = doc.get_node_text(macro_field)
        return macro_name == "vec"

    return False


def get_token_tree_node(node: Node) -> Node | None:
    """
    Find token_tree node in macro invocation.

    Args:
        node: macro_invocation node

    Returns:
        token_tree node or None
    """
    for child in node.children:
        if child.type == "token_tree":
            return child
    return None


def process_vec_macro_literal(
    context: ProcessingContext,
    node: Node,
    max_tokens: int
) -> None:
    """
    Process Rust vec! macro literal.

    Apply smart content trimming while preserving structure.

    Args:
        context: Processing context
        node: macro_invocation node
        max_tokens: Maximum number of tokens
    """
    # Get full macro text
    full_text = context.doc.get_node_text(node)
    token_count = context.tokenizer.count_text(full_text)

    # If does not exceed limit - skip
    if token_count <= max_tokens:
        return

    # Find token_tree (contains the arguments)
    token_tree = get_token_tree_node(node)
    if not token_tree:
        return

    # Get inner content (between [ ])
    token_tree_text = context.doc.get_node_text(token_tree)

    # Extract content between brackets
    if not (token_tree_text.startswith('[') and token_tree_text.endswith(']')):
        return

    inner_content = token_tree_text[1:-1].strip()

    # Parse elements (simple comma-separated split)
    elements = [elem.strip() for elem in inner_content.split(',') if elem.strip()]

    if not elements:
        return

    # Calculate how many elements we can keep
    overhead = context.tokenizer.count_text('vec!["…"]')
    content_budget = max(10, max_tokens - overhead)

    # Determine if this is multiline
    is_multiline = '\n' in full_text

    # Select elements that fit in budget
    included_elements = []
    current_tokens = 0

    for elem in elements:
        elem_tokens = context.tokenizer.count_text(elem + ", ")

        if current_tokens + elem_tokens <= content_budget:
            included_elements.append(elem)
            current_tokens += elem_tokens
        else:
            break

    # If we cannot include any element - use only placeholder
    if not included_elements:
        replacement = 'vec!["…"]' if not is_multiline else 'vec![\n    "…"\n]'
    else:
        # Form replacement with included elements and placeholder
        if is_multiline:
            # Multiline format - preserve indentation
            base_indent = _get_line_indent_at_position(context.raw_text, node.start_byte)
            element_indent = base_indent + "    "

            result_lines = ['vec![']
            for elem in included_elements:
                result_lines.append(f'{element_indent}{elem},')
            result_lines.append(f'{element_indent}"…",')
            result_lines.append(f'{base_indent}]')
            replacement = '\n'.join(result_lines)
        else:
            # Single-line format
            joined = ", ".join(included_elements)
            replacement = f'vec![{joined}, "…"]'

    # Apply replacement
    start_char, end_char = context.doc.get_node_range(node)
    context.editor.add_replacement(
        start_char, end_char, replacement,
        edit_type="literal_trimmed"
    )

    # Add savings comment
    _add_savings_comment(context, node, full_text, replacement)

    # Update metrics
    context.metrics.mark_element_removed("literal")
    context.metrics.add_chars_saved(len(full_text) - len(replacement))


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
        line_start += 1

    # Collect indentation
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

    # Calculate token savings
    original_tokens = context.tokenizer.count_text(original_text)
    replacement_tokens = context.tokenizer.count_text(replacement)
    saved_tokens = original_tokens - replacement_tokens

    # If no savings - don't add comment
    if saved_tokens <= 0:
        return

    # Form comment text
    comment_text = f" // literal array (−{saved_tokens} tokens)"

    # Find end of literal
    end_char = node.end_byte

    # Check what comes after literal
    text_after = context.raw_text[end_char:min(end_char + 100, len(context.raw_text))]

    # Look for end of line or semicolon
    insertion_offset = min(20, len(text_after))
    for i, char in enumerate(text_after):
        if char in ('\n', '\r'):
            insertion_offset = i
            break
        elif char == ';':
            insertion_offset = i + 1
            break

    insertion_pos = end_char + insertion_offset

    # Add comment
    context.editor.add_insertion(
        insertion_pos,
        comment_text,
        edit_type="literal_comment"
    )


def process_rust_literals(context: ProcessingContext, max_tokens: int | None) -> None:
    """
    Process Rust-specific literals (vec! macros).

    This method is called via hook from base LiteralOptimizer
    to process Rust-specific constructs.

    Args:
        context: Processing context
        max_tokens: Maximum number of tokens for literal
    """
    if max_tokens is None:
        return

    # Find all vec! macro calls
    def find_vec_macros(node: Node):
        """Find all vec! macro invocations recursively."""
        macros = []

        if is_vec_macro(node, context.doc):
            macros.append(node)

        # Recursively walk children
        for child in node.children:
            macros.extend(find_vec_macros(child))

        return macros

    # Find all vec! macros
    vec_macros = find_vec_macros(context.doc.root_node)

    # Process each macro
    for macro_node in vec_macros:
        process_vec_macro_literal(context, macro_node, max_tokens)
