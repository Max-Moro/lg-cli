import pytest

from lg.conf import build_typed, ConfigCoerceError
from lg.markdown.model import MarkdownCfg, MarkdownDropCfg, SectionRule, SectionMatch, MarkerRule, PlaceholderPolicy


def test_build_markdowncfg_with_nested_drop():
    raw = {
        "max_heading_level": 2,
        "drop": {
            "sections": [
                {
                    "match": {"kind": "text", "pattern": "Installation"},
                    "level_at_most": 3,
                    "reason": "user",
                    "placeholder": "> *(omitted {title}; {lines})*",
                },
                {
                    "match": {"kind": "regex", "pattern": "^(Legacy|Deprecated)", "flags": "i"},
                },
                {
                    "path": ["FAQ", "User"],
                },
            ],
            "markers": [
                {"start": "<!-- a -->", "end": "<!-- b -->", "include_markers": True, "reason": "noise"}
            ],
            "frontmatter": True,
            "placeholder": {"mode": "summary", "template": "> *(cut {title}; {lines})*"},
        },
    }
    cfg = build_typed(MarkdownCfg, raw)
    assert isinstance(cfg, MarkdownCfg)
    assert cfg.max_heading_level == 2
    assert isinstance(cfg.drop, MarkdownDropCfg)
    assert cfg.drop.frontmatter is True
    assert isinstance(cfg.drop.placeholder, PlaceholderPolicy)
    assert cfg.drop.placeholder.mode == "summary"
    assert cfg.drop.sections and isinstance(cfg.drop.sections[0], SectionRule)
    assert isinstance(cfg.drop.sections[0].match, SectionMatch)
    assert cfg.drop.sections[0].match.kind == "text"
    assert cfg.drop.sections[1].match.kind == "regex"
    assert cfg.drop.sections[2].path == ["FAQ", "User"]
    assert isinstance(cfg.drop.markers[0], MarkerRule)
    assert cfg.drop.markers[0].include_markers is True


def test_unknown_key_in_nested_model_raises():
    raw = {
        "max_heading_level": 2,
        "drop": {
            "sections": [{
                "match": {"kind": "text", "pattern": "X"},
                "unknown_field": 123
            }]
        }
    }
    with pytest.raises(ConfigCoerceError) as ei:
        build_typed(MarkdownCfg, raw)
    # Должен подсветить путь до поля
    assert "drop.sections.0" in str(ei.value) or "sections.0" in str(ei.value)


def test_literal_validation():
    raw = {
        "drop": {
            "placeholder": {"mode": "none"}  # допустимое Literal
        }
    }
    cfg = build_typed(MarkdownCfg, raw)
    assert cfg.drop.placeholder.mode == "none"
