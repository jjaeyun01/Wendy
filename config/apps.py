import curses
import json
import os
from pathlib import Path
from config.palette import make_palette

os.environ.setdefault("ESCDELAY", "0")

CATEGORIES = [
    "Browser",
    "IDE",
    "Music",
    "Notes",
    "Terminal",
]

CATEGORY_HINTS = {
    "Browser":  ["chrome", "firefox", "safari", "brave", "arc", "edge", "opera", "vivaldi"],
    "IDE":      ["code", "xcode", "intellij", "pycharm", "webstorm", "goland", "rider", "clion", "rubymine", "sublime", "atom", "zed", "cursor", "nova"],
    "Music":    ["spotify", "music", "itunes", "vox", "doppler", "capo", "swinsian", "deezer", "tidal", "chrome", "firefox", "safari", "brave", "arc", "edge", "opera", "vivaldi"],
    "Notes":    ["obsidian", "notion", "bear", "notes", "craft", "roam", "logseq", "evernote", "simplenote", "ulysses", "typora"],
    "Terminal": ["terminal", "iterm", "iterm2", "warp", "alacritty", "kitty", "hyper", "ghostty"],
}

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


def get_applications() -> list[str]:
    apps = set()
    search_dirs = [
        Path("/Applications"),
        Path("/System/Applications"),
        Path("/System/Applications/Utilities"),
        Path.home() / "Applications",
    ]
    for app_dir in search_dirs:
        if app_dir.exists():
            for path in app_dir.iterdir():
                if path.suffix == ".app":
                    apps.add(path.name[:-4])
    return sorted(apps, key=lambda x: x.lower())


def filter_apps(all_apps: list[str], category: str) -> list[str]:
    hints = CATEGORY_HINTS.get(category, [])
    matched = [a for a in all_apps if any(h in a.lower() for h in hints)]
    return matched if matched else all_apps


def run_apps(stdscr, color_mode: str) -> bool:
    curses.curs_set(0)
    p = make_palette(color_mode)

    def safe(y, x, text, attr=None):
        if attr is None:
            attr = p["NORM"]
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
        safe(0, 0, " @ WENDY ", p["RED"])
        safe(0, 9, title, p["DIM"])
        safe(0, w - len(controls) - 1, controls, p["PINK"])
        try:
            stdscr.attron(p["RED"])
            stdscr.hline(1, 0, curses.ACS_HLINE, w - 1)
            stdscr.attroff(p["RED"])
        except:
            pass

    settings = load_settings()
    all_apps = get_applications()
    cursor = 0
    changed = False

    # ── Category screen ───────────────────────────────────────────────────────
    while True:
        h, w = stdscr.getmaxyx()
        stdscr.erase()
        draw_header("apps")

        for i, cat in enumerate(CATEGORIES):
            row = 3 + i * 2
            current = settings.get(cat.lower(), "")
            suffix = f"  {current}" if current else ""
            if cursor == i:
                safe(row, 2, ">", p["RED"])
                safe(row, 4, cat, p["RED"])
                if suffix:
                    safe(row, 4 + len(cat), suffix, p["DIM"])
            else:
                safe(row, 4, cat, p["NORM"])
                if suffix:
                    safe(row, 4 + len(cat), suffix, p["DIM"])

        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_UP:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_DOWN:
            cursor = min(len(CATEGORIES) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            chosen_cat = CATEGORIES[cursor]
            filtered = filter_apps(all_apps, chosen_cat)

            # ── App picker screen ─────────────────────────────────────────────
            app_cursor = 0
            scroll = 0
            while True:
                h, w = stdscr.getmaxyx()
                stdscr.erase()
                draw_header(f"apps  /  {chosen_cat.lower()}")

                list_rows = (h - 4) // 2
                if app_cursor < scroll:
                    scroll = app_cursor
                elif app_cursor >= scroll + list_rows:
                    scroll = app_cursor - list_rows + 1

                if not filtered:
                    safe(3, 4, "No apps found in /Applications.", p["DIM"])
                else:
                    for screen_i, idx in enumerate(range(scroll, min(scroll + list_rows, len(filtered)))):
                        row = 3 + screen_i * 2
                        app_name = filtered[idx]
                        if app_cursor == idx:
                            safe(row, 2, ">", p["RED"])
                            safe(row, 4, app_name, p["RED"])
                        else:
                            safe(row, 4, app_name, p["NORM"])

                stdscr.refresh()
                key = stdscr.getch()

                if key == curses.KEY_UP:
                    app_cursor = max(0, app_cursor - 1)
                elif key == curses.KEY_DOWN:
                    app_cursor = min(len(filtered) - 1, app_cursor + 1)
                elif key in (curses.KEY_ENTER, 10, 13):
                    if filtered:
                        settings[chosen_cat.lower()] = filtered[app_cursor]
                        save_settings(settings)
                        changed = True
                    break
                elif key in (ord("q"), 27):
                    break

        elif key in (ord("q"), 27):
            break

    return changed
