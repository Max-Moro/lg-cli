"""
Literal optimization pipeline.

This module serves as the single entry point for literal optimization.
Orchestrates the two-pass literal processing workflow.
"""

from __future__ import annotations

from typing import cast, Optional

from lg.adapters.code_model import LiteralConfig
from lg.adapters.context import ProcessingContext
from .formatter import ResultFormatter
from .parser import LiteralParser
from .selector import BudgetSelector, Selection
from ..components import (
    ASTSequenceProcessor,
    BlockInitProcessor,
)
from ..patterns import (
    LiteralProfile,
    BlockInitProfile,
    CollectionProfile,
    StringProfile,
    ParsedLiteral,
    TrimResult,
    MappingProfile,
    FactoryProfile,
)
from ..utils.element_parser import ElementParser, Element, ParseConfig
from ..utils.interpolation import InterpolationHandler


class LiteralPipeline:
    """
    Main pipeline for literal optimization.

    Orchestrates two-pass literal processing:
    - Pass 1: String literals (inline truncation)
    - Pass 2: Collections (DFS with nested optimization)
    """

    def __init__(self, cfg: LiteralConfig, adapter):
        """
        Initialize pipeline.

        Args:
            cfg: Literal configuration
            adapter: Language adapter
        """
        self.cfg = cfg
        from ....code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)

        # Get descriptor from adapter
        self.descriptor = self.adapter.create_literal_descriptor()

        # Get comment style from adapter
        comment_style: tuple[str, tuple[str, str]] = cast(tuple[str, tuple[str, str]], self.adapter.get_comment_style()[:2])
        self.single_comment = comment_style[0]
        self.block_comment = comment_style[1]

        # Cache parsers for different patterns
        self._parsers: dict[str, ElementParser] = {}

        # =================================
        # Universal processing stages of the pipeline
        # =================================

        self.literal_parser = LiteralParser(self.adapter.tokenizer)
        self.selector = BudgetSelector(self.adapter.tokenizer)
        self.formatter = ResultFormatter(self.adapter.tokenizer, comment_style)
        self.interpolation = InterpolationHandler()

        # =================================
        # Special components (ordered by priority)
        # =================================

        # Collect all profiles for nested literal detection
        all_profiles = (
            self.descriptor.string_profiles +
            self.descriptor.sequence_profiles +
            self.descriptor.mapping_profiles +
            self.descriptor.factory_profiles +
            self.descriptor.block_init_profiles
        )

        # Create component instances
        self.special_components = [
            ASTSequenceProcessor(
                self.adapter.tokenizer,
                self.descriptor.string_profiles
            ),
            BlockInitProcessor(
                self.adapter.tokenizer,
                all_profiles,
                self._process_literal_impl,
                comment_style
            ),
        ]

    def apply(self, context: ProcessingContext) -> None:
        """
        Apply literal optimization using two-pass approach.

        Pass 1: Process strings (top-level only)
        Pass 2: Process collections with DFS (nested structures)

        Args:
            context: Processing context with document
        """
        # Get max_tokens from config
        max_tokens = self.cfg.max_tokens
        if max_tokens is None:
            return  # Optimization disabled

        # Two-pass approach for orthogonal string/collection processing

        # Pass 1: Process all string profiles
        self._process_strings(context, max_tokens)

        # Pass 2: Process all collection profiles
        self._process_collections(context, max_tokens)

    def _process_strings(
        self,
        context: ProcessingContext,
        max_tokens: int,
    ) -> None:
        """
        Pass 1: Process string literals.

        Args:
            context: Processing context
            max_tokens: Token budget
        """
        # Collect AST-extraction collection nodes to skip their children
        # Only SequenceProfile can have requires_ast_extraction=True
        ast_extraction_nodes_set = set()

        for seq_profile in self.descriptor.sequence_profiles:
            if seq_profile.requires_ast_extraction:
                seq_nodes = context.doc.query_nodes(seq_profile.query, "lit")
                for seq_node in seq_nodes:
                    ast_extraction_nodes_set.add((seq_node.start_byte, seq_node.end_byte))

        # Process each string profile
        for profile in self.descriptor.string_profiles:
            nodes = context.doc.query_nodes(profile.query, "lit")

            # Find top-level strings (not nested, not in AST-extraction collections)
            top_level_strings = []
            for i, node in enumerate(nodes):
                start_byte, end_byte = context.doc.get_node_range(node)

                # Check if nested in another string
                is_nested = any(
                    j != i and
                    nodes[j].start_byte <= start_byte and
                    nodes[j].end_byte >= end_byte
                    for j in range(len(nodes))
                )
                if is_nested:
                    continue

                # Check if parent is AST-extraction collection
                if node.parent:
                    parent_range = (node.parent.start_byte, node.parent.end_byte)
                    if parent_range in ast_extraction_nodes_set:
                        continue

                top_level_strings.append(node)

            # Process each top-level string
            for node in top_level_strings:
                # Skip docstrings
                if self.adapter.is_docstring_node(node, context.doc):
                    continue

                # Get node info
                literal_text = context.doc.get_node_text(node)
                token_count = self.adapter.tokenizer.count_text_cached(literal_text)

                # Skip if within budget
                if token_count <= max_tokens:
                    continue

                # Process node with unified entry point
                result = self._process_literal(context, node, profile, max_tokens)

                if result and result.saved_tokens > 0:
                    self._apply_result(context, node, result, literal_text)

    def _process_collections(
        self,
        context: ProcessingContext,
        max_tokens: int,
    ) -> None:
        """
        Pass 2: Process collection literals with DFS.

        Args:
            context: Processing context
            max_tokens: Token budget
        """
        # Process each profile type through unified entry point

        for profile in self.descriptor.sequence_profiles:
            self._process_profile(context, profile, max_tokens)

        for profile in self.descriptor.mapping_profiles:
            self._process_profile(context, profile, max_tokens)

        for profile in self.descriptor.factory_profiles:
            self._process_profile(context, profile, max_tokens)

        for profile in self.descriptor.block_init_profiles:
            self._process_profile(context, profile, max_tokens)

    def _process_profile(
        self,
        context: ProcessingContext,
        profile: LiteralProfile,
        max_tokens: int,
    ) -> None:
        """
        Common pipeline logic for processing any profile type.

        Args:
            context: Processing context
            profile: Profile to process
            max_tokens: Token budget
        """
        nodes = context.doc.query_nodes(profile.query, "lit")

        # Deduplicate by coordinates
        seen_coords = set()
        unique_nodes = []
        for node in nodes:
            coords = (node.start_byte, node.end_byte)
            if coords not in seen_coords:
                seen_coords.add(coords)
                unique_nodes.append(node)

        # Find top-level collections
        top_level = []
        for i, node in enumerate(unique_nodes):
            start_byte, end_byte = context.doc.get_node_range(node)

            # Check if nested in another collection
            is_nested = any(
                j != i and
                unique_nodes[j].start_byte <= start_byte and
                unique_nodes[j].end_byte >= end_byte
                for j in range(len(unique_nodes))
            )
            if is_nested:
                continue

            top_level.append(node)

        # Process each top-level collection
        for node in top_level:
            literal_text = context.doc.get_node_text(node)
            token_count = self.adapter.tokenizer.count_text_cached(literal_text)

            # Skip budget check for BLOCK_INIT (handles budget internally)
            if token_count > max_tokens or isinstance(profile, BlockInitProfile):
                # Call unified processing entry point
                result = self._process_literal(context, node, profile, max_tokens)

                # Apply if tokens saved
                if result and result.saved_tokens > 0:
                    self._apply_result(context, node, result, literal_text)

    def _process_literal(
        self,
        context: ProcessingContext,
        node,
        profile: LiteralProfile,
        budget: int
    ) -> Optional[TrimResult]:
        """
        Unified literal processing entry point.

        Only coordinates stages and components - no detailed logic.

        Args:
            context: Processing context
            node: Tree-sitter node
            profile: Literal profile
            budget: Token budget

        Returns:
            TrimResult if optimization applied, None otherwise
        """
        # Try special components first (in priority order)
        for component in self.special_components:
            if component.can_handle(profile, node, context.doc):
                return component.process(
                    node,
                    context.doc,
                    context.raw_text,
                    profile,
                    budget
                )

        # Standard path through stages
        parsed = self.literal_parser.parse_from_node(
            node, context.doc, context.raw_text, profile
        )

        if not parsed or parsed.original_tokens <= budget:
            return None

        # Route by profile type
        if isinstance(profile, StringProfile):
            return self._process_string(parsed, budget)
        else:
            return self._process_collection(parsed, budget)

    def _apply_result(
        self,
        context: ProcessingContext,
        node,
        result: TrimResult,
        original_text: str
    ) -> None:
        """
        Unified result application.

        Args:
            context: Processing context
            node: Tree-sitter node (or list of nodes for single-node replacement)
            result: Trim result to apply
            original_text: Original text for metrics
        """
        # Determine nodes to replace from result or from node parameter
        if result.nodes_to_replace:
            # Use nodes from TrimResult (composing replacement)
            nodes = result.nodes_to_replace
            start_byte = nodes[0].start_byte
            end_byte = nodes[-1].end_byte

            context.editor.add_replacement_composing_nested(
                start_byte, end_byte, result.trimmed_text,
                edit_type="literal_trimmed"
            )
        else:
            # Simple single-node replacement
            start_byte, end_byte = context.doc.get_node_range(node)
            context.editor.add_replacement_composing_nested(
                start_byte, end_byte, result.trimmed_text,
                edit_type="literal_trimmed"
            )

        # Add comment if needed
        placeholder_style = self.adapter.cfg.placeholders.style
        if placeholder_style != "none" and result.comment_text:
            text_after = context.raw_text[end_byte:]
            formatted_comment, offset = self.formatter._format_comment_for_context(
                text_after, result.comment_text
            )
            context.editor.add_insertion(
                end_byte + offset,
                formatted_comment,
                edit_type="literal_comment"
            )

        # Update metrics
        context.metrics.mark_element_removed("literal")
        context.metrics.add_chars_saved(len(original_text) - len(result.trimmed_text))


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
            # Use factory method to create config with automatic wrapper collection
            config = ParseConfig.from_profile_and_descriptor(profile, self.descriptor)
            self._parsers[key] = ElementParser(config)

        return self._parsers[key]

    def _process_literal_impl(
        self,
        node,
        doc,
        source_text: str,
        profile: LiteralProfile,
        token_budget: int = 0,
    ) -> Optional[TrimResult]:
        """
        Process a literal and return trimmed result if beneficial.

        Args:
            node: Tree-sitter node representing the literal
            doc: Tree-sitter document
            source_text: Full source text
            profile: LiteralProfile (StringProfile, SequenceProfile, etc.) that matched this node
            token_budget: Maximum tokens for content

        Returns:
            TrimResult if trimming is beneficial, None otherwise
        """
        # Use profile-based parsing with automatic indent detection
        parsed = self.literal_parser.parse_from_node(
            node, doc, source_text, profile
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
            # This path should not be reached from _process_literal_impl
            raise RuntimeError(
                "BLOCK_INIT profiles must be processed via LiteralPipeline._process_block_init_node, "
                "not _process_literal_impl"
            )
        else:
            return self._process_collection(cast(ParsedLiteral[CollectionProfile], parsed), token_budget)

    def _process_string(
        self,
        parsed: ParsedLiteral[StringProfile],
        budget: int
    ) -> Optional[TrimResult]:
        """
        Process string literals through standard stages.

        Args:
            parsed: Parsed string literal
            budget: Token budget

        Returns:
            TrimResult if optimization applied
        """
        # Calculate overhead
        overhead = self.selector.calculate_overhead(
            parsed.opening, parsed.closing, "…",
            parsed.is_multiline, parsed.element_indent
        )
        content_budget = max(1, budget - overhead)

        # Truncate content
        truncated = self.adapter.tokenizer.truncate_to_tokens(
            parsed.content, content_budget
        )

        if len(truncated) >= len(parsed.content):
            return None

        # Adjust for interpolation
        markers = self.interpolation.get_active_markers(
            parsed.profile, parsed.opening, parsed.content
        )
        if markers:
            truncated = self.interpolation.adjust_truncation(
                truncated, parsed.content, markers
            )

        # Create pseudo-selection and format
        kept_element = Element(
            text=truncated,
            raw_text=truncated,
            start_offset=0,
            end_offset=len(truncated),
        )
        removed_element = Element(
            text="...", raw_text="...",
            start_offset=0, end_offset=0
        )

        selection = Selection(
            kept_elements=[kept_element],
            removed_elements=[removed_element],
            total_count=1,
            tokens_kept=self.adapter.tokenizer.count_text_cached(truncated),
            tokens_removed=parsed.original_tokens - self.adapter.tokenizer.count_text_cached(truncated),
        )

        # Format result
        formatted = self.formatter.format(parsed, selection)

        trimmed_tokens = self.adapter.tokenizer.count_text_cached(formatted.text)

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


    def _process_collection(
        self,
        parsed: ParsedLiteral[CollectionProfile],
        budget: int
    ) -> Optional[TrimResult]:
        """
        Process collections through selector + formatter.

        Args:
            parsed: Parsed collection literal
            budget: Token budget

        Returns:
            TrimResult if optimization applied
        """
        parser = self._get_parser_for_profile(parsed.profile)
        elements = parser.parse(parsed.content)

        if not elements:
            return None

        # Calculate overhead
        placeholder = parsed.profile.placeholder_template
        overhead = self.selector.calculate_overhead(
            parsed.opening, parsed.closing, placeholder,
            parsed.is_multiline, parsed.element_indent
        )
        content_budget = max(1, budget - overhead)

        # Select elements with DFS
        selection = self.selector.select_dfs(
            elements, content_budget,
            profile=parsed.profile,
            get_parser_func=self._get_parser_for_profile,
            min_keep=parsed.profile.min_elements,
            tuple_size=parsed.profile.tuple_size if isinstance(parsed.profile, FactoryProfile) else 1,
            preserve_top_level_keys=parsed.profile.preserve_all_keys if isinstance(parsed.profile, MappingProfile) else False,
        )

        if not selection.has_removals:
            return None

        # Format result
        formatted = self.formatter.format_dfs(parsed, selection, parser)

        trimmed_tokens = self.adapter.tokenizer.count_text_cached(formatted.text)

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
