#!/usr/bin/env python3
"""
Базовые тесты для SectionProcessor из LG V2.

Проверяют основную функциональность обработчика секций по запросу.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lg.section_processor import SectionProcessor
from lg.template.context import TemplateContext
from lg.run_context import RunContext
from lg.cache.fs_cache import Cache
from lg.vcs import NullVcs
from lg.stats import TokenService
from lg.types_v2 import SectionRef, FileEntry, RenderedSection
from lg.config.adaptive_loader import AdaptiveConfigLoader
from lg.config.adaptive_model import ModeOptions


class TestSectionProcessor:
    """Тесты для SectionProcessor."""

    @pytest.fixture
    def temp_workspace(self):
        """Временная рабочая область для тестов."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            
            # Создаем базовую структуру
            lg_cfg = workspace / "lg-cfg"
            lg_cfg.mkdir()
            
            # Создаем простой sections.yaml
            sections_yaml = lg_cfg / "sections.yaml"
            sections_yaml.write_text('''
test-section:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "**/*.py"
            ''', encoding="utf-8")
            
            # Создаем тестовый файл
            test_file = workspace / "test.py" 
            test_file.write_text('print("Hello, World!")\n', encoding="utf-8")
            
            yield workspace

    @pytest.fixture
    def mock_run_ctx(self, temp_workspace):
        """Mock RunContext для тестов."""
        # Создаем минимальный токенайзер
        tokenizer = Mock(spec=TokenService)
        tokenizer.model_info = Mock()
        tokenizer.model_info.label = "test-model"
        tokenizer.model_info.ctx_limit = 4000
        tokenizer.count_text = Mock(return_value=10)

        # Создаем адаптивный загрузчик
        adaptive_loader = Mock(spec=AdaptiveConfigLoader)
        
        # Настраиваем мок для тегов
        from lg.config.adaptive_model import TagsConfig
        mock_tags_config = TagsConfig()
        mock_tags_config.tag_sets = {}
        mock_tags_config.global_tags = {}
        adaptive_loader.get_tags_config.return_value = mock_tags_config
        
        # Создаем базовые опции режима
        mode_options = ModeOptions(
            vcs_mode="all",
            allow_tools=False,
            code_fence=True
        )
        
        # Создаем RunContext
        run_ctx = Mock(spec=RunContext)
        run_ctx.root = temp_workspace
        run_ctx.cache = Cache(temp_workspace / ".lg-cache", enabled=True)
        run_ctx.vcs = NullVcs()
        run_ctx.tokenizer = tokenizer
        run_ctx.adaptive_loader = adaptive_loader
        run_ctx.mode_options = mode_options
        run_ctx.active_tags = set()
        run_ctx.options = Mock()
        run_ctx.options.modes = {}
        
        return run_ctx

    @pytest.fixture
    def template_ctx(self, mock_run_ctx):
        """Mock TemplateContext для тестов."""
        return TemplateContext(mock_run_ctx)

    def test_section_processor_creation(self, mock_run_ctx):
        """Тест создания SectionProcessor."""
        processor = SectionProcessor(mock_run_ctx)
        
        assert processor.run_ctx == mock_run_ctx
        assert processor.cache == mock_run_ctx.cache
        assert processor.vcs == mock_run_ctx.vcs
        assert processor.tokenizer == mock_run_ctx.tokenizer
        assert isinstance(processor.section_cache, dict)
        assert isinstance(processor._config_cache, dict)

    def test_resolve_section_ref(self, mock_run_ctx, temp_workspace):
        """Тест разрешения ссылки на секцию."""
        processor = SectionProcessor(mock_run_ctx)
        
        section_ref = processor._resolve_section_ref("test-section")
        
        assert isinstance(section_ref, SectionRef)
        assert section_ref.name == "test-section"
        assert section_ref.scope_path == ""
        assert section_ref.cfg_path == temp_workspace / "lg-cfg"

    def test_compute_cache_key(self, mock_run_ctx, template_ctx):
        """Тест вычисления ключа кэша."""
        processor = SectionProcessor(mock_run_ctx)
        
        # Устанавливаем некоторые теги и режимы для тестирования
        template_ctx.current_state.active_tags.add("test-tag")
        template_ctx.current_state.active_modes["test-mode"] = "test-value"
        
        key1 = processor._compute_cache_key("test-section", template_ctx)
        key2 = processor._compute_cache_key("test-section", template_ctx)
        
        # Одинаковые параметры должны давать одинаковый ключ
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 16  # Усеченный SHA256
        
        # Изменение тегов должно дать другой ключ
        template_ctx.current_state.active_tags.add("another-tag")
        key3 = processor._compute_cache_key("test-section", template_ctx)
        assert key1 != key3

    def test_get_section_config(self, mock_run_ctx, temp_workspace):
        """Тест получения конфигурации секции."""
        processor = SectionProcessor(mock_run_ctx)
        
        # Тест получения существующей секции
        config = processor._get_section_config(temp_workspace, "test-section")
        assert config is not None
        assert config.extensions == [".py"]
        
        # Тест несуществующей секции
        config = processor._get_section_config(temp_workspace, "nonexistent-section")
        assert config is None

    def test_freeze_cfg(self, mock_run_ctx):
        """Тест заморозки конфигурации для кэширования."""
        processor = SectionProcessor(mock_run_ctx)
        
        # Тест с различными типами данных
        test_dict = {"key": "value", "nested": {"a": 1}}
        frozen = processor._freeze_cfg(test_dict)
        assert isinstance(frozen, tuple)
        
        # Проверяем, что одинаковые объекты дают одинаковые результаты
        frozen2 = processor._freeze_cfg(test_dict)
        assert frozen == frozen2
        
        # Проверяем с другими типами
        assert processor._freeze_cfg([1, 2, 3]) == (1, 2, 3)
        assert processor._freeze_cfg({1, 2, 3}) == (1, 2, 3)
        assert processor._freeze_cfg("string") == "string"

    @patch('lg.section_processor.get_adapter_for_path')
    @patch('lg.io.fs.read_text')
    def test_process_files_basic(self, mock_read_text, mock_get_adapter, mock_run_ctx, temp_workspace):
        """Базовый тест обработки файлов."""
        # Настраиваем моки
        mock_read_text.return_value = 'print("test")'
        
        mock_adapter_cls = Mock()
        mock_adapter_cls.name = "python"
        mock_adapter = Mock()
        mock_adapter.name = "python"
        mock_adapter.should_skip.return_value = False
        mock_adapter.process.return_value = ('processed_text', {'test_meta': 1})
        mock_adapter_cls.bind.return_value = mock_adapter
        mock_get_adapter.return_value = mock_adapter_cls
        
        processor = SectionProcessor(mock_run_ctx)
        
        # Создаем простой план с одним файлом
        from lg.types_v2 import SectionManifest, SectionPlan, FileGroup
        
        file_entry = FileEntry(
            abs_path=temp_workspace / "test.py",
            rel_path="test.py", 
            language_hint="python"
        )
        
        group = FileGroup(lang="python", entries=[file_entry])
        
        manifest = SectionManifest(
            ref=SectionRef("test-section", "", temp_workspace / "lg-cfg"),
            files=[file_entry],
            path_labels="auto"
        )
        
        plan = SectionPlan(
            manifest=manifest,
            groups=[group],
            md_only=False,
            use_fence=True,
            labels={"test.py": "test.py"}
        )
        
        template_ctx = TemplateContext(mock_run_ctx)
        processed_files = processor._process_files(plan, template_ctx)
        
        assert len(processed_files) == 1
        processed_file = processed_files[0]
        assert processed_file.rel_path == "test.py"
        assert processed_file.processed_text == "processed_text\n"
        assert processed_file.meta["test_meta"] == 1

    def test_conditional_filtering(self, mock_run_ctx, temp_workspace):
        """Тест условной фильтрации файлов."""
        # Создаем секцию с условными фильтрами
        sections_yaml = temp_workspace / "lg-cfg" / "sections.yaml"
        sections_yaml.write_text('''
conditional-section:
  extensions: [".py", ".js"]
  filters:
    mode: allow
    allow:
      - "**/*"
  when:
    - condition: "tag:python"
      allow:
        - "**/*.py"
      block:
        - "**/*.js"
    - condition: "tag:javascript"
      allow:
        - "**/*.js"
      block:
        - "**/*.py"
        ''', encoding="utf-8")
        
        # Создаем тестовые файлы
        py_file = temp_workspace / "test.py"
        py_file.write_text('print("Python")', encoding="utf-8")
        js_file = temp_workspace / "test.js" 
        js_file.write_text('console.log("JS");', encoding="utf-8")
        
        processor = SectionProcessor(mock_run_ctx)
        template_ctx = TemplateContext(mock_run_ctx)
        
        # Тест с тегом python - должен включить только .py файлы
        template_ctx.current_state.active_tags.add("python")
        
        section_ref = processor._resolve_section_ref("conditional-section")
        manifest = processor._build_section_manifest(section_ref, template_ctx)
        
        # Проверяем, что остался только Python файл
        py_files = [f for f in manifest.files if f.rel_path.endswith('.py')]
        js_files = [f for f in manifest.files if f.rel_path.endswith('.js')]
        
        assert len(py_files) > 0, "Python файл должен быть включен"
        assert len(js_files) == 0, "JavaScript файлы должны быть исключены"

    def test_cache_behavior(self, mock_run_ctx, template_ctx):
        """Тест поведения кэша.""" 
        from lg.types_v2 import RenderedSection
        
        processor = SectionProcessor(mock_run_ctx)
        
        # Создаем моки для результата обработки
        mock_result1 = RenderedSection(
            ref=Mock(),
            text="result1",
            files=[]
        )
        mock_result2 = RenderedSection(
            ref=Mock(),
            text="result2", 
            files=[]
        )
        
        call_count = 0
        def mock_full_processing(section_name, ctx):
            nonlocal call_count
            call_count += 1
            return mock_result1 if call_count == 1 else mock_result2
        
        # Мокируем весь пайплайн обработки, чтобы проверить только логику кэширования
        with patch.object(processor, '_resolve_section_ref') as mock_resolve, \
             patch.object(processor, '_build_section_manifest') as mock_manifest, \
             patch.object(processor, '_build_section_plan') as mock_plan, \
             patch.object(processor, '_process_files') as mock_files, \
             patch.object(processor, '_render_section') as mock_render:
            
            mock_render.side_effect = [mock_result1, mock_result2]
            
            # Первый вызов - должен выполнить полную обработку
            result1 = processor.process_section("test-section", template_ctx)
            assert len(processor.section_cache) == 1
            assert result1 is mock_result1
            
            # Второй вызов с тем же контекстом - должен вернуть из кэша
            result2 = processor.process_section("test-section", template_ctx)
            assert result1 is result2  # Должен быть тот же объект из кэша
            assert len(processor.section_cache) == 1  # Кэш не должен расти
            
            # Проверяем, что мокированные методы вызывались только один раз
            assert mock_resolve.call_count == 1
            assert mock_manifest.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__])