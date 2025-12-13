"""
Literal optimization pipeline.

This module serves as the single entry point for literal optimization.
Orchestrates the literal processing workflow.
"""

from __future__ import annotations

from typing import cast, Optional, List

from tree_sitter._binding import Node

from .parser import LiteralParser
from .selector import BudgetSelector
from ..components import *
from ..patterns import (
    LiteralProfile,
    BlockInitProfile,
    StringProfile,
    TrimResult,
    SequenceProfile,
)
from ..utils.comment_formatter import CommentFormatter
from ....code_model import LiteralConfig
from ....context import ProcessingContext
from ....tree_sitter_support import TreeSitterDocument, Node


class LiteralPipeline:
    """
    Main pipeline for literal optimization.

    Orchestrates single-pass unified processing for all literal types
    (strings, sequences, mappings, factories, and block initializations).
    """

    def __init__(self, adapter):
        """
        Initialize pipeline.

        Args:
            adapter: Language adapter
        """
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
                comment_style
            ),
            RustLetGroupProcessor(
                self.adapter.tokenizer,
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

    def apply(self, context: ProcessingContext, cfg: LiteralConfig) -> None:
        """
        Apply literal optimization using unified single-pass approach.

        Args:
            context: Processing context with document
            cfg: Literal configuration
        """
        # Get max_tokens from config
        max_tokens = cfg.max_tokens
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

        # Process all nodes (not just top-level) in inside-out order
        # This allows add_replacement_composing_nested to compose correctly:
        # inner nodes are processed first, outer nodes compose with their edits

        def node_depth(node):
            """Calculate nesting depth of a node (distance from root)."""
            depth = 0
            current = node.parent
            while current:
                depth += 1
                current = current.parent
            return depth

        # For StringProfile: skip strings that are children of AST-extraction sequences
        # (they will be processed as part of the whole sequence)
        nodes_to_process = []
        for node in unique_nodes:
            if isinstance(profile, StringProfile) and node.parent:
                parent_range = (node.parent.start_byte, node.parent.end_byte)
                if parent_range in ast_extraction_nodes_set:
                    continue  # Skip - will be processed as whole sequence
            nodes_to_process.append(node)

        # Sort by depth (deepest first), then by position (left to right)
        # Deepest-first ensures nested edits are created before parent edits
        nodes_to_process.sort(key=lambda n: (-node_depth(n), n.start_byte))

        # Process each node in inside-out order
        for node in nodes_to_process:
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
        node: Node,
        doc: TreeSitterDocument,
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
