from lg.adapters.markdown import MarkdownAdapter

MD = """\
# Guide

## Getting Started
Intro

## CLI Options
--foo
--bar

## FAQ
### User
Q/A

### Dev
Q/A

## Legacy Notes
old
"""

def _adapter(cfg):
    return MarkdownAdapter().bind(cfg)  # type: ignore

def test_sections_match_by_slug():
    cfg = {
        "drop": {
            "sections": [
                {"match": {"kind": "slug", "pattern": "cli-options"}}
            ],
            "markers": [],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(drop {title} L{level}; {lines})*"},
        },
        "max_heading_level": None,
    }
    out, meta = _adapter(cfg).process(MD, group_size=1, mixed=False)
    assert "CLI Options" not in out
    assert "Getting Started" in out
    assert "FAQ" in out
    # уровень подставился
    assert "L2" in out
    assert int(meta.get("md.placeholders", 0)) == 1

def test_sections_match_by_regex_flags():
    cfg = {
        "drop": {
            "sections": [
                {"match": {"kind": "regex", "pattern": "^legacy", "flags": "i"}}
            ],
            "markers": [],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(omitted {title})*"},
        },
        "max_heading_level": None,
    }
    out, meta = _adapter(cfg).process(MD, group_size=1, mixed=False)
    assert "Legacy Notes" not in out
    assert int(meta.get("md.placeholders", 0)) == 1

def test_sections_match_by_path_only():
    cfg = {
        "drop": {
            "sections": [
                {"path": ["FAQ", "User"], "placeholder": "> *(FAQ user pruned)*"}
            ],
            "markers": [],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(GEN)*"},
        },
        "max_heading_level": None,
    }
    out, meta = _adapter(cfg).process(MD, group_size=1, mixed=False)
    assert "### User" not in out
    assert "### Dev" in out
    assert "> *(FAQ user pruned)*" in out
    assert int(meta.get("md.placeholders", 0)) == 1

def test_sections_level_bounds():
    cfg = {
        "drop": {
            "sections": [
                # удалим только H2 разделы (level_exact)
                {"match": {"kind": "regex", "pattern": "."}, "level_exact": 2, "reason": "demo"}
            ],
            "markers": [],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(omit L{level} {title})*"},
        },
        "max_heading_level": None,
    }
    out, meta = _adapter(cfg).process(MD, group_size=1, mixed=False)
    # Все H2 (Getting Started, CLI Options, FAQ, Legacy Notes) удалены целиком
    assert "## " not in out
    # остался только корневой H1
    assert "# Guide" in out
    # placeholder-ы есть
    assert int(meta.get("md.placeholders", 0)) >= 1

def test_sections_match_plus_path_combo():
    cfg = {
        "drop": {
            "sections": [
                # совпадение по text + ограничение по предкам (ничего не вырежет, т.к. у "Dev" предок FAQ)
                {"match": {"kind": "text", "pattern": "Dev"}, "path": ["User"]},
                # совпадение по text + правильный путь
                {"match": {"kind": "text", "pattern": "Dev"}, "path": ["FAQ"]},
            ],
            "markers": [],
            "frontmatter": False,
            "placeholder": {"mode": "summary", "template": "> *(PH)*"},
        },
        "max_heading_level": None,
    }
    out, meta = _adapter(cfg).process(MD, group_size=1, mixed=False)
    assert "### Dev" not in out
    assert "### User" in out
    assert int(meta.get("md.placeholders", 0)) == 1
