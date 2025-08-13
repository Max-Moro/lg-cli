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
        # Приводим все маски к lowercase, чтобы матчинг был нечувствителен к регистру
        allow_patterns = [pat.lower() for pat in src.allow]
        block_patterns = [pat.lower() for pat in src.block]

        self.allow_ps = (
            pathspec.PathSpec.from_lines("gitwildmatch", allow_patterns)
            if allow_patterns else None
        )
        self.block_ps = (
            pathspec.PathSpec.from_lines("gitwildmatch", block_patterns)
            if block_patterns else None
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

        Алгоритм (исправленный для вложенных `mode: allow`):
        1) Идём сверху вниз по каталожным сегментам, накапливая «самый глубокий» узел,
           для каждого узла вычисляем подстроку пути, относительную этому узлу.
        2) На каждом уровне:
           • Сначала проверяем `block`: совпало → немедленно False.
           • Если `mode == 'allow'`: ДОЛЖНО совпасть с локальным allow, иначе немедленно False.
             (т. е. `allow` действует как жёсткий фильтр для поддерева.)
           • Если `mode == 'block'` и `allow` совпал → запоминаем True, но продолжаем проход
             вниз — дочерний `block` всё ещё может запретить.
        3) Если до конца не принято решение — возвращаем fallback:
           deepest.mode == 'block'  → True  (default-allow)
           deepest.mode == 'allow'  → False (default-deny)
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
            # 1) block всегда сильнее — немедленный отказ
            if nd.block_ps and nd.block_ps.match_file(sub):
                return False

            # 2) Жёсткая семантика для mode=allow:
            #    Всё, что не попало под allow текущего узла, отбрасываем сразу.
            if nd.mode == "allow":
                # Пустой allow_ps (или None) в режиме allow означает "ничего не разрешено".
                if not nd.allow_ps or not nd.allow_ps.match_file(sub):
                    return False
                # Попали под локальный allow → пока разрешаем и идём дальше (дочерние узлы могут сузить правила)
                decision = True
                continue

            # 3) mode=block: default-allow, но локальный allow может включать
            if nd.allow_ps and nd.allow_ps.match_file(sub):
                decision = True

        # Если на пути не встретился ни один явный запрет/разрешение,
        # решение принимает самый глубокий узел.
        if decision is not None:
            return decision

        # --- fallback по mode самого глубокого узла ----------------- #
        return node.mode == "block"  # default-allow если mode == block
