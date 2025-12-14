"""
Java double-brace initialization processor.

Handles patterns like:
    new HashMap<>() {{
        put("key1", "value1");
        put("key2", "value2");
    }}
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..optimizations.literals import (
    BlockInitProcessorBase,
    BlockInitProfile,
    TrimResult,
    LiteralProfile,
)
from ..optimizations.literals.utils.indentation import detect_base_indent
from ..tree_sitter_support import TreeSitterDocument, Node


class JavaDoubleBraceProcessor(BlockInitProcessorBase):
    """Processes Java double-brace initialization patterns."""

    def can_handle(self, profile: LiteralProfile, node: Node, doc: TreeSitterDocument) -> bool:
        """
        Check applicability.

        Applicable to BlockInitProfile with object_creation_expression or block nodes.
        """
        if not isinstance(profile, BlockInitProfile):
            return False

        return node.type in ("object_creation_expression", "block", "class_body")

    def process(
        self,
        node: Node,
        doc: TreeSitterDocument,
        source_text: str,
        profile: BlockInitProfile,
        token_budget: int,
    ) -> Optional[TrimResult]:
        """Process Java double-brace initialization."""
        base_indent = detect_base_indent(source_text, node.start_byte)

        result = self._process_block(profile, node, doc, token_budget, base_indent)
        if result:
            result.nodes_to_replace = [node]
        return result

    def _process_block(
        self,
        profile: BlockInitProfile,
        node: Node,
        doc: TreeSitterDocument,
        token_budget: int,
        base_indent: str,
    ) -> Optional[TrimResult]:
        """Process a block-based initialization."""
        statements_node = self._find_statements_block(node, profile)
        if not statements_node:
            return None

        statements = self._get_child_statements(statements_node)
        if not statements:
            return None

        matching_stmts = []
        for stmt in statements:
            if profile.statement_pattern and self._matches_pattern(stmt, profile.statement_pattern, doc):
                matching_stmts.append(stmt)

        if len(matching_stmts) < profile.min_elements:
            return None

        keep_stmts, remove_stmts = self._select_statements(matching_stmts, doc, token_budget)

        if not remove_stmts:
            return None

        original_text = doc.get_node_text(node)
        original_tokens = self.tokenizer.count_text_cached(original_text)

        trimmed_text = self._reconstruct_block(
            node, keep_stmts, remove_stmts, profile, doc, base_indent
        )

        trimmed_tokens = self.tokenizer.count_text_cached(trimmed_text)
        saved_tokens = original_tokens - trimmed_tokens

        return TrimResult(
            trimmed_text=trimmed_text,
            original_tokens=original_tokens,
            trimmed_tokens=trimmed_tokens,
            saved_tokens=saved_tokens,
            elements_kept=len(keep_stmts),
            elements_removed=len(remove_stmts),
            comment_text=None,
            comment_position=None,
        )

    def _find_statements_block(
        self, node: Node, profile: BlockInitProfile
    ) -> Optional[Node]:
        """Find the block containing statements to process."""
        if not profile.block_selector:
            if node.type in ("block", "class_body", "declaration_list"):
                return node
            return None

        current = node
        for segment in profile.block_selector.split("/"):
            found = False
            for child in current.children:
                if child.type == segment:
                    current = child
                    found = True
                    break
            if not found:
                return None

        return current

    def _get_child_statements(self, block_node: Node) -> List[Node]:
        """Get child statements from block, filtering out structural nodes."""
        statements = []
        for child in block_node.children:
            if child.type in ("{", "}", ";"):
                continue
            if "statement" in child.type or "declaration" in child.type or child.type == "identifier":
                statements.append(child)

        return statements

    def _select_statements(
        self,
        statements: List[Node],
        doc: TreeSitterDocument,
        token_budget: int,
    ) -> Tuple[List[Node], List[Node]]:
        """Select which statements to keep and remove using budget-aware strategy."""
        keep = []
        remove = []

        tokens_used = 0
        for stmt in statements:
            stmt_tokens = self.tokenizer.count_text_cached(doc.get_node_text(stmt))

            is_first = len(keep) == 0
            if tokens_used + stmt_tokens <= token_budget or is_first:
                keep.append(stmt)
                tokens_used += stmt_tokens
            else:
                remove.append(stmt)

        return keep, remove

    def _reconstruct_block(
        self,
        original_node: Node,
        keep_stmts: List[Node],
        remove_stmts: List[Node],
        profile: BlockInitProfile,
        doc: TreeSitterDocument,
        base_indent: str,
    ) -> str:
        """Reconstruct block with kept statements and placeholder."""
        original_text = doc.get_node_text(original_node)

        statements_block = self._find_statements_block(original_node, profile)
        all_statements = self._get_child_statements(statements_block)

        if keep_stmts:
            first_kept = keep_stmts[0]
            opening_end = first_kept.start_byte - original_node.start_byte
            opening = original_text[:opening_end]
        else:
            opening = original_text

        if all_statements:
            last_stmt = all_statements[-1]
            closing_start = last_stmt.end_byte - original_node.start_byte
            closing = original_text[closing_start:]
        else:
            closing = ""

        if len(all_statements) >= 2:
            stmt0_end = all_statements[0].end_byte - original_node.start_byte
            stmt1_start = all_statements[1].start_byte - original_node.start_byte
            separator = original_text[stmt0_end:stmt1_start]
        else:
            separator = "\n" + base_indent

        stmt_parts = []
        for i, stmt in enumerate(keep_stmts):
            stmt_text = doc.get_node_text(stmt)

            if i == 0:
                stmt_parts.append(stmt_text)
            else:
                stmt_parts.append(separator + stmt_text)

        if remove_stmts and profile.placeholder_position.value == "middle" and keep_stmts:
            removed_count = len(remove_stmts)
            tokens_saved = sum(
                self.tokenizer.count_text_cached(doc.get_node_text(s))
                for s in remove_stmts
            )

            placeholder_comment = f"{separator}{self.single_comment} … ({removed_count} more, −{tokens_saved} tokens)"
            stmt_parts.append(placeholder_comment)

        statements_text = "".join(stmt_parts)

        return opening + statements_text + closing
