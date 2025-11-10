"""
Integration tests for ensure_cfg_actual() function.

Tests full migration flow with lock coordination.
"""
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lg.migrate.runner import ensure_cfg_actual, _put_state
from lg.migrate.version import CFG_CURRENT
from lg.migrate.errors import MigrationFatalError
from lg.cache.fs_cache import Cache


def test_ensure_cfg_actual_with_no_migrations_needed(migrate_project: Path, test_cache: Cache):
    """ensure_cfg_actual completes successfully when config is already actual."""
    cfg_root = migrate_project / "lg-cfg"

    # Pre-set as actual
    _put_state(
        test_cache,
        repo_root=migrate_project,
        cfg_root=cfg_root,
        actual=CFG_CURRENT,
        applied=[],
        last_error=None
    )

    # Should complete without error
    ensure_cfg_actual(cfg_root)

    # State should remain actual
    state = test_cache.get_cfg_state(cfg_root)
    assert state["actual"] == CFG_CURRENT


@patch('lg.migrate.runner.get_migrations')
def test_ensure_cfg_actual_executes_migrations(mock_get_migs, migrate_project: Path):
    """ensure_cfg_actual runs migrations when needed."""
    cfg_root = migrate_project / "lg-cfg"

    # Mock migrations
    mock_migration = Mock()
    mock_migration.id = 1
    mock_migration.title = "Test Migration"
    mock_migration.run = Mock(return_value=True)  # Migration made changes
    mock_get_migs.return_value = [mock_migration]

    # Run
    ensure_cfg_actual(cfg_root)

    # Verify migration was executed
    assert mock_migration.run.called


def test_parallel_processes_coordination_with_threads(migrate_project: Path, test_cache: Cache):
    """Simulated parallel processes coordinate through lock (using threads)."""
    cfg_root = migrate_project / "lg-cfg"

    results = []
    errors = []

    def worker(worker_id: int):
        try:
            # Small random delay to increase contention
            time.sleep(worker_id * 0.05)
            ensure_cfg_actual(cfg_root)
            results.append(worker_id)
        except Exception as e:
            errors.append((worker_id, str(e)))

    # Launch 5 simulated "processes" (threads due to GIL safety)
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    # All workers should complete successfully
    assert len(results) == 5
    assert len(errors) == 0

    # Config should be actual
    state = test_cache.get_cfg_state(cfg_root)
    assert state["actual"] >= CFG_CURRENT


@patch('lg.migrate.runner.get_migrations')
def test_migration_failure_recorded_in_cache(mock_get_migs, migrate_project: Path, test_cache: Cache):
    """Failed migrations are recorded in cache state."""
    cfg_root = migrate_project / "lg-cfg"

    # Mock failing migration
    mock_migration = Mock()
    mock_migration.id = 1
    mock_migration.title = "Failing Migration"
    mock_migration.run = Mock(side_effect=RuntimeError("Migration error"))
    mock_get_migs.return_value = [mock_migration]

    # Should raise MigrationFatalError
    with pytest.raises(MigrationFatalError):
        ensure_cfg_actual(cfg_root)

    # Check error was recorded
    state = test_cache.get_cfg_state(cfg_root)
    assert state["last_error"] is not None
    assert "Migration error" in state["last_error"]["message"]


def test_double_check_after_wait_prevents_duplicate_work(migrate_project: Path, test_cache: Cache):
    """Waiting process doesn't re-run migrations after another process completes."""
    cfg_root = migrate_project / "lg-cfg"

    migration_run_count = [0]

    @patch('lg.migrate.runner.get_migrations')
    def first_worker(mock_get_migs):
        """First worker acquires lock and runs migrations."""
        mock_migration = Mock()
        mock_migration.id = 1
        mock_migration.title = "Test Migration"

        def record_run(*args, **kwargs):
            migration_run_count[0] += 1
            time.sleep(0.3)  # Simulate work
            return True

        mock_migration.run = Mock(side_effect=record_run)
        mock_get_migs.return_value = [mock_migration]

        ensure_cfg_actual(cfg_root)

    def second_worker():
        """Second worker waits for first to complete."""
        time.sleep(0.1)  # Let first worker acquire lock
        ensure_cfg_actual(cfg_root)

    # Run both workers
    t1 = threading.Thread(target=first_worker)
    t2 = threading.Thread(target=second_worker)

    t1.start()
    t2.start()

    t1.join(timeout=5)
    t2.join(timeout=5)

    # Migration should run exactly once (by first worker only)
    assert migration_run_count[0] == 1
