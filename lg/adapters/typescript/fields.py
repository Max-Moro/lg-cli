"""
TypeScript field analysis for detecting trivial constructors, getters, and setters.
"""

from __future__ import annotations

from typing import List

from ..optimizations.fields import FieldsClassifier
from ..tree_sitter_support import Node


class TypeScriptFieldsClassifier(FieldsClassifier):
    """TypeScript-specific fields classifier."""

    def is_trivial_constructor(self, constructor_body: Node) -> bool:
        """
        Определяет, является ли конструктор TypeScript тривиальным.

        Тривиальный конструктор содержит только:
        - Простые присваивания вида this.field = param
        - Возможно super() вызов

        Args:
            constructor_body: Узел тела конструктора

        Returns:
            True если конструктор тривиальный
        """
        statements = self._extract_statements(constructor_body)

        # Пустой конструктор - тривиальный
        if not statements:
            return True

        significant_statements = []

        for stmt in statements:
            stmt_type = stmt.type

            # Пропускаем super() вызовы
            if stmt_type == "expression_statement":
                if self._is_super_call(self.doc.get_node_text(stmt)):
                    continue

            # Проверяем простые присваивания this.field = param
            if stmt_type == "expression_statement":
                if self._is_simple_field_assignment(self.doc.get_node_text(stmt).strip()):
                    significant_statements.append(stmt)
                    continue

            # Любая другая конструкция делает конструктор нетривиальным
            return False

        # Конструктор тривиальный, если содержит только простые присваивания полей
        return len(significant_statements) > 0


    def is_trivial_getter(self, getter_body: Node) -> bool:
        """
        Определяет, является ли геттер TypeScript тривиальным.

        Тривиальный геттер содержит только:
        - return this._field (или this.field)

        Args:
            getter_body: Узел тела геттера

        Returns:
            True если геттер тривиальный
        """
        statements = self._extract_statements(getter_body)

        if len(statements) != 1:
            return False

        stmt = statements[0]

        # Должен быть return statement
        if stmt.type != "return_statement":
            return False

        return self._is_simple_field_access(self.doc.get_node_text(stmt).strip())


    def is_trivial_setter(self, setter_body: Node) -> bool:
        """
        Определяет, является ли сеттер TypeScript тривиальным.

        Тривиальный сеттер содержит только:
        - this._field = value (или this.field = value)

        Args:
            setter_body: Узел тела сеттера

        Returns:
            True если сеттер тривиальный
        """
        statements = self._extract_statements(setter_body)

        if len(statements) != 1:
            return False

        stmt = statements[0]

        # Должен быть expression statement с assignment
        if stmt.type != "expression_statement":
            return False

        return self._is_simple_field_assignment(self.doc.get_node_text(stmt).strip())


    # ============= Вспомогательные функции =============


    @staticmethod
    def _extract_statements(body_node: Node) -> List[Node]:
        """Извлекает statements из блока кода TypeScript."""
        statements = []

        for child in body_node.children:
            if child.type in (
                "expression_statement", "return_statement", "assignment_expression",
                "if_statement", "for_statement", "while_statement"
            ):
                statements.append(child)

        return statements


    @staticmethod
    def _is_super_call(text: str) -> bool:
        """Проверяет, является ли statement вызовом super()."""
        return "super(" in text


    def _is_simple_field_assignment(self, text: str) -> bool:
        """
        Проверяет, является ли statement простым присваиванием поля.
        Формат: this.field = param
        """
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
        if not self._is_simple_identifier(right):
            return False

        return True


    def _is_simple_field_access(self, text: str) -> bool:
        """
        Проверяет, является ли return простым доступом к полю.
        Формат: return this.field или return this._field
        """
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
        return self._is_simple_identifier(field_name)


    @staticmethod
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
