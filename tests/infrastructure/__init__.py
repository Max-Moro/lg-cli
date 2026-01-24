"""
Unified test infrastructure for Listing Generator.

This package contains common utilities and helpers
used across all tests to avoid code duplication.

Modules:
- file_utils: Utilities for creating files and directories
- config_builders: Configuration builders (sections, modes, tags)
- rendering_utils: Utilities for rendering templates and sections
"""

# Adaptive configurations
from .adaptive_config import ModeConfig, ModeSetConfig, TagConfig, TagSetConfig
from .cli_utils import run_cli, jload, DEFAULT_TOKENIZER_LIB, DEFAULT_ENCODER, DEFAULT_CTX_LIMIT
from .config_builders import (
    create_sections_yaml, create_section_fragment, create_modes_yaml, create_tags_yaml,
    create_basic_lg_cfg, create_basic_sections_yaml, create_template,
    get_basic_sections_config, get_multilang_sections_config,
    # NEW: Meta-section builders for new adaptive system
    create_mode_meta_section, create_tag_meta_section,
    create_integration_mode_section, create_adaptive_section,
)
# Core utilities that should be available everywhere
from .file_utils import write, write_source_file, write_markdown
from .rendering_utils import load_sections, render_template, make_run_options, make_run_context, make_engine
from .testing_utils import lctx_md

__all__ = [
    # File utilities
    "write", "write_source_file", "write_markdown",

    # Rendering utilities
    "load_sections", "render_template", "make_run_options", "make_run_context", "make_engine",

    # Testing utilities
    "lctx_md",

    # CLI utilities
    "run_cli", "jload",
    "DEFAULT_TOKENIZER_LIB", "DEFAULT_ENCODER", "DEFAULT_CTX_LIMIT",

    # Config builders (legacy)
    "create_sections_yaml", "create_modes_yaml", "create_tags_yaml", "create_basic_sections_yaml",

    # Config builders (new adaptive system)
    "create_mode_meta_section", "create_tag_meta_section",
    "create_integration_mode_section", "create_adaptive_section",

    # Adaptive config classes
    "ModeConfig", "ModeSetConfig", "TagConfig", "TagSetConfig",
]