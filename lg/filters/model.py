from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal

Mode = Literal["allow", "block"]


@dataclass
class FilterNode:
    """
    Узел фильтрации.

    • `mode`:  "allow"  → default-deny,  "block" → default-allow
    • `allow`: белый список; `block`: чёрный список.
      При совпадении с обоими списками побеждает block.
    • `children`: переопределения для подпапок (имя папки → FilterNode).
    """
    mode: Mode
    allow: List[str] = field(default_factory=list)
    block: List[str] = field(default_factory=list)
    children: Dict[str, "FilterNode"] = field(default_factory=dict)

    def empty_allow_warning(self) -> bool:
        """True, если mode == 'allow' и список allow пуст — повод предупредить."""
        return self.mode == "allow" and not self.allow

    @classmethod
    def from_dict(cls, obj: dict[str, any], path: str = "") -> FilterNode:
        """
        Построить FilterNode рекурсивно из словаря из конфига.
        path — внутренний путь для ошибок/ворнингов.
        """
        if "mode" not in obj:
            raise RuntimeError(f"Missing 'mode' in filters at '{path or '/'}'")

        node = cls(
            mode=obj["mode"],
            allow=obj.get("allow", []),
            block=obj.get("block", []),
        )
        if node.empty_allow_warning():
            import logging
            logging.warning(
                "Filter at '%s' has mode=allow but empty allow-list → everything denied",
                path or "/",
            )

        for child_name, child_obj in obj.get("children", {}).items():
            node.children[child_name] = cls.from_dict(
                child_obj, f"{path}/{child_name}"
            )
        return node
