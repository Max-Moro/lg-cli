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

            # Get content lines count for single-line protection
            # Use strippable_range to count only content lines (excluding braces)
            lines_count = self._get_content_lines_count(context, func_group)

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
        leading comments. For brace-languages, it excludes opening '{' and
        closing '}' to preserve valid AST structure.
        """
        func_type = func_group.element_info.element_type

        # Get strippable range (in bytes) and convert to chars
        start_byte, end_byte = func_group.strippable_range
        start_char = context.doc.byte_to_char_position(start_byte)
        end_char = context.doc.byte_to_char_position(end_byte)

        # Nothing to strip if range is empty
        if start_char >= end_char:
            return

        # Get the stripped text to compute indentation from first content line
        stripped_text = context.raw_text[start_char:end_char]
        indent_prefix = self._compute_indent_from_text(stripped_text)

        # Check if strippable_range starts with newline (brace-languages after '{')
        # In this case, preserve the newline and start placeholder on next line
        placeholder_prefix = indent_prefix
        if stripped_text.startswith('\n'):
            placeholder_prefix = "\n" + indent_prefix

        start_line = context.doc.get_line_number(start_char)
        end_line = context.doc.get_line_number(end_char)

        # Calculate actual lines removed (non-empty content lines)
        lines_removed = self._count_content_lines(stripped_text)

        context.add_placeholder(
            func_type + "_body",
            start_char,  # Start from strippable range, not line beginning
            end_char,
            start_line,
            end_line,
            placeholder_prefix=placeholder_prefix,
            lines_removed=lines_removed
        )

    def _get_content_lines_count(self, context: ProcessingContext, func_group: FunctionGroup) -> int:
        """
        Get count of content lines in function body for single-line protection.

        Uses strippable_range to count only actual content lines,
        excluding braces and empty lines. This ensures single-line functions
        like `fun f() { return x }` are protected from stripping.

        Args:
            context: Processing context
            func_group: Function group with strippable range

        Returns:
            Number of non-empty content lines
        """
        start_byte, end_byte = func_group.strippable_range
        if start_byte >= end_byte:
            return 0

        start_char = context.doc.byte_to_char_position(start_byte)
        end_char = context.doc.byte_to_char_position(end_byte)
        content_text = context.raw_text[start_char:end_char]

        return self._count_content_lines(content_text)

    def _count_content_lines(self, text: str) -> int:
        """
        Count non-empty content lines in text.

        For brace-based languages, strippable text typically starts with
        newline (after '{') and ends before '}'. We count only lines with
        actual content, not empty lines or lines with only whitespace.

        Args:
            text: Text to count lines in

        Returns:
            Number of non-empty lines
        """
        lines = text.split('\n')
        return sum(1 for line in lines if line.strip())

    def _compute_indent_from_text(self, text: str) -> str:
        """
        Compute indentation from first non-empty line of text.
        """
        lines = text.split('\n')
        for line in lines:
            stripped = line.lstrip()
            if stripped:
                return line[:len(line) - len(stripped)]
        return ""

    def _apply_trim(
        self,
        context: ProcessingContext,
        func_group: FunctionGroup,
        trimmer: FunctionBodyTrimmer
    ) -> None:
        """
        Trim function body to token budget.

        Keeps some code at the start, preserves return statement at the end,
        replaces the middle section with placeholder.
        """
        result = trimmer.trim(context, func_group)
        if result is None:
            return

        func_type = func_group.element_info.element_type

        # Use "truncated" suffix to distinguish from complete body removal
        placeholder_type = func_type + "_body_truncated"

        # Compute placeholder prefix with proper newline handling
        # If placeholder starts right after '{' (no prefix kept), add newline
        placeholder_prefix = result.indent
        if not result.kept_prefix:
            # No prefix kept - placeholder goes right after opening brace
            # Need newline before indent
            placeholder_prefix = "\n" + result.indent

        # Add placeholder for the removed middle section
        # Pass explicit lines_removed from TrimResult for accurate count
        context.placeholders.add_placeholder(
            placeholder_type,
            result.placeholder_start_char,
            result.placeholder_end_char,
            context.doc.get_line_number(result.placeholder_start_char),
            context.doc.get_line_number(result.placeholder_end_char),
            placeholder_prefix=placeholder_prefix,
            lines_removed=result.lines_removed
        )
        # Update metrics
        context.metrics.mark_element_removed(func_type + "_body", 1)
        context.metrics.mark_placeholder_inserted()

    def _find_line_start(self, text: str, pos: int) -> int:
        """Find the start of the line containing position pos."""
        line_start = text.rfind('\n', 0, pos)
        if line_start == -1:
            return 0
        return line_start + 1
