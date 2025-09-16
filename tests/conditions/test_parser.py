"""
Тесты для парсера условий.
"""

import pytest

from lg.conditions.model import (
    ConditionType,
    TagCondition,
    TagSetCondition,
    ScopeCondition,
    GroupCondition,
    NotCondition,
    BinaryCondition,
)
from lg.conditions.parser import ConditionParser, ParseError


class TestConditionParser:
    
    def setup_method(self):
        self.parser = ConditionParser()
    
    def test_empty_condition_error(self):
        """Тест ошибки при пустом условии"""
        with pytest.raises(ParseError, match="Empty condition"):
            self.parser.parse("")
        
        with pytest.raises(ParseError, match="Empty condition"):
            self.parser.parse("   ")
    
    def test_simple_tag_condition(self):
        """Тест простого условия тега"""
        result = self.parser.parse("tag:python")
        
        assert isinstance(result, TagCondition)
        assert result.name == "python"
    
    def test_tagset_condition(self):
        """Тест условия набора тегов"""
        result = self.parser.parse("TAGSET:language:python")
        
        assert isinstance(result, TagSetCondition)
        assert result.set_name == "language"
        assert result.tag_name == "python"
    
    def test_scope_condition_local(self):
        """Тест условия локального скоупа"""
        result = self.parser.parse("scope:local")
        
        assert isinstance(result, ScopeCondition)
        assert result.scope_type == "local"
    
    def test_scope_condition_parent(self):
        """Тест условия родительского скоупа"""
        result = self.parser.parse("scope:parent")
        
        assert isinstance(result, ScopeCondition)
        assert result.scope_type == "parent"
    
    def test_invalid_scope_type(self):
        """Тест ошибки при неверном типе скоупа"""
        with pytest.raises(ParseError, match="Invalid scope type"):
            self.parser.parse("scope:invalid")
    
    def test_not_condition(self):
        """Тест условия отрицания"""
        result = self.parser.parse("NOT tag:deprecated")
        
        assert isinstance(result, NotCondition)
        assert isinstance(result.condition, TagCondition)
        assert result.condition.name == "deprecated"
    
    def test_and_condition(self):
        """Тест условия И"""
        result = self.parser.parse("tag:python AND tag:tests")
        
        assert isinstance(result, BinaryCondition)
        assert result.operator == ConditionType.AND
        
        assert isinstance(result.left, TagCondition)
        assert result.left.name == "python"
        
        assert isinstance(result.right, TagCondition)
        assert result.right.name == "tests"
    
    def test_or_condition(self):
        """Тест условия ИЛИ"""
        result = self.parser.parse("tag:python OR tag:javascript")
        
        assert isinstance(result, BinaryCondition)
        assert result.operator == ConditionType.OR
        
        assert isinstance(result.left, TagCondition)
        assert result.left.name == "python"
        
        assert isinstance(result.right, TagCondition)
        assert result.right.name == "javascript"
    
    def test_operator_precedence(self):
        """Тест приоритета операторов: AND имеет больший приоритет чем OR"""
        result = self.parser.parse("tag:a OR tag:b AND tag:c")
        
        # Должно быть: tag:a OR (tag:b AND tag:c)
        assert isinstance(result, BinaryCondition)
        assert result.operator == ConditionType.OR
        
        assert isinstance(result.left, TagCondition)
        assert result.left.name == "a"
        
        assert isinstance(result.right, BinaryCondition)
        assert result.right.operator == ConditionType.AND
        assert isinstance(result.right.left, TagCondition)
        assert result.right.left.name == "b"
        assert isinstance(result.right.right, TagCondition)
        assert result.right.right.name == "c"
    
    def test_not_precedence(self):
        """Тест приоритета оператора NOT"""
        result = self.parser.parse("NOT tag:a AND tag:b")
        
        # Должно быть: (NOT tag:a) AND tag:b
        assert isinstance(result, BinaryCondition)
        assert result.operator == ConditionType.AND
        
        assert isinstance(result.left, NotCondition)
        assert isinstance(result.left.condition, TagCondition)
        assert result.left.condition.name == "a"
        
        assert isinstance(result.right, TagCondition)
        assert result.right.name == "b"
    
    def test_grouping_with_parentheses(self):
        """Тест группировки в скобках"""
        result = self.parser.parse("(tag:a OR tag:b) AND tag:c")
        
        # Должно быть: (tag:a OR tag:b) AND tag:c
        assert isinstance(result, BinaryCondition)
        assert result.operator == ConditionType.AND
        
        assert isinstance(result.left, GroupCondition)
        group_content = result.left.condition
        assert isinstance(group_content, BinaryCondition)
        assert group_content.operator == ConditionType.OR
        
        assert isinstance(result.right, TagCondition)
        assert result.right.name == "c"
    
    def test_nested_grouping(self):
        """Тест вложенных скобок"""
        result = self.parser.parse("((tag:a))")
        
        assert isinstance(result, GroupCondition)
        assert isinstance(result.condition, GroupCondition)
        assert isinstance(result.condition.condition, TagCondition)
        assert result.condition.condition.name == "a"
    
    def test_multiple_and_operators(self):
        """Тест множественных операторов AND (левая ассоциативность)"""
        result = self.parser.parse("tag:a AND tag:b AND tag:c")
        
        # Должно быть: (tag:a AND tag:b) AND tag:c
        assert isinstance(result, BinaryCondition)
        assert result.operator == ConditionType.AND
        
        assert isinstance(result.left, BinaryCondition)
        assert result.left.operator == ConditionType.AND
        assert isinstance(result.left.left, TagCondition)
        assert result.left.left.name == "a"
        assert isinstance(result.left.right, TagCondition)
        assert result.left.right.name == "b"
        
        assert isinstance(result.right, TagCondition)
        assert result.right.name == "c"
    
    def test_multiple_not_operators(self):
        """Тест множественных операторов NOT (правая ассоциативность)"""
        result = self.parser.parse("NOT NOT tag:a")
        
        # Должно быть: NOT (NOT tag:a)
        assert isinstance(result, NotCondition)
        assert isinstance(result.condition, NotCondition)
        assert isinstance(result.condition.condition, TagCondition)
        assert result.condition.condition.name == "a"
    
    def test_complex_expression(self):
        """Тест сложного выражения с различными операторами"""
        result = self.parser.parse("tag:python AND (NOT tag:deprecated OR scope:local)")
        
        assert isinstance(result, BinaryCondition)
        assert result.operator == ConditionType.AND
        
        # Левая часть
        assert isinstance(result.left, TagCondition)
        assert result.left.name == "python"
        
        # Правая часть - группа
        assert isinstance(result.right, GroupCondition)
        group = result.right.condition
        assert isinstance(group, BinaryCondition)
        assert group.operator == ConditionType.OR
        
        # NOT tag:deprecated
        assert isinstance(group.left, NotCondition)
        assert isinstance(group.left.condition, TagCondition)
        assert group.left.condition.name == "deprecated"
        
        # scope:local
        assert isinstance(group.right, ScopeCondition)
        assert group.right.scope_type == "local"
    
    def test_syntax_errors(self):
        """Тест различных синтаксических ошибок"""
        
        # Отсутствует двоеточие после tag
        with pytest.raises(ParseError, match="Expected ':' after 'tag'"):
            self.parser.parse("tag python")
        
        # Отсутствует имя тега
        with pytest.raises(ParseError, match="Expected tag name"):
            self.parser.parse("tag:")
        
        # Отсутствует закрывающая скобка
        with pytest.raises(ParseError, match="Expected '\\)'"):
            self.parser.parse("(tag:python")
        
        # Неожиданный токен
        with pytest.raises(ParseError, match="Unexpected token"):
            self.parser.parse("AND tag:python")
        
        # Неожиданный конец выражения
        with pytest.raises(ParseError, match="Unexpected end of expression"):
            self.parser.parse("tag:python AND")
    
    def test_whitespace_handling(self):
        """Тест обработки пробелов"""
        result1 = self.parser.parse("tag:python")
        result2 = self.parser.parse("  tag  :  python  ")
        result3 = self.parser.parse("tag\t:\tpython")
        
        # Все варианты должны дать одинаковый результат
        assert isinstance(result1, TagCondition)
        assert isinstance(result2, TagCondition)
        assert isinstance(result3, TagCondition)
        
        assert result1.name == result2.name == result3.name == "python"
    
    def test_string_representation(self):
        """Тест строкового представления условий"""
        # Проверяем, что парсер может разобрать результат str()
        
        original = "tag:python AND NOT tag:deprecated"
        parsed = self.parser.parse(original)
        
        # Строковое представление может отличаться форматированием
        str_repr = str(parsed)
        reparsed = self.parser.parse(str_repr)
        
        # Но должно иметь ту же семантику
        assert type(parsed) == type(reparsed)
        if isinstance(parsed, BinaryCondition) and isinstance(reparsed, BinaryCondition):
            assert parsed.operator == reparsed.operator