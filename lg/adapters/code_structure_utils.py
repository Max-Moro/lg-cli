"""
Utility functions for Tree-sitter node analysis in optimizations.
Provides common functions for determining node types and relationships.
"""

from __future__ import annotations

from typing import Optional

from lg.adapters.tree_sitter_support import Node


def is_method_node(node: Node) -> bool:
    """
    Определяет, является ли узел методом класса.
    Универсальная функция, которая работает для разных языков.
    
    Args:
        node: Tree-sitter узел для анализа
        
    Returns:
        True если узел является методом класса, False если функцией верхнего уровня
    """
    # Проходим вверх по дереву в поисках определения класса
    current = node.parent
    while current:
        if current.type in ("class_definition", "class_declaration", "class_body"):
            return True
        # Останавливаемся на границах модуля/файла
        if current.type in ("program", "source_file", "module"):
            break
        current = current.parent
    return False


def find_function_definition_in_parents(node: Node) -> Optional[Node]:
    """
    Находит function_definition для данного узла, поднимаясь по дереву.
    
    Args:
        node: Узел для поиска родительской функции
        
    Returns:
        Function definition или None если не найден
    """
    current = node.parent
    while current:
        if current.type in ("function_definition", "method_definition", "arrow_function", 
                           "function_declaration"):
            return current
        current = current.parent
    return None


def get_element_type_from_node(node: Node) -> str:
    """
    Определяет тип элемента на основе структуры узла.
    
    Args:
        node: Tree-sitter узел
        
    Returns:
        Строка с типом элемента: "function", "method", "class", "interface", "type"
    """
    node_type = node.type
    
    # Прямое соответствие типов узлов
    if node_type in ("class_definition", "class_declaration"):
        return "class"
    elif node_type in ("interface_declaration",):
        return "interface"
    elif node_type in ("type_alias_declaration",):
        return "type"
    elif node_type in ("function_definition", "function_declaration", "arrow_function"):
        # Определяем функция это или метод по контексту
        return "method" if is_method_node(node) else "function"
    elif node_type in ("method_definition",):
        return "method"
    else:
        # Fallback: пытаемся определить по родительскому контексту
        if is_method_node(node):
            return "method"
        else:
            return "function"


def collect_function_like_nodes(captures: list[tuple[Node, str]]) -> dict[Node, dict]:
    """
    Группирует захваты Tree-sitter по функциям/методам.
    
    Args:
        captures: Список (node, capture_name) из Tree-sitter запроса
        
    Returns:
        Словарь: function_node -> {"definition": node, "body": node, "name": node, "type": str}
    """
    function_groups = {}
    
    # Сначала собираем все определения функций
    for node, capture_name in captures:
        if capture_name in ("function_definition", "method_definition"):
            function_groups[node] = {
                "definition": node,
                "type": get_element_type_from_node(node)
            }
    
    # Затем ищем соответствующие тела и имена
    for node, capture_name in captures:
        if capture_name in ("function_body", "method_body"):
            # Ищем соответствующее определение функции
            func_def = find_function_definition_in_parents(node)
            if func_def and func_def in function_groups:
                function_groups[func_def]["body"] = node
        
        elif capture_name in ("function_name", "method_name"):
            # Ищем соответствующее определение функции
            func_def = find_function_definition_in_parents(node)
            if func_def and func_def in function_groups:
                function_groups[func_def]["name"] = node
    
    # Обрабатываем случаи когда нет явного definition в захватах
    for node, capture_name in captures:
        if capture_name in ("function_name", "method_name") and node not in function_groups:
            # Создаем группу на основе имени
            func_def = find_function_definition_in_parents(node)
            if func_def and func_def not in function_groups:
                function_groups[func_def] = {
                    "definition": func_def,
                    "name": node,
                    "type": get_element_type_from_node(func_def)
                }
    
    return function_groups
