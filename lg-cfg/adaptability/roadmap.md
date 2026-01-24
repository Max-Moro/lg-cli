# Development Roadmap: New Adaptive System

## Overview

This roadmap outlines the development phases for implementing the new adaptive modes and tags system in LG CLI. The work is structured to minimize risk and allow incremental testing.

---

## Phase 1: Foundation — Data Models and Parsing ✅ COMPLETE

**Implemented**:
- `lg/adaptive/model.py` — `Mode`, `ModeSet`, `Tag`, `TagSet`, `AdaptiveModel`
- `lg/adaptive/errors.py` — 8 exception classes
- `lg/adaptive/__init__.py` — public API
- `lg/section/model.py` — extended with `extends`, `mode_sets_raw`, `tag_sets_raw`, `is_meta_section()`
- `lg/template/frontmatter.py` — `ContextFrontmatter`, `parse_frontmatter()`, `strip_frontmatter()`

---

## Phase 2: Resolution Logic ✅ COMPLETE

**Implemented**:
- `lg/adaptive/section_extractor.py` — `extract_adaptive_model()`
- `lg/adaptive/validation.py` — `AdaptiveValidator`, validation functions
- `lg/adaptive/extends_resolver.py` — `ExtendsResolver`, `ResolvedSectionData`
- `lg/adaptive/context_collector.py` — `ContextCollector`, `CollectedSections`
- `lg/adaptive/context_resolver.py` — `ContextResolver`, `ContextAdaptiveData`

---

## Phase 3: Integration with Existing Systems

**Goal**: Connect new adaptive system to template engine and CLI.

### 3.1. Update TemplateContext (`lg/template/context.py`)

**Tasks**:
- [ ] Accept `AdaptiveModel` in constructor
- [ ] Update `enter_mode_block()` to validate against model
- [ ] Update `get_condition_evaluator()` to use model's tag-sets
- [ ] Update `_get_tagsets()` to use model

**Dependencies**: Phase 2

**Tests**:
- Mode block with valid mode
- Mode block with invalid mode
- Condition evaluation with new tag-sets

### 3.2. Update RunContext (`lg/run_context.py`)

**Tasks**:
- [ ] Remove `adaptive_loader` field
- [ ] Remove global `mode_options` and `active_tags`
- [ ] Add lazy `ContextResolver` access
- [ ] Update `ConditionContext` creation

**Dependencies**: 2.4

**Tests**:
- RunContext creation without old fields
- Access to resolver

### 3.3. Update Engine (`lg/engine.py`)

**Tasks**:
- [ ] Create `ContextResolver` in `_init_services()`
- [ ] Build `AdaptiveModel` per target in `render_context()` and `render_section()`
- [ ] Pass model to `TemplateContext`
- [ ] Update section render flow

**Dependencies**: 3.1, 3.2

**Tests**:
- Render context with new adaptive model
- Render section with new adaptive model
- End-to-end with `{% mode %}`

### 3.4. Update `{% mode %}` Processing (`lg/template/adaptive/`)

**Tasks**:
- [ ] Update `ModeBlockNode` processing to use context's model
- [ ] Add validation call before entering mode block
- [ ] Ensure proper error messages

**Dependencies**: 3.1

**Tests**:
- Valid mode block renders
- Invalid mode block raises error

### 3.5. Meta-Section Render Protection

**Tasks**:
- [ ] Add check in `SectionProcessor.process_section()`
- [ ] Raise `MetaSectionRenderError` for sections without filters
- [ ] Clear error message with section name

**Dependencies**: 1.2, 1.4

**Tests**:
- Normal section renders
- Meta-section raises error

---

## Phase 4: CLI Commands

**Goal**: Update CLI to support new list commands with context/provider filtering.

### 4.1. Update JSON Schemas

**Tasks**:
- [ ] Update `mode_sets_list.schema.json`:
  - Add `runs` to Mode
  - Add `integration` boolean to ModeSet
- [ ] Regenerate `mode_sets_list_schema.py`
- [ ] Update `tag_sets_list.schema.json` if needed
- [ ] Regenerate `tag_sets_list_schema.py`

**Dependencies**: 1.1

**Tests**: Schema validation

### 4.2. Update `list mode-sets` Command

**Tasks**:
- [ ] Add `--context` required argument
- [ ] Add `--provider` required argument
- [ ] Build adaptive model for context
- [ ] Filter by provider (integration mode-set only)
- [ ] Return filtered response

**Dependencies**: Phase 2, 4.1

**Tests**:
- List with context and provider
- Provider filtering
- Error on missing arguments
- Error on unsupported provider

### 4.3. Update `list tag-sets` Command

**Tasks**:
- [ ] Add `--context` required argument
- [ ] Build adaptive model for context
- [ ] Return context-specific tag-sets

**Dependencies**: Phase 2

**Tests**:
- List with context
- Error on missing context

### 4.4. CLI Argument Parsing (`lg/cli.py`)

**Tasks**:
- [ ] Add `--context` to list mode-sets
- [ ] Add `--provider` to list mode-sets
- [ ] Add `--context` to list tag-sets
- [ ] Update help text

**Dependencies**: 4.2, 4.3

**Tests**: Argument parsing

---

## Phase 5: Cleanup and Documentation

**Goal**: Remove deprecated code, update documentation.

### 5.1. Deprecate Old Adaptive System

**Tasks**:
- [ ] Mark `lg/config/modes.py` as deprecated
- [ ] Mark `lg/config/tags.py` as deprecated
- [ ] Mark `lg/config/adaptive_loader.py` as deprecated
- [ ] Mark `lg/config/adaptive_model.py` as deprecated (keep for reference)
- [ ] Remove usage of old modules from codebase
- [ ] Add deprecation warnings if old files found

**Dependencies**: Phases 1-4 complete

**Tests**: Deprecation warnings work

### 5.2. Update Documentation

**Tasks**:
- [ ] Update `docs/en/adaptability.md`
- [ ] Update `docs/en/templates.md`
- [ ] Add examples for new `extends` feature
- [ ] Add examples for frontmatter `include`
- [ ] Document new CLI arguments

**Dependencies**: Phase 4

**Tests**: Documentation examples work

### 5.3. Code Quality

**Tasks**:
- [ ] Run Qodana inspection
- [ ] Fix any new issues
- [ ] Update type hints
- [ ] Ensure test coverage

**Dependencies**: All phases

---

## Phase 6: Migration Tool (Separate Project)

**Goal**: Automated migration from old format.

### 6.1. Migration Logic

**Tasks**:
- [ ] Parse old `modes.yaml` and `tags.yaml`
- [ ] Generate `ai-interaction.sec.yaml` meta-section
- [ ] Generate frontmatter for existing contexts
- [ ] Backup old files
- [ ] Apply changes

**Dependencies**: Phases 1-5 complete

### 6.2. CLI Migration Command

**Tasks**:
- [ ] Add `listing-generator migrate` command
- [ ] Dry-run mode
- [ ] Backup creation
- [ ] Progress reporting

**Dependencies**: 6.1

---

## Dependency Graph

```
Phase 1: Foundation ✅ COMPLETE
Phase 2: Resolution ✅ COMPLETE
                    │
Phase 3: Integration│
  3.1 TemplateContext ◄───────────────────────┤
  3.2 RunContext ◄────────────────────────────┤
  3.3 Engine ◄──── 3.1, 3.2                   │
  3.4 Mode Processing ◄───────────────────────┤
  3.5 Meta-Section Protection ◄───────────────┘
                    │
Phase 4: CLI        │
  4.1 JSON Schemas ◄──────────────────────────┤
  4.2 list mode-sets ◄────────────────────────┤
  4.3 list tag-sets ◄─────────────────────────┤
  4.4 CLI Parsing ◄───────────────────────────┘
                    │
Phase 5: Cleanup    │
  5.1 Deprecation ◄─┴─ All phases
  5.2 Documentation
  5.3 Code Quality

Phase 6: Migration (separate)
  6.1 Migration Logic
  6.2 CLI Command
```

---

## Success Criteria

- [ ] All existing tests pass (no regressions)
- [ ] New tests cover all edge cases in TZ
- [ ] `list mode-sets --context --provider` works correctly
- [ ] `list tag-sets --context` works correctly
- [ ] `{% mode %}` validates against context model
- [ ] Meta-sections cannot be rendered
- [ ] Single integration mode-set rule enforced
- [ ] Provider filtering works
- [ ] Documentation updated
- [ ] Qodana clean
