"""
Comment optimization.
Processes comments and docstrings according to policy.
"""

from __future__ import annotations

from typing import Tuple, cast

from ..code_model import CommentConfig
from ..context import ProcessingContext
from ..tree_sitter_support import Node


class CommentOptimizer:
    """Handles comment processing optimization."""
    
    def __init__(self, adapter):
        """
        Initialize with parent adapter for language-specific checks.
        
        Args:
            adapter: Parent CodeAdapter instance for language-specific methods
        """
        from ..code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)
    
    def apply(self, context: ProcessingContext) -> None:
        """
        Apply comment processing based on policy.
        
        Args:
            context: Processing context with document and editor
        """
        policy = self.adapter.cfg.comment_policy
        
        # If policy is keep_all, nothing to do
        if isinstance(policy, str) and policy == "keep_all":
            return
        
        # Find comments in the code
        comments = context.doc.query("comments")

        for node, capture_name in comments:
            comment_text = context.doc.get_node_text(node)

            should_remove, replacement = self._should_process_comment(
                policy, capture_name, comment_text, context
            )

            if should_remove:
                self.remove_comment(
                    context,
                    node,
                    comment_type=capture_name,
                    replacement=replacement,
                    placeholder_style=self.adapter.cfg.placeholders.style
                )

    @staticmethod
    def remove_comment(
            context: ProcessingContext,
            comment_node: Node,
            comment_type: str = "comment",
            replacement: str = None,
            placeholder_style: str = "inline"
    ) -> bool:
        """
        Удаляет комментарий с автоматическим учетом метрик.

        Args:
            context: Контекст обработки с доступом к документу
            comment_node: Узел комментария для удаления
            comment_type: Тип комментария ("comment", "docstring")
            replacement: Кастомная замена (если None, используется плейсхолдер)
            placeholder_style: Стиль плейсхолдера
        """
        start_byte, end_byte = context.doc.get_node_range(comment_node)
        start_line, end_line = context.doc.get_line_range(comment_node)
        lines_count = end_line - start_line + 1

        if replacement is None:
            replacement = context.placeholder_gen.create_comment_placeholder(
                comment_type, style=placeholder_style
            )
            context.metrics.mark_placeholder_inserted()

        context.editor.add_replacement(
            start_byte, end_byte, replacement,
            type=f"{comment_type}_removal",
            is_placeholder=bool(replacement),
            lines_removed=lines_count
        )

        context.metrics.mark_comment_removed()
        if replacement:
            context.metrics.add_lines_saved(lines_count)
            bytes_saved = end_byte - start_byte - len(replacement.encode('utf-8'))
            if bytes_saved > 0:
                context.metrics.add_bytes_saved(bytes_saved)

        return True

    def _should_process_comment(
        self, 
        policy, 
        capture_name: str, 
        comment_text: str, 
        context: ProcessingContext
    ) -> Tuple[bool, str]:
        """
        Determine how to process a comment based on policy.
        
        Args:
            policy: Comment processing policy (string or CommentConfig object)
            capture_name: Type of comment (comment, docstring, etc.)
            comment_text: Text content of the comment
            context: Processing context
            
        Returns:
            Tuple of (should_remove, replacement_text)
        """
        # Simple string policy
        if isinstance(policy, str):
            if policy == "keep_all":
                return False, ""
            elif policy == "strip_all":
                # Remove all comments with placeholder
                placeholder = context.placeholder_gen.create_comment_placeholder(
                    capture_name, style=self.adapter.cfg.placeholders.style
                )
                return True, placeholder
            elif policy == "keep_doc":
                # Remove regular comments, keep docstrings
                if capture_name == "comment" and not self.adapter.is_documentation_comment(comment_text):
                    placeholder = context.placeholder_gen.create_comment_placeholder(
                        capture_name, style=self.adapter.cfg.placeholders.style
                    )
                    return True, placeholder
                else:
                    return False, ""
            elif policy == "keep_first_sentence":
                # For documentation comments (JSDoc, etc.), keep first sentence only
                if capture_name == "docstring" or self.adapter.is_documentation_comment(comment_text):
                    first_sentence = self.adapter.hook__extract_first_sentence(self, comment_text)
                    if first_sentence != comment_text:
                        return True, first_sentence
                    return False, ""
                else:
                    # Regular comments get removed with placeholder
                    placeholder = context.placeholder_gen.create_comment_placeholder(
                        capture_name, style=self.adapter.cfg.placeholders.style
                    )
                    return True, placeholder
        
        # Complex policy (CommentConfig object)
        elif hasattr(policy, 'policy'):
            return self._process_complex_comment_policy(policy, capture_name, comment_text, context)
        
        return False, ""
    
    def _process_complex_comment_policy(
        self,
        policy: CommentConfig,
        capture_name: str,
        comment_text: str,
        context: ProcessingContext
    ) -> Tuple[bool, str]:
        """
        Process comments using complex policy configuration.
        
        Args:
            policy: CommentConfig object with detailed rules
            capture_name: Type of comment
            comment_text: Comment text content
            context: Processing context
            
        Returns:
            Tuple of (should_remove, replacement_text)
        """
        import re
        
        # Check for forced removal patterns
        for pattern in policy.strip_patterns:
            try:
                if re.search(pattern, comment_text, re.IGNORECASE):
                    placeholder = context.placeholder_gen.create_comment_placeholder(
                        capture_name, style=self.adapter.cfg.placeholders.style
                    )
                    return True, placeholder
            except re.error:
                # Ignore invalid regex patterns
                continue
        
        # Check for preservation patterns
        for pattern in policy.keep_annotations:
            try:
                if re.search(pattern, comment_text, re.IGNORECASE):
                    # Check max_length for preserved comments
                    if policy.max_length is not None and len(comment_text) > policy.max_length:
                        # Truncate comment
                        truncated = comment_text[:policy.max_length].rstrip()
                        truncated += "..."
                        return True, truncated
                    return False, ""  # Keep as is
            except re.error:
                # Ignore invalid regex patterns
                continue
        
        # Apply base policy with max_length consideration
        base_policy = policy.policy
        if base_policy == "keep_all":
            # Check max_length even for keep_all
            if policy.max_length is not None and len(comment_text) > policy.max_length:
                truncated = comment_text[:policy.max_length].rstrip() + "..."
                return True, truncated
            return False, ""
        
        elif base_policy == "strip_all":
            placeholder = context.placeholder_gen.create_comment_placeholder(
                capture_name, style=self.adapter.cfg.placeholders.style
            )
            return True, placeholder
        
        elif base_policy == "keep_doc":
            if capture_name == "comment" and not self.adapter.is_documentation_comment(comment_text):
                placeholder = context.placeholder_gen.create_comment_placeholder(
                    capture_name, style=self.adapter.cfg.placeholders.style
                )
                return True, placeholder
            else:  # docstring
                if policy.max_length is not None and len(comment_text) > policy.max_length:
                    truncated = comment_text[:policy.max_length].rstrip() + "..."
                    return True, truncated
                return False, ""
        
        elif base_policy == "keep_first_sentence":
            if capture_name == "docstring" or self.adapter.is_documentation_comment(comment_text):
                first_sentence = self.adapter.hook__extract_first_sentence(self, comment_text)
                # Apply max_length to extracted sentence
                if policy.max_length is not None and len(first_sentence) > policy.max_length:
                    first_sentence = first_sentence[:policy.max_length].rstrip() + "..."
                if first_sentence != comment_text:
                    return True, first_sentence
            else:
                # Regular comments get removed with placeholder
                placeholder = context.placeholder_gen.create_comment_placeholder(
                    capture_name, style=self.adapter.cfg.placeholders.style
                )
                return True, placeholder
        
        return False, ""

    @staticmethod
    def extract_first_sentence(text: str) -> str:
        """
        Extract the first sentence from comment text.

        Args:
            text: Comment text to process

        Returns:
            First sentence with appropriate punctuation
        """
        import re

        # Handle JSDoc comments (/** ... */)
        if text.strip().startswith('/**'):
            # Extract content between /** and */
            match = re.match(r'/\*\*\s*(.*?)\s*\*/', text, re.DOTALL)
            if match:
                content = match.group(1)
                # Remove leading * from each line
                lines = content.split('\n')
                clean_lines = []
                for line in lines:
                    clean_line = re.sub(r'^\s*\*\s?', '', line)
                    if clean_line.strip():
                        clean_lines.append(clean_line)

                if clean_lines:
                    # Find first sentence in the cleaned content
                    full_text = ' '.join(clean_lines)
                    sentences = re.split(r'[.!?]+', full_text)
                    if sentences and sentences[0].strip():
                        first = sentences[0].strip()
                        return f'/**\n * {first}.\n */'

            return text  # Fallback if parsing fails

        # Handle regular comments
        else:
            # Remove comment markers and find first sentence
            clean_text = text.strip()
            if clean_text.startswith('//'):
                clean_text = clean_text[2:].strip()
            elif clean_text.startswith('/*') and clean_text.endswith('*/'):
                clean_text = clean_text[2:-2].strip()

            sentences = re.split(r'[.!?]+', clean_text)
            if sentences and sentences[0].strip():
                first = sentences[0].strip()
                return f"{first}."

        return text  # Fallback to original text
