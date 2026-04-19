import curses
import json
import os
from pathlib import Path

os.environ.setdefault("ESCDELAY", "0")

MODES = [
    "Dark",
    "Light",
]

SETTINGS_PATH = Path("settings.json")


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text())
        except Exception:
            pass
    return {}


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))


def run_color_mode(stdscr, color_mode: str) -> bool:
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()

    if color_mode == "dark":
        curses.init_pair(1, curses.COLOR_RED,     -1)
        curses.init_pair(2, curses.COLOR_WHITE,   -1)
        curses.init_pair(3, curses.COLOR_MAGENTA, -1)
    else:
        curses.init_pair(1, curses.COLOR_RED,     -1)
        curses.init_pair(2, curses.COLOR_BLACK,   -1)
        curses.init_pair(3, curses.COLOR_MAGENTA, -1)

    RED  = curses.color_pair(1) | curses.A_BOLD
    NORM = curses.color_pair(2)
    HINT = curses.color_pair(3)

    def safe(y, x, text, attr=None):
        if attr is None:
            attr = NORM
        h, w = stdscr.getmaxyx()
        text = str(text)
        if y < 0 or y >= h or x < 0 or x >= w:
            return
        try:
            stdscr.attron(attr)
            stdscr.addstr(y, x, text[:w - x - 1])
            stdscr.attroff(attr)
        except:
            pass

    def draw_header(title: str) -> None:
        h, w = stdscr.getmaxyx()
        controls = "↑↓ navigate   enter select   esc back"
        safe(0, 0, " @ WENDY ", RED)
        safe(0, 9, title, NORM)
        safe(0, w - len(controls) - 1, controls, HINT)
        try:
            stdscr.attron(RED)
            stdscr.hline(1, 0, curses.ACS_HLINE, w - 1)
            stdscr.attroff(RED)
        except:
            pass

    settings = load_settings()
    cursor = next((i for i, m in enumerate(MODES) if m.lower() == color_mode), 0)
    changed = False

    while True:
        h, w = stdscr.getmaxyx()
        stdscr.erase()
        draw_header("color mode")

        for i, mode in enumerate(MODES):
            row = 3 + i * 2
            if cursor == i:
                safe(row, 2, ">", RED)
                safe(row, 4, mode, RED)
            else:
                safe(row, 4, mode, NORM)

        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_UP:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_DOWN:
            cursor = min(len(MODES) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            chosen = MODES[cursor].lower()
            if chosen != color_mode:
                settings["color_mode"] = chosen
                save_settings(settings)
                changed = True
            break
        elif key in (ord("q"), 27):
            break

    return changed
