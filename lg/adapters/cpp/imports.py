"""
C++ import analysis and classification using Tree-sitter AST.
Clean implementation without regex parsing.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..optimizations.imports import ImportClassifier, TreeSitterImportAnalyzer, ImportInfo
from ..tree_sitter_support import TreeSitterDocument, Node


class CppImportClassifier(ImportClassifier):
    """C++-specific import classifier."""

    def __init__(self, external_patterns: List[str] | None = None):
        self.external_patterns = external_patterns if external_patterns is not None else []

        # Standard C++ library headers
        self.cpp_stdlib = {
            # C++ Standard Library
            'iostream', 'fstream', 'sstream', 'iomanip',
            'string', 'vector', 'list', 'map', 'set', 'unordered_map', 'unordered_set',
            'algorithm', 'iterator', 'functional', 'utility', 'memory',
            'exception', 'stdexcept', 'typeinfo', 'type_traits',
            'cstdlib', 'cstdio', 'cstring', 'cmath', 'ctime',
            'thread', 'mutex', 'condition_variable', 'future', 'atomic',
            'regex', 'random', 'chrono', 'filesystem',
            'optional', 'variant', 'any',

            # C Standard Library (commonly used in C++)
            'cassert', 'cctype', 'cerrno', 'cfloat', 'ciso646',
            'climits', 'clocale', 'csetjmp', 'csignal', 'cstdarg',
            'cstddef', 'cstdint', 'cwchar', 'cwctype',
        }

        # Common external patterns for C++
        self.default_external_patterns = [
            r'^boost/',
            r'^Qt[A-Z]',
            r'^[A-Z][a-z]+/',  # Capitalized libraries (e.g., Eigen/, OpenCV/)
            r'^opencv2/',
            r'^nlohmann/',
            r'^fmt/',
            r'^spdlog/',
            r'^gtest/',
            r'^gmock/',
        ]

    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """Determine if a C++ include is external or local."""
        import re

        # Check user-defined patterns first
        for pattern in self.external_patterns:
            if re.match(pattern, module_name):
                return True

        # Check if it's a C++ standard library header
        # Remove path separators to get base header name
        base_header = module_name.split('/')[-1]
        base_header = base_header.replace('.h', '').replace('.hpp', '')

        if base_header in self.cpp_stdlib:
            return True

        # Check default external patterns (before local import check)
        for pattern in self.default_external_patterns:
            if re.match(pattern, module_name):
                return True

        # Check heuristics for local imports
        if self._is_local_import(module_name):
            return False

        # System headers without path (e.g., <stdio.h>, <windows.h>)
        if '/' not in module_name:
            return True

        # If has path and modern C++ extension, likely local
        if module_name.endswith(('.hpp', '.hxx', '.hh', '.h++')):
            return False

        # Default to external for ambiguous cases
        return True

    @staticmethod
    def _is_local_import(module_name: str) -> bool:
        """Check if include looks like a local/project include."""
        import re

        # Relative includes
        if module_name.startswith('.'):
            return True

        # Common local patterns
        local_patterns = [
            r'^src/',
            r'^include/',
            r'^lib/',
            r'^utils/',
            r'^core/',
            r'^internal/',
            r'^detail/',
            r'^impl/',
        ]

        for pattern in local_patterns:
            if re.match(pattern, module_name):
                return True

        # Modern C++ extensions suggest project files
        if module_name.endswith(('.hpp', '.hxx', '.hh', '.h++')):
            return True

        return False


class CppImportAnalyzer(TreeSitterImportAnalyzer):
    """C++-specific Tree-sitter import analyzer."""

    def _parse_import_from_ast(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """Parse C++ include using Tree-sitter AST structure."""
        start_byte, end_byte = doc.get_node_range(node)
        start_line, end_line = doc.get_line_range(node)
        line_count = end_line - start_line + 1

        module_name = ""
        is_external_by_syntax = None

        # In C++ includes have structure:
        # #include <header> or #include "header"
        # Look for path in children
        for child in node.children:
            if child.type == "string_literal":
                # #include "local/header.hpp" - quoted style indicates LOCAL by C++ convention
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                # Remove quotes
                module_name = text.strip('"')
                is_external_by_syntax = False  # Quotes → local
                break
            elif child.type == "system_lib_string":
                # #include <system/header> - angle brackets indicate EXTERNAL by C++ convention
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                # Remove angle brackets
                module_name = text.strip('<>')
                is_external_by_syntax = True  # Angle brackets → external
                break

        if not module_name:
            return None

        # Determine if external: use C++ syntax convention first, then classifier
        # C++ convention: <...> is external, "..." is local
        # But allow classifier to override via external_patterns config
        if is_external_by_syntax is not None:
            # Respect C++ syntax convention
            is_external = is_external_by_syntax
        else:
            # Fallback to classifier
            is_external = self.classifier.is_external(module_name)

        # C++ includes don't have explicit imported items
        # We treat the header name as the imported item
        imported_items = [module_name.split('/')[-1]]

        return ImportInfo(
            node=node,
            import_type="include",
            module_name=module_name,
            imported_items=imported_items,
            is_external=is_external,
            is_wildcard=False,  # C++ includes always include everything
            aliases={},
            start_byte=start_byte,
            end_byte=end_byte,
            line_count=line_count
        )
