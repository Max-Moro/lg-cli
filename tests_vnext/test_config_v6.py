from pathlib import Path
import pytest
from lg_vnext.config.load import load_config_v6, list_sections

def test_load_config_v6_ok(tmpproj: Path):
    cfg = load_config_v6(tmpproj)
    assert cfg.schema_version == 6
    assert set(cfg.sections.keys()) == {"all", "docs"}
    assert cfg.sections["all"].code_fence is True
    assert cfg.sections["docs"].markdown.max_heading_level == 3

def test_list_sections(tmpproj: Path):
    assert list_sections(tmpproj) == ["all", "docs"]

def test_load_config_v6_missing(tmp_path: Path):
    with pytest.raises(RuntimeError):
        load_config_v6(tmp_path)
