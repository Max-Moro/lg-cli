"""
Tests for stale lock detection and recovery.

Verifies that stale locks (from crashed processes) are properly recovered.
"""
import json
import os
import time
from pathlib import Path

import pytest

from lg.migrate.runner import _MigrationLock


def test_lock_age_boundary_at_stale_seconds(cache_dir: Path, cfg_root: Path):
    """Lock is considered stale exactly at stale_seconds boundary."""
    lock1 = _MigrationLock(cache_dir, cfg_root, stale_seconds=1, wait_timeout=3)
    assert lock1.try_acquire() is True

    # Just before stale threshold
    time.sleep(0.9)
    lock2 = _MigrationLock(cache_dir, cfg_root, stale_seconds=1, wait_timeout=3)
    assert lock2.try_acquire() is False  # Still fresh

    # After stale threshold
    time.sleep(0.2)  # Total 1.1s
    lock3 = _MigrationLock(cache_dir, cfg_root, stale_seconds=1, wait_timeout=3)
    assert lock3.try_acquire() is True  # Now stale, can steal


def test_multiple_rapid_acquisitions_after_release(migration_lock: _MigrationLock, cache_dir: Path, cfg_root: Path):
    """Multiple processes can acquire lock sequentially after proper release."""
    # First acquisition
    assert migration_lock.try_acquire() is True
    migration_lock.mark_completed()
    migration_lock.release()

    # Second acquisition (should succeed immediately)
    lock2 = _MigrationLock(cache_dir, cfg_root, stale_seconds=1, wait_timeout=3)
    assert lock2.try_acquire() is True
    lock2.release()

    # Third acquisition
    lock3 = _MigrationLock(cache_dir, cfg_root, stale_seconds=1, wait_timeout=3)
    assert lock3.try_acquire() is True
    lock3.release()


def test_recovery_preserves_original_pid_in_metadata(cache_dir: Path, cfg_root: Path):
    """Recovery records the original (crashed) process PID."""
    # Simulate crashed process with explicit PID
    lock1 = _MigrationLock(cache_dir, cfg_root, stale_seconds=1, wait_timeout=3)
    assert lock1.try_acquire() is True

    # Manually set a "foreign" PID to simulate another process
    foreign_pid = 88888
    lock1._write_info({"pid": foreign_pid, "started_at": "2024-01-01T00:00:00Z"})

    # Don't release (simulate crash)
    # Wait for staleness
    time.sleep(1.1)

    # Recovery by another process
    lock2 = _MigrationLock(cache_dir, cfg_root, stale_seconds=1, wait_timeout=3)
    assert lock2.try_acquire() is True

    # Check recovery metadata
    recovery_info = lock2._read_info()
    # In real scenario PIDs would differ, but in tests they're same process
    # Key check: recovered_from_pid should be the foreign PID
    assert recovery_info["recovered_from_pid"] == foreign_pid
    assert "recovered_at" in recovery_info
    assert recovery_info["pid"] == os.getpid()  # Current process PID


def test_stale_lock_without_lock_json_can_be_recovered(cache_dir: Path, cfg_root: Path):
    """Stale lock without metadata can still be recovered."""
    lock1 = _MigrationLock(cache_dir, cfg_root, stale_seconds=1, wait_timeout=3)

    # Manually create lock directory without lock.json (simulate corruption)
    lock1.lock_dir.mkdir(parents=True, exist_ok=True)

    # Wait for staleness
    time.sleep(1.1)

    # Recovery should still work
    lock2 = _MigrationLock(cache_dir, cfg_root, stale_seconds=1, wait_timeout=3)
    assert lock2.try_acquire() is True
    assert lock2.acquired is True
