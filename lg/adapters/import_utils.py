"""
Utilities for import statement analysis and classification.
Supports Python and TypeScript/JavaScript imports.
"""

from __future__ import annotations

import re
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


class ImportClassifier:
    """Classifies imports as external vs local."""
    
    def __init__(self, external_patterns: List[str] = None):
        """
        Initialize with patterns for external packages.
        
        Args:
            external_patterns: Regex patterns to identify external packages
        """
        self.external_patterns = external_patterns or []
        
        # Default patterns for common external packages  
        self.default_external_patterns = [
            r'^[a-z][a-z0-9_]*$',  # Single word packages (numpy, pandas, etc.)
            r'^@[a-z][a-z0-9_]*/',  # Scoped packages (@angular/core)
            r'^react',
            r'^vue',
            r'^angular',
            r'^express',
            r'^lodash',
            r'^moment',
        ]
        
        # Python standard library modules (partial list)
        self.python_stdlib = {
            'os', 'sys', 'json', 're', 'math', 'random', 'datetime', 'time',
            'pathlib', 'collections', 'itertools', 'functools', 'typing',
            'urllib', 'http', 'email', 'html', 'xml', 'csv', 'sqlite3',
            'threading', 'multiprocessing', 'subprocess', 'logging',
            'unittest', 'argparse', 'configparser', 'shutil', 'glob',
            'pickle', 'base64', 'hashlib', 'hmac', 'secrets', 'uuid'
        }
    
    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """
        Determine if a module is external (third-party) or local.
        
        Args:
            module_name: The module being imported
            project_root: Optional project root for better local detection
            
        Returns:
            True if module is external, False if local
        """
        # Check user-defined patterns first
        for pattern in self.external_patterns:
            if re.match(pattern, module_name):
                return True
        
        # Check if it's a Python standard library module
        base_module = module_name.split('.')[0]
        if base_module in self.python_stdlib:
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
    
    def _is_local_import(self, module_name: str) -> bool:
        """Check if import looks like a local/relative import."""
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
    
    def _looks_like_local(self, module_name: str) -> bool:
        """Heuristics to identify local modules."""
        # Contains uppercase (PascalCase, common in local modules)
        if any(c.isupper() for c in module_name):
            return True
        
        # Multiple dots often indicate deep local structure
        if module_name.count('.') >= 2:
            return True
        
        # Common local module patterns
        local_indicators = ['app', 'src', 'lib', 'utils', 'models', 'views', 'services', 'myapp']
        for indicator in local_indicators:
            if module_name.startswith(indicator + '.') or module_name == indicator:
                return True
        
        # Contains numbers or unusual underscores
        if re.search(r'[0-9]|__', module_name):
            return True
        
        return False


class ImportAnalyzer:
    """Analyzes and processes import statements."""
    
    def __init__(self, classifier: ImportClassifier = None):
        self.classifier = classifier or ImportClassifier()
    
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
    
    def _parse_import_node(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """Parse a single import node into ImportInfo."""
        import_text = doc.get_node_text(node)
        start_byte, end_byte = doc.get_node_range(node)
        start_line, end_line = doc.get_line_range(node)
        
        # Parse based on language and import type
        if doc.lang_name == "python":
            return self._parse_python_import(
                doc, node, import_type, import_text, start_byte, end_byte, end_line - start_line + 1
            )
        elif doc.lang_name in ("typescript", "javascript"):
            return self._parse_ts_import(
                doc, node, import_type, import_text, start_byte, end_byte, end_line - start_line + 1
            )
        
        return None
    
    def _parse_python_import(
        self, doc: TreeSitterDocument, node: Node, import_type: str, 
        import_text: str, start_byte: int, end_byte: int, line_count: int
    ) -> Optional[ImportInfo]:
        """Parse Python import statement."""
        if import_type == "import":
            # import os, sys, numpy as np
            match = re.match(r'import\s+(.+)', import_text)
            if match:
                imports_part = match.group(1)
                items = [item.strip() for item in imports_part.split(',')]
                
                # Extract module names and aliases
                module_names = []
                imported_items = []
                alias = None
                
                for item in items:
                    if ' as ' in item:
                        module, alias_part = item.split(' as ', 1)
                        module_names.append(module.strip())
                        imported_items.append(alias_part.strip())
                        alias = alias_part.strip()
                    else:
                        module_names.append(item.strip())
                        imported_items.append(item.strip())
                
                # Use first module for classification
                main_module = module_names[0] if module_names else ""
                
                return ImportInfo(
                    node=node,
                    import_type=import_type,
                    module_name=main_module,
                    imported_items=imported_items,
                    is_external=self.classifier.is_external(main_module),
                    alias=alias,
                    start_byte=start_byte,
                    end_byte=end_byte,
                    line_count=line_count
                )
        
        elif import_type == "import_from":
            # from os.path import join, dirname
            match = re.match(r'from\s+(.+?)\s+import\s+(.+)', import_text)
            if match:
                module_name = match.group(1).strip()
                imports_part = match.group(2).strip()
                
                # Parse imported items
                if imports_part == "*":
                    imported_items = ["*"]
                else:
                    items = [item.strip() for item in imports_part.split(',')]
                    imported_items = []
                    for item in items:
                        if ' as ' in item:
                            orig, alias = item.split(' as ', 1)
                            imported_items.append(f"{orig.strip()} as {alias.strip()}")
                        else:
                            imported_items.append(item)
                
                return ImportInfo(
                    node=node,
                    import_type=import_type,
                    module_name=module_name,
                    imported_items=imported_items,
                    is_external=self.classifier.is_external(module_name),
                    start_byte=start_byte,
                    end_byte=end_byte,
                    line_count=line_count
                )
        
        return None
    
    def _parse_ts_import(
        self, doc: TreeSitterDocument, node: Node, import_type: str,
        import_text: str, start_byte: int, end_byte: int, line_count: int
    ) -> Optional[ImportInfo]:
        """Parse TypeScript/JavaScript import statement."""
        # import { Component } from '@angular/core';
        # import React from 'react';
        # import * as fs from 'fs';
        
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
