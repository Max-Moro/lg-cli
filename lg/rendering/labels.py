from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

from ..types import PathLabelMode


def _split(rel_posix: str) -> List[str]:
    # Всегда POSIX (‘/’), вход — из Manifest.rel_path
    return rel_posix.split("/")


def _join(parts: List[str]) -> str:
    return "/".join(parts)


def _common_dir_prefix(paths: List[List[str]]) -> List[str]:
    """
    Общий префикс директорий по всем путям (без имени файла).
    Возвращает список компонент директории, которые совпадают у всех.
    """
    if not paths:
        return []
    # Сравниваем только директории (все кроме последней компоненты — basename)
    dirs = [p[:-1] if p else [] for p in paths]
    if not all(dirs):
        # Если у кого-то путь плоский (только basename), префикса нет
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
    Для каждого пути выбираем минимальный уникальный суффикс (по компонентам справа).
    Пример: ["lg","engine.py"], ["io","engine.py"] → "lg/engine.py", "io/engine.py".
    """
    n = len(paths)
    # Начинаем с basename (последняя компонента)
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
                # увеличиваем суффикс, если можно
                if suffix_len[i] < len(paths[i]):
                    suffix_len[i] += 1
                    changed = True
        # цикл завершится, когда коллизии исчезнут или все дойдут до полного пути

    out: List[str] = []
    for i in range(n):
        out.append(_join(paths[i][-suffix_len[i] :]))
    return out


def build_labels(rel_paths: Iterable[str], *, mode: PathLabelMode, origin: str = "self") -> Dict[str, str]:
    """
    Построить карту {rel_path → label} с учётом выбранного режима.
    Аргумент rel_paths — POSIX-пути (как в Manifest.rel_path).
    
    Args:
        rel_paths: Итерируемая коллекция относительных путей
        mode: Режим отображения меток
        origin: Текущий origin из template context ("self" или путь к подобласти)
    """
    rel_list = list(rel_paths)
    if not rel_list:
        return {}

    if mode in ("relative", "off"):
        # Тривиально — метка равна исходному относительному пути
        return {p: p for p in rel_list}

    parts_all: List[List[str]] = [_split(p) for p in rel_list]

    if mode == "basename":
        labels = _minimal_unique_suffixes(parts_all)
        return {p: lbl for p, lbl in zip(rel_list, labels)}

    # mode == "scope_relative": снимаем origin (если не "self")
    if mode == "scope_relative":
        if origin and origin != "self":
            # Снимаем origin префикс со всех путей
            origin_prefix = origin.rstrip("/") + "/"
            stripped_paths = []
            for p in rel_list:
                if p.startswith(origin_prefix):
                    stripped_paths.append(p[len(origin_prefix):])
                elif p == origin.rstrip("/"):
                    # Путь совпадает с origin (без слэша)
                    stripped_paths.append(_split(p)[-1] if _split(p) else p)
                else:
                    # Путь не начинается с origin - оставляем как есть
                    stripped_paths.append(p)
            return {p: lbl for p, lbl in zip(rel_list, stripped_paths)}
        else:
            # origin == "self" или пустой — эквивалентно "relative"
            return {p: p for p in rel_list}

    # Не должны сюда попасть, но на всякий случай
    return {p: p for p in rel_list}
