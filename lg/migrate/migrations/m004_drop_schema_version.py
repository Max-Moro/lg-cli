from __future__ import annotations

from ruamel.yaml.comments import CommentedMap

from ..fs import CfgFs
from ..yaml_rt import rewrite_yaml_rt, load_yaml_rt


class _M004_DropSchemaVersion:
    """
    Миграция №4:
      Удаляем устаревшее верхнеуровневое поле `schema_version` из lg-cfg/sections.yaml,
      чтобы новый парсер не принимал его за секцию.
    """
    id = 4
    title = "Remove legacy top-level 'schema_version' from sections.yaml"

    def probe(self, fs: CfgFs) -> bool:
        if not fs.exists("sections.yaml"):
            return False
        try:
            doc = load_yaml_rt(fs.cfg_root / "sections.yaml")
            # Удаляем при наличии ключа — неважно, какое у него значение/тип
            return isinstance(doc, CommentedMap) and "schema_version" in doc
        except Exception:
            # На всякий случай: эвристика по тексту
            txt = fs.read_text("sections.yaml")
            return "schema_version" in txt

    def apply(self, fs: CfgFs) -> None:
        if not fs.exists("sections.yaml"):
            return

        def _transform(doc: CommentedMap) -> bool:
            if not isinstance(doc, CommentedMap):
                return False
            if "schema_version" in doc:
                try:
                    del doc["schema_version"]
                except Exception:
                    pass
                return True
            return False

        rewrite_yaml_rt(fs.cfg_root / "sections.yaml", _transform)


MIGRATION = _M004_DropSchemaVersion()

__all__ = ["MIGRATION"]
