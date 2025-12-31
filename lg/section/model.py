from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal

from ..filtering.model import FilterNode

# Path label mode — how file paths are displayed in rendered sections
PathLabelMode = Literal["scope_relative", "relative", "basename"]


@dataclass
class ConditionalAdapterOptions:
    """
    Conditional adapter options.

    If condition is true, specified adapter options are applied.
    """
    condition: str  # Condition as string (e.g., "tag:include-inits")
    options: Dict[str, object] = field(default_factory=dict)  # Adapter options to apply

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> ConditionalAdapterOptions:
        """Create from YAML dictionary."""
        if not isinstance(data, dict):
            raise ValueError("ConditionalAdapterOptions data must be a dictionary")

        if "condition" not in data:
            raise ValueError("ConditionalAdapterOptions must have 'condition' field")

        condition = str(data["condition"])

        # All other keys (except condition) are adapter options
        options = {k: v for k, v in data.items() if k != "condition"}

        return cls(condition=condition, options=options)

@dataclass
class AdapterConfig:
    """
    Adapter configuration with conditional options support.
    """
    base_options: Dict[str, object] = field(default_factory=dict)  # base adapter options
    conditional_options: List[ConditionalAdapterOptions] = field(default_factory=list)  # conditional options

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> AdapterConfig:
        """Create from YAML dictionary."""
        if not isinstance(data, dict):
            return cls(base_options=dict(data) if data else {})

        base_options = {}
        conditional_options = []

        for key, value in data.items():
            if key == "when":
                # Process conditional options
                if isinstance(value, list):
                    for when_item in value:
                        conditional_options.append(ConditionalAdapterOptions.from_dict(when_item))
                else:
                    raise ValueError(f"'when' must be a list, got {type(value)}")
            else:
                # Regular adapter options
                base_options[key] = value

        return cls(base_options=base_options, conditional_options=conditional_options)

@dataclass
class TargetRule:
    """
    Targeted overrides of adapter configurations for specific paths.
    The match field supports string or list of glob strings (relative to repo root).
    All other keys in source YAML inside the rule are treated as adapter names.
    """
    match: List[str] = field(default_factory=list)
    # adapter_name -> raw dict-config (as in section)
    adapter_cfgs: Dict[str, dict] = field(default_factory=dict)

@dataclass
class SectionCfg:
    extensions: List[str] = field(default_factory=lambda: [".py"])
    filters: FilterNode = field(
        default_factory=lambda: FilterNode(mode="block")  # default-allow
    )
    skip_empty: bool = True                  # global rule
    path_labels: PathLabelMode = "scope_relative"      # How to print file markers in section

    # Adapter configs with conditional options support: adapter_name → AdapterConfig
    adapters: Dict[str, AdapterConfig] = field(default_factory=dict)

    # Targeted overrides by paths
    targets: List[TargetRule] = field(default_factory=list)

    @staticmethod
    def from_dict(name: str, node: dict) -> SectionCfg:
        # extensions
        exts = list(map(str, node.get("extensions", [".py"])))
        # filters (now with-conditions are processed inside FilterNode.from_dict)
        filters = FilterNode.from_dict(node.get("filters", {"mode": "block"}))
        # adapters config (everything except service keys)
        service_keys = {"extensions", "filters", "skip_empty", "targets", "path_labels"}
        adapters_cfg: Dict[str, AdapterConfig] = {}
        for k, v in node.items():
            if k in service_keys:
                continue
            if not isinstance(v, dict):
                raise RuntimeError(f"Adapter config for '{k}' in section '{name}' must be a mapping")
            try:
                adapters_cfg[str(k)] = AdapterConfig.from_dict(dict(v))  # type: ignore
            except Exception as e:
                raise RuntimeError(f"Failed to parse adapter config for '{k}' in section '{name}': {e}")

        # targets
        targets_raw = node.get("targets", []) or []
        if not isinstance(targets_raw, list):
            raise RuntimeError(f"Section '{name}': 'targets' must be a list")
        targets: List[TargetRule] = []
        for idx, item in enumerate(targets_raw):
            if not isinstance(item, dict):
                raise RuntimeError(f"Section '{name}': targets[{idx}] must be a mapping")
            if "match" not in item:
                raise RuntimeError(f"Section '{name}': targets[{idx}] missing required key 'match'")
            match_val = item["match"]
            if isinstance(match_val, str):
                match_list = [match_val]
            elif isinstance(match_val, list) and all(isinstance(x, str) for x in match_val):
                match_list = list(match_val)
            else:
                raise RuntimeError(f"Section '{name}': targets[{idx}].match must be string or list of strings")
            adapter_cfgs: Dict[str, dict] = {}
            for ak, av in item.items():
                if ak == "match":
                    continue
                if not isinstance(av, dict):
                    raise RuntimeError(f"Section '{name}': targets[{idx}].{ak} must be a mapping (adapter cfg)")
                adapter_cfgs[str(ak)] = dict(av)  # type: ignore
            targets.append(TargetRule(match=match_list, adapter_cfgs=adapter_cfgs))

        # path_labels
        path_labels = str(node.get("path_labels", "scope_relative")).strip().lower()
        if path_labels not in ("scope_relative", "relative", "basename"):
            raise RuntimeError(f"Section '{name}': invalid path_labels='{path_labels}' (allowed: scope_relative|relative|basename|off)")

        return SectionCfg(
            extensions=exts,
            filters=filters,
            skip_empty=bool(node.get("skip_empty", True)),
            path_labels=path_labels,
            adapters=adapters_cfg,
            targets=targets,
        )

EmptyPolicy = Literal["inherit", "include", "exclude"]
