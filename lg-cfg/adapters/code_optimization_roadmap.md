## Дорожная карта: Миграция на новую Code Optimization архитектуру

Этот документ описывает план миграции с текущей архитектуры (CodeAnalyzer hierarchy) на новую декларативную архитектуру (LanguageCodeDescriptor).

---

### Ключевые принципы миграции

#### Принцип 1: Старый код отключаем, но сохраняем

Весь legacy-код отключаем от pipeline, но физически удаляем только в самом конце:

```
lg/adapters/code_analysis.py                              # Отключить, пометить deprecated
lg/adapters/<язык>/code_analysis.py                       # Отключить, пометить deprecated
lg/adapters/<язык>/queries.py                             # Оставить только comments и imports
lg/adapters/optimizations/public_api/language_profiles/   # Отключить, пометить deprecated
```

**Причина**: Старый код служит исчерпывающим примером — "как и почему работало раньше". Удаление после полной стабилизации.

#### Принцип 2: Разрушительный рефакторинг

Это **не** постепенная миграция. Мы полностью переходим на новую архитектуру:

- LG временно перестаёт быть стабильным
- Промежуточные состояния не тестируются
- Все языки переводятся последовательно, но в рамках одного этапа

#### Принцип 3: Нет пилотного языка

Нет специального "пилотного" языка. Нет состояния "часть языков по-старому, часть по-новому":

- Оба оптимизатора переводятся на новую архитектуру **до** работы с языками
- Затем все 10 языков актуализируются последовательно
- Тестирование начинается только когда legacy полностью отключен

#### Принцип 4: Стратегия тестирования

Используем только существующие golden-тесты:

```bash
# Во время работы над языками:
./scripts/test_adapters.sh function_bodies,public_api <язык>

# После завершения всех языков:
./scripts/test_adapters.sh function_bodies,public_api all
```

**Важно**: Не запускать другие оптимизаторы — их актуализация не относится к текущей работе.

---

### Этапы миграции

#### Этап 1: Создание shared-инфраструктуры

Создать новые модули без изменения существующего кода:

```
lg/adapters/optimizations/shared/
├── __init__.py
├── descriptor.py    # LanguageCodeDescriptor
├── profiles.py      # ElementProfile
├── models.py        # CodeElement
└── collector.py     # ElementCollector
```

**Задачи**:
- [ ] Реализовать `ElementProfile` с `is_public` callback
- [ ] Реализовать `CodeElement` (унифицированная модель)
- [ ] Реализовать `LanguageCodeDescriptor`
- [ ] Реализовать `ElementCollector` с методами:
  - `collect_all()`
  - `collect_private()`
  - `collect_with_bodies()`

**Критерий**: Код компилируется.

---

#### Этап 2: Перевод оптимизаторов на shared-инфраструктуру

Переписать оба оптимизатора на использование `ElementCollector` вместо `code_analyzer`:

**ProcessingContext**:
- [ ] Добавить `_collector: Optional[ElementCollector]` поле
- [ ] Добавить `get_collector(descriptor)` метод для lazy-кэширования

**PublicApiOptimizer**:
- [ ] Использовать `context.get_collector(descriptor).collect_private()`
- [ ] Удалить зависимость от `context.code_analyzer`

**FunctionBodyOptimizer**:
- [ ] Использовать `context.get_collector(descriptor).collect_with_bodies()`
- [ ] Адаптировать evaluators для работы с `CodeElement`
- [ ] Удалить зависимость от `context.code_analyzer`

**Критерий**: Оптимизаторы используют только shared-инфраструктуру. Collector кэшируется в ProcessingContext.

---

#### Этап 3: Отключение legacy-кода

Полностью отключить старый код от pipeline:

- [ ] Удалить `create_code_analyzer()` из `CodeAdapter`
- [ ] Удалить `context.code_analyzer` из `ProcessingContext`
- [ ] Пометить deprecated:
  - `lg/adapters/code_analysis.py`
  - `lg/adapters/<язык>/code_analysis.py`
  - `lg/adapters/optimizations/public_api/language_profiles/`
- [ ] Добавить `get_code_descriptor()` в `CodeAdapter` (abstract method)

**Критерий**: Legacy-код не вызывается. Pipeline использует только новую архитектуру (но языки ещё не работают).

---

#### Этап 4: Актуализация языков

Последовательно создать `code_profiles.py` для каждого языка:

| Язык | Статус |
|------|--------|
| Python | ⬜ |
| TypeScript | ⬜ |
| JavaScript | ⬜ |
| Java | ⬜ |
| Kotlin | ⬜ |
| Scala | ⬜ |
| Go | ⬜ |
| Rust | ⬜ |
| C++ | ⬜ |
| C | ⬜ |

**Для каждого языка**:
- [ ] Создать `<язык>/code_profiles.py` с `<ЯЗЫК>_CODE_DESCRIPTOR`
- [ ] Реализовать `_is_public_<язык>()` callback
- [ ] Перенести профили элементов из `language_profiles/<язык>.py`
- [ ] Добавить `has_body=True` и `docstring_extractor` для functions/methods
- [ ] Реализовать `get_code_descriptor()` в адаптере
- [ ] Проверить: `./scripts/test_adapters.sh function_bodies,public_api <язык>`

**Критерий**: Все golden-тесты для языка проходят.

---

#### Этап 5: Финальная проверка и очистка

**Финальная проверка**:
```bash
./scripts/test_adapters.sh function_bodies,public_api all
```

**Физическое удаление legacy-кода**:
- [ ] Удалить `lg/adapters/code_analysis.py`
- [ ] Удалить `lg/adapters/<язык>/code_analysis.py` (все 10 файлов)
- [ ] Удалить `lg/adapters/optimizations/public_api/language_profiles/` (вся директория)
- [ ] Очистить `lg/adapters/<язык>/queries.py` (оставить только comments и imports)
- [ ] Обновить `__init__.py` файлы
- [ ] Обновить документацию

**Критерий**: Репозиторий чист от legacy. Все тесты проходят.

