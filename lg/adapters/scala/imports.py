"""
Scala import analysis and classification using Tree-sitter AST.
Clean implementation without regex parsing.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..optimizations.imports import ImportClassifier, TreeSitterImportAnalyzer, ImportInfo
from ..tree_sitter_support import TreeSitterDocument, Node


class ScalaImportClassifier(ImportClassifier):
    """Scala-specific import classifier."""

    def __init__(self, external_patterns: List[str] | None = None):
        self.external_patterns = external_patterns if external_patterns is not None else []

        # Scala standard library packages
        self.scala_stdlib = {
            'scala', 'scala.collection', 'scala.util', 'scala.concurrent',
            'scala.io', 'scala.math', 'scala.reflect', 'scala.sys',
            'scala.annotation', 'scala.beans', 'scala.language',
            'scala.text', 'scala.xml',
        }

        # Java standard library (commonly used in Scala)
        self.java_stdlib = {
            'java.lang', 'java.util', 'java.io', 'java.nio',
            'java.net', 'java.math', 'java.time',
        }

        # Common external patterns for Scala
        self.default_external_patterns = [
            r'^scala\.',
            r'^java\.',
            r'^javax\.',
            r'^akka\.',
            r'^cats\.',
            r'^zio\.',
            r'^play\.',
            r'^slick\.',
            r'^org\.scalatest\.',
            r'^org\.scalactic\.',
            r'^org\.apache\.',
            r'^com\.typesafe\.',
        ]

    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """Determine if a Scala import is external or local."""
        import re

        # Check user-defined patterns first
        for pattern in self.external_patterns:
            if re.match(pattern, module_name):
                return True

        # Check if it's a Scala/Java standard library package
        package_prefix = module_name.split('.')[0]
        if package_prefix in ['scala', 'java', 'javax']:
            return True

        # Check two-segment prefix for standard libs
        if '.' in module_name:
            two_segment = '.'.join(module_name.split('.')[:2])
            if two_segment in self.scala_stdlib or two_segment in self.java_stdlib:
                return True

        # Check default external patterns
        for pattern in self.default_external_patterns:
            if re.match(pattern, module_name):
                return True

        # Heuristics for local imports
        if self._is_local_import(module_name):
            return False

        # If starts with common third-party prefixes, it's external
        if module_name.startswith(('org.', 'com.', 'net.', 'io.', 'akka.', 'cats.', 'zio.')):
            if not self._is_local_import(module_name):
                return True

        # Default to local for unknown packages
        return False

    @staticmethod
    def _is_local_import(module_name: str) -> bool:
        """Check if import looks like a local/project import."""
        import re

        # Test/example package patterns (always local)
        if module_name.startswith('com.example.') or module_name.startswith('org.example.'):
            return True

        # Common local patterns
        local_patterns = [
            r'^app\.',
            r'^main\.',
            r'^src\.',
            r'^internal\.',
            r'^impl\.',
            r'^models?\.',
            r'^controllers?\.',
            r'^services?\.',
            r'^utils?\.',
        ]

        for pattern in local_patterns:
            if re.match(pattern, module_name):
                return True

        # Project-specific patterns (heuristic)
        if module_name.count('.') >= 3:
            parts = module_name.split('.')
            if len(parts) >= 3:
                third_segment = parts[2]
                local_indicators = ['app', 'application', 'service', 'api', 'core', 'model', 'controller']
                if third_segment in local_indicators:
                    return True

        return False


class ScalaImportAnalyzer(TreeSitterImportAnalyzer):
    """Scala-specific Tree-sitter import analyzer."""

    def _parse_import_from_ast(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """Parse Scala import using Tree-sitter AST structure."""
        start_byte, end_byte = doc.get_node_range(node)
        start_line, end_line = doc.get_line_range(node)
        line_count = end_line - start_line + 1

        module_name = ""
        imported_items = []
        is_wildcard = False
        aliases = {}

        # Scala imports have various structures:
        # import package.Class
        # import package._
        # import package.{Class1, Class2}
        # import package.{Class => Alias}

        # Build the full import path from individual identifiers
        # Scala import_declaration contains separate identifier nodes for each segment
        # Example: import scala.collection.mutable.ArrayBuffer
        # Children: [import, identifier(scala), ., identifier(collection), ., identifier(mutable), ., identifier(ArrayBuffer)]
        path_parts = []
        for child in node.children:
            if child.type == "identifier":
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                path_parts.append(text)
            elif child.type == "stable_identifier":
                # Backup: if we get stable_identifier (less common), use it directly
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                module_name = text
                break

        # Join all path parts with dots if we collected them
        if path_parts and not module_name:
            module_name = '.'.join(path_parts)

        # Check for wildcard or selectors
        for child in node.children:
            if child.type == "wildcard":
                # import package._
                is_wildcard = True
                imported_items = ["_"]
                break
            elif child.type == "namespace_selectors":
                # import package.{Class1, Class2, Class3 => Alias}
                items, item_aliases = self._parse_namespace_selectors(doc, child)
                imported_items.extend(items)
                aliases.update(item_aliases)

        # If no selectors and no wildcard, it's a simple import
        if not imported_items and not is_wildcard:
            # import package.Class
            if '.' in module_name:
                parts = module_name.split('.')
                imported_items = [parts[-1]]
            else:
                imported_items = [module_name]

        if not module_name:
            return None

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

    def _parse_namespace_selectors(self, doc: TreeSitterDocument, selectors_node: Node) -> tuple[List[str], dict]:
        """Parse namespace selectors { Class1, Class2 => Alias }."""
        imported_items = []
        aliases = {}

        for child in selectors_node.children:
            # Handle direct identifiers (for namespace_selectors)
            if child.type == "identifier":
                text = doc.get_node_text(child)
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                imported_items.append(text)

            elif child.type == "import_selector":
                # Can be: identifier or (identifier => identifier)
                identifiers = []
                for grandchild in child.children:
                    if grandchild.type == "identifier":
                        text = doc.get_node_text(grandchild)
                        if isinstance(text, bytes):
                            text = text.decode('utf-8')
                        identifiers.append(text)

                if len(identifiers) == 1:
                    # Simple selector: Class1
                    imported_items.append(identifiers[0])
                elif len(identifiers) == 2:
                    # Aliased selector: Class1 => Alias
                    actual_name, alias_name = identifiers
                    imported_items.append(alias_name)
                    aliases[actual_name] = alias_name

            elif child.type == "wildcard":
                # Wildcard in selectors: {_, Class1}
                imported_items.append("_")

        return imported_items, aliases
