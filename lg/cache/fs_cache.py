from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict, is_dataclass, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

CACHE_VERSION = 1

def _sha1_text(text: str) -> str:
    """Простой хеш от текста для кеширования токенов."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()

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

@dataclass(frozen=True)
class CacheSnapshot:
    enabled: bool
    path: Path
    exists: bool
    size_bytes: int
    entries: int


class Cache:
    """
    Единый файловый кэш для:
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
        self.dir = (root / ".lg-cache")
        if self.enabled:
            try:
                _ensure_dir(self.dir)
            except Exception:
                self.enabled = False

    # --------------------------- ПРОСТОЕ КЕШИРОВАНИЕ ТОКЕНОВ --------------------------- #

    def get_text_tokens(self, text: str, model: str) -> Optional[int]:
        """
        Получает количество токенов для текста из кэша по простому хешу.
        
        Args:
            text: Текст для подсчета токенов
            model: Имя модели
            
        Returns:
            Количество токенов или None если нет в кэше
        """
        if not self.enabled or not text:
            return None
        
        text_hash = _sha1_text(text)
        path = self._bucket_path("tokens", text_hash)
        
        try:
            data = self._load_json(path)
            if not data:
                return None
            return data.get("tokens", {}).get(model)
        except Exception:
            return None
    
    def put_text_tokens(self, text: str, model: str, token_count: int) -> None:
        """
        Сохраняет количество токенов для текста в кэш по простому хешу.
        
        Args:
            text: Текст
            model: Имя модели
            token_count: Количество токенов
        """
        if not self.enabled or not text:
            return
        
        text_hash = _sha1_text(text)
        path = self._bucket_path("tokens", text_hash)
        
        try:
            # Загружаем существующие данные или создаем новые
            data = self._load_json(path) or {
                "v": CACHE_VERSION,
                "text_hash": text_hash,
                "tokens": {},
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            
            # Обновляем токены для модели
            data["tokens"][model] = int(token_count)
            data["updated_at"] = datetime.utcnow().isoformat() + "Z"
            
            self._atom_write(path, data)
        except Exception:
            pass

    # --------------------------- PROCESSED --------------------------- #

    def build_processed_key(
        self,
        abs_path: Path,
        adapter_cfg: Any,
        active_tags: set[str],
    ) -> tuple[str, Path]:
        """
        Ключ processed-кэша. Включает файловый fingerprint (mtime/size),
        а также контекст обработки (adapter, cfg, group_size, tool_version).
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
            "cfg": _fingerprint_cfg(adapter_cfg),
            "tool": self.tool_version,
        }
        
        # Добавляем информацию о тегах для адаптивных возможностей
        if active_tags:
            payload["active_tags"] = sorted(active_tags)

        h = _sha1_json(payload)
        path = self._bucket_path("processed", h)
        return h, path

    def get_processed(self, key_path: Path) -> Optional[dict]:
        """
        Возвращает entry:
          { "v":1, "processed_text":str, "meta":{}, "created_at":..., "updated_at":... }
        или None.
        """
        return self._load_json(key_path)

    def put_processed(self, key_path: Path, *, processed_text: str, meta: dict | None = None) -> None:
        now = datetime.utcnow().isoformat() + "Z"
        self._atom_write(key_path, {
            "v": CACHE_VERSION,
            "processed_text": processed_text,
            "meta": meta or {},
            "created_at": now,
            "updated_at": now,
        })

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

    # --------------------------- CFG STATE (lg-cfg) --------------------------- #
    def _cfg_state_path(self, cfg_root: Path) -> Path:
        # ключ по абсолютному пути (sha1), чтобы устойчиво к переносам/линкам
        h = hashlib.sha1(str(cfg_root.resolve()).encode("utf-8")).hexdigest()
        return self._bucket_path("cfg_state", h)

    def get_cfg_state(self, cfg_root: Path) -> Optional[dict]:
        return self._load_json(self._cfg_state_path(cfg_root))

    def put_cfg_state(self, cfg_root: Path, data: dict) -> None:
        self._atom_write(self._cfg_state_path(cfg_root), data or {})

    # --------------------------- MAINTENANCE --------------------------- #
    def purge_all(self) -> bool:
        """Полная очистка содержимого кэша (.lg-cache)."""
        try:
            if self.dir.exists():
                shutil.rmtree(self.dir, ignore_errors=True)
            self.dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    def snapshot(self) -> CacheSnapshot:
        """Собрать best-effort снимок состояния кэша."""
        size = 0
        entries = 0
        try:
            if self.dir.exists():
                for p in self.dir.rglob("*"):
                    try:
                        if p.is_file():
                            entries += 1
                            size += p.stat().st_size
                    except Exception:
                        # best-effort — пропускаем проблемные файлы
                        pass
        except Exception:
            # оставляем size=0, entries=0
            pass
        return CacheSnapshot(
            enabled=bool(self.enabled),
            path=self.dir,
            exists=self.dir.exists(),
            size_bytes=size,
            entries=entries,
        )

    def rebuild(self) -> CacheSnapshot:
        """Очистить и вернуть новый снимок."""
        self.purge_all()
        return self.snapshot()