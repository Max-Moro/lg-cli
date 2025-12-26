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

  lang: # Target language
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
        style: "inline"  # Placeholder style: inline, block, none
        min_savings_ratio: 2.0  # Minimum savings ratio

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
  mode: "public_only"  # Possible modes: none, all, public_only, non_public, large_only
  min_lines: 5  # Minimum size for removal in large_only mode
  except_patterns: ["^init", "^main"]  # Don't touch functions matching regex
  keep_annotated: ["@important", "@critical"]  # Keep annotated functions
```

Modes:
- `none` — don't remove anything
- `all` — remove all function bodies
- `public_only` — remove only from public functions/methods
- `non_public` — remove only from private/protected
- `large_only` — remove functions larger than `min_lines`

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

The `placeholders` setting determines how to denote removed code sections:

```yaml
placeholders:
  style: "inline"  # inline, block, none
  min_savings_ratio: 2.0  # Minimum token savings ratio
  min_abs_savings_if_none: 5  # Minimum absolute savings for style=none
```

Styles:
- `inline` — single-line comments
- `block` — block comments
- `none` — no placeholders (complete removal)

Placeholders contain information about removed element type, name, and size.

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

### Language-Specific Features

**Trivial file detection** is enabled by default for all languages. Trivial files (like `__init__.py` with only re-exports, `index.ts` barrel files, `doc.go` with only package docs) are automatically skipped from listings. This can be disabled per-section with `skip_trivial_files: false`.

**Python** provides special handlers for decorators (`@property`, `@classmethod`) and Python-specific comment styles (docstrings).

**TypeScript** offers optimized work with JSX and decorators, and special logic for exported API.

---

### Best Practices

- Start with basic configuration `strip_function_bodies: true` and `comment_policy: "keep_doc"`
- For API-oriented code use `public_api_only: true`
- For code with many dependencies enable `imports.policy: "strip_external"`
- Use `targets` for more precise tuning depending on code type
- For automatic optimization use `budget` with reasonable token limit
- Check effect with `lg report …` command and watch token savings fields
