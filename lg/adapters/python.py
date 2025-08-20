from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .base import BaseAdapter
from ..config import EmptyPolicy


@dataclass
class PythonCfg:
    empty_policy: EmptyPolicy = "inherit"
    skip_trivial_inits: bool = True
    trivial_init_max_noncomment: int = 1


class PythonAdapter(BaseAdapter[PythonCfg]):
    name = "python"
    extensions = {".py"}

    # --------------------------------------------------------------------- #
    def should_skip(self, path: Path, text: str) -> bool:  # type: ignore[override]
        if self.cfg.skip_trivial_inits and path.name == "__init__.py":
            significant = [
                ln.strip()
                for ln in text.splitlines()
                if ln.strip() and not ln.lstrip().startswith("#")
            ]
            limit = int(self.cfg.trivial_init_max_noncomment)
            if len(significant) <= limit and all(
                ln in ("pass", "...") for ln in significant
            ):
                return True

        return False
