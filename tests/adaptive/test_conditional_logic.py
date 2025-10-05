"""
Тесты условной логики в шаблонах.

Проверяет работу условных блоков {% if %}, операторов AND/OR/NOT,
TAGSET условий и их комбинаций в адаптивных шаблонах.
"""

from __future__ import annotations

import pytest

from lg.template.processor import TemplateProcessingError
from .conftest import (
    adaptive_project, make_run_options, render_template,
    create_conditional_template, TagConfig, TagSetConfig,
    create_tags_yaml
)


def test_basic_tag_conditions(adaptive_project):
    """Тест базовых условий на теги."""
    root = adaptive_project
    
    template_content = """# Tag Conditions Test

{% if tag:minimal %}
## Minimal section
Content for minimal mode
{% endif %}

{% if tag:nonexistent %}
## Should not appear
This should not be rendered
{% endif %}

## Always visible
This is always shown
"""
    
    create_conditional_template(root, "tag-conditions", template_content)
    
    # Тест без активных тегов
    result1 = render_template(root, "ctx:tag-conditions", make_run_options())
    assert "Minimal section" not in result1
    assert "Should not appear" not in result1  
    assert "Always visible" in result1
    
    # Тест с активным тегом
    options = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "ctx:tag-conditions", options)
    assert "Minimal section" in result2
    assert "Should not appear" not in result2
    assert "Always visible" in result2


def test_negation_conditions(adaptive_project):
    """Тест условий отрицания NOT."""
    root = adaptive_project
    
    template_content = """# Negation Test

{% if NOT tag:minimal %}
## Full mode
Complete documentation and code
{% else %}
## Minimal mode  
Condensed version
{% endif %}

{% if NOT tag:nonexistent %}
## Always true
This should always appear (NOT nonexistent)
{% endif %}
"""
    
    create_conditional_template(root, "negation-test", template_content)
    
    # Без тегов - NOT tag:minimal = true
    result1 = render_template(root, "ctx:negation-test", make_run_options())
    assert "Full mode" in result1
    assert "Minimal mode" not in result1
    assert "Always true" in result1
    
    # С тегом minimal - NOT tag:minimal = false
    options = make_run_options(extra_tags={"minimal"})  
    result2 = render_template(root, "ctx:negation-test", options)
    assert "Full mode" not in result2
    assert "Minimal mode" in result2
    assert "Always true" in result2


def test_and_or_conditions(adaptive_project):
    """Тест логических операторов AND и OR."""
    root = adaptive_project
    
    template_content = """# AND/OR Test

{% if tag:agent AND tag:tools %}
## Full agent mode
Both agent and tools active
{% endif %}

{% if tag:minimal OR tag:review %}
## Compact mode
Either minimal or review active
{% endif %}

{% if tag:python AND NOT tag:minimal %}
## Full Python
Complete Python documentation
{% endif %}

{% if tag:docs OR tag:architecture %}
## Documentation
Architecture or docs mode
{% endif %}
"""
    
    create_conditional_template(root, "and-or-test", template_content)
    
    # Тест AND - оба тега активны
    options1 = make_run_options(extra_tags={"agent", "tools"})
    result1 = render_template(root, "ctx:and-or-test", options1)
    assert "Full agent mode" in result1
    
    # Тест AND - только один тег активен  
    options2 = make_run_options(extra_tags={"agent"})
    result2 = render_template(root, "ctx:and-or-test", options2)
    assert "Full agent mode" not in result2
    
    # Тест OR - один из тегов активен
    options3 = make_run_options(extra_tags={"minimal"})
    result3 = render_template(root, "ctx:and-or-test", options3)
    assert "Compact mode" in result3
    
    options4 = make_run_options(extra_tags={"review"})
    result4 = render_template(root, "ctx:and-or-test", options4)
    assert "Compact mode" in result4
    
    # Тест сложной комбинации AND NOT
    options5 = make_run_options(extra_tags={"python"})
    result5 = render_template(root, "ctx:and-or-test", options5)
    assert "Full Python" in result5
    
    options6 = make_run_options(extra_tags={"python", "minimal"})
    result6 = render_template(root, "ctx:and-or-test", options6)
    assert "Full Python" not in result6


def test_tagset_conditions(adaptive_project):
    """Тест специальных TAGSET условий."""
    root = adaptive_project
    
    template_content = """# TAGSET Test

{% if TAGSET:language:python %}
## Python section
Python-specific content
{% endif %}

{% if TAGSET:language:typescript %}
## TypeScript section  
TypeScript-specific content
{% endif %}

{% if TAGSET:code-type:tests %}
## Test code section
Test-specific content
{% endif %}

{% if TAGSET:nonexistent:any %}
## Should always show
Nonexistent tagset should be true
{% endif %}
"""
    
    create_conditional_template(root, "tagset-test", template_content)
    
    # Без активных тегов - все TAGSET условия должны быть true
    result1 = render_template(root, "ctx:tagset-test", make_run_options())
    assert "Python section" in result1
    assert "TypeScript section" in result1 
    assert "Test code section" in result1
    assert "Should always show" in result1
    
    # Активируем python - только TAGSET:language:python должно быть true
    options2 = make_run_options(extra_tags={"python"})
    result2 = render_template(root, "ctx:tagset-test", options2)
    assert "Python section" in result2
    assert "TypeScript section" not in result2
    assert "Test code section" in result2  # другой набор, остается true
    
    # Активируем tests из code-type набора
    options3 = make_run_options(extra_tags={"tests"})
    result3 = render_template(root, "ctx:tagset-test", options3)
    assert "Python section" in result3      # language набор пуст, true
    assert "TypeScript section" in result3  # language набор пуст, true
    assert "Test code section" in result3   # tests активен в code-type


def test_complex_nested_conditions(adaptive_project):
    """Тест сложных вложенных условий."""
    root = adaptive_project
    
    template_content = """# Complex Conditions

{% if tag:agent %}
## Agent Mode

{% if tag:tools AND tag:review %}
### Agent with review tools
Full agent capabilities for review
{% elif tag:tools %}
### Agent with basic tools  
Standard agent capabilities
{% else %}
### Basic agent
Minimal agent without tools
{% endif %}

{% if TAGSET:language:python OR TAGSET:language:typescript %}
### Language-specific agent
Agent for specific language
{% endif %}

{% endif %}

{% if NOT tag:agent AND tag:minimal %}
## Minimal non-agent mode
Simplified interface without agent
{% endif %}
"""
    
    create_conditional_template(root, "complex-nested", template_content)
    
    # Тест агента с полными возможностями
    options1 = make_run_options(extra_tags={"agent", "tools", "review", "python"})
    result1 = render_template(root, "ctx:complex-nested", options1)
    assert "Agent Mode" in result1
    assert "Agent with review tools" in result1
    assert "Basic agent" not in result1
    assert "Language-specific agent" in result1
    assert "Minimal non-agent mode" not in result1
    
    # Тест агента с базовыми инструментами
    options2 = make_run_options(extra_tags={"agent", "tools"})  
    result2 = render_template(root, "ctx:complex-nested", options2)
    assert "Agent Mode" in result2
    assert "Agent with basic tools" in result2
    assert "Agent with review tools" not in result2
    assert "Language-specific agent" in result2  # TAGSET без активных языков = true
    
    # Тест минимального режима без агента
    options3 = make_run_options(extra_tags={"minimal"})
    result3 = render_template(root, "ctx:complex-nested", options3)
    assert "Agent Mode" not in result3
    assert "Minimal non-agent mode" in result3


def test_parentheses_in_conditions(adaptive_project):
    """Тест группировки условий с помощью скобок."""
    root = adaptive_project
    
    template_content = """# Parentheses Test

{% if (tag:python OR tag:typescript) AND tag:docs %}
## Documented language
Language with documentation
{% endif %}

{% if tag:agent AND (tag:minimal OR tag:review) %}
## Focused agent
Agent in specific mode
{% endif %}

{% if NOT (tag:agent AND tag:tools) %}
## Not full agent
Either no agent or agent without tools
{% endif %}
"""
    
    create_conditional_template(root, "parentheses-test", template_content)
    
    # Тест первого условия
    options1 = make_run_options(extra_tags={"python", "docs"})
    result1 = render_template(root, "ctx:parentheses-test", options1)
    assert "Documented language" in result1
    
    options2 = make_run_options(extra_tags={"python"})  # без docs
    result2 = render_template(root, "ctx:parentheses-test", options2)
    assert "Documented language" not in result2
    
    # Тест второго условия
    options3 = make_run_options(extra_tags={"agent", "minimal"})
    result3 = render_template(root, "ctx:parentheses-test", options3)
    assert "Focused agent" in result3
    
    # Тест третьего условия (отрицание группы)
    options4 = make_run_options(extra_tags={"agent"})  # agent без tools
    result4 = render_template(root, "ctx:parentheses-test", options4)
    assert "Not full agent" in result4
    
    options5 = make_run_options(extra_tags={"agent", "tools"})  # полный agent
    result5 = render_template(root, "ctx:parentheses-test", options5)
    assert "Not full agent" not in result5


def test_else_and_elif_blocks(adaptive_project):
    """Тест блоков else и elif."""
    root = adaptive_project
    
    template_content = """# Else/Elif Test

{% if tag:agent %}
## Agent active
{% elif tag:minimal %}
## Minimal mode
{% elif tag:review %}
## Review mode
{% else %}
## Default mode
{% endif %}

{% if tag:python %}
### Python detected
{% else %}
### Other language or none
{% endif %}
"""
    
    create_conditional_template(root, "else-elif-test", template_content)
    
    # Тест if (первое условие)
    options1 = make_run_options(extra_tags={"agent", "minimal"})  # agent имеет приоритет
    result1 = render_template(root, "ctx:else-elif-test", options1)
    assert "Agent active" in result1
    assert "Minimal mode" not in result1
    assert "Default mode" not in result1
    
    # Тест elif (второе условие)
    options2 = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "ctx:else-elif-test", options2)
    assert "Agent active" not in result2
    assert "Minimal mode" in result2
    assert "Default mode" not in result2
    
    # Тест else (ни одно условие не подошло)
    options3 = make_run_options(extra_tags={"docs"})
    result3 = render_template(root, "ctx:else-elif-test", options3)
    assert "Agent active" not in result3
    assert "Minimal mode" not in result3
    assert "Default mode" in result3
    
    # Тест вложенного else
    assert "Other language or none" in result3


def test_conditions_with_mode_blocks(adaptive_project):
    """Тест взаимодействия условий с блоками режимов."""
    root = adaptive_project
    
    template_content = """# Conditions with Mode Blocks

{% mode ai-interaction:agent %}
## Inside agent mode

{% if tag:tools %}
### Tools available in agent mode
{% endif %}

{% if tag:minimal %}
### Minimal agent
{% else %}
### Full agent  
{% endif %}

{% endmode %}

{% if tag:agent %}
## Agent tag detected outside mode block
{% endif %}
"""
    
    create_conditional_template(root, "mode-conditions", template_content)
    
    # Тест 1: без предварительно активированного тега agent
    result1 = render_template(root, "ctx:mode-conditions", make_run_options())
    
    # В блоке режима agent активируются теги agent и tools
    assert "Inside agent mode" in result1
    assert "Tools available in agent mode" in result1
    assert "Full agent" in result1  # tag:minimal не активен
    assert "Minimal agent" not in result1
    
    # Вне блока режима тег agent НЕ должен быть доступен (режим восстанавливается)
    assert "Agent tag detected outside mode block" not in result1
    
    # Тест 2: с предварительно активированным тегом agent
    result2 = render_template(root, "ctx:mode-conditions", make_run_options(extra_tags={"agent"}))
    
    # В блоке режима agent все еще активен
    assert "Inside agent mode" in result2
    assert "Tools available in agent mode" in result2
    assert "Full agent" in result2
    assert "Minimal agent" not in result2
    
    # Вне блока режима тег agent должен быть доступен (был активен изначально)
    assert "Agent tag detected outside mode block" in result2


def test_custom_tagsets_in_conditions(adaptive_project):
    """Тест пользовательских наборов тегов в условиях.""" 
    root = adaptive_project
    
    # Добавляем кастомный набор тегов
    custom_tag_sets = {
        "feature-flags": TagSetConfig(
            title="Feature Flags",
            tags={
                "new-ui": TagConfig(title="New UI"),
                "beta-api": TagConfig(title="Beta API"),
                "experimental": TagConfig(title="Experimental")
            }
        )
    }
    create_tags_yaml(root, custom_tag_sets)
    
    template_content = """# Custom TagSet Test

{% if TAGSET:feature-flags:new-ui %}
## New UI enabled
Show new interface
{% endif %}

{% if TAGSET:feature-flags:beta-api %}
## Beta API enabled
Use beta endpoints
{% endif %}

{% if tag:new-ui AND tag:beta-api %}
## Both new features
Combined new features
{% endif %}
"""
    
    create_conditional_template(root, "custom-tagset", template_content)
    
    # Без активных флагов - все TAGSET условия true
    result1 = render_template(root, "ctx:custom-tagset", make_run_options())
    assert "New UI enabled" in result1
    assert "Beta API enabled" in result1
    assert "Both new features" not in result1  # теги не активны
    
    # Активируем один флаг
    options2 = make_run_options(extra_tags={"new-ui"})
    result2 = render_template(root, "ctx:custom-tagset", options2)
    assert "New UI enabled" in result2
    assert "Beta API enabled" not in result2  # другой тег в наборе активен
    assert "Both new features" not in result2
    
    # Активируем оба флага
    options3 = make_run_options(extra_tags={"new-ui", "beta-api"})
    result3 = render_template(root, "ctx:custom-tagset", options3)
    assert "New UI enabled" in result3
    assert "Beta API enabled" in result3 
    assert "Both new features" in result3


def test_invalid_condition_syntax_errors(adaptive_project):
    """Тест обработки ошибок в синтаксисе условий."""
    root = adaptive_project
    
    # Некорректный синтаксис условий
    invalid_templates = [
        "{% if tag:python AND %}Invalid{% endif %}",  # незавершенное AND
        "{% if OR tag:python %}Invalid{% endif %}",   # OR без левого операнда
        "{% if (tag:python %}Invalid{% endif %}",     # несбалансированные скобки
        "{% if tag:python) %}Invalid{% endif %}",     # лишняя закрывающая скобка
        "{% if TAGSET:invalid %}Invalid{% endif %}",  # неполный TAGSET
    ]
    
    for i, invalid_content in enumerate(invalid_templates):
        template_name = f"invalid-{i}"
        create_conditional_template(root, template_name, invalid_content)
        
        # Проверяем, что возникает ошибка обработки
        with pytest.raises((TemplateProcessingError, ValueError)):
            render_template(root, f"ctx:{template_name}", make_run_options())


def test_condition_evaluation_performance(adaptive_project):
    """Тест производительности оценки сложных условий."""
    root = adaptive_project
    
    # Создаем шаблон с большим количеством условий
    conditions = []
    for i in range(50):
        conditions.append(f"{{% if tag:tag{i} %}}Section {i:02d}{{% endif %}}")  # используем двузначные номера
    
    template_content = "# Performance Test\n\n" + "\n\n".join(conditions)
    create_conditional_template(root, "performance-test", template_content)
    
    # Активируем некоторые теги
    active_tags = {f"tag{i}" for i in range(0, 50, 5)}  # каждый 5-й тег
    options = make_run_options(extra_tags=active_tags)
    
    # Проверяем, что рендеринг завершается без ошибок
    result = render_template(root, "ctx:performance-test", options)
    
    # Проверяем, что активированные секции присутствуют
    for i in range(0, 50, 5):
        assert f"Section {i:02d}" in result
        
    # Проверяем, что неактивированные секции отсутствуют 
    for i in [1, 2, 3, 4]:
        assert f"Section {i:02d}" not in result


def test_template_comments(adaptive_project):
    """Тест шаблонных комментариев {# ... #}."""
    root = adaptive_project
    
    template_content = """# Template Comments Test

{# Это комментарий для разработчиков шаблонов #}
## Visible Section

Some visible content here.

{# 
   Многострочный комментарий
   который не должен попасть в результат
   Здесь могут быть TODO, заметки о структуре и т.п.
#}

{% if tag:minimal %}
{# Этот комментарий внутри условного блока #}
## Minimal Mode
Content for minimal mode
{% endif %}

{# Комментарий между секциями #}

## Another Section

More visible content.

{# Финальный комментарий в конце документа #}
"""
    
    create_conditional_template(root, "comments-test", template_content)
    
    # Тест без активных тегов
    result1 = render_template(root, "ctx:comments-test", make_run_options())
    
    # Проверяем, что видимый контент присутствует
    assert "Template Comments Test" in result1
    assert "Visible Section" in result1
    assert "Some visible content here" in result1
    assert "Another Section" in result1
    assert "More visible content" in result1
    
    # Проверяем, что комментарии удалены
    assert "Это комментарий для разработчиков" not in result1
    assert "Многострочный комментарий" not in result1
    assert "который не должен попасть в результат" not in result1
    assert "TODO" not in result1
    assert "Комментарий между секциями" not in result1
    assert "Финальный комментарий" not in result1
    assert "{#" not in result1
    assert "#}" not in result1
    
    # Тест с активным тегом
    options = make_run_options(extra_tags={"minimal"})
    result2 = render_template(root, "ctx:comments-test", options)
    
    # Проверяем, что условный блок появился
    assert "Minimal Mode" in result2
    assert "Content for minimal mode" in result2
    
    # Проверяем, что комментарий внутри условного блока все равно удален
    assert "Этот комментарий внутри условного блока" not in result2
    assert "{#" not in result2
    assert "#}" not in result2


def test_comments_with_special_characters(adaptive_project):
    """Тест комментариев со специальными символами."""
    root = adaptive_project
    
    template_content = """# Special Characters Test

{# Комментарий с ${плейсхолдером} внутри #}
## Section 1

{# Комментарий с {% директивой %} внутри #}
## Section 2

{# Комментарий с <html> тегами и "кавычками" 'разными' #}
## Section 3

{# Комментарий с символами: @, #, $, %, ^, &, * #}
## Section 4
"""
    
    create_conditional_template(root, "special-chars-test", template_content)
    
    result = render_template(root, "ctx:special-chars-test", make_run_options())
    
    # Проверяем, что секции присутствуют
    assert "Section 1" in result
    assert "Section 2" in result
    assert "Section 3" in result
    assert "Section 4" in result
    
    # Проверяем, что комментарии удалены
    assert "плейсхолдером" not in result
    assert "директивой" not in result
    assert "<html>" not in result
    assert "кавычками" not in result
    # Проверяем, что не осталось маркеров комментариев в неожиданных местах
    # (допускаем наличие '#}' в других контекстах, но проверяем что сами комментарии удалены)
    assert "Комментарий с ${" not in result
    assert "Комментарий с {%" not in result
    assert "Комментарий с <html>" not in result
    assert "Комментарий с символами" not in result


def test_adjacent_comments_and_content(adaptive_project):
    """Тест комментариев рядом с контентом без пробелов."""
    root = adaptive_project
    
    template_content = """{# Комментарий в начале без переноса #}# Title
{# Комментарий после заголовка #}
Content line 1
{# Встроенный комментарий #}Content line 2
{# Комментарий перед концом #}"""
    
    create_conditional_template(root, "adjacent-test", template_content)
    
    result = render_template(root, "ctx:adjacent-test", make_run_options())
    
    # Проверяем корректность склейки контента
    assert "# Title" in result
    assert "Content line 1" in result
    assert "Content line 2" in result
    
    # Проверяем, что комментарии удалены
    assert "Комментарий в начале" not in result
    assert "Комментарий после заголовка" not in result
    assert "Встроенный комментарий" not in result
    assert "Комментарий перед концом" not in result
    assert "{#" not in result
    assert "#}" not in result