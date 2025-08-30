from __future__ import annotations

from typing import List, Protocol


class Migration(Protocol):
    """Строгий контракт миграции."""
    id: int
    title: str

    def probe(self, fs: "CfgFs") -> bool: ...   # noqa: E701
    def apply(self, fs: "CfgFs") -> None: ...   # noqa: E701


_MIGRATIONS: List[Migration] = []


def register(migration: Migration) -> None:
    """Регистрация миграции (опц.)."""
    _MIGRATIONS.append(migration)
    _MIGRATIONS.sort(key=lambda m: m.id)


def get_migrations() -> List[Migration]:
    """Список миграций по возрастанию id. Пока пусто — добавим в следующих патчах."""
    return list(_MIGRATIONS)


# Ленивая импорт-подписка на тип CfgFs (избегаем циклов)
class CfgFs:  # pragma: no cover - подсказка типов
    pass

__all__ = ["Migration", "register", "get_migrations"]
