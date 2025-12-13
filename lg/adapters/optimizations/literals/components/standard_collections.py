"""
Standard collections processor component.

Handles processing of standard collection literals with:
- Budget-aware element selection
- Multiline/single-line formatting
"""

from __future__ import annotations

from typing import Optional

from lg.stats.tokenizer import TokenService
from .base import LiteralProcessor
from ..descriptor import LanguageLiteralDescriptor
from ..patterns import (
    LiteralProfile,
    CollectionProfile,
    SequenceProfile,
    MappingProfile,
    FactoryProfile,
    TrimResult,
)
from ..processing.collection_formatter import CollectionFormatter
from ..processing.parser import LiteralParser
from ..processing.selector import BudgetSelector
from ..utils import CommentFormatter
from ..utils.element_parser import ElementParser, ParseConfig


class StandardCollectionsProcessor(LiteralProcessor):
    """
    Processes standard collection literals.

    Autonomous component that:
    - Parses collection structure
    - Applies budget-aware selection
    - Formats result
    """

    def __init__(
        self,
        tokenizer: TokenService,
        literal_parser: LiteralParser,
        selector: BudgetSelector,
        comment_formatter: CommentFormatter,
        descriptor: LanguageLiteralDescriptor,
    ):
        """
        Initialize processor.

        Factory wrappers are pre-computed once during initialization
        for performance (avoids O(N × P) recalculation where N is number
        of literals and P is number of profiles).

        Args:
            tokenizer: Token counting service
            literal_parser: Shared LiteralParser instance
            selector: BudgetSelector instance
            comment_formatter: Shared CommentFormatter instance
            descriptor: Language literal descriptor (for ElementParser factory)
        """
        self.tokenizer = tokenizer
        self.parser = literal_parser
        self.selector = selector
        self.collection_formatter = CollectionFormatter(tokenizer, comment_formatter)
        self.descriptor = descriptor

        self.factory_wrappers = ElementParser.collect_factory_wrappers_from_descriptor(
            self.descriptor
        )

        # Cache parsers for different patterns
        self._parsers: dict[str, ElementParser] = {}

    def can_handle(
        self,
        profile: LiteralProfile,
        node,
        doc,
    ) -> bool:
        """
        Check if this component is applicable to the given literal.

        StandardCollectionsProcessor is applicable to:
        - SequenceProfile (without requires_ast_extraction flag)
        - MappingProfile
        - FactoryProfile

        Args:
            profile: Literal profile
            node: Tree-sitter node (unused, kept for interface consistency)
            doc: Tree-sitter document (unused, kept for interface consistency)

        Returns:
            True if this component should handle the literal
        """
        # SequenceProfile без requires_ast_extraction
        if isinstance(profile, SequenceProfile):
            return not profile.requires_ast_extraction

        # MappingProfile и FactoryProfile
        return isinstance(profile, (MappingProfile, FactoryProfile))

    def process(
        self,
        node,
        doc,
        source_text: str,
        profile: CollectionProfile,
        token_budget: int,
    ) -> Optional[TrimResult]:
        """
        Full autonomous processing of collection literal.

        Component itself:
        - Uses LiteralParser to extract structure
        - Parses elements
        - Applies budget-aware selection
        - Formats result

        Args:
            node: Tree-sitter node
            doc: Tree-sitter document
            source_text: Full source text
            profile: CollectionProfile (Sequence/Mapping/Factory)
            token_budget: Token budget

        Returns:
            TrimResult if optimization applied, None otherwise
        """
        # Parse literal structure
        parsed = self.parser.parse_from_node(node, doc, source_text, profile)

        if not parsed or parsed.original_tokens <= token_budget:
            return None

        # Calculate overhead
        placeholder = profile.placeholder_template
        overhead = self.selector.calculate_overhead(
            parsed.opening, parsed.closing, placeholder,
            parsed.is_multiline, parsed.element_indent
        )
        content_budget = max(1, token_budget - overhead)

        # Parse elements
        parser = self._get_parser_for_profile(profile)
        elements = parser.parse(parsed.content)

        if not elements:
            return None

        # Select elements
        tuple_size = profile.tuple_size if isinstance(profile, FactoryProfile) else 1
        preserve_keys = profile.preserve_all_keys if isinstance(profile, MappingProfile) else False

        selection = self.selector.select(
            elements, content_budget,
            parser,
            min_keep=profile.min_elements,
            tuple_size=tuple_size,
            preserve_top_level_keys=preserve_keys,
        )

        if not selection.has_removals:
            return None

        # Format result
        formatted = self.collection_formatter.format(parsed, selection, parser)

        # Build final result
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

    def _get_parser_for_profile(self, profile: CollectionProfile) -> ElementParser:
        """
        Get or create parser for a profile.

        Args:
            profile: CollectionProfile to create parser for

        Returns:
            ElementParser configured for this profile
        """
        # Create cache key from profile attributes
        separator = profile.separator
        kv_separator = profile.kv_separator if isinstance(profile, (MappingProfile, FactoryProfile)) else None
        tuple_size = profile.tuple_size if isinstance(profile, FactoryProfile) else 1

        key = f"{separator}:{kv_separator}:{tuple_size}"

        if key not in self._parsers:
            # Use factory method with pre-computed factory_wrappers
            config = ParseConfig(
                separator=separator,
                kv_separator=kv_separator,
                preserve_whitespace=False,
                factory_wrappers=self.factory_wrappers,
            )
            self._parsers[key] = ElementParser(config)

        return self._parsers[key]
