"""
TypeScript field analysis for detecting trivial constructors, getters, and setters.
"""

from __future__ import annotations

from typing import List, Optional

from ..context import ProcessingContext
from ..tree_sitter_support import Node


def is_trivial_constructor(constructor_body: Node, context: ProcessingContext) -> bool:
    """
    Определяет, является ли конструктор TypeScript тривиальным.
    
    Тривиальный конструктор содержит только:
    - Простые присваивания вида this.field = param
    - Возможно super() вызов
    
    Args:
        constructor_body: Узел тела конструктора
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
        
        # Пропускаем super() вызовы
        if stmt_type == "expression_statement":
            if _is_super_call(stmt, context):
                continue
        
        # Проверяем простые присваивания this.field = param
        if stmt_type == "expression_statement":
            if _is_simple_field_assignment(stmt, context):
                significant_statements.append(stmt)
                continue
        
        # Любая другая конструкция делает конструктор нетривиальным
        return False
    
    # Конструктор тривиальный, если содержит только простые присваивания полей
    return len(significant_statements) > 0


def is_trivial_getter(getter_body: Node, context: ProcessingContext) -> bool:
    """
    Определяет, является ли геттер TypeScript тривиальным.
    
    Тривиальный геттер содержит только:
    - return this._field (или this.field)
    
    Args:
        getter_body: Узел тела геттера
        context: Контекст обработки
        
    Returns:
        True если геттер тривиальный
    """
    statements = _extract_statements(getter_body, context)
    
    if len(statements) != 1:
        return False
    
    stmt = statements[0]
    
    # Должен быть return statement
    if stmt.type != "return_statement":
        return False
    
    return _is_simple_field_access(stmt, context)


def is_trivial_setter(setter_body: Node, context: ProcessingContext) -> bool:
    """
    Определяет, является ли сеттер TypeScript тривиальным.
    
    Тривиальный сеттер содержит только:
    - this._field = value (или this.field = value)
    
    Args:
        setter_body: Узел тела сеттера
        context: Контекст обработки
        
    Returns:
        True если сеттер тривиальный
    """
    statements = _extract_statements(setter_body, context)
    
    if len(statements) != 1:
        return False
    
    stmt = statements[0]
    
    # Должен быть expression statement с assignment
    if stmt.type != "expression_statement":
        return False
    
    return _is_simple_field_assignment(stmt, context)


# ============= Вспомогательные функции =============


def _extract_statements(body_node: Node, context: ProcessingContext) -> List[Node]:
    """Извлекает statements из блока кода TypeScript."""
    statements = []
    
    for child in body_node.children:
        if child.type in (
            "expression_statement", "return_statement", "assignment_expression",
            "if_statement", "for_statement", "while_statement"
        ):
            statements.append(child)
    
    return statements


def _is_super_call(expression_stmt: Node, context: ProcessingContext) -> bool:
    """Проверяет, является ли statement вызовом super()."""
    text = context.get_node_text(expression_stmt)
    return "super(" in text


def _is_simple_field_assignment(expression_stmt: Node, context: ProcessingContext) -> bool:
    """
    Проверяет, является ли statement простым присваиванием поля.
    Формат: this.field = param
    """
    text = context.get_node_text(expression_stmt).strip()
    
    # Удаляем точку с запятой в конце если есть
    if text.endswith(';'):
        text = text[:-1].strip()
    
    # Простая проверка паттерна this.field = param
    if " = " not in text:
        return False
    
    left, right = text.split(" = ", 1)
    left = left.strip()
    right = right.strip()
    
    # Левая часть должна быть this.something
    if not left.startswith("this."):
        return False
    
    # Правая часть должна быть простым идентификатором
    if not _is_simple_identifier(right):
        return False
    
    return True


def _is_simple_field_access(return_node: Node, context: ProcessingContext) -> bool:
    """
    Проверяет, является ли return простым доступом к полю.
    Формат: return this.field или return this._field
    """
    text = context.get_node_text(return_node).strip()
    
    # Удаляем 'return' в начале
    if text.startswith("return "):
        value = text[7:].strip()
    else:
        return False
    
    # Удаляем точку с запятой в конце если есть
    if value.endswith(';'):
        value = value[:-1].strip()
    
    # Должно быть this.field или this._field
    if not value.startswith("this."):
        return False
    
    field_name = value[5:]  # убираем "this."
    
    # Имя поля должно быть простым идентификатором
    return _is_simple_identifier(field_name)


def _is_simple_identifier(text: str) -> bool:
    """Проверяет, является ли текст простым идентификатором."""
    if not text:
        return False
    
    # Простая проверка на валидный идентификатор
    if not (text[0].isalpha() or text[0] == '_'):
        return False
    
    for char in text[1:]:
        if not (char.isalnum() or char == '_'):
            return False
    
    return True
