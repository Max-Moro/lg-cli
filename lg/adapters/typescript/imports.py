"""
TypeScript import analysis and classification.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..optimizations.imports import ImportClassifier, ImportAnalyzer, ImportInfo
from ..tree_sitter_support import TreeSitterDocument, Node


class TypeScriptImportClassifier(ImportClassifier):
    """TypeScript-specific import classifier."""
    
    def __init__(self, external_patterns: List[str] = None):
        self.external_patterns = external_patterns or []
        
        # Common external patterns for TS/JS
        self.default_external_patterns = [
            r'^[a-z][a-z0-9_]*$',  # Single word packages (react, lodash, etc.)
            r'^@[a-z][a-z0-9_]*/',  # Scoped packages (@angular/core)
            r'^react',
            r'^vue',
            r'^angular',
            r'^express',
            r'^lodash',
            r'^moment',
        ]
    
    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """Determine if a TS/JS module is external or local."""
        import re
        
        # Check user-defined patterns first
        for pattern in self.external_patterns:
            if re.match(pattern, module_name):
                return True
        
        # Heuristics for local imports
        if self._is_local_import(module_name):
            return False
        
        # Check default external patterns
        for pattern in self.default_external_patterns:
            if re.match(pattern, module_name):
                return True
        
        # If we can't determine, assume external for unknown packages
        return not self._looks_like_local(module_name)
    
    @staticmethod
    def _is_local_import(module_name: str) -> bool:
        """Check if import looks like a local/relative import."""
        import re
        
        # Relative imports
        if module_name.startswith('.'):
            return True
        
        # Common local patterns (both dot and slash notation)
        local_patterns = [
            r'^src[/.]',
            r'^lib[/.]',
            r'^utils[/.]',
            r'^components[/.]',
            r'^pages[/.]',
            r'^services[/.]',
            r'^models[/.]',
            r'^config[/.]',
            r'^tests?[/.]',
        ]
        
        for pattern in local_patterns:
            if re.match(pattern, module_name):
                return True
        
        # Also check exact matches for common local directories
        if module_name in ['src', 'lib', 'utils', 'components', 'services', 'models']:
            return True
        
        return False
    
    @staticmethod
    def _looks_like_local(module_name: str) -> bool:
        """Heuristics to identify local modules."""

        # Contains uppercase (PascalCase, common in local modules)
        if any(c.isupper() for c in module_name):
            return True
        
        # Multiple slashes often indicate deep local structure
        if module_name.count('/') >= 2:
            return True
        
        # Common local module patterns
        local_indicators = ['app', 'src', 'lib', 'utils', 'components', 'services']
        for indicator in local_indicators:
            if module_name.startswith(indicator + '/') or module_name == indicator:
                return True
        
        return False


class TypeScriptImportAnalyzer(ImportAnalyzer):
    """TypeScript-specific import analyzer."""
    
    def _parse_import_node(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """Parse a TypeScript import node into ImportInfo."""
        import re
        
        import_text = doc.get_node_text(node)
        start_byte, end_byte = doc.get_node_range(node)
        start_line, end_line = doc.get_line_range(node)
        line_count = end_line - start_line + 1
        
        # Extract module name from quotes
        module_match = re.search(r'''['"]([^'"]+)['"]''', import_text)
        if not module_match:
            return None
        
        module_name = module_match.group(1)
        
        # Parse what's being imported
        imported_items = []
        alias = None
        
        # Check for different import patterns
        if ' * as ' in import_text:
            # import * as fs from 'fs'
            match = re.search(r'import\s+\*\s+as\s+(\w+)', import_text)
            if match:
                alias = match.group(1)
                imported_items = ["*"]
        elif ' { ' in import_text:
            # import { Component, OnInit } from '@angular/core'
            match = re.search(r'{\s*([^}]+)\s*}', import_text)
            if match:
                items_text = match.group(1)
                items = [item.strip() for item in items_text.split(',')]
                imported_items = items
        else:
            # import React from 'react'
            match = re.search(r'import\s+(\w+)', import_text)
            if match:
                default_import = match.group(1)
                imported_items = [default_import]
                alias = default_import
        
        return ImportInfo(
            node=node,
            import_type=import_type,
            module_name=module_name,
            imported_items=imported_items,
            is_external=self.classifier.is_external(module_name),
            alias=alias,
            start_byte=start_byte,
            end_byte=end_byte,
            line_count=line_count
        )
