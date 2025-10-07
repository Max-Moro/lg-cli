from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal

Mode = Literal["allow", "block"]


@dataclass
class ConditionalFilter:
    """
    Условное правило фильтрации файлов.
    
    Если условие истинно, применяются указанные allow/block правила.
    """
    condition: str  # Условие в виде строки (например, "tag:python AND NOT tag:minimal")
    allow: List[str] = field(default_factory=list)  # Дополнительные allow паттерны
    block: List[str] = field(default_factory=list)  # Дополнительные block паттерны
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConditionalFilter":
        """Создает экземпляр из словаря YAML."""
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
    Узел фильтрации.

    • `mode`:  "allow"  → default-deny,  "block" → default-allow
    • `allow`: белый список; `block`: чёрный список.
      При совпадении с обоими списками побеждает block.
    • `children`: переопределения для подпапок (имя папки → FilterNode).
    • `conditional_filters`: условные правила фильтрации для данного узла.
    """
    mode: Mode
    allow: List[str] = field(default_factory=list)
    block: List[str] = field(default_factory=list)
    children: Dict[str, "FilterNode"] = field(default_factory=dict)
    conditional_filters: List[ConditionalFilter] = field(default_factory=list)

    @classmethod
    def from_dict(cls, obj: dict, path: str = "") -> FilterNode:
        """
        Построить FilterNode рекурсивно из словаря из конфига.
        path — внутренний путь для ошибок/ворнингов.
        """
        if "mode" not in obj:
            raise RuntimeError(f"Missing 'mode' in filters at '{path or '/'}'")

        # Парсим условные фильтры (when)
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
