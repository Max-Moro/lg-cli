"""
Function body optimization.
Removes or minimizes function/method bodies based on configuration.
"""

from __future__ import annotations

from typing import cast, List, Tuple, Union

from .decision import FunctionBodyDecision
from .evaluators import ExceptPatternEvaluator, KeepAnnotatedEvaluator, BasePolicyEvaluator
from ...code_analysis import ElementInfo, FunctionGroup
from ...code_model import FunctionBodyConfig
from ...context import ProcessingContext
from ...tree_sitter_support import Node


class FunctionBodyOptimizer:
    """Handles function body stripping optimization."""

    def __init__(self, adapter):
        """Initialize with parent adapter."""
        from ...code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)

    def apply(self, context: ProcessingContext, cfg: Union[bool, FunctionBodyConfig]) -> None:
        """
        Apply function body stripping based on configuration.

        Args:
            context: Processing context with document and editor
            cfg: Configuration for function body stripping
        """
        if not cfg:
            return

        # Normalize config
        normalized_cfg = self._normalize_config(cfg)

        # Create evaluator pipeline
        evaluators = self._create_evaluators(normalized_cfg)

        # Collect all function and method groups
        function_groups = context.code_analyzer.collect_function_like_elements()

        # Process each function group
        for func_def, func_group in function_groups.items():
            if func_group.body_node is None:
                continue

            # Get line count for single-line protection
            start_line, end_line = context.doc.get_line_range(func_group.body_node)
            lines_count = end_line - start_line + 1

            # Evaluate decision
            decision = self._evaluate(evaluators, func_group.element_info, lines_count)

            # Apply decision
            self._apply_decision(context, decision, func_group)

    def _normalize_config(self, cfg: Union[bool, FunctionBodyConfig]) -> FunctionBodyConfig:
        """Normalize configuration to FunctionBodyConfig."""
        if isinstance(cfg, bool):
            return FunctionBodyConfig(policy="strip_all")
        return cfg

    def _create_evaluators(
        self,
        cfg: FunctionBodyConfig
    ) -> Tuple[List, BasePolicyEvaluator]:
        """Create evaluator pipeline based on configuration."""
        preservation_evaluators = []

        if cfg.except_patterns:
            preservation_evaluators.append(ExceptPatternEvaluator(cfg.except_patterns))

        if cfg.keep_annotated:
            preservation_evaluators.append(KeepAnnotatedEvaluator(cfg.keep_annotated))

        base_evaluator = BasePolicyEvaluator(cfg.policy)
        return preservation_evaluators, base_evaluator

    def _evaluate(
        self,
        evaluators: Tuple[List, BasePolicyEvaluator],
        element: ElementInfo,
        lines_count: int
    ) -> FunctionBodyDecision:
        """Run evaluation pipeline and return final decision."""
        preservation_evaluators, base_evaluator = evaluators

        # Single-line protection
        if lines_count <= 1:
            return FunctionBodyDecision(action="keep")

        # Run preservation evaluators first
        for evaluator in preservation_evaluators:
            decision = evaluator.evaluate(element)
            if decision is not None:
                return decision

        return base_evaluator.evaluate(element)

    def _apply_decision(
        self,
        context: ProcessingContext,
        decision: FunctionBodyDecision,
        func_group: FunctionGroup
    ) -> None:
        """Apply the decision for a function body."""
        if decision.action == "keep":
            return

        if decision.action == "strip":
            self._apply_strip(context, func_group)

        # "trim" action will be implemented in Phase 5

    def _apply_strip(
        self,
        context: ProcessingContext,
        func_group: FunctionGroup
    ) -> None:
        """
        Strip function body, respecting protected content.

        Protected content (e.g., Python docstrings) is preserved.
        Everything after protected content is removed.
        """
        body_node = func_group.body_node
        protected = func_group.protected_content
        func_type = func_group.element_info.element_type

        _, body_end_char = context.doc.get_node_range(body_node)

        if protected is not None:
            # Strip after protected content
            protected_end_char = context.doc.byte_to_char_position(protected.end_byte)

            # Nothing to remove if protected content ends at body end
            if protected_end_char >= body_end_char:
                return

            start_char = protected_end_char
        else:
            # No protected content - strip entire body
            start_char, _ = context.doc.get_node_range(body_node)

        start_line = context.doc.get_line_number(start_char)
        end_line = context.doc.get_line_number(body_end_char)

        context.add_placeholder(
            func_type + "_body",
            start_char,
            body_end_char,
            start_line,
            end_line
        )
