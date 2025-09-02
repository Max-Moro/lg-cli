"""
Tree-sitter based TypeScript/JavaScript adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any

from .code_base import CodeAdapter, CodeDocument
from .code_model import CodeCfg
from .tree_sitter_support import TreeSitterDocument
from .range_edits import RangeEditor, PlaceholderGenerator, get_comment_style


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
        
        # TypeScript-специфичные оптимизации (не вызываем super() чтобы избежать дублирования)
        if self.cfg.strip_function_bodies:
            # Используем общий set для отслеживания обработанных диапазонов
            processed_ranges = set()
            self._strip_ts_functions(doc, editor, meta, processed_ranges)
            self._strip_ts_methods(doc, editor, meta, processed_ranges)
            self._strip_arrow_functions(doc, editor, meta, processed_ranges)
    
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
