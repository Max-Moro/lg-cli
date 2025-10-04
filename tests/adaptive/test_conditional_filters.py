"""
Тесты условной фильтрации файлов на разных уровнях иерархии FilterNode.

Проверяет работу условий when в конфигурации секций на корневом уровне
и на всех уровнях вложенности (children).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import (
    make_run_options, render_template, write,
    create_tags_yaml, TagConfig, TagSetConfig
)


@pytest.fixture
def hierarchical_project(tmp_path: Path) -> Path:
    """
    Создает проект с иерархической структурой для тестирования
    условных фильтров на разных уровнях.
    """
    root = tmp_path
    
    # Создаем структуру файлов
    write(root / "pyproject.toml", "[project]\nname = 'test'\n")
    write(root / "lg" / "cli.py", "# CLI module\n")
    write(root / "lg" / "types.py", "# Types module\n")
    write(root / "lg" / "engine.py", "# Engine module\n")
    
    # Подструктура config
    write(root / "lg" / "config" / "load.py", "# Config loader\n")
    write(root / "lg" / "config" / "model.py", "# Config models\n")
    write(root / "lg" / "config" / "extra.py", "# Extra config\n")
    
    # Подструктура adapters
    write(root / "lg" / "adapters" / "__init__.py", "# Adapters package\n")
    write(root / "lg" / "adapters" / "registry.py", "# Registry\n")
    write(root / "lg" / "adapters" / "base.py", "# Base adapter\n")
    write(root / "lg" / "adapters" / "markdown.py", "# Markdown adapter\n")
    
    # Подструктура template с плагинами
    write(root / "lg" / "template" / "processor.py", "# Template processor\n")
    write(root / "lg" / "template" / "context.py", "# Template context\n")
    write(root / "lg" / "template" / "common_placeholders" / "plugin.py", "# Common placeholders\n")
    write(root / "lg" / "template" / "adaptive" / "plugin.py", "# Adaptive plugin\n")
    write(root / "lg" / "template" / "md_placeholders" / "plugin.py", "# MD placeholders\n")
    
    # Создаем конфигурацию тегов с наборами для фич шаблонизатора
    tag_sets = {
        "template-features": TagSetConfig(
            title="Фичи шаблонизатора",
            tags={
                "common-placeholders": TagConfig(title="Базовые плейсхолдеры"),
                "adaptive": TagConfig(title="Адаптивные возможности"),
                "md-placeholders": TagConfig(title="Markdown плейсхолдеры")
            }
        )
    }
    global_tags = {
        "minimal": TagConfig(title="Минимальная версия")
    }
    create_tags_yaml(root, tag_sets, global_tags)
    
    return root


def test_root_level_conditional_filters(hierarchical_project):
    """Тест условных фильтров на корневом уровне секции."""
    root = hierarchical_project
    
    # Конфигурация с условиями на корневом уровне
    sections_yaml = """
src:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/cli.py"
      - "/lg/types.py"
    when:
      - condition: "tag:minimal"
        allow: ["/lg/engine.py"]
"""
    
    write(root / "lg-cfg" / "sections.yaml", sections_yaml)
    
    # Без тега minimal - только cli.py и types.py
    result1 = render_template(root, "sec:src", make_run_options())
    assert "cli.py" in result1
    assert "types.py" in result1
    assert "engine.py" not in result1
    
    # С тегом minimal - добавляется engine.py
    options = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "sec:src", options)
    assert "cli.py" in result2
    assert "types.py" in result2
    assert "engine.py" in result2


def test_child_level_conditional_filters(hierarchical_project):
    """Тест условных фильтров на уровне children."""
    root = hierarchical_project
    
    # Конфигурация с условиями на уровне children
    sections_yaml = """
src:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/"
    children:
      lg:
        mode: allow
        allow:
          - "/config/"
          - "/adapters/"
        when:
          - condition: "tag:minimal"
            allow: ["/types.py"]
"""
    
    write(root / "lg-cfg" / "sections.yaml", sections_yaml)
    
    # Без тега minimal - только config и adapters
    result1 = render_template(root, "sec:src", make_run_options())
    assert "config/load.py" in result1 or "config" in result1
    assert "adapters/base.py" in result1 or "adapters" in result1
    assert "lg/types.py" not in result1
    
    # С тегом minimal - добавляется types.py
    options = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "sec:src", options)
    assert "config" in result2
    assert "adapters" in result2
    assert "types.py" in result2


def test_deep_nested_conditional_filters(hierarchical_project):
    """Тест условных фильтров на глубоко вложенных уровнях."""
    root = hierarchical_project
    
    # Конфигурация с условиями на глубоко вложенном уровне
    sections_yaml = """
src:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/"
    children:
      lg:
        mode: allow
        allow:
          - "/template/"
        children:
          template:
            mode: allow
            allow:
              - "/*.py"
            when:
              - condition: "TAGSET:template-features:common-placeholders"
                allow: ["/common_placeholders/"]
              - condition: "TAGSET:template-features:adaptive"
                allow: ["/adaptive/"]
              - condition: "TAGSET:template-features:md-placeholders"
                allow: ["/md_placeholders/"]
"""
    
    write(root / "lg-cfg" / "sections.yaml", sections_yaml)
    
    # Без активных тегов из template-features - все плагины включены
    result1 = render_template(root, "sec:src", make_run_options())
    assert "processor.py" in result1
    assert "common_placeholders" in result1
    assert "adaptive" in result1
    assert "md_placeholders" in result1
    
    # С активным common-placeholders - только он и базовые файлы
    options2 = make_run_options(extra_tags={"common-placeholders"})
    result2 = render_template(root, "sec:src", options2)
    assert "processor.py" in result2
    assert "common_placeholders" in result2
    assert "adaptive" not in result2
    assert "md_placeholders" not in result2
    
    # С активным adaptive - только он и базовые файлы
    options3 = make_run_options(extra_tags={"adaptive"})
    result3 = render_template(root, "sec:src", options3)
    assert "processor.py" in result3
    assert "common_placeholders" not in result3
    assert "adaptive" in result3
    assert "md_placeholders" not in result3


def test_multiple_conditional_filters_same_level(hierarchical_project):
    """Тест нескольких условных фильтров на одном уровне."""
    root = hierarchical_project
    
    sections_yaml = """
src:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/"
    children:
      lg:
        mode: allow
        allow:
          - "/config/load.py"
        when:
          - condition: "tag:minimal"
            allow: ["/adapters/"]
          - condition: "NOT tag:minimal"
            allow: ["/template/"]
"""
    
    write(root / "lg-cfg" / "sections.yaml", sections_yaml)
    
    # Без тега minimal - config и template
    result1 = render_template(root, "sec:src", make_run_options())
    assert "config/load.py" in result1
    assert "adapters" not in result1
    assert "template" in result1
    
    # С тегом minimal - config и adapters
    options = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "sec:src", options)
    assert "config/load.py" in result2
    assert "adapters" in result2
    assert "template" not in result2


def test_conditional_filters_with_block_rules(hierarchical_project):
    """Тест условных фильтров с правилами блокировки."""
    root = hierarchical_project
    
    sections_yaml = """
src:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/"
    children:
      lg:
        mode: allow
        allow:
          - "/config/"
          - "/adapters/"
        when:
          - condition: "tag:minimal"
            block: ["/config/extra.py"]
"""
    
    write(root / "lg-cfg" / "sections.yaml", sections_yaml)
    
    # Без тега minimal - все файлы config включены
    result1 = render_template(root, "sec:src", make_run_options())
    assert "config/load.py" in result1
    assert "config/model.py" in result1
    assert "config/extra.py" in result1
    
    # С тегом minimal - extra.py заблокирован
    options = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "sec:src", options)
    assert "config/load.py" in result2
    assert "config/model.py" in result2
    assert "config/extra.py" not in result2


def test_conditional_filters_inheritance(hierarchical_project):
    """Тест наследования условных фильтров по уровням."""
    root = hierarchical_project
    
    sections_yaml = """
src:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/"
    when:
      - condition: "tag:minimal"
        allow: ["/pyproject.toml"]
    children:
      lg:
        mode: allow
        allow:
          - "/config/"
        when:
          - condition: "tag:minimal"
            allow: ["/adapters/"]
"""
    
    write(root / "lg-cfg" / "sections.yaml", sections_yaml)
    
    # Без тега minimal - только config
    result1 = render_template(root, "sec:src", make_run_options())
    assert "pyproject.toml" not in result1
    assert "config" in result1
    assert "adapters" not in result1
    
    # С тегом minimal - оба уровня применяются
    options = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "sec:src", options)
    assert "pyproject.toml" in result2
    assert "config" in result2
    assert "adapters" in result2


def test_conditional_filters_complex_conditions(hierarchical_project):
    """Тест условных фильтров со сложными условиями."""
    root = hierarchical_project
    
    sections_yaml = """
src:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/"
    children:
      lg:
        mode: allow
        allow:
          - "/config/"
        when:
          - condition: "TAGSET:template-features:adaptive OR tag:minimal"
            allow: ["/template/"]
          - condition: "tag:minimal"
            allow: ["/adapters/"]
"""
    
    write(root / "lg-cfg" / "sections.yaml", sections_yaml)
    
    # Без тегов - template включен (TAGSET без активных тегов = true)
    result1 = render_template(root, "sec:src", make_run_options())
    assert "config" in result1
    assert "template" in result1
    assert "adapters" not in result1
    
    # С minimal - template и adapters включены
    options2 = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "sec:src", options2)
    assert "config" in result2
    assert "template" in result2
    assert "adapters" in result2
    
    # С adaptive из TAGSET - template включен, adapters нет (minimal не активен)
    options3 = make_run_options(extra_tags={"adaptive"})
    result3 = render_template(root, "sec:src", options3)
    assert "config" in result3
    assert "template" in result3
    assert "adapters" not in result3


def test_conditional_filters_evaluation_error_handling(hierarchical_project):
    """Тест обработки ошибок при вычислении условий."""
    root = hierarchical_project
    
    # Конфигурация с невалидным условием
    sections_yaml = """
src:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/lg/"
    when:
      - condition: "tag:valid"
        allow: ["/pyproject.toml"]
      - condition: "invalid_syntax @@@ ???"
        allow: ["/lg/cli.py"]
      - condition: "tag:another_valid"
        allow: ["/lg/types.py"]
"""
    
    write(root / "lg-cfg" / "sections.yaml", sections_yaml)
    
    # Должно обработаться без падения, но с предупреждением
    # Валидные условия должны применяться
    options = make_run_options(extra_tags={"valid", "another_valid"})
    result = render_template(root, "sec:src", options)
    
    # Валидные условия сработали
    assert "pyproject.toml" in result
    assert "lg/types.py" in result
    
    # Невалидное условие игнорируется (не падает весь процесс)
    # cli.py может быть или не быть в зависимости от базовых правил


def test_example_from_issue(tmp_path):
    """
    Тест примера из задачи - иерархическая конфигурация с условными фильтрами.
    
    Проверяет работу условий на уровне lg/template/when.
    """
    root = tmp_path
    
    # Создаем структуру из примера
    write(root / "pyproject.toml", "[project]\nname = 'lg'\n")
    write(root / "lg" / "cli.py", "# CLI\n")
    write(root / "lg" / "types.py", "# Types\n")
    write(root / "lg" / "engine.py", "# Engine\n")
    write(root / "lg" / "section_processor.py", "# Section processor\n")
    
    write(root / "lg" / "config" / "load.py", "# Load\n")
    write(root / "lg" / "config" / "model.py", "# Model\n")
    
    write(root / "lg" / "adapters" / "__init__.py", "# Init\n")
    write(root / "lg" / "adapters" / "registry.py", "# Registry\n")
    write(root / "lg" / "adapters" / "base.py", "# Base\n")
    write(root / "lg" / "adapters" / "processor.py", "# Processor\n")
    write(root / "lg" / "adapters" / "markdown.py", "# Markdown\n")
    
    write(root / "lg" / "template" / "processor.py", "# Template processor\n")
    write(root / "lg" / "template" / "common.py", "# Template common\n")
    write(root / "lg" / "template" / "common_placeholders" / "plugin.py", "# Common placeholders plugin\n")
    write(root / "lg" / "template" / "adaptive" / "plugin.py", "# Adaptive plugin\n")
    write(root / "lg" / "template" / "md_placeholders" / "plugin.py", "# MD placeholders plugin\n")
    
    # Конфигурация из примера задачи
    sections_yaml = """
src:
  extensions: [".py", ".toml"]
  filters:
    mode: allow
    allow:
      - "/pyproject.toml"
      - "/lg/"
    children:
      lg:
        mode: allow
        allow:
          - "/cli.py"
          - "/types.py"
          - "/engine.py"
          - "/section_processor.py"
          - "/config/"
          - "/adapters/"
          - "/template/"
        children:
          config:
            mode: allow
            allow:
              - "/load.py"
              - "/model.py"
          adapters:
            mode: allow
            allow:
              - "/__init__.py"
              - "/registry.py"
              - "/base.py"
              - "/processor.py"
              - "/markdown.py"
          template:
            mode: allow
            allow:
              - "/*.py"
            when:
              - condition: "TAGSET:template-features:common-placeholders"
                allow: ["/common_placeholders/"]
              - condition: "TAGSET:template-features:adaptive"
                allow: ["/adaptive/"]
              - condition: "TAGSET:template-features:md-placeholders"
                allow: ["/md_placeholders/"]
"""
    
    # Создаем теги
    tag_sets = {
        "template-features": TagSetConfig(
            title="Фичи шаблонизатора",
            tags={
                "common-placeholders": TagConfig(title="Базовые плейсхолдеры"),
                "adaptive": TagConfig(title="Адаптивные возможности"),
                "md-placeholders": TagConfig(title="Markdown плейсхолдеры")
            }
        )
    }
    create_tags_yaml(root, tag_sets, {})
    
    write(root / "lg-cfg" / "sections.yaml", sections_yaml)
    
    # Тест 1: Без активных тегов - все плагины включены
    result1 = render_template(root, "sec:src", make_run_options())
    assert "pyproject.toml" in result1
    assert "lg/cli.py" in result1
    assert "config/load.py" in result1
    assert "adapters/__init__.py" in result1
    assert "template/processor.py" in result1 or "template/common.py" in result1
    assert "common_placeholders" in result1
    assert "adaptive" in result1
    assert "md_placeholders" in result1
    
    # Тест 2: С активным common-placeholders - только этот плагин
    options2 = make_run_options(extra_tags={"common-placeholders"})
    result2 = render_template(root, "sec:src", options2)
    assert "pyproject.toml" in result2
    assert "template/processor.py" in result2 or "template/common.py" in result2
    assert "common_placeholders" in result2
    assert "adaptive" not in result2
    assert "md_placeholders" not in result2
    
    # Тест 3: С активным adaptive - только этот плагин
    options3 = make_run_options(extra_tags={"adaptive"})
    result3 = render_template(root, "sec:src", options3)
    assert "template/processor.py" in result3 or "template/common.py" in result3
    assert "common_placeholders" not in result3
    assert "adaptive" in result3
    assert "md_placeholders" not in result3
