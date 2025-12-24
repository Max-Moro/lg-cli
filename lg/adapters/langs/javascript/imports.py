"""
JavaScript import analysis and classification using Tree-sitter AST.
Clean implementation without regex parsing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from ...optimizations.imports import ImportClassifier, TreeSitterImportAnalyzer, ImportInfo
from ...tree_sitter_support import TreeSitterDocument, Node


class JavaScriptImportClassifier(ImportClassifier):
    """JavaScript-specific import classifier."""

    def __init__(self, external_patterns: List[str] | None = None):
        self.external_patterns = external_patterns if external_patterns is not None else []

        # Node.js built-in modules
        self.nodejs_builtins = {
            'fs', 'path', 'os', 'util', 'url', 'events', 'stream', 'crypto',
            'http', 'https', 'net', 'dns', 'tls', 'child_process', 'cluster',
            'worker_threads', 'process', 'buffer', 'timers', 'console',
            'assert', 'zlib', 'querystring', 'readline', 'repl', 'vm',
            'module', 'perf_hooks', 'async_hooks', 'inspector', 'trace_events'
        }

        # Common external patterns for JS
        self.default_external_patterns = [
            r'^[a-z][a-z0-9_-]*$',  # Single word packages (react, lodash, etc.)
            r'^@[a-z][a-z0-9_-]*/',  # Scoped packages (@babel/core, @types/node)
            r'^react',
            r'^vue',
            r'^express',
            r'^lodash',
            r'^moment',
            r'^axios',
            r'^webpack',
            r'^babel',
            r'^eslint',
        ]

    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """Determine if a JS module is external or local."""
        import re

        # Check user-defined patterns first
        for pattern in self.external_patterns:
            if re.match(pattern, module_name):
                return True

        # Check if it's a Node.js built-in module
        base_module = module_name.split('/')[0]
        if base_module in self.nodejs_builtins:
            return True

        # Relative imports are always local
        if module_name.startswith('.'):
            return False

        # Scoped packages are external
        if module_name.startswith('@'):
            return True

        # Check default external patterns
        for pattern in self.default_external_patterns:
            if re.match(pattern, module_name):
                return True

        # Default: assume local
        return False


class JavaScriptImportAnalyzer(TreeSitterImportAnalyzer):
    """JavaScript-specific Tree-sitter import analyzer."""

    def _parse_import_from_ast(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """Parse JavaScript import or re-export using Tree-sitter AST structure."""
        start_byte, end_byte = doc.get_node_range(node)
        start_line, end_line = doc.get_line_range(node)
        line_count = end_line - start_line + 1

        # Handle both import_statement and export_statement (for re-exports)
        if node.type == "export_statement":
            return self._parse_export_from(doc, node, start_byte, end_byte, line_count)

        # Regular import statement
        # Find source module
        module_name = ""
        import_clause_node = None

        for child in node.children:
            if child.type == 'string':
                # Extract module name from quoted string
                source_text = doc.get_node_text(child)
                # Remove quotes - could be single or double
                module_name = source_text.strip('\'"')
            elif child.type == 'import_clause':
                import_clause_node = child

        if not module_name:
            return None

        # Parse the import clause if present
        if not import_clause_node:
            # Side-effect import: import 'module'
            return ImportInfo(
                node=node,
                import_type="import",
                module_name=module_name,
                imported_items=[],
                is_external=self.classifier.is_external(module_name),
                start_byte=start_byte,
                end_byte=end_byte,
                line_count=line_count
            )

        # Parse the import clause
        imported_items, aliases, is_wildcard = self._parse_import_clause(doc, import_clause_node)

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

    def _parse_export_from(self, doc: TreeSitterDocument, node: Node,
                          start_byte: int, end_byte: int, line_count: int) -> Optional[ImportInfo]:
        """Parse export...from statement (re-export)."""
        # export { Foo, Bar } from './module'
        # export * from './module'
        # export * as ns from './module'

        module_name = ""
        exported_items = []
        aliases = {}
        is_wildcard = False

        for child in node.children:
            if child.type == 'string':
                # Source module
                source_text = doc.get_node_text(child)
                module_name = source_text.strip('\'"')

            elif child.type == 'export_clause':
                # Named exports: { Foo, Bar as Baz }
                named_items, named_aliases = self._parse_named_imports(doc, child)
                exported_items.extend(named_items)
                aliases.update(named_aliases)

            elif child.type == 'namespace_export':
                # export * as ns from
                is_wildcard = True
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        ns_name = doc.get_node_text(grandchild)
                        exported_items.append(ns_name)
                        aliases['*'] = ns_name

        # Check for wildcard export without namespace
        node_text = doc.get_node_text(node)
        if isinstance(node_text, bytes):
            node_text = node_text.decode('utf-8')
        if 'export *' in node_text and 'as' not in node_text:
            is_wildcard = True
            exported_items = ['*']

        if not module_name:
            return None

        return ImportInfo(
            node=node,
            import_type="export_from",
            module_name=module_name,
            imported_items=exported_items,
            is_external=self.classifier.is_external(module_name),
            is_wildcard=is_wildcard,
            aliases=aliases,
            start_byte=start_byte,
            end_byte=end_byte,
            line_count=line_count
        )

    def _parse_import_clause(self, doc: TreeSitterDocument, import_clause_node: Node) -> tuple[List[str], Dict[str, str], bool]:
        """Parse import clause from AST, handling all JavaScript import patterns."""
        imported_items = []
        aliases = {}
        is_wildcard = False

        for child in import_clause_node.children:
            if child.type == 'identifier':
                # Default import: import React
                default_name = doc.get_node_text(child)
                imported_items.append(default_name)

            elif child.type == 'namespace_import':
                # Namespace import: import * as fs
                is_wildcard = True
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        namespace_name = doc.get_node_text(grandchild)
                        imported_items.append(namespace_name)
                        aliases['*'] = namespace_name

            elif child.type == 'named_imports':
                # Named imports: import { a, b as c, d }
                named_items, named_aliases = self._parse_named_imports(doc, child)
                imported_items.extend(named_items)
                aliases.update(named_aliases)

        return imported_items, aliases, is_wildcard

    def _parse_named_imports(self, doc: TreeSitterDocument, named_imports_node: Node) -> tuple[List[str], Dict[str, str]]:
        """Parse named imports list from AST."""
        imported_items = []
        aliases = {}

        for child in named_imports_node.children:
            if child.type == 'import_specifier':
                # Import specifier can contain identifier or aliased import
                identifiers = []
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        identifiers.append(doc.get_node_text(grandchild))

                if len(identifiers) == 1:
                    # Simple import: { Component }
                    imported_items.append(identifiers[0])
                elif len(identifiers) == 2:
                    # Aliased import: { Component as Comp }
                    actual_name, alias_name = identifiers
                    imported_items.append(alias_name)
                    aliases[actual_name] = alias_name

        return imported_items, aliases
