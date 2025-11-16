from __future__ import annotations

import re
from pathlib import Path

import pytest

from lg.template.common import parse_locator, resolve_cfg_root
from lg.config.paths import cfg_root


def test_parse_locator_local_and_addressed(monorepo: Path):
    loc = parse_locator("tpl:docs/guide", expected_kind="tpl")
    assert loc.origin == "self"
    assert loc.resource == "docs/guide"

    loc = parse_locator("tpl@apps/web:docs/guide", expected_kind="tpl")
    assert loc.origin == "apps/web"
    assert loc.resource == "docs/guide"

    loc = parse_locator("tpl@[apps/web]:docs/a:b", expected_kind="tpl")
    assert loc.origin == "apps/web"
    assert loc.resource == "docs/a:b"

    with pytest.raises(RuntimeError, match="Invalid locator"):
        parse_locator("tpl:", expected_kind="tpl")

    with pytest.raises(RuntimeError, match="Invalid locator"):
        parse_locator("tpl@", expected_kind="tpl")

    with pytest.raises(RuntimeError, match="Not a tpl locator"):
        parse_locator("foo@apps/web:docs/guide", expected_kind="tpl")


def test_resolve_cfg_root_self_and_child(monorepo: Path):
    base = cfg_root(monorepo)
    got_self = resolve_cfg_root("self", current_cfg_root=base, repo_root=monorepo)
    assert got_self == base and got_self.is_dir()

    got_child = resolve_cfg_root("apps/web", current_cfg_root=base, repo_root=monorepo)
    assert got_child == (monorepo / "apps" / "web" / "lg-cfg")


def test_resolve_cfg_root_missing_and_escape(monorepo: Path):
    base = cfg_root(monorepo)

    with pytest.raises(RuntimeError, match="Child lg-cfg not found"):
        resolve_cfg_root("missing/pkg", current_cfg_root=base, repo_root=monorepo)

    # Attempt to escape beyond repo boundaries
    with pytest.raises(RuntimeError, match=re.escape("escapes repository")):
        resolve_cfg_root("../..", current_cfg_root=base, repo_root=monorepo)
