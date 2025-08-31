from __future__ import annotations

from typing import Iterable, List, Optional, Protocol, Sequence


class Migration(Protocol):
    """Строгий контракт миграции."""
    id: int
    title: str

    """
    ДОЛЖНА быстро выйти (return False), если миграция не нужна.
    Вернуть True, если реально изменила содержимое lg-cfg/.
    Если нужны сайд-эффекты при allow_side_effects=False — бросить PreflightRequired.
    Любые другие исключения трактуются как ошибка миграции (фаза "run").
    """
    def run(self, fs: "CfgFs", *, allow_side_effects: bool) -> bool: ...   # noqa: E701


_MIGRATIONS: List[Migration] = []
_FROZEN: Optional[Sequence[Migration]] = None


def register(migration: Migration) -> None:
    """Регистрация одной миграции."""
    global _FROZEN
    if _FROZEN is not None:
        # Защитимся от поздней регистрации после первого запроса списка
        raise RuntimeError("Migrations are already frozen; call register/register_many before get_migrations()")
    _MIGRATIONS.append(migration)

def register_many(migrations: Iterable[Migration]) -> None:
    """Пакетная регистрация миграций."""
    global _FROZEN
    if _FROZEN is not None:
        raise RuntimeError("Migrations are already frozen; call register_many before get_migrations()")
    _MIGRATIONS.extend(migrations)

def get_migrations() -> List[Migration]:
    """
    Возвращает миграции, отсортированные по id (возрастающе).
    Сортировка и «заморозка» происходят один раз при первом вызове.
    """
    global _FROZEN
    if _FROZEN is None:
        _FROZEN = tuple(sorted(_MIGRATIONS, key=lambda m: m.id))
    return list(_FROZEN)


# Ленивая импорт-подписка на тип CfgFs (избегаем циклов)
class CfgFs:  # pragma: no cover - подсказка типов
    pass

__all__ = ["Migration", "register", "register_many", "get_migrations"]
