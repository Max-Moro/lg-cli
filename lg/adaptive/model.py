"""
Data models for the new adaptive modes and tags system.

Defines core types for modes, mode-sets, tags, tag-sets,
and the aggregate AdaptiveModel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Any, Set


# Type alias for runs map: provider_id -> command/args
RunsMap = Dict[str, str]

# VCS mode type
VcsMode = Literal["all", "changes", "branch-changes"]


@dataclass
class Mode:
    """
    A specific mode within a mode-set.

    Modes can activate tags and define provider-specific run commands.
    """
    id: str
    title: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    default_task: Optional[str] = None
    vcs_mode: VcsMode = "all"
    runs: RunsMap = field(default_factory=dict)

    @classmethod
    def from_dict(cls, mode_id: str, data: Dict[str, Any]) -> Mode:
        """Create Mode from YAML dictionary."""
        if isinstance(data, str):
            # Short form: just title
            return cls(id=mode_id, title=data)

        return cls(
            id=mode_id,
            title=str(data.get("title", mode_id)),
            description=str(data.get("description", "")),
            tags=list(data.get("tags", [])),
            default_task=data.get("default_task"),
            vcs_mode=data.get("vcs_mode", "all"),
            runs=dict(data.get("runs", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for YAML/JSON."""
        result: Dict[str, Any] = {"title": self.title}
        if self.description:
            result["description"] = self.description
        if self.tags:
            result["tags"] = self.tags
        if self.default_task:
            result["default_task"] = self.default_task
        if self.vcs_mode != "all":
            result["vcs_mode"] = self.vcs_mode
        if self.runs:
            result["runs"] = self.runs
        return result

    def has_provider(self, provider_id: str) -> bool:
        """Check if mode supports given provider."""
        return provider_id in self.runs

    def get_supported_providers(self) -> Set[str]:
        """Get set of all supported provider IDs."""
        return set(self.runs.keys())


@dataclass
class ModeSet:
    """
    A group of mutually exclusive modes.

    Mode-sets are either "integration" (have runs) or "content" (no runs).
    """
    id: str
    title: str
    modes: Dict[str, Mode] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, set_id: str, data: Dict[str, Any]) -> ModeSet:
        """Create ModeSet from YAML dictionary."""
        modes = {}
        modes_data = data.get("modes", {})
        for mode_id, mode_data in modes_data.items():
            modes[mode_id] = Mode.from_dict(mode_id, mode_data)

        return cls(
            id=set_id,
            title=str(data.get("title", set_id)),
            modes=modes,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for YAML/JSON."""
        return {
            "title": self.title,
            "modes": {mode_id: mode.to_dict() for mode_id, mode in self.modes.items()},
        }

    @property
    def is_integration(self) -> bool:
        """True if any mode has runs defined (integration mode-set)."""
        return any(mode.runs for mode in self.modes.values())

    def get_mode(self, mode_id: str) -> Optional[Mode]:
        """Get mode by ID."""
        return self.modes.get(mode_id)

    def get_supported_providers(self) -> Set[str]:
        """Get union of all providers supported by modes in this set."""
        providers: Set[str] = set()
        for mode in self.modes.values():
            providers.update(mode.get_supported_providers())
        return providers

    def filter_by_provider(self, provider_id: str) -> ModeSet:
        """
        Return new ModeSet with only modes that support given provider.

        For content mode-sets (no runs), returns self unchanged.
        For integration mode-sets, filters out modes without runs for provider.
        """
        if not self.is_integration:
            return self

        filtered_modes = {
            mode_id: mode
            for mode_id, mode in self.modes.items()
            if mode.has_provider(provider_id)
        }

        return ModeSet(
            id=self.id,
            title=self.title,
            modes=filtered_modes,
        )


@dataclass
class Tag:
    """An atomic filtering tag."""
    id: str
    title: str
    description: str = ""

    @classmethod
    def from_dict(cls, tag_id: str, data: Any) -> Tag:
        """Create Tag from YAML dictionary or string."""
        if isinstance(data, str):
            return cls(id=tag_id, title=data)
        if isinstance(data, dict):
            return cls(
                id=tag_id,
                title=str(data.get("title", tag_id)),
                description=str(data.get("description", "")),
            )
        return cls(id=tag_id, title=tag_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for YAML/JSON."""
        result: Dict[str, Any] = {"title": self.title}
        if self.description:
            result["description"] = self.description
        return result


@dataclass
class TagSet:
    """A group of related tags."""
    id: str
    title: str
    tags: Dict[str, Tag] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, set_id: str, data: Dict[str, Any]) -> TagSet:
        """Create TagSet from YAML dictionary."""
        tags = {}
        tags_data = data.get("tags", {})
        for tag_id, tag_data in tags_data.items():
            tags[tag_id] = Tag.from_dict(tag_id, tag_data)

        return cls(
            id=set_id,
            title=str(data.get("title", set_id)),
            tags=tags,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for YAML/JSON."""
        return {
            "title": self.title,
            "tags": {tag_id: tag.to_dict() for tag_id, tag in self.tags.items()},
        }

    def get_tag(self, tag_id: str) -> Optional[Tag]:
        """Get tag by ID."""
        return self.tags.get(tag_id)


@dataclass
class AdaptiveModel:
    """
    Complete adaptive model for a context or section.

    Contains all mode-sets and tag-sets after resolution and merging.
    """
    mode_sets: Dict[str, ModeSet] = field(default_factory=dict)
    tag_sets: Dict[str, TagSet] = field(default_factory=dict)

    def get_mode_set(self, set_id: str) -> Optional[ModeSet]:
        """Get mode-set by ID."""
        return self.mode_sets.get(set_id)

    def get_tag_set(self, set_id: str) -> Optional[TagSet]:
        """Get tag-set by ID."""
        return self.tag_sets.get(set_id)

    def get_integration_mode_sets(self) -> List[ModeSet]:
        """Get all integration mode-sets (those with runs)."""
        return [ms for ms in self.mode_sets.values() if ms.is_integration]

    def get_content_mode_sets(self) -> List[ModeSet]:
        """Get all content mode-sets (those without runs)."""
        return [ms for ms in self.mode_sets.values() if not ms.is_integration]

    def get_integration_mode_set(self) -> Optional[ModeSet]:
        """
        Get the single integration mode-set.

        Returns None if no integration mode-set exists.
        Use validate_single_integration() to check for multiple.
        """
        integration_sets = self.get_integration_mode_sets()
        if len(integration_sets) == 1:
            return integration_sets[0]
        return None

    def validate_single_integration(self, context_name: str = "") -> None:
        """
        Validate that exactly one integration mode-set exists.

        Raises:
            MultipleIntegrationModeSetsError: if > 1 integration mode-set
            NoIntegrationModeSetError: if 0 integration mode-sets
        """
        from .errors import MultipleIntegrationModeSetsError, NoIntegrationModeSetError

        integration_sets = self.get_integration_mode_sets()
        if len(integration_sets) > 1:
            raise MultipleIntegrationModeSetsError(
                mode_sets=[ms.id for ms in integration_sets],
                context_name=context_name,
            )
        if len(integration_sets) == 0:
            raise NoIntegrationModeSetError(context_name=context_name)

    def filter_by_provider(self, provider_id: str) -> AdaptiveModel:
        """
        Return new AdaptiveModel with modes filtered by provider.

        - Content mode-sets are included unchanged
        - Integration mode-set is filtered to only modes supporting provider
        """
        filtered_mode_sets = {}
        for set_id, mode_set in self.mode_sets.items():
            filtered_mode_sets[set_id] = mode_set.filter_by_provider(provider_id)

        return AdaptiveModel(
            mode_sets=filtered_mode_sets,
            tag_sets=self.tag_sets,  # Tag-sets unchanged
        )

    def get_all_tag_ids(self) -> Set[str]:
        """Get set of all tag IDs from all tag-sets."""
        result: Set[str] = set()
        for tag_set in self.tag_sets.values():
            result.update(tag_set.tags.keys())
        return result

    def has_mode(self, modeset_id: str, mode_id: str) -> bool:
        """Check if specific mode exists in model."""
        mode_set = self.mode_sets.get(modeset_id)
        if not mode_set:
            return False
        return mode_id in mode_set.modes

    def merge_with(self, other: AdaptiveModel) -> AdaptiveModel:
        """
        Merge with another model (other takes priority on conflicts).

        Used for extends resolution: parent.merge_with(child).
        """
        # Merge mode-sets
        merged_mode_sets = dict(self.mode_sets)
        for set_id, other_set in other.mode_sets.items():
            if set_id in merged_mode_sets:
                # Merge modes within set (other wins on conflict)
                existing = merged_mode_sets[set_id]
                merged_modes = dict(existing.modes)
                merged_modes.update(other_set.modes)
                merged_mode_sets[set_id] = ModeSet(
                    id=set_id,
                    title=other_set.title,  # Child title wins
                    modes=merged_modes,
                )
            else:
                merged_mode_sets[set_id] = other_set

        # Merge tag-sets
        merged_tag_sets = dict(self.tag_sets)
        for set_id, other_set in other.tag_sets.items():
            if set_id in merged_tag_sets:
                # Merge tags within set (other wins on conflict)
                existing = merged_tag_sets[set_id]
                merged_tags = dict(existing.tags)
                merged_tags.update(other_set.tags)
                merged_tag_sets[set_id] = TagSet(
                    id=set_id,
                    title=other_set.title,  # Child title wins
                    tags=merged_tags,
                )
            else:
                merged_tag_sets[set_id] = other_set

        return AdaptiveModel(
            mode_sets=merged_mode_sets,
            tag_sets=merged_tag_sets,
        )

    def is_empty(self) -> bool:
        """Check if model has no mode-sets and no tag-sets."""
        return not self.mode_sets and not self.tag_sets


__all__ = [
    "RunsMap",
    "VcsMode",
    "Mode",
    "ModeSet",
    "Tag",
    "TagSet",
    "AdaptiveModel",
]
