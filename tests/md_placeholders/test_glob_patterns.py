"""
Тесты глобов для md-плейсхолдеров.

Проверяет функциональность массового включения файлов:
- ${md:docs/*} для включения всех файлов в папке
- ${md:docs/**} для рекурсивного включения
- Различные паттерны глобов
- Обработка порядка включения файлов
- Комбинации глобов с другими параметрами
"""

from __future__ import annotations

import pytest

from .conftest import (
    md_project, create_template, render_template, 
    create_glob_test_files, write_markdown
)


def test_glob_basic_directory_wildcard(md_project):
    """Тест базового глоба для всех файлов в директории."""
    root = md_project
    
    # Создаем дополнительные файлы для тестирования глобов
    create_glob_test_files(root)
    
    create_template(root, "glob-basic-test", """# Glob Basic Test

## All Documentation Files
${md:docs/*}

End of test.
""")
    
    result = render_template(root, "ctx:glob-basic-test")
    
    # Проверяем, что все файлы из docs/ включились
    assert "User Guide" in result           # из guide.md (уже был)
    assert "API Reference" in result        # из api.md (уже был)
    assert "Project overview" in result     # из overview.md (новый)
    assert "Step by step tutorial" in result  # из tutorial.md (новый)
    assert "Frequently asked questions" in result  # из faq.md (новый)
    
    # Но файлы из подпапок НЕ должны включиться (только *)
    assert "Internal architecture" not in result  # из docs/advanced/internals.md
    assert "Plugin development" not in result     # из docs/advanced/plugins.md
    
    assert "End of test." in result


def test_glob_recursive_wildcard(md_project):
    """Тест рекурсивного глоба для всех файлов включая подпапки."""
    root = md_project
    
    create_glob_test_files(root)
    
    create_template(root, "glob-recursive-test", """# Recursive Glob Test

## All Documentation (including subdirs)
${md:docs/**}
""")
    
    result = render_template(root, "ctx:glob-recursive-test")
    
    # Должны включиться все файлы, включая из подпапок
    assert "User Guide" in result           # docs/guide.md
    assert "API Reference" in result        # docs/api.md  
    assert "Project overview" in result     # docs/overview.md
    assert "Step by step tutorial" in result  # docs/tutorial.md
    assert "Frequently asked questions" in result  # docs/faq.md
    assert "Internal architecture" in result  # docs/advanced/internals.md
    assert "Plugin development" in result     # docs/advanced/plugins.md


def test_glob_specific_pattern(md_project):
    """Тест специфических паттернов глобов."""
    root = md_project
    
    create_glob_test_files(root)
    
    # Создаем файлы с разными именами для паттернов
    write_markdown(root / "docs" / "user-guide.md", "User Guide Extended", "Extended user documentation.")
    write_markdown(root / "docs" / "dev-guide.md", "Developer Guide", "Developer documentation.")
    write_markdown(root / "docs" / "quick-start.md", "Quick Start", "Getting started quickly.")
    
    create_template(root, "glob-pattern-test", """# Pattern Test

## All *-guide files  
${md:docs/*-guide}

## All quick-* files
${md:docs/quick-*}
""")
    
    result = render_template(root, "ctx:glob-pattern-test")
    
    # Должны включиться только файлы, соответствующие паттернам
    assert "Extended user documentation." in result  # user-guide.md
    assert "Developer documentation." in result      # dev-guide.md
    assert "Getting started quickly." in result      # quick-start.md
    
    # Но не должны включиться другие файлы
    assert "Project overview" not in result         # overview.md
    assert "Step by step tutorial" not in result    # tutorial.md


def test_glob_with_contextual_analysis(md_project):
    """Тест глобов с контекстуальным анализом заголовков."""
    root = md_project
    
    create_glob_test_files(root)
    
    create_template(root, "glob-contextual-test", """# Main Documentation

## All Guides Section

### Documentation Files
${md:docs/*}
""")
    
    result = render_template(root, "ctx:glob-contextual-test")
    
    # Файлы должны быть обработаны с правильными уровнями заголовков
    # Под H3 → max_heading_level=4, strip_h1=true
    assert "#### Installation" in result    # было H2 в guide.md, стало H4
    assert "#### Authentication" in result  # было H2 в api.md, стало H4
    
    # H1 заголовки должны быть удалены (strip_h1=true)
    lines = result.split('\n')
    h1_lines = [line for line in lines if line.startswith('#### ') and ('User Guide' in line or 'API Reference' in line)]
    assert len(h1_lines) == 0  # H1 заголовки удалены


def test_glob_with_explicit_parameters(md_project):
    """Тест глобов с явными параметрами."""
    root = md_project
    
    create_glob_test_files(root)
    
    create_template(root, "glob-params-test", """# Parameters Test

## Documentation (level 3, keep H1)
${md:docs/*, level:3, strip_h1:false}

## Advanced Documentation (level 5)  
${md:docs/advanced/*, level:5}
""")
    
    result = render_template(root, "ctx:glob-params-test")
    
    # Первый глоб: level:3, strip_h1:false
    assert "### User Guide" in result       # H1 сохранен, стал H3
    assert "### API Reference" in result    # H1 сохранен, стал H3
    assert "#### Installation" in result    # было H2, стало H4
    
    # Второй глоб: level:5 (strip_h1 по умолчанию)
    assert "##### Internals" in result      # H1 из internals.md стал H5
    assert "##### Plugins" in result        # H1 из plugins.md стал H5


def test_glob_with_conditional_inclusion(md_project):
    """Тест глобов с условным включением.""" 
    root = md_project
    
    # Добавляем конфигурацию тегов
    from .conftest import write
    write(root / "lg-cfg" / "tags.yaml", """
tags:
  advanced:
    title: "Advanced documentation"
  basic:
    title: "Basic documentation"
""")
    
    create_glob_test_files(root)
    
    create_template(root, "glob-conditional-test", """# Conditional Glob Test

## Basic Docs (always)
${md:docs/*.md}

## Advanced Docs (only if advanced tag)
${md:docs/advanced/*, if:tag:advanced}
""")
    
    # Без тегов - только основные файлы
    result1 = render_template(root, "ctx:glob-conditional-test")
    assert "User Guide" in result1          # основной файл
    assert "Internal architecture" not in result1  # из advanced/
    
    # С тегом advanced - все файлы
    from .conftest import make_run_options
    options_advanced = make_run_options(extra_tags={"advanced"})
    result2 = render_template(root, "ctx:glob-conditional-test", options_advanced)
    assert "User Guide" in result2          # основной файл
    assert "Internal architecture" in result2  # из advanced/


def test_glob_empty_directory_handling(md_project):
    """Тест обработки пустых директорий в глобах."""
    root = md_project
    
    # Создаем пустую директорию
    (root / "empty").mkdir(exist_ok=True)
    
    create_template(root, "glob-empty-test", """# Empty Glob Test

## Empty Directory
${md:empty/*}

## Non-existent Directory  
${md:nonexistent/*}

## Regular Files
${md:docs/guide}
""")
    
    # Пустые глобы не должны вызывать ошибку, но могут не включать контент
    result = render_template(root, "ctx:glob-empty-test")
    
    # Обычный файл должен работать
    assert "User Guide" in result
    assert "This is a comprehensive user guide." in result


def test_glob_file_ordering(md_project):
    """Тест порядка файлов при использовании глобов."""
    root = md_project
    
    # Создаем файлы с предсказуемыми именами для проверки порядка
    write_markdown(root / "ordered" / "01-first.md", "First Document", "This is the first document.")
    write_markdown(root / "ordered" / "02-second.md", "Second Document", "This is the second document.")  
    write_markdown(root / "ordered" / "03-third.md", "Third Document", "This is the third document.")
    
    create_template(root, "glob-order-test", """# Order Test

${md:ordered/*}
""")
    
    result = render_template(root, "ctx:glob-order-test")
    
    # Проверяем, что файлы идут в алфавитном порядке (стандартное поведение glob)
    first_pos = result.find("This is the first document.")
    second_pos = result.find("This is the second document.")
    third_pos = result.find("This is the third document.")
    
    assert first_pos < second_pos < third_pos, "Files should be in alphabetical order"


def test_glob_with_anchors_error(md_project):
    """Тест что глобы не поддерживают якорные ссылки."""
    root = md_project
    
    create_template(root, "glob-anchor-error-test", """# Glob Anchor Error

${md:docs/*#Authentication}
""")
    
    # Глобы с якорными ссылками должны вызывать ошибку
    with pytest.raises(Exception):  # ValueError о несовместимости глобов и якорей
        render_template(root, "ctx:glob-anchor-error-test")


def test_glob_complex_patterns(md_project):
    """Тест сложных паттернов глобов."""
    root = md_project
    
    # Создаем файлы с различными расширениями и именами
    write_markdown(root / "mixed" / "doc1.md", "Doc 1", "Document 1 content")
    write_markdown(root / "mixed" / "guide.md", "Guide", "Guide content")
    write_markdown(root / "mixed" / "readme.txt", "ReadMe", "This is a txt file")  # не .md
    (root / "mixed" / "script.py").write_text("print('hello')")  # не .md
    
    create_template(root, "glob-complex-test", """# Complex Patterns

## All .md files in mixed/
${md:mixed/*.md}

## Should be empty (no .txt files processed)
${md:mixed/*.txt}
""")
    
    result = render_template(root, "ctx:glob-complex-test")
    
    # Только .md файлы должны включиться
    assert "Document 1 content" in result
    assert "Guide content" in result
    
    # .txt файлы не должны обрабатываться (секция настроена только на .md)
    assert "This is a txt file" not in result


@pytest.mark.parametrize("pattern,expected_files", [
    ("docs/g*", ["guide"]),                    # файлы, начинающиеся с 'g'
    ("docs/*guide*", ["guide"]),              # файлы, содержащие 'guide'  
    ("docs/a*", ["api"]),                     # файлы, начинающиеся с 'a'
    ("docs/???", ["api"]),                    # файлы из 3 символов
])
def test_glob_patterns_parametrized(md_project, pattern, expected_files):
    """Параметризованный тест различных паттернов глобов."""
    root = md_project
    
    create_template(root, f"glob-param-{pattern.replace('/', '-').replace('*', 'star').replace('?', 'q')}", f"""# Pattern Test

${{md:{pattern}}}
""")
    
    result = render_template(root, f"ctx:glob-param-{pattern.replace('/', '-').replace('*', 'star').replace('?', 'q')}")
    
    # Проверяем наличие ожидаемых файлов
    for expected_file in expected_files:
        if expected_file == "guide":
            assert "User Guide" in result
        elif expected_file == "api":
            assert "API Reference" in result