"""
Tree-sitter based import analysis infrastructure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

from .classifier import ImportClassifier
from ...tree_sitter_support import TreeSitterDocument, Node


@dataclass
class ImportInfo:
    """Information about a single import statement."""
    node: Node                     # Tree-sitter node for the import
    import_type: str               # "import", "import_from", "export", etc.
    module_name: str               # Module being imported from
    imported_items: List[str]      # List of imported names/aliases
    is_external: bool              # External vs local classification
    is_wildcard: bool = False      # True for "import *" or "export *"
    aliases: Dict[str, str] = None # name -> alias mapping
    start_byte: int = 0
    end_byte: int = 0
    line_count: int = 1

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = {}


class TreeSitterImportAnalyzer(ABC):
    """
    Base Tree-sitter based import analyzer.
    Uses AST structure instead of regex parsing.
    """

    def __init__(self, classifier: ImportClassifier):
        self.classifier = classifier

    def analyze_imports(self, doc: TreeSitterDocument) -> List[ImportInfo]:
        """
        Analyze all imports in a document using Tree-sitter queries.

        Returns:
            List of ImportInfo objects with detailed analysis
        """
        results = []

        # Get imports through inline Tree-sitter query
        query_string = self.get_import_query()
        import_nodes = doc.query_nodes(query_string, "import")

        for node in import_nodes:
            import_info = self._parse_import_from_ast(doc, node, "import")
            if import_info:
                results.append(import_info)

        return results

    @abstractmethod
    def get_import_query(self) -> str:
        """
        Get Tree-sitter query for finding imports.

        Returns:
            Query string with @import captures
        """
        pass

    @abstractmethod
    def _parse_import_from_ast(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """
        Parse import node using Tree-sitter AST structure.
        Language-specific implementation.
        """
        pass

    @staticmethod
    def group_imports(imports: List[ImportInfo]) -> Dict[str, List[ImportInfo]]:
        """Group imports by type (external vs local)."""
        groups = {
            "external": [],
            "local": []
        }

        for imp in imports:
            if imp.is_external:
                groups["external"].append(imp)
            else:
                groups["local"].append(imp)

        return groups


__all__ = ["ImportInfo", "TreeSitterImportAnalyzer"]
