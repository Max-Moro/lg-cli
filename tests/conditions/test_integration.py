"""
Интеграционные тесты для системы условий.

Тестирует полный пайплайн: парсинг -> вычисление,
а также интеграцию с ConditionContext.
"""

import pytest

from lg.conditions import (
    ConditionParser,
    ConditionEvaluator,
    evaluate_condition_string,
)
from lg.run_context import ConditionContext


class TestConditionsIntegration:
    
    def test_end_to_end_pipeline(self):
        """Тест полного пайплайна обработки условий"""
        
        # Настройка контекста
        context = ConditionContext(
            active_tags={"python", "tests", "api"},
            tagsets={
                "language": {"python", "javascript", "go"},
                "component": {"api", "ui", "db"},
                "stage": {"dev", "prod"}
            },
            current_scope="local"
        )
        
        # Набор тестовых случаев: (условие, ожидаемый результат)
        test_cases = [
            # Простые условия
            ("tag:python", True),
            ("tag:javascript", False),
            
            # Условия наборов тегов
            ("TAGSET:language:python", True),      # активен указанный тег
            ("TAGSET:language:javascript", False), # активен другой тег из набора
            ("TAGSET:stage:dev", True),           # ни один тег из набора не активен
            
            # Скоупы
            ("scope:local", True),
            ("scope:parent", False),
            
            # Логические операторы
            ("tag:python AND tag:tests", True),
            ("tag:python AND tag:javascript", False),
            ("tag:python OR tag:javascript", True),
            ("tag:javascript OR tag:go", False),
            
            # Отрицание
            ("NOT tag:javascript", True),
            ("NOT tag:python", False),
            ("NOT NOT tag:python", True),
            
            # Группировка
            ("(tag:python OR tag:javascript) AND tag:tests", True),
            ("(tag:javascript OR tag:go) AND tag:tests", False),
            ("tag:python AND (tag:tests OR tag:javascript)", True),
            
            # Сложные выражения
            ("tag:python AND NOT tag:deprecated", True),
            ("TAGSET:language:python AND scope:local", True),
            ("NOT (tag:javascript OR tag:go) AND tag:api", True),
            (
                "tag:python AND (TAGSET:component:api OR scope:parent) AND NOT tag:deprecated",
                True
            ),
        ]
        
        parser = ConditionParser()
        evaluator = ConditionEvaluator(context)
        
        for condition_str, expected in test_cases:
            # Тестируем через парсер + вычислитель
            ast = parser.parse(condition_str)
            result = evaluator.evaluate(ast)
            assert result == expected, f"Failed for condition: {condition_str}"
            
            # Тестируем через удобную функцию
            result2 = evaluate_condition_string(condition_str, context)
            assert result2 == expected, f"Failed for condition (via function): {condition_str}"
    
    def test_context_methods(self):
        """Тест методов ConditionContext"""
        
        context = ConditionContext(
            active_tags={"python", "api", "minimal"},
            tagsets={
                "language": {"python", "javascript", "go"},
                "component": {"api", "ui", "db"},
                "empty": set()
            },
            current_scope="local"
        )
        
        # Тест is_tag_active
        assert context.is_tag_active("python") is True
        assert context.is_tag_active("javascript") is False
        assert context.is_tag_active("nonexistent") is False
        
        # Тест is_tagset_condition_met
        
        # Указанный тег активен в наборе
        assert context.is_tagset_condition_met("language", "python") is True
        
        # Указанный тег не активен, но другие из набора активны  
        assert context.is_tagset_condition_met("language", "javascript") is False
        
        # В наборе component активен тег api, поэтому условие истинно только для api
        assert context.is_tagset_condition_met("component", "ui") is False  # активен другой тег
        assert context.is_tagset_condition_met("component", "db") is False  # активен другой тег
        
        # Указанный тег активен в наборе (совпадение с активным)
        assert context.is_tagset_condition_met("component", "api") is True
        
        # Пустой набор
        assert context.is_tagset_condition_met("empty", "anything") is True
        
        # Несуществующий набор
        assert context.is_tagset_condition_met("nonexistent", "tag") is True  # несуществующий = пустой = True
        
        # Тест is_scope_condition_met
        assert context.is_scope_condition_met("local") is True
        assert context.is_scope_condition_met("parent") is False
        assert context.is_scope_condition_met("invalid") is False
    
    def test_context_edge_cases(self):
        """Тест граничных случаев контекста"""
        
        # Полностью пустой контекст
        empty_context = ConditionContext()
        
        assert empty_context.is_tag_active("anything") is False
        assert empty_context.is_tagset_condition_met("set", "tag") is True  # несуществующий набор = пустой = True
        assert empty_context.is_scope_condition_met("local") is False  # пустая строка != "local"
        
        # Контекст только с активными тегами
        tags_only_context = ConditionContext(active_tags={"python", "api"})
        
        assert tags_only_context.is_tag_active("python") is True
        assert tags_only_context.is_tagset_condition_met("nonexistent", "python") is True  # несуществующий набор
        
        # Контекст только с наборами тегов
        tagsets_only_context = ConditionContext(
            tagsets={"language": {"python", "go"}}
        )
        
        assert tagsets_only_context.is_tag_active("python") is False  # не активен
        assert tagsets_only_context.is_tagset_condition_met("language", "python") is True  # пустое пересечение
    
    def test_error_propagation(self):
        """Тест распространения ошибок через весь пайплайн"""
        
        context = ConditionContext()
        
        # Ошибки парсинга должны пробрасываться
        with pytest.raises(Exception):
            evaluate_condition_string("invalid syntax @@", context)
        
        with pytest.raises(Exception):
            evaluate_condition_string("tag:", context)  # неполное условие
        
        with pytest.raises(Exception):
            evaluate_condition_string("", context)  # пустое условие
    
    def test_whitespace_and_formatting(self):
        """Тест обработки различных вариантов форматирования"""
        
        context = ConditionContext(active_tags={"python", "tests"})
        
        # Различные варианты пробелов должны давать одинаковый результат
        variants = [
            "tag:python AND tag:tests",
            "tag:python  AND  tag:tests",
            " tag:python AND tag:tests ",
            "tag : python AND tag : tests",
            "\ttag:python\tAND\ttag:tests\t",
            "tag:python\nAND\ntag:tests"
        ]
        
        expected_result = evaluate_condition_string("tag:python AND tag:tests", context)
        
        for variant in variants:
            result = evaluate_condition_string(variant, context)
            assert result == expected_result, f"Failed for variant: {repr(variant)}"
    
    def test_complex_real_world_scenarios(self):
        """Тест сложных сценариев, похожих на реальные"""
        
        # Имитируем реальный контекст разработки
        context = ConditionContext(
            active_tags={"python", "backend", "api", "tests", "development"},
            tagsets={
                "language": {"python", "javascript", "typescript", "go"},
                "component": {"frontend", "backend", "api", "db"},
                "environment": {"development", "staging", "production"},
                "feature": {"auth", "payments", "notifications"}
            },
            current_scope="local"
        )
        
        scenarios = [
            # Показать код только для Python backend разработки
            (
                "tag:python AND tag:backend AND TAGSET:environment:development",
                True
            ),
            
            # Показать тесты только если они включены и это не продакшн
            (
                "tag:tests AND NOT TAGSET:environment:production",
                True
            ),
            
            # Показать API документацию только для API компонента или если это общие тесты
            (
                "TAGSET:component:api OR (tag:tests AND scope:local)",
                True
            ),
            
            # Скрыть экспериментальные фичи в продакшне
            (
                "NOT (tag:experimental AND TAGSET:environment:production)",
                True  # experimental не активен
            ),
            
            # Показать только релевантные для текущей разработки файлы
            (
                "(tag:python OR tag:javascript) AND "
                "(TAGSET:component:backend OR TAGSET:component:api) AND "
                "NOT tag:deprecated",
                True
            ),
        ]
        
        for condition_str, expected in scenarios:
            result = evaluate_condition_string(condition_str, context)
            assert result == expected, f"Failed for scenario: {condition_str}"
    
    def test_performance_with_complex_expressions(self):
        """Тест производительности с большими выражениями"""
        
        context = ConditionContext(
            active_tags={"tag1", "tag3", "tag5"},
            tagsets={
                f"set{i}": {f"tag{j}" for j in range(i, i+3)} 
                for i in range(1, 6)
            }
        )
        
        # Большое выражение с множественными условиями
        large_condition = " OR ".join([
            f"(tag:tag{i} AND TAGSET:set{i%5+1}:tag{i} AND scope:local)"
            for i in range(1, 21)
        ])
        
        # Должно работать без ошибок и в разумное время
        result = evaluate_condition_string(large_condition, context)
        assert isinstance(result, bool)
        
        # Тест с глубокой вложенностью
        nested_condition = "(" * 10 + "tag:tag1" + ")" * 10
        result = evaluate_condition_string(nested_condition, context)
        assert result is True