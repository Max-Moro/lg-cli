# Архитектура подсистемы пропуска тривиальных файлов

Этот документ описывает архитектуру новой подсистемы оптимизации — **полного пропуска тривиальных файлов**.

---

## Мотивация

### Проблема

Многие проекты содержат файлы, которые выполняют сугубо **техническую роль** для компилятора, линкера или системы сборки, но практически **не несут полезной информации для AI-агента**:

- **Python**: тривиальные `__init__.py` с только реэкспортами
- **TypeScript/JavaScript**: barrel-файлы (`index.ts`) с реэкспортами
- **Go**: файлы `doc.go` с только package-level документацией
- **Rust**: тривиальные `mod.rs` или `lib.rs` с только `pub mod` декларациями
- **C/C++**: заголовочные файлы с только forward declarations или include guards
- **Kotlin/Java/Scala**: package-info файлы с только аннотациями

### Решение

Вместо включения таких файлов в листинг с последующей оптимизацией (удаление тел, комментариев и т.д.) — **полный пропуск файла** на раннем этапе обработки.

### Преимущества

1. **Экономия токенов** — файл не занимает место даже в виде заголовка/placeholder
2. **Чистота контекста** — AI видит только содержательный код
3. **Производительность** — ранний skip экономит время парсинга и обработки
4. **Унификация** — единый механизм для всех языков вместо разрозненных опций

---

## Архитектура

### Структура подсистемы

```
lg/adapters/
│
├── optimizations/
│   │
│   └── trivial_files/              # Общая инфраструктура
│       ├── __init__.py             # Публичный API
│       ├── analyzer.py             # TrivialFileAnalyzer (базовый класс)
│       └── patterns.py             # Общие паттерны тривиальности
│
└── langs/
    │
    ├── python/
    │   └── trivial.py              # PythonTrivialAnalyzer
    │
    ├── typescript/
    │   └── trivial.py              # TypeScriptTrivialAnalyzer
    │
    ├── javascript/
    │   └── trivial.py              # JavaScriptTrivialAnalyzer
    │
    ├── go/
    │   └── trivial.py              # GoTrivialAnalyzer
    │
    ├── rust/
    │   └── trivial.py              # RustTrivialAnalyzer
    │
    ├── kotlin/
    │   └── trivial.py              # KotlinTrivialAnalyzer
    │
    ├── java/
    │   └── trivial.py              # JavaTrivialAnalyzer
    │
    ├── scala/
    │   └── trivial.py              # ScalaTrivialAnalyzer
    │
    ├── cpp/
    │   └── trivial.py              # CppTrivialAnalyzer
    │
    └── c/
        └── trivial.py              # CTrivialAnalyzer
```

### Точка интеграции

Подсистема интегрируется через метод `should_skip()` в `CodeAdapter`:

```python
# lg/adapters/code_base.py

class CodeAdapter(BaseAdapter[C], ABC):

    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """
        Determine if file should be completely skipped from listing.

        Override in language adapters to detect trivial files.
        Default: no files are skipped.
        """
        return False
```

Языковые адаптеры переопределяют этот метод:

```python
# lg/adapters/langs/python/adapter.py

class PythonAdapter(CodeAdapter[PythonCfg]):

    def should_skip(self, lightweight_ctx: LightweightContext) -> bool:
        """Python-specific trivial file detection."""
        from .trivial import PythonTrivialAnalyzer
        analyzer = PythonTrivialAnalyzer()
        return analyzer.is_trivial(lightweight_ctx, self)
```

---

## Модель данных

### TrivialFileAnalyzer (базовый класс)

```python
# lg/adapters/optimizations/trivial_files/analyzer.py

from abc import ABC, abstractmethod
from typing import Optional

from ...context import LightweightContext


class TrivialFileAnalyzer(ABC):
    """
    Base class for language-specific trivial file detection.

    Subclasses implement language-specific patterns and heuristics.
    """

    @abstractmethod
    def is_trivial(
        self,
        ctx: LightweightContext,
        adapter
    ) -> bool:
        """
        Determine if file is trivial and should be skipped.

        Args:
            ctx: Lightweight context with file info and raw text
            adapter: Language adapter (for access to tokenizer, descriptors, etc.)

        Returns:
            True if file should be skipped entirely
        """
        pass

    def _get_full_context(self, ctx: LightweightContext, adapter):
        """
        Helper to lazily get full ProcessingContext when needed.

        Use sparingly — prefer lightweight analysis when possible.
        """
        return ctx.get_full_context(adapter, adapter.tokenizer)
```

### TrivialityResult (опционально)

Для более детальной диагностики можно использовать результат с причиной:

```python
@dataclass
class TrivialityResult:
    """Result of triviality analysis."""
    is_trivial: bool
    reason: Optional[str] = None  # "reexport_only", "empty_module", etc.
    confidence: float = 1.0  # 0.0-1.0 for heuristic decisions
```

---

## Языковые анализаторы

### Python: PythonTrivialAnalyzer

**Файлы для анализа**: `__init__.py`

**Критерии тривиальности**:

1. **Пустой файл** — только docstring или комментарии
2. **Только реэкспорты** — содержит только:
   - `from .module import name`
   - `from .module import *`
   - `__all__ = [...]`
   - Комментарии и docstrings

**Не тривиальные**:

- Содержит определения функций, классов, переменных
- Содержит условную логику (`if`, `try/except`)
- Содержит вызовы функций (кроме `__all__`)

```python
# lg/adapters/langs/python/trivial.py

class PythonTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial Python __init__.py files."""

    # Node types that indicate non-trivial content
    NON_TRIVIAL_TYPES = {
        "function_definition",
        "class_definition",
        "if_statement",
        "try_statement",
        "while_statement",
        "for_statement",
        "with_statement",
        "match_statement",
    }

    # Import types that are considered re-exports
    REEXPORT_TYPES = {
        "import_from_statement",
        "import_statement",
    }

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        # Only analyze __init__.py files
        if ctx.filename != "__init__.py":
            return False

        # Quick check: empty or very small file
        text = ctx.raw_text.strip()
        if not text:
            return True

        # Parse and analyze AST
        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_init_file(doc)

    def _analyze_init_file(self, doc) -> bool:
        """Analyze __init__.py AST for triviality."""
        root = doc.root_node

        for child in root.children:
            node_type = child.type

            # Skip trivial nodes
            if node_type in ("comment", "expression_statement"):
                # expression_statement with string = docstring
                if node_type == "expression_statement":
                    if not self._is_docstring_or_all(child, doc):
                        return False
                continue

            # Non-trivial content found
            if node_type in self.NON_TRIVIAL_TYPES:
                return False

            # Allow only imports
            if node_type not in self.REEXPORT_TYPES:
                return False

        return True

    def _is_docstring_or_all(self, node, doc) -> bool:
        """Check if expression is docstring or __all__ assignment."""
        text = doc.get_node_text(node)
        # Docstring: starts with quotes
        if text.startswith(('"""', "'''", '"', "'")):
            return True
        # __all__ assignment
        if text.strip().startswith("__all__"):
            return True
        return False
```

### TypeScript/JavaScript: BarrelFileAnalyzer

**Файлы для анализа**: `index.ts`, `index.js`, `index.tsx`, `index.jsx`

**Критерии тривиальности**:

1. **Только реэкспорты**:
   - `export { ... } from './module'`
   - `export * from './module'`
   - `export { default as Name } from './module'`

2. **Опционально допускаются**:
   - Комментарии
   - Type-only exports
   - `export type { ... } from './module'`

**Не тривиальные**:

- Содержит определения (functions, classes, interfaces, types)
- Содержит логику (statements, expressions кроме exports)
- Содержит side-effect imports (`import './styles.css'`)

```python
# lg/adapters/langs/typescript/trivial.py

class TypeScriptTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial TypeScript barrel files."""

    BARREL_FILENAMES = {"index.ts", "index.tsx"}

    REEXPORT_TYPES = {
        "export_statement",
    }

    NON_TRIVIAL_TYPES = {
        "function_declaration",
        "class_declaration",
        "interface_declaration",
        "type_alias_declaration",
        "enum_declaration",
        "variable_declaration",
        "expression_statement",
    }

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        if ctx.filename not in self.BARREL_FILENAMES:
            return False

        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_barrel_file(doc)

    def _analyze_barrel_file(self, doc) -> bool:
        """Analyze barrel file for triviality."""
        root = doc.root_node

        for child in root.children:
            node_type = child.type

            # Skip comments
            if node_type == "comment":
                continue

            # Non-trivial content
            if node_type in self.NON_TRIVIAL_TYPES:
                return False

            # For exports, check they are re-exports (have 'from')
            if node_type == "export_statement":
                if not self._is_reexport(child, doc):
                    return False
                continue

            # Side-effect imports are not trivial
            if node_type == "import_statement":
                return False

            # Unknown node type - be conservative
            return False

        return True

    def _is_reexport(self, node, doc) -> bool:
        """Check if export statement is a re-export (has 'from' clause)."""
        text = doc.get_node_text(node)
        return " from " in text or " from'" in text or ' from"' in text
```

### Go: GoTrivialAnalyzer

**Файлы для анализа**: `doc.go`

**Критерии тривиальности**:

1. **Только package declaration и комментарии**:
   - `package name`
   - Package-level documentation comments

```python
# lg/adapters/langs/go/trivial.py

class GoTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial Go doc.go files."""

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        if ctx.filename != "doc.go":
            return False

        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_doc_file(doc)

    def _analyze_doc_file(self, doc) -> bool:
        """Analyze doc.go for triviality."""
        root = doc.root_node

        for child in root.children:
            node_type = child.type

            # Allow package clause and comments
            if node_type in ("package_clause", "comment"):
                continue

            # Anything else = non-trivial
            return False

        return True
```

### Rust: RustTrivialAnalyzer

**Файлы для анализа**: `mod.rs`, `lib.rs`

**Критерии тривиальности**:

1. **Только mod declarations**:
   - `pub mod name;`
   - `mod name;`
   - `pub use ...;` (re-exports)

```python
# lg/adapters/langs/rust/trivial.py

class RustTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial Rust mod.rs/lib.rs files."""

    TRIVIAL_FILENAMES = {"mod.rs", "lib.rs"}

    ALLOWED_TYPES = {
        "mod_item",        # mod declarations
        "use_declaration", # use/re-exports
        "attribute_item",  # #[...] attributes
        "line_comment",
        "block_comment",
    }

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        if ctx.filename not in self.TRIVIAL_FILENAMES:
            return False

        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_mod_file(doc)

    def _analyze_mod_file(self, doc) -> bool:
        """Analyze mod.rs/lib.rs for triviality."""
        root = doc.root_node

        for child in root.children:
            if child.type not in self.ALLOWED_TYPES:
                return False

        return True
```

### C/C++: Header Guard Only Files

**Файлы для анализа**: `.h`, `.hpp`

**Критерии тривиальности**:

1. **Только include guards и forward declarations**:
   - `#ifndef`, `#define`, `#endif`
   - Forward declarations: `class Foo;`, `struct Bar;`

```python
# lg/adapters/langs/cpp/trivial.py

class CppTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial C++ header files."""

    ALLOWED_TYPES = {
        "preproc_ifdef",
        "preproc_ifndef",
        "preproc_def",
        "preproc_endif",
        "preproc_include",
        "comment",
        "declaration",  # Forward declarations
    }

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        # Only analyze headers
        if ctx.ext not in ("h", "hpp", "hh", "hxx"):
            return False

        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_header(doc)

    def _analyze_header(self, doc) -> bool:
        """Analyze header for triviality."""
        root = doc.root_node

        has_content = False

        for child in root.children:
            node_type = child.type

            if node_type not in self.ALLOWED_TYPES:
                return False

            # Forward declaration check
            if node_type == "declaration":
                if not self._is_forward_declaration(child, doc):
                    return False
                has_content = True

        # Empty headers are trivial
        return True

    def _is_forward_declaration(self, node, doc) -> bool:
        """Check if declaration is a forward declaration."""
        text = doc.get_node_text(node).strip()
        # Forward declaration ends with ; without body
        return text.endswith(";") and "{" not in text
```

### Kotlin: PackageInfoAnalyzer

**Файлы для анализа**: файлы только с `package` и аннотациями

```python
# lg/adapters/langs/kotlin/trivial.py

class KotlinTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial Kotlin files."""

    ALLOWED_TYPES = {
        "package_header",
        "import_header",
        "annotation",
        "comment",
        "multiline_comment",
    }

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_file(doc)

    def _analyze_file(self, doc) -> bool:
        """Analyze Kotlin file for triviality."""
        root = doc.root_node

        for child in root.children:
            if child.type not in self.ALLOWED_TYPES:
                return False

        return True
```

### Java: PackageInfoAnalyzer

**Файлы для анализа**: `package-info.java`

```python
# lg/adapters/langs/java/trivial.py

class JavaTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial Java package-info files."""

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        if ctx.filename != "package-info.java":
            return False

        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_package_info(doc)

    def _analyze_package_info(self, doc) -> bool:
        """Analyze package-info.java for triviality."""
        root = doc.root_node

        ALLOWED = {"package_declaration", "comment", "annotation"}

        for child in root.children:
            if child.type not in ALLOWED:
                return False

        return True
```

### Scala: PackageObjectAnalyzer

**Файлы для анализа**: `package.scala` (пустые package objects)

```python
# lg/adapters/langs/scala/trivial.py

class ScalaTrivialAnalyzer(TrivialFileAnalyzer):
    """Detect trivial Scala package objects."""

    def is_trivial(self, ctx: LightweightContext, adapter) -> bool:
        if ctx.filename != "package.scala":
            return False

        doc = adapter.create_document(ctx.raw_text, ctx.ext)
        return self._analyze_package_object(doc)

    def _analyze_package_object(self, doc) -> bool:
        """Analyze package.scala for triviality."""
        # Check if package object has only imports and type aliases
        root = doc.root_node

        ALLOWED = {"package_clause", "import_declaration", "comment"}

        for child in root.children:
            if child.type == "package_object":
                # Check package object body
                body = child.child_by_field_name("body")
                if body and self._has_non_trivial_members(body):
                    return False
                continue

            if child.type not in ALLOWED:
                return False

        return True
```

---

## Конфигурация

### Глобальная опция

Пропуск тривиальных файлов включён по умолчанию. При необходимости можно отключить:

```yaml
api-module:
  extensions: [".py", ".ts"]

  # Disable trivial file skipping (default: true)
  skip_trivial_files: false
```

### Модель конфигурации

```python
@dataclass
class CodeCfg:
    # ... other fields ...
    skip_trivial_files: bool = True  # Enable trivial file detection
```

### Поведение по умолчанию

- **Включено**: тривиальные файлы автоматически пропускаются
- Каждый язык определяет свои критерии тривиальности
- Решение принимается на основе AST-анализа, не эвристик по имени

---

## Интеграция в pipeline

### Точка вызова

`should_skip()` вызывается в `processor.py` **до** парсинга и обработки файла:

```python
# lg/adapters/processor.py

def process_files(plan: SectionPlan, template_ctx: TemplateContext) -> List[ProcessedFile]:
    processed_files = []

    for file_entry in plan.files:
        # ... adapter binding ...

        # Create lightweight context
        lightweight_ctx = LightweightContext(
            file_path=fp,
            raw_text=raw_text,
            group_size=total_files,
            template_ctx=template_ctx,
            file_label=file_label
        )

        # Early skip check - BEFORE full processing
        if adapter.name != "base" and adapter.should_skip(lightweight_ctx):
            continue  # Skip this file entirely

        # ... rest of processing ...
```

### Производительность

1. **Lightweight analysis** — используем `LightweightContext` без полного парсинга когда возможно
2. **Lazy document creation** — `TreeSitterDocument` создаётся только если нужен AST-анализ
3. **Early exit** — проверка имени файла до парсинга
4. **No caching needed** — решение принимается один раз за файл

---

## Тестирование

### Структура тестов

Тесты тривиальных файлов следуют стандартной структуре проекта:

```
tests/adapters/
├── python/
│   ├── conftest.py                  # Фикстуры для загрузки образцов
│   ├── test_trivial_files.py        # Тесты пропуска тривиальных файлов
│   └── goldens/
│       └── do/                      # Входные образцы (стандартная папка)
│           ├── trivial_init_empty.py
│           ├── trivial_init_reexports.py
│           └── non_trivial_init.py
│
├── typescript/
│   ├── conftest.py
│   ├── test_trivial_files.py
│   └── goldens/
│       └── do/
│           ├── trivial_barrel.ts
│           └── non_trivial_barrel.ts
│
├── go/
│   ├── conftest.py
│   ├── test_trivial_files.py
│   └── goldens/
│       └── do/
│           ├── trivial_doc.go
│           └── non_trivial_doc.go
│
└── rust/
    ├── conftest.py
    ├── test_trivial_files.py
    └── goldens/
        └── do/
            ├── trivial_mod.rs
            └── non_trivial_mod.rs
```

### Загрузка образцов через conftest.py

Образцы загружаются через фикстуры в `conftest.py` каждого языка:

```python
# tests/adapters/python/conftest.py

import pytest
from ..golden_utils import load_sample_code


@pytest.fixture
def do_trivial_init_empty():
    """Empty __init__.py file."""
    return load_sample_code("trivial_init_empty")


@pytest.fixture
def do_trivial_init_reexports():
    """__init__.py with only re-exports."""
    return load_sample_code("trivial_init_reexports")


@pytest.fixture
def do_non_trivial_init():
    """__init__.py with function definitions."""
    return load_sample_code("non_trivial_init")
```

```python
# tests/adapters/typescript/conftest.py

import pytest
from ..golden_utils import load_sample_code


@pytest.fixture
def do_trivial_barrel():
    """Barrel file with only re-exports."""
    return load_sample_code("trivial_barrel")


@pytest.fixture
def do_non_trivial_barrel():
    """Barrel file with definitions."""
    return load_sample_code("non_trivial_barrel")
```

### Подход к тестированию

В отличие от других оптимизаций, тесты тривиальных файлов **не используют golden files** для результатов (файл пропускается полностью). Вместо этого:

1. **Фикстуры** загружают образцы из `goldens/do/`
2. **Unit-тесты** проверяют `is_trivial()` методы
3. **Assertions** на boolean результат

```python
# tests/adapters/python/test_trivial_files.py

from pathlib import Path
from lg.adapters.langs.python import PythonCfg
from lg.adapters.langs.python.trivial import PythonTrivialAnalyzer
from .utils import lctx, make_adapter


class TestPythonTrivialFiles:
    """Test trivial __init__.py detection."""

    def test_empty_init_is_trivial(self, do_trivial_init_empty):
        """Empty __init__.py should be skipped."""
        analyzer = PythonTrivialAnalyzer()
        adapter = make_adapter(PythonCfg())

        ctx = lctx(do_trivial_init_empty, Path("/pkg/__init__.py"))
        assert analyzer.is_trivial(ctx, adapter) is True

    def test_reexports_only_is_trivial(self, do_trivial_init_reexports):
        """__init__.py with only re-exports is trivial."""
        analyzer = PythonTrivialAnalyzer()
        adapter = make_adapter(PythonCfg())

        ctx = lctx(do_trivial_init_reexports, Path("/pkg/__init__.py"))
        assert analyzer.is_trivial(ctx, adapter) is True

    def test_with_function_is_not_trivial(self, do_non_trivial_init):
        """__init__.py with function definition is not trivial."""
        analyzer = PythonTrivialAnalyzer()
        adapter = make_adapter(PythonCfg())

        ctx = lctx(do_non_trivial_init, Path("/pkg/__init__.py"))
        assert analyzer.is_trivial(ctx, adapter) is False

    def test_non_init_file_not_checked(self, do_trivial_init_reexports):
        """Non-__init__.py files are never trivial."""
        analyzer = PythonTrivialAnalyzer()
        adapter = make_adapter(PythonCfg())

        # Same content but different filename
        ctx = lctx(do_trivial_init_reexports, Path("/pkg/utils.py"))
        assert analyzer.is_trivial(ctx, adapter) is False
```

```python
# tests/adapters/typescript/test_trivial_files.py

from pathlib import Path
from lg.adapters.langs.typescript import TypeScriptCfg
from lg.adapters.langs.typescript.trivial import TypeScriptTrivialAnalyzer
from .utils import lctx, make_adapter


class TestTypeScriptTrivialFiles:
    """Test trivial barrel file detection."""

    def test_barrel_with_reexports_is_trivial(self, do_trivial_barrel):
        """index.ts with only re-exports is trivial."""
        analyzer = TypeScriptTrivialAnalyzer()
        adapter = make_adapter(TypeScriptCfg())

        ctx = lctx(do_trivial_barrel, Path("/src/components/index.ts"))
        assert analyzer.is_trivial(ctx, adapter) is True

    def test_barrel_with_definitions_is_not_trivial(self, do_non_trivial_barrel):
        """index.ts with function definitions is not trivial."""
        analyzer = TypeScriptTrivialAnalyzer()
        adapter = make_adapter(TypeScriptCfg())

        ctx = lctx(do_non_trivial_barrel, Path("/src/components/index.ts"))
        assert analyzer.is_trivial(ctx, adapter) is False

    def test_non_index_file_not_checked(self, do_trivial_barrel):
        """Non-index.ts files are never trivial."""
        analyzer = TypeScriptTrivialAnalyzer()
        adapter = make_adapter(TypeScriptCfg())

        ctx = lctx(do_trivial_barrel, Path("/src/components/exports.ts"))
        assert analyzer.is_trivial(ctx, adapter) is False
```

### Примеры файлов-образцов

```python
# tests/adapters/python/goldens/do/trivial_init_empty.py

"""Package docstring."""
```

```python
# tests/adapters/python/goldens/do/trivial_init_reexports.py

"""Package with re-exports only."""

from .module import func
from .other import Class, helper
from .utils import *

__all__ = ["func", "Class", "helper"]
```

```python
# tests/adapters/python/goldens/do/non_trivial_init.py

"""Package with actual code."""

from .module import func


def package_helper():
    """Helper function defined in __init__."""
    return func() + 1
```

```typescript
// tests/adapters/typescript/goldens/do/trivial_barrel.ts

export { Component } from './Component';
export { useHook } from './hooks';
export * from './types';
export type { Config } from './config';
```

```typescript
// tests/adapters/typescript/goldens/do/non_trivial_barrel.ts

export { Component } from './Component';

// This function makes the barrel non-trivial
export function createComponent(props: Props): Component {
    return new Component(props);
}
```

### Совместимость с test_adapters.sh

Тесты доступны через стандартный раннер:

```bash
# Запуск тестов тривиальных файлов для Python
./scripts/test_adapters.sh trivial_files python

# Запуск для TypeScript
./scripts/test_adapters.sh trivial_files typescript

# Запуск для всех языков
./scripts/test_adapters.sh trivial_files all

# Запуск вместе с другими оптимизациями
./scripts/test_adapters.sh trivial_files,imports python
```

---

## План реализации

### Этапы

1. **Базовая инфраструктура**
   - Создать `lg/adapters/optimizations/trivial_files/`
   - Реализовать базовый класс `TrivialFileAnalyzer`

2. **Языковые анализаторы**
   - Python: `PythonTrivialAnalyzer` для `__init__.py`
   - TypeScript: `TypeScriptTrivialAnalyzer` для barrel-файлов
   - JavaScript: `JavaScriptTrivialAnalyzer` для barrel-файлов
   - Go: `GoTrivialAnalyzer` для `doc.go`
   - Rust: `RustTrivialAnalyzer` для `mod.rs`, `lib.rs`
   - C/C++: `CppTrivialAnalyzer` для header-only файлов
   - Kotlin: `KotlinTrivialAnalyzer` для package-info
   - Java: `JavaTrivialAnalyzer` для `package-info.java`
   - Scala: `ScalaTrivialAnalyzer` для `package.scala`

3. **Тестирование**
   - Создать образцы файлов в `goldens/do/`
   - Добавить фикстуры в `conftest.py`
   - Написать тесты для каждого языка

4. **Документация**
   - Обновить `docs/en/adapters.md`
   - Добавить примеры конфигурации

---

## Итоги

### Ключевые принципы

1. **Раннее решение** — skip до парсинга и обработки
2. **Языковая специфика** — каждый язык знает свои тривиальные паттерны
3. **Консервативность** — при сомнениях НЕ пропускаем файл
4. **Унификация** — единый механизм вместо разрозненных опций
5. **Тестируемость** — простые unit-тесты на boolean результат

### Преимущества архитектуры

- **Модульность** — легко добавить новый язык
- **Расширяемость** — можно добавить более сложные паттерны
- **Производительность** — минимальные затраты на анализ
- **Совместимость** — интегрируется в существующий pipeline
