from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Set

from .cache.fs_cache import Cache
from .config.adaptive_loader import AdaptiveConfigLoader
from .config.adaptive_model import ModeOptions
from .types import RunOptions
from .git import VcsProvider
from .stats import TokenService


@dataclass
class ConditionContext:
    """
    Context for evaluating conditions in adaptive templates.

    Contains information about active tags, tag sets and scopes,
    necessary for correct evaluation of conditions like:
    - tag:name
    - TAGSET:set_name:tag_name
    - origin: "self" or path to scope (e.g., "apps/web")
    """
    active_tags: Set[str] = field(default_factory=set)
    tagsets: Dict[str, Set[str]] = field(default_factory=dict)
    origin: str = ""
    task_text: Optional[str] = None

    def is_tag_active(self, tag_name: str) -> bool:
        """Check if specified tag is active."""
        return tag_name in self.active_tags

    def is_tagset_condition_met(self, set_name: str, tag_name: str) -> bool:
        """
        Check TAGSET:set_name:tag_name condition.

        Rules:
        - True if no tag from the set is active
        - True if specified tag is active
        - False in all other cases
        """
        tagset_tags = self.tagsets.get(set_name, set())
        if not tagset_tags:
            # Set doesn't exist or is empty - condition is true (no tag is active)
            return True

        # Check which tags from the set are active
        active_in_set = tagset_tags.intersection(self.active_tags)

        if not active_in_set:
            # No tag from the set is active - condition is true
            return True

        # There are active tags from the set - condition is true only if specified tag is active
        return tag_name in active_in_set

    def is_scope_condition_met(self, scope_type: str) -> bool:
        """
        Check scope:local/parent condition.

        Args:
            scope_type: "local" or "parent"

        Returns:
            True if condition is met:
            - scope:local - true for local scope (origin == "self" or empty)
            - scope:parent - true for parent scope (origin != "self" and not empty)
        """
        if scope_type == "local":
            return not self.origin or self.origin == "self"
        elif scope_type == "parent":
            return bool(self.origin and self.origin != "self")
        return False

    def is_task_provided(self) -> bool:
        """
        Check if non-empty effective task text is provided.

        Takes into account both explicitly specified --task and tasks from active modes.

        Returns:
            True if there is effective task_text (explicit or from modes)
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
    mode_options: ModeOptions = field(default_factory=ModeOptions)  # merged options from modes
    active_tags: Set[str] = field(default_factory=set)  # all active tags

    def get_effective_task_text(self) -> Optional[str]:
        """
        Return effective task text considering priorities.

        Priority:
        1. Explicitly specified --task (if not empty)
        2. Tasks from active modes (combined through paragraphs)
        3. None if neither is specified

        Returns:
            Effective task text or None
        """
        # Priority 1: explicitly specified --task
        if self.options.task_text and self.options.task_text.strip():
            return self.options.task_text

        # Priority 2: tasks from active modes
        mode_tasks = self._collect_mode_tasks()
        if mode_tasks:
            # Combine tasks through double newline (paragraphs)
            return "\n\n".join(mode_tasks)

        # Priority 3: nothing specified
        return None

    def _collect_mode_tasks(self) -> list[str]:
        """
        Collect default_task from all active modes.

        Returns:
            List of non-empty tasks from modes in modeset name order (for determinism)
        """
        modes_config = self.adaptive_loader.get_modes_config()
        tasks = []

        # Sort by modeset name for determinism
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
