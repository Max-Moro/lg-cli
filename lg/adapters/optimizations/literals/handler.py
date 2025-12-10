"""
Language literal handler.

Coordinates literal detection, parsing, selection, and formatting
for a specific programming language.
"""

from __future__ import annotations

from typing import List, Optional

from lg.stats.tokenizer import TokenService
from .block_init import BlockInitProcessor
from .components.interpolation import InterpolationHandler
from .descriptor import LanguageLiteralDescriptor
from .element_parser import ElementParser, Element
from .patterns import (
    ParsedLiteral,
    TrimResult,
    StringProfile,
    BlockInitProfile,
    LiteralProfile,
)
from .processing.formatter import ResultFormatter
from .processing.parser import LiteralParser
from .processing.selector import BudgetSelector, Selection, DFSSelection


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

    def get_parser_for_profile(self, profile) -> ElementParser:
        """
        Get or create parser for a profile.

        Args:
            profile: LiteralProfile to create parser for

        Returns:
            ElementParser configured for this profile
        """
        from .element_parser import create_parse_config_from_profile

        # Create cache key from profile attributes
        separator = getattr(profile, 'separator', ',')
        kv_separator = getattr(profile, 'kv_separator', None)
        tuple_size = getattr(profile, 'tuple_size', 1)
        key = f"{separator}:{kv_separator}:{tuple_size}"

        if key not in self._parsers:
            config = create_parse_config_from_profile(profile, self._factory_wrappers)
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
        profile: Optional[LiteralProfile] = None,
        tree_sitter_type: str = "",
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
        if profile is None:
            return None

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
            return self._process_string(parsed, token_budget)
        elif isinstance(profile, BlockInitProfile):
            # BLOCK_INIT requires special handling with node access
            # This path should not be reached from process_literal
            raise RuntimeError(
                "BLOCK_INIT profiles must be processed via process_block_init_node, "
                "not process_literal"
            )
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
        parsed: ParsedLiteral,
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
        min_elements = getattr(profile, 'min_elements', 1)
        tuple_size = getattr(profile, 'tuple_size', 1)
        preserve_all_keys = getattr(profile, 'preserve_all_keys', False)

        selection = self.selector.select_dfs(
            elements, content_budget,
            profile=profile,
            handler=self,
            min_keep=min_elements,
            tuple_size=tuple_size,
            preserve_top_level_keys=preserve_all_keys,
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
        profile: Optional[LiteralProfile] = None,
        node=None,  # tree_sitter Node
        doc=None,  # TreeSitterDocument
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
        if profile is None:
            return None

        # Delegate to BlockInitProcessor
        # Returns (TrimResult, nodes_used) or None
        result = self.block_init_processor.process(
            profile=profile,
            node=node,
            doc=doc,
            token_budget=token_budget,
            base_indent=base_indent,
        )

        # Return as-is: (TrimResult, nodes_used) or None
        return result

    def process_ast_based_sequence(
        self,
        profile: Optional[LiteralProfile] = None,
        node=None,  # tree_sitter Node
        doc=None,  # TreeSitterDocument
        token_budget: int = 0,
        base_indent: str = "",
        element_indent: str = "",
    ) -> Optional[TrimResult]:
        """
        Process sequence literals using AST-based element extraction.

        This method is used for sequences where elements cannot be reliably
        extracted via text parsing (e.g., no separators). Common use cases:
        - C/C++ concatenated strings: "a" "b" "c"
        - Languages with implicit sequence concatenation

        Uses tree-sitter AST to extract child elements, then keeps as many
        as fit within the token budget.

        Args:
            profile: SequenceProfile with requires_ast_extraction=True
            node: Tree-sitter node representing the sequence
            doc: Tree-sitter document
            token_budget: Token budget
            base_indent: Base indentation
            element_indent: Element indentation

        Returns:
            TrimResult if optimization applied, None otherwise
        """
        if profile is None:
            return None

        # Get all child string nodes that match string profiles
        # Use the query to find string nodes
        string_profiles = self.descriptor.string_profiles

        # Collect all string child nodes by querying each string profile
        child_strings = []
        child_string_set = set()  # Track by (start, end) to avoid duplicates

        for str_profile in string_profiles:
            matched_nodes = doc.query_nodes(str_profile.query, "lit")
            for matched_node in matched_nodes:
                # Check if this node is a direct or indirect child of the input node
                if (matched_node.start_byte >= node.start_byte and
                    matched_node.end_byte <= node.end_byte):
                    coords = (matched_node.start_byte, matched_node.end_byte)
                    if coords not in child_string_set:
                        child_string_set.add(coords)
                        child_strings.append(matched_node)

        # Sort by position
        child_strings.sort(key=lambda n: n.start_byte)

        if not child_strings:
            return None  # No strings to process

        # Get full text and token count
        full_text = doc.get_node_text(node)
        original_tokens = self.tokenizer.count_text_cached(full_text)

        # If already within budget, no trimming needed
        if original_tokens <= token_budget:
            return None

        # Keep as many complete child strings as fit in budget
        # Overhead is just for placeholder (no delimiters)
        placeholder = profile.placeholder_template
        placeholder_tokens = self.tokenizer.count_text_cached(placeholder)

        content_budget = max(1, token_budget - placeholder_tokens)

        # Accumulate child strings until we exceed budget
        kept_strings = []
        running_tokens = 0

        for child in child_strings:
            child_text = doc.get_node_text(child)
            child_tokens = self.tokenizer.count_text_cached(child_text)

            if running_tokens + child_tokens <= content_budget:
                kept_strings.append(child_text)
                running_tokens += child_tokens
            else:
                break  # Budget exceeded, stop

        # Need at least one string
        if not kept_strings:
            # Keep first string even if it exceeds budget
            kept_strings = [doc.get_node_text(child_strings[0])]
            running_tokens = self.tokenizer.count_text_cached(kept_strings[0])

        # If we kept all strings, no optimization needed
        if len(kept_strings) == len(child_strings):
            return None

        # Build trimmed text: insert placeholder INSIDE last string (before closing delimiter)
        last_child_text = doc.get_node_text(child_strings[len(kept_strings) - 1])

        # Detect closing delimiter from last child string text
        # Check common string delimiters
        closing_delimiter = None
        if last_child_text.endswith('"""'):
            closing_delimiter = '"""'
        elif last_child_text.endswith("'''"):
            closing_delimiter = "'''"
        elif last_child_text.endswith('"'):
            # Could be regular string or raw string ending
            # Check if it's a raw string (language-specific)
            if last_child_text.startswith('R"') or last_child_text.startswith('r"'):
                # Raw string - find closing sequence
                import re
                match = re.search(r'\)([^)]*)"$', last_child_text)
                if match:
                    closing_delimiter = ")" + match.group(1) + '"'
                else:
                    closing_delimiter = ')"'  # Default
            else:
                closing_delimiter = '"'
        elif last_child_text.endswith("'"):
            closing_delimiter = "'"

        # Preserve indentation from original
        lines = full_text.split('\n')
        if len(lines) > 1:
            # Multiline: build kept strings, insert placeholder in last one
            parts = []
            for i, s in enumerate(kept_strings):
                if i == len(kept_strings) - 1:
                    # Last string: insert placeholder before closing delimiter
                    if closing_delimiter and s.endswith(closing_delimiter):
                        parts.append(s[:-len(closing_delimiter)] + placeholder + closing_delimiter)
                    else:
                        # Fallback if can't find delimiter
                        parts.append(s + placeholder)
                else:
                    parts.append(s)

            # Join with newlines and indent
            trimmed_text = parts[0]
            for s in parts[1:]:
                trimmed_text += f"\n{element_indent}{s}"
        else:
            # Single line: insert placeholder in last string before closing delimiter
            last_string = kept_strings[-1]
            if closing_delimiter and last_string.endswith(closing_delimiter):
                kept_strings[-1] = last_string[:-len(closing_delimiter)] + placeholder + closing_delimiter
            else:
                kept_strings[-1] = last_string + placeholder
            trimmed_text = " ".join(kept_strings)

        # Calculate tokens for trimmed text
        trimmed_tokens = self.tokenizer.count_text_cached(trimmed_text)
        saved_tokens = original_tokens - trimmed_tokens

        # Create comment
        comment_name = profile.comment_name or 'literal'
        comment_text = f"{comment_name} (−{saved_tokens} tokens)"

        return TrimResult(
            trimmed_text=trimmed_text,
            original_tokens=original_tokens,
            trimmed_tokens=trimmed_tokens,
            saved_tokens=saved_tokens,
            elements_kept=len(kept_strings),
            elements_removed=len(child_strings) - len(kept_strings),
            comment_text=comment_text,
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