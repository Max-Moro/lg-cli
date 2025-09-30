"""
Тесты комплексных сценариев для плейсхолдеров.

Проверяет сложные случаи использования:
- Смешанные типы плейсхолдеров в одном шаблоне
- Каскадные включения через множественные скоупы
- Глубокая вложенность и сложные зависимости
- Интеграционные тесты полного цикла обработки
"""

from __future__ import annotations

import pytest

from lg.template import TemplateProcessingError
from .conftest import (
    basic_project, federated_project,
    create_template, render_template,
    create_complex_federated_templates
)


def test_all_placeholder_types_in_single_template(federated_project):
    """Тест всех типов плейсхолдеров в одном шаблоне."""
    root = federated_project
    
    # Создаем дополнительные шаблоны и контексты для теста
    create_template(root, "intro-tpl", """# System Introduction

This is a comprehensive system overview.
""", "tpl")
    
    create_template(root, "summary-ctx", """# Summary Context

## Quick Overview

${overview}
""", "ctx")
    
    create_template(root / "apps" / "web", "web-intro-tpl", """# Web Introduction

Modern web application built with TypeScript.
""", "tpl")
    
    create_template(root / "libs" / "core", "core-summary-ctx", """# Core Summary

${core-lib}
""", "ctx")
    
    # Шаблон, использующий все типы плейсхолдеров
    create_template(root, "comprehensive-test", """${tpl:intro-tpl}

## Project Structure

### Local Sections
${overview}
${root-config}

### Cross-Scope Sections
${@apps/web:web-src}
${@libs/core:core-lib}

### Local Templates
${tpl:intro-tpl}

### Cross-Scope Templates
${tpl@apps/web:web-intro-tpl}

### Local Contexts
${ctx:summary-ctx}

### Cross-Scope Contexts
${ctx@libs/core:core-summary-ctx}

## Conclusion

This template demonstrates all placeholder types working together.
""")
    
    result = render_template(root, "ctx:comprehensive-test")
    
    # Проверяем содержимое от всех типов плейсхолдеров
    
    # Локальные секции
    assert "Federated Project" in result
    
    # Cross-scope секции
    assert "export const App" in result
    assert "class Processor:" in result
    
    # Локальные шаблоны
    assert "System Introduction" in result
    assert "comprehensive system overview" in result
    
    # Cross-scope шаблоны
    assert "Web Introduction" in result
    assert "Modern web application" in result
    
    # Локальные контексты
    assert "Summary Context" in result
    assert "Quick Overview" in result
    
    # Cross-scope контексты
    assert "Core Summary" in result
    
    # Финальный текст
    assert "all placeholder types working together" in result


def test_cascading_includes_across_multiple_scopes(federated_project):
    """Тест каскадных включений через множественные скоупы."""
    root = federated_project
    
    # Создаем сложную структуру каскадных зависимостей
    paths = create_complex_federated_templates(root)
    
    result = render_template(root, "ctx:full-stack")
    
    # Проверяем, что все уровни каскада отработали
    assert "Project Overview" in result  # из project-overview.tpl
    assert "Federated Project" in result  # из секции overview
    
    assert "Web Application" in result  # из web-intro.tpl
    assert "export const App" in result  # из web-src секции
    
    assert "Core Library API" in result  # из api-docs.tpl
    assert "def get_client():" in result  # из core-api секции


def test_deeply_nested_mixed_placeholders(basic_project):
    """Тест глубоко вложенных смешанных плейсхолдеров."""
    root = basic_project
    
    # Создаем сложную иерархию вложенности
    
    # Уровень 4 (самый глубокий)
    create_template(root, "level4/content", """Deep content: ${src}""", "tpl")
    
    # Уровень 3
    create_template(root, "level3/wrapper", """# Level 3

${tpl:level4/content}
""", "ctx")
    
    # Уровень 2
    create_template(root, "level2/container", """# Level 2

${ctx:level3/wrapper}

Additional docs: ${docs}
""", "tpl")
    
    # Уровень 1
    create_template(root, "level1/main", """# Level 1

${tpl:level2/container}

Tests: ${tests}
""", "ctx")
    
    # Главный шаблон
    create_template(root, "deeply-nested-test", """# Deeply Nested Test

${ctx:level1/main}

## Summary

This demonstrates deep nesting of mixed placeholders.
""")
    
    result = render_template(root, "ctx:deeply-nested-test")
    
    # Проверяем, что все уровни отработали
    assert "Level 1" in result
    assert "Level 2" in result
    assert "Level 3" in result
    assert "Deep content:" in result
    assert "def main():" in result  # из src через level4
    assert "Project Documentation" in result  # из docs через level2
    assert "def test_main():" in result  # из tests через level1
    assert "deep nesting of mixed placeholders" in result


def test_multiple_file_groups_with_mixed_placeholders(basic_project):
    """Тест множественных групп файлов с смешанными плейсхолдерами."""
    root = basic_project
    
    # Создаем дополнительные файлы для тестирования группировки
    from .conftest import write_source_file
    
    write_source_file(root / "src" / "models" / "user.py", "class User: pass", "python")
    write_source_file(root / "src" / "models" / "product.py", "class Product: pass", "python")
    write_source_file(root / "src" / "api" / "handlers.py", "def handle_request(): pass", "python")
    
    # Создаем специализированные секции для новых файлов
    from .conftest import create_sections_yaml, get_basic_sections_config
    
    sections_config = get_basic_sections_config()
    sections_config.update({
        "models": {
            "extensions": [".py"],
            "code_fence": True,
            "filters": {
                "mode": "allow",
                "allow": ["/src/models/**"]
            }
        },
        "api": {
            "extensions": [".py"],
            "code_fence": True,
            "filters": {
                "mode": "allow",
                "allow": ["/src/api/**"]
            }
        }
    })
    create_sections_yaml(root, sections_config)
    
    # Создаем шаблоны для каждой группы
    create_template(root, "models-intro", """## Data Models

The following classes represent our data structures:
""", "tpl")
    
    create_template(root, "api-intro", """## API Layer

Request handling implementation:
""", "tpl")
    
    # Главный контекст с множественными группами
    create_template(root, "multiple-groups-test", """# Multiple File Groups Test

## Core Implementation
${src}

${tpl:models-intro}
${models}

${tpl:api-intro}
${api}

## Documentation
${docs}

## Testing Suite
${tests}
""")
    
    result = render_template(root, "ctx:multiple-groups-test")
    
    # Проверяем все группы файлов
    assert "def main():" in result  # из основного src
    assert "class User: pass" in result  # из models
    assert "class Product: pass" in result  # из models
    assert "def handle_request(): pass" in result  # из api
    assert "Project Documentation" in result  # из docs
    assert "def test_main():" in result  # из tests
    
    # Проверяем шаблоны
    assert "Data Models" in result
    assert "API Layer" in result


def test_error_handling_in_complex_scenarios(federated_project):
    """Тест обработки ошибок в сложных сценариях.""" 
    root = federated_project
    
    # Создаем шаблон с ошибкой в середине сложной структуры
    create_template(root, "error-in-middle", """# Error Test

## Valid Section
${overview}

## Invalid Section (should cause error)
${@apps/web:nonexistent-section}

## This should not be reached
${@libs/core:core-lib}
""")
    
    # Ошибка должна прерывать обработку
    with pytest.raises(TemplateProcessingError, match=r"Section 'nonexistent-section' not found"):
        render_template(root, "ctx:error-in-middle")


def test_performance_with_large_number_of_placeholders(basic_project):
    """Тест производительности с большим количеством плейсхолдеров."""
    root = basic_project
    
    # Создаем шаблон с множественными повторениями
    placeholder_content = []
    for i in range(50):  # 50 повторений каждого типа
        placeholder_content.extend([
            f"## Section {i}",
            "${src}",
            f"## Docs {i}",
            "${docs}",
        ])
    
    template_content = "# Performance Test\n\n" + "\n\n".join(placeholder_content)
    
    create_template(root, "performance-test", template_content)
    
    # Рендеринг должен завершиться без ошибок (проверяем на основные маркеры)
    result = render_template(root, "ctx:performance-test")
    
    assert "Performance Test" in result
    assert "def main():" in result
    assert "Project Documentation" in result
    
    # Проверяем, что содержимое повторилось нужное количество раз
    main_occurrences = result.count("def main():")
    assert main_occurrences == 50


def test_mixed_addressing_schemes(federated_project):
    """Тест смешанных схем адресации в одном документе."""
    root = federated_project
    
    create_template(root, "mixed-addressing-test", """# Mixed Addressing Test

## Classic Addressing
${@apps/web:web-src}
${@libs/core:core-lib}

## Bracketed Addressing  
${@[apps/web]:web-docs}
${@[libs/core]:core-api}

## Local References
${overview}

## Mixed in Templates
${tpl@apps/web:web-intro}
${tpl@[libs/core]:api-docs}

## Mixed in Contexts
${ctx@apps/web:web-context}
${ctx@[libs/core]:core-context}
""")
    
    # Создаем необходимые шаблоны и контексты
    create_template(root / "apps" / "web", "web-intro", """Web intro content""", "tpl")
    create_template(root / "libs" / "core", "api-docs", """API docs content""", "tpl")
    create_template(root / "apps" / "web", "web-context", """Web context content""", "ctx")
    create_template(root / "libs" / "core", "core-context", """Core context content""", "ctx")
    
    result = render_template(root, "ctx:mixed-addressing-test")
    
    # Обе схемы адресации должны работать одинаково
    assert "export const App" in result  # из web-src (классическая адресация)
    assert "class Processor:" in result  # из core-lib (классическая адресация)
    assert "Deployment instructions" in result  # из web-docs (скобочная адресация)
    assert "def get_client():" in result  # из core-api (скобочная адресация)
    
    # Локальные ссылки
    assert "Federated Project" in result  # из overview
    
    # Смешанная адресация в шаблонах и контекстах
    assert "Web intro content" in result
    assert "API docs content" in result
    assert "Web context content" in result
    assert "Core context content" in result


def test_edge_case_empty_and_whitespace_handling(basic_project):
    """Тест граничных случаев с пустым содержимым и пробелами."""
    root = basic_project
    
    # Создаем пустые и почти пустые шаблоны
    create_template(root, "empty-tpl", "", "tpl")
    create_template(root, "whitespace-only-tpl", "   \n  \n   ", "tpl")
    create_template(root, "empty-ctx", "", "ctx")
    
    create_template(root, "edge-cases-test", """# Edge Cases Test

Before empty template:
${tpl:empty-tpl}
After empty template.

Before whitespace template:
${tpl:whitespace-only-tpl}
After whitespace template.

Before empty context:
${ctx:empty-ctx}
After empty context.

## Normal Content
${src}
""")
    
    result = render_template(root, "ctx:edge-cases-test")
    
    # Проверяем корректную обработку граничных случаев
    assert "Before empty template:" in result
    assert "After empty template." in result
    assert "Before whitespace template:" in result
    assert "After whitespace template." in result
    assert "Before empty context:" in result
    assert "After empty context." in result
    assert "def main():" in result


@pytest.mark.parametrize("complexity_level", [1, 3, 5])
def test_scalable_complexity_levels(basic_project, complexity_level):
    """Параметризованный тест различных уровней сложности."""
    root = basic_project
    
    # Создаем шаблон с переменной сложностью
    content_parts = ["# Scalable Complexity Test"]
    
    for level in range(complexity_level):
        create_template(root, f"level-{level}", f"""## Level {level}

Content at level {level}.
""", "tpl")
        
        content_parts.extend([
            f"## Level {level} Section",
            f"${{tpl:level-{level}}}",
            "${src}",
            "${docs}"
        ])
    
    template_content = "\n\n".join(content_parts)
    create_template(root, f"complexity-{complexity_level}", template_content)
    
    result = render_template(root, f"ctx:complexity-{complexity_level}")
    
    # Проверяем, что все уровни присутствуют
    for level in range(complexity_level):
        assert f"Level {level}" in result
        assert f"Content at level {level}" in result
    
    # Проверяем базовое содержимое
    assert "def main():" in result
    assert "Project Documentation" in result