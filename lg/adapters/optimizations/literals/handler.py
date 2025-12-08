"""
Language literal handler.

Coordinates literal detection, parsing, selection, and formatting
for a specific programming language.
"""

from __future__ import annotations

from typing import List, Optional

from .block_init import BlockInitProcessor
from .categories import (
    LiteralCategory,
    LiteralPattern,
    ParsedLiteral,
    TrimResult,
)
from .descriptor import LanguageLiteralDescriptor
from .formatter import ResultFormatter
from .parser import ElementParser, ParseConfig, Element
from .selector import BudgetSelector, Selection, DFSSelection
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
        self.selector = BudgetSelector(tokenizer)
        self.formatter = ResultFormatter(tokenizer, comment_style)
        self.block_init_processor = BlockInitProcessor(tokenizer, handler=self, comment_style=comment_style)

        # Collect factory wrappers from all FACTORY_CALL patterns for nested detection
        self._factory_wrappers = self._collect_factory_wrappers()

        # Cache parsers for different patterns
        self._parsers: dict[str, ElementParser] = {}

    def _collect_factory_wrappers(self) -> List[str]:
        """Collect all factory method wrappers from descriptor for nested detection."""
        wrappers = []
        for pattern in self.descriptor.patterns:
            if pattern.category in (LiteralCategory.FACTORY_CALL, LiteralCategory.MAPPING) and pattern.wrapper_match:
                # Extract wrapper names from regex
                # Examples: "(mapOf|listOf)$" -> ["mapOf", "listOf"]
                #           "List\.of$" -> ["List.of"]
                regex = pattern.wrapper_match.rstrip("$")

                # Remove grouping parentheses if present
                if regex.startswith("(") and regex.endswith(")"):
                    regex = regex[1:-1]

                # Split by | to get alternatives
                alternatives = regex.split("|")

                # Clean each alternative and add to wrappers
                for alt in alternatives:
                    wrapper = alt.replace("\\.", ".")
                    if wrapper and wrapper not in wrappers:
                        wrappers.append(wrapper)

        # Add additional wrappers from descriptor
        for wrapper in self.descriptor.nested_factory_wrappers:
            if wrapper not in wrappers:
                wrappers.append(wrapper)

        return wrappers

    def get_parser(self, pattern: LiteralPattern) -> ElementParser:
        """Get or create parser for a pattern."""
        key = f"{pattern.separator}:{pattern.kv_separator}"

        if key not in self._parsers:
            config = ParseConfig(
                separator=pattern.separator,
                kv_separator=pattern.kv_separator,
                preserve_whitespace=pattern.preserve_whitespace,
                factory_wrappers=self._factory_wrappers,
            )
            self._parsers[key] = ElementParser(config)

        return self._parsers[key]

    def _detect_wrapper_from_text(self, text: str, pattern: 'LiteralPattern') -> Optional[str]:
        """
        Detect wrapper prefix using opening delimiter from the known pattern.

        Examples:
        - Java: "List.of(...)" -> "List.of" (opening: "(")
        - Go: "[]string{...}" -> "[]string" (opening: "{")
        - Kotlin: "mapOf(...)" -> "mapOf" (opening: "(")

        Args:
            text: Full literal text
            pattern: The pattern that matched this literal

        Returns:
            Wrapper string or None
        """
        stripped = text.strip()

        # Get opening and closing delimiters from the known pattern
        opening = pattern.get_opening(text) if callable(pattern.opening) else pattern.opening
        closing = pattern.get_closing(text) if callable(pattern.closing) else pattern.closing

        # If text starts with opening delimiter, there's no wrapper
        if stripped.startswith(opening):
            return None

        # Find position of opening delimiter
        pos = stripped.find(opening)
        if pos > 0:
            # Extract wrapper as-is (preserve formatting)
            wrapper = stripped[:pos]

            # Include empty bracket pairs that are part of type/wrapper syntax
            if stripped[pos:pos+2] == opening + closing:
                wrapper += opening + closing

            return wrapper

        return None

    def parse_literal_with_pattern(
        self,
        text: str,
        pattern: 'LiteralPattern',
        start_byte: int,
        end_byte: int,
        base_indent: str = "",
        element_indent: str = "",
    ) -> Optional[ParsedLiteral]:
        """
        Parse a literal from source text using a known pattern.

        Args:
            text: Full literal text including delimiters
            pattern: LiteralPattern that matched this node
            start_byte: Start position in source
            end_byte: End position in source
            base_indent: Indentation of line containing literal
            element_indent: Indentation for elements inside

        Returns:
            ParsedLiteral or None if not recognized
        """
        # Detect wrapper (some patterns like Go composite_literal need it)
        wrapper = self._detect_wrapper_from_text(text, pattern)

        # Detect opening/closing
        opening = pattern.get_opening(text)
        closing = pattern.get_closing(text)

        # Extract content (pass wrapper to skip past it when searching for opening)
        content = self._extract_content(text, opening, closing, wrapper)

        if content is None:
            return None

        # Detect layout
        is_multiline = "\n" in text

        # Count tokens
        original_tokens = self.tokenizer.count_text_cached(text)

        return ParsedLiteral(
            original_text=text,
            start_byte=start_byte,
            end_byte=end_byte,
            original_tokens=original_tokens,
            category=pattern.category,
            opening=opening,
            closing=closing,
            content=content,
            wrapper=wrapper,
            is_multiline=is_multiline,
            base_indent=base_indent,
            element_indent=element_indent,
            pattern=pattern,
        )

    def _extract_content(
        self,
        text: str,
        opening: str,
        closing: str,
        wrapper: Optional[str] = None
    ) -> Optional[str]:
        """Extract content between opening and closing delimiters."""
        stripped = text.strip()

        # Handle wrapper prefix (e.g., "vec!" in "vec![...]", type prefixes)
        if not stripped.startswith(opening):
            # If wrapper is known, start search AFTER wrapper to avoid
            # finding opening brackets that are part of wrapper itself
            if wrapper:
                search_from = len(wrapper)
            else:
                search_from = 0

            # Find opening position
            open_pos = stripped.find(opening, search_from)
            if open_pos == -1:
                return None
            stripped = stripped[open_pos:]

        if not stripped.startswith(opening) or not stripped.endswith(closing):
            return None

        return stripped[len(opening):-len(closing)]

    def process_literal(
        self,
        text: str,
        pattern: 'LiteralPattern',
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
            pattern: LiteralPattern that matched this node
            tree_sitter_type: Tree-sitter node type (for wrapper detection)
            start_byte: Start position
            end_byte: End position
            token_budget: Maximum tokens for content
            base_indent: Line indentation
            element_indent: Element indentation

        Returns:
            TrimResult if trimming is beneficial, None otherwise
        """
        # Parse literal with known pattern
        parsed = self.parse_literal_with_pattern(
            text, pattern, start_byte, end_byte,
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
        elif parsed.category == LiteralCategory.BLOCK_INIT:
            # BLOCK_INIT requires special handling with node access
            # This path should not be reached from process_literal
            raise RuntimeError(
                "BLOCK_INIT patterns must be processed via process_block_init_node, "
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
        interpolation_markers = self._get_active_interpolation_markers(parsed)
        if interpolation_markers:
            truncated = self._adjust_for_interpolation(
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

        content_budget = max(1, token_budget - overhead)

        # Select elements with DFS (budget-aware nested selection)
        # For preserve_all_keys: keep all top-level keys, but apply DFS to nested values
        selection = self.selector.select_dfs(
            elements, content_budget,
            parser=parser,
            min_keep=pattern.min_elements,
            tuple_size=pattern.tuple_size,
            preserve_top_level_keys=pattern.preserve_all_keys,
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
        pattern: LiteralPattern,
        node,  # tree_sitter Node
        doc,  # TreeSitterDocument
        token_budget: int,
        base_indent: str = "",
    ) -> Optional[TrimResult]:
        """
        Process BLOCK_INIT pattern with direct node access.

        This is a separate entry point for BLOCK_INIT patterns
        because they require AST navigation, not just text processing.

        Args:
            pattern: LiteralPattern with BLOCK_INIT category
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
        result = self.block_init_processor.process(
            pattern=pattern,
            node=node,
            doc=doc,
            token_budget=token_budget,
            base_indent=base_indent,
        )

        # Return as-is: (TrimResult, nodes_used) or None
        return result

    def process_ast_based_sequence(
        self,
        pattern: 'LiteralPattern',
        node,  # tree_sitter Node
        doc,  # TreeSitterDocument
        token_budget: int,
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
            pattern: LiteralPattern that matched this node
            node: Tree-sitter node representing the sequence
            doc: Tree-sitter document
            token_budget: Token budget
            base_indent: Base indentation
            element_indent: Element indentation

        Returns:
            TrimResult if optimization applied, None otherwise
        """

        # Get all child string nodes that match string patterns
        # Use the query to find string nodes
        string_patterns = [p for p in self.descriptor.patterns if p.category == LiteralCategory.STRING]

        # Collect all string child nodes by querying each string pattern
        child_strings = []
        child_string_set = set()  # Track by (start, end) to avoid duplicates

        for str_pattern in string_patterns:
            matched_nodes = doc.query_nodes(str_pattern.query, "lit")
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
        placeholder = pattern.placeholder_template
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
        comment_text = f"{pattern.comment_name} (−{saved_tokens} tokens)"

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

    def _get_active_interpolation_markers(
        self,
        parsed: ParsedLiteral,
    ) -> list[tuple]:
        """
        Get interpolation markers that are active for this specific string.

        Some markers only apply when the string has specific characteristics:
        - Python {}: only for f-strings (opening starts with f/F)
        - Rust {}: only for format strings (we can't detect reliably)
        - JS ${}: for template strings (backticks)

        For markers with a prefix (like $), they're self-checking via the prefix.
        For markers without prefix, the pattern's interpolation_active callback
        determines whether the marker applies to a specific string.

        Args:
            parsed: The parsed literal

        Returns:
            List of active interpolation markers
        """
        markers = parsed.pattern.interpolation_markers
        if not markers:
            return []

        # Check if pattern has an activation callback
        activation_callback = parsed.pattern.interpolation_active

        active_markers = []

        for marker in markers:
            prefix, opening, closing = marker

            # Markers with a prefix (like "$" in "${...}") are self-checking
            if prefix:
                active_markers.append(marker)
            else:
                # Empty prefix markers - use callback if available
                if activation_callback is not None:
                    if activation_callback(parsed.opening, parsed.content):
                        active_markers.append(marker)
                else:
                    # No callback - assume marker is always active
                    active_markers.append(marker)

        return active_markers

    def _adjust_for_interpolation(
        self,
        truncated: str,
        original: str,
        markers: list[tuple],
    ) -> str:
        """
        Adjust truncation point to respect string interpolation boundaries.

        If truncation lands inside an interpolator like ${...} or #{...},
        extend to include the complete interpolator to preserve valid AST.

        Args:
            truncated: The truncated string content
            original: The original full string content
            markers: List of (prefix, opening, closing) tuples

        Returns:
            Adjusted truncated string that doesn't break interpolators
        """
        cut_pos = len(truncated)

        # Find all interpolation regions in original
        interpolators = self._find_interpolation_regions(original, markers)

        for start, end in interpolators:
            # If cut position is inside this interpolator
            if start < cut_pos <= end:
                # Extend to include the full interpolator
                return original[:end]

        return truncated

    def _find_interpolation_regions(
        self,
        content: str,
        markers: list[tuple],
    ) -> list[tuple[int, int]]:
        """
        Find all string interpolation regions in content.

        Args:
            content: String content to search
            markers: List of (prefix, opening, closing) tuples

        Returns:
            List of (start, end) tuples for each interpolator
        """
        regions = []
        i = 0

        while i < len(content):
            for prefix, opening, closing in markers:
                full_opener = prefix + opening

                # Case 1: Bracketed interpolation like ${...}, #{...}, {...}
                if opening and closing:
                    if content[i:].startswith(full_opener):
                        brace_pos = i + len(prefix)
                        end = self._find_matching_brace(content, brace_pos)
                        if end != -1:
                            regions.append((i, end + 1))
                            i = end + 1
                            break
                # Case 2: Simple identifier like $name (no braces)
                elif prefix and not opening:
                    if content[i:].startswith(prefix):
                        # Find end of identifier
                        end = self._find_identifier_end(content, i + len(prefix))
                        if end > i + len(prefix):
                            regions.append((i, end))
                            i = end
                            break
            else:
                i += 1

        return regions

    def _find_identifier_end(self, content: str, start: int) -> int:
        """
        Find the end of an identifier starting at position.

        Identifiers: letters, digits, underscores (first char not digit).

        Args:
            content: String content
            start: Position where identifier starts

        Returns:
            Position after the last character of identifier
        """
        i = start
        if i >= len(content):
            return start

        # First char must be letter or underscore
        if not (content[i].isalpha() or content[i] == '_'):
            return start

        i += 1
        while i < len(content) and (content[i].isalnum() or content[i] == '_'):
            i += 1

        return i

    def _find_matching_brace(self, content: str, start: int) -> int:
        """
        Find the matching closing brace for an opening brace at start position.

        Handles nested braces and string literals inside interpolators.

        Args:
            content: String content
            start: Position of opening brace

        Returns:
            Position of matching closing brace, or -1 if not found
        """
        if start >= len(content) or content[start] != '{':
            return -1

        depth = 1
        i = start + 1
        in_string = False
        string_char = None

        while i < len(content) and depth > 0:
            char = content[i]

            # Handle string literals inside interpolator
            if not in_string and char in '"\'`':
                in_string = True
                string_char = char
            elif in_string and char == string_char:
                # Check for escape
                if i > 0 and content[i-1] != '\\':
                    in_string = False
                    string_char = None
            elif not in_string:
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1

            i += 1

        if depth == 0:
            return i - 1  # Position of closing brace

        return -1
