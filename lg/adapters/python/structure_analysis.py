"""
Python-specific code structure analysis.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from ..structure_analysis import CodeStructureAnalyzer, FunctionGroup
from ..tree_sitter_support import Node


class PythonCodeStructureAnalyzer(CodeStructureAnalyzer):
    """Python-specific implementation of code structure analyzer."""

    def is_method_element(self, node: Node) -> bool:
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

    def get_element_type(self, node: Node) -> str:
        """
        Определяет тип элемента Python на основе структуры узла.
        
        Args:
            node: Tree-sitter узел
            
        Returns:
            Строка с типом элемента: "function", "method", "class"
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

    def collect_function_like_elements(self, captures: List[Tuple[Node, str]]) -> Dict[Node, FunctionGroup]:
        """
        Группирует захваты Tree-sitter по функциям/методам Python.
        
        Args:
            captures: Список (node, capture_name) из Tree-sitter запроса
            
        Returns:
            Словарь: function_node -> FunctionGroup с информацией о функции
        """
        function_groups = {}
        
        # Сначала собираем все определения функций
        for node, capture_name in captures:
            if capture_name == "function_definition":
                function_groups[node] = FunctionGroup(
                    definition=node,
                    element_type=self.get_element_type(node)
                )
        
        # Затем ищем соответствующие тела и имена
        for node, capture_name in captures:
            if capture_name == "function_body":
                # Ищем соответствующее определение функции
                func_def = self.find_function_definition_in_parents(node)
                if func_def and func_def in function_groups:
                    # Создаем новый FunctionGroup с обновленными данными
                    old_group = function_groups[func_def]
                    function_groups[func_def] = FunctionGroup(
                        definition=old_group.definition,
                        element_type=old_group.element_type,
                        name_node=old_group.name_node,
                        body_node=node,
                        decorators=old_group.decorators
                    )
            
            elif capture_name == "function_name":
                # Ищем соответствующее определение функции
                func_def = self.find_function_definition_in_parents(node)
                if func_def and func_def in function_groups:
                    # Создаем новый FunctionGroup с обновленными данными
                    old_group = function_groups[func_def]
                    function_groups[func_def] = FunctionGroup(
                        definition=old_group.definition,
                        element_type=old_group.element_type,
                        name_node=node,
                        body_node=old_group.body_node,
                        decorators=old_group.decorators
                    )
        
        # Обрабатываем случаи когда нет явного definition в захватах
        for node, capture_name in captures:
            if capture_name == "function_name" and node not in function_groups:
                # Создаем группу на основе имени
                func_def = self.find_function_definition_in_parents(node)
                if func_def and func_def not in function_groups:
                    function_groups[func_def] = FunctionGroup(
                        definition=func_def,
                        element_type=self.get_element_type(func_def),
                        name_node=node
                    )
        
        # Добавляем декораторы для всех функций
        for func_def in function_groups:
            decorators = self.find_decorators_for_element(func_def)
            if decorators:
                old_group = function_groups[func_def]
                function_groups[func_def] = FunctionGroup(
                    definition=old_group.definition,
                    element_type=old_group.element_type,
                    name_node=old_group.name_node,
                    body_node=old_group.body_node,
                    decorators=decorators
                )
        
        return function_groups

    def get_decorated_definition_types(self) -> Set[str]:
        """
        Возвращает типы узлов для wrapped decorated definitions в Python.
        """
        return {
            "decorated_definition",    # Python @decorator
        }

    def get_decorator_types(self) -> Set[str]:
        """
        Возвращает типы узлов для отдельных декораторов в Python.
        """
        return {
            "decorator",              # Python @decorator
        }

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Проверяет, является ли узел пробелом или комментарием в Python.
        """
        return node.type in ("comment", "newline", "\n", " ", "\t")
