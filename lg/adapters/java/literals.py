"""Java-specific literal optimization."""

from __future__ import annotations

from typing import Optional

from ..optimizations.literals import DefaultLiteralHandler, LiteralInfo
from ..context import ProcessingContext
from ..tree_sitter_support import Node


class JavaLiteralHandler(DefaultLiteralHandler):
    """Handler for Java collection factory methods (Map.of, List.of, etc.)."""

    def analyze_literal_structure(
        self, stripped: str, is_multiline: bool, language: str
    ) -> Optional[LiteralInfo]:
        """
        Detect Java collection factory methods and return appropriate structure info.

        For method invocations like Map.of(...), List.of(...), we don't want
        to add square brackets - the opening/closing should be empty strings
        or match the actual method call syntax.
        """
        # Check if this looks like a collection factory method
        # Pattern: ClassName.methodName(...)
        if '.' in stripped and '(' in stripped and stripped[0].isupper():
            # This is a method invocation like Map.of(...)
            # Extract the content (the part inside parentheses)
            paren_start = stripped.find('(')
            paren_end = stripped.rfind(')')

            if paren_start != -1 and paren_end != -1:
                content = stripped[paren_start + 1:paren_end]
                # Return with empty opening/closing so no brackets are added
                return LiteralInfo("array", "", "", stripped, is_multiline, language)

        return None  # Use default analysis

    def trim_array_content(
        self,
        context: ProcessingContext,
        literal_info: LiteralInfo,
        max_tokens: int,
        node: Node
    ) -> Optional[str]:
        """
        Trim Java collection factory method calls.

        Handles patterns like:
        - Map.of("key1", value1, "key2", value2, ...)
        - List.of("item1", "item2", "item3", ...)
        - Set.of("a", "b", "c", ...)
        - Map.ofEntries(Map.entry(...), ...)

        These are method invocations, not array literals, so we need
        to preserve method call syntax.
        """
        # Get the full node text to detect if this is a method invocation
        node_text = context.doc.get_node_text(node).strip()

        # Check if this looks like a collection factory method
        # Pattern: ClassName.methodName(args)
        if not ('.' in node_text and '(' in node_text):
            # Not a method call, use default logic
            return None

        # For method invocations, we need to preserve the method call structure
        # Example: Map.of("a", 1, "b", 2) -> Map.of("a", 1, "…")

        # Find the argument list within parentheses
        paren_start = node_text.find('(')
        paren_end = node_text.rfind(')')

        if paren_start == -1 or paren_end == -1:
            return None  # Malformed, use default

        method_prefix = node_text[:paren_start + 1]  # "Map.of("
        method_suffix = node_text[paren_end:]  # ")"
        args_text = node_text[paren_start + 1:paren_end]  # argument content

        # Reserve tokens for method call structure
        overhead_text = f"{method_prefix}\"…\"{method_suffix}"
        overhead_tokens = context.tokenizer.count_text(overhead_text)
        content_budget = max(10, max_tokens - overhead_tokens)

        # Parse arguments (simplified - split by commas at depth 0)
        args = self._parse_arguments(args_text)

        # Select arguments that fit in budget
        included_args = []
        current_tokens = 0

        for arg in args:
            arg_tokens = context.tokenizer.count_text(arg + ", ")
            if current_tokens + arg_tokens <= content_budget:
                included_args.append(arg)
                current_tokens += arg_tokens
            else:
                break

        if not included_args:
            # If no argument fits, include partial first argument
            first_arg = args[0] if args else '""'
            trimmed_arg = context.tokenizer.truncate_to_tokens(first_arg, content_budget - 5)
            return f"{method_prefix}{trimmed_arg}, \"…\"{method_suffix}"

        # Build result
        joined = ", ".join(included_args)
        return f"{method_prefix}{joined}, \"…\"{method_suffix}"

    def trim_object_content(
        self,
        context: ProcessingContext,
        literal_info: LiteralInfo,
        max_tokens: int,
        node: Node
    ) -> Optional[str]:
        """
        Trim Java Map factory method calls (Map.ofEntries with Map.entry).

        Similar to trim_array_content but for Map.ofEntries pattern.
        """
        node_text = context.doc.get_node_text(node).strip()

        # Check for Map.ofEntries pattern
        if 'Map.ofEntries' not in node_text and 'Map.of' not in node_text:
            return None  # Use default logic

        # Reuse array trimming logic since Map.of/ofEntries have similar structure
        return self.trim_array_content(context, literal_info, max_tokens, node)

    def _parse_arguments(self, args_text: str) -> list[str]:
        """
        Parse argument list considering nesting depth.
        Splits by comma at depth 0 only.
        """
        if not args_text.strip():
            return []

        arguments = []
        current_arg = ""
        depth = 0
        in_string = False
        string_char = None

        for i, char in enumerate(args_text):
            # Handle strings
            if char in ('"', "'") and not in_string:
                in_string = True
                string_char = char
                current_arg += char
            elif char == string_char and in_string:
                # Check for escaping
                if i > 0 and args_text[i-1] != '\\':
                    in_string = False
                    string_char = None
                current_arg += char
            elif in_string:
                current_arg += char
            # Handle nesting outside strings
            elif char in ('(', '[', '{'):
                depth += 1
                current_arg += char
            elif char in (')', ']', '}'):
                depth -= 1
                current_arg += char
            elif char == ',' and depth == 0:
                # Found top-level separator
                if current_arg.strip():
                    arguments.append(current_arg.strip())
                current_arg = ""
            else:
                current_arg += char

        # Add last argument
        if current_arg.strip():
            arguments.append(current_arg.strip())

        return arguments
