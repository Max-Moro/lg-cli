"""
Тесты условных опций адаптеров.

Проверяет работу условных блоков `when` в конфигурации языковых адаптеров,
включая динамическое изменение поведения адаптеров на основе активных тегов.
"""

from __future__ import annotations

import textwrap

from .conftest import (
    adaptive_project, make_run_options, render_template,
    create_conditional_template, TagConfig, create_tags_yaml,
    write
)


def test_conditional_python_adapter_options(adaptive_project):
    """
    Тест условных опций Python адаптера через теги.
    
    Проверяет возможность включения тривиальных __init__.py файлов
    в листинг при активации специального тега.
    """
    root = adaptive_project
    
    # Добавляем специальный тег для управления __init__.py файлами
    special_tags = {
        "include-inits": TagConfig(
            title="Включить __init__.py файлы",
            description="Показывать даже тривиальные __init__.py в листингах"
        )
    }
    create_tags_yaml(root, global_tags=special_tags, append=True)
    
    # Создаем структуру пакетов с __init__.py файлами
    write(root / "src" / "__init__.py", "pass")  # тривиальный 
    write(root / "src" / "package1" / "__init__.py", "pass")  # тривиальный 
    write(root / "src" / "package1" / "module.py", "def func1():\n    return 'package1'\n")
    write(root / "src" / "package2" / "__init__.py", "__version__ = '1.0.0'\n")  # не тривиальный
    write(root / "src" / "package2" / "core.py", "def func2():\n    return 'package2'\n")
    
    # Создаем две секции: одну с условной опцией, другую без
    sections_content = textwrap.dedent("""
    python-default:
      extensions: [".py"]
      code_fence: true
      python:
        skip_trivial_inits: true  # стандартное поведение - пропускать тривиальные
      filters:
        mode: allow
        allow:
          - "/src/**"
    
    python-with-inits:
      extensions: [".py"] 
      code_fence: true
      python:
        skip_trivial_inits: true  # базовое значение
        when:
          - condition: "tag:include-inits"
            skip_trivial_inits: false  # переопределяем при активном теге
      filters:
        mode: allow
        allow:
          - "/src/**"
    """).strip() + "\n"
    
    write(root / "lg-cfg" / "sections.yaml", sections_content)
    
    # Создаем шаблон, использующий обе секции для сравнения
    template_content = """# Conditional Adapter Options Test

## Default Python section (always skips trivial __init__.py)

${python-default}

## Conditional Python section (includes __init__.py when tag active)

${python-with-inits}
"""
    
    create_conditional_template(root, "adapter-options-test", template_content)
    
    # Тест 1: без активного тега - обе секции должны пропускать тривиальные __init__.py
    result1 = render_template(root, "ctx:adapter-options-test", make_run_options())
    
    # Проверяем, что тривиальные __init__.py отсутствуют в обеих секциях
    init_markers = [
        "FILE: __init__.py",
        "FILE: package1/__init__.py"
    ]
    for marker in init_markers:
        assert marker not in result1, f"Trivial {marker} should be skipped without tag"
    
        # Нетривиальный __init__.py должен присутствовать
        assert "FILE: package2/__init__.py" in result1
        assert "__version__ = '1.0.0'" in result1
        
        # Обычные модули должны присутствовать
        assert "FILE: package1/module.py" in result1
        assert "FILE: package2/core.py" in result1    # Тест 2: с активным тегом - только вторая секция должна включать тривиальные __init__.py
    options = make_run_options(extra_tags={"include-inits"})
    result2 = render_template(root, "ctx:adapter-options-test", options)
    
    # В первой секции (python-default) тривиальные __init__.py все еще должны отсутствовать
    # Во второй секции (python-with-inits) они должны присутствовать
    
    # Подсчитаем количество вхождений каждого файла
    trivial_init1_count = result2.count("FILE: __init__.py") 
    trivial_init2_count = result2.count("FILE: package1/__init__.py")
    nontrivial_init_count = result2.count("FILE: package2/__init__.py")
    
    # Тривиальные __init__.py должны появиться только один раз (во второй секции)
    assert trivial_init1_count == 1, f"Expected 1 occurrence of __init__.py, got {trivial_init1_count}"
    assert trivial_init2_count == 1, f"Expected 1 occurrence of package1/__init__.py, got {trivial_init2_count}"
    
    # Нетривиальный должен появиться дважды (в обеих секциях)
    assert nontrivial_init_count == 2, f"Expected 2 occurrences of package2/__init__.py, got {nontrivial_init_count}"


def test_multiple_conditional_adapter_options(adaptive_project):
    """
    Тест множественных условных опций адаптера.
    
    Проверяет комбинирование нескольких условных правил в одном адаптере.
    """
    root = adaptive_project
    
    # Добавляем несколько тегов для управления поведением
    special_tags = {
        "include-inits": TagConfig(title="Включить __init__.py"),
        "strip-bodies": TagConfig(title="Убрать тела функций"),
        "verbose-mode": TagConfig(title="Подробный режим")
    }
    create_tags_yaml(root, global_tags=special_tags, append=True)
    
    # Создаем файлы с разным содержимым
    write(root / "src" / "__init__.py", "pass")
    write(root / "src" / "api.py", textwrap.dedent("""
    def public_function():
        '''Публичная функция API.'''
        # Выполняем внутреннюю логику
        result = internal_logic()
        # Логируем результат
        log_api_call("public_function", result)
        # Возвращаем обработанный результат
        return process_result(result)

    def _internal_function():
        '''Внутренняя функция.'''
        # Сложные вычисления
        data = complex_computation()
        # Валидация данных
        if not validate_data(data):
            raise ValueError("Invalid data")
        # Обработка и возврат
        return transform_data(data)
    """).strip() + "\n")    # Создаем секцию с множественными условными опциями
    sections_content = textwrap.dedent("""
    adaptive-python:
      extensions: [".py"]
      code_fence: true
      python:
        skip_trivial_inits: true
        strip_function_bodies: false
        when:
          - condition: "tag:include-inits"
            skip_trivial_inits: false
          - condition: "tag:strip-bodies AND NOT tag:verbose-mode"
            strip_function_bodies: true
          - condition: "tag:verbose-mode"
            strip_function_bodies: false
            skip_trivial_inits: false
      filters:
        mode: allow
        allow:
          - "/src/**"
    """).strip() + "\n"
    
    write(root / "lg-cfg" / "sections.yaml", sections_content)
    
    template_content = """# Multiple Conditional Options Test

${adaptive-python}
"""
    
    create_conditional_template(root, "multiple-options-test", template_content)
    
    # Тест 1: только include-inits
    result1 = render_template(root, "ctx:multiple-options-test", 
                             make_run_options(extra_tags={"include-inits"}))
    
    assert "FILE: __init__.py" in result1  # __init__.py включен
    assert "def public_function():" in result1  # тела функций сохранены
    assert "internal_logic()" in result1
    
    # Тест 2: только strip-bodies (без verbose-mode)
    result2 = render_template(root, "ctx:multiple-options-test",
                             make_run_options(extra_tags={"strip-bodies"}))
    
    assert "FILE: __init__.py" not in result2  # __init__.py пропущен
    assert "def public_function():" in result2     # сигнатуры есть
    assert "internal_logic()" not in result2      # тела функций убраны
    
    # Тест 3: strip-bodies + verbose-mode (verbose-mode отменяет strip-bodies)
    result3 = render_template(root, "ctx:multiple-options-test",
                             make_run_options(extra_tags={"strip-bodies", "verbose-mode"}))
    
    assert "FILE: __init__.py" in result3     # __init__.py включен (verbose-mode)
    assert "def public_function():" in result3    # сигнатуры есть
    assert "internal_logic()" in result3          # тела функций сохранены (verbose-mode приоритетнее)
    
    # Тест 4: все три тега (verbose-mode должен доминировать)
    result4 = render_template(root, "ctx:multiple-options-test",
                             make_run_options(extra_tags={"include-inits", "strip-bodies", "verbose-mode"}))
    
    assert "FILE: __init__.py" in result4     # __init__.py включен
    assert "def public_function():" in result4    # сигнатуры есть  
    assert "internal_logic()" in result4          # тела функций сохранены


def test_conditional_options_with_complex_conditions(adaptive_project):
    """
    Тест условных опций адаптеров со сложными условиями.

    Проверяет работу AND/OR/NOT операторов в условиях адаптеров.
    """
    root = adaptive_project
    
    # Теги для сложных условий
    complex_tags = {
        "production": TagConfig(title="Продакшн режим"),
        "debug": TagConfig(title="Отладочный режим"), 
        "api-docs": TagConfig(title="Документация API"),
        "internal-docs": TagConfig(title="Внутренняя документация")
    }
    create_tags_yaml(root, global_tags=complex_tags, append=True)
    
    # Создаем файлы
    write(root / "src" / "__init__.py", "pass")  # тривиальный
    write(root / "src" / "debug.py", textwrap.dedent("""
    def debug_function():
        '''Debug utility function.'''
        # Печатаем отладочную информацию
        print("Debug info")
        # Собираем системную информацию
        system_info = collect_system_info()
        # Логируем детали
        log_debug_details(system_info)
        return True

    def production_function():
        '''Production function.''' 
        # Обрабатываем продакшн данные
        data = get_production_data()
        # Применяем бизнес-логику
        processed = apply_business_rules(data)
        # Возвращаем результат
        return processed
    """).strip() + "\n")    # Секция со сложными условными опциями
    sections_content = textwrap.dedent("""
    complex-conditions:
      extensions: [".py"]
      code_fence: true
      python:
        skip_trivial_inits: true
        strip_function_bodies: false
        when:
          # В продакшне без отладки убираем __init__.py для компактности
          - condition: "tag:production AND NOT tag:debug"
            skip_trivial_inits: true
            strip_function_bodies: true
          # В режиме отладки или для внутренней документации показываем все
          - condition: "tag:debug OR tag:internal-docs"
            skip_trivial_inits: false
            strip_function_bodies: false
          # Для API документации показываем только сигнатуры
          - condition: "tag:api-docs AND NOT tag:internal-docs"
            strip_function_bodies: true
      filters:
        mode: allow
        allow:
          - "/src/**"
    """).strip() + "\n"
    
    write(root / "lg-cfg" / "sections.yaml", sections_content)
    
    template_content = """# Complex Conditions Test

${complex-conditions}
"""
    
    create_conditional_template(root, "complex-conditions-test", template_content)
    
    # Тест 1: production без debug - максимальная компактность  
    result1 = render_template(root, "ctx:complex-conditions-test",
                             make_run_options(extra_tags={"production"}))
    
    assert "def debug_function():" in result1      # сигнатуры есть
    assert "collect_system_info()" not in result1  # тела функций убраны (проверяем специфичную функцию из debug.py)
    assert "def production_function():" in result1
    assert "get_production_data()" not in result1  # тела функций убраны (проверяем специфичную функцию из debug.py)
    
    # Тест 2: debug режим - все детали
    result2 = render_template(root, "ctx:complex-conditions-test", 
                             make_run_options(extra_tags={"debug"}))
    
    assert "FILE: __init__.py" in result2        # __init__.py включен (изменили формат)
    assert "def debug_function():" in result2     # сигнатуры есть
    assert "collect_system_info()" in result2    # тела функций сохранены
    assert "get_production_data()" in result2    # тела функций сохранены
    
    # Тест 3: api-docs без internal-docs - только сигнатуры
    result3 = render_template(root, "ctx:complex-conditions-test",
                             make_run_options(extra_tags={"api-docs"}))
    
    assert "def debug_function():" in result3     # сигнатуры есть  
    assert "collect_system_info()" not in result3 # тела функций убраны
    assert "get_production_data()" not in result3 # тела функций убраны
    
    # Тест 4: api-docs + internal-docs - internal-docs отменяет strip_function_bodies
    result4 = render_template(root, "ctx:complex-conditions-test",
                             make_run_options(extra_tags={"api-docs", "internal-docs"}))
    
    assert "FILE: __init__.py" in result4        # __init__.py включен (internal-docs)
    assert "def debug_function():" in result4     # сигнатуры есть
    assert "collect_system_info()" in result4    # тела функций сохранены (internal-docs приоритетнее)
    assert "get_production_data()" in result4    # тела функций сохранены (internal-docs приоритетнее)


def test_conditional_options_inheritance_and_priority(adaptive_project):
    """
    Тест приоритета и наследования условных опций адаптеров.
    
    Проверяет, что более поздние правила when переопределяют более ранние.
    """
    root = adaptive_project
    
    # Теги для тестирования приоритета
    priority_tags = {
        "base-mode": TagConfig(title="Базовый режим"),
        "override-mode": TagConfig(title="Переопределяющий режим"),
        "final-mode": TagConfig(title="Финальный режим")
    }
    create_tags_yaml(root, global_tags=priority_tags, append=True)
    
    write(root / "src" / "__init__.py", "pass")
    write(root / "src" / "example.py", "def func(): pass\n")
    
    # Секция с правилами разного приоритета
    sections_content = textwrap.dedent("""
    priority-test:
      extensions: [".py"]
      code_fence: true
      python:
        skip_trivial_inits: true  # базовое значение
        when:
          # Первое правило
          - condition: "tag:base-mode"
            skip_trivial_inits: false
          # Второе правило переопределяет первое при совпадении условий
          - condition: "tag:base-mode AND tag:override-mode"  
            skip_trivial_inits: true
          # Третье правило с высшим приоритетом
          - condition: "tag:final-mode"
            skip_trivial_inits: false
      filters:
        mode: allow
        allow:
          - "/src/**"
    """).strip() + "\n"
    
    write(root / "lg-cfg" / "sections.yaml", sections_content)
    
    template_content = """# Priority Test

${priority-test}
"""
    
    create_conditional_template(root, "priority-test", template_content)
    
    # Тест 1: только base-mode - первое правило активно
    result1 = render_template(root, "ctx:priority-test",
                             make_run_options(extra_tags={"base-mode"}))
    
    assert "FILE: __init__.py" in result1  # skip_trivial_inits: false
    
    # Тест 2: base-mode + override-mode - второе правило переопределяет первое
    result2 = render_template(root, "ctx:priority-test", 
                             make_run_options(extra_tags={"base-mode", "override-mode"}))
    
    assert "FILE: __init__.py" not in result2  # skip_trivial_inits: true (переопределено)
    
    # Тест 3: все три тега - final-mode имеет высший приоритет
    result3 = render_template(root, "ctx:priority-test",
                             make_run_options(extra_tags={"base-mode", "override-mode", "final-mode"}))
    
    assert "FILE: __init__.py" in result3  # skip_trivial_inits: false (final-mode)
    
    # Тест 4: только final-mode - не зависит от других правил
    result4 = render_template(root, "ctx:priority-test", 
                             make_run_options(extra_tags={"final-mode"}))
    
    assert "FILE: __init__.py" in result4  # skip_trivial_inits: false