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

## Phase 3: Integration with Existing Systems ✅ COMPLETE

---

## Phase 4: CLI Commands ✅ COMPLETE

**Implemented**:
- `lg/config/mode_sets_list.schema.json` — added `runs` to Mode, `integration` to ModeSet
- `lg/config/mode_sets_list_schema.py` — regenerated with new fields
- `lg/config/adaptive_factory.py` — NEW: `create_context_resolver(root)`
- `lg/config/modes.py` — new `list_mode_sets(root, context, provider)` using ContextResolver
- `lg/config/tags.py` — new `list_tag_sets(root, context)` using ContextResolver
- `lg/cli.py` — added `--context` and `--provider` arguments, error handling

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
Phase 4: CLI ✅ COMPLETE
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
- [x] `list mode-sets --context --provider` works correctly
- [x] `list tag-sets --context` works correctly
- [x] `{% mode %}` validates against context model
- [x] Meta-sections cannot be rendered
- [x] Single integration mode-set rule enforced
- [x] Provider filtering works
- [ ] Documentation updated
- [ ] Qodana clean
