"""
Rust let-group initialization processor.

Handles patterns like:
    let mut m = HashMap::new();
    m.insert("key1", "value1");
    m.insert("key2", "value2");
"""

from __future__ import annotations

from typing import List, Optional

from ..optimizations.literals import (
    BlockInitProcessorBase,
    BlockInitProfile,
    TrimResult,
    LiteralProfile,
)
from ..optimizations.literals.utils.indentation import detect_base_indent
from ..tree_sitter_support import TreeSitterDocument, Node


class RustLetGroupProcessor(BlockInitProcessorBase):
    """Processes Rust let-group initialization patterns."""

    def can_handle(self, profile: LiteralProfile, node: Node, doc: TreeSitterDocument) -> bool:
        """
        Check applicability.

        Applicable to BlockInitProfile with let_declaration.
        """
        if not isinstance(profile, BlockInitProfile):
            return False

        return node.type == "let_declaration"

    def process(
        self,
        node: Node,
        doc: TreeSitterDocument,
        source_text: str,
        profile: BlockInitProfile,
        token_budget: int,
    ) -> Optional[TrimResult]:
        """Process Rust let-group initialization."""
        base_indent = detect_base_indent(source_text, node.start_byte)

        return self._process_let_group(profile, node, doc, token_budget, base_indent)

    def _process_let_group(
        self,
        profile: BlockInitProfile,
        node: Node,
        doc: TreeSitterDocument,
        token_budget: int,
        base_indent: str,
    ) -> Optional[TrimResult]:
        """Process a let-declaration group."""
        if not self._is_collection_init(node, doc):
            return None

        var_name = self._extract_var_name(node, doc)
        if not var_name:
            return None

        insert_stmts = self._collect_insert_statements(node, var_name, profile, doc)
        if len(insert_stmts) < profile.min_elements:
            return None

        original_text = self._get_group_text(node, insert_stmts, doc)
        original_tokens = self.tokenizer.count_text_cached(original_text)

        if original_tokens <= token_budget:
            return None

        let_tokens = self.tokenizer.count_text_cached(doc.get_node_text(node))
        statements_budget = token_budget - let_tokens

        if statements_budget <= 0:
            return None

        keep_stmts = []
        remove_stmts = []
        tokens_used = 0

        for stmt in insert_stmts:
            stmt_tokens = self.tokenizer.count_text_cached(doc.get_node_text(stmt))

            is_first = len(keep_stmts) == 0
            if tokens_used + stmt_tokens <= statements_budget or is_first:
                keep_stmts.append(stmt)
                tokens_used += stmt_tokens
            else:
                remove_stmts.append(stmt)

        if not remove_stmts:
            return None

        trimmed_text = self._reconstruct_let_group(
            node, keep_stmts, remove_stmts, profile, doc, base_indent, token_budget
        )

        trimmed_tokens = self.tokenizer.count_text_cached(trimmed_text)
        saved_tokens = original_tokens - trimmed_tokens

        if saved_tokens <= 0:
            return None

        nodes_to_replace = [node] + insert_stmts

        return TrimResult(
            trimmed_text=trimmed_text,
            original_tokens=original_tokens,
            trimmed_tokens=trimmed_tokens,
            saved_tokens=saved_tokens,
            elements_kept=len(keep_stmts) + 1,
            elements_removed=len(remove_stmts),
            comment_text=None,
            comment_position=None,
            nodes_to_replace=nodes_to_replace,
        )

    def _is_collection_init(self, node: Node, doc: TreeSitterDocument) -> bool:
        """Check if let_declaration initializes HashMap::new() or Vec::new()."""
        value_node = node.child_by_field_name("value")
        if not value_node or value_node.type != "call_expression":
            return False

        function = value_node.child_by_field_name("function")
        if not function or function.type != "scoped_identifier":
            return False

        name = function.child_by_field_name("name")
        if name:
            method_name = doc.get_node_text(name)
            return method_name == "new"

        return False

    def _extract_var_name(self, node: Node, doc: TreeSitterDocument) -> Optional[str]:
        """Extract variable name from let_declaration."""
        pattern_node = node.child_by_field_name("pattern")
        if not pattern_node:
            return None

        if pattern_node.type == "identifier":
            return doc.get_node_text(pattern_node)

        if pattern_node.type == "mut_pattern":
            for child in pattern_node.children:
                if child.type == "identifier":
                    return doc.get_node_text(child)

        return None

    def _collect_insert_statements(
        self, let_node: Node, var_name: str, profile: BlockInitProfile, doc: TreeSitterDocument
    ) -> List[Node]:
        """Collect following statements that call methods on var_name."""
        parent = let_node.parent
        if not parent:
            return []

        let_index = None
        for i, child in enumerate(parent.children):
            if child == let_node:
                let_index = i
                break

        if let_index is None:
            return []

        insert_stmts = []
        for i in range(let_index + 1, len(parent.children)):
            child = parent.children[i]

            if child.type in ('{', '}', ';'):
                continue

            if child.type != "expression_statement":
                break

            if self._statement_calls_var(child, var_name, doc):
                insert_stmts.append(child)
            else:
                break

        return insert_stmts

    def _statement_calls_var(self, stmt: Node, var_name: str, doc: TreeSitterDocument) -> bool:
        """Check if statement calls a method on var_name."""
        for child in stmt.children:
            if child.type == "call_expression":
                function = child.child_by_field_name("function")
                if function and function.type == "field_expression":
                    receiver = function.child_by_field_name("value")
                    if receiver:
                        receiver_name = doc.get_node_text(receiver)
                        if receiver_name == var_name:
                            return True
        return False

    def _get_group_text(self, let_node: Node, insert_stmts: List[Node], doc: TreeSitterDocument) -> str:
        """Get combined text for entire group (let + inserts)."""
        if not insert_stmts:
            return doc.get_node_text(let_node)

        parts = [doc.get_node_text(let_node)]
        for stmt in insert_stmts:
            parts.append(doc.get_node_text(stmt))
        return "\n".join(parts)

    def _reconstruct_let_group(
        self,
        let_node: Node,
        keep_inserts: List[Node],
        remove_inserts: List[Node],
        profile: BlockInitProfile,
        doc: TreeSitterDocument,
        base_indent: str,
        token_budget: int,
    ) -> str:
        """Reconstruct let group with trimmed inserts."""
        let_text = doc.get_node_text(let_node)

        separator = "\n" + base_indent

        insert_parts = []
        for insert in keep_inserts:
            insert_text = doc.get_node_text(insert)
            insert_parts.append(insert_text)

        if remove_inserts and profile.placeholder_position.value == "middle":
            removed_count = len(remove_inserts)
            tokens_saved = sum(
                self.tokenizer.count_text_cached(doc.get_node_text(s))
                for s in remove_inserts
            )
            placeholder = f"{self.single_comment} … ({removed_count} more, −{tokens_saved} tokens)"
            insert_parts.append(placeholder)

        if insert_parts:
            inserts_text = separator.join(insert_parts)
            return let_text + separator + inserts_text
        else:
            return let_text
