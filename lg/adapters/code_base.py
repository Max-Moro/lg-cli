"""
Base class for language programming adapters.
Provides common functionality for code processing and optimization orchestration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, TypeVar, Optional, cast, ClassVar

from .base import BaseAdapter
from .budget import BudgetController
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
from .optimizations.comment_analysis import CommentAnalyzer
from .comment_style import CommentStyle
from .tree_sitter_support import TreeSitterDocument, Node

C = TypeVar("C", bound=CodeCfg)

class CodeAdapter(BaseAdapter[C], ABC):
    """
    Base class for all language programming adapters.
    Provides common methods for code processing and placeholder system.
    """

    # Default comment style - subclasses should override
    COMMENT_STYLE: ClassVar[CommentStyle] = CommentStyle(
        single_line="//",
        multi_line=("/*", "*/"),
        doc_markers=("/**", "*/")
    )

    def _post_bind(self) -> None:
        """
        Post-bind initialization for code adapters.
        Creates optimizer instances based on configuration.

        If budget is enabled, all optimizers are created (budget may use any of them).
        Otherwise, only optimizers needed by current config are created.
        """
        cfg = self.cfg
        has_budget = cfg.budget and cfg.budget.max_tokens_per_file

        # Determine which optimizers are needed
        needs_public_api = has_budget or cfg.public_api_only
        needs_function_bodies = has_budget or bool(cfg.strip_function_bodies)
        needs_comments = has_budget or cfg.comment_policy != "keep_all"
        needs_imports = has_budget or cfg.imports.policy != "keep_all" or cfg.imports.summarize_long
        needs_literals = has_budget or cfg.literals.max_tokens is not None

        # Create optimizer instances (only those that are needed)
        self.public_api_optimizer = PublicApiOptimizer(self) if needs_public_api else None
        self.function_body_optimizer = FunctionBodyOptimizer(self) if needs_function_bodies else None
        self.comment_optimizer = CommentOptimizer(self) if needs_comments else None
        self.import_optimizer = ImportOptimizer(self) if needs_imports else None
        self.literal_pipeline = LiteralPipeline(self) if needs_literals else None

        # Create budget controller if budgeting is enabled
        self.budget_controller = BudgetController(self, self.tokenizer, cfg.budget) if has_budget else None

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

    def create_comment_analyzer(self, doc: TreeSitterDocument, code_analyzer: CodeAnalyzer) -> CommentAnalyzer:
        """Create language-specific comment analyzer for the document."""
        return CommentAnalyzer(doc, self.COMMENT_STYLE)

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """Create language-specific literal descriptor."""
        pass

    @property
    def comment_style(self) -> CommentStyle:
        """
        Get comment style for this language adapter.

        Returns:
            CommentStyle instance with comment markers for this language.
        """
        return self.COMMENT_STYLE

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
        if self.budget_controller is not None:
            effective_cfg, budget_metrics = self.budget_controller.fit_config(lightweight_ctx, self.cfg)

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
        if code_cfg.public_api_only and self.public_api_optimizer:
            self.public_api_optimizer.apply(context)

        # Process function bodies
        if code_cfg.strip_function_bodies and self.function_body_optimizer:
            self.function_body_optimizer.apply(context, code_cfg.strip_function_bodies)

        # Process comments
        if self.comment_optimizer:
            self.comment_optimizer.apply(context, code_cfg.comment_policy)

        # Process imports
        if self.import_optimizer:
            self.import_optimizer.apply(context, code_cfg.imports)

        # Process literals
        if code_cfg.literals.max_tokens is not None and self.literal_pipeline:
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
