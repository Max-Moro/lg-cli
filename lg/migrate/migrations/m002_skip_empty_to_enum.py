from __future__ import annotations

from typing import Any

from ruamel.yaml.comments import CommentedMap

from ..fs import CfgFs
from ..yaml_rt import rewrite_yaml_rt


class _M002_SkipEmptyToEnum:
    """
    Миграция №2:
      Ранее: в адаптерах встречалось `skip_empty: true|false`
      Теперь: `empty_policy: exclude|include`
      Применяем к:
        • lg-cfg/sections.yaml
        • lg-cfg/**.sec.yaml
      NB: секционный `skip_empty` НЕ трогаем — остаётся глобальной политикой.
    """
    id = 2
    title = "Adapters: skip_empty(bool) → empty_policy(enum)"

    _SERVICE_KEYS = {"extensions", "filters", "skip_empty", "code_fence", "targets", "path_labels"}

    def probe(self, fs: CfgFs) -> bool:
        # Быстрая эвристика: встречается ли 'skip_empty' в адаптерных узлах?
        # Проходим по всем релевантным yaml-ам и ищем текстово — дешёво.
        candidates = ["sections.yaml", *fs.glob_rel("**/*.sec.yaml")]
        for rel in candidates:
            if not fs.exists(rel):
                continue
            txt = fs.read_text(rel)
            if "skip_empty" in txt:
                return True
        return False

    # ---------- helpers ----------
    def _bool_to_policy(self, val: Any) -> str | None:
        if isinstance(val, bool):
            return "exclude" if val else "include"
        return None

    def _patch_adapter_map(self, amap: CommentedMap) -> bool:
        """
        Заменяет skip_empty → empty_policy внутри конкретного адаптера.
        Возвращает True, если были изменения.
        """
        if not isinstance(amap, CommentedMap):
            return False
        if "skip_empty" not in amap:
            return False
        pol = self._bool_to_policy(amap.get("skip_empty"))
        if pol is None:
            # Неочевидное значение — лучше удалить ключ и не добавлять policy
            # (парсеры и так справятся дефолтами; минимальная правка)
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
        # адаптеры: все ключи, кроме служебных — это конфиги адаптеров
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

    def apply(self, fs: CfgFs) -> None:
        files = []
        if fs.exists("sections.yaml"):
            files.append("sections.yaml")
        files.extend(fs.glob_rel("**/*.sec.yaml"))
        for rel in files:
            path = fs.cfg_root / rel

            def _transform(doc: CommentedMap) -> bool:
                changed = False
                # doc — карта секций (или пустая)
                for name, node in list(doc.items()):
                    if not isinstance(node, CommentedMap):
                        continue
                    if self._patch_section(node):
                        changed = True
                return changed

            rewrite_yaml_rt(path, _transform)


MIGRATION = _M002_SkipEmptyToEnum()

__all__ = ["MIGRATION"]
