"""
Base class for imperative block initialization processors.

Provides common functionality for different initialization patterns:
- Java double-brace initialization
- Rust HashMap let-group initialization
"""

from __future__ import annotations

from abc import abstractmethod
from typing import List, Optional, Callable

from lg.adapters.tree_sitter_support import Node, TreeSitterDocument
from .base import LiteralProcessor
from ..patterns import TrimResult, BlockInitProfile, LiteralProfile

# Type alias for literal processing callback
ProcessLiteralCallback = Callable[
    [object, object, str, LiteralProfile, int],
    Optional[TrimResult]
]


class BlockInitProcessorBase(LiteralProcessor):
    """
    Base class for block initialization processors.

    Subclasses implement specific patterns (Java double-brace, Rust let-group).
    """

    def __init__(
        self,
        tokenizer,
        all_profiles: List[LiteralProfile],
        process_literal_callback: ProcessLiteralCallback,
        comment_style: tuple[str, tuple[str, str]],
    ):
        """
        Initialize base processor.

        Args:
            tokenizer: Token counting service
            all_profiles: List of all literal profiles for nested literal detection
            process_literal_callback: Callback for processing nested literals
            comment_style: Comment syntax (single_line, (block_open, block_close))
        """
        self.tokenizer = tokenizer
        self.all_profiles = all_profiles
        self.process_literal_callback = process_literal_callback
        self.single_comment = comment_style[0]
        self.block_comment = comment_style[1]
        self.source_text = None
        self.doc = None

    @abstractmethod
    def can_handle(self, profile: LiteralProfile, node, doc) -> bool:
        """Check if this component can handle the pattern."""
        pass

    @abstractmethod
    def process(
        self,
        node,
        doc,
        source_text: str,
        profile: BlockInitProfile,
        token_budget: int,
    ) -> Optional[TrimResult]:
        """Process the block initialization pattern."""
        pass

    def _optimize_statement_recursive(
        self,
        stmt_node: Node,
        doc: TreeSitterDocument,
        token_budget: int,
    ) -> str:
        """
        Recursively optimize nested literals within a statement (DFS).

        Common implementation used by all subclasses.
        """
        stmt_text = doc.get_node_text(stmt_node)
        nested_literals = []

        def find_literals(node: Node, is_direct_child: bool = False):
            found_literal = False
            for profile in self.all_profiles:
                try:
                    nodes = doc.query_nodes(profile.query, "lit")
                    if node in nodes:
                        if node.start_byte == stmt_node.start_byte and node.end_byte == stmt_node.end_byte:
                            break

                        if is_direct_child:
                            break

                        profile_type = type(profile).__name__
                        category_map = {
                            'StringProfile': 'string',
                            'SequenceProfile': 'sequence',
                            'MappingProfile': 'mapping',
                            'FactoryProfile': 'factory',
                            'BlockInitProfile': 'block',
                        }
                        category = category_map.get(profile_type, '')
                        if category in ["sequence", "mapping", "factory", "block"]:
                            nested_literals.append(node)
                            found_literal = True
                        break
                except:
                    continue

            if not found_literal:
                for child in node.children:
                    find_literals(child, is_direct_child=False)

        for child in stmt_node.children:
            find_literals(child, is_direct_child=True)

        if not nested_literals:
            return stmt_text

        stmt_start = stmt_node.start_byte
        replacements = []

        for nested_node in nested_literals:
            nested_text = doc.get_node_text(nested_node)
            nested_tokens = self.tokenizer.count_text_cached(nested_text)

            if nested_tokens <= token_budget:
                continue

            nested_profile = None
            for profile in self.all_profiles:
                try:
                    nodes = doc.query_nodes(profile.query, "lit")
                    if nested_node in nodes:
                        nested_profile = profile
                        break
                except:
                    continue

            if not nested_profile:
                continue

            if isinstance(nested_profile, BlockInitProfile):
                trim_result = self.process(
                    nested_node,
                    doc,
                    self.source_text,
                    nested_profile,
                    token_budget,
                )
            else:
                trim_result = self.process_literal_callback(
                    nested_node,
                    self.doc,
                    self.source_text,
                    nested_profile,
                    token_budget,
                )

            if trim_result and trim_result.saved_tokens > 0:
                rel_start = nested_node.start_byte - stmt_start
                rel_end = nested_node.end_byte - stmt_start
                replacements.append((rel_start, rel_end, trim_result.trimmed_text))

        replacements.sort(key=lambda r: r[0], reverse=True)
        optimized_text = stmt_text

        for rel_start, rel_end, new_text in replacements:
            optimized_text = (
                optimized_text[:rel_start]
                + new_text
                + optimized_text[rel_end:]
            )

        return optimized_text

    def _matches_pattern(self, node: Node, pattern: str, doc: TreeSitterDocument) -> bool:
        """Check if node matches a pattern."""
        if pattern.startswith("*/"):
            target_pattern = pattern[2:]
            return self._matches_in_subtree(node, target_pattern, doc)

        if "[" in pattern:
            node_type, rest = pattern.split("[", 1)
            field_check = rest.rstrip("]")

            if node.type != node_type:
                return False

            if "=" in field_check:
                field_name, expected_value = field_check.split("=", 1)
                expected_value = expected_value.strip("'\"")

                field_node = node.child_by_field_name(field_name)
                if not field_node:
                    return False

                actual_value = doc.get_node_text(field_node)
                return actual_value == expected_value

            return False

        return node.type == pattern

    def _matches_in_subtree(self, node: Node, pattern: str, doc: TreeSitterDocument) -> bool:
        """Check if pattern matches anywhere in subtree."""
        if self._matches_pattern(node, pattern, doc):
            return True

        for child in node.children:
            if self._matches_in_subtree(child, pattern, doc):
                return True

        return False
