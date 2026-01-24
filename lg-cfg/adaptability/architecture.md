# New Adaptive System Architecture

## 1. Overview

This document describes the planned architecture for the new adaptive modes and tags system in LG CLI. The design follows the principles outlined in `analysis.md` and `tz-cli.md`.

---

## 2. Module Structure

### 2.1. New Package: `lg/adaptive/`

```
lg/adaptive/
├── __init__.py           # Public API exports
├── model.py              # Data models (ModeSet, Mode, TagSet, Tag, RunsMap)
├── section_extractor.py  # Extract adaptive data from SectionCfg
├── extends_resolver.py   # Resolve `extends` chains with cycle detection
├── context_collector.py  # Collect sections from context templates
├── context_resolver.py   # Build final adaptive model for context
├── validation.py         # Validation rules (single integration mode-set, etc.)
└── errors.py             # Specialized exceptions
```

### 2.2. Module Responsibilities ✅ IMPLEMENTED

All Phase 1-2 modules are implemented. See source code in `lg/adaptive/` for details.

| Module | Purpose |
|--------|---------|
| `model.py` | Core data models: `Mode`, `ModeSet`, `Tag`, `TagSet`, `AdaptiveModel` |
| `errors.py` | Specialized exceptions for the adaptive system |
| `section_extractor.py` | Extract `AdaptiveModel` from `SectionCfg` raw dictionaries |
| `extends_resolver.py` | Resolve `extends` chains with cycle detection and merge |
| `context_collector.py` | Collect all sections from context template without rendering |
| `context_resolver.py` | Orchestrate full adaptive model resolution for context |
| `validation.py` | Validation rules (single integration mode-set, mode references, provider support) |

---

## 3. Changes to Existing Modules

### 3.1. `lg/section/model.py` ✅

Extended with `extends`, `mode_sets_raw`, `tag_sets_raw` fields and `is_meta_section()` method.
See implementation in `lg/section/model.py`.

### 3.2. `lg/template/frontmatter.py` ✅

Implemented `ContextFrontmatter`, `parse_frontmatter()`, `strip_frontmatter()`, `has_frontmatter()`.
See implementation in `lg/template/frontmatter.py`.

### 3.3. `lg/template/context.py`

Update `TemplateContext` to use context-specific adaptive model:

```python
class TemplateContext:
    def __init__(self, run_ctx: RunContext, adaptive_model: AdaptiveModel):
        self.run_ctx = run_ctx
        self.adaptive_model = adaptive_model  # NEW: context-specific model
        # ...

    def enter_mode_block(self, modeset: str, mode: str) -> None:
        # Validate against adaptive_model instead of global config
        ...
```

### 3.4. `lg/run_context.py`

Remove global adaptive loader, add context-specific model:

```python
@dataclass(frozen=True)
class RunContext:
    root: Path
    options: RunOptions
    cache: Cache
    vcs: VcsProvider
    # ...

    # REMOVED: adaptive_loader, mode_options, active_tags (now per-context)

    # NEW: Lazy resolver for adaptive models
    adaptive_resolver: ContextResolver = field(default=None)
```

### 3.5. `lg/engine.py`

Update to build adaptive model per target:

```python
class Engine:
    def _init_processors(self) -> None:
        # Create adaptive resolver
        self.adaptive_resolver = ContextResolver(
            section_service=self.run_ctx.section_service,
            extends_resolver=ExtendsResolver(self.run_ctx.section_service),
            context_collector=ContextCollector(self.template_processor)
        )

    def render_context(self, context_name: str) -> str:
        # Build adaptive model for this context
        adaptive_model = self.adaptive_resolver.resolve_for_context(context_name)

        # Create TemplateContext with context-specific model
        template_ctx = TemplateContext(self.run_ctx, adaptive_model)
        ...
```

---

## 4. CLI Commands

### 4.1. Updated `list mode-sets`

```
listing-generator list mode-sets --context <ctx-name> --provider <provider-id>
```

Response format (updated schema):

```json
{
  "mode-sets": [
    {
      "id": "ai-interaction",
      "title": "AI Interaction",
      "integration": true,
      "modes": [
        {
          "id": "ask",
          "title": "Ask",
          "description": "Question-answer mode",
          "tags": [],
          "runs": {
            "com.anthropic.claude.cli": "--permission-mode default"
          }
        }
      ]
    }
  ]
}
```

### 4.2. Updated `list tag-sets`

```
listing-generator list tag-sets --context <ctx-name>
```

Response format remains similar, but now context-aware.

---

## 5. Merge Semantics

### 5.1. Order of Application

For a single section with `extends: [A, B]`:
1. Resolve A (recursively with its extends)
2. Resolve B (recursively with its extends)
3. Merge: A ← B ← local section

For a context with multiple sections:
1. Traverse template depth-first, left-to-right
2. Collect sections in order
3. Process frontmatter `include` sections (appended)
4. Merge all in order: first ← second ← ... ← last

### 5.2. Merge Rules by Field

| Field | Merge Rule |
|-------|------------|
| `mode-sets` | Merge by id; modes merge by id; child wins |
| `tag-sets` | Merge by id; tags merge by id; child wins |
| `extensions` | Union |
| `adapters` | Deep merge; child wins on conflict |
| `skip_empty` | Child wins |
| `path_labels` | Child wins |
| `filters` | **NOT inherited** - use child's only |
| `targets` | **NOT inherited** - use child's only |
| `extends` | **NOT inherited** - already processed |

---

## 6. Error Handling ✅

Exception classes implemented in `lg/adaptive/errors.py`:
- `AdaptiveError` (base)
- `ExtendsCycleError`
- `MetaSectionRenderError`
- `MultipleIntegrationModeSetsError`
- `NoIntegrationModeSetError`
- `ProviderNotSupportedError`
- `InvalidModeReferenceError`
- `SectionNotFoundInExtendsError`

---

## 7. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Command                              │
│   listing-generator render ctx:my-context --mode ai:agent       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                           Engine                                 │
│  1. Parse target (ctx:my-context)                               │
│  2. Build AdaptiveModel for context                             │
│  3. Create TemplateContext with model                           │
│  4. Process template                                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
┌───────────────────────────┐  ┌───────────────────────────────────┐
│    ContextResolver        │  │      TemplateProcessor            │
│                           │  │                                   │
│  1. Parse frontmatter     │  │  1. Parse template AST            │
│  2. Collect sections      │  │  2. Resolve references            │
│  3. Resolve extends       │  │  3. Evaluate conditions           │
│  4. Merge adaptive data   │  │  4. Process sections              │
│  5. Validate model        │  │  5. Render output                 │
└───────────────────────────┘  └───────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TemplateContext                               │
│  - AdaptiveModel (context-specific)                             │
│  - ConditionContext (uses model's tag-sets)                     │
│  - Mode state stack (validates against model)                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Backward Compatibility

### 8.1. Migration Strategy

Migration from old system will be handled separately. Key points:
- Old `modes.yaml`/`tags.yaml` will be converted to meta-sections
- Existing contexts will get frontmatter with `include` references
- Automated migration tool will be provided

### 8.2. Deprecation Path

1. First release: New system active, old files ignored with warning
2. Next release: Migration tool required before use
3. Future release: Old format support removed

---

## 9. Testing Strategy

### 9.1. Unit Tests

- `test_model.py`: Data model serialization/deserialization
- `test_extends_resolver.py`: Inheritance chains, cycle detection
- `test_context_collector.py`: Section collection from templates
- `test_context_resolver.py`: Full model resolution
- `test_validation.py`: All validation rules

### 9.2. Integration Tests

- End-to-end `list mode-sets` with context filtering
- End-to-end `render` with new adaptive model
- `{% mode %}` validation in templates
- Provider filtering for integration mode-sets

---

## 10. Performance Considerations

### 10.1. Caching

- Cache resolved `SectionCfg` (after extends) by section path
- Cache `AdaptiveModel` by context name + active modes hash
- Invalidate on `lg-cfg/` file changes (existing watcher)

### 10.2. Lazy Loading

- Parse frontmatter only when needed (list commands, render)
- Resolve extends chains lazily (on first access)
- Don't load full template AST for section collection if possible
