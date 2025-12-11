"""
Block initialization processor for BLOCK_INIT category.

Handles imperative initialization blocks like:
- Java double-brace initialization
- Rust HashMap initialization blocks
- Other statement-based data structure initialization
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Callable

from lg.adapters.tree_sitter_support import Node, TreeSitterDocument
from ..patterns import TrimResult, BlockInitProfile, LiteralProfile

# Type alias for literal processing callback
ProcessLiteralCallback = Callable[
    [str, LiteralProfile, int, int, int, str, str],  # text, profile, start_byte, end_byte, token_budget, base_indent, element_indent
    Optional[TrimResult]
]


class BlockInitProcessor:
    """
    Processes BLOCK_INIT patterns - imperative initialization blocks.

    These are sequences of statements that initialize data structures,
    where we want to keep structure (first/last statements) but trim
    repetitive middle parts.

    Supports DFS (recursive) optimization of nested literals within statements.
    """

    def __init__(
        self,
        tokenizer,
        all_profiles: List[LiteralProfile],
        process_literal_callback: ProcessLiteralCallback,
        comment_style: tuple[str, tuple[str, str], tuple[str, str]],
    ):
        """
        Initialize processor.

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

    def process(
        self,
        profile: BlockInitProfile,
        node: Node,
        doc: TreeSitterDocument,
        token_budget: int,
        base_indent: str,
    ) -> Optional[Tuple[TrimResult, List[Node]]]:
        """
        Process a BLOCK_INIT profile.

        Args:
            profile: BlockInitProfile with BLOCK_INIT configuration
            node: Tree-sitter node to process (will be expanded to group for let_declaration)
            doc: Tree-sitter document
            token_budget: Token budget for this block
            base_indent: Base indentation

        Returns:
            (TrimResult, nodes_used) tuple if trimming applied, None otherwise
            nodes_used is the list of nodes to replace:
            - For Java: [node] (single node)
            - For Rust: [let_node] + insert_stmts (expanded group)
        """
        # Route based on node type
        if node.type == "let_declaration":
            # Rust-style: let mut var = HashMap::new(); var.insert(...);
            # Expands to group internally
            return self._process_let_group(profile, node, doc, token_budget, base_indent)
        else:
            # Java-style: whole block with multiple statements
            result = self._process_block(profile, node, doc, token_budget, base_indent)
            return (result, [node]) if result else None

    def _process_block(
        self,
        profile: BlockInitProfile,
        node: Node,
        doc: TreeSitterDocument,
        token_budget: int,
        base_indent: str,
    ) -> Optional[TrimResult]:
        """
        Process a block-based BLOCK_INIT profile (Java double-brace).

        Args:
            profile: BlockInitProfile with BLOCK_INIT configuration
            node: Tree-sitter node (block or object_creation_expression)
            doc: Tree-sitter document
            token_budget: Token budget for this block
            base_indent: Base indentation

        Returns:
            TrimResult if trimming applied, None otherwise
        """
        # 1. Find statements block
        statements_node = self._find_statements_block(node, profile, doc)
        if not statements_node:
            return None

        # 2. Collect statements matching the profile
        statements = self._get_child_statements(statements_node)
        if not statements:
            return None

        # Filter statements by profile (e.g., "*/method_invocation" for Java double-brace)
        matching_stmts = []
        for stmt in statements:
            if profile.statement_pattern and self._matches_pattern(stmt, profile.statement_pattern, doc):
                matching_stmts.append(stmt)

        # 3. Check if worth trimming
        if len(matching_stmts) < profile.min_elements:
            return None  # Too few statements

        # 4. Calculate what to keep/remove using budget-aware selection
        keep_stmts, remove_stmts = self._select_statements(
            matching_stmts, profile, doc, token_budget
        )

        if not remove_stmts:
            return None  # Nothing to remove

        # 5. Calculate tokens
        original_text = doc.get_node_text(node)
        original_tokens = self.tokenizer.count_text_cached(original_text)

        # 6. Build trimmed text with DFS optimization
        trimmed_text = self._reconstruct_block(
            node, keep_stmts, remove_stmts, profile, doc, base_indent, token_budget
        )

        trimmed_tokens = self.tokenizer.count_text_cached(trimmed_text)
        saved_tokens = original_tokens - trimmed_tokens

        # No external comment needed - placeholder is already embedded in trimmed_text
        return TrimResult(
            trimmed_text=trimmed_text,
            original_tokens=original_tokens,
            trimmed_tokens=trimmed_tokens,
            saved_tokens=saved_tokens,
            elements_kept=len(keep_stmts),
            elements_removed=len(remove_stmts),
            comment_text=None,  # Placeholder already in trimmed_text
            comment_position=None,
        )

    def _process_let_group(
        self,
        profile: BlockInitProfile,
        node: Node,
        doc: TreeSitterDocument,
        token_budget: int,
        base_indent: str,
    ) -> Optional[Tuple[TrimResult, List[Node]]]:
        """
        Process a let-declaration group (Rust HashMap::new() + inserts).

        Args:
            profile: BlockInitProfile with BLOCK_INIT configuration
            node: let_declaration node
            doc: Tree-sitter document
            token_budget: Token budget
            base_indent: Base indentation

        Returns:
            TrimResult if trimming applied, None otherwise
        """
        # 1. Check if this is HashMap::new() or similar collection init
        if not self._is_collection_init(node, doc):
            return None

        # 2. Extract variable name from let declaration
        var_name = self._extract_var_name(node, doc)
        if not var_name:
            return None

        # 3. Collect following statements for this variable
        insert_stmts = self._collect_insert_statements(node, var_name, profile, doc)
        if len(insert_stmts) < profile.min_elements:
            return None  # Too few statements

        # 4. Calculate original tokens for the group (let + all inserts)
        original_text = self._get_group_text(node, insert_stmts, doc)
        original_tokens = self.tokenizer.count_text_cached(original_text)

        # Skip if entire group fits in budget
        if original_tokens <= token_budget:
            return None

        # Budget-aware selection: keep statements that fit in budget
        # Calculate budget for statements (excluding let declaration overhead)
        let_tokens = self.tokenizer.count_text_cached(doc.get_node_text(node))
        statements_budget = token_budget - let_tokens

        if statements_budget <= 0:
            # Budget too small even for let declaration
            return None

        # Select statements that fit in budget
        keep_stmts = []
        remove_stmts = []
        tokens_used = 0

        for stmt in insert_stmts:
            stmt_tokens = self.tokenizer.count_text_cached(doc.get_node_text(stmt))

            # Keep if within budget OR if this is the first statement (minimum 1)
            is_first = len(keep_stmts) == 0
            if tokens_used + stmt_tokens <= statements_budget or is_first:
                keep_stmts.append(stmt)
                tokens_used += stmt_tokens
            else:
                remove_stmts.append(stmt)

        # If no statements were removed, no optimization needed
        if not remove_stmts:
            return None

        # 5. Build trimmed text with DFS optimization
        trimmed_text = self._reconstruct_let_group(
            node, keep_stmts, remove_stmts, profile, doc, base_indent, token_budget
        )

        trimmed_tokens = self.tokenizer.count_text_cached(trimmed_text)
        saved_tokens = original_tokens - trimmed_tokens

        if saved_tokens <= 0:
            return None  # Not economical

        # No external comment needed - placeholder is already embedded in trimmed_text
        trim_result = TrimResult(
            trimmed_text=trimmed_text,
            original_tokens=original_tokens,
            trimmed_tokens=trimmed_tokens,
            saved_tokens=saved_tokens,
            elements_kept=len(keep_stmts) + 1,  # +1 for let statement
            elements_removed=len(remove_stmts),
            comment_text=None,  # Placeholder already in text
            comment_position=None,
        )

        # Return result + all nodes that should be replaced (let + all inserts)
        nodes_to_replace = [node] + insert_stmts
        return (trim_result, nodes_to_replace)

    def _find_statements_block(
        self, node: Node, profile: BlockInitProfile, doc: TreeSitterDocument
    ) -> Optional[Node]:
        """
        Find the block containing statements to process.

        Args:
            node: Root node
            profile: Profile with block_selector
            doc: Document

        Returns:
            Statements block node or None
        """
        if not profile.block_selector:
            # No selector - use node itself if it's a block-like node
            if node.type in ("block", "class_body", "declaration_list"):
                return node
            return None

        # Navigate path like "class_body/block"
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
        """
        Get child statements from block, filtering out structural nodes.

        Args:
            block_node: Block node

        Returns:
            List of statement nodes
        """
        statements = []
        for child in block_node.children:
            # Skip structural tokens like braces
            if child.type in ("{", "}", ";"):
                continue
            # Include actual statements
            if "statement" in child.type or "declaration" in child.type or child.type == "identifier":
                statements.append(child)

        return statements

    def _matches_pattern(self, node: Node, pattern: str, doc: TreeSitterDocument) -> bool:
        """
        Check if node matches a pattern.

        Supports simple patterns like:
        - "identifier" - matches node type exactly
        - "*/call_expression" - matches call_expression anywhere in subtree
        - "call_expression[method='insert']" - matches with field value check

        Args:
            node: Node to check
            pattern: Pattern string
            doc: Document

        Returns:
            True if matches
        """
        # Handle wildcard prefix
        if pattern.startswith("*/"):
            target_pattern = pattern[2:]
            # Check node and all descendants
            return self._matches_in_subtree(node, target_pattern, doc)

        # Handle field value check like "call_expression[method='insert']"
        if "[" in pattern:
            node_type, rest = pattern.split("[", 1)
            field_check = rest.rstrip("]")

            if node.type != node_type:
                return False

            # Parse field check like "method='insert'"
            if "=" in field_check:
                field_name, expected_value = field_check.split("=", 1)
                expected_value = expected_value.strip("'\"")

                # Get field node
                field_node = node.child_by_field_name(field_name)
                if not field_node:
                    return False

                # Check if field node text matches
                actual_value = doc.get_node_text(field_node)
                return actual_value == expected_value

            return False

        # Simple type match
        return node.type == pattern

    def _matches_in_subtree(self, node: Node, pattern: str, doc: TreeSitterDocument) -> bool:
        """Check if pattern matches anywhere in subtree."""
        if self._matches_pattern(node, pattern, doc):
            return True

        for child in node.children:
            if self._matches_in_subtree(child, pattern, doc):
                return True

        return False

    def _select_statements(
        self,
        statements: List[Node],
        profile: BlockInitProfile,
        doc: TreeSitterDocument,
        token_budget: int,
    ) -> Tuple[List[Node], List[Node]]:
        """
        Select which statements to keep and remove using budget-aware strategy.

        Args:
            statements: Statements to trim (e.g., put/add calls for Java double-brace)
            profile: Profile configuration (unused currently, kept for consistency)
            doc: Document for getting node text
            token_budget: Token budget for entire block

        Returns:
            Tuple of (keep_statements, remove_statements)
        """
        keep = []
        remove = []

        # Keep statements that fit in budget (minimum 1)
        tokens_used = 0
        for stmt in statements:
            stmt_tokens = self.tokenizer.count_text_cached(doc.get_node_text(stmt))

            # Keep if within budget OR if this is the first statement (minimum 1)
            is_first = len(keep) == 0
            if tokens_used + stmt_tokens <= token_budget or is_first:
                keep.append(stmt)
                tokens_used += stmt_tokens
            else:
                remove.append(stmt)

        return keep, remove

    def _optimize_statement_recursive(
        self,
        stmt_node: Node,
        doc: TreeSitterDocument,
        token_budget: int,
    ) -> str:
        """
        Recursively optimize nested literals within a statement (DFS).

        Args:
            stmt_node: Statement node to optimize
            doc: Document
            token_budget: Token budget for nested optimization

        Returns:
            Optimized statement text with nested literals trimmed
        """

        # Get statement text
        stmt_text = doc.get_node_text(stmt_node)

        # Query for nested literals within this statement
        # Note: We need to query within stmt_node's subtree
        nested_literals = []

        # Recursively find nested collection/block literals
        # We only want to optimize nested collections, not parts of the statement itself
        def find_literals(node: Node, is_direct_child: bool = False):
            # Check if this node matches any profile in descriptor
            found_literal = False
            # Try to match against all profile types
            for profile in self.all_profiles:
                # Try to match this node using the profile's query
                try:
                    # Query to see if this specific node matches
                    nodes = doc.query_nodes(profile.query, "lit")
                    if node in nodes:
                        # Skip the statement node itself
                        if node.start_byte == stmt_node.start_byte and node.end_byte == stmt_node.end_byte:
                            break

                        # Skip direct children of statement (these are part of the statement structure)
                        # For example: put(...) method_invocation is direct child, but HashMap inside argument is not
                        if is_direct_child:
                            break

                        # Only collect collections/blocks
                        # Categories to optimize: SEQUENCE, MAPPING, FACTORY_CALL, BLOCK_INIT
                        # Get category from profile's comment_name if available, or infer from type
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
                    # Query failed, skip this profile
                    continue

            # Don't recurse into found literals (they will be processed separately)
            if not found_literal:
                # Recurse into children
                for child in node.children:
                    find_literals(child, is_direct_child=False)

        # Start with direct children marked as such
        for child in stmt_node.children:
            find_literals(child, is_direct_child=True)

        # If no nested literals, return original
        if not nested_literals:
            return stmt_text

        # Statement start position for relative offset calculation
        stmt_start = stmt_node.start_byte

        # Build list of replacements (start, end, new_text)
        replacements = []

        for nested_node in nested_literals:
            # Get nested node text
            nested_text = doc.get_node_text(nested_node)
            nested_tokens = self.tokenizer.count_text_cached(nested_text)

            # Skip if already within budget
            if nested_tokens <= token_budget:
                continue

            # Try to optimize this nested literal
            # Determine profile and process
            nested_profile = None
            # Use all_profiles
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

            # Optimize nested literal based on profile type
            trim_result = None

            if isinstance(nested_profile, BlockInitProfile):
                # Nested BLOCK_INIT - call recursively with profile
                result = self.process(
                    nested_profile,
                    nested_node,
                    doc,
                    token_budget,
                    base_indent="",
                )
                if result:
                    trim_result, _ = result
            else:
                # Regular literal - use callback
                trim_result = self.process_literal_callback(
                    nested_text,
                    nested_profile,
                    nested_node.start_byte,
                    nested_node.end_byte,
                    token_budget,
                    "",  # base_indent
                    "",  # element_indent
                )

            # Collect replacement if optimization succeeded
            if trim_result and trim_result.saved_tokens > 0:
                # Calculate position relative to statement start
                rel_start = nested_node.start_byte - stmt_start
                rel_end = nested_node.end_byte - stmt_start
                replacements.append((rel_start, rel_end, trim_result.trimmed_text))

        # Apply replacements from end to start (to preserve offsets)
        replacements.sort(key=lambda r: r[0], reverse=True)
        optimized_text = stmt_text

        for rel_start, rel_end, new_text in replacements:
            optimized_text = (
                optimized_text[:rel_start]
                + new_text
                + optimized_text[rel_end:]
            )

        return optimized_text

    def _reconstruct_block(
        self,
        original_node: Node,
        keep_stmts: List[Node],
        remove_stmts: List[Node],
        profile: BlockInitProfile,
        doc: TreeSitterDocument,
        base_indent: str,
        token_budget: int,
    ) -> str:
        """
        Reconstruct block with kept statements and placeholder.

        Args:
            original_node: Original block node
            keep_stmts: Statements to keep
            remove_stmts: Statements removed (for count)
            profile: Profile with placeholder config
            doc: Document
            base_indent: Base indentation

        Returns:
            Reconstructed text
        """
        # Get original text for structure preservation
        original_text = doc.get_node_text(original_node)

        # Find statements block (compute once, reuse below)
        statements_block = self._find_statements_block(original_node, profile, doc)
        all_statements = self._get_child_statements(statements_block)

        # Extract opening (everything before first kept statement)
        if keep_stmts:
            first_kept = keep_stmts[0]
            opening_end = first_kept.start_byte - original_node.start_byte
            opening = original_text[:opening_end]
        else:
            opening = original_text

        # Extract closing (everything after last statement in block)
        # Must use ALL statements, not just kept ones, to avoid including removed statements
        if all_statements:
            last_stmt = all_statements[-1]
            closing_start = last_stmt.end_byte - original_node.start_byte
            closing = original_text[closing_start:]
        else:
            closing = ""

        # Build statement texts with preserved whitespace
        # Extract separator pattern from first two statements in statements block

        # Get separator between first two statements
        if len(all_statements) >= 2:
            stmt0_end = all_statements[0].end_byte - original_node.start_byte
            stmt1_start = all_statements[1].start_byte - original_node.start_byte
            separator = original_text[stmt0_end:stmt1_start]
        else:
            separator = "\n" + base_indent

        stmt_parts = []
        for i, stmt in enumerate(keep_stmts):
            # Get statement text with recursive optimization (DFS)
            stmt_text = self._optimize_statement_recursive(stmt, doc, token_budget)

            # Get whitespace before statement (from previous statement or opening)
            if i == 0:
                # First statement - whitespace already in opening
                stmt_parts.append(stmt_text)
            else:
                # Use extracted separator pattern
                stmt_parts.append(separator + stmt_text)

        # Insert placeholder comment after kept statements if needed
        if remove_stmts and profile.placeholder_position.value == "middle" and keep_stmts:
            # Format placeholder comment
            removed_count = len(remove_stmts)
            tokens_saved = sum(
                self.tokenizer.count_text_cached(doc.get_node_text(s))
                for s in remove_stmts
            )

            # Use the same separator as between statements (already extracted above)
            placeholder_comment = f"{separator}{self.single_comment} … ({removed_count} more, −{tokens_saved} tokens)"
            # Append placeholder AFTER all kept statements
            stmt_parts.append(placeholder_comment)

        # Combine
        statements_text = "".join(stmt_parts)

        return opening + statements_text + closing

    # ========== Helper methods for let_declaration groups (Rust) ==========

    def _is_collection_init(self, node: Node, doc: TreeSitterDocument) -> bool:
        """Check if let_declaration initializes HashMap::new() or Vec::new()."""
        value_node = node.child_by_field_name("value")
        if not value_node or value_node.type != "call_expression":
            return False

        function = value_node.child_by_field_name("function")
        if not function or function.type != "scoped_identifier":
            return False

        # Check if method name is "new"
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

        # Handle mut_pattern
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

        # Find let_node position
        let_index = None
        for i, child in enumerate(parent.children):
            if child == let_node:
                let_index = i
                break

        if let_index is None:
            return []

        # Collect following statements
        insert_stmts = []
        for i in range(let_index + 1, len(parent.children)):
            child = parent.children[i]

            if child.type in ('{', '}', ';'):
                continue

            if child.type != "expression_statement":
                break  # Different statement type

            # Check if it's a call on our variable
            if self._statement_calls_var(child, var_name, doc):
                insert_stmts.append(child)
            else:
                break  # Statement doesn't match

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

        # Create a temporary node spanning the entire group
        # Just concatenate text of all parts
        parts = [doc.get_node_text(let_node)]
        for stmt in insert_stmts:
            parts.append(doc.get_node_text(stmt))
        return "\n".join(parts)  # Approximate - whitespace doesn't matter for token count

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
        """Reconstruct let group with trimmed inserts and DFS optimization."""
        # Optimize let declaration itself (may contain nested literals)
        let_text = self._optimize_statement_recursive(let_node, doc, token_budget)

        # Get separator between statements (approximate as newline)
        separator = "\n" + base_indent

        # Build insert parts with DFS optimization
        insert_parts = []
        for insert in keep_inserts:
            insert_text = self._optimize_statement_recursive(insert, doc, token_budget)
            insert_parts.append(insert_text)

        # Add placeholder if needed
        if remove_inserts and profile.placeholder_position.value == "middle":
            removed_count = len(remove_inserts)
            tokens_saved = sum(
                self.tokenizer.count_text_cached(doc.get_node_text(s))
                for s in remove_inserts
            )
            placeholder = f"{self.single_comment} … ({removed_count} more, −{tokens_saved} tokens)"
            insert_parts.append(placeholder)

        # Combine
        if insert_parts:
            inserts_text = separator.join(insert_parts)
            return let_text + separator + inserts_text
        else:
            return let_text
