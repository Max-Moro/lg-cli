# Literal Optimization v2 Refactoring

> Memory file for tracking the large-scale refactoring of the literal optimization subsystem.
> **Last updated**: 2025-12-04 (Session 4: Code review fixes - formatter refactoring, Priority 3 complete)

---

## Introduction and Motivation

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

## Development Methodology

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

## Current Status and Roadmap

### Current Status

**Phase**: Java migration DONE — Python, JS, TS, Java all fully migrated with two-pass optimization
**Last work session**: 2025-12-04 — Java factory calls, two-pass optimization, range edits composition, critical bug fixes

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

### Two-Pass Optimization for String-Collection Independence ✅ IMPLEMENTED

When a collection contains string literals, we want to optimize BOTH:
1. Individual string literals (truncation with "…")
2. The collection structure itself (removing elements)

**Problem**: If we optimize strings first and save their edits, then optimize the collection (which replaces the entire range), the string edits are lost.

**Solution**: Two-phase approach with composable edits:

#### Pass 1: String Literals (Independent Processing)
- Process ALL string literals independently of their context
- Apply string truncation edits immediately
- Track ranges of processed strings for Pass 2 coordination

#### Pass 2: Collections with DFS (Composing with Pass 1)
- Process top-level collections (not nested inside others)
- DFS handles nested structures internally
- **Use composable edits** to preserve string optimizations from Pass 1

**Example result** (JavaScript object with nested string and structure optimization):
```javascript
const config = {
    apiKey: "this is a very l…", // literal string
    timeout: 5000
};
```

**Implementation:**
- `core.py` — `optimize()` method implements two-pass pipeline:
  - Pass 0: Identify collections vs strings
  - Pass 1: Process all strings independently
  - Pass 2: Process top-level collections with DFS + composing
- `handler.py` — `_apply_trim_result_composing()` uses composable edit method
- Coordination via `processed_strings` list to avoid conflicts

### Range Edits Composition System ✅ IMPLEMENTED

Extended `lg/adapters/range_edits.py` to support **composable nested edits**.

**Problem**: When wide edit (e.g., collection replacement) contains narrow edits (e.g., string truncations), the standard "wider edit wins" policy loses the narrow edits.

**Solution**: New method `add_replacement_composing_nested()` that:
1. Finds all nested edits inside the wide edit range
2. Applies nested edits to the wide replacement text (with coordinate translation)
3. Removes absorbed nested edits
4. Adds the composed result as final replacement

**Key implementation details:**
- `add_replacement_composing_nested()` — Main composition method
- `_apply_nested_edits_to_text()` — Coordinate translation logic
  - Groups replacements with their following insertions
  - Applies groups to wide text by finding original substrings
  - Handles whitespace normalization for formatting mismatches
- Comprehensive test suite: `tests/adapters/test_range_edits_nested.py` (5 tests)

**Example** (from test suite):
```python
# Original
obj = {"key": "this is a very long string value"}

# Pass 1: String optimized
obj = {"key": "this is a very l…"} // literal string

# Pass 2: Object replaced (composing string edit)
obj = {"key": "this is a very l…"} // literal string (preserved!)
```

### Java Factory Calls Support ✅ IMPLEMENTED

Java uses factory methods like `List.of()`, `Map.of()` instead of literal syntax. This required new pattern features:

#### New Pattern Features

**1. `wrapper_match: Optional[str]`** (in `LiteralPattern`)
- Regex pattern to match factory call wrapper
- Example: `r"Map\.of"` matches `Map.of(...)` but not `List.of(...)`
- Used when multiple factory patterns share same Tree-Sitter type (`method_invocation`)

**2. `tuple_size: int`** (in `LiteralPattern`)
- Groups elements into tuples for Map.of semantics
- `Map.of(k1, v1, k2, v2)` → groups of 2 (key-value pairs)
- DFS respects tuple boundaries when trimming
- Default: 1 (no grouping)

#### Java Patterns Implemented

**List.of pattern:**
```python
JAVA_LIST_OF = LiteralPattern(
    category=LiteralCategory.FACTORY_CALL,
    tree_sitter_types=["method_invocation"],
    opening="(",
    closing=")",
    separator=",",
    wrapper_match=r"List\.of",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…"',
    min_elements=1,
)
```

**Map.of pattern:**
```python
JAVA_MAP_OF = LiteralPattern(
    category=LiteralCategory.FACTORY_CALL,
    tree_sitter_types=["method_invocation"],
    opening="(",
    closing=")",
    separator=",",
    wrapper_match=r"Map\.of",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template='"…", "…"',
    min_elements=1,
    tuple_size=2,  # Key-value pairs
)
```

**Map.ofEntries pattern:**
```python
JAVA_MAP_OF_ENTRIES = LiteralPattern(
    category=LiteralCategory.FACTORY_CALL,
    tree_sitter_types=["method_invocation"],
    opening="(",
    closing=")",
    separator=",",
    wrapper_match=r"Map\.ofEntries",
    placeholder_position=PlaceholderPosition.END,
    placeholder_template="Map.entry(…, …)",
    min_elements=1,
)
```

#### Implementation Details

**Pattern matching with wrapper:**
- `descriptor.py` — `get_pattern_for()` checks both `tree_sitter_type` AND `wrapper_match`
- `handler.py` — `_detect_wrapper_from_text()` extracts wrapper from source text
  - Fixed critical bug: Was returning everything before first `[` or `{` found ANYWHERE in text
  - Now correctly detects factory calls by checking if text STARTS with bracket

**Tuple grouping in DFS:**
- `selector.py` — `_select_dfs_tuples()` groups elements by `tuple_size`
- `selector.py` — `_group_into_tuples()` ensures balanced groups (pads if needed)
- `formatter.py` — Respects tuple boundaries in multiline formatting

**Example output** (Java Map.of with nested structure):
```java
Map<String, Object> nestedData = Map.of(
    "level1", Map.of(
        "level2", Map.of(
            "level3", "value"
            // … (1 more, −28 tokens)
        )
        // … (0 more, −28 tokens)
    )
    // … (0 more, −28 tokens)
);
```

### Debugging Complex Issues: Lessons Learned

#### Use Temporary Debug Scripts, Not Golden Tests

When deep debugging is needed:

✅ **Do**: Write standalone debug scripts
```python
# debug_issue.py
from lg.adapters.python import PythonCfg
from tests.adapters.python.utils import make_adapter, lctx

code = '''... minimal reproduction ...'''
cfg = PythonCfg()
cfg.literals.max_tokens = 40
adapter = make_adapter(cfg)
result, meta = adapter.process(lctx(code))
print(result)
```

❌ **Don't**: Repeatedly regenerate golden files for debugging
- Golden tests are for **final verification**, not iterative debugging
- Regenerating goldens repeatedly exhausts context window quickly
- Hard to track intermediate states

#### Add Recursion Depth Tracking for Nested Algorithms

When debugging recursive formatters:

```python
# At module level
_DEBUG_RECURSION_DEPTH = 0

# In recursive function
global _DEBUG_RECURSION_DEPTH
depth_prefix = "  " * _DEBUG_RECURSION_DEPTH
_DEBUG_RECURSION_DEPTH += 1
try:
    print(f"{depth_prefix}Entering function [depth={_DEBUG_RECURSION_DEPTH}]")
    # ... function body ...
finally:
    _DEBUG_RECURSION_DEPTH -= 1
```

This prevents output from different recursion levels from being mixed/confused.

#### Verify Object Identity When Strings Behave Strangely

When a string appears to change size mysteriously:
```python
print(f"Type: {type(obj).__name__}, id: {id(obj)}, len: {len(obj)}")
print(f"Is same object: {obj1 is obj2}")
```

In our case, this revealed that `parsed.wrapper` (which should be None or "Map.of") contained the entire unoptimized text due to the wrapper detection bug.

#### Check Both Selector AND Formatter Output

Don't assume formatter is correct if selector works:
- Selector may correctly select elements: `kept=1/2, removed=1`
- But formatter might still produce wrong output if it uses wrong data

Add debug output at BOTH stages:
```python
# After selection
print(f"Selection: kept={len(kept)}, removed={len(removed)}")

# After formatting
print(f"Formatted output: {len(result)} chars")
```

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
| Python | ✅ DONE | 19 passed, 2 skipped | MIDDLE_COMMENT for dicts, f-string interpolation, two-pass with composing |
| JavaScript | ✅ DONE | 19 passed | MIDDLE_COMMENT for objects, `${}` interpolation, two-pass with composing |
| TypeScript | ✅ DONE | 17 passed | Inherits JS patterns + TS object types, two-pass with composing |
| Java | ✅ DONE | 4 passed | Factory calls (List.of, Map.of, Map.ofEntries), wrapper_match, tuple_size=2 for Map.of |
| Kotlin | ⏸️ WAIT | - | Factory calls (listOf), `${}` and `$var` interpolation |
| Scala | ⏸️ WAIT | - | Factory calls, `${}` and `$var` interpolation |
| Go | ⏸️ WAIT | - | Composite literals, no interpolation |
| Rust | ⏸️ WAIT | - | vec![], `{}` format strings (unreliable detection) |
| C | ⏸️ WAIT | - | Array initializers, no interpolation |
| C++ | ⏸️ WAIT | - | Initializer lists, no interpolation |

### Key Achievements So Far

- **Two-pass optimization**: Independent string + collection optimization with composable edits (59 tests passing)
- **Range edits composition**: Nested edit preservation system for complex transformations (5 dedicated tests)
- **DFS-trimming**: Recursive optimization of nested structures preserving multiline layout
- **Java factory calls**: Full support for List.of, Map.of with wrapper_match and tuple_size
- **MIDDLE_COMMENT**: Inline `# … (N more, −M tokens)` inside collections
- **Context-aware comments**: Block vs single-line based on surrounding code
- **String interpolation boundaries**: Safe truncation that respects `${...}`, `{...}` boundaries
- **Declarative patterns**: ~60 lines for Python descriptor, ~120 lines for Java vs 300+ in old system
- **Clean separation**: Core knows nothing about specific languages

### Next Steps

1. **Continue language migration** with full DFS and two-pass support:
   - Kotlin (factory calls: listOf, mapOf — needs `${}` and `$var` interpolation, similar to Java)
   - Scala (factory calls — needs `${}` and `$var` interpolation)
   - Go (composite literals — no string interpolation)
   - Rust (vec![], macro calls — `{}` format strings unreliable to detect)
   - C, C++ (array/struct initializers — no string interpolation)

2. **Consider additional features** based on language needs:
   - Lazy evaluation for Scala (=> markers in pattern detection)
   - Macro detection improvements for Rust
   - String interpolation for Kotlin/Scala (reuse Java wrapper_match patterns)

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
