from __future__ import annotations

from ruamel.yaml.comments import CommentedMap

from ..fs import CfgFs
from ..errors import PreflightRequired
from ..yaml_rt import rewrite_yaml_rt, load_yaml_rt


class _M004_DropSchemaVersion:
    """
    Миграция №4:
      Удаляем устаревшее верхнеуровневое поле `schema_version` из lg-cfg/sections.yaml,
      чтобы новый парсер не принимал его за секцию.
    """
    id = 4
    title = "Remove legacy top-level 'schema_version' from sections.yaml"

    def _needs(self, fs: CfgFs) -> bool:
        """Быстрый детектор необходимости правки."""
        if not fs.exists("sections.yaml"):
            return False
        try:
            doc = load_yaml_rt(fs.cfg_root / "sections.yaml")
            return isinstance(doc, CommentedMap) and "schema_version" in doc
        except Exception:
            # Фолбэк: грубая эвристика по тексту
            try:
                txt = fs.read_text("sections.yaml")
                return "schema_version" in txt
            except Exception:
                return False

    def run(self, fs: CfgFs, *, allow_side_effects: bool) -> bool:
        """
        Удаляет верхнеуровневый ключ schema_version из sections.yaml.
        Возвращает True при реальном изменении файла, иначе False.
        Если требуется изменить файл, но сайд-эффекты запрещены — PreflightRequired.
        """
        need = self._needs(fs)
        if not need:
            return False

        if not allow_side_effects:
            raise PreflightRequired(
                "Migration #4 requires side effects (rewrite lg-cfg/sections.yaml). "
                "Run inside a Git repo or enable no-git mode."
            )

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

        try:
            return bool(rewrite_yaml_rt(fs.cfg_root / "sections.yaml", _transform))
        except Exception:
            # Некорректный YAML — оставляем как есть; диагностика всплывёт в Doctor/CLI.
            return False


MIGRATION = _M004_DropSchemaVersion()

__all__ = ["MIGRATION"]
