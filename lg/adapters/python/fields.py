"""
Python field analysis for detecting trivial constructors, getters, and setters.
"""

from __future__ import annotations

from typing import List

from ..tree_sitter_support import Node
from ..optimizations.fields import FieldsClassifier


class PythonFieldsClassifier(FieldsClassifier):
    """Python-specific fields classifier."""

    def is_trivial_constructor(self, constructor_body: Node) -> bool:
        """
        Определяет, является ли конструктор Python тривиальным.

        Тривиальный конструктор содержит только:
        - Простые присваивания вида self.field = param
        - Возможно docstring
        - Возможно super().__init__() вызов

        Args:
            constructor_body: Узел тела конструктора (__init__)

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

            # Пропускаем docstring (первое expression_statement со строкой)
            if stmt_type == "expression_statement":
                if self._is_docstring(stmt):
                    continue

            # Пропускаем super().__init__() вызовы
            if stmt_type == "expression_statement":
                if self._is_super_init_call(self.doc.get_node_text(stmt)):
                    continue

            # Проверяем простые присваивания self.field = param
            if stmt_type == "assignment":
                if self._is_simple_field_assignment(stmt):
                    significant_statements.append(stmt)
                    continue

            # Любая другая конструкция делает конструктор нетривиальным
            return False

        # Конструктор тривиальный, если содержит только простые присваивания полей
        return len(significant_statements) > 0


    def is_trivial_getter(self, getter_body: Node) -> bool:
        """
        Определяет, является ли геттер Python тривиальным.

        Тривиальный геттер содержит только:
        - return self._field (или self.field)
        - Возможно docstring

        Args:
            getter_body: Узел тела геттера

        Returns:
            True если геттер тривиальный
        """
        statements = self._extract_statements(getter_body)

        if not statements:
            return False

        return_statement = None

        for stmt in statements:
            stmt_type = stmt.type

            # Пропускаем docstring
            if stmt_type == "expression_statement":
                if self._is_docstring(stmt):
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

        return self._is_simple_field_access(return_statement)


    def is_trivial_setter(self, setter_body: Node) -> bool:
        """
        Определяет, является ли сеттер Python тривиальным.

        Тривиальный сеттер содержит только:
        - self._field = value (или self.field = value)
        - Возможно docstring

        Args:
            setter_body: Узел тела сеттера

        Returns:
            True если сеттер тривиальный
        """
        statements = self._extract_statements(setter_body)

        if not statements:
            return False

        assignment_statement = None

        for stmt in statements:
            stmt_type = stmt.type

            # Пропускаем docstring
            if stmt_type == "expression_statement":
                if self._is_docstring(stmt):
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

        return self._is_simple_field_assignment(assignment_statement)

    # ============= Вспомогательные функции =============

    @staticmethod
    def _extract_statements(body_node: Node) -> List[Node]:
        """Извлекает statements из блока кода."""
        statements = []

        for child in body_node.children:
            if child.type in (
                "expression_statement", "assignment", "return_statement",
                "if_statement", "for_statement", "while_statement"
            ):
                statements.append(child)

        return statements


    @staticmethod
    def _is_docstring(expression_stmt: Node) -> bool:
        """Проверяет, является ли expression_statement docstring."""
        for child in expression_stmt.children:
            if child.type == "string":
                # Простая эвристика: строка в начале функции - docstring
                return True
        return False


    @staticmethod
    def _is_super_init_call(text: str) -> bool:
        """Проверяет, является ли statement вызовом super().__init__()."""
        return "super()" in text and "__init__" in text


    def _is_simple_field_assignment(self, assignment_node: Node) -> bool:
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
        left_text = self.doc.get_node_text(left_node)
        if not left_text.startswith("self."):
            return False

        # Правая часть должна быть простым идентификатором (параметром)
        right_text = self.doc.get_node_text(right_node)
        if not right_text.replace("_", "").replace("-", "").isalnum():
            return False

        return True


    def _is_simple_field_access(self, return_node: Node) -> bool:
        """
        Проверяет, является ли return простым доступом к полю.
        Формат: return self.field или return self._field
        """
        # Ищем значение return'а
        for child in return_node.children:
            if child.type == "attribute":
                access_text = self.doc.get_node_text(child)
                # Должно быть self.field или self._field
                if access_text.startswith("self."):
                    return True

        return False
