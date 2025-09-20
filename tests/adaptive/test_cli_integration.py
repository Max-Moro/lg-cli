"""
Тесты CLI интерфейса для адаптивных возможностей.

Проверяет команды list mode-sets, list tag-sets и использование
флагов --mode и --tags через CLI интерфейс.
"""

from __future__ import annotations

from tests.conftest import run_cli, jload
from .conftest import adaptive_project, federated_project


def test_list_mode_sets_cli(adaptive_project, monkeypatch):
    """Тест команды lg list mode-sets."""
    root = adaptive_project
    monkeypatch.chdir(root)
    
    result = run_cli(root, "list", "mode-sets")
    
    assert result.returncode == 0
    data = jload(result.stdout)
    
    # Проверяем структуру ответа
    assert "mode-sets" in data
    mode_sets = data["mode-sets"]
    
    # Проверяем наличие ожидаемых наборов режимов
    mode_set_ids = {ms["id"] for ms in mode_sets}
    assert "ai-interaction" in mode_set_ids
    assert "dev-stage" in mode_set_ids
    
    # Проверяем структуру одного набора
    ai_set = next(ms for ms in mode_sets if ms["id"] == "ai-interaction")
    assert ai_set["title"] == "Способ работы с AI"
    assert "modes" in ai_set
    
    # Проверяем режимы внутри набора
    modes = {m["id"]: m for m in ai_set["modes"]}
    assert "ask" in modes
    assert "agent" in modes
    
    agent_mode = modes["agent"]
    assert agent_mode["title"] == "Агентная работа"
    assert "tags" in agent_mode
    assert "agent" in agent_mode["tags"]
    assert "tools" in agent_mode["tags"]


def test_list_tag_sets_cli(adaptive_project, monkeypatch):
    """Тест команды lg list tag-sets."""
    root = adaptive_project
    monkeypatch.chdir(root)
    
    result = run_cli(root, "list", "tag-sets")
    
    assert result.returncode == 0
    data = jload(result.stdout)
    
    # Проверяем структуру ответа
    assert "tag-sets" in data
    tag_sets = data["tag-sets"]
    
    # Проверяем наличие ожидаемых наборов тегов
    tag_set_ids = {ts["id"] for ts in tag_sets}
    assert "language" in tag_set_ids
    assert "code-type" in tag_set_ids
    
    # Проверяем глобальные теги
    global_set = next((ts for ts in tag_sets if ts["id"] == "global"), None)
    if global_set:
        global_tags = {t["id"] for t in global_set["tags"]}
        assert "agent" in global_tags
        assert "review" in global_tags
        assert "minimal" in global_tags


def test_render_with_mode_flags(adaptive_project, monkeypatch):
    """Тест рендеринга с флагами --mode.""" 
    from tests.conftest import write
    
    root = adaptive_project
    monkeypatch.chdir(root)
    
    # Создаем простой контекст для тестирования
    write(root / "lg-cfg" / "mode-test.ctx.md", """# Mode Test

{% if tag:agent %}
## Agent Mode Active
{% endif %}

{% if tag:tests %}  
## Test Mode Active
{% endif %}

## Content
${src}
""")
    
    # Тест без режимов
    result1 = run_cli(root, "render", "ctx:mode-test")
    assert result1.returncode == 0
    assert "Agent Mode Active" not in result1.stdout
    assert "Test Mode Active" not in result1.stdout
    assert "Content" in result1.stdout
    
    # Тест с одним режимом
    result2 = run_cli(root, "render", "ctx:mode-test", "--mode", "ai-interaction:agent")
    assert result2.returncode == 0
    assert "Agent Mode Active" in result2.stdout
    assert "Test Mode Active" not in result2.stdout
    
    # Тест с несколькими режимами  
    result3 = run_cli(root, "render", "ctx:mode-test", 
                      "--mode", "ai-interaction:agent",
                      "--mode", "dev-stage:testing")
    assert result3.returncode == 0
    assert "Agent Mode Active" in result3.stdout
    assert "Test Mode Active" in result3.stdout


def test_render_with_tags_flags(adaptive_project, monkeypatch):
    """Тест рендеринга с флагом --tags."""
    from tests.conftest import write
    
    root = adaptive_project
    monkeypatch.chdir(root)
    
    # Создаем контекст для тестирования тегов
    write(root / "lg-cfg" / "tags-test.ctx.md", """# Tags Test

{% if tag:minimal %}
## Minimal Version
{% endif %}

{% if tag:python %}
## Python Content
{% endif %}

{% if tag:review %}
## Review Mode
{% endif %}

## Base Content
${docs}
""")
    
    # Тест без дополнительных тегов
    result1 = run_cli(root, "render", "ctx:tags-test")
    assert result1.returncode == 0
    assert "Minimal Version" not in result1.stdout
    assert "Python Content" not in result1.stdout
    
    # Тест с одним тегом
    result2 = run_cli(root, "render", "ctx:tags-test", "--tags", "minimal")
    assert result2.returncode == 0
    assert "Minimal Version" in result2.stdout
    assert "Python Content" not in result2.stdout
    
    # Тест с несколькими тегами
    result3 = run_cli(root, "render", "ctx:tags-test", "--tags", "minimal,python,review")
    assert result3.returncode == 0
    assert "Minimal Version" in result3.stdout
    assert "Python Content" in result3.stdout
    assert "Review Mode" in result3.stdout


def test_combined_modes_and_tags_cli(adaptive_project, monkeypatch):
    """Тест комбинированного использования --mode и --tags."""
    from tests.conftest import write
    
    root = adaptive_project
    monkeypatch.chdir(root)
    
    write(root / "lg-cfg" / "combined-test.ctx.md", """# Combined Test

{% if tag:agent %}
## Agent from Mode: {{ tag:agent }}
{% endif %}

{% if tag:tools %}
## Tools from Mode: {{ tag:tools }}
{% endif %}

{% if tag:custom %}
## Custom from Tags: {{ tag:custom }}
{% endif %}

${src}
""")
    
    # Комбинируем режим (который активирует agent, tools) с дополнительным тегом
    result = run_cli(root, "render", "ctx:combined-test",
                     "--mode", "ai-interaction:agent",
                     "--tags", "custom")
    
    assert result.returncode == 0
    # Теги из режима должны активироваться
    assert "Agent from Mode" in result.stdout
    assert "Tools from Mode" in result.stdout  
    # Дополнительный тег тоже должен работать
    assert "Custom from Tags" in result.stdout


def test_report_with_adaptive_options(adaptive_project, monkeypatch):
    """Тест команды report с адаптивными опциями."""
    root = adaptive_project
    monkeypatch.chdir(root)
    
    result = run_cli(root, "report", "sec:src",
                     "--mode", "dev-stage:review", 
                     "--tags", "python")
    
    assert result.returncode == 0
    data = jload(result.stdout)
    
    # Проверяем базовую структуру отчета
    assert "protocol" in data
    assert "target" in data
    assert "total" in data
    assert "files" in data
    
    # Проверяем, что отчет содержит файлы
    assert len(data["files"]) > 0
    
    # Проверяем метаданные
    assert data["target"] == "src"
    assert data["scope"] == "section"


def test_invalid_mode_cli_error(adaptive_project, monkeypatch):
    """Тест обработки ошибки неверного режима через CLI."""
    root = adaptive_project
    monkeypatch.chdir(root)
    
    # Неверный набор режимов
    result1 = run_cli(root, "render", "sec:src", "--mode", "invalid:mode")
    assert result1.returncode == 2
    assert "Unknown mode set 'invalid'" in result1.stderr
    
    # Неверный режим в правильном наборе
    result2 = run_cli(root, "render", "sec:src", "--mode", "ai-interaction:invalid")
    assert result2.returncode == 2
    assert "Unknown mode 'invalid' in mode set 'ai-interaction'" in result2.stderr


def test_invalid_mode_format_cli_error(adaptive_project, monkeypatch):
    """Тест обработки неверного формата режима."""
    root = adaptive_project
    monkeypatch.chdir(root)
    
    # Неверный формат (без двоеточия)
    result = run_cli(root, "render", "sec:src", "--mode", "invalid-format")
    assert result.returncode == 2
    assert "Invalid mode format" in result.stderr


def test_federated_modes_cli(federated_project, monkeypatch):
    """Тест CLI команд с федеративной структурой."""
    root = federated_project
    monkeypatch.chdir(root)
    
    # Проверяем list mode-sets в федеративном проекте
    result = run_cli(root, "list", "mode-sets")
    assert result.returncode == 0
    
    data = jload(result.stdout)
    mode_set_ids = {ms["id"] for ms in data["mode-sets"]}
    
    # Должны быть режимы из всех скоупов
    assert "workflow" in mode_set_ids      # корневой
    assert "frontend" in mode_set_ids      # apps/web  
    assert "library" in mode_set_ids       # libs/core


def test_federated_rendering_cli(federated_project, monkeypatch):
    """Тест рендеринга с режимами из дочерних скоупов через CLI."""
    from tests.conftest import write
    
    root = federated_project
    monkeypatch.chdir(root)
    
    # Создаем тестовый контекст
    write(root / "lg-cfg" / "fed-test.ctx.md", """# Federated Test

{% if tag:typescript %}
## TypeScript Mode
{% endif %}

{% if tag:python %}
## Python Mode  
{% endif %}

## Overview
${overview}
""")
    
    # Активируем режим из дочернего скоупа
    result = run_cli(root, "render", "ctx:fed-test", "--mode", "frontend:ui")
    assert result.returncode == 0
    assert "TypeScript Mode" in result.stdout
    assert "Python Mode" not in result.stdout
    
    # Активируем режим из другого дочернего скоупа
    result2 = run_cli(root, "render", "ctx:fed-test", "--mode", "library:internals")
    assert result2.returncode == 0
    assert "Python Mode" in result2.stdout
    assert "TypeScript Mode" not in result2.stdout


def test_empty_tags_parameter(adaptive_project, monkeypatch):
    """Тест пустого параметра --tags."""
    root = adaptive_project
    monkeypatch.chdir(root)
    
    # Пустая строка тегов должна работать как отсутствие тегов
    result = run_cli(root, "render", "sec:src", "--tags", "")
    assert result.returncode == 0
    assert len(result.stdout) > 0


def test_whitespace_in_tags_parameter(adaptive_project, monkeypatch):
    """Тест обработки пробелов в параметре --tags."""
    from tests.conftest import write
    
    root = adaptive_project  
    monkeypatch.chdir(root)
    
    write(root / "lg-cfg" / "whitespace-test.ctx.md", """# Whitespace Test

{% if tag:minimal %}
## Minimal Active
{% endif %}

{% if tag:python %}
## Python Active
{% endif %}
""")
    
    # Тестируем пробелы вокруг тегов
    result = run_cli(root, "render", "ctx:whitespace-test", "--tags", " minimal , python ")
    assert result.returncode == 0
    assert "Minimal Active" in result.stdout
    assert "Python Active" in result.stdout


def test_multiple_mode_parameters(adaptive_project, monkeypatch):
    """Тест множественных параметров --mode."""
    from tests.conftest import write
    
    root = adaptive_project
    monkeypatch.chdir(root)
    
    write(root / "lg-cfg" / "multi-mode-test.ctx.md", """# Multi Mode Test

{% if tag:agent %}
## Agent: Active
{% endif %}

{% if tag:tests %}
## Tests: Active  
{% endif %}

{% if tag:review %}
## Review: Active
{% endif %}
""")
    
    # Используем несколько --mode флагов
    result = run_cli(root, "render", "ctx:multi-mode-test",
                     "--mode", "ai-interaction:agent",
                     "--mode", "dev-stage:testing")
    
    assert result.returncode == 0
    assert "Agent: Active" in result.stdout
    assert "Tests: Active" in result.stdout
    assert "Review: Active" not in result.stdout