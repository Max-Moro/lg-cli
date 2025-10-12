# Kotlin Adapter Tests

Этот пакет содержит комплексный набор тестов для Kotlin языкового адаптера в Listing Generator.

## Структура

```
tests/adapters/kotlin/
├── conftest.py                          # Фикстуры и утилиты для тестов
├── goldens/                             # Golden файлы для тестов
│   ├── do/                              # Исходные образцы Kotlin кода
│   │   ├── function_bodies.kt           # Для тестирования удаления тел функций
│   │   ├── comments.kt                  # Для тестирования обработки комментариев
│   │   ├── literals.kt                  # Для тестирования оптимизации литералов
│   │   ├── imports.kt                   # Для тестирования оптимизации импортов
│   │   ├── public_api.kt                # Для тестирования фильтрации API
│   │   └── budget_complex.kt            # Для тестирования системы бюджетирования
│   ├── function_bodies/                 # Эталонные результаты для функций
│   ├── comments/                        # Эталонные результаты для комментариев
│   ├── literals/                        # Эталонные результаты для литералов
│   ├── imports/                         # Эталонные результаты для импортов
│   ├── public_api/                      # Эталонные результаты для API
│   └── budget/                          # Эталонные результаты для бюджета
├── test_function_bodies.py              # Тесты удаления тел функций
├── test_comments.py                     # Тесты обработки комментариев
├── test_literals.py                     # Тесты оптимизации литералов
├── test_imports.py                      # Тесты оптимизации импортов
├── test_public_api.py                   # Тесты фильтрации публичного API
├── test_budget.py                       # Тесты системы бюджетирования
├── test_literal_comment_context.py      # Тесты контекста комментариев
└── test_literals_indentation.py         # Тесты отступов в литералах
```

## Типы тестов

### 1. Function Bodies Tests (`test_function_bodies.py`)
Тестирует удаление тел функций и методов:
- Базовое удаление тел функций и методов
- Режим "large_only" (удаление только больших функций)
- Обработка лямбда-функций
- Сохранение структуры классов
- Режим "public_only"
- Сохранение KDoc при удалении тел

### 2. Comments Tests (`test_comments.py`)
Тестирует политики обработки комментариев:
- `keep_all` - сохранение всех комментариев
- `strip_all` - удаление всех комментариев
- `keep_doc` - сохранение только KDoc
- `keep_first_sentence` - сохранение только первого предложения
- Комплексные политики с кастомными настройками

### 3. Literals Tests (`test_literals.py`)
Тестирует оптимизацию литералов (строк, массивов, объектов):
- Обрезка длинных строковых литералов
- Оптимизация больших списков
- Оптимизация крупных map структур
- Разные бюджеты токенов (10, 20 и т.д.)

### 4. Imports Tests (`test_imports.py`)
Тестирует оптимизацию импортов:
- `keep_all` - сохранение всех импортов
- `strip_local` - удаление локальных импортов
- `strip_external` - удаление внешних импортов
- `strip_all` - удаление всех импортов
- Свёртка длинных списков импортов

### 5. Public API Tests (`test_public_api.py`)
Тестирует фильтрацию публичного API:
- Удаление private функций, методов, классов
- Сохранение публичных элементов
- Обработка visibility модификаторов
- Работа с data class и companion objects
- Обработка аннотаций

### 6. Budget Tests (`test_budget.py`)
Тестирует систему бюджетирования токенов:
- Прогрессивное ужимание при уменьшении бюджета
- Монотонное уменьшение размера результата
- Применение различных стратегий оптимизации

### 7. Literal Comment Context Tests (`test_literal_comment_context.py`)
Тестирует умное размещение комментариев при оптимизации литералов:
- Выбор между `//` и `/* */` в зависимости от контекста
- Предотвращение поломки синтаксиса

### 8. Literals Indentation Tests (`test_literals_indentation.py`)
Тестирует сохранение корректных отступов при оптимизации литералов:
- Отступы в map структурах
- Отступы в списках
- Отступы в вложенных структурах

## Запуск тестов

```bash
# Все тесты Kotlin адаптера
pytest tests/adapters/kotlin/

# Конкретный набор тестов
pytest tests/adapters/kotlin/test_function_bodies.py
pytest tests/adapters/kotlin/test_comments.py

# С обновлением golden файлов
PYTEST_UPDATE_GOLDENS=1 pytest tests/adapters/kotlin/test_function_bodies.py
```

## Golden файлы

Golden файлы - это эталонные результаты для сравнения. Они находятся в директории `goldens/`:

- `goldens/do/` - исходные образцы кода
- `goldens/*/` - эталонные результаты для различных оптимизаций

### Обновление golden файлов

Когда вы изменяете логику адаптера и хотите обновить эталоны:

```bash
PYTEST_UPDATE_GOLDENS=1 pytest tests/adapters/kotlin/
```

## Создание новых тестов

1. Добавьте новый образец кода в `goldens/do/your_test.kt`
2. Создайте тестовый файл `test_your_feature.py`
3. Используйте фикстуры из `conftest.py`:
   - `make_adapter(cfg)` - создание адаптера с заглушкой
   - `make_adapter_real(cfg)` - создание адаптера с реальным токенизатором
   - `lctx_kt(code)` - создание контекста для обработки
   - `assert_golden_match()` - сравнение с эталоном
   - `load_sample_code()` - загрузка образца кода

Пример:
```python
from .conftest import make_adapter, lctx_kt, assert_golden_match
from lg.adapters.kotlin import KotlinCfg

def test_my_feature():
    cfg = KotlinCfg(my_option=True)
    adapter = make_adapter(cfg)
    
    code = '''
    fun myFunction() {
        println("test")
    }
    '''
    
    result, meta = adapter.process(lctx_kt(code))
    
    assert "expected" in result
    assert_golden_match(result, "my_feature", "basic")
```

## Замечания

- Все тесты используют унифицированную инфраструктуру из `tests/infrastructure/`
- Golden файлы автоматически определяют язык по расширению `.kt`
- Тесты должны быть детерминированными и воспроизводимыми
- При изменении формата вывода адаптера необходимо обновить golden файлы

