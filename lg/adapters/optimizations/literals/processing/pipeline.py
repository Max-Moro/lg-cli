"""
Literal optimization pipeline.

This module serves as the single entry point for literal optimization.
Orchestrates the two-pass literal processing workflow.
"""

from __future__ import annotations

from typing import cast, Optional, List

from lg.adapters.code_model import LiteralConfig
from lg.adapters.context import ProcessingContext
from .parser import LiteralParser
from .selector import BudgetSelector
from ..components import (
    LiteralProcessor,
    ASTSequenceProcessor,
    JavaDoubleBraceProcessor,
    RustLetGroupProcessor,
    StringLiteralProcessor,
    StandardCollectionsProcessor,
)
from ..patterns import (
    LiteralProfile,
    BlockInitProfile,
    StringProfile,
    TrimResult,
    SequenceProfile,
)
from ..utils.comment_formatter import CommentFormatter


class LiteralPipeline:
    """
    Main pipeline for literal optimization.

    Orchestrates single-pass unified processing for all literal types
    (strings, sequences, mappings, factories, and block initializations).
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

        # Shared services
        self.selector = BudgetSelector(self.adapter.tokenizer)
        self.comment_formatter = CommentFormatter(comment_style)
        self.literal_parser = LiteralParser(self.adapter.tokenizer)

        # =================================
        # Processing components (ordered by priority)
        # =================================

        # Create component instances
        # Order matters: more specific components first
        self.special_components: List[LiteralProcessor] = [
            # Special cases
            ASTSequenceProcessor(
                self.adapter.tokenizer,
                [p for p in self.descriptor.profiles if isinstance(p, StringProfile)]
            ),
            JavaDoubleBraceProcessor(
                self.adapter.tokenizer,
                self.descriptor.profiles,
                self._process_literal,
                comment_style
            ),
            RustLetGroupProcessor(
                self.adapter.tokenizer,
                self.descriptor.profiles,
                self._process_literal,
                comment_style
            ),

            # Standard cases
            StringLiteralProcessor(
                self.adapter.tokenizer,
                self.literal_parser,
                self.comment_formatter
            ),
            StandardCollectionsProcessor(
                self.adapter.tokenizer,
                self.literal_parser,
                self.selector,
                self.comment_formatter,
                self.descriptor
            ),
        ]

    def apply(self, context: ProcessingContext) -> None:
        """
        Apply literal optimization using unified single-pass approach.

        Args:
            context: Processing context with document
        """
        # Get max_tokens from config
        max_tokens = self.cfg.max_tokens
        if max_tokens is None:
            return  # Optimization disabled

        # Process all profiles in single pass
        for profile in self.descriptor.profiles:
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
        # Collect AST-extraction collection nodes to skip their children
        ast_extraction_nodes_set = set()

        # Only SequenceProfile can have requires_ast_extraction=True
        for p in self.descriptor.profiles:
            if isinstance(p, SequenceProfile) and p.requires_ast_extraction:
                seq_nodes = context.doc.query_nodes(p.query, "lit")
                for seq_node in seq_nodes:
                    ast_extraction_nodes_set.add((seq_node.start_byte, seq_node.end_byte))

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

            # For StringProfile: skip strings that are children of AST-extraction sequences
            if isinstance(profile, StringProfile) and node.parent:
                parent_range = (node.parent.start_byte, node.parent.end_byte)
                if parent_range in ast_extraction_nodes_set:
                    continue  # Skip - will be processed as whole sequence

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
                result = self._process_literal(
                    node, context.doc, context.raw_text, profile, max_tokens
                )

                # Apply if tokens saved
                if result and result.saved_tokens > 0:
                    self._apply_result(context, node, result, literal_text)

    def _process_literal(
        self,
        node,
        doc,
        source_text: str,
        profile: LiteralProfile,
        budget: int
    ) -> Optional[TrimResult]:
        """
        Unified literal processing entry point.

        Called both from the pipeline and recursively from components.
        Delegates all processing to specialized components.

        Args:
            node: Tree-sitter node representing the literal
            doc: Tree-sitter document
            source_text: Full source text
            profile: Literal profile (StringProfile, SequenceProfile, etc.)
            budget: Token budget

        Returns:
            TrimResult if optimization applied, None otherwise
        """
        # Try components in priority order
        for component in self.special_components:
            if component.can_handle(profile, node, doc):
                return component.process(
                    node,
                    doc,
                    source_text,
                    profile,
                    budget
                )

        # No component handled this literal
        return None

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
            node: Tree-sitter node
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
            formatted_comment, offset = self.comment_formatter.format_for_context(
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
