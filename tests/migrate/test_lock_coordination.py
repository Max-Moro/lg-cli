"""
Unit tests for _MigrationLock coordination mechanisms.

Tests lock acquisition, waiting, completion markers, and release.
"""
import json
import time
from pathlib import Path

import pytest

from lg.migrate.runner import _MigrationLock
from lg.migrate.errors import MigrationFatalError


def test_try_acquire_succeeds_when_lock_dir_absent(migration_lock: _MigrationLock):
    """Lock acquisition succeeds when lock directory doesn't exist."""
    assert migration_lock.try_acquire() is True
    assert migration_lock.acquired is True
    assert migration_lock.lock_dir.exists()

    # Verify lock.json was created
    lock_info = migration_lock.lock_dir / "lock.json"
    assert lock_info.exists()

    data = json.loads(lock_info.read_text(encoding="utf-8"))
    assert "pid" in data
    assert "started_at" in data


def test_try_acquire_fails_when_lock_dir_exists_fresh(migration_lock: _MigrationLock):
    """Lock acquisition fails when fresh lock directory exists."""
    # First process acquires lock
    assert migration_lock.try_acquire() is True

    # Second process tries to acquire (fresh lock)
    second_lock = _MigrationLock(
        migration_lock.cache_dir,
        migration_lock.cfg_root,
        stale_seconds=10,  # Won't be stale for 10 seconds
        wait_timeout=3
    )
    assert second_lock.try_acquire() is False
    assert second_lock.acquired is False


def test_try_acquire_steals_stale_lock_and_records_recovery(cache_dir: Path, cfg_root: Path):
    """Lock acquisition succeeds for stale locks and records recovery info."""
    # Create initial lock
    lock1 = _MigrationLock(cache_dir, cfg_root, stale_seconds=1, wait_timeout=3)
    assert lock1.try_acquire() is True
    old_pid = lock1._read_info().get("pid")

    # Wait for lock to become stale
    time.sleep(1.1)

    # Second process recovers stale lock
    lock2 = _MigrationLock(cache_dir, cfg_root, stale_seconds=1, wait_timeout=3)
    assert lock2.try_acquire() is True
    assert lock2.acquired is True

    # Verify recovery was recorded
    info = lock2._read_info()
    assert "recovered_at" in info
    assert "recovered_from_pid" in info
    assert info["recovered_from_pid"] == old_pid


def test_wait_for_completion_returns_when_lock_absent(migration_lock: _MigrationLock):
    """Waiting process returns immediately when lock doesn't exist."""
    # No lock exists - should return immediately
    start = time.time()
    migration_lock.wait_for_completion()
    elapsed = time.time() - start

    assert elapsed < 0.1  # Should be nearly instant


def test_wait_for_completion_times_out_after_configured_seconds(migration_lock: _MigrationLock):
    """Waiting process times out if migration doesn't complete."""
    # Create fresh lock (but don't complete it)
    migration_lock.lock_dir.mkdir(parents=True, exist_ok=True)
    (migration_lock.lock_dir / "lock.json").write_text(
        json.dumps({"pid": 99999, "started_at": "2024-01-01T00:00:00Z"}),
        encoding="utf-8"
    )

    # Wait should timeout (wait_timeout=3)
    start = time.time()
    with pytest.raises(MigrationFatalError, match="Timeout waiting for migration"):
        migration_lock.wait_for_completion()
    elapsed = time.time() - start

    # Should timeout around 3 seconds
    assert 2.5 < elapsed < 4.0


def test_wait_for_completion_returns_when_lock_disappears(migration_lock: _MigrationLock):
    """Waiting returns successfully when lock directory disappears (normal release scenario)."""
    # Create lock directory
    migration_lock.lock_dir.mkdir(parents=True, exist_ok=True)

    # Simulate lock disappearing mid-wait (normal release after migration)
    import threading
    def remove_lock():
        time.sleep(0.2)
        import shutil
        shutil.rmtree(migration_lock.lock_dir, ignore_errors=True)

    thread = threading.Thread(target=remove_lock)
    thread.start()

    # Wait should return successfully (not error)
    start = time.time()
    migration_lock.wait_for_completion()  # Should NOT raise
    elapsed = time.time() - start

    # Should return after lock disappears (~0.2-0.4s with double-check)
    assert 0.15 < elapsed < 0.5

    thread.join()


def test_release_removes_lock_directory(migration_lock: _MigrationLock):
    """Lock directory is removed after release."""
    assert migration_lock.try_acquire() is True
    assert migration_lock.lock_dir.exists()

    migration_lock.release()

    assert not migration_lock.lock_dir.exists()
    assert migration_lock.acquired is False


def test_release_is_idempotent(migration_lock: _MigrationLock):
    """Multiple releases don't cause errors."""
    assert migration_lock.try_acquire() is True

    # First release
    migration_lock.release()
    assert not migration_lock.lock_dir.exists()

    # Second release (should not raise)
    migration_lock.release()
    assert migration_lock.acquired is False


def test_exponential_backoff_during_wait(migration_lock: _MigrationLock):
    """Wait polling uses exponential backoff between checks."""
    # Create lock and release it after delay
    migration_lock.lock_dir.mkdir(parents=True, exist_ok=True)

    def release_after_delay():
        time.sleep(0.3)
        # Remove lock directory (simulating release)
        import shutil
        shutil.rmtree(migration_lock.lock_dir, ignore_errors=True)

    import threading
    thread = threading.Thread(target=release_after_delay)
    thread.start()

    # Wait should complete after ~0.3s
    start = time.time()
    migration_lock.wait_for_completion()
    elapsed = time.time() - start

    # Should complete around 0.3-0.4s
    assert 0.25 < elapsed < 0.5

    thread.join()


def test_lock_info_json_contains_required_fields(migration_lock: _MigrationLock):
    """Lock info JSON has all required metadata."""
    assert migration_lock.try_acquire() is True

    info = migration_lock._read_info()
    assert isinstance(info, dict)
    assert "pid" in info
    assert "started_at" in info
    assert isinstance(info["pid"], int)
    assert isinstance(info["started_at"], str)
