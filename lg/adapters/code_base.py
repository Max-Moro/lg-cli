"""
Base class for language programming adapters.
Provides common functionality for code processing and optimization orchestration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, TypeVar, Optional, cast

from .base import BaseAdapter
from .code_analysis import CodeAnalyzer
from .code_model import CodeCfg, PlaceholderConfig
from .context import ProcessingContext, LightweightContext
from .optimizations import (
    PublicApiOptimizer,
    FunctionBodyOptimizer,
    CommentOptimizer,
    ImportOptimizer,
    LiteralPipeline,
    LanguageLiteralDescriptor,
    TreeSitterImportAnalyzer,
    ImportClassifier
)
from .optimizations.comment_analysis import CommentAnalyzer, CommentStyle
from .tree_sitter_support import TreeSitterDocument, Node

C = TypeVar("C", bound=CodeCfg)

class CodeAdapter(BaseAdapter[C], ABC):
    """
    Base class for all language programming adapters.
    Provides common methods for code processing and placeholder system.
    """

    def _post_bind(self) -> None:
        """
        Post-bind initialization for code adapters.
        Initializes literal pipeline when literals optimization is enabled.
        """
        # Initialize literal pipeline only if literals optimization is enabled
        # This avoids heavy initialization when max_tokens is None
        if self.cfg.literals.max_tokens is not None:
            self.literal_pipeline = LiteralPipeline(self)
        else:
            self.literal_pipeline = None

    @abstractmethod
    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        """Create a parsed Tree-sitter document."""
        pass

    @abstractmethod
    def create_import_classifier(self, external_patterns: List[str]) -> ImportClassifier:
        """Create language-specific import classifier. Must be overridden by subclasses."""
        pass

    @abstractmethod
    def create_import_analyzer(self, classifier: ImportClassifier) -> TreeSitterImportAnalyzer:
        """Create language-specific import analyzer. Must be overridden by subclasses."""
        pass

    @abstractmethod
    def create_code_analyzer(self, doc: TreeSitterDocument) -> CodeAnalyzer:
        """Create language-specific unified code analyzer."""
        pass

    @abstractmethod
    def create_comment_analyzer(self, doc: TreeSitterDocument) -> CommentAnalyzer:
        """Create language-specific comment analyzer for the document."""
        pass

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """Create language-specific literal descriptor."""
        pass

    @property
    def comment_style(self) -> tuple[str, tuple[str, str], tuple[str, str]]:
        """
        Get comment style as tuple for backward compatibility.

        Returns:
            Tuple of (single_line, multi_line, doc_markers) in the legacy format.
        """
        # Get analyzer class (not instance) to access STYLE
        # This is a workaround - we need the style without creating a document
        # Subclasses should use their analyzer's STYLE directly
        analyzer_cls = self._get_comment_analyzer_class()
        style = analyzer_cls.STYLE
        return style.single_line, style.multi_line, style.doc_markers

    def _get_comment_analyzer_class(self) -> type[CommentAnalyzer]:
        """Get the comment analyzer class for this adapter. Override in subclasses."""
        return CommentAnalyzer

    # ============= HOOKS for injecting into optimization process ===========

    def hook__remove_function_body(
            self,
            root_optimizer: FunctionBodyOptimizer,
            context: ProcessingContext,
            func_def: Optional[Node],
            body_node: Node,
            func_type: str
    ) -> None:
        """Hook for customizing function body removal."""
        root_optimizer.remove_function_body(context, body_node, func_type)

    # ============= Main pipeline for language optimizer operations ===========

    def process(self, lightweight_ctx: LightweightContext) -> Tuple[str, Dict[str, Any]]:
        """
        Main code processing method.
        Applies all configured optimizations.
        """
        # Select effective config with active budget (sandbox without placeholders)
        effective_cfg = self.cfg
        budget_metrics: dict[str, int] | None = None
        if self.cfg.budget and self.cfg.budget.max_tokens_per_file:
            from .budget import BudgetController
            controller = BudgetController[C](self, self.tokenizer, self.cfg.budget)
            effective_cfg, budget_metrics = controller.fit_config(lightweight_ctx, self.cfg)

        # Get full context from lightweight context for actual run
        context = lightweight_ctx.get_full_context(self, self.tokenizer)

        # Then apply optimizations based on selected config
        # Cast for type-narrowing: effective_cfg matches adapter's config type
        self._apply_optimizations(context, cast(C, effective_cfg))

        # Finalize placeholders
        text, meta = self._finalize_placeholders(context, effective_cfg.placeholders)

        # Mix in budget metrics
        if budget_metrics:
            meta.update(budget_metrics)

        return text, meta

    # noinspection PyUnresolvedReferences
    def _apply_optimizations(self, context: ProcessingContext, code_cfg: C) -> None:
        """
        Apply optimizations via specialized modules.
        Each module is responsible for its type of optimization.
        """
        # Filter by public API
        if code_cfg.public_api_only:
            public_api_optimizer = PublicApiOptimizer(self)
            public_api_optimizer.apply(context)

        # Process function bodies
        if code_cfg.strip_function_bodies:
            function_body_optimizer = FunctionBodyOptimizer(code_cfg.strip_function_bodies, self)
            function_body_optimizer.apply(context)

        # Process comments
        comment_optimizer = CommentOptimizer(code_cfg.comment_policy, self)
        comment_optimizer.apply(context)

        # Process imports
        import_optimizer = ImportOptimizer(code_cfg.imports, self)
        import_optimizer.apply(context)

        # Process literals - only if pipeline was initialized
        if self.literal_pipeline is not None:
            self.literal_pipeline.apply(context, code_cfg.literals)

    def _finalize_placeholders(self, context: ProcessingContext, ph_cfg: PlaceholderConfig) -> Tuple[str, Dict[str, Any]]:
        """
        Finalize placeholders and apply them to editor, get final metrics.
        """
        collapsed_edits, placeholder_stats = context.placeholders.finalize_edits()

        min_savings_ratio = ph_cfg.min_savings_ratio
        min_abs_savings_if_none = ph_cfg.min_abs_savings_if_none

        for spec, repl in collapsed_edits:
            # Get original text for range
            src = context.raw_text[spec.start_char:spec.end_char]

            # Determine "empty" replacement flag
            is_none = (repl == "")

            # Check feasibility
            if not self.tokenizer.is_economical(
                    src,
                    repl,
                    min_ratio=min_savings_ratio,
                    replacement_is_none=is_none,
                    min_abs_savings_if_none=min_abs_savings_if_none,
            ):
                # Skip replacement, keep original
                continue

            # Apply relevant placeholders to editor
            context.editor.add_replacement(spec.start_char, spec.end_char, repl,
                # Type not specified as context collects metadata itself about placeholders
                edit_type=None
            )

        # Update metrics from placeholders
        for key, value in placeholder_stats.items():
            if isinstance(value, (int, float)):
                context.metrics.set(key, value)

        # Apply all changes in text editor and return statistics
        result_text, edit_stats = context.editor.apply_edits()

        # Combine metrics from editor and context
        metrics = context.metrics.to_dict()
        metrics.update(edit_stats)
        return result_text, metrics
