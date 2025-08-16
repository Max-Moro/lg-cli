from __future__ import annotations

from pathlib import PurePosixPath
from typing import Dict, List, Tuple

import pathspec  # Git-wildmatch backend

from .model import FilterNode


class _CompiledNode:
    """Внутреннее представление узла с готовыми PathSpec-ами."""
    __slots__ = ("mode", "allow_ps", "block_ps", "children", "allow_raw", "block_raw")

    def __init__(self, src: FilterNode):
        self.mode = src.mode
        # Приводим все маски к lowercase, чтобы матчинг был нечувствителен к регистру
        allow_patterns = [pat.lower() for pat in src.allow]
        block_patterns = [pat.lower() for pat in src.block]
        # Храним «сырые» списки для эвристик прунинга директорий
        self.allow_raw = allow_patterns
        self.block_raw = block_patterns

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
    # INNER HELPERS
    # ------------------------------------------------------------ #
    def _nodes_chain(self, path: str) -> List[Tuple[_CompiledNode, str]]:
        """
        Построить цепочку (узел, subpath) от корня до «самого глубокого»
        узла, соответствующего подпапкам пути.
        Используется и в includes(), и в may_descend().
        """
        norm = path.lower().strip("/")
        parts = PurePosixPath(norm).parts

        node = self._root
        nodes_to_check: List[Tuple[_CompiledNode, str]] = [(node, norm or "")]

        for idx, part in enumerate(parts[:-1]):  # последняя часть — файл или текущая папка
            nxt = node.children.get(part)
            if nxt is None:
                break
            node = nxt
            subpath = "/".join(parts[idx + 1 :]) or "."
            nodes_to_check.append((node, subpath))
        return nodes_to_check

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
        nodes_to_check = self._nodes_chain(rel_path)
        # deepest node — последний кортеж
        node = nodes_to_check[-1][0]

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

    # ------------------------------------------------------------ #
    def may_descend(self, rel_dir: str) -> bool:
        """
        Быстрый ответ на вопрос: есть ли смысл спускаться в поддерево `rel_dir/`?
        Используется для раннего отсечения директорий при обходе ФС.
        Семантика консервативная (False → точно бесполезно; True → возможно полезно).
        """
        # Нормализуем и гарантируем вид "dir" без ведущего слеша
        norm = rel_dir.strip("/").lower()
        if norm == "":
            return True  # корень всегда пригоден

        nodes_to_check = self._nodes_chain(norm)
        # deepest node нужен для fallback-логики в конце
        node = nodes_to_check[-1][0]

        decision: bool | None = None
        for nd, sub in nodes_to_check:
            # Блокирующее правило на поддереве — спуск бесполезен
            if nd.block_ps and (nd.block_ps.match_file(sub) or nd.block_ps.match_file(sub + "/")):
                return False

            if nd.mode == "allow":
                # Пустой allow в allow-узле → внутри ничего не разрешено
                if not nd.allow_ps:
                    return False
                # 2.1 Быстрая эвристика по «сырым» паттернам:
                #     - basename-паттерн без '/' (напр. "*.md") → может матчиться в любом каталоге
                #     - паттерн, начинающийся с этого каталога (c/без ведущего '/'): "/dir/..." или "dir/..."
                #     - паттерн с "**" — потенциально матчится в глубине
                sub_no_slash = sub.lstrip("/")
                for pat in nd.allow_raw:
                    if "**" in pat:
                        decision = True
                        break
                    if "/" not in pat:
                        decision = True
                        break
                    if pat.startswith(sub_no_slash + "/") or pat.startswith("/" + sub_no_slash + "/"):
                        decision = True
                        break
                # 2.2 Консервативная проверка через PathSpec
                if decision or (
                    nd.allow_ps.match_file(sub) or
                    nd.allow_ps.match_file(sub + "/") or
                    nd.allow_ps.match_file(sub + "/x")
                ):
                    decision = True
                else:
                    # В строгом allow-режиме отсутствие совпадений на уровне узла
                    # означает, что ниже спускаться смысла нет.
                    return False
            else:
                # mode=block: default-allow — спуск потенциально полезен, но
                # локальный allow ещё больше подтверждает это.
                if nd.allow_ps and (
                    nd.allow_ps.match_file(sub) or
                    nd.allow_ps.match_file(sub + "/") or
                    nd.allow_ps.match_file(sub + "/x")
                ):
                    decision = True

        if decision is not None:
            return decision
        # Фоллбек: в block-узле (default-allow) можно спускаться, в allow — нельзя
        return node.mode == "block"
