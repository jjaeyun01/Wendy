import curses
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from config.palette import make_palette

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = ROOT / "settings.json"


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")


def _motion_block(settings: dict) -> dict:
    m = settings.setdefault("motion", {})
    if not isinstance(m, dict):
        settings["motion"] = {}
        m = settings["motion"]
    m.setdefault("camera_index", 0)
    m.setdefault("templates_dir", "motions")
    m.setdefault("compare_frames", 32)
    m.setdefault("distance_threshold", 0.26)
    m.setdefault("cooldown_sec", 3.0)
    m.setdefault("record_seconds", 2.2)
    m.setdefault("match_stride", 2)
    m.setdefault("buffer_max_frames", 90)
    m.setdefault("actions", {})
    if not isinstance(m["actions"], dict):
        m["actions"] = {}
    return m


TUNABLE = [
    ("distance_threshold", "float", 0.08, 0.55, 0.02),
    ("cooldown_sec", "float", 0.5, 30.0, 0.5),
    ("camera_index", "int", 0, 6, 1),
    ("compare_frames", "int", 12, 64, 2),
    ("record_seconds", "float", 0.8, 5.0, 0.2),
    ("match_stride", "int", 1, 8, 1),
    ("buffer_max_frames", "int", 50, 180, 10),
]

LABELS = {
    "distance_threshold": "Distance threshold (higher = easier trigger)",
    "cooldown_sec": "Cooldown after trigger (seconds)",
    "camera_index": "Webcam index",
    "compare_frames": "Compare window (frames resampled)",
    "record_seconds": "Record duration (seconds)",
    "match_stride": "Match every N frames",
    "buffer_max_frames": "Motion buffer size",
}


def _template_stems(m: dict) -> list[str]:
    td = ROOT / str(m.get("templates_dir", "motions"))
    if not td.is_dir():
        return []
    return sorted(p.stem for p in td.glob("*.json"))


def _suspend_and_run_script(args: list[str]) -> None:
    curses.def_prog_mode()
    curses.endwin()
    try:
        subprocess.run([sys.executable, *args], cwd=str(ROOT))
    finally:
        try:
            input("\nPress Enter to return to Wendy…")
        except EOFError:
            pass
        curses.reset_prog_mode()


def _prompt_gesture_name(stdscr, draw_header, safe, p) -> Optional[str]:
    """Return stripped name, or None if cancelled."""
    name_buf = ""
    while True:
        h, w = stdscr.getmaxyx()
        stdscr.erase()
        draw_header()
        safe(3, 4, "Recording opens a separate webcam window.", p["NORM"])
        safe(4, 4, "There: SPACE = start   Q = quit", p["DIM"])
        safe(h - 1, 0, ("Gesture file name: " + name_buf + "█")[: w - 1], p["PINK"])
        stdscr.refresh()
        kk = stdscr.getch()
        if kk in (curses.KEY_ENTER, 10, 13):
            return name_buf.strip() or None
        if kk in (27,):
            return None
        if kk in (curses.KEY_BACKSPACE, 127):
            name_buf = name_buf[:-1]
        elif 32 <= kk <= 126:
            name_buf += chr(kk)


def run_motion(stdscr, color_mode: str) -> bool:
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
            stdscr.addstr(y, x, text[: w - x - 1])
            stdscr.attroff(attr)
        except Exception:
            pass

    def draw_header() -> None:
        h, w = stdscr.getmaxyx()
        controls = "↑↓ move   ←→ tune   esc back"
        safe(0, 0, " @ WENDY ", p["RED"])
        safe(0, 9, "motion", p["DIM"])
        safe(0, w - len(controls) - 1, controls, p["PINK"])
        try:
            stdscr.attron(p["RED"])
            stdscr.hline(1, 0, curses.ACS_HLINE, w - 1)
            stdscr.attroff(p["RED"])
        except Exception:
            pass

    def build_rows(m: dict) -> list[dict]:
        rows = []
        for key, kind, lo, hi, step in TUNABLE:
            rows.append(
                {
                    "kind": "tune",
                    "key": key,
                    "k": kind,
                    "lo": lo,
                    "hi": hi,
                    "step": step,
                    "label": LABELS.get(key, key),
                }
            )
        for stem in _template_stems(m):
            rows.append({"kind": "action", "stem": stem})
        rows.append({"kind": "record", "label": "Record new gesture (webcam)"})
        rows.append({"kind": "test", "label": "Test distance overlay (webcam)"})
        return rows

    settings = load_settings()
    m = _motion_block(settings)
    rows = build_rows(m)
    cursor = 0
    scroll = 0
    changed = False
    editing = False
    edit_buf = ""
    edit_stem = ""

    while True:
        h, w = stdscr.getmaxyx()
        body_h = h - 4
        stdscr.erase()
        draw_header()

        if cursor < scroll:
            scroll = cursor
        if cursor >= scroll + body_h:
            scroll = cursor - body_h + 1

        y = 3
        for idx in range(scroll, min(scroll + body_h, len(rows))):
            row = rows[idx]
            is_cur = idx == cursor
            attr = p["RED"] if is_cur else p["NORM"]
            mark = ">" if is_cur else " "
            safe(y, 2, mark, attr)
            if row["kind"] == "tune":
                val = m.get(row["key"])
                line = f"{row['label'][: max(1, w - 24)]}"
                safe(y, 4, line, attr)
                safe(y, min(w - 14, 48), f"{val}", p["PINK"] if is_cur else p["DIM"])
            elif row["kind"] == "action":
                act = m.get("actions", {}).get(row["stem"], "state_runner.py")
                line = f"Gesture «{row['stem']}» → {act}"
                safe(y, 4, line[: w - 6], attr)
            else:
                safe(y, 4, row["label"], attr)
            y += 1

        foot = "[←→] tune   [enter] action / record / test   [r] jump record   [t] overlay test"
        safe(h - 2, 0, foot[: w - 1], p["DIM"])
        if editing:
            prompt = "action path (repo-relative): "
            safe(h - 1, 0, (prompt + edit_buf + "█")[: w - 1], p["PINK"])
        else:
            msg = f"templates: {', '.join(_template_stems(m)) or '(none)'}"
            safe(h - 1, 0, msg[: w - 1], p["DIM"])

        stdscr.refresh()

        if editing:
            key = stdscr.getch()
            if key in (curses.KEY_ENTER, 10, 13):
                path = edit_buf.strip() or "state_runner.py"
                m.setdefault("actions", {})[edit_stem] = path
                save_settings(settings)
                changed = True
                rows = build_rows(m)
                editing = False
                edit_buf = ""
            elif key in (27,):
                editing = False
                edit_buf = ""
            elif key in (curses.KEY_BACKSPACE, 127):
                edit_buf = edit_buf[:-1]
            elif 32 <= key <= 126:
                edit_buf += chr(key)
            continue

        key = stdscr.getch()
        if key == curses.KEY_UP:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_DOWN:
            cursor = min(len(rows) - 1, cursor + 1)
        elif key in (curses.KEY_LEFT,):
            r = rows[cursor]
            if r["kind"] == "tune":
                k, typ, lo, hi, step = r["key"], r["k"], r["lo"], r["hi"], r["step"]
                v = m.get(k)
                if typ == "float":
                    v = max(lo, float(v) - step)
                    m[k] = round(v, 3)
                else:
                    m[k] = max(lo, int(v) - int(step))
                save_settings(settings)
                changed = True
        elif key in (curses.KEY_RIGHT,):
            r = rows[cursor]
            if r["kind"] == "tune":
                k, typ, lo, hi, step = r["key"], r["k"], r["lo"], r["hi"], r["step"]
                v = m.get(k)
                if typ == "float":
                    v = min(hi, float(v) + step)
                    m[k] = round(v, 3)
                else:
                    m[k] = min(hi, int(v) + int(step))
                save_settings(settings)
                changed = True
        elif key in (curses.KEY_ENTER, 10, 13):
            r = rows[cursor]
            if r["kind"] == "action":
                editing = True
                edit_stem = r["stem"]
                edit_buf = str(m.get("actions", {}).get(r["stem"], "state_runner.py"))
            elif r["kind"] == "record":
                name = _prompt_gesture_name(stdscr, draw_header, safe, p)
                if name:
                    _suspend_and_run_script(
                        [str(ROOT / "listeners" / "motion_detector.py"), "record", name]
                    )
                    settings = load_settings()
                    m = _motion_block(settings)
                    rows = build_rows(m)
                    changed = True
            elif r["kind"] == "test":
                _suspend_and_run_script(
                    [str(ROOT / "listeners" / "motion_detector.py"), "test"]
                )
                settings = load_settings()
                m = _motion_block(settings)
                rows = build_rows(m)
        elif key == ord("r"):
            for i, row in enumerate(rows):
                if row["kind"] == "record":
                    cursor = i
                    break
            name = _prompt_gesture_name(stdscr, draw_header, safe, p)
            if name:
                _suspend_and_run_script(
                    [str(ROOT / "listeners" / "motion_detector.py"), "record", name]
                )
                settings = load_settings()
                m = _motion_block(settings)
                rows = build_rows(m)
                changed = True
        elif key == ord("t"):
            _suspend_and_run_script(
                [str(ROOT / "listeners" / "motion_detector.py"), "test"]
            )
            settings = load_settings()
            m = _motion_block(settings)
            rows = build_rows(m)
        elif key in (27, ord("q")):
            break

    return changed
