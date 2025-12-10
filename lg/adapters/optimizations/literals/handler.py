"""
Language literal handler.

Coordinates literal detection, parsing, selection, and formatting
for a specific programming language.
"""

from __future__ import annotations

from typing import List, Optional, cast

from tree_sitter._binding import Node

from lg.stats.tokenizer import TokenService
from .components.block_init import BlockInitProcessor
from .components.interpolation import InterpolationHandler
from .descriptor import LanguageLiteralDescriptor
from .element_parser import ElementParser, Element, ParseConfig
from .patterns import (
    ParsedLiteral,
    TrimResult,
    StringProfile,
    BlockInitProfile,
    LiteralProfile,
    CollectionProfile,
    MappingProfile,
    FactoryProfile, SequenceProfile
)
from .processing.formatter import ResultFormatter
from .processing.parser import LiteralParser
from .processing.selector import BudgetSelector, Selection, DFSSelection
from ...tree_sitter_support import TreeSitterDocument


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
        language: str,
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
        self.language = language
        self.tokenizer = tokenizer

        # Store comment style for context-aware formatting
        self.single_comment = comment_style[0]
        self.block_comment = comment_style[1]

        # Create reusable components
        self.literal_parser = LiteralParser(tokenizer)
        self.selector = BudgetSelector(tokenizer)
        self.formatter = ResultFormatter(tokenizer, comment_style)
        self.block_init_processor = BlockInitProcessor(tokenizer, handler=self, comment_style=comment_style)
        self.interpolation = InterpolationHandler()

        # Collect factory wrappers from all FACTORY_CALL patterns for nested detection
        self._factory_wrappers = self._collect_factory_wrappers()

        # Cache parsers for different patterns
        self._parsers: dict[str, ElementParser] = {}

    def _collect_factory_wrappers(self) -> List[str]:
        """Collect all factory method wrappers from descriptor for nested detection."""
        wrappers = []

        # Collect from factory profiles
        for profile in self.descriptor.factory_profiles:
            if profile.wrapper_match:
                regex = profile.wrapper_match.rstrip("$")
                if regex.startswith("(") and regex.endswith(")"):
                    regex = regex[1:-1]
                alternatives = regex.split("|")
                for alt in alternatives:
                    wrapper = alt.replace("\\.", ".")
                    if wrapper and wrapper not in wrappers:
                        wrappers.append(wrapper)

        # Collect from mapping profiles (some have wrappers like Kotlin mapOf)
        for profile in self.descriptor.mapping_profiles:
            if profile.wrapper_match:
                regex = profile.wrapper_match.rstrip("$")
                if regex.startswith("(") and regex.endswith(")"):
                    regex = regex[1:-1]
                alternatives = regex.split("|")
                for alt in alternatives:
                    wrapper = alt.replace("\\.", ".")
                    if wrapper and wrapper not in wrappers:
                        wrappers.append(wrapper)

        # Add additional wrappers from descriptor
        for wrapper in self.descriptor.nested_factory_wrappers:
            if wrapper not in wrappers:
                wrappers.append(wrapper)

        return wrappers

    def get_parser_for_profile(self, profile: CollectionProfile) -> ElementParser:
        """
        Get or create parser for a profile.

        Args:
            profile: LiteralProfile to create parser for

        Returns:
            ElementParser configured for this profile
        """

        # Create cache key from profile attributes
        separator = profile.separator
        kv_separator = profile.kv_separator if isinstance(profile, (MappingProfile, FactoryProfile)) else None
        tuple_size = profile.tuple_size if isinstance(profile, FactoryProfile) else 1

        key = f"{separator}:{kv_separator}:{tuple_size}"

        if key not in self._parsers:
            config = ParseConfig(
                separator=separator,
                kv_separator=kv_separator,
                preserve_whitespace=False,
                factory_wrappers=self._factory_wrappers,
            )
            self._parsers[key] = ElementParser(config)

        return self._parsers[key]

    def _extract_content(
        self,
        text: str,
        opening: str,
        closing: str,
        wrapper: Optional[str] = None
    ) -> Optional[str]:
        """Delegate to literal_parser."""
        return self.literal_parser._extract_content(text, opening, closing, wrapper)

    def process_literal(
        self,
        text: str,
        profile: LiteralProfile,
        start_byte: int = 0,
        end_byte: int = 0,
        token_budget: int = 0,
        base_indent: str = "",
        element_indent: str = "",
    ) -> Optional[TrimResult]:
        """
        Process a literal and return trimmed result if beneficial.

        Args:
            text: Full literal text
            profile: LiteralProfile (StringProfile, SequenceProfile, etc.) that matched this node
            tree_sitter_type: Tree-sitter node type (for wrapper detection)
            start_byte: Start position
            end_byte: End position
            token_budget: Maximum tokens for content
            base_indent: Line indentation
            element_indent: Element indentation

        Returns:
            TrimResult if trimming is beneficial, None otherwise
        """

        # Use profile-based parsing
        parsed = self.literal_parser.parse_literal_with_profile(
            text, profile, start_byte, end_byte,
            base_indent, element_indent
        )

        if not parsed:
            return None

        # Check if already within budget
        if parsed.original_tokens <= token_budget:
            return None

        # Handle based on profile type
        profile = parsed.profile
        if isinstance(profile, StringProfile):
            return self._process_string(cast(ParsedLiteral[StringProfile], parsed), token_budget)
        elif isinstance(profile, BlockInitProfile):
            # BLOCK_INIT requires special handling with node access
            # This path should not be reached from process_literal
            raise RuntimeError(
                "BLOCK_INIT profiles must be processed via process_block_init_node, "
                "not process_literal"
            )
        else:
            return self._process_collection_dfs(cast(ParsedLiteral[CollectionProfile], parsed), token_budget)

    def _process_string(
        self,
        parsed: ParsedLiteral[StringProfile],
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

        # Adjust for string interpolation boundaries
        # Don't cut inside ${...}, #{...}, etc.
        interpolation_markers = self.interpolation.get_active_markers(
            parsed.profile, parsed.opening, parsed.content
        )
        if interpolation_markers:
            truncated = self.interpolation.adjust_truncation(
                truncated, parsed.content, interpolation_markers
            )

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
            tokens_kept=self.tokenizer.count_text_cached(truncated),
            tokens_removed=parsed.original_tokens - self.tokenizer.count_text_cached(truncated),
        )
        # Mark as having removals for formatting
        selection.removed_elements = [Element(
            text="...", raw_text="...", start_offset=0, end_offset=0
        )]

        # Format result
        formatted = self.formatter.format(parsed, selection)

        return self.formatter.create_trim_result(parsed, selection, formatted)

    def _process_collection_dfs(
        self,
        parsed: ParsedLiteral[CollectionProfile],
        token_budget: int
    ) -> Optional[TrimResult]:
        """Process collection literal with DFS for nested structures."""
        profile = parsed.profile

        # Get parser for this profile
        parser = self.get_parser_for_profile(profile)

        # Parse elements
        elements = parser.parse(parsed.content)

        if not elements:
            return None

        # Calculate overhead
        placeholder = profile.placeholder_template
        overhead = self.selector.calculate_overhead(
            parsed.opening, parsed.closing, placeholder,
            parsed.is_multiline, parsed.element_indent
        )

        content_budget = max(1, token_budget - overhead)

        # Select elements with DFS (budget-aware nested selection)
        # For preserve_all_keys: keep all top-level keys, but apply DFS to nested values

        selection = self.selector.select_dfs(
            elements, content_budget,
            profile=profile,
            handler=self,
            min_keep=profile.min_elements,
            tuple_size=profile.tuple_size if isinstance(profile, FactoryProfile) else 1,
            preserve_top_level_keys=profile.preserve_all_keys if isinstance(profile, MappingProfile) else False,
        )

        if not selection.has_removals:
            return None  # No trimming needed

        # Format result with DFS
        formatted = self.formatter.format_dfs(parsed, selection, parser)
        return self._create_trim_result_dfs(parsed, selection, formatted)

    def _create_trim_result_dfs(
        self,
        parsed: ParsedLiteral[CollectionProfile],
        selection: DFSSelection,
        formatted,  # FormattedResult
    ) -> TrimResult:
        """Create TrimResult from DFS formatting data."""
        trimmed_tokens = self.tokenizer.count_text_cached(formatted.text)

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

    def process_block_init_node(
        self,
        profile: BlockInitProfile,
        node: Node,
        doc: TreeSitterDocument,
        token_budget: int = 0,
        base_indent: str = "",
    ) -> Optional[TrimResult]:
        """
        Process BLOCK_INIT profile with direct node access.

        This is a separate entry point for BLOCK_INIT profiles
        because they require AST navigation, not just text processing.

        Args:
            profile: BlockInitProfile that matched this node
            node: Tree-sitter node to process (will be expanded to group for let_declarations)
            doc: Tree-sitter document
            token_budget: Token budget
            base_indent: Base indentation

        Returns:
            (TrimResult, nodes_used) tuple if optimization applied, None otherwise
            nodes_used is the list of nodes that should be replaced (expanded group for Rust)
        """

        # Delegate to BlockInitProcessor
        # Returns (TrimResult, nodes_used) or None
        return self.block_init_processor.process(
            profile=profile,
            node=node,
            doc=doc,
            token_budget=token_budget,
            base_indent=base_indent,
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