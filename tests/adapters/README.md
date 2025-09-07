# Golden Tests System for Language Adapters

Эта система предоставляет единообразное тестирование языковых адаптеров с использованием golden-файлов (эталонных файлов).

## Что такое Golden Tests

Golden tests (snapshot tests, approval tests) — это техника тестирования, при которой:

1. **Первый запуск**: создается эталонный файл с ожидаемым результатом
2. **Последующие запуски**: результат сравнивается с эталоном
3. **При изменениях**: тест падает, показывая diff между ожидаемым и фактическим результатом
4. **Обновление эталонов**: при осознанных изменениях можно обновить эталонные файлы

## Структура

```
tests/adapters/
├── golden_utils.py              # Универсальная система golden-тестов
├── python/
│   ├── goldens/                 # Эталонные файлы для Python
│   │   ├── python_basic_strip.golden
│   │   └── python_full_pipeline.golden
│   ├── conftest.py             # Fixtures и утилиты для Python тестов
│   └── test_*.py               # Тесты Python адаптера
├── typescript/
│   ├── goldens/                # Эталонные файлы для TypeScript
│   ├── conftest.py             # Fixtures и утилиты для TS тестов  
│   └── test_*.py               # Тесты TypeScript адаптера
└── README.md                   # Этот файл
```

## Использование в тестах

### Базовое использование

```python
from ..golden_utils import assert_golden_match

def test_my_optimization(self, sample_code):
    adapter = PythonAdapter()
    adapter._cfg = PythonCfg(strip_function_bodies=True)
    
    result, meta = adapter.process(lctx_py(sample_code))
    
    # Автоматическое определение языка и создание/сравнение golden-файла
    assert_golden_match(result, "test_name")
```

### Расширенное использование

```python
# Явное указание языка
assert_golden_match(result, "test_name", language="python")

# Принудительное обновление (обычно не нужно в тестах)
assert_golden_match(result, "test_name", update_golden=True)
```

## Создание и обновление golden-файлов

### Автоматическое создание

При первом запуске теста golden-файл создается автоматически:

```bash
.venv/Scripts/python.exe -m pytest tests/adapters/python/test_function_bodies.py::test_new_feature -v
```

### Обновление через переменную окружения

```bash
# Обновить все golden-файлы в конкретном тесте
PYTEST_UPDATE_GOLDENS=1 .venv/Scripts/python.exe -m pytest tests/adapters/python/test_function_bodies.py -v

# Обновить golden-файлы для всех Python тестов
PYTEST_UPDATE_GOLDENS=1 .venv/Scripts/python.exe -m pytest tests/adapters/python/ -v
```

### Обновление через скрипт (рекомендуется)

```bash
# Показать список доступных языков
./scripts/update_goldens.sh --list

# Проверить отсутствующие golden-файлы
./scripts/update_goldens.sh --check  

# Посмотреть что будет обновлено (dry run)
./scripts/update_goldens.sh python --dry-run

# Обновить golden-файлы для Python
./scripts/update_goldens.sh python

# Обновить golden-файлы для TypeScript  
./scripts/update_goldens.sh typescript

# Обновить все golden-файлы
./scripts/update_goldens.sh

# Обновить с дополнительными опциями pytest
PYTEST_ARGS="-v --tb=short" ./scripts/update_goldens.sh python
```

## Workflow разработки

### 1. Написание нового теста

```python
def test_new_optimization(self, sample_code):
    adapter = PythonAdapter()
    adapter._cfg = PythonCfg(new_optimization=True)
    
    result, meta = adapter.process(lctx_py(sample_code))
    
    # Проверяем логику
    assert "expected_marker" in result
    assert meta.get("optimization.applied", 0) > 0
    
    # Golden test
    assert_golden_match(result, "new_optimization")
```

### 2. Первый запуск

```bash
.venv/Scripts/python.exe -m pytest tests/adapters/python/test_new.py::test_new_optimization -v
```

Golden-файл будет создан автоматически.

### 3. Проверка и коммит

```bash
# Просмотреть созданный golden-файл
cat tests/adapters/python/goldens/new_optimization.golden

# Закоммитить в репозиторий
git add tests/adapters/python/goldens/new_optimization.golden
git commit -m "Add golden test for new optimization"
```

### 4. При изменениях в коде

Если тест падает с ошибкой golden test:

```bash
# Просмотреть diff
.venv/Scripts/python.exe -m pytest tests/adapters/python/test_new.py::test_new_optimization -v

# Если изменения ожидаемые - обновить golden-файл
PYTEST_UPDATE_GOLDENS=1 .venv/Scripts/python.exe -m pytest tests/adapters/python/test_new.py::test_new_optimization -v

# Проверить изменения и закоммитить
git diff tests/adapters/python/goldens/new_optimization.golden
git add tests/adapters/python/goldens/new_optimization.golden  
git commit -m "Update golden file after optimization improvement"
```

## Best Practices

### Именование golden-файлов

- Используйте описательные имена: `python_basic_strip`, `typescript_class_methods`
- Избегайте слишком длинных имен
- Используйте snake_case

### Детерминизм

Убедитесь что результаты тестов детерминированы:

- Не включайте время/даты в вывод
- Сортируйте коллекции при необходимости
- Используйте фиксированные входные данные

### Размер golden-файлов

- Старайтесь делать тесты фокусными - один аспект на тест
- Для больших результатов рассмотрите разбиение на несколько тестов
- Очень большие golden-файлы затрудняют review

### Контроль версий

- **Обязательно** коммитьте golden-файлы в репозиторий
- Включите изменения golden-файлов в review процесс
- При merge conflicts в golden-файлах регенерируйте их

### CI/CD

В CI/CD убедитесь что:

- Golden-файлы проверяются как обычные тесты
- НЕ используется автообновление (PYTEST_UPDATE_GOLDENS=1)
- При падении тестов diff ясно виден в логах

## Troubleshooting

### Тест падает с "Golden test failed"

1. Просмотрите diff в выводе pytest
2. Определите причину изменений:
   - Баг в коде → исправьте код
   - Ожидаемое изменение → обновите golden-файл

### Golden-файл не создается

1. Проверьте права на запись в директорию `goldens/`
2. Убедитесь что используете правильную функцию `assert_golden_match`
3. Проверьте что тест доходит до вызова `assert_golden_match`

### Проблемы с определением языка

Если автоопределение языка не работает:

```python
# Явно укажите язык
assert_golden_match(result, "test_name", language="python")
```

### Encoding проблемы

Golden-файлы сохраняются в UTF-8. При проблемах с кодировкой:

1. Убедитесь что входные данные в UTF-8
2. Проверьте настройки вашего редактора
3. При необходимости нормализуйте входные данные

## Расширение системы

### Добавление нового языка

1. Создайте директорию `tests/adapters/new_language/`
2. Добавьте `conftest.py` с импортом:
   ```python
   from ..golden_utils import assert_golden_match
   ```
3. Создайте директорию `goldens/`
4. Скрипт `update_goldens.sh` автоматически обнаружит новый язык

### Кастомизация golden-файлов

Для специфичных требований можно расширить `golden_utils.py`:

```python
def assert_golden_match_custom(result, name, normalizer=None):
    if normalizer:
        result = normalizer(result)
    assert_golden_match(result, name)
```
