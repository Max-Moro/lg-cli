## Дорожная карта: Миграция на новую Code Optimization архитектуру

Этот документ описывает пошаговый план миграции с текущей архитектуры (CodeAnalyzer hierarchy) на новую декларативную архитектуру (LanguageCodeDescriptor).

---

### Обзор этапов

| Этап | Название | Описание | Риск |
|------|----------|----------|------|
| 0 | Подготовка | Тесты, baseline, документация | Низкий |
| 1 | Инфраструктура | Новые модели и коллектор | Низкий |
| 2 | Python pilot | Полная миграция Python | Средний |
| 3 | Остальные языки | Миграция 9 языков | Средний |
| 4 | Оптимизаторы | Переключение на новую архитектуру | Высокий |
| 5 | Очистка | Удаление legacy кода | Низкий |

---

### Этап 0: Подготовка

**Цель**: Убедиться, что baseline стабилен и есть чёткое понимание текущего состояния.

#### Задачи

- [ ] **0.1** Убедиться что все тесты проходят
  ```bash
  ./scripts/test_adapters.sh all all
  pytest tests/
  ```

- [ ] **0.2** Документировать текущие queries для каждого языка
  - Создать таблицу: какие queries используются для public API
  - Создать таблицу: какие queries используются для function bodies

- [ ] **0.3** Создать чеклист профилей для каждого языка
  - Список элементов: class, function, method, field, etc.
  - Для каждого: visibility logic, export logic, has_body

**Критерий завершения**: Документ с полным списком элементов и их характеристик для всех 10 языков.

---

### Этап 1: Инфраструктура

**Цель**: Создать новые модели и коллектор без изменения существующего кода.

#### Задачи

- [ ] **1.1** Создать структуру директорий
  ```
  lg/adapters/optimizations/code/
  ├── __init__.py
  ├── models.py        # Visibility, CodeElement
  ├── profiles.py      # ElementProfile
  ├── descriptor.py    # LanguageCodeDescriptor
  └── collector.py     # ElementCollector
  ```

- [ ] **1.2** Реализовать `models.py`
  ```python
  @dataclass
  class CodeElement:
      profile: "ElementProfile"
      node: Node
      name: Optional[str] = None
      is_public: bool = True  # Вычисляется через profile.is_public
      body_node: Optional[Node] = None
      body_range: Optional[Tuple[int, int]] = None
      docstring_node: Optional[Node] = None
      decorators: List[Node] = field(default_factory=list)
  ```

- [ ] **1.3** Реализовать `profiles.py`
  ```python
  @dataclass
  class ElementProfile:
      name: str
      query: str
      is_public: Optional[Callable[[Node, Doc], bool]] = None  # None = always public
      additional_check: Optional[Callable[[Node, Doc], bool]] = None
      has_body: bool = False
      body_query: Optional[str] = None
      docstring_extractor: Optional[Callable[[Node, Doc], Optional[Node]]] = None
      parent_profile: Optional[str] = None
  ```

- [ ] **1.4** Реализовать `descriptor.py`
  ```python
  @dataclass
  class LanguageCodeDescriptor:
      language: str
      profiles: List[ElementProfile]
      decorator_types: Set[str] = field(default_factory=set)
      comment_types: Set[str] = field(default_factory=set)
  ```

- [ ] **1.5** Реализовать `collector.py`
  - `collect_all() -> List[CodeElement]`
  - `collect_private() -> List[CodeElement]`
  - `collect_with_bodies() -> List[CodeElement]`
  - `_filter_nested()` — фильтрация вложенных элементов

- [ ] **1.6** Написать unit-тесты для инфраструктуры
  ```
  tests/adapters/optimizations/code/
  ├── test_models.py
  ├── test_profiles.py
  └── test_collector.py
  ```

**Критерий завершения**: Все unit-тесты проходят. Инфраструктура готова к использованию.

---

### Этап 2: Python pilot

**Цель**: Полностью мигрировать Python на новую архитектуру. Валидировать подход.

#### Задачи

- [ ] **2.1** Создать `python/code_profiles.py`
  - Создать `_is_public_python()` callback (логика `_` и `__` префиксов)
  - Перенести профили из `optimizations/public_api/language_profiles/python.py`
  - Добавить `has_body=True` и `docstring_extractor` для functions/methods

- [ ] **2.2** Добавить метод в `PythonAdapter`
  ```python
  def get_code_descriptor(self) -> LanguageCodeDescriptor:
      from .code_profiles import PYTHON_CODE_DESCRIPTOR
      return PYTHON_CODE_DESCRIPTOR
  ```

- [ ] **2.3** Создать временные "bridge" оптимизаторы
  - `NewPublicApiOptimizer` — использует дескриптор
  - `NewFunctionBodyOptimizer` — использует дескриптор
  - Они работают параллельно со старыми (для сравнения)

- [ ] **2.4** Написать сравнительные тесты
  - Для каждого Python golden: сравнить результат старого и нового оптимизатора
  - Результаты должны быть идентичны

- [ ] **2.5** Исправить расхождения
  - Если результаты отличаются — исправить новый оптимизатор
  - Документировать любые намеренные изменения

- [ ] **2.6** Переключить Python на новую архитектуру
  ```python
  # code_base.py
  def _apply_optimizations(self, context, code_cfg):
      if self.get_code_descriptor():  # Новый путь
          ...
      else:  # Legacy путь
          ...
  ```

- [ ] **2.7** Запустить полный набор тестов для Python
  ```bash
  ./scripts/test_adapters.sh all python
  ```

**Критерий завершения**: Все Python тесты проходят. Голдены не изменились.

---

### Этап 3: Миграция остальных языков

**Цель**: Мигрировать остальные 9 языков по паттерну Python.

#### Порядок миграции (по сложности)

1. **Go** — простая visibility логика (naming convention)
2. **Rust** — `pub` модификаторы, понятная логика
3. **Java** — стандартные access modifiers
4. **Kotlin** — похож на Java
5. **Scala** — modifiers + case classes
6. **TypeScript** — export + visibility
7. **JavaScript** — convention-based (_, #)
8. **C++** — access specifiers + namespaces
9. **C** — static + naming

#### Для каждого языка

- [ ] Создать `<lang>/code_profiles.py`
- [ ] Добавить `get_code_descriptor()` в адаптер
- [ ] Запустить сравнительные тесты
- [ ] Исправить расхождения
- [ ] Переключить на новую архитектуру
- [ ] Проверить: `./scripts/test_adapters.sh all <lang>`

**Чеклист по языкам**:

| Язык | code_profiles.py | get_code_descriptor | Сравнительные тесты | Переключение | Финальные тесты |
|------|------------------|---------------------|---------------------|--------------|-----------------|
| Python | ✅ (Этап 2) | ✅ | ✅ | ✅ | ✅ |
| Go | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Rust | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Java | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Kotlin | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| Scala | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| TypeScript | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| JavaScript | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| C++ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| C | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |

**Критерий завершения**: Все 10 языков мигрированы. Все тесты проходят.

---

### Этап 4: Переключение оптимизаторов

**Цель**: Полностью перейти на новые оптимизаторы, удалить legacy код.

#### Задачи

- [ ] **4.1** Удалить legacy путь из `_apply_optimizations`
  ```python
  def _apply_optimizations(self, context, code_cfg):
      # Только новый путь
      if code_cfg.public_api_only:
          self.public_api_optimizer.apply(context)
      if code_cfg.strip_function_bodies:
          self.function_body_optimizer.apply(context, ...)
  ```

- [ ] **4.2** Удалить `create_code_analyzer()` из всех адаптеров

- [ ] **4.3** Удалить `context.code_analyzer` из ProcessingContext

- [ ] **4.4** Обновить `_post_bind()` в CodeAdapter
  - Создавать оптимизаторы на основе дескриптора

- [ ] **4.5** Полный прогон всех тестов
  ```bash
  ./scripts/test_adapters.sh all all
  pytest tests/
  ```

**Критерий завершения**: Legacy код не используется. Все тесты проходят.

---

### Этап 5: Очистка

**Цель**: Удалить весь legacy код, обновить документацию.

#### Задачи

- [ ] **5.1** Удалить файлы:
  ```
  lg/adapters/code_analysis.py
  lg/adapters/python/code_analysis.py
  lg/adapters/typescript/code_analysis.py
  lg/adapters/javascript/code_analysis.py
  lg/adapters/java/code_analysis.py
  lg/adapters/kotlin/code_analysis.py
  lg/adapters/scala/code_analysis.py
  lg/adapters/rust/code_analysis.py
  lg/adapters/go/code_analysis.py
  lg/adapters/cpp/code_analysis.py
  lg/adapters/c/code_analysis.py
  lg/adapters/optimizations/public_api/language_profiles/
  ```

- [ ] **5.2** Обновить `__init__.py` файлы
  - Удалить экспорты CodeAnalyzer, ElementInfo, FunctionGroup

- [ ] **5.3** Обновить imports во всех файлах

- [ ] **5.4** Обновить документацию:
  - `lg-cfg/adapters/code_optimization_architecture.md` — финальная версия
  - `docs/en/adapters.md` — обновить примеры
  - `README.md` — если есть упоминания

- [ ] **5.5** Финальный прогон всех тестов
  ```bash
  ./scripts/test_adapters.sh all all
  pytest tests/
  ```

- [ ] **5.6** Code review и коммит

**Критерий завершения**: Репозиторий чист от legacy кода. Документация актуальна.

---

### Риски и митигация

#### Риск 1: Расхождение результатов
**Проблема**: Новая архитектура даёт другие результаты.
**Митигация**: Сравнительные тесты на каждом этапе. При расхождении — анализ причины.

#### Риск 2: Неполное покрытие тестами
**Проблема**: Некоторые edge cases не покрыты тестами.
**Митигация**: Расширить golden tests перед миграцией. Добавить тесты для сложных случаев.

#### Риск 3: Сложность visibility логики в некоторых языках
**Проблема**: TypeScript/C++ имеют сложную логику (namespaces, access specifiers).
**Митигация**: Начать с простых языков (Go, Rust). Накопить опыт перед сложными.

#### Риск 4: Проблемы с function body stripping
**Проблема**: Текущая логика strippable_range сложная и языкоспецифичная.
**Митигация**: Детально протестировать на Python. Переносить логику аккуратно.

---

### Метрики успеха

1. **Нулевые изменения в голденах** после миграции
2. **100% тестов проходят** на каждом этапе
3. **Уменьшение LOC** в итоге (ожидается -30-40% в adapters/)
4. **Единообразие** между языками в code_profiles.py

---

### Оценка времени

| Этап | Оценка | Комментарий |
|------|--------|-------------|
| Этап 0 | 2-3 часа | Документация и анализ |
| Этап 1 | 4-6 часов | Новый код, тесты |
| Этап 2 | 6-8 часов | Python pilot, валидация |
| Этап 3 | 2-3 часа на язык × 9 = 18-27 часов | Зависит от сложности |
| Этап 4 | 2-4 часа | Переключение |
| Этап 5 | 2-3 часа | Очистка |

**Итого**: ~35-50 часов работы

---

### Следующие шаги

1. Прочитать и обсудить этот roadmap
2. Определить приоритеты (если нужно ускорить — какие языки важнее)
3. Начать с Этапа 0 (подготовка)
