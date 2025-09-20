"""
Базовые тесты для адаптивных возможностей.

Проверяет основную функциональность режимов, тегов и их влияние на генерацию контекстов.
"""

from __future__ import annotations

import pytest

from lg.engine import run_report
from .conftest import (
    adaptive_project, make_run_options, make_engine,
    create_conditional_template, render_for_test
)


def test_basic_modes_loading(adaptive_project):
    """Тест базовой загрузки режимов из конфигурации."""
    root = adaptive_project
    
    # Тестируем загрузку режимов без активации
    options = make_run_options()
    engine = make_engine(root, options)
    
    modes_config = engine.run_ctx.adaptive_loader.get_modes_config()
    
    # Проверяем, что все наборы режимов загружены
    assert "ai-interaction" in modes_config.mode_sets
    assert "dev-stage" in modes_config.mode_sets
    
    # Проверяем конкретные режимы
    ai_modes = modes_config.mode_sets["ai-interaction"].modes
    assert "ask" in ai_modes
    assert "agent" in ai_modes
    assert ai_modes["agent"].tags == ["agent", "tools"]
    
    dev_modes = modes_config.mode_sets["dev-stage"].modes
    assert "planning" in dev_modes
    assert "review" in dev_modes
    assert dev_modes["review"].options.get("vcs_mode") == "changes"


def test_basic_tags_loading(adaptive_project):
    """Тест базовой загрузки тегов из конфигурации."""
    root = adaptive_project
    
    options = make_run_options()
    engine = make_engine(root, options)
    
    tags_config = engine.run_ctx.adaptive_loader.get_tags_config()
    
    # Проверяем наборы тегов
    assert "language" in tags_config.tag_sets
    assert "code-type" in tags_config.tag_sets
    
    language_tags = tags_config.tag_sets["language"].tags
    assert "python" in language_tags
    assert "typescript" in language_tags
    
    # Проверяем глобальные теги
    assert "agent" in tags_config.global_tags
    assert "review" in tags_config.global_tags
    assert "minimal" in tags_config.global_tags


def test_mode_activation_affects_active_tags(adaptive_project):
    """Тест активации тегов через режимы."""
    root = adaptive_project
    
    # Активируем режим, который добавляет теги
    options = make_run_options(modes={"ai-interaction": "agent"})
    engine = make_engine(root, options)
    
    # Проверяем, что теги из режима активированы
    assert "agent" in engine.run_ctx.active_tags
    assert "tools" in engine.run_ctx.active_tags
    
    # Активируем другой режим
    options2 = make_run_options(modes={"dev-stage": "testing"})
    engine2 = make_engine(root, options2)
    
    assert "tests" in engine2.run_ctx.active_tags
    assert "agent" not in engine2.run_ctx.active_tags


def test_extra_tags_are_activated(adaptive_project):
    """Тест активации дополнительных тегов.""" 
    root = adaptive_project
    
    options = make_run_options(extra_tags={"minimal", "python"})
    engine = make_engine(root, options)
    
    assert "minimal" in engine.run_ctx.active_tags
    assert "python" in engine.run_ctx.active_tags


def test_mode_options_merging(adaptive_project):
    """Тест объединения опций от активных режимов."""
    root = adaptive_project
    
    # Активируем режим с опциями
    options = make_run_options(modes={"dev-stage": "review"})
    engine = make_engine(root, options)
    
    # Проверяем, что опции режима применились
    assert engine.run_ctx.mode_options.vcs_mode == "changes"
    
    # Активируем режим с другими опциями
    options2 = make_run_options(modes={"ai-interaction": "agent"})
    engine2 = make_engine(root, options2)
    
    assert engine2.run_ctx.mode_options.allow_tools == True


def test_conditional_template_with_tags(adaptive_project):
    """Тест условных шаблонов с проверкой тегов."""
    root = adaptive_project
    
    # Создаем шаблон с условием на тег
    template_content = """# Adaptive Test

{% if tag:minimal %}
## Minimal Mode
${docs}
{% else %}
## Full Mode  
${src}
${docs}
{% endif %}

{% if tag:tests %}
## Testing Section
${tests}
{% endif %}
"""
    
    create_conditional_template(root, "adaptive-test", template_content)
    
    # Тестируем без тегов
    options1 = make_run_options()
    result1 = render_for_test(root, "ctx:adaptive-test", options1)
    
    assert "Full Mode" in result1
    assert "Minimal Mode" not in result1
    assert "Testing Section" not in result1
    
    # Тестируем с тегом minimal
    options2 = make_run_options(extra_tags={"minimal"})
    result2 = render_for_test(root, "ctx:adaptive-test", options2)
    
    assert "Minimal Mode" in result2
    assert "Full Mode" not in result2
    
    # Тестируем с тегом tests
    options3 = make_run_options(extra_tags={"tests"})
    result3 = render_for_test(root, "ctx:adaptive-test", options3)
    
    assert "Testing Section" in result3


def test_mode_blocks_in_templates(adaptive_project):
    """Тест блоков режимов в шаблонах."""
    root = adaptive_project
    
    template_content = """# Mode Block Test

{% mode ai-interaction:agent %}
## Agent Mode Active
${src}
{% endmode %}

## Always Visible
${docs}
"""
    
    create_conditional_template(root, "mode-block-test", template_content)
    
    # Рендерим без активации режима
    options1 = make_run_options()
    result1 = render_for_test(root, "ctx:mode-block-test", options1)
    
    # В блоке режима должны активироваться теги agent и tools
    assert "Agent Mode Active" in result1
    assert "Always Visible" in result1


def test_tagset_conditions(adaptive_project):
    """Тест условий TAGSET."""
    root = adaptive_project
    
    template_content = """# TagSet Test

{% if TAGSET:language:python %}
## Python Code
${src}
{% endif %}

{% if TAGSET:language:typescript %}
## TypeScript Code  
${src}
{% endif %}

{% if NOT tag:javascript %}
## Not JavaScript
${docs}
{% endif %}
"""
    
    create_conditional_template(root, "tagset-test", template_content)
    
    # Тестируем без активных тегов языков
    options1 = make_run_options()
    result1 = render_for_test(root, "ctx:tagset-test", options1)
    
    # Если ни один тег из набора не активен, TAGSET условия истинны
    # NOT tag:javascript истинно, так как javascript тег не активен
    assert "Python Code" in result1
    assert "TypeScript Code" in result1
    assert "Not JavaScript" in result1
    
    # Активируем python тег
    options2 = make_run_options(extra_tags={"python"})
    result2 = render_for_test(root, "ctx:tagset-test", options2)
    
    # Теперь TAGSET условие истинно только для python
    # NOT tag:javascript все еще истинно, так как javascript не активен
    assert "Python Code" in result2
    assert "TypeScript Code" not in result2
    assert "Not JavaScript" in result2
    
    # Активируем javascript тег
    options3 = make_run_options(extra_tags={"javascript"})
    result3 = render_for_test(root, "ctx:tagset-test", options3)
    
    # Теперь TAGSET:language:javascript истинно, остальные TAGSET ложны
    # NOT tag:javascript ложно, так как javascript активен
    assert "Python Code" not in result3
    assert "TypeScript Code" not in result3
    assert "Not JavaScript" not in result3


def test_complex_conditions(adaptive_project):
    """Тест сложных условных выражений."""
    root = adaptive_project
    
    template_content = """# Complex Conditions

{% if tag:agent AND tag:tests %}
## Agent Testing Mode
${tests}
{% endif %}

{% if tag:minimal OR tag:review %}
## Minimal or Review
${docs}
{% endif %}

{% if NOT (tag:agent AND tag:tools) %}
## Not Full Agent
${src}
{% endif %}
"""
    
    create_conditional_template(root, "complex-test", template_content)
    
    # Тестируем различные комбинации тегов
    options1 = make_run_options(extra_tags={"agent", "tests"})
    result1 = render_for_test(root, "ctx:complex-test", options1)
    assert "Agent Testing Mode" in result1
    
    options2 = make_run_options(extra_tags={"minimal"})
    result2 = render_for_test(root, "ctx:complex-test", options2)
    assert "Minimal or Review" in result2
    
    options3 = make_run_options(extra_tags={"agent"})  # без tools
    result3 = render_for_test(root, "ctx:complex-test", options3)
    assert "Not Full Agent" in result3


def test_mode_activation_through_cli_like_interface(adaptive_project, monkeypatch):
    """Тест активации режимов через интерфейс, похожий на CLI."""
    root = adaptive_project
    monkeypatch.chdir(root)
    
    # Создаем простой шаблон для тестирования
    create_conditional_template(root, "cli-test", """# CLI Test

{% if tag:agent %}
## Agent Active  
{% endif %}

{% if tag:tests %}
## Tests Active
{% endif %}
""")
    
    # Тестируем активацию через режимы (как в CLI --mode ai-interaction:agent)
    options = make_run_options(modes={"ai-interaction": "agent", "dev-stage": "testing"})
    result = render_for_test(root, "ctx:cli-test", options)
    
    assert "Agent Active" in result
    assert "Tests Active" in result


def test_report_includes_mode_information(adaptive_project, monkeypatch):
    """Тест включения информации о режимах в отчет."""
    root = adaptive_project
    monkeypatch.chdir(root)
    
    options = make_run_options(
        modes={"ai-interaction": "agent"},
        extra_tags={"minimal"}
    )
    
    report = run_report("sec:src", options)
    
    # Проверяем, что отчет содержит информацию о файлах
    assert len(report.files) > 0
    
    # Проверяем базовую структуру отчета
    assert report.total.tokensProcessed > 0
    assert report.target == "sec:src"
    assert report.scope.value == "section"


@pytest.mark.parametrize("mode_set,mode", [
    ("ai-interaction", "ask"),
    ("ai-interaction", "agent"), 
    ("dev-stage", "planning"),
    ("dev-stage", "review")
])
def test_all_predefined_modes_work(adaptive_project, mode_set, mode):
    """Параметризованный тест всех предопределенных режимов."""
    root = adaptive_project
    
    options = make_run_options(modes={mode_set: mode})
    engine = make_engine(root, options)
    
    # Проверяем, что режим активирован
    assert engine.run_ctx.options.modes[mode_set] == mode
    
    # Проверяем, что контекст создается без ошибок
    assert engine.run_ctx.root == root
    
    # Проверяем базовое рендеринг секции (результат может быть пустым для режима changes)
    result = engine.render_section("src")
    assert isinstance(result, str)  # Проверяем, что рендеринг прошел без ошибок


def test_invalid_mode_raises_error(adaptive_project):
    """Тест обработки ошибок при указании неверного режима."""
    root = adaptive_project
    
    # Неверный набор режимов
    with pytest.raises(ValueError, match="Unknown mode set 'invalid-set'"):
        options = make_run_options(modes={"invalid-set": "any-mode"})
        make_engine(root, options)
    
    # Неверный режим в правильном наборе
    with pytest.raises(ValueError, match="Unknown mode 'invalid-mode' in mode set 'ai-interaction'"):
        options = make_run_options(modes={"ai-interaction": "invalid-mode"})  
        make_engine(root, options)