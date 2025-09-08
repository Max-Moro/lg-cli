"""
Comment optimization.
Processes comments and docstrings according to policy.
"""

from __future__ import annotations

import re
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
                        # Truncate comment with proper closing
                        truncated = self.adapter.hook__smart_truncate_comment(self, comment_text, policy.max_length)
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
                truncated = self.adapter.hook__smart_truncate_comment(self, comment_text, policy.max_length)
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
                    truncated = self.adapter.hook__smart_truncate_comment(self, comment_text, policy.max_length)
                    return True, truncated
                return False, ""
        
        elif base_policy == "keep_first_sentence":
            if capture_name == "docstring" or self.adapter.is_documentation_comment(comment_text):
                first_sentence = self.adapter.hook__extract_first_sentence(self, comment_text)
                # Apply max_length to extracted sentence
                if policy.max_length is not None and len(first_sentence) > policy.max_length:
                    first_sentence = self.adapter.hook__smart_truncate_comment(self, first_sentence, policy.max_length)
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
            First sentence with appropriate punctuation and formatting
        """

        # Handle JSDoc comments (/** ... */) with proper indentation
        if text.strip().startswith('/**'):
            # Extract the original indentation by looking at the first line
            lines = text.split('\n')
            if len(lines) > 1:
                # Get indentation from the second line (first content line)
                second_line = lines[1] if len(lines) > 1 else ''
                indent_match = re.match(r'^(\s*)\*', second_line)
                base_indent = indent_match.group(1) if indent_match else '     '
            else:
                base_indent = '     '  # Default JSDoc indentation

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
                        # Return with proper JSDoc formatting and indentation
                        return f'/**\n{base_indent}* {first}.\n{base_indent}*/'

            return text  # Fallback if parsing fails

        # Handle regular single-line comments
        elif text.startswith('//'):
            # Remove comment markers and find first sentence
            clean_text = text[2:].strip()
            sentences = re.split(r'[.!?]+', clean_text)
            if sentences and sentences[0].strip():
                first = sentences[0].strip()
                return f"// {first}."

        # Handle regular multiline comments (/* ... */)
        elif text.startswith('/*') and text.rstrip().endswith('*/'):
            # Extract content between /* and */
            match = re.match(r'/\*\s*(.*?)\s*\*/', text, re.DOTALL)
            if match:
                content = match.group(1)
                sentences = re.split(r'[.!?]+', content)
                if sentences and sentences[0].strip():
                    first = sentences[0].strip()
                    return f"/* {first}. */"

        return text  # Fallback to original text

    @staticmethod
    def smart_truncate_comment(comment_text: str, max_length: int) -> str:
        """
        Intelligently truncate a comment while preserving proper closing tags.
        
        Args:
            comment_text: Original comment text
            max_length: Maximum allowed length
            
        Returns:
            Properly truncated comment with correct closing tags
        """
        if len(comment_text) <= max_length:
            return comment_text

        # JSDoc/TypeScript style comments (/** ... */)
        if comment_text.strip().startswith('/**'):
            # Preserve indentation from original
            lines = comment_text.split('\n')
            if len(lines) > 1:
                second_line = lines[1] if len(lines) > 1 else ''
                indent_match = re.match(r'^(\s*)\*', second_line)
                base_indent = indent_match.group(1) if indent_match else '     '
            else:
                base_indent = '     '

            # Reserve space for closing with proper indentation
            closing = f'\n{base_indent}*/'
            truncate_to = max_length - len(closing) - 1  # -1 for ellipsis

            if truncate_to < 4:  # Minimum for "/**"
                return f"/**\n{base_indent}* …\n{base_indent}*/"

            truncated = comment_text[:truncate_to].rstrip()
            return f"{truncated}…{closing}"

        # Regular multiline comment (/* … */)
        elif comment_text.startswith('/*') and comment_text.rstrip().endswith('*/'):
            # Reserve space for ' … */'
            truncate_to = max_length - 4
            if truncate_to < 2:  # Minimum for "/* */"
                return "/* … */"
            
            truncated = comment_text[:truncate_to].rstrip()
            return f"{truncated} … */"
        
        # Single line comments
        elif comment_text.startswith('//'):
            # Simple truncation with ellipsis
            truncate_to = max_length - 1  # Reserve space for '…'
            if truncate_to < 0:
                return f"//…"
            
            truncated = comment_text[:truncate_to].rstrip()
            return f"{truncated}…"
        
        # Fallback: simple truncation
        else:
            truncate_to = max_length - 1
            if truncate_to < 0:
                return "…"
            
            truncated = comment_text[:truncate_to].rstrip()
            return f"{truncated}…"
