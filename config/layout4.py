"""
Four-pane workspace layouts (Contents has four apps selected).
UI matches config/layout3.py: palette, safe, draw_header.
"""

import curses
import os

from config.layout_common import cat_label
from config.layout3 import _pick_slot

os.environ.setdefault("ESCDELAY", "0")

TAG_PLACEHOLDER = ["A: —", "B: —", "C: —", "D: —"]

LAYOUTS_4 = [
    {
        "id": 1,
        "name": "2×2 Grid",
        "art": [
            "+-------------+-------------+",
            "|      A      |      B      |",
            "+-------------+-------------+",
            "|      C      |      D      |",
            "+-------------+-------------+",
        ],
    },
]


def _abcd_tag_lines(
    slots: dict[str, str] | None,
    apps: list[str] | None,
) -> list[str]:
    """
    Right-hand legend: saved A–D mapping when valid; else four Contents apps in
    sorted order (same idea as layout2).
    """
    if apps is not None and len(apps) == 4:
        if (
            slots
            and all(k in slots for k in ("A", "B", "C", "D"))
            and set(slots.values()) == set(apps)
        ):
            return [
                f"A: {cat_label(slots['A'])}",
                f"B: {cat_label(slots['B'])}",
                f"C: {cat_label(slots['C'])}",
                f"D: {cat_label(slots['D'])}",
            ]
        a0, a1, a2, a3 = sorted(apps)
        return [
            f"A: {cat_label(a0)}",
            f"B: {cat_label(a1)}",
            f"C: {cat_label(a2)}",
            f"D: {cat_label(a3)}",
        ]
    if not slots or not all(k in slots for k in ("A", "B", "C", "D")):
        return list(TAG_PLACEHOLDER)
    return [
        f"A: {cat_label(slots['A'])}",
        f"B: {cat_label(slots['B'])}",
        f"C: {cat_label(slots['C'])}",
        f"D: {cat_label(slots['D'])}",
    ]


def pick_layout_4(
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
    layouts = LAYOUTS_4
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

        tag_lines = _abcd_tag_lines(slots, apps)
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


def assign_slots_abcd(
    stdscr,
    p,
    safe,
    draw_header,
    header_base: str,
    apps: list[str],
) -> dict[str, str] | None:
    """
    Map regions A–D to the four enabled categories. Pick A, B, C; D is the last app.
    Returns {"A":…, "B":…, "C":…, "D":…} or None on esc (back to tile picker).
    """
    if len(apps) != 4:
        return None

    letters = ["A", "B", "C", "D"]
    assigned: dict[str, str] = {}
    cursor = 0

    while True:
        if (
            "A" in assigned
            and "B" in assigned
            and "C" in assigned
            and "D" not in assigned
        ):
            remaining = [a for a in sorted(apps) if a not in assigned.values()]
            assigned["D"] = remaining[0]

        all_done = all(x in assigned for x in letters)

        stdscr.erase()
        hint = (
            "enter select   esc layout"
            if not all_done
            else "enter confirm   esc layout"
        )
        draw_header(header_base, hint)

        for i, letter in enumerate(letters):
            row = 3 + i * 2
            is_sel = i == cursor
            cur = ">" if is_sel else " "
            attr = p["RED"] if is_sel else p["NORM"]
            value = cat_label(assigned[letter]) if letter in assigned else "—"
            val_attr = p["DIM"] if letter == "D" and "D" not in assigned else p["NORM"]
            if is_sel:
                val_attr = attr
            safe(row, 2, cur, attr)
            safe(row, 4, f"Region {letter}", attr)
            safe(row, 16, value, val_attr)

        stdscr.refresh()
        key = stdscr.getch()

        if key in (ord("q"), 27):
            return None
        elif key == curses.KEY_UP:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_DOWN:
            cursor = min(len(letters) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            if all_done:
                return assigned
            letter = letters[cursor]
            if letter == "D":
                continue
            available = [a for a in sorted(apps) if a not in assigned.values()
                         or assigned.get(letter) == a]
            if letter in assigned:
                available = [assigned[letter]] + [
                    a for a in sorted(apps)
                    if a != assigned[letter] and a not in assigned.values()
                ]
            picked = _pick_slot(
                stdscr,
                p,
                safe,
                draw_header,
                f"{header_base}  /  {letter}",
                letter,
                available,
            )
            if picked is not None:
                if letter in assigned:
                    assigned.pop(letter)
                    if "D" in assigned:
                        assigned.pop("D")
                assigned[letter] = picked
                for j, s in enumerate(letters):
                    if s not in assigned:
                        cursor = j
                        break
