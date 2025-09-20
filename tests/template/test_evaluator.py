"""Тесты для оценщика условий шаблонов TemplateConditionEvaluator."""
import pytest

from lg.conditions.model import TagCondition, TagSetCondition
from lg.run_context import ConditionContext
from lg.template.evaluator import (
    TemplateConditionEvaluator,
    TemplateEvaluationError,
    create_template_evaluator,
    evaluate_simple_condition
)


class TestTemplateConditionEvaluator:
    """Основные тесты для TemplateConditionEvaluator."""

    def test_create_evaluator(self):
        """Создание оценщика с контекстом."""
        context = ConditionContext(
            active_tags={"debug", "test"}, 
            tagsets={"lang": {"java", "python"}},
            origin="self"
        )
        
        evaluator = TemplateConditionEvaluator(context)
        
        assert evaluator.condition_context == context
        assert evaluator.condition_context.active_tags == {"debug", "test"}
        assert evaluator.get_tagsets() == {"lang": {"java", "python"}}

    def test_evaluate_tag_condition_true(self):
        """Оценка условия тега - положительный результат."""
        context = ConditionContext(
            active_tags={"debug", "test"}, 
            tagsets={},
            origin="self"
        )
        evaluator = TemplateConditionEvaluator(context)
        
        # Создаем условие "debug"
        condition = TagCondition("debug")
        result = evaluator.evaluate(condition)
        
        assert result is True

    def test_evaluate_tag_condition_false(self):
        """Оценка условия тега - отрицательный результат."""
        context = ConditionContext(
            active_tags={"debug", "test"}, 
            tagsets={},
            origin="self"
        )
        evaluator = TemplateConditionEvaluator(context)
        
        # Создаем условие "production"
        condition = TagCondition("production")
        result = evaluator.evaluate(condition)
        
        assert result is False

    def test_evaluate_tagset_condition_true(self):
        """Оценка условия набора тегов - положительный результат."""
        context = ConditionContext(
            active_tags={"debug"}, 
            tagsets={"lang": {"java", "python"}},
            origin="self"
        )
        evaluator = TemplateConditionEvaluator(context)
        
        # Создаем условие "lang:java"
        condition = TagSetCondition("lang", "java")
        result = evaluator.evaluate(condition)
        
        assert result is True

    def test_evaluate_tagset_condition_false(self):
        """Оценка условия набора тегов - отрицательный результат."""
        context = ConditionContext(
            active_tags={"debug", "java"}, # java активен в наборе lang
            tagsets={"lang": {"java", "python"}},
            origin="self"
        )
        evaluator = TemplateConditionEvaluator(context)
        
        # Создаем условие "lang:cpp" - поскольку java активен, только java вернет True
        condition = TagSetCondition("lang", "python")
        result = evaluator.evaluate(condition)
        
        assert result is False

    def test_evaluate_condition_text(self):
        """Оценка условия из текстового представления."""
        context = ConditionContext(
            active_tags={"debug", "test"}, 
            tagsets={"lang": {"java", "python"}},
            origin="self"
        )
        evaluator = TemplateConditionEvaluator(context)
        
        # Простое условие тега
        assert evaluator.evaluate_condition_text("tag:debug") is True
        assert evaluator.evaluate_condition_text("tag:production") is False
        
        # Условие набора тегов (ни один тег из наборов не активен - всегда True)
        assert evaluator.evaluate_condition_text("TAGSET:lang:java") is True
        assert evaluator.evaluate_condition_text("TAGSET:lang:cpp") is True

    def test_evaluate_complex_condition_text(self):
        """Оценка сложных условий из текста."""
        context = ConditionContext(
            active_tags={"debug", "test"}, 
            tagsets={"lang": {"java"}, "env": {"dev", "staging"}},
            origin="self"
        )
        evaluator = TemplateConditionEvaluator(context)
        
        # Логические операции
        assert evaluator.evaluate_condition_text("tag:debug AND tag:test") is True
        assert evaluator.evaluate_condition_text("tag:debug AND tag:production") is False
        assert evaluator.evaluate_condition_text("tag:debug OR tag:production") is True
        assert evaluator.evaluate_condition_text("NOT tag:production") is True
        assert evaluator.evaluate_condition_text("NOT tag:debug") is False
        
        # Смешанные условия (наборы без активных тегов всегда True)
        assert evaluator.evaluate_condition_text("tag:debug AND TAGSET:lang:java") is True
        assert evaluator.evaluate_condition_text("tag:debug AND TAGSET:env:prod") is True

    def test_evaluate_condition_text_with_active_tagsets(self):
        """Оценка условий из текста с активными тегами в наборах."""
        context = ConditionContext(
            active_tags={"debug", "java", "dev"},
            tagsets={"lang": {"java", "python"}, "env": {"dev", "staging"}},
            origin="self"
        )
        evaluator = TemplateConditionEvaluator(context)
        
        # Когда java активен в наборе lang
        assert evaluator.evaluate_condition_text("TAGSET:lang:java") is True
        assert evaluator.evaluate_condition_text("TAGSET:lang:python") is False
        
        # Когда dev активен в наборе env
        assert evaluator.evaluate_condition_text("TAGSET:env:dev") is True
        assert evaluator.evaluate_condition_text("TAGSET:env:staging") is False
        
        # Смешанные условия
        assert evaluator.evaluate_condition_text("tag:debug AND TAGSET:lang:java") is True
        assert evaluator.evaluate_condition_text("tag:debug AND TAGSET:lang:python") is False

    def test_update_context(self):
        """Обновление контекста оценщика."""
        initial_context = ConditionContext(
            active_tags={"debug"}, 
            tagsets={},
            origin="self"
        )
        evaluator = TemplateConditionEvaluator(initial_context)
        
        # Проверяем начальное состояние
        assert evaluator.is_tag_active("debug") is True
        assert evaluator.is_tag_active("production") is False
        
        # Обновляем контекст
        new_context = ConditionContext(
            active_tags={"production"}, 
            tagsets={},
            origin="self"
        )
        evaluator.update_context(new_context)
        
        # Проверяем обновленное состояние
        assert evaluator.is_tag_active("debug") is False
        assert evaluator.is_tag_active("production") is True

    def test_is_tag_active(self):
        """Проверка активности тегов."""
        context = ConditionContext(
            active_tags={"debug", "test", "java"}, 
            tagsets={},
            origin="self"
        )
        evaluator = TemplateConditionEvaluator(context)
        
        assert evaluator.is_tag_active("debug") is True
        assert evaluator.is_tag_active("test") is True
        assert evaluator.is_tag_active("java") is True
        assert evaluator.is_tag_active("production") is False
        assert evaluator.is_tag_active("cpp") is False

    def test_is_tagset_condition_met(self):
        """Проверка условий набора тегов."""
        context = ConditionContext(
            active_tags={"debug"}, 
            tagsets={
                "lang": {"java", "python", "cpp"},
                "env": {"dev", "staging", "prod"}
            },
            origin="self"
        )
        evaluator = TemplateConditionEvaluator(context)
        
        # Наборы без активных тегов - всегда True (федеральная логика)
        assert evaluator.is_tagset_condition_met("lang", "java") is True
        assert evaluator.is_tagset_condition_met("lang", "python") is True
        assert evaluator.is_tagset_condition_met("lang", "rust") is True  # Ни один тег из lang не активен
        assert evaluator.is_tagset_condition_met("env", "dev") is True
        assert evaluator.is_tagset_condition_met("env", "local") is True  # Ни один тег из env не активен
        
        # Несуществующие наборы - всегда True
        assert evaluator.is_tagset_condition_met("unknown", "tag") is True

    def test_is_tagset_condition_met_with_active_tags(self):
        """Проверка условий набора тегов с активными тегами в наборах."""
        context = ConditionContext(
            active_tags={"java", "dev"}, 
            tagsets={
                "lang": {"java", "python", "cpp"},
                "env": {"dev", "staging", "prod"}
            },
            origin="self"
        )
        evaluator = TemplateConditionEvaluator(context)
        
        # java активен в наборе lang - условие истинно только для java
        assert evaluator.is_tagset_condition_met("lang", "java") is True
        assert evaluator.is_tagset_condition_met("lang", "python") is False
        assert evaluator.is_tagset_condition_met("lang", "cpp") is False
        
        # dev активен в наборе env - условие истинно только для dev
        assert evaluator.is_tagset_condition_met("env", "dev") is True
        assert evaluator.is_tagset_condition_met("env", "staging") is False
        assert evaluator.is_tagset_condition_met("env", "prod") is False


class TestTemplateEvaluationError:
    """Тесты для TemplateEvaluationError."""

    def test_create_error(self):
        """Создание ошибки оценки шаблона."""
        error = TemplateEvaluationError(
            "Invalid condition", 
            "tag:unknown", 
            line=5, 
            column=10
        )
        
        assert "Invalid condition" in str(error)
        assert "tag:unknown" in str(error)
        assert "5:10" in str(error)
        assert error.condition_text == "tag:unknown"
        assert error.line == 5
        assert error.column == 10

    def test_create_error_minimal(self):
        """Создание ошибки с минимальными параметрами."""
        error = TemplateEvaluationError("Test error", "condition")
        
        assert "Test error" in str(error)
        assert "condition" in str(error)
        assert "0:0" in str(error)


class TestCreateTemplateEvaluator:
    """Тесты для функции create_template_evaluator."""

    def test_create_simple_evaluator(self):
        """Создание простого оценщика."""
        evaluator = create_template_evaluator(
            active_tags={"debug", "test"},
            active_modes={"java": "class"},
            tagsets={"lang": {"java", "python"}}
        )
        
        assert evaluator.condition_context.active_tags == {"debug", "test"}
        assert evaluator.get_tagsets() == {"lang": {"java", "python"}}

    def test_create_evaluator_with_scope(self):
        """Создание оценщика с указанием скоупа."""
        evaluator = create_template_evaluator(
            active_tags={"debug"},
            active_modes={},
            tagsets={},
            origin="parent"
        )
        
        assert evaluator.condition_context.origin == "parent"

    def test_create_evaluator_empty(self):
        """Создание оценщика с пустыми параметрами."""
        evaluator = create_template_evaluator(
            active_tags=set(),
            active_modes={},
            tagsets={}
        )
        
        assert evaluator.condition_context.active_tags == set()
        assert evaluator.get_tagsets() == {}


class TestEvaluateSimpleCondition:
    """Тесты для функции evaluate_simple_condition."""

    def test_evaluate_simple_tag_condition(self):
        """Простая оценка условия тега."""
        result = evaluate_simple_condition(
            "tag:debug",
            active_tags={"debug", "test"}
        )
        assert result is True
        
        result = evaluate_simple_condition(
            "tag:production",
            active_tags={"debug", "test"}
        )
        assert result is False

    def test_evaluate_simple_tagset_condition(self):
        """Простая оценка условия набора тегов."""
        result = evaluate_simple_condition(
            "TAGSET:lang:java",
            active_tags={"debug"},
            tagsets={"lang": {"java", "python"}}
        )
        assert result is True
        
        result = evaluate_simple_condition(
            "TAGSET:lang:cpp",
            active_tags={"debug"},
            tagsets={"lang": {"java", "python"}}
        )
        assert result is True  # Ни один тег из lang не активен, поэтому True

    def test_evaluate_simple_complex_condition(self):
        """Простая оценка сложного условия."""
        result = evaluate_simple_condition(
            "tag:debug AND TAGSET:lang:java",
            active_tags={"debug", "test"},
            tagsets={"lang": {"java", "python"}}
        )
        assert result is True
        
        result = evaluate_simple_condition(
            "tag:debug AND TAGSET:lang:cpp",
            active_tags={"debug", "test"},
            tagsets={"lang": {"java", "python"}}
        )
        assert result is True  # debug=True AND (ни один тег из lang не активен)=True

    def test_evaluate_simple_without_tagsets(self):
        """Оценка без наборов тегов."""
        result = evaluate_simple_condition(
            "tag:debug OR tag:test",
            active_tags={"debug"}
        )
        assert result is True
        
        result = evaluate_simple_condition(
            "tag:production",
            active_tags={"debug"}
        )
        assert result is False

    def test_evaluate_simple_error_handling(self):
        """Обработка ошибок в простой оценке."""
        from lg.conditions.parser import ParseError
        with pytest.raises(ParseError):
            evaluate_simple_condition(
                "invalid syntax",
                active_tags={"debug"}
            )


class TestTemplateEvaluatorIntegration:
    """Интеграционные тесты для оценщика шаблонов."""

    def test_real_world_scenario(self):
        """Сценарий реального использования."""
        # Имитируем контекст Java-проекта
        evaluator = create_template_evaluator(
            active_tags={"debug", "unit_test", "spring"},
            active_modes={"java": "class", "test": "junit"},
            tagsets={
                "lang": {"java", "kotlin", "scala"},
                "framework": {"spring", "hibernate", "junit"},
                "env": {"dev", "test", "staging", "prod"}
            }
        )
        
        # Проверяем различные условия
        assert evaluator.evaluate_condition_text("tag:debug") is True
        assert evaluator.evaluate_condition_text("tag:production") is False
        
        assert evaluator.evaluate_condition_text("TAGSET:lang:java") is True
        assert evaluator.evaluate_condition_text("TAGSET:lang:python") is True  # Ни один тег из lang не активен
        
        assert evaluator.evaluate_condition_text("TAGSET:framework:spring") is True
        assert evaluator.evaluate_condition_text("TAGSET:framework:django") is False
        
        # Сложные условия
        assert evaluator.evaluate_condition_text("tag:debug AND TAGSET:lang:java") is True
        assert evaluator.evaluate_condition_text("tag:debug AND TAGSET:framework:spring AND TAGSET:lang:java") is True
        assert evaluator.evaluate_condition_text("tag:production OR (tag:debug AND TAGSET:lang:java)") is True
        assert evaluator.evaluate_condition_text("TAGSET:env:dev AND NOT tag:production") is True

    def test_mode_context_switching(self):
        """Переключение контекста режимов."""
        # Начальный контекст - обычный код
        evaluator = create_template_evaluator(
            active_tags={"debug"},
            active_modes={"java": "class"},
            tagsets={"lang": {"java"}}
        )
        
        assert evaluator.evaluate_condition_text("tag:debug AND TAGSET:lang:java") is True
        
        # Переключаемся в контекст тестов
        new_context = ConditionContext(
            active_tags={"debug", "test"},
            tagsets={"lang": {"java"}, "test": {"unit", "integration"}},
            origin="self"
        )
        evaluator.update_context(new_context)
        
        assert evaluator.evaluate_condition_text("tag:debug AND tag:test") is True
        assert evaluator.evaluate_condition_text("TAGSET:lang:java AND TAGSET:test:unit") is True

    def test_nested_conditions_evaluation(self):
        """Оценка вложенных условий."""
        evaluator = create_template_evaluator(
            active_tags={"debug", "api", "web"},
            active_modes={},
            tagsets={
                "lang": {"java", "javascript"},
                "layer": {"controller", "service", "repository"},
                "protocol": {"http", "grpc", "websocket"}
            }
        )
        
        # Проверяем вложенные логические условия
        complex_condition = "(tag:debug OR tag:production) AND (TAGSET:lang:java OR TAGSET:lang:javascript) AND TAGSET:layer:controller"
        assert evaluator.evaluate_condition_text(complex_condition) is True
        
        complex_condition = "(tag:staging AND tag:production) OR (TAGSET:lang:java AND TAGSET:layer:service)"
        assert evaluator.evaluate_condition_text(complex_condition) is True
        
        # Условие с отрицанием
        complex_condition = "NOT (tag:production AND TAGSET:layer:repository) AND TAGSET:protocol:http"
        assert evaluator.evaluate_condition_text(complex_condition) is True