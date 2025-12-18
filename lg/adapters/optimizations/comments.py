"""
Comment optimization.
Processes comments and docstrings according to policy.
"""

from __future__ import annotations

import logging
import re
from typing import cast, Tuple, Union

logger = logging.getLogger(__name__)

from .comment_analysis import CommentAnalyzer
from ..code_model import CommentConfig, CommentPolicy
from ..context import ProcessingContext
from ..tree_sitter_support import Node


class CommentOptimizer:
    """Handles comment processing optimization."""
    
    def __init__(self, adapter):
        """Initialize with parent adapter."""
        from ..code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)
    
    def apply(self, context: ProcessingContext, cfg: Union[CommentPolicy, CommentConfig]) -> None:
        """
        Apply comment processing based on policy.

        Args:
            context: Processing context with document and editor
            cfg: Configuration for comment processing
        """
        # If policy is keep_all, nothing to do
        if isinstance(cfg, str) and cfg == "keep_all":
            return

        # Get language-specific comment analyzer
        analyzer = self.adapter.create_comment_analyzer(context.doc, context.code_analyzer)

        # Get policy for group handling check
        policy = cfg if isinstance(cfg, str) else getattr(cfg, 'policy', None)

        # Track processed nodes to avoid double-processing in group handling
        processed_positions = set()

        # Find comments in the code
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
            if policy == "keep_first_sentence" and is_docstring:
                group_handled = self._handle_comment_group_for_first_sentence(
                    node, analyzer, context, processed_positions
                )
                if group_handled:
                    # Group was processed, first node falls through to standard processing
                    pass

            # Standard processing
            should_remove, replacement = self._should_process_comment(
                cfg, comment_text, is_docstring, context, analyzer
            )

            if should_remove:
                self.remove_comment(
                    context,
                    node,
                    is_docstring=is_docstring,
                    replacement=replacement
                )

    @staticmethod
    def remove_comment(
            context: ProcessingContext,
            comment_node: Node,
            is_docstring: bool,
            replacement: str = None
    ) -> bool:
        """
        Remove comment with automatic metrics accounting.

        Args:
            context: Processing context with document access
            comment_node: Comment node to remove
            is_docstring: Whether this comment is a docstring
            replacement: Custom replacement (if None, placeholder is used)
        """
        element_type = "docstring" if is_docstring else "comment"

        if replacement is None:
            # Use placeholder API
            context.add_placeholder_for_node(element_type, comment_node)
        else:
            # Custom replacement
            start_char, end_char = context.doc.get_node_range(comment_node)
            context.editor.add_replacement(
                start_char, end_char, replacement,
                edit_type=f"{element_type}_truncated",
            )
            context.metrics.mark_element_removed(element_type)

        return True

    def _should_process_comment(
        self,
        cfg: Union[CommentPolicy, CommentConfig],
        comment_text: str,
        is_docstring: bool,
        context: ProcessingContext,
        analyzer: CommentAnalyzer
    ) -> Tuple[bool, str]:
        """
        Determine how to process a comment based on policy.

        Args:
            cfg: Configuration for comment processing
            comment_text: Text content of the comment
            is_docstring: Whether this is a documentation comment (determined by multiple strategies)
            context: Processing context
            analyzer: Language-specific comment analyzer

        Returns:
            Tuple of (should_remove, replacement_text)
        """
        # Simple string policy
        if isinstance(cfg, str):
            policy: str = cfg
            if policy == "keep_all":
                return False, ""
            elif policy == "strip_all":
                # Remove all comments with placeholder (None means use default placeholder)
                return True, None
            elif policy == "keep_doc":
                # Remove regular comments, keep docstrings
                # Use is_docstring parameter which includes all detection strategies
                if not is_docstring:
                    return True, None
                else:
                    return False, ""
            elif policy == "keep_first_sentence":
                # For documentation comments, keep first sentence only
                if is_docstring:
                    first_sentence = analyzer.extract_first_sentence(comment_text)
                    if first_sentence != comment_text:
                        return True, first_sentence
                    return False, ""
                else:
                    # Regular comments get removed with placeholder
                    return True, None

        # Complex policy (CommentConfig object)
        elif hasattr(cfg, 'policy'):
            return self._process_complex_comment_policy(cfg, comment_text, is_docstring, context, analyzer)

        return False, ""
    
    def _process_complex_comment_policy(
        self,
        cfg: Union[CommentPolicy, CommentConfig],
        comment_text: str,
        is_docstring: bool,
        context: ProcessingContext,
        analyzer: CommentAnalyzer
    ) -> Tuple[bool, str]:
        """
        Process comments using complex configuration.

        Args:
            cfg: Configuration for comment processing
            comment_text: Comment text content
            is_docstring: Whether this is a documentation comment
            context: Processing context
            analyzer: Language-specific comment analyzer

        Returns:
            Tuple of (should_remove, replacement_text)
        """
        complex_cfg: CommentConfig = cast(CommentConfig, cfg)

        # Check for forced removal patterns
        for pattern in complex_cfg.strip_patterns:
            try:
                if re.search(pattern, comment_text, re.IGNORECASE):
                    return True, None  # Use default placeholder
            except re.error as e:
                logger.warning("Invalid regex pattern in strip_patterns '%s': %s", pattern, e)
                continue

        # Check for preservation patterns
        for pattern in complex_cfg.keep_annotations:
            try:
                if re.search(pattern, comment_text, re.IGNORECASE):
                    # Check max_tokens for preserved comments
                    if complex_cfg.max_tokens is not None and context.tokenizer.count_text_cached(comment_text) > complex_cfg.max_tokens:
                        # Truncate comment with proper closing
                        truncated = analyzer.truncate_comment(comment_text, complex_cfg.max_tokens, context.tokenizer)
                        return True, truncated
                    return False, ""  # Keep as is
            except re.error as e:
                logger.warning("Invalid regex pattern in keep_annotations '%s': %s", pattern, e)
                continue

        # Apply base policy with max_tokens consideration
        base_policy = complex_cfg.policy
        if base_policy == "keep_all":
            # Check max_tokens even for keep_all
            if complex_cfg.max_tokens is not None and context.tokenizer.count_text_cached(comment_text) > complex_cfg.max_tokens:
                truncated = analyzer.truncate_comment(comment_text, complex_cfg.max_tokens, context.tokenizer)
                return True, truncated
            return False, ""

        elif base_policy == "strip_all":
            return True, None  # Use default placeholder

        elif base_policy == "keep_doc":
            if not is_docstring:
                return True, None  # Use default placeholder
            else:  # docstring
                if complex_cfg.max_tokens is not None and context.tokenizer.count_text_cached(comment_text) > complex_cfg.max_tokens:
                    truncated = analyzer.truncate_comment(comment_text, complex_cfg.max_tokens, context.tokenizer)
                    return True, truncated
                return False, ""

        elif base_policy == "keep_first_sentence":
            if is_docstring:
                first_sentence = analyzer.extract_first_sentence(comment_text)
                # Apply max_tokens to extracted sentence
                if complex_cfg.max_tokens is not None and context.tokenizer.count_text_cached(first_sentence) > complex_cfg.max_tokens:
                    first_sentence = analyzer.truncate_comment(first_sentence, complex_cfg.max_tokens, context.tokenizer)
                if first_sentence != comment_text:
                    return True, first_sentence
            else:
                # Regular comments get removed with placeholder
                return True, None  # Use default placeholder

        return False, ""

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