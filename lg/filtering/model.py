from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal

Mode = Literal["allow", "block"]


@dataclass
class ConditionalFilter:
    """
    Conditional file filtering rule.

    If the condition is true, the specified allow/block rules are applied.
    """
    condition: str  # Condition as a string (e.g., "tag:python AND NOT tag:minimal")
    allow: List[str] = field(default_factory=list)  # Additional allow patterns
    block: List[str] = field(default_factory=list)  # Additional block patterns

    @classmethod
    def from_dict(cls, data: dict) -> "ConditionalFilter":
        """Creates an instance from a YAML dictionary."""
        if "condition" not in data:
            raise ValueError("ConditionalFilter requires 'condition' field")

        return cls(
            condition=str(data["condition"]),
            allow=list(data.get("allow", [])),
            block=list(data.get("block", []))
        )


@dataclass
class FilterNode:
    """
    Filter node.

    • `mode`: "allow" → default-deny, "block" → default-allow
    • `allow`: whitelist; `block`: blacklist.
      When matching both lists, block wins.
    • `children`: overrides for subdirectories (folder name → FilterNode).
    • `conditional_filters`: conditional filtering rules for this node.
    """
    mode: Mode
    allow: List[str] = field(default_factory=list)
    block: List[str] = field(default_factory=list)
    children: Dict[str, "FilterNode"] = field(default_factory=dict)
    conditional_filters: List[ConditionalFilter] = field(default_factory=list)

    @classmethod
    def from_dict(cls, obj: dict, path: str = "") -> FilterNode:
        """
        Recursively build a FilterNode from a config dictionary.
        path - internal path for errors/warnings.
        """
        if "mode" not in obj:
            raise RuntimeError(f"Missing 'mode' in filters at '{path or '/'}'")

        # Parse conditional filters (when)
        conditional_filters: List[ConditionalFilter] = []
        when_raw = obj.get("when", []) or []
        if when_raw:
            if not isinstance(when_raw, list):
                raise RuntimeError(f"Filter at '{path or '/'}': 'when' must be a list")
            for idx, when_item in enumerate(when_raw):
                if not isinstance(when_item, dict):
                    raise RuntimeError(f"Filter at '{path or '/'}': when[{idx}] must be a mapping")
                try:
                    conditional_filters.append(ConditionalFilter.from_dict(when_item))
                except Exception as e:
                    raise RuntimeError(f"Filter at '{path or '/'}': when[{idx}] - {e}")

        node = cls(
            mode=obj["mode"],
            allow=obj.get("allow", []),
            block=obj.get("block", []),
            conditional_filters=conditional_filters,
        )

        for child_name, child_obj in obj.get("children", {}).items():
            node.children[child_name] = cls.from_dict(
                child_obj, f"{path}/{child_name}"
            )
        return node
