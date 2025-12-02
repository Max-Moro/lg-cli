"""
Java import analysis and classification using Tree-sitter AST.
Clean implementation without regex parsing.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..optimizations.imports import ImportClassifier, TreeSitterImportAnalyzer, ImportInfo
from ..tree_sitter_support import TreeSitterDocument, Node


class JavaImportClassifier(ImportClassifier):
    """Java-specific import classifier."""

    def __init__(self, external_patterns: List[str] | None = None):
        self.external_patterns = external_patterns if external_patterns is not None else []

        # Java standard library packages
        self.java_stdlib = {
            'java.lang', 'java.util', 'java.io', 'java.nio', 'java.net',
            'java.math', 'java.text', 'java.time', 'java.sql',
            'java.awt', 'java.swing', 'javax.swing',
            'java.beans', 'java.rmi', 'java.security',
            'javax.crypto', 'javax.net', 'javax.sql',
            'javax.xml', 'javax.annotation',
        }

        # Common external patterns for Java
        self.default_external_patterns = [
            r'^java\.',
            r'^javax\.',
        ]

    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """Determine if a Java import is external or local."""
        import re

        # Check user-defined patterns first
        for pattern in self.external_patterns:
            if re.match(pattern, module_name):
                return True

        # Check if it's a Java standard library package
        package_prefix = '.'.join(module_name.split('.')[:2])
        if package_prefix in self.java_stdlib:
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
                    'fasterxml', 'springframework', 'hibernate',
                }
                if second_segment in known_external_orgs:
                    return True

        # Default: assume local
        return False


class JavaImportAnalyzer(TreeSitterImportAnalyzer):
    """Java-specific Tree-sitter import analyzer."""

    def _parse_import_from_ast(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """Parse Java import using Tree-sitter AST structure."""
        start_byte, end_byte = doc.get_node_range(node)
        start_line, end_line = doc.get_line_range(node)
        line_count = end_line - start_line + 1

        module_name = ""
        is_wildcard = False
        imported_items = []

        # Java imports have structure:
        # import package.Class; or import package.*;
        # or import static package.Class.method;

        # Check for static import
        is_static = False
        for child in node.children:
            if child.type == "static":
                is_static = True
                break

        # Find the imported path
        for child in node.children:
            if child.type == "scoped_identifier":
                # import java.util.List
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                module_name = text

                # Extract class name as imported item
                if '.' in module_name:
                    parts = module_name.split('.')
                    imported_items = [parts[-1]]
                else:
                    imported_items = [module_name]
                break
            elif child.type == "asterisk":
                # import java.util.*
                is_wildcard = True
                # Get package name from previous sibling
                idx = node.children.index(child)
                if idx > 0:
                    prev = node.children[idx - 1]
                    if prev.type == "scoped_identifier":
                        text = doc.get_node_text(prev)
                        if isinstance(text, bytes):
                            text = text.decode('utf-8')
                        module_name = text
                imported_items = ["*"]
                break
            elif child.type == "identifier":
                # Simple import (rare, but possible)
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                module_name = text
                imported_items = [text]
                break

        if not module_name:
            return None

        return ImportInfo(
            node=node,
            import_type="import_static" if is_static else "import",
            module_name=module_name,
            imported_items=imported_items,
            is_external=self.classifier.is_external(module_name),
            is_wildcard=is_wildcard,
            aliases={},
            start_byte=start_byte,
            end_byte=end_byte,
            line_count=line_count
        )
