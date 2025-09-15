"""
Python import analysis and classification using Tree-sitter AST.
Clean implementation without regex parsing.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..optimizations.imports import ImportClassifier, TreeSitterImportAnalyzer, ImportInfo
from ..tree_sitter_support import TreeSitterDocument, Node


class PythonImportClassifier(ImportClassifier):
    """Python-specific import classifier."""
    
    def __init__(self, external_patterns: List[str] = []):
        self.external_patterns = external_patterns
        
        # Python standard library modules (comprehensive list)
        self.python_stdlib = {
            # Core modules
            'os', 'sys', 'json', 're', 'math', 'random', 'datetime', 'time',
            'pathlib', 'collections', 'itertools', 'functools', 'typing',
            'urllib', 'http', 'email', 'html', 'xml', 'csv', 'sqlite3',
            'threading', 'multiprocessing', 'subprocess', 'logging',
            'unittest', 'argparse', 'configparser', 'shutil', 'glob',
            'pickle', 'base64', 'hashlib', 'hmac', 'secrets', 'uuid',
            
            # Additional standard library
            'abc', 'array', 'ast', 'asyncio', 'atexit', 'binascii', 'bisect',
            'bz2', 'calendar', 'cmath', 'codecs', 'copy', 'copyreg', 'dataclasses',
            'decimal', 'difflib', 'dis', 'enum', 'errno', 'faulthandler', 'fcntl',
            'filecmp', 'fnmatch', 'fractions', 'gc', 'getopt', 'getpass', 'gettext',
            'gzip', 'heapq', 'importlib', 'inspect', 'io', 'ipaddress', 'keyword',
            'linecache', 'locale', 'lzma', 'mmap', 'operator', 'platform', 'pprint',
            'profile', 'pstats', 'pwd', 'queue', 'reprlib', 'resource', 'runpy',
            'sched', 'select', 'shelve', 'signal', 'site', 'socket', 'ssl', 'stat',
            'statistics', 'string', 'struct', 'symtable', 'sysconfig', 'tarfile',
            'tempfile', 'textwrap', 'timeit', 'token', 'tokenize', 'trace',
            'traceback', 'types', 'unicodedata', 'warnings', 'wave', 'weakref',
            'zipfile', 'zlib'
        }
        
        # Common external patterns
        self.default_external_patterns = [
            r'^[a-z][a-z0-9_]*$',  # Single word packages (numpy, pandas, etc.)
        ]
    
    def is_external(self, module_name: str, project_root: Optional[Path] = None) -> bool:
        """Determine if a Python module is external or local."""
        import re
        
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
    
    @staticmethod
    def _is_local_import(module_name: str) -> bool:
        """Check if import looks like a local/relative import."""
        import re
        
        # Relative imports
        if module_name.startswith('.'):
            return True
        
        # Common local patterns
        local_patterns = [
            r'^src\.',
            r'^lib\.',
            r'^utils\.',
            r'^models\.',
            r'^config\.',
            r'^tests?\.',
            r'^internal?\.',
        ]
        
        for pattern in local_patterns:
            if re.match(pattern, module_name):
                return True
        
        return False
    
    @staticmethod
    def _looks_like_local(module_name: str) -> bool:
        """Heuristics to identify local modules."""
        import re
        
        # Contains uppercase (PascalCase, common in local modules)
        if any(c.isupper() for c in module_name):
            return True
        
        # Multiple dots often indicate deep local structure
        if module_name.count('.') >= 2:
            return True
        
        # Common local module patterns  
        local_indicators = ['app', 'src', 'lib', 'utils', 'models', 'views', 'services', 'myapp', 'myproject']
        for indicator in local_indicators:
            if module_name.startswith(indicator + '.') or module_name == indicator:
                return True
        
        # Contains numbers or unusual underscores
        if re.search(r'[0-9]|__', module_name):
            return True
        
        return False


class PythonImportAnalyzer(TreeSitterImportAnalyzer):
    """Python-specific Tree-sitter import analyzer."""
    
    def _parse_import_from_ast(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """Parse Python import using Tree-sitter AST structure."""
        start_byte, end_byte = doc.get_node_range(node)
        start_line, end_line = doc.get_line_range(node)
        line_count = end_line - start_line + 1
        
        if import_type == "import":
            return self._parse_import_statement(doc, node, start_byte, end_byte, line_count)
        elif import_type == "import_from":
            return self._parse_import_from_statement(doc, node, start_byte, end_byte, line_count)
        
        return None
    
    def _parse_import_statement(self, doc: TreeSitterDocument, node: Node, 
                              start_byte: int, end_byte: int, line_count: int) -> Optional[ImportInfo]:
        """Parse 'import module' statements using AST."""
        # In Python AST, import statement children are: 'import' keyword followed by module names
        imported_items = []
        aliases = {}
        module_names = []
        
        for child in node.children:
            if child.type == 'dotted_name':
                # Simple module name: import os
                module_name = doc.get_node_text(child)
                module_names.append(module_name)
                imported_items.append(module_name)
            elif child.type == 'aliased_import':
                # Module with alias: import numpy as np
                name_node = child.child_by_field_name('name')
                alias_node = child.child_by_field_name('alias')
                
                if name_node and alias_node:
                    actual_name = doc.get_node_text(name_node)
                    alias_name = doc.get_node_text(alias_node)
                    module_names.append(actual_name)
                    imported_items.append(alias_name)
                    aliases[actual_name] = alias_name
        
        # Use first module for classification
        main_module = module_names[0] if module_names else ""
        
        return ImportInfo(
            node=node,
            import_type="import",
            module_name=main_module,
            imported_items=imported_items,
            is_external=self.classifier.is_external(main_module),
            aliases=aliases,
            start_byte=start_byte,
            end_byte=end_byte,
            line_count=line_count
        )
    
    def _parse_import_from_statement(self, doc: TreeSitterDocument, node: Node,
                                   start_byte: int, end_byte: int, line_count: int) -> Optional[ImportInfo]:
        """Parse 'from module import items' statements using AST."""
        # Find module name - can be dotted_name or relative_import
        module_name = ""
        imported_items = []
        aliases = {}
        is_wildcard = False
        
        # Parse children to find module and imported items
        for child in node.children:
            if child.type == 'dotted_name':
                # Check if this is the module name (before 'import' keyword)
                # or imported item (after 'import' keyword)
                if not module_name:  # First dotted_name is module
                    module_name = doc.get_node_text(child)
                else:  # Subsequent dotted_names are imported items
                    item_name = doc.get_node_text(child)
                    imported_items.append(item_name)
                    
            elif child.type == 'relative_import':
                # Relative import: from .module or from ..module
                module_name = doc.get_node_text(child)
                
            elif child.type == 'identifier':
                # After 'import' keyword - this is imported item
                item_name = doc.get_node_text(child)
                imported_items.append(item_name)
                
            elif child.type == 'aliased_import':
                # item as alias
                name_node = child.child_by_field_name('name')
                alias_node = child.child_by_field_name('alias')
                
                if name_node and alias_node:
                    actual_name = doc.get_node_text(name_node)
                    alias_name = doc.get_node_text(alias_node)
                    imported_items.append(alias_name)
                    aliases[actual_name] = alias_name
                    
            elif child.type == 'wildcard_import':
                # from module import *
                imported_items = ['*']
                is_wildcard = True
        
        return ImportInfo(
            node=node,
            import_type="import_from",
            module_name=module_name,
            imported_items=imported_items,
            is_external=self.classifier.is_external(module_name),
            is_wildcard=is_wildcard,
            aliases=aliases,
            start_byte=start_byte,
            end_byte=end_byte,
            line_count=line_count
        )
    
