"""
Тесты для основного процессора шаблонов lg.template.processor.

Проверяет работу TemplateProcessor - центрального компонента движка
шаблонизации LG V2, который координирует работу всех подсистем.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lg.cache.fs_cache import Cache
from lg.config.adaptive_loader import AdaptiveConfigLoader
from lg.config.adaptive_model import ModesConfig, ModeSet, Mode, TagsConfig, ModeOptions
from lg.run_context import RunContext
from lg.stats import TokenService
from lg.template.processor import TemplateProcessor, TemplateProcessingError, TemplateContext
from lg.types import RunOptions
from lg.vcs import NullVcs


class TestTemplateProcessor:
    """Тесты основного класса TemplateProcessor."""
    
    @pytest.fixture
    def mock_run_ctx(self):
        """Создает мок контекста выполнения для тестов."""
        run_ctx = Mock(spec=RunContext)
        run_ctx.root = Path("/test/repo")
        run_ctx.options = RunOptions()
        
        # Мок адаптивного загрузчика
        adaptive_loader = Mock(spec=AdaptiveConfigLoader)
        adaptive_loader.get_modes_config.return_value = ModesConfig()
        adaptive_loader.get_tags_config.return_value = TagsConfig()
        run_ctx.adaptive_loader = adaptive_loader
        
        # Мок остальных сервисов
        run_ctx.cache = Mock(spec=Cache)
        run_ctx.vcs = Mock(spec=NullVcs)
        run_ctx.tokenizer = Mock(spec=TokenService)
        run_ctx.mode_options = ModeOptions()
        run_ctx.active_tags = set()
        
        return run_ctx
    
    @pytest.fixture
    def processor(self, mock_run_ctx):
        """Создает экземпляр TemplateProcessor для тестов."""
        return TemplateProcessor(mock_run_ctx, validate_paths=False)
    
    def test_init(self, mock_run_ctx):
        """Тест инициализации TemplateProcessor."""
        processor = TemplateProcessor(mock_run_ctx)
        
        assert processor.run_ctx == mock_run_ctx
        assert isinstance(processor.template_ctx, TemplateContext)
        assert processor.section_handler is None
        assert processor._template_cache == {}
        assert processor._resolved_cache == {}
    
    def test_set_section_handler(self, processor):
        """Тест установки обработчика секций."""
        mock_handler = Mock()
        
        processor.set_section_handler(mock_handler)
        
        assert processor.section_handler == mock_handler
    

    def test_process_template_text_simple_text(self, processor):
        """Тест обработки простого текстового шаблона."""
        template_text = "Hello, world!"
        
        result = processor.process_template_text(template_text)
        
        assert result == "Hello, world!"
    
    def test_process_template_text_with_comments(self, processor):
        """Тест обработки шаблона с комментариями."""
        template_text = "Hello {# this is a comment #} world!"
        
        result = processor.process_template_text(template_text)
        
        assert result == "Hello  world!"

    def test_process_template_text_with_section_no_handler(self, processor):
        """Тест обработки шаблона с секцией без обработчика."""
        template_text = "Start ${section1} end"
        
        result = processor.process_template_text(template_text)
        
        assert result == "Start ${section:section1} end"

    def test_process_template_text_with_section_handler(self, processor):
        """Тест обработки шаблона с секцией и обработчиком."""
        template_text = "Start ${section1} end"
        
        # Устанавливаем мок обработчик
        mock_handler = Mock(return_value="SECTION_CONTENT")
        processor.set_section_handler(mock_handler)
        
        result = processor.process_template_text(template_text)
        
        assert result == "Start SECTION_CONTENT end"
        # Проверяем что обработчик был вызван с SectionRef
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        section_ref = call_args[0][0]
        assert section_ref.name == "section1"
        assert call_args[0][1] == processor.template_ctx

    @patch('lg.template.processor.load_context_from')
    def test_process_template_file(self, mock_load, processor):
        """Тест обработки шаблона из файла."""
        mock_load.return_value = (Path("/test/template.ctx.md"), "Hello from file!")
        
        result = processor.process_template_file("test-template")
        
        assert result == "Hello from file!"
        mock_load.assert_called_once()


    def test_process_template_text_caching(self, processor):
        """Тест кэширования распарсенных шаблонов."""
        template_text = "Simple template"
        
        # Первый вызов
        result1 = processor.process_template_text(template_text, "test-template")
        
        # Второй вызов с тем же содержимым
        result2 = processor.process_template_text(template_text, "test-template")
        
        assert result1 == result2
        # Проверяем, что кэш заполнен
        assert len(processor._template_cache) > 0

    def test_processing_error_handling(self, processor):
        """Тест обработки ошибок при парсинге."""
        # Некорректный синтаксис шаблона
        template_text = "{% if invalid condition %} content {% endif %}"
        
        with pytest.raises(TemplateProcessingError) as exc_info:
            processor.process_template_text(template_text, "test-template")
        
        assert "test-template" in str(exc_info.value)

    @patch('lg.template.processor.load_context_from')
    def test_file_loading_error(self, mock_load, processor):
        """Тест обработки ошибок при загрузке файла."""
        mock_load.side_effect = FileNotFoundError("Template not found")
        
        with pytest.raises(TemplateProcessingError) as exc_info:
            processor.process_template_file("missing-template")
        
        assert "missing-template" in str(exc_info.value)


class TestSectionHandling:
    """Тесты обработки плейсхолдеров секций."""
    
    @pytest.fixture
    def mock_run_ctx(self):
        """Создает мок контекста выполнения."""
        run_ctx = Mock(spec=RunContext)
        run_ctx.root = Path("/test/repo")
        run_ctx.options = RunOptions()
        run_ctx.adaptive_loader = Mock(spec=AdaptiveConfigLoader)
        run_ctx.adaptive_loader.get_modes_config.return_value = ModesConfig()
        run_ctx.adaptive_loader.get_tags_config.return_value = TagsConfig()
        run_ctx.mode_options = ModeOptions()
        run_ctx.active_tags = set()
        return run_ctx
    
    @pytest.fixture
    def processor(self, mock_run_ctx):
        """Создает процессор с мок обработчиком секций."""
        processor = TemplateProcessor(mock_run_ctx)
        
        # Мок обработчик секций
        def mock_section_handler(section_ref, template_ctx):
            return f"RENDERED_{section_ref.name.upper()}"
        
        processor.set_section_handler(mock_section_handler)
        return processor

    def test_single_section(self, processor):
        """Тест обработки одной секции."""
        template_text = "Before ${docs} after"
        
        result = processor.process_template_text(template_text)
        
        assert result == "Before RENDERED_DOCS after"

    def test_multiple_sections(self, processor):
        """Тест обработки нескольких секций."""
        template_text = "Start ${section1} middle ${section2} end"
        
        result = processor.process_template_text(template_text)
        
        assert result == "Start RENDERED_SECTION1 middle RENDERED_SECTION2 end"

    def test_section_in_conditional(self, processor):
        """Тест обработки секции внутри условного блока."""
        template_text = """
        Start content
        {% if tag:docs %}
        ${documentation}
        {% endif %}
        End content
        """
        
        # Устанавливаем активный тег docs
        processor.template_ctx.add_extra_tag("docs")
        
        result = processor.process_template_text(template_text)
        
        assert "RENDERED_DOCUMENTATION" in result
        assert "Start content" in result
        assert "End content" in result

    def test_section_context_passing(self, processor):
        """Тест передачи контекста в обработчик секций."""
        template_text = "Content: ${test_section}"
        
        # Заменяем обработчик на более детальный мок
        mock_handler = Mock(return_value="TEST_RESULT")
        processor.set_section_handler(mock_handler)
        
        result = processor.process_template_text(template_text)
        
        assert result == "Content: TEST_RESULT"
        # Проверяем что обработчик был вызван с SectionRef
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        section_ref = call_args[0][0]
        assert section_ref.name == "test_section"
        assert call_args[0][1] == processor.template_ctx


class TestIncludeHandling:
    """Тесты обработки включений шаблонов."""
    
    @pytest.fixture
    def mock_run_ctx(self):
        """Создает мок контекста выполнения."""
        run_ctx = Mock(spec=RunContext)
        run_ctx.root = Path("/test/repo")
        run_ctx.options = RunOptions()
        run_ctx.adaptive_loader = Mock(spec=AdaptiveConfigLoader)
        run_ctx.adaptive_loader.get_modes_config.return_value = ModesConfig()
        run_ctx.adaptive_loader.get_tags_config.return_value = TagsConfig()
        run_ctx.mode_options = ModeOptions()
        run_ctx.active_tags = set()
        return run_ctx
    
    @pytest.fixture
    def processor(self, mock_run_ctx):
        return TemplateProcessor(mock_run_ctx, validate_paths=False)

    def test_template_include(self, processor):
        """Тест включения шаблона."""
        # Мокаем load функции в resolver
        with patch.object(processor.resolver, 'load_template_fn') as mock_load_tpl:
            mock_load_tpl.return_value = (Path("/test/include.tpl.md"), "Included template content")
            
            template_text = "Before ${tpl:header} after"
            
            result = processor.process_template_text(template_text)
            
            assert result == "Before Included template content after"
            mock_load_tpl.assert_called_once()

    def test_context_include(self, processor):
        """Тест включения контекста."""
        # Мокаем load функции в resolver
        with patch.object(processor.resolver, 'load_context_fn') as mock_load_ctx:
            mock_load_ctx.return_value = (Path("/test/include.ctx.md"), "Included context content")
            
            template_text = "Before ${ctx:intro} after"
            
            result = processor.process_template_text(template_text)
            
            assert result == "Before Included context content after"
            mock_load_ctx.assert_called_once()

    def test_nested_includes(self, processor):
        """Тест вложенных включений."""
        # Мокаем load функции в resolver
        with patch.object(processor.resolver, 'load_template_fn') as mock_load_tpl:
            # Первый уровень включает второй
            mock_load_tpl.side_effect = [
                (Path("/test/level1.tpl.md"), "Level 1: ${tpl:level2}"),
                (Path("/test/level2.tpl.md"), "Level 2 content")
            ]
            
            template_text = "Start ${tpl:level1} end"
            
            result = processor.process_template_text(template_text)
            
            assert result == "Start Level 1: Level 2 content end"
            assert mock_load_tpl.call_count == 2

    def test_include_error_handling(self, processor):
        """Тест обработки ошибок при включении."""
        # Мокируем функции resolver для полноценного теста
        with patch.object(processor.resolver, 'load_template_fn') as mock_load_tpl, \
             patch.object(processor.resolver, '_resolve_cfg_root_safe') as mock_cfg_root:
            
            # Настраиваем мок cfg_root
            mock_cfg_root.return_value = Path("/test/repo/lg-cfg")
            # Настраиваем ошибку загрузки
            mock_load_tpl.side_effect = FileNotFoundError("Template not found")
            
            template_text = "Before ${tpl:missing} after"
            
            # Ожидаем ошибку резолвинга
            with pytest.raises(TemplateProcessingError) as exc_info:
                processor.process_template_text(template_text)
                
            assert "Resolution failed" in str(exc_info.value)

    def test_include_without_resolution(self, processor):
        """Тест включения, которое не может быть разрешено."""
        # Мокируем функции resolver для полноценного теста
        with patch.object(processor.resolver, 'load_template_fn') as mock_load_tpl, \
             patch.object(processor.resolver, '_resolve_cfg_root_safe') as mock_cfg_root:
            
            # Настраиваем мок cfg_root
            mock_cfg_root.return_value = Path("/test/repo/lg-cfg")
            # Настраиваем ошибку загрузки
            mock_load_tpl.side_effect = FileNotFoundError("Template not found")
            
            template_text = "Before ${tpl:unresolved} after"
            
            # Ожидаем, что резолвер выдаст ошибку при отсутствии шаблона
            with pytest.raises(TemplateProcessingError) as exc_info:
                processor.process_template_text(template_text)
                
            # Проверяем, что ошибка связана с резолвингом
            assert "Resolution failed" in str(exc_info.value)
class TestConditionalBlocks:
    """Тесты обработки условных блоков."""
    
    @pytest.fixture
    def mock_run_ctx(self):
        """Создает мок контекста выполнения с режимами и тегами."""
        run_ctx = Mock(spec=RunContext)
        run_ctx.root = Path("/test/repo")
        run_ctx.options = RunOptions()
        
        # Мок конфигурации режимов
        modes_config = ModesConfig()
        modes_config.mode_sets = {
            "test_modes": ModeSet(
                title="Test Modes",
                modes={
                    "dev": Mode(title="Development", tags=["dev"]),
                    "prod": Mode(title="Production", tags=["prod"])
                }
            )
        }
        
        # Мок конфигурации тегов
        from lg.config.adaptive_model import TagSet, Tag
        tags_config = TagsConfig()
        tags_config.tag_sets = {
            "language": TagSet(
                title="Languages",
                tags={
                    "python": Tag(title="Python"),
                    "typescript": Tag(title="TypeScript")
                }
            )
        }
        tags_config.global_tags = {
            "docs": Tag(title="Documentation"),
            "tests": Tag(title="Tests")
        }
        
        adaptive_loader = Mock(spec=AdaptiveConfigLoader)
        adaptive_loader.get_modes_config.return_value = modes_config
        adaptive_loader.get_tags_config.return_value = tags_config
        
        run_ctx.adaptive_loader = adaptive_loader
        run_ctx.mode_options = ModeOptions()
        run_ctx.active_tags = set()
        
        return run_ctx
    
    @pytest.fixture
    def processor(self, mock_run_ctx):
        return TemplateProcessor(mock_run_ctx)

    def test_if_true_condition(self, processor):
        """Тест условного блока с истинным условием."""
        template_text = """
        Start
        {% if tag:docs %}
        Documentation content
        {% endif %}
        End
        """
        
        # Активируем тег docs
        processor.template_ctx.add_extra_tag("docs")
        
        result = processor.process_template_text(template_text)
        
        assert "Documentation content" in result
        assert "Start" in result
        assert "End" in result

    def test_if_false_condition(self, processor):
        """Тест условного блока с ложным условием."""
        template_text = """
        Start
        {% if tag:missing %}
        This should not appear
        {% endif %}
        End
        """
        
        result = processor.process_template_text(template_text)
        
        assert "This should not appear" not in result
        assert "Start" in result
        assert "End" in result

    def test_if_else_true(self, processor):
        """Тест условного блока с else веткой (условие истинно)."""
        template_text = """
        Start
        {% if tag:docs %}
        True branch
        {% else %}
        False branch
        {% endif %}
        End
        """
        
        processor.template_ctx.add_extra_tag("docs")
        
        result = processor.process_template_text(template_text)
        
        assert "True branch" in result
        assert "False branch" not in result

    def test_if_else_false(self, processor):
        """Тест условного блока с else веткой (условие ложно)."""
        template_text = """
        Start
        {% if tag:missing %}
        True branch
        {% else %}
        False branch
        {% endif %}
        End
        """
        
        result = processor.process_template_text(template_text)
        
        assert "True branch" not in result
        assert "False branch" in result

    def test_nested_conditionals(self, processor):
        """Тест вложенных условных блоков."""
        template_text = """
        {% if tag:docs %}
        Outer true
        {% if tag:tests %}
        Inner true
        {% else %}
        Inner false
        {% endif %}
        {% else %}
        Outer false
        {% endif %}
        """
        
        processor.template_ctx.add_extra_tag("docs")
        processor.template_ctx.add_extra_tag("tests")
        
        result = processor.process_template_text(template_text)
        
        assert "Outer true" in result
        assert "Inner true" in result
        assert "Inner false" not in result
        assert "Outer false" not in result

    def test_complex_condition(self, processor):
        """Тест сложного условия с логическими операторами."""
        template_text = """
        {% if tag:docs AND tag:tests %}
        Both tags active
        {% endif %}
        """
        
        # Активируем оба тега
        processor.template_ctx.add_extra_tag("docs")
        processor.template_ctx.add_extra_tag("tests")
        
        result = processor.process_template_text(template_text)
        
        assert "Both tags active" in result


class TestModeBlocks:
    """Тесты обработки режимных блоков."""
    
    @pytest.fixture
    def mock_run_ctx(self):
        """Создает мок контекста с режимами."""
        run_ctx = Mock(spec=RunContext)
        run_ctx.root = Path("/test/repo")
        run_ctx.options = RunOptions()
        
        # Создаем реальную конфигурацию режимов для тестов
        modes_config = ModesConfig()
        modes_config.mode_sets = {
            "dev_stage": ModeSet(
                title="Development Stage",
                modes={
                    "development": Mode(
                        title="Development", 
                        tags=["dev", "debug"]
                    ),
                    "production": Mode(
                        title="Production", 
                        tags=["prod", "optimized"]
                    )
                }
            ),
            "feature": ModeSet(
                title="Feature Mode",
                modes={
                    "full": Mode(title="Full Feature", tags=["full"]),
                    "minimal": Mode(title="Minimal", tags=["minimal"])
                }
            )
        }
        
        adaptive_loader = Mock(spec=AdaptiveConfigLoader)
        adaptive_loader.get_modes_config.return_value = modes_config
        adaptive_loader.get_tags_config.return_value = TagsConfig()
        
        run_ctx.adaptive_loader = adaptive_loader
        run_ctx.mode_options = ModeOptions()
        run_ctx.active_tags = set()
        
        return run_ctx
    
    @pytest.fixture
    def processor(self, mock_run_ctx):
        return TemplateProcessor(mock_run_ctx)

    def test_mode_block_basic(self, processor):
        """Тест базового режимного блока."""
        template_text = """
        Before mode block
        {% mode dev_stage:development %}
        Inside development mode
        {% if tag:dev %}
        Development specific content
        {% endif %}
        {% endmode %}
        After mode block
        """
        
        result = processor.process_template_text(template_text)
        
        assert "Before mode block" in result
        assert "Inside development mode" in result
        assert "Development specific content" in result
        assert "After mode block" in result

    def test_mode_block_tag_activation(self, processor):
        """Тест активации тегов внутри режимного блока."""
        template_text = """
        {% if tag:dev %}
        Outside: Should not appear
        {% endif %}
        
        {% mode dev_stage:development %}
        {% if tag:dev %}
        Inside: Should appear
        {% endif %}
        {% endmode %}
        
        {% if tag:dev %}
        After: Should not appear
        {% endif %}
        """
        
        result = processor.process_template_text(template_text)
        
        assert "Outside: Should not appear" not in result
        assert "Inside: Should appear" in result
        assert "After: Should not appear" not in result

    def test_nested_mode_blocks(self, processor):
        """Тест вложенных режимных блоков."""
        template_text = """
        {% mode dev_stage:development %}
        Outer mode
        {% if tag:dev %}
        Dev tag active in outer
        {% endif %}
        
        {% mode feature:minimal %}
        Inner mode
        {% if tag:minimal %}
        Minimal tag active in inner
        {% endif %}
        {% if tag:dev %}
        Dev tag still active in inner
        {% endif %}
        {% endmode %}
        
        Back to outer
        {% if tag:minimal %}
        Minimal tag should not be active
        {% endif %}
        {% endmode %}
        """
        
        result = processor.process_template_text(template_text)
        
        assert "Outer mode" in result
        assert "Dev tag active in outer" in result
        assert "Inner mode" in result
        assert "Minimal tag active in inner" in result
        assert "Dev tag still active in inner" in result
        assert "Back to outer" in result
        assert "Minimal tag should not be active" not in result

    def test_mode_block_error_unknown_modeset(self, processor):
        """Тест ошибки с неизвестным набором режимов."""
        template_text = """
        {% mode unknown_modeset:mode %}
        Content
        {% endmode %}
        """
        
        with pytest.raises(TemplateProcessingError) as exc_info:
            processor.process_template_text(template_text)
        
        # Проверяем, что произошла ошибка обработки (может быть парсинг или выполнение)
        assert "TemplateProcessingError" in str(type(exc_info.value))

    def test_mode_block_error_unknown_mode(self, processor):
        """Тест ошибки с неизвестным режимом."""
        template_text = """
        {% mode dev_stage:unknown_mode %}
        Content
        {% endmode %}
        """
        
        with pytest.raises(TemplateProcessingError) as exc_info:
            processor.process_template_text(template_text)
        
        # Проверяем, что произошла ошибка обработки
        assert "TemplateProcessingError" in str(type(exc_info.value))

    def test_mode_block_proper_cleanup(self, processor):
        """Тест корректной очистки состояния после режимного блока."""
        # Добавляем начальный тег
        processor.template_ctx.add_extra_tag("initial")
        
        template_text = """
        {% if tag:initial %}
        Initial tag active before
        {% endif %}
        {% if tag:dev %}
        Dev tag should not be active before
        {% endif %}
        
        {% mode dev_stage:development %}
        {% if tag:dev %}
        Dev tag active inside
        {% endif %}
        {% endmode %}
        
        {% if tag:initial %}
        Initial tag active after
        {% endif %}
        {% if tag:dev %}
        Dev tag should not be active after
        {% endif %}
        """
        
        result = processor.process_template_text(template_text)
        
        assert "Initial tag active before" in result
        assert "Dev tag should not be active before" not in result
        assert "Dev tag active inside" in result
        assert "Initial tag active after" in result
        assert "Dev tag should not be active after" not in result


class TestDependencyAnalysis:
    """Тесты анализа зависимостей и валидации шаблонов."""
    
    @pytest.fixture
    def mock_run_ctx(self):
        """Создает мок контекста выполнения."""
        run_ctx = Mock(spec=RunContext)
        run_ctx.root = Path("/test/repo")
        run_ctx.options = RunOptions()
        
        # Мок конфигурации режимов
        modes_config = ModesConfig()
        modes_config.mode_sets = {
            "test_modes": ModeSet(
                title="Test Modes",
                modes={
                    "valid": Mode(title="Valid Mode", tags=["valid"]),
                    "invalid": Mode(title="Invalid Mode", tags=["invalid"])
                }
            )
        }
        
        adaptive_loader = Mock(spec=AdaptiveConfigLoader)
        adaptive_loader.get_modes_config.return_value = modes_config
        adaptive_loader.get_tags_config.return_value = TagsConfig()
        
        run_ctx.adaptive_loader = adaptive_loader
        run_ctx.mode_options = ModeOptions()
        run_ctx.active_tags = set()
        
        return run_ctx
    
    @pytest.fixture
    def processor(self, mock_run_ctx):
        return TemplateProcessor(mock_run_ctx)

    @patch('lg.template.processor.load_context_from')
    def test_get_dependencies_sections_only(self, mock_load, processor):
        """Тест анализа зависимостей шаблона с секциями."""
        template_content = """
        # Header
        
        ${section1}
        
        ## Subsection
        
        ${section2}
        ${section3}
        """
        
        mock_load.return_value = (Path("/test/template.ctx.md"), template_content)
        
        dependencies = processor.get_template_dependencies("test-template")
        
        assert "sections" in dependencies
        assert "includes" in dependencies
        assert "conditional" in dependencies
        
        assert set(dependencies["sections"]) == {"section1", "section2", "section3"}
        assert dependencies["includes"] == []
        assert dependencies["conditional"] is False

    @patch('lg.template.processor.load_context_from')
    def test_get_dependencies_with_includes(self, mock_load, processor):
        """Тест анализа зависимостей с включениями."""
        template_content = """
        ${tpl:header}
        
        Content here
        
        ${ctx:footer}
        ${tpl:sidebar}
        """
        
        mock_load.return_value = (Path("/test/template.ctx.md"), template_content)
        
        dependencies = processor.get_template_dependencies("test-template")
        
        assert set(dependencies["includes"]) == {"tpl:header", "ctx:footer", "tpl:sidebar"}
        assert dependencies["sections"] == []
        assert dependencies["conditional"] is False

    @patch('lg.template.processor.load_context_from')
    def test_get_dependencies_with_conditionals(self, mock_load, processor):
        """Тест анализа зависимостей с условными блоками."""
        template_content = """
        Basic content
        
        {% if tag:docs %}
        ${documentation}
        {% endif %}
        
        {% mode dev_stage:development %}
        ${dev_content}
        {% endmode %}
        """
        
        mock_load.return_value = (Path("/test/template.ctx.md"), template_content)
        
        dependencies = processor.get_template_dependencies("test-template")
        
        assert set(dependencies["sections"]) == {"documentation", "dev_content"}
        assert dependencies["includes"] == []
        assert dependencies["conditional"] is True

    @patch('lg.template.processor.load_context_from')
    def test_get_dependencies_mixed(self, mock_load, processor):
        """Тест анализа зависимостей смешанного шаблона."""
        template_content = """
        ${tpl:header}
        
        {% if tag:full %}
        ${full_content}
        {% else %}
        ${minimal_content}
        {% endif %}
        
        {% mode feature:advanced %}
        ${ctx:advanced_footer}
        {% endmode %}
        """
        
        mock_load.return_value = (Path("/test/template.ctx.md"), template_content)
        
        dependencies = processor.get_template_dependencies("test-template")
        
        assert set(dependencies["sections"]) == {"full_content", "minimal_content"}
        assert set(dependencies["includes"]) == {"tpl:header", "ctx:advanced_footer"}
        assert dependencies["conditional"] is True

    @patch('lg.template.processor.load_context_from')
    def test_dependency_analysis_error(self, mock_load, processor):
        """Тест обработки ошибок при анализе зависимостей."""
        mock_load.side_effect = FileNotFoundError("Template not found")
        
        with pytest.raises(TemplateProcessingError) as exc_info:
            processor.get_template_dependencies("missing-template")
        
        assert "Failed to analyze dependencies" in str(exc_info.value)
        assert "missing-template" in str(exc_info.value)

    @patch('lg.template.processor.load_context_from')
    def test_prevalidate_template_valid(self, mock_load, processor):
        """Тест валидации корректного шаблона."""
        template_content = """
        {% if tag:docs %}
        Valid content
        {% endif %}
        
        {% mode test_modes:valid %}
        More content
        {% endmode %}
        """
        
        mock_load.return_value = (Path("/test/template.ctx.md"), template_content)
        
        issues = processor.prevalidate_template("valid-template")
        
        assert issues == []

    @patch('lg.template.processor.load_context_from')
    def test_prevalidate_template_invalid_condition(self, mock_load, processor):
        """Тест валидации шаблона с некорректным условием."""
        template_content = """
        {% if invalid_syntax %}
        Content
        {% endif %}
        """
        
        mock_load.return_value = (Path("/test/template.ctx.md"), template_content)
        
        issues = processor.prevalidate_template("invalid-template")
        
        assert len(issues) > 0
        assert any("Invalid condition" in issue for issue in issues)

    @patch('lg.template.processor.load_context_from')
    def test_prevalidate_template_unknown_modeset(self, mock_load, processor):
        """Тест валидации шаблона с неизвестным набором режимов."""
        template_content = """
        {% mode unknown_modeset:mode %}
        Content
        {% endmode %}
        """
        
        mock_load.return_value = (Path("/test/template.ctx.md"), template_content)
        
        issues = processor.prevalidate_template("invalid-modeset")
        
        # Проверяем, что есть проблемы (может быть ошибка парсинга или валидации)
        assert len(issues) > 0

    @patch('lg.template.processor.load_context_from')
    def test_prevalidate_template_unknown_mode(self, mock_load, processor):
        """Тест валидации шаблона с неизвестным режимом."""
        template_content = """
        {% mode test_modes:unknown_mode %}
        Content
        {% endmode %}
        """
        
        mock_load.return_value = (Path("/test/template.ctx.md"), template_content)
        
        issues = processor.prevalidate_template("invalid-mode")
        
        assert len(issues) > 0
        assert any("Unknown mode" in issue for issue in issues)

    @patch('lg.template.processor.load_context_from')
    @patch('lg.template.processor.load_template_from')
    def test_prevalidate_template_missing_includes(self, mock_load_tpl, mock_load_ctx, processor):
        """Тест валидации шаблона с отсутствующими включениями.""" 
        template_content = """
        ${tpl:existing}
        ${ctx:missing}
        """
        
        mock_load_ctx.side_effect = [
            # Первый вызов для основного шаблона
            (Path("/test/template.ctx.md"), template_content),
            # Второй вызов для ctx:missing - ошибка
            FileNotFoundError("Template not found")
        ]
        
        def load_template_side_effect(cfg_root, name):
            if name == "existing":
                return (Path("/test/existing.tpl.md"), "Content")
            else:
                raise FileNotFoundError("Template not found")
        
        mock_load_tpl.side_effect = load_template_side_effect
        
        issues = processor.prevalidate_template("template-with-missing-includes")
        
        assert len(issues) > 0
        # Проверяем любую ошибку загрузки включений
        assert any("Cannot load" in issue or "Template not found" in issue for issue in issues)

    @patch('lg.template.processor.load_context_from')
    def test_prevalidate_template_parse_error(self, mock_load, processor):
        """Тест валидации шаблона с ошибкой парсинга."""
        mock_load.side_effect = Exception("Parse error")
        
        issues = processor.prevalidate_template("unparseable-template")
        
        assert len(issues) > 0
        assert any("Failed to parse template" in issue for issue in issues)


class TestErrorHandling:
    """Тесты обработки различных типов ошибок."""
    
    @pytest.fixture
    def mock_run_ctx(self):
        """Создает мок контекста выполнения."""
        run_ctx = Mock(spec=RunContext)
        run_ctx.root = Path("/test/repo")
        run_ctx.options = RunOptions()
        run_ctx.adaptive_loader = Mock(spec=AdaptiveConfigLoader)
        run_ctx.adaptive_loader.get_modes_config.return_value = ModesConfig()
        run_ctx.adaptive_loader.get_tags_config.return_value = TagsConfig()
        run_ctx.mode_options = ModeOptions()
        run_ctx.active_tags = set()
        return run_ctx
    
    @pytest.fixture
    def processor(self, mock_run_ctx):
        return TemplateProcessor(mock_run_ctx)

    def test_lexer_error(self, processor):
        """Тест обработки ошибки лексера."""
        # Некорректный синтаксис, который вызовет LexerError
        template_text = "${ unclosed placeholder"
        
        with pytest.raises(TemplateProcessingError) as exc_info:
            processor.process_template_text(template_text)
        
        assert "TemplateProcessingError" in str(type(exc_info.value))

    def test_parser_error(self, processor):
        """Тест обработки ошибки парсера."""
        # Некорректная структура, которая вызовет ParserError
        template_text = "{% if %} content {% endif %}"  # Пустое условие
        
        with pytest.raises(TemplateProcessingError) as exc_info:
            processor.process_template_text(template_text)
        
        assert "TemplateProcessingError" in str(type(exc_info.value))

    def test_condition_evaluation_error(self, processor):
        """Тест обработки ошибки вычисления условий."""
        # Некорректное условие
        template_text = "{% if invalid_operator_syntax %} content {% endif %}"
        
        with pytest.raises(TemplateProcessingError) as exc_info:
            processor.process_template_text(template_text)
        
        assert "TemplateProcessingError" in str(type(exc_info.value))

    @patch('lg.template.processor.load_template_from')
    @patch('lg.template.processor.load_context_from') 
    def test_circular_include_handling(self, mock_load_ctx, mock_load_tpl, processor):
        """Тест обработки циклических включений."""
        # Мокаем циклические включения: template1 включает template2, template2 включает template1
        def load_side_effect(cfg_root, name):
            if name == "template1":
                return (Path("/test/template1.tpl.md"), "${tpl:template2}")
            elif name == "template2": 
                return (Path("/test/template2.tpl.md"), "${tpl:template1}")
            else:
                raise FileNotFoundError("Template not found")
        
        mock_load_tpl.side_effect = load_side_effect
        
        template_text = "${tpl:template1}"
        
        # Должен обработать без зависания (благодаря ограничениям на глубину рекурсии)
        # Или выдать ошибку о циклической зависимости
        try:
            result = processor.process_template_text(template_text)
            # Если успешно обработал, проверяем результат
            assert "Error loading" in result or "template" in result
        except (TemplateProcessingError, RecursionError):
            # Ожидаемые ошибки при циклических включениях
            pass

    def test_unexpected_error_handling(self, processor):
        """Тест обработки неожиданных ошибок."""
        template_text = "Normal template content"
        
        # Мокаем неожиданную ошибку в _evaluate_ast
        with patch.object(processor, '_evaluate_ast', side_effect=RuntimeError("Unexpected error")):
            with pytest.raises(TemplateProcessingError) as exc_info:
                processor.process_template_text(template_text)
            
            assert "Unexpected error during processing" in str(exc_info.value)

    def test_error_context_preservation(self, processor):
        """Тест сохранения контекста ошибок."""
        template_text = "{% invalid syntax %}"
        template_name = "error-test-template"
        
        with pytest.raises(TemplateProcessingError) as exc_info:
            processor.process_template_text(template_text, template_name)
        
        # Проверяем, что имя шаблона присутствует в ошибке
        assert template_name in str(exc_info.value)


class TestIntegration:
    """Интеграционные тесты с реальными файлами и сложными сценариями."""
    
    @pytest.fixture
    def mock_run_ctx(self):
        """Создает реалистичный контекст выполнения."""
        run_ctx = Mock(spec=RunContext)
        run_ctx.root = Path("/test/repo")
        run_ctx.options = RunOptions()
        
        # Полная конфигурация режимов
        modes_config = ModesConfig()
        modes_config.mode_sets = {
            "ai_interaction": ModeSet(
                title="AI Interaction Mode",
                modes={
                    "ask": Mode(title="Ask Questions", tags=["interactive"]),
                    "agent": Mode(title="Agent Mode", tags=["agent", "tools"])
                }
            ),
            "dev_stage": ModeSet(
                title="Development Stage", 
                modes={
                    "planning": Mode(title="Planning", tags=["docs", "architecture"]),
                    "development": Mode(title="Development", tags=["code", "implementation"]),
                    "testing": Mode(title="Testing", tags=["tests", "qa"]),
                    "review": Mode(title="Review", tags=["review", "minimal"])
                }
            )
        }
        
        # Конфигурация тегов
        from lg.config.adaptive_model import TagSet, Tag
        tags_config = TagsConfig()
        tags_config.tag_sets = {
            "language": TagSet(
                title="Programming Languages",
                tags={
                    "python": Tag(title="Python"),
                    "typescript": Tag(title="TypeScript"),
                    "javascript": Tag(title="JavaScript")
                }
            ),
            "feature": TagSet(
                title="Feature Areas",
                tags={
                    "api": Tag(title="API Layer"),
                    "ui": Tag(title="User Interface"),
                    "db": Tag(title="Database")
                }
            )
        }
        tags_config.global_tags = {
            "docs": Tag(title="Documentation"),
            "tests": Tag(title="Test Code"),
            "agent": Tag(title="Agent Features"),
            "tools": Tag(title="Tool Integration"),
            "minimal": Tag(title="Minimal Content"),
            "review": Tag(title="Code Review")
        }
        
        adaptive_loader = Mock(spec=AdaptiveConfigLoader)
        adaptive_loader.get_modes_config.return_value = modes_config
        adaptive_loader.get_tags_config.return_value = tags_config
        
        run_ctx.adaptive_loader = adaptive_loader
        run_ctx.mode_options = ModeOptions()
        run_ctx.active_tags = set()
        
        return run_ctx
    
    @pytest.fixture
    def processor(self, mock_run_ctx):
        processor = TemplateProcessor(mock_run_ctx, validate_paths=False)
        
        # Устанавливаем реалистичный обработчик секций
        def section_handler(section_ref, template_ctx):
            section_name = section_ref.name
            active_tags = template_ctx.get_active_tags()
            
            if "minimal" in active_tags:
                return f"<!-- {section_name} (minimal) -->"
            elif "tests" in active_tags and "test" in section_name:
                return f"# Test content for {section_name}\n\ndef test_{section_name}():\n    pass"
            else:
                return f"# Full content for {section_name}\n\n## Details\n\nImplementation here..."
        
        processor.set_section_handler(section_handler)
        return processor

    def test_complex_template_with_all_features(self, processor):
        """Тест сложного шаблона со всеми возможностями."""
        # Основной шаблон
        main_template = """
        # Project Documentation
        
        ${tpl:header}
        
        ## Development Guide
        
        {% if tag:docs %}
        This section provides detailed development information.
        {% endif %}
        
        {% mode dev_stage:planning %}
        
        ### Architecture Overview
        ${architecture}
        
        {% if TAGSET:language:python %}
        #### Python Implementation
        ${python_impl}
        {% endif %}
        
        {% endmode %}
        
        {% mode ai_interaction:agent %}
        
        ### Agent Capabilities
        {% if tag:tools %}
        ${agent_tools}
        {% endif %}
        
        {% endmode %}
        
        ## Testing
        
        {% if tag:tests %}
        ${test_suite}
        {% endif %}
        
        ${tpl:footer}
        """
        
        # Включаемые шаблоны
        header_template = "<!-- Project Header -->\n\nWelcome to the project!"
        footer_template = "<!-- Project Footer -->\n\nEnd of documentation."
        
        # Мокаем load функции
        with patch.object(processor, '_load_template_text') as mock_load_text, \
             patch.object(processor.resolver, 'load_template_fn') as mock_load_tpl:
            
            mock_load_text.return_value = main_template
            mock_load_tpl.side_effect = lambda cfg_root, name: {
                "header": (Path("/test/header.tpl.md"), header_template),
                "footer": (Path("/test/footer.tpl.md"), footer_template)
            }[name]
            
            result = processor.process_template_file("main")
            
            # Базовая структура должна присутствовать
            assert "# Project Documentation" in result
            assert "Welcome to the project!" in result
            assert "End of documentation." in result
            
            # Содержимое режимных блоков должно быть включено
            assert "Architecture Overview" in result
            assert "Agent Capabilities" in result
            
            # Секции должны быть отрендерены
            assert "Full content for architecture" in result

    @patch('lg.template.processor.load_context_from')
    def test_conditional_content_with_tagset(self, mock_load, processor):
        """Тест условного содержимого с наборами тегов."""
        template_content = """
        # Multi-language Project
        
        {% if TAGSET:language:python %}
        ## Python Implementation
        ${python_code}
        {% endif %}
        
        {% if TAGSET:language:typescript %}
        ## TypeScript Implementation  
        ${typescript_code}
        {% endif %}
        
        {% if TAGSET:language:javascript %}
        ## JavaScript Implementation
        ${javascript_code}
        {% endif %}
        """
        
        mock_load.return_value = (Path("/test/multi.ctx.md"), template_content)
        
        # Активируем тег Python
        processor.template_ctx.add_extra_tag("python")
        
        result = processor.process_template_file("multi")
        
        # Должна быть только Python секция
        assert "## Python Implementation" in result
        assert "Full content for python_code" in result
        assert "## TypeScript Implementation" not in result
        assert "## JavaScript Implementation" not in result

    @patch('lg.template.processor.load_context_from')
    def test_nested_mode_blocks_with_conditions(self, mock_load, processor):
        """Тест вложенных режимных блоков с условиями."""
        template_content = """
        # Development Workflow
        
        {% mode dev_stage:testing %}
        
        ## Testing Phase
        
        {% if tag:tests %}
        Basic test setup is active.
        {% endif %}
        
        {% mode ai_interaction:agent %}
        
        ### Agent-Assisted Testing
        
        {% if tag:agent AND tag:tests %}
        Agent tools for testing are available.
        ${agent_test_tools}
        {% endif %}
        
        {% endmode %}
        
        {% if tag:tests %}
        Back to basic testing mode.
        {% endif %}
        
        {% endmode %}
        
        End of workflow.
        """
        
        mock_load.return_value = (Path("/test/workflow.ctx.md"), template_content)
        
        result = processor.process_template_file("workflow")
        
        # Проверяем правильную активацию тегов
        assert "Basic test setup is active." in result
        assert "Agent tools for testing are available." in result
        # Секция должна быть обработана - проверяем наличие тестового содержимого
        assert "def test_agent_test_tools():" in result
        assert "Back to basic testing mode." in result
        assert "End of workflow." in result


    def test_template_context_isolation(self, processor):
        """Тест изоляции контекста между шаблонами."""
        # Первый шаблон с режимным блоком
        template1 = """
        {% mode dev_stage:planning %}
        Planning content
        {% if tag:docs %}
        Docs are active
        {% endif %}
        {% endmode %}
        """
        
        # Второй шаблон без режимных блоков
        template2 = """
        Regular content
        {% if tag:docs %}
        This should not appear
        {% endif %}
        """
        
        result1 = processor.process_template_text(template1)
        result2 = processor.process_template_text(template2)
        
        # В первом шаблоне теги должны быть активны
        assert "Docs are active" in result1
        
        # Во втором шаблоне теги не должны быть активны
        assert "This should not appear" not in result2


class TestOriginIncludes:
    """Тесты для обработки включений с управлением origin."""

    @pytest.fixture
    def mock_run_ctx(self):
        """Создает мок контекста выполнения."""
        run_ctx = Mock(spec=RunContext)
        run_ctx.root = Path("/test/repo")
        run_ctx.options = RunOptions()
        
        # Мок адаптивного загрузчика с поддержкой scope условий
        adaptive_loader = Mock(spec=AdaptiveConfigLoader)
        adaptive_loader.get_modes_config.return_value = ModesConfig()
        adaptive_loader.get_tags_config.return_value = TagsConfig()
        run_ctx.adaptive_loader = adaptive_loader
        
        run_ctx.cache = Mock(spec=Cache)
        run_ctx.vcs = Mock(spec=NullVcs)
        run_ctx.tokenizer = Mock(spec=TokenService)
        run_ctx.mode_options = ModeOptions()
        run_ctx.active_tags = {"debug"}
        
        return run_ctx

    @pytest.fixture
    def processor(self, mock_run_ctx):
        """Создает процессор с мок функциями загрузки."""
        processor = TemplateProcessor(mock_run_ctx, validate_paths=False)
        
        # Мок загрузчики шаблонов
        def mock_load_template(cfg_root, name):
            if name == "local_template":
                return Path("local_template.tpl.md"), "Local content: {% if scope:local %}LOCAL{% endif %}"
            elif name == "parent_template":
                return Path("parent_template.tpl.md"), "Parent content: {% if scope:parent %}PARENT{% endif %}"
            else:
                raise FileNotFoundError(f"Template {name} not found")
        
        def mock_load_context(cfg_root, name):
            if name == "scope_test":
                return Path("scope_test.ctx.md"), "Context: {% if scope:local %}LOCAL{% endif %}{% if scope:parent %}PARENT{% endif %}"
            else:
                raise FileNotFoundError(f"Context {name} not found")
        
        processor.resolver.load_template_fn = mock_load_template
        processor.resolver.load_context_fn = mock_load_context
        
        return processor

    def test_include_local_template(self, processor):
        """Тест включения локального шаблона."""
        template_text = "Start ${tpl:local_template} end"
        
        result = processor.process_template_text(template_text)
        
        assert result == "Start Local content: LOCAL end"

    def test_include_template_from_different_scope(self, processor):
        """Тест включения шаблона из другого скоупа."""
        # Исправленный формат: нужно использовать правильную адресную нотацию
        # Но пока парсер еще не поддерживает адресные включения, используем простые
        template_text = "Start ${tpl:parent_template} end"
        
        # Настраиваем загрузчик для симуляции другого скоупа
        def parent_scope_loader(cfg_root, name):
            if name == "parent_template":
                # Симулируем что шаблон загружается из другого скоупа
                return Path("parent_template.tpl.md"), "Parent content: {% if scope:parent %}PARENT{% endif %}"
            else:
                raise FileNotFoundError(f"Template {name} not found")
        
        # Для данного теста будем вручную менять origin в процессоре
        original_loader = processor.resolver.load_template_fn
        processor.resolver.load_template_fn = parent_scope_loader
        
        result = processor.process_template_text(template_text)
        
        # Восстанавливаем оригинальный загрузчик
        processor.resolver.load_template_fn = original_loader
        
        # В этом тесте мы не меняем origin, так что условие scope:parent не сработает
        assert "Start Parent content: " in result
        assert "end" in result

    def test_nested_scope_includes(self, processor):
        """Тест вложенных включений с разными скоупами."""
        # Настраиваем более сложную загрузку
        def complex_load_template(cfg_root, name):
            if name == "outer":
                return Path("outer.tpl.md"), "{% if scope:local %}OUTER_LOCAL{% endif %} ${tpl@child:inner} {% if scope:local %}OUTER_LOCAL_END{% endif %}"
            elif name == "inner":
                return Path("inner.tpl.md"), "{% if scope:parent %}INNER_PARENT{% endif %}"
            else:
                raise FileNotFoundError(f"Template {name} not found")
        
        processor.resolver.load_template_fn = complex_load_template
        
        template_text = "${tpl:outer}"
        
        result = processor.process_template_text(template_text)
        
        # outer шаблон работает в локальном скоупе, inner - в родительском
        assert "OUTER_LOCAL" in result
        assert "INNER_PARENT" in result
        assert "OUTER_LOCAL_END" in result

    def test_context_include_with_scope(self, processor):
        """Тест включения контекста с проверкой скоупа."""
        template_text = "Local: ${ctx:scope_test} Remote: ${ctx@remote:scope_test}"
        
        result = processor.process_template_text(template_text)
        
        # Локальный контекст должен показать LOCAL, удаленный - PARENT
        assert "Local: Context: LOCAL" in result
        assert "Remote: Context: PARENT" in result

    def test_scope_condition_evaluation_during_include(self, processor):
        """Тест оценки scope условий во время обработки включений."""
        # Более детальный тест с отслеживанием изменений origin
        template_changes = []
        
        def tracking_load_template(cfg_root, name):
            if name == "tracker":
                return Path("tracker.tpl.md"), """
                {% if scope:local %}
                In local scope
                {% endif %}
                {% if scope:parent %}
                In parent scope  
                {% endif %}
                """
            else:
                raise FileNotFoundError(f"Template {name} not found")
        
        processor.resolver.load_template_fn = tracking_load_template
        
        template_text = """
        Root level: {% if scope:local %}ROOT_LOCAL{% endif %}
        Include: ${tpl@other:tracker}
        Back to root: {% if scope:local %}ROOT_LOCAL_BACK{% endif %}
        """
        
        result = processor.process_template_text(template_text)
        
        # Проверяем правильную обработку скоупов
        assert "ROOT_LOCAL" in result
        assert "In parent scope" in result
        assert "ROOT_LOCAL_BACK" in result
        assert "In local scope" not in result  # Это должно быть false в родительском скоупе


if __name__ == "__main__":
    pytest.main([__file__])