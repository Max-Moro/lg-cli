"""
Java-specific literal handling for collection factory methods.
Uses early hook for full control over factory method processing.
"""

from __future__ import annotations

import re
from typing import Optional

from ..context import ProcessingContext
from ..optimizations.literals import DefaultLiteralHandler
from ..tree_sitter_support import Node


class JavaLiteralHandler(DefaultLiteralHandler):
    """
    Handler for Java collection factory methods.

    Uses early hook (try_process_literal) for full control.
    Handles:
    - List.of(), Set.of(), Stream.of() - simple element lists
    - Map.of(k1, v1, k2, v2) - key-value pairs as arguments
    - Map.ofEntries(Map.entry(...), ...) - entry-based construction
    - Arrays.asList() - legacy list pattern
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
        Process Java collection factory methods with full control.

        Returns trimmed result if this is a factory method, None otherwise.
        """
        # Only process @array captures (tree-sitter marks factory methods as arrays)
        if capture_name != "array":
            return None

        # Check if this is a factory method call
        stripped = literal_text.strip()
        match = re.match(r'^(\w+)\.(\w+)\s*\((.*)\)\s*$', stripped, re.DOTALL)

        if not match:
            return None

        class_name, method_name, args_content = match.groups()

        # Route to appropriate handler
        if class_name in ("List", "Set", "Stream") and method_name == "of":
            return self._trim_simple_factory(
                context, class_name, method_name, args_content,
                max_tokens, node, '"…"'
            )

        if class_name == "Arrays" and method_name == "asList":
            return self._trim_simple_factory(
                context, class_name, method_name, args_content,
                max_tokens, node, '"…"'
            )

        if class_name == "Map" and method_name == "of":
            return self._trim_map_of(
                context, class_name, method_name, args_content,
                max_tokens, node
            )

        if class_name == "Map" and method_name == "ofEntries":
            return self._trim_map_of_entries(
                context, class_name, method_name, args_content,
                max_tokens, node
            )

        # Not a recognized factory method
        return None

    def _trim_simple_factory(
        self,
        context: ProcessingContext,
        class_name: str,
        method_name: str,
        args_content: str,
        max_tokens: int,
        node: Node,
        placeholder: str
    ) -> str:
        """Trim simple factory methods (List.of, Set.of, Arrays.asList)."""
        is_multiline = '\n' in args_content

        # Reserve space
        factory_call = f"{class_name}.{method_name}("
        overhead = context.tokenizer.count_text_cached(f"{factory_call}{placeholder})")
        content_budget = max(10, max_tokens - overhead)

        # Parse arguments
        args = self._parse_arguments(args_content)

        if not args:
            return f"{factory_call}{placeholder})"

        # Select arguments within budget
        included = self._select_within_budget(context, args, content_budget)

        if not included:
            # No complete arguments fit - show only placeholder
            return f"{factory_call}{placeholder})"

        # Format result
        if is_multiline:
            element_indent, base_indent = self._get_indentations(context, node)
            indented = [f"{element_indent}{arg}" for arg in included]
            joined = f",\n".join(indented)
            return f"{factory_call}\n{joined},\n{element_indent}{placeholder}\n{base_indent})"
        else:
            joined = ", ".join(included)
            return f"{factory_call}{joined}, {placeholder})"

    def _trim_map_of(
        self,
        context: ProcessingContext,
        class_name: str,
        method_name: str,
        args_content: str,
        max_tokens: int,
        node: Node
    ) -> str:
        """Trim Map.of(k1, v1, k2, v2, ...) - pair-based arguments."""
        is_multiline = '\n' in args_content

        # Reserve space
        factory_call = f"{class_name}.{method_name}("
        placeholder_pair = '"…", "…"'
        overhead = context.tokenizer.count_text_cached(f"{factory_call}{placeholder_pair})")
        content_budget = max(10, max_tokens - overhead)

        # Parse and group into pairs
        args = self._parse_arguments(args_content)
        pairs = []
        for i in range(0, len(args), 2):
            if i + 1 < len(args):
                pairs.append(f"{args[i]}, {args[i+1]}")

        if not pairs:
            return f"{factory_call}{placeholder_pair})"

        # Select pairs within budget
        included_pairs = self._select_within_budget(context, pairs, content_budget)

        if not included_pairs:
            # No complete pairs fit - show only placeholder
            return f"{factory_call}{placeholder_pair})"

        # Format result
        if is_multiline:
            element_indent, base_indent = self._get_indentations(context, node)
            indented = [f"{element_indent}{pair}" for pair in included_pairs]
            joined = f",\n".join(indented)
            return f"{factory_call}\n{joined},\n{element_indent}{placeholder_pair}\n{base_indent})"
        else:
            joined = ", ".join(included_pairs)
            return f"{factory_call}{joined}, {placeholder_pair})"

    def _trim_map_of_entries(
        self,
        context: ProcessingContext,
        class_name: str,
        method_name: str,
        args_content: str,
        max_tokens: int,
        node: Node
    ) -> str:
        """Trim Map.ofEntries(Map.entry(...), ...) - entry-based construction."""
        is_multiline = '\n' in args_content

        # Reserve space
        factory_call = f"{class_name}.{method_name}("
        placeholder_entry = 'Map.entry("…", "…")'
        overhead = context.tokenizer.count_text_cached(f"{factory_call}{placeholder_entry})")
        content_budget = max(10, max_tokens - overhead)

        # Parse Map.entry() calls
        entries = self._parse_arguments(args_content)

        if not entries:
            return f"{factory_call}{placeholder_entry})"

        # Select entries within budget
        included = self._select_within_budget(context, entries, content_budget)

        if not included:
            # No complete entries fit - show only placeholder
            return f"{factory_call}{placeholder_entry})"

        # Format result
        if is_multiline:
            element_indent, base_indent = self._get_indentations(context, node)
            indented = [f"{element_indent}{entry}" for entry in included]
            joined = f",\n".join(indented)
            return f"{factory_call}\n{joined},\n{element_indent}{placeholder_entry}\n{base_indent})"
        else:
            joined = ", ".join(included)
            return f"{factory_call}{joined}, {placeholder_entry})"

    def _parse_arguments(self, args_text: str) -> list[str]:
        """Parse argument list considering nesting and strings."""
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
            elem_tokens = context.tokenizer.count_text_cached(elem + ", ")
            if current_tokens + elem_tokens <= budget:
                included.append(elem)
                current_tokens += elem_tokens
            else:
                break

        return included

    def _get_indentations(self, context: ProcessingContext, node: Node) -> tuple[str, str]:
        """Determine element and base indentation from node."""
        # Get node text to analyze indentation
        full_text = context.doc.get_node_text(node)
        start_char = node.start_byte

        # Base indent (line where call starts)
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

        # Element indent (from first element in full_text or default)
        element_indent = base_indent + "    "  # Default: 4 spaces
        full_lines = full_text.split('\n')
        if len(full_lines) > 1:
            # Try to detect from second line onwards
            for line in full_lines[1:]:
                stripped = line.strip()
                if stripped and not stripped.startswith(')'):
                    # Extract indent
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
