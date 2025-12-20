"""
Function body optimization.
Removes or minimizes function/method bodies based on configuration.
"""

from __future__ import annotations

from typing import cast, List, Optional, Tuple, Union

from .decision import FunctionBodyDecision
from .evaluators import ExceptPatternEvaluator, KeepAnnotatedEvaluator, BasePolicyEvaluator
from .trimmer import FunctionBodyTrimmer
from ...code_analysis import ElementInfo, FunctionGroup
from ...code_model import FunctionBodyConfig
from ...context import ProcessingContext


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

        # Create evaluator pipeline and trimmer
        evaluators = self._create_evaluators(normalized_cfg)
        trimmer = FunctionBodyTrimmer(normalized_cfg.max_tokens) if normalized_cfg.max_tokens else None

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

            # Apply max_tokens post-processing
            if trimmer and decision.action == "keep":
                if trimmer.should_trim(context, func_group):
                    decision = FunctionBodyDecision(action="trim", max_tokens=normalized_cfg.max_tokens)

            # Apply decision
            self._apply_decision(context, decision, func_group, trimmer)

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
        func_group: FunctionGroup,
        trimmer: Optional[FunctionBodyTrimmer]
    ) -> None:
        """Apply the decision for a function body."""
        if decision.action == "keep":
            return

        if decision.action == "strip":
            self._apply_strip(context, func_group)

        elif decision.action == "trim" and trimmer:
            self._apply_trim(context, func_group, trimmer)

    def _apply_strip(
        self,
        context: ProcessingContext,
        func_group: FunctionGroup
    ) -> None:
        """
        Strip function body using pre-computed strippable_range.

        The strippable_range is computed by the language-specific analyzer
        and already accounts for protected content (docstrings) and
        leading comments.
        """
        func_type = func_group.element_info.element_type

        # Get strippable range (in bytes) and convert to chars
        start_byte, end_byte = func_group.strippable_range
        start_char = context.doc.byte_to_char_position(start_byte)
        end_char = context.doc.byte_to_char_position(end_byte)

        # Nothing to strip if range is empty
        if start_char >= end_char:
            return

        # Find line start and compute indentation
        line_start = self._find_line_start(context.raw_text, start_char)
        indent_prefix = context.raw_text[line_start:start_char]

        start_line = context.doc.get_line_number(start_char)
        end_line = context.doc.get_line_number(end_char)

        context.add_placeholder(
            func_type + "_body",
            line_start,  # Start from line beginning
            end_char,
            start_line,
            end_line,
            placeholder_prefix=indent_prefix
        )

    def _apply_trim(
        self,
        context: ProcessingContext,
        func_group: FunctionGroup,
        trimmer: FunctionBodyTrimmer
    ) -> None:
        """
        Trim function body to token budget.

        Keeps some code, replaces rest with placeholder.
        """
        result = trimmer.trim(context, func_group)
        if result is None:
            return

        start_char, end_char, trimmed_text = result
        func_type = func_group.element_info.element_type

        # Get indent from start of strippable range (consistent with function body)
        line_start = self._find_line_start(context.raw_text, start_char)
        indent_prefix = context.raw_text[line_start:start_char]

        if trimmed_text:
            # Trimmed text ends at a complete line, placeholder starts on next line
            trimmed_end = start_char + len(trimmed_text)

            # Placeholder replaces from trimmed_end to end
            # Since trimmed_text ends with \n, trimmed_end is at line start
            # Use indent from original body
            context.add_placeholder(
                func_type + "_body",
                trimmed_end,
                end_char,
                context.doc.get_line_number(trimmed_end),
                context.doc.get_line_number(end_char),
                placeholder_prefix=indent_prefix
            )
        else:
            # Nothing left after trim - full strip (same as _apply_strip)
            context.add_placeholder(
                func_type + "_body",
                line_start,
                end_char,
                context.doc.get_line_number(start_char),
                context.doc.get_line_number(end_char),
                placeholder_prefix=indent_prefix
            )

    def _find_line_start(self, text: str, pos: int) -> int:
        """Find the start of the line containing position pos."""
        line_start = text.rfind('\n', 0, pos)
        if line_start == -1:
            return 0
        return line_start + 1
