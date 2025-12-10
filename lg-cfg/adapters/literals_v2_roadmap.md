# Дорожная карта: Literal Optimization (целевое состояние «v2»)

> Рабочий код перерабатывается в текущем каталоге. Параллельных веток и совместимости со старой моделью не будет.

## Принципы миграции

1. **Атомарность**: Каждый подэтап - минимальное изменение с полной проверкой тестов
2. **Нулевые регрессии**: После каждого подэтапа все 100 тестов должны проходить
3. **Постепенность**: Миграция языков идет группами по 1-3 языка
4. **Backward compatibility**: До полной миграции ядра сохраняется совместимость через конвертацию

## Этапы (после каждого подэтапа все тесты проходят)

### ✅ Этап 1: Новая модель паттернов и дескриптора (profiles → patterns)

**Цель**: Заменить плоский `LiteralPattern` на типизированную иерархию профилей из v2.

---

### ✅ Этап 2: Ввод `processing/pipeline.py` как владельца оркестрации

**Выполнено**:
- Создан `lg/adapters/optimizations/literals/processing/pipeline.py` с полной оркестрацией
- Pipeline владеет двухпроходной логикой (Pass 1: strings, Pass 2: collections)
- Pipeline управляет обходом AST и применением результатов к context
- **УДАЛЁН** `core.py` (логика перенесена в pipeline)
- Все импорты обновлены: `LiteralOptimizer` → `LiteralPipeline`

---

#### ✅ Этап 3: Вынос парсинга

**Выполнено**:
- Создан `processing/parser.py` с классом `LiteralParser` для парсинга литералов из Tree-sitter нод
- Перенесены методы `parse_literal_with_pattern`, `_detect_wrapper_from_text`, `_extract_content` из `handler.py` в `LiteralParser`
- `handler.py` делегирует парсинг в `LiteralParser` (остались только прокладки)
- Старый `parser.py` переименован в `element_parser.py` (парсинг элементов ВНУТРИ литералов)
- Обновлены все импорты: `from .parser import` → `from .element_parser import`
- Чёткое разделение:
  - `processing/parser.py` (`LiteralParser`) — парсинг литералов из исходного кода
  - `element_parser.py` (`ElementParser`) — парсинг элементов внутри контента литерала

---

### ✅ Этап 4: Вынос бюджетного выбора

**Выполнено**:
- Создан `processing/selector.py` с полной логикой выбора по бюджету (Selection/DFSSelection)
- Обновлены импорты в `handler.py`, `formatter.py`, `__init__.py`
- **УДАЛЁН** старый `selector.py`

---

### ✅ Этап 5: Вынос форматирования и плейсхолдеров

**Выполнено**:
- Создан `processing/formatter.py` с полной логикой форматирования (ResultFormatter, FormattedResult)
- Обновлены импорты в `handler.py`, `__init__.py`
- **УДАЛЁН** старый `formatter.py`

---

### Этап 6: Адаптация ядра для работы с профилями напрямую

**Цель**: Убрать промежуточную конвертацию профилей → LiteralPattern, научить ядро работать с профилями.

#### ✅ 6.1) Рефакторинг parser для работы с профилями

**Выполнено**:
- Добавлен `LiteralProfile = Union[StringProfile, SequenceProfile, ...]` в `patterns.py`
- `ParsedLiteral.profile: object` вместо `pattern` (избегаем circular imports)
- `processing/parser.py`: новые методы `parse_literal_with_profile()`, `_get_category_from_profile()`, `_get_delimiter()`
- `processing/pipeline.py`: итерирует по `descriptor.string_profiles`, `descriptor.*_profiles` и передает профили в handler
- `handler.py`: методы принимают `profile` + `pattern` (backward compat), добавлена временная `_convert_profile_to_pattern()`
- `processing/formatter.py`: использует `hasattr()` для безопасного доступа к атрибутам профилей
- Интерполяция работает корректно через `isinstance(profile, StringProfile)`

#### ✅ 6.2) Рефакторинг selector для работы с профилями

**Выполнено**:
- Добавлена функция `create_parse_config_from_profile()` в `element_parser.py`
- Добавлен метод `handler.get_parser_for_profile()` для создания parser из профиля
- Обновлены сигнатуры `select_dfs()` и `_select_dfs_tuples()` для работы с `profile` и `handler`
- Временная конвертация `_convert_profile_to_pattern()` больше не используется в selector

#### ✅ 6.3) Рефакторинг formatter для работы с профилями

**Выполнено**:
- Исправлено последнее использование `parsed.pattern.query` → `getattr(profile, 'query', 'unknown')`
- Formatter полностью работает с профилями через `hasattr()`/`getattr()`
- Убрана последняя зависимость от `parsed.pattern` в formatter

#### 6.4) Удаление backward compatibility
- Удалить метод `to_patterns()` (и использующий его код) из `LanguageLiteralDescriptor`
- Удалить старое поле `_patterns: List[LiteralPattern]` если оно осталось
- **Критерий**: Все 100 тестов проходят

#### 6.5) Удаление LiteralPattern
- Переместить enum `LiteralCategory` в `patterns.py` (используется профилями)
- Удалить класс `LiteralPattern` из `categories.py`
- Обновить импорты во всех файлах
- **Критерий**: Все 100 тестов проходят

---

### Этап 7: Компонент Interpolation
- Создать `components/interpolation.py`: правила границ/делимитеров интерполяции, корректировка тримминга строк
- Удалить дублирующие проверки интерполяции из parser/formatter и из `handler.py`; подключить через pipeline
- **Критерий**: Все 100 тестов проходят

---

### Этап 8: Компонент AST sequence
- Создать `components/ast_sequence.py` для последовательностей без разделителей (конкатенации строк и т.п.)
- Удалить AST-специфичные костыли из `handler.py`; использовать компонент через pipeline
- **Критерий**: Все 100 тестов проходят

---

### Этап 9: Компонент Block init
- Создать `components/block_init.py` с API для imperative инициализаций (double-brace Java, Rust HashMap chain)
- Удалить из старого `block_init.py` размещённые эвристики; подключить новый компонент из pipeline
- **Критерий**: Все 100 тестов проходят

---

### Этап 10: Компонент Placeholder/Comment
- Создать `components/placeholder.py` для единого формирования плейсхолдеров/комментариев
- Удалить логику вставки комментариев из formatter и `handler.py`; оставить вызовы компонента
- **Критерий**: Все 100 тестов проходят

---

### Этап 11: Компонент Budgeting
- Создать `components/budgeting.py` с политиками приоритетов/лимитов
- Убрать бюджетные решения из formatter/parser; pipeline передает бюджет в selector/компонент
- **Критерий**: Все 100 тестов проходят

---

### Этап 12: Полное отключение наследия handler

**Цель**: Удалить последний legacy файл и убедиться что pipeline содержит только высокоуровневую оркестрацию.

- **УДАЛИТЬ** `handler.py` (единственный оставшийся legacy файл)
- Обновить экспорты `lg/adapters/optimizations/literals/__init__.py` на `processing/` + `components/`
- Убедиться что в `pipeline.py` осталась **только высокоуровневая оркестрация**:
  - Управление двухпроходной логикой
  - Вызовы компонентов из `processing/` и `components/`
  - Никакой детальной логики парсинга/форматирования/бюджетирования
- Проверить, что адаптеры используют только pipeline/processing/компоненты
- **Критерий**: Все 100 тестов проходят

---

### Этап 13: Разгрузка языковых хаков
- В языковых `literals.py` убрать специальные ветки, которые покрываются компонентами (interpolation, ast_sequence, block_init)
- Оставить только декларативные профили/флаги в дескрипторах
- **Критерий**: Все 100 тестов проходят

---

### Этап 14: Финальная чистка структуры
- Убрать временные типы/шунты, оставить минимально необходимый публичный API (patterns/descriptor/pipeline/компоненты)
- Обновить `__init__.py` в `components/` и `processing/` для явных экспортов
- Финальный прогон всех тестов
- **Критерий**: Все 100 тестов проходят

---

## Текущий статус

- **Ветка**: `literals-v2`
- **Текущий этап**: Завершён подэтап 6.3, готов к подэтапу 6.4
- **Последний успешный прогон**: 100/100 тестов
- **Удалённые legacy файлы**: `core.py` ✅, `selector.py` ✅, `formatter.py` ✅
- **Переименованные файлы**: `parser.py` → `element_parser.py` ✅
- **Новые файлы в processing/**: `parser.py` ✅, `selector.py` ✅, `formatter.py` ✅
- **Оставшиеся legacy файлы**: `handler.py` (будет удалён на Этапе 12)
- **Прогресс Этапа 6**: Parser ✅, Selector ✅, Formatter ✅
