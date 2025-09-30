"""
Тесты плейсхолдеров контекстов.

Проверяет функциональность включения контекстов:
- ${ctx:name} - локальные контексты
- ${ctx@origin:name} - адресные контексты
- Вложенные контексты и их корректная обработка
- Обработка ошибок и предотвращение бесконечной рекурсии
"""

from __future__ import annotations

import pytest

from lg.template import TemplateProcessingError
from .conftest import (
    basic_project, federated_project,
    create_template, render_template
)


def test_simple_context_placeholder(basic_project):
    """Тест простого включения контекста ${ctx:name}."""
    root = basic_project
    
    # Создаем вложенный контекст
    create_template(root, "shared-context", """# Shared Context

## Source Code Overview

${src}

## Documentation Overview

${docs}
""", "ctx")
    
    # Создаем главный контекст, который включает вложенный
    create_template(root, "main-with-nested-test", """# Main Context with Nested

This is the main context that includes a shared context.

${ctx:shared-context}

## Additional Testing

${tests}
""")
    
    result = render_template(root, "ctx:main-with-nested-test")
    
    # Проверяем, что содержимое вложенного контекста присутствует
    assert "Shared Context" in result
    assert "Source Code Overview" in result
    assert "Documentation Overview" in result
    
    # Проверяем содержимое секций из вложенного контекста
    assert "def main():" in result
    assert "Project Documentation" in result
    
    # Проверяем содержимое из главного контекста
    assert "This is the main context" in result
    assert "def test_main():" in result


def test_context_placeholder_in_subdirectory(basic_project):
    """Тест включения контекстов из поддиректорий."""
    root = basic_project
    
    # Создаем контексты в поддиректориях
    create_template(root, "reports/code-report", """# Code Report

## Implementation Status

${src}

---
Generated on $(date)
""", "ctx")
    
    create_template(root, "reports/docs-report", """# Documentation Report

## Current Documentation

${docs}

---  
Documentation is up to date.
""", "ctx")
    
    # Используем контексты из поддиректории
    create_template(root, "subdirs-ctx-test", """# Combined Reports

## Code Analysis

${ctx:reports/code-report}

## Documentation Analysis

${ctx:reports/docs-report}
""")
    
    result = render_template(root, "ctx:subdirs-ctx-test")
    
    assert "Code Report" in result
    assert "def main():" in result
    assert "Generated on $(date)" in result
    
    assert "Documentation Report" in result
    assert "Project Documentation" in result
    assert "Documentation is up to date." in result


def test_context_placeholder_not_found_error(basic_project):
    """Тест ошибки при включении несуществующего контекста."""
    root = basic_project
    
    create_template(root, "bad-context-test", """# Bad Context Test

${ctx:nonexistent-context}
""")
    
    with pytest.raises(TemplateProcessingError, match=r"Resource not found"):
        render_template(root, "ctx:bad-context-test")


def test_addressed_context_placeholder(federated_project):
    """Тест адресных плейсхолдеров контекстов ${ctx@origin:name}."""
    root = federated_project
    
    # Создаем контексты в дочерних скоупах
    create_template(root / "apps" / "web", "web-context", """# Web Context

## Web Application Overview

${web-src}

## Web Documentation

${web-docs}

This context covers the complete web application.
""", "ctx")
    
    create_template(root / "libs" / "core", "core-context", """# Core Context

## Core Library Implementation

${core-lib}

## Core Public API

${core-api}

This context covers the core library functionality.
""", "ctx")
    
    # Главный контекст с адресными включениями
    create_template(root, "addressed-contexts-test", """# System-Wide Context

## Project Overview

${overview}

## Web Application Context

${ctx@apps/web:web-context}

## Core Library Context

${ctx@libs/core:core-context}
""")
    
    result = render_template(root, "ctx:addressed-contexts-test")
    
    # Проверяем корневое содержимое
    assert "System-Wide Context" in result
    assert "Federated Project" in result
    
    # Проверяем содержимое из web контекста
    assert "Web Context" in result
    assert "export const App" in result
    assert "Deployment instructions" in result
    assert "complete web application" in result
    
    # Проверяем содержимое из core контекста
    assert "Core Context" in result
    assert "class Processor:" in result
    assert "def get_client():" in result
    assert "core library functionality" in result


def test_nested_context_includes(basic_project):
    """Тест вложенных включений контекстов (ctx включает другие ctx)."""
    root = basic_project
    
    # Создаем базовые контексты
    create_template(root, "base/code-ctx", """# Code Context

${src}
""", "ctx")
    
    create_template(root, "base/docs-ctx", """# Docs Context

${docs}
""", "ctx")
    
    # Промежуточный контекст, который объединяет базовые
    create_template(root, "combined-ctx", """# Combined Context

${ctx:base/code-ctx}

${ctx:base/docs-ctx}
""", "ctx")
    
    # Главный контекст, который включает промежуточный
    create_template(root, "nested-test", """# Nested Test

## Main Content

${ctx:combined-ctx}

## Additional Tests

${tests}
""")
    
    result = render_template(root, "ctx:nested-test")
    
    # Проверяем все уровни вложенности
    assert "Code Context" in result
    assert "Docs Context" in result
    assert "def main():" in result
    assert "Project Documentation" in result
    assert "def test_main():" in result


def test_multiple_context_placeholders_same_context(basic_project):
    """Тест множественных ссылок на один и тот же контекст."""
    root = basic_project
    
    create_template(root, "reusable-ctx", """# Reusable Context

This context can be included multiple times.

${src}
""", "ctx")
    
    create_template(root, "multiple-same-ctx-test", """# Multiple Same Context Test

## First Include

${ctx:reusable-ctx}

## Some Content Between

Intermediate content.

## Second Include

${ctx:reusable-ctx}
""")
    
    result = render_template(root, "ctx:multiple-same-ctx-test")
    
    # Содержимое контекста должно появиться дважды
    occurrences = result.count("Reusable Context")
    assert occurrences == 2
    
    occurrences = result.count("This context can be included multiple times.")
    assert occurrences == 2
    
    occurrences = result.count("def main():")
    assert occurrences == 2
    
    assert "Intermediate content." in result


def test_context_placeholder_with_templates_and_sections(basic_project):
    """Тест контекстов, комбинирующих шаблоны и секции."""
    root = basic_project
    
    # Создаем шаблон для использования в контексте
    create_template(root, "context-header", """# Generated Context Header

This context was generated automatically.
""", "tpl")
    
    # Создаем контекст, который использует и шаблоны, и секции
    create_template(root, "mixed-ctx", """${tpl:context-header}

## Source Implementation

${src}

## Documentation

${docs}

## Summary

This context combines templates and sections effectively.
""", "ctx")
    
    # Используем этот контекст
    create_template(root, "mixed-usage-test", """# Mixed Usage Test

${ctx:mixed-ctx}

## Additional Testing

${tests}
""")
    
    result = render_template(root, "ctx:mixed-usage-test")
    
    assert "Generated Context Header" in result
    assert "This context was generated automatically." in result
    assert "def main():" in result
    assert "Project Documentation" in result
    assert "This context combines templates and sections effectively." in result
    assert "def test_main():" in result


def test_context_placeholder_empty_context(basic_project):
    """Тест включения пустого контекста."""
    root = basic_project
    
    create_template(root, "empty-ctx", "", "ctx")
    
    create_template(root, "empty-context-test", """# Empty Context Test

Before empty context.
${ctx:empty-ctx}
After empty context.
""")
    
    result = render_template(root, "ctx:empty-context-test")
    
    assert "Before empty context." in result
    assert "After empty context." in result
    # Между ними не должно быть никакого контента от пустого контекста


def test_context_placeholder_whitespace_handling(basic_project):
    """Тест обработки пробелов вокруг плейсхолдеров контекстов."""
    root = basic_project
    
    create_template(root, "spaced-ctx", """Content with spaces.""", "ctx")
    
    create_template(root, "whitespace-ctx-test", """# Whitespace Test

Before context.
${ctx:spaced-ctx}
After context.

Indented:
    ${ctx:spaced-ctx}
End.
""")
    
    result = render_template(root, "ctx:whitespace-ctx-test")
    
    assert "Before context." in result
    assert "Content with spaces." in result
    assert "After context." in result
    assert "End." in result


def test_context_placeholder_mixed_local_and_addressed(federated_project):
    """Тест смешанных локальных и адресных включений контекстов."""
    root = federated_project
    
    # Локальный контекст
    create_template(root, "local-ctx", """# Local Context

${overview}
""", "ctx")
    
    # Адресные контексты в дочерних скоупах  
    create_template(root / "apps" / "web", "web-ctx", """# Web Context

${web-src}
""", "ctx")
    
    create_template(root / "libs" / "core", "core-ctx", """# Core Context

${core-lib}
""", "ctx")
    
    # Контекст, смешивающий все типы
    create_template(root, "mixed-contexts-test", """# Mixed Contexts Test

## Local Context

${ctx:local-ctx}

## Web Context (addressed)

${ctx@apps/web:web-ctx}

## Core Context (addressed)

${ctx@libs/core:core-ctx}
""")
    
    result = render_template(root, "ctx:mixed-contexts-test")
    
    # Локальный контекст
    assert "Local Context" in result
    assert "Federated Project" in result
    
    # Адресные контексты
    assert "Web Context" in result
    assert "export const App" in result
    
    assert "Core Context" in result
    assert "class Processor:" in result


def test_context_placeholder_case_sensitivity(basic_project):
    """Тест чувствительности к регистру в именах контекстов."""
    root = basic_project
    
    create_template(root, "CamelContext", """CamelContext content""", "ctx")
    
    # Правильный регистр должен работать
    create_template(root, "case-correct-ctx-test", """${ctx:CamelContext}""")
    result = render_template(root, "ctx:case-correct-ctx-test")
    assert "CamelContext content" in result
    
    # Имена шаблонов не чувствительны к регистру
    create_template(root, "case-error-ctx-test", """${ctx:camelcontext}""")
    result = render_template(root, "ctx:case-error-ctx-test")
    assert "CamelContext content" in result


@pytest.mark.parametrize("context_name,content_check", [
    ("shared-context", "Shared Context"),
    ("reports/code-report", "Code Report")
])
def test_context_placeholder_parametrized(basic_project, context_name, content_check):
    """Параметризованный тест различных контекстов."""
    root = basic_project
    
    # Подготавливаем контексты
    create_template(root, "shared-context", """# Shared Context

${src}
""", "ctx")
    
    create_template(root, "reports/code-report", """# Code Report

${src}
""", "ctx")
    
    create_template(root, f"param-ctx-test-{context_name.replace('/', '-')}", f"""# Param Test

${{ctx:{context_name}}}
""")
    
    result = render_template(root, f"ctx:param-ctx-test-{context_name.replace('/', '-')}")
    assert content_check in result


def test_context_vs_template_placeholder_distinction(basic_project):
    """Тест различения плейсхолдеров контекстов и шаблонов."""
    root = basic_project
    
    # Создаем и контекст, и шаблон с одинаковым именем
    create_template(root, "same-name", """# Template Same Name

This is a template.
""", "tpl")
    
    create_template(root, "same-name", """# Context Same Name

This is a context.

${src}
""", "ctx")
    
    # Используем оба типа плейсхолдеров
    create_template(root, "distinction-test", """# Distinction Test

## Template Include

${tpl:same-name}

## Context Include

${ctx:same-name}
""")
    
    result = render_template(root, "ctx:distinction-test")
    
    # Оба должны присутствовать с правильным содержимым
    assert "Template Same Name" in result
    assert "This is a template." in result
    
    assert "Context Same Name" in result
    assert "This is a context." in result
    assert "def main():" in result  # из секции src в контексте