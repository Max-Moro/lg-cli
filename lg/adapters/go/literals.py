"""Go-specific literal handling using early hook."""

from __future__ import annotations

from typing import Optional

from ..context import ProcessingContext
from ..optimizations.literals import DefaultLiteralHandler
from ..tree_sitter_support import Node


class GoLiteralHandler(DefaultLiteralHandler):
    """
    Handler for Go composite literals.

    Uses early hook (try_process_literal) for full control.
    Handles:
    - Struct literals: Type{field1: value1, field2: value2} - preserves ALL field names
    - Slice literals: []Type{elem1, elem2} - can trim elements
    - Map literals: map[K]V{key1: val1, key2: val2} - can trim pairs
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
        Process Go composite literals with full control.

        Returns trimmed result if this is a composite_literal, None otherwise.
        """
        # Only process @array captures (tree-sitter marks composite literals as arrays)
        if capture_name != "array":
            return None

        # Verify this is actually a composite_literal node
        if node.type != "composite_literal":
            return None

        # Get type and literal_value nodes
        type_node = self._get_type_node(node)
        literal_value_node = self._get_literal_value_node(node)

        if not type_node or not literal_value_node:
            return None

        # Determine if this is a struct literal vs map/slice literal
        # Both use keyed_element, but struct has type_identifier/pointer_type, map has map_type
        is_struct = type_node.type in ("type_identifier", "pointer_type", "struct_type", "qualified_type")

        if is_struct:
            return self._trim_struct_literal(context, node, type_node, literal_value_node, max_tokens)
        else:
            # Map or slice literal - can trim elements
            return self._trim_collection_literal(context, node, type_node, literal_value_node, max_tokens)

    def _trim_struct_literal(
        self,
        context: ProcessingContext,
        node: Node,
        type_node: Node,
        literal_value_node: Node,
        max_tokens: int
    ) -> str:
        """
        Trim Go struct literals while preserving ALL field names.

        CRITICAL: Struct initialization requires all fields or explicit zero values.
        We preserve field names and trim only their values.
        """
        type_text = context.doc.get_node_text(type_node)
        literal_value_text = context.doc.get_node_text(literal_value_node)
        is_multiline = '\n' in literal_value_text

        # Parse keyed elements (field: value pairs)
        keyed_elements = self._get_keyed_elements(literal_value_node, context)

        if not keyed_elements:
            # Empty struct
            return f"{type_text}{{}}"

        # Reserve space for struct wrapper
        overhead = context.tokenizer.count_text(f"{type_text}{{}}")
        content_budget = max(10, max_tokens - overhead)

        # Process fields with budget-aware accumulation
        # For struct literals: ALWAYS preserve all field names (critical for Go semantics)
        processed_fields = []
        accumulated_tokens = 0

        for field_name, field_value in keyed_elements:
            # Calculate tokens for this field (include comma and space for multiline)
            field_text = f"{field_name}: {field_value}"
            field_with_separator = field_text + ", "
            field_tokens = context.tokenizer.count_text(field_with_separator)

            if accumulated_tokens + field_tokens <= content_budget:
                # Field fits completely within budget
                processed_fields.append(field_text)
                accumulated_tokens += field_tokens
            else:
                # Field doesn't fit - use placeholder value
                # IMPORTANT: For Go structs, we MUST include all fields to preserve structure
                placeholder = self._get_field_placeholder(field_value)
                placeholder_text = f"{field_name}: {placeholder}"
                processed_fields.append(placeholder_text)

                # Update accumulated tokens (may exceed budget, but structure is more important)
                placeholder_with_separator = placeholder_text + ", "
                accumulated_tokens += context.tokenizer.count_text(placeholder_with_separator)

        # Format result
        if is_multiline:
            base_indent = self._get_line_indent(context.raw_text, node.start_byte)
            element_indent = base_indent + "\t"

            result_lines = [f"{type_text}{{"]
            for field in processed_fields:
                if not field.endswith(','):
                    field = field + ','
                result_lines.append(f"{element_indent}{field}")
            result_lines.append(f"{base_indent}}}")
            return '\n'.join(result_lines)
        else:
            joined = ", ".join(processed_fields)
            return f"{type_text}{{{joined}}}"

    def _trim_collection_literal(
        self,
        context: ProcessingContext,
        node: Node,
        type_node: Node,
        literal_value_node: Node,
        max_tokens: int
    ) -> str:
        """Trim Go slice/map literals (can remove elements)."""
        type_text = context.doc.get_node_text(type_node)
        literal_value_text = context.doc.get_node_text(literal_value_node)
        is_multiline = '\n' in literal_value_text

        # Parse elements
        inner_content = literal_value_text.strip()
        if inner_content.startswith('{') and inner_content.endswith('}'):
            inner_content = inner_content[1:-1].strip()

        elements = self._parse_elements(inner_content)

        if not elements:
            return f'{type_text}{{"…"}}'

        # Reserve space
        overhead = context.tokenizer.count_text(f'{type_text}{{"…"}}')
        content_budget = max(10, max_tokens - overhead)

        # Select elements within budget
        included = []
        current_tokens = 0

        for elem in elements:
            elem_tokens = context.tokenizer.count_text(elem + ", ")
            if current_tokens + elem_tokens <= content_budget:
                included.append(elem)
                current_tokens += elem_tokens
            else:
                break

        if not included:
            # No elements fit - show only placeholder
            return f'{type_text}{{"…"}}'

        # Check if we included all elements (no trimming needed)
        all_included = len(included) == len(elements)

        # Format result
        if is_multiline:
            base_indent = self._get_line_indent(context.raw_text, node.start_byte)
            element_indent = base_indent + "\t"

            result_lines = [f"{type_text}{{"]
            for elem in included:
                if not elem.endswith(','):
                    elem = elem + ','
                result_lines.append(f"{element_indent}{elem}")

            # Add comment placeholder if content was trimmed
            if not all_included:
                result_lines.append(f"{element_indent}// …")

            result_lines.append(f"{base_indent}}}")
            return '\n'.join(result_lines)
        else:
            joined = ", ".join(included)
            # Add comment placeholder if content was trimmed
            if not all_included:
                return f'{type_text}{{{joined}, /* … */}}'
            else:
                return f'{type_text}{{{joined}}}'

    def _get_field_placeholder(self, field_value: str) -> str:
        """Determine appropriate placeholder for field value based on its type."""
        value = field_value.strip()

        # Map literal
        if value.startswith('map['):
            return 'map[string]interface{}{"…": "…"}'

        # Slice literal
        if value.startswith('[]'):
            return '[]string{"…"}'

        # Numeric
        if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            return '0'

        # Boolean
        if value in ('true', 'false'):
            return 'false'

        # Default: string
        return '"…"'

    def _get_keyed_elements(self, literal_value_node: Node, context: ProcessingContext) -> list[tuple[str, str]]:
        """Extract field name and value pairs from struct literal."""
        keyed_elements = []

        for child in literal_value_node.children:
            if child.type == "keyed_element":
                # keyed_element structure: literal_element : literal_element
                # First literal_element is the field name, second is the value
                elements = [c for c in child.children if c.type == "literal_element"]

                if len(elements) >= 2:
                    field_name = context.doc.get_node_text(elements[0])
                    field_value = context.doc.get_node_text(elements[1])
                    keyed_elements.append((field_name, field_value))

        return keyed_elements

    def _get_type_node(self, composite_node: Node) -> Optional[Node]:
        """Get type child from composite_literal node."""
        for child in composite_node.children:
            if child.type in ("slice_type", "map_type", "struct_type", "type_identifier", "qualified_type", "pointer_type"):
                return child
        return None

    def _get_literal_value_node(self, composite_node: Node) -> Optional[Node]:
        """Get literal_value child from composite_literal node."""
        for child in composite_node.children:
            if child.type == "literal_value":
                return child
        return None

    def _has_keyed_elements(self, literal_value_node: Node) -> bool:
        """Check if literal_value contains keyed_element nodes (struct literals)."""
        for child in literal_value_node.children:
            if child.type == "keyed_element":
                return True
        return False

    def _parse_elements(self, content: str) -> list[str]:
        """Parse elements from literal content."""
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

            if char in ('"', '`') and not in_string:
                in_string = True
                string_char = char
                current_element += char
            elif char == string_char and in_string:
                if i > 0 and content[i-1] != '\\':
                    in_string = False
                    string_char = None
                current_element += char
            elif in_string:
                current_element += char
            elif char in ('{', '[', '('):
                depth += 1
                current_element += char
            elif char in ('}', ']', ')'):
                depth -= 1
                current_element += char
            elif char == ',' and depth == 0:
                if current_element.strip():
                    elements.append(current_element.strip())
                current_element = ""
            else:
                current_element += char

            i += 1

        if current_element.strip():
            elements.append(current_element.strip())

        return elements

    def _get_line_indent(self, text: str, byte_pos: int) -> str:
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
