# Golden Tests System for Language Adapters

This system provides uniform testing of language adapters using golden files (reference files). The system is organized by optimization types and uses language file extensions for better IDE support.

## What are Golden Tests

Golden tests (snapshot tests, approval tests) are a testing technique where:

1. **First run**: a reference file is created with the expected result
2. **Subsequent runs**: the result is compared with the reference
3. **On changes**: the test fails, showing the diff between expected and actual result
4. **Updating references**: when changes are intentional, reference files can be updated

## Structure

```
tests/adapters/
├── golden_utils.py              # Universal golden-test system
├── python/
│   ├── goldens/                 # Data for Python tests
│   │   ├── do/                  # Input data (source code)
│   │   │   └── function_bodies.py
│   │   ├── function_bodies/     # Function body optimization results
│   │   │   ├── basic_strip.py
│   │   │   └── large_only_strip.py
│   │   ├── complex/             # Complex tests
│   │   │   └── full_pipeline.py
│   │   ├── comments/            # Comment processing tests
│   │   ├── literals/            # Literal processing tests
│   │   ├── imports/             # Import processing tests
│   │   ├── public_api/          # Public API tests
│   │   └── fields/              # Field processing tests
│   ├── conftest.py             # Fixtures and utilities for Python tests
│   └── test_*.py               # Python adapter tests
├── typescript/
│   ├── goldens/                # Data for TypeScript tests
│   │   ├── do/                  # Input data (source code)
│   │   │   ├── function_bodies.ts
│   │   │   ├── barrel_file_sample.ts
│   │   │   └── non_barrel_file_sample.ts
│   │   ├── function_bodies/     # Function body optimization results
│   │   │   ├── basic_strip.ts
│   │   │   ├── arrow_functions.ts
│   │   │   └── class_methods.ts
│   │   └── complex/             # Complex tests
│   │       └── full_pipeline.ts
│   ├── conftest.py             # Fixtures and utilities for TS tests
│   └── test_*.py               # TypeScript adapter tests
└── golden_utils.md             # This file
```

## Usage in Tests

### Basic Usage

```python
from ..golden_utils import assert_golden_match, load_sample_code

def test_function_body_optimization(self, do_function_bodies):
    adapter = PythonAdapter()
    adapter._cfg = PythonCfg(strip_function_bodies=True)
    
    result, meta = adapter.process(lctx_py(do_function_bodies))

    # Compare with golden file in function_bodies/ subdirectory
    assert_golden_match(result, "function_bodies", "basic_strip")
```

### Usage with Input Data

```python
def test_with_custom_input():
    # Load input data from do/
    do_function_bodies = load_sample_code("function_bodies")

    adapter = PythonAdapter()
    adapter._cfg = PythonCfg(strip_function_bodies=True)

    result, meta = adapter.process(lctx_py(sample_code))

    # Result is saved to function_bodies/custom_test.py
    assert_golden_match(result, "function_bodies", "custom_test")
```

### Different Optimization Types

```python
# Function body tests
assert_golden_match(result, "function_bodies", "basic_strip")
assert_golden_match(result, "function_bodies", "large_only_strip")

# Complex tests
assert_golden_match(result, "complex", "full_pipeline")

# Comment tests
assert_golden_match(result, "comments", "strip_all")
assert_golden_match(result, "comments", "keep_doc")

# Literal tests
assert_golden_match(result, "literals", "trim_arrays")

# Import tests
assert_golden_match(result, "imports", "external_only")

# Public API tests
assert_golden_match(result, "public_api", "strip_private")

# Field tests
assert_golden_match(result, "fields", "trivial_constructors")
```

### Advanced Usage

```python
# Explicitly specify language
assert_golden_match(result, "function_bodies", "test_name", language="typescript")

# Force update (usually not needed in tests)
assert_golden_match(result, "function_bodies", "test_name", update_golden=True)
```

## Creating and Updating Golden Files

### Automatic Creation

On first test run, the golden file is created automatically in the corresponding subdirectory:

```bash
.venv/Scripts/python.exe -m pytest tests/adapters/python/test_function_bodies.py::test_new_feature -v
```

The file will be created at `tests/adapters/python/goldens/function_bodies/new_feature.py`

### Update via Environment Variable

```bash
# Update all golden files in a specific test
PYTEST_UPDATE_GOLDENS=1 .venv/Scripts/python.exe -m pytest tests/adapters/python/test_function_bodies.py -v

# Update golden files for all Python tests
PYTEST_UPDATE_GOLDENS=1 .venv/Scripts/python.exe -m pytest tests/adapters/python/ -v
```

### Update via Script (Recommended)

```bash
# Show list of available languages
./scripts/update_goldens.sh --list

# Check for missing golden files
./scripts/update_goldens.sh --check

# See what would be updated (dry run)
./scripts/update_goldens.sh python --dry-run

# Update golden files for Python
./scripts/update_goldens.sh python

# Update golden files for TypeScript
./scripts/update_goldens.sh typescript

# Update all golden files
./scripts/update_goldens.sh

# Update with additional pytest options
PYTEST_ARGS="-v --tb=short" ./scripts/update_goldens.sh python
```

### Result File Structure

Golden files are now saved with language extensions in subdirectories by optimization type:

- **Python**: `.py` files in `tests/adapters/python/goldens/<optimization_type>/`
- **TypeScript**: `.ts` files in `tests/adapters/typescript/goldens/<optimization_type>/`
- **JavaScript**: `.js` files in `tests/adapters/javascript/goldens/<optimization_type>/`

This ensures correct syntax highlighting in IDEs and simplifies manual analysis.

## Development Workflow

### 1. Preparing Input Data

If you need new input data, create a file in `do/`:

```bash
# Create new input file
cat > tests/adapters/python/goldens/do/custom_sample.py << 'EOF'
# Custom test code
def example_function():
    return "test"
EOF
```

### 2. Writing a New Test

```python
def test_new_optimization(self):
    # Load input data
    sample_code = load_sample_code("custom_sample")

    adapter = PythonAdapter()
    adapter._cfg = PythonCfg(new_optimization=True)

    result, meta = adapter.process(lctx_py(sample_code))

    # Check logic
    assert "expected_marker" in result
    assert meta.get("optimization.applied", 0) > 0

    # Golden test with optimization type specified
    assert_golden_match(result, "function_bodies", "new_optimization")
```

### 3. First Run

```bash
.venv/Scripts/python.exe -m pytest tests/adapters/python/test_new.py::test_new_optimization -v
```

Golden file will be created automatically at `tests/adapters/python/goldens/function_bodies/new_optimization.py`

### 4. Review and Commit

```bash
# View created golden file (with syntax highlighting!)
cat tests/adapters/python/goldens/function_bodies/new_optimization.py

# Commit input and output data
git add tests/adapters/python/goldens/do/custom_sample.py
git add tests/adapters/python/goldens/function_bodies/new_optimization.py
git commit -m "Add golden test for new optimization"
```

### 5. On Code Changes

If test fails with golden test error:

```bash
# View diff
.venv/Scripts/python.exe -m pytest tests/adapters/python/test_new.py::test_new_optimization -v

# If changes are expected - update golden file
PYTEST_UPDATE_GOLDENS=1 .venv/Scripts/python.exe -m pytest tests/adapters/python/test_new.py::test_new_optimization -v

# Check changes and commit
git diff tests/adapters/python/goldens/function_bodies/new_optimization.py
git add tests/adapters/python/goldens/function_bodies/new_optimization.py
git commit -m "Update golden file after optimization improvement"
```

## Best Practices

### Organization by Optimization Types

**Use correct subdirectories:**
- `function_bodies/` - for function and method body optimization tests
- `comments/` - for comment processing tests
- `literals/` - for literal optimization tests
- `imports/` - for import processing tests
- `public_api/` - for public API filtering tests
- `fields/` - for field and constructor processing tests
- `complex/` - for complex tests with multiple optimization types

### Naming Golden Files

- Use descriptive names: `basic_strip`, `large_only_strip`, `full_pipeline`
- Avoid overly long names
- Use snake_case
- DON'T duplicate language in name (file extension is used)
- DON'T duplicate optimization type in name (subdirectory is used)

### Determinism

Ensure test results are deterministic:

- Don't include time/dates in output
- Sort collections when necessary
- Use fixed input data

### Golden File Size

- Try to make tests focused - one aspect per test
- For large results consider splitting into multiple tests
- Very large golden files complicate review

### Input Data Management

- Create reusable input files in `do/`
- Use `load_sample_code()` instead of hardcoding in fixtures
- Name input files descriptively: `function_bodies`, `barrel_file_sample`, `complex_class_sample`

### Version Control

- **Always** commit golden files and input data to repository
- Commit both `do/` (inputs) and result files
- Include golden file changes in review process
- On merge conflicts in golden files regenerate them via script
- New commit command: `git add tests/adapters/*/goldens/**/*`

<!-- lg:comment:start -->
### CI/CD

In CI/CD ensure that:

- Golden files are checked like regular tests
- Auto-update is NOT used (PYTEST_UPDATE_GOLDENS=1)
- Test failures show clear diff in logs

## Troubleshooting

### Test Fails with "Golden test failed"

1. Review diff in pytest output
2. Determine cause of changes:
   - Bug in code → fix the code
   - Expected change → update golden file

### Golden File Not Created

1. Check write permissions for `goldens/` directory
2. Ensure you're using correct `assert_golden_match` function
3. Verify test reaches the `assert_golden_match` call

### Language Detection Issues

If automatic language detection doesn't work:

```python
# Explicitly specify language
assert_golden_match(result, "function_bodies", "test_name", language="python")
```

### Subdirectory Errors

If test fails with error about missing directory:

1. Ensure you're using correct `optimization_type`
2. Verify directory is created automatically on first run
3. Use existing types: `function_bodies`, `complex`, `comments`, `literals`, `imports`, `public_api`, `fields`

### Input Data Loading Issues

If `load_sample_code()` doesn't find file:

```python
# Check that file exists
from pathlib import Path
sample_path = Path("tests/adapters/python/goldens/do/function_bodies.py")
assert sample_path.exists(), f"Sample file not found: {sample_path}"

# Or explicitly specify language
do_function_bodies = load_sample_code("function_bodies", language="python")
```

### Encoding Issues

Golden files are saved in UTF-8. For encoding problems:

1. Ensure input data is in UTF-8
2. Check your editor settings
3. Normalize input data if necessary

## Extending the System

### Adding a New Language

1. Create directory structure:
   ```bash
   mkdir -p tests/adapters/new_language/goldens/{do,function_bodies,complex,comments,literals,imports,public_api,fields}
   ```

2. Add `conftest.py` with imports:
   ```python
   from ..golden_utils import assert_golden_match, load_sample_code

   @pytest.fixture
   def do_function_bodies():
       return load_sample_code("function_bodies")
   ```

3. Add extension to `golden_utils.py`:
   ```python
   extension_map = {
       # ... existing languages ...
       "new_language": ".newlang"
   }
   ```

4. Create input files in `do/`:
   ```bash
   echo "// New language sample" > tests/adapters/new_language/goldens/do/function_bodies.newlang
   ```

5. `update_goldens.sh` script will automatically discover the new language

### Adding a New Optimization Type

1. Create subdirectory for all languages:
   ```bash
   mkdir -p tests/adapters/{python,typescript}/goldens/new_optimization_type
   ```

2. Use in tests:
   ```python
   assert_golden_match(result, "new_optimization_type", "test_name")
   ```

### Customizing Golden Files

For specific requirements, extend `golden_utils.py`:

```python
def assert_golden_match_custom(result, optimization_type, name, normalizer=None):
    if normalizer:
        result = normalizer(result)
    assert_golden_match(result, optimization_type, name)
```

### Data Manipulation Utilities

New functions for working with golden system:

```python
# List all input files
from tests.adapters.golden_utils import list_sample_files
samples = list_sample_files("python")

# List all golden files
golden_files = list_golden_files("python", "function_bodies")

# Get directories
golden_dir = get_golden_dir("python", "function_bodies")
```

## Updated System Benefits

### 🎯 Organization by Optimization Types
- Clear separation of tests by functionality
- Easy finding of specific tests
- Scalability when adding new optimization types

### 💻 IDE Support
- Correct syntax highlighting in golden files
- Autocompletion and code analysis work in samples
- Code navigation in input and output files

### 📁 Centralized Input Data
- All test data in one place (`do/`)
- Data reuse between tests
- No duplication of hardcoded fixtures

### 🔄 Simplified Management
- Unified API for all test types
- Automatic subdirectory creation
- Improved update scripts

### 🚀 Better Developer Experience
- More informative error messages
- Easy addition of new languages and optimization types
- Intuitive file structure

This updated system makes developing and maintaining golden tests significantly more convenient and organized!
<!-- lg:comment:end -->
