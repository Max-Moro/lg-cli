# Changelog

All notable changes to Listing Generator CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Breaking:** Adaptive system architecture reworked — modes and tags now defined inside sections (`mode-sets`, `tag-sets` keys) instead of global `modes.yaml`/`tags.yaml` files
- Unified error handling with consistent user-facing error messages across all commands
- `list mode-sets` and `list tag-sets` commands now require `--context` argument (modes/tags are context-dependent)
- `list mode-sets` command now requires `--provider` argument for filtering integration modes

### Added
- Cross-scope addressing with `@..` and `@../sibling` syntax for accessing parent and sibling `lg-cfg/` directories
- Parent directory traversal in filter patterns (`/../sibling/**`) for including files outside current scope
- Conditional adapter options in `targets:` entries with `when:` syntax (same as section-level conditions)
- Meta-sections (sections without `filters`) for reusable mode/tag definitions via `extends`
- Section inheritance with `extends` key and deterministic merge rules
- Frontmatter `include` directive in `.ctx.md` for including meta-sections
- Integration mode sets with `runs` map for AI provider launch parameters
- Universal `clipboard` provider (implicitly compatible with all modes)
- `list contexts --provider` filtering by compatible providers
- `--provider` argument for `render`/`report` commands
- `provider:<base-id>` conditional operator for provider-specific content
- `default_task` mode option for automatic `${task}` placeholder population
- Comprehensive error diagnostics for adaptive system (cycle detection, validation)

### Fixed
- Current directory reset when transitioning between scopes (prevents path duplication in cross-scope references)

### Removed
- Global `modes.yaml` and `tags.yaml` configuration files (no automatic migration provided — manual update required)

## [0.10.2] - 2026-01-15

### Fixed
- Git worktree and submodule support: gitignore detection now works correctly when `.git` is a file (worktree/submodule) rather than a directory

## [0.10.0] - 2026-01-01

### Added
- Language adapters for C++, C, Java, JavaScript, Scala, Go, and Rust
- `max_tokens` parameter for function body trimming (preserve function structure while reducing size)
- Relative paths within `lg-cfg/` directories (`../`, nested includes)
- `TAGONLY` conditional operator for exclusive tag matching (true only when specified tag is the only active tag from set)

### Changed
- Function body optimization policies: `keep_all`, `strip_all`, `keep_public` (simplified from previous mode system)
- Automatic context-based placeholder formatting (inline/block/embedded)

## [0.9.2] - 2025-11-22

### Added
- Context generation from source code with filtering and normalization
- Adaptive capabilities system (modes, tags, conditional logic)
- Language adapters (Python, TypeScript, Kotlin, Markdown)
- Tokenization support (tiktoken, HuggingFace tokenizers, sentencepiece)
- Git integration (changes/branch-changes VCS modes)
- Template engine with cascading includes
- Diagnostics and caching system
- Configuration scaffolding with presets
