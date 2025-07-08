from __future__ import annotations

from pathlib import PurePosixPath
from typing import Dict

import pathspec  # Git-wildmatch backend

from .model import FilterNode


class _CompiledNode:
    """Внутреннее представление узла с готовыми PathSpec-ами."""
    __slots__ = ("mode", "allow_ps", "block_ps", "children")

    def __init__(self, src: FilterNode):
        self.mode = src.mode
        self.allow_ps = (
            pathspec.PathSpec.from_lines("gitwildmatch", src.allow) if src.allow else None
        )
        self.block_ps = (
            pathspec.PathSpec.from_lines("gitwildmatch", src.block) if src.block else None
        )
        self.children: Dict[str, "_CompiledNode"] = {
            name.lower(): _CompiledNode(child) for name, child in src.children.items()
        }


class FilterEngine:
    """
    Решает, следует ли включать путь `rel_posix` (строка POSIX lower-case),
    согласно дереву правил.
    """

    def __init__(self, root: FilterNode):
        self._root = _CompiledNode(root)

    # ------------------------------------------------------------ #
    def includes(self, rel_path: str) -> bool:
        """
        Вернёт True, если путь разрешён.

        Алгоритм:
        1. Идём сверху вниз по каталожным сегментам, накапливая «самый глубокий» узел.
        2. На каждом уровне: сначала применяем block, потом allow.
        3. Если ни одно правило не сработало — решение принимает `mode`
           самого глубокого узла.
        """
        path = rel_path.lower()
        parts = PurePosixPath(path).parts

        node = self._root
        nodes_to_check: list[tuple[_CompiledNode, str]] = [(node, path)]

        # Спускаемся к потомкам, если описаны
        for idx, part in enumerate(parts[:-1]):  # последняя часть — имя файла
            nxt = node.children.get(part)
            if nxt is None:
                break
            node = nxt
            subpath = "/".join(parts[idx + 1 :]) or "."  # относительный в подузле
            nodes_to_check.append((node, subpath))

        decision: bool | None = None  # None → ещё не определились

        for nd, sub in nodes_to_check:
            if nd.block_ps and nd.block_ps.match_file(sub):
                decision = False
                # block финальный, можно прервать, но обязательно пройти allow выше
            if decision is not False and nd.allow_ps and nd.allow_ps.match_file(sub):
                decision = True

        if decision is not None:
            return decision

        # --- fallback по mode самого глубокого узла ----------------- #
        return node.mode == "block"  # default-allow если mode == block
