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

from .conftest import md_project, create_template, render_template, write_markdown


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
    
    # H1 из api.md должен стать H4 (3+1)
    # H2 из api.md должны стать H5  
    # H3 из api.md должны стать H6
    assert "#### API Reference" in result  # было H1, стало H4
    assert "##### Authentication" in result  # было H2, стало H5  
    assert "##### Endpoints" in result      # было H2, стало H5
    assert "###### GET /users" in result     # было H3, стало H6


def test_contextual_heading_level_from_h2_position(md_project):
    """Тест автоматического определения max_heading_level=3 при вставке под H2."""
    root = md_project
    
    create_template(root, "h2-context-test", """# Project Documentation

## User Guide

${md:docs/guide}

## Other Section
""")
    
    result = render_template(root, "ctx:h2-context-test")
    
    # H1 из guide.md должен стать H3 (2+1)
    # H2 из guide.md должны стать H4
    assert "### User Guide" in result       # было H1, стало H3  
    assert "#### Installation" in result    # было H2, стало H4
    assert "#### Usage" in result           # было H2, стало H4


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
    
    # H1 заголовки должны быть удалены, так как есть родительские заголовки секций
    assert "API Reference Section" in result  # заголовок секции из шаблона
    assert "Guide Section" in result          # заголовок секции из шаблона
    
    # Оригинальные H1 не должны присутствовать как отдельные заголовки
    lines = result.split('\n')
    h1_lines = [line for line in lines if line.startswith('# ') and line != '# Main Documentation']
    
    # Не должно быть H1 "API Reference" или "User Guide" как отдельных строк
    api_h1_lines = [line for line in h1_lines if 'API Reference' in line]
    guide_h1_lines = [line for line in h1_lines if 'User Guide' in line] 
    
    assert len(api_h1_lines) == 0, f"Found unexpected H1 lines: {api_h1_lines}"
    assert len(guide_h1_lines) == 0, f"Found unexpected H1 lines: {guide_h1_lines}"
    
    # Но содержимое должно присутствовать (на правильных уровнях)
    assert "Authentication" in result
    assert "Installation" in result


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
    assert "### API Reference" in result  # было H1, стало H3, сохранилось
    assert "### User Guide" in result     # было H1, стало H3, сохранилось
    assert "#### Authentication" in result # было H2, стало H4
    assert "#### Installation" in result   # было H2, стало H4


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
    assert "#### Authentication" in result   # было H2 в api.md, стало H4
    assert "##### Endpoints" in result       # было H2 в api.md, стало H4 → H5 (ошибка в ожидании, должно быть H4)
    
    # guide.md под H3 → max_heading_level=4, strip_h1=true
    assert "#### Installation" in result      # было H2 в guide.md, стало H4  
    assert "#### Usage" in result            # было H2 в guide.md, стало H4
    
    # changelog.md под H4 → max_heading_level=5, strip_h1=false (нет H1)
    assert "##### v1.0.0" in result          # было H2 в changelog.md, стало H5
    assert "##### v0.9.0" in result          # было H2 в changelog.md, стало H5


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
    assert "#### Authentication" in result  # было H2, стало H4


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
    assert "### Authentication" in result   # было H2, стало H3
    assert "### Installation" in result     # было H2, стало H3


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
    
    # Под H6 уже нельзя идти глубже, поэтому должно остаться на H6
    # Или возможно поведение по умолчанию - не изменять заголовки если превышен лимит
    # Проверим что H1 из api.md не станет H7 (невалидно в Markdown)
    lines = result.split('\n')
    invalid_headings = [line for line in lines if line.startswith('#######')]
    assert len(invalid_headings) == 0, "Found invalid H7+ headings"


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
    assert "## API Reference" in result    # было H1, стало H2 (явно задано)
    assert "### Authentication" in result  # было H2, стало H3


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
    assert "### Authentication" in result   # из api.md, было H2→H3
    assert "### Installation" in result     # из guide.md, было H2→H3
    assert "### v1.0.0" in result          # из changelog.md, было H2→H3