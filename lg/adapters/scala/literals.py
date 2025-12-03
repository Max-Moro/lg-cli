"""Scala-specific literal optimization using early hook."""

from __future__ import annotations

from typing import Optional

from ..context import ProcessingContext
from ..optimizations.literals import DefaultLiteralHandler
from ..tree_sitter_support import Node


class ScalaLiteralHandler(DefaultLiteralHandler):
    """
    Handler for Scala collection factory calls and interpolated strings.

    Uses early hook (try_process_literal) for full control.
    Handles:
    - Map(...) - arrow operator pairs (key -> value)
    - List/Set/Vector/Seq(...) - simple element lists
    - Interpolated strings - s"...", f"...", raw"...", etc.
    """

    def try_process_literal(
        self,
        context: ProcessingContext,
        node: Node,
        capture_name: str,
        literal_text: str,
        max_tokens: int
    ) -> Optional[str]:
        """
        Process Scala literals with full control.

        Returns trimmed result if recognized pattern, None otherwise.
        """
        # Only process @array captures (tree-sitter marks factory calls as arrays)
        if capture_name != "array":
            return None

        stripped = literal_text.strip()

        # Check for collection factory call pattern: CollectionName(...)
        if not ('(' in stripped and stripped[0].isupper()):
            return None

        # Find collection name and arguments
        paren_start = stripped.find('(')
        collection_name = stripped[:paren_start]

        # Route to appropriate handler
        if collection_name == "Map":
            return self._trim_map_factory(context, stripped, max_tokens, node)
        elif collection_name in ("List", "Set", "Vector", "Seq", "Array"):
            return self._trim_simple_factory(context, collection_name, stripped, max_tokens, node)

        # Not a recognized factory
        return None

    def _trim_map_factory(
        self,
        context: ProcessingContext,
        node_text: str,
        max_tokens: int,
        node: Node
    ) -> str:
        """
        Trim Scala Map(...) factory calls with arrow operators.

        CRITICAL: Arrow pairs (key -> value) must be kept atomic.
        """
        # Extract arguments
        paren_start = node_text.find('(')
        paren_end = node_text.rfind(')')

        if paren_start == -1 or paren_end == -1:
            return node_text

        factory_call = node_text[:paren_start + 1]  # "Map("
        closing = node_text[paren_end:]  # ")"
        args_text = node_text[paren_start + 1:paren_end]

        is_multiline = '\n' in args_text

        # Reserve space for placeholder
        placeholder_pair = '"…" -> "…"'
        overhead = context.tokenizer.count_text(f"{factory_call}{placeholder_pair}{closing}")
        content_budget = max(10, max_tokens - overhead)

        # Parse arrow pairs (CRITICAL: keep key -> value together)
        pairs = self._parse_arrow_pairs(args_text)

        if not pairs:
            return f"{factory_call}{placeholder_pair}{closing}"

        # Select pairs within budget
        included_pairs = self._select_within_budget(context, pairs, content_budget)

        if not included_pairs:
            # No complete pairs fit - show only placeholder
            return f"{factory_call}{placeholder_pair}{closing}"

        # Format result
        if is_multiline:
            element_indent, base_indent = self._get_indentations(context, node)
            indented = [f"{element_indent}{pair}" for pair in included_pairs]
            joined = ",\n".join(indented)
            return f"{factory_call}\n{joined},\n{element_indent}{placeholder_pair}{closing}"
        else:
            joined = ", ".join(included_pairs)
            return f"{factory_call}{joined}, {placeholder_pair}{closing}"

    def _trim_simple_factory(
        self,
        context: ProcessingContext,
        collection_name: str,
        node_text: str,
        max_tokens: int,
        node: Node
    ) -> str:
        """Trim simple collection factories (List, Set, Vector, etc.)."""
        # Extract arguments
        paren_start = node_text.find('(')
        paren_end = node_text.rfind(')')

        if paren_start == -1 or paren_end == -1:
            return node_text

        factory_call = node_text[:paren_start + 1]  # "List("
        closing = node_text[paren_end:]  # ")"
        args_text = node_text[paren_start + 1:paren_end]

        is_multiline = '\n' in args_text

        # Reserve space
        placeholder = '"…"'
        overhead = context.tokenizer.count_text(f"{factory_call}{placeholder}{closing}")
        content_budget = max(10, max_tokens - overhead)

        # Parse arguments
        args = self._parse_arguments(args_text)

        if not args:
            return f"{factory_call}{placeholder}{closing}"

        # Select arguments within budget
        included = self._select_within_budget(context, args, content_budget)

        if not included:
            # No complete arguments fit - show only placeholder
            return f"{factory_call}{placeholder}{closing}"

        # Format result
        if is_multiline:
            element_indent, base_indent = self._get_indentations(context, node)
            indented = [f"{element_indent}{arg}" for arg in included]
            joined = ",\n".join(indented)
            return f"{factory_call}\n{joined},\n{element_indent}{placeholder}{closing}"
        else:
            joined = ", ".join(included)
            return f"{factory_call}{joined}, {placeholder}{closing}"

    def _parse_arrow_pairs(self, args_text: str) -> list[str]:
        """
        Parse Scala Map arguments as arrow pairs.

        CRITICAL: Each pair "key -> value" is treated as atomic unit.
        Comma separates pairs, not individual elements.
        """
        if not args_text.strip():
            return []

        pairs = []
        current_pair = ""
        depth = 0
        in_string = False
        string_char = None

        for i, char in enumerate(args_text):
            # Handle strings
            if char in ('"', "'") and not in_string:
                in_string = True
                string_char = char
                current_pair += char
            elif char == string_char and in_string:
                if i > 0 and args_text[i-1] != '\\':
                    in_string = False
                    string_char = None
                current_pair += char
            elif in_string:
                current_pair += char
            # Handle nesting outside strings
            elif char in ('(', '[', '{'):
                depth += 1
                current_pair += char
            elif char in (')', ']', '}'):
                depth -= 1
                current_pair += char
            elif char == ',' and depth == 0:
                # Found pair separator
                stripped_pair = current_pair.strip()
                # Validate that pair contains arrow operator
                if stripped_pair and '->' in stripped_pair:
                    pairs.append(stripped_pair)
                elif stripped_pair:
                    # Not a valid arrow pair - might be malformed
                    # Include anyway to preserve structure
                    pairs.append(stripped_pair)
                current_pair = ""
            else:
                current_pair += char

        # Add last pair
        stripped_pair = current_pair.strip()
        if stripped_pair and '->' in stripped_pair:
            pairs.append(stripped_pair)
        elif stripped_pair:
            pairs.append(stripped_pair)

        return pairs

    def _parse_arguments(self, args_text: str) -> list[str]:
        """Parse simple argument list (for List, Set, etc.)."""
        if not args_text.strip():
            return []

        arguments = []
        current_arg = ""
        depth = 0
        in_string = False
        string_char = None

        for i, char in enumerate(args_text):
            if char in ('"', "'") and not in_string:
                in_string = True
                string_char = char
                current_arg += char
            elif char == string_char and in_string:
                if i > 0 and args_text[i-1] != '\\':
                    in_string = False
                    string_char = None
                current_arg += char
            elif in_string:
                current_arg += char
            elif char in ('(', '[', '{'):
                depth += 1
                current_arg += char
            elif char in (')', ']', '}'):
                depth -= 1
                current_arg += char
            elif char == ',' and depth == 0:
                if current_arg.strip():
                    arguments.append(current_arg.strip())
                current_arg = ""
            else:
                current_arg += char

        if current_arg.strip():
            arguments.append(current_arg.strip())

        return arguments

    def _select_within_budget(
        self,
        context: ProcessingContext,
        elements: list[str],
        budget: int
    ) -> list[str]:
        """Select elements that fit within token budget."""
        included = []
        current_tokens = 0

        for elem in elements:
            elem_tokens = context.tokenizer.count_text(elem + ", ")
            if current_tokens + elem_tokens <= budget:
                included.append(elem)
                current_tokens += elem_tokens
            else:
                break

        return included

    def _get_indentations(self, context: ProcessingContext, node: Node) -> tuple[str, str]:
        """Determine element and base indentation from node."""
        full_text = context.doc.get_node_text(node)
        start_char = node.start_byte

        # Base indent
        start_line = context.doc.get_line_number(start_char)
        lines = context.raw_text.split('\n')
        base_indent = ""
        if start_line < len(lines):
            line = lines[start_line]
            for char in line:
                if char in ' \t':
                    base_indent += char
                else:
                    break

        # Element indent (from first element or default)
        element_indent = base_indent + "  "  # Scala convention: 2 spaces
        full_lines = full_text.split('\n')
        if len(full_lines) > 1:
            for line in full_lines[1:]:
                if line.strip() and not line.strip().startswith(')'):
                    detected_indent = ""
                    for char in line:
                        if char in ' \t':
                            detected_indent += char
                        else:
                            break
                    if detected_indent:
                        element_indent = detected_indent
                        break

        return element_indent, base_indent

    # Protocol methods (return None to delegate to default)
    def analyze_literal_structure(self, stripped: str, is_multiline: bool, language: str):
        """Analyze Scala interpolated string literals (s"...", f"...", raw"...", etc.)."""
        import re
        from ..optimizations.literals import LiteralInfo

        # Check for interpolation prefix
        # Scala supports: s, f, raw, sql, and custom interpolators
        match = re.match(r'^([a-z]+)(""""|""")', stripped)
        if match:
            # Triple-quoted interpolated string: s"""..."""
            prefix = match.group(1)
            quote_type = match.group(2)
            if quote_type == '""""':  # Malformed - skip
                return None

            opening = f'{prefix}"""'
            closing = '"""'

            start_pos = len(opening)
            end_pos = stripped.rfind(closing)
            if end_pos > start_pos:
                content = stripped[start_pos:end_pos]
                return LiteralInfo("string", opening, closing, content, is_multiline, language)

        # Check for single/double quoted interpolated strings: s"..." or s'...'
        match = re.match(r'^([a-z]+)(["\'])', stripped)
        if match:
            prefix = match.group(1)
            quote_char = match.group(2)

            opening = f'{prefix}{quote_char}'
            closing = quote_char

            start_pos = len(opening)
            end_pos = stripped.rfind(closing)
            if end_pos > start_pos:
                content = stripped[start_pos:end_pos]
                return LiteralInfo("string", opening, closing, content, is_multiline, language)

        return None  # Not an interpolated string, use generic logic
