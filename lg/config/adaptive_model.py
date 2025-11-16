"""
Data models for the adaptive capabilities system.
Contains classes for modes, tags and their sets with YAML serialization support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any, Literal, Optional


@dataclass
class Mode:
    """
    Mode - specific option within a mode set.

    Activates certain tags and may contain special settings.
    """
    title: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)
    default_task: Optional[str] = None  # Default task description for the mode

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Mode":
        """Create instance from dictionary (from YAML)."""
        return cls(
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            tags=list(data.get("tags", [])),
            default_task=data.get("default_task"),
            options=dict(data.get("options", {})) if "options" in data else {
                k: v for k, v in data.items()
                if k not in {"title", "description", "tags", "default_task"}
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for YAML."""
        result: Dict[str, Any] = {"title": self.title}
        if self.description:
            result["description"] = self.description
        if self.tags:
            result["tags"] = self.tags
        if self.default_task is not None:
            result["default_task"] = self.default_task
        # Add additional options directly
        result.update(self.options)
        return result


@dataclass
class ModeSet:
    """
    Mode set - group of mutually exclusive options.

    Represents a specific aspect of work (e.g., "AI interaction method").
    """
    title: str
    modes: Dict[str, Mode] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModeSet":
        """Create instance from dictionary (from YAML)."""
        modes = {}
        modes_data = data.get("modes", {})
        for mode_name, mode_data in modes_data.items():
            if isinstance(mode_data, dict):
                modes[mode_name] = Mode.from_dict(mode_data)
            else:
                # Simplified form: title only
                modes[mode_name] = Mode(title=str(mode_data))

        return cls(
            title=str(data.get("title", "")),
            modes=modes
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for YAML."""
        return {
            "title": self.title,
            "modes": {name: mode.to_dict() for name, mode in self.modes.items()}
        }


@dataclass
class Tag:
    """
    Tag - atomic filtering element.

    Can be activated or deactivated to configure generated contexts.
    """
    title: str
    description: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any] | str) -> "Tag":
        """Create instance from dictionary or string (from YAML)."""
        if isinstance(data, str):
            return cls(title=data)
        return cls(
            title=str(data.get("title", "")),
            description=str(data.get("description", ""))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for YAML."""
        result = {"title": self.title}
        if self.description:
            result["description"] = self.description
        return result


@dataclass
class TagSet:
    """
    Tag set - group of related tags.

    Represents a specific category (e.g., "Programming languages").
    """
    title: str
    tags: Dict[str, Tag] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TagSet":
        """Create instance from dictionary (from YAML)."""
        tags = {}
        tags_data = data.get("tags", {})
        for tag_name, tag_data in tags_data.items():
            tags[tag_name] = Tag.from_dict(tag_data)

        return cls(
            title=str(data.get("title", "")),
            tags=tags
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for YAML."""
        return {
            "title": self.title,
            "tags": {name: tag.to_dict() for name, tag in self.tags.items()}
        }


@dataclass
class ModesConfig:
    """
    Complete modes configuration from modes.yaml.
    """
    mode_sets: Dict[str, ModeSet] = field(default_factory=dict)
    include: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModesConfig":
        """Create instance from dictionary (from YAML)."""
        mode_sets = {}
        mode_sets_data = data.get("mode-sets", {})
        for set_name, set_data in mode_sets_data.items():
            mode_sets[set_name] = ModeSet.from_dict(set_data)

        return cls(
            mode_sets=mode_sets,
            include=list(data.get("include", []))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for YAML."""
        result = {}
        if self.mode_sets:
            result["mode-sets"] = {name: mode_set.to_dict() for name, mode_set in self.mode_sets.items()}
        if self.include:
            result["include"] = self.include
        return result


@dataclass
class TagsConfig:
    """
    Complete tags configuration from tags.yaml.
    """
    tag_sets: Dict[str, TagSet] = field(default_factory=dict)
    global_tags: Dict[str, Tag] = field(default_factory=dict)
    include: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TagsConfig":
        """Create instance from dictionary (from YAML)."""
        # Tag sets
        tag_sets = {}
        tag_sets_data = data.get("tag-sets", {})
        for set_name, set_data in tag_sets_data.items():
            tag_sets[set_name] = TagSet.from_dict(set_data)

        # Global tags (not part of specific sets)
        global_tags = {}
        global_tags_data = data.get("tags", {})
        for tag_name, tag_data in global_tags_data.items():
            global_tags[tag_name] = Tag.from_dict(tag_data)

        return cls(
            tag_sets=tag_sets,
            global_tags=global_tags,
            include=list(data.get("include", []))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for YAML."""
        result = {}
        if self.tag_sets:
            result["tag-sets"] = {name: tag_set.to_dict() for name, tag_set in self.tag_sets.items()}
        if self.global_tags:
            result["tags"] = {name: tag.to_dict() for name, tag in self.global_tags.items()}
        if self.include:
            result["include"] = self.include
        return result


# Default standard configuration
DEFAULT_MODES_CONFIG = ModesConfig(
    mode_sets={
        "ai-interaction": ModeSet(
            title="AI interaction method",
            modes={
                "ask": Mode(
                    title="Ask",
                    description="Basic question-answer mode"
                ),
                "agent": Mode(
                    title="Agent work",
                    description="Mode with tools",
                    tags=["agent", "tools"],
                    options={"allow_tools": True}
                )
            }
        ),
        "dev-stage": ModeSet(
            title="Dev stage",
            modes={
                "planning": Mode(
                    title="Planning",
                    tags=["architecture", "docs"]
                ),
                "code-writing": Mode(
                    title="Code writing"
                ),
                "tests-writing": Mode(
                    title="Tests writing",
                    tags=["tests"],
                    default_task="Write tests for the current functional block."
                ),
                "review": Mode(
                    title="Code review",
                    tags=["review"],
                    options={"vcs_mode": "branch-changes"},
                    default_task="Conduct code review of changes and provide improvement recommendations."
                )
            }
        )
    }
)

DEFAULT_TAGS_CONFIG = TagsConfig(
    tag_sets={
        "language": TagSet(
            title="Programming languages",
            tags={
                "python": Tag(title="Python"),
                "typescript": Tag(title="TypeScript"),
                "javascript": Tag(title="JavaScript")
            }
        ),
        "code-type": TagSet(
            title="Code type",
            tags={
                "product": Tag(title="Product code"),
                "tests": Tag(title="Test code"),
                "generated": Tag(title="Generated code")
            }
        )
    },
    global_tags={
        "agent": Tag(title="Agent capabilities"),
        "review": Tag(title="Code review guidelines"),
        "architecture": Tag(title="Architecture documentation"),
        "docs": Tag(title="Documentation"),
        "tools": Tag(title="Tools")
    }
)


@dataclass
class ModeOptions:
    """
    Typed container for merged options from all active modes.

    Contains all possible options that can be defined in modes,
    with reasonable default values.
    """
    # VCS options
    vcs_mode: Literal["all", "changes", "branch-changes"] = "all"

    # Tool capabilities
    allow_tools: bool = False  # permission to use tools in agent mode

    # Additional options can be added as needed

    @classmethod
    def merge_from_modes(cls, modes_config: ModesConfig, active_modes: Dict[str, str]) -> ModeOptions:
        """
        Create MergedModeOptions by merging options from all active modes.

        Args:
            modes_config: Configuration of all available modes
            active_modes: Dictionary of active modes {modeset_name: mode_name}

        Returns:
            MergedModeOptions with combined settings
        """
        result = cls()

        # Iterate through all active modes and collect their options
        for modeset_name, mode_name in active_modes.items():
            modeset = modes_config.mode_sets.get(modeset_name)
            if not modeset:
                continue

            mode = modeset.modes.get(mode_name)
            if not mode or not mode.options:
                continue

            # Merge options into typed dataclass
            for option_key, option_value in mode.options.items():
                if option_key == "vcs_mode" and isinstance(option_value, str):
                    if option_value in ("all", "changes", "branch-changes"):
                        result.vcs_mode = option_value  # type: ignore
                elif option_key == "allow_tools" and isinstance(option_value, bool):
                    result.allow_tools = option_value
                # Additional option handling can be added here

        return result