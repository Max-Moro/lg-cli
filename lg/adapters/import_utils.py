"""
Abstract utilities for import statement analysis and classification.
Language-agnostic base classes and interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .tree_sitter_support import TreeSitterDocument, Node


@dataclass
class ImportInfo:
    """Information about an import statement."""
    node: Node
    import_type: str  # "import", "import_from", etc.
    module_name: str
    imported_items: List[str]  # What is being imported (functions, classes, etc.)
    is_external: bool
    alias: Optional[str] = None
    start_byte: int = 0
    end_byte: int = 0
    line_count: int = 1


class ImportClassifier(ABC):
    """Abstract base class for import classification."""
    
    @abstractmethod
    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """
        Determine if a module is external (third-party) or local.
        
        Args:
            module_name: The module being imported
            project_root: Optional project root for better local detection
            
        Returns:
            True if module is external, False if local
        """
        pass


class ImportAnalyzer(ABC):
    """Abstract base class for import analysis."""
    
    def __init__(self, classifier: ImportClassifier):
        self.classifier = classifier
    
    def analyze_imports(self, doc: TreeSitterDocument) -> List[ImportInfo]:
        """
        Analyze all imports in a document.
        
        Returns:
            List of ImportInfo objects with detailed information
        """
        imports = doc.query("imports")
        results = []
        
        for node, capture_name in imports:
            import_info = self._parse_import_node(doc, node, capture_name)
            if import_info:
                results.append(import_info)
        
        return results
    
    @abstractmethod
    def _parse_import_node(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """Parse a single import node into ImportInfo. Language-specific implementation."""
        pass
    
    def group_imports(self, imports: List[ImportInfo]) -> Dict[str, List[ImportInfo]]:
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
    
    def should_summarize(self, imports: List[ImportInfo], max_items: int) -> bool:
        """Check if import list should be summarized."""
        return len(imports) > max_items
