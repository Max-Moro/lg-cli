"""
Тесты якорных ссылок для md-плейсхолдеров.

Проверяет функциональность частичного включения документов:
- ${md:file#section} для включения отдельных разделов
- Обработка различных форматов заголовков
- Включение вложенных разделов
- Обработка несуществующих якорей
"""

from __future__ import annotations

import pytest

from .conftest import md_project, create_template, render_template, write_markdown


def test_anchor_basic_section_inclusion(md_project):
    """Тест базового включения раздела по якорю."""
    root = md_project
    
    # Создаем файл с несколькими разделами
    write_markdown(root / "sections.md", 
                  title="Complete Guide",
                  content="""## Getting Started

Installation instructions here.

### Requirements

- Python 3.8+
- Node.js 16+

## Advanced Usage

Advanced features description.

### Configuration

Config file setup.

### Deployment  

Production deployment guide.

## Troubleshooting

Common issues and solutions.
""")
    
    create_template(root, "anchor-basic-test", """# Anchor Test

## Only Getting Started
${md:sections#Getting Started}

## Only Advanced Usage  
${md:sections#Advanced Usage}

## Only Troubleshooting
${md:sections#Troubleshooting}
""")
    
    result = render_template(root, "ctx:anchor-basic-test")
    
    # Проверяем, что каждый раздел включился отдельно
    assert "Installation instructions here." in result
    assert "Advanced features description." in result
    assert "Common issues and solutions." in result
    
    # Проверяем структуру заголовков (должны сохранить иерархию)
    assert "## Getting Started" in result
    assert "### Requirements" in result
    assert "## Advanced Usage" in result
    assert "### Configuration" in result
    assert "### Deployment" in result
    assert "## Troubleshooting" in result


def test_anchor_with_slug_matching(md_project):
    """Тест сопоставления якорей через slug (приведение к GitHub-стилю)."""
    root = md_project
    
    write_markdown(root / "slugs.md",
                  title="Test Document",
                  content="""## API & Usage

API documentation.

## FAQ: Common Questions

Frequently asked questions.

## Multi-Word Section Title

Content here.
""")
    
    create_template(root, "anchor-slug-test", """# Slug Matching Test

## Using exact text  
${md:slugs#API & Usage}

## Using slug format
${md:slugs#api-usage}

## FAQ section (with colon)
${md:slugs#FAQ: Common Questions}

## Multi-word using slug
${md:slugs#multi-word-section-title}
""")
    
    result = render_template(root, "ctx:anchor-slug-test")
    
    # Все варианты должны работать благодаря slug-сопоставлению
    assert result.count("API documentation.") >= 2  # должно встречаться дважды
    assert result.count("Frequently asked questions.") >= 1
    assert result.count("Content here.") >= 1


def test_anchor_nested_section_inclusion(md_project):
    """Тест включения вложенных разделов."""
    root = md_project
    
    write_markdown(root / "nested.md",
                  title="Documentation",
                  content="""## Installation

Basic installation.

### Prerequisites  

System requirements.

#### Hardware

Minimum specs.

#### Software

Required packages.

### Download

Get the installer.

## Configuration

Setup instructions.
""")
    
    create_template(root, "anchor-nested-test", """# Nested Sections Test

## Prerequisites Section (includes subsections)
${md:nested#Prerequisites}

## Just Hardware Requirements  
${md:nested#Hardware}
""")
    
    result = render_template(root, "ctx:anchor-nested-test")
    
    # Prerequisites должен включать все подразделы
    assert "System requirements." in result
    assert "Minimum specs." in result
    assert "Required packages." in result
    assert "Get the installer." in result
    
    # Hardware должен быть только минимальные specs
    assert result.count("Minimum specs.") >= 2  # встречается в обеих секциях


def test_anchor_nonexistent_section_error(md_project):
    """Тест обработки ошибки при несуществующем якоре."""
    root = md_project
    
    create_template(root, "anchor-notfound-test", """# Not Found Test

${md:docs/api#NonexistentSection}
""")
    
    # Должна возникнуть ошибка о том, что секция не найдена
    with pytest.raises(Exception):  # RuntimeError или другая ошибка
        render_template(root, "ctx:anchor-notfound-test")


def test_anchor_case_insensitive_matching(md_project):
    """Тест нечувствительности к регистру при поиске якорей."""
    root = md_project
    
    write_markdown(root / "case-test.md",
                  title="Case Test",
                  content="""## Installation Guide

Setup instructions.

## API Reference

API docs.
""")
    
    create_template(root, "anchor-case-test", """# Case Test

## Lowercase anchor
${md:case-test#installation guide}

## Mixed case anchor  
${md:case-test#Api Reference}

## Uppercase anchor
${md:case-test#API REFERENCE}
""")
    
    result = render_template(root, "ctx:anchor-case-test")
    
    # Все варианты должны работать
    assert result.count("Setup instructions.") >= 1
    assert result.count("API docs.") >= 2  # встречается дважды


def test_anchor_with_special_characters(md_project):
    """Тест якорей с специальными символами."""
    root = md_project
    
    write_markdown(root / "special.md",
                  title="Special Characters",
                  content="""## Section 1: Overview

Basic info.

## Section 2.1 - Advanced

Advanced topics.

## FAQ (Frequently Asked Questions)

Q&A section.

## "Quoted Section" Title

Special formatting.
""")
    
    create_template(root, "anchor-special-test", """# Special Characters Test

## Overview section
${md:special#Section 1: Overview}

## Advanced section (with dash and dot)
${md:special#Section 2.1 - Advanced}

## FAQ with parentheses
${md:special#FAQ (Frequently Asked Questions)}

## Quoted section
${md:special#"Quoted Section" Title}
""")
    
    result = render_template(root, "ctx:anchor-special-test")
    
    # Все секции должны найтись
    assert "Basic info." in result
    assert "Advanced topics." in result
    assert "Q&A section." in result
    assert "Special formatting." in result


def test_anchor_with_contextual_analysis(md_project):
    """Тест работы якорей с контекстуальным анализом заголовков."""
    root = md_project
    
    create_template(root, "anchor-contextual-test", """# Main Document

## API Documentation

### Authentication Section
${md:docs/api#Authentication}

### Endpoints Section
${md:docs/api#Endpoints}
""")
    
    result = render_template(root, "ctx:anchor-contextual-test")
    
    # Якорные разделы должны быть обработаны с правильными уровнями заголовков
    # Authentication был H2, под H3 должен стать H4
    assert "#### Authentication" in result
    
    # Содержимое Authentication раздела
    assert "Use API keys." in result
    
    # Endpoints раздел  
    assert "#### Endpoints" in result
    assert "### GET /users" in result  # было H3, под H3 стало H4 → H5 (ошибка в ожидании)


def test_anchor_combined_with_explicit_parameters(md_project):
    """Тест якорей в комбинации с явными параметрами."""
    root = md_project
    
    create_template(root, "anchor-params-test", """# Parameters Test

## Authentication (level 5, strip H1)
${md:docs/api#Authentication, level:5, strip_h1:true}

## Endpoints (level 2, keep H1)  
${md:docs/api#Endpoints, level:2, strip_h1:false}
""")
    
    result = render_template(root, "ctx:anchor-params-test")
    
    # Authentication: level:5, strip_h1:true
    assert "##### Authentication" in result  # H2 → H5
    
    # Endpoints: level:2, strip_h1:false  
    assert "## Endpoints" in result         # H2 → H2
    assert "### GET /users" in result       # H3 → H3


def test_anchor_with_addressed_placeholders(md_project):
    """Тест якорей с адресными плейсхолдерами."""
    root = md_project
    
    create_template(root, "anchor-addressed-test", """# Addressed Anchors Test

## Internal Authentication
${md@self:internal#Authentication}

## Main API Authentication
${md:docs/api#Authentication}
""")
    
    # Создаем файл в lg-cfg с Authentication разделом
    write_markdown(root / "lg-cfg" / "internal.md",
                  title="Internal Documentation",
                  content="""## Authentication

Internal auth process.

## Other Section

Other content.
""")
    
    result = render_template(root, "ctx:anchor-addressed-test")
    
    # Должны быть оба раздела Authentication
    assert "Internal auth process." in result  # из @self:internal
    assert "Use API keys." in result           # из docs/api


def test_anchor_empty_section_handling(md_project):
    """Тест обработки пустых разделов."""
    root = md_project
    
    write_markdown(root / "empty-sections.md",
                  title="Empty Sections Test",
                  content="""## Non-Empty Section

Some content.

## Empty Section

## Another Section  

More content.
""")
    
    create_template(root, "anchor-empty-test", """# Empty Sections Test

## Non-empty
${md:empty-sections#Non-Empty Section}

## Empty section  
${md:empty-sections#Empty Section}

## Another
${md:empty-sections#Another Section}
""")
    
    result = render_template(root, "ctx:anchor-empty-test")
    
    # Не пустые разделы должны включиться
    assert "Some content." in result
    assert "More content." in result
    
    # Пустой раздел должен обрабатываться корректно (заголовок без содержимого)
    assert "## Empty Section" in result


@pytest.mark.parametrize("anchor,expected_content", [
    ("Authentication", "Use API keys."),
    ("Endpoints", "Get users list."),
    ("authentication", "Use API keys."),  # case insensitive
    ("ENDPOINTS", "Get users list."),     # case insensitive
])
def test_anchor_parametrized(md_project, anchor, expected_content):
    """Параметризованный тест различных якорей."""
    root = md_project
    
    create_template(root, f"anchor-param-{anchor.lower()}", f"""# Anchor Test

${{md:docs/api#{anchor}}}
""")
    
    result = render_template(root, f"ctx:anchor-param-{anchor.lower()}")
    assert expected_content in result


def test_anchor_with_setext_headings(md_project):
    """Тест якорей с Setext заголовками (подчеркивания)."""
    root = md_project
    
    write_markdown(root / "setext.md",
                  title="",  # без H1
                  content="""Setext Example
==============

This is a setext H1.

Subsection
----------

This is a setext H2.

## ATX Section

This is ATX H2.
""")
    
    create_template(root, "anchor-setext-test", """# Setext Test

## H1 Section
${md:setext#Setext Example}

## H2 Section  
${md:setext#Subsection}

## ATX Section
${md:setext#ATX Section}
""")
    
    result = render_template(root, "ctx:anchor-setext-test")
    
    # Все типы заголовков должны найтись
    assert "This is a setext H1." in result
    assert "This is a setext H2." in result  
    assert "This is ATX H2." in result