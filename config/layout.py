"""
Workspace layout pickers for 1–4 Contents apps (tile ASCII + region slot assignment).
Used from config/states.py — palette, safe, draw_header passed in.
"""

from __future__ import annotations

import curses
import os
from collections.abc import Callable

os.environ.setdefault("ESCDELAY", "0")


def cat_label(key: str) -> str:
    return {
        "browser": "Browser",
        "ide": "IDE",
        "music": "Music",
        "notes": "Notes",
        "terminal": "Terminal",
    }.get(key, key.replace("_", " ").title())


TAG_1 = ["A: —"]
TAG_2 = ["A: —", "B: —"]
TAG_3 = ["A: —", "B: —", "C: —"]
TAG_4 = ["A: —", "B: —", "C: —", "D: —"]


def _layout_id_eq(a: int | str | None, b: int | str | None) -> bool:
    if a is None or b is None:
        return False
    try:
        return int(a) == int(b)
    except (TypeError, ValueError):
        return False


LAYOUTS_1 = [
    {
        "id": 1,
        "name": "Full",
        "art": [
            "+-------------------------+",
            "|                         |",
            "|                         |",
            "|            A            |",
            "|                         |",
            "|                         |",
            "+-------------------------+",
        ],
    },
]

LAYOUTS_2 = [
    {
        "id": 1,
        "name": "Side by side",
        "art": [
            "+------------+------------+",
            "|            |            |",
            "|      A     |      B     |",
            "|            |            |",
            "|            |            |",
            "|            |            |",
            "+------------+------------+",
        ],
    },
    {
        "id": 2,
        "name": "Stacked",
        "art": [
            "+-------------------------+",
            "|                         |",
            "|            A            |",
            "+-------------------------+",
            "|                         |",
            "|            B            |",
            "+-------------------------+",
        ],
    },
]

LAYOUTS_3 = [
    {
        "id": 1,
        "name": "Equal Thirds",
        "art": [
            "+--------+-------+--------+",
            "|        |       |        |",
            "|   A    |   B   |   C    |",
            "|        |       |        |",
            "|        |       |        |",
            "|        |       |        |",
            "+--------+-------+--------+",
        ],
    },
    {
        "id": 2,
        "name": "Side + Stacked",
        "art": [
            "+------------+------------+",
            "|            |     B      |",
            "|     A      |            |",
            "|            +------------+",
            "|            |     C      |",
            "|            |            |",
            "+------------+------------+",
        ],
    },
    {
        "id": 3,
        "name": "Stacked + Side",
        "art": [
            "+------------+------------+",
            "|     B      |            |",
            "|            |     A      |",
            "+------------+            |",
            "|     C      |            |",
            "|            |            |",
            "+------------+------------+",
        ],
    },
]

LAYOUTS_4 = [
    {
        "id": 1,
        "name": "2×2 Grid",
        "art": [
            "+------------+------------+",
            "|      A     |      B     |",
            "|            |            |",
            "+------------+------------+",
            "|      C     |      D     |",
            "|            |            |",
            "+------------+------------+",
        ],
    },
]


def _a_tag_lines(
    slots: dict[str, str] | None,
    apps: list[str] | None,
) -> list[str]:
    if apps is not None and len(apps) == 1:
        return [f"A: {cat_label(apps[0])}"]
    if not slots or "A" not in slots:
        return list(TAG_1)
    if apps is not None and slots.get("A") not in apps:
        return list(TAG_1)
    return [f"A: {cat_label(slots['A'])}"]


def _ab_tag_lines(
    slots: dict[str, str] | None,
    apps: list[str] | None,
) -> list[str]:
    if (
        slots
        and all(k in slots for k in ("A", "B"))
        and (apps is None or set(slots.values()) == set(apps))
    ):
        return [
            f"A: {cat_label(slots['A'])}",
            f"B: {cat_label(slots['B'])}",
        ]
    return list(TAG_2)


def _abc_tag_lines(
    slots: dict[str, str] | None,
    apps: list[str] | None,
) -> list[str]:
    if not slots or not all(k in slots for k in ("A", "B", "C")):
        return list(TAG_3)
    if apps is not None and len(apps) == 3 and set(slots.values()) != set(apps):
        return list(TAG_3)
    return [
        f"A: {cat_label(slots['A'])}",
        f"B: {cat_label(slots['B'])}",
        f"C: {cat_label(slots['C'])}",
    ]


def _abcd_tag_lines(
    slots: dict[str, str] | None,
    apps: list[str] | None,
) -> list[str]:
    if (
        slots
        and all(k in slots for k in ("A", "B", "C", "D"))
        and (apps is None or set(slots.values()) == set(apps))
    ):
        return [
            f"A: {cat_label(slots['A'])}",
            f"B: {cat_label(slots['B'])}",
            f"C: {cat_label(slots['C'])}",
            f"D: {cat_label(slots['D'])}",
        ]
    return list(TAG_4)


def _pick_layout_screen(
    stdscr,
    p,
    safe,
    draw_header,
    header_title: str,
    layouts: list,
    *,
    current_layout_id: int | None,
    cursor_start_id: int | None,
    slots: dict[str, str] | None,
    apps: list[str] | None,
    tag_lines_fn: Callable[[dict[str, str] | None, list[str] | None], list[str]],
) -> int | None:
    selected = 0
    start_id = cursor_start_id if cursor_start_id is not None else current_layout_id
    if start_id is not None:
        for i, lo in enumerate(layouts):
            if _layout_id_eq(lo["id"], start_id):
                selected = i
                break

    while True:
        _, w = stdscr.getmaxyx()
        stdscr.erase()
        draw_header(header_title, "↑↓ navigate   enter select   esc back")

        sel_layout = layouts[selected]
        art = sel_layout["art"]
        art_w = len(art[0]) if art else 0
        art_col = max(4, w - art_w - 4)
        art_row = 3

        for j, line in enumerate(art):
            safe(art_row + j, art_col, line, p["RED"])

        tag_lines = tag_lines_fn(slots, apps)
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

        # Draw layout list last so RED cursor / saved highlights are not covered by ASCII art.
        for i, layout in enumerate(layouts):
            row = 3 + i * 2
            is_cursor = i == selected
            is_saved = _layout_id_eq(layout["id"], current_layout_id)
            cur = ">" if is_cursor else " "
            if is_cursor or is_saved:
                attr = p["RED"]
            else:
                attr = p["NORM"]
            safe(row, 2, cur, attr)
            safe(row, 4, f"{layout['id']:02d}  {layout['name']}", attr)

        stdscr.refresh()
        key = stdscr.getch()

        if key in (ord("q"), 27):
            return None
        if key == curses.KEY_UP:
            selected = max(0, selected - 1)
        elif key == curses.KEY_DOWN:
            selected = min(len(layouts) - 1, selected + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            return int(layouts[selected]["id"])


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
    return _pick_layout_screen(
        stdscr,
        p,
        safe,
        draw_header,
        header_title,
        LAYOUTS_1,
        current_layout_id=current_layout_id,
        cursor_start_id=cursor_start_id,
        slots=slots,
        apps=apps,
        tag_lines_fn=_a_tag_lines,
    )


def pick_layout_2(
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
    return _pick_layout_screen(
        stdscr,
        p,
        safe,
        draw_header,
        header_title,
        LAYOUTS_2,
        current_layout_id=current_layout_id,
        cursor_start_id=cursor_start_id,
        slots=slots,
        apps=apps,
        tag_lines_fn=_ab_tag_lines,
    )


def pick_layout_3(
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
    return _pick_layout_screen(
        stdscr,
        p,
        safe,
        draw_header,
        header_title,
        LAYOUTS_3,
        current_layout_id=current_layout_id,
        cursor_start_id=cursor_start_id,
        slots=slots,
        apps=apps,
        tag_lines_fn=_abc_tag_lines,
    )


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
    return _pick_layout_screen(
        stdscr,
        p,
        safe,
        draw_header,
        header_title,
        LAYOUTS_4,
        current_layout_id=current_layout_id,
        cursor_start_id=cursor_start_id,
        slots=slots,
        apps=apps,
        tag_lines_fn=_abcd_tag_lines,
    )


def _pick_slot(
    stdscr,
    p,
    safe,
    draw_header,
    header_title: str,
    slot_letter: str,
    options: list[str],
) -> str | None:
    if len(options) == 1:
        return options[0]
    cursor = 0
    while True:
        _, w = stdscr.getmaxyx()
        stdscr.erase()
        draw_header(header_title, "↑↓ navigate   enter select   esc back")
        for i, opt in enumerate(options):
            row = 3 + i * 2
            label = cat_label(opt)
            is_sel = i == cursor
            cur = ">" if is_sel else " "
            attr = p["RED"] if is_sel else p["NORM"]
            safe(row, 2, cur, attr)
            safe(row, 4, label, attr)
        stdscr.refresh()
        key = stdscr.getch()
        if key in (ord("q"), 27):
            return None
        if key == curses.KEY_UP:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_DOWN:
            cursor = min(len(options) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            return options[cursor]


def assign_slots_ab(
    stdscr,
    p,
    safe,
    draw_header,
    header_base: str,
    apps: list[str],
) -> dict[str, str] | None:
    if len(apps) != 2:
        return None

    letters = ["A", "B"]
    assigned: dict[str, str] = {}
    cursor = 0

    while True:
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
            val_attr = attr if is_sel else p["NORM"]
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
                    if letter == "A" and "B" in assigned:
                        assigned.pop("B")
                assigned[letter] = picked
                for j, s in enumerate(letters):
                    if s not in assigned:
                        cursor = j
                        break


def assign_slots_abc(
    stdscr,
    p,
    safe,
    draw_header,
    header_base: str,
    apps: list[str],
) -> dict[str, str] | None:
    if len(apps) != 3:
        return None

    region_keys = ["A", "B", "C"]
    assigned: dict[str, str] = {}
    cursor = 0

    while True:
        all_done = all(s in assigned for s in region_keys)

        stdscr.erase()
        hint = (
            "enter select   esc layout"
            if not all_done
            else "enter confirm   esc layout"
        )
        draw_header(header_base, hint)

        for i, letter in enumerate(region_keys):
            row = 3 + i * 2
            is_sel = i == cursor
            cur = ">" if is_sel else " "
            attr = p["RED"] if is_sel else p["NORM"]
            value = cat_label(assigned[letter]) if letter in assigned else "—"
            val_attr = attr if is_sel else p["NORM"]
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
            cursor = min(len(region_keys) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            if all_done:
                return assigned
            letter = region_keys[cursor]
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
                    old = assigned.pop(letter)
                    if assigned.get("C") != old and "C" in assigned:
                        pass
                    elif "C" in assigned:
                        assigned.pop("C")
                assigned[letter] = picked
                for j, s in enumerate(region_keys):
                    if s not in assigned:
                        cursor = j
                        break


def assign_slots_abcd(
    stdscr,
    p,
    safe,
    draw_header,
    header_base: str,
    apps: list[str],
) -> dict[str, str] | None:
    if len(apps) != 4:
        return None

    letters = ["A", "B", "C", "D"]
    assigned: dict[str, str] = {}
    cursor = 0

    while True:
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
            val_attr = attr if is_sel else p["NORM"]
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
