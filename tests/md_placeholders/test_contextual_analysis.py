"""
Тесты контекстуального анализа заголовков для md-плейсхолдеров.

Реализует логику согласно ТЗ:
- strip_h1=true когда плейсхолдеры разделены заголовками родительского шаблона
- strip_h1=false когда плейсхолдеры образуют непрерывную цепочку
- max_heading_level определяется уровнем ближайшего родительского заголовка
"""

from __future__ import annotations

from .conftest import md_project, create_template, render_template


def extract_heading_level(text: str, heading_text: str) -> int | None:
    """
    Извлекает точный уровень заголовка из текста.
    
    Args:
        text: Текст для поиска
        heading_text: Текст заголовка (без #)
    
    Returns:
        Уровень заголовка (количество #) или None если не найден
    """
    heading_text = heading_text.strip()
    
    for line in text.split('\n'):
        line_stripped = line.strip()

        # Проверяем, начинается ли строка с #
        if line_stripped.startswith('#'):
            # Считаем количество # в начале
            level = 0
            for char in line_stripped:
                if char == '#':
                    level += 1
                else:
                    break

            # Получаем текст заголовка (после # и пробелов)
            title_part = line_stripped[level:].strip()

            # Сравниваем с искомым заголовком
            if title_part == heading_text:
                return level

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
        f"but found level {actual_level}. Full result:\n{result}"
    )


def assert_heading_not_present(result: str, heading_text: str):
    """
    Проверяет, что заголовок отсутствует в результате.
    
    Args:
        result: Результат рендеринга
        heading_text: Текст заголовка для проверки
    """
    actual_level = extract_heading_level(result, heading_text)
    assert actual_level is None, (
        f"Heading '{heading_text}' should not be present, but found at level {actual_level}. "
        f"Full result:\n{result}"
    )


# ===== Тесты для strip_h1=true (плейсхолдеры разделены заголовками) =====

def test_placeholders_separated_by_headings_strip_h1_true(md_project):
    """
    Тест случая strip_h1=true: плейсхолдеры разделены заголовками родительского шаблона.
    
    Соответствует первому примеру из ТЗ:
    ### Шаблоны, контексты и каскадные включения
    ${md:docs/templates}
    ### Руководство по работе с Markdown
    ${md:docs/markdown}
    """
    root = md_project
    
    create_template(root, "separated-placeholders", """# Listing Generator 

## Расширенная документация

### Шаблоны, контексты и каскадные включения

${md:docs/api}

### Руководство по работе с Markdown

${md:docs/guide}

### Языковые адаптеры

${md:docs/changelog}

## Лицензия
""")
    
    result = render_template(root, "ctx:separated-placeholders")
    
    # Плейсхолдеры разделены заголовками H3 родительского шаблона
    # Поэтому strip_h1=true, max_heading_level=4 (H3+1)
    
    # H1 заголовки из файлов должны быть удалены
    assert_heading_not_present(result, "API Reference")
    assert_heading_not_present(result, "User Guide")
    # changelog.md не имеет H1, поэтому ничего не удаляется
    
    # H2 заголовки из файлов становятся H4 (под H3 родительского шаблона)
    assert_heading_level(result, "Authentication", 4)  # из api.md
    assert_heading_level(result, "Endpoints", 4)       # из api.md
    assert_heading_level(result, "Installation", 4)    # из guide.md
    assert_heading_level(result, "Usage", 4)           # из guide.md
    assert_heading_level(result, "v1.0.0", 4)         # из changelog.md
    assert_heading_level(result, "v0.9.0", 4)         # из changelog.md
    
    # Заголовки из родительского шаблона должны остаться на своих местах
    assert_heading_level(result, "Listing Generator", 1)
    assert_heading_level(result, "Расширенная документация", 2)
    assert_heading_level(result, "Шаблоны, контексты и каскадные включения", 3)
    assert_heading_level(result, "Руководство по работе с Markdown", 3)
    assert_heading_level(result, "Языковые адаптеры", 3)
    assert_heading_level(result, "Лицензия", 2)


def test_placeholders_separated_by_h2_headings(md_project):
    """
    Тест случая strip_h1=true с заголовками H2 в качестве разделителей.
    """
    root = md_project
    
    create_template(root, "h2-separated", """# Project Documentation

## API Reference Section

${md:docs/api}

## User Guide Section

${md:docs/guide}

## Changelog Section

${md:docs/changelog}

## Summary
""")
    
    result = render_template(root, "ctx:h2-separated")
    
    # Плейсхолдеры разделены заголовками H2
    # strip_h1=true, max_heading_level=3 (H2+1)
    
    # H1 заголовки из файлов удалены
    assert_heading_not_present(result, "API Reference")
    assert_heading_not_present(result, "User Guide")
    
    # H2 заголовки из файлов становятся H3
    assert_heading_level(result, "Authentication", 3)
    assert_heading_level(result, "Installation", 3)
    assert_heading_level(result, "v1.0.0", 3)


# ===== Тесты для strip_h1=false (плейсхолдеры образуют цепочку) =====

def test_placeholders_continuous_chain_strip_h1_false(md_project):
    """
    Тест случая strip_h1=false: плейсхолдеры образуют непрерывную цепочку.
    
    Соответствует второму примеру из ТЗ:
    ## Расширенная документация
    ${md:docs/templates}
    ${md:docs/markdown}
    ${md:docs/markdown}
    """
    root = md_project
    
    create_template(root, "continuous-chain", """# Listing Generator 

## Расширенная документация

${md:docs/api}

${md:docs/guide}

${md:docs/changelog}

## Лицензия
""")
    
    result = render_template(root, "ctx:continuous-chain")
    
    # Плейсхолдеры образуют непрерывную цепочку под H2
    # strip_h1=false, max_heading_level=3 (H2+1)
    
    # H1 заголовки из файлов сохраняются, но становятся H3
    assert_heading_level(result, "API Reference", 3)   # было H1, стало H3
    assert_heading_level(result, "User Guide", 3)      # было H1, стало H3
    # changelog.md не имеет H1
    
    # H2 заголовки из файлов становятся H4
    assert_heading_level(result, "Authentication", 4)  # было H2, стало H4
    assert_heading_level(result, "Installation", 4)    # было H2, стало H4
    # Но заголовки из changelog.md (который без H1) также нормализуются как H2->H3
    assert_heading_level(result, "v1.0.0", 3)         # было H2, стало H3 (файл без H1)
    
    # Заголовки из родительского шаблона сохраняются
    assert_heading_level(result, "Listing Generator", 1)
    assert_heading_level(result, "Расширенная документация", 2)
    assert_heading_level(result, "Лицензия", 2)


def test_continuous_chain_starting_immediately(md_project):
    """
    Тест непрерывной цепочки, начинающейся сразу после заголовка секции.
    """
    root = md_project
    
    create_template(root, "immediate-chain", """# Main Document

## Documentation Section
${md:docs/api}
${md:docs/guide}
${md:docs/changelog}

## Other Section

Some other content.
""")
    
    result = render_template(root, "ctx:immediate-chain")
    
    # Плейсхолдеры образуют цепочку под H2
    # strip_h1=false, max_heading_level=3
    
    # H1 заголовки сохраняются на уровне H3
    assert_heading_level(result, "API Reference", 3)
    assert_heading_level(result, "User Guide", 3)
    
    # H2 заголовки на уровне H4
    assert_heading_level(result, "Authentication", 4)
    assert_heading_level(result, "Installation", 4)


def test_mixed_content_between_placeholders_breaks_chain(md_project):
    """
    Тест что произвольный контент между плейсхолдерами прерывает цепочку.
    
    Если между плейсхолдерами есть другой контент, это может изменить логику.
    Уточним поведение: текст между плейсхолдерами НЕ прерывает цепочку,
    только заголовки прерывают.
    """
    root = md_project
    
    create_template(root, "mixed-content", """# Main Document

## Documentation Section

${md:docs/api}

Some explanatory text between placeholders.

${md:docs/guide}

More text.

${md:docs/changelog}

## Other Section
""")
    
    result = render_template(root, "ctx:mixed-content")
    
    # Текст между плейсхолдерами НЕ прерывает цепочку
    # strip_h1=false, max_heading_level=3
    
    assert_heading_level(result, "API Reference", 3)
    assert_heading_level(result, "User Guide", 3)


# ===== Тесты для определения max_heading_level =====

def test_max_heading_level_from_h4_context(md_project):
    """
    Тест автоматического определения max_heading_level=5 при вставке под H4.
    """
    root = md_project
    
    create_template(root, "h4-context", """# Main

## Part 1

### Chapter 1

#### Section: API Documentation

${md:docs/api}

#### Another Section

Some content.
""")
    
    result = render_template(root, "ctx:h4-context")
    
    # Плейсхолдер под H4, разделен от других заголовком
    # strip_h1=true, max_heading_level=5 (H4+1)
    
    # H1 удален
    assert_heading_not_present(result, "API Reference")
    
    # H2 заголовки становятся H5
    assert_heading_level(result, "Authentication", 5)
    assert_heading_level(result, "Endpoints", 5)


def test_max_heading_level_limits_at_h6(md_project):
    """
    Тест ограничения максимального уровня заголовков на H6.
    """
    root = md_project
    
    create_template(root, "h6-limit", """# Level 1

## Level 2

### Level 3

#### Level 4

##### Level 5

###### Level 6 Section

${md:docs/api}
""")
    
    result = render_template(root, "ctx:h6-limit")
    
    # При попытке установить max_heading_level=7, система должна ограничить до H6
    # или применить другую логику для предотвращения недопустимых заголовков
    
    lines = result.split('\n')
    invalid_headings = [line for line in lines if line.startswith('#######')]
    assert len(invalid_headings) == 0, f"Found invalid H7+ headings: {invalid_headings}"
    
    # Содержимое файлов должно присутствовать
    assert "Authentication" in result
    assert "Endpoints" in result


# ===== Тесты для плейсхолдеров внутри заголовков =====

def test_placeholder_inside_heading_replaces_heading_text(md_project):
    """
    Тест плейсхолдера внутри заголовка - заменяет текст заголовка.
    
    ### ${md:docs/api}
    
    Здесь H1 из api.md становится содержимым заголовка H3.
    """
    root = md_project
    
    create_template(root, "inline-heading", """# Listing Generator 

## Расширенная документация

### ${md:docs/api}

### ${md:docs/guide}

## Заключение
""")
    
    result = render_template(root, "ctx:inline-heading")
    
    # Плейсхолдеры внутри заголовков H3
    # H1 из файлов заменяет содержимое заголовков H3
    # strip_h1=true (H1 использован для заголовка), max_heading_level=4
    
    assert_heading_level(result, "API Reference", 3)   # H1 из api.md стал H3
    assert_heading_level(result, "User Guide", 3)      # H1 из guide.md стал H3
    
    # H2 заголовки из файлов становятся H4
    assert_heading_level(result, "Authentication", 4)
    assert_heading_level(result, "Installation", 4)


def test_placeholder_inside_h2_heading(md_project):
    """
    Тест плейсхолдера внутри заголовка H2.
    """
    root = md_project
    
    create_template(root, "h2-inline", """# Project Manual

## API: ${md:docs/api}

## Guide: ${md:docs/guide}

## Summary
""")
    
    result = render_template(root, "ctx:h2-inline")
    
    # H1 из файлов становится частью H2 заголовков
    assert_heading_level(result, "API: API Reference", 2)
    assert_heading_level(result, "Guide: User Guide", 2)
    
    # H2 заголовки из файлов становятся H3
    assert_heading_level(result, "Authentication", 3)
    assert_heading_level(result, "Installation", 3)


# ===== Тесты для явных параметров =====

def test_explicit_parameters_override_contextual_analysis(md_project):
    """
    Тест что явные параметры переопределяют контекстуальный анализ.
    """
    root = md_project
    
    create_template(root, "explicit-override", """# Main

## Section

### Subsection

${md:docs/api, level:2, strip_h1:false}
""")
    
    result = render_template(root, "ctx:explicit-override")
    
    # Явные параметры должны переопределить автоматический анализ
    # level:2 означает max_heading_level=2
    # strip_h1:false означает сохранить H1
    
    assert_heading_level(result, "API Reference", 2)    # H1→H2 (явно задано)
    assert_heading_level(result, "Authentication", 3)   # H2→H3


def test_explicit_strip_h1_true_overrides_chain_logic(md_project):
    """
    Тест что явный strip_h1:true переопределяет логику цепочки.
    """
    root = md_project
    
    create_template(root, "explicit-strip", """# Main

## Documentation

${md:docs/api, strip_h1:true}

${md:docs/guide, strip_h1:true}
""")
    
    result = render_template(root, "ctx:explicit-strip")
    
    # Несмотря на цепочку плейсхолдеров, явный strip_h1:true должен сработать
    assert_heading_not_present(result, "API Reference")
    assert_heading_not_present(result, "User Guide")
    
    # Содержимое начинается с H3 (под H2)
    assert_heading_level(result, "Authentication", 3)
    assert_heading_level(result, "Installation", 3)


# ===== Специальные случаи =====

def test_setext_headings_in_contextual_analysis(md_project):
    """
    Тест контекстуального анализа с Setext заголовками (подчеркивания).
    """
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
    
    # Setext заголовки: "Project Guide" = H1, "API Documentation" = H2
    # Плейсхолдеры разделены заголовками H2
    # strip_h1=true, max_heading_level=3
    
    assert_heading_not_present(result, "API Reference")
    assert_heading_not_present(result, "User Guide")
    
    assert_heading_level(result, "Authentication", 3)
    assert_heading_level(result, "Installation", 3)


def test_fenced_blocks_ignored_in_contextual_analysis(md_project):
    """
    Тест что заголовки в fenced-блоках игнорируются при анализе контекста.
    """
    root = md_project
    
    create_template(root, "fenced-ignore", """# Documentation

## Configuration Example

```yaml
# This is not a real heading
## This is also not a heading  
### Neither is this
```

### Actual Section

${md:docs/api}

### Another Section

More content.
""")
    
    result = render_template(root, "ctx:fenced-ignore")
    
    # Должен анализировать только реальные заголовки, игнорируя ```-блоки
    # Плейсхолдер разделен заголовками H3
    # strip_h1=true, max_heading_level=4
    
    assert_heading_not_present(result, "API Reference")
    assert_heading_level(result, "Authentication", 4)
