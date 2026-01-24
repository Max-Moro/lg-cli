# Development Roadmap: New Adaptive System
<!-- FILE: lg-cfg/adaptability/roadmap.md -->

Date: 2026-01-24

## Overview

This roadmap outlines the development phases for implementing the new adaptive modes and tags system in LG CLI. The work is structured to minimize risk and allow incremental testing.

---

## Phase 1: Foundation — Data Models and Parsing

**Goal**: Establish core data structures and parsing capabilities without changing existing behavior.

### 1.1. New Data Models (`lg/adaptive/model.py`)

**Tasks**:
- [ ] Create `Mode` dataclass with `runs` support
- [ ] Create `ModeSet` dataclass with `is_integration` property
- [ ] Create `Tag` and `TagSet` dataclasses
- [ ] Create `AdaptiveModel` aggregate class
- [ ] Implement `filter_by_provider()` method
- [ ] Add JSON serialization for CLI output

**Dependencies**: None

**Tests**:
- Model creation and property access
- `is_integration` detection
- Provider filtering logic
- JSON serialization

### 1.2. Section Model Extensions (`lg/section/model.py`)

**Tasks**:
- [ ] Add `extends: List[str]` field to `SectionCfg`
- [ ] Add `mode_sets: Dict` and `tag_sets: Dict` fields
- [ ] Implement `is_meta_section()` method
- [ ] Update `from_dict()` to parse new fields
- [ ] Add validation for new fields

**Dependencies**: None

**Tests**:
- Parsing sections with `extends`
- Parsing inline `mode-sets` and `tag-sets`
- Meta-section detection

### 1.3. Frontmatter Parser (`lg/template/frontmatter.py`)

**Tasks**:
- [ ] Create `ContextFrontmatter` dataclass
- [ ] Implement `parse_frontmatter()` function
- [ ] Implement `strip_frontmatter()` function
- [ ] Handle edge cases (no frontmatter, empty, malformed)

**Dependencies**: None

**Tests**:
- Parse valid frontmatter
- Handle missing frontmatter
- Handle malformed YAML
- Strip frontmatter correctly

### 1.4. Error Types (`lg/adaptive/errors.py`)

**Tasks**:
- [ ] Create `AdaptiveError` base class
- [ ] Create `ExtendsCycleError`
- [ ] Create `MetaSectionRenderError`
- [ ] Create `MultipleIntegrationModeSetsError`
- [ ] Create `NoIntegrationModeSetError`
- [ ] Create `ProviderNotSupportedError`
- [ ] Create `InvalidModeReferenceError`

**Dependencies**: None

**Tests**: Error message formatting

---

## Phase 2: Resolution Logic

**Goal**: Implement section inheritance and adaptive model resolution.

### 2.1. Extends Resolver (`lg/adaptive/extends_resolver.py`)

**Tasks**:
- [ ] Create `ExtendsResolver` class
- [ ] Implement cycle detection with resolution stack
- [ ] Implement depth-first, left-to-right traversal
- [ ] Implement `_merge_sections()` with correct semantics:
  - Mode-sets/tag-sets: merge by id, child wins
  - Extensions: union
  - Adapters: deep merge
  - Filters/targets: NOT inherited
- [ ] Handle addressed section references (`@scope:name`)
- [ ] Cache resolved sections

**Dependencies**: 1.2, 1.4

**Tests**:
- Simple extends chain
- Multiple extends
- Cycle detection
- Merge semantics for each field type
- Cross-scope extends

### 2.2. Section Extractor (`lg/adaptive/section_extractor.py`)

**Tasks**:
- [ ] Create `extract_adaptive_data()` function
- [ ] Parse raw `mode-sets` dict into `ModeSet` objects
- [ ] Parse raw `tag-sets` dict into `TagSet` objects
- [ ] Handle missing/empty adaptive data

**Dependencies**: 1.1, 1.2

**Tests**:
- Extract from section with full adaptive data
- Extract from section with partial data
- Extract from section with no adaptive data

### 2.3. Context Collector (`lg/adaptive/context_collector.py`)

**Tasks**:
- [ ] Create `ContextCollector` class
- [ ] Implement template AST traversal
- [ ] Collect `${section}` placeholders
- [ ] Collect sections from `${tpl:...}` and `${ctx:...}` (transitive)
- [ ] Exclude `${md:...}` placeholders
- [ ] Process frontmatter `include` sections
- [ ] Ignore conditions (collect all branches)

**Dependencies**: 1.3, Template system understanding

**Tests**:
- Collect from simple context
- Collect transitive includes
- Frontmatter includes
- Ignore `${md:...}`
- Collect from both branches of `{% if %}`

### 2.4. Context Resolver (`lg/adaptive/context_resolver.py`)

**Tasks**:
- [ ] Create `ContextResolver` class
- [ ] Implement `resolve_for_context()`
- [ ] Implement `resolve_for_section()`
- [ ] Implement deterministic merge order
- [ ] Integrate with validator

**Dependencies**: 2.1, 2.2, 2.3

**Tests**:
- Full context resolution
- Section-only resolution
- Merge order verification
- Integration with validator

### 2.5. Validation (`lg/adaptive/validation.py`)

**Tasks**:
- [ ] Create `AdaptiveValidator` class
- [ ] Implement `validate_model()` — single integration mode-set rule
- [ ] Implement `validate_mode_reference()` — `{% mode %}` validation
- [ ] Implement `validate_provider_support()` — provider filtering

**Dependencies**: 1.1, 1.4

**Tests**:
- Valid model passes
- Multiple integration mode-sets fails
- Zero integration mode-sets fails
- Invalid mode reference fails
- Unsupported provider fails

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
Phase 1: Foundation
  1.1 Data Models ────────────────────────────┐
  1.2 Section Extensions ─────────────────────┤
  1.3 Frontmatter Parser ─────────────────────┤
  1.4 Error Types ────────────────────────────┤
                                              │
Phase 2: Resolution                           │
  2.1 Extends Resolver ◄──────────────────────┤
  2.2 Section Extractor ◄─────────────────────┤
  2.3 Context Collector ◄─────────────────────┤
  2.4 Context Resolver ◄──── 2.1, 2.2, 2.3    │
  2.5 Validation ◄────────────────────────────┘
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

## Estimates

| Phase | Complexity | Notes |
|-------|------------|-------|
| Phase 1 | Low | Foundational, isolated changes |
| Phase 2 | High | Core logic, many edge cases |
| Phase 3 | Medium | Integration requires careful refactoring |
| Phase 4 | Low | CLI changes are straightforward |
| Phase 5 | Low | Cleanup and docs |
| Phase 6 | Medium | Separate project, user-facing |

---

## Risk Mitigation

### Technical Risks

1. **Circular extends detection complexity**
   - Mitigation: Use simple stack-based detection, fail fast

2. **Template AST traversal for section collection**
   - Mitigation: Reuse existing template parsing, add visitor pattern

3. **Performance impact of per-context resolution**
   - Mitigation: Aggressive caching at multiple levels

### Process Risks

1. **Breaking existing functionality**
   - Mitigation: Keep old code until Phase 5, run full test suite

2. **Incomplete test coverage**
   - Mitigation: Test-first development, edge case focus

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
