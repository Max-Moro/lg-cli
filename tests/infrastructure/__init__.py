"""
Унифицированная тестовая инфраструктура для Listing Generator.

Этот пакет содержит общие утилиты, билдеры проектов, фикстуры и хелперы,
которые используются во всех тестах для избежания дублирования кода.

Модули:
- file_utils: Утилиты для создания файлов и директорий
- project_builders: Билдеры для различных типов тестовых проектов  
- adapter_utils: Утилиты для работы с языковыми адаптерами
- config_builders: Билдеры конфигурации (sections, modes, tags)
- rendering_utils: Утилиты для рендеринга шаблонов и секций
"""

# Основные утилиты, которые должны быть доступны везде
from .file_utils import write, write_source_file, write_markdown
from .rendering_utils import render_template, make_run_options, make_engine
from .testing_utils import stub_tokenizer, TokenServiceStub
from .config_builders import (
    create_sections_yaml, create_section_fragment, create_modes_yaml, create_tags_yaml,
    create_basic_lg_cfg, create_basic_sections_yaml, create_template,
    get_basic_sections_config, get_multilang_sections_config
)
from .adapter_utils import is_tree_sitter_available
from .run_context import make_run_context

# Адаптивные конфигурации
from .adaptive_config import ModeConfig, ModeSetConfig, TagConfig, TagSetConfig

__all__ = [
    # File utilities
    "write", "write_source_file", "write_markdown",
    
    # Rendering utilities  
    "render_template", "make_run_options", "make_engine",
    
    # Testing utilities
    "stub_tokenizer", "TokenServiceStub",
    
    # Config builders
    "create_sections_yaml", "create_modes_yaml", "create_tags_yaml", "create_basic_sections_yaml",
    
    # Adapter utilities
    "is_tree_sitter_available",

    # RunContext
    "make_run_context",
    
    # Adaptive config classes
    "ModeConfig", "ModeSetConfig", "TagConfig", "TagSetConfig",
]