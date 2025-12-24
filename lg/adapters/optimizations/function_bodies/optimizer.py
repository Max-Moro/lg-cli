"""
Function body optimization.
Removes or minimizes function/method bodies based on configuration.
"""

from __future__ import annotations

from typing import cast, List, Optional, Tuple, Union

from .decision import FunctionBodyDecision
from .evaluators import ExceptPatternEvaluator, KeepAnnotatedEvaluator, BasePolicyEvaluator
from .trimmer import FunctionBodyTrimmer
from ...code_model import FunctionBodyConfig
from ...context import ProcessingContext
from ...placeholders import PlaceholderAction
from ...shared import CodeElement


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

        # Get collector (cached in context, uses pre-loaded descriptor)
        collector = context.get_collector()

        # Collect elements with bodies
        elements_with_bodies = collector.collect_with_bodies()

        # Process each element
        for element in elements_with_bodies:
            if element.body_node is None or element.body_range is None:
                continue

            # Get content lines count for single-line protection
            lines_count = self._get_content_lines_count(context, element)

            # Evaluate decision
            decision = self._evaluate(evaluators, element, lines_count)

            # Apply max_tokens post-processing
            if trimmer and decision.action == "keep":
                if trimmer.should_trim_element(context, element):
                    decision = FunctionBodyDecision(action="trim", max_tokens=normalized_cfg.max_tokens)

            # Apply decision
            self._apply_decision(context, decision, element, trimmer)

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
        element: CodeElement,
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
        element: CodeElement,
        trimmer: Optional[FunctionBodyTrimmer]
    ) -> None:
        """Apply the decision for a function body."""
        if decision.action == "keep":
            return

        if decision.action == "strip":
            self._apply_strip(context, element)

        elif decision.action == "trim" and trimmer:
            self._apply_trim(context, element, trimmer)

    def _apply_strip(
        self,
        context: ProcessingContext,
        element: CodeElement
    ) -> None:
        """
        Strip function body using pre-computed body_range.
        """
        func_type = element.profile.name

        # Get strippable range (in bytes) and convert to chars
        start_byte, end_byte = element.body_range
        start_char = context.doc.byte_to_char_position(start_byte)
        end_char = context.doc.byte_to_char_position(end_byte)

        # Nothing to strip if range is empty
        if start_char >= end_char:
            return

        # Get the stripped text to compute indentation from first content line
        stripped_text = context.raw_text[start_char:end_char]
        indent_prefix = self._compute_indent_from_text(stripped_text)

        # Check if body_range starts with newline (brace-languages after '{')
        placeholder_prefix = indent_prefix
        if stripped_text.startswith('\n'):
            placeholder_prefix = "\n" + indent_prefix

        context.add_placeholder(
            func_type + "_body",
            start_char,
            end_char,
            action=PlaceholderAction.OMIT,
            placeholder_prefix=placeholder_prefix,
        )

    def _get_content_lines_count(self, context: ProcessingContext, element: CodeElement) -> int:
        """
        Get count of content lines in function body for single-line protection.
        """
        if element.body_range is None:
            return 0

        start_byte, end_byte = element.body_range
        if start_byte >= end_byte:
            return 0

        start_char = context.doc.byte_to_char_position(start_byte)
        end_char = context.doc.byte_to_char_position(end_byte)
        content_text = context.raw_text[start_char:end_char]

        return self._count_content_lines(content_text)

    def _count_content_lines(self, text: str) -> int:
        """
        Count non-empty content lines in text.
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
        element: CodeElement,
        trimmer: FunctionBodyTrimmer
    ) -> None:
        """
        Trim function body to token budget.
        """
        result = trimmer.trim_element(context, element)
        if result is None:
            return

        func_type = element.profile.name

        # Compute placeholder prefix with proper newline handling
        placeholder_prefix = result.indent
        if not result.kept_prefix:
            placeholder_prefix = "\n" + result.indent

        # Add placeholder for the removed middle section with TRUNCATE action
        context.add_placeholder(
            func_type + "_body",
            result.placeholder_start_char,
            result.placeholder_end_char,
            action=PlaceholderAction.TRUNCATE,
            placeholder_prefix=placeholder_prefix,
        )
