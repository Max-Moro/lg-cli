from __future__ import annotations

from ruamel.yaml.comments import CommentedMap

from ..fs import CfgFs
from ..errors import PreflightRequired
from ..yaml_rt import rewrite_yaml_rt, load_yaml_rt


class _M004_DropSchemaVersion:
    """
    Migration #4:
      Remove deprecated top-level field `schema_version` from lg-cfg/sections.yaml,
      so the new parser doesn't mistakenly treat it as a section.
    """
    id = 4
    title = "Remove legacy top-level 'schema_version' from sections.yaml"

    def _needs(self, fs: CfgFs) -> bool:
        """Fast detector for necessity of fix."""
        if not fs.exists("sections.yaml"):
            return False
        try:
            doc = load_yaml_rt(fs.cfg_root / "sections.yaml")
            return isinstance(doc, CommentedMap) and "schema_version" in doc
        except Exception:
            # Fallback: rough heuristic by text
            try:
                txt = fs.read_text("sections.yaml")
                return "schema_version" in txt
            except Exception:
                return False

    def run(self, fs: CfgFs, *, allow_side_effects: bool) -> bool:
        """
        Removes top-level schema_version key from sections.yaml.
        Returns True if the file was actually changed, otherwise False.
        If the file needs to be changed but side effects are forbidden — raises PreflightRequired.
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
            # Malformed YAML — leave as is; diagnostics will bubble up in Doctor/CLI.
            return False


MIGRATION = _M004_DropSchemaVersion()

__all__ = ["MIGRATION"]
