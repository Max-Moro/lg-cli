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
        classifier = self.adapter.create_import_classifier(config.external_only_patterns)
        analyzer = self.adapter.create_import_analyzer(classifier)
        
        # Analyze all imports using Tree-sitter
        imports = analyzer.analyze_imports(context.doc)
        if not imports:
            return
        
        # Group by type
        grouped = analyzer.group_imports(imports)
        
        # Apply policy-specific processing
        if config.policy == "strip_all":
            self._process_strip_all(imports, context)
        elif config.policy == "strip_external":
            self._process_strip_external(grouped["external"], context)
        elif config.policy == "strip_local":
            self._process_strip_local(grouped["local"], context)
        
        # Apply summarize_long if enabled (works in addition to policies)
        if config.summarize_long:
            # Re-analyze remaining imports after policy processing
            remaining_imports = analyzer.analyze_imports(context.doc)
            if remaining_imports:
                self._process_summarize_long(remaining_imports, context)
    
    def _process_strip_all(self, imports: List[ImportInfo], context: ProcessingContext) -> None:
        """Remove all imports."""
        for imp in imports:
            self._remove_import(context, imp, "import")
    
    def _process_strip_external(self, external_imports: List[ImportInfo], context: ProcessingContext) -> None:
        """Remove external imports, keeping only local ones."""
        for imp in external_imports:
            self._remove_import(context, imp, "external_import")
    
    def _process_strip_local(self, local_imports: List[ImportInfo], context: ProcessingContext) -> None:
        """Remove local imports, keeping only external ones."""
        for imp in local_imports:
            self._remove_import(context, imp, "local_import")
    
    def _process_summarize_long(self, imports: List[ImportInfo], context: ProcessingContext) -> None:
        """Summarize imports with too many items."""
        max_items = self.adapter.cfg.imports.max_items_before_summary
        
        for imp in imports:
            if len(imp.imported_items) > max_items:
                self._remove_import(context, imp, f"long_{imp.import_type}")
    
    def _remove_import(self, context: ProcessingContext, import_info: ImportInfo, reason: str) -> None:
        """Remove an import and add appropriate placeholder."""
        start_byte, end_byte = context.doc.get_node_range(import_info.node)
        start_line, end_line = context.doc.get_line_range(import_info.node)
        lines_count = end_line - start_line + 1
        
        # Create appropriate placeholder
        if reason.startswith("long_"):
            placeholder = self._create_long_import_placeholder(import_info, lines_count)
        elif reason == "local_import":
            placeholder = self._create_local_import_placeholder(import_info)
        else:
            placeholder = f"# … {reason} omitted"
        
        # Apply the edit
        context.editor.add_replacement(
            start_byte, end_byte, placeholder,
            type=f"{reason}_removal",
            is_placeholder=True,
            lines_removed=lines_count
        )
        
        # Update metrics
        context.metrics.mark_import_removed()
        context.metrics.add_lines_saved(lines_count)
        context.metrics.add_bytes_saved(end_byte - start_byte - len(placeholder.encode('utf-8')))
        context.metrics.mark_placeholder_inserted()
    
    def _create_long_import_placeholder(self, import_info: ImportInfo, lines_count: int) -> str:
        """Create placeholder for long import."""
        count = len(import_info.imported_items)
        style = self.adapter.cfg.placeholders.style
        
        if style == "inline" or style == "auto":
            return f"{self.adapter.get_comment_style()[0]} … {count} imports omitted"
        elif style == "block":
            multi_start, multi_end = self.adapter.get_comment_style()[1]
            return f"{multi_start} … {count} imports omitted {multi_end}"
        else:
            return ""
    
    def _create_local_import_placeholder(self, import_info: ImportInfo) -> str:
        """Create placeholder for removed local import."""
        style = self.adapter.cfg.placeholders.style
        
        if style == "inline" or style == "auto":
            return f"{self.adapter.get_comment_style()[0]} … 1 imports omitted"
        elif style == "block":
            multi_start, multi_end = self.adapter.get_comment_style()[1]
            return f"{multi_start} … 1 imports omitted {multi_end}"
        else:
            return ""


# Export the classes that will be used by language adapters
__all__ = [
    "ImportInfo",
    "ImportClassifier", 
    "TreeSitterImportAnalyzer",
    "ImportOptimizer"
]
