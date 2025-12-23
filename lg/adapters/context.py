"""
Processing context for language adapters.
Encapsulates state and provides methods for typical operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from .metrics import MetricsCollector
from .placeholders import PlaceholderManager, PlaceholderAction
from .range_edits import RangeEditor
from .tree_sitter_support import TreeSitterDocument, Node
from ..stats import TokenService


class LightState:
    def __init__(
            self,
            file_path: Path,
            raw_text: str,
            group_size: int
    ):
        self.file_path = file_path
        self.raw_text = raw_text
        self.group_size = group_size

        # Calculate derived fields
        self.filename = file_path.name
        self.ext = file_path.suffix.lstrip(".") if file_path.suffix else ""

class LightweightContext(LightState):
    """
    Lightweight processing context with basic file information.
    Created at an early stage and can be lazily extended to ProcessingContext.
    """

    def __init__(
        self,
        file_path: Path,
        raw_text: str,
        group_size: int,
        template_ctx=None,
        file_label: str = None
    ):
        super().__init__(file_path, raw_text, group_size)

        # For lazy initialization of full context
        self._full_context: Optional[ProcessingContext] = None
        # Template context for processing conditional constructs
        self.template_ctx = template_ctx
        # File label for insertion into documentation
        self.file_label = file_label

    def get_full_context(self, adapter, tokenizer: TokenService) -> ProcessingContext:
        """
        Lazy creation of full ProcessingContext when needed.

        Args:
            tokenizer: Token counting service
            adapter: Language adapter for creating document and placeholder generator

        Returns:
            ProcessingContext initialized from this lightweight context
        """
        if self._full_context is None:
            self._full_context = ProcessingContext.from_lightweight(self, adapter, tokenizer)

        return self._full_context


class ProcessingContext(LightState):
    """
    Processing context, encapsulating doc, editor, placeholders and metrics.
    """

    def __init__(
        self,
        file_path: Path,
        raw_text: str,
        group_size: int,
        adapter_name: str,
        doc: TreeSitterDocument,
        editor: RangeEditor,
        placeholders: PlaceholderManager,
        tokenizer: TokenService,
        get_descriptor: Callable,  # () -> LanguageCodeDescriptor
    ):
        super().__init__(file_path, raw_text, group_size)

        self.doc = doc
        self.editor = editor
        self.placeholders = placeholders
        self.metrics = MetricsCollector(adapter_name)
        self.tokenizer = tokenizer
        self._get_descriptor = get_descriptor  # Lazy: called only when collector is needed
        self._collector = None  # ElementCollector, created lazily

    def add_placeholder(
        self,
        element_type: str,
        start_char: int,
        end_char: int,
        *,
        action: PlaceholderAction = PlaceholderAction.OMIT,
        placeholder_prefix: str = "",
        count: int = 1,
        replacement_text: Optional[str] = None,
        add_suffix_comment: bool = True,
        tokens_saved: Optional[int] = None,
        use_composing_nested: bool = False,
    ) -> None:
        """
        Add placeholder with explicit coordinates.

        Args:
            element_type: Type of element ("function_body", "literal_string", etc.)
            start_char: Start position in characters
            end_char: End position in characters
            action: OMIT for complete removal, TRUNCATE for partial reduction
            placeholder_prefix: Indentation prefix for placeholder text
            count: Number of elements
            replacement_text: For TRUNCATE action — the shortened content
            add_suffix_comment: Flag to add suffix comment after element
            tokens_saved: Tokens saved (for literal_* types)
            use_composing_nested: Use composing_nested for nested structures (literals)
        """
        self.placeholders.add_placeholder(
            element_type, start_char, end_char,
            action=action,
            placeholder_prefix=placeholder_prefix,
            count=count,
            replacement_text=replacement_text,
            add_suffix_comment=add_suffix_comment,
            tokens_saved=tokens_saved,
            use_composing_nested=use_composing_nested,
        )
        # Normalize literal_* types to "literal" for metrics
        metrics_type = "literal" if element_type.startswith("literal_") else element_type
        self.metrics.mark_element_removed(metrics_type, count)
        self.metrics.mark_placeholder_inserted()

    def add_placeholder_for_node(
        self,
        element_type: str,
        node: Node,
        *,
        action: PlaceholderAction = PlaceholderAction.OMIT,
        count: int = 1,
        replacement_text: Optional[str] = None,
        add_suffix_comment: bool = True,
        tokens_saved: Optional[int] = None,
        use_composing_nested: bool = False,
    ) -> None:
        """
        Add placeholder exactly at node boundaries.

        Args:
            element_type: Type of element
            node: Tree-sitter node to replace
            action: OMIT or TRUNCATE
            count: Number of elements
            replacement_text: For TRUNCATE action — the shortened content
            add_suffix_comment: Flag to add suffix comment after element
            tokens_saved: Tokens saved (for literal_* types)
            use_composing_nested: Use composing_nested for nested structures (literals)
        """
        self.placeholders.add_placeholder_for_node(
            element_type, node,
            action=action,
            count=count,
            replacement_text=replacement_text,
            add_suffix_comment=add_suffix_comment,
            tokens_saved=tokens_saved,
            use_composing_nested=use_composing_nested,
        )
        # Normalize literal_* types to "literal" for metrics
        metrics_type = "literal" if element_type.startswith("literal_") else element_type
        self.metrics.mark_element_removed(metrics_type, count)
        self.metrics.mark_placeholder_inserted()

    def get_collector(self):
        """
        Get or create ElementCollector for this context.

        Collector is cached for reuse between optimizers.
        Descriptor is obtained lazily via callback on first access.

        Returns:
            ElementCollector instance
        """
        if self._collector is None:
            # Import here to avoid circular dependency
            from .optimizations.shared import ElementCollector
            descriptor = self._get_descriptor()
            self._collector = ElementCollector(self.doc, descriptor)
        return self._collector

    @classmethod
    def from_lightweight(
        cls,
        lightweight_ctx: LightweightContext,
        adapter,
        tokenizer: TokenService
    ) -> ProcessingContext:
        """
        Create full ProcessingContext from lightweight context.

        Args:
            lightweight_ctx: Lightweight context with basic information
            adapter: Language adapter for creating components
            tokenizer: Token counting service

        Returns:
            Full ProcessingContext
        """
        # Create components for full context
        doc = adapter.create_document(lightweight_ctx.raw_text, lightweight_ctx.ext)
        editor = RangeEditor(lightweight_ctx.raw_text)

        # Create PlaceholderManager with settings from adapter
        placeholders = PlaceholderManager(
            doc,
            adapter.comment_style,
            editor,  # Pass editor for apply_to_editor() support
        )

        return cls(
            lightweight_ctx.file_path,
            lightweight_ctx.raw_text,
            lightweight_ctx.group_size,
            adapter.name,
            doc,
            editor,
            placeholders,
            tokenizer,
            get_descriptor=adapter.get_code_descriptor,  # Lazy: called only when needed
        )
