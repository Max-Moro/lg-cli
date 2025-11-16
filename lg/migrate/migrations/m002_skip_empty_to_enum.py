from __future__ import annotations

from typing import Any

from ruamel.yaml.comments import CommentedMap

from ..fs import CfgFs
from ..errors import PreflightRequired
from ..yaml_rt import rewrite_yaml_rt, load_yaml_rt


class _M002_SkipEmptyToEnum:
    """
    Migration #2:
      Before: adapters had `skip_empty: true|false`
      Now: `empty_policy: exclude|include`
      Applies to:
        • lg-cfg/sections.yaml
        • lg-cfg/**.sec.yaml
      NB: section-level `skip_empty` is NOT touched — remains a global policy.
    """
    id = 2
    title = "Adapters: skip_empty(bool) → empty_policy(enum)"

    _SERVICE_KEYS = {"extensions", "filters", "skip_empty", "code_fence", "targets", "path_labels"}

    # ---------- helpers (detection) ----------
    def _would_patch_adapter_map(self, amap: CommentedMap) -> bool:
        """
        True if a specific adapter has the 'skip_empty' key (any type),
        i.e., transformation will require modification.
        """
        return isinstance(amap, CommentedMap) and "skip_empty" in amap

    def _would_patch_targets(self, section: CommentedMap) -> bool:
        targets = section.get("targets")
        if not isinstance(targets, list):
            return False
        for item in targets:
            if not isinstance(item, CommentedMap):
                continue
            for k, v in item.items():
                if k == "match":
                    continue
                if isinstance(v, CommentedMap) and self._would_patch_adapter_map(v):
                    return True
        return False

    def _would_patch_section(self, sec_map: CommentedMap) -> bool:
        # adapters: all keys except service keys are adapter configs
        for k, v in sec_map.items():
            if k in self._SERVICE_KEYS:
                continue
            if isinstance(v, CommentedMap) and self._would_patch_adapter_map(v):
                return True
        # targets
        if self._would_patch_targets(sec_map):
            return True
        return False

    # ---------- helpers (patching) ----------
    def _bool_to_policy(self, val: Any) -> str | None:
        if isinstance(val, bool):
            return "exclude" if val else "include"
        return None

    def _patch_adapter_map(self, amap: CommentedMap) -> bool:
        """
        Replaces skip_empty → empty_policy within a specific adapter.
        Returns True if there were changes.
        """
        if not isinstance(amap, CommentedMap):
            return False
        if "skip_empty" not in amap:
            return False
        pol = self._bool_to_policy(amap.get("skip_empty"))
        if pol is None:
            # Non-obvious value — better to delete the key without adding policy
            try:
                del amap["skip_empty"]
            except Exception:
                pass
            return True
        amap["empty_policy"] = pol
        try:
            del amap["skip_empty"]
        except Exception:
            pass
        return True

    def _patch_targets(self, section: CommentedMap) -> bool:
        changed = False
        targets = section.get("targets")
        if not isinstance(targets, list):
            return False
        for item in targets:
            if not isinstance(item, CommentedMap):
                continue
            for k, v in list(item.items()):
                if k == "match":
                    continue
                if isinstance(v, CommentedMap):
                    if self._patch_adapter_map(v):
                        changed = True
        return changed

    def _patch_section(self, sec_map: CommentedMap) -> bool:
        changed = False
        # adapters: all keys except service keys are adapter configs
        for k, v in list(sec_map.items()):
            if k in self._SERVICE_KEYS:
                continue
            if isinstance(v, CommentedMap):
                if self._patch_adapter_map(v):
                    changed = True
        # targets
        if self._patch_targets(sec_map):
            changed = True
        return changed

    # ---------- main method ----------
    def run(self, fs: CfgFs, *, allow_side_effects: bool) -> bool:
        """
        Performs skip_empty(bool) → empty_policy(enum) replacement in adapters.
        Returns True if there were real changes in at least one file,
        otherwise False. If modifications are needed and side effects are forbidden —
        raises PreflightRequired.
        """
        files: list[str] = []
        if fs.exists("sections.yaml"):
            files.append("sections.yaml")
        files.extend(fs.glob_rel("**/*.sec.yaml"))

        # 1) "dry" check — is there actually something to patch
        need_change = False
        for rel in files:
            try:
                doc = load_yaml_rt(fs.cfg_root / rel)
            except Exception:
                # Malformed YAML — skip (let another subsystem complain later)
                continue
            for _, node in (doc.items() if isinstance(doc, CommentedMap) else []):
                if not isinstance(node, CommentedMap):
                    continue
                if self._would_patch_section(node):
                    need_change = True
                    break
            if need_change:
                break

        if not need_change:
            return False

        if not allow_side_effects:
            raise PreflightRequired(
                "Migration #2 requires side effects (rewrite YAML files). "
                "Run inside a Git repo or allow no-git mode."
            )

        # 2) Apply transformations (idempotently), aggregate the fact of changes
        any_changed = False
        for rel in files:
            path = fs.cfg_root / rel

            def _transform(doc: CommentedMap) -> bool:
                changed = False
                for _, node in list(doc.items()):
                    if not isinstance(node, CommentedMap):
                        continue
                    if self._patch_section(node):
                        changed = True
                return changed

            try:
                if rewrite_yaml_rt(path, _transform):
                    any_changed = True
            except Exception:
                # If file is broken and cannot be parsed — skip it; serious
                # diagnostics will be provided by Doctor/CLI at a later stage.
                continue

        return any_changed


MIGRATION = _M002_SkipEmptyToEnum()

__all__ = ["MIGRATION"]
