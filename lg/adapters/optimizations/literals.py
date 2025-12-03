"""
Literal optimization.
Processes and trims literal data (strings, arrays, objects) with simplified logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol

from ..code_model import LiteralConfig
from ..context import ProcessingContext
from ..tree_sitter_support import Node, TreeSitterDocument


class LiteralHandler(Protocol):
    """Protocol for customizing literal processing operations."""

    def try_process_literal(
        self,
        context: ProcessingContext,
        node: Node,
        capture_name: str,
        literal_text: str,
        max_tokens: int
    ) -> Optional[str]:
        """
        Early hook for FULL control over literal processing.

        Called BEFORE any analyze/trim logic. If returns non-None,
        that result is used and standard processing is skipped.

        Args:
            context: Processing context
            node: Tree-sitter node
            capture_name: Query capture name (@array, @string, etc.)
            literal_text: Original literal text
            max_tokens: Token budget

        Returns:
            Trimmed content if handler processes completely, None to continue standard path
        """
        ...

    def analyze_literal_structure(
        self,
        stripped: str,
        is_multiline: bool,
        language: str
    ) -> Optional[LiteralInfo]:
        """
        Analyze literal structure for special formats (e.g., Rust raw strings, template literals).

        Args:
            stripped: Stripped literal text
            is_multiline: Whether literal spans multiple lines
            language: Language identifier

        Returns:
            LiteralInfo if custom analysis applied, None to use generic logic
        """
        ...

    def trim_string_content(
        self,
        context: ProcessingContext,
        literal_info: LiteralInfo,
        max_tokens: int
    ) -> Optional[str]:
        """
        Trim string literal content with language-specific logic.

        Args:
            context: Processing context
            literal_info: Analyzed literal information
            max_tokens: Token budget

        Returns:
            Trimmed string if custom logic applied, None to use generic logic
        """
        ...

    def trim_array_content(
        self,
        context: ProcessingContext,
        literal_info: LiteralInfo,
        max_tokens: int,
        node: Node
    ) -> Optional[str]:
        """
        Trim array literal content with language-specific logic.

        Args:
            context: Processing context
            literal_info: Analyzed literal information
            max_tokens: Token budget
            node: Tree-sitter node

        Returns:
            Trimmed array if custom logic applied, None to use generic logic
        """
        ...

    def trim_object_content(
        self,
        context: ProcessingContext,
        literal_info: LiteralInfo,
        max_tokens: int,
        node: Node
    ) -> Optional[str]:
        """
        Trim object literal content with language-specific logic.

        Args:
            context: Processing context
            literal_info: Analyzed literal information
            max_tokens: Token budget
            node: Tree-sitter node

        Returns:
            Trimmed object if custom logic applied, None to use generic logic
        """
        ...


@dataclass
class LiteralInfo:
    """Information about literal structure for smart trimming."""
    type: str  # "string", "array", "object", "set", "tuple"
    opening: str  # "[", "{", "(", '"""', etc.
    closing: str  # "]", "}", ")", '"""', etc.
    content: str  # content without boundaries
    is_multiline: bool
    language: str  # "python", "typescript", etc.


@dataclass
class CommentPlacement:
    """Information about comment placement."""
    char_offset: int
    text: str


class DefaultLiteralHandler:
    """Default handler that delegates all operations to generic logic."""

    def try_process_literal(
        self,
        context: ProcessingContext,
        node: Node,
        capture_name: str,
        literal_text: str,
        max_tokens: int
    ) -> Optional[str]:
        """Default: continue with standard processing path."""
        return None

    def analyze_literal_structure(
        self, stripped: str, is_multiline: bool, language: str
    ) -> Optional[LiteralInfo]:
        """Default: use generic analysis logic."""
        return None

    def trim_string_content(
        self, context: ProcessingContext, literal_info: LiteralInfo, max_tokens: int
    ) -> Optional[str]:
        """Default: use generic string trimming logic."""
        return None

    def trim_array_content(
        self, context: ProcessingContext, literal_info: LiteralInfo, max_tokens: int, node: Node
    ) -> Optional[str]:
        """Default: use generic array trimming logic."""
        return None

    def trim_object_content(
        self, context: ProcessingContext, literal_info: LiteralInfo, max_tokens: int, node: Node
    ) -> Optional[str]:
        """Default: use generic object trimming logic."""
        return None


class LiteralOptimizer:
    """Handles literal data processing optimization with simplified logic."""

    def __init__(self, cfg: LiteralConfig, adapter):
        """Initialize with parent adapter for language-specific checks."""
        self.cfg = cfg
        self.adapter = adapter
        # Get custom handler or use default
        self._handler = adapter.hook__get_literal_handler(root_optimizer=self) or DefaultLiteralHandler()

    def apply(self, context: ProcessingContext) -> None:
        """Apply literal processing based on configuration."""
        max_tokens = self.cfg.max_tokens
        if max_tokens is None:
            return  # Optimization disabled

        # Find all literals in code
        literals = context.doc.query("literals")

        for node, capture_name in literals:
            # Skip docstrings - they are handled by separate comment logic
            if capture_name == "string" and self.adapter.is_docstring_node(node, context.doc):
                continue

            literal_text = context.doc.get_node_text(node)
            token_count = context.tokenizer.count_text(literal_text)

            if token_count > max_tokens:
                self._trim_literal(context, node, capture_name, literal_text, max_tokens)

    def _trim_literal(
        self,
        context: ProcessingContext,
        node: Node,
        capture_name: str,
        literal_text: str,
        max_tokens: int
    ) -> None:
        """Smart trim literal while preserving AST validity."""
        # ===== EARLY HOOK: Full control for complex cases =====
        custom_result = self._handler.try_process_literal(
            context, node, capture_name, literal_text, max_tokens
        )

        if custom_result is not None:
            # Handler processed completely - apply result and return
            start_char, end_char = context.doc.get_node_range(node)

            # Calculate savings
            original_tokens = context.tokenizer.count_text(literal_text)
            saved_tokens = original_tokens - context.tokenizer.count_text(custom_result)

            # Apply replacement
            context.editor.add_replacement(
                start_char, end_char, custom_result,
                edit_type="literal_trimmed"
            )

            # Check placeholder style and add comment if needed
            placeholder_style = self.adapter.cfg.placeholders.style
            if placeholder_style != "none" and saved_tokens > 0:
                # Extract type from capture_name for comment
                comment_type = capture_name if capture_name in ("string", "array", "object", "set", "tuple") else "literal"
                comment_text = f"literal {comment_type} (−{saved_tokens} tokens)"
                placement = self._find_comment_placement(context.raw_text, end_char, comment_text, self.adapter.get_comment_style()[0])
                context.editor.add_insertion(
                    placement.char_offset, placement.text,
                    edit_type="literal_comment"
                )

            # Update metrics
            context.metrics.mark_element_removed("literal")
            context.metrics.add_chars_saved(len(literal_text) - len(custom_result))
            return

        # ===== STANDARD PATH: Continue with analyze + trim =====
        # Analyze literal structure
        literal_info = self._analyze_literal_structure(literal_text, capture_name, self.adapter.name)

        # Smart trim content
        trimmed_content = self._smart_trim_content(context, literal_info, max_tokens, node)

        # Form correct replacement
        replacement = f"{literal_info.opening}{trimmed_content}{literal_info.closing}"

        # Calculate token savings
        original_tokens = context.tokenizer.count_text(literal_text)
        saved_tokens = original_tokens - context.tokenizer.count_text(replacement)

        # Apply literal replacement
        start_char, end_char = context.doc.get_node_range(node)
        context.editor.add_replacement(
            start_char, end_char, replacement,
            edit_type="literal_trimmed"
        )

        # Check placeholder style from adapter configuration
        placeholder_style = self.adapter.cfg.placeholders.style

        # If style is "none", don't add comment
        if placeholder_style != "none":
            self._add_comment(context, literal_info, saved_tokens, end_char)

        # Update metrics
        context.metrics.mark_element_removed("literal")
        context.metrics.add_chars_saved(len(literal_text) - len(replacement))

    def _analyze_literal_structure(self, literal_text: str, capture_name: str, language: str) -> LiteralInfo:
        """Analyze literal structure for smart trimming."""
        stripped = literal_text.strip()
        is_multiline = '\n' in literal_text

        # Determine type and boundaries of literal
        if capture_name == "string":
            return self._analyze_string_literal(stripped, is_multiline, language)
        elif capture_name == "set":
            content = self._extract_content(literal_text, "{", "}")
            return LiteralInfo("set", "{", "}", content, is_multiline, language)
        elif capture_name in ("array", "list"):
            return self._analyze_array_literal(stripped, literal_text, is_multiline, language)
        elif capture_name in ("object", "dictionary"):
            content = self._extract_content(literal_text, "{", "}")
            return LiteralInfo("object", "{", "}", content, is_multiline, language)
        else:
            # Universal analysis by syntax
            return self._analyze_by_syntax(stripped, literal_text, is_multiline, language)

    def _analyze_string_literal(self, stripped: str, is_multiline: bool, language: str) -> LiteralInfo:
        """Analyze string literals."""
        # Try handler first for custom literal formats
        custom_info = self._handler.analyze_literal_structure(stripped, is_multiline, language)
        if custom_info is not None:
            return custom_info

        if stripped.startswith('"""') or stripped.startswith("'''"):
            # Python triple quotes
            quote = stripped[:3]
            content = self._extract_content(stripped, quote, quote)
            return LiteralInfo("string", quote, quote, content, is_multiline, language)
        elif stripped.startswith('`'):
            # Template strings (TypeScript)
            content = self._extract_content(stripped, "`", "`")
            return LiteralInfo("string", "`", "`", content, is_multiline, language)
        elif stripped.startswith('"'):
            content = self._extract_content(stripped, '"', '"')
            return LiteralInfo("string", '"', '"', content, is_multiline, language)
        elif stripped.startswith("'"):
            content = self._extract_content(stripped, "'", "'")
            return LiteralInfo("string", "'", "'", content, is_multiline, language)
        else:
            # Fallback
            return LiteralInfo("string", '"', '"', stripped, is_multiline, language)

    def _analyze_array_literal(self, stripped: str, literal_text: str, is_multiline: bool, language: str) -> LiteralInfo:
        """Analyze arrays/lists."""
        # Try handler first for custom literal formats (like Map.of(), List.of())
        custom_info = self._handler.analyze_literal_structure(stripped, is_multiline, language)
        if custom_info is not None:
            return custom_info

        if stripped.startswith('[') and stripped.endswith(']'):
            content = self._extract_content(literal_text, "[", "]")
            return LiteralInfo("array", "[", "]", content, is_multiline, language)
        elif stripped.startswith('(') and stripped.endswith(')'):
            # Tuple in Python
            content = self._extract_content(literal_text, "(", ")")
            return LiteralInfo("tuple", "(", ")", content, is_multiline, language)
        elif stripped.startswith('{') and stripped.endswith('}'):
            content = self._extract_content(literal_text, "{", "}")
            # In C/C++, {} is used for array/vector initialization, not objects
            if language in ("cpp", "c"):
                return LiteralInfo("array", "{", "}", content, is_multiline, language)
            else:
                return LiteralInfo("object", "{", "}", content, is_multiline, language)
        else:
            # Fallback to array
            content = self._extract_content(literal_text, "[", "]")
            return LiteralInfo("array", "[", "]", content, is_multiline, language)

    def _analyze_by_syntax(self, stripped: str, literal_text: str, is_multiline: bool, language: str) -> LiteralInfo:
        """Universal analysis by syntax."""
        if stripped.startswith('[') and stripped.endswith(']'):
            content = self._extract_content(literal_text, "[", "]")
            return LiteralInfo("array", "[", "]", content, is_multiline, language)
        elif stripped.startswith('{') and stripped.endswith('}'):
            content = self._extract_content(literal_text, "{", "}")
            return LiteralInfo("object", "{", "}", content, is_multiline, language)
        elif stripped.startswith('(') and stripped.endswith(')'):
            content = self._extract_content(literal_text, "(", ")")
            return LiteralInfo("tuple", "(", ")", content, is_multiline, language)
        else:
            return LiteralInfo("literal", "", "", stripped, is_multiline, language)

    def _extract_content(self, literal_text: str, opening: str, closing: str) -> str:
        """Extract literal content without opening/closing characters."""
        stripped = literal_text.strip()

        if opening and closing and stripped.startswith(opening) and stripped.endswith(closing):
            return stripped[len(opening):-len(closing)]

        return stripped

    def _smart_trim_content(self, context: ProcessingContext, literal_info: LiteralInfo, max_tokens: int, node: Node) -> str:
        """Smart trim content considering literal structure."""
        if literal_info.type == "string":
            return self._trim_string_content(context, literal_info, max_tokens)
        elif literal_info.type in ("array", "tuple", "set"):
            return self._trim_array_content(context, literal_info, max_tokens, node)
        elif literal_info.type == "object":
            return self._trim_object_content(context, literal_info, max_tokens, node)
        else:
            return context.tokenizer.truncate_to_tokens(literal_info.content, max_tokens)

    def _trim_string_content(self, context: ProcessingContext, literal_info: LiteralInfo, max_tokens: int) -> str:
        """Trim string literals."""
        # Try handler first for custom string trimming
        custom_result = self._handler.trim_string_content(context, literal_info, max_tokens)
        if custom_result is not None:
            return custom_result

        content = literal_info.content

        # Reserve space for boundaries and trim character
        overhead_text = f"{literal_info.opening}…{literal_info.closing}"
        overhead_tokens = context.tokenizer.count_text(overhead_text)
        content_budget = max(1, max_tokens - overhead_tokens)

        # Trim content to budget
        trimmed = context.tokenizer.truncate_to_tokens(content, content_budget)
        return f"{trimmed}…"

    def _trim_array_content(self, context: ProcessingContext, literal_info: LiteralInfo, max_tokens: int, node: Node) -> str:
        """Trim arrays/lists with correct placeholder element."""
        # Try handler first for custom array trimming
        custom_result = self._handler.trim_array_content(context, literal_info, max_tokens, node)
        if custom_result is not None:
            return custom_result

        content = literal_info.content.strip()

        # Reserve space for boundaries and placeholder
        placeholder_element = '"…"'
        overhead = f"{literal_info.opening}{placeholder_element},{literal_info.closing}"
        overhead_tokens = context.tokenizer.count_text(overhead)
        content_budget = max(10, max_tokens - overhead_tokens)

        # Parse elements
        elements = self._parse_elements(content)

        # Find elements that fit in budget
        included_elements = self._select_elements_within_budget(context, elements, content_budget)

        if not included_elements:
            # If no element fits, take first one partially
            first_element = elements[0] if elements else '""'
            trimmed_element = context.tokenizer.truncate_to_tokens(first_element, content_budget - 10)
            return f"{trimmed_element}, \"…\""

        # Form result
        if literal_info.is_multiline:
            # Determine correct indentation from context
            element_indent, base_indent = self._get_base_indentations(context.doc, node, context.raw_text)
            # Add indentation to each element
            indented_elements = [f"{element_indent}{element}" for element in included_elements]
            joined = f",\n".join(indented_elements)
            return f"\n{joined},\n{element_indent}\"…\",\n{base_indent}"
        else:
            joined = ", ".join(included_elements)
            return f"{joined}, \"…\""

    def _trim_object_content(self, context: ProcessingContext, literal_info: LiteralInfo, max_tokens: int, node: Node) -> str:
        """Trim objects/dictionaries with correct placeholder."""
        # Try handler first for custom object trimming
        custom_result = self._handler.trim_object_content(context, literal_info, max_tokens, node)
        if custom_result is not None:
            return custom_result

        content = literal_info.content.strip()

        # Reserve space for boundaries and placeholder
        placeholder_pair = '"…": "…"'
        overhead = f"{literal_info.opening}{placeholder_pair},{literal_info.closing}"
        overhead_tokens = context.tokenizer.count_text(overhead)
        content_budget = max(10, max_tokens - overhead_tokens)

        # Parse key-value pairs
        pairs = self._parse_elements(content)

        # Find pairs that fit in budget
        included_pairs = self._select_elements_within_budget(context, pairs, content_budget)

        if not included_pairs:
            # If no pair fits, use only placeholder
            if literal_info.is_multiline:
                # Determine correct indentation from context
                element_indent, base_indent = self._get_base_indentations(context.doc, node, context.raw_text)
                return f"\n{element_indent}\"…\": \"…\",\n{base_indent}"
            else:
                return '"…": "…"'

        # Form result
        if literal_info.is_multiline:
            # Determine correct indentation from context
            element_indent, base_indent = self._get_base_indentations(context.doc, node, context.raw_text)
            # Add indentation to each element
            indented_pairs = [f"{element_indent}{pair}" for pair in included_pairs]
            joined = f",\n".join(indented_pairs)
            return f"\n{joined},\n{element_indent}\"…\": \"…\",\n{base_indent}"
        else:
            joined = ", ".join(included_pairs)
            return f"{joined}, \"…\": \"…\""

    def _select_elements_within_budget(self, context: ProcessingContext, elements: List[str], budget: int) -> List[str]:
        """Select elements that fit in token budget."""
        included_elements = []
        current_tokens = 0

        for element in elements:
            element_tokens = context.tokenizer.count_text(element + ",")
            if current_tokens + element_tokens <= budget:
                included_elements.append(element)
                current_tokens += element_tokens
            else:
                break

        return included_elements

    def _parse_elements(self, content: str) -> List[str]:
        """
        Universal element parser considering nesting.
        Works for both arrays and objects.
        """
        if not content.strip():
            return []

        elements = []
        current_element = ""
        depth = 0
        in_string = False
        string_char = None

        for i, char in enumerate(content):
            # Handle strings
            if char in ('"', "'", "`") and not in_string:
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
            elif char in ('(', '[', '{'):
                depth += 1
                current_element += char
            elif char in (')', ']', '}'):
                depth -= 1
                current_element += char
            elif char == ',' and depth == 0:
                # Found top-level separator
                if current_element.strip():
                    elements.append(current_element.strip())
                current_element = ""
            else:
                current_element += char

        # Add last element
        if current_element.strip():
            elements.append(current_element.strip())

        return elements

    def _get_base_indentations(self, doc: TreeSitterDocument, node: Node, raw_text: str) -> tuple[str, str]:
        """
        Determine correct indentation for elements and base literal indentation.

        Returns:
            Tuple of (element_indent, base_indent)
        """
        # Get full literal text from source file
        full_literal_text = doc.get_node_text(node)
        start_char, end_char = doc.get_node_range(node)

        # Determine base indentation (indentation of line where literal starts)
        start_line = doc.get_line_number(start_char)
        lines = raw_text.split('\n')
        base_indent = ""
        if start_line < len(lines):
            line = lines[start_line]
            for char in line:
                if char in ' \t':
                    base_indent += char
                else:
                    break

        # Determine indentation for elements inside literal
        element_indent = self._detect_element_indentation_from_full_text(full_literal_text, base_indent)

        return element_indent, base_indent

    def _detect_element_indentation_from_full_text(self, full_literal_text: str, base_indent: str) -> str:
        """
        Determine element indentation inside literal from full literal text.
        """
        lines = full_literal_text.split('\n')
        if len(lines) < 2:
            return "    "  # 4 spaces by default

        # Look for first line with element content (not empty, not closing bracket)
        for line in lines[1:]:
            stripped = line.strip()
            if stripped and not stripped.startswith(('}', ']', ')')):
                # Extract leading whitespace
                element_indent = ""
                for char in line:
                    if char in ' \t':
                        element_indent += char
                    else:
                        break
                # If found indentation, use it
                if element_indent:
                    return element_indent

        # Fallback - add standard indentation to base
        return base_indent + "    "

    def _add_comment(self, context: ProcessingContext, literal_info: LiteralInfo, saved_tokens: int, end_char: int) -> None:
        """Add comment in correct place."""
        comment_style = self.adapter.get_comment_style()
        single_comment = comment_style[0]

        comment_text = f"literal {literal_info.type} (−{saved_tokens} tokens)"

        # Find best place for comment placement
        placement = self._find_comment_placement(context.raw_text, end_char, comment_text, single_comment)

        context.editor.add_insertion(
            placement.char_offset, placement.text,
            edit_type="literal_comment"
        )

    def _find_comment_placement(self, text: str, end_char: int, comment_text: str, single_comment: str) -> CommentPlacement:
        """Find best place for comment placement."""
        text_after = text[end_char:]
        line_after = text_after.split('\n')[0]

        # 1. Look for closing brackets/quotes right after literal
        bracket_pos = self._find_closing_brackets_after_literal(line_after)
        if bracket_pos is not None:
            insertion_pos = end_char + bracket_pos + 1
            text_after_bracket = line_after[bracket_pos + 1:].strip()
            if text_after_bracket and not text_after_bracket.startswith((';', ',', ')')):
                # Code after - use block comment
                block_open, block_close = self.adapter.get_comment_style()[1]
                comment = f" {block_open} {comment_text} {block_close}"
            else:
                # No code - use single-line (without extra semicolon)
                comment = f" {single_comment} {comment_text}"
            return CommentPlacement(insertion_pos, comment)

        # 2. Look for semicolon
        semicolon_pos = line_after.find(';')
        if semicolon_pos != -1:
            insertion_pos = end_char + semicolon_pos + 1
            text_after_semicolon = line_after[semicolon_pos + 1:].strip()
            if text_after_semicolon:
                # Code after - use block comment
                block_open, block_close = self.adapter.get_comment_style()[1]
                comment = f" {block_open} {comment_text} {block_close}"
            else:
                # No code - use single-line (don't add extra semicolon)
                comment = f" {single_comment} {comment_text}"
            return CommentPlacement(insertion_pos, comment)

        # 3. Look for comma (for arrays, objects)
        comma_pos = line_after.find(',')
        if comma_pos != -1:
            insertion_pos = end_char + comma_pos + 1
            text_after_comma = line_after[comma_pos + 1:].strip()
            if text_after_comma and not text_after_comma.startswith((']', '}', ')')):
                # Code after - use block comment
                block_open, block_close = self.adapter.get_comment_style()[1]
                comment = f" {block_open} {comment_text} {block_close}"
            else:
                # No code - use single-line
                comment = f" {single_comment} {comment_text}"
            return CommentPlacement(insertion_pos, comment)

        # 4. If nothing found - place right after literal
        if line_after.strip():
            # Code after - use block comment
            block_open, block_close = self.adapter.get_comment_style()[1]
            comment = f" {block_open} {comment_text} {block_close}"
        else:
            # No code - use single-line
            comment = f" {single_comment} {comment_text}"

        return CommentPlacement(end_char, comment)

    def _find_closing_brackets_after_literal(self, line_after: str) -> int | None:
        """Find closing brackets right after literal."""
        # Look for closing brackets at start of line (after literal)
        for i, char in enumerate(line_after):
            if char in '])}':
                return i
            elif char not in ' \t':  # Stop on first non-whitespace character
                break
        return None
