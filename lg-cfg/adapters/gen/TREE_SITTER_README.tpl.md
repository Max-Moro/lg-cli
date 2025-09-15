# Tree-sitter: Комплексная документация для Python разработчиков

## Содержание

1. [Введение и установка](#введение-и-установка)
2. [Основные концепции](#основные-концепции)
3. [Python API](#python-api)
4. [Работа с языковыми парсерами](#работа-с-языковыми-парсерами)
5. [Синтаксические запросы (Queries)](#синтаксические-запросы-queries)
6. [Подсветка синтаксиса](#подсветка-синтаксиса)
7. [Навигация по коду](#навигация-по-коду)
8. [Продвинутые возможности](#продвинутые-возможности)
9. [Примеры для конкретных языков](#примеры-для-конкретных-языков)
10. [Лучшие практики](#лучшие-практики)

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
pip install tree-sitter-javascript
pip install tree-sitter-typescript
pip install tree-sitter-java
pip install tree-sitter-c
pip install tree-sitter-cpp
pip install tree-sitter-scala
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
print(f"Начальный байт: {node.start_byte}")
print(f"Конечный байт: {node.end_byte}")
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

# JavaScript
import tree_sitter_javascript as tsjs
JS_LANGUAGE = Language(tsjs.language())

# TypeScript
import tree_sitter_typescript as tsts
TS_LANGUAGE = Language(tsts.language_typescript())
TSX_LANGUAGE = Language(tsts.language_tsx())

# Java
import tree_sitter_java as tsjava
JAVA_LANGUAGE = Language(tsjava.language())

# C
import tree_sitter_c as tsc
C_LANGUAGE = Language(tsc.language())

# C++
import tree_sitter_cpp as tscpp
CPP_LANGUAGE = Language(tscpp.language())

# Scala
import tree_sitter_scala as tsscala
SCALA_LANGUAGE = Language(tsscala.language())
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

## Подсветка синтаксиса

### Стандартные имена подсветки

```python
HIGHLIGHT_NAMES = [
    "attribute",
    "comment", 
    "constant",
    "constant.builtin",
    "constructor",
    "function",
    "function.builtin", 
    "function.method",
    "keyword",
    "module",
    "number",
    "operator", 
    "property",
    "property.builtin",
    "punctuation",
    "punctuation.bracket",
    "punctuation.delimiter",
    "punctuation.special",
    "string",
    "string.special",
    "tag",
    "type",
    "type.builtin",
    "variable",
    "variable.builtin",
    "variable.parameter",
]
```

### Использование подсветки

```python
from tree_sitter_highlight import Highlighter, HighlightConfiguration

# Создание конфигурации подсветки
highlight_config = HighlightConfiguration(
    language=PY_LANGUAGE,
    highlight_query=tspython.HIGHLIGHTS_QUERY,
    injection_query="",  # Опционально
    locals_query=""      # Опционально
)

highlight_config.configure(HIGHLIGHT_NAMES)

# Создание подсветчика
highlighter = Highlighter()

# Выполнение подсветки
highlights = highlighter.highlight(
    highlight_config,
    source_code.encode('utf-8'),
    None,
    lambda name: None  # Callback для инъекций языков
)

# Обработка результатов
for event in highlights:
    match event:
        case HighlightEvent.Source(start, end):
            print(f"Исходный код: {start}-{end}")
        case HighlightEvent.HighlightStart(style):
            print(f"Начало стиля: {style}")
        case HighlightEvent.HighlightEnd():
            print("Конец стиля")
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

### Многоязыковые документы

```python
# Парсинг HTML с встроенным JavaScript
html_parser = Parser(HTML_LANGUAGE)
html_tree = html_parser.parse(template_content)

# Найти script теги
script_nodes = []
# ... логика поиска script нод ...

# Парсинг JavaScript внутри script тегов
js_parser = Parser(JS_LANGUAGE)
for script_node in script_nodes:
    js_ranges = [Range(
        start_point=script_node.start_point,
        end_point=script_node.end_point,
        start_byte=script_node.start_byte,
        end_byte=script_node.end_byte
    )]
    js_parser.included_ranges = js_ranges
    js_tree = js_parser.parse(template_content)
```

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

### Java

```python
import tree_sitter_java as tsjava

# Анализ классов и методов Java
JAVA_QUERY = """
(class_declaration
  name: (identifier) @class.name
  body: (class_body
    (method_declaration
      name: (identifier) @method.name
      parameters: (formal_parameters) @method.params)))

(interface_declaration
  name: (identifier) @interface.name)

(annotation
  name: (identifier) @annotation.name)
"""

def analyze_java_file(source_code):
    parser = Parser(Language(tsjava.language()))
    tree = parser.parse(source_code.encode('utf-8'))
    
    query = Query(Language(tsjava.language()), JAVA_QUERY)
    cursor = QueryCursor(query)
    captures = cursor.captures(tree.root_node)
    
    result = {
        "classes": [],
        "methods": [],
        "interfaces": [],
        "annotations": []
    }
    
    for capture_name, nodes in captures.items():
        for node in nodes:
            text = node.text.decode('utf-8')
            if capture_name == "class.name":
                result["classes"].append(text)
            elif capture_name == "method.name":
                result["methods"].append(text)
            elif capture_name == "interface.name":
                result["interfaces"].append(text)
            elif capture_name == "annotation.name":
                result["annotations"].append(text)
    
    return result
```

### C/C++

```python
import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp

# Анализ функций и структур C/C++
C_CPP_QUERY = """
(function_definition
  declarator: (function_declarator
    declarator: (identifier) @function.name)
  body: (compound_statement) @function.body)

(struct_specifier
  name: (type_identifier) @struct.name
  body: (field_declaration_list) @struct.body)

(class_specifier
  name: (type_identifier) @class.name
  body: (field_declaration_list) @class.body)

(call_expression
  function: (identifier) @function.call)
"""

def analyze_c_cpp_file(source_code, is_cpp=False):
    language = Language(tscpp.language() if is_cpp else tsc.language())
    parser = Parser(language)
    tree = parser.parse(source_code.encode('utf-8'))
    
    query = Query(language, C_CPP_QUERY)
    cursor = QueryCursor(query)
    captures = cursor.captures(tree.root_node)
    
    result = {
        "functions": [],
        "structs": [],
        "classes": [] if is_cpp else None,
        "function_calls": []
    }
    
    for capture_name, nodes in captures.items():
        for node in nodes:
            text = node.text.decode('utf-8')
            if capture_name == "function.name":
                result["functions"].append(text)
            elif capture_name == "struct.name":
                result["structs"].append(text)
            elif capture_name == "class.name" and is_cpp:
                result["classes"].append(text)
            elif capture_name == "function.call":
                result["function_calls"].append(text)
    
    return result
```

### Scala

```python
import tree_sitter_scala as tsscala

# Анализ Scala кода
SCALA_QUERY = """
(class_definition
  name: (identifier) @class.name)

(object_definition
  name: (identifier) @object.name)

(function_definition
  name: (identifier) @function.name
  parameters: (parameters) @function.params)

(trait_definition
  name: (identifier) @trait.name)

(case_class_definition
  name: (identifier) @case_class.name)
"""

def analyze_scala_file(source_code):
    parser = Parser(Language(tsscala.language()))
    tree = parser.parse(source_code.encode('utf-8'))
    
    query = Query(Language(tsscala.language()), SCALA_QUERY)
    cursor = QueryCursor(query)
    captures = cursor.captures(tree.root_node)
    
    result = {
        "classes": [],
        "objects": [],
        "functions": [],
        "traits": [],
        "case_classes": []
    }
    
    for capture_name, nodes in captures.items():
        for node in nodes:
            text = node.text.decode('utf-8')
            if capture_name == "class.name":
                result["classes"].append(text)
            elif capture_name == "object.name":
                result["objects"].append(text)
            elif capture_name == "function.name":
                result["functions"].append(text)
            elif capture_name == "trait.name":
                result["traits"].append(text)
            elif capture_name == "case_class.name":
                result["case_classes"].append(text)
    
    return result
```

## Лучшие практики

### Управление памятью

```python
# Всегда удаляйте объекты после использования
def safe_parsing(source_code, language):
    parser = None
    tree = None
    try:
        parser = Parser(language)
        tree = parser.parse(source_code.encode('utf-8'))
        
        # Ваша логика обработки
        return process_tree(tree)
        
    finally:
        # Объекты автоматически освобождаются в Python
        # но можно явно удалить для больших деревьев
        pass
```

### Эффективная работа с большими файлами

```python
def analyze_large_file(file_path, language, chunk_size=8192):
    """Анализ больших файлов по частям"""
    parser = Parser(language)
    
    with open(file_path, 'rb') as f:
        def read_callback(byte_offset, point):
            f.seek(byte_offset)
            chunk = f.read(chunk_size)
            return chunk if chunk else None
        
        tree = parser.parse(read_callback)
        return tree

def find_specific_patterns(tree, query_string):
    """Поиск специфических паттернов с ограничением глубины"""
    query = Query(tree.language, query_string)
    cursor = QueryCursor(query)
    
    # Ограничение поиска по глубине для производительности
    cursor.set_max_start_depth(10)
    
    return cursor.captures(tree.root_node)
```

### Инкрементальное обновление

```python
class IncrementalParser:
    def __init__(self, language):
        self.parser = Parser(language)
        self.tree = None
        self.source_code = ""
    
    def update(self, new_source_code):
        """Инкрементальное обновление дерева"""
        if self.tree is None:
            self.tree = self.parser.parse(new_source_code.encode('utf-8'))
            self.source_code = new_source_code
            return self.tree
        
        # Вычисление изменений
        old_source = self.source_code.encode('utf-8')
        new_source = new_source_code.encode('utf-8')
        
        # Простое определение изменений (в реальности нужна более сложная логика)
        start_byte = 0
        old_end_byte = len(old_source)
        new_end_byte = len(new_source)
        
        # Редактирование дерева
        self.tree.edit(
            start_byte=start_byte,
            old_end_byte=old_end_byte,
            new_end_byte=new_end_byte,
            start_point=Point(0, 0),
            old_end_point=Point(old_source.count(b'\n'), 0),
            new_end_point=Point(new_source.count(b'\n'), 0)
        )
        
        # Повторный парсинг с использованием старого дерева
        self.tree = self.parser.parse(new_source, self.tree)
        self.source_code = new_source_code
        
        return self.tree
```

### Кэширование и оптимизация

```python
from functools import lru_cache

class OptimizedAnalyzer:
    def __init__(self):
        self.parsers = {}
        self.queries = {}
    
    @lru_cache(maxsize=10)
    def get_parser(self, language_name):
        """Кэширование парсеров"""
        if language_name not in self.parsers:
            language_map = {
                'python': Language(tspython.language()),
                'javascript': Language(tsjs.language()),
                'typescript': Language(tsts.language_typescript()),
                'java': Language(tsjava.language()),
                'c': Language(tsc.language()),
                'cpp': Language(tscpp.language()),
                'scala': Language(tsscala.language()),
            }
            self.parsers[language_name] = Parser(language_map[language_name])
        
        return self.parsers[language_name]
    
    @lru_cache(maxsize=20)
    def get_query(self, language_name, query_string):
        """Кэширование запросов"""
        parser = self.get_parser(language_name)
        query_key = (language_name, hash(query_string))
        
        if query_key not in self.queries:
            self.queries[query_key] = Query(parser.language, query_string)
        
        return self.queries[query_key]
```

### Работа с кодировками

```python
def parse_with_encoding_detection(file_path, language):
    """Парсинг с автоопределением кодировки"""
    import chardet
    
    with open(file_path, 'rb') as f:
        raw_data = f.read()
    
    # Определение кодировки
    encoding_info = chardet.detect(raw_data)
    encoding = encoding_info['encoding'] or 'utf-8'
    
    # Декодирование
    try:
        source_code = raw_data.decode(encoding)
    except UnicodeDecodeError:
        source_code = raw_data.decode('utf-8', errors='replace')
    
    # Парсинг
    parser = Parser(language)
    return parser.parse(source_code.encode('utf-8'))
```

## Интеграция с другими инструментами

### Интеграция с LSP

```python
def create_lsp_diagnostics(tree):
    """Создание диагностики для LSP сервера"""
    diagnostics = []
    
    def find_errors(node):
        if node.is_error:
            diagnostics.append({
                "range": {
                    "start": {"line": node.start_point.row, "character": node.start_point.column},
                    "end": {"line": node.end_point.row, "character": node.end_point.column}
                },
                "severity": 1,  # Error
                "message": f"Syntax error: unexpected {node.type}",
                "source": "tree-sitter"
            })
        
        if node.is_missing:
            diagnostics.append({
                "range": {
                    "start": {"line": node.start_point.row, "character": node.start_point.column},
                    "end": {"line": node.end_point.row, "character": node.end_point.column}
                },
                "severity": 1,  # Error
                "message": f"Missing {node.type}",
                "source": "tree-sitter"
            })
        
        for child in node.children:
            find_errors(child)
    
    find_errors(tree.root_node)
    return diagnostics
```

### Создание AST-анализаторов

```python
class ASTAnalyzer:
    def __init__(self, language):
        self.parser = Parser(language)
        self.language = language
    
    def get_complexity_score(self, source_code):
        """Вычисление сложности кода"""
        tree = self.parser.parse(source_code.encode('utf-8'))
        
        complexity_query = """
        (if_statement) @complexity
        (for_statement) @complexity  
        (while_statement) @complexity
        (try_statement) @complexity
        (function_definition) @complexity
        """
        
        query = Query(self.language, complexity_query)
        cursor = QueryCursor(query)
        captures = cursor.captures(tree.root_node)
        
        return len(captures.get('complexity', []))
    
    def extract_dependencies(self, source_code):
        """Извлечение зависимостей"""
        tree = self.parser.parse(source_code.encode('utf-8'))
        
        # Специфичные запросы для каждого языка
        # Здесь пример для Python
        import_query = """
        (import_statement
          name: (dotted_name) @import.module)
        
        (import_from_statement
          module_name: (dotted_name) @import.module)
        """
        
        query = Query(self.language, import_query)
        cursor = QueryCursor(query)
        captures = cursor.captures(tree.root_node)
        
        modules = []
        for nodes in captures.values():
            for node in nodes:
                modules.append(node.text.decode('utf-8'))
        
        return list(set(modules))
```

## Обработка ошибок и отладка

### Отладка парсинга

```python
def debug_parsing(source_code, language):
    """Отладка процесса парсинга"""
    parser = Parser(language)
    
    # Включение логирования
    def logger(log_type, message):
        print(f"[{log_type.name}] {message}")
    
    parser.logger = logger
    
    tree = parser.parse(source_code.encode('utf-8'))
    
    # Анализ ошибок
    errors = []
    def collect_errors(node):
        if node.is_error or node.is_missing:
            errors.append({
                'type': 'ERROR' if node.is_error else 'MISSING',
                'node_type': node.type,
                'position': node.start_point,
                'text': node.text.decode('utf-8', errors='replace')
            })
        
        for child in node.children:
            collect_errors(child)
    
    collect_errors(tree.root_node)
    return tree, errors
```

### Валидация синтаксиса

```python
def validate_syntax(source_code, language):
    """Валидация синтаксиса с подробным отчетом"""
    parser = Parser(language)
    tree = parser.parse(source_code.encode('utf-8'))
    
    issues = []
    
    def analyze_node(node, depth=0):
        # Проверка на ошибки
        if node.is_error:
            issues.append({
                'type': 'syntax_error',
                'severity': 'error',
                'message': f'Syntax error at {node.start_point}',
                'location': {
                    'start': node.start_point,
                    'end': node.end_point
                },
                'context': node.text.decode('utf-8', errors='replace')[:100]
            })
        
        # Проверка на пропущенные элементы
        if node.is_missing:
            issues.append({
                'type': 'missing_element',
                'severity': 'error', 
                'message': f'Missing {node.type} at {node.start_point}',
                'location': {
                    'start': node.start_point,
                    'end': node.end_point
                }
            })
        
        # Рекурсивный анализ детей
        for child in node.children:
            analyze_node(child, depth + 1)
    
    analyze_node(tree.root_node)
    
    return {
        'is_valid': len(issues) == 0,
        'issues': issues,
        'tree': tree
    }
```

## Утилитарные функции

### Конвертация между форматами

```python
def tree_to_dict(node):
    """Конвертация дерева в словарь"""
    result = {
        'type': node.type,
        'start_point': {'row': node.start_point.row, 'column': node.start_point.column},
        'end_point': {'row': node.end_point.row, 'column': node.end_point.column},
        'text': node.text.decode('utf-8', errors='replace') if not node.children else None,
        'children': []
    }
    
    for child in node.children:
        result['children'].append(tree_to_dict(child))
    
    return result

def tree_to_json(tree):
    """Конвертация дерева в JSON"""
    import json
    return json.dumps(tree_to_dict(tree.root_node), indent=2, ensure_ascii=False)

def find_node_at_position(tree, row, column):
    """Поиск ноды в определенной позиции"""
    point = Point(row, column)
    return tree.root_node.descendant_for_point_range(point, point)
```

### Метрики кода

```python
def calculate_code_metrics(source_code, language):
    """Вычисление метрик кода"""
    parser = Parser(language)
    tree = parser.parse(source_code.encode('utf-8'))
    
    metrics = {
        'total_nodes': 0,
        'max_depth': 0,
        'function_count': 0,
        'class_count': 0,
        'lines_of_code': source_code.count('\n') + 1
    }
    
    def calculate_depth(node, current_depth=0):
        metrics['total_nodes'] += 1
        metrics['max_depth'] = max(metrics['max_depth'], current_depth)
        
        if node.type in ('function_definition', 'method_definition'):
            metrics['function_count'] += 1
        elif node.type in ('class_definition', 'class_declaration'):
            metrics['class_count'] += 1
        
        for child in node.children:
            calculate_depth(child, current_depth + 1)
    
    calculate_depth(tree.root_node)
    return metrics
```

## Заключение

Tree-sitter предоставляет мощный и гибкий API для анализа исходного кода. Основные преимущества при работе с Python:

1. **Простота использования** — интуитивный API
2. **Производительность** — быстрый парсинг и инкрементальные обновления  
3. **Гибкость** — поддержка множества языков и кастомных запросов
4. **Устойчивость** — работа даже с некорректным кодом

Используйте эту документацию как справочник при разработке инструментов анализа кода, IDE, линтеров и других приложений, работающих с исходным кодом.