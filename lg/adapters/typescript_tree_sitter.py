"""
Tree-sitter based TypeScript/JavaScript adapter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from .code_base import CodeAdapter, CodeDocument
from .code_model import TypeScriptCfg
from .tree_sitter_support import TreeSitterDocument
from .range_edits import RangeEditor, PlaceholderGenerator, get_comment_style


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
        
        # Применяем базовые оптимизации
        super().apply_tree_sitter_optimizations(doc, editor, meta)
        
        # TypeScript-специфичные оптимизации
        if self.cfg.strip_function_bodies:
            self._strip_ts_methods(doc, editor, meta)
            self._strip_arrow_functions(doc, editor, meta)
    
    def _strip_ts_methods(
        self, 
        doc: TreeSitterDocument, 
        editor: RangeEditor, 
        meta: Dict[str, Any]
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
                method_text = doc.get_node_text(node)
                start_byte, end_byte = doc.get_node_range(node)
                start_line, end_line = doc.get_line_range(node)
                lines_count = end_line - start_line + 1
                
                # Проверяем условия удаления
                should_strip = self._should_strip_function_body(cfg, method_text, lines_count)
                
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
        meta: Dict[str, Any]
    ) -> None:
        """Обрабатывает стрелочные функции в TypeScript."""
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return
        
        # Получаем генератор плейсхолдеров
        comment_style = get_comment_style(self.name)
        placeholder_gen = PlaceholderGenerator(comment_style)
        
        # Ищем стрелочные функции
        functions = doc.query("functions")
        
        for node, capture_name in functions:
            if capture_name == "arrow_body":
                # Проверяем, что это не однострочная стрелочная функция
                arrow_text = doc.get_node_text(node)
                start_byte, end_byte = doc.get_node_range(node)
                start_line, end_line = doc.get_line_range(node)
                lines_count = end_line - start_line + 1
                
                # Для стрелочных функций применяем более консервативный подход
                # Удаляем только многострочные тела
                if lines_count > 1 and self._should_strip_function_body(cfg, arrow_text, lines_count):
                    placeholder = placeholder_gen.create_function_placeholder(
                        name="arrow",
                        lines_removed=lines_count,
                        bytes_removed=end_byte - start_byte,
                        style=self.cfg.placeholders.style
                    )
                    
                    editor.add_replacement(
                        start_byte, end_byte, placeholder,
                        type="arrow_function_removal",
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
