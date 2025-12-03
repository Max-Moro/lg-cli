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


def is_hashmap_initialization_block(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if node is a block containing HashMap imperative initialization.

    Pattern: block with HashMap::new() followed by multiple .insert() calls

    Args:
        node: Node to check
        doc: Tree-sitter document

    Returns:
        True if this is a HashMap initialization block
    """
    if node.type != "block":
        return False

    # Need at least: let declaration + multiple insert statements
    if len(node.children) < 4:  # {, let, inserts, }
        return False

    # Check first meaningful child is let with HashMap::new()
    has_hashmap_init = False
    insert_count = 0

    for child in node.children:
        if child.type == "let_declaration":
            # Check if value is HashMap::new() or BTreeMap::new()
            value_node = child.child_by_field_name("value")
            if value_node and value_node.type == "call_expression":
                func_node = value_node.child_by_field_name("function")
                if func_node and func_node.type == "scoped_identifier":
                    text = doc.get_node_text(func_node)
                    if "HashMap::new" in text or "BTreeMap::new" in text:
                        has_hashmap_init = True

        elif child.type == "expression_statement":
            # Check if this is a .insert() call
            expr_child = child.children[0] if child.children else None
            if expr_child and expr_child.type == "call_expression":
                func = expr_child.child_by_field_name("function")
                if func and func.type == "field_expression":
                    field = func.child_by_field_name("field")
                    if field and doc.get_node_text(field) == "insert":
                        insert_count += 1

    # Need HashMap init + multiple inserts (at least 3)
    return has_hashmap_init and insert_count >= 3


def process_hashmap_block_literal(
    context: ProcessingContext,
    node: Node,
    max_tokens: int
) -> None:
    """
    Process Rust HashMap initialization block.

    Preserves structure and removes only .insert() calls.

    Args:
        context: Processing context
        node: block node
        max_tokens: Maximum number of tokens
    """
    full_text = context.doc.get_node_text(node)
    token_count = context.tokenizer.count_text(full_text)

    if token_count <= max_tokens:
        return

    # Find the let declaration and return value
    let_line = None
    return_line = None

    for child in node.children:
        if child.type == "let_declaration" and let_line is None:
            # Take FIRST let declaration (main HashMap init)
            let_line = context.doc.get_node_text(child)
        elif child.type == "identifier":
            # This is the return value (last identifier before })
            return_line = context.doc.get_node_text(child)

    if not let_line or not return_line:
        return

    # Get indentation
    base_indent = _get_line_indent_at_position(context.raw_text, node.start_byte)
    inner_indent = base_indent + "    "

    # Build replacement
    replacement_lines = [
        '{',
        f'{inner_indent}{let_line}',
        f'{inner_indent}// …',
        f'{inner_indent}{return_line}',
        f'{base_indent}}}'
    ]
    replacement = '\n'.join(replacement_lines)

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


def is_lazy_static_with_hashmap(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if node is lazy_static! macro containing HashMap initialization.

    Args:
        node: Node to check
        doc: Tree-sitter document

    Returns:
        True if this is lazy_static! with HashMap
    """
    if node.type != "macro_invocation":
        return False

    # Check macro name
    macro_field = node.child_by_field_name("macro")
    if not macro_field or doc.get_node_text(macro_field) != "lazy_static":
        return False

    # Check if contains HashMap pattern
    text = doc.get_node_text(node)
    return "HashMap" in text and ".insert(" in text and text.count(".insert(") >= 3


def process_lazy_static_literal(
    context: ProcessingContext,
    node: Node,
    max_tokens: int
) -> None:
    """
    Process lazy_static! macro with HashMap initialization.

    Preserves macro structure and removes only .insert() calls.

    Args:
        context: Processing context
        node: macro_invocation node
        max_tokens: Maximum number of tokens
    """
    full_text = context.doc.get_node_text(node)
    token_count = context.tokenizer.count_text(full_text)

    if token_count <= max_tokens:
        return

    # Parse structure: lazy_static! { static ref NAME: TYPE = { ... }; }
    # We need to preserve everything except .insert() calls

    lines = full_text.split('\n')
    if len(lines) < 5:
        return

    # Extract key parts
    first_line = lines[0]  # lazy_static! {
    static_line = lines[1] if len(lines) > 1 else ""  # static ref NAME: TYPE = {
    last_line = lines[-1]  # }
    second_last = lines[-2] if len(lines) > 1 else ""  # };

    # Find let and return lines inside the block
    let_line = None
    return_var = None

    for line in lines[2:-2]:
        stripped = line.strip()
        if stripped.startswith("let mut"):
            let_line = line
        elif stripped and not stripped.startswith("m.insert(") and not "insert(" in stripped:
            # Potential return variable
            if stripped.rstrip(';').strip() in ['m', 'config', 'map', 'data']:
                return_var = line

    if not let_line:
        return

    # Get base indentation
    base_indent = _get_line_indent_at_position(context.raw_text, node.start_byte)
    level2_indent = base_indent + "    "
    level3_indent = level2_indent + "    "

    # Build replacement
    replacement_lines = [first_line]
    replacement_lines.append(static_line)
    replacement_lines.append(let_line)
    replacement_lines.append(f'{level3_indent}// …')
    if return_var:
        replacement_lines.append(return_var)
    replacement_lines.append(second_last)
    replacement_lines.append(last_line)

    replacement = '\n'.join(replacement_lines)

    # Apply replacement
    start_char, end_char = context.doc.get_node_range(node)
    context.editor.add_replacement(
        start_char, end_char, replacement,
        edit_type="literal_trimmed"
    )

    # Add savings comment after closing }
    original_tokens = context.tokenizer.count_text(full_text)
    replacement_tokens = context.tokenizer.count_text(replacement)
    saved_tokens = original_tokens - replacement_tokens

    if saved_tokens > 0:
        comment_text = f" // literal object (−{saved_tokens} tokens)"
        end_char_node = node.end_byte
        context.editor.add_insertion(
            end_char_node,
            comment_text,
            edit_type="literal_comment"
        )

    # Update metrics
    context.metrics.mark_element_removed("literal")
    context.metrics.add_chars_saved(len(full_text) - len(replacement))


def process_rust_literals(context: ProcessingContext, max_tokens: int | None) -> None:
    """
    Process Rust-specific literals (vec! macros, HashMap blocks, lazy_static!).

    This method is called via hook from base LiteralOptimizer
    to process Rust-specific constructs.

    Args:
        context: Processing context
        max_tokens: Maximum number of tokens for literal
    """
    if max_tokens is None:
        return

    # Recursive node finder
    def find_nodes_recursive(node: Node, predicate, results=None):
        """Find all nodes matching predicate recursively."""
        if results is None:
            results = []

        if predicate(node):
            results.append(node)

        for child in node.children:
            find_nodes_recursive(child, predicate, results)

        return results

    # Find and process vec! macros
    vec_macros = find_nodes_recursive(
        context.doc.root_node,
        lambda n: is_vec_macro(n, context.doc)
    )
    for macro_node in vec_macros:
        process_vec_macro_literal(context, macro_node, max_tokens)

    # Find and process HashMap initialization blocks
    hashmap_blocks = find_nodes_recursive(
        context.doc.root_node,
        lambda n: is_hashmap_initialization_block(n, context.doc)
    )
    for block_node in hashmap_blocks:
        process_hashmap_block_literal(context, block_node, max_tokens)

    # Find and process lazy_static! with HashMap
    lazy_statics = find_nodes_recursive(
        context.doc.root_node,
        lambda n: is_lazy_static_with_hashmap(n, context.doc)
    )
    for lazy_node in lazy_statics:
        process_lazy_static_literal(context, lazy_node, max_tokens)
