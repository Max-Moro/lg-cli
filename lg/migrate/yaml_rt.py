from __future__ import annotations

from pathlib import Path
from typing import Callable

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString, SingleQuotedScalarString

_YAML_RT = YAML(typ="rt")
_YAML_RT.preserve_quotes = True       # preserve original quotes
_YAML_RT.indent(mapping=2, sequence=4, offset=2)
# Optionally, to prevent ruamel from reformatting lines with wrapping:
_YAML_RT.width = 1000000


def load_yaml_rt(path: Path) -> CommentedMap:
    data = _YAML_RT.load(path.read_text(encoding="utf-8", errors="ignore")) or CommentedMap()
    if not isinstance(data, CommentedMap):
        # Normalize to map — section files are maps by contract
        data = CommentedMap()
    return data


def dump_yaml_rt(path: Path, data: CommentedMap) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp-rt")
    with tmp.open("w", encoding="utf-8") as f:
        _YAML_RT.dump(data, f)
    tmp.replace(path)


def rewrite_yaml_rt(path: Path, transform: Callable[[CommentedMap], bool]) -> bool:
    """
    Load YAML with round-trip, call transform(map) → bool "changed?",
    and if changed — save atomically.
    """
    data = load_yaml_rt(path)
    changed = bool(transform(data))
    if changed:
        dump_yaml_rt(path, data)
    return changed

def dq(s: str) -> DoubleQuotedScalarString:
    """Force wrap string in double quotes when writing."""
    return DoubleQuotedScalarString(s)

def sq(s: str) -> SingleQuotedScalarString:
    """Force wrap string in single quotes when writing."""
    return SingleQuotedScalarString(s)

__all__ = ["load_yaml_rt", "dump_yaml_rt", "rewrite_yaml_rt", "dq", "sq"]
