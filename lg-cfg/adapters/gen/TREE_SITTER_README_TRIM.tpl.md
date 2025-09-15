# Tree-sitter: Комплексная документация для Python разработчиков

## Введение и установка

### Что такое Tree-sitter

Tree-sitter — это инкрементальная библиотека для парсинга, которая создает конкретные синтаксические деревья для исходного кода и эффективно обновляет их при редактировании. Основные преимущества:

- **Универсальность** — может парсить любой язык программирования
- **Скорость** — достаточно быстр для парсинга при каждом нажатии клавиши
- **Устойчивость** — предоставляет полезные результаты даже при синтаксических ошибках
- **Независимость** — runtime библиотека написана на чистом C

### Установка

```bash
# Установка основной библиотеки
pip install tree-sitter

# Установка языковых парсеров
pip install tree-sitter-python
pip install tree-sitter-typescript
```

### Версии ABI

- **LANGUAGE_VERSION**: 15 (последняя поддерживаемая версия)
- **MIN_COMPATIBLE_LANGUAGE_VERSION**: 13 (минимальная совместимая версия)

## Основные концепции

### Четыре основных типа объектов

1. **Language** — определяет как парсить конкретный язык программирования
2. **Parser** — объект с состоянием для создания синтаксических деревьев
3. **Tree** — представляет синтаксическое дерево всего файла исходного кода
4. **Node** — представляет отдельную ноду в синтаксическом дереве

### Именованные vs анонимные ноды

- **Именованные ноды** соответствуют именованным правилам в грамматике
- **Анонимные ноды** соответствуют строковым литералам в грамматике

## Python API

### Базовый пример использования

```python
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

# Создание языка и парсера
PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

# Парсинг кода
source_code = '''
def foo():
    if bar:
        baz()
'''

tree = parser.parse(bytes(source_code, "utf8"))
root_node = tree.root_node

# Получение информации о ноде
print(f"Тип корневой ноды: {root_node.type}")
print(f"Позиция: {root_node.start_point} - {root_node.end_point}")
print(f"Дети: {len(root_node.children)}")
```

### Класс Language

```python
# Создание языка
language = Language(tspython.language())

# Свойства языка
print(language.abi_version)        # Версия ABI
print(language.node_kind_count)    # Количество типов нод
print(language.field_count)        # Количество полей

# Методы для работы с типами нод
node_id = language.id_for_node_kind("function_definition", True)
node_name = language.node_kind_for_id(node_id)
is_named = language.node_kind_is_named(node_id)

# Методы для работы с полями
field_id = language.field_id_for_name("name")
field_name = language.field_name_for_id(field_id)

# Создание итератора предпросмотра
lookahead_iter = language.lookahead_iterator(state_id)
```

### Класс Parser

```python
# Создание парсера
parser = Parser(language)

# Или создание без языка и установка позже
parser = Parser()
parser.language = language

# Парсинг из строки
tree = parser.parse(bytes(source_code, "utf8"))

# Парсинг с callback функцией
def read_callable(byte_offset, point):
    row, column = point
    if row >= len(source_lines):
        return None
    if column >= len(source_lines[row]):
        return b"\n"
    return source_lines[row][column:].encode("utf8")

tree = parser.parse(read_callable, encoding="utf8")

# Инкрементальный парсинг
old_tree = parser.parse(old_source)
# ... редактирование дерева ...
new_tree = parser.parse(new_source, old_tree)

# Установка диапазонов для парсинга
from tree_sitter import Range, Point

ranges = [
    Range(
        start_point=Point(0, 10),
        end_point=Point(0, 20),
        start_byte=10,
        end_byte=20
    )
]
parser.included_ranges = ranges
```

### Класс Tree

```python
# Получение корневой ноды
root_node = tree.root_node

# Копирование дерева (очень быстро)
tree_copy = tree.copy()

# Редактирование дерева
tree.edit(
    start_byte=5,
    old_end_byte=5,
    new_end_byte=7,
    start_point=Point(0, 5),
    old_end_point=Point(0, 5),
    new_end_point=Point(0, 7)
)

# Получение измененных диапазонов
changed_ranges = old_tree.changed_ranges(new_tree)
for range_obj in changed_ranges:
    print(f"Изменен диапазон: {range_obj.start_point} - {range_obj.end_point}")

# Корневая нода со смещением
root_with_offset = tree.root_node_with_offset(10, Point(2, 2))
```

### Класс Node

```python
# Основные свойства ноды
node = tree.root_node
print(f"Тип: {node.type}")
print(f"Именованная: {node.is_named}")
print(f"Пропущенная: {node.is_missing}")
print(f"Дополнительная: {node.is_extra}")
print(f"Ошибка: {node.is_error}")
print(f"Есть изменения: {node.has_changes}")
print(f"Есть ошибки: {node.has_error}")

# Позиционирование
print(f"Начальный байт: {node.start_char}")
print(f"Конечный байт: {node.end_char}")
print(f"Начальная позиция: {node.start_point}")
print(f"Конечная позиция: {node.end_point}")
print(f"Байтовый диапазон: {node.byte_range}")

# Работа с детьми
print(f"Количество детей: {node.child_count}")
print(f"Количество именованных детей: {node.named_child_count}")

# Получение детей
first_child = node.child(0)
named_child = node.named_child(0)
all_children = node.children
named_children = node.named_children

# Работа с полями
name_node = node.child_by_field_name("name")
body_node = node.child_by_field_name("body")
field_name = node.field_name_for_child(0)

# Навигация по дереву
parent = node.parent
next_sibling = node.next_sibling
prev_sibling = node.prev_sibling
next_named_sibling = node.next_named_sibling

# Поиск потомков
descendant = node.descendant_for_byte_range(10, 20)
named_descendant = node.named_descendant_for_byte_range(10, 20)
point_descendant = node.descendant_for_point_range(
    Point(1, 0), Point(2, 10)
)

# Получение текста ноды
text = node.text  # Возвращает bytes

# Строковое представление
s_expression = str(node)
```

### Класс TreeCursor

```python
# Создание курсора
cursor = tree.walk()

# Или от конкретной ноды
cursor = node.walk()

# Навигация
cursor.goto_first_child()    # True если успешно
cursor.goto_last_child()
cursor.goto_next_sibling()
cursor.goto_previous_sibling()
cursor.goto_parent()

# Переход к потомку по индексу
cursor.goto_descendant(5)

# Переход к первому ребенку по байту/позиции
child_index = cursor.goto_first_child_for_byte(100)
child_index = cursor.goto_first_child_for_point(Point(5, 10))

# Получение текущей ноды
current_node = cursor.node

# Информация о позиции
field_id = cursor.field_id
field_name = cursor.field_name
depth = cursor.depth
descendant_index = cursor.descendant_index

# Сброс курсора
cursor.reset(node)
cursor.reset_to(other_cursor)

# Копирование курсора
cursor_copy = cursor.copy()
```

## Работа с языковыми парсерами

### Поддерживаемые языки

```python
# Python
import tree_sitter_python as tspython
PY_LANGUAGE = Language(tspython.language())

# TypeScript
import tree_sitter_typescript as tsts
TS_LANGUAGE = Language(tsts.language_typescript())
TSX_LANGUAGE = Language(tsts.language_tsx())
```

### Парсинг с различными кодировками

```python
# UTF-8 (по умолчанию)
tree = parser.parse(source_code.encode('utf-8'))

# UTF-16
tree = parser.parse(source_code.encode('utf-16'), encoding="utf16")

# Callback для кастомного чтения
def read_callback(byte_offset, point):
    # Ваша логика чтения
    return chunk.encode('utf-8')

tree = parser.parse(read_callback)
```

## Синтаксические запросы (Queries)

### Создание и выполнение запросов

```python
from tree_sitter import Query, QueryCursor

# Создание запроса
query = Query(
    PY_LANGUAGE,
    """
    (function_definition
      name: (identifier) @function.def
      body: (block) @function.block)

    (call
      function: (identifier) @function.call
      arguments: (argument_list) @function.args)
    """
)

# Выполнение запроса
query_cursor = QueryCursor(query)

# Получение совпадений
matches = query_cursor.matches(tree.root_node)
for pattern_index, captures in matches:
    print(f"Паттерн {pattern_index}:")
    for capture_name, nodes in captures.items():
        for node in nodes:
            print(f"  {capture_name}: {node.text}")

# Получение захватов
captures = query_cursor.captures(tree.root_node)
for capture_name, nodes in captures.items():
    print(f"{capture_name}:")
    for node in nodes:
        print(f"  {node.text} at {node.start_point}")
```

### Синтаксис запросов

```scheme
; Базовый синтаксис - S-выражения
(function_definition
  name: (identifier) @func-name
  parameters: (parameters) @params
  body: (block) @body)

; Альтернативы
[
  (identifier) @variable
  (number) @constant
  (string) @string
]

; Квантификаторы
(comment)+ @comments          ; один или более
(decorator)* @decorators      ; ноль или более
(type_annotation)? @type      ; опционально

; Группировка
(
  (comment)
  (function_definition)
)

; Якоря
(array . (identifier) @first-element)     ; первый элемент
(block (_) @last-statement .)             ; последнее выражение
(call (identifier) @func . (identifier) @first-arg)  ; соседние ноды

; Поля
(assignment_expression
  left: (identifier) @variable
  right: (expression) @value)

; Отрицание полей
(class_declaration
  name: (identifier) @class_name
  !type_parameters)

; Анонимные ноды
(binary_expression
  operator: "!="
  right: (null))

; Специальные ноды
(ERROR) @error-node
(MISSING) @missing-node
(MISSING identifier) @missing-identifier
(_) @wildcard-named
_ @wildcard-any
```

### Предикаты и директивы

```scheme
; Проверка равенства
((identifier) @variable.builtin
  (#eq? @variable.builtin "self"))

; Проверка неравенства
((identifier) @variable
  (#not-eq? @variable "self"))

; Регулярные выражения
((identifier) @constant
  (#match? @constant "^[A-Z][A-Z_]+$"))

; Отрицание регулярного выражения
((identifier) @variable
  (#not-match? @variable "^[A-Z]"))

; Проверка вхождения в множество
((identifier) @builtin
  (#any-of? @builtin "print" "len" "range" "enumerate"))

; Сравнение захватов
(assignment_expression
  left: (identifier) @var1
  right: (identifier) @var2
  (#eq? @var1 @var2))

; Квантифицированные предикаты
((comment)+ @comments
  (#any-eq? @comments "# TODO"))

; Установка свойств
((comment) @injection.content
  (#set! injection.language "sql"))

; Проверка свойств
((identifier) @variable
  (#is? local))

((identifier) @function
  (#is-not? local))
```

## Навигация по коду

### Извлечение тегов

```python
from tree_sitter_tags import TagsContext, TagsConfiguration

# Создание конфигурации тегов
tags_config = TagsConfiguration(
    language=PY_LANGUAGE,
    tags_query=tspython.TAGS_QUERY,
    locals_query=""  # Опционально
)

# Создание контекста
context = TagsContext()

# Генерация тегов
tags = context.generate_tags(
    tags_config,
    source_code.encode('utf-8'),
    None
)

# Обработка тегов
for tag in tags:
    print(f"Тип: {tag.kind}")
    print(f"Диапазон: {tag.range}")
    print(f"Имя: {tag.name_range}")
    print(f"Документация: {tag.docs}")
```

### Стандартные типы тегов

- `@definition.class` — определения классов
- `@definition.function` — определения функций
- `@definition.method` — определения методов
- `@definition.module` — определения модулей
- `@definition.interface` — определения интерфейсов
- `@reference.call` — вызовы функций/методов
- `@reference.class` — ссылки на классы
- `@reference.implementation` — реализации интерфейсов

## Продвинутые возможности

### Работа с ошибками

```python
def find_errors(node):
    """Рекурсивно находит все ошибки в дереве"""
    errors = []
    
    if node.is_error:
        errors.append(node)
    
    if node.is_missing:
        errors.append(node)
    
    for child in node.children:
        errors.extend(find_errors(child))
    
    return errors

def has_syntax_errors(tree):
    """Проверяет наличие синтаксических ошибок"""
    return tree.root_node.has_error
```

### Эффективный обход дерева

```python
def walk_tree_iteratively(tree):
    """Итеративный обход дерева с помощью курсора"""
    cursor = tree.walk()
    
    visited_children = False
    while True:
        if not visited_children:
            # Обработка текущей ноды
            yield cursor.node
            
            if not cursor.goto_first_child():
                visited_children = True
        elif cursor.goto_next_sibling():
            visited_children = False
        elif not cursor.goto_parent():
            break
        else:
            visited_children = True

def find_nodes_by_type(node, node_type):
    """Находит все ноды определенного типа"""
    result = []
    
    def visit(node):
        if node.type == node_type:
            result.append(node)
        for child in node.children:
            visit(child)
    
    visit(node)
    return result
```

## Примеры для конкретных языков

### Python

```python
import tree_sitter_python as tspython

# Анализ функций Python
FUNCTION_QUERY = """
(function_definition
  name: (identifier) @function.name
  parameters: (parameters) @function.params
  body: (block) @function.body)

(class_definition
  name: (identifier) @class.name
  body: (block) @class.body)
"""

def analyze_python_file(source_code):
    parser = Parser(Language(tspython.language()))
    tree = parser.parse(source_code.encode('utf-8'))
    
    query = Query(Language(tspython.language()), FUNCTION_QUERY)
    cursor = QueryCursor(query)
    captures = cursor.captures(tree.root_node)
    
    functions = []
    classes = []
    
    for capture_name, nodes in captures.items():
        for node in nodes:
            if capture_name == "function.name":
                functions.append(node.text.decode('utf-8'))
            elif capture_name == "class.name":
                classes.append(node.text.decode('utf-8'))
    
    return {"functions": functions, "classes": classes}
```

### JavaScript/TypeScript

```python
import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts

# Анализ импортов и экспортов
IMPORT_EXPORT_QUERY = """
(import_statement
  (import_clause
    (named_imports
      (import_specifier
        name: (identifier) @import.name))))

(export_statement
  (export_clause
    (export_specifier
      name: (identifier) @export.name)))

(call_expression
  function: (identifier) @function.call
  arguments: (arguments) @function.args)
"""

def analyze_js_imports_exports(source_code, is_typescript=False):
    language = Language(tsts.language_typescript() if is_typescript 
                       else tsjs.language())
    parser = Parser(language)
    tree = parser.parse(source_code.encode('utf-8'))
    
    query = Query(language, IMPORT_EXPORT_QUERY)
    cursor = QueryCursor(query)
    captures = cursor.captures(tree.root_node)
    
    imports = []
    exports = []
    calls = []
    
    for capture_name, nodes in captures.items():
        for node in nodes:
            text = node.text.decode('utf-8')
            if capture_name == "import.name":
                imports.append(text)
            elif capture_name == "export.name":
                exports.append(text)
            elif capture_name == "function.call":
                calls.append(text)
    
    return {
        "imports": imports,
        "exports": exports,
        "function_calls": calls
    }
```

## Заключение

Tree-sitter предоставляет мощный и гибкий API для анализа исходного кода. Основные преимущества при работе с Python:

1. **Простота использования** — интуитивный API
2. **Производительность** — быстрый парсинг и инкрементальные обновления  
3. **Гибкость** — поддержка множества языков и кастомных запросов
4. **Устойчивость** — работа даже с некорректным кодом

Используйте эту документацию как справочник при разработке инструментов анализа кода, IDE, линтеров и других приложений, работающих с исходным кодом.