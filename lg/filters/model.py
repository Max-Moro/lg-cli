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

    # ------------------ вспомогательные методы ------------------ #
    def empty_allow_warning(self) -> bool:
        """True, если mode == 'allow' и список allow пуст — повод предупредить."""
        return self.mode == "allow" and not self.allow
