from __future__ import annotations

from pathlib import Path

from lg.cache.fs_cache import Cache
from lg.config.adaptive_loader import AdaptiveConfigLoader
from lg.config.adaptive_model import ModeOptions
from lg.run_context import RunContext
from lg.section_processor import SectionProcessor
from lg.stats import TokenService
from lg.stats.collector import StatsCollector
from lg.template.context import TemplateContext
from lg.types import RunOptions, SectionRef
from lg.vcs import NullVcs


def _write(tmp: Path, rel: str, text: str = "x") -> Path:
    p = tmp / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def _write_sections_yaml(tmp: Path, text: str) -> Path:
    p = tmp / "lg-cfg" / "sections.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_section_processor_integration(tmp_path: Path):
    """Тестирует интеграцию section_processor с manifest.builder."""
    
    # Создаем файловую структуру
    _write(tmp_path, "src/main.py", 'print("hello world")')
    _write(tmp_path, "src/utils.py", 'def helper():\n    return "test"')
    
    # Создаем конфигурацию секции
    _write_sections_yaml(tmp_path, """
py-files:
  extensions: [".py"]
  skip_empty: true
  filters:
    mode: allow
    allow:
      - "src/**"
""")
    
    # Создаем контекст выполнения
    run_ctx = _create_run_context(tmp_path)
    
    # Создаем коллектор статистики
    stats_collector = StatsCollector(
        tokenizer=run_ctx.tokenizer
    )
    
    # Создаем процессор секций
    section_processor = SectionProcessor(
        run_ctx=run_ctx,
        stats_collector=stats_collector
    )
    
    # Создаем контекст шаблона и ссылку на секцию
    template_ctx = TemplateContext(run_ctx)
    section_ref = SectionRef(
        name="py-files",
        scope_rel="",
        scope_dir=tmp_path
    )
    
    # Обрабатываем секцию
    rendered_section = section_processor.process_section(section_ref, template_ctx)
    
    # Проверяем результат
    assert rendered_section.ref == section_ref
    assert len(rendered_section.files) == 2
    assert rendered_section.text  # Должен быть не пустой текст
    
    # Проверяем что в тексте есть содержимое файлов
    assert "hello world" in rendered_section.text
    assert "def helper" in rendered_section.text
    
    # Проверяем файлы
    file_paths = {f.rel_path for f in rendered_section.files}
    assert "src/main.py" in file_paths
    assert "src/utils.py" in file_paths


def test_section_processor_with_conditional_filters(tmp_path: Path):
    """Тестирует работу section_processor с условными фильтрами."""
    
    # Создаем файловую структуру  
    _write(tmp_path, "src/main.py", 'print("main")')
    _write(tmp_path, "src/test_main.py", 'def test_main(): pass')
    _write(tmp_path, "docs/readme.md", '# README')
    
    # Конфигурация с условным фильтром
    _write_sections_yaml(tmp_path, """
all-files:
  extensions: [".py", ".md"]
  filters:
    mode: allow
    allow:
      - "**"
  when:
    - condition: "tag:minimal"
      block:
        - "**/*test*.py"
        - "docs/**"
""")
    
    # Тест 1: без тега minimal - все файлы включены
    run_ctx = _create_run_context(tmp_path, active_tags=set())
    stats_collector = StatsCollector(tokenizer=run_ctx.tokenizer)
    section_processor = SectionProcessor(run_ctx=run_ctx, stats_collector=stats_collector)
    
    template_ctx = TemplateContext(run_ctx)
    section_ref = SectionRef(name="all-files", scope_rel="", scope_dir=tmp_path)
    
    rendered_section = section_processor.process_section(section_ref, template_ctx)
    
    file_paths = {f.rel_path for f in rendered_section.files}
    assert len(file_paths) == 3
    assert "src/main.py" in file_paths
    assert "src/test_main.py" in file_paths
    assert "docs/readme.md" in file_paths
    
    # Тест 2: с тегом minimal - тестовые файлы и документация исключены
    run_ctx = _create_run_context(tmp_path, active_tags={"minimal"})
    stats_collector = StatsCollector(tokenizer=run_ctx.tokenizer)
    section_processor = SectionProcessor(run_ctx=run_ctx, stats_collector=stats_collector)
    
    template_ctx = TemplateContext(run_ctx)
    
    rendered_section = section_processor.process_section(section_ref, template_ctx)
    
    file_paths = {f.rel_path for f in rendered_section.files}
    assert len(file_paths) == 1
    assert "src/main.py" in file_paths
    assert "src/test_main.py" not in file_paths  # Заблокирован
    assert "docs/readme.md" not in file_paths    # Заблокирован


def _create_run_context(root: Path, active_tags: set | None = None) -> RunContext:
    """Вспомогательная функция для создания RunContext."""
    if active_tags is None:
        active_tags = set()
    
    tool_ver = "0.3.0"
    cache = Cache(root, enabled=None, fresh=False, tool_version=tool_ver)
    vcs = NullVcs()
    tokenizer = TokenService(root, "o3", cache=cache)
    adaptive_loader = AdaptiveConfigLoader(root)
    
    return RunContext(
        root=root,
        options=RunOptions(),
        cache=cache,
        vcs=vcs,
        tokenizer=tokenizer,
        adaptive_loader=adaptive_loader,
        mode_options=ModeOptions(),
        active_tags=active_tags
    )