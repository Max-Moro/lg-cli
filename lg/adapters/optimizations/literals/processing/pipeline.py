"""
Literal optimization pipeline.

This module serves as the single entry point for literal optimization.
Orchestrates the two-pass literal processing workflow.
"""

from __future__ import annotations

from typing import Callable, cast, List, Optional, Tuple, Union

from lg.adapters.code_model import LiteralConfig
from lg.adapters.context import ProcessingContext
from ..patterns import (
    LiteralProfile,
    BlockInitProfile,
    SequenceProfile,
    CollectionProfile,
    StringProfile,
    ParsedLiteral,
    TrimResult,
    MappingProfile,
    FactoryProfile,
)
from ..components.block_init import BlockInitProcessor
from ..components.budgeting import BudgetCalculator
from ..components.interpolation import InterpolationHandler
from ..components.placeholder import PlaceholderCommentFormatter
from ..element_parser import ElementParser, Element, ParseConfig
from .formatter import ResultFormatter
from .parser import LiteralParser
from .selector import BudgetSelector, Selection, DFSSelection


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
        comment_style = self.adapter.get_comment_style()
        self.single_comment = comment_style[0]
        self.block_comment = comment_style[1]

        # Create reusable components
        self.literal_parser = LiteralParser(self.adapter.tokenizer)
        self.selector = BudgetSelector(self.adapter.tokenizer)
        self.formatter = ResultFormatter(self.adapter.tokenizer, comment_style)
        self.interpolation = InterpolationHandler()
        self.placeholder_formatter = PlaceholderCommentFormatter(comment_style)
        self.budget_calculator = BudgetCalculator(self.adapter.tokenizer)

        # Collect factory wrappers from all FACTORY_CALL patterns for nested detection
        self._factory_wrappers = self._collect_factory_wrappers()

        # Cache parsers for different patterns
        self._parsers: dict[str, ElementParser] = {}

        # Create AST sequence processor
        from ..components.ast_sequence import ASTSequenceProcessor
        self.ast_sequence_processor = ASTSequenceProcessor(
            self.adapter.tokenizer,
            self.descriptor.string_profiles
        )

        # Create block init processor
        all_profiles = (
            self.descriptor.string_profiles +
            self.descriptor.sequence_profiles +
            self.descriptor.mapping_profiles +
            self.descriptor.factory_profiles +
            self.descriptor.block_init_profiles
        )
        self.block_init_processor = BlockInitProcessor(
            self.adapter.tokenizer,
            all_profiles,
            self._process_literal_impl,
            (comment_style[0], (comment_style[1][0], comment_style[1][1]))
        )

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

    def _get_parser_for_profile(self, profile: CollectionProfile) -> ElementParser:
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

    def _process_literal_impl(
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
            # This path should not be reached from _process_literal_impl
            raise RuntimeError(
                "BLOCK_INIT profiles must be processed via LiteralPipeline._process_block_init_node, "
                "not _process_literal_impl"
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
        overhead = self.budget_calculator.calculate_overhead(
            parsed.opening, parsed.closing, "…",
            parsed.is_multiline, parsed.element_indent
        )

        content_budget = max(1, token_budget - overhead)

        # Truncate content
        truncated = self.adapter.tokenizer.truncate_to_tokens(
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
            tokens_kept=self.adapter.tokenizer.count_text_cached(truncated),
            tokens_removed=parsed.original_tokens - self.adapter.tokenizer.count_text_cached(truncated),
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
        parser = self._get_parser_for_profile(profile)

        # Parse elements
        elements = parser.parse(parsed.content)

        if not elements:
            return None

        # Calculate overhead
        placeholder = profile.placeholder_template
        overhead = self.budget_calculator.calculate_overhead(
            parsed.opening, parsed.closing, placeholder,
            parsed.is_multiline, parsed.element_indent
        )

        content_budget = max(1, token_budget - overhead)

        # Select elements with DFS (budget-aware nested selection)
        selection = self.selector.select_dfs(
            elements, content_budget,
            profile=profile,
            get_parser_func=self._get_parser_for_profile,
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

                # Process node with profile
                result = self._process_literal_impl(
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

        for profile in self.descriptor.sequence_profiles:
            self._process_profile(context, profile, max_tokens, processed_strings,
                                 self._process_sequence_node)

        for profile in self.descriptor.mapping_profiles:
            self._process_profile(context, profile, max_tokens, processed_strings,
                                 self._process_standard_collection_node)

        for profile in self.descriptor.factory_profiles:
            self._process_profile(context, profile, max_tokens, processed_strings,
                                 self._process_standard_collection_node)

        for profile in self.descriptor.block_init_profiles:
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
        return self._process_literal_impl(
            text=text,
            profile=profile,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            token_budget=max_tokens,
            base_indent=self._get_base_indent(context.raw_text, node.start_byte),
            element_indent=self._get_element_indent(text, ""),
        )

    def _apply_trim_result(self, context: ProcessingContext, node, result, original_text: str) -> None:
        """Apply trim result."""
        start_byte, end_byte = context.doc.get_node_range(node)

        context.editor.add_replacement(
            start_byte, end_byte, result.trimmed_text,
            edit_type="literal_trimmed"
        )

        placeholder_style = self.adapter.cfg.placeholders.style
        if placeholder_style != "none" and result.comment_text:
            text_after = context.raw_text[end_byte:]
            formatted_comment, offset = self.placeholder_formatter.format_comment_for_context(
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
        """Apply trim result using composing method."""
        start_byte = nodes[0].start_byte
        end_byte = nodes[-1].end_byte

        context.editor.add_replacement_composing_nested(
            start_byte, end_byte, result.trimmed_text,
            edit_type="literal_trimmed"
        )

        placeholder_style = self.adapter.cfg.placeholders.style
        if placeholder_style != "none" and result.comment_text:
            text_after = context.raw_text[end_byte:]
            formatted_comment, offset = self.placeholder_formatter.format_comment_for_context(
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
