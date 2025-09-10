"""
Python-specific visibility analysis.
"""

from __future__ import annotations

from typing import List, Optional

from ..visibility_analysis import VisibilityAnalyzer, Visibility, ExportStatus, PrivateElement
from ..tree_sitter_support import Node


class PythonVisibilityAnalyzer(VisibilityAnalyzer):
    """Python-specific implementation of visibility analyzer."""

    def determine_visibility(self, node: Node) -> Visibility:
        """
        Определяет видимость элемента Python по соглашениям об underscore.
        
        Правила:
        - Имена, начинающиеся с одного _ считаются "protected" (внутренние)
        - Имена, начинающиеся с двух __ считаются "private" 
        - Имена без _ или с trailing _ считаются публичными
        - Специальные методы __method__ считаются публичными
        """
        element_name = self.get_element_name(node)
        if not element_name:
            return Visibility.PUBLIC  # Если имя не найдено, считаем публичным
        
        # Специальные методы Python (dunder methods) считаются публичными
        if element_name.startswith("__") and element_name.endswith("__"):
            return Visibility.PUBLIC
        
        # Имена с двумя подчеркиваниями в начале - приватные
        if element_name.startswith("__"):
            return Visibility.PRIVATE
        
        # Имена с одним подчеркиванием в начале - защищенные
        if element_name.startswith("_"):
            return Visibility.PROTECTED
        
        # Все остальные - публичные
        return Visibility.PUBLIC

    def determine_export_status(self, node: Node) -> ExportStatus:
        """
        Определяет статус экспорта элемента Python.
        
        В Python экспорт определяется через __all__ или по умолчанию все публичные элементы.
        Пока упрощенная реализация - считаем все публичные элементы экспортируемыми.
        """
        # TODO: Реализовать проверку __all__ в будущих итерациях
        visibility = self.determine_visibility(node)
        
        if visibility == Visibility.PUBLIC:
            return ExportStatus.EXPORTED
        else:
            return ExportStatus.NOT_EXPORTED

    def is_method_element(self, node: Node) -> bool:
        """
        Определяет, является ли узел методом класса Python.
        """
        # Проходим вверх по дереву в поисках определения класса
        current = node.parent
        while current:
            if current.type == "class_definition":
                return True
            # Останавливаемся на границах модуля/файла
            if current.type in ("module", "program"):
                break
            current = current.parent
        return False

    def get_element_type(self, node: Node) -> str:
        """
        Определяет тип элемента Python на основе структуры узла.
        """
        node_type = node.type
        
        # Прямое соответствие типов узлов
        if node_type == "class_definition":
            return "class"
        elif node_type == "function_definition":
            # Определяем функция это или метод по контексту
            return "method" if self.is_method_element(node) else "function"
        else:
            # Fallback: пытаемся определить по родительскому контексту
            if self.is_method_element(node):
                return "method"
            else:
                return "function"

    def _collect_language_specific_elements(self, context) -> List[PrivateElement]:
        """
        Собирает Python-специфичные приватные элементы.
        
        Включает обработку переменных/assignments и других Python-специфичных конструкций.
        """
        private_elements = []
        
        # Собираем assignments (переменные)
        self._collect_variable_assignments(context, private_elements)
        
        return private_elements
    
    def _collect_variable_assignments(self, context, private_elements: List[PrivateElement]) -> None:
        """Собирает Python переменные, которые должны быть удалены в режиме public API."""
        assignments = context.doc.query_opt("assignments")
        for node, capture_name in assignments:
            if capture_name == "variable_name":
                # Получаем узел assignment statement
                assignment_def = node.parent
                if assignment_def:
                    visibility_info = self.analyze_element_visibility(assignment_def)
                    
                    # Для top-level переменных проверяем публичность и экспорт
                    if not visibility_info.should_be_included_in_public_api:
                        private_elements.append(PrivateElement(
                            node=assignment_def,
                            element_type="variable",
                            visibility_info=visibility_info
                        ))

    def get_element_name(self, node: Node) -> Optional[str]:
        """
        Извлекает имя элемента Python из узла Tree-sitter.
        """
        # Специальная обработка для assignments
        if node.type == "assignment":
            # В assignment левая часть - это имя переменной
            for child in node.children:
                if child.type == "identifier":
                    return self.doc.get_node_text(child)
        
        # Ищем дочерний узел с именем функции/класса/метода
        for child in node.children:
            if child.type == "identifier":
                return self.doc.get_node_text(child)
        
        # Для некоторых типов узлов имя может быть в поле name
        name_node = node.child_by_field_name("name")
        if name_node:
            return self.doc.get_node_text(name_node)
        
        return None
