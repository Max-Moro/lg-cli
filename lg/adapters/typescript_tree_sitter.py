"""
Tree-sitter based TypeScript/JavaScript adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from .code_base import CodeAdapter, CodeDocument
from .code_model import CodeCfg
from .import_utils import ImportClassifier, ImportAnalyzer, ImportInfo
from .range_edits import RangeEditor, PlaceholderGenerator, get_comment_style
from .tree_sitter_support import TreeSitterDocument, Node


@dataclass
class TypeScriptCfg(CodeCfg):
    """Конфигурация для TypeScript/JavaScript адаптера."""
    
    def __post_init__(self):
        # TypeScript-специфичные дефолты
        if not hasattr(self, '_ts_defaults_applied'):
            self.public_api_only = True  # для TS часто нужен только exported API
            self._ts_defaults_applied = True


class TypeScriptTreeSitterAdapter(CodeAdapter[TypeScriptCfg]):
    """Tree-sitter based TypeScript adapter."""
    
    name = "typescript"
    extensions = {".ts", ".tsx"}

    def apply_tree_sitter_optimizations(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        meta: Dict[str, Any]
    ) -> None:
        """TypeScript-специфичная обработка с Tree-sitter."""
        
        # TypeScript-специфичные оптимизации для функций
        if self.cfg.strip_function_bodies:
            # Используем общий set для отслеживания обработанных диапазонов
            processed_ranges = set()
            self._strip_ts_functions(doc, editor, meta, processed_ranges)
            self._strip_ts_methods(doc, editor, meta, processed_ranges)
            self._strip_arrow_functions(doc, editor, meta, processed_ranges)
        
        # Вызываем базовую обработку комментариев
        self.process_comments_ts(doc, editor, meta)
        
        # Вызываем базовую обработку импортов
        self.process_imports_ts(doc, editor, meta)
    
    def _create_import_classifier(self, external_patterns: List[str] = None):
        """Создает TypeScript-специфичный классификатор импортов."""
        return TypeScriptImportClassifier(external_patterns)
    
    def _create_import_analyzer(self, classifier):
        """Создает TypeScript-специфичный анализатор импортов."""
        return TypeScriptImportAnalyzer(classifier)
    
    def _strip_ts_functions(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        meta: Dict[str, Any],
        processed_ranges: set
    ) -> None:
        """Обрабатывает функции TypeScript."""
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return
        
        # Получаем генератор плейсхолдеров
        comment_style = get_comment_style(self.name)
        placeholder_gen = PlaceholderGenerator(comment_style)
        
        # Ищем функции
        functions = doc.query("functions")
        
        for node, capture_name in functions:
            if capture_name == "function_body":
                # Получаем информацию о функции
                start_byte, end_byte = doc.get_node_range(node)
                
                # Пропускаем если этот диапазон уже обработан
                range_key = (start_byte, end_byte)
                if range_key in processed_ranges:
                    continue
                processed_ranges.add(range_key)
                
                function_text = doc.get_node_text(node)
                start_line, end_line = doc.get_line_range(node)
                lines_count = end_line - start_line + 1
                
                # Проверяем условия удаления (используем метод из базового класса)
                should_strip = super()._should_strip_function_body(cfg, function_text, lines_count)
                
                if should_strip:
                    # Создаем плейсхолдер
                    placeholder = placeholder_gen.create_function_placeholder(
                        name="function",
                        lines_removed=lines_count,
                        bytes_removed=end_byte - start_byte,
                        style=self.cfg.placeholders.style
                    )
                    
                    # Добавляем правку
                    editor.add_replacement(
                        start_byte, end_byte, placeholder,
                        type="function_body_removal",
                        is_placeholder=True,
                        lines_removed=lines_count
                    )
                    
                    meta["code.removed.functions"] += 1
    
    def _strip_ts_methods(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        meta: Dict[str, Any],
        processed_ranges: set
    ) -> None:
        """Обрабатывает методы классов в TypeScript."""
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return
        
        # Получаем генератор плейсхолдеров
        comment_style = get_comment_style(self.name)
        placeholder_gen = PlaceholderGenerator(comment_style)
        
        # Ищем методы в классах
        methods = doc.query("methods")
        
        for node, capture_name in methods:
            if capture_name == "method_body":
                # Получаем информацию о методе
                start_byte, end_byte = doc.get_node_range(node)
                
                # Пропускаем если этот диапазон уже обработан
                range_key = (start_byte, end_byte)
                if range_key in processed_ranges:
                    continue
                processed_ranges.add(range_key)
                
                method_text = doc.get_node_text(node)
                start_line, end_line = doc.get_line_range(node)
                lines_count = end_line - start_line + 1
                
                # Проверяем условия удаления (используем метод из базового класса)
                should_strip = super()._should_strip_function_body(cfg, method_text, lines_count)
                
                if should_strip:
                    # Создаем плейсхолдер для метода
                    placeholder = placeholder_gen.create_method_placeholder(
                        name="method",
                        lines_removed=lines_count,
                        bytes_removed=end_byte - start_byte,
                        style=self.cfg.placeholders.style
                    )
                    
                    editor.add_replacement(
                        start_byte, end_byte, placeholder,
                        type="method_body_removal",
                        is_placeholder=True,
                        lines_removed=lines_count
                    )
                    
                    meta["code.removed.methods"] += 1
    
    def _strip_arrow_functions(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        meta: Dict[str, Any],
        processed_ranges: set
    ) -> None:
        """Обрабатывает стрелочные функции в TypeScript."""
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return
        
        # Получаем генератор плейсхолдеров
        comment_style = get_comment_style(self.name)
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
            range_key = (start_byte, end_byte)
            if range_key in processed_ranges:
                continue
            processed_ranges.add(range_key)
            
            arrow_text = doc.get_node_text(body_node)
            start_line, end_line = doc.get_line_range(body_node)
            lines_count = end_line - start_line + 1
            
            # Только стрипим многострочные стрелочные функции
            if lines_count > 1 and super()._should_strip_function_body(cfg, arrow_text, lines_count):
                placeholder = placeholder_gen.create_function_placeholder(
                    name="arrow",
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

    # Совместимость со старым интерфейсом
    def parse_code(self, text: str) -> CodeDocument:
        """Совместимость - создает заглушку CodeDocument."""
        lines = text.splitlines()
        return CodeDocument(lines)


class JavaScriptTreeSitterAdapter(TypeScriptTreeSitterAdapter):
    """Tree-sitter based JavaScript adapter (наследует от TypeScript)."""
    
    name = "javascript"
    extensions = {".js", ".jsx"}
    
    # JavaScript использует ту же логику, что и TypeScript,
    # но без типов (которые в любом случае обрабатываются Tree-sitter'ом)


class TypeScriptImportClassifier(ImportClassifier):
    """TypeScript/JavaScript-specific import classifier."""
    
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
    """TypeScript/JavaScript-specific import analyzer."""
    
    def _parse_import_node(self, doc: TreeSitterDocument, node: Node, import_type: str) -> Optional[ImportInfo]:
        """Parse a TypeScript/JavaScript import node into ImportInfo."""
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
