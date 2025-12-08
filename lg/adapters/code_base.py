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
    LiteralOptimizer,
    LanguageLiteralDescriptor,
    TreeSitterImportAnalyzer,
    ImportClassifier
)
from .tree_sitter_support import TreeSitterDocument, Node

C = TypeVar("C", bound=CodeCfg)

class CodeAdapter(BaseAdapter[C], ABC):
    """
    Base class for all language programming adapters.
    Provides common methods for code processing and placeholder system.
    """

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

    def create_literal_descriptor(self) -> LanguageLiteralDescriptor:
        """
        Create language-specific literal descriptor for v2 optimizer.

        Override in language adapters that support literal optimization v2.
        Returns None for languages not yet migrated to v2.

        Returns:
            LanguageLiteralDescriptor or None
        """
        return None

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

    def get_comment_style(self) -> Tuple[str, tuple[str, str], tuple[str, str]]:
        """Comment style for language (single-line, multi-line, docstring)."""
        return "//", ("/*", "*/"), ('/**', '*/')

    def is_documentation_comment(self, comment_text: str) -> bool:
        """Is this comment part of the documentation system."""
        return comment_text.strip().startswith('/**')

    def is_docstring_node(self, node, doc: TreeSitterDocument) -> bool:
        """Check if node is a docstring."""
        return False

    def hook__extract_first_sentence(self, root_optimizer: CommentOptimizer, text: str) -> str:
        """Hook for extracting first sentence from comment text."""
        return root_optimizer.extract_first_sentence(text)

    def hook__smart_truncate_comment(self, root_optimizer: CommentOptimizer, comment_text: str, max_tokens: int, tokenizer) -> str:
        """Hook for correctly closing multi-line comments and docstrings after truncation."""
        return root_optimizer.smart_truncate_comment(comment_text, max_tokens, tokenizer)

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

        # Process literals (use v2 if adapter provides descriptor, else v1)
        literal_optimizer = LiteralOptimizer(code_cfg.literals, self)
        literal_optimizer.apply(context)

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
