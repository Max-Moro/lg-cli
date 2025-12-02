"""
C import analysis and classification using Tree-sitter AST.
Clean implementation without regex parsing.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..optimizations.imports import ImportClassifier, TreeSitterImportAnalyzer, ImportInfo
from ..tree_sitter_support import TreeSitterDocument, Node


class CImportClassifier(ImportClassifier):
    """C-specific import classifier."""

    def __init__(self, external_patterns: List[str] | None = None):
        self.external_patterns = external_patterns if external_patterns is not None else []

        # Standard C library headers
        self.c_stdlib = {
            # Standard C headers
            'stdio.h', 'stdlib.h', 'string.h', 'math.h', 'time.h',
            'assert.h', 'ctype.h', 'errno.h', 'float.h', 'iso646.h',
            'limits.h', 'locale.h', 'setjmp.h', 'signal.h', 'stdarg.h',
            'stddef.h', 'stdint.h', 'wchar.h', 'wctype.h',

            # POSIX headers
            'unistd.h', 'pthread.h', 'sys/types.h', 'sys/stat.h',
            'fcntl.h', 'dirent.h', 'regex.h',
        }

        # Common external patterns for C
        self.default_external_patterns = [
            r'^sys/',
            r'^arpa/',
            r'^net/',
            r'^linux/',
            r'^windows\.h',
            r'^SDL',
            r'^GL/',
            r'^curl/',
            r'^openssl/',
        ]

    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """Determine if a C include is external or local."""
        import re

        # Check user-defined patterns first
        for pattern in self.external_patterns:
            if re.match(pattern, module_name):
                return True

        # Check if it's a C standard library header
        if module_name in self.c_stdlib:
            return True

        # Check base header name
        base_header = module_name.split('/')[-1]
        if base_header in self.c_stdlib:
            return True

        # Check default external patterns
        for pattern in self.default_external_patterns:
            if re.match(pattern, module_name):
                return True

        # System headers without path
        if '/' not in module_name:
            return True

        # Default: assume local (headers with paths are usually project files)
        return False


class CImportAnalyzer(TreeSitterImportAnalyzer):
    """C-specific Tree-sitter import analyzer."""

    def _parse_import_from_ast(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """Parse C include using Tree-sitter AST structure."""
        start_byte, end_byte = doc.get_node_range(node)
        start_line, end_line = doc.get_line_range(node)
        line_count = end_line - start_line + 1

        module_name = ""
        is_external_by_syntax = None

        # In C includes have structure:
        # #include <header.h> or #include "header.h"
        # Look for path in children
        for child in node.children:
            if child.type == "string_literal":
                # #include "local/header.h" - quoted style indicates LOCAL by C convention
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                # Remove quotes
                module_name = text.strip('"')
                is_external_by_syntax = False  # Quotes → local
                break
            elif child.type == "system_lib_string":
                # #include <system/header.h> - angle brackets indicate EXTERNAL by C convention
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                # Remove angle brackets
                module_name = text.strip('<>')
                is_external_by_syntax = True  # Angle brackets → external
                break

        if not module_name:
            return None

        # Determine if external: use C syntax convention first, then classifier
        # C convention: <...> is external, "..." is local
        # But allow classifier to override via external_patterns config
        if is_external_by_syntax is not None:
            # Respect C syntax convention
            is_external = is_external_by_syntax
        else:
            # Fallback to classifier
            is_external = self.classifier.is_external(module_name)

        # C includes don't have explicit imported items
        # We treat the header name as the imported item
        imported_items = [module_name.split('/')[-1]]

        return ImportInfo(
            node=node,
            import_type="include",
            module_name=module_name,
            imported_items=imported_items,
            is_external=is_external,
            is_wildcard=False,  # C includes always include everything
            aliases={},
            start_byte=start_byte,
            end_byte=end_byte,
            line_count=line_count
        )
