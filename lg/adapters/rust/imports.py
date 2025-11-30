"""
Rust import analysis and classification using Tree-sitter AST.
Clean implementation without regex parsing.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..optimizations.imports import ImportClassifier, TreeSitterImportAnalyzer, ImportInfo
from ..tree_sitter_support import TreeSitterDocument, Node


class RustImportClassifier(ImportClassifier):
    """Rust-specific import classifier."""

    def __init__(self, external_patterns: List[str] | None = None):
        self.external_patterns = external_patterns if external_patterns is not None else []

        # Rust standard library crates
        self.rust_stdlib = {
            'std', 'core', 'alloc', 'proc_macro',
            'test', 'std::collections', 'std::io', 'std::fs',
            'std::net', 'std::sync', 'std::thread',
            'std::time', 'std::path', 'std::env',
        }

        # Common external patterns for Rust
        self.default_external_patterns = [
            r'^std::',
            r'^core::',
            r'^alloc::',
            r'^serde',
            r'^tokio',
            r'^async_std',
            r'^futures',
            r'^log',
            r'^env_logger',
            r'^clap',
            r'^regex',
            r'^rand',
            r'^chrono',
            r'^reqwest',
            r'^hyper',
            r'^actix',
        ]

    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """Determine if a Rust import is external or local."""
        import re

        # Check user-defined patterns first
        for pattern in self.external_patterns:
            if re.match(pattern, module_name):
                return True

        # Check if it's a Rust standard library crate/module
        root_crate = module_name.split('::')[0]
        if root_crate in ['std', 'core', 'alloc', 'proc_macro', 'test']:
            return True

        # Check against known stdlib modules
        for stdlib_module in self.rust_stdlib:
            if module_name.startswith(stdlib_module):
                return True

        # Check default external patterns
        for pattern in self.default_external_patterns:
            if re.match(pattern, module_name):
                return True

        # Heuristics for local imports
        if self._is_local_import(module_name, project_root):
            return False

        # If starts with 'crate::', it's local
        if module_name.startswith('crate::'):
            return True

        # If starts with 'super::' or 'self::', it's local
        if module_name.startswith(('super::', 'self::')):
            return True

        # If we have project_root, check Cargo.toml
        if project_root:
            cargo_toml = project_root / "Cargo.toml"
            if cargo_toml.exists():
                try:
                    content = cargo_toml.read_text(encoding='utf-8')
                    # Check if module name matches package name
                    for line in content.split('\n'):
                        if line.strip().startswith('name ='):
                            package_name = line.split('=')[1].strip().strip('"\'')
                            # Replace hyphens with underscores (Rust convention)
                            package_name = package_name.replace('-', '_')
                            if module_name.startswith(package_name):
                                return True
                except Exception:
                    pass

        # Single identifier without :: is likely external crate
        if '::' not in module_name:
            return True

        # Default to external for unknown packages
        return True

    @staticmethod
    def _is_local_import(module_name: str, project_root: Optional[Path] = None) -> bool:
        """Check if import looks like a local/project import."""
        # Relative imports
        if module_name.startswith(('crate::', 'super::', 'self::')):
            return True

        # Common local patterns
        if '::' in module_name:
            parts = module_name.split('::')
            # Internal modules
            if 'internal' in parts or 'private' in parts:
                return True

        return False


class RustImportAnalyzer(TreeSitterImportAnalyzer):
    """Rust-specific Tree-sitter import analyzer."""

    def _parse_import_from_ast(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """Parse Rust use declaration using Tree-sitter AST structure."""
        start_byte, end_byte = doc.get_node_range(node)
        start_line, end_line = doc.get_line_range(node)
        line_count = end_line - start_line + 1

        module_name = ""
        imported_items = []
        is_wildcard = False
        aliases = {}

        # Rust use declarations have various structures:
        # use std::collections::HashMap;
        # use std::io::*;
        # use std::io::{Read, Write};
        # use std::io::Result as IoResult;

        # Find the argument (what's being imported)
        for child in node.children:
            if child.type == "scoped_identifier":
                # use std::collections::HashMap
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                module_name = text

                # Extract last component as imported item
                if '::' in module_name:
                    parts = module_name.split('::')
                    imported_items = [parts[-1]]
                else:
                    imported_items = [module_name]

            elif child.type == "identifier":
                # Simple use: use crate_name
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                module_name = text
                imported_items = [text]

            elif child.type == "use_wildcard":
                # use std::io::*
                is_wildcard = True
                # Get the module path before ::*
                for subchild in node.children:
                    if subchild.type == "scoped_identifier":
                        text = doc.get_node_text(subchild)
                        if isinstance(text, bytes):
                            text = text.decode('utf-8')
                        module_name = text
                        break
                imported_items = ["*"]

            elif child.type == "use_list":
                # use std::io::{Read, Write}
                items, item_aliases = self._parse_use_list(doc, child)
                imported_items.extend(items)
                aliases.update(item_aliases)

                # Get module path (everything before the use_list)
                for subchild in node.children:
                    if subchild.type == "scoped_identifier":
                        text = doc.get_node_text(subchild)
                        if isinstance(text, bytes):
                            text = text.decode('utf-8')
                        module_name = text
                        break

            elif child.type == "use_as_clause":
                # use std::io::Result as IoResult
                actual_name = None
                alias_name = None

                for subchild in child.children:
                    if subchild.type == "scoped_identifier":
                        text = doc.get_node_text(subchild)
                        if isinstance(text, bytes):
                            text = text.decode('utf-8')
                        module_name = text
                        actual_name = text.split('::')[-1]
                    elif subchild.type == "identifier":
                        text = doc.get_node_text(subchild)
                        if isinstance(text, bytes):
                            text = text.decode('utf-8')
                        alias_name = text

                if actual_name and alias_name:
                    imported_items = [alias_name]
                    aliases[actual_name] = alias_name

        if not module_name:
            return None

        return ImportInfo(
            node=node,
            import_type="use",
            module_name=module_name,
            imported_items=imported_items,
            is_external=self.classifier.is_external(module_name),
            is_wildcard=is_wildcard,
            aliases=aliases,
            start_byte=start_byte,
            end_byte=end_byte,
            line_count=line_count
        )

    def _parse_use_list(self, doc: TreeSitterDocument, use_list_node: Node) -> tuple[List[str], dict]:
        """Parse use list { Item1, Item2 as Alias }."""
        imported_items = []
        aliases = {}

        for child in use_list_node.children:
            if child.type == "identifier":
                # Simple item: Read
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                imported_items.append(text)

            elif child.type == "scoped_identifier":
                # Nested path: collections::HashMap
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                # Use last component
                imported_items.append(text.split('::')[-1])

            elif child.type == "use_as_clause":
                # Item as Alias
                actual_name = None
                alias_name = None

                for subchild in child.children:
                    if subchild.type in ["identifier", "scoped_identifier"]:
                        text = doc.get_node_text(subchild)
                        if isinstance(text, bytes):
                            text = text.decode('utf-8')
                        if actual_name is None:
                            actual_name = text.split('::')[-1] if '::' in text else text
                        else:
                            alias_name = text

                if actual_name and alias_name:
                    imported_items.append(alias_name)
                    aliases[actual_name] = alias_name

            elif child.type == "use_wildcard":
                # Wildcard in list
                imported_items.append("*")

        return imported_items, aliases
