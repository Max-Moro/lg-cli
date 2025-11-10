"""
Fixtures for migration system tests.
"""
import pytest
from pathlib import Path
from lg.migrate.runner import _MigrationLock
from lg.cache.fs_cache import Cache


@pytest.fixture
def migrate_project(tmp_path: Path) -> Path:
    """
    Minimal project structure for migration tests.

    Creates:
    - lg-cfg/sections.yaml (minimal config)
    - .lg-cache/ (created on demand by _MigrationLock)

    Returns:
        Path to project root
    """
    root = tmp_path
    cfg_dir = root / "lg-cfg"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    # Minimal sections.yaml
    sections_yaml = cfg_dir / "sections.yaml"
    sections_yaml.write_text(
        "all:\n"
        "  extensions: ['.md']\n",
        encoding="utf-8"
    )

    return root


@pytest.fixture
def cache_dir(migrate_project: Path) -> Path:
    """Cache directory for migration lock testing."""
    return migrate_project / ".lg-cache"


@pytest.fixture
def cfg_root(migrate_project: Path) -> Path:
    """Configuration directory for migration testing."""
    return migrate_project / "lg-cfg"


@pytest.fixture
def migration_lock(cache_dir: Path, cfg_root: Path) -> _MigrationLock:
    """
    Configured _MigrationLock instance with short timeouts for testing.

    Uses:
    - stale_seconds=1 (quick for tests)
    - wait_timeout=3 (fail fast if hanging)
    """
    return _MigrationLock(
        cache_dir=cache_dir,
        cfg_root=cfg_root,
        stale_seconds=1,
        wait_timeout=3
    )


@pytest.fixture
def test_cache(migrate_project: Path) -> Cache:
    """Cache instance for migration state testing."""
    return Cache(
        migrate_project,
        enabled=True,
        fresh=False,
        tool_version="test"
    )
