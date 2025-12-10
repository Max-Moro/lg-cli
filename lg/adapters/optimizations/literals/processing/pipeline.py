"""
Literal optimization pipeline (v2 entry point).

This module serves as the single entry point for literal optimization.
Orchestrates the two-pass literal processing workflow.
"""

from __future__ import annotations

from typing import Callable, cast, List, Tuple, Union

from lg.adapters.code_model import LiteralConfig
from lg.adapters.context import ProcessingContext
from ..patterns import LiteralProfile, BlockInitProfile, SequenceProfile, CollectionProfile
from ..components.block_init import BlockInitProcessor


class LiteralPipeline:
    """
    Main pipeline for literal optimization (v2).

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
        descriptor = self.adapter.create_literal_descriptor()

        # Create handler with language-specific comment style
        from ..handler import LanguageLiteralHandler
        comment_style = self.adapter.get_comment_style()
        self.handler = LanguageLiteralHandler(
            self.adapter.name,
            descriptor,
            self.adapter.tokenizer,
            (comment_style[0], (comment_style[1][0], comment_style[1][1]))
        )

        # Create AST sequence processor
        from ..components.ast_sequence import ASTSequenceProcessor
        self.ast_sequence_processor = ASTSequenceProcessor(
            self.adapter.tokenizer,
            descriptor.string_profiles
        )

        # Create block init processor
        comment_style = self.adapter.get_comment_style()
        all_profiles = (
            self.handler.descriptor.string_profiles +
            self.handler.descriptor.sequence_profiles +
            self.handler.descriptor.mapping_profiles +
            self.handler.descriptor.factory_profiles +
            self.handler.descriptor.block_init_profiles
        )
        self.block_init_processor = BlockInitProcessor(
            self.adapter.tokenizer,
            all_profiles,
            self.handler.process_literal,
            (comment_style[0], (comment_style[1][0], comment_style[1][1]))
        )

    def apply(self, context: ProcessingContext) -> None:
        """
        Apply literal optimization using two-pass approach.

        Pass 1: Process strings (top-level only)
        Pass 2: Process collections with DFS (nested structures)

        Args:
            context: Processing context with document
        """
        if self.handler is None:
            return  # Language not supported

        # Get max_tokens from config
        max_tokens = self.cfg.max_tokens
        if max_tokens is None:
            return  # Optimization disabled

        # Two-pass approach for orthogonal string/collection processing
        processed_strings = []  # Track (start, end, tokens_saved) for processed strings

        # Pass 1: Process all string profiles
        self._process_strings(context, max_tokens, processed_strings)

        # Pass 2: Process all collection profiles
        self._process_collections(context, max_tokens, processed_strings)

    def _process_strings(
        self,
        context: ProcessingContext,
        max_tokens: int,
        processed_strings: List
    ) -> None:
        """
        Pass 1: Process string literals.

        Args:
            context: Processing context
            _: Unused (for parameter compatibility)
            max_tokens: Token budget
            processed_strings: Output list for tracking processed ranges
        """
        # Collect AST-extraction collection nodes to skip their children
        # Only SequenceProfile can have requires_ast_extraction=True
        ast_extraction_nodes_set = set()

        for seq_profile in self.handler.descriptor.sequence_profiles:
            if seq_profile.requires_ast_extraction:
                seq_nodes = context.doc.query_nodes(seq_profile.query, "lit")
                for seq_node in seq_nodes:
                    ast_extraction_nodes_set.add((seq_node.start_byte, seq_node.end_byte))

        # Process each string profile
        for profile in self.handler.descriptor.string_profiles:
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

                # Process node (delegate to handler with profile)
                result = self.handler.process_literal(
                    text=literal_text,
                    profile=profile,
                    start_byte=node.start_byte,
                    end_byte=node.end_byte,
                    token_budget=max_tokens,
                    base_indent=self._get_base_indent(context.raw_text, node.start_byte),
                    element_indent=self._get_element_indent(literal_text, ""),
                )

                if result and result.saved_tokens > 0:
                    start_byte, end_byte = context.doc.get_node_range(node)
                    self._apply_trim_result(context, node, result, literal_text)
                    processed_strings.append((start_byte, end_byte, result.saved_tokens))

    def _process_collections(
        self,
        context: ProcessingContext,
        max_tokens: int,
        processed_strings: List
    ) -> None:
        """
        Pass 2: Process collection literals with DFS.

        Args:
            context: Processing context
            _: Unused (for parameter compatibility)
            max_tokens: Token budget
            processed_strings: Ranges already processed in Pass 1
        """
        # Process each profile type with specialized processor
        # Type-safe, no isinstance or string tags needed

        for profile in self.handler.descriptor.sequence_profiles:
            self._process_profile(context, profile, max_tokens, processed_strings,
                                 self._process_sequence_node)

        for profile in self.handler.descriptor.mapping_profiles:
            self._process_profile(context, profile, max_tokens, processed_strings,
                                 self._process_standard_collection_node)

        for profile in self.handler.descriptor.factory_profiles:
            self._process_profile(context, profile, max_tokens, processed_strings,
                                 self._process_standard_collection_node)

        for profile in self.handler.descriptor.block_init_profiles:
            self._process_profile(context, profile, max_tokens, processed_strings,
                                 self._process_block_init_node)

    def _process_profile(
        self,
        context: ProcessingContext,
        profile: LiteralProfile,
        max_tokens: int,
        processed_strings: List,
        processor: Callable
    ) -> None:
        """
        Common pipeline logic for processing any profile type.

        Args:
            context: Processing context
            profile: Profile to process (type determined by processor)
            max_tokens: Token budget
            processed_strings: Already processed string ranges
            processor: Specialized processor function for this profile type
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

            # Skip if contained in processed string
            contained_in_string = any(
                s <= start_byte and end_byte <= e
                for s, e, _ in processed_strings
            )
            if not contained_in_string:
                top_level.append(node)

        # Process each top-level collection
        for node in top_level:
            literal_text = context.doc.get_node_text(node)
            token_count = self.adapter.tokenizer.count_text_cached(literal_text)

            # Skip budget check for BLOCK_INIT (handles budget internally)
            # Processor knows how to handle its profile type
            if token_count > max_tokens or isinstance(profile, BlockInitProfile):
                # Call specialized processor
                result = processor(context, node, max_tokens, profile)

                # Apply if tokens saved
                if result:
                    if isinstance(result, tuple):
                        # BLOCK_INIT with expanded nodes
                        trim_result, nodes_used = result
                        self._apply_trim_result_composing(context, nodes_used, trim_result, literal_text)
                    elif result.saved_tokens > 0:
                        # Standard result
                        self._apply_trim_result_composing(context, [node], result, literal_text)

    def _process_block_init_node(
        self,
        context: ProcessingContext,
        node,
        max_tokens: int,
        profile: BlockInitProfile
    ) -> Union[object, Tuple]:
        """
        Process BlockInitProfile node.

        Args:
            context: Processing context
            node: Tree-sitter node
            max_tokens: Token budget
            profile: BlockInitProfile instance

        Returns:
            Processing result or tuple
        """
        result = self.block_init_processor.process(
            profile=profile,
            node=node,
            doc=context.doc,
            token_budget=max_tokens,
            base_indent=self._get_base_indent(context.raw_text, node.start_byte),
        )
        return result

    def _process_sequence_node(
        self,
        context: ProcessingContext,
        node,
        max_tokens: int,
        profile: SequenceProfile
    ) -> object:
        """
        Process SequenceProfile node.

        Args:
            context: Processing context
            node: Tree-sitter node
            max_tokens: Token budget
            profile: SequenceProfile instance

        Returns:
            Processing result
        """
        if profile.requires_ast_extraction:
            text = context.doc.get_node_text(node)
            base_indent = self._get_base_indent(context.raw_text, node.start_byte)
            element_indent = self._get_element_indent(text, base_indent)

            result = self.ast_sequence_processor.process(
                profile=profile,
                node=node,
                doc=context.doc,
                token_budget=max_tokens,
                element_indent=element_indent,
            )
            return result
        else:
            # Standard sequence processing
            return self._process_standard_collection_node(context, node, max_tokens, profile)

    def _process_standard_collection_node(
        self,
        context: ProcessingContext,
        node,
        max_tokens: int,
        profile: CollectionProfile
    ) -> object:
        """
        Process standard collection nodes (mapping, factory, regular sequence).

        Args:
            context: Processing context
            node: Tree-sitter node
            max_tokens: Token budget
            profile: Profile instance

        Returns:
            Processing result
        """
        text = context.doc.get_node_text(node)
        return self.handler.process_literal(
            text=text,
            profile=profile,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            token_budget=max_tokens,
            base_indent=self._get_base_indent(context.raw_text, node.start_byte),
            element_indent=self._get_element_indent(text, ""),
        )

    def _apply_trim_result(self, context: ProcessingContext, node, result, original_text: str) -> None:
        """Apply trim result (temporary delegation)."""
        start_byte, end_byte = context.doc.get_node_range(node)

        context.editor.add_replacement(
            start_byte, end_byte, result.trimmed_text,
            edit_type="literal_trimmed"
        )

        placeholder_style = self.adapter.cfg.placeholders.style
        if placeholder_style != "none" and result.comment_text:
            text_after = context.raw_text[end_byte:]
            formatted_comment, offset = self.handler.get_comment_for_context(
                text_after, result.comment_text
            )
            context.editor.add_insertion(
                end_byte + offset,
                formatted_comment,
                edit_type="literal_comment"
            )

        context.metrics.mark_element_removed("literal")
        context.metrics.add_chars_saved(len(original_text) - len(result.trimmed_text))

    def _apply_trim_result_composing(self, context: ProcessingContext, nodes: List, result, original_text: str) -> None:
        """Apply trim result using composing method (temporary delegation)."""
        start_byte = nodes[0].start_byte
        end_byte = nodes[-1].end_byte

        context.editor.add_replacement_composing_nested(
            start_byte, end_byte, result.trimmed_text,
            edit_type="literal_trimmed"
        )

        placeholder_style = self.adapter.cfg.placeholders.style
        if placeholder_style != "none" and result.comment_text:
            text_after = context.raw_text[end_byte:]
            formatted_comment, offset = self.handler.get_comment_for_context(
                text_after, result.comment_text
            )
            context.editor.add_insertion(
                end_byte + offset,
                formatted_comment,
                edit_type="literal_comment"
            )

        context.metrics.mark_element_removed("literal")
        context.metrics.add_chars_saved(len(original_text) - len(result.trimmed_text))

    def _get_base_indent(self, text: str, byte_pos: int) -> str:
        """Get indentation of line containing byte position."""
        line_start = text.rfind('\n', 0, byte_pos)
        if line_start == -1:
            line_start = 0
        else:
            line_start += 1

        indent = ""
        for i in range(line_start, min(byte_pos, len(text))):
            if text[i] in ' \t':
                indent += text[i]
            else:
                break

        return indent

    def _get_element_indent(self, literal_text: str, base_indent: str) -> str:
        """Detect element indentation from literal content."""
        lines = literal_text.split('\n')
        if len(lines) < 2:
            return base_indent + "    "

        for line in lines[1:]:
            stripped = line.strip()
            if stripped and not stripped.startswith((']', '}', ')')):
                indent = ""
                for char in line:
                    if char in ' \t':
                        indent += char
                    else:
                        break
                if indent:
                    return indent

        return base_indent + "    "
