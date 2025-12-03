"""Scala-specific literal optimization."""

from __future__ import annotations

import re
from typing import Optional

from ..optimizations.literals import DefaultLiteralHandler, LiteralInfo
from ..context import ProcessingContext
from ..tree_sitter_support import Node


class ScalaLiteralHandler(DefaultLiteralHandler):
    """Handler for Scala interpolated strings (s"...", f"...", raw"...", etc.)."""

    def analyze_literal_structure(
        self,
        stripped: str,
        is_multiline: bool,
        language: str
    ) -> Optional[LiteralInfo]:
        """
        Analyze Scala string interpolation and collection factory calls.

        Scala supports:
        1. String interpolation with prefixes:
           - s"..." or s\"\"\"...\"\"\" - standard interpolation
           - f"..." or f\"\"\"...\"\"\" - formatted interpolation
           - raw"..." or raw\"\"\"...\"\"\" - raw interpolation
           - custom"..." - user-defined interpolators

        2. Collection factory calls:
           - List(...), Map(...), Set(...), Vector(...), etc.

        Args:
            stripped: Stripped literal text
            is_multiline: Whether literal spans multiple lines
            language: Language identifier

        Returns:
            LiteralInfo if this is an interpolated string or collection factory, None otherwise
        """
        # First, check for interpolated strings
        # Pattern: <interpolator><quote>...<quote>
        # Interpolator: identifier starting with letter/underscore
        # Quote: """ or " or '
        match = re.match(r'^([a-zA-Z_]\w*)("""|"|\')', stripped)

        if match:
            interpolator = match.group(1)
            quote_style = match.group(2)

            # Opening includes interpolator prefix
            opening = interpolator + quote_style
            closing = quote_style

            # Extract content between quotes
            content_start = len(opening)
            content_end = stripped.rfind(closing)

            if content_end > content_start:
                content = stripped[content_start:content_end]
                return LiteralInfo("string", opening, closing, content, is_multiline, language)

            # Edge case: empty interpolated string
            if content_end == content_start:
                return LiteralInfo("string", opening, closing, "", is_multiline, language)

        # Second, check for collection factory calls
        # Pattern: CollectionName(...) where CollectionName starts with uppercase
        if '(' in stripped and stripped[0].isupper():
            # This is likely a collection factory call like List(...), Map(...), etc.
            # Return with empty opening/closing so no brackets are added
            return LiteralInfo("array", "", "", stripped, is_multiline, language)

        return None  # Use generic logic

    def trim_array_content(
        self,
        context: ProcessingContext,
        literal_info: LiteralInfo,
        max_tokens: int,
        node: Node
    ) -> Optional[str]:
        """
        Trim Scala collection factory calls.

        Handles patterns like:
        - List("item1", "item2", ...)
        - Map("key1" -> value1, "key2" -> value2, ...)
        - Set("a", "b", "c", ...)
        - Vector(...), Seq(...), etc.
        """
        node_text = context.doc.get_node_text(node).strip()

        # Check if this is a collection factory call
        # Pattern: CollectionName(args)
        if not ('(' in node_text and node_text[0].isupper()):
            # Not a factory call, use default logic
            return None

        # Find the argument list within parentheses
        paren_start = node_text.find('(')
        paren_end = node_text.rfind(')')

        if paren_start == -1 or paren_end == -1:
            return None

        collection_name = node_text[:paren_start]  # "List", "Map", etc.
        method_prefix = node_text[:paren_start + 1]  # "List("
        method_suffix = node_text[paren_end:]  # ")"
        args_text = node_text[paren_start + 1:paren_end]

        # Reserve tokens for collection call structure
        overhead_text = f"{method_prefix}\"…\"{method_suffix}"
        overhead_tokens = context.tokenizer.count_text(overhead_text)
        content_budget = max(10, max_tokens - overhead_tokens)

        # Parse arguments
        args = self._parse_scala_arguments(args_text)

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
            # If no argument fits, include partial first
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
        Trim Scala Map factory calls with arrow syntax.

        Handles: Map("key1" -> value1, "key2" -> value2, ...)
        """
        node_text = context.doc.get_node_text(node).strip()

        # Check for Map pattern
        if not node_text.startswith('Map('):
            return None

        # Reuse array trimming logic
        return self.trim_array_content(context, literal_info, max_tokens, node)

    def _parse_scala_arguments(self, args_text: str) -> list[str]:
        """
        Parse Scala argument list considering nesting and arrow operators.
        """
        if not args_text.strip():
            return []

        arguments = []
        current_arg = ""
        depth = 0
        in_string = False
        string_char = None

        i = 0
        while i < len(args_text):
            char = args_text[i]

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

            i += 1

        # Add last argument
        if current_arg.strip():
            arguments.append(current_arg.strip())

        return arguments
