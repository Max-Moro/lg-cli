"""
Тесты для вычислителя условий.
"""

import pytest

from lg.conditions.evaluator import ConditionEvaluator, evaluate_condition_string
from lg.conditions.parser import ConditionParser
from lg.run_context import ConditionContext


class TestConditionEvaluator:
    
    def setup_method(self):
        self.parser = ConditionParser()
        
        # Создаем тестовый контекст
        self.context = ConditionContext(
            active_tags={"python", "tests", "minimal"},
            tagsets={
                "language": {"python", "javascript", "typescript"},
                "feature": {"auth", "api", "ui"},
                "empty_set": set()
            },
            current_scope="local",
        )
        
        self.evaluator = ConditionEvaluator(self.context)
    
    def test_simple_tag_conditions(self):
        """Тест простых условий тегов"""
        
        # Активный тег
        condition = self.parser.parse("tag:python")
        assert self.evaluator.evaluate(condition) is True
        
        # Неактивный тег  
        condition = self.parser.parse("tag:javascript")
        assert self.evaluator.evaluate(condition) is False
        
        # Другие активные теги
        condition = self.parser.parse("tag:tests")
        assert self.evaluator.evaluate(condition) is True
        
        condition = self.parser.parse("tag:minimal")
        assert self.evaluator.evaluate(condition) is True
    
    def test_tagset_conditions(self):
        """Тест условий наборов тегов"""
        
        # Указанный тег активен в наборе
        condition = self.parser.parse("TAGSET:language:python")
        assert self.evaluator.evaluate(condition) is True
        
        # Указанный тег не активен, но другие из набора активны
        condition = self.parser.parse("TAGSET:language:javascript")
        assert self.evaluator.evaluate(condition) is False
        
        # Ни один тег из набора не активен
        condition = self.parser.parse("TAGSET:feature:auth")
        assert self.evaluator.evaluate(condition) is True
        
        condition = self.parser.parse("TAGSET:feature:api")
        assert self.evaluator.evaluate(condition) is True
        
        # Пустой набор тегов
        condition = self.parser.parse("TAGSET:empty_set:anything")
        assert self.evaluator.evaluate(condition) is True
    
    def test_scope_conditions(self):
        """Тест условий скоупов"""
        
        # Текущий скоуп = local
        condition = self.parser.parse("scope:local")
        assert self.evaluator.evaluate(condition) is True
        
        condition = self.parser.parse("scope:parent")
        assert self.evaluator.evaluate(condition) is False
        
        # Изменим скоуп
        context_parent = ConditionContext(
            active_tags=set(),
            tagsets={},
            current_scope="parent",
        )
        evaluator_parent = ConditionEvaluator(context_parent)
        
        condition = self.parser.parse("scope:local")
        assert evaluator_parent.evaluate(condition) is False
        
        condition = self.parser.parse("scope:parent")
        assert evaluator_parent.evaluate(condition) is True
    
    def test_not_conditions(self):
        """Тест условий отрицания"""
        
        # NOT активного тега
        condition = self.parser.parse("NOT tag:python")
        assert self.evaluator.evaluate(condition) is False
        
        # NOT неактивного тега
        condition = self.parser.parse("NOT tag:javascript")
        assert self.evaluator.evaluate(condition) is True
        
        # Двойное отрицание
        condition = self.parser.parse("NOT NOT tag:python")
        assert self.evaluator.evaluate(condition) is True
        
        condition = self.parser.parse("NOT NOT tag:javascript")
        assert self.evaluator.evaluate(condition) is False
    
    def test_and_conditions(self):
        """Тест условий И"""
        
        # Оба тега активны
        condition = self.parser.parse("tag:python AND tag:tests")
        assert self.evaluator.evaluate(condition) is True
        
        # Один тег активен, другой нет
        condition = self.parser.parse("tag:python AND tag:javascript")
        assert self.evaluator.evaluate(condition) is False
        
        # Оба тега неактивны
        condition = self.parser.parse("tag:javascript AND tag:java")
        assert self.evaluator.evaluate(condition) is False
        
        # Тройное И
        condition = self.parser.parse("tag:python AND tag:tests AND tag:minimal")
        assert self.evaluator.evaluate(condition) is True
        
        condition = self.parser.parse("tag:python AND tag:tests AND tag:javascript")
        assert self.evaluator.evaluate(condition) is False
    
    def test_or_conditions(self):
        """Тест условий ИЛИ"""
        
        # Оба тега активны
        condition = self.parser.parse("tag:python OR tag:tests")
        assert self.evaluator.evaluate(condition) is True
        
        # Один тег активен, другой нет
        condition = self.parser.parse("tag:python OR tag:javascript")
        assert self.evaluator.evaluate(condition) is True
        
        # Оба тега неактивны
        condition = self.parser.parse("tag:javascript OR tag:java")
        assert self.evaluator.evaluate(condition) is False
        
        # Тройное ИЛИ
        condition = self.parser.parse("tag:javascript OR tag:java OR tag:python")
        assert self.evaluator.evaluate(condition) is True
        
        condition = self.parser.parse("tag:javascript OR tag:java OR tag:go")
        assert self.evaluator.evaluate(condition) is False
    
    def test_operator_precedence_evaluation(self):
        """Тест приоритета операторов при вычислении"""
        
        # tag:python OR tag:javascript AND tag:tests
        # Должно быть: tag:python OR (tag:javascript AND tag:tests)
        # python=True, javascript=False, tests=True
        # Результат: True OR (False AND True) = True OR False = True
        condition = self.parser.parse("tag:python OR tag:javascript AND tag:tests")
        assert self.evaluator.evaluate(condition) is True
        
        # tag:javascript OR tag:go AND tag:tests  
        # Результат: False OR (False AND True) = False OR False = False
        condition = self.parser.parse("tag:javascript OR tag:go AND tag:tests")
        assert self.evaluator.evaluate(condition) is False
    
    def test_grouping_evaluation(self):
        """Тест вычисления с группировкой в скобках"""
        
        # (tag:python OR tag:javascript) AND tag:tests
        # (True OR False) AND True = True AND True = True
        condition = self.parser.parse("(tag:python OR tag:javascript) AND tag:tests")
        assert self.evaluator.evaluate(condition) is True
        
        # (tag:javascript OR tag:go) AND tag:tests
        # (False OR False) AND True = False AND True = False  
        condition = self.parser.parse("(tag:javascript OR tag:go) AND tag:tests")
        assert self.evaluator.evaluate(condition) is False
        
        # tag:python AND (tag:tests OR tag:javascript)
        # True AND (True OR False) = True AND True = True
        condition = self.parser.parse("tag:python AND (tag:tests OR tag:javascript)")
        assert self.evaluator.evaluate(condition) is True
    
    def test_complex_expressions(self):
        """Тест сложных выражений"""
        
        # tag:python AND (NOT tag:deprecated OR scope:local)
        # python=True, deprecated=False, scope:local=True
        # True AND (NOT False OR True) = True AND (True OR True) = True AND True = True
        condition = self.parser.parse("tag:python AND (NOT tag:deprecated OR scope:local)")
        assert self.evaluator.evaluate(condition) is True
        
        # NOT (tag:javascript OR tag:go) AND tag:python
        # NOT (False OR False) AND True = NOT False AND True = True AND True = True
        condition = self.parser.parse("NOT (tag:javascript OR tag:go) AND tag:python")
        assert self.evaluator.evaluate(condition) is True
        
        # TAGSET:language:javascript OR (tag:python AND tag:tests)
        # False OR (True AND True) = False OR True = True
        condition = self.parser.parse("TAGSET:language:javascript OR (tag:python AND tag:tests)")
        assert self.evaluator.evaluate(condition) is True
    
    def test_short_circuit_evaluation(self):
        """Тест короткого вычисления"""
        
        # Создаем контекст, который будет вызывать ошибку при обращении к неизвестному тегу
        class StrictContext(ConditionContext):
            def is_tag_active(self, tag_name: str) -> bool:
                if tag_name not in {"python", "tests"}:
                    raise ValueError(f"Unknown tag: {tag_name}")
                return tag_name in {"python", "tests"}
        
        strict_context = StrictContext(active_tags={"python", "tests"})
        strict_evaluator = ConditionEvaluator(strict_context)
        
        # tag:python OR tag:unknown_tag
        # Первый операнд True, второй не должен вычисляться
        condition = self.parser.parse("tag:python OR tag:unknown_tag")
        assert strict_evaluator.evaluate(condition) is True
        
        # tag:unknown_tag AND tag:python
        # Первый операнд вызовет ошибку
        condition = self.parser.parse("tag:unknown_tag AND tag:python")
        with pytest.raises(ValueError, match="Unknown tag"):
            strict_evaluator.evaluate(condition)
    
    def test_evaluate_condition_string_function(self):
        """Тест удобной функции evaluate_condition_string"""
        
        # Успешное вычисление
        result = evaluate_condition_string("tag:python AND tag:tests", self.context)
        assert result is True
        
        result = evaluate_condition_string("tag:javascript", self.context)
        assert result is False
        
        # Ошибка парсинга
        with pytest.raises(Exception):  # ParseError или ValueError
            evaluate_condition_string("invalid syntax", self.context)
    
    def test_empty_context(self):
        """Тест с пустым контекстом"""
        empty_context = ConditionContext()
        empty_evaluator = ConditionEvaluator(empty_context)
        
        # Все теги неактивны
        condition = self.parser.parse("tag:python")
        assert empty_evaluator.evaluate(condition) is False
        
        # NOT должен работать
        condition = self.parser.parse("NOT tag:python")
        assert empty_evaluator.evaluate(condition) is True
        
        # Пустые наборы тегов
        condition = self.parser.parse("TAGSET:language:python")
        assert empty_evaluator.evaluate(condition) is True  # Пустой набор всегда True
    
    def test_unknown_tagset(self):
        """Тест с неизвестным набором тегов"""
        
        # Неизвестный набор должен вести себя как пустой
        condition = self.parser.parse("TAGSET:unknown_set:python")
        assert self.evaluator.evaluate(condition) is True
    
    def test_case_sensitivity(self):
        """Тест чувствительности к регистру"""
        
        # Теги чувствительны к регистру
        condition = self.parser.parse("tag:Python")  # С заглавной P
        assert self.evaluator.evaluate(condition) is False  # python с маленькой p активен
        
        condition = self.parser.parse("tag:python")  # С маленькой p
        assert self.evaluator.evaluate(condition) is True