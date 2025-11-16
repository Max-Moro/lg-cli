from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

from ..types import PathLabelMode


def _split(rel_posix: str) -> List[str]:
    # Always POSIX ('/'), input comes from Manifest.rel_path
    return rel_posix.split("/")


def _join(parts: List[str]) -> str:
    return "/".join(parts)


def _common_dir_prefix(paths: List[List[str]]) -> List[str]:
    """
    Common directory prefix across all paths (excluding file name).
    Returns a list of directory components that match for all paths.
    """
    if not paths:
        return []
    # Compare only directories (all except the last component — basename)
    dirs = [p[:-1] if p else [] for p in paths]
    if not all(dirs):
        # If any path is flat (only basename), no prefix exists
        pass
    pref: List[str] = []
    i = 0
    while True:
        token: str | None = None
        for d in dirs:
            if i >= len(d):
                token = None
                break
            if token is None:
                token = d[i]
            elif d[i] != token:
                token = None
                break
        if token is None:
            break
        pref.append(token)
        i += 1
    return pref


def _minimal_unique_suffixes(paths: List[List[str]]) -> List[str]:
    """
    For each path, select the minimal unique suffix (by components from the right).
    Example: ["lg","engine.py"], ["io","engine.py"] → "lg/engine.py", "io/engine.py".
    """
    n = len(paths)
    # Start with basename (last component)
    suffix_len = [1] * n

    def key(i: int) -> Tuple[str, ...]:
        return tuple(paths[i][-suffix_len[i] :])

    changed = True
    while changed:
        changed = False
        seen: Dict[Tuple[str, ...], int] = {}
        clash: Dict[Tuple[str, ...], int] = {}

        for i in range(n):
            k = key(i)
            if k in seen:
                clash[k] = 1
            else:
                seen[k] = 1

        if not clash:
            break

        for i in range(n):
            k = key(i)
            if k in clash:
                # Increase suffix if possible
                if suffix_len[i] < len(paths[i]):
                    suffix_len[i] += 1
                    changed = True
        # Loop ends when collisions disappear or all reach the full path

    out: List[str] = []
    for i in range(n):
        out.append(_join(paths[i][-suffix_len[i] :]))
    return out


def build_labels(rel_paths: Iterable[str], *, mode: PathLabelMode, origin: str = "self") -> Dict[str, str]:
    """
    Build a map {rel_path → label} considering the selected mode.
    The rel_paths argument contains POSIX paths (as in Manifest.rel_path).

    Args:
        rel_paths: Iterable collection of relative paths
        mode: Label display mode
        origin: Current origin from template context ("self" or path to a subregion)
    """
    rel_list = list(rel_paths)
    if not rel_list:
        return {}

    if mode == "relative":
        # Trivially — label equals the original relative path
        return {p: p for p in rel_list}

    parts_all: List[List[str]] = [_split(p) for p in rel_list]

    if mode == "basename":
        labels = _minimal_unique_suffixes(parts_all)
        return {p: lbl for p, lbl in zip(rel_list, labels)}

    # mode == "scope_relative": strip origin (if not "self")
    if mode == "scope_relative":
        if origin and origin != "self":
            # Strip origin prefix from all paths
            origin_prefix = origin.rstrip("/") + "/"
            stripped_paths = []
            for p in rel_list:
                if p.startswith(origin_prefix):
                    stripped_paths.append(p[len(origin_prefix):])
                elif p == origin.rstrip("/"):
                    # Path matches origin (without slash)
                    stripped_paths.append(_split(p)[-1] if _split(p) else p)
                else:
                    # Path does not start with origin - keep as is
                    stripped_paths.append(p)
            return {p: lbl for p, lbl in zip(rel_list, stripped_paths)}
        else:
            # origin == "self" or empty — equivalent to "relative"
            return {p: p for p in rel_list}

    return {p: p for p in rel_list}
