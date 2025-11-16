from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict, is_dataclass, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .gitignore_helper import ensure_gitignore_entry

CACHE_VERSION = 1

def _sha1_text(text: str) -> str:
    """Simple hash of text for token caching."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()

def _sha1_json(payload: dict) -> str:
    return hashlib.sha1(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _fingerprint_cfg(cfg_obj: Any) -> Any:
    """
    Stable serializable fingerprint of adapter/options configuration.
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
    File cache for LG file processing and token counting.

    Stores:
      - processed texts (by processed key)
      - tokens raw/processed (by model+mode)
      - rendered tokens (for final document)
      - configuration state (cfg_state)

    Directory structure of .lg-cache/:
      - tokens/ - token counting cache
      - processed/ - processed files cache
      - cfg_state/ - configuration and migration state
      - diag/ - diagnostic bundles
      - tokenizer-models/ - tokenization model cache (SEPARATE SUBSYSTEM, not managed by Cache)

    Keys are distributed into subdirectories by sha1 prefix.
    All errors are best-effort (do not break the pipeline).
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
        self.root = root
        self.dir = (root / ".lg-cache")
        if self.enabled:
            try:
                _ensure_dir(self.dir)
                # Ensure entry in .gitignore
                ensure_gitignore_entry(root, ".lg-cache/", comment="LG cache directory")
            except Exception:
                self.enabled = False

    # ----------------------- SIMPLE TOKEN CACHING ----------------------- #

    def get_text_tokens(self, text: str, cache_key: str) -> Optional[int]:
        """
        Get token count for text from cache by simple hash.

        Args:
            text: Text for token counting
            cache_key: Tokenizer key

        Returns:
            Token count or None if not in cache
        """
        if not self.enabled or not text:
            return None
        
        text_hash = _sha1_text(text)
        path = self._bucket_path("tokens", text_hash)
        
        try:
            data = self._load_json(path)
            if not data:
                return None
            return data.get("tokens", {}).get(cache_key)
        except Exception:
            return None
    
    def put_text_tokens(self, text: str, model: str, token_count: int) -> None:
        """
        Save token count for text to cache by simple hash.

        Args:
            text: Text
            model: Model name
            token_count: Token count
        """
        if not self.enabled or not text:
            return
        
        text_hash = _sha1_text(text)
        path = self._bucket_path("tokens", text_hash)
        
        try:
            # Load existing data or create new
            data = self._load_json(path) or {
                "v": CACHE_VERSION,
                "text_hash": text_hash,
                "tokens": {},
                "created_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            }

            # Update tokens for model
            data["tokens"][model] = int(token_count)
            data["updated_at"] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

            self._atom_write(path, data)
        except Exception:
            pass

    # ----------------------- PROCESSED ----------------------- #

    def build_processed_key(
        self,
        abs_path: Path,
        adapter_cfg: Any,
        active_tags: set[str],
    ) -> tuple[str, Path]:
        """
        Processed cache key. Includes file fingerprint (mtime/size),
        as well as processing context (adapter, cfg, group_size, tool_version).
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

        # Add tag information for adaptive capabilities
        if active_tags:
            payload["active_tags"] = sorted(active_tags)

        h = _sha1_json(payload)
        path = self._bucket_path("processed", h)
        return h, path

    def get_processed(self, key_path: Path) -> Optional[dict]:
        """
        Return entry:
          { "v":1, "processed_text":str, "meta":{}, "created_at":..., "updated_at":... }
        or None.
        """
        return self._load_json(key_path)

    def put_processed(self, key_path: Path, *, processed_text: str, meta: dict | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        self._atom_write(key_path, {
            "v": CACHE_VERSION,
            "processed_text": processed_text,
            "meta": meta or {},
            "created_at": now,
            "updated_at": now,
        })

    # ----------------------- IO helpers ----------------------- #

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

    # ----------------------- CFG STATE (lg-cfg) ----------------------- #
    def _cfg_state_path(self, cfg_root: Path) -> Path:
        # Key by absolute path (sha1) to be robust against moves/links
        h = hashlib.sha1(str(cfg_root.resolve()).encode("utf-8")).hexdigest()
        return self._bucket_path("cfg_state", h)

    def get_cfg_state(self, cfg_root: Path) -> Optional[dict]:
        return self._load_json(self._cfg_state_path(cfg_root))

    def put_cfg_state(self, cfg_root: Path, data: dict) -> None:
        self._atom_write(self._cfg_state_path(cfg_root), data or {})

    # ----------------------- MAINTENANCE ----------------------- #
    def purge_all(self) -> bool:
        """
        Complete cleanup of LG cache contents.

        Deletes only LG cache subdirectories (tokens, processed, cfg_state, diag),
        NOT affecting other subsystems (e.g., tokenizer-models).
        """
        try:
            if not self.dir.exists():
                return True

            # List of LG cache subdirectories (not affecting other subsystems)
            lg_cache_buckets = ["tokens", "processed", "cfg_state", "diag"]

            for bucket in lg_cache_buckets:
                bucket_dir = self.dir / bucket
                if bucket_dir.exists():
                    shutil.rmtree(bucket_dir, ignore_errors=True)

            return True
        except Exception:
            return False

    def snapshot(self) -> CacheSnapshot:
        """
        Collect a best-effort snapshot of LG cache state.

        Counts only LG cache subdirectories (tokens, processed, cfg_state, diag),
        NOT affecting other subsystems (e.g., tokenizer-models).
        """
        size = 0
        entries = 0

        # List of LG cache subdirectories (not affecting other subsystems)
        lg_cache_buckets = ["tokens", "processed", "cfg_state", "diag"]

        try:
            if self.dir.exists():
                for bucket in lg_cache_buckets:
                    bucket_dir = self.dir / bucket
                    if not bucket_dir.exists():
                        continue

                    for p in bucket_dir.rglob("*"):
                        try:
                            if p.is_file():
                                entries += 1
                                size += p.stat().st_size
                        except Exception:
                            # best-effort — skip problematic files
                            pass
        except Exception:
            # leave size=0, entries=0
            pass
        return CacheSnapshot(
            enabled=bool(self.enabled),
            path=self.dir,
            exists=self.dir.exists(),
            size_bytes=size,
            entries=entries,
        )

    def rebuild(self) -> CacheSnapshot:
        """Clear and return a new snapshot."""
        self.purge_all()
        return self.snapshot()