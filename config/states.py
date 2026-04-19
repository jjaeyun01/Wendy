import curses
import os

from config.layout import (
    assign_slots_ab,
    assign_slots_abc,
    assign_slots_abcd,
    pick_layout_1,
    pick_layout_2,
    pick_layout_3,
    pick_layout_4,
)
from config.palette import make_palette
from config.settings_store import load_settings, save_settings

os.environ.setdefault("ESCDELAY", "0")

CATEGORIES = ["Browser", "IDE", "Music", "Notes", "Terminal"]
WORKSPACE_IDS = [str(i) for i in range(1, 10)] + [chr(c) for c in range(ord("A"), ord("Z") + 1)]

WORKSPACE_VIEWS = ["Contents", "Layouts", "Set Final Screen"]


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
    COLS = 9
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

        for i, ws_id in enumerate(WORKSPACE_IDS):
            col = i % COLS
            row_n = i // COLS
            y = 3 + row_n * 2
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
    """Contents, Layouts, Set Final Screen (alphabetical). Esc returns to grid."""
    cursor = 0
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
            elif WORKSPACE_VIEWS[cursor] == "Contents":
                if _run_ws_apps(stdscr, color_mode, state_name, ws_id, p, safe, draw_header):
                    changed = True
            # "Set Final Screen" — intentionally does nothing
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
        session_layout_id: int | None = None
        while True:
            settings = load_settings()
            state = settings.get("states", {}).get(state_name, {})
            ws_data = state.get("workspaces", {}).get(ws_id, {})
            lay = ws_data.get("layout") or {}
            saved_id = lay.get("id") if lay.get("n") == 3 else None
            cursor_id = session_layout_id if session_layout_id is not None else saved_id
            apps_three = sorted(ws_data.get("apps") or [])
            slot_map = lay.get("slots") if lay.get("n") == 3 else None
            picked_id = pick_layout_3(
                stdscr,
                p,
                safe,
                draw_header,
                header,
                current_layout_id=saved_id,
                cursor_start_id=cursor_id,
                slots=slot_map if isinstance(slot_map, dict) else None,
                apps=apps_three,
            )
            if picked_id is None:
                return False
            session_layout_id = picked_id
            if len(apps_three) != 3:
                return False
            slots = assign_slots_abc(stdscr, p, safe, draw_header, header, apps_three)
            if slots is None:
                continue
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

    if n == 2:
        session_layout_id: int | None = None
        while True:
            settings = load_settings()
            state = settings.get("states", {}).get(state_name, {})
            ws_data = state.get("workspaces", {}).get(ws_id, {})
            lay = ws_data.get("layout") or {}
            saved_id = lay.get("id") if lay.get("n") == 2 else None
            cursor_id = session_layout_id if session_layout_id is not None else saved_id
            apps_two = sorted(ws_data.get("apps") or [])
            slot_map = lay.get("slots") if lay.get("n") == 2 else None
            picked_id = pick_layout_2(
                stdscr,
                p,
                safe,
                draw_header,
                header,
                current_layout_id=saved_id,
                cursor_start_id=cursor_id,
                slots=slot_map if isinstance(slot_map, dict) else None,
                apps=apps_two,
            )
            if picked_id is None:
                return False
            session_layout_id = picked_id
            if len(apps_two) != 2:
                return False
            slots = assign_slots_ab(stdscr, p, safe, draw_header, header, apps_two)
            if slots is None:
                continue
            settings = load_settings()
            if "states" not in settings:
                settings["states"] = {}
            if state_name not in settings["states"]:
                settings["states"][state_name] = {}
            st = settings["states"][state_name]
            if "workspaces" not in st:
                st["workspaces"] = {}
            prev = dict(st["workspaces"].get(ws_id, {}))
            prev["layout"] = {"n": 2, "id": picked_id, "slots": slots}
            st["workspaces"][ws_id] = prev
            save_settings(settings)
            return True

    if n == 4:
        session_layout_id: int | None = None
        while True:
            settings = load_settings()
            state = settings.get("states", {}).get(state_name, {})
            ws_data = state.get("workspaces", {}).get(ws_id, {})
            lay = ws_data.get("layout") or {}
            saved_id = lay.get("id") if lay.get("n") == 4 else None
            cursor_id = session_layout_id if session_layout_id is not None else saved_id
            apps_four = sorted(ws_data.get("apps") or [])
            slot_map = lay.get("slots") if lay.get("n") == 4 else None
            picked_id = pick_layout_4(
                stdscr,
                p,
                safe,
                draw_header,
                header,
                current_layout_id=saved_id,
                cursor_start_id=cursor_id,
                slots=slot_map if isinstance(slot_map, dict) else None,
                apps=apps_four,
            )
            if picked_id is None:
                return False
            session_layout_id = picked_id
            if len(apps_four) != 4:
                return False
            slots = assign_slots_abcd(stdscr, p, safe, draw_header, header, apps_four)
            if slots is None:
                continue
            settings = load_settings()
            if "states" not in settings:
                settings["states"] = {}
            if state_name not in settings["states"]:
                settings["states"][state_name] = {}
            st = settings["states"][state_name]
            if "workspaces" not in st:
                st["workspaces"] = {}
            prev = dict(st["workspaces"].get(ws_id, {}))
            prev["layout"] = {"n": 4, "id": picked_id, "slots": slots}
            st["workspaces"][ws_id] = prev
            save_settings(settings)
            return True

    if n != 1:
        return False
    settings = load_settings()
    state = settings.get("states", {}).get(state_name, {})
    ws_data = state.get("workspaces", {}).get(ws_id, {})
    lay = ws_data.get("layout") or {}
    saved_id = lay.get("id") if lay.get("n") == 1 else None
    apps_n = sorted(ws_data.get("apps") or [])
    slot_map = lay.get("slots") if lay.get("n") == 1 else None
    picked_id = pick_layout_1(
        stdscr,
        p,
        safe,
        draw_header,
        header,
        current_layout_id=saved_id,
        cursor_start_id=saved_id,
        slots=slot_map if isinstance(slot_map, dict) else None,
        apps=apps_n,
    )
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
    prev["layout"] = {"n": 1, "id": picked_id}
    st["workspaces"][ws_id] = prev
    save_settings(settings)
    return True


def _run_ws_apps(stdscr, color_mode, state_name, ws_id, p, safe, draw_header) -> bool:
    settings = load_settings()
    state = settings.get("states", {}).get(state_name, {})
    workspaces = state.get("workspaces", {})
    ws_data = workspaces.get(ws_id, {})
    enabled = set(ws_data.get("apps", []))
    browser_url = ws_data.get("browser_url", "")
    music_url = ws_data.get("music_url", "")
    initial_apps = set(enabled)
    initial_browser_url = browser_url
    initial_music_url = music_url
    cursor = 0
    url_input = False
    url_buf = ""
    url_target = None

    BROWSER_HINTS = ["chrome", "firefox", "safari", "brave", "arc", "edge", "opera", "vivaldi"]

    def music_is_browser(s):
        app = s.get("apps", {}).get("music", "").lower()
        return any(h in app for h in BROWSER_HINTS)

    while True:
        h, w = stdscr.getmaxyx()
        settings = load_settings()
        state = settings.get("states", {}).get(state_name, {})
        ws_data = state.get("workspaces", {}).get(ws_id, {})
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
        count_col = w - len(count_str) - 1
        bottom_y = h - 1

        contents_dirty = (
            enabled != initial_apps
            or browser_url != initial_browser_url
            or music_url != initial_music_url
        )
        layout_hint = "Esc to save, then update layout in Layouts" if contents_dirty else None

        if url_input:
            safe(bottom_y, count_col, count_str, p["RED"] if len(enabled) >= 4 else p["DIM"])
            safe(bottom_y, 0, "url: " + url_buf + "█", p["PINK"])
        else:
            safe(
                bottom_y,
                count_col,
                count_str,
                p["RED"] if len(enabled) >= 4 else p["DIM"],
            )
            if layout_hint:
                left_max = max(0, count_col - 1)
                if left_max > 0:
                    text = layout_hint
                    if len(text) > left_max:
                        text = text[: max(0, left_max - 3)] + "..."
                    safe(bottom_y, 0, text, p["PINK"])

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
                existing_ws = settings["states"][state_name]["workspaces"].get(ws_id, {})
                ws_block = {**existing_ws}
                ws_block["apps"] = sorted(enabled)
                ws_block["browser_url"] = browser_url
                ws_block["music_url"] = music_url

                n_apps = len(enabled)
                ex_layout = existing_ws.get("layout") or {}
                ln = ex_layout.get("n")
                if n_apps == 0 or not ex_layout:
                    ws_block.pop("layout", None)
                elif ln != n_apps:
                    ws_block.pop("layout", None)
                elif n_apps == 1:
                    if ex_layout.get("id") is not None:
                        ws_block["layout"] = {"n": 1, "id": ex_layout["id"]}
                    else:
                        ws_block.pop("layout", None)
                else:
                    sl = ex_layout.get("slots")
                    if isinstance(sl, dict) and set(sl.values()) == set(enabled):
                        ws_block["layout"] = ex_layout
                    elif ex_layout.get("id") is not None:
                        ws_block["layout"] = {"n": n_apps, "id": ex_layout["id"]}
                    else:
                        ws_block.pop("layout", None)

                settings["states"][state_name]["workspaces"][ws_id] = ws_block
                save_settings(settings)
                break

    return True