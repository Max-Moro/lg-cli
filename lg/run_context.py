from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Set

from .cache.fs_cache import Cache
from .types import RunOptions
from .vcs import VcsProvider
from .stats import TokenService


@dataclass(frozen=True)
class RunContext:
    root: Path
    options: RunOptions
    cache: Cache
    vcs: VcsProvider
    tokenizer: TokenService
    active_modes: Dict[str, str] = field(default_factory=dict)  # modeset_name -> mode_name
    active_tags: Set[str] = field(default_factory=set)  # все активные теги
    
    def get_condition_context(self):
        """Создание контекста для вычисления условий."""
        from .config.condition_context import ConditionContext
        from .config.tags import get_all_available_tags
        
        # Получаем все доступные наборы тегов
        tag_sets, global_tags = get_all_available_tags(self.root)
        
        # Создаем карту наборов тегов для контекста
        tagsets: Dict[str, Set[str]] = {}
        for set_name, tag_set in tag_sets.items():
            tagsets[set_name] = set(tag_set.tags.keys())
        
        # Добавляем глобальные теги как отдельный набор
        if global_tags:
            tagsets["global"] = set(global_tags.keys())
        
        return ConditionContext(
            active_tags=self.active_tags,
            tagsets=tagsets,
            current_scope="local",  # По умолчанию локальный скоуп
            parent_scope="parent"
        )
