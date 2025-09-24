"""
Тесты базовых md-плейсхолдеров.

Проверяет основную функциональность вставки ${md:...}:
- Простые вставки файлов
- Автоматическое добавление расширения .md  
- Пути в поддиректориях
- Базовая обработка заголовков
"""

from __future__ import annotations

import pytest

from .conftest import md_project, create_template, render_template


def test_simple_md_placeholder(md_project):
    """Тест простой вставки ${md:README}."""
    root = md_project
    
    # Создаем шаблон с простым md-плейсхолдером
    create_template(root, "simple-test", """# Test Template

## Project Documentation

${md:README}

End of template.
""")
    
    result = render_template(root, "ctx:simple-test")
    
    # Проверяем, что содержимое README.md вставилось
    assert "Main Project" in result
    assert "This is the main project documentation." in result
    assert "## Features" in result
    assert "- Feature A" in result
    assert "End of template." in result
    

def test_md_placeholder_adds_extension_automatically(md_project):
    """Тест автоматического добавления расширения .md."""
    root = md_project
    
    # Оба варианта должны работать одинаково
    create_template(root, "extension-test", """# Extension Test

## With explicit .md
${md:README.md}

## Without extension (should auto-add .md)  
${md:README}

## Should be identical
""")
    
    result = render_template(root, "ctx:extension-test")
    
    # Содержимое должно появиться дважды
    occurrences = result.count("Main Project")
    assert occurrences == 0 # заголовок H1 удаляется strip_h1
    
    occurrences = result.count("This is the main project documentation.")
    assert occurrences == 2


def test_md_placeholder_with_subdirectory(md_project):
    """Тест вставки файлов из поддиректорий."""
    root = md_project
    
    create_template(root, "subdir-test", """# Subdirectory Test

## User Guide
${md:docs/guide}

## API Reference  
${md:docs/api}
""")
    
    result = render_template(root, "ctx:subdir-test")
    
    # Проверяем содержимое из docs/guide.md
    assert "User Guide" in result
    assert "This is a comprehensive user guide." in result
    assert "## Installation" in result
    assert "Run the installer." in result
    
    # Проверяем содержимое из docs/api.md
    assert "API Reference" in result  
    assert "API documentation." in result
    assert "## Authentication" in result
    assert "### GET /users" in result

@pytest.mark.skip()
def test_md_placeholder_file_not_found_error(md_project):
    """Тест обработки ошибки когда файл не найден."""
    root = md_project

    create_template(root, "notfound-test", """# Not Found Test

${md:nonexistent-file}
""")

    # Должна возникнуть ошибка о том, что файл не найден
    with pytest.raises(Exception):  # Может быть FileNotFoundError или другая ошибка
        render_template(root, "ctx:notfound-test")


def test_md_placeholder_empty_file_handling(md_project):
    """Тест обработки пустых файлов."""
    root = md_project
    
    # Создаем пустой файл
    from .conftest import write
    write(root / "empty.md", "")
    
    create_template(root, "empty-test", """# Empty Test

Before empty file.

${md:empty}

After empty file.
""")
    
    result = render_template(root, "ctx:empty-test")
    
    assert "Before empty file." in result
    assert "After empty file." in result
    # Пустой файл не должен добавлять содержимого


def test_md_placeholder_with_file_without_h1(md_project):
    """Тест вставки файла без H1 заголовка."""
    root = md_project
    
    create_template(root, "no-h1-test", """# No H1 Test

## Changelog Section

${md:docs/changelog}
""")
    
    result = render_template(root, "ctx:no-h1-test")
    
    # Файл changelog.md не содержит H1, только H2
    assert "## v1.0.0" in result
    assert "- Initial release" in result  
    assert "## v0.9.0" in result
    assert "- Beta version" in result


def test_multiple_md_placeholders_in_single_template(md_project):
    """Тест множественных md-плейсхолдеров в одном шаблоне."""
    root = md_project
    
    create_template(root, "multiple-test", """# Multiple MD Test

## Main Documentation
${md:README}

## User Guide  
${md:docs/guide}

## API Documentation
${md:docs/api}

## Changelog
${md:docs/changelog}

## Summary
That's all the documentation!
""")
    
    result = render_template(root, "ctx:multiple-test")
    
    # Проверяем, что все файлы включились
    assert "Main Project" not in result  # из README
    assert "This is a comprehensive user guide." in result  # из guide
    assert "API documentation." in result  # из api  
    assert "### v1.0.0" in result  # из changelog
    assert "That's all the documentation!" in result


def test_md_placeholder_preserves_markdown_structure(md_project):
    """Тест сохранения Markdown-структуры при вставке.""" 
    root = md_project
    
    create_template(root, "structure-test", """# Structure Test

${md:docs/api}
""")
    
    result = render_template(root, "ctx:structure-test")
    
    # Проверяем, что заголовки разных уровней сохранились
    lines = result.split('\n')
    
    # Должен быть H2 из файла
    h2_lines = [line for line in lines if line.startswith('## ')]
    assert any("API Reference" in line for line in h2_lines)
    
    # Должны быть H3 заголовки
    h3_lines = [line for line in lines if line.startswith('### ')]
    assert any("Authentication" in line for line in h3_lines)
    assert any("Endpoints" in line for line in h3_lines)
    
    # Должны быть H4 заголовки
    h4_lines = [line for line in lines if line.startswith('#### ')]
    assert any("GET /users" in line for line in h4_lines)


def test_md_placeholder_whitespace_handling(md_project):
    """Тест обработки пробелов вокруг md-плейсхолдеров."""
    root = md_project
    
    create_template(root, "whitespace-test", """# Whitespace Test

Before placeholder.
${md:README}
After placeholder.

Indented:
    ${md:docs/changelog}
End.
""")
    
    result = render_template(root, "ctx:whitespace-test")
    
    # Проверяем корректную вставку без нарушения форматирования
    assert "Before placeholder." in result
    assert "After placeholder." in result
    assert "End." in result
    
    # Содержимое из файлов должно присутствовать
    assert "Main Project" in result
    assert "## v1.0.0" in result


@pytest.mark.parametrize("filename,expected_content", [
    ("README", "Main Project"),
    ("docs/guide", "User Guide"), 
    ("docs/api", "API Reference"),
    ("docs/changelog", "v1.0.0")
])
def test_md_placeholder_parametrized(md_project, filename, expected_content):
    """Параметризованный тест различных md-плейсхолдеров."""
    root = md_project
    
    create_template(root, f"param-test-{filename.replace('/', '-')}", f"""# Param Test

${{md:{filename}}}
""")
    
    result = render_template(root, f"ctx:param-test-{filename.replace('/', '-')}")
    assert expected_content in result