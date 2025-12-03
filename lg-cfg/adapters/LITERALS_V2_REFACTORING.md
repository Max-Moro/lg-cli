# Literal Optimization v2 Refactoring

> Memory file for tracking the large-scale refactoring of the literal optimization subsystem.
> **Last updated**: 2025-12-03 (Session 2: Interpolation boundaries)

---

## Part 1: Introduction and Motivation

### Why This Refactoring?

The literal optimization subsystem has grown organically over time, with support for new languages added via incremental patches. This has led to significant architectural problems that make the codebase difficult to maintain and extend.

**Supported languages**: Python, JavaScript, TypeScript, Java, Kotlin, Scala, Go, Rust, C, C++

### Problems with the Current System

#### Problem 1: Core Biased Toward Python/TypeScript

The current core (`lg/adapters/optimizations/literals.py`) is heavily focused on Python and TypeScript because they were implemented first. The core "knows" too much about these languages, making it convenient only for similar languages and awkward for others.

#### Problem 2: Two Disconnected Hook Systems (Level 1 & Level 2)

Instead of a unified, well-designed pipeline, we have two independent hook subsystems that are barely connected. Developers must choose which system to use rather than having a coherent flow. This clearly indicates architectural drift — one system was created, then another was bolted on later.

#### Problem 3: Rigid Placeholder Positioning

The core always forces placeholders at the END of collections. But for some languages and structures, this is suboptimal. Sometimes a MIDDLE comment is more natural:

```go
var ErrorMessages = map[string]string{
    "VALIDATION_FAILED": "Input validation failed...",
    // … (5 more, −108 tokens)
}
```

Instead of the awkward:
```go
var ErrorMessages = map[string]string{
    "VALIDATION_FAILED": "Input validation failed...",
    "…": "…",
} // literal map (−108 tokens)
```

#### Problem 4: Tree-Sitter Structure Variations Not Handled

Different languages have different Tree-Sitter AST structures for similar concepts. The old system doesn't handle this cleanly, leading to hacks and workarounds.

#### Problem 5: Oversized Language Adapters

Each language adapter (`lg/adapters/<lang>/literals.py`) is ~300+ lines. This indicates the core isn't helping — languages prefer to use hooks and do everything themselves. Hooks are correct, but not when every adapter needs 300 lines of custom code. We need balance between universality and flexibility.

### Architecture Principles for v2

To avoid repeating these mistakes:

1. **Language-agnostic core**: The core must not know about specific languages. All language-specific logic belongs in handlers/descriptors.

2. **Declarative patterns**: Languages should declare their literal patterns (delimiters, separators, placeholder styles) rather than imperatively hooking into processing.

3. **Flexible placeholder positioning**: Support multiple positions (END, MIDDLE_COMMENT, INLINE) as first-class options.

4. **Single unified pipeline**: One clear processing flow, not multiple disconnected hook systems.

5. **Small language descriptors**: If a language adapter needs 300 lines, the architecture is wrong. Target: ~50-100 lines of declarative configuration.

### Reference: Existing Golden Files

We have working test samples for all languages to guide the new implementation:

- `tests/adapters/python/goldens/do/literals.py`
- `tests/adapters/javascript/goldens/do/literals.js`
- `tests/adapters/typescript/goldens/do/literals.ts`
- `tests/adapters/java/goldens/do/literals.java`
- `tests/adapters/kotlin/goldens/do/literals.kt`
- `tests/adapters/scala/goldens/do/literals.scala`
- `tests/adapters/go/goldens/do/literals.go`
- `tests/adapters/rust/goldens/do/literals.rs`
- `tests/adapters/c/goldens/do/literals.c`
- `tests/adapters/cpp/goldens/do/literals.cpp`



---

## Part 2: Development Methodology

### Testing Strategy

#### Running Tests

```bash
# Run tests for specific language
./scripts/test_adapters.sh literals python

# Run tests for multiple languages
./scripts/test_adapters.sh literals java,scala,go

# Run tests for all languages
./scripts/test_adapters.sh literals all
```

#### Working with Golden Files

Golden files are the source of truth. **Never trust just pass/fail** — always check the actual output.

```bash
# Regenerate golden files after changes
./scripts/test_adapters.sh literals python true

# Review what changed
git diff tests/adapters/python/goldens/literals/

# Accept changes if correct
git add tests/adapters/python/goldens/literals/
```

**Important**: When reviewing golden diffs, check for:
- Correct placeholder positioning
- Proper indentation preservation
- Accurate token counts in comments
- No broken syntax (comments in wrong places)

#### Debugging Literal Processing

When tests fail unexpectedly, write temporary debug scripts:

```python
# debug_literal.py
from lg.adapters.python import PythonCfg
from tests.adapters.python.utils import make_adapter, lctx

code = '''
config = {
    "key": "value",
    "another": "data"
}
'''

cfg = PythonCfg()
cfg.literals.max_tokens = 10
adapter = make_adapter(cfg)

result, meta = adapter.process(lctx(code))
print("=== RESULT ===")
print(result)
print("=== META ===")
print(meta)
```

### Context-Aware Comment Placement

When literal is followed by code on the same line, single-line comments break syntax:

```python
msg = "long..."; print(msg)  # ← Comment here breaks print()
```

**Solution**: Analyze context and use block comments when needed:
```python
msg = "long..." /* literal string */ ; print(msg)
```

This logic lives in `handler.py`, not in core — keeping core language-agnostic.

### Architecture Guidelines

1. **Don't add language-specific code to core** — use handlers/descriptors
2. **Test incrementally** — run tests after each change
3. **Check git diff for goldens** — visual review catches issues tests miss
4. **Keep descriptors declarative** — patterns, not procedures

---

## Part 3: Current Status and Roadmap

### Current Status

**Phase**: String interpolation boundaries DONE — Ready to continue language migration
**Last commit**: `1be3e35` - DFS-trimming for nested literal structures

### String Interpolation Boundaries ✅ IMPLEMENTED

When truncating strings with interpolation (f-strings, template literals), cutting inside `${...}` or `{...}` breaks AST:

```typescript
// BROKEN - cuts inside ${...}
`- Email: ${getUse…`

// CORRECT - extends to complete interpolator
`- Email: ${getUserEmail()}…`
```

**Implementation:**
- `categories.py` — Added `interpolation_markers: List[tuple]` to `LiteralPattern`
  - Format: `(prefix, opening, closing)` tuples
  - Examples: `("$", "{", "}")` for JS, `("", "{", "}")` for Python f-strings
- `handler.py` — `_get_active_interpolation_markers()` checks if markers apply to specific string
  - Python: only for f-strings (opening contains `f`/`F`)
  - JS/TS: only for template strings (backticks)
- `handler.py` — `_adjust_for_interpolation()` extends truncation to complete interpolators
- `handler.py` — `_find_interpolation_regions()` locates all interpolator boundaries
- `handler.py` — `_find_matching_brace()` handles nested braces inside interpolators

**Configured languages:**
- JavaScript/TypeScript: `[("$", "{", "}")]` for template strings
- Python: `[("", "{", "}")]` for f-strings (conditional on `f` prefix)

### DFS-Trimming for Nested Structures ✅ IMPLEMENTED

Recursive budget-aware trimming for nested literal structures. Instead of keeping or removing nested structures entirely, DFS descends into them and trims at each level.

**Result:**
```python
config = {
    "database": {
        "host": "localhost",
        # … (3 more, −38 tokens)
    },
    # … (2 more, −142 tokens)
}
```

**Implementation:**
- `parser.py` — `Element` extended with `nested_opening`, `nested_closing`, `nested_content`, `has_nested_structure`
- `selector.py` — `DFSSelection` dataclass + `select_dfs()` method with recursive budget tracking
- `formatter.py` — `format_dfs()` + `_reconstruct_element_with_nested()` with multiline/single-line awareness
- `handler.py` — `_process_collection_dfs()` integrates DFS into the pipeline

### v2 Core Architecture

```
lg/adapters/optimizations/literals_v2/
├── __init__.py      # Public exports
├── categories.py    # LiteralCategory, PlaceholderPosition, LiteralPattern
├── core.py          # LiteralOptimizerV2 - main entry point
├── descriptor.py    # LanguageLiteralDescriptor interface
├── formatter.py     # ResultFormatter - output formatting
├── handler.py       # LanguageLiteralHandler - processing pipeline
├── parser.py        # ElementParser - generic element parsing
└── selector.py      # BudgetSelector - budget-aware selection
```

### Language Descriptors

```
lg/adapters/<lang>/literals_v2.py  # Declarative pattern definitions
```

Example (Python):
```python
PYTHON_DICT = LiteralPattern(
    category=LiteralCategory.MAPPING,
    tree_sitter_types=["dictionary"],
    opening="{",
    closing="}",
    separator=",",
    kv_separator=":",
    placeholder_position=PlaceholderPosition.MIDDLE_COMMENT,
    comment_name="object",
)
```

### Migration Progress

| Language | Status | Tests | Notes |
|----------|--------|-------|-------|
| Python | ✅ DONE | 19 passed, 2 skipped | MIDDLE_COMMENT for dicts, f-string interpolation |
| JavaScript | ✅ DONE | 19 passed | MIDDLE_COMMENT for objects, `${}` interpolation |
| TypeScript | ✅ DONE | 17 passed | Inherits JS patterns + TS object types |
| Java | ⏸️ WAIT | - | Factory calls (List.of), no interpolation |
| Kotlin | ⏸️ WAIT | - | Factory calls (listOf), `${}` and `$var` interpolation |
| Scala | ⏸️ WAIT | - | Factory calls, `${}` and `$var` interpolation |
| Go | ⏸️ WAIT | - | Composite literals, no interpolation |
| Rust | ⏸️ WAIT | - | vec![], `{}` format strings (unreliable detection) |
| C | ⏸️ WAIT | - | Array initializers, no interpolation |
| C++ | ⏸️ WAIT | - | Initializer lists, no interpolation |

### Key Achievements So Far

- **DFS-trimming**: Recursive optimization of nested structures preserving multiline layout
- **MIDDLE_COMMENT**: Inline `# … (N more, −M tokens)` inside collections
- **Context-aware comments**: Block vs single-line based on surrounding code
- **String interpolation boundaries**: Safe truncation that respects `${...}`, `{...}` boundaries
- **Declarative patterns**: ~60 lines for Python descriptor vs 300+ in old system
- **Clean separation**: Core knows nothing about specific languages

### Next Steps

1. **Continue language migration** with full DFS support:
   - Java (factory calls: List.of, Map.of — no string interpolation)
   - Kotlin (factory calls: listOf, mapOf — needs `${}` and `$var` interpolation)
   - Scala (factory calls — needs `${}` and `$var` interpolation)
   - Go (composite literals — no string interpolation)
   - Rust (vec![], macro calls — `{}` format strings unreliable to detect)
   - C, C++ (array/struct initializers — no string interpolation)

---

## Quick Reference

```bash
# Test commands
./scripts/test_adapters.sh literals <lang>        # Run tests
./scripts/test_adapters.sh literals <lang> true   # Regenerate goldens
git diff tests/adapters/<lang>/goldens/literals/  # Review changes

# Key files
lg/adapters/optimizations/literals_v2/core.py     # Main optimizer
lg/adapters/optimizations/literals_v2/handler.py  # Language handler
lg/adapters/<lang>/literals_v2.py                 # Language patterns
```
