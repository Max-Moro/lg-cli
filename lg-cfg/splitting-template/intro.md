# Задача по разделению шаблонизатора на модули

## Введение

В инструменте LG конечные контексты представляются в виде Markdown формата и могут собираться из множества источников по определенным правилам. По этой причине внутри LG используется довольно развитый движок шаблонизации на основе AST-based подхода — `lg/template/`.

Данный движок состоит из довольно традиционных модулей для AST-based систем:
- `nodes.py`
- `lexer.py`
- `parser.py`
- `evaluator.py`
- `resolver.py`
- `processor.py`

Так и исключительно из модулей со специфичной бизнес логикой:
- `virtual_sections.py`
- `heading_context.py`
- `context.py`
- `common.py`

На начальных этапах разработки такое разделение было логичным, но теперь, при росте функциональных возможностей его уже не достаточно.

Если рассматривать не внутреннюю математику, а именно бизнес функции движка шаблонизации, то можно выделить три крупных функциональных блока.

### Блок №1. Обработка плейсхолдеров секций и родных для LG шаблонов

- вставка секций — `${my-section}`
- вставка шаблонов — `${tpl:common/intro}`
- вставка контекста — `${ctx:api/review}`
- адресные ссылки и работа со скоупами

### Блок №2. Работа с условными конструкциями и операторами для адаптивных возможностей

- Условные конструкции
- Операторы условий
- Режимные блоки
- Комментарии

### Блок №3. Вставка не родных для LG Markdown-фрагментов через MD-плейсхолдер

Все возможности плейсхолдера `${md:…}`.

## Архитектура нового модульного шаблонизатора

Ниже представлен подробный план для создания новой версии в `lg/template_v2/`. Основная задача - разделить функциональность на логические блоки, обеспечивая гибкость и возможность независимой разработки компонентов.

### Общая структура директорий

```
lg/template_v2/
├── __init__.py
├── base.py              # Базовые интерфейсы и абстракции
├── registry.py          # Реестр компонентов
├── lexer.py             # Основа лексера
├── parser.py            # Основа парсера
├── processor.py         # Оркестрирующий компонент
├── errors.py            # Централизованная обработка ошибок
├── resolver.py          # Базовый резолвер ссылок
│
├── common_placeholders/ # Блок №1
│   ├── __init__.py
│   ├── nodes.py         # SectionNode, IncludeNode и т.д.
│   ├── tokens.py        # Определения токенов
│   ├── plugin.py        # Регистрация компонентов
│   ├── parser_rules.py  # Правила парсинга плейсхолдеров
│   ├── resolver.py      # Резолвер секций и шаблонов
│   └── processor.py     # Обработка узлов
│
├── adaptive/            # Блок №2
│   ├── __init__.py
│   ├── nodes.py         # ConditionalNode, ModeNode и т.д.
│   ├── tokens.py        # Определения токенов
│   ├── plugin.py        # Регистрация компонентов
│   ├── parser_rules.py  # Правила парсинга условий
│   ├── evaluator.py     # Вычислитель условий
│   └── processor.py     # Обработка узлов
│
└── md_placeholders/     # Блок №3
    ├── __init__.py
    ├── nodes.py         # MarkdownFileNode
    ├── tokens.py        # Определения токенов
    ├── plugin.py        # Регистрация компонентов
    ├── parser_rules.py  # Правила парсинга md-плейсхолдеров
    ├── heading_context.py # Анализ контекста заголовков
    ├── virtual_sections.py # Создание виртуальных секций
    └── processor.py     # Обработка узлов
```

### Ключевые компоненты архитектуры

#### 1. Система плагинов и регистрации

Основой нового подхода станет регистрационная система, позволяющая каждому функциональному блоку регистрировать свои компоненты в общем реестре:

```python
# lg/template_v2/base.py
from abc import ABC, abstractmethod
from typing import Dict, Type, Any

class TemplatePlugin(ABC):
    """Интерфейс для плагинов шаблонизатора."""
    
    @abstractmethod
    def register_token_types(self) -> Dict[str, Type]:
        """Регистрирует типы токенов."""
        pass
    
    @abstractmethod
    def register_node_types(self) -> Dict[str, Type]:
        """Регистрирует типы узлов AST."""
        pass
    
    @abstractmethod
    def register_parser_rules(self) -> Dict[str, Any]:
        """Регистрирует правила парсинга."""
        pass
    
    @abstractmethod
    def register_processors(self) -> Dict[str, Any]:
        """Регистрирует обработчики узлов."""
        pass
```

```python
# lg/template_v2/registry.py
class TemplateRegistry:
    """Централизованный реестр всех компонентов шаблонизатора."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.token_types = {}
        self.node_types = {}
        self.parser_rules = {}
        self.processors = {}
        self.plugins = []
    
    def register_plugin(self, plugin):
        """Регистрирует плагин и все его компоненты."""
        self.plugins.append(plugin)
        
        self.token_types.update(plugin.register_token_types())
        self.node_types.update(plugin.register_node_types())
        self.parser_rules.update(plugin.register_parser_rules())
        self.processors.update(plugin.register_processors())
```

#### 2. Модульный лексический анализатор

Лексер будет собирать регулярные выражения для токенов из всех зарегистрированных плагинов:

```python
# lg/template_v2/lexer.py
import re
from .registry import TemplateRegistry

class ModularLexer:
    """Лексический анализатор, собирающий паттерны токенов из плагинов."""
    
    def __init__(self):
        self.registry = TemplateRegistry.get_instance()
        self.patterns = {}
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        """Собирает паттерны токенов из реестра."""
        for token_name, token_class in self.registry.token_types.items():
            if hasattr(token_class, 'pattern') and token_class.pattern:
                self.patterns[token_name] = re.compile(token_class.pattern)
    
    def tokenize(self, text):
        """Разбивает текст на токены, используя собранные паттерны."""
        # Логика токенизации с учетом приоритетов и позиций
        # ...
```

#### 3. Модульный синтаксический анализатор

Парсер будет использовать правила парсинга из всех зарегистрированных плагинов:

```python
# lg/template_v2/parser.py
from .registry import TemplateRegistry

class ModularParser:
    """Синтаксический анализатор, использующий правила из плагинов."""
    
    def __init__(self):
        self.registry = TemplateRegistry.get_instance()
    
    def parse(self, tokens):
        """Парсит токены в AST с использованием зарегистрированных правил."""
        context = ParsingContext(tokens)
        ast = []
        
        while not context.is_at_end():
            node = self._parse_next_node(context)
            if node:
                ast.append(node)
            else:
                # Обработка ошибок или просто продвижение вперед
                context.advance()
        
        return ast
    
    def _parse_next_node(self, context):
        """Пытается применить каждое правило парсинга для текущей позиции."""
        # Сохраняем позицию для отката при неудачных попытках
        save_position = context.position
        
        # Пробуем каждое правило в порядке приоритета
        for rule_name, rule_func in self.registry.parser_rules.items():
            context.position = save_position  # Сбрасываем позицию
            node = rule_func(context)
            if node:
                return node
        
        # Ни одно правило не сработало
        return None
```

#### 4. Пример реализации функционального блока

Рассмотрим как будет реализован блок для обработки плейсхолдеров секций:

```python
# lg/template_v2/common_placeholders/plugin.py
from ..base import TemplatePlugin
from .nodes import SectionNode, IncludeNode, TextNode
from .tokens import SectionToken, IncludeToken
from .parser_rules import parse_section, parse_include
from .processor import process_section, process_include

class CommonPlaceholdersPlugin(TemplatePlugin):
    """Плагин для обработки плейсхолдеров секций и шаблонов."""
    
    def register_token_types(self):
        return {
            'SECTION_START': SectionToken,
            'INCLUDE_START': IncludeToken,
            # Другие токены...
        }
    
    def register_node_types(self):
        return {
            'SectionNode': SectionNode,
            'IncludeNode': IncludeNode,
            'TextNode': TextNode,
            # Другие узлы...
        }
    
    def register_parser_rules(self):
        return {
            'parse_section': parse_section,
            'parse_include': parse_include,
            # Другие правила...
        }
    
    def register_processors(self):
        return {
            'process_section': process_section,
            'process_include': process_include,
            # Другие обработчики...
        }
```

#### 5. Пример правила парсинга для секций

```python
# lg/template_v2/common_placeholders/parser_rules.py
from .nodes import SectionNode

def parse_section(context):
    """Правило парсинга для плейсхолдеров секций ${section_name}."""
    if context.current().type != 'PLACEHOLDER_START':
        return None
    
    # Продвигаемся вперед, пропуская ${
    context.advance()
    
    # Проверяем, что это не специальный плейсхолдер (tpl:, ctx:, md:)
    current = context.current()
    if current.type == 'IDENTIFIER':
        if current.value in ('tpl', 'ctx', 'md'):
            # Это другой тип плейсхолдера
            return None
    
    # Собираем имя секции
    section_name = ''
    while not context.is_at_end() and context.current().type != 'PLACEHOLDER_END':
        token = context.advance()
        section_name += token.value
    
    # Пропускаем закрывающую }
    context.advance()
    
    return SectionNode(section_name=section_name.strip())
```

### Интеграция и переключение между версиями

Для обеспечения плавной миграции добавим в engine.py логику переключения между версиями:

```python
# lg/engine.py
import os
from pathlib import Path

# ... существующий код ...

def _init_template_processor(self):
    """Инициализирует шаблонизатор нужной версии."""
    # Определяем, какую версию использовать
    use_v2 = os.environ.get("LG_USE_TEMPLATE_V2", "").lower() in ("1", "true", "yes")
    
    if use_v2:
        # Импортируем и используем новую версию
        from .template_v2.processor import TemplateProcessor
        self.template_processor = TemplateProcessor(self.run_ctx)
    else:
        # Используем текущую версию
        from .template.processor import TemplateProcessor
        self.template_processor = TemplateProcessor(self.run_ctx)

    # Установка обработчика секций
    self.template_processor.set_section_handler(self.section_processor.process_section)

# ... остальной код ...
```

## Специфика реализации каждого функционального блока

### Блок №1: Обработка плейсхолдеров секций и шаблонов

Этот блок отвечает за базовую функциональность вставки секций и шаблонов:
- Парсинг `${section_name}` и `${tpl:template_name}`
- Обработка адресных ссылок (`@origin:name`)
- Резолвинг и загрузка включаемых шаблонов

### Блок №2: Адаптивные возможности

Этот блок отвечает за условные конструкции и режимы:
- Парсинг `{% if condition %}...{% endif %}` и `{% mode ... %}`
- Вычисление условных выражений
- Управление активными режимами и тегами

### Блок №3: Вставка Markdown-фрагментов

Этот блок специализируется на обработке `${md:...}`:
- Анализ контекста заголовков
- Создание виртуальных секций
- Обработка параметров и якорей

## Преимущества новой архитектуры

1. **Модульность и расширяемость:**
   - Четкое разделение функциональных блоков
   - Легкое добавление новых возможностей через плагины
   - Независимая разработка и тестирование компонентов

2. **Улучшенная поддерживаемость:**
   - Изолированные изменения в каждом блоке
   - Уменьшение сложности отдельных модулей
   - Более четкие зависимости и API

3. **Гибкость конфигурации:**
   - Возможность включения/отключения определенных функций
   - Единообразный подход к регистрации компонентов
   - Упрощенное внедрение новых типов узлов и правил