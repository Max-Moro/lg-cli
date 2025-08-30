from __future__ import annotations

# Единая «текущая» версия формата lg-cfg/, к которой инструмент приводит конфиг.
# Реальные миграции могут поднимать сразу до CURRENT (мегамиграции).
CFG_CURRENT: int = 2

__all__ = ["CFG_CURRENT"]
