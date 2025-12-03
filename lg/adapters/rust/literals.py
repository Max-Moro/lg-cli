"""
Rust-specific literal handling using Level 1 early hook pattern.
Handles raw strings, vec! macros, HashMap blocks, and lazy_static! macros.
"""

from __future__ import annotations

import re
from typing import Optional

from ..context import ProcessingContext
from ..optimizations.literals import DefaultLiteralHandler, LiteralInfo
from ..tree_sitter_support import Node


class RustLiteralHandler(DefaultLiteralHandler):
    """
    Handler for Rust-specific literals using Level 1 early hook pattern.

    Handles:
    - Raw strings: r#"..."# (via analyze_literal_structure)
    - vec! macros: vec![...] (Level 1 early hook processing)
    - HashMap blocks: imperative initialization (Level 1 early hook processing)
    - lazy_static! macros: lazy_static! { ... } (Level 1 early hook processing)
    """

    def try_process_literal(
        self,
        context: ProcessingContext,
        node: Node,
        capture_name: str,
        literal_text: str,
        max_tokens: int
    ) -> Optional[str]:
        """Process Rust literals with full control."""
        # Route based on capture type and node type
        if capture_name == "string":
            # Raw strings are handled by analyze_literal_structure
            return None

        elif capture_name == "array":
            # Check for vec! macro
            if node.type == "macro_invocation":
                return self._trim_vec_macro(context, node, literal_text, max_tokens)
            # Check for HashMap initialization block (block from let_declaration)
            elif node.type == "block" and self._is_hashmap_block(node, context):
                return self._trim_hashmap_block(context, node, literal_text, max_tokens)
            return None  # Regular array, use default

        elif capture_name == "object":
            # Check for lazy_static! macro
            if node.type == "macro_invocation":
                return self._trim_lazy_static(context, node, literal_text, max_tokens)
            return None

        return None


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

    def _trim_vec_macro(
        self,
        context: ProcessingContext,
        node: Node,
        literal_text: str,
        max_tokens: int
    ) -> Optional[str]:
        """Handle vec! macro literal trimming (migrate from process_vec_macro_literal)."""
        full_text = literal_text
        token_count = context.tokenizer.count_text(full_text)

        # If does not exceed limit - skip
        if token_count <= max_tokens:
            return None

        # Find token_tree (contains the arguments)
        token_tree = self._get_token_tree_node(node)
        if not token_tree:
            return None

        # Get inner content (between [ ])
        token_tree_text = context.doc.get_node_text(token_tree)

        # Extract content between brackets
        if not (token_tree_text.startswith('[') and token_tree_text.endswith(']')):
            return None

        inner_content = token_tree_text[1:-1].strip()

        # Parse elements (simple comma-separated split)
        elements = [elem.strip() for elem in inner_content.split(',') if elem.strip()]

        if not elements:
            return None

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
                base_indent = self._get_line_indent_at_position(context.raw_text, node.start_byte)
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

        return replacement

    def _trim_lazy_static(
        self,
        context: ProcessingContext,
        node: Node,
        literal_text: str,
        max_tokens: int
    ) -> Optional[str]:
        """Handle lazy_static! macro with HashMap initialization (migrate from process_lazy_static_literal)."""
        full_text = literal_text
        token_count = context.tokenizer.count_text(full_text)

        if token_count <= max_tokens:
            return None

        # Check if contains HashMap pattern
        text = full_text
        if not ("HashMap" in text and ".insert(" in text and text.count(".insert(") >= 3):
            return None

        # Parse structure: lazy_static! { static ref NAME: TYPE = { ... }; }
        # We need to preserve everything except .insert() calls

        lines = full_text.split('\n')
        if len(lines) < 5:
            return None

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
            return None

        # Get base indentation
        base_indent = self._get_line_indent_at_position(context.raw_text, node.start_byte)
        level2_indent = base_indent + "    "
        level3_indent = level2_indent + "    "

        # Build replacement
        replacement_lines = [
            first_line,
            static_line,
            let_line,
            f'{level3_indent}// …',
        ]
        if return_var:
            replacement_lines.append(return_var)
        replacement_lines.extend([second_last, last_line])

        replacement = '\n'.join(replacement_lines)

        return replacement

    def _is_hashmap_block(self, node: Node, context: ProcessingContext) -> bool:
        """Check if block is a HashMap initialization block."""
        text = context.doc.get_node_text(node)
        # Check for HashMap pattern with multiple inserts
        return ("HashMap::new()" in text or "HashMap<" in text) and text.count(".insert(") >= 3

    def _trim_hashmap_block(
        self,
        context: ProcessingContext,
        node: Node,
        literal_text: str,
        max_tokens: int
    ) -> Optional[str]:
        """Handle HashMap initialization block trimming."""
        full_text = literal_text
        token_count = context.tokenizer.count_text(full_text)

        if token_count <= max_tokens:
            return None

        lines = full_text.split('\n')
        if len(lines) < 5:
            return None

        # Extract key parts
        first_line = lines[0]  # {
        last_line = lines[-1]  # }

        # Find the primary let mut declaration and return variable
        primary_let = None
        return_var = None

        for line in lines[1:-1]:
            stripped = line.strip()
            if stripped.startswith("let mut") and "HashMap::new()" in stripped:
                # This is the main HashMap declaration
                if primary_let is None:
                    primary_let = line
            elif stripped and not ".insert(" in stripped and not "let mut" in stripped:
                # Potential return variable (like 'config', 'm', 'map', 'data')
                var_name = stripped.rstrip(';').strip()
                if var_name and not '{' in var_name and not '}' in var_name:
                    # Simple variable name
                    if var_name in ['config', 'm', 'map', 'data'] or (primary_let and var_name in primary_let):
                        return_var = line

        if not primary_let:
            return None

        # Get base indentation from the block's position
        base_indent = self._get_line_indent_at_position(context.raw_text, node.start_byte)
        inner_indent = base_indent + "    "

        # Build replacement
        replacement_lines = [first_line, primary_let, f'{inner_indent}// …']
        if return_var:
            replacement_lines.append(return_var)
        replacement_lines.append(last_line)

        return '\n'.join(replacement_lines)

    def _get_token_tree_node(self, node: Node) -> Optional[Node]:
        """Find token_tree node in macro invocation."""
        for child in node.children:
            if child.type == "token_tree":
                return child
        return None

    def _get_line_indent_at_position(self, text: str, byte_pos: int) -> str:
        """Get indentation of line where byte position is located."""
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
