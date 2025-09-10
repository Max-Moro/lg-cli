"""
Python-специфичная реализация унифицированного анализатора кода.
Объединяет функциональность анализа структуры и видимости для Python.
"""

from __future__ import annotations

from typing import List, Optional, Set

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, PrivateElement
from ..tree_sitter_support import Node


class PythonCodeAnalyzer(CodeAnalyzer):
    """Python-специфичная реализация унифицированного анализатора кода."""

    def determine_element_type(self, node: Node) -> str:
        """
        Определяет тип элемента Python на основе структуры узла.
        
        Args:
            node: Tree-sitter узел
            
        Returns:
            Строка с типом элемента: "function", "method", "class"
        """
        node_type = node.type
        
        if node_type == "class_definition":
            return "class"
        elif node_type == "function_definition":
            return "method" if self.is_method_context(node) else "function"
        elif node_type == "assignment":
            return "variable"
        else:
            # Fallback: пытаемся определить по родительскому контексту
            if self.is_method_context(node):
                return "method"
            else:
                return "function"

    def extract_element_name(self, node: Node) -> Optional[str]:
        """
        Извлекает имя элемента Python из узла Tree-sitter.
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            Имя элемента или None если не найдено
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

    def determine_visibility(self, node: Node) -> Visibility:
        """
        Определяет видимость элемента Python по соглашениям об underscore.
        
        Правила:
        - Имена, начинающиеся с одного _ считаются "protected" (внутренние)
        - Имена, начинающиеся с двух __ считаются "private" 
        - Имена без _ или с trailing _ считаются публичными
        - Специальные методы __method__ считаются публичными
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            Уровень видимости элемента
        """
        element_name = self.extract_element_name(node)
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
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            Статус экспорта элемента
        """
        # TODO: Реализовать проверку __all__ в будущих итерациях
        visibility = self.determine_visibility(node)
        
        if visibility == Visibility.PUBLIC:
            return ExportStatus.EXPORTED
        else:
            return ExportStatus.NOT_EXPORTED

    def is_method_context(self, node: Node) -> bool:
        """
        Определяет, является ли узел методом класса Python.
        
        Args:
            node: Tree-sitter узел для анализа
            
        Returns:
            True если узел является методом класса, False если функцией верхнего уровня
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

    def find_function_definition_in_parents(self, node: Node) -> Optional[Node]:
        """
        Находит function_definition для данного узла, поднимаясь по дереву.
        
        Args:
            node: Узел для поиска родительской функции
            
        Returns:
            Function definition или None если не найден
        """
        current = node.parent
        while current:
            if current.type == "function_definition":
                return current
            current = current.parent
        return None

    def get_decorated_definition_types(self) -> Set[str]:
        """
        Возвращает типы узлов для wrapped decorated definitions в Python.
        
        Returns:
            Множество типов узлов
        """
        return {
            "decorated_definition",    # Python @decorator
        }

    def get_decorator_types(self) -> Set[str]:
        """
        Возвращает типы узлов для отдельных декораторов в Python.
        
        Returns:
            Множество типов узлов
        """
        return {
            "decorator",              # Python @decorator
        }

    def collect_language_specific_private_elements(self) -> List[PrivateElement]:
        """
        Собирает Python-специфичные приватные элементы.
        
        Включает обработку переменных/assignments и других Python-специфичных конструкций.
        
        Returns:
            Список Python-специфичных приватных элементов
        """
        private_elements = []
        
        # Собираем assignments (переменные)
        self._collect_variable_assignments(private_elements)
        
        return private_elements
    
    def _collect_variable_assignments(self, private_elements: List[PrivateElement]) -> None:
        """
        Собирает Python переменные, которые должны быть удалены в режиме public API.
        
        Args:
            private_elements: Список для добавления приватных элементов
        """
        assignments = self.doc.query_opt("assignments")
        for node, capture_name in assignments:
            if capture_name == "variable_name":
                # Получаем узел assignment statement
                assignment_def = node.parent
                if assignment_def:
                    element_info = self.analyze_element(assignment_def)
                    
                    # Для top-level переменных проверяем публичность и экспорт
                    if not element_info.should_be_included_in_public_api:
                        private_elements.append(PrivateElement(element_info))

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Проверяет, является ли узел пробелом или комментарием в Python.
        
        Args:
            node: Tree-sitter узел для проверки
            
        Returns:
            True если узел является пробелом или комментарием
        """
        return node.type in ("comment", "newline", "\n", " ", "\t")
