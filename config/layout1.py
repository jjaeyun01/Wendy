"""
Single-pane workspace layouts (Contents has one app selected).
UI matches config/layout3.py: palette, safe, draw_header.
"""

import curses
import os

from config.layout_common import cat_label

os.environ.setdefault("ESCDELAY", "0")

TAG_PLACEHOLDER = ["A: —"]

LAYOUTS_1 = [
    {
        "id": 1,
        "name": "Full",
        "art": [
            "+----------------------------+",
            "|                            |",
            "|             A              |",
            "|                            |",
            "+----------------------------+",
        ],
    },
]


def _a_tag_lines(
    slots: dict[str, str] | None,
    apps: list[str] | None,
) -> list[str]:
    # One app in Contents → region A is that app (no saved slots required).
    if apps is not None and len(apps) == 1:
        return [f"A: {cat_label(apps[0])}"]
    if not slots or "A" not in slots:
        return list(TAG_PLACEHOLDER)
    if apps is not None and slots.get("A") not in apps:
        return list(TAG_PLACEHOLDER)
    return [f"A: {cat_label(slots['A'])}"]


def pick_layout_1(
    stdscr,
    p,
    safe,
    draw_header,
    header_title: str,
    *,
    current_layout_id: int | None = None,
    cursor_start_id: int | None = None,
    slots: dict[str, str] | None = None,
    apps: list[str] | None = None,
) -> int | None:
    layouts = LAYOUTS_1
    selected = 0
    start_id = cursor_start_id if cursor_start_id is not None else current_layout_id
    if start_id is not None:
        for i, lo in enumerate(layouts):
            if lo["id"] == start_id:
                selected = i
                break

    while True:
        _, w = stdscr.getmaxyx()
        stdscr.erase()
        draw_header(header_title, "↑↓ navigate   enter select   esc back")

        for i, layout in enumerate(layouts):
            row = 3 + i * 2
            is_cursor = i == selected
            is_saved = current_layout_id is not None and layout["id"] == current_layout_id
            cur = ">" if is_cursor else " "
            if is_cursor:
                attr = p["RED"]
            elif is_saved:
                attr = p["RED"]
            else:
                attr = p["NORM"]
            safe(row, 2, cur, attr)
            safe(row, 4, f"{layout['id']:02d}  {layout['name']}", attr)

        layout = layouts[selected]
        art = layout["art"]
        art_w = len(art[0]) if art else 0
        art_col = max(4, w - art_w - 4)
        art_row = 3

        for j, line in enumerate(art):
            safe(art_row + j, art_col, line, p["RED"])

        tag_lines = _a_tag_lines(slots, apps)
        if tag_lines:
            max_tag_len = max(len(t) for t in tag_lines)
            gap = 2
            tag_start_col = art_col + art_w + gap
            if tag_start_col + max_tag_len < w:
                for k, line in enumerate(tag_lines):
                    safe(art_row + k, tag_start_col, line, p["DIM"])
            else:
                y0 = art_row + len(art)
                for k, line in enumerate(tag_lines):
                    safe(y0 + k, art_col, line, p["DIM"])

        stdscr.refresh()
        key = stdscr.getch()

        if key in (ord("q"), 27):
            return None
        if key == curses.KEY_UP:
            selected = max(0, selected - 1)
        elif key == curses.KEY_DOWN:
            selected = min(len(layouts) - 1, selected + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            return layouts[selected]["id"]
