"""
Тесты граничных случаев и edge cases для адаптивных возможностей.

Проверяет работу системы в нестандартных ситуациях, обработку ошибок,
производительность и совместимость.
"""

from __future__ import annotations

import pytest

from .conftest import (
    adaptive_project, make_run_options, make_engine, render_template,
    create_conditional_template, create_modes_yaml, create_tags_yaml,
    ModeConfig, ModeSetConfig, TagConfig, TagSetConfig
)


def test_empty_configuration_defaults(tmp_path):
    """Тест поведения при отсутствии конфигурации адаптивных возможностей."""
    from tests.infrastructure.file_utils import write
    
    root = tmp_path
    
    # Создаем проект без modes.yaml и tags.yaml
    write(root / "lg-cfg" / "sections.yaml", """
test-section:
  extensions: [".txt"]
  filters:
    mode: allow
    allow:
      - "/**"
""")
    
    write(root / "test.txt", "Hello, world!")
    
    # Должны использоваться значения по умолчанию
    options = make_run_options()
    engine = make_engine(root, options)
    
    modes_config = engine.run_ctx.adaptive_loader.get_modes_config()
    tags_config = engine.run_ctx.adaptive_loader.get_tags_config()
    
    # Проверяем наличие режимов по умолчанию
    assert "ai-interaction" in modes_config.mode_sets
    assert "dev-stage" in modes_config.mode_sets
    
    # Проверяем базовую функциональность
    result = engine.render_section("test-section")
    assert "Hello, world!" in result


def test_circular_includes_prevention(tmp_path):
    """Тест предотвращения циклических включений в федеративной структуре.""" 
    from tests.infrastructure.file_utils import write
    
    root = tmp_path
    
    # Создаем циклические включения: root -> child -> root
    create_modes_yaml(root, {}, include=["child"])
    create_modes_yaml(root / "child", {}, include=["../"])  # циклическая ссылка
    
    # Создаем минимальные секции
    write(root / "lg-cfg" / "sections.yaml", """
root-sec:
  extensions: [".txt"] 
  filters:
    mode: allow
    allow: ["/root.txt"]
""")
    
    write(root / "child" / "lg-cfg" / "sections.yaml", """
child-sec:
  extensions: [".txt"]
  filters:  
    mode: allow
    allow: ["/child.txt"]
""")
    
    write(root / "root.txt", "root")
    write(root / "child.txt", "child")
    
    # Система должна обработать это корректно (без бесконечной рекурсии)
    options = make_run_options()
    engine = make_engine(root, options)
    
    # Должно работать без зависания
    assert engine.run_ctx.adaptive_loader is not None


def test_extremely_long_tag_names(adaptive_project):
    """Тест очень длинных имен тегов и режимов."""
    root = adaptive_project
    
    # Создаем режим с очень длинным именем
    long_name = "very-long-mode-name-that-exceeds-normal-expectations" * 5
    long_modes = {
        "long-test": ModeSetConfig(
            title="Long Test",
            modes={
                long_name: ModeConfig(
                    title="Long Mode",
                    tags=[f"long-tag-{i}" for i in range(50)]
                )
            }
        )
    }
    create_modes_yaml(root, long_modes, append=True)
    
    # Создаем шаблон с длинными именами
    long_tags = [f"long-tag-{i}" for i in range(20)]
    conditions = [f"{{% if tag:{tag} %}}{tag} active{{% endif %}}" for tag in long_tags[:5]]
    template_content = f"# Long Names Test\n\n" + "\n".join(conditions)
    
    create_conditional_template(root, "long-names-test", template_content)
    
    # Активируем режим с длинным именем
    options = make_run_options(modes={"long-test": long_name})
    result = render_template(root, "ctx:long-names-test", options)
    
    # Проверяем, что длинные теги активировались
    for i in range(5):
        assert f"long-tag-{i} active" in result


def test_unicode_in_configurations(adaptive_project):
    """Тест поддержки Unicode в конфигурациях."""
    root = adaptive_project
    
    # Создаем режимы с Unicode именами и описаниями
    unicode_modes = {
        "международный": ModeSetConfig(
            title="Международный режим",
            modes={
                "русский": ModeConfig(
                    title="Русский язык",
                    description="Поддержка русского языка",
                    tags=["русский", "кириллица"]
                ),
                "中文": ModeConfig(
                    title="中文支持",
                    tags=["中文", "汉字"]
                )
            }
        )
    }
    create_modes_yaml(root, unicode_modes, append=True)

    unicode_tags = {
        "языки": TagSetConfig(
            title="Языки мира",
            tags={
                "русский": TagConfig(title="Русский"),
                "中文": TagConfig(title="中文"),
                "العربية": TagConfig(title="العربية")
            }
        )
    }
    create_tags_yaml(root, unicode_tags, append=True)
    
    template_content = """# Unicode Test

{% if tag:русский %}
## Русский контент
Это русский текст
{% endif %}

{% if tag:中文 %}
## 中文内容  
这是中文文本
{% endif %}
"""
    
    create_conditional_template(root, "unicode-test", template_content)
    
    # Активируем Unicode режим
    options = make_run_options(modes={"международный": "русский"})
    result = render_template(root, "ctx:unicode-test", options)
    
    assert "Русский контент" in result
    assert "这是中文文本" not in result  # тег 中文 не активен


def test_massive_number_of_tags(adaptive_project):
    """Тест производительности с большим количеством тегов."""
    root = adaptive_project

    # Создаем большое количество тегов
    massive_tag_sets = {}
    for i in range(10):  # 10 наборов
        tags = {}
        for j in range(100):  # по 100 тегов в каждом
            tags[f"tag-{i}-{j}"] = TagConfig(title=f"Tag {i}-{j}")

        massive_tag_sets[f"set-{i}"] = TagSetConfig(
            title=f"Set {i}",
            tags=tags
        )

    create_tags_yaml(root, massive_tag_sets, append=True)

    # Создаем шаблон с множественными условиями tag (проверяем активность конкретных тегов)
    conditions = []
    for i in range(5):
        for j in range(10):
            conditions.append(f"{{% if tag:tag-{i}-{j} %}}Tag {i}-{j} active{{% endif %}}")
    
    template_content = "# Massive Tags Test\n\n" + "\n".join(conditions)
    create_conditional_template(root, "massive-tags-test", template_content)

    # Активируем некоторые теги
    active_tags = {f"tag-0-{j}" for j in range(5)}  # теги из первого набора
    options = make_run_options(extra_tags=active_tags)

    # Проверяем, что рендеринг завершается разумное время
    result = render_template(root, "ctx:massive-tags-test", options)

    # Проверяем результат
    for j in range(5):
        assert f"Tag 0-{j} active" in result

    # Теги из других наборов не должны активироваться
    assert "Tag 1-0 active" not in result


def test_deeply_nested_conditions(adaptive_project):
    """Тест глубоко вложенных условных блоков."""
    root = adaptive_project
    
    # Создаем глубоко вложенную структуру условий
    template_content = """# Deeply Nested Test

{% if tag:level1 %}
## Level 1
{% if tag:level2 %}
### Level 2  
{% if tag:level3 %}
#### Level 3
{% if tag:level4 %}
##### Level 4
{% if tag:level5 %}
###### Level 5
Deep nesting works!
{% endif %}
{% endif %}
{% endif %}
{% endif %}
{% endif %}
"""
    
    create_conditional_template(root, "deep-nesting-test", template_content)
    
    # Тестируем с частичной активацией
    options1 = make_run_options(extra_tags={"level1", "level2"})
    result1 = render_template(root, "ctx:deep-nesting-test", options1)
    assert "Level 1" in result1
    assert "Level 2" in result1  
    assert "Level 3" not in result1
    
    # Тестируем с полной активацией
    options2 = make_run_options(extra_tags={f"level{i}" for i in range(1, 6)})
    result2 = render_template(root, "ctx:deep-nesting-test", options2)
    assert "Deep nesting works!" in result2


def test_mode_block_error_recovery(adaptive_project):
    """Тест восстановления после ошибок в блоках режимов."""
    root = adaptive_project
    
    # Создаем шаблон с потенциально проблемными блоками режимов
    template_content = """# Mode Block Recovery Test

{% mode ai-interaction:agent %}
## Inside agent mode
Content 1
{% endmode %}

Normal content between blocks

{% mode invalid-set:invalid-mode %}
## This should cause error handling
Content 2  
{% endmode %}

More normal content

{% mode dev-stage:testing %}
## This should still work
Content 3
{% endmode %}
"""
    
    create_conditional_template(root, "mode-error-test", template_content)
    
    # Проверяем обработку ошибки
    with pytest.raises(Exception):  # Ожидаем ошибку из-за invalid-set
        render_template(root, "ctx:mode-error-test", make_run_options())


def test_tagset_with_empty_sets(adaptive_project):
    """Тест TAGSET условий с пустыми наборами тегов."""
    root = adaptive_project
    
    # Создаем набор тегов с пустым содержимым
    empty_tag_sets = {
        "empty-set": TagSetConfig(
            title="Empty Set",
            tags={}  # пустой набор тегов
        )
    }
    create_tags_yaml(root, empty_tag_sets, append=True)
    
    template_content = """# Empty TagSet Test

{% if TAGSET:empty-set:any %}
## Empty set condition
Should always be true for empty set
{% endif %}

{% if TAGSET:nonexistent-set:any %}
## Nonexistent set condition  
Should always be true for nonexistent set
{% endif %}
"""
    
    create_conditional_template(root, "empty-tagset-test", template_content)
    
    result = render_template(root, "ctx:empty-tagset-test", make_run_options())
    
    # Пустые и несуществующие наборы должны давать true
    assert "Empty set condition" in result
    assert "Nonexistent set condition" in result


def test_memory_usage_with_large_templates(adaptive_project):
    """Тест использования памяти с большими шаблонами."""
    root = adaptive_project
    
    # Создаем очень большой шаблон
    large_sections = []
    for i in range(200):
        large_sections.append(f"""
## Section {i}

{{% if tag:section-{i} %}}
Section {i} is active with lots of content here. 
This section contains multiple paragraphs and detailed information
that would normally be quite lengthy in a real scenario.
{{% endif %}}
""")
    
    template_content = "# Large Template Test\n" + "\n".join(large_sections)
    create_conditional_template(root, "large-template-test", template_content)
    
    # Активируем некоторые секции
    active_tags = {f"section-{i}" for i in range(0, 200, 10)}  # каждую 10-ю секцию
    options = make_run_options(extra_tags=active_tags)
    
    # Проверяем, что рендеринг завершается без проблем с памятью
    result = render_template(root, "ctx:large-template-test", options)
    
    # Проверяем, что активные секции присутствуют
    for i in range(0, 200, 10):
        assert f"Section {i} is active" in result


def test_special_characters_in_tag_names(adaptive_project):
    """Тест специальных символов в именах тегов."""
    root = adaptive_project
    
    # Создаем теги со специальными символами (только допустимые в лексере)
    special_global_tags = {
        "tag_with_underscore": TagConfig(title="Underscore Tag"), 
        "tag123": TagConfig(title="Number Tag"),
        "CamelCaseTag": TagConfig(title="Camel Case Tag"),
        "UPPER_TAG": TagConfig(title="Upper Case Tag")
    }
    create_tags_yaml(root, global_tags=special_global_tags, append=True)
    
    template_content = """# Special Characters Test

{% if tag:tag_with_underscore %}
## Underscore tag active
{% endif %}

{% if tag:tag123 %}
## Number tag active  
{% endif %}

{% if tag:CamelCaseTag %}
## Camel case tag active
{% endif %}

{% if tag:UPPER_TAG %}
## Upper case tag active
{% endif %}
"""
    
    create_conditional_template(root, "special-chars-test", template_content)
    
    # Активируем все специальные теги
    options = make_run_options(extra_tags={
        "tag_with_underscore", "tag123", "CamelCaseTag", "UPPER_TAG"
    })
    result = render_template(root, "ctx:special-chars-test", options)
    
    assert "Underscore tag active" in result
    assert "Number tag active" in result
    assert "Camel case tag active" in result
    assert "Upper case tag active" in result


def test_configuration_reload_behavior(adaptive_project):
    """Тест поведения при изменении конфигурации во время выполнения."""
    root = adaptive_project
    
    # Создаем базовый движок
    engine1 = make_engine(root, make_run_options())
    initial_modes = set(engine1.run_ctx.adaptive_loader.get_modes_config().mode_sets.keys())
    
    # Добавляем новую конфигурацию
    new_modes = {
        "runtime-added": ModeSetConfig(
            title="Runtime Added",
            modes={
                "new-mode": ModeConfig(title="New Mode", tags=["new-tag"])
            }
        )
    }
    create_modes_yaml(root, new_modes, append=True)
    
    # Создаем новый движок (должен увидеть новую конфигурацию)
    engine2 = make_engine(root, make_run_options())
    updated_modes = set(engine2.run_ctx.adaptive_loader.get_modes_config().mode_sets.keys())
    
    # Новый движок должен видеть обновленную конфигурацию
    assert "runtime-added" in updated_modes
    assert "runtime-added" not in initial_modes


def test_backwards_compatibility_warnings(adaptive_project):
    """Тест предупреждений о совместимости с устаревшими форматами."""
    # Этот тест может быть расширен в будущем при добавлении новых версий API
    root = adaptive_project
    
    # Пока просто проверяем, что текущий формат работает
    options = make_run_options()
    engine = make_engine(root, options)
    
    # Проверяем, что система работает с текущими конфигурациями
    assert engine.run_ctx.adaptive_loader is not None
    assert len(engine.run_ctx.adaptive_loader.get_modes_config().mode_sets) > 0


@pytest.mark.slow
def test_performance_regression_detection(adaptive_project):
    """Тест для выявления регрессий производительности."""
    import time
    
    root = adaptive_project
    
    # Создаем нагрузочный тест
    heavy_template = """# Performance Test

{% for i in range(100) %}
{% if tag:perf-{{ i }} %}
## Section {{ i }}
Content for section {{ i }}
{% endif %}
{% endfor %}
"""
    
    # Примечание: Это псевдо-код, так как цикл for не поддерживается в текущей реализации
    # Заменяем на ручное создание условий
    conditions = []
    for i in range(100):
        conditions.append(f"{{% if tag:perf-{i} %}}## Section {i}\nContent for section {i}{{% endif %}}")
    
    template_content = "# Performance Test\n\n" + "\n\n".join(conditions)
    create_conditional_template(root, "performance-regression-test", template_content)
    
    # Измеряем время рендеринга
    start_time = time.time()
    
    options = make_run_options(extra_tags={f"perf-{i}" for i in range(50)})
    result = render_template(root, "ctx:performance-regression-test", options)
    
    end_time = time.time()
    
    # Проверяем, что рендеринг завершился в разумное время (< 5 секунд)
    assert (end_time - start_time) < 5.0, f"Rendering took too long: {end_time - start_time} seconds"
    
    # Проверяем корректность результата
    for i in range(50):
        assert f"Section {i}" in result