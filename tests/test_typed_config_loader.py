import pytest

from lg.adapters.markdown import MarkdownAdapter
from lg.markdown.model import MarkdownCfg
from lg.stats.tokenizer import default_tokenizer


def test_markdown_cfg_nested_drop_is_parsed():
    raw = {
        "max_heading_level": 2,
        "drop": {
            "frontmatter": True,
            "placeholder": {"mode": "summary", "template": "> *(omit {title}; {lines})*"},
            "sections": [
                {
                    "match": {"kind": "text", "pattern": "Installation"},
                    "level_at_most": 3,
                    "reason": "user-docs",
                },
                {
                    "match": {"kind": "regex", "pattern": "^(Legacy|Deprecated)", "flags": "i"},
                },
                {
                    "path": ["FAQ", "User"],
                    "placeholder": "> *(FAQ pruned; {lines})*",
                },
            ],
            "markers": [
                {"start": "<!-- lg:omit:start -->", "end": "<!-- lg:omit:end -->", "include_markers": True}
            ],
        },
    }
    adapter = MarkdownAdapter().bind(raw, default_tokenizer())
    cfg: MarkdownCfg = adapter.cfg
    assert cfg.max_heading_level == 2
    assert cfg.drop is not None and cfg.drop.frontmatter is True
    assert cfg.drop.placeholder.mode == "summary"
    assert len(cfg.drop.sections) == 3
    assert cfg.drop.sections[0].match is not None and cfg.drop.sections[0].match.kind == "text"
    assert cfg.drop.markers[0].include_markers is True

def test_unknown_extra_key_raises():
    bad = {
        "drop": {
            "sections": [
                {
                    "match": {"kind": "text", "pattern": "A"},
                    "unknown_field": 123
                }
            ]
        }
    }
    with pytest.raises(ValueError):
        MarkdownAdapter().bind(bad, default_tokenizer())
