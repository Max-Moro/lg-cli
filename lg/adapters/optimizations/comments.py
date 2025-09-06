"""
Comment optimization.
Processes comments and docstrings according to policy.
"""

from __future__ import annotations

from typing import Tuple

from ..code_model import CommentConfig
from ..context import ProcessingContext


class CommentOptimizer:
    """Handles comment processing optimization."""
    
    def __init__(self, adapter):
        """
        Initialize with parent adapter for language-specific checks.
        
        Args:
            adapter: Parent CodeAdapter instance for language-specific methods
        """
        self.adapter = adapter
    
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
        comments = context.query("comments")

        for node, capture_name in comments:
            comment_text = context.get_node_text(node)
            
            should_remove, replacement = self._should_process_comment(
                policy, capture_name, comment_text, context
            )
            
            if should_remove:
                context.remove_comment(
                    node,
                    comment_type=capture_name,
                    replacement=replacement,
                    placeholder_style=self.adapter.cfg.placeholders.style
                )
    
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
                if capture_name == "comment":
                    # For TypeScript/JavaScript, check if this is a JSDoc comment
                    if self.adapter.name in ("typescript", "javascript"):
                        if self._is_jsdoc_comment(comment_text):
                            return False, ""  # Keep JSDoc comments
                    
                    # For all languages, remove regular comments
                    placeholder = context.placeholder_gen.create_comment_placeholder(
                        capture_name, style=self.adapter.cfg.placeholders.style
                    )
                    return True, placeholder
                else:
                    return False, ""
            elif policy == "keep_first_sentence":
                # For docstrings, keep first sentence only
                if capture_name == "docstring":
                    first_sentence = self._extract_first_sentence(comment_text)
                    if first_sentence != comment_text:
                        return True, first_sentence
                    return False, ""
                # Regular comments get removed
                elif capture_name == "comment":
                    placeholder = context.placeholder_gen.create_comment_placeholder(
                        capture_name, style=self.adapter.cfg.placeholders.style
                    )
                    return True, placeholder
                else:
                    return False, ""
        
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
            if capture_name == "comment":
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
            if capture_name == "docstring":
                first_sentence = self._extract_first_sentence(comment_text)
                # Apply max_length to extracted sentence
                if policy.max_length is not None and len(first_sentence) > policy.max_length:
                    first_sentence = first_sentence[:policy.max_length].rstrip() + "..."
                if first_sentence != comment_text:
                    return True, first_sentence
            elif capture_name == "comment":
                placeholder = context.placeholder_gen.create_comment_placeholder(
                    capture_name, style=self.adapter.cfg.placeholders.style
                )
                return True, placeholder
        
        return False, ""
    
    def _is_jsdoc_comment(self, comment_text: str) -> bool:
        """
        Check if a comment is a JSDoc comment (TypeScript/JavaScript documentation).
        
        Args:
            comment_text: The comment text to check
            
        Returns:
            True if this is a JSDoc comment that should be preserved
        """
        # JSDoc comments start with /** (not just /*)
        return comment_text.strip().startswith('/**')

    def _extract_first_sentence(self, text: str) -> str:
        """
        Extract the first sentence from comment text.
        
        Args:
            text: Comment text to process
            
        Returns:
            First sentence with appropriate punctuation
        """
        # Remove quotes for Python docstrings
        clean_text = text.strip('"\'')
        
        # Find first sentence (ends with . ! ?)
        import re
        sentences = re.split(r'[.!?]+', clean_text)
        if sentences and sentences[0].strip():
            first = sentences[0].strip()
            # Restore quotes if this is Python docstring
            if text.startswith('"""') or text.startswith("'''"):
                return f'"""{first}."""'
            elif text.startswith('"') or text.startswith("'"):
                quote = text[0]
                return f'{quote}{first}.{quote}'
            else:
                return f"{first}."
        
        return text  # Fallback to original text
