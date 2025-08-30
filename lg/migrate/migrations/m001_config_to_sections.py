from __future__ import annotations

from ..fs import CfgFs


class _M001_ConfigToSections:
    """
    Миграция №1:
      Ранее: основной конфиг секций назывался `config.yaml`
      Теперь: `sections.yaml`
    """
    id = 1
    title = "Rename lg-cfg/config.yaml → lg-cfg/sections.yaml"

    def probe(self, fs: CfgFs) -> bool:
        return fs.exists("config.yaml") and not fs.exists("sections.yaml")

    def apply(self, fs: CfgFs) -> None:
        # Идемпотентно: если уже перенесено — ничего не делаем.
        if fs.exists("config.yaml") and not fs.exists("sections.yaml"):
            fs.move_atomic("config.yaml", "sections.yaml")


MIGRATION = _M001_ConfigToSections()

__all__ = ["MIGRATION"]
