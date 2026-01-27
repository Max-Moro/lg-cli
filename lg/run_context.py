from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Set

from .cache.fs_cache import Cache
from .types import RunOptions
from .git import VcsProvider
from .git.gitignore import GitIgnoreService
from .stats import TokenService
from .addressing import AddressingContext


# ---- Provider normalization ----

_PROVIDER_SUFFIXES = (".cli", ".ext", ".api")


def normalize_provider_id(provider_id: str) -> str:
    """
    Normalize provider ID by stripping technical suffix.

    Removes the last segment indicating the technical medium:
    - .cli — CLI tool
    - .ext — IDE extension
    - .api — direct API call

    If no known suffix is present (e.g., 'clipboard'), returns as-is.

    Args:
        provider_id: Full provider ID (e.g., 'com.anthropic.claude.cli')

    Returns:
        Base provider ID (e.g., 'com.anthropic.claude')
    """
    for suffix in _PROVIDER_SUFFIXES:
        if provider_id.endswith(suffix):
            return provider_id[:-len(suffix)]
    return provider_id


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
    provider_base_id: Optional[str] = None

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

    def is_tagonly_condition_met(self, set_name: str, tag_name: str) -> bool:
        """
        Check TAGONLY:set_name:tag_name condition.

        Rules:
        - True only if specified tag is active AND it's the only active tag from the set
        - False if tag is not active
        - False if other tags from the set are also active
        - False if no tags from the set are active
        """
        tagset_tags = self.tagsets.get(set_name, set())
        if not tagset_tags:
            # Set doesn't exist or is empty - condition is false
            return False

        # Check which tags from the set are active
        active_in_set = tagset_tags.intersection(self.active_tags)

        # True only if exactly one tag is active and it's the specified one
        return active_in_set == {tag_name}

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

    def is_provider_condition_met(self, base_id: str) -> bool:
        """
        Check provider:<base-id> condition.

        True if --provider was specified and its normalized base-id
        matches the given base_id.

        Args:
            base_id: Expected provider base ID (e.g., 'com.anthropic.claude')

        Returns:
            True if provider matches, False otherwise
        """
        if not self.provider_base_id:
            return False
        return self.provider_base_id == base_id


@dataclass(frozen=True)
class RunContext:
    root: Path
    options: RunOptions
    cache: Cache
    vcs: VcsProvider
    gitignore: Optional[GitIgnoreService]  # None if no .git directory
    tokenizer: TokenService
    addressing: AddressingContext
