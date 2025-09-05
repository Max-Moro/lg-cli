"""
Import optimization.
Processes import statements according to policy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ..context import ProcessingContext
from ..tree_sitter_support import TreeSitterDocument, Node


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

    @staticmethod
    def should_summarize(imports: List[ImportInfo], max_items: int) -> bool:
        """Check if import list should be summarized."""
        return len(imports) > max_items

class ImportOptimizer:
    """Handles import processing optimization."""
    
    def __init__(self, adapter):
        """
        Initialize with parent adapter for language-specific checks.
        
        Args:
            adapter: Parent CodeAdapter instance for language-specific methods
        """
        self.adapter = adapter
    
    def apply(self, context: ProcessingContext) -> None:
        """
        Apply import processing based on policy.
        
        Args:
            context: Processing context with document and editor
        """
        config = self.adapter.cfg.import_config
        
        # If policy is keep_all, nothing to do
        if config.policy == "keep_all":
            return
        
        # Language adapters must provide their implementations
        classifier = self.adapter.create_import_classifier(config.external_only_patterns)
        analyzer = self.adapter.create_import_analyzer(classifier)
        
        # Analyze all imports
        imports = analyzer.analyze_imports(context.doc)
        if not imports:
            return
        
        # Group by type
        grouped = analyzer.group_imports(imports)
        
        if config.policy == "external_only":
            # Remove local imports, keep external
            self._process_external_only(grouped["local"], context)
        
        elif config.policy == "summarize_long":
            # Summarize long import lists
            if analyzer.should_summarize(imports, config.max_items_before_summary):
                self._process_summarize_long(grouped, context)
    
    def _process_external_only(
        self,
        local_imports: List,
        context: ProcessingContext
    ) -> None:
        """
        Remove local imports, keeping only external ones.
        
        Args:
            local_imports: List of local import objects
            context: Processing context
        """
        if not local_imports:
            return
        
        for imp in local_imports:
            context.remove_import(
                imp.node,
                import_type="local_import",
                placeholder_style=self.adapter.cfg.placeholders.style
            )
    
    def _process_summarize_long(
        self,
        grouped_imports: Dict[str, List],
        context: ProcessingContext,
    ) -> None:
        """
        Summarize long import lists into placeholders.
        
        Args:
            grouped_imports: Dictionary of import groups by type
            context: Processing context
        """
        # Process each group separately
        for group_type, imports in grouped_imports.items():
            if not imports or len(imports) <= self.adapter.cfg.import_config.max_items_before_summary:
                continue
            
            # Group consecutive imports for summarization
            import_ranges = []
            for imp in imports:
                import_ranges.append((imp.start_byte, imp.end_byte, imp))
            
            # Sort by position in file
            import_ranges.sort(key=lambda x: x[0])
            
            # Find groups of consecutive imports
            groups = self._find_consecutive_import_groups(import_ranges)
            
            for group in groups:
                if len(group) <= 2:  # Don't summarize small groups
                    continue
                
                # Use context method for group removal
                context.remove_consecutive_imports(
                    group, group_type, self.adapter.cfg.placeholders.style
                )
    
    @staticmethod
    def _find_consecutive_import_groups(import_ranges: List) -> List[List]:
        """
        Find groups of consecutive imports for summarization.
        
        Args:
            import_ranges: List of (start_byte, end_byte, import_info) tuples
            
        Returns:
            List of groups, where each group is a list of consecutive imports
        """
        if not import_ranges:
            return []
        
        groups = []
        current_group = [import_ranges[0]]
        
        for i in range(1, len(import_ranges)):
            prev_end = current_group[-1][1]
            curr_start = import_ranges[i][0]
            
            # If between imports there's little space (only whitespace/newlines), consider consecutive
            if curr_start - prev_end < 50:  # Heuristic: 50 bytes
                current_group.append(import_ranges[i])
            else:
                if len(current_group) > 1:
                    groups.append(current_group)
                current_group = [import_ranges[i]]
        
        if len(current_group) > 1:
            groups.append(current_group)
        
        return groups
