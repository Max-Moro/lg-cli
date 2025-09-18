"""
Построитель манифеста одной секции для LG V2.

Заменяет части старого build_manifest, но работает с одной секцией
и учитывает активный контекст шаблона (режимы, теги, условия).
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..adapters.registry import get_adapter_for_path
from ..conditions.evaluator import evaluate_condition_string
from ..config import SectionCfg, load_config
from ..config.paths import is_cfg_relpath
from ..io.filters import FilterEngine
from ..io.fs import build_gitignore_spec, iter_files
from ..lang import get_language_for_file
from ..template.context import TemplateContext
from ..types_v2 import FileEntry, SectionManifest, SectionRef


def build_section_manifest(
    section_ref: SectionRef, 
    template_ctx: TemplateContext,
    root: Path,
    vcs,
    vcs_mode: str
) -> SectionManifest:
    """
    Строит манифест одной секции с учетом активного контекста.
    
    Args:
        section_ref: Ссылка на секцию
        template_ctx: Контекст шаблона с активными режимами/тегами
        root: Корень репозитория
        vcs: VCS провайдер
        vcs_mode: Режим VCS ("all" или "changes")
        
    Returns:
        Манифест секции с отфильтрованными файлами
        
    Raises:
        RuntimeError: Если секция не найдена
    """
    # TODO
    
    return NOne
