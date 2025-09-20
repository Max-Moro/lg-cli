from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Any

from ..io.model import FilterNode, ConditionalFilter
from ..types import PathLabelMode


@dataclass
class ConditionalAdapterOptions:
    """
    Условные опции адаптера.

    Если условие истинно, применяются указанные опции адаптера.
    """
    condition: str  # Условие в виде строки (например, "tag:include-inits")
    options: Dict[str, Any] = field(default_factory=dict)  # Опции адаптера для применения

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConditionalAdapterOptions:
        """Создание из словаря YAML."""
        if not isinstance(data, dict):
            raise ValueError("ConditionalAdapterOptions data must be a dictionary")

        if "condition" not in data:
            raise ValueError("ConditionalAdapterOptions must have 'condition' field")

        condition = str(data["condition"])

        # Все остальные ключи (кроме condition) являются опциями адаптера
        options = {k: v for k, v in data.items() if k != "condition"}

        return cls(condition=condition, options=options)

@dataclass
class AdapterConfig:
    """
    Конфигурация адаптера с поддержкой условных опций.
    """
    base_options: Dict[str, Any] = field(default_factory=dict)  # базовые опции адаптера
    conditional_options: List[ConditionalAdapterOptions] = field(default_factory=list)  # условные опции
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AdapterConfig:
        """Создание из словаря YAML."""
        if not isinstance(data, dict):
            return cls(base_options=dict(data) if data else {})
        
        base_options = {}
        conditional_options = []
        
        for key, value in data.items():
            if key == "when":
                # Обрабатываем условные опции
                if isinstance(value, list):
                    for when_item in value:
                        conditional_options.append(ConditionalAdapterOptions.from_dict(when_item))
                else:
                    raise ValueError(f"'when' must be a list, got {type(value)}")
            else:
                # Обычные опции адаптера
                base_options[key] = value
        
        return cls(base_options=base_options, conditional_options=conditional_options)

@dataclass
class TargetRule:
    """
    Адресные оверрайды конфигураций адаптеров для конкретных путей.
    Поле match поддерживает строку или список строк-глобов (относительно корня репо).
    Все остальные ключи в исходном YAML внутри правила трактуются как имена адаптеров.
    """
    match: List[str] = field(default_factory=list)
    # имя_адаптера -> сырой dict-конфиг (как в секции)
    adapter_cfgs: Dict[str, Dict] = field(default_factory=dict)

@dataclass
class SectionCfg:
    extensions: List[str] = field(default_factory=lambda: [".py"])
    filters: FilterNode = field(
        default_factory=lambda: FilterNode(mode="block")  # default-allow
    )
    skip_empty: bool = True                  # глобальное правило
    code_fence: bool = True                  # оборачивать файлы в ```{lang}
    path_labels: PathLabelMode = "auto"      # Как печатать файл-маркеры в секции

    # Конфиги адаптеров с поддержкой условных опций: имя_адаптера → AdapterConfig
    adapters: Dict[str, AdapterConfig] = field(default_factory=dict)

    # Адресные оверрайды по путям
    targets: List[TargetRule] = field(default_factory=list)
    
    # Условные фильтры
    conditional_filters: List[ConditionalFilter] = field(default_factory=list)

    @staticmethod
    def from_dict(name: str, node: dict) -> "SectionCfg":
        # extensions
        exts = list(map(str, node.get("extensions", [".py"])))
        # filters
        filters = FilterNode.from_dict(node.get("filters", {"mode": "block"}))
        # adapters config (всё, что не service keys)
        service_keys = {"extensions", "filters", "skip_empty", "code_fence", "targets", "path_labels", "when"}
        adapters_cfg: Dict[str, AdapterConfig] = {}
        for k, v in node.items():
            if k in service_keys:
                continue
            if not isinstance(v, dict):
                raise RuntimeError(f"Adapter config for '{k}' in section '{name}' must be a mapping")
            try:
                adapters_cfg[str(k)] = AdapterConfig.from_dict(dict(v))
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
                adapter_cfgs[str(ak)] = dict(av)
            targets.append(TargetRule(match=match_list, adapter_cfgs=adapter_cfgs))

        # conditional filters (when)
        conditional_filters: List[ConditionalFilter] = []
        when_raw = node.get("when", []) or []
        if when_raw:
            if not isinstance(when_raw, list):
                raise RuntimeError(f"Section '{name}': 'when' must be a list")
            for idx, when_item in enumerate(when_raw):
                if not isinstance(when_item, dict):
                    raise RuntimeError(f"Section '{name}': when[{idx}] must be a mapping")
                try:
                    conditional_filters.append(ConditionalFilter.from_dict(when_item))
                except Exception as e:
                    raise RuntimeError(f"Section '{name}': when[{idx}] - {e}")

        # path_labels
        path_labels = str(node.get("path_labels", "auto")).strip().lower()
        if path_labels not in ("auto", "relative", "basename", "off"):
            raise RuntimeError(f"Section '{name}': invalid path_labels='{path_labels}' (allowed: auto|relative|basename|off)")

        return SectionCfg(
            extensions=exts,
            filters=filters,
            code_fence=bool(node.get("code_fence", True)),
            skip_empty=bool(node.get("skip_empty", True)),
            path_labels=path_labels,
            adapters=adapters_cfg,
            targets=targets,
            conditional_filters=conditional_filters,
        )

@dataclass
class Config:
    sections: Dict[str, SectionCfg] = field(default_factory=dict)

EmptyPolicy = Literal["inherit", "include", "exclude"]
