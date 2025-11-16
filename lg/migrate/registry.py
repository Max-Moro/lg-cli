from __future__ import annotations

from typing import Iterable, List, Optional, Protocol, Sequence


class Migration(Protocol):
    """Strict migration contract."""
    id: int
    title: str

    """
    MUST exit quickly (return False) if the migration is not needed.
    Return True if the lg-cfg/ content was actually changed.
    If side effects are needed when allow_side_effects=False — raise PreflightRequired.
    Any other exceptions are treated as migration errors (phase "run").
    """
    def run(self, fs: "CfgFs", *, allow_side_effects: bool) -> bool: ...   # noqa: E701


_MIGRATIONS: List[Migration] = []
_FROZEN: Optional[Sequence[Migration]] = None


def register(migration: Migration) -> None:
    """Registration of a single migration."""
    global _FROZEN
    if _FROZEN is not None:
        # Protect against late registration after the first request for the list
        raise RuntimeError("Migrations are already frozen; call register/register_many before get_migrations()")
    _MIGRATIONS.append(migration)

def register_many(migrations: Iterable[Migration]) -> None:
    """Batch registration of migrations."""
    global _FROZEN
    if _FROZEN is not None:
        raise RuntimeError("Migrations are already frozen; call register_many before get_migrations()")
    _MIGRATIONS.extend(migrations)

def get_migrations() -> List[Migration]:
    """
    Returns migrations sorted by id (ascending).
    Sorting and "freezing" happen once on the first call.
    """
    global _FROZEN
    if _FROZEN is None:
        _FROZEN = tuple(sorted(_MIGRATIONS, key=lambda m: m.id))
    return list(_FROZEN)


# Lazy import subscription to the CfgFs type (avoid cycles)
class CfgFs:  # pragma: no cover - type hint
    pass

__all__ = ["Migration", "register", "register_many", "get_migrations"]
