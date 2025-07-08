from __future__ import annotations
from pathlib import Path
from typing import Dict, List

from lg.adapters.base import BaseAdapter

@BaseAdapter.register
class PythonAdapter(BaseAdapter):
    name = "python"
    extensions = {".py"}

    DEFAULTS: Dict[str, object] = {
        "skip_empty": True,
        "skip_trivial_inits": True,
        "trivial_init_max_noncomment": 1,
    }

    # --------------------------------------------------------------------- #
    def should_skip(self, path: Path, text: str, cfg: Dict) -> bool:
        """
        cfg — **только** содержимое секции \"python\" из listing_config.json
        (если секции нет, сюда придёт пустой dict → действуют DEFAULTS).
        """
        # итоговые параметры = DEFAULTS ⊕ секция python
        p = {**self.DEFAULTS, **cfg}

        # 1) полностью пустой файл
        if p["skip_empty"] and not text.strip():
            return True

        # 2) тривиальный __init__.py
        if (
            p["skip_trivial_inits"]
            and path.name == "__init__.py"
        ):
            significant = [
                ln.strip()
                for ln in text.splitlines()
                if ln.strip() and not ln.lstrip().startswith("#")
            ]
            limit = int(p["trivial_init_max_noncomment"])
            if len(significant) <= limit and all(
                ln in ("pass", "...") for ln in significant
            ):
                return True

        return False
