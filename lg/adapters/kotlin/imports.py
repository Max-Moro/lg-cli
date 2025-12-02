"""
Kotlin import analysis and classification using Tree-sitter AST.
Clean implementation without regex parsing.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..optimizations.imports import ImportClassifier, TreeSitterImportAnalyzer, ImportInfo
from ..tree_sitter_support import TreeSitterDocument, Node


class KotlinImportClassifier(ImportClassifier):
    """Kotlin-specific import classifier."""

    def __init__(self, external_patterns: List[str] | None = None):
        self.external_patterns = external_patterns if external_patterns is not None else []

        # Standard JVM and Kotlin libraries
        self.standard_packages = {
            'java', 'javax', 'kotlin', 'kotlinx',
            'android', 'androidx',
            'org.junit', 'org.hamcrest', 'org.mockito',
        }

        # Patterns for external libraries
        self.default_external_patterns = [
            r'^java\.',
            r'^javax\.',
            r'^kotlin\.',
            r'^kotlinx\.',
            r'^android\.',
            r'^androidx\.',
        ]

    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """Determine if a Kotlin import is external or local."""
        import re

        # Check user-defined patterns first
        for pattern in self.external_patterns:
            if re.match(pattern, module_name):
                return True

        # Check if it's standard library
        package_prefix = module_name.split('.')[0]
        if package_prefix in self.standard_packages:
            return True

        # Check default external patterns
        for pattern in self.default_external_patterns:
            if re.match(pattern, module_name):
                return True

        # Check if it starts with common organizational prefixes
        if module_name.startswith(('org.', 'com.', 'net.', 'io.')):
            parts = module_name.split('.')
            if len(parts) >= 2:
                second_segment = parts[1]
                # Known external organizations in JVM ecosystem
                known_external_orgs = {
                    'google', 'android', 'amazonaws', 'apache', 'eclipse',
                    'junit', 'hamcrest', 'mockito', 'slf4j', 'jetbrains',
                    'fasterxml', 'springframework', 'hibernate', 'koin', 'ktor',
                }
                if second_segment in known_external_orgs:
                    return True

        # Default: assume local
        return False


class KotlinImportAnalyzer(TreeSitterImportAnalyzer):
    """Kotlin-specific Tree-sitter import analyzer."""
    
    def _parse_import_from_ast(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """Parse Kotlin import using Tree-sitter AST structure."""
        start_byte, end_byte = doc.get_node_range(node)
        start_line, end_line = doc.get_line_range(node)
        line_count = end_line - start_line + 1

        # In Kotlin imports have structure:
        # import qualified_identifier [. *] [as identifier]

        module_name = ""
        imported_items = []
        aliases = {}
        alias_name = None

        # Look for qualified_identifier for import path
        qualified_id = None
        for child in node.children:
            if child.type == "qualified_identifier":
                qualified_id = child
                break

        if qualified_id:
            # Extract qualified_identifier text
            text = doc.get_node_text(qualified_id)
            if isinstance(text, bytes):
                text = text.decode('utf-8')
            module_name = text

        # Check for wildcard (. *)
        has_wildcard_dot = False
        has_wildcard_star = False
        for child in node.children:
            if child.type == "." and not has_wildcard_dot:
                # Check if asterisk follows the dot
                next_idx = node.children.index(child) + 1
                if next_idx < len(node.children) and node.children[next_idx].type == "*":
                    has_wildcard_dot = True
            elif child.type == "*" and has_wildcard_dot:
                has_wildcard_star = True

        is_wildcard = has_wildcard_dot and has_wildcard_star

        # Look for alias (as identifier)
        found_as = False
        for i, child in enumerate(node.children):
            if child.type == "as":
                found_as = True
            elif found_as and child.type == "identifier":
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                alias_name = text
                break

        # Form imported_items and aliases
        if is_wildcard:
            imported_items = ["*"]
        elif alias_name:
            imported_items = [alias_name]
            # Last part of path is the imported element
            if module_name:
                parts = module_name.split('.')
                if parts:
                    actual_name = parts[-1]
                    aliases[actual_name] = alias_name
        else:
            # Simple import without alias
            if module_name:
                parts = module_name.split('.')
                if parts:
                    imported_items = [parts[-1]]

        return ImportInfo(
            node=node,
            import_type="import",
            module_name=module_name,
            imported_items=imported_items,
            is_external=self.classifier.is_external(module_name),
            is_wildcard=is_wildcard,
            aliases=aliases,
            start_byte=start_byte,
            end_byte=end_byte,
            line_count=line_count
        )

