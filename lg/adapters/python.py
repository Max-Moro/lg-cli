from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lg.adapters.base import BaseAdapter

@dataclass
class LangPython:
    skip_empty: bool = True
    skip_trivial_inits: bool = True
    trivial_init_max_noncomment: int = 1


@BaseAdapter.register
class PythonAdapter(BaseAdapter):
    name = "python"
    extensions = {".py"}
    config_cls = LangPython

    # --------------------------------------------------------------------- #
    def should_skip(self, path: Path, text: str, cfg: LangPython) -> bool:  # type: ignore[override]
        # 1) полностью пустой файл
        if cfg.skip_empty and not text.strip():
            return True

        # 2) тривиальный __init__.py
        if cfg.skip_trivial_inits and path.name == "__init__.py":
            significant = [
                ln.strip()
                for ln in text.splitlines()
                if ln.strip() and not ln.lstrip().startswith("#")
            ]
            limit = int(cfg.trivial_init_max_noncomment)
            if len(significant) <= limit and all(
                ln in ("pass", "...") for ln in significant
            ):
                return True

        return False
