"""
Python field analysis for detecting trivial constructors, getters, and setters.
"""

from __future__ import annotations

from typing import List, Optional

from ..context import ProcessingContext
from ..tree_sitter_support import Node


def is_trivial_constructor(constructor_body: Node, context: ProcessingContext) -> bool:
    """
    Определяет, является ли конструктор Python тривиальным.
    
    Тривиальный конструктор содержит только:
    - Простые присваивания вида self.field = param
    - Возможно docstring
    - Возможно super().__init__() вызов
    
    Args:
        constructor_body: Узел тела конструктора (__init__)
        context: Контекст обработки
        
    Returns:
        True если конструктор тривиальный
    """
    statements = _extract_statements(constructor_body, context)
    
    # Пустой конструктор - тривиальный
    if not statements:
        return True
    
    significant_statements = []
    
    for stmt in statements:
        stmt_type = stmt.type
        
        # Пропускаем docstring (первое expression_statement со строкой)
        if stmt_type == "expression_statement":
            if _is_docstring(stmt, context):
                continue
        
        # Пропускаем super().__init__() вызовы
        if stmt_type == "expression_statement":
            if _is_super_init_call(stmt, context):
                continue
        
        # Проверяем простые присваивания self.field = param
        if stmt_type == "assignment":
            if _is_simple_field_assignment(stmt, context):
                significant_statements.append(stmt)
                continue
        
        # Любая другая конструкция делает конструктор нетривиальным
        return False
    
    # Конструктор тривиальный, если содержит только простые присваивания полей
    return len(significant_statements) > 0


def is_trivial_getter(getter_body: Node, context: ProcessingContext) -> bool:
    """
    Определяет, является ли геттер Python тривиальным.
    
    Тривиальный геттер содержит только:
    - return self._field (или self.field)
    - Возможно docstring
    
    Args:
        getter_body: Узел тела геттера
        context: Контекст обработки
        
    Returns:
        True если геттер тривиальный
    """
    statements = _extract_statements(getter_body, context)
    
    if not statements:
        return False
    
    return_statement = None
    
    for stmt in statements:
        stmt_type = stmt.type
        
        # Пропускаем docstring
        if stmt_type == "expression_statement":
            if _is_docstring(stmt, context):
                continue
        
        # Ищем return statement
        if stmt_type == "return_statement":
            if return_statement is not None:
                # Более одного return - нетривиальный
                return False
            return_statement = stmt
            continue
        
        # Любая другая конструкция - нетривиальный
        return False
    
    # Должен быть ровно один return с простым доступом к полю
    if return_statement is None:
        return False
    
    return _is_simple_field_access(return_statement, context)


def is_trivial_setter(setter_body: Node, context: ProcessingContext) -> bool:
    """
    Определяет, является ли сеттер Python тривиальным.
    
    Тривиальный сеттер содержит только:
    - self._field = value (или self.field = value)
    - Возможно docstring
    
    Args:
        setter_body: Узел тела сеттера
        context: Контекст обработки
        
    Returns:
        True если сеттер тривиальный
    """
    statements = _extract_statements(setter_body, context)
    
    if not statements:
        return False
    
    assignment_statement = None
    
    for stmt in statements:
        stmt_type = stmt.type
        
        # Пропускаем docstring
        if stmt_type == "expression_statement":
            if _is_docstring(stmt, context):
                continue
        
        # Ищем assignment statement
        if stmt_type == "assignment":
            if assignment_statement is not None:
                # Более одного присваивания - нетривиальный
                return False
            assignment_statement = stmt
            continue
        
        # Любая другая конструкция - нетривиальный
        return False
    
    # Должно быть ровно одно простое присваивание поля
    if assignment_statement is None:
        return False
    
    return _is_simple_field_assignment(assignment_statement, context)


# ============= Вспомогательные функции =============


def _extract_statements(body_node: Node, context: ProcessingContext) -> List[Node]:
    """Извлекает statements из блока кода."""
    statements = []
    
    for child in body_node.children:
        if child.type in (
            "expression_statement", "assignment", "return_statement",
            "if_statement", "for_statement", "while_statement"
        ):
            statements.append(child)
    
    return statements


def _is_docstring(expression_stmt: Node, context: ProcessingContext) -> bool:
    """Проверяет, является ли expression_statement docstring."""
    for child in expression_stmt.children:
        if child.type == "string":
            # Простая эвристика: строка в начале функции - docstring
            return True
    return False


def _is_super_init_call(expression_stmt: Node, context: ProcessingContext) -> bool:
    """Проверяет, является ли statement вызовом super().__init__()."""
    text = context.get_node_text(expression_stmt)
    return "super()" in text and "__init__" in text


def _is_simple_field_assignment(assignment_node: Node, context: ProcessingContext) -> bool:
    """
    Проверяет, является ли присваивание простым присваиванием поля.
    Формат: self.field = param
    """
    # Ищем левую часть (target) и правую часть (value)
    left_node = None
    right_node = None
    
    for child in assignment_node.children:
        if child.type == "attribute":
            left_node = child
        elif child.type in ("identifier", "attribute"):
            if left_node is not None:
                right_node = child
            else:
                left_node = child
    
    if left_node is None or right_node is None:
        return False
    
    # Левая часть должна быть self.something
    left_text = context.get_node_text(left_node)
    if not left_text.startswith("self."):
        return False
    
    # Правая часть должна быть простым идентификатором (параметром)
    right_text = context.get_node_text(right_node)
    if not right_text.replace("_", "").replace("-", "").isalnum():
        return False
    
    return True


def _is_simple_field_access(return_node: Node, context: ProcessingContext) -> bool:
    """
    Проверяет, является ли return простым доступом к полю.
    Формат: return self.field или return self._field
    """
    # Ищем значение return'а
    for child in return_node.children:
        if child.type == "attribute":
            access_text = context.get_node_text(child)
            # Должно быть self.field или self._field
            if access_text.startswith("self."):
                return True
    
    return False
