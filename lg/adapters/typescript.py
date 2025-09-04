"""
TypeScript adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional
from tree_sitter import Language, Parser

from .code_base import CodeAdapter
from .code_model import CodeCfg
from .import_utils import ImportClassifier, ImportAnalyzer, ImportInfo
from .range_edits import RangeEditor, PlaceholderGenerator
from .tree_sitter_support import TreeSitterDocument, Node


@dataclass
class TypeScriptCfg(CodeCfg):
    """Конфигурация для TypeScript адаптера."""
    
    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> TypeScriptCfg:
        """Загрузка конфигурации из словаря YAML."""
        if not d:
            return TypeScriptCfg()

        cfg = TypeScriptCfg()
        cfg.general_load(d)

        # TypeScript-специфичные настройки

        return cfg


class TypeScriptDocument(TreeSitterDocument):

    def get_language_parser(self) -> Parser:
        import tree_sitter_typescript as tsts
        # У TS и TSX — две разные грамматики в одном пакете.
        lang: Optional[Language] = None
        if self.ext == "ts":
            lang = Language(tsts.language_typescript())
        elif self.ext == "tsx":
            lang = Language(tsts.language_tsx())

        return Parser(lang)

    def get_language(self) -> Language:
        import tree_sitter_typescript as tsts
        if self.ext == "ts":
            return Language(tsts.language_typescript())
        elif self.ext == "tsx":
            return Language(tsts.language_tsx())
        else:
            # Default to TypeScript
            return Language(tsts.language_typescript())

    def get_query_definitions(self) -> Dict[str, str]:
        from .queries import get_queries_for_language
        return get_queries_for_language('typescript')

class TypeScriptAdapter(CodeAdapter[TypeScriptCfg]):

    name = "typescript"
    extensions = {".ts", ".tsx"}

    def lang_flag__is_oop(self) -> bool:
        return True

    def lang_flag__with_access_modifiers(self) -> bool:
        return True

    def get_comment_style(self) -> tuple[str, tuple[str, str]]:
        return "//", ("/*", "*/")

    def create_document(self, text: str, ext: str) -> TreeSitterDocument:
        return TypeScriptDocument(text, ext)

    def create_import_classifier(self, external_patterns: List[str] = None):
        """Создает TypeScript-специфичный классификатор импортов."""
        return TypeScriptImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier):
        """Создает TypeScript-специфичный анализатор импортов."""
        return TypeScriptImportAnalyzer(classifier)

    def hook__strip_function_bodies(
        self,
        doc: TreeSitterDocument,
        editor: RangeEditor,
        meta: Dict[str, Any]
    ) -> None:
        self._strip_arrow_functions(doc, editor, meta)
    
    def _strip_arrow_functions(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        meta: Dict[str, Any]
    ) -> None:
        """Обрабатывает стрелочные функции в TypeScript."""
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return
        
        # Получаем генератор плейсхолдеров
        comment_style = self.get_comment_style()
        placeholder_gen = PlaceholderGenerator(comment_style)
        
        # Ищем стрелочные функции отдельно через re-query
        arrow_functions = [n for n, c in doc.query("functions") if n.type == "arrow_function"]
        
        for node in arrow_functions:
            # Найти тело стрелочной функции
            body_node = None
            for child in node.children:
                if child.type in ("statement_block", "expression"):
                    body_node = child
                    break
            
            if not body_node:
                continue
                
            start_byte, end_byte = doc.get_node_range(body_node)
            
            arrow_text = doc.get_node_text(body_node)
            start_line, end_line = doc.get_line_range(body_node)
            lines_count = end_line - start_line + 1
            
            # Только стрипим многострочные стрелочные функции
            if lines_count > 1 and super()._should_strip_function_body(cfg, arrow_text, lines_count):
                placeholder = placeholder_gen.create_function_placeholder(
                    lines_removed=lines_count,
                    bytes_removed=end_byte - start_byte,
                    style=self.cfg.placeholders.style
                )
                
                editor.add_replacement(
                    start_byte, end_byte, placeholder,
                    type="arrow_function_body_removal",
                    is_placeholder=True,
                    lines_removed=lines_count
                )
                
                meta["code.removed.functions"] += 1


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
    
    def _is_local_import(self, module_name: str) -> bool:
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
    
    def _looks_like_local(self, module_name: str) -> bool:
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
