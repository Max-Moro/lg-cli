"""
Тесты адресных md-плейсхолдеров.

Проверяет функциональность адресных ссылок:
- ${md@self:file} для файлов в lg-cfg/
- ${md@origin:file} для файлов из других скоупов
- Федеративные включения между lg-cfg разных модулей
"""

from __future__ import annotations

import pytest

from .conftest import (
    federated_md_project, md_project, create_template, 
    render_template, write_markdown
)


def test_md_placeholder_with_self_origin(md_project):
    """Тест ${md@self:file} для файлов в lg-cfg/."""
    root = md_project
    
    create_template(root, "self-test", """# Self Origin Test

## Internal Documentation
${md@self:internal}

## End
""")
    
    result = render_template(root, "ctx:self-test")
    
    # Проверяем, что файл из lg-cfg/ включился
    assert "Internal Documentation" in result  # из шаблона
    assert "This is internal documentation stored in lg-cfg." in result  # из файла


def test_md_placeholder_self_vs_regular(md_project):
    """Тест различий между ${md@self:file} и ${md:file}."""
    root = md_project
    
    # Создаем файл и в корне и в lg-cfg/
    from .conftest import write_markdown
    write_markdown(root / "test-file.md", 
                  title="Root Version",
                  content="This is the root version of the file.")
    
    write_markdown(root / "lg-cfg" / "test-file.md",
                  title="LG-CFG Version", 
                  content="This is the lg-cfg version of the file.")
    
    create_template(root, "origin-comparison", """# Origin Comparison

## Regular (from root)
${md:test-file}

## Self (from lg-cfg)  
${md@self:test-file}
""")
    
    result = render_template(root, "ctx:origin-comparison")
    
    # Должны быть оба файла (содержимое, но не заголовки H1 - они удаляются strip_h1)
    assert "Root Version" not in result
    assert "LG-CFG Version" not in result
    assert "This is the root version" in result
    assert "This is the lg-cfg version" in result


def test_md_placeholder_federated_origin(federated_md_project):
    """Тест ${md@origin:file} для файлов из других скоупов."""
    root = federated_md_project
    
    create_template(root, "federated-test", """# Federated Test

## Main Project
${md:README}

## Web App Documentation  
${md@apps/web:web-readme}

## Utility Library
${md@libs/utils:utils-readme}

## Web Deployment Guide (from web's lg-cfg)
${md@apps/web:deployment}
""")
    
    result = render_template(root, "ctx:federated-test")
    
    # Проверяем содержимое из корня (заголовок H1 удаляется strip_h1)
    assert "Federated Project" not in result
    assert "Main project in a monorepo structure." in result
    
    # Проверяем содержимое из apps/web
    assert "Web Application" not in result
    assert "Frontend web application." in result
    assert "## Components" in result
    
    # Проверяем содержимое из libs/utils
    assert "Utility Library" in result
    assert "Shared utility functions." in result
    assert "## Math Utils" in result
    assert "## String Utils" in result
    
    # Проверяем файл из lg-cfg дочернего скоупа
    assert "Web Deployment Guide" in result
    assert "How to deploy the web app." in result
    assert "npm run build" in result


@pytest.mark.skip(reason="Относительные пути вида ../../ пока не поддерживаются")
def test_md_placeholder_nested_federated_access(federated_md_project):
    """Тест вложенных федеративных включений (скоуп обращается к другому скоупу)."""
    root = federated_md_project
    
    # Создаем шаблон в apps/web, который включает файлы из libs/utils
    create_template(root / "apps" / "web", "cross-reference", """# Web Cross-Reference

## Our Web App
${md:web-readme}

## Shared Utilities (from libs)
${md@../../libs/utils:utils-readme}

## Main Project Overview
${md@../../:README}
""", template_type="ctx")
    
    result = render_template(root / "apps" / "web", "ctx:cross-reference") 
    
    # Проверяем, что включились файлы из разных скоупов (заголовки H1 удаляются strip_h1)
    assert "Web Application" not in result
    assert "Utility Library" not in result
    assert "Federated Project" not in result
    assert "Frontend web application." in result    # содержимое из apps/web
    assert "Shared utility functions." in result    # содержимое из libs/utils
    assert "Main project in a monorepo structure." in result  # содержимое из корня


@pytest.mark.skip(reason="Обработка ошибок пока возвращает пустые строки вместо исключений")
def test_md_placeholder_origin_not_found_error(md_project):
    """Тест обработки ошибки когда origin не существует."""
    root = md_project
    
    create_template(root, "bad-origin-test", """# Bad Origin Test

${md@nonexistent/module:some-file}
""")
    
    # Должна возникнуть ошибка о том, что origin не найден
    with pytest.raises(Exception):  # RuntimeError или другая ошибка
        render_template(root, "ctx:bad-origin-test")


@pytest.mark.skip(reason="Обработка ошибок пока возвращает пустые строки вместо исключений")
def test_md_placeholder_file_not_found_in_origin(federated_md_project):
    """Тест обработки ошибки когда файл не найден в указанном origin."""
    root = federated_md_project
    
    create_template(root, "file-not-found-test", """# File Not Found Test

${md@apps/web:nonexistent-file}
""")
    
    # Должна возникнуть ошибка о том, что файл не найден в скоупе
    with pytest.raises(Exception):
        render_template(root, "ctx:file-not-found-test")


@pytest.mark.skip(reason="Обработка ошибок пока возвращает пустые строки вместо исключений")
def test_md_placeholder_origin_without_lg_cfg(tmp_path):
    """Тест обработки ошибки когда в origin нет lg-cfg/."""
    root = tmp_path
    
    # Создаем базовый проект
    from .conftest import create_basic_lg_cfg
    create_basic_lg_cfg(root)
    
    # Создаем директорию без lg-cfg/
    write_markdown(root / "no-cfg" / "test.md",
                  title="Test File", 
                  content="Test content")
    
    create_template(root, "no-cfg-test", """# No Config Test

${md@no-cfg:test}
""")
    
    # Должна возникнуть ошибка о том, что lg-cfg не найден
    with pytest.raises(Exception):  # RuntimeError: Child lg-cfg not found
        render_template(root, "ctx:no-cfg-test")


def test_md_placeholder_self_with_subdirectories(md_project):
    """Тест ${md@self:path/file} с поддиректориями в lg-cfg."""
    root = md_project
    
    # Создаем файл в поддиректории lg-cfg/
    write_markdown(root / "lg-cfg" / "docs" / "internal-guide.md",
                  title="Internal Guide",
                  content="Guide for internal team members.\n\n## Setup\n\nInternal setup instructions.")
    
    create_template(root, "self-subdir-test", """# Self Subdirectory Test

## Internal Guide
${md@self:docs/internal-guide}
""")
    
    result = render_template(root, "ctx:self-subdir-test")
    
    assert "Internal Guide" in result
    assert "Guide for internal team members." in result
    assert "## Setup" in result
    assert "Internal setup instructions." in result


@pytest.mark.parametrize("origin,filename,expected_content", [
    ("apps/web", "web-readme", "Web Application"),
    ("libs/utils", "utils-readme", "Utility Library"),  
    ("apps/web", "deployment", "Web Deployment Guide")  # из lg-cfg/
])
def test_md_placeholder_federated_parametrized(federated_md_project, origin, filename, expected_content):
    """Параметризованный тест федеративных md-плейсхолдеров."""
    root = federated_md_project

    create_template(root, f"param-federated-{origin.replace('/', '-')}-{filename}", f"""# Parametrized Test

${{md@{origin}:{filename}}}
""")
    
    result = render_template(root, f"ctx:param-federated-{origin.replace('/', '-')}-{filename}")
    assert expected_content in result


def test_md_placeholder_complex_federated_template(federated_md_project):
    """Тест сложного шаблона с множественными федеративными включениями."""
    root = federated_md_project
    
    create_template(root, "complex-federated", """# Complete Project Documentation

## Overview
${md:README}

## Applications

### Web Frontend  
${md@apps/web:web-readme}

#### Deployment
${md@apps/web:deployment}

## Libraries

### Utilities
${md@libs/utils:utils-readme}

## Internal Documentation
${md@self:internal}

---
*This documentation combines content from multiple project modules.*
""")
    
    result = render_template(root, "ctx:complex-federated")
    
    # Проверяем наличие всех ожидаемых разделов
    assert "Complete Project Documentation" in result
    assert "Federated Project" not in result
    assert "Web Application" not in result
    assert "Web Deployment Guide" not in result
    assert "Utility Library" not in result
    assert "Internal Documentation" in result   # self lg-cfg
    assert "*This documentation combines content" in result  # footer