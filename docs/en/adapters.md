# Listing Generator · Language Adapters

This document describes the **language adapter system** in Listing Generator (LG). Adapters allow intelligent optimization of source code listings by removing "noisy" parts while preserving structurally important information.

---

### Why This Is Needed

LLM models work noticeably better with code when:
- they see only **structurally important parts** (signatures, types, interfaces),
- they don't receive bulky **function bodies** (especially for helper methods),
- they're not overloaded with **extensive comments** or **massive literals**,
- they don't waste tokens on **unnecessary imports** or **private details**.

Language adapters solve these problems by transforming code into a more **dense representation**:

1. **Reduce context size**, keeping only what's most important
2. **Increase information density** per token
3. **Lower costs** for large contexts
4. **Improve model focus** on important API parts

---

### Basic Language Adapter Configuration

Language adapters are configured through sections in YAML configuration:

```yaml
api-module:
  extensions: [".py", ".ts", ".js"]

  python:  # Target language
    # Base configuration for entire section
    public_api_only: false  # Show only public API
    strip_function_bodies: true  # Remove function bodies
    comment_policy: "keep_doc"  # Comment handling policy

    # Detailed settings for specific aspects
    imports:
      policy: "strip_external"
      summarize_long: true

    literals:
      max_tokens: 100

    placeholders:
      min_savings_ratio: 2.0  # Minimum savings ratio
      min_abs_savings_if_none: 5  # Minimum absolute savings

    # Token budgeting
    budget:
      max_tokens_per_file: 500
```

---

### Function Body Removal

The `strip_function_bodies` setting allows reducing bulky algorithmic parts while preserving important signatures:

```yaml
# Simple variant (bool)
strip_function_bodies: true

# Extended configuration
strip_function_bodies:
  policy: "strip_all"  # Possible policies: keep_all, strip_all, keep_public
  max_tokens: 50  # Trim function bodies to N tokens instead of complete removal
  except_patterns: ["^init", "^main"]  # Don't touch functions matching regex
  keep_annotated: ["@important", "@critical"]  # Keep annotated functions
```

**Policies:**
- `keep_all` — keep all function bodies
- `strip_all` — remove all function bodies
- `keep_public` — remove only private function/method bodies

**The `max_tokens` parameter:**
Instead of completely removing function bodies, you can use `max_tokens` to trim them to a specified token budget. LG will preserve the beginning of the function and the return statement (if present), inserting a placeholder between them. This allows you to see the main function logic while saving tokens on implementation details.

---

### Comment Processing

The `comment_policy` setting determines how to handle comments and documentation:

```yaml
# Simple variant (string)
comment_policy: "keep_doc"  # keep_all, strip_all, keep_doc, keep_first_sentence

# Extended configuration
comment_policy:
  policy: "keep_doc"
  max_tokens: 50  # Comment size limit in tokens
  keep_annotations: ["TODO", "FIXME", "@param"]  # Keep with these markers
  strip_patterns: ["Copyright", "License"]  # Remove by regex
```

Policies:
- `keep_all` — keep all comments
- `strip_all` — remove all comments
- `keep_doc` — keep only documentation comments
- `keep_first_sentence` — keep only first sentence from documentation

---

### Public API

The `public_api_only` option cleans code of private/internal details:

```yaml
# Enable public API mode
public_api_only: true
```

In this mode:
- Private/protected functions/methods are removed
- Internal classes and interfaces are removed
- Only public members and exported elements are preserved
- Public API necessary for understanding structure is preserved

---

### Import Processing

The `imports` setting allows optimizing import sections:

```yaml
imports:
  policy: "strip_external"  # keep_all, strip_all, strip_external, strip_local
  summarize_long: true  # Collapse long import lists
  max_items_before_summary: 5  # Threshold for collapsing
  external_patterns: ["^@angular/", "^lodash"]  # External library patterns
```

Import policies:
- `keep_all` — keep all imports
- `strip_all` — remove all imports
- `strip_external` — remove only external libraries
- `strip_local` — remove only local imports

---

### Literal Reduction

The `literals` setting limits the size of literal data:

```yaml
literals:
  max_tokens: 100  # Maximum tokens for literals
```

Processed:
- Long strings
- Large arrays/lists
- Bulky objects/dictionaries
- JSON structures

Instead of full content, a shortened version with placeholder is inserted.

---

### Token Budgeting

The budgeting system (`budget`) automatically selects optimal compression level for each file:

```yaml
budget:
  max_tokens_per_file: 500  # Per-file limit in tokens
  priority_order:  # Order of optimization application
    - "imports_external"
    - "literals"
    - "comments"
    - "imports_local"
    - "private_bodies"
    - "public_api_only"
    - "public_bodies"
    - "docstrings_first_sentence"
```

How it works:
1. LG analyzes each file for token count
2. If file exceeds limit, applies optimizations sequentially
3. Priority determines order of transformation application
4. Stops after reaching budget or exhausting available optimizations

---

### Targeted Configuration via targets

Different optimization strategies can be set for different parts of the codebase:

```yaml
api-module:
  extensions: [".py", ".ts"]

  python:
    # Base settings for entire section
    strip_function_bodies: false

    # Targeted overrides
    targets:
      # API modules - only public interfaces
      - match: ["**/api/**", "**/interfaces/**"]
        public_api_only: true
        strip_function_bodies: true

      # Tests - minimal volume
      - match: ["**/test/**"]
        strip_function_bodies: true
        comment_policy: "strip_all"

      # Utils - budgeting
      - match: ["**/utils/**"]
        budget:
          max_tokens_per_file: 300
```

The `match` rule accepts both string and array of glob patterns. When multiple rules match, the more specific one wins.

---

### Placeholder System

The `placeholders` setting determines savings thresholds for applying optimizations:

```yaml
placeholders:
  min_savings_ratio: 2.0  # Minimum token savings ratio
  min_abs_savings_if_none: 5  # Minimum absolute savings for complete removal
```

Placeholders are automatically formatted based on context:
- **Single-line comments** — for most removals
- **Block comments** — when code remains on the same line
- **Inline** — for shortened literals (inside string)

Placeholders contain information about removed element type, name, and size. The `min_savings_ratio` parameter controls the minimum ratio of saved tokens to placeholder size (default 2.0, meaning savings must be at least twice the placeholder size).

---

### Metrics in Reports

Language adapters provide detailed statistics in LG reports:

```json
{
  "code.removed.functions": 15,
  "code.removed.methods": 8,
  "code.removed.comments": 42,
  "code.removed.imports": 3,
  "code.removed.literals": 2,
  "code.bytes_saved": 8960,
  "code.placeholders": 18,
  "code.lines_saved": 245
}
```

These metrics help understand what exactly "eats" tokens and how effective the applied optimizations are.

---

### Automatic Trivial File Skipping

LG automatically detects and skips trivial files that don't carry meaningful content for code analysis:

**Examples of trivial files:**
- Python: `__init__.py` with only re-exports (`from .module import ...`, `__all__ = [...]`)
- TypeScript/JavaScript: barrel files `index.ts`/`index.js` with only re-exports (`export { ... } from './module'`)
- Go: `doc.go` with only package documentation

**Configuration:**
```yaml
api-module:
  extensions: [".py", ".ts"]

  python:
    skip_trivial_files: true  # enabled by default

  typescript:
    skip_trivial_files: true  # enabled by default
```

This feature is enabled by default for all languages and helps reduce noise in listings. If needed, it can be disabled via `skip_trivial_files: false` in section configuration.

---

### Supported Languages

LG supports language adapters for the following programming languages. Each language has a specific configuration key and recommended file extensions:

| Language | YAML Key | Recommended extensions |
|----------|----------|------------------------|
| **Python** | `python:` | `[".py"]` |
| **TypeScript** | `typescript:` | `[".ts", ".tsx"]` |
| **JavaScript** | `javascript:` | `[".js", ".jsx", ".mjs", ".cjs"]` |
| **Kotlin** | `kotlin:` | `[".kt", ".kts"]` |
| **Java** | `java:` | `[".java"]` |
| **C++** | `cpp:` | `[".cpp", ".hpp", ".cc", ".hh", ".cxx", ".hxx"]` |
| **C** | `c:` | `[".c", ".h"]` |
| **Scala** | `scala:` | `[".scala", ".sc"]` |
| **Go** | `go:` | `[".go"]` |
| **Rust** | `rust:` | `[".rs"]` |

**Configuration example:**
```yaml
my-section:
  extensions: [".py", ".java"]

  python:
    strip_function_bodies: true
    comment_policy: "keep_doc"

  java:
    public_api_only: true
    strip_function_bodies: true
```

**Current list:**
The complete list of supported adapters can be obtained with:
```bash
lg diag
```

**Uniform configuration:**
All languages are configured through a common settings model. Internal processing differences (syntax specifics, element visibility rules, comment styles) are encapsulated in adapters and transparent to the user — you don't need to learn the specifics of each language separately.

---

### Best Practices

- Start with basic configuration `strip_function_bodies: true` and `comment_policy: "keep_doc"`
- For API-oriented code use `public_api_only: true`
- For code with many dependencies enable `imports.policy: "strip_external"`
- Use `targets` for more precise tuning depending on code type
- For automatic optimization use `budget` with reasonable token limit
- Check effect with `lg report …` command and watch token savings fields
