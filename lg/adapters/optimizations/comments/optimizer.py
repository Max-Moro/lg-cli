"""
Comment optimization.
Processes comments and docstrings according to policy.
"""

from __future__ import annotations

import logging
from typing import cast, List, Tuple, Union

logger = logging.getLogger(__name__)

from .decision import CommentDecision, PolicyEvaluator
from .evaluators import (
    StripPatternEvaluator,
    KeepAnnotationEvaluator,
    BasePolicyEvaluator,
    MaxTokensTransformer,
)
from .analyzer import CommentAnalyzer
from ...code_model import CommentConfig, CommentPolicy
from ...context import ProcessingContext
from ...placeholders import PlaceholderAction
from ...tree_sitter_support import Node


class CommentOptimizer:
    """Handles comment processing optimization."""
    
    def __init__(self, adapter):
        """Initialize with parent adapter."""
        from ...code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)
    
    def apply(self, context: ProcessingContext, cfg: Union[CommentPolicy, CommentConfig]) -> None:
        """
        Apply comment processing based on policy.

        Args:
            context: Processing context with document and editor
            cfg: Configuration for comment processing
        """
        # Normalize configuration
        normalized_cfg = self._normalize_config(cfg)

        # Early exit for keep_all with no constraints
        if (normalized_cfg.policy == "keep_all"
            and not normalized_cfg.max_tokens
            and not normalized_cfg.strip_patterns):
            return

        # Create decision pipeline
        evaluators, transformer = self._create_decision_pipeline(normalized_cfg)

        # Get language-specific comment analyzer
        analyzer = self.adapter.create_comment_analyzer(context)

        # Track processed nodes to avoid double-processing in group handling
        processed_positions = set()

        # Find and process comments
        comments = context.doc.query("comments")

        for node, capture_name in comments:
            # Skip if already processed (as part of a group)
            position = (node.start_byte, node.end_byte)
            if position in processed_positions:
                continue

            comment_text = context.doc.get_node_text(node)

            # Determine if this is a docstring using the analyzer
            is_docstring = analyzer.is_documentation_comment(node, comment_text, capture_name)

            # Handle comment groups for keep_first_sentence policy
            if normalized_cfg.policy == "keep_first_sentence" and is_docstring:
                group_handled = self._handle_comment_group_for_first_sentence(
                    node, analyzer, context, processed_positions
                )
                if group_handled:
                    # Group was processed, first node falls through to standard processing
                    pass

            # Evaluate and execute
            decision = self._evaluate_comment(
                evaluators, transformer, comment_text, is_docstring, context, analyzer
            )
            self._apply_decision(context, node, decision, is_docstring)


    def _normalize_config(self, cfg: Union[CommentPolicy, CommentConfig]) -> CommentConfig:
        """
        Normalize configuration to CommentConfig.
        Converts simple string policy to full config object.

        Args:
            cfg: Configuration (either string policy or CommentConfig object)

        Returns:
            Normalized CommentConfig object
        """
        if isinstance(cfg, str):
            # Simple mode: just a policy string
            return CommentConfig(
                policy=cfg,
                max_tokens=None,
                keep_annotations=[],
                strip_patterns=[]
            )
        else:
            # Already CommentConfig
            return cfg

    def _create_decision_pipeline(
        self,
        cfg: CommentConfig
    ) -> Tuple[List[PolicyEvaluator], MaxTokensTransformer]:
        """
        Create evaluator pipeline based on configuration.
        Returns (evaluators, transformer) tuple.

        Args:
            cfg: Normalized comment configuration

        Returns:
            Tuple of (evaluators list, max_tokens transformer)
        """
        evaluators = []

        # Priority 1: Strip patterns (forced removal)
        if cfg.strip_patterns:
            evaluators.append(StripPatternEvaluator(cfg.strip_patterns))

        # Priority 2: Keep annotations (forced preservation)
        if cfg.keep_annotations:
            evaluators.append(KeepAnnotationEvaluator(cfg.keep_annotations))

        # Priority 3: Base policy (default behavior)
        evaluators.append(BasePolicyEvaluator(cfg.policy))

        # Post-processor: max_tokens enforcement
        transformer = MaxTokensTransformer(cfg.max_tokens)

        return evaluators, transformer

    def _evaluate_comment(
        self,
        evaluators: List[PolicyEvaluator],
        transformer: MaxTokensTransformer,
        comment_text: str,
        is_docstring: bool,
        context: ProcessingContext,
        analyzer: CommentAnalyzer
    ) -> CommentDecision:
        """
        Run evaluation pipeline and return final decision.

        Args:
            evaluators: List of policy evaluators
            transformer: Max tokens transformer
            comment_text: Comment text content
            is_docstring: Whether this is a documentation comment
            context: Processing context (for transformer)
            analyzer: Language-specific comment analyzer

        Returns:
            Final CommentDecision after pipeline processing
        """
        # Run evaluators in priority order
        for evaluator in evaluators:
            decision = evaluator.evaluate(comment_text, is_docstring, analyzer)
            if decision is not None:
                # Apply max_tokens transformation if needed
                return transformer.transform(decision, context, analyzer)

        # Fallback (should never happen due to BasePolicyEvaluator)
        return CommentDecision("keep", replacement=comment_text)

    def _apply_decision(
        self,
        context: ProcessingContext,
        node: Node,
        decision: CommentDecision,
        is_docstring: bool
    ) -> None:
        """
        Execute decision by updating context.

        Args:
            context: Processing context
            node: Comment node to process
            decision: Decision from evaluation pipeline
            is_docstring: Whether this is a documentation comment
        """
        element_type = "docstring" if is_docstring else "comment"

        if decision.action == "keep":
            # Nothing to do
            return

        elif decision.action == "remove":
            # Remove with placeholder
            context.add_placeholder_for_node(element_type, node, action = PlaceholderAction.OMIT)

        elif decision.action == "transform":
            # Replace with transformed (shortened) text
            context.add_placeholder_for_node(
                element_type,
                node,
                action=PlaceholderAction.TRUNCATE,
                replacement_text=decision.replacement,
                add_suffix_comment=False,  # Shortened comment doesn't need extra indication
            )

    def _handle_comment_group_for_first_sentence(
        self,
        node: Node,
        analyzer: CommentAnalyzer,
        context: ProcessingContext,
        processed_positions: set
    ) -> bool:
        """
        Handle comment groups for keep_first_sentence policy.

        For grouped comments (e.g., consecutive // in Go, /// in Rust):
        - Marks all nodes in group as processed
        - Removes all lines except the first one
        - First line will be processed normally to extract first sentence

        Args:
            node: Current comment node
            analyzer: Language-specific comment analyzer
            context: Processing context
            processed_positions: Set to track processed node positions

        Returns:
            True if group was handled (first node should fall through to standard processing),
            False if no group or single-node group
        """
        from .text_utils import get_line_range

        group = analyzer.get_comment_group(node)
        if not group or len(group) <= 1:
            return False

        # Process the group: first node gets first sentence, rest removed
        for i, group_node in enumerate(group):
            group_pos = (group_node.start_byte, group_node.end_byte)
            processed_positions.add(group_pos)

            if i == 0:
                # First node: will be processed normally below (fall through)
                continue

            # Rest of nodes: remove the entire line (including leading indent and trailing newline)
            start_char, end_char = context.doc.get_node_range(group_node)

            # Extend to full line boundaries using utility
            start_char, end_char = get_line_range(context.doc.text, start_char, end_char)

            context.editor.add_replacement(
                start_char, end_char, "",
                edit_type="docstring_truncated"
            )
            context.metrics.mark_element_removed("docstring")

        return True