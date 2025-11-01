"""
Тесты плейсхолдеров шаблонов.

Проверяет функциональность включения шаблонов:
- ${tpl:name} - локальные шаблоны
- ${tpl@origin:name} - адресные шаблоны  
- Вложенные включения и рекурсивная обработка
- Обработка ошибок и циклических ссылок
"""

from __future__ import annotations

import pytest

from lg.template import TemplateProcessingError
from .conftest import (
    basic_project, federated_project,
    create_template, render_template, create_nested_template_structure
)


def test_simple_template_placeholder(basic_project):
    """Тест простого включения шаблона ${tpl:name}."""
    root = basic_project
    
    # Создаем базовый шаблон
    create_template(root, "intro", """# Project Introduction

This is a comprehensive overview of the project structure and functionality.

## Key Components

- Source code organization
- Documentation standards  
- Testing framework
""", "tpl")
    
    # Создаем контекст, который использует шаблон
    create_template(root, "with-intro-test", """# Complete Project Context

${tpl:intro}

## Implementation Details

${src}

## Documentation

${docs}
""")
    
    result = render_template(root, "ctx:with-intro-test")
    
    # Проверяем, что содержимое шаблона вставилось
    assert "Project Introduction" in result
    assert "comprehensive overview" in result
    assert "Key Components" in result
    
    # Проверяем, что остальное содержимое также присутствует
    assert "def main():" in result
    assert "Project Documentation" in result


def test_template_placeholder_in_subdirectory(basic_project):
    """Тест включения шаблонов из поддиректорий."""
    root = basic_project
    
    # Создаем шаблон в поддиректории
    create_template(root, "common/header", """# Standard Header

Project: Test Application  
Version: 1.0.0  
Generated: $(date)
""", "tpl")
    
    create_template(root, "common/footer", """---

© 2024 Test Project. All rights reserved.
""", "tpl")
    
    # Используем шаблоны из поддиректории
    create_template(root, "subdirs-test", """${tpl:common/header}

## Main Content

${src}

${tpl:common/footer}
""")
    
    result = render_template(root, "ctx:subdirs-test")
    
    assert "Standard Header" in result
    assert "Project: Test Application" in result
    assert "def main():" in result
    assert "© 2024 Test Project" in result


def test_nested_template_includes(basic_project):
    """Тест вложенных включений шаблонов (tpl включает другие tpl)."""
    root = basic_project
    
    # Создаем структуру вложенных шаблонов
    paths = create_nested_template_structure(root)
    
    result = render_template(root, "ctx:basic-context")
    
    # Проверяем, что все уровни вложенности отработали
    assert "Project Introduction" in result  # из intro.tpl.md
    assert "Modular architecture" in result  # из intro.tpl.md
    assert "def main():" in result  # из секции src
    assert "Project Documentation" in result  # из секции docs
    assert "Contact Information" in result  # из footer.tpl.md
    assert "def test_main():" in result  # из секции tests


def test_template_placeholder_not_found_error(basic_project):
    """Тест ошибки при включении несуществующего шаблона.""" 
    root = basic_project
    
    create_template(root, "bad-template-test", """# Bad Template Test

${tpl:nonexistent-template}
""")
    
    with pytest.raises(TemplateProcessingError, match=r"Resource not found"):
        render_template(root, "ctx:bad-template-test")


def test_addressed_template_placeholder(federated_project):
    """Тест адресных плейсхолдеров шаблонов ${tpl@origin:name}."""
    root = federated_project
    
    # Создаем шаблоны в дочерних скоупах
    create_template(root / "apps" / "web", "web-summary", """# Web Application Summary

## Source Code

${web-src}

## Configuration  

The web app uses modern TypeScript and React.
""", "tpl")
    
    create_template(root / "libs" / "core", "core-summary", """# Core Library Summary

## Implementation

${core-lib}

## Public API

${core-api}
""", "tpl")
    
    # Главный контекст с адресными включениями
    create_template(root, "addressed-templates-test", """# Full System Overview

${overview}

## Web Application

${tpl@apps/web:web-summary}

## Core Library

${tpl@libs/core:core-summary}
""")
    
    result = render_template(root, "ctx:addressed-templates-test")
    
    # Проверяем содержимое из корневой секции
    assert "Federated Project" in result
    
    # Проверяем содержимое из web шаблона
    assert "Web Application Summary" in result
    assert "export const App" in result
    assert "modern TypeScript" in result
    
    # Проверяем содержимое из core шаблона  
    assert "Core Library Summary" in result
    assert "class Processor:" in result
    assert "def get_client():" in result


def test_multiple_template_placeholders_same_template(basic_project):
    """Тест множественных ссылок на один и тот же шаблон."""
    root = basic_project
    
    create_template(root, "reusable", """## Reusable Section

This section appears multiple times.
""", "tpl")
    
    create_template(root, "multiple-same-test", """# Multiple Same Template Test

${tpl:reusable}

## Middle Content

Some content in between.

${tpl:reusable}

## End
""")
    
    result = render_template(root, "ctx:multiple-same-test")
    
    # Содержимое шаблона должно появиться дважды
    occurrences = result.count("Reusable Section")
    assert occurrences == 2
    
    occurrences = result.count("This section appears multiple times.")
    assert occurrences == 2
    
    assert "Some content in between." in result


def test_template_placeholder_with_sections_and_other_templates(basic_project):
    """Тест комбинирования шаблонов с секциями и другими шаблонами."""
    root = basic_project
    
    create_template(root, "code-intro", """## Source Code Analysis

The following code represents the core implementation:
""", "tpl")
    
    create_template(root, "code-outro", """## Code Review Notes

Please review the above implementation for:
- Performance implications
- Security considerations
- Maintainability
""", "tpl")
    
    create_template(root, "combined-test", """# Combined Test

${tpl:code-intro}

${src}

${tpl:code-outro}

## Additional Documentation

${docs}
""")
    
    result = render_template(root, "ctx:combined-test")
    
    # Проверяем правильный порядок и содержимое
    assert "Source Code Analysis" in result
    assert "def main():" in result
    assert "Code Review Notes" in result
    assert "Project Documentation" in result
    
    # Проверяем правильный порядок элементов
    intro_pos = result.find("Source Code Analysis")
    code_pos = result.find("def main():")
    outro_pos = result.find("Code Review Notes")
    docs_pos = result.find("Project Documentation")
    
    assert intro_pos < code_pos < outro_pos < docs_pos


def test_deeply_nested_template_includes(basic_project):
    """Тест глубоко вложенных включений шаблонов."""
    root = basic_project
    
    # Создаем цепочку: level1 -> level2 -> level3 -> level4
    create_template(root, "level4", """Level 4 Content""", "tpl")
    
    create_template(root, "level3", """Level 3: ${tpl:level4}""", "tpl")
    
    create_template(root, "level2", """Level 2: ${tpl:level3}""", "tpl")
    
    create_template(root, "level1", """Level 1: ${tpl:level2}""", "tpl")
    
    create_template(root, "deep-nesting-test", """# Deep Nesting Test

${tpl:level1}
""")
    
    result = render_template(root, "ctx:deep-nesting-test")
    
    assert "Level 1: Level 2: Level 3: Level 4 Content" in result


def test_template_placeholder_with_whitespace_handling(basic_project):
    """Тест обработки пробелов вокруг плейсхолдеров шаблонов."""
    root = basic_project
    
    create_template(root, "spaced", """Content with spaces around it.""", "tpl")
    
    create_template(root, "whitespace-test", """# Whitespace Test

Before template.
${tpl:spaced}
After template.

Indented:
    ${tpl:spaced}
End.
""")
    
    result = render_template(root, "ctx:whitespace-test")
    
    assert "Before template." in result
    assert "Content with spaces around it." in result
    assert "After template." in result
    assert "End." in result


def test_template_placeholder_empty_template(basic_project):
    """Тест включения пустого шаблона."""
    root = basic_project
    
    create_template(root, "empty", "", "tpl")
    
    create_template(root, "empty-template-test", """# Empty Template Test

Before empty.
${tpl:empty}
After empty.
""")
    
    result = render_template(root, "ctx:empty-template-test")
    
    assert "Before empty." in result
    assert "After empty." in result
    # Между ними не должно быть никакого контента от пустого шаблона


def test_template_placeholder_mixed_local_and_addressed(federated_project):
    """Тест смешанных локальных и адресных включений шаблонов."""
    root = federated_project
    
    # Локальный шаблон
    create_template(root, "local-intro", """# System Overview

This document covers the entire system.
""", "tpl")
    
    # Адресные шаблоны в дочерних скоупах
    create_template(root / "apps" / "web", "web-details", """## Web Details

${web-src}
""", "tpl")
    
    create_template(root / "libs" / "core", "core-details", """## Core Details

${core-lib}
""", "tpl")
    
    # Контекст, смешивающий все типы
    create_template(root, "mixed-templates-test", """${tpl:local-intro}

${overview}

${tpl@apps/web:web-details}

${tpl@libs/core:core-details}
""")
    
    result = render_template(root, "ctx:mixed-templates-test")
    
    # Локальный шаблон
    assert "System Overview" in result
    
    # Корневая секция
    assert "Federated Project" in result
    
    # Адресные шаблоны
    assert "Web Details" in result
    assert "Core Details" in result
    assert "export const App" in result
    assert "class Processor:" in result


@pytest.mark.parametrize("template_name,expected_content", [
    ("intro", "Project Introduction"),
    ("footer", "Contact Information")
])
def test_template_placeholder_parametrized(basic_project, template_name, expected_content):
    """Параметризованный тест различных шаблонов.""" 
    root = basic_project
    
    # Создаем структуру шаблонов заранее
    create_nested_template_structure(root)
    
    create_template(root, f"param-test-{template_name}", f"""# Param Test

${{tpl:{template_name}}}
""")
    
    result = render_template(root, f"ctx:param-test-{template_name}")
    assert expected_content in result


def test_template_placeholder_case_sensitivity(basic_project):
    """Тест чувствительности к регистру в именах шаблонов."""
    root = basic_project
    
    create_template(root, "CamelCase", """CamelCase content""", "tpl")
    
    # Правильный регистр должен работать
    create_template(root, "case-correct-test", """${tpl:CamelCase}""")
    result = render_template(root, "ctx:case-correct-test")
    assert "CamelCase content" in result
    
    # Имена шаблонов не чувствительны к регистру
    create_template(root, "case-error-test", """${tpl:camelcase}""")
    result = render_template(root, "ctx:case-error-test")
    assert "CamelCase content" in result

def test_tpl_placeholder_in_nested_context_include(federated_project):
    """
    Тест вложенных контекстов с tpl-плейсхолдерами.

    Воспроизводит баг: ${ctx@apps/web:web-ctx} содержит ${tpl:docs/guide},
    который должен резолвиться относительно apps/web/lg-cfg/, а не корневого lg-cfg/.
    """
    root = federated_project

    # Создаем корневой контекст, который включает дочерний
    create_template(root, "main-with-nested", """# Main Project

## Core
${md:README}

---

## Web Application Details
${ctx@apps/web:web-ctx}
""")

    result = render_template(root, "ctx:main-with-nested")

    # Проверяем, что корневой README включился в Core
    assert "This is a monorepo with multiple modules." in result

    # Проверяем lg-cfg/docs/guide.tpl.md из apps/web's включился
    assert "WEB GUIDE (no sections here)" in result
    
    # Проверяем, что Web App Deployment из apps/web включился
    assert "Deployment instructions for the web application." in result