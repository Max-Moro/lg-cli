"""
Comment optimization.
Processes comments and docstrings according to policy.
"""

from __future__ import annotations

import re
from typing import cast, Tuple, Union

from ..code_model import CommentConfig, CommentPolicy
from ..context import ProcessingContext
from ..tree_sitter_support import Node


class CommentOptimizer:
    """Handles comment processing optimization."""
    
    def __init__(self, cfg: Union[CommentPolicy, CommentConfig], adapter):
        """
        Initialize with parent adapter for language-specific checks.
        """
        self.cfg = cfg
        from ..code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)
    
    def apply(self, context: ProcessingContext) -> None:
        """
        Apply comment processing based on policy.

        Args:
            context: Processing context with document and editor
        """
        # If policy is keep_all, nothing to do
        if isinstance(self.cfg, str) and self.cfg == "keep_all":
            return

        # Check if we need special group handling for Go keep_first_sentence
        policy = self.cfg if isinstance(self.cfg, str) else getattr(self.cfg, 'policy', None)
        needs_group_handling = (
            policy == "keep_first_sentence" and
            hasattr(self.adapter, '_get_comment_analyzer')
        )

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

            # Determine if this is a docstring using multiple strategies:
            # 1. capture_name from Tree-sitter query (for languages with syntactic docstrings like Python)
            # 2. Text-based check (for JSDoc-style /** ... */)
            # 3. Position-based check using is_docstring_node (for Go and similar languages)
            # This must be computed BEFORE _should_process_comment for keep_doc policy
            is_docstring = (
                capture_name == "docstring" or
                self.adapter.is_documentation_comment(comment_text) or
                self.adapter.is_docstring_node(node, context.doc)
            )

            # Special handling for Go doc comment groups with keep_first_sentence
            if needs_group_handling and is_docstring:
                group = self.adapter._get_comment_analyzer(context.doc).get_comment_group_for_node(node)
                if group and len(group) > 1:
                    # Keep only first node of the group, remove the rest
                    for i, group_node in enumerate(group):
                        group_pos = (group_node.start_byte, group_node.end_byte)
                        processed_positions.add(group_pos)

                        if i == 0:
                            # First node: keep as is
                            continue
                        else:
                            # Rest of nodes: remove completely including trailing newline
                            start_char, end_char = context.doc.get_node_range(group_node)

                            # Extend to include trailing newline if present (handle \r\n and \n)
                            if end_char < len(context.doc.text):
                                if context.doc.text[end_char:end_char+2] == '\r\n':
                                    end_char += 2
                                elif context.doc.text[end_char] == '\n':
                                    end_char += 1

                            context.editor.add_replacement(
                                start_char, end_char, "",
                                edit_type="docstring_truncated"
                            )
                            context.metrics.mark_element_removed("docstring")
                    continue

            should_remove, replacement = self._should_process_comment(
                capture_name, comment_text, is_docstring, context
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
        capture_name: str,
        comment_text: str,
        is_docstring: bool,
        context: ProcessingContext
    ) -> Tuple[bool, str]:
        """
        Determine how to process a comment based on policy.

        Args:
            capture_name: Type of comment (comment, docstring, etc.)
            comment_text: Text content of the comment
            is_docstring: Whether this is a documentation comment (determined by multiple strategies)
            context: Processing context

        Returns:
            Tuple of (should_remove, replacement_text)
        """
        # Simple string policy
        if isinstance(self.cfg, str):
            policy: str = self.cfg
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
                    first_sentence = self.adapter.hook__extract_first_sentence(self, comment_text)
                    if first_sentence != comment_text:
                        return True, first_sentence
                    return False, ""
                else:
                    # Regular comments get removed with placeholder
                    return True, None
        
        # Complex policy (CommentConfig object)
        elif hasattr(self.cfg, 'policy'):
            return self._process_complex_comment_policy(comment_text, is_docstring, context)
        
        return False, ""
    
    def _process_complex_comment_policy(
        self,
        comment_text: str,
        is_docstring: bool,
        context: ProcessingContext
    ) -> Tuple[bool, str]:
        """
        Process comments using complex configuration.

        Args:
            comment_text: Comment text content
            is_docstring: Whether this is a documentation comment
            context: Processing context

        Returns:
            Tuple of (should_remove, replacement_text)
        """
        complex_cfg: CommentConfig  = cast(CommentConfig, self.cfg)

        # Check for forced removal patterns
        for pattern in complex_cfg.strip_patterns:
            try:
                if re.search(pattern, comment_text, re.IGNORECASE):
                    return True, None  # Use default placeholder
            except re.error:
                # Ignore invalid regex patterns
                continue
        
        # Check for preservation patterns
        for pattern in complex_cfg.keep_annotations:
            try:
                if re.search(pattern, comment_text, re.IGNORECASE):
                    # Check max_tokens for preserved comments
                    if complex_cfg.max_tokens is not None and context.tokenizer.count_text_cached(comment_text) > complex_cfg.max_tokens:
                        # Truncate comment with proper closing
                        truncated = self.adapter.hook__smart_truncate_comment(self, comment_text, complex_cfg.max_tokens, context.tokenizer)
                        return True, truncated
                    return False, ""  # Keep as is
            except re.error:
                # Ignore invalid regex patterns
                continue
        
        # Apply base policy with max_tokens consideration
        base_policy = complex_cfg.policy
        if base_policy == "keep_all":
            # Check max_tokens even for keep_all
            if complex_cfg.max_tokens is not None and context.tokenizer.count_text_cached(comment_text) > complex_cfg.max_tokens:
                truncated = self.adapter.hook__smart_truncate_comment(self, comment_text, complex_cfg.max_tokens, context.tokenizer)
                return True, truncated
            return False, ""
        
        elif base_policy == "strip_all":
            return True, None  # Use default placeholder
        
        elif base_policy == "keep_doc":
            if not is_docstring:
                return True, None  # Use default placeholder
            else:  # docstring
                if complex_cfg.max_tokens is not None and context.tokenizer.count_text_cached(comment_text) > complex_cfg.max_tokens:
                    truncated = self.adapter.hook__smart_truncate_comment(self, comment_text, complex_cfg.max_tokens, context.tokenizer)
                    return True, truncated
                return False, ""

        elif base_policy == "keep_first_sentence":
            if is_docstring:
                first_sentence = self.adapter.hook__extract_first_sentence(self, comment_text)
                # Apply max_tokens to extracted sentence
                if complex_cfg.max_tokens is not None and context.tokenizer.count_text_cached(first_sentence) > complex_cfg.max_tokens:
                    first_sentence = self.adapter.hook__smart_truncate_comment(self, first_sentence, complex_cfg.max_tokens, context.tokenizer)
                if first_sentence != comment_text:
                    return True, first_sentence
            else:
                # Regular comments get removed with placeholder
                return True, None  # Use default placeholder
        
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
    def smart_truncate_comment(comment_text: str, max_tokens: int, tokenizer) -> str:
        """
        Intelligently truncate a comment while preserving proper closing tags.
        
        Args:
            comment_text: Original comment text
            max_tokens: Maximum allowed tokens
            tokenizer: TokenService for counting tokens
            
        Returns:
            Properly truncated comment with correct closing tags
        """
        if tokenizer.count_text_cached(comment_text) <= max_tokens:
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
            closing_tokens = tokenizer.count_text_cached(closing)
            ellipsis_tokens = tokenizer.count_text_cached('…')
            content_budget = max(1, max_tokens - closing_tokens - ellipsis_tokens)

            if content_budget < 1:
                return f"/**\n{base_indent}* …\n{base_indent}*/"

            # Truncate using tokenizer
            truncated = tokenizer.truncate_to_tokens(comment_text, content_budget)
            return f"{truncated}…{closing}"

        # Regular multiline comment (/* … */)
        elif comment_text.startswith('/*') and comment_text.rstrip().endswith('*/'):
            # Reserve space for ' … */'
            closing = ' … */'
            closing_tokens = tokenizer.count_text_cached(closing)
            content_budget = max(1, max_tokens - closing_tokens)
            
            if content_budget < 1:
                return "/* … */"
            
            # Truncate using tokenizer
            truncated = tokenizer.truncate_to_tokens(comment_text, content_budget)
            return f"{truncated} … */"
        
        # Single line comments
        elif comment_text.startswith('//'):
            # Simple truncation with ellipsis
            ellipsis_tokens = tokenizer.count_text_cached('…')
            content_budget = max(1, max_tokens - ellipsis_tokens)
            
            if content_budget < 1:
                return f"//…"
            
            # Truncate using tokenizer
            truncated = tokenizer.truncate_to_tokens(comment_text, content_budget)
            return f"{truncated}…"
        
        # Fallback: simple truncation
        else:
            ellipsis_tokens = tokenizer.count_text_cached('…')
            content_budget = max(1, max_tokens - ellipsis_tokens)
            
            if content_budget < 1:
                return "…"
            
            # Truncate using tokenizer
            truncated = tokenizer.truncate_to_tokens(comment_text, content_budget)
            return f"{truncated}…"
