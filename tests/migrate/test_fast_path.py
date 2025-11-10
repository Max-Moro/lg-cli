"""
Tests for fast path optimization in migration system.

When configuration is already actual, ensure_cfg_actual should skip locking.
"""
import pytest
from pathlib import Path

from lg.migrate.runner import ensure_cfg_actual, _fingerprint_cfg, _put_state
from lg.migrate.version import CFG_CURRENT
from lg.cache.fs_cache import Cache
from lg.version import tool_version


def test_fast_path_skips_lock_when_config_actual(migrate_project: Path, test_cache: Cache):
    """Fast path: no lock when config is already actual."""
    cfg_root = migrate_project / "lg-cfg"

    # Set config as actual in cache
    _put_state(
        test_cache,
        repo_root=migrate_project,
        cfg_root=cfg_root,
        actual=CFG_CURRENT,
        applied=[],
        last_error=None
    )

    # This should complete immediately without locking
    ensure_cfg_actual(cfg_root)

    # Verify no lock was created
    lock_base = test_cache.dir / "locks"
    if lock_base.exists():
        lock_dirs = list(lock_base.iterdir())
        assert len(lock_dirs) == 0, "Lock should not be created for actual config"


def test_fast_path_bypasses_when_fingerprint_matches(migrate_project: Path, test_cache: Cache):
    """Fast path uses fingerprint matching to skip lock."""
    cfg_root = migrate_project / "lg-cfg"

    # Calculate current fingerprint
    fp = _fingerprint_cfg(migrate_project, cfg_root)

    # Store state with matching fingerprint
    _put_state(
        test_cache,
        repo_root=migrate_project,
        cfg_root=cfg_root,
        actual=CFG_CURRENT,
        applied=[],
        last_error=None
    )

    # Get stored state
    state = test_cache.get_cfg_state(cfg_root)
    assert state["fingerprint"] == fp
    assert state["actual"] == CFG_CURRENT

    # Should complete without locking
    ensure_cfg_actual(cfg_root)


def test_slow_path_taken_when_fingerprint_differs(migrate_project: Path, test_cache: Cache):
    """Slow path: lock is used when fingerprint changes."""
    cfg_root = migrate_project / "lg-cfg"

    # Store state with WRONG fingerprint (simulating config change)
    _put_state(
        test_cache,
        repo_root=migrate_project,
        cfg_root=cfg_root,
        actual=CFG_CURRENT,
        applied=[],
        last_error=None
    )

    # Modify the cache to have wrong fingerprint
    state = test_cache.get_cfg_state(cfg_root)
    state["fingerprint"] = "wrong_fingerprint_value"
    test_cache.put_cfg_state(cfg_root, state)

    # This should trigger lock path (but migrations won't actually run as config is valid)
    ensure_cfg_actual(cfg_root)

    # Fingerprint should be updated now
    updated_state = test_cache.get_cfg_state(cfg_root)
    assert updated_state["fingerprint"] != "wrong_fingerprint_value"


def test_fast_path_detects_last_error_in_cache(migrate_project: Path, test_cache: Cache):
    """Fast path is bypassed when last_error exists in cache."""
    cfg_root = migrate_project / "lg-cfg"

    # Store state with error
    _put_state(
        test_cache,
        repo_root=migrate_project,
        cfg_root=cfg_root,
        actual=CFG_CURRENT,
        applied=[],
        last_error={"message": "Previous migration failed"}
    )

    # Should NOT use fast path due to last_error
    # (Will trigger lock path to retry migration)
    ensure_cfg_actual(cfg_root)

    # After successful run, error should be cleared
    state = test_cache.get_cfg_state(cfg_root)
    assert state.get("last_error") is None
