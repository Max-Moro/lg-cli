"""
Тесты явных параметров для md-плейсхолдеров.

Проверяет функциональность переопределения автоматических настроек:
- ${md:file, level:4, strip_h1:false}
- Приоритет явных параметров над контекстуальным анализом
- Различные комбинации параметров
- Обработка некорректных параметров
"""

from __future__ import annotations

import pytest

from .conftest import md_project, create_template, render_template


def test_explicit_level_parameter(md_project):
    """Тест явного параметра level для переопределения max_heading_level."""
    root = md_project
    
    create_template(root, "explicit-level-test", """# Main Document

## Default Context (should be level 3)
${md:docs/api}

## Explicit Level 5  
${md:docs/api, level:5}

## Explicit Level 2
${md:docs/guide, level:2}
""")
    
    result = render_template(root, "ctx:explicit-level-test")
    
    # Первое включение: контекстуальный анализ (под H2 → max_heading_level=3)
    api_occurrences = []
    guide_occurrences = []
    
    lines = result.split('\n')
    for line in lines:
        if 'API Reference' in line:
            api_occurrences.append(line.strip())
        elif 'User Guide' in line:
            guide_occurrences.append(line.strip())
    
    # Должно быть 2 включения API Reference
    assert len(api_occurrences) >= 2
    
    # Проверяем уровни заголовков для разных параметров level
    assert any(line.startswith('### ') for line in api_occurrences)  # контекстуальный (level 3)
    assert any(line.startswith('##### ') for line in api_occurrences)  # explicit level 5
    
    # Guide с явным level:2
    assert len(guide_occurrences) >= 1
    assert any(line.startswith('## ') for line in guide_occurrences)  # explicit level 2


def test_explicit_strip_h1_parameter(md_project):
    """Тест явного параметра strip_h1."""
    root = md_project
    
    create_template(root, "explicit-strip-test", """# Documentation

## Section with H1 preserved  
${md:docs/api, strip_h1:false}

## Section with H1 removed
${md:docs/guide, strip_h1:true}
""")
    
    result = render_template(root, "ctx:explicit-strip-test")
    
    # strip_h1:false - H1 должен сохраниться и стать H3 (под H2)
    assert "### API Reference" in result
    
    # strip_h1:true - H1 должен быть удален, остальные заголовки сдвинуты
    lines = result.split('\n')
    
    # Не должно быть H3 "User Guide" (удален)
    guide_h3_lines = [line for line in lines if line.strip() == "### User Guide"]
    assert len(guide_h3_lines) == 0
    
    # Но H2 заголовки из guide должны присутствовать как H3
    assert "### Installation" in result  # было H2, стало H3
    assert "### Usage" in result         # было H2, стало H3


def test_explicit_parameters_combination(md_project):
    """Тест комбинации явных параметров level и strip_h1."""
    root = md_project
    
    create_template(root, "combo-params-test", """# Test Document

${md:docs/api, level:4, strip_h1:false}

${md:docs/guide, level:6, strip_h1:true}
""")
    
    result = render_template(root, "ctx:combo-params-test")
    
    # api.md: level:4, strip_h1:false
    assert "#### API Reference" in result    # H1→H4, сохранен
    assert "##### Authentication" in result  # H2→H5
    
    # guide.md: level:6, strip_h1:true  
    # H1 удален, H2 становятся H6
    assert "###### Installation" in result   # было H2, стало H6
    assert "###### Usage" in result          # было H2, стало H6
    
    # H1 "User Guide" не должно быть
    lines = result.split('\n')
    guide_h6_lines = [line for line in lines if line.strip().startswith("###### ") and "User Guide" in line]
    assert len(guide_h6_lines) == 0


def test_explicit_parameters_override_contextual_analysis(md_project):
    """Тест что явные параметры переопределяют контекстуальный анализ."""
    root = md_project
    
    create_template(root, "override-contextual-test", """# Main

## Deep Section

### Very Deep

#### Super Deep

##### Extremely Deep  

###### Maximum Depth Context

${md:docs/api, level:2, strip_h1:false}
""")
    
    result = render_template(root, "ctx:override-contextual-test")
    
    # Несмотря на глубокую вложенность (H6), явные параметры должны сработать
    assert "## API Reference" in result     # level:2, strip_h1:false
    assert "### Authentication" in result   # было H2, стало H3


def test_explicit_level_parameter_edge_cases(md_project):
    """Тест граничных случаев для параметра level."""
    root = md_project
    
    create_template(root, "level-edges-test", """# Edge Cases

## Level 1 (minimum)
${md:docs/api, level:1}

## Level 6 (maximum valid)  
${md:docs/guide, level:6}
""")
    
    result = render_template(root, "ctx:level-edges-test")
    
    # level:1 - минимальный уровень
    assert "# API Reference" in result      # H1→H1 (остался как есть)
    assert "## Authentication" in result    # H2→H2
    
    # level:6 - максимальный уровень
    assert "###### User Guide" in result    # H1→H6
    # H2 не может стать H7 (невалидно), должен остаться H6 или обрабатываться по-другому
    lines = result.split('\n')
    h7_lines = [line for line in lines if line.startswith('#######')]
    assert len(h7_lines) == 0, "Found invalid H7+ headings"


def test_invalid_level_parameter_error(md_project):
    """Тест обработки некорректных значений параметра level."""
    root = md_project
    
    # Тестируем различные некорректные значения
    test_cases = [
        "${md:docs/api, level:0}",     # меньше минимума
        "${md:docs/api, level:7}",     # больше максимума  
        "${md:docs/api, level:abc}",   # не число
        "${md:docs/api, level:}",      # пустое значение
    ]
    
    for i, invalid_placeholder in enumerate(test_cases):
        create_template(root, f"invalid-level-{i}", f"""# Invalid Level Test

{invalid_placeholder}
""")
        
        # Должна возникать ошибка валидации
        with pytest.raises(Exception):  # ValueError или другая ошибка валидации
            render_template(root, f"ctx:invalid-level-{i}")


def test_invalid_strip_h1_parameter_error(md_project):
    """Тест обработки некорректных значений параметра strip_h1."""
    root = md_project
    
    test_cases = [
        "${md:docs/api, strip_h1:yes}",    # не boolean
        "${md:docs/api, strip_h1:1}",      # число вместо boolean
        "${md:docs/api, strip_h1:}",       # пустое значение
    ]
    
    for i, invalid_placeholder in enumerate(test_cases):
        create_template(root, f"invalid-strip-{i}", f"""# Invalid Strip Test

{invalid_placeholder}
""")
        
        with pytest.raises(Exception):  # ValueError или другая ошибка валидации
            render_template(root, f"ctx:invalid-strip-{i}")


def test_parameter_parsing_with_spaces(md_project):
    """Тест парсинга параметров с различными пробелами."""
    root = md_project
    
    create_template(root, "spaces-test", """# Spaces Test

## No spaces
${md:docs/api,level:3,strip_h1:true}

## With spaces
${md:docs/guide, level:4, strip_h1:false}

## Mixed spaces  
${md:docs/changelog,level:5, strip_h1: true}
""")
    
    result = render_template(root, "ctx:spaces-test")
    
    # Все варианты должны работать корректно
    assert "### Authentication" in result    # api: level:3, strip_h1:true
    assert "#### User Guide" in result       # guide: level:4, strip_h1:false  
    assert "##### v1.0.0" in result          # changelog: level:5, strip_h1:true


def test_unknown_parameter_error(md_project):
    """Тест обработки неизвестных параметров."""
    root = md_project
    
    create_template(root, "unknown-param-test", """# Unknown Parameter Test

${md:docs/api, level:3, unknown_param:value, strip_h1:true}
""")
    
    # Неизвестные параметры должны вызывать ошибку или игнорироваться
    with pytest.raises(Exception):  # ValueError о неизвестном параметре
        render_template(root, "ctx:unknown-param-test")


def test_parameter_case_sensitivity(md_project):
    """Тест чувствительности к регистру в параметрах."""
    root = md_project
    
    create_template(root, "case-test", """# Case Sensitivity Test

${md:docs/api, Level:3, Strip_H1:True}
""")
    
    # Параметры должны быть чувствительны к регистру
    with pytest.raises(Exception):  # Неизвестные параметры Level, Strip_H1
        render_template(root, "ctx:case-test")


@pytest.mark.parametrize("level,expected_h1,expected_h2", [
    (1, "# API Reference", "## Authentication"),
    (2, "## API Reference", "### Authentication"), 
    (3, "### API Reference", "#### Authentication"),
    (4, "#### API Reference", "##### Authentication"),
    (5, "##### API Reference", "###### Authentication"),
    (6, "###### API Reference", "###### Authentication"),  # H2 не может стать H7
])
def test_level_parameter_parametrized(md_project, level, expected_h1, expected_h2):
    """Параметризованный тест различных значений level."""
    root = md_project
    
    create_template(root, f"param-level-{level}", f"""# Level {level} Test

${{md:docs/api, level:{level}, strip_h1:false}}
""")
    
    result = render_template(root, f"ctx:param-level-{level}")
    
    assert expected_h1 in result
    # Для level:6 H2 может не преобразовываться в H7 (проверяем отдельно)
    if level < 6:
        assert expected_h2 in result


@pytest.mark.parametrize("strip_h1,should_have_h1", [
    (True, False),   # strip_h1:true - не должно быть H1
    (False, True),   # strip_h1:false - должен быть H1
])
def test_strip_h1_parameter_parametrized(md_project, strip_h1, should_have_h1):
    """Параметризованный тест strip_h1."""
    root = md_project
    
    create_template(root, f"param-strip-{strip_h1}", f"""# Strip H1 Test

${{md:docs/api, level:3, strip_h1:{str(strip_h1).lower()}}}
""")
    
    result = render_template(root, f"ctx:param-strip-{strip_h1}")
    
    has_api_h3 = "### API Reference" in result
    assert has_api_h3 == should_have_h1, f"Expected H1 presence: {should_have_h1}, got: {has_api_h3}"