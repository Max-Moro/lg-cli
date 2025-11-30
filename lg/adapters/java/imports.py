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
            r'^org\.junit\.',
            r'^org\.mockito\.',
            r'^org\.springframework\.',
            r'^org\.apache\.',
            r'^com\.google\.',
            r'^org\.slf4j\.',
            r'^org\.hibernate\.',
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

        # Heuristics for local imports
        if self._is_local_import(module_name):
            return False

        # If starts with common third-party prefixes, it's external
        if module_name.startswith(('org.', 'com.', 'net.', 'io.')):
            # But check if it's not a known local pattern
            if not self._is_local_import(module_name):
                return True

        # Default to local for unknown packages
        return False

    @staticmethod
    def _is_local_import(module_name: str) -> bool:
        """Check if import looks like a local/project import."""
        import re

        # Common local patterns
        local_patterns = [
            r'^app\.',
            r'^main\.',
            r'^src\.',
            r'^internal\.',
            r'^impl\.',
        ]

        for pattern in local_patterns:
            if re.match(pattern, module_name):
                return True

        # Project-specific patterns (heuristic)
        # If package has specific structure like com.mycompany.myapp
        if module_name.count('.') >= 3:
            parts = module_name.split('.')
            # Check for common company/project indicators
            if len(parts) >= 3:
                third_segment = parts[2]
                # If third segment looks like a project name (not a library)
                local_indicators = ['app', 'application', 'service', 'api', 'core', 'model', 'entity']
                if third_segment in local_indicators:
                    return True

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
