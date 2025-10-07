from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Set

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
    - origin: "self" или путь к области (например, "apps/web")
    """
    active_tags: Set[str] = field(default_factory=set)
    tagsets: Dict[str, Set[str]] = field(default_factory=dict)
    origin: str = ""
    task_text: Optional[str] = None

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
        
        Args:
            scope_type: "local" или "parent"
            
        Returns:
            True если условие выполнено:
            - scope:local - истинно для локального скоупа (origin == "self" или пустой)
            - scope:parent - истинно для родительского скоупа (origin != "self" и не пустой)
        """
        if scope_type == "local":
            return not self.origin or self.origin == "self"
        elif scope_type == "parent":
            return bool(self.origin and self.origin != "self")
        return False

    def is_task_provided(self) -> bool:
        """
        Проверяет, задан ли непустой эффективный текст задачи.
        
        Учитывает как явно указанный --task, так и задачи из активных режимов.
        
        Returns:
            True если есть эффективный task_text (явный или из режимов)
        """
        return bool(self.task_text and self.task_text.strip())


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

    def get_effective_task_text(self) -> Optional[str]:
        """
        Возвращает эффективный текст задачи с учетом приоритетов.
        
        Приоритет:
        1. Явно указанный --task (если не пустой)
        2. Задачи из активных режимов (объединенные через параграфы)
        3. None, если ни то ни другое не задано
        
        Returns:
            Эффективный текст задачи или None
        """
        # Приоритет 1: явно указанный --task
        if self.options.task_text and self.options.task_text.strip():
            return self.options.task_text
        
        # Приоритет 2: задачи из активных режимов
        mode_tasks = self._collect_mode_tasks()
        if mode_tasks:
            # Объединяем задачи через двойной перевод строки (параграфы)
            return "\n\n".join(mode_tasks)
        
        # Приоритет 3: ничего не задано
        return None
    
    def _collect_mode_tasks(self) -> list[str]:
        """
        Собирает default_task из всех активных режимов.
        
        Returns:
            Список непустых задач из режимов в порядке имени modeset (для детерминизма)
        """
        modes_config = self.adaptive_loader.get_modes_config()
        tasks = []
        
        # Сортируем по имени modeset для детерминизма
        for modeset_name in sorted(self.options.modes.keys()):
            mode_name = self.options.modes[modeset_name]
            
            modeset = modes_config.mode_sets.get(modeset_name)
            if not modeset:
                continue
            
            mode = modeset.modes.get(mode_name)
            if not mode or not mode.default_task:
                continue
            
            tasks.append(mode.default_task)
        
        return tasks
