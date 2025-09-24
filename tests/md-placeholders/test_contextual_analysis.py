"""
Тесты контекстуального анализа заголовков для md-плейсхолдеров.

Проверяет автоматическое определение max_heading_level и strip_single_h1 
на основе позиции плейсхолдера в шаблоне:
- Анализ окружающих заголовков
- Определение уровня вложенности
- Автоматическая установка strip_h1 при наличии родительского заголовка
"""

from __future__ import annotations

import pytest
import re

from .conftest import md_project, create_template, render_template, write_markdown


def extract_heading_level(text: str, heading_text: str) -> int | None:
    """
    Извлекает точный уровень заголовка из текста.
    
    Args:
        text: Текст для поиска
        heading_text: Текст заголовка (без #)
    
    Returns:
        Уровень заголовка (количество #) или None если не найден
    """
    # Ищем заголовок в формате ATX (# заголовок)
    pattern = rf'^(#{1,6})\s+{re.escape(heading_text.strip())}\s*$'
    for line in text.split('\n'):
        match = re.match(pattern, line.strip())
        if match:
            return len(match.group(1))
    return None


def assert_heading_level(result: str, heading_text: str, expected_level: int):
    """
    Проверяет точный уровень заголовка в результате.
    
    Args:
        result: Результат рендеринга
        heading_text: Текст заголовка (без #)
        expected_level: Ожидаемый уровень заголовка
    """
    actual_level = extract_heading_level(result, heading_text)
    assert actual_level == expected_level, (
        f"Expected heading '{heading_text}' to be level {expected_level}, "
        f"but found level {actual_level}"
    )


def assert_heading_not_present(result: str, heading_text: str):
    """
    Проверяет, что заголовок отсутствует в результате.
    
    Args:
        result: Результат рендеринга
        heading_text: Текст заголовка для проверки
    """
    actual_level = extract_heading_level(result, heading_text)
    assert actual_level is None, f"Heading '{heading_text}' should not be present, but found at level {actual_level}"


def test_contextual_heading_level_from_h3_position(md_project):
    """Тест автоматического определения max_heading_level=4 при вставке под H3."""
    root = md_project
    
    create_template(root, "h3-context-test", """# Main Document

## Section A

### Subsection: API Documentation  

${md:docs/api}

### Another Subsection

Some other content.
""")
    
    result = render_template(root, "ctx:h3-context-test")
    
    # H1 из api.md должен стать H4 (H3 + 1)
    assert_heading_level(result, "API Reference", 4)
    
    # H2 из api.md должны стать H5
    assert_heading_level(result, "Authentication", 5)
    assert_heading_level(result, "Endpoints", 5)
    
    # H3 из api.md должны стать H6  
    assert_heading_level(result, "GET /users", 6)


def test_contextual_heading_level_from_h2_position(md_project):
    """Тест автоматического определения max_heading_level=3 при вставке под H2."""
    root = md_project
    
    create_template(root, "h2-context-test", """# Project Documentation

## User Guide

${md:docs/guide}

## Other Section
""")
    
    result = render_template(root, "ctx:h2-context-test")
    
    # H1 из guide.md должен стать H3 (H2 + 1)
    assert_heading_level(result, "User Guide", 3)
    
    # H2 из guide.md должны стать H4
    assert_heading_level(result, "Installation", 4)
    assert_heading_level(result, "Usage", 4)


def test_contextual_strip_h1_when_parent_heading_exists(md_project):
    """Тест автоматической установки strip_h1=true при наличии родительского заголовка."""
    root = md_project
    
    create_template(root, "strip-h1-test", """# Main Documentation

## API Reference Section

${md:docs/api}

## Guide Section  

${md:docs/guide}
""")
    
    result = render_template(root, "ctx:strip-h1-test")
    
    # Проверяем наличие заголовков секций из шаблона
    assert_heading_level(result, "API Reference Section", 2)
    assert_heading_level(result, "Guide Section", 2)
    
    # Оригинальные H1 из файлов должны быть удалены (strip_h1=true)
    assert_heading_not_present(result, "API Reference")
    assert_heading_not_present(result, "User Guide")
    
    # Но содержимое H2+ должно присутствовать на правильных уровнях
    # Под H2 секциями содержимое начинается с H3
    assert_heading_level(result, "Authentication", 3)  # было H2, стало H3
    assert_heading_level(result, "Installation", 3)    # было H2, стало H3


def test_contextual_no_strip_h1_when_no_parent_heading(md_project):
    """Тест НЕ установки strip_h1 когда нет родительского заголовка."""
    root = md_project
    
    create_template(root, "no-strip-test", """# Main Documentation

Some intro text.

${md:docs/api}

${md:docs/guide}

End of document.
""")
    
    result = render_template(root, "ctx:no-strip-test")
    
    # H1 заголовки должны сохраниться, но стать H3 (под главным H1)
    assert_heading_level(result, "API Reference", 3)  # было H1, стало H3, сохранилось
    assert_heading_level(result, "User Guide", 3)     # было H1, стало H3, сохранилось
    
    # H2 из документов становятся H4
    assert_heading_level(result, "Authentication", 4) # было H2, стало H4
    assert_heading_level(result, "Installation", 4)   # было H2, стало H4


def test_placeholder_inside_heading_with_contextual_analysis(md_project):
    """Тест контекстуального анализа для плейсхолдеров внутри заголовков."""
    root = md_project
    
    create_template(root, "inline-placeholder-test", """# Listing Generator 

## Расширенная документация

### ${md:docs/api}

### ${md:docs/guide}

## Заключение
""")
    
    result = render_template(root, "ctx:inline-placeholder-test")
    
    # Плейсхолдеры заменяются содержимым H1 из файлов
    # При этом strip_h1=true (есть родительский заголовок H3), max_heading_level=4
    assert_heading_level(result, "API Reference", 3)  # заголовок H3 принимает содержимое H1 из файла
    assert_heading_level(result, "User Guide", 3)     # заголовок H3 принимает содержимое H1 из файла
    
    # Остальное содержимое файлов начинается с H4
    assert_heading_level(result, "Authentication", 4) # было H2, стало H4
    assert_heading_level(result, "Installation", 4)   # было H2, стало H4


def test_placeholder_inside_heading_multiple_levels(md_project):
    """Тест плейсхолдеров на разных уровнях заголовков."""
    root = md_project
    
    create_template(root, "multi-level-inline-test", """# Project Manual

## Part I: ${md:docs/api}

### Details

Some details here.

## Part II: ${md:docs/guide}

### More Details

More details here.
""")
    
    result = render_template(root, "ctx:multi-level-inline-test")
    
    # H2 заголовки получают содержимое H1 из файлов
    assert_heading_level(result, "Part I: API Reference", 2)
    assert_heading_level(result, "Part II: User Guide", 2)
    
    # Остальное содержимое файлов размещается на уровне H3+
    assert_heading_level(result, "Authentication", 3)  # было H2, стало H3
    assert_heading_level(result, "Installation", 3)    # было H2, стало H3


def test_contextual_analysis_with_multiple_heading_levels(md_project):
    """Тест сложного контекстуального анализа с разными уровнями заголовков."""
    root = md_project
    
    create_template(root, "complex-levels-test", """# Project Manual

## Part I: API

### Chapter 1: Reference

${md:docs/api}

### Chapter 2: Examples

Some examples here.

## Part II: Guides  

### Chapter 3: User Guide

${md:docs/guide}

#### Section 3.1: Advanced Usage

${md:docs/changelog}

## Summary
""")
    
    result = render_template(root, "ctx:complex-levels-test")
    
    # api.md под H3 → max_heading_level=4, strip_h1=true  
    assert_heading_level(result, "Authentication", 4)   # было H2 в api.md, стало H4
    assert_heading_level(result, "Endpoints", 4)        # было H2 в api.md, стало H4
    
    # guide.md под H3 → max_heading_level=4, strip_h1=true
    assert_heading_level(result, "Installation", 4)     # было H2 в guide.md, стало H4  
    assert_heading_level(result, "Usage", 4)            # было H2 в guide.md, стало H4
    
    # changelog.md под H4 → max_heading_level=5, strip_h1=false (нет H1 в changelog.md)
    assert_heading_level(result, "v1.0.0", 5)          # было H2 в changelog.md, стало H5
    assert_heading_level(result, "v0.9.0", 5)          # было H2 в changelog.md, стало H5


def test_contextual_analysis_ignores_content_in_fenced_blocks(md_project):
    """Тест что контекстуальный анализ игнорирует заголовки в fenced-блоках."""
    root = md_project
    
    create_template(root, "fenced-ignore-test", """# Documentation

## Configuration

Example config:

```yaml  
# This is not a real heading
## This is also not a heading  
### Neither is this
```

### Actual Section

${md:docs/api}
""")
    
    result = render_template(root, "ctx:fenced-ignore-test")
    
    # Должен анализировать только "### Actual Section", игнорируя содержимое в ```
    # Поэтому api.md должен иметь max_heading_level=4
    assert_heading_level(result, "Authentication", 4)  # было H2, стало H4


def test_contextual_analysis_with_setext_headings(md_project):
    """Тест контекстуального анализа с Setext заголовками (подчеркивания)."""
    root = md_project
    
    create_template(root, "setext-test", """Project Guide
=============

API Documentation  
-----------------

${md:docs/api}

User Guide
----------

${md:docs/guide}
""")
    
    result = render_template(root, "ctx:setext-test")
    
    # "API Documentation" это H2 (---), поэтому api.md → max_heading_level=3
    # "User Guide" это тоже H2, поэтому guide.md → max_heading_level=3
    assert_heading_level(result, "Authentication", 3)   # было H2, стало H3
    assert_heading_level(result, "Installation", 3)     # было H2, стало H3


def test_contextual_analysis_edge_case_h6_limit(md_project):
    """Тест ограничения H6 при глубокой вложенности."""
    root = md_project
    
    create_template(root, "h6-limit-test", """# Level 1

## Level 2  

### Level 3

#### Level 4

##### Level 5

###### Level 6 Section

${md:docs/api}
""")
    
    result = render_template(root, "ctx:h6-limit-test")
    
    # Проверим что не создались недопустимые H7+ заголовки
    lines = result.split('\n')
    invalid_headings = [line for line in lines if line.startswith('#######')]
    assert len(invalid_headings) == 0, f"Found invalid H7+ headings: {invalid_headings}"
    
    # В зависимости от реализации, заголовки могут остаться на уровне H6 
    # или система может отказаться от нормализации вообще
    # Проверим что хотя бы базовая структура сохранена
    assert "API Reference" in result, "API Reference content should be present"
    assert "Authentication" in result, "Authentication content should be present"


def test_no_contextual_analysis_for_explicit_parameters(md_project):
    """Тест что явные параметры отключают контекстуальный анализ."""
    root = md_project
    
    create_template(root, "explicit-params-test", """# Main

## Section

### Subsection  

${md:docs/api, level:2, strip_h1:false}
""")
    
    result = render_template(root, "ctx:explicit-params-test")
    
    # Явные параметры должны переопределить контекстуальный анализ
    # level:2 означает H1→H2, strip_h1:false означает сохранить H1
    assert_heading_level(result, "API Reference", 2)    # было H1, стало H2 (явно задано)
    assert_heading_level(result, "Authentication", 3)   # было H2, стало H3


def test_contextual_analysis_with_multiple_placeholders_same_level(md_project):
    """Тест контекстуального анализа для нескольких плейсхолдеров на одном уровне."""
    root = md_project
    
    create_template(root, "same-level-test", """# Documentation

## API References

${md:docs/api}

## User Guides

${md:docs/guide}  

## Changelog

${md:docs/changelog}
""")
    
    result = render_template(root, "ctx:same-level-test")
    
    # Все плейсхолдеры под H2, поэтому max_heading_level=3, strip_h1=true
    assert_heading_level(result, "Authentication", 3)   # из api.md, было H2→H3
    assert_heading_level(result, "Installation", 3)     # из guide.md, было H2→H3
    assert_heading_level(result, "v1.0.0", 3)          # из changelog.md, было H2→H3


def test_placeholder_in_heading_with_mixed_content(md_project):
    """Тест плейсхолдера внутри заголовка в смешанном контенте."""
    root = md_project
    
    create_template(root, "mixed-content-test", """# Project Documentation

## Introduction

Some introduction text here.

## ${md:docs/api}

Some additional context after API section.

## ${md:docs/guide}

## Conclusion

Final thoughts.
""")
    
    result = render_template(root, "ctx:mixed-content-test")
    
    # H2 заголовки должны принять содержимое H1 из файлов
    assert_heading_level(result, "API Reference", 2)
    assert_heading_level(result, "User Guide", 2)
    
    # Остальное содержимое на уровне H3
    assert_heading_level(result, "Authentication", 3)
    assert_heading_level(result, "Installation", 3)
    
    # Заголовки из шаблона должны остаться на своих уровнях
    assert_heading_level(result, "Introduction", 2)
    assert_heading_level(result, "Conclusion", 2)


def test_nested_placeholders_in_headings(md_project):
    """Тест вложенных плейсхолдеров в заголовках разных уровней."""
    root = md_project
    
    create_template(root, "nested-test", """# Main Guide

## Part 1: ${md:docs/api}

### Section 1.1: Details

Some details about API.

#### ${md:docs/guide}

### Section 1.2: More Info

More information here.

## Part 2: Other Content

Regular content.
""")
    
    result = render_template(root, "ctx:nested-test")
    
    # Проверяем корректную интеграцию содержимого на разных уровнях
    assert_heading_level(result, "Part 1: API Reference", 2)   # H2 принял H1 из api.md
    assert_heading_level(result, "User Guide", 4)              # H4 принял H1 из guide.md
    
    # Вложенное содержимое должно быть на правильных уровнях
    assert_heading_level(result, "Authentication", 3)          # из api.md под H2
    assert_heading_level(result, "Installation", 5)            # из guide.md под H4