"""Тесты для контекста шаблонов TemplateContext."""
import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, Set
import warnings

from lg.template.context import TemplateContext, TemplateState, create_template_context
from lg.template.evaluator import TemplateConditionEvaluator
from lg.run_context import RunContext
from lg.config.adaptive_model import ModeOptions, ModesConfig, ModeSet, Mode, TagsConfig, TagSet, Tag
from lg.conditions.model import TagCondition


class TestTemplateState:
    """Тесты для TemplateState."""

    def test_create_template_state(self):
        """Создание состояния шаблона."""
        mode_options = ModeOptions()
        active_tags = {"debug", "test"}
        active_modes = {"java": "class", "test": "unit"}
        
        state = TemplateState(
            mode_options=mode_options,
            active_tags=active_tags,
            active_modes=active_modes
        )
        
        assert state.mode_options == mode_options
        assert state.active_tags == active_tags
        assert state.active_modes == active_modes

    def test_copy_template_state(self):
        """Копирование состояния шаблона."""
        mode_options = ModeOptions()
        active_tags = {"debug", "test"}
        active_modes = {"java": "class"}
        
        original = TemplateState(
            mode_options=mode_options,
            active_tags=active_tags,
            active_modes=active_modes
        )
        
        copy = original.copy()
        
        # Проверяем, что копия содержит те же данные
        assert copy.mode_options == original.mode_options
        assert copy.active_tags == original.active_tags
        assert copy.active_modes == original.active_modes
        
        # Проверяем, что копия независима от оригинала
        copy.active_tags.add("production")
        copy.active_modes["test"] = "integration"
        
        assert "production" not in original.active_tags
        assert "test" not in original.active_modes


class TestTemplateContext:
    """Основные тесты для TemplateContext."""

    def setup_method(self):
        """Настройка для каждого теста."""
        # Создаем mock объекты
        self.run_ctx = Mock(spec=RunContext)
        self.adaptive_loader = Mock()
        
        # Настраиваем базовые атрибуты
        self.run_ctx.adaptive_loader = self.adaptive_loader
        self.run_ctx.mode_options = ModeOptions()
        self.run_ctx.active_tags = {"debug", "test"}
        self.run_ctx.options = Mock()
        self.run_ctx.options.modes = {"java": "class"}

    def test_create_template_context(self):
        """Создание контекста шаблона."""
        context = TemplateContext(self.run_ctx)
        
        assert context.run_ctx == self.run_ctx
        assert context.adaptive_loader == self.adaptive_loader
        assert context.current_state.active_tags == {"debug", "test"}
        assert context.current_state.active_modes == {"java": "class"}
        assert context.state_stack == []

    def test_get_active_tags(self):
        """Получение активных тегов."""
        context = TemplateContext(self.run_ctx)
        
        active_tags = context.get_active_tags()
        
        assert active_tags == {"debug", "test"}
        # Проверяем, что возвращается копия, а не ссылка
        active_tags.add("production")
        assert "production" not in context.current_state.active_tags

    def test_get_active_modes(self):
        """Получение активных режимов."""
        context = TemplateContext(self.run_ctx)
        
        active_modes = context.get_active_modes()
        
        assert active_modes == {"java": "class"}
        # Проверяем, что возвращается копия
        active_modes["test"] = "unit"
        assert "test" not in context.current_state.active_modes

    def test_get_mode_options(self):
        """Получение опций режимов."""
        context = TemplateContext(self.run_ctx)
        
        mode_options = context.get_mode_options()
        
        assert mode_options == self.run_ctx.mode_options

    def test_is_in_mode_block_false(self):
        """Проверка нахождения в блоке режима - false."""
        context = TemplateContext(self.run_ctx)
        
        assert context.is_in_mode_block() is False
        assert context.get_nesting_level() == 0

    def test_add_extra_tag(self):
        """Добавление дополнительного тега."""
        context = TemplateContext(self.run_ctx)
        initial_tags = context.get_active_tags()
        
        context.add_extra_tag("production")
        
        assert "production" in context.current_state.active_tags
        assert context.current_state.active_tags == initial_tags | {"production"}

    def test_remove_tag(self):
        """Удаление тега."""
        context = TemplateContext(self.run_ctx)
        
        context.remove_tag("test")
        
        assert "test" not in context.current_state.active_tags
        assert context.current_state.active_tags == {"debug"}

    def test_remove_nonexistent_tag(self):
        """Удаление несуществующего тега."""
        context = TemplateContext(self.run_ctx)
        initial_tags = context.get_active_tags()
        
        context.remove_tag("nonexistent")
        
        assert context.get_active_tags() == initial_tags


class TestTemplateContextModeBlocks:
    """Тесты для работы с блоками режимов."""

    def setup_method(self):
        """Настройка для каждого теста."""
        # Создаем mock run_ctx
        self.run_ctx = Mock(spec=RunContext)
        self.adaptive_loader = Mock()
        
        self.run_ctx.adaptive_loader = self.adaptive_loader
        self.run_ctx.mode_options = ModeOptions()
        self.run_ctx.active_tags = {"debug"}
        self.run_ctx.options = Mock()
        self.run_ctx.options.modes = {"java": "class"}
        
        # Настраиваем mock конфигурации режимов
        self.setup_modes_config()

    def setup_modes_config(self):
        """Настройка конфигурации режимов."""
        # Создаем режим test:unit с тегами
        unit_mode = Mode(
            title="Unit testing mode",
            description="Unit testing mode",
            tags=["unit_test", "testing"]
        )
        
        integration_mode = Mode(
            title="Integration testing mode", 
            description="Integration testing mode",
            tags=["integration_test", "testing"]
        )
        
        # Создаем набор режимов test
        test_mode_set = ModeSet(
            title="Testing modes",
            modes={"unit": unit_mode, "integration": integration_mode}
        )
        
        # Создаем конфигурацию режимов
        modes_config = ModesConfig(
            mode_sets={"test": test_mode_set}
        )
        
        self.adaptive_loader.get_modes_config.return_value = modes_config

    def test_enter_mode_block_success(self):
        """Успешный вход в блок режима."""
        context = TemplateContext(self.run_ctx)
        initial_tags = context.get_active_tags().copy()
        
        context.enter_mode_block("test", "unit")
        
        # Проверяем, что состояние сохранено в стек
        assert len(context.state_stack) == 1
        assert context.is_in_mode_block() is True
        assert context.get_nesting_level() == 1
        
        # Проверяем, что режим активен
        assert context.current_state.active_modes["test"] == "unit"
        
        # Проверяем, что теги режима добавлены
        expected_tags = initial_tags | {"unit_test", "testing"}
        assert context.get_active_tags() == expected_tags

    def test_enter_mode_block_unknown_modeset(self):
        """Ошибка при входе в блок несуществующего набора режимов."""
        context = TemplateContext(self.run_ctx)
        
        with pytest.raises(ValueError, match="Unknown mode set 'unknown'"):
            context.enter_mode_block("unknown", "mode")

    def test_enter_mode_block_unknown_mode(self):
        """Ошибка при входе в блок несуществующего режима."""
        context = TemplateContext(self.run_ctx)
        
        with pytest.raises(ValueError, match="Unknown mode 'unknown' in mode set 'test'"):
            context.enter_mode_block("test", "unknown")

    def test_exit_mode_block_success(self):
        """Успешный выход из блока режима."""
        context = TemplateContext(self.run_ctx)
        initial_tags = context.get_active_tags().copy()
        initial_modes = context.get_active_modes().copy()
        
        # Входим в блок режима
        context.enter_mode_block("test", "unit")
        
        # Проверяем изменения
        assert context.get_active_tags() != initial_tags
        assert context.get_active_modes() != initial_modes
        
        # Выходим из блока
        context.exit_mode_block()
        
        # Проверяем восстановление состояния
        assert context.get_active_tags() == initial_tags
        assert context.get_active_modes() == initial_modes
        assert context.is_in_mode_block() is False
        assert context.get_nesting_level() == 0

    def test_exit_mode_block_empty_stack(self):
        """Ошибка при выходе из блока когда стек пуст."""
        context = TemplateContext(self.run_ctx)
        
        with pytest.raises(RuntimeError, match="No mode block to exit"):
            context.exit_mode_block()

    def test_nested_mode_blocks(self):
        """Тестирование вложенных блоков режимов."""
        context = TemplateContext(self.run_ctx)
        initial_state = (context.get_active_tags().copy(), context.get_active_modes().copy())
        
        # Первый уровень вложенности
        context.enter_mode_block("test", "unit")
        level1_state = (context.get_active_tags().copy(), context.get_active_modes().copy())
        assert context.get_nesting_level() == 1
        
        # Второй уровень вложенности
        context.enter_mode_block("test", "integration")
        level2_state = (context.get_active_tags().copy(), context.get_active_modes().copy())
        assert context.get_nesting_level() == 2
        
        # Проверяем, что состояния различаются
        assert level2_state != level1_state
        assert level1_state != initial_state
        
        # Выходим из второго уровня
        context.exit_mode_block()
        assert (context.get_active_tags(), context.get_active_modes()) == level1_state
        assert context.get_nesting_level() == 1
        
        # Выходим из первого уровня
        context.exit_mode_block()
        assert (context.get_active_tags(), context.get_active_modes()) == initial_state
        assert context.get_nesting_level() == 0


class TestTemplateContextConditionEvaluation:
    """Тесты для оценки условий в контексте шаблона."""

    def setup_method(self):
        """Настройка для каждого теста."""
        self.run_ctx = Mock(spec=RunContext)
        self.adaptive_loader = Mock()
        
        self.run_ctx.adaptive_loader = self.adaptive_loader
        self.run_ctx.mode_options = ModeOptions()
        self.run_ctx.active_tags = {"debug", "java"}
        self.run_ctx.options = Mock()
        self.run_ctx.options.modes = {}
        
        # Настраиваем mock для tagsets
        java_tag = Tag(title="Java")
        python_tag = Tag(title="Python")
        lang_tagset = TagSet(
            title="Languages",
            tags={"java": java_tag, "python": python_tag}
        )
        tags_config = TagsConfig(
            tag_sets={"lang": lang_tagset},
            global_tags={}
        )
        self.adaptive_loader.get_tags_config.return_value = tags_config

    def test_get_condition_evaluator(self):
        """Получение оценщика условий."""
        context = TemplateContext(self.run_ctx)
        
        evaluator = context.get_condition_evaluator()
        
        assert isinstance(evaluator, TemplateConditionEvaluator)
        assert evaluator.get_active_tags() == {"debug", "java"}

    def test_condition_evaluator_caching(self):
        """Кэширование оценщика условий."""
        context = TemplateContext(self.run_ctx)
        
        evaluator1 = context.get_condition_evaluator()
        evaluator2 = context.get_condition_evaluator()
        
        # Должен возвращать тот же объект
        assert evaluator1 is evaluator2

    def test_condition_evaluator_reset_on_tag_change(self):
        """Сброс оценщика при изменении тегов."""
        context = TemplateContext(self.run_ctx)
        
        evaluator1 = context.get_condition_evaluator()
        context.add_extra_tag("production")
        evaluator2 = context.get_condition_evaluator()
        
        # Должен создать новый оценщик
        assert evaluator1 is not evaluator2
        assert evaluator2.get_active_tags() == {"debug", "java", "production"}

    def test_evaluate_condition_text(self):
        """Оценка условия из текста."""
        context = TemplateContext(self.run_ctx)
        
        # Тестируем условие активного тега
        assert context.evaluate_condition_text("tag:debug") is True
        assert context.evaluate_condition_text("tag:java") is True
        assert context.evaluate_condition_text("tag:production") is False
        
        # Тестируем сложные условия
        assert context.evaluate_condition_text("tag:debug AND tag:java") is True
        assert context.evaluate_condition_text("tag:debug AND tag:production") is False

    def test_evaluate_condition_ast(self):
        """Оценка условия из AST."""
        context = TemplateContext(self.run_ctx)
        
        # Создаем AST условия
        condition = TagCondition("debug")
        
        assert context.evaluate_condition(condition) is True
        
        # Тестируем с неактивным тегом
        condition = TagCondition("production")
        assert context.evaluate_condition(condition) is False


class TestTemplateContextManager:
    """Тесты для использования TemplateContext как контекстного менеджера."""

    def setup_method(self):
        """Настройка для каждого теста."""
        self.run_ctx = Mock(spec=RunContext)
        self.adaptive_loader = Mock()
        
        self.run_ctx.adaptive_loader = self.adaptive_loader
        self.run_ctx.mode_options = ModeOptions()
        self.run_ctx.active_tags = {"debug"}
        self.run_ctx.options = Mock()
        self.run_ctx.options.modes = {}

    def test_context_manager_clean_exit(self):
        """Чистый выход из контекстного менеджера."""
        with TemplateContext(self.run_ctx) as context:
            assert isinstance(context, TemplateContext)
        
        # Не должно быть предупреждений
        # (проверяется отсутствием исключений)

    def test_context_manager_with_unclosed_blocks(self):
        """Выход из контекстного менеджера с незакрытыми блоками."""
        # Настраиваем конфигурацию режимов для теста
        unit_mode = Mode(title="Unit mode", description="Unit mode", tags=["unit"])
        test_mode_set = ModeSet(title="Test modes", modes={"unit": unit_mode})
        modes_config = ModesConfig(mode_sets={"test": test_mode_set})
        self.adaptive_loader.get_modes_config.return_value = modes_config
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            with TemplateContext(self.run_ctx) as context:
                context.enter_mode_block("test", "unit")
                # Умышленно не закрываем блок
            
            # Проверяем, что было выдано предупреждение
            assert len(w) == 1
            assert issubclass(w[0].category, RuntimeWarning)
            assert "unclosed mode blocks" in str(w[0].message)


class TestCreateTemplateContext:
    """Тесты для функции create_template_context."""

    def test_create_template_context_function(self):
        """Тестирование функции создания контекста."""
        run_ctx = Mock(spec=RunContext)
        adaptive_loader = Mock()
        
        run_ctx.adaptive_loader = adaptive_loader
        run_ctx.mode_options = ModeOptions()
        run_ctx.active_tags = {"test"}
        run_ctx.options = Mock()
        run_ctx.options.modes = {}
        
        context = create_template_context(run_ctx)
        
        assert isinstance(context, TemplateContext)
        assert context.run_ctx == run_ctx


class TestTemplateContextIntegration:
    """Интеграционные тесты для TemplateContext."""

    def setup_method(self):
        """Настройка для интеграционных тестов."""
        self.run_ctx = Mock(spec=RunContext)
        self.adaptive_loader = Mock()
        
        self.run_ctx.adaptive_loader = self.adaptive_loader
        self.run_ctx.mode_options = ModeOptions()
        self.run_ctx.active_tags = {"debug"}
        self.run_ctx.options = Mock()
        self.run_ctx.options.modes = {"java": "class"}
        
        # Настраиваем полную конфигурацию
        self.setup_full_config()

    def setup_full_config(self):
        """Настройка полной конфигурации для интеграционных тестов."""
        # Режимы
        class_mode = Mode(title="Class mode", description="Class mode", tags=["class_context"])
        method_mode = Mode(title="Method mode", description="Method mode", tags=["method_context"])
        test_mode = Mode(title="Test mode", description="Test mode", tags=["test_context"])
        
        java_modes = ModeSet(
            title="Java modes",
            modes={"class": class_mode, "method": method_mode}
        )
        test_modes = ModeSet(
            title="Test modes", 
            modes={"unit": test_mode}
        )
        
        modes_config = ModesConfig(
            mode_sets={"java": java_modes, "test": test_modes}
        )
        
        # Теги
        java_tag = Tag(title="Java")
        python_tag = Tag(title="Python")
        cpp_tag = Tag(title="C++")
        lang_tagset = TagSet(
            title="Languages",
            tags={"java": java_tag, "python": python_tag, "cpp": cpp_tag}
        )
        
        debug_tag = Tag(title="Debug")
        production_tag = Tag(title="Production")
        
        tags_config = TagsConfig(
            tag_sets={"lang": lang_tagset},
            global_tags={"debug": debug_tag, "production": production_tag}
        )
        
        self.adaptive_loader.get_modes_config.return_value = modes_config
        self.adaptive_loader.get_tags_config.return_value = tags_config

    def test_real_world_scenario(self):
        """Реальный сценарий использования контекста."""
        context = TemplateContext(self.run_ctx)
        
        # Начальное состояние
        assert "debug" in context.get_active_tags()
        assert context.get_active_modes() == {"java": "class"}
        
        # Вход в блок test:unit
        context.enter_mode_block("test", "unit")
        
        # Проверяем новые теги
        assert "test_context" in context.get_active_tags()
        assert context.get_active_modes() == {"java": "class", "test": "unit"}
        
        # Оценка условий в новом контексте
        assert context.evaluate_condition_text("tag:debug") is True
        assert context.evaluate_condition_text("tag:test_context") is True
        assert context.evaluate_condition_text("tag:debug AND tag:test_context") is True
        
        # Вход во вложенный блок java:method
        context.enter_mode_block("java", "method")
        
        # Проверяем изменения
        assert "method_context" in context.get_active_tags()
        assert context.get_active_modes() == {"java": "method", "test": "unit"}
        
        # Выход из вложенного блока
        context.exit_mode_block()
        
        # Проверяем восстановление
        assert "method_context" not in context.get_active_tags()
        assert context.get_active_modes() == {"java": "class", "test": "unit"}
        
        # Выход из внешнего блока
        context.exit_mode_block()
        
        # Проверяем полное восстановление
        assert "test_context" not in context.get_active_tags()
        assert context.get_active_modes() == {"java": "class"}

    def test_complex_condition_evaluation(self):
        """Сложная оценка условий с изменением контекста."""
        context = TemplateContext(self.run_ctx)
        
        # Базовые условия
        assert context.evaluate_condition_text("tag:debug") is True
        assert context.evaluate_condition_text("TAGSET:lang:java") is True
        
        # Вход в тестовый режим и добавление дополнительных тегов
        context.enter_mode_block("test", "unit")
        context.add_extra_tag("integration")
        
        # Сложные условия
        complex_condition = "tag:debug AND tag:test_context AND tag:integration"
        assert context.evaluate_condition_text(complex_condition) is True
        
        # Условие с tagset
        tagset_condition = "TAGSET:lang:java AND tag:test_context"
        assert context.evaluate_condition_text(tagset_condition) is True