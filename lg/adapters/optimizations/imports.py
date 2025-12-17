"""
Tree-sitter based import optimization system.
Clean architecture with proper AST-based analysis.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import cast, Dict, List, Optional

from ..code_model import ImportConfig
from ..context import ProcessingContext
from ..tree_sitter_support import TreeSitterDocument, Node


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
        """Initialize with parent adapter."""
        from ..code_base import CodeAdapter
        self.adapter = cast(CodeAdapter, adapter)
    
    def apply(self, context: ProcessingContext, cfg: ImportConfig) -> None:
        """
        Apply import processing based on policy.

        Args:
            context: Processing context with document and editor
            cfg: Configuration for import processing
        """

        # If policy is keep_all, nothing to do (except maybe summarize_long)
        if cfg.policy == "keep_all" and not cfg.summarize_long:
            return

        # Get language-specific analyzer
        classifier = self.adapter.create_import_classifier(cfg.external_patterns)
        analyzer = self.adapter.create_import_analyzer(classifier)

        # Analyze all imports using Tree-sitter
        imports = analyzer.analyze_imports(context.doc)
        if not imports:
            return

        # Group by type
        grouped = analyzer.group_imports(imports)

        # Apply policy-specific processing
        if cfg.policy == "strip_all":
            self._process_strip(imports, context)
        elif cfg.policy == "strip_external":
            self._process_strip(grouped["external"], context)
        elif cfg.policy == "strip_local":
            self._process_strip(grouped["local"], context)

        # Apply summarize_long if enabled (works in addition to policies)
        if cfg.summarize_long:
            # Re-analyze remaining imports after policy processing
            remaining_imports = analyzer.analyze_imports(context.doc)
            if remaining_imports:
                self._process_summarize_long(remaining_imports, context, cfg)
    
    def _process_strip(self, imports: List[ImportInfo], context: ProcessingContext) -> None:
        """Remove specified imports."""
        for imp in imports:
            self._remove_import(context, imp)
    
    def _process_summarize_long(self, imports: List[ImportInfo], context: ProcessingContext, cfg: ImportConfig) -> None:
        """
        Summarize imports with too many items.

        For languages with from-imports (Python, TypeScript):
        - Check number of items in single import

        For languages with separate imports (Kotlin, Java):
        - Group consecutive imports from one base module
        - Summarize groups exceeding threshold
        """
        max_items = cfg.max_items_before_summary

        # First check imports with multiple items (Python/TS style)
        for imp in imports:
            if len(imp.imported_items) > max_items:
                self._remove_import(context, imp)

        # Then group consecutive imports from one base module (Kotlin/Java style)
        # Base module is first 2 path segments (e.g., io.ktor for io.ktor.server.*)
        grouped_by_base = self._group_consecutive_imports_by_base_module(imports, context)

        for base_module, group in grouped_by_base.items():
            if len(group) > max_items:
                # Summarize entire group
                for imp in group:
                    self._remove_import(context, imp)
    
    def _group_consecutive_imports_by_base_module(self, imports: List[ImportInfo], context: ProcessingContext) -> Dict[str, List[ImportInfo]]:
        """
        Group consecutive imports by base module.

        Sequence is broken if:
        - Base module changes
        - Non-empty lines between imports (comments, code)

        Example:
        import io.ktor.server.Application
        import io.ktor.server.call
        // Comment - break!
        import io.ktor.http.HttpStatus

        Creates TWO io.ktor groups, not one.
        """
        groups: Dict[str, List[ImportInfo]] = {}
        current_base = None
        current_group_key = None
        prev_end_byte = None

        for imp in imports:
            if not imp.module_name:
                continue

            # Determine base module based on separator type
            # Path-based languages (C++, C, Go): use first directory segment
            # Package-based languages (Java, Kotlin, Scala): use first 2 package segments
            if '/' in imp.module_name:
                # Path-based: "validation/email_validator.hpp" -> "validation"
                parts = imp.module_name.split('/')
                base = parts[0] if parts else imp.module_name
            elif '.' in imp.module_name:
                # Package-based: "com.example.foo.Bar" -> "com.example"
                parts = imp.module_name.split('.')
                if len(parts) >= 2:
                    base = '.'.join(parts[:2])
                else:
                    base = imp.module_name
            else:
                # No separator: use full name
                base = imp.module_name

            # Check for sequence break
            is_consecutive = True
            if prev_end_byte is not None:
                # Check that only spaces/newlines between previous and current import
                between_text = context.raw_text[prev_end_byte:imp.start_byte]
                # If non-empty lines (comments, code) - break
                if between_text.strip():
                    is_consecutive = False

            # Check if this import is part of current sequence
            if base == current_base and is_consecutive:
                # Continue current group
                if current_group_key:
                    groups[current_group_key].append(imp)
            else:
                # Start new group
                current_base = base
                # Create unique key for group (base + position of first import)
                current_group_key = f"{base}@{imp.start_byte}"
                groups[current_group_key] = [imp]

            prev_end_byte = imp.end_byte

        return groups

    @staticmethod
    def _remove_import(context: ProcessingContext, import_info: ImportInfo) -> None:
        """Remove an import and add appropriate placeholder."""
        count = len(import_info.imported_items)

        # Use new simple API
        context.add_placeholder_for_node("import", import_info.node, count=count)
    
# Export the classes that will be used by language adapters
__all__ = [
    "ImportInfo",
    "ImportClassifier", 
    "TreeSitterImportAnalyzer",
    "ImportOptimizer"
]
