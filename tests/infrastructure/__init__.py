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
- fixtures: Переиспользуемые фикстуры pytest
"""

# Основные утилиты, которые должны быть доступны везде
from .file_utils import write, write_file, write_source_file, write_markdown
from .rendering_utils import render_template, make_run_options, make_engine
from .config_builders import (
    create_sections_yaml, create_section_fragment, create_modes_yaml, create_tags_yaml,
    create_basic_lg_cfg, create_basic_sections_yaml, create_template,
    write_modes_yaml, write_tags_yaml,
    get_basic_sections_config, get_multilang_sections_config
)
from .adapter_utils import make_adapter, make_adapter_real, is_tree_sitter_available
from .project_builders import ProjectBuilder, create_basic_project, create_adaptive_project

# Основные фикстуры 
from .fixtures import tmp_project, make_run_context

# Адаптивные конфигурации
from .adaptive_config import ModeConfig, ModeSetConfig, TagConfig, TagSetConfig

__all__ = [
    # File utilities
    "write", "write_file", "write_source_file", "write_markdown",
    
    # Rendering utilities  
    "render_template", "make_run_options", "make_engine",
    
    # Config builders
    "create_sections_yaml", "create_modes_yaml", "create_tags_yaml", 
    "write_modes_yaml", "write_tags_yaml",
    
    # Adapter utilities
    "make_adapter", "make_adapter_real", "is_tree_sitter_available",
    
    # Project builders
    "ProjectBuilder", "create_basic_project", "create_adaptive_project",
    
    # Fixtures
    "tmp_project", "make_run_context",
    
    # Adaptive config classes
    "ModeConfig", "ModeSetConfig", "TagConfig", "TagSetConfig",
]