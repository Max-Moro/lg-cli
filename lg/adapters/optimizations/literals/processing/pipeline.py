"""
Literal optimization pipeline.

This module serves as the single entry point for literal optimization.
Orchestrates the literal processing workflow.
"""

from __future__ import annotations

from typing import cast, Optional, List

from .parser import LiteralParser
from .selector import BudgetSelector
from ..components import (
    ASTSequenceProcessor,
    BlockInitProcessorBase,
    StandardCollectionsProcessor,
    StringLiteralProcessor,
)
from ..patterns import (
    LiteralProfile,
    BlockInitProfile,
    StringProfile,
    SequenceProfile,
    TrimResult,
    PlaceholderPosition,
)
from ..processor import LiteralProcessor
from ....code_model import LiteralConfig
from ....context import ProcessingContext
from ....tree_sitter_support import TreeSitterDocument, Node
from ....placeholders import PlaceholderAction


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

        # Get comment style from adapter (now returns CommentStyle directly)
        comment_style = self.adapter.comment_style

        # Shared services
        self.selector = BudgetSelector(self.adapter.tokenizer)
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
        ]

        # Add language-specific processor if provided by descriptor
        if self.descriptor.custom_processor:
            # Check which base class to determine constructor signature
            if issubclass(self.descriptor.custom_processor, BlockInitProcessorBase):
                # BlockInit-based processors need tokenizer + comment_style
                processor_instance = self.descriptor.custom_processor(
                    self.adapter.tokenizer,
                    comment_style
                )
            elif issubclass(self.descriptor.custom_processor, StandardCollectionsProcessor):
                # StandardCollections-based processors need full set of services
                processor_instance = self.descriptor.custom_processor(
                    self.adapter.tokenizer,
                    self.literal_parser,
                    self.selector,
                    comment_style,
                    self.descriptor
                )
            elif issubclass(self.descriptor.custom_processor, StringLiteralProcessor):
                # StringLiteral-based processors need tokenizer, parser
                processor_instance = self.descriptor.custom_processor(
                    self.adapter.tokenizer,
                    self.literal_parser,
                )
            else:
                # Unknown processor type - skip
                processor_instance = None

            if processor_instance:
                self.special_components.append(processor_instance)

        # Standard cases (append after custom)
        self.special_components.extend([
            StringLiteralProcessor(
                self.adapter.tokenizer,
                self.literal_parser,
            ),
            StandardCollectionsProcessor(
                self.adapter.tokenizer,
                self.literal_parser,
                self.selector,
                comment_style,
                self.descriptor
            ),
        ])

    def apply(self, context: ProcessingContext, cfg: LiteralConfig) -> None:
        """
        Apply literal optimization using unified single-pass approach.

        Collect all nodes from all profiles and process in depth order.
        This ensures deepest nodes are processed first, regardless of profile type.

        Args:
            context: Processing context with document
            cfg: Literal configuration
        """
        # Get max_tokens from config
        max_tokens = cfg.max_tokens
        if max_tokens is None:
            return  # Optimization disabled

        def node_depth(node):
            """Calculate nesting depth of a node (distance from root)."""
            depth = 0
            current = node.parent
            while current:
                depth += 1
                current = current.parent
            return depth

        # Collect AST-extraction collection nodes to skip their children
        ast_extraction_nodes_set = set()
        for p in self.descriptor.profiles:
            if isinstance(p, SequenceProfile) and p.requires_ast_extraction:
                seq_nodes = context.doc.query_nodes(p.query, "lit")
                for seq_node in seq_nodes:
                    ast_extraction_nodes_set.add((seq_node.start_byte, seq_node.end_byte))

        # Collect all (node, profile) pairs from all profiles
        all_node_profile_pairs = []

        for profile in self.descriptor.profiles:
            nodes = context.doc.query_nodes(profile.query, "lit")

            # Deduplicate by coordinates
            seen_coords = set()
            unique_nodes = []
            for node in nodes:
                coords = (node.start_byte, node.end_byte)
                if coords not in seen_coords:
                    seen_coords.add(coords)
                    unique_nodes.append(node)

            # Filter nodes
            for node in unique_nodes:
                # Skip strings that are children of AST-extraction sequences
                if isinstance(profile, StringProfile) and node.parent:
                    parent_range = (node.parent.start_byte, node.parent.end_byte)
                    if parent_range in ast_extraction_nodes_set:
                        continue  # Skip - will be processed as whole sequence

                all_node_profile_pairs.append((node, profile))

        # Sort ALL nodes by depth (deepest first), then by position
        # This ensures inside-out processing across ALL profile types
        all_node_profile_pairs.sort(key=lambda pair: (-node_depth(pair[0]), pair[0].start_byte))

        # Process all nodes in unified depth order
        for node, profile in all_node_profile_pairs:
            self._process_node(context, node, profile, max_tokens)


    def _process_node(
        self,
        context: ProcessingContext,
        node: Node,
        profile: LiteralProfile,
        max_tokens: int,
    ) -> None:
        """
        Process a single node with its associated profile.

        Args:
            context: Processing context
            node: Tree-sitter node to process
            profile: Profile for this node
            max_tokens: Token budget
        """
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
                self._apply_result(context, node, result, literal_text, profile)

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
        original_text: str,
        profile: LiteralProfile,
    ) -> None:
        """
        Unified result application using PlaceholderManager.

        Args:
            context: Processing context
            node: Tree-sitter node
            result: Trim result to apply
            original_text: Original text for metrics
            profile: Literal profile for element type
        """
        # Determine position based on result or node
        if result.nodes_to_replace:
            # Use nodes from TrimResult (composing replacement - e.g., block init)
            nodes = result.nodes_to_replace
            start_byte = nodes[0].start_byte
            end_byte = nodes[-1].end_byte
        else:
            # Simple single-node replacement
            start_byte, end_byte = node.start_byte, node.end_byte

        # Convert to char positions
        start_char = context.doc.byte_to_char_position(start_byte)
        end_char = context.doc.byte_to_char_position(end_byte)

        # Build element type: "literal_string", "literal_dict", etc.
        element_type = f"literal_{profile.get_category_name()}"

        # Determine if suffix comment is needed based on PlaceholderPosition
        # END/INLINE → need suffix comment (info not in replacement_text)
        # MIDDLE_COMMENT/NONE → no suffix comment (info already embedded)
        placeholder_pos = profile.placeholder_position
        needs_suffix = placeholder_pos in (PlaceholderPosition.END, PlaceholderPosition.INLINE)

        # Use PlaceholderManager for main replacement
        # use_composing_nested=True for proper nesting support (literals can be nested)
        context.add_placeholder(
            element_type,
            start_char,
            end_char,
            action=PlaceholderAction.TRUNCATE,
            replacement_text=result.trimmed_text,
            add_suffix_comment=needs_suffix,
            tokens_saved=result.saved_tokens if needs_suffix else None,
            use_composing_nested=True,
        )

        # Update additional metrics (chars saved)
        context.metrics.add_chars_saved(len(original_text) - len(result.trimmed_text))
