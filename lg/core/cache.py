from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime
from importlib import metadata
from pathlib import Path
from typing import Any, Optional


def _tool_version() -> str:
    try:
        return metadata.version("listing-generator")
    except Exception:
        return "0.0.0"


def _norm_bool(x: Any) -> bool:
    if isinstance(x, bool):
        return x
    if x is None:
        return False
    s = str(x).strip().lower()
    return s not in {"0", "false", "no", "off", ""}


class Cache:
    """
    Простой файловый кэш на проект: ./.lg-cache/processed/<hash>.json
    Ключ = sha1(JSON) от {path, mtime_ns, size, adapter, cfg_fingerprint, group_size, mixed, tool_version}.
    Значение = { processed_text: str, tokens: {model: int}, created_at, updated_at }.
    """
    def __init__(self, root: Path, *, enabled: Optional[bool] = None, fresh: bool = False):
        # ENV имеет приоритет, затем флаг CLI, затем включено по умолчанию
        env = os.environ.get("LG_CACHE", None)
        if env is not None:
            self.enabled = _norm_bool(env)
        elif enabled is not None:
            self.enabled = bool(enabled)
        else:
            self.enabled = True
        self.fresh = bool(fresh)
        self.dir = (root / ".lg-cache" / "processed")
        if self.enabled:
            try:
                self.dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                # кэш никогда не должен ломать работу
                self.enabled = False

    @staticmethod
    def _fingerprint_cfg(cfg_obj: Any) -> Any:
        """
        Делаем стабильный сериализуемый fingerprint конфигурации адаптера.
        """
        try:
            if is_dataclass(cfg_obj):
                return asdict(cfg_obj)
            if hasattr(cfg_obj, "__dict__"):
                return cfg_obj.__dict__
        except Exception:
            pass
        return str(cfg_obj)

    @staticmethod
    def _key_sha1(payload: dict) -> str:
        data = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha1(data).hexdigest()

    def _entry_path(self, key_hash: str) -> Path:
        # раскладываем по двум уровням префиксов, чтобы не плодить тысячи файлов в одной папке
        return self.dir / key_hash[:2] / key_hash[2:4] / f"{key_hash}.json"

    def build_key(
        self,
        *,
        abs_path: Path,
        adapter_name: str,
        adapter_cfg: Any,
        group_size: int,
        mixed: bool,
    ) -> tuple[str, Path]:
        try:
            st = abs_path.stat()
            payload = {
                "path": str(abs_path.resolve()),
                "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
                "size": int(st.st_size),
                "adapter": adapter_name,
                "cfg": self._fingerprint_cfg(adapter_cfg),
                "group_size": int(group_size),
                "mixed": bool(mixed),
                "tool": _tool_version(),
            }
        except Exception:
            # при любой ошибке ключ всё равно должен получаться
            payload = {
                "path": str(abs_path),
                "mtime_ns": 0,
                "size": 0,
                "adapter": adapter_name,
                "cfg": self._fingerprint_cfg(adapter_cfg),
                "group_size": int(group_size),
                "mixed": bool(mixed),
                "tool": _tool_version(),
            }
        h = self._key_sha1(payload)
        return h, self._entry_path(h)

    def get_processed(self, key_hash: str, path: Path) -> Optional[dict]:
        if not self.enabled or self.fresh:
            return None
        try:
            pdir = path.parent
            if not pdir.exists():
                return None
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def put_processed(self, key_hash: str, path: Path, *, processed_text: str) -> None:
        if not self.enabled:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            now = datetime.utcnow().isoformat() + "Z"
            data = {
                "v": 1,
                "processed_text": processed_text,
                "tokens": {},           # зарезервировано для будущей пер-модели
                "created_at": now,
                "updated_at": now,
            }
            tmp = path.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            tmp.replace(path)
        except Exception:
            # кэш — best effort
            pass
