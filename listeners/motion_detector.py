#!/usr/bin/env python3
"""
Webcam motion detector (MediaPipe Hands).

  Record a custom gesture:
    python3 listeners/motion_detector.py record <name>   (from repo root)

  Run matching (loads motions/*.json, runs bash script from motion.actions):
    python3 listeners/motion_detector.py run
    python3 listeners/motion_detector.py

  Test overlay (distance vs threshold, no launch):
    python3 listeners/motion_detector.py test

Configure settings.json → "motion" (see MOTION_DEFAULTS) and "motion"."actions".
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Tuple
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

from motion_features import (
    compare_buffer_to_template,
    encode_hands,
    load_template,
    save_template,
)


def _repo_root() -> Path:
    """Directory that has config.json + wendy_daemon.py (works if listeners/ moves)."""
    here = Path(__file__).resolve().parent
    for p in [here, *here.parents]:
        if (p / "config.json").is_file() and (p / "wendy_daemon.py").is_file():
            return p
    return here.parent


LISTENERS_DIR = Path(__file__).resolve().parent
ROOT = _repo_root()
DEFAULT_ACTION = ROOT / "state_runner.py"
SETTINGS_PATH = ROOT / "settings.json"

MOTION_DEFAULTS = {
    "camera_index": 0,
    "templates_dir": "motions",
    "compare_frames": 32,
    "distance_threshold": 0.26,
    "cooldown_sec": 3.0,
    "record_seconds": 2.2,
    "match_stride": 2,
    "buffer_max_frames": 90,
}


def load_motion_runtime() -> Tuple[dict, dict]:
    """Return (numeric motion config, template_stem → script path relative to ROOT)."""
    cfg = dict(MOTION_DEFAULTS)
    actions: dict = {}
    if not SETTINGS_PATH.is_file():
        return cfg, actions
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return cfg, actions
    user = data.get("motion")
    if isinstance(user, dict):
        cfg.update({k: v for k, v in user.items() if k in MOTION_DEFAULTS})
        raw = user.get("actions")
        if isinstance(raw, dict):
            actions = {str(k): str(v) for k, v in raw.items() if v}
    return cfg, actions


def _load_motion_settings() -> dict:
    cfg, _ = load_motion_runtime()
    return cfg


def _is_under_repo(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def _resolve_action_script(stem: str, actions: dict) -> Path:
    rel = actions.get(stem, "state_runner.py")
    if not isinstance(rel, str) or not rel.strip():
        rel = "state_runner.py"
    rel = rel.strip()
    target = (ROOT / rel).resolve()
    if not target.is_file():
        print(f"  ⚠ Unknown action for «{stem}»: {rel!r} — using state_runner.py")
        return DEFAULT_ACTION
    if not _is_under_repo(target):
        print(f"  ⚠ Action path must stay inside the repo — using state_runner.py")
        return DEFAULT_ACTION
    return target


def _launch_action(path: Path) -> None:
    if path.suffix == ".py":
        subprocess.Popen([sys.executable, str(path)], cwd=str(ROOT))
    else:
        subprocess.Popen(["bash", str(path)], cwd=str(ROOT))


def _import_mediapipe_hands():
    try:
        import mediapipe as mp  # type: ignore

        return mp.solutions.hands
    except ImportError as e:
        raise SystemExit(
            "mediapipe is required for motion detection. Install with:\n"
            "  pip install -r requirements.txt\n"
            f"Original error: {e}"
        ) from e


def _sanitize_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise SystemExit("Name must be non-empty.")
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    if safe != name:
        print(f"  (using filename-safe name: {safe})")
    return safe


def _hands_loop(
    hands_module,
    cap,
    on_result,
    show: bool,
    window: str,
    overlay=None,
) -> None:
    import mediapipe as mp  # type: ignore

    mp_hands = hands_module
    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        model_complexity=1,
        min_detection_confidence=0.65,
        min_tracking_confidence=0.5,
    ) as hands:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                print("  ✗ Failed to read from webcam.")
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            result = hands.process(rgb)
            rgb.flags.writeable = True

            if show:
                preview = frame.copy()
                if result.multi_hand_landmarks:
                    for lm in result.multi_hand_landmarks:
                        mp.solutions.drawing_utils.draw_landmarks(
                            preview,
                            lm,
                            mp_hands.HAND_CONNECTIONS,
                        )
                if overlay:
                    overlay(preview)
                cv2.imshow(window, preview)
                key = cv2.waitKey(1) & 0xFF
            else:
                key = -1

            stop = on_result(frame, result, key)
            if stop:
                break


def cmd_record(name: str, cfg: dict) -> None:
    mp_hands_mod = _import_mediapipe_hands()
    name = _sanitize_name(name)
    out = ROOT / cfg["templates_dir"] / f"{name}.json"
    cap = cv2.VideoCapture(int(cfg["camera_index"]))
    if not cap.isOpened():
        raise SystemExit(f"Could not open camera index {cfg['camera_index']}")

    window = "Wendy — record motion (SPACE=start, Q=quit)"
    frames: list = []
    phase = "wait"  # wait | capture
    capture_until = 0.0
    record_seconds = float(cfg["record_seconds"])

    print("\n  Wendy motion recorder")
    print(f"  Output: {out.relative_to(ROOT)}")
    print("  Show your gesture after you press SPACE.")
    print("  Q in the preview window to quit.\n")

    def on_result(frame, result, key):
        nonlocal phase, capture_until, frames

        if key == ord("q") or key == ord("Q"):
            return True

        lm = result.multi_hand_landmarks
        hd = result.multi_handedness
        feat = encode_hands(lm, hd)

        now = time.time()
        if phase == "wait":
            if key == ord(" "):
                phase = "capture"
                capture_until = now + record_seconds
                frames = []
                print(f"  Recording for {record_seconds:.1f}s…")
            return False

        # capture
        frames.append(feat.copy())
        if now >= capture_until:
            return True
        return False

    try:
        _hands_loop(mp_hands_mod, cap, on_result, show=True, window=window, overlay=None)
    finally:
        cap.release()
        cv2.destroyAllWindows()

    # Keep frames where at least one hand was visible (non-zero norm on either half)
    dim_half = 63
    kept = []
    for f in frames:
        l = float(np.linalg.norm(f[:dim_half]))
        r = float(np.linalg.norm(f[dim_half:]))
        if l > 1e-3 or r > 1e-3:
            kept.append(f)

    if len(kept) < 12:
        raise SystemExit(
            "Too few frames with visible hands. Try again with better light "
            "and keep your hands in frame for the full recording."
        )

    save_template(out, name, kept, meta={"record_seconds": record_seconds})
    print(f"  ✓ Saved {len(kept)} frames → {out.relative_to(ROOT)}\n")


def cmd_run(cfg: dict, actions: dict) -> None:
    mp_hands_mod = _import_mediapipe_hands()
    motions_dir = ROOT / cfg["templates_dir"]
    paths = sorted(motions_dir.glob("*.json"))
    if not paths:
        raise SystemExit(
            f"No templates in {motions_dir.relative_to(ROOT)}/\n"
            "Record one with:\n"
            f"  python3 listeners/motion_detector.py record <name>\n"
        )

    templates = []
    for p in paths:
        try:
            templates.append(load_template(p))
        except (json.JSONDecodeError, KeyError, OSError) as e:
            print(f"  ⚠ Skipping {p.name}: {e}")

    if not templates:
        raise SystemExit("No valid motion templates to load.")

    cap = cv2.VideoCapture(int(cfg["camera_index"]))
    if not cap.isOpened():
        raise SystemExit(f"Could not open camera index {cfg['camera_index']}")

    compare_len = int(cfg["compare_frames"])
    threshold = float(cfg["distance_threshold"])
    cooldown = float(cfg["cooldown_sec"])
    stride = max(1, int(cfg["match_stride"]))
    buf_max = max(40, int(cfg["buffer_max_frames"]))

    buffer: deque = deque(maxlen=buf_max)
    last_fire = 0.0
    frame_i = 0
    window = "Wendy — motion (Q=quit)"

    print("\n  Wendy motion detector running.")
    print(f"  Templates: {[t['name'] for t in templates]}")
    print(f"  distance ≤ {threshold} → run mapped script  |  cooldown {cooldown}s\n")

    def on_result(frame, result, key):
        nonlocal last_fire, frame_i

        if key == ord("q") or key == ord("Q"):
            return True

        lm = result.multi_hand_landmarks
        hd = result.multi_handedness
        feat = encode_hands(lm, hd)
        buffer.append(feat.astype(np.float64))
        frame_i += 1

        now = time.time()
        if now - last_fire < cooldown:
            return False
        if frame_i % stride != 0:
            return False

        best = None
        best_stem = None
        for t in templates:
            vecs = t["_vectors"]
            d = compare_buffer_to_template(buffer, vecs, compare_len)
            if best is None or d < best[0]:
                best = d
                best_stem = t.get("_stem") or t.get("name") or "unknown"

        if best is not None and best <= threshold:
            script = _resolve_action_script(str(best_stem), actions)
            print(f"  ✦ Match «{best_stem}» (d={best:.3f}) → {script.relative_to(ROOT)}\n")
            last_fire = now
            _launch_action(script)

        return False

    try:
        _hands_loop(mp_hands_mod, cap, on_result, show=True, window=window, overlay=None)
    finally:
        cap.release()
        cv2.destroyAllWindows()


def cmd_test(cfg: dict, actions: dict) -> None:
    mp_hands_mod = _import_mediapipe_hands()
    motions_dir = ROOT / cfg["templates_dir"]
    paths = sorted(motions_dir.glob("*.json"))
    if not paths:
        raise SystemExit(
            f"No templates in {motions_dir.relative_to(ROOT)}/ — record one first.\n"
        )
    templates = []
    for p in paths:
        try:
            templates.append(load_template(p))
        except (json.JSONDecodeError, KeyError, OSError) as e:
            print(f"  ⚠ Skipping {p.name}: {e}")
    if not templates:
        raise SystemExit("No valid motion templates.")

    cap = cv2.VideoCapture(int(cfg["camera_index"]))
    if not cap.isOpened():
        raise SystemExit(f"Could not open camera index {cfg['camera_index']}")

    compare_len = int(cfg["compare_frames"])
    threshold = float(cfg["distance_threshold"])
    stride = max(1, int(cfg["match_stride"]))
    buf_max = max(40, int(cfg["buffer_max_frames"]))
    buffer: deque = deque(maxlen=buf_max)
    frame_i = 0
    window = "Wendy — motion TEST (Q=quit)"
    state = {"d": float("inf"), "stem": "", "thr": threshold, "script": ""}

    def overlay(preview):
        d = state["d"]
        st = state["stem"] or "—"
        thr = state["thr"]
        if d == float("inf"):
            line = "Move hands… (no template match yet)"
            color = (180, 180, 180)
        else:
            line = f"{st}  d={d:.3f}  thr={thr:.3f}"
            color = (80, 220, 120) if d <= thr else (200, 200, 200)
        cv2.putText(
            preview,
            line,
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )
        if state.get("script"):
            cv2.putText(
                preview,
                f"would run: {state['script']}",
                (12, 52),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (120, 200, 255),
                1,
                cv2.LINE_AA,
            )

    def on_result(frame, result, key):
        nonlocal frame_i

        if key == ord("q") or key == ord("Q"):
            return True

        lm = result.multi_hand_landmarks
        hd = result.multi_handedness
        feat = encode_hands(lm, hd)
        buffer.append(feat.astype(np.float64))
        frame_i += 1
        if frame_i % stride != 0:
            return False

        best = float("inf")
        best_stem = ""
        for t in templates:
            vecs = t["_vectors"]
            d = compare_buffer_to_template(buffer, vecs, compare_len)
            if d < best:
                best = d
                best_stem = str(t.get("_stem") or t.get("name") or "?")

        if best == float("inf"):
            state["d"] = float("inf")
            state["stem"] = ""
            state["script"] = ""
        else:
            state["d"] = best
            state["stem"] = best_stem
            if best <= threshold:
                sp = _resolve_action_script(best_stem, actions)
                state["script"] = str(sp.relative_to(ROOT))
            else:
                state["script"] = ""

        return False

    print("\n  Wendy motion TEST (no launch). Adjust motion.distance_threshold in TUI.\n")

    try:
        _hands_loop(mp_hands_mod, cap, on_result, show=True, window=window, overlay=overlay)
    finally:
        cap.release()
        cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(description="Wendy webcam motion templates")
    sub = parser.add_subparsers(dest="command", required=False)

    p_rec = sub.add_parser("record", help="Record a gesture to motions/<name>.json")
    p_rec.add_argument("name", help="Template name (saved as motions/<name>.json)")

    sub.add_parser("run", help="Run live matching against all templates")
    sub.add_parser("test", help="Webcam overlay: distance vs threshold (does not launch)")

    args = parser.parse_args()
    cfg, actions = load_motion_runtime()

    if args.command == "record":
        cmd_record(args.name, cfg)
    elif args.command == "test":
        cmd_test(cfg, actions)
    elif args.command in (None, "run"):
        cmd_run(cfg, actions)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
