from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lg.cache.fs_cache import Cache
from lg.types import RunOptions
from lg.vcs import VcsProvider


@dataclass(frozen=True)
class RunContext:
    root: Path
    options: RunOptions
    cache: Cache
    vcs: VcsProvider
