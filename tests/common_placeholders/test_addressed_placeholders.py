"""
Тесты адресных плейсхолдеров секций.

Проверяет функциональность cross-scope ссылок:
- ${@origin:section-name} - классический формат
- ${@[origin]:section-name} - скобочный формат для origin с двоеточиями
- Федеративные проекты и множественные скоупы
- Обработка ошибок адресации
"""

from __future__ import annotations

import pytest

from .conftest import (
    federated_project,
    create_template, render_template
)


def test_simple_addressed_section_placeholder(federated_project):
    """Тест простых адресных плейсхолдеров ${@origin:section}."""
    root = federated_project
    
    # Создаем шаблон с адресными ссылками
    create_template(root, "addressed-test", """# Addressed Test

## Root Project Overview

${overview}

## Web Application Source

${@apps/web:web-src}

## Core Library

${@libs/core:core-lib}
""")
    
    result = render_template(root, "ctx:addressed-test")
    
    # Проверяем содержимое из корневой секции
    assert "Federated Project" in result
    assert "Project Overview" in result
    
    # Проверяем содержимое из apps/web
    assert "export const App" in result
    assert "export function webUtil" in result
    
    # Проверяем содержимое из libs/core
    assert "class Processor:" in result


def test_bracketed_addressed_section_placeholder(federated_project):
    """Тест скобочных адресных плейсхолдеров ${@[origin]:section}.""" 
    root = federated_project
    
    # Создаем шаблон с скобочной адресацией
    create_template(root, "bracketed-test", """# Bracketed Test

## Web App (bracketed syntax)

${@[apps/web]:web-src}

## Core Lib (bracketed syntax)

${@[libs/core]:core-lib}
""")
    
    result = render_template(root, "ctx:bracketed-test")
    
    # Содержимое должно быть идентично обычной адресации
    assert "export const App" in result
    assert "class Processor:" in result


def test_mixed_local_and_addressed_placeholders(federated_project):
    """Тест смешанных локальных и адресных плейсхолдеров."""
    root = federated_project
    
    create_template(root, "mixed-test", """# Mixed Test

## Local Root Sections

${overview}
${root-config}

## External Web Sections

${@apps/web:web-src}
${@apps/web:web-docs}

## External Core Sections

${@libs/core:core-lib}
${@libs/core:core-api}
""")
    
    result = render_template(root, "ctx:mixed-test")
    
    # Локальные секции
    assert "Federated Project" in result
    
    # Web секции
    assert "export const App" in result
    assert "Deployment instructions" in result
    
    # Core секции - обычная и API (с урезанными телами функций)
    assert "class Processor:" in result
    assert "def get_client():" in result


def test_addressed_placeholder_nonexistent_scope_error(federated_project):
    """Тест ошибки при ссылке на несуществующий скоуп."""
    root = federated_project
    
    create_template(root, "bad-scope-test", """# Bad Scope Test

${@nonexistent/module:some-section}
""")
    
    # Должна возникнуть ошибка о несуществующем скоупе
    with pytest.raises(RuntimeError, match=r"Child lg-cfg not found"):
        render_template(root, "ctx:bad-scope-test")


def test_addressed_placeholder_nonexistent_section_error(federated_project):
    """Тест ошибки при ссылке на несуществующую секцию в существующем скоупе."""
    root = federated_project
    
    create_template(root, "bad-section-test", """# Bad Section Test

${@apps/web:nonexistent-section}
""")
    
    # Должна возникнуть ошибка о несуществующей секции
    with pytest.raises(RuntimeError, match=r"Section 'nonexistent-section' not found"):
        render_template(root, "ctx:bad-section-test")


def test_addressed_placeholder_complex_paths(federated_project):
    """Тест адресных плейсхолдеров с комплексными путями."""
    root = federated_project
    
    # Создаем вложенную структуру скоупов
    from .conftest import create_sections_yaml, write_source_file
    
    # Глубоко вложенный скоуп
    deep_sections = {
        "deep-section": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow", 
                "allow": ["/deep/**"]
            }
        }
    }
    create_sections_yaml(root / "libs" / "core" / "modules" / "auth", deep_sections)
    
    write_source_file(root / "libs" / "core" / "modules" / "auth" / "deep" / "security.py",
                     "def authenticate(): pass", "python")
    
    create_template(root, "complex-paths-test", """# Complex Paths Test

## Deep Auth Module

${@libs/core/modules/auth:deep-section}
""")
    
    result = render_template(root, "ctx:complex-paths-test")
    
    assert "def authenticate(): pass" in result


def test_multiple_addressed_placeholders_same_scope(federated_project):
    """Тест множественных адресных плейсхолдеров из одного скоупа."""
    root = federated_project
    
    create_template(root, "multiple-same-scope-test", """# Multiple Same Scope Test

## Web Source Code

${@apps/web:web-src}

## Web Documentation

${@apps/web:web-docs}

## Web Source Code Again

${@apps/web:web-src}
""")
    
    result = render_template(root, "ctx:multiple-same-scope-test")
    
    # Содержимое web-src должно появиться дважды
    occurrences = result.count("export const App")
    assert occurrences == 2
    
    # Содержимое web-docs должно появиться один раз
    occurrences = result.count("Deployment instructions")
    assert occurrences == 1


def test_addressed_placeholder_chain_references(federated_project):
    """Тест цепочки адресных ссылок (A -> B -> C)."""
    root = federated_project
    
    # Создаем промежуточный шаблон в libs/core
    create_template(root / "libs" / "core", "core-summary", """# Core Summary

## Core Library Code

${core-lib}

## Core API

${core-api}
""", "tpl")
    
    # Создаем шаблон в apps/web, который ссылается на промежуточный
    create_template(root / "apps" / "web", "web-with-core", """# Web with Core

## Web Application

${web-src}

## Core Library Summary

${tpl@../../libs/core:core-summary}
""", "tpl")
    
    # Главный шаблон ссылается на web-with-core
    create_template(root, "chain-test", """# Chain Test

${tpl@apps/web:web-with-core}
""")
    
    result = render_template(root, "ctx:chain-test")
    
    # Проверяем, что все уровни цепочки отработали
    assert "export const App" in result  # из web-src
    assert "class Processor:" in result  # из core-lib
    assert "def get_client():" in result  # из core-api


def test_addressed_placeholder_relative_vs_absolute_paths():
    """Тест относительных vs абсолютных путей в адресации."""
    # Все пути в адресации считаются относительно корня репозитория
    # Этот тест должен проверить, что различные способы записи пути дают одинаковый результат
    pass  # Детальная логика зависит от реализации resolver'а


@pytest.mark.parametrize("origin,section,expected_content", [
    ("apps/web", "web-src", "export const App"),
    ("apps/web", "web-docs", "Deployment instructions"), 
    ("libs/core", "core-lib", "class Processor:"),
    ("libs/core", "core-api", "def get_client():")
])
def test_addressed_placeholder_parametrized(federated_project, origin, section, expected_content):
    """Параметризованный тест различных адресных плейсхолдеров."""
    root = federated_project
    
    create_template(root, f"param-test-{origin.replace('/', '-')}-{section}", f"""# Param Test

${{@{origin}:{section}}}
""")
    
    result = render_template(root, f"ctx:param-test-{origin.replace('/', '-')}-{section}")
    assert expected_content in result


def test_addressed_placeholder_deep_nesting(federated_project):
    """Тест глубокой вложенности адресных ссылок."""
    root = federated_project
    
    # Создаем глубокую структуру модулей
    from .conftest import create_sections_yaml, write_source_file
    
    # Четыре уровня вложенности
    deep_path = root / "libs" / "core" / "modules" / "data" / "processors" / "advanced"
    
    deep_sections = {
        "advanced-processor": {
            "extensions": [".py"],
            "filters": {
                "mode": "allow",
                "allow": ["/advanced/**"]
            }
        }
    }
    create_sections_yaml(deep_path, deep_sections)
    
    write_source_file(deep_path / "advanced" / "ml.py",
                     "class MLProcessor: pass", "python")
    
    create_template(root, "deep-nesting-test", """# Deep Nesting Test

${@libs/core/modules/data/processors/advanced:advanced-processor}
""")
    
    result = render_template(root, "ctx:deep-nesting-test")
    
    assert "class MLProcessor: pass" in result


def test_addressed_placeholder_case_sensitivity(federated_project):
    """Тест чувствительности к регистру в адресных плейсхолдерах."""
    root = federated_project
    
    # Правильный регистр должен работать
    create_template(root, "case-correct-test", """# Case Test

${@apps/web:web-src}
""")
    
    result = render_template(root, "ctx:case-correct-test")
    assert "export const App" in result
    
    # Неправильный регистр должен вызывать ошибку
    create_template(root, "case-error-test", """# Case Error Test

${@Apps/Web:web-src}
""")
    
    with pytest.raises(RuntimeError, match=r"Child lg-cfg not found"):
        render_template(root, "ctx:case-error-test")