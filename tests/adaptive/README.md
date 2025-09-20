# Тесты адаптивных возможностей

Этот пакет содержит интеграционные тесты для функционального блока "Адаптивные возможности" Listing Generator.

## Структура тестов

### `conftest.py`
Основная тестовая инфраструктура, предоставляющая:

- **Типы конфигурации**: `ModeConfig`, `ModeSetConfig`, `TagConfig`, `TagSetConfig` для типизированного создания конфигураций
- **Хелперы конфигурации**: `write_modes_yaml()`, `write_tags_yaml()` для быстрого создания YAML файлов
- **Готовые конфигурации**: `get_default_modes_config()`, `get_default_tags_config()` со стандартными настройками
- **Хелперы запуска**: `make_run_options()`, `make_run_context()`, `make_engine()` для создания объектов выполнения
- **Фикстуры проектов**: `adaptive_project`, `minimal_adaptive_project`, `federated_project` для разных сценариев
- **Хелперы шаблонов**: `create_conditional_template()`, `create_mode_template()` для создания шаблонов с условной логикой

### Тестовые модули

#### `test_basic_functionality.py`
Базовые тесты основной функциональности:
- Загрузка и активация режимов и тегов
- Влияние режимов на активные теги 
- Объединение опций от режимов
- Базовые условные шаблоны
- Блоки режимов в шаблонах
- TAGSET условия
- CLI-подобный интерфейс

#### `test_federated.py`
Тесты федеративной функциональности:
- Загрузка конфигураций из множественных `lg-cfg` скоупов
- Приоритет родительских конфигураций при конфликтах
- Объединение режимов и тегов из разных скоупов
- Адресные ссылки между скоупами (`${@apps/web:section}`)
- Условия `scope:local` и `scope:parent`
- Совместимость с CLI командами `list mode-sets` и `list tag-sets`

#### `test_conditional_logic.py`
Тесты условной логики в шаблонах:
- Базовые условия `{% if tag:name %}`
- Логические операторы `AND`, `OR`, `NOT`
- Группировка с помощью скобок `(condition1 OR condition2) AND condition3`
- Блоки `{% else %}` и `{% elif %}`
- TAGSET условия для срезов по наборам тегов
- Вложенные и сложные условия
- Взаимодействие с блоками режимов
- Пользовательские наборы тегов
- Обработка ошибок синтаксиса

#### `test_cli_integration.py`
Тесты CLI интерфейса:
- Команды `lg list mode-sets` и `lg list tag-sets`
- Флаги `--mode modeset:mode` и `--tags tag1,tag2`
- Команда `lg render` с адаптивными опциями
- Команда `lg report` с адаптивными опциями
- Обработка ошибок неверных режимов
- Федеративные проекты через CLI
- Обработка пробелов и специальных символов в параметрах

#### `test_edge_cases.py`
Тесты граничных случаев и edge cases:
- Поведение при отсутствии конфигурации (использование умолчаний)
- Предотвращение циклических включений
- Очень длинные имена режимов и тегов  
- Unicode поддержка в конфигурациях
- Производительность с большим количеством тегов
- Глубоко вложенные условия
- Восстановление после ошибок
- Пустые и несуществующие наборы тегов
- Безопасность параллельного выполнения
- Использование памяти с большими шаблонами
- Специальные символы в именах
- Тесты производительности и регрессий

## Фикстуры проектов

### `adaptive_project`
Стандартный проект с полной адаптивной конфигурацией:
- Режимы: `ai-interaction` (ask, agent), `dev-stage` (planning, development, testing, review)
- Теги: наборы `language` и `code-type`, глобальные теги для различных задач
- Секции: `src`, `docs`, `tests` с базовой фильтрацией
- Тестовые файлы для каждой секции

### `minimal_adaptive_project` 
Минимальный проект для простых тестов:
- Один набор режимов `simple` с режимами `default` и `minimal`
- Один глобальный тег `minimal`
- Одна секция `all` для всех `.py` файлов
- Один тестовый файл

### `federated_project`
Монорепозиторий с федеративной структурой:
- Корневой `lg-cfg` с базовыми режимами и тегами
- Дочерний скоуп `apps/web` с фронтенд режимами и TypeScript тегами
- Дочерний скоуп `libs/core` с библиотечными режимами и Python тегами
- Взаимные включения через `include` директивы
- Тестовые файлы в каждом скоупе

## Использование

### Быстрый старт
```python
def test_my_adaptive_feature(adaptive_project):
    root = adaptive_project
    
    # Создаем шаблон с условием
    create_conditional_template(root, "my-test", """
    {% if tag:minimal %}
    ## Minimal mode
    {% endif %}
    """)
    
    # Тестируем с активным тегом
    options = make_run_options(extra_tags={"minimal"})
    result = run_render("ctx:my-test", options)
    
    assert "Minimal mode" in result
```

### Создание кастомных конфигураций
```python
def test_custom_modes(tmp_path):
    root = tmp_path
    
    # Создаем кастомные режимы
    modes = {
        "my-workflow": ModeSetConfig(
            title="My Workflow",
            modes={
                "dev": ModeConfig(
                    title="Development", 
                    tags=["dev-mode"],
                    options={"code_fence": False}
                )
            }
        )
    }
    write_modes_yaml(root, modes)
    
    # Используем в тестах...
```

### Федеративное тестирование
```python  
def test_cross_scope_functionality(federated_project):
    root = federated_project
    
    # Создаем шаблон с адресными ссылками
    create_conditional_template(root, "cross-scope", """
    ## Root content
    ${overview}
    
    ## Web content  
    ${@apps/web:web-src}
    """)
    
    # Тестируем активацию режимов из дочерних скоупов
    options = make_run_options(modes={"frontend": "ui"})
    result = run_render("ctx:cross-scope", options)
```

## Запуск тестов

```bash
# Все тесты адаптивных возможностей
pytest tests/adaptive/

# Конкретный модуль
pytest tests/adaptive/test_basic_functionality.py

# Конкретный тест
pytest tests/adaptive/test_basic_functionality.py::test_mode_activation_affects_active_tags

# С подробным выводом
pytest -v tests/adaptive/

# Только быстрые тесты (исключить медленные)
pytest -m "not slow" tests/adaptive/
```

## Полезные команды

```bash
# Проверка покрытия тестами
pytest --cov=lg.config.adaptive_loader --cov=lg.config.modes --cov=lg.config.tags tests/adaptive/

# Запуск только CLI тестов
pytest tests/adaptive/test_cli_integration.py

# Запуск только федеративных тестов  
pytest tests/adaptive/test_federated.py

# Пропуск медленных тестов производительности
pytest -k "not performance" tests/adaptive/
```