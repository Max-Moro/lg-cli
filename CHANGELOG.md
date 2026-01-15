# Changelog

All notable changes to Listing Generator CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
