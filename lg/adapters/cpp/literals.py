"""C++-specific literal optimization."""

import re
from typing import Optional
from tree_sitter import Node
from ..context import ProcessingContext
from ..optimizations.literals import (
    DefaultLiteralHandler,
    LiteralInfo,
    LiteralOptimizer
)


# noinspection PyProtectedMember
class CppLiteralHandler(DefaultLiteralHandler):
    """Handler for C++ struct arrays and nested initializers."""

    def __init__(self, optimizer: LiteralOptimizer):
        """Initialize handler with reference to root optimizer."""
        self.optimizer = optimizer

    def trim_array_content(
        self,
        context: ProcessingContext,
        literal_info: LiteralInfo,
        max_tokens: int,
        node: Node
    ) -> Optional[str]:
        """Trim arrays, suppressing placeholder for struct arrays and numeric arrays."""
        # Get content from node
        content = context.doc.get_node_text(node)[1:-1]  # Remove outer brackets

        # Use optimizer's element parser (delegation pattern)
        elements = self.optimizer._parse_elements(content)  # noinspection PyProtectedMemberInspection

        # Check if struct array (first element starts with {)
        is_struct_array = elements and elements[0].strip().startswith('{')

        # Check if numeric array (all elements are numbers)
        is_numeric_array = all(elem.strip().rstrip(',').replace('-', '').replace('.', '').isdigit()
                               for elem in elements if elem.strip())

        if not is_struct_array and not is_numeric_array:
            return None  # Use generic logic for regular arrays

        # For numeric arrays, suppress placeholder completely
        if is_numeric_array:
            # Just trim without adding string placeholder
            overhead_text = f"{literal_info.opening}{literal_info.closing}"
            overhead_tokens = context.tokenizer.count_text(overhead_text)
            content_budget = max(1, max_tokens - overhead_tokens)

            included_elements = self.optimizer._select_elements_within_budget(context, elements, content_budget)

            if not included_elements:
                return ""  # Empty array content

            # Form result without placeholder for numeric arrays
            if literal_info.is_multiline:
                element_indent, base_indent = self.optimizer._get_base_indentations(context.doc, node, context.raw_text)
                indented_elements = [f"{element_indent}{element}" for element in included_elements]
                joined = f",\n".join(indented_elements)
                return f"\n{joined},\n{base_indent}"
            else:
                joined = ", ".join(included_elements)
                return joined

        # Custom trimming without placeholder for struct arrays
        overhead_text = f"{literal_info.opening}{literal_info.closing}"
        overhead_tokens = context.tokenizer.count_text(overhead_text)
        content_budget = max(1, max_tokens - overhead_tokens)

        # Select elements within budget (delegation pattern)
        included_elements = self.optimizer._select_elements_within_budget(context, elements, content_budget)

        if not included_elements:
            # No elements fit - try to include first element with nested content trimmed
            if not elements:
                return "{}"

            first_element = elements[0]
            # If first element is a nested struct (contains braces), try to trim its nested content
            if '{' in first_element:
                # Try to create a version with empty nested content
                # Pattern: {"key", {...}} -> {"key", {}}
                # Find the nested structure and replace with {}
                trimmed = re.sub(r'\{[^{}]*(?:\{[^{}]*}[^{}]*)*}', '{}', first_element, count=1)
                trimmed_tokens = context.tokenizer.count_text(trimmed)

                if trimmed_tokens <= content_budget:
                    # Trimmed version fits!
                    if literal_info.is_multiline:
                        element_indent, base_indent = self.optimizer._get_base_indentations(context.doc, node, context.raw_text)
                        return f"\n{element_indent}{trimmed},\n{base_indent}"
                    else:
                        return trimmed

            # Still doesn't fit, return empty nested structure
            return "{}"

        # Form result without placeholder
        if literal_info.is_multiline:
            element_indent, base_indent = self.optimizer._get_base_indentations(context.doc, node, context.raw_text)
            indented_elements = [f"{element_indent}{element}" for element in included_elements]
            joined = f",\n".join(indented_elements)
            return f"\n{joined},\n{base_indent}"
        else:
            joined = ", ".join(included_elements)
            return joined

    def trim_object_content(
        self,
        context: ProcessingContext,
        literal_info: LiteralInfo,
        max_tokens: int,
        node: Node
    ) -> Optional[str]:
        """Trim objects, ensuring proper closing braces for nested initializers."""
        content = literal_info.content.strip()

        # Parse key-value pairs
        pairs = self.optimizer._parse_elements(content)

        # Check if nested initializer (has nested braces)
        is_nested_initializer = pairs and any('{' in pair or '[' in pair for pair in pairs)

        if not is_nested_initializer:
            return None  # Use generic logic for regular objects

        # Custom trimming for nested initializers (no placeholder, ensure closing braces)
        # Reserve space for boundaries (no placeholder for nested initializers)
        overhead = f"{literal_info.opening}{literal_info.closing}"
        overhead_tokens = context.tokenizer.count_text(overhead)
        content_budget = max(10, max_tokens - overhead_tokens)

        # Find pairs that fit in budget
        included_pairs = self.optimizer._select_elements_within_budget(context, pairs, content_budget)

        if not included_pairs:
            # No pairs fit - for nested initializers, return empty nested structure
            # This will be wrapped in outer braces to form {{}}
            if literal_info.is_multiline:
                element_indent, base_indent = self.optimizer._get_base_indentations(context.doc, node, context.raw_text)
                result = f"\n{element_indent}{{}}\n{base_indent}"
            else:
                result = "{}"
        else:
            # Form result without placeholder
            if literal_info.is_multiline:
                element_indent, base_indent = self.optimizer._get_base_indentations(context.doc, node, context.raw_text)
                indented_pairs = [f"{element_indent}{pair}" for pair in included_pairs]
                joined = f",\n".join(indented_pairs)
                result = f"\n{joined},\n{base_indent}"
            else:
                joined = ", ".join(included_pairs)
                result = joined

        # Ensure proper closing braces
        open_braces = result.count('{')
        close_braces = result.count('}')

        if open_braces > close_braces:
            missing_braces = open_braces - close_braces
            result += '}' * missing_braces

        return result
