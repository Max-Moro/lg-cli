from __future__ import annotations

from ..fs import CfgFs
from ..errors import PreflightRequired


class _M001_ConfigToSections:
    """
    Migration #1:
      Before: main section config was called `config.yaml`
      Now: `sections.yaml`
    """
    id = 1
    title = "Rename lg-cfg/config.yaml → lg-cfg/sections.yaml"

    def run(self, fs: CfgFs, *, allow_side_effects: bool) -> bool:
        """
        Moves lg-cfg/config.yaml → lg-cfg/sections.yaml.
        Returns True if the move was actually performed (there were changes),
        otherwise False (nothing to do).
        """
        needs = fs.exists("config.yaml") and not fs.exists("sections.yaml")
        if not needs:
            return False

        if not allow_side_effects:
            raise PreflightRequired(
                "Migration #1 requires side effects (rename config.yaml → sections.yaml). "
                "Run inside a Git repo or allow no-git mode."
            )

        fs.move_atomic("config.yaml", "sections.yaml")
        return True


MIGRATION = _M001_ConfigToSections()

__all__ = ["MIGRATION"]
