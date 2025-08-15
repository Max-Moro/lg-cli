from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

CACHE_VERSION = 1  # vNext cache format

def _sha1_json(payload: dict) -> str:
    return hashlib.sha1(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _fingerprint_cfg(cfg_obj: Any) -> Any:
    """
    Стабильный сериализуемый fingerprint конфигурации адаптера/опций.
    """
    try:
        if is_dataclass(cfg_obj):
            return asdict(cfg_obj)
        if hasattr(cfg_obj, "__dict__"):
            return cfg_obj.__dict__
    except Exception:
        pass
    return cfg_obj

class Cache:
    """
    Единый файловый кэш для vNext:
      • processed-тексты (по ключу processed)
      • токены raw/processed (by model+mode)
      • rendered-токены (на итоговый документ)
    Ключи раскладываются по подкаталогам по префиксу sha1.
    Любые ошибки — best-effort (не роняют пайплайн).
    """

    def __init__(self, root: Path, *, enabled: Optional[bool] = None, fresh: bool = False, tool_version: str = "0.0.0"):
        env = os.environ.get("LG_CACHE", None)
        if env is not None:
            self.enabled = env.strip().lower() not in {"0", "false", "no", "off", ""}
        elif enabled is not None:
            self.enabled = bool(enabled)
        else:
            self.enabled = True
        self.fresh = bool(fresh)
        self.tool_version = tool_version
        self.dir = (root / ".lg-cache" / "vnext")
        if self.enabled:
            try:
                _ensure_dir(self.dir)
            except Exception:
                self.enabled = False

    # --------------------------- КЛЮЧИ --------------------------- #

    def build_processed_key(
        self,
        *,
        abs_path: Path,
        adapter_name: str,
        adapter_cfg: Any,
        group_size: int,
        mixed: bool,
    ) -> tuple[str, Path]:
        """
        Ключ processed-кэша. Включает файловый fingerprint (mtime/size),
        а также контекст обработки (adapter, cfg, group_size, mixed, tool_version).
        """
        try:
            st = abs_path.stat()
            file_fp = {
                "path": str(abs_path.resolve()),
                "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
                "size": int(st.st_size),
            }
        except Exception:
            file_fp = {"path": str(abs_path), "mtime_ns": 0, "size": 0}
        payload = {
            "v": CACHE_VERSION,
            "kind": "processed",
            "file": file_fp,
            "adapter": adapter_name,
            "cfg": _fingerprint_cfg(adapter_cfg),
            "group_size": int(group_size),
            "mixed": bool(mixed),
            "tool": self.tool_version,
        }
        h = _sha1_json(payload)
        path = self._bucket_path("processed", h)
        return h, path

    def build_raw_tokens_key(self, *, abs_path: Path) -> tuple[str, Path]:
        """
        Ключ для raw-токенов на основе только файлового fingerprint.
        (Адаптер/группировка не участвуют, т.к. читаем «сырой» текст с диска.)
        """
        try:
            st = abs_path.stat()
            file_fp = {
                "path": str(abs_path.resolve()),
                "mtime_ns": int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))),
                "size": int(st.st_size),
            }
        except Exception:
            file_fp = {"path": str(abs_path), "mtime_ns": 0, "size": 0}
        payload = {
            "v": CACHE_VERSION,
            "kind": "raw-tokens",
            "file": file_fp,
            "tool": self.tool_version,
        }
        h = _sha1_json(payload)
        path = self._bucket_path("raw_tokens", h)
        return h, path

    def build_rendered_key(
        self,
        *,
        context_name: str,
        sections_used: Dict[str, int],
        options_fp: Dict[str, Any],  # {mode, code_fence, model, markdown.max_heading_level, ...}
        processed_keys: Dict[str, str],  # rel_path -> processed_key_sha1 (для инвалидации)
    ) -> tuple[str, Path]:
        """
        Ключ rendered-документа. Включает:
          - имя контекста, кратности секций
          - опции рендера (в т.ч. markdown.max_heading_level, code_fence)
          - список файлов и их processed-ключи
          - версию инструмента
        """
        payload = {
            "v": CACHE_VERSION,
            "kind": "rendered",
            "context": context_name,
            "sections": dict(sorted(sections_used.items())),
            "options": options_fp,
            "processed": dict(sorted(processed_keys.items())),  # стабилизируем порядок
            "tool": self.tool_version,
        }
        h = _sha1_json(payload)
        path = self._bucket_path("rendered", h)
        return h, path

    # --------------------------- IO helpers --------------------------- #

    def _bucket_path(self, bucket: str, key: str) -> Path:
        d = self.dir / bucket / key[:2] / key[2:4]
        return d / f"{key}.json"

    def _load_json(self, path: Path) -> Optional[dict]:
        if not self.enabled or self.fresh:
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _atom_write(self, path: Path, data: dict) -> None:
        if not self.enabled:
            return
        try:
            _ensure_dir(path.parent)
            tmp = path.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            tmp.replace(path)
        except Exception:
            pass

    # --------------------------- PROCESSED --------------------------- #

    def get_processed(self, key_path: Path) -> Optional[dict]:
        """
        Возвращает entry:
          { "v":1, "processed_text":str, "tokens":{model:{mode:int}}, "meta":{}, "created_at":..., "updated_at":... }
        или None.
        """
        return self._load_json(key_path)

    def put_processed(self, key_path: Path, *, processed_text: str, meta: dict | None = None) -> None:
        now = datetime.utcnow().isoformat() + "Z"
        self._atom_write(key_path, {
            "v": CACHE_VERSION,
            "processed_text": processed_text,
            "tokens": {},   # model -> { "raw":int, "processed":int, "rendered":int }
            "meta": meta or {},
            "created_at": now,
            "updated_at": now,
        })

    # --------------------------- TOKENS (raw/processed) --------------------------- #

    def get_tokens(self, key_path: Path, *, model: str, mode: str) -> Optional[int]:
        try:
            data = self._load_json(key_path)
            if not data:
                return None
            return int((data.get("tokens") or {}).get(model, {}).get(mode))
        except Exception:
            return None

    def update_tokens(self, key_path: Path, *, model: str, mode: str, value: int) -> None:
        if not self.enabled:
            return
        try:
            data = self._load_json(key_path) or {"v": CACHE_VERSION, "tokens": {}, "processed_text": "", "meta": {}, "created_at": datetime.utcnow().isoformat() + "Z"}
            tokens = data.setdefault("tokens", {})
            per_model = tokens.setdefault(model, {})
            per_model[mode] = int(value)
            data["updated_at"] = datetime.utcnow().isoformat() + "Z"
            self._atom_write(key_path, data)
        except Exception:
            pass

    # --------------------------- RENDERED TOKENS --------------------------- #

    def get_rendered_tokens(self, key_path: Path, *, model: str) -> Optional[int]:
        data = self._load_json(key_path)
        if not data:
            return None
        try:
            return int((data.get("tokens") or {}).get(model))
        except Exception:
            return None

    def update_rendered_tokens(self, key_path: Path, *, model: str, value: int) -> None:
        if not self.enabled:
            return
        try:
            now = datetime.utcnow().isoformat() + "Z"
            data = self._load_json(key_path) or {"v": CACHE_VERSION, "tokens": {}, "created_at": now}
            data.setdefault("tokens", {})[model] = int(value)
            data["updated_at"] = now
            self._atom_write(key_path, data)
        except Exception:
            pass
