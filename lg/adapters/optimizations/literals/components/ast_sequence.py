"""
AST-based sequence literal processor component.

Handles processing of sequence literals that require AST-based element extraction,
such as C/C++ concatenated strings where elements cannot be reliably extracted
via text parsing (no explicit separators).

This component:
- Extracts child string nodes from AST using tree-sitter queries
- Selects as many strings as fit within token budget
- Inserts placeholder inside the last kept string
- Handles both single-line and multiline formatting
"""

from __future__ import annotations

import re
from typing import Optional, List

from lg.stats.tokenizer import TokenService
from ..patterns import LiteralProfile, SequenceProfile, TrimResult, StringProfile
from ..utils.indentation import detect_base_indent, detect_element_indent


class ASTSequenceProcessor:
    """
    Processes sequence literals using AST-based element extraction.

    Used for sequences where elements cannot be reliably extracted via text
    parsing (e.g., no separators). Common use cases:
    - C/C++ concatenated strings: "a" "b" "c"
    - Languages with implicit sequence concatenation

    Uses tree-sitter AST to extract child elements, then keeps as many
    as fit within the token budget.
    """

    def __init__(self, tokenizer: TokenService, string_profiles: List[StringProfile]):
        """
        Initialize processor.

        Args:
            tokenizer: Token counting service
            descriptor: Language literal descriptor (for accessing string profiles)
        """
        self.tokenizer = tokenizer
        self.string_profiles = string_profiles

    def can_handle(
        self,
        profile: LiteralProfile,
        node,
        doc,
    ) -> bool:
        """
        Check if this component is applicable to the given literal.

        ASTSequenceProcessor is applicable only to SequenceProfile
        with requires_ast_extraction=True flag.

        Args:
            profile: Literal profile
            node: Tree-sitter node (unused, kept for interface consistency)
            doc: Tree-sitter document (unused, kept for interface consistency)

        Returns:
            True if this component should handle the literal
        """
        return (
            isinstance(profile, SequenceProfile) and
            profile.requires_ast_extraction
        )


    def process(
        self,
        node,
        doc,
        source_text: str,
        profile: SequenceProfile,
        token_budget: int,
    ) -> Optional[TrimResult]:
        """
        Full autonomous processing of AST-based sequence literal.

        Component itself:
        - Extracts text from node
        - Determines indentation
        - Parses elements via AST
        - Formats result

        Args:
            node: Tree-sitter node
            doc: Tree-sitter document
            source_text: Full source text
            profile: SequenceProfile with requires_ast_extraction=True
            token_budget: Token budget

        Returns:
            TrimResult if optimization applied, None otherwise
        """
        text = doc.get_node_text(node)
        base_indent = detect_base_indent(source_text, node.start_byte)
        element_indent = detect_element_indent(text, base_indent)

        # Collect all string child nodes by querying each string profile
        child_strings = []
        child_string_set = set()  # Track by (start, end) to avoid duplicates

        for str_profile in self.string_profiles:
            matched_nodes = doc.query_nodes(str_profile.query, "lit")
            for matched_node in matched_nodes:
                # Check if this node is a direct or indirect child of the input node
                if (matched_node.start_byte >= node.start_byte and
                    matched_node.end_byte <= node.end_byte):
                    coords = (matched_node.start_byte, matched_node.end_byte)
                    if coords not in child_string_set:
                        child_string_set.add(coords)
                        child_strings.append(matched_node)

        # Sort by position
        child_strings.sort(key=lambda n: n.start_byte)

        if not child_strings:
            return None  # No strings to process

        # Get full text and token count
        full_text = doc.get_node_text(node)
        original_tokens = self.tokenizer.count_text_cached(full_text)

        # If already within budget, no trimming needed
        if original_tokens <= token_budget:
            return None

        # Keep as many complete child strings as fit in budget
        # Overhead is just for placeholder (no delimiters)
        placeholder = profile.placeholder_template
        placeholder_tokens = self.tokenizer.count_text_cached(placeholder)

        content_budget = max(1, token_budget - placeholder_tokens)

        # Accumulate child strings until we exceed budget
        kept_strings = []
        running_tokens = 0

        for child in child_strings:
            child_text = doc.get_node_text(child)
            child_tokens = self.tokenizer.count_text_cached(child_text)

            if running_tokens + child_tokens <= content_budget:
                kept_strings.append(child_text)
                running_tokens += child_tokens
            else:
                break  # Budget exceeded, stop

        # Need at least one string
        if not kept_strings:
            # Keep first string even if it exceeds budget
            kept_strings = [doc.get_node_text(child_strings[0])]
            running_tokens = self.tokenizer.count_text_cached(kept_strings[0])

        # If we kept all strings, no optimization needed
        if len(kept_strings) == len(child_strings):
            return None

        # Build trimmed text: insert placeholder INSIDE last string (before closing delimiter)
        last_child_text = doc.get_node_text(child_strings[len(kept_strings) - 1])

        # Detect closing delimiter from last child string text
        # Check common string delimiters
        closing_delimiter = None
        if last_child_text.endswith('"""'):
            closing_delimiter = '"""'
        elif last_child_text.endswith("'''"):
            closing_delimiter = "'''"
        elif last_child_text.endswith('"'):
            # Could be regular string or raw string ending
            # Check if it's a raw string (language-specific)
            if last_child_text.startswith('R"') or last_child_text.startswith('r"'):
                # Raw string - find closing sequence
                match = re.search(r'\)([^)]*)"$', last_child_text)
                if match:
                    closing_delimiter = ")" + match.group(1) + '"'
                else:
                    closing_delimiter = ')"'  # Default
            else:
                closing_delimiter = '"'
        elif last_child_text.endswith("'"):
            closing_delimiter = "'"

        # Preserve indentation from original
        lines = full_text.split('\n')
        if len(lines) > 1:
            # Multiline: build kept strings, insert placeholder in last one
            parts = []
            for i, s in enumerate(kept_strings):
                if i == len(kept_strings) - 1:
                    # Last string: insert placeholder before closing delimiter
                    if closing_delimiter and s.endswith(closing_delimiter):
                        parts.append(s[:-len(closing_delimiter)] + placeholder + closing_delimiter)
                    else:
                        # Fallback if can't find delimiter
                        parts.append(s + placeholder)
                else:
                    parts.append(s)

            # Join with newlines and indent
            trimmed_text = parts[0]
            for s in parts[1:]:
                trimmed_text += f"\n{element_indent}{s}"
        else:
            # Single line: insert placeholder in last string before closing delimiter
            last_string = kept_strings[-1]
            if closing_delimiter and last_string.endswith(closing_delimiter):
                kept_strings[-1] = last_string[:-len(closing_delimiter)] + placeholder + closing_delimiter
            else:
                kept_strings[-1] = last_string + placeholder
            trimmed_text = " ".join(kept_strings)

        # Calculate tokens for trimmed text
        trimmed_tokens = self.tokenizer.count_text_cached(trimmed_text)
        saved_tokens = original_tokens - trimmed_tokens

        # Create comment
        comment_name = profile.comment_name or 'literal'
        comment_text = f"{comment_name} (−{saved_tokens} tokens)"

        return TrimResult(
            trimmed_text=trimmed_text,
            original_tokens=original_tokens,
            trimmed_tokens=trimmed_tokens,
            saved_tokens=saved_tokens,
            elements_kept=len(kept_strings),
            elements_removed=len(child_strings) - len(kept_strings),
            comment_text=comment_text,
        )
