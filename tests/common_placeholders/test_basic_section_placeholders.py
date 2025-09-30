"""
Тесты базовых плейсхолдеров секций.

Проверяет основную функциональность вставки ${section-name}:
- Простые вставки секций
- Секции из фрагментов (*.sec.yaml)
- Обработка ошибок
- Множественные плейсхолдеры в одном шаблоне
"""

from __future__ import annotations

import pytest

from lg.template import TemplateProcessingError
from .conftest import (
    basic_project, multilang_project, fragments_project,
    create_template, render_template
)


def test_simple_section_placeholder(basic_project):
    """Тест простой вставки секции ${src}."""
    root = basic_project
    
    # Создаем шаблон с простым плейсхолдером секции
    create_template(root, "simple-test", """# Test Template

## Source Code

${src}

End of template.
""")
    
    result = render_template(root, "ctx:simple-test")
    
    # Проверяем, что содержимое секции src вставилось
    assert "Source Code" in result
    assert "Source file: main.py" in result
    assert "def main():" in result
    assert "Source file: utils.py" in result
    assert "def helper_function(x):" in result
    assert "End of template." in result


def test_section_placeholder_with_different_sections(basic_project):
    """Тест вставки разных секций в одном шаблоне."""
    root = basic_project
    
    create_template(root, "multi-section-test", """# Multi-Section Test

## Documentation

${docs}

## Source Code

${src}

## Test Suite

${tests}
""")
    
    result = render_template(root, "ctx:multi-section-test")
    
    # Проверяем содержимое из секции docs
    assert "Project Documentation" in result
    assert "API Reference" in result
    
    # Проверяем содержимое из секции src  
    assert "def main():" in result
    assert "def helper_function(x):" in result
    
    # Проверяем содержимое из секции tests
    assert "def test_main():" in result
    assert "def test_helper():" in result


def test_section_placeholder_with_fragments(fragments_project):
    """Тест вставки секций из фрагментов *.sec.yaml."""
    root = fragments_project
    
    create_template(root, "fragments-test", """# Fragments Test

## Main Module

${main}

## Database Layer

${database}

## Security: Authentication

${security/auth}

## Security: Permissions

${security/permissions} 

## API v1

${api/api-v1}
""")
    
    result = render_template(root, "ctx:fragments-test")
    
    # Проверяем основную секцию
    assert "print('main')" in result
    
    # Проверяем секцию из одиночного фрагмента
    assert "class User: pass" in result
    
    # Проверяем секции из многосекционного фрагмента
    assert "def login(): pass" in result
    assert "def check(): pass" in result
    
    # Проверяем секцию из подпапки
    assert "def handle(): pass" in result


def test_section_placeholder_not_found_error(basic_project):
    """Тест обработки ошибки когда секция не найдена."""
    root = basic_project
    
    create_template(root, "notfound-test", """# Not Found Test

${nonexistent-section}
""")
    
    # Должна возникнуть ошибка о том, что секция не найдена
    with pytest.raises(TemplateProcessingError, match=r"Section 'nonexistent-section' not found"):
        render_template(root, "ctx:notfound-test")


def test_section_placeholder_empty_section(basic_project):
    """Тест обработки пустой секции (без файлов)."""
    root = basic_project
    
    # Создаем секцию, которая не находит файлов
    from .conftest import create_sections_yaml
    
    sections_config = {
        "empty-section": {
            "extensions": [".nonexistent"],
            "filters": {
                "mode": "allow",
                "allow": ["/src/**"]
            }
        }
    }
    
    # Дополняем существующую конфигурацию
    existing_config = {
        "src": {
            "extensions": [".py"],
            "code_fence": True,
            "filters": {
                "mode": "allow",
                "allow": ["/src/**"]
            }
        }
    }
    existing_config.update(sections_config)
    create_sections_yaml(root, existing_config)
    
    create_template(root, "empty-test", """# Empty Test

Before empty section.

${empty-section}

After empty section.
""")
    
    result = render_template(root, "ctx:empty-test")
    
    # Пустая секция должна быть пропущена
    assert "Before empty section." in result
    assert "After empty section." in result
    # Между ними не должно быть дополнительного контента, кроме разделителей


def test_section_placeholder_preserves_code_fencing(multilang_project):
    """Тест сохранения code fencing для разных языков."""
    root = multilang_project
    
    create_template(root, "fencing-test", """# Code Fencing Test

## Python Code

${python-src}

## TypeScript Code  

${typescript-src}

## Documentation (no fencing)

${shared-docs}
""")
    
    result = render_template(root, "ctx:fencing-test")
    
    # Проверяем, что Python код обернут в fenced блоки
    assert "```python" in result
    assert "class Core:" in result
    
    # Проверяем, что TypeScript код обернут в fenced блоки
    assert "```typescript" in result or "```ts" in result
    assert "export class App" in result
    
    # Проверяем, что документация не обернута (code_fence: false)
    assert "Architecture Overview" in result
    # Не должно быть fenced блоков вокруг документации
    lines = result.split('\n')
    md_context = []
    in_md_section = False
    for line in lines:
        if "Architecture Overview" in line:
            in_md_section = True
        if in_md_section:
            md_context.append(line)
            if line.startswith("## Frontend (TypeScript)"):
                break
    
    # Документация не должна быть в fenced блоке
    md_text = '\n'.join(md_context)
    assert "```" not in md_text or md_text.count("```") == 0


def test_multiple_same_section_placeholders(basic_project):
    """Тест множественных ссылок на одну и ту же секцию."""
    root = basic_project
    
    create_template(root, "duplicate-test", """# Duplicate Test

## First Reference

${src}

## Some Text Between

This is some intermediate content.

## Second Reference  

${src}

## End
""")
    
    result = render_template(root, "ctx:duplicate-test")
    
    # Содержимое секции должно появиться дважды
    occurrences = result.count("def main():")
    assert occurrences == 2
    
    occurrences = result.count("def helper_function(x):")
    assert occurrences == 2
    
    # Промежуточный текст должен присутствовать
    assert "This is some intermediate content." in result


def test_section_placeholder_whitespace_handling(basic_project):
    """Тест обработки пробелов вокруг плейсхолдеров секций."""
    root = basic_project
    
    create_template(root, "whitespace-test", """# Whitespace Test

Before placeholder.
${src}
After placeholder.

Indented:
    ${docs}
End.
""")
    
    result = render_template(root, "ctx:whitespace-test")
    
    # Проверяем корректную вставку без нарушения форматирования
    assert "Before placeholder." in result
    assert "After placeholder." in result
    assert "End." in result
    
    # Содержимое из секций должно присутствовать
    assert "def main():" in result
    assert "Project Documentation" in result


def test_section_placeholder_in_nested_structure(basic_project):
    """Тест плейсхолдеров секций в вложенной структуре списков и цитат."""
    root = basic_project
    
    create_template(root, "nested-test", """# Nested Test

## Code Examples

1. Main module:
   ${src}

2. Documentation:
   > ${docs}

3. Tests:
   - Unit tests: ${tests}
   - Integration tests: coming soon

## Summary

That completes the overview.
""")
    
    result = render_template(root, "ctx:nested-test")
    
    # Проверяем, что все секции вставились
    assert "def main():" in result
    assert "Project Documentation" in result  
    assert "def test_main():" in result
    
    # Проверяем, что структура документа сохранилась
    assert "1. Main module:" in result
    assert "2. Documentation:" in result
    assert "3. Tests:" in result
    assert "That completes the overview." in result


@pytest.mark.parametrize("section_name,expected_content", [
    ("src", "def main():"),
    ("docs", "Project Documentation"),
    ("tests", "def test_main():"),
    ("all", "def main():")  # секция all включает все файлы
])
def test_section_placeholder_parametrized(basic_project, section_name, expected_content):
    """Параметризованный тест различных плейсхолдеров секций."""
    root = basic_project
    
    template_content = f"""# Param Test

${{{section_name}}}
"""
    create_template(root, f"param-test-{section_name}", template_content)
    
    result = render_template(root, f"ctx:param-test-{section_name}")
    assert expected_content in result


def test_section_placeholder_with_complex_names(fragments_project):
    """Тест плейсхолдеров с комплексными именами секций."""
    root = fragments_project
    
    # Тестируем различные форматы имен секций
    create_template(root, "complex-names-test", """# Complex Names Test

## Simple name
${main}

## Name with slash  
${security/auth}

## Name with dash from fragment
${api/api-v1}
""")
    
    result = render_template(root, "ctx:complex-names-test")
    
    assert "print('main')" in result
    assert "def login(): pass" in result  
    assert "def handle(): pass" in result


def test_section_placeholder_case_sensitivity(basic_project):
    """Тест чувствительности к регистру в именах секций."""
    root = basic_project
    
    create_template(root, "case-test", """# Case Test

${src}
""")
    
    result = render_template(root, "ctx:case-test")
    assert "def main():" in result
    
    # Проверяем, что неправильный регистр вызывает ошибку
    create_template(root, "case-error-test", """# Case Error Test

${SRC}
""")
    
    with pytest.raises(TemplateProcessingError, match=r"Section 'SRC' not found"):
        render_template(root, "ctx:case-error-test")