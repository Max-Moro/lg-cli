from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Set

from .cache.fs_cache import Cache
from .config.adaptive_loader import AdaptiveConfigLoader
from .config.adaptive_model import ModeOptions
from .types import RunOptions
from .vcs import VcsProvider
from .stats import TokenService


@dataclass
class ConditionContext:
    """
    Контекст для вычисления условий в адаптивных шаблонах.

    Содержит информацию об активных тегах, наборах тегов и скоупах,
    необходимую для правильной оценки условий типа:
    - tag:name
    - TAGSET:set_name:tag_name
    - scope:local/parent
    """
    active_tags: Set[str] = field(default_factory=set)
    tagsets: Dict[str, Set[str]] = field(default_factory=dict)
    current_scope: str = ""
    parent_scope: str = ""

    def is_tag_active(self, tag_name: str) -> bool:
        """Проверяет, активен ли указанный тег."""
        return tag_name in self.active_tags

    def is_tagset_condition_met(self, set_name: str, tag_name: str) -> bool:
        """
        Проверяет условие TAGSET:set_name:tag_name.

        Правила:
        - Истинно, если ни один тег из набора не активен
        - Истинно, если указанный тег активен
        - Ложно во всех остальных случаях
        """
        tagset_tags = self.tagsets.get(set_name, set())
        if not tagset_tags:
            # Набор не существует или пуст - условие истинно (ни один тег не активен)
            return True

        # Проверяем, какие теги из набора активны
        active_in_set = tagset_tags.intersection(self.active_tags)

        if not active_in_set:
            # Ни один тег из набора не активен - условие истинно
            return True

        # Есть активные теги из набора - условие истинно только если указанный тег активен
        return tag_name in active_in_set

    def is_scope_condition_met(self, scope_type: str) -> bool:
        """
        Проверяет условие scope:local/parent.
        """
        if scope_type == "local":
            return self.current_scope == "local"
        elif scope_type == "parent":
            return self.current_scope == "parent"
        return False

@dataclass(frozen=True)
class RunContext:
    root: Path
    options: RunOptions
    cache: Cache
    vcs: VcsProvider
    tokenizer: TokenService
    adaptive_loader: AdaptiveConfigLoader
    mode_options: ModeOptions = field(default_factory=ModeOptions)  # смердженные опции от режимов
    active_tags: Set[str] = field(default_factory=set)  # все активные теги

    def get_condition_context(self):
        """Создание контекста для вычисления условий."""

        # Получаем все доступные наборы тегов
        tag_sets, global_tags = self.adaptive_loader.get_all_available_tags()
        
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
