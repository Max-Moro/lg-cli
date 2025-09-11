from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .cache.fs_cache import Cache
from .types import RunOptions
from .vcs import VcsProvider
from .stats import TokenService


@dataclass(frozen=True)
class RunContext:
    root: Path
    options: RunOptions
    cache: Cache
    vcs: VcsProvider
    tokenizer: TokenService
