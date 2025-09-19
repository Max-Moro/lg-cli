from __future__ import annotations

from pathlib import Path

import pytest

from lg.config.adaptive_model import ModeOptions
from lg.manifest.builder_v2 import build_section_manifest
from lg.run_context import RunContext
from lg.template.context import TemplateContext, TemplateState
from lg.types_v2 import SectionRef
from lg.vcs import NullVcs
from lg.cache.fs_cache import Cache
from lg.config.adaptive_loader import AdaptiveConfigLoader
from lg.stats import TokenService
from lg.types import RunOptions


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


def test_basic_section_manifest_v2(tmp_path: Path):
    """Тестирует базовую функциональность build_section_manifest."""
    
    # Создаем файловую структуру
    _write(tmp_path, "src/main.py", "print('hello')")
    _write(tmp_path, "src/utils.py", "def helper(): pass")
    _write(tmp_path, "tests/test_main.py", "def test(): pass")
    
    # Создаем конфигурацию секции
    _write_sections_yaml(tmp_path, """
py-files:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "src/**"
      - "tests/**"
""")
    
    # Создаем контекст выполнения
    tool_ver = "0.3.0"
    cache = Cache(tmp_path, enabled=None, fresh=False, tool_version=tool_ver)
    vcs = NullVcs()
    tokenizer = TokenService(tmp_path, "o3", cache=cache)
    adaptive_loader = AdaptiveConfigLoader(tmp_path)
    
    run_ctx = RunContext(
        root=tmp_path,
        options=RunOptions(),
        cache=cache,
        vcs=vcs,
        tokenizer=tokenizer,
        adaptive_loader=adaptive_loader,
        mode_options=ModeOptions(),
        active_tags=set()
    )
    
    # Создаем контекст шаблона
    template_ctx = TemplateContext(run_ctx)
    
    # Создаем ссылку на секцию
    section_ref = SectionRef(
        name="py-files",
        scope_rel="",
        scope_dir=tmp_path
    )
    
    # Строим манифест
    manifest = build_section_manifest(
        section_ref=section_ref,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=vcs,
        vcs_mode="all"
    )
    
    # Проверяем результат
    assert manifest.ref == section_ref
    assert len(manifest.files) == 3
    
    # Проверяем что все файлы правильно включены
    file_paths = {f.rel_path for f in manifest.files}
    assert "src/main.py" in file_paths
    assert "src/utils.py" in file_paths  
    assert "tests/test_main.py" in file_paths


def test_conditional_filters_v2(tmp_path: Path):
    """Тестирует работу условных фильтров."""
    
    # Создаем файловую структуру
    _write(tmp_path, "src/main.py", "print('hello')")
    _write(tmp_path, "src/test_main.py", "def test(): pass")
    _write(tmp_path, "docs/readme.md", "# README")
    
    # Создаем конфигурацию с условными фильтрами
    _write_sections_yaml(tmp_path, """
all-files:
  extensions: [".py", ".md"]
  filters:
    mode: allow
    allow:
      - "src/**"
      - "docs/**"
  when:
    - condition: "tag:tests"
      allow:
        - "**/*test*.py"
    - condition: "NOT tag:tests"
      block:
        - "**/*test*.py"
""")
    
    # Тест 1: без тега tests - test файлы должны быть заблокированы
    run_ctx = _create_run_context(tmp_path, active_tags=set())
    template_ctx = TemplateContext(run_ctx)
    
    section_ref = SectionRef(name="all-files", scope_rel="", scope_dir=tmp_path)
    
    manifest = build_section_manifest(
        section_ref=section_ref,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=NullVcs(),
        vcs_mode="all"
    )
    
    file_paths = {f.rel_path for f in manifest.files}
    assert "src/main.py" in file_paths
    assert "src/test_main.py" not in file_paths  # Заблокирован условным фильтром
    assert "docs/readme.md" in file_paths
    
    # Тест 2: с тегом tests - test файлы должны быть включены
    run_ctx = _create_run_context(tmp_path, active_tags={"tests"})
    template_ctx = TemplateContext(run_ctx)
    
    manifest = build_section_manifest(
        section_ref=section_ref,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=NullVcs(),
        vcs_mode="all"
    )
    
    file_paths = {f.rel_path for f in manifest.files}
    assert "src/main.py" in file_paths
    assert "src/test_main.py" in file_paths  # Разрешен условным фильтром
    assert "docs/readme.md" in file_paths


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