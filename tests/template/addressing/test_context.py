"""
Tests for lg/template/addressing/context.py

Tests AddressingContext class for managing directory context stack.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lg.template.addressing import AddressingContext, DirectoryContext


class TestAddressingContextInit:
    """Tests for AddressingContext initialization."""

    def test_init_creates_root_context(self, tmp_path: Path):
        """Initialization creates root context with 'self' origin."""
        cfg_root = tmp_path / "lg-cfg"
        ctx = AddressingContext(tmp_path, cfg_root)

        assert len(ctx) == 1
        assert ctx.origin == "self"
        assert ctx.current_directory == ""
        assert ctx.cfg_root == cfg_root.resolve()

    def test_repo_root_is_resolved(self, tmp_path: Path):
        """Repo root path is resolved to absolute."""
        cfg_root = tmp_path / "lg-cfg"
        ctx = AddressingContext(tmp_path, cfg_root)

        assert ctx.repo_root.is_absolute()


class TestAddressingContextStack:
    """Tests for stack operations in AddressingContext."""

    def test_push_adds_context(self, tmp_path: Path):
        """Push adds new context to stack."""
        cfg_root = tmp_path / "lg-cfg"
        ctx = AddressingContext(tmp_path, cfg_root)

        ctx.push("apps/web", "docs", cfg_root)

        assert len(ctx) == 2
        assert ctx.origin == "apps/web"
        assert ctx.current_directory == "docs"

    def test_pop_removes_context(self, tmp_path: Path):
        """Pop removes and returns top context."""
        cfg_root = tmp_path / "lg-cfg"
        ctx = AddressingContext(tmp_path, cfg_root)
        ctx.push("apps/web", "docs", cfg_root)

        popped = ctx.pop()

        assert len(ctx) == 1
        assert ctx.origin == "self"
        assert popped.origin == "apps/web"

    def test_pop_root_raises_error(self, tmp_path: Path):
        """Cannot pop root context."""
        cfg_root = tmp_path / "lg-cfg"
        ctx = AddressingContext(tmp_path, cfg_root)

        with pytest.raises(RuntimeError, match="Cannot pop root"):
            ctx.pop()

    def test_nested_push_pop(self, tmp_path: Path):
        """Multiple push/pop operations work correctly."""
        cfg_root = tmp_path / "lg-cfg"
        ctx = AddressingContext(tmp_path, cfg_root)

        ctx.push("scope1", "dir1", cfg_root)
        ctx.push("scope2", "dir2", cfg_root)
        assert len(ctx) == 3
        assert ctx.origin == "scope2"

        ctx.pop()
        assert len(ctx) == 2
        assert ctx.origin == "scope1"

        ctx.pop()
        assert len(ctx) == 1
        assert ctx.origin == "self"


class TestAddressingContextPushForFile:
    """Tests for push_for_file convenience method."""

    def test_push_for_file_computes_directory(self, tmp_path: Path):
        """push_for_file computes current_dir from file path."""
        cfg_root = tmp_path / "lg-cfg"
        cfg_root.mkdir(parents=True)
        (cfg_root / "docs").mkdir()
        file_path = cfg_root / "docs" / "api.tpl.md"
        file_path.touch()

        ctx = AddressingContext(tmp_path, cfg_root)
        ctx.push_for_file(file_path)

        assert ctx.current_directory == "docs"

    def test_push_for_file_with_new_origin(self, tmp_path: Path):
        """push_for_file with new origin changes scope."""
        cfg_root = tmp_path / "lg-cfg"
        cfg_root.mkdir(parents=True)

        # Create apps/web/lg-cfg structure
        web_cfg = tmp_path / "apps" / "web" / "lg-cfg"
        web_cfg.mkdir(parents=True)
        file_path = web_cfg / "intro.tpl.md"
        file_path.touch()

        ctx = AddressingContext(tmp_path, cfg_root)
        ctx.push_for_file(file_path, new_origin="apps/web")

        assert ctx.origin == "apps/web"
        assert ctx.cfg_root == web_cfg.resolve()

    def test_push_for_file_at_root(self, tmp_path: Path):
        """push_for_file for file at lg-cfg root sets empty current_dir."""
        cfg_root = tmp_path / "lg-cfg"
        cfg_root.mkdir(parents=True)
        file_path = cfg_root / "main.ctx.md"
        file_path.touch()

        ctx = AddressingContext(tmp_path, cfg_root)
        ctx.push_for_file(file_path)

        assert ctx.current_directory == ""


class TestAddressingContextProperties:
    """Tests for AddressingContext properties."""

    def test_current_returns_top_context(self, tmp_path: Path):
        """current property returns top of stack."""
        cfg_root = tmp_path / "lg-cfg"
        ctx = AddressingContext(tmp_path, cfg_root)
        ctx.push("apps/web", "docs", cfg_root)

        current = ctx.current

        assert isinstance(current, DirectoryContext)
        assert current.origin == "apps/web"

    def test_get_effective_origin_for_self(self, tmp_path: Path):
        """get_effective_origin returns 'self' for root scope."""
        cfg_root = tmp_path / "lg-cfg"
        ctx = AddressingContext(tmp_path, cfg_root)

        assert ctx.get_effective_origin() == "self"

    def test_get_effective_origin_for_nested(self, tmp_path: Path):
        """get_effective_origin returns path for nested scope."""
        cfg_root = tmp_path / "lg-cfg"
        ctx = AddressingContext(tmp_path, cfg_root)
        ctx.push("apps/web", "", cfg_root)

        assert ctx.get_effective_origin() == "apps/web"

    def test_repr_is_readable(self, tmp_path: Path):
        """repr shows useful information."""
        cfg_root = tmp_path / "lg-cfg"
        ctx = AddressingContext(tmp_path, cfg_root)
        ctx.push("apps/web", "docs", cfg_root)

        repr_str = repr(ctx)

        assert "depth=2" in repr_str
        assert "apps/web" in repr_str
