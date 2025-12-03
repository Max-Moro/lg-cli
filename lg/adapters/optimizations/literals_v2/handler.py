"""
Language literal handler.

Coordinates literal detection, parsing, selection, and formatting
for a specific programming language.
"""

from __future__ import annotations

from typing import Optional

from .categories import (
    LiteralCategory,
    LiteralPattern,
    ParsedLiteral,
    TrimResult,
)
from .descriptor import LanguageLiteralDescriptor
from .parser import ElementParser, ParseConfig, Element
from .selector import BudgetSelector, Selection, DFSSelection
from .formatter import ResultFormatter
from lg.stats.tokenizer import TokenService


class LanguageLiteralHandler:
    """
    Handles literal optimization for a specific language.

    Coordinates the full pipeline:
    1. Pattern matching (via descriptor)
    2. Content parsing (via element parser)
    3. Budget-aware selection (via selector)
    4. Result formatting (via formatter)

    Languages can subclass to override specific behaviors.
    """

    def __init__(
        self,
        descriptor: LanguageLiteralDescriptor,
        tokenizer: TokenService,
        comment_style: tuple[str, tuple[str, str]] = ("//", ("/*", "*/")),
    ):
        """
        Initialize handler.

        Args:
            descriptor: Language literal descriptor
            tokenizer: Token counting service
            comment_style: Comment syntax for this language
        """
        self.descriptor = descriptor
        self.language = descriptor.language
        self.tokenizer = tokenizer

        # Store comment style for context-aware formatting
        self.single_comment = comment_style[0]
        self.block_comment = comment_style[1]

        # Create reusable components
        self.selector = BudgetSelector(tokenizer)
        self.formatter = ResultFormatter(tokenizer, comment_style)

        # Cache parsers for different patterns
        self._parsers: dict[str, ElementParser] = {}

    def get_parser(self, pattern: LiteralPattern) -> ElementParser:
        """Get or create parser for a pattern."""
        key = f"{pattern.separator}:{pattern.kv_separator}"

        if key not in self._parsers:
            config = ParseConfig(
                separator=pattern.separator,
                kv_separator=pattern.kv_separator,
                preserve_whitespace=pattern.preserve_whitespace,
            )
            self._parsers[key] = ElementParser(config)

        return self._parsers[key]

    def detect_literal_type(self, tree_sitter_type: str) -> bool:
        """Check if a tree-sitter node type is a literal we handle."""
        return self.descriptor.get_pattern_for(tree_sitter_type) is not None

    def parse_literal(
        self,
        text: str,
        tree_sitter_type: str,
        start_byte: int,
        end_byte: int,
        base_indent: str = "",
        element_indent: str = "",
    ) -> Optional[ParsedLiteral]:
        """
        Parse a literal from source text.

        Args:
            text: Full literal text including delimiters
            tree_sitter_type: Tree-sitter node type
            start_byte: Start position in source
            end_byte: End position in source
            base_indent: Indentation of line containing literal
            element_indent: Indentation for elements inside

        Returns:
            ParsedLiteral or None if not recognized
        """
        pattern = self.descriptor.get_pattern_for(tree_sitter_type)
        if not pattern:
            return None

        # Detect opening/closing
        opening = pattern.get_opening(text)
        closing = pattern.get_closing(text)

        # Extract content
        content = self._extract_content(text, opening, closing)
        if content is None:
            return None

        # Detect layout
        is_multiline = "\n" in text

        # Count tokens
        original_tokens = self.tokenizer.count_text(text)

        # Detect wrapper for factory calls
        wrapper = self._detect_wrapper(text, pattern)

        return ParsedLiteral(
            original_text=text,
            start_byte=start_byte,
            end_byte=end_byte,
            category=pattern.category,
            pattern=pattern,
            opening=opening,
            closing=closing,
            content=content,
            is_multiline=is_multiline,
            base_indent=base_indent,
            element_indent=element_indent or (base_indent + "    "),
            wrapper=wrapper,
            original_tokens=original_tokens,
        )

    def _extract_content(
        self,
        text: str,
        opening: str,
        closing: str
    ) -> Optional[str]:
        """Extract content between opening and closing delimiters."""
        stripped = text.strip()

        # Handle wrapper prefix (e.g., "vec!" in "vec![...]")
        if not stripped.startswith(opening):
            # Find opening position
            open_pos = stripped.find(opening)
            if open_pos == -1:
                return None
            stripped = stripped[open_pos:]

        if not stripped.startswith(opening) or not stripped.endswith(closing):
            return None

        return stripped[len(opening):-len(closing)]

    def _detect_wrapper(
        self,
        text: str,
        pattern: LiteralPattern
    ) -> Optional[str]:
        """Detect wrapper prefix for factory calls."""
        if pattern.category != LiteralCategory.FACTORY_CALL:
            return None

        stripped = text.strip()
        opening = pattern.get_opening(text)

        open_pos = stripped.find(opening)
        if open_pos > 0:
            return stripped[:open_pos]

        return None

    def process_literal(
        self,
        text: str,
        tree_sitter_type: str,
        start_byte: int,
        end_byte: int,
        token_budget: int,
        base_indent: str = "",
        element_indent: str = "",
    ) -> Optional[TrimResult]:
        """
        Process a literal and return trimmed result if beneficial.

        Args:
            text: Full literal text
            tree_sitter_type: Tree-sitter node type
            start_byte: Start position
            end_byte: End position
            token_budget: Maximum tokens for content
            base_indent: Line indentation
            element_indent: Element indentation

        Returns:
            TrimResult if trimming is beneficial, None otherwise
        """
        # Parse literal
        parsed = self.parse_literal(
            text, tree_sitter_type, start_byte, end_byte,
            base_indent, element_indent
        )
        if not parsed:
            return None

        # Check if already within budget
        if parsed.original_tokens <= token_budget:
            return None

        # Handle based on category
        if parsed.category == LiteralCategory.STRING:
            return self._process_string(parsed, token_budget)
        else:
            return self._process_collection_dfs(parsed, token_budget)

    def _process_string(
        self,
        parsed: ParsedLiteral,
        token_budget: int
    ) -> Optional[TrimResult]:
        """Process string literal - truncate content."""
        # Calculate overhead
        overhead = self.selector.calculate_overhead(
            parsed.opening, parsed.closing, "…",
            parsed.is_multiline, parsed.element_indent
        )

        content_budget = max(1, token_budget - overhead)

        # Truncate content
        truncated = self.tokenizer.truncate_to_tokens(
            parsed.content, content_budget
        )

        if len(truncated) >= len(parsed.content):
            return None  # No trimming needed

        # Create pseudo-selection for string
        kept_element = Element(
            text=truncated,
            raw_text=truncated,
            start_offset=0,
            end_offset=len(truncated),
        )

        selection = Selection(
            kept_elements=[kept_element],
            removed_elements=[],  # Conceptually removed
            total_count=1,
            tokens_kept=self.tokenizer.count_text(truncated),
            tokens_removed=parsed.original_tokens - self.tokenizer.count_text(truncated),
        )
        # Mark as having removals for formatting
        selection.removed_elements = [Element(
            text="...", raw_text="...", start_offset=0, end_offset=0
        )]

        # Format result
        formatted = self.formatter.format(parsed, selection)

        return self.formatter.create_trim_result(parsed, selection, formatted)

    def _process_collection(
        self,
        parsed: ParsedLiteral,
        token_budget: int
    ) -> Optional[TrimResult]:
        """Process collection literal (array, map, etc.)."""
        pattern = parsed.pattern

        # Get parser for this pattern
        parser = self.get_parser(pattern)

        # Parse elements
        elements = parser.parse(parsed.content)

        if not elements:
            return None

        # Calculate overhead
        placeholder = pattern.placeholder_template
        overhead = self.selector.calculate_overhead(
            parsed.opening, parsed.closing, placeholder,
            parsed.is_multiline, parsed.element_indent
        )

        content_budget = max(10, token_budget - overhead)

        # Select elements within budget
        selection = self.selector.select_first(
            elements, content_budget,
            min_keep=pattern.min_elements,
        )

        if not selection.has_removals:
            return None  # No trimming needed

        # Format result
        formatted = self.formatter.format(parsed, selection)

        return self.formatter.create_trim_result(parsed, selection, formatted)

    def _process_collection_dfs(
        self,
        parsed: ParsedLiteral,
        token_budget: int
    ) -> Optional[TrimResult]:
        """Process collection literal with DFS for nested structures."""
        pattern = parsed.pattern

        # Get parser for this pattern
        parser = self.get_parser(pattern)

        # Parse elements
        elements = parser.parse(parsed.content)

        if not elements:
            return None

        # Calculate overhead
        placeholder = pattern.placeholder_template
        overhead = self.selector.calculate_overhead(
            parsed.opening, parsed.closing, placeholder,
            parsed.is_multiline, parsed.element_indent
        )

        content_budget = max(10, token_budget - overhead)

        # Select elements with DFS (budget-aware nested selection)
        selection = self.selector.select_dfs(
            elements, content_budget,
            parser=parser,
            min_keep=pattern.min_elements,
        )

        if not selection.has_removals:
            return None  # No trimming needed

        # Format result with DFS
        formatted = self.formatter.format_dfs(parsed, selection, parser)

        return self._create_trim_result_dfs(parsed, selection, formatted)

    def _create_trim_result_dfs(
        self,
        parsed: ParsedLiteral,
        selection: DFSSelection,
        formatted,  # FormattedResult
    ) -> TrimResult:
        """Create TrimResult from DFS formatting data."""
        from .formatter import FormattedResult

        trimmed_tokens = self.tokenizer.count_text(formatted.text)

        return TrimResult(
            trimmed_text=formatted.text,
            original_tokens=parsed.original_tokens,
            trimmed_tokens=trimmed_tokens,
            saved_tokens=parsed.original_tokens - trimmed_tokens,
            elements_kept=selection.kept_count,
            elements_removed=selection.removed_count,
            comment_text=formatted.comment,
            comment_position=formatted.comment_byte,
        )

    # ========== Context-aware comment formatting ==========

    def get_comment_for_context(
        self,
        text_after_literal: str,
        comment_content: str,
    ) -> tuple[str, int]:
        """
        Determine comment format and insertion offset based on context.

        This method can be overridden by language-specific handlers
        for custom behavior.

        Args:
            text_after_literal: Text after the literal in the source
            comment_content: Raw comment text (e.g., "literal string (−N tokens)")

        Returns:
            Tuple of (formatted_comment, offset_from_literal_end)
            The offset indicates where to insert relative to literal end.
        """
        # Get the remainder of the line after the literal
        line_remainder = text_after_literal.split('\n')[0]

        # Find insertion point and determine comment style
        offset, needs_block = self._find_comment_insertion_point(line_remainder)

        if needs_block:
            return self._format_block_comment(comment_content), offset

        return self._format_single_comment(comment_content), offset

    def _find_comment_insertion_point(self, line_remainder: str) -> tuple[int, bool]:
        """
        Find the best insertion point for comment.

        Returns:
            Tuple of (offset, needs_block_comment)
            - offset: characters to skip before inserting
            - needs_block_comment: whether block comment is needed
        """
        if not line_remainder.strip():
            return 0, False  # Empty line - insert at literal end, single-line OK

        # Look for punctuation that should come before the comment
        offset = 0

        # Skip closing brackets first
        while offset < len(line_remainder) and line_remainder[offset] in ')]}':
            offset += 1

        # Check for semicolon
        if offset < len(line_remainder) and line_remainder[offset] == ';':
            offset += 1
            # Check what follows the semicolon
            after_semi = line_remainder[offset:].strip()
            if after_semi:
                # Code after semicolon - need block comment
                return offset, True
            return offset, False

        # Check for comma
        if offset < len(line_remainder) and line_remainder[offset] == ',':
            offset += 1
            after_comma = line_remainder[offset:].strip()
            # Safe if followed by closing bracket or end of line
            if not after_comma or after_comma[0] in ')]}':
                return offset, False
            # More elements follow - need block comment
            return offset, True

        # No recognized punctuation - check if there's code
        remaining = line_remainder[offset:].strip()
        if remaining:
            return offset, True  # Code present - need block comment

        return offset, False

    def _format_single_comment(self, content: str) -> str:
        """Format as single-line comment."""
        return f" {self.single_comment} {content}"

    def _format_block_comment(self, content: str) -> str:
        """Format as block comment."""
        return f" {self.block_comment[0]} {content} {self.block_comment[1]}"
