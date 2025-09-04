"""
TypeScript adapter core: configuration, document and adapter classes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from tree_sitter import Language

from ..code_base import CodeAdapter
from ..code_model import CodeCfg
from ..context import ProcessingContext
from ..tree_sitter_support import TreeSitterDocument, Node


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

    def get_language(self) -> Language:
        import tree_sitter_typescript as tsts
        if self.ext == "ts":
            # У TS и TSX — две разные грамматики в одном пакете.
            return Language(tsts.language_typescript())
        elif self.ext == "tsx":
            return Language(tsts.language_tsx())
        else:
            # Default to TypeScript
            return Language(tsts.language_typescript())

    def get_query_definitions(self) -> Dict[str, str]:
        from .queries import QUERIES
        return QUERIES


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
        from .imports import TypeScriptImportClassifier
        return TypeScriptImportClassifier(external_patterns)

    def create_import_analyzer(self, classifier):
        """Создает TypeScript-специфичный анализатор импортов."""
        from .imports import TypeScriptImportAnalyzer
        return TypeScriptImportAnalyzer(classifier)

    def hook__strip_function_bodies(self, context: ProcessingContext) -> None:
        """Хук для обработки стрелочных функций."""
        self._strip_arrow_functions(context)

    def _strip_arrow_functions(self, context: ProcessingContext) -> None:
        """Обработка стрелочных функций."""
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return
        
        # Ищем стрелочные функции отдельно через re-query
        arrow_functions = [n for n, c in context.query("functions") if n.type == "arrow_function"]
        
        for node in arrow_functions:
            # Найти тело стрелочной функции
            body_node = None
            for child in node.children:
                if child.type in ("statement_block", "expression"):
                    body_node = child
                    break
            
            if not body_node:
                continue
                
            start_line, end_line = context.get_line_range(body_node)
            lines_count = end_line - start_line + 1
            
            # Только стрипим многострочные стрелочные функции
            should_strip = lines_count > 1 and self.should_strip_function_body(node, lines_count, cfg, context)
            
            if should_strip:
                context.remove_function_body(
                    body_node,
                    func_type="function",
                    placeholder_style=self.cfg.placeholders.style
                )

    def is_public_element(self, node: Node, context: ProcessingContext) -> bool:
        """
        Определяет публичность элемента TypeScript по модификаторам доступа.
        
        Правила TypeScript:
        - Элементы с модификатором 'private' - приватные
        - Элементы с модификатором 'protected' - защищенные (считаем приватными)  
        - Элементы с модификатором 'public' или без модификатора - публичные
        """
        # Debug: добавим отладочную информацию
        node_text = context.get_node_text(node)
        
        # Ищем модификаторы доступа среди дочерних узлов и в тексте
        for child in node.children:
            if child.type == "accessibility_modifier":
                modifier_text = context.get_node_text(child)
                if modifier_text in ("private", "protected"):
                    return False
                elif modifier_text == "public":
                    return True
        
        # Fallback: проверяем в тексте узла наличие модификаторов
        if "private " in node_text or node_text.strip().startswith("private "):
            return False
        if "protected " in node_text or node_text.strip().startswith("protected "):
            return False
        
        # Если модификатор не найден, элемент считается публичным по умолчанию
        return True

    def is_exported_element(self, node: Node, context: ProcessingContext) -> bool:
        """
        Определяет, экспортируется ли элемент TypeScript.
        
        Правила:
        - Методы внутри классов НЕ считаются экспортируемыми 
        - Top-level функции, классы, интерфейсы экспортируются если есть export
        - Приватные/защищенные методы никогда не экспортируются
        """
        # Если это метод внутри класса, он НЕ экспортируется напрямую
        if node.type == "method_definition":
            return False
        
        # Проверяем, что это top-level элемент с export
        node_text = context.get_node_text(node)
        
        # Простая проверка: элемент экспортируется если непосредственно перед ним стоит export
        if node_text.strip().startswith("export "):
            return True
        
        # Проверяем parent для export statement
        current = node
        while current and current.type not in ("program", "source_file"):
            if current.type == "export_statement":
                return True
            current = current.parent
        
        # Дополнительная проверка через поиск export в начале строки
        return self._check_export_in_source_line(node, context)

    def _check_export_in_source_line(self, node: Node, context: ProcessingContext) -> bool:
        """
        Проверяет наличие 'export' в исходной строке элемента.
        Это fallback для случаев, когда Tree-sitter не правильно парсит export.
        """
        start_line, _ = context.get_line_range(node)
        lines = context.doc.text.split('\n')
        
        if start_line < len(lines):
            line_text = lines[start_line].strip()
            # Простая проверка на наличие export в начале строки
            if line_text.startswith('export '):
                return True
        
        return False

    def _is_barrel_file(self, context: ProcessingContext) -> bool:
        """
        Определяет, является ли файл barrel file (index.ts или содержит только реэкспорты).
        """
        # Проверяем имя файла
        if context.doc.ext in ("index.ts", "index.tsx"):
            return True
        
        # Анализируем содержимое - если большинство строк содержат export ... from
        lines = context.doc.text.split('\n')
        export_lines = 0
        non_empty_lines = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
                non_empty_lines += 1
                if 'export' in stripped and 'from' in stripped:
                    export_lines += 1
        
        # Если больше 50% строк - реэкспорты, считаем barrel file
        return non_empty_lines > 0 and (export_lines / non_empty_lines) > 0.5
