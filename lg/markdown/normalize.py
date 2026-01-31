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
      • If max_heading_level=None → don't touch (except H1 removal).
      • If strip_h1=True → remove top H1 (ATX/Setext).
      • Shift heading levels so minimum level equals max_heading_level.
      • If file_label provided → insert HTML comment with file marker.
    """
    meta = {"md.removed_h1": 0, "md.shifted": False, "md.file_label_inserted": False}

    lines = text.splitlines()

    # 1) special processing for placeholders inside headings
    removed_h1 = False
    h1_line_index = -1  # line index where H1 was/is

    if placeholder_inside_heading and lines:
        # For placeholders inside headings, extract H1 text without # symbols
        atx_match = re.match(r"^#\s+(.*)$", lines[0])
        if atx_match:
            # Replace H1 with plain text
            heading_text = atx_match.group(1).strip()
            lines[0] = heading_text
            removed_h1 = True
            h1_line_index = 0
            meta["md.removed_h1"] = 1
        elif len(lines) >= 2 and lines[0].strip() and re.match(r"^={2,}\s*$", lines[1]):
            # Setext heading - keep only text, remove underline
            heading_text = lines[0].strip()
            lines = [heading_text] + lines[2:]
            removed_h1 = True
            h1_line_index = 0
            meta["md.removed_h1"] = 1
    elif strip_h1:
        # Standard strip_h1 processing
        if lines:
            # ATX: "# Title"
            if re.match(r"^#\s", lines[0]):
                lines = lines[1:]
                removed_h1 = True
                h1_line_index = -1  # H1 removed, marker at start
                meta["md.removed_h1"] = 1
            # Setext: Title + "===="
            elif len(lines) >= 2 and lines[0].strip() and re.match(r"^={2,}\s*$", lines[1]):
                lines = lines[2:]
                removed_h1 = True
                h1_line_index = -1  # H1 removed, marker at start
                meta["md.removed_h1"] = 1
    else:
        # H1 not removed - find its position for marker insertion after it
        if lines:
            # ATX: "# Title"
            if re.match(r"^#\s", lines[0]):
                h1_line_index = 0
            # Setext: Title + "===="
            elif len(lines) >= 2 and lines[0].strip() and re.match(r"^={2,}\s*$", lines[1]):
                h1_line_index = 1  # after underline

    # File marker insertion (before heading level normalization)
    file_comment = f"<!-- FILE: {file_label} -->"

    if placeholder_inside_heading and removed_h1 and h1_line_index >= 0:
        # Special case: placeholder_inside_heading + H1 was converted to text
        # Insert comment AFTER heading text line
        insert_pos = h1_line_index + 1
        lines.insert(insert_pos, file_comment)
    elif removed_h1 or h1_line_index < 0:
        # H1 was completely removed or not found - insert marker at start
        lines.insert(0, file_comment)
        # Adjust index if H1 was found after insertion
        if h1_line_index >= 0:
            h1_line_index += 1
    else:
        # H1 kept - insert marker after it
        insert_pos = h1_line_index + 1
        lines.insert(insert_pos, file_comment)

    meta["md.file_label_inserted"] = True

    if max_heading_level is None:
        return "\n".join(lines), meta

    max_lvl = int(max_heading_level)

    in_fence = False
    fence_pat = re.compile(r"^(```|~~~)")  # Both ``` and ~~~ are valid fenced block delimiters
    head_pat = re.compile(r"^(#+)\s")

    if placeholder_inside_heading and removed_h1:
        # Special logic for placeholders inside headings
        # H2 should become level max_heading_level + 1
        shift = (max_lvl + 1) - 2  # H2 (level 2) becomes max_lvl + 1
    else:
        # 2) collect min_lvl
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
            # no headings
            return "\n".join(lines), meta

        shift = max_lvl - min_lvl

    meta["md.shifted"] = bool(shift)
    if shift == 0:
        return "\n".join(lines), meta

    # 3) apply shift
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
            # Limit max heading level to H6
            if new_level > 6:
                new_level = 6
            new_hashes = "#" * new_level
            out.append(f"{new_hashes} {ln[m.end():]}")
        else:
            out.append(ln)

    return "\n".join(out), meta
