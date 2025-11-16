"""
Filtering engine for filesystem paths.

Implements a tree-based filtering system with support for:
- Allow/block modes (default-deny/default-allow)
- Hierarchical rules with overrides
- Path-based syntax for compact rule descriptions
- Early directory pruning
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Dict, List, Optional

import pathspec

from .model import FilterNode


# ============================================================================
# Helper structures
# ============================================================================

@dataclass(frozen=True)
class PathMatch:
    """Result of checking a path against filtering rules."""
    matched: bool
    reason: str  # For debugging: why this decision was made


@dataclass(frozen=True)
class CompiledPatterns:
    """Compiled patterns for fast checking."""
    allow_spec: Optional[pathspec.PathSpec]
    block_spec: Optional[pathspec.PathSpec]
    allow_raw: List[str]  # Raw patterns for heuristics
    block_raw: List[str]

    @classmethod
    def compile(cls, allow: List[str], block: List[str]) -> CompiledPatterns:
        """
        Compiles pattern lists into PathSpec objects.

        All patterns are converted to lowercase for case-insensitive matching.
        """
        allow_lower = [pat.lower() for pat in allow]
        block_lower = [pat.lower() for pat in block]

        return cls(
            allow_spec=pathspec.PathSpec.from_lines("gitwildmatch", allow_lower) if allow_lower else None,
            block_spec=pathspec.PathSpec.from_lines("gitwildmatch", block_lower) if block_lower else None,
            allow_raw=allow_lower,
            block_raw=block_lower
        )


# ============================================================================
# Compiled filter node
# ============================================================================

class CompiledFilterNode:
    """
    Compiled filter node with ready-to-use PathSpec objects.

    Represents a filter tree node after expanding path-based keys
    and compiling patterns for efficient matching.
    """

    __slots__ = ("mode", "patterns", "children")

    def __init__(self, mode: str, patterns: CompiledPatterns, children: Dict[str, CompiledFilterNode]):
        self.mode = mode
        self.patterns = patterns
        self.children = children

    @classmethod
    def from_filter_node(cls, node: FilterNode) -> CompiledFilterNode:
        """
        Compiles a FilterNode into an efficient representation.

        Expands path-based keys into a full hierarchy and compiles
        all patterns into PathSpec objects.
        """
        # First expand path-based keys
        expanded_node = PathBasedExpander.expand(node)

        # Compile patterns
        patterns = CompiledPatterns.compile(
            expanded_node.allow,
            expanded_node.block
        )

        # Recursively compile child nodes
        children = {
            name.lower(): cls.from_filter_node(child)
            for name, child in expanded_node.children.items()
        }

        return cls(expanded_node.mode, patterns, children)

    def check_block(self, subpath: str) -> bool:
        """Checks if a path is blocked."""
        if self.patterns.block_spec:
            return self.patterns.block_spec.match_file(subpath)
        return False

    def check_allow(self, subpath: str) -> bool:
        """Checks if a path is explicitly allowed."""
        if self.patterns.allow_spec:
            return self.patterns.allow_spec.match_file(subpath)
        return False

    def get_child(self, name: str) -> Optional[CompiledFilterNode]:
        """Gets a child node by name (case-insensitive)."""
        return self.children.get(name.lower())


# ============================================================================
# Path-based hierarchy expansion
# ============================================================================

class PathBasedExpander:
    """
    Expands path-based keys into a full hierarchy of filter nodes.

    Transforms compact syntax like:
        children:
          "main/kotlin": {...}

    Into a full hierarchy:
        children:
          main:
            mode: allow
            allow: ["/kotlin/"]
            children:
              kotlin: {...}
    """

    @staticmethod
    def expand(node: FilterNode) -> FilterNode:
        """
        Expands path-based keys in a node and its children.

        Args:
            node: Source node for expansion

        Returns:
            Node with expanded children

        Raises:
            RuntimeError: If conflicts between path-based and explicit nodes are detected
        """
        if not node.children:
            return node

        # Split keys into simple and path-based
        simple_children: Dict[str, FilterNode] = {}
        path_children: Dict[str, FilterNode] = {}

        for key, child in node.children.items():
            normalized = key.strip("/").lower()
            if "/" in normalized:
                path_children[normalized] = child
            else:
                simple_children[normalized] = child

        # If there are no path-based keys, just recursively process children
        if not path_children:
            expanded_children = {
                name: PathBasedExpander.expand(child)
                for name, child in simple_children.items()
            }
            return FilterNode(
                mode=node.mode,
                allow=node.allow,
                block=node.block,
                children=expanded_children,
                conditional_filters=node.conditional_filters
            )

        # Validate for conflicts
        PathBasedExpander._validate_no_conflicts(simple_children, path_children)

        # Build expanded hierarchy
        expanded_children = dict(simple_children)

        for path, target_node in sorted(path_children.items()):
            PathBasedExpander._insert_path(expanded_children, path, target_node)

        # Recursively process all children
        final_children = {
            name: PathBasedExpander.expand(child)
            for name, child in expanded_children.items()
        }

        return FilterNode(
            mode=node.mode,
            allow=node.allow,
            block=node.block,
            children=final_children,
            conditional_filters=node.conditional_filters
        )

    @staticmethod
    def _validate_no_conflicts(
        simple_children: Dict[str, FilterNode],
        path_children: Dict[str, FilterNode]
    ) -> None:
        """
        Validates the absence of conflicts between simple and path-based keys.

        A conflict occurs if a path-based key intersects with an explicitly
        defined hierarchy in simple children or other path-based keys.

        Extending a path-based key with another path-based key is allowed,
        as long as there are no conflicting explicit child definitions.
        """
        for path_key in path_children.keys():
            parts = path_key.split("/")

            # Check each path prefix
            for i in range(1, len(parts)):
                prefix = "/".join(parts[:i])
                suffix = "/".join(parts[i:])

                # Conflict with simple key
                if prefix in simple_children:
                    if PathBasedExpander._has_child_prefix(simple_children[prefix], suffix):
                        raise RuntimeError(
                            f"Filter path conflict: '{path_key}' conflicts with "
                            f"explicit definition under '{prefix}'"
                        )

                # Conflict with another path-based key
                if prefix in path_children:
                    prefix_node = path_children[prefix]
                    # If the prefix node has children, check for conflict with suffix
                    # Example: "src/main" with child "resources", and "src/main/kotlin/..." - OK
                    #          "src/main" with child "kotlin", and "src/main/kotlin/..." - CONFLICT
                    if PathBasedExpander._has_child_prefix(prefix_node, suffix):
                        raise RuntimeError(
                            f"Filter path conflict: '{path_key}' conflicts with "
                            f"explicit definition under '{prefix}'"
                        )

    @staticmethod
    def _has_child_prefix(node: FilterNode, path: str) -> bool:
        """Checks if at least a prefix of the path exists in the node's children."""
        if not path:
            return False

        first_segment = path.split("/")[0]
        return first_segment in node.children

    @staticmethod
    def _extract_inherited_rules(parent_node: Optional[FilterNode], child_name: str) -> List[str]:
        """
        Extracts rules from a parent node that apply to a child node.

        If the parent node has allow-rules like "/child_name/subpath",
        extract "/subpath" for inheritance by the child node.

        Args:
            parent_node: Parent node (or None)
            child_name: Name of the child node

        Returns:
            List of inherited rules (paths relative to the child node)
        """
        if not parent_node or not parent_node.allow:
            return []

        inherited = []
        prefix = f"/{child_name}/"

        for rule in parent_node.allow:
            if rule.startswith(prefix):
                # Remove prefix and add to inherited rules
                inherited_rule = rule[len(prefix):]
                # Normalize: add "/" at the beginning if missing
                if inherited_rule and not inherited_rule.startswith("/"):
                    inherited_rule = "/" + inherited_rule
                if inherited_rule:  # Skip empty rules
                    inherited.append(inherited_rule)

        return inherited

    @staticmethod
    def _insert_path(
        children_dict: Dict[str, FilterNode],
        path: str,
        target_node: FilterNode
    ) -> None:
        """
        Inserts a path-based node into the hierarchy, creating intermediate nodes.

        Intermediate nodes are created with mode="allow" and allow=["/{next_segment}/"] +
        inherited rules from the parent node (if any).

        Rule inheritance: if the parent node has allow=["/services/generation/..."],
        and we create an intermediate node "services", it will get allow=["/ai/", "/generation/..."].
        """
        parts = path.split("/")

        # Iterate up to the second-to-last segment
        current_dict = children_dict
        parent_node: Optional[FilterNode] = None

        for idx, part in enumerate(parts[:-1]):
            next_segment = parts[idx + 1]

            if part not in current_dict:
                # Extract inherited rules from parent
                inherited_rules = PathBasedExpander._extract_inherited_rules(parent_node, part)

                # Create intermediate node with inherited rules
                current_dict[part] = FilterNode(
                    mode="allow",
                    allow=[f"/{next_segment}/"] + inherited_rules,
                    block=[],
                    children={},
                    conditional_filters=[]
                )
            else:
                # Node exists - add new segment to allow list
                existing = current_dict[part]
                new_pattern = f"/{next_segment}/"
                if new_pattern not in existing.allow:
                    existing.allow.append(new_pattern)

            # Remember current node as parent for next iteration
            parent_node = current_dict[part]
            current_dict = current_dict[part].children

        # Insert target node
        current_dict[parts[-1]] = target_node


# ============================================================================
# Node chain for checking
# ============================================================================

@dataclass(frozen=True)
class NodeInChain:
    """Node in a checking chain with a relative subpath."""
    node: CompiledFilterNode
    subpath: str  # Path relative to this node


class NodeChainBuilder:
    """
    Builds a chain of nodes from root to the deepest node
    corresponding to path segments.
    """

    @staticmethod
    def build(root: CompiledFilterNode, path: str) -> List[NodeInChain]:
        """
        Builds a chain of nodes for path checking.

        Iterates through path segments (except the last, which might be a file)
        and collects all nodes for which rules need to be checked.

        Args:
            root: Root filtering node
            path: Normalized path (lowercase, POSIX)

        Returns:
            List of nodes with corresponding subpaths for checking
        """
        norm = path.lower().strip("/")
        parts = PurePosixPath(norm).parts

        chain: List[NodeInChain] = [NodeInChain(root, norm or "")]

        current_node = root

        # Iterate through all segments except the last
        for idx, part in enumerate(parts[:-1]):
            child = current_node.get_child(part)
            if child is None:
                break

            current_node = child
            subpath = "/".join(parts[idx + 1:]) or "."
            chain.append(NodeInChain(current_node, subpath))

        return chain


# ============================================================================
# Path evaluator
# ============================================================================

class PathEvaluator:
    """
    Evaluates whether a path should be included in the selection.

    Implements complex filtering logic considering:
    - Block priority over allow
    - Strict mode=allow semantics (default-deny)
    - Rule inheritance across the node chain
    """

    @staticmethod
    def evaluate_include(chain: List[NodeInChain]) -> bool:
        """
        Determines whether a file should be included by path.

        Algorithm:
        1. Iterate through the node chain from root to leaf
        2. At each level:
           - block always wins (immediate rejection)
           - For mode=allow: MUST match local allow, otherwise reject
           - For mode=block: local allow gives temporary permission
        3. If no decision is made - fallback to deepest node's mode

        Args:
            chain: Chain of nodes with subpaths

        Returns:
            True if path is allowed, False otherwise
        """
        if not chain:
            return False

        decision: Optional[bool] = None
        deepest_node = chain[-1].node

        for item in chain:
            node = item.node
            subpath = item.subpath

            # 1. Block always wins
            if node.check_block(subpath):
                return False

            # 2. Strict semantics for mode=allow
            if node.mode == "allow":
                if not node.check_allow(subpath):
                    return False
                # Matched local allow - continue checking
                decision = True
                continue

            # 3. mode=block: default-allow, but local allow strengthens
            if node.check_allow(subpath):
                decision = True

        # Fallback to deepest node's mode
        if decision is not None:
            return decision

        return deepest_node.mode == "block"


class DirectoryPruner:
    """
    Determines whether to descend into a directory subtree.

    Used for early directory pruning during filesystem traversal
    to avoid scanning obviously unnecessary branches.
    """

    @staticmethod
    def may_descend(chain: List[NodeInChain]) -> bool:
        """
        Checks if it makes sense to descend into a directory.

        Conservative check: False = definitely useless, True = potentially useful.

        Args:
            chain: Chain of nodes for the directory

        Returns:
            True if descent is potentially useful
        """
        if not chain:
            return True

        decision: Optional[bool] = None
        deepest_node = chain[-1].node

        for item in chain:
            node = item.node
            subpath = item.subpath

            # 1. Blocking rule - descent is useless
            if DirectoryPruner._check_dir_blocked(node, subpath):
                return False

            # 2. Allow mode - check for possible matches in depth
            if node.mode == "allow":
                if not node.patterns.allow_spec:
                    return False

                if DirectoryPruner._may_match_in_subtree(node, subpath):
                    decision = True
                else:
                    return False
            else:
                # 3. Block mode - descent is potentially useful
                if DirectoryPruner._check_dir_allowed(node, subpath):
                    decision = True

        if decision is not None:
            return decision

        # Fallback: descent is possible in block-mode
        return deepest_node.mode == "block"

    @staticmethod
    def _check_dir_blocked(node: CompiledFilterNode, subpath: str) -> bool:
        """Checks if a directory is blocked."""
        if not node.patterns.block_spec:
            return False

        return (
            node.patterns.block_spec.match_file(subpath) or
            node.patterns.block_spec.match_file(subpath + "/")
        )

    @staticmethod
    def _check_dir_allowed(node: CompiledFilterNode, subpath: str) -> bool:
        """Checks if a directory is explicitly allowed."""
        if not node.patterns.allow_spec:
            return False

        return (
            node.patterns.allow_spec.match_file(subpath) or
            node.patterns.allow_spec.match_file(subpath + "/") or
            node.patterns.allow_spec.match_file(subpath + "/x")
        )

    @staticmethod
    def _may_match_in_subtree(node: CompiledFilterNode, subpath: str) -> bool:
        """
        Fast heuristic: could something match in the subtree.

        Checks raw patterns for:
        - Basename patterns without '/' (match everywhere)
        - Patterns with '**' (match in depth)
        - Patterns starting with the current path
        """
        subpath_clean = subpath.lstrip("/")

        for pat in node.patterns.allow_raw:
            # Patterns with ** match in depth
            if "**" in pat:
                return True

            # Basename patterns without / match everywhere
            if "/" not in pat:
                return True

            # Patterns starting with current path
            if pat.startswith(subpath_clean + "/") or pat.startswith("/" + subpath_clean + "/"):
                return True

        # Conservative check via PathSpec
        return (
            node.patterns.allow_spec.match_file(subpath) or
            node.patterns.allow_spec.match_file(subpath + "/") or
            node.patterns.allow_spec.match_file(subpath + "/x")
        )


# ============================================================================
# Main filtering engine
# ============================================================================

class FilterEngine:
    """
    Filtering engine for filesystem paths.

    Provides two main methods:
    - includes(): decides whether to include a file
    - may_descend(): decides whether to descend into a directory (for pruning)

    Uses a compiled filter tree for efficient checking.
    """

    def __init__(self, root: FilterNode):
        """
        Initializes the filtering engine.

        Args:
            root: Root node of the filter tree
        """
        self._root = CompiledFilterNode.from_filter_node(root)

    def includes(self, rel_path: str) -> bool:
        """
        Checks whether to include a file by path.

        Args:
            rel_path: Relative path of the file (from repository root)

        Returns:
            True if the file is allowed by filtering rules
        """
        chain = NodeChainBuilder.build(self._root, rel_path)
        return PathEvaluator.evaluate_include(chain)

    def may_descend(self, rel_dir: str) -> bool:
        """
        Checks whether to descend into a directory.

        Used for early directory pruning during filesystem traversal.
        Conservative check: False = definitely useless, True = potentially useful.

        Args:
            rel_dir: Relative path of the directory (from repository root)

        Returns:
            True if descent into the directory is potentially useful
        """
        norm = rel_dir.strip("/").lower()
        if not norm:
            return True  # Root is always accessible

        chain = NodeChainBuilder.build(self._root, norm)
        return DirectoryPruner.may_descend(chain)


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "FilterEngine",
    "PathMatch",
    "CompiledFilterNode",
]
