"""
String literal processor component.

Handles processing of string literals with:
- Content truncation within token budget
- Interpolation boundary detection
- Inline placeholder insertion
"""

from __future__ import annotations

from typing import Optional

from lg.stats.tokenizer import TokenService
from ..patterns import LiteralProfile, StringProfile, TrimResult
from ..processing.parser import LiteralParser
from ..processing.selector import Selection
from ..processing.string_formatter import StringFormatter
from ..processor import LiteralProcessor
from ..utils.element_parser import Element
from ..utils.interpolation import InterpolationHandler
from ....tree_sitter_support import TreeSitterDocument, Node


class StringLiteralProcessor(LiteralProcessor):
    """
    Processes string literals with truncation and interpolation handling.

    Autonomous component that:
    - Parses string content
    - Truncates to token budget
    - Adjusts for interpolation boundaries
    - Formats result with inline placeholder
    """

    def __init__(
        self,
        tokenizer: TokenService,
        literal_parser: LiteralParser,
    ):
        """
        Initialize processor.

        Args:
            tokenizer: Token counting service
            literal_parser: Shared LiteralParser instance
        """
        self.tokenizer = tokenizer
        self.interpolation = InterpolationHandler()
        self.parser = literal_parser
        self.string_formatter = StringFormatter(tokenizer)

    def can_handle(self, profile: LiteralProfile, node: Node, doc: TreeSitterDocument) -> bool:
        """
        Check if this component is applicable to the given literal.

        StringLiteralProcessor is applicable only to StringProfile.

        Args:
            profile: Literal profile
            node: Tree-sitter node (unused, kept for interface consistency)
            doc: Tree-sitter document (unused, kept for interface consistency)

        Returns:
            True if this component should handle the literal
        """
        return isinstance(profile, StringProfile)

    def process(
        self,
        node: Node,
        doc: TreeSitterDocument,
        source_text: str,
        profile: StringProfile,
        token_budget: int,
    ) -> Optional[TrimResult]:
        """
        Full autonomous processing of string literal.

        Component itself:
        - Uses LiteralParser to extract structure
        - Truncates content to budget
        - Adjusts for interpolation
        - Formats result

        Args:
            node: Tree-sitter node
            doc: Tree-sitter document
            source_text: Full source text
            profile: StringProfile
            token_budget: Token budget

        Returns:
            TrimResult if optimization applied, None otherwise
        """
        # Parse literal structure
        parsed = self.parser.parse_from_node(node, doc, source_text, profile)

        if not parsed or parsed.original_tokens <= token_budget:
            return None

        # Calculate overhead for placeholder
        placeholder = profile.placeholder_template
        overhead_text = f"{parsed.opening}{placeholder}{parsed.closing}"
        overhead = self.tokenizer.count_text_cached(overhead_text)
        content_budget = max(1, token_budget - overhead)

        # Truncate content
        truncated = self.tokenizer.truncate_to_tokens(parsed.content, content_budget)

        # Check if truncation happened
        if len(truncated) >= len(parsed.content):
            return None

        # Adjust for interpolation
        markers = self.interpolation.get_active_markers(
            profile, parsed.opening
        )
        if markers:
            truncated = self.interpolation.adjust_truncation(
                truncated, parsed.content, markers
            )

        # Create pseudo-selection for formatter
        kept_element = Element(
            text=truncated,
            raw_text=truncated,
            start_offset=0,
            end_offset=len(truncated),
        )
        removed_element = Element(text="", raw_text="", start_offset=0, end_offset=0)

        selection = Selection(
            kept_elements=[kept_element],
            removed_elements=[removed_element],
            total_count=1,
            tokens_kept=self.tokenizer.count_text_cached(truncated),
            tokens_removed=parsed.original_tokens - self.tokenizer.count_text_cached(truncated),
        )

        # Format result
        formatted = self.string_formatter.format(parsed, selection)

        # Build final result
        trimmed_tokens = self.tokenizer.count_text_cached(formatted.text)

        return TrimResult(
            trimmed_text=formatted.text,
            original_tokens=parsed.original_tokens,
            trimmed_tokens=trimmed_tokens,
            saved_tokens=parsed.original_tokens - trimmed_tokens,
            elements_kept=selection.kept_count,
            elements_removed=selection.removed_count,
        )
