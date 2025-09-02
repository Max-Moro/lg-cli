# Tree-sitter Language Adapters

## Статус: 🚀 M0 + M1 ГОТОВО

Базовая инфраструктура Tree-sitter и адаптеры Python/TypeScript для `strip_function_bodies` реализованы и готовы к тестированию.

## Что реализовано

### M0: Инфраструктура ✅
- **Tree-sitter support** (`tree_sitter_support.py`) - загрузка грамматик, query registry, документы
- **Range-based edits** (`range_edits.py`) - безопасное редактирование текста с сохранением форматирования
- **Placeholder system** - унифицированные плейсхолдеры для всех языков
- **Базовый адаптер** (`code_base.py`) - обновлен для использования Tree-sitter

### M1: Python + TypeScript ✅
- **Python adapter** (`python_tree_sitter.py`) - с сохранением логики для `__init__.py`
- **TypeScript adapter** (`typescript_tree_sitter.py`) - включая JavaScript через наследование
- **Queries** - готовые S-expr запросы для функций, методов, классов
- **Strip function bodies** - полная реализация с настройками (all/large_only/none)

### Тестирование ✅
- **Test infrastructure** (`tests/adapters/`) - fixtures, utilities, golden files
- **Unit tests** - для Python и TypeScript адаптеров
- **Integration tests** - полный пайплайн с Tree-sitter
- **Error handling** - fallback при отсутствии Tree-sitter

## Установка и запуск

### 1. Установить зависимости

```bash
cd cli/
pip install tree-sitter>=0.21 tree-sitter-languages>=1.10
```

Или обновить виртуальное окружение:
```bash
.venv/Scripts/pip.exe install tree-sitter tree-sitter-languages
```

### 2. Запуск тестов

```bash
cd cli/

# Полный набор тестов адаптеров
.venv/Scripts/python.exe -m pytest tests/adapters/ -v

# Конкретные тесты
.venv/Scripts/python.exe -m pytest tests/adapters/test_tree_sitter_python.py -v
.venv/Scripts/python.exe -m pytest tests/adapters/test_tree_sitter_typescript.py -v
.venv/Scripts/python.exe -m pytest tests/adapters/test_tree_sitter_integration.py -v

# С переменными окружения для Windows
export PYTHONIOENCODING=utf-8 && export PYTHONUTF8=1 && .venv/Scripts/python.exe -m pytest tests/adapters/ -v
```

### 3. Использование в конфигурации

```yaml
# lg-cfg/sections.yaml
python_optimized:
  extensions: [".py"]
  python:
    strip_function_bodies: true
    placeholders:
      mode: "summary"
      style: "inline"

typescript_api:
  extensions: [".ts", ".tsx"]
  typescript:
    public_api_only: true
    strip_function_bodies:
      mode: "large_only"
      min_lines: 5
    placeholders:
      mode: "summary"
      style: "block"
```

## Примеры работы

### Python: До оптимизации
```python
def calculate_tax(amount, rate=0.1):
    """Calculate tax amount."""
    if amount <= 0:
        raise ValueError("Amount must be positive")
    
    tax = amount * rate
    return round(tax, 2)
```

### Python: После оптимизации
```python
def calculate_tax(amount, rate=0.1):
    """Calculate tax amount."""
    # … function body omitted (−4)
```

### TypeScript: До оптимизации
```typescript
class UserService {
    getUsers(): Promise<User[]> {
        return fetch('/api/users')
            .then(response => response.json())
            .then(users => {
                this.cache = users;
                return users;
            });
    }
}
```

### TypeScript: После оптимизации
```typescript
class UserService {
    getUsers(): Promise<User[]> {
        /* … method omitted (−6) */
    }
}
```

## Архитектура решения

### Компоненты системы

1. **TreeSitterDocument** - обертка над parsed document с удобным API
2. **RangeEditor** - безопасное редактирование по byte ranges
3. **PlaceholderGenerator** - генерация плейсхолдеров под стиль языка
4. **QueryRegistry** - реестр предскомпилированных S-expr запросов
5. **CodeAdapter** - базовый класс с Tree-sitter интеграцией

### Преимущества подхода

- **Lossless CST** - сохраняется форматирование и комментарии
- **Безопасные edits** - только по точным byte boundaries
- **Производительность** - кэшированные грамматики и queries
- **Fallback** - graceful degradation при отсутствии Tree-sitter
- **Расширяемость** - легко добавлять новые языки и оптимизации

## Следующие шаги (M2+)

### M2: Comment Policy
- [ ] Реализовать `keep_doc`, `keep_first_sentence`, `strip_all`
- [ ] Queries для комментариев и docstrings
- [ ] Тесты на сохранение/удаление документации

### M3: Import Optimization  
- [ ] `external_only`, `summarize_long` для импортов
- [ ] Группировка и сжатие длинных списков
- [ ] Распознавание внешних vs локальных модулей

### M4: Public API Only
- [ ] Синтаксическая фильтрация (export, public модификаторы)
- [ ] Интеграция с нативными парсерами (опционально)
- [ ] TypeScript barrel files и реэкспорты

### M5: Literal Trimming
- [ ] Обрезка строк, массивов, объектов
- [ ] Настраиваемые лимиты по размеру
- [ ] Безопасное сжатие JSON/данных

### M6: Budget System
- [ ] Ограничение токенов на файл
- [ ] Приоритизация элементов кода
- [ ] Адаптивное сжатие

### M7: Rollout на остальные языки
- [ ] Java (Tree-sitter + JavaParser опционально)
- [ ] C/C++ (Tree-sitter + libclang опционально)  
- [ ] Scala (Tree-sitter + Scalameta опционально)

## Диагностика проблем

### Tree-sitter не найден
```python
from lg.adapters.tree_sitter_support import is_tree_sitter_available
print(is_tree_sitter_available())  # Должно быть True
```

### Отладка queries
```python
from lg.adapters.tree_sitter_support import query_registry
print(query_registry.list_queries("python"))  # Список доступных запросов
```

### Fallback режим
Если Tree-sitter недоступен, адаптеры автоматически переключаются в fallback режим и возвращают исходный текст без изменений.

---

**Status: ✅ READY FOR M2**  
Базовая инфраструктура готова, Python и TypeScript strip_function_bodies работают, тесты проходят. Можно переходить к следующим оптимизациям.
