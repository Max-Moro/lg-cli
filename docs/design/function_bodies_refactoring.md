# Function Body Optimization Refactoring

## Executive Summary

This document describes the architectural refactoring of the **Function Body Optimization** subsystem in Listing Generator language adapters. The goal is to bring it up to the level of other optimization subsystems (comments, literals) while implementing new functional requirements.

---

## 1. Current State Analysis

### 1.1 Existing Implementation

The current implementation is located in a single file `lg/adapters/optimizations/function_bodies.py` (~145 lines) containing:

- `FunctionBodyOptimizer` class with all logic
- Static methods for body removal
- Policy evaluation in `should_strip_function_body()`

**Problems:**
1. **Monolithic structure** - all logic in one class
2. **Inconsistent policy naming** - `none`, `all`, `large_only` vs. comment's `keep_all`, `strip_all`
3. **`large_only` mode** is a special case that should be orthogonal to main policy
4. **`public_only` mode** - semantically questionable (why strip only public?)
5. **No support for `max_tokens` trimming** - unlike comments
6. **`except_patterns` and `keep_annotated`** - declared in config but not implemented

### 1.2 Configuration Model (current)

```python
FunctionBodyStrip = Literal["none", "all", "public_only", "non_public", "large_only"]

@dataclass
class FunctionBodyConfig:
    mode: FunctionBodyStrip = "none"
    min_lines: int = 5
    except_patterns: List[str] = field(default_factory=list)  # NOT IMPLEMENTED
    keep_annotated: List[str] = field(default_factory=list)   # NOT IMPLEMENTED
```

### 1.3 Test Coverage

Existing tests cover:
- Basic stripping (`strip_function_bodies=True`)
- `large_only` mode
- `public_only` and `non_public` modes
- Docstring preservation (Python-specific)
- Edge cases (single-line, nested functions)

10 languages have golden tests for function_bodies.

---

## 2. New Requirements

### 2.1 Policy Changes

| Old Policy | New Policy | Behavior |
|------------|------------|----------|
| `none` | `keep_all` | Keep all function bodies |
| `all` | `strip_all` | Strip all function bodies |
| `non_public` | `keep_public` | Keep public, strip private |
| `public_only` | **REMOVED** | — |
| `large_only` | **REMOVED** | Replaced by `max_tokens` |

### 2.2 New Features

#### 2.2.1 Token-based Trimming (`max_tokens`)

Replace `min_lines` with optional `max_tokens`:
- If specified, trim function body to fit token budget
- If trimming occurs mid-line, remove the incomplete line
- Works **in addition** to any base policy

#### 2.2.2 Exception Patterns (`except_patterns`)

Regex patterns for function names that should **never** be stripped:
```yaml
except_patterns: ["^__init__", "^main$", "^test_"]
```

#### 2.2.3 Annotation-based Preservation (`keep_annotated`)

Regex patterns for decorators/annotations that preserve function bodies:
```yaml
keep_annotated: ["@important", "@critical", "@preserve"]
```

### 2.3 Configuration Model (new)

```python
FunctionBodyPolicy = Literal["keep_all", "strip_all", "keep_public"]

@dataclass
class FunctionBodyConfig:
    policy: FunctionBodyPolicy = "keep_all"
    max_tokens: Optional[int] = None
    except_patterns: List[str] = field(default_factory=list)
    keep_annotated: List[str] = field(default_factory=list)
```

---

## 3. Architecture Design

### 3.1 Package Structure

```
lg/adapters/optimizations/function_bodies/
├── __init__.py          # Public API exports
├── optimizer.py         # Main FunctionBodyOptimizer class
├── decision.py          # Decision model (FunctionBodyDecision)
├── evaluators.py        # Policy evaluators
└── trimmer.py           # Token-based body trimming
```

### 3.2 Component Responsibilities

#### 3.2.1 `decision.py` - Decision Model

```python
@dataclass
class FunctionBodyDecision:
    """Decision about function body processing."""
    action: Literal["keep", "strip", "trim"]
    max_tokens: Optional[int] = None  # For "trim" action
```

Simple model - less complex than comments because function bodies don't need "transform with replacement" semantics.

#### 3.2.2 `evaluators.py` - Policy Evaluators

```python
class ExceptPatternEvaluator:
    """Check if function name matches except_patterns."""
    def evaluate(self, func_name: str, ...) -> Optional[FunctionBodyDecision]

class KeepAnnotatedEvaluator:
    """Check if function has preservation annotations."""
    def evaluate(self, decorators: List[Node], ...) -> Optional[FunctionBodyDecision]

class BasePolicyEvaluator:
    """Apply base policy (keep_all, strip_all, keep_public)."""
    def evaluate(self, in_public_api: bool, ...) -> Optional[FunctionBodyDecision]
```

Evaluator chain:
1. `ExceptPatternEvaluator` - pattern-based preservation (commutative with #2)
2. `KeepAnnotatedEvaluator` - annotation-based preservation (commutative with #1)
3. `BasePolicyEvaluator` - default policy application (fallback)

#### 3.2.3 `trimmer.py` - Token-based Trimming

```python
class FunctionBodyTrimmer:
    """Trim function body to token budget."""

    def trim(
        self,
        body_text: str,
        max_tokens: int,
        tokenizer: TokenService
    ) -> tuple[str, bool]:
        """
        Trim body to fit token budget.

        Returns:
            Tuple of (trimmed_text, was_trimmed)
        """
```

Post-processor that applies after decision is made:
- Only activates when `max_tokens` is set
- Works with "keep" and "strip" decisions
- For "keep" + max_tokens: trim if body exceeds budget
- For "strip": no trimming needed (full removal)

#### 3.2.4 `optimizer.py` - Main Orchestrator

```python
class FunctionBodyOptimizer:
    """Main optimizer coordinating all components."""

    def __init__(self, adapter):
        self.adapter = adapter

    def apply(self, context: ProcessingContext, cfg: Union[bool, FunctionBodyConfig]):
        """Apply function body optimization."""
        # 1. Normalize config
        # 2. Create evaluator pipeline
        # 3. Iterate functions
        # 4. Make decisions
        # 5. Apply trimming if needed
        # 6. Execute removals
```

### 3.3 Decision Flow

```
┌─────────────────────┐
│   Function Found    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ ExceptPatternEval   │──► Match? → keep
│        OR           │   (both check for preservation,
│ KeepAnnotatedEval   │──► Match? → keep   order doesn't matter)
└──────────┬──────────┘
           │ No match
           ▼
┌─────────────────────┐
│ BasePolicyEval      │──► keep_all → keep
│                     │──► strip_all → strip
│                     │──► keep_public + public → keep
│                     │──► keep_public + private → strip
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ MaxTokensTrimmer    │──► keep + exceeds? → trim
│ (post-processor)    │──► strip → no change
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Apply Decision    │
└─────────────────────┘
```

### 3.4 Comparison with Comments Architecture

| Aspect | Comments | Function Bodies |
|--------|----------|-----------------|
| Decision actions | keep, remove, transform | keep, strip, trim |
| Evaluator count | 3 (strip, keep, base) | 3 (except, annotated, base) |
| Post-processor | MaxTokensTransformer | FunctionBodyTrimmer |
| Language-specific | CommentAnalyzer | Uses CodeAnalyzer |
| Complexity | High (grouping, styles) | Medium |

**Key differences:**
- Function bodies use existing `CodeAnalyzer` infrastructure
- No need for language-specific "function analyzer" classes
- Simpler decision model (no "transform with replacement")
- Trimming is simpler than comment truncation (no style preservation needed)

---

## 4. Migration Strategy

### 4.1 Phase 1: Package Structure (Non-breaking)

**Goal:** Create new package structure without changing behavior.

**Steps:**
1. Create `lg/adapters/optimizations/function_bodies/` directory
2. Move existing code to `optimizer.py`
3. Create `__init__.py` with same public API
4. Update imports in `lg/adapters/optimizations/__init__.py`
5. Run all tests - should pass with no changes

**Risk:** Low - pure refactoring
**Tests:** All existing tests must pass

### 4.2 Phase 2: Policy Renaming (Breaking)

**Goal:** Rename policies to new naming convention.

**Steps:**
1. Update `FunctionBodyStrip` type alias:
   - `none` → `keep_all`
   - `all` → `strip_all`
   - `non_public` → `keep_public`
   - Remove `public_only` and `large_only`
2. Rename `mode` to `policy` in `FunctionBodyConfig`
3. Update `general_load()` in `CodeCfg`
4. Update `BasePolicyEvaluator` logic
5. Update all tests and golden files

**Risk:** Medium - breaking change for existing configs
**Tests:** Update test configs, regenerate goldens

### 4.3 Phase 3: Decision Architecture

**Goal:** Introduce decision model and evaluator chain.

**Steps:**
1. Create `decision.py` with `FunctionBodyDecision`
2. Create `evaluators.py` with three evaluators
3. Refactor `optimizer.py` to use evaluator chain
4. Remove `should_strip_function_body()` method
5. Add tests for each evaluator

**Risk:** Medium - internal refactoring
**Tests:** Add unit tests for evaluators

### 4.4 Phase 4: Exception Patterns + Annotation Preservation

**Goal:** Implement `except_patterns` and `keep_annotated` functionality.

**Steps:**
1. Implement `ExceptPatternEvaluator`
2. Implement `KeepAnnotatedEvaluator`
3. Use `CodeAnalyzer.find_decorators_for_element()` for annotations
4. Add both to evaluator chain
5. Add tests for pattern and annotation matching

**Risk:** Low - additive features
**Tests:** New test cases for both features

### 4.5 Phase 5: Token-based Trimming

**Goal:** Implement `max_tokens` trimming.

**Steps:**
1. Create `trimmer.py` with `FunctionBodyTrimmer`
2. Implement line-aware trimming logic
3. Integrate into optimizer as post-processor
4. Remove `min_lines` parameter
5. Add tests for trimming behavior

**Risk:** Medium - replaces `min_lines` functionality
**Tests:** New tests for `max_tokens`, update `large_only` tests

---

## 5. Testing Strategy

### 5.1 Test Categories

1. **Unit tests** (new)
   - `test_evaluators.py` - individual evaluator logic
   - `test_trimmer.py` - trimming algorithm
   - `test_decision.py` - decision model

2. **Integration tests** (existing + new)
   - `test_function_bodies.py` per language
   - Golden tests for all configurations

3. **Regression tests**
   - All existing golden tests must pass after Phase 1
   - Golden regeneration in Phase 2

### 5.2 Golden Test Updates

| Phase | Golden Changes |
|-------|----------------|
| 1 | None |
| 2 | Regenerate with new policy names |
| 3 | None (same behavior) |
| 4-5 | Add new golden files for new features |

---

## 6. File Changes Summary

### New Files
```
lg/adapters/optimizations/function_bodies/__init__.py
lg/adapters/optimizations/function_bodies/optimizer.py
lg/adapters/optimizations/function_bodies/decision.py
lg/adapters/optimizations/function_bodies/evaluators.py
lg/adapters/optimizations/function_bodies/trimmer.py
```

### Modified Files
```
lg/adapters/optimizations/__init__.py        # Update imports
lg/adapters/code_model.py                    # Policy type + config changes
lg/adapters/code_base.py                     # Minor updates if needed
tests/adapters/*/test_function_bodies.py     # Test updates
tests/adapters/*/goldens/function_bodies/*   # Golden updates
```

### Deleted Files
```
lg/adapters/optimizations/function_bodies.py # Replaced by package
```

---

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Golden test failures | Medium | Phase-by-phase regeneration |
| Complex trimming edge cases | Medium | Extensive unit tests |
| Language-specific issues | Medium | Test all 10 languages each phase |

---

## 8. Implementation Status

### Completed:

- [x] **Phase 1**: Package structure created
- [x] **Phase 2**: Policy renaming + config model updated
- [x] **Phase 3-4**: Decision architecture + evaluators implemented
- [x] **Phase 5**: Token-based trimming (max_tokens) implemented
- [x] **Phase 6**: Architecture refinement - `strippable_range` replaces `protected_content`
- [x] **Tests**: All 97 function_bodies tests pass across 10 languages
- [x] **Goldens updated**: All golden files regenerated with correct indentation

### Key Architectural Decisions:

#### Strippable Range (final architecture)

Instead of multiple fields (`protected_content`, `effective_body_start_byte`), we use a single unified `strippable_range`:

```python
@dataclass(frozen=True)
class FunctionGroup:
    definition: Node
    element_info: ElementInfo
    name_node: Optional[Node] = None
    body_node: Optional[Node] = None
    # Byte range for stripping (start_byte, end_byte)
    strippable_range: Tuple[int, int] = (0, 0)
```

- `CodeAnalyzer.compute_strippable_range(func_def, body_node)` returns `(body_node.start_byte, body_node.end_byte)` by default
- `PythonCodeAnalyzer` overrides to handle docstrings and leading comments
- `KotlinCodeAnalyzer` overrides to handle KDoc inside function body
- Optimizer simply uses `strippable_range` - all language complexity is encapsulated in analyzers

#### Files Created/Modified:

**New package:**
```
lg/adapters/optimizations/function_bodies/
├── __init__.py
├── optimizer.py      # Main orchestrator using strippable_range
├── decision.py       # FunctionBodyDecision(action, max_tokens)
├── evaluators.py     # ExceptPatternEvaluator, KeepAnnotatedEvaluator, BasePolicyEvaluator
└── trimmer.py        # FunctionBodyTrimmer for max_tokens
```

**Modified:**
- `lg/adapters/code_model.py` - FunctionBodyPolicy, FunctionBodyConfig
- `lg/adapters/code_analysis.py` - FunctionGroup.strippable_range, compute_strippable_range()
- `lg/adapters/python/code_analysis.py` - compute_strippable_range() for docstrings + leading comments
- `lg/adapters/kotlin/code_analysis.py` - compute_strippable_range() for KDoc
- `lg/adapters/kotlin/adapter.py` - removed hook

**Deleted:**
- `lg/adapters/kotlin/function_bodies.py` - replaced by compute_strippable_range()

---

## 9. Definition of Done

- [x] All 5 phases completed
- [x] All function_bodies tests pass (97/97)
- [x] New tests for all new features
- [x] Documentation updated
- [x] No regressions in function_bodies golden tests
- [ ] Code review passed

---

## Appendix A: Configuration Examples

### A.1 Simple Usage
```yaml
python:
  strip_function_bodies: true  # Equivalent to strip_all policy
```

### A.2 Keep Public API
```yaml
python:
  strip_function_bodies:
    policy: "keep_public"
```

### A.3 Full Configuration
```yaml
python:
  strip_function_bodies:
    policy: "strip_all"
    max_tokens: 50
    except_patterns: ["^__init__", "^main$"]
    keep_annotated: ["@critical", "@api"]
```

### A.4 Token Budget Only
```yaml
python:
  strip_function_bodies:
    policy: "keep_all"
    max_tokens: 100  # Trim large bodies, keep small ones
```
