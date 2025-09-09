"""
Tree-sitter based import optimization system.
Clean architecture with proper AST-based analysis.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, cast

from ..context import ProcessingContext
from ..tree_sitter_support import TreeSitterDocument, Node


@dataclass
class ImportInfo:
    """Information about a single import statement."""
    node: Node                      # Tree-sitter node for the import
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


class ImportClassifier(ABC):
    """Abstract base for import classification (external vs local)."""

    @abstractmethod
    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """Determine if a module is external (third-party) or local."""
        pass


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
        
        # Get imports through Tree-sitter queries
        import_nodes = doc.query("imports")
        
        for node, capture_name in import_nodes:
            import_info = self._parse_import_from_ast(doc, node, capture_name)
            if import_info:
                results.append(import_info)
        
        return results

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


class ImportOptimizer:
    """
    Tree-sitter based import processor.
    Handles all import optimization policies.
    """
    
    def __init__(self, adapter):
        """
        Initialize with parent adapter for language-specific operations.
        
        Args:
            adapter: Parent CodeAdapter instance
        """
        from ..code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)
    
    def apply(self, context: ProcessingContext) -> None:
        """
        Apply import processing based on policy.
        
        Args:
            context: Processing context with document and editor
        """
        config = self.adapter.cfg.imports
        
        # If policy is keep_all, nothing to do (except maybe summarize_long)
        if config.policy == "keep_all" and not config.summarize_long:
            return
        
        # Get language-specific analyzer
        classifier = self.adapter.create_import_classifier(config.external_patterns)
        analyzer = self.adapter.create_import_analyzer(classifier)
        
        # Analyze all imports using Tree-sitter
        imports = analyzer.analyze_imports(context.doc)
        if not imports:
            return
        
        # Group by type
        grouped = analyzer.group_imports(imports)
        
        # Apply policy-specific processing
        if config.policy == "strip_all":
            self._process_strip(imports, context)
        elif config.policy == "strip_external":
            self._process_strip(grouped["external"], context)
        elif config.policy == "strip_local":
            self._process_strip(grouped["local"], context)
        
        # Apply summarize_long if enabled (works in addition to policies)
        if config.summarize_long:
            # Re-analyze remaining imports after policy processing
            remaining_imports = analyzer.analyze_imports(context.doc)
            if remaining_imports:
                self._process_summarize_long(remaining_imports, context)
    
    def _process_strip(self, imports: List[ImportInfo], context: ProcessingContext) -> None:
        """Remove specified imports."""
        for imp in imports:
            self._remove_import(context, imp)
    
    def _process_summarize_long(self, imports: List[ImportInfo], context: ProcessingContext) -> None:
        """Summarize imports with too many items."""
        max_items = self.adapter.cfg.imports.max_items_before_summary
        
        for imp in imports:
            if len(imp.imported_items) > max_items:
                self._remove_import(context, imp)
    
    @staticmethod
    def _remove_import(context: ProcessingContext, import_info: ImportInfo) -> None:
        """Remove an import and add appropriate placeholder."""
        count = len(import_info.imported_items)
        
        # Используем новое простое API
        context.add_placeholder("import", import_info.node, count=count)
    
# Export the classes that will be used by language adapters
__all__ = [
    "ImportInfo",
    "ImportClassifier", 
    "TreeSitterImportAnalyzer",
    "ImportOptimizer"
]
