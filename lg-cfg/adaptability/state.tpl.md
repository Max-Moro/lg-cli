## Текущий статус разработки функционального блока «Адаптивные возможности»

### Анализ существующего кода и точек интеграции

Текущая архитектура LG построена вокруг следующих основных компонентов:

1. **Конфигурация** (config) - загрузка и обработка YAML-конфигураций
2. **Контексты** (context) - шаблоны, контексты и плейсхолдеры
3. **Манифесты** (manifest) - построение файловых манифестов на основе фильтров
4. **Рендеринг** (render) - преобразование обработанных файлов в итоговый текст
5. **Адаптеры** (adapters) - обработка файлов разных форматов
6. **Статистика** (stats) - подсчет токенов и формирование отчетов
7. **CLI** (cli.py) - интерфейс командной строки

#### Точки расширения

Для внедрения адаптивных возможностей мы выделяем следующие ключевые точки расширения:

1. **Загрузка конфигурации режимов и тегов**
   - Новые файлы: `modes.yaml`, `tags.yaml`
   - Интеграция с существующей системой конфигурации

2. **Контекст выполнения**
   - Расширение `RunContext` для хранения активных режимов и тегов

3. **Обработка шаблонов**
   - Добавление поддержки условной логики (`{% if ... %}`)
   - Поддержка блоков режимов (`{% mode ... %}`)

4. **Фильтрация файлов**
   - Расширение модели фильтров для поддержки условной логики

5. **CLI**
   - Новые параметры для управления режимами и тегами
   - Новые команды для вывода информации о доступных режимах и тегах
   - Логика работы с `vcs.changed_files` теперь работает с опцией `vcs_mode` от активного режима, а не с аргументом `--mode` из CLI

### Новые модули и их назначение

#### Система конфигурации режимов и тегов

```
lg/config/
  ├── modes.py      # Загрузка и обработка режимов
  ├── tags.py       # Загрузка и обработка тегов
  └── adaptive.py   # Общая логика адаптивной системы
```

#### Система условий

```
lg/conditions/
  ├── __init__.py
  ├── parser.py     # Парсер с рекурсивным спуском
  ├── lexer.py      # Лексер для токенизации условий
  └── model.py      # Модели условных выражений
```

##### Ключевые классы и функции:

```python
# model.py
class ConditionType(Enum):
    TAG = "tag"
    TAGSET = "tagset"
    SCOPE = "scope"
    AND = "and"
    OR = "or"
    NOT = "not"
    GROUP = "group"  # для явной группировки в скобках

@dataclass
class Condition(ABC):
    """Базовый абстрактный класс для условий"""
    
    @abstractmethod
    def get_type(self) -> ConditionType:
        """Возвращает тип условия"""
        pass

@dataclass
class TagCondition(Condition):
    """Условие наличия тега: tag:name"""
    name: str
    
    def get_type(self) -> ConditionType:
        return ConditionType.TAG

@dataclass
class TagSetCondition(Condition):
    """Условие на набор тегов: TAGSET:set:tag"""
    set_name: str
    tag_name: str
    
    def get_type(self) -> ConditionType:
        return ConditionType.TAGSET

@dataclass
class ScopeCondition(Condition):
    """Условие скоупа: scope:type"""
    scope_type: str  # "local" или "parent"
    
    def get_type(self) -> ConditionType:
        return ConditionType.SCOPE

@dataclass
class GroupCondition(Condition):
    """Группа условий в скобках: (condition)"""
    condition: Condition
    
    def get_type(self) -> ConditionType:
        return ConditionType.GROUP

@dataclass
class NotCondition(Condition):
    """Отрицание условия: NOT condition"""
    condition: Condition
    
    def get_type(self) -> ConditionType:
        return ConditionType.NOT

@dataclass
class BinaryCondition(Condition):
    """Бинарная операция: left op right"""
    left: Condition
    right: Condition
    operator: ConditionType  # AND или OR
    
    def get_type(self) -> ConditionType:
        return self.operator

# lexer.py
@dataclass
class Token:
    """Токен для парсинга условий"""
    type: str
    value: str
    position: int
    
    def __repr__(self):
        return f"Token({self.type}, '{self.value}', pos={self.position})"

class ConditionLexer:
    """Лексер для разбиения строки условия на токены"""
    
    TOKEN_SPECS = [ ]
    
    def tokenize(self, text: str) -> List[Token]:
        """Разбивает строку на токены"""
         ...
    
# parser.py
class ConditionParser:
    
    def parse(self, condition_str: str) -> Condition:
        """Парсит строку условия в AST"""
       ...
```

#### Расширения шаблонизатора

```
lg/templates/
  ├── __init__.py
  ├── conditional.py  # Обработка условных блоков
  └── mode_blocks.py  # Обработка блоков режимов
```

##### Ключевые классы и функции:

```python
# conditional.py
@dataclass
class ConditionalBlock:
    condition: Condition
    content: str
    else_content: Optional[str] = None

def parse_conditional_blocks(template_text: str) -> List[Union[str, ConditionalBlock]]:
    """Разбор шаблона на текст и условные блоки"""
    ...

def render_with_conditions(blocks: List[Union[str, ConditionalBlock]], context: ConditionContext) -> str:
    """Рендеринг шаблона с учетом условий"""
    ...

# mode_blocks.py
@dataclass
class ModeBlock:
    mode_set: str
    mode: str
    content: str

def parse_mode_blocks(template_text: str) -> List[Union[str, ModeBlock]]:
    """Разбор шаблона на текст и блоки режимов"""
    ...

def process_mode_blocks(blocks: List[Union[str, ModeBlock]], active_modes: Dict[str, str]) -> str:
    """Обработка блоков режимов"""
    ...
```

#### Обновления в системе фильтрации

```python
# io/model.py
@dataclass
class ConditionalFilterRule:
    condition: Condition
    allow: List[str] = field(default_factory=list)
    block: List[str] = field(default_factory=list)
    
@dataclass
class FilterNode:
    mode: Mode
    allow: List[str] = field(default_factory=list)
    block: List[str] = field(default_factory=list)
    children: Dict[str, "FilterNode"] = field(default_factory=dict)
    when: List[ConditionalFilterRule] = field(default_factory=list)  # новое поле
```

### План внедрения

#### [+] Итерация 1: Основы и конфигурация

1. **[+] Реализация базовых моделей данных**
2. **[+] Загрузка конфигурации**
3. **[+] Расширение RunContext**

#### [] Итерация 2: Система условий

1. **[] Парсер условий**
   - Реализация модели для представления условий
   - Парсер для выражений условий с поддержкой операторов `tag`, `TAGSET`, `AND`, `OR`, `NOT`

2. **[] Вычислитель условий**
   - Реализация вычислителя условных выражений
   - Контекстно-зависимая оценка (`scope:local`, `scope:parent`)

3. **[] Фреймворк тестирования**
   - Модульные тесты для парсера условий
   - Модульные тесты для вычислителя условий

#### [] Итерация 3: Условные блоки в шаблонах

1. **[] Базовые условные блоки**
   - Реализация синтаксиса `{% if условие %} ... {% endif %}`
   - Интеграция с системой рендеринга шаблонов

2. **[] Блоки режимов**
   - Реализация синтаксиса `{% mode modeset:mode %} ... {% endmode %}`
   - Поддержка переопределения режимов в шаблонах

3. **[] Тестирование**
   - Модульные тесты для условных блоков
   - Интеграционные тесты для обработки шаблонов

#### [] Итерация 4: Интеграция условной фильтрации

1. **[] Условные фильтры**
   - Расширение узлов фильтрации с условиями `when`
   - Интеграция вычисления условий с обработкой фильтров

2. **[] Расширения конфигурации секций**
   - Обновление `SectionCfg` для поддержки условных конфигураций
   - Применение условий к конфигурации адаптеров

#### [] Итерация 5: CLI и документация

1. **[] Команды CLI**
   - Реализация команды `lg list mode-sets`
   - Реализация команды `lg list tag-sets`
   - Полная интеграция параметров `--mode` и `--tags`

2. **[] Документация**
   - Пользовательская документация по режимам и тегам
   - Примеры условных шаблонов
   - Руководство по миграции от старого стиля к условным шаблонам

3. **[] Примеры и тесты**
   - Примеры конфигураций
   - Сквозные тесты
