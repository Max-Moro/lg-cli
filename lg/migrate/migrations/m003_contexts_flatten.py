from __future__ import annotations

import re
from pathlib import Path
from typing import Set

from ..fs import CfgFs
from ..errors import PreflightRequired


class _M003_ContextsFlatten:
    """
    Migration #3:
      • Move ALL *.md from lg-cfg/contexts/** → lg-cfg/** (preserving subdirectories relative to contexts/).
      • Classify files:
          – if a file is referenced as `${tpl:<resource>}` in at least one document in lg-cfg → template (*.tpl.md);
          – otherwise → treat as context (*.ctx.md).
      • Placeholders are NOT rewritten.
      • Destination conflicts:
          – if content matches → delete source;
          – otherwise → move as `<name>.from-contexts(.N).tpl.md` or `.ctx.md`.
      • Idempotent.
    """
    id = 3
    title = "Flatten lg-cfg/contexts/** → lg-cfg/** with smart suffix (.tpl/.ctx) by usage"

    # Exactly the same token semantics as in TemplateTokens: ${...} and $...
    _PH_RE = re.compile(
        r"""
        \$\{
            (?P<braced>[A-Za-z0-9_@:/\-\[\].]+)
        }
        |
        \$
            (?P<name>[A-Za-z0-9_@:/\-\[\].]+)
        """,
        re.VERBOSE,
    )

    def run(self, fs: CfgFs, *, allow_side_effects: bool) -> bool:
        """
        Returns True if the tree was actually modified (moved/deleted/directory cleanup),
        otherwise False. If modification is required but side effects are forbidden — raises PreflightRequired.
        """
        # 1) Collect all candidates for migration
        src_files = fs.glob_rel("contexts/**/*.md")
        src_files += [rel for rel in fs.glob_rel("contexts/*.md") if rel not in src_files]
        if not src_files:
            return False  # nothing to do

        # Any presence of files under contexts/ → side effects will be needed
        if not allow_side_effects:
            raise PreflightRequired(
                "Migration #3 requires side effects (moving/removing files from lg-cfg/contexts). "
                "Run inside a Git repo or enable no-git mode."
            )

        # 2) Scan usage of ${tpl:...} in ALL md files of the current lg-cfg/
        used_as_tpl = self._collect_tpl_usages(fs)

        # 3) Move/delete by classification
        any_changed = False
        for src_rel in src_files:
            resource = self._resource_name(src_rel)
            is_tpl = resource in used_as_tpl
            dst_rel = self._dst_for(resource, is_tpl=is_tpl)

            if fs.exists(dst_rel):
                try:
                    src_text = fs.read_text(src_rel)
                    dst_text = fs.read_text(dst_rel)
                except Exception:
                    src_text = ""
                    dst_text = None

                if dst_text is not None and src_text == dst_text:
                    # Matches — just delete the source
                    fs.remove_file(src_rel)
                    any_changed = True
                    continue

                # Content conflict — place nearby as .from-contexts(-N)
                n = 1
                alt_rel = self._with_variant(dst_rel, n)
                while fs.exists(alt_rel):
                    n += 1
                    alt_rel = self._with_variant(dst_rel, n)
                fs.move_atomic(src_rel, alt_rel)
                any_changed = True
                continue

            # Regular move
            fs.move_atomic(src_rel, dst_rel)
            any_changed = True

        # 4) If contexts/ is empty — clean up the remainder
        if not fs.dir_has_files("contexts"):
            fs.remove_dir_tree("contexts")
            # even if there's nothing more to delete — it's safe; counting this as a change is not required,
            # but logical: since we were moving files — any_changed is already True. If the only action
            # was to clean up an empty folder — count this as a change:
            any_changed = True or any_changed

        return any_changed

    # ---------- helpers ----------
    @staticmethod
    def _resource_name(src_rel: str) -> str:
        """
        'contexts/foo/bar.tpl.md' → 'foo/bar'
        """
        assert src_rel.startswith("contexts/")
        tail = src_rel[len("contexts/") :]
        p = Path(tail)
        name = p.name
        if name.endswith(".tpl.md"):
            stem = name[: -len(".tpl.md")]
        elif name.endswith(".ctx.md"):
            stem = name[: -len(".ctx.md")]
        elif name.endswith(".md"):
            stem = name[: -len(".md")]
        else:
            stem = p.stem
        return str(p.with_name(stem).as_posix())

    @staticmethod
    def _dst_for(resource: str, is_tpl: bool) -> str:
        """
        resource='foo/bar' → 'foo/bar.tpl.md' | 'foo/bar.ctx.md'
        """
        suffix = ".tpl.md" if is_tpl else ".ctx.md"
        return str(Path(resource).with_suffix(suffix).as_posix())

    @staticmethod
    def _with_variant(rel: str, n: int) -> str:
        p = Path(rel)
        name = p.name
        if name.endswith(".tpl.md"):
            base = name[: -len(".tpl.md")]
            tail = ".tpl.md"
        elif name.endswith(".ctx.md"):
            base = name[: -len(".ctx.md")]
            tail = ".ctx.md"
        elif name.endswith(".md"):
            base = name[: -len(".md")]
            tail = ".md"
        else:
            base = p.stem
            tail = p.suffix
        extra = ".from-contexts" if n == 1 else f".from-contexts-{n}"
        new_name = f"{base}{extra}{tail}"
        return str(p.with_name(new_name).as_posix())

    def _collect_tpl_usages(self, fs: CfgFs) -> Set[str]:
        """
        Parse ALL *.md under the current lg-cfg/ and collect resources referenced as ${tpl:...}.
        Consider only local forms ('tpl:...'), skip addressed forms ('tpl@...').
        Return a set of resource names (with subdirectories).
        """
        used_as_tpl: Set[str] = set()
        for rel in fs.glob_rel("**/*.md"):
            text = fs.read_text(rel)
            for m in self._PH_RE.finditer(text):
                token = m.group("braced") or m.group("name") or ""
                if not token or token.startswith("tpl@"):
                    continue
                if token.startswith("tpl:"):
                    res = token[len("tpl:") :].strip()
                    if res:
                        used_as_tpl.add(res)
        return used_as_tpl


MIGRATION = _M003_ContextsFlatten()

__all__ = ["MIGRATION"]
