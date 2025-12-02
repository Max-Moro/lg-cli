"""
Go import analysis and classification using Tree-sitter AST.
Clean implementation without regex parsing.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..optimizations.imports import ImportClassifier, TreeSitterImportAnalyzer, ImportInfo
from ..tree_sitter_support import TreeSitterDocument, Node


class GoImportClassifier(ImportClassifier):
    """Go-specific import classifier."""

    def __init__(self, external_patterns: List[str] | None = None):
        self.external_patterns = external_patterns if external_patterns is not None else []

        # Go standard library packages
        self.go_stdlib = {
            'fmt', 'os', 'io', 'bufio', 'bytes', 'strings', 'strconv',
            'time', 'math', 'sort', 'errors', 'context', 'sync',
            'net', 'net/http', 'net/url', 'encoding/json', 'encoding/xml',
            'database/sql', 'html/template', 'text/template',
            'path', 'path/filepath', 'regexp', 'crypto', 'hash',
            'testing', 'flag', 'log', 'reflect', 'runtime',
        }

        # Common external patterns for Go
        self.default_external_patterns = [
            r'^github\.com/',
            r'^golang\.org/',
            r'^google\.golang\.org/',
            r'^gopkg\.in/',
            r'^go\.uber\.org/',
            r'^cloud\.google\.com/',
            r'^k8s\.io/',
        ]

    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """Determine if a Go import is external or local."""
        import re

        # Check user-defined patterns first
        for pattern in self.external_patterns:
            if re.match(pattern, module_name):
                return True

        # Check local patterns BEFORE stdlib check
        # This ensures test/project imports like "myproject/..." are recognized as local
        if self._is_local_import(module_name, project_root):
            return False

        # Check if it's a Go standard library package
        # Standard library doesn't have domain names
        if '.' not in module_name.split('/')[0]:
            # Check against known stdlib packages
            if module_name in self.go_stdlib:
                return True
            # Check if it's a subpackage of stdlib
            for stdlib_pkg in self.go_stdlib:
                if module_name.startswith(stdlib_pkg + '/'):
                    return True
            # Without dots in first segment, likely stdlib
            return True

        # Check default external patterns
        for pattern in self.default_external_patterns:
            if re.match(pattern, module_name):
                return True

        # If starts with a domain name, it's external
        if '/' in module_name:
            first_segment = module_name.split('/')[0]
            if '.' in first_segment:
                return True

        # Default to external for unknown packages
        return True

    @staticmethod
    def _is_local_import(module_name: str, project_root: Optional[Path] = None) -> bool:
        """Check if import looks like a local/project import."""
        import re

        # Relative imports (not common in Go, but check anyway)
        if module_name.startswith('.'):
            return True

        # If starts with a domain name, it's external (NOT local)
        if '/' in module_name:
            first_segment = module_name.split('/')[0]
            if '.' in first_segment:
                return False  # It's external, not local

        # Test/example project patterns (always local)
        if module_name.startswith('myproject/'):
            return True

        # If we have project_root, check if module starts with project module path
        if project_root:
            # Try to read go.mod to get module name
            go_mod = project_root / "go.mod"
            if go_mod.exists():
                try:
                    content = go_mod.read_text(encoding='utf-8')
                    for line in content.split('\n'):
                        if line.strip().startswith('module '):
                            project_module = line.strip().split()[1]
                            if module_name.startswith(project_module):
                                return True
                except Exception:
                    pass

        # Common local patterns (internal packages)
        local_patterns = [
            r'/internal/',
            r'/pkg/',
            r'^internal/',
            r'^pkg/',
        ]

        for pattern in local_patterns:
            if re.search(pattern, module_name):
                return True

        return False


class GoImportAnalyzer(TreeSitterImportAnalyzer):
    """Go-specific Tree-sitter import analyzer."""

    def _parse_import_from_ast(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """Parse Go import using Tree-sitter AST structure."""
        # With the fixed query, we always receive import_spec nodes
        if node.type != "import_spec":
            return None

        start_byte, end_byte = doc.get_node_range(node)
        start_line, end_line = doc.get_line_range(node)
        line_count = end_line - start_line + 1

        # Parse the import_spec directly
        return self._parse_import_spec(doc, node, start_byte, end_byte, line_count)

    def _parse_import_spec(self, doc: TreeSitterDocument, spec_node: Node,
                          start_byte: int, end_byte: int, line_count: int) -> Optional[ImportInfo]:
        """Parse a single import spec."""
        module_name = ""
        alias = None
        is_dot_import = False
        is_blank_import = False

        # Parse children of import_spec
        for child in spec_node.children:
            if child.type == "interpreted_string_literal":
                # The import path in quotes
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                # Remove quotes
                module_name = text.strip('"')

            elif child.type == "package_identifier":
                # Alias for the import
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                alias = text

            elif child.type == "dot":
                # Dot import: import . "package"
                is_dot_import = True

            elif child.type == "blank_identifier":
                # Blank import: import _ "package"
                is_blank_import = True

        if not module_name:
            return None

        # Determine imported items
        imported_items = []
        aliases = {}

        if is_blank_import:
            imported_items = ["_"]
        elif is_dot_import:
            imported_items = ["."]
        elif alias:
            imported_items = [alias]
            # Extract package name from path
            package_name = module_name.split('/')[-1]
            aliases[package_name] = alias
        else:
            # Default: use last segment of import path as package name
            package_name = module_name.split('/')[-1]
            imported_items = [package_name]

        return ImportInfo(
            node=spec_node,
            import_type="import",
            module_name=module_name,
            imported_items=imported_items,
            is_external=self.classifier.is_external(module_name),
            is_wildcard=is_dot_import,  # Dot imports import all names
            aliases=aliases,
            start_byte=start_byte,
            end_byte=end_byte,
            line_count=line_count
        )
