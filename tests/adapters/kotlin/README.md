# Kotlin Adapter Tests

This package contains a comprehensive test suite for the Kotlin language adapter in Listing Generator.

## Structure

```
tests/adapters/kotlin/
├── conftest.py                          # Fixtures and utilities for tests
├── goldens/                             # Golden files for tests
│   ├── do/                              # Original Kotlin code samples
│   │   ├── function_bodies.kt           # For testing function body removal
│   │   ├── comments.kt                  # For testing comment processing
│   │   ├── literals.kt                  # For testing literal optimization
│   │   ├── imports.kt                   # For testing import optimization
│   │   ├── public_api.kt                # For testing API filtering
│   │   └── budget_complex.kt            # For testing budgeting system
│   ├── function_bodies/                 # Reference results for functions
│   ├── comments/                        # Reference results for comments
│   ├── literals/                        # Reference results for literals
│   ├── imports/                         # Reference results for imports
│   ├── public_api/                      # Reference results for API
│   └── budget/                          # Reference results for budget
├── test_function_bodies.py              # Function body removal tests
├── test_comments.py                     # Comment processing tests
├── test_literals.py                     # Literal optimization tests
├── test_imports.py                      # Import optimization tests
├── test_public_api.py                   # Public API filtering tests
├── test_budget.py                       # Budgeting system tests
├── test_literal_comment_context.py      # Comment context tests
└── test_literals_indentation.py         # Literal indentation tests
```

## Test Types

### 1. Function Bodies Tests (`test_function_bodies.py`)
Tests function and method body removal:
- Basic function and method body removal
- "large_only" mode (removing only large functions)
- Lambda function handling
- Class structure preservation
- "public_only" mode
- KDoc preservation during body removal

### 2. Comments Tests (`test_comments.py`)
Tests comment processing policies:
- `keep_all` - keep all comments
- `strip_all` - remove all comments
- `keep_doc` - keep only KDoc
- `keep_first_sentence` - keep only first sentence
- Complex policies with custom settings

### 3. Literals Tests (`test_literals.py`)
Tests literal optimization (strings, arrays, objects):
- Trimming long string literals
- Optimizing large lists
- Optimizing large map structures
- Different token budgets (10, 20, etc.)

### 4. Imports Tests (`test_imports.py`)
Tests import optimization:
- `keep_all` - keep all imports
- `strip_local` - remove local imports
- `strip_external` - remove external imports
- `strip_all` - remove all imports
- Collapsing long import lists

### 5. Public API Tests (`test_public_api.py`)
Tests public API filtering:
- Removing private functions, methods, classes
- Preserving public elements
- Handling visibility modifiers
- Working with data classes and companion objects
- Annotation processing

### 6. Budget Tests (`test_budget.py`)
Tests token budgeting system:
- Progressive compression with decreasing budget
- Monotonic result size reduction
- Applying various optimization strategies

### 7. Literal Comment Context Tests (`test_literal_comment_context.py`)
Tests smart comment placement during literal optimization:
- Choosing between `//` and `/* */` depending on context
- Preventing syntax breakage

### 8. Literals Indentation Tests (`test_literals_indentation.py`)
Tests preserving correct indentation during literal optimization:
- Indentation in map structures
- Indentation in lists
- Indentation in nested structures

## Running Tests

```bash
# All Kotlin adapter tests
pytest tests/adapters/kotlin/

# Specific test suite
pytest tests/adapters/kotlin/test_function_bodies.py
pytest tests/adapters/kotlin/test_comments.py

# With golden file updates
PYTEST_UPDATE_GOLDENS=1 pytest tests/adapters/kotlin/test_function_bodies.py
```

## Golden Files

Golden files are reference results for comparison. They are located in the `goldens/` directory:

- `goldens/do/` - original code samples
- `goldens/*/` - reference results for various optimizations

### Updating Golden Files

When you change adapter logic and want to update references:

```bash
PYTEST_UPDATE_GOLDENS=1 pytest tests/adapters/kotlin/
```

## Creating New Tests

1. Add new code sample to `goldens/do/your_test.kt`
2. Create test file `test_your_feature.py`
3. Use fixtures from `conftest.py`:
   - `make_adapter(cfg)` - create adapter
   - `lctx_kt(code)` - create context for processing
   - `assert_golden_match()` - compare with reference
   - `load_sample_code()` - load code sample

Example:
```python
from .conftest import make_adapter, lctx_kt, assert_golden_match
from lg.adapters.kotlin import KotlinCfg

def test_my_feature():
    cfg = KotlinCfg(my_option=True)
    adapter = make_adapter(cfg)

    code = '''
    fun myFunction() {
        println("test")
    }
    '''

    result, meta = adapter.process(lctx_kt(code))

    assert "expected" in result
    assert_golden_match(result, "my_feature", "basic")
```

## Notes

- All tests use unified infrastructure from `tests/infrastructure/`
- Golden files automatically determine language by `.kt` extension
- Tests must be deterministic and reproducible
- When changing adapter output format, golden files must be updated

