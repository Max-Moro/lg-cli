from __future__ import annotations

import re


def normalize_markdown(
    text: str, *,
    max_heading_level: int | None,
    strip_h1: bool,
    file_label: str,
    placeholder_inside_heading: bool = False,
) -> tuple[str, dict]:
    """
      • Если max_heading_level=None → не трогаем (кроме снятия H1).
      • Если strip_h1=True → снимаем верхний H1 (ATX/Setext).
      • Сдвиг уровней заголовков так, чтобы минимальный уровень стал равен max_heading_level.
      • Если file_label задан → вставляем HTML-комментарий с меткой файла.
    """
    meta = {"md.removed_h1": 0, "md.shifted": False, "md.file_label_inserted": False}

    lines = text.splitlines()

    # 1) специальная обработка для плейсхолдеров внутри заголовков
    removed_h1 = False
    h1_line_index = -1  # индекс строки где был/есть H1
    
    if placeholder_inside_heading and lines:
        # Для плейсхолдеров внутри заголовков извлекаем только текст H1 без символов #
        atx_match = re.match(r"^#\s+(.*)$", lines[0])
        if atx_match:
            # Заменяем H1 на просто текст
            heading_text = atx_match.group(1).strip()
            lines[0] = heading_text
            removed_h1 = True
            h1_line_index = 0
            meta["md.removed_h1"] = 1
        elif len(lines) >= 2 and lines[0].strip() and re.match(r"^={2,}\s*$", lines[1]):
            # Setext заголовок - оставляем только текст, убираем подчеркивание
            heading_text = lines[0].strip()
            lines = [heading_text] + lines[2:]
            removed_h1 = True
            h1_line_index = 0
            meta["md.removed_h1"] = 1
    elif strip_h1:
        # Обычная обработка strip_h1
        if lines:
            # ATX: "# Title"
            if re.match(r"^#\s", lines[0]):
                lines = lines[1:]
                removed_h1 = True
                h1_line_index = -1  # H1 удален, метка в начало
                meta["md.removed_h1"] = 1
            # Setext: Title + "===="
            elif len(lines) >= 2 and lines[0].strip() and re.match(r"^={2,}\s*$", lines[1]):
                lines = lines[2:]
                removed_h1 = True
                h1_line_index = -1  # H1 удален, метка в начало
                meta["md.removed_h1"] = 1
    else:
        # H1 не удаляется - найдем его позицию для вставки метки после него
        if lines:
            # ATX: "# Title"
            if re.match(r"^#\s", lines[0]):
                h1_line_index = 0
            # Setext: Title + "===="
            elif len(lines) >= 2 and lines[0].strip() and re.match(r"^={2,}\s*$", lines[1]):
                h1_line_index = 1  # после подчеркивания

    # Вставка метки файла (до нормализации уровней заголовков)
    file_comment = f"<!-- FILE: {file_label} -->"

    if placeholder_inside_heading and removed_h1 and h1_line_index >= 0:
        # Особый случай: placeholder_inside_heading + H1 был преобразован в текст
        # Вставляем комментарий ПОСЛЕ строки с текстом заголовка
        insert_pos = h1_line_index + 1
        lines.insert(insert_pos, file_comment)
    elif removed_h1 or h1_line_index < 0:
        # H1 был полностью удален или не найден - вставляем метку в начало
        lines.insert(0, file_comment)
        # Корректируем индекс если был найден H1 после вставки
        if h1_line_index >= 0:
            h1_line_index += 1
    else:
        # H1 оставлен - вставляем метку после него
        insert_pos = h1_line_index + 1
        lines.insert(insert_pos, file_comment)

    meta["md.file_label_inserted"] = True

    if max_heading_level is None:
        return "\n".join(lines), meta

    max_lvl = int(max_heading_level)

    in_fence = False
    fence_pat = re.compile(r"^```")
    head_pat = re.compile(r"^(#+)\s")
    
    if placeholder_inside_heading and removed_h1:
        # Специальная логика для плейсхолдеров внутри заголовков
        # H2 должен стать уровнем max_heading_level + 1
        shift = (max_lvl + 1) - 2  # H2 (уровень 2) становится max_lvl + 1
    else:
        # 2) собрать min_lvl
        min_lvl: int | None = None
        for ln in lines:
            if fence_pat.match(ln):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = head_pat.match(ln)
            if m:
                lvl = len(m.group(1))
                min_lvl = lvl if min_lvl is None else min(min_lvl, lvl)

        if min_lvl is None:
            # заголовков нет
            return "\n".join(lines), meta

        shift = max_lvl - min_lvl

    meta["md.shifted"] = bool(shift)
    if shift == 0:
        return "\n".join(lines), meta

    # 3) применить сдвиг
    out: list[str] = []
    in_fence = False
    for ln in lines:
        if fence_pat.match(ln):
            in_fence = not in_fence
            out.append(ln)
            continue
        if in_fence:
            out.append(ln)
            continue
        m = head_pat.match(ln)
        if m:
            new_level = len(m.group(1)) + shift
            # Ограничиваем максимальный уровень заголовков до H6
            if new_level > 6:
                new_level = 6
            new_hashes = "#" * new_level
            out.append(f"{new_hashes} {ln[m.end():]}")
        else:
            out.append(ln)

    return "\n".join(out), meta
