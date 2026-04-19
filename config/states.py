import curses
import os

from config.layout3 import assign_slots_abc, pick_layout_3
from config.palette import make_palette
from config.settings_store import load_settings, save_settings

os.environ.setdefault("ESCDELAY", "0")

CATEGORIES = ["Browser", "IDE", "Music", "Notes", "Terminal"]
WORKSPACE_IDS = [str(i) for i in range(1, 10)] + [chr(c) for c in range(ord("A"), ord("Z") + 1)]

# ── Layouts for 1, 2, or 4 content apps (3-pane layouts live in config/layout3.py) ─

LAYOUTS_1 = [
    {
        "id": 1,
        "name": "Full",
        "tag": "100%",
        "art": [
            "+----------------------------+",
            "|                            |",
            "|             A              |",
            "|                            |",
            "+----------------------------+",
        ],
    },
]

LAYOUTS_2 = [
    {
        "id": 1,
        "name": "Side by side",
        "tag": "1/2 + 1/2",
        "art": [
            "+-------------+-------------+",
            "|             |             |",
            "|      A      |      B      |",
            "|             |             |",
            "+-------------+-------------+",
        ],
    },
    {
        "id": 2,
        "name": "Stacked",
        "tag": "1/2 + 1/2",
        "art": [
            "+----------------------------+",
            "|            A               |",
            "+----------------------------+",
            "|            B               |",
            "+----------------------------+",
        ],
    },
]

LAYOUTS_4 = [
    {
        "id": 1,
        "name": "2×2 Grid",
        "tag": "2×2",
        "art": [
            "+-------------+-------------+",
            "|      A      |      B      |",
            "+-------------+-------------+",
            "|      C      |      D      |",
            "+-------------+-------------+",
        ],
    },
    {
        "id": 2,
        "name": "Columns",
        "tag": "4 × 1/4",
        "art": [
            "+-----+-----+-----+-----+",
            "|  A  |  B  |  C  |  D  |",
            "|     |     |     |     |",
            "|     |     |     |     |",
            "+-----+-----+-----+-----+",
        ],
    },
]


def _layouts_for_content_count(n: int) -> list:
    if n <= 0:
        return []
    if n == 1:
        return LAYOUTS_1
    if n == 2:
        return LAYOUTS_2
    if n == 4:
        return LAYOUTS_4
    return []


def _pick_layout_list(stdscr, p, safe, draw_header, header_title: str, layouts: list) -> int | None:
    """Generic layout picker for 1, 2, or 4 panes (same interaction as layout3)."""
    if not layouts:
        return None
    selected = 0
    while True:
        _, w = stdscr.getmaxyx()
        stdscr.erase()
        draw_header(header_title, "↑↓ navigate   enter select   esc back")

        for i, layout in enumerate(layouts):
            row = 3 + i * 2
            is_sel = i == selected
            cur = ">" if is_sel else " "
            attr = p["RED"] if is_sel else p["NORM"]
            safe(row, 2, cur, attr)
            safe(row, 4, f"{layout['id']:02d}  {layout['name']}", attr)

        layout = layouts[selected]
        art = layout["art"]
        art_w = len(art[0]) if art else 0
        art_col = max(4, w - art_w - 4)
        art_row = 3

        for j, line in enumerate(art):
            safe(art_row + j, art_col, line, p["RED"])

        y_after = art_row + len(art) + 1
        if layout.get("tag_lines"):
            for k, line in enumerate(layout["tag_lines"]):
                safe(y_after + k, art_col, line, p["DIM"])
        elif layout.get("tag"):
            safe(y_after, art_col, layout["tag"], p["DIM"])

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

# After picking a workspace: alphabetical — Contents (app toggles + URLs), Layouts (tile picker).
WORKSPACE_VIEWS = ["Contents", "Layouts"]


def run_states(stdscr, color_mode: str) -> bool:
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

    def draw_header(title: str, controls: str = "↑↓ navigate   enter open   esc back") -> None:
        h, w = stdscr.getmaxyx()
        safe(0, 0, " @ WENDY ", p["RED"])
        safe(0, 9, title, p["DIM"])
        safe(0, w - len(controls) - 1, controls, p["PINK"])
        try:
            stdscr.attron(p["RED"])
            stdscr.hline(1, 0, curses.ACS_HLINE, w - 1)
            stdscr.attroff(p["RED"])
        except:
            pass

    def draw_shortcuts() -> None:
        h, w = stdscr.getmaxyx()
        shortcuts = "n  new   d  delete"
        safe(h - 1, w - len(shortcuts) - 1, shortcuts, p["DIM"])

    settings = load_settings()
    states = sorted(settings.get("states", {}).keys())
    cursor = 0
    scroll = 0
    changed = False
    adding = False
    input_buf = ""

    # ── States list screen ────────────────────────────────────────────────────
    while True:
        h, w = stdscr.getmaxyx()
        list_rows = (h - 4) // 2
        stdscr.erase()
        draw_header("states")

        if not states:
            safe(3, 4, "No states yet.", p["DIM"])
        else:
            if cursor < scroll:
                scroll = cursor
            elif cursor >= scroll + list_rows:
                scroll = cursor - list_rows + 1

            for screen_i, idx in enumerate(range(scroll, min(scroll + list_rows, len(states)))):
                row = 3 + screen_i * 2
                name = states[idx]
                if cursor == idx:
                    safe(row, 2, ">", p["RED"])
                    safe(row, 4, name, p["RED"])
                else:
                    safe(row, 4, name, p["NORM"])

        if adding:
            prompt = "new state: "
            safe(h - 1, 0, prompt + input_buf + "█", p["PINK"])
        else:
            draw_shortcuts()

        stdscr.refresh()

        if adding:
            key = stdscr.getch()
            if key in (curses.KEY_ENTER, 10, 13):
                name = input_buf.strip()
                if name:
                    if "states" not in settings:
                        settings["states"] = {}
                    settings["states"][name] = {"workspaces": {}}
                    save_settings(settings)
                    states = sorted(settings["states"].keys())
                    cursor = states.index(name)
                    changed = True
                adding = False
                input_buf = ""
            elif key == 27:
                adding = False
                input_buf = ""
            elif key in (curses.KEY_BACKSPACE, 127):
                input_buf = input_buf[:-1]
            elif 32 <= key <= 126:
                input_buf += chr(key)
        else:
            key = stdscr.getch()

            if key == curses.KEY_UP:
                cursor = max(0, cursor - 1)
            elif key == curses.KEY_DOWN:
                cursor = min(max(0, len(states) - 1), cursor + 1)
            elif key in (curses.KEY_ENTER, 10, 13):
                if states:
                    chosen = states[cursor]
                    state_changed = _run_workspaces(stdscr, color_mode, chosen, p, safe, draw_header)
                    if state_changed:
                        changed = True
                    settings = load_settings()
                    states = sorted(settings.get("states", {}).keys())
            elif key == ord("n"):
                adding = True
                input_buf = ""
            elif key == ord("d"):
                if states:
                    name = states[cursor]
                    settings.get("states", {}).pop(name, None)
                    save_settings(settings)
                    states = sorted(settings.get("states", {}).keys())
                    cursor = min(cursor, max(0, len(states) - 1))
                    changed = True
            elif key in (ord("q"), 27):
                break

    return changed


def _run_workspaces(stdscr, color_mode, state_name, p, safe, draw_header) -> bool:
    # ── Workspace list screen ─────────────────────────────────────────────────
    # WORKSPACE_IDS = ["1".."9", "A".."Z"]
    # Show them in a grid, highlight selected ones (have apps assigned)
    COLS = 9  # 9 per row looks clean: 1-9 on first row, A-I, J-R, S-Z
    cursor = 0
    changed = False

    while True:
        settings = load_settings()
        state = settings.get("states", {}).get(state_name, {})
        workspaces = state.get("workspaces", {})

        h, w = stdscr.getmaxyx()
        stdscr.erase()
        draw_header(
            f"states  /  {state_name}",
            "↑↓←→ navigate   enter open   esc back",
        )

        safe(3, 4, "workspaces", p["DIM"])

        for i, ws_id in enumerate(WORKSPACE_IDS):
            col = i % COLS
            row_n = i // COLS
            y = 5 + row_n * 2
            x = 4 + col * 5

            has_apps = bool(workspaces.get(ws_id, {}).get("apps"))
            is_cursor = cursor == i

            if is_cursor:
                safe(y, x - 2, ">", p["RED"])

            if is_cursor:
                attr = p["RED"]
            elif has_apps:
                attr = p["PINK"]
            else:
                attr = p["NORM"]

            safe(y, x, ws_id, attr)

        # Show current workspace summary bottom right
        current_ws_id = WORKSPACE_IDS[cursor]
        current_apps = workspaces.get(current_ws_id, {}).get("apps", [])
        summary = f"{current_ws_id}:  " + ("  ".join(a.capitalize() for a in current_apps) if current_apps else "empty")
        safe(h - 1, w - len(summary) - 1, summary, p["DIM"])

        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_UP:
            cursor = max(0, cursor - COLS)
        elif key == curses.KEY_DOWN:
            cursor = min(len(WORKSPACE_IDS) - 1, cursor + COLS)
        elif key == curses.KEY_LEFT:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_RIGHT:
            cursor = min(len(WORKSPACE_IDS) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            ws_id = WORKSPACE_IDS[cursor]
            ws_changed = _run_workspace_menu(
                stdscr, color_mode, state_name, ws_id, p, safe, draw_header
            )
            if ws_changed:
                changed = True
        elif key in (ord("q"), 27):
            break

    return changed


def _run_workspace_menu(stdscr, color_mode, state_name, ws_id, p, safe, draw_header) -> bool:
    """Contents vs Layouts (alphabetical). Esc from Contents returns here; esc from menu returns to grid."""
    cursor = 0  # Contents — first row
    changed = False
    while True:
        h, w = stdscr.getmaxyx()
        stdscr.erase()
        draw_header(
            f"states  /  {state_name}  /  {ws_id}",
            "↑↓ navigate   enter open   esc back",
        )
        for i, label in enumerate(WORKSPACE_VIEWS):
            row = 3 + i * 2
            if cursor == i:
                safe(row, 2, ">", p["RED"])
                safe(row, 4, label, p["RED"])
            else:
                safe(row, 4, label, p["NORM"])

        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_UP:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_DOWN:
            cursor = min(len(WORKSPACE_VIEWS) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            if WORKSPACE_VIEWS[cursor] == "Layouts":
                if _run_workspace_layouts(stdscr, state_name, ws_id, p, safe, draw_header):
                    changed = True
            else:
                if _run_ws_apps(stdscr, color_mode, state_name, ws_id, p, safe, draw_header):
                    changed = True
        elif key in (ord("q"), 27):
            return changed


def _run_workspace_layouts(stdscr, state_name, ws_id, p, safe, draw_header) -> bool:
    """Pick a tile layout matching the number of apps in Contents. Saves `layout: {n, id}`."""
    settings = load_settings()
    state = settings.get("states", {}).get(state_name, {})
    ws_data = state.get("workspaces", {}).get(ws_id, {})
    n = len(ws_data.get("apps") or [])

    if n == 0:
        while True:
            stdscr.erase()
            draw_header(
                f"states  /  {state_name}  /  {ws_id}  /  layouts",
                "esc back",
            )
            safe(3, 4, "No contents selected. Open Contents first, then choose Layouts.", p["DIM"])
            stdscr.refresh()
            key = stdscr.getch()
            if key in (ord("q"), 27):
                return False

    n = min(n, 4)
    header = f"states  /  {state_name}  /  {ws_id}  /  layouts"
    if n == 3:
        picked_id = pick_layout_3(stdscr, p, safe, draw_header, header)
        if picked_id is None:
            return False
        apps_three = sorted(ws_data.get("apps") or [])
        if len(apps_three) != 3:
            return False
        slots = assign_slots_abc(stdscr, p, safe, draw_header, header, apps_three)
        if slots is None:
            return False
        settings = load_settings()
        if "states" not in settings:
            settings["states"] = {}
        if state_name not in settings["states"]:
            settings["states"][state_name] = {}
        st = settings["states"][state_name]
        if "workspaces" not in st:
            st["workspaces"] = {}
        prev = dict(st["workspaces"].get(ws_id, {}))
        prev["layout"] = {"n": 3, "id": picked_id, "slots": slots}
        st["workspaces"][ws_id] = prev
        save_settings(settings)
        return True

    layouts = _layouts_for_content_count(n)
    if not layouts:
        return False
    picked_id = _pick_layout_list(stdscr, p, safe, draw_header, header, layouts)
    if picked_id is None:
        return False

    settings = load_settings()
    if "states" not in settings:
        settings["states"] = {}
    if state_name not in settings["states"]:
        settings["states"][state_name] = {}
    st = settings["states"][state_name]
    if "workspaces" not in st:
        st["workspaces"] = {}
    prev = dict(st["workspaces"].get(ws_id, {}))
    prev["layout"] = {"n": n, "id": picked_id}
    st["workspaces"][ws_id] = prev
    save_settings(settings)
    return True


def _run_ws_apps(stdscr, color_mode, state_name, ws_id, p, safe, draw_header) -> bool:
    # ── App toggle screen for one workspace ───────────────────────────────────
    settings = load_settings()
    state = settings.get("states", {}).get(state_name, {})
    workspaces = state.get("workspaces", {})
    ws_data = workspaces.get(ws_id, {})
    enabled = set(ws_data.get("apps", []))
    browser_url = ws_data.get("browser_url", "")
    music_url = ws_data.get("music_url", "")
    cursor = 0
    url_input = False
    url_buf = ""
    url_target = None  # "browser" or "music"

    BROWSER_HINTS = ["chrome", "firefox", "safari", "brave", "arc", "edge", "opera", "vivaldi"]

    def music_is_browser(s):
        app = s.get("apps", {}).get("music", "").lower()
        return any(h in app for h in BROWSER_HINTS)

    while True:
        h, w = stdscr.getmaxyx()
        settings = load_settings()
        stdscr.erase()
        draw_header(
            f"states  /  {state_name}  /  {ws_id}",
            "↑↓ navigate   enter toggle   esc save",
        )

        for i, cat in enumerate(CATEGORIES):
            row = 3 + i * 2
            selected = cat.lower() in enabled
            if cursor == i:
                safe(row, 2, ">", p["RED"])
                safe(row, 4, cat, p["RED"])
            elif selected:
                safe(row, 4, cat, p["PINK"])
            else:
                safe(row, 4, cat, p["NORM"])

            # Show URL inline after Browser or Music (if music app is a browser)
            if not url_input:
                if cat.lower() == "browser" and browser_url:
                    max_len = w - (4 + len(cat) + 2) - 2
                    url_display = browser_url if len(browser_url) <= max_len else browser_url[:max_len - 3] + "..."
                    safe(row, 4 + len(cat), f"  {url_display}", p["DIM"])
                elif cat.lower() == "music" and music_url and music_is_browser(settings):
                    max_len = w - (4 + len(cat) + 2) - 2
                    url_display = music_url if len(music_url) <= max_len else music_url[:max_len - 3] + "..."
                    safe(row, 4 + len(cat), f"  {url_display}", p["DIM"])

        count_str = f"{len(enabled)}/4"
        safe(h - 1, w - len(count_str) - 1, count_str, p["RED"] if len(enabled) >= 4 else p["DIM"])

        if url_input:
            safe(h - 1, 0, "url: " + url_buf + "█", p["PINK"])

        stdscr.refresh()
        key = stdscr.getch()

        if url_input:
            if key in (curses.KEY_ENTER, 10, 13):
                if url_target == "browser":
                    browser_url = url_buf.strip()
                elif url_target == "music":
                    music_url = url_buf.strip()
                url_input = False
                url_buf = ""
                url_target = None
            elif key == 27:
                url_input = False
                url_buf = ""
                url_target = None
            elif key in (curses.KEY_BACKSPACE, 127):
                url_buf = url_buf[:-1]
            elif 32 <= key <= 126:
                url_buf += chr(key)
        else:
            if key == curses.KEY_UP:
                cursor = max(0, cursor - 1)
            elif key == curses.KEY_DOWN:
                cursor = min(len(CATEGORIES) - 1, cursor + 1)
            elif key in (curses.KEY_ENTER, 10, 13):
                cat = CATEGORIES[cursor].lower()
                if cat in enabled:
                    enabled.discard(cat)
                    if cat == "browser":
                        browser_url = ""
                    elif cat == "music":
                        music_url = ""
                else:
                    if len(enabled) < 4:
                        enabled.add(cat)
                        if cat == "browser":
                            url_input = True
                            url_buf = browser_url
                            url_target = "browser"
                        elif cat == "music" and music_is_browser(settings):
                            url_input = True
                            url_buf = music_url
                            url_target = "music"
            elif key in (ord("q"), 27):
                settings = load_settings()
                if "states" not in settings:
                    settings["states"] = {}
                if state_name not in settings["states"]:
                    settings["states"][state_name] = {}
                if "workspaces" not in settings["states"][state_name]:
                    settings["states"][state_name]["workspaces"] = {}
                settings["states"][state_name]["workspaces"][ws_id] = {
                    "apps": sorted(enabled),
                    "browser_url": browser_url,
                    "music_url": music_url,
                }
                save_settings(settings)
                break

    return True
