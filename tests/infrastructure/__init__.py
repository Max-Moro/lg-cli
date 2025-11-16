"""
Unified test infrastructure for Listing Generator.

This package contains common utilities and helpers
used across all tests to avoid code duplication.

Modules:
- file_utils: Utilities for creating files and directories
- adapter_utils: Utilities for working with language adapters
- config_builders: Configuration builders (sections, modes, tags)
- rendering_utils: Utilities for rendering templates and sections
"""

# Core utilities that should be available everywhere
from .file_utils import write, write_source_file, write_markdown
from .rendering_utils import render_template, make_run_options, make_run_context, make_engine
from .testing_utils import stub_tokenizer, TokenServiceStub, lctx, lctx_py, lctx_ts, lctx_md, lctx_kt
from .cli_utils import run_cli, jload, DEFAULT_TOKENIZER_LIB, DEFAULT_ENCODER, DEFAULT_CTX_LIMIT
from .config_builders import (
    create_sections_yaml, create_section_fragment, create_modes_yaml, create_tags_yaml,
    create_basic_lg_cfg, create_basic_sections_yaml, create_template,
    get_basic_sections_config, get_multilang_sections_config
)
from .adapter_utils import is_tree_sitter_available

# Adaptive configurations
from .adaptive_config import ModeConfig, ModeSetConfig, TagConfig, TagSetConfig

__all__ = [
    # File utilities
    "write", "write_source_file", "write_markdown",

    # Rendering utilities
    "render_template", "make_run_options", "make_run_context", "make_engine",

    # Testing utilities
    "stub_tokenizer", "TokenServiceStub", "lctx", "lctx_py", "lctx_ts", "lctx_md", "lctx_kt",

    # CLI utilities
    "run_cli", "jload",
    "DEFAULT_TOKENIZER_LIB", "DEFAULT_ENCODER", "DEFAULT_CTX_LIMIT",

    # Config builders
    "create_sections_yaml", "create_modes_yaml", "create_tags_yaml", "create_basic_sections_yaml",

    # Adapter utilities
    "is_tree_sitter_available",

    # Adaptive config classes
    "ModeConfig", "ModeSetConfig", "TagConfig", "TagSetConfig",
]