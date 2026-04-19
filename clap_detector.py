"""
Wendy — clap listener (runs inside wendy_daemon or standalone).

When visual_clap_require=true (default), BOTH a mic double-clap AND a visual
hand-clap (two hands coming together on camera) must occur within
visual_clap_window_sec to fire the trigger. This eliminates false positives
from music, ambient noise, or app sounds.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

# ── Optional CNN classifier (loads lazily on first audio block) ──────────────
_cnn: "object | None | bool" = None  # None=not tried, False=unavailable, obj=ready

def _get_cnn():
    global _cnn
    if _cnn is not None:
        return _cnn if _cnn is not False else None
    try:
        from ml.clap_cnn import ClapCNNClassifier
        clf = ClapCNNClassifier.load()
        _cnn = clf if clf is not None else False
        if clf is not None:
            print("  ✓ Clap CNN loaded (spectral gate active)")
    except Exception:
        _cnn = False
    return _cnn if _cnn is not False else None

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
STATE_RUNNER = ROOT / "state_runner.py"


def _load_settings() -> dict:
    defaults = {
        "clap_threshold": 0.25,
        "clap_interval_ms": 1200,
        "cooldown_ms": 3000,
        "post_trigger_guard_sec": 22.0,
        "double_clap_min_gap_sec": 0.22,
        "visual_clap_require": True,
        "visual_clap_window_sec": 1.5,
        "visual_clap_distance": 0.15,
        "camera_index": 0,
    }
    if not CONFIG_PATH.is_file():
        return defaults
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return defaults
    s = cfg.get("settings")
    if not isinstance(s, dict):
        return defaults
    out = dict(defaults)
    for k in (
        "clap_threshold", "clap_interval_ms", "cooldown_ms",
        "post_trigger_guard_sec", "double_clap_min_gap_sec",
        "visual_clap_window_sec", "visual_clap_distance", "camera_index",
    ):
        if k in s:
            try:
                out[k] = float(s[k])
            except (TypeError, ValueError):
                pass
    if "visual_clap_require" in s:
        out["visual_clap_require"] = bool(s["visual_clap_require"])
    return out


class VisualClapDetector:
    """
    Background thread: watches the webcam for a clapping motion.
    Clap = two hands visible, wrist distance drops from far (>far_thr) to
    close (<near_thr). Uses hysteresis so a sustained close position does
    not keep firing.
    """

    def __init__(self, camera_index: int = 0, near_threshold: float = 0.15, debug: bool = False):
        self._cam_idx = int(camera_index)
        self._near = float(near_threshold)
        self._far = self._near * 1.4  # hands-apart threshold (was 2.2, too high)
        self._debug = debug
        self._last_event: float = 0.0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._ready = threading.Event()  # signals camera init result
        self.available = False

    def start(self) -> bool:
        t = threading.Thread(target=self._run, daemon=True, name="wendy-visual")
        t.start()
        self._ready.wait(timeout=6.0)  # wait for camera to open (or fail)
        return self.available

    def stop(self) -> None:
        self._stop.set()

    def last_event_time(self) -> float:
        with self._lock:
            return self._last_event

    def _run(self) -> None:
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            print(f"  ⚠  Visual clap disabled — cv2 not available: {exc}")
            self._ready.set()
            return

        cap = cv2.VideoCapture(self._cam_idx)
        if not cap.isOpened():
            print(f"  ⚠  Visual clap disabled — camera {self._cam_idx} not available")
            self._ready.set()
            return

        self.available = True
        self._ready.set()  # unblock start()

        prev_gray = None
        was_far = False
        last_visual_clap = 0.0
        visual_cooldown = 0.8  # seconds between visual clap events
        kernel = np.ones((5, 5), np.uint8)
        warmup = 8  # skip first N frames while prev_gray stabilises
        debug_tick = 0

        while not self._stop.is_set():
            ok, frame = cap.read()
            if not ok or frame is None:
                time.sleep(0.03)
                continue

            fh, fw = frame.shape[:2]
            # Use central 80% vertically — excludes ceiling and table surface
            roi = frame[int(fh * 0.10): int(fh * 0.90), :]
            rh, rw = roi.shape[:2]

            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (15, 15), 0)

            if prev_gray is None or prev_gray.shape != gray.shape:
                prev_gray = gray
                continue

            if warmup > 0:
                warmup -= 1
                prev_gray = gray
                continue

            # Frame differencing: finds moving regions regardless of skin colour
            diff = cv2.absdiff(prev_gray, gray)
            prev_gray = gray.copy()

            _, thresh = cv2.threshold(diff, 18, 255, cv2.THRESH_BINARY)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            thresh = cv2.dilate(thresh, kernel, iterations=1)

            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            min_area = rw * rh * 0.003
            blobs = sorted(
                [c for c in contours if cv2.contourArea(c) > min_area],
                key=cv2.contourArea,
                reverse=True,
            )

            def cx(c):
                M = cv2.moments(c)
                return (M["m10"] / M["m00"] / rw) if M["m00"] else 0.5

            def cy(c):
                M = cv2.moments(c)
                return (M["m01"] / M["m00"] / rh) if M["m00"] else 0.5

            # Require one motion blob in the LEFT half and one in the RIGHT half
            # (left hand / right hand approaching each other)
            left  = next((c for c in blobs if cx(c) < 0.5), None)
            right = next((c for c in blobs if cx(c) >= 0.5), None)

            debug_tick += 1
            if self._debug and debug_tick % 15 == 0:
                if left is None and right is None:
                    print(f"  [cam] no blobs  total={len(blobs)}")
                elif left is None:
                    print(f"  [cam] only RIGHT blob  total={len(blobs)}")
                elif right is None:
                    print(f"  [cam] only LEFT blob   total={len(blobs)}")
                else:
                    lx_, rx_ = cx(left), cx(right)
                    d_ = abs(lx_ - rx_)
                    print(f"  [cam] L={lx_:.2f} R={rx_:.2f} dist={d_:.2f}  far>{self._far:.2f} near<{self._near:.2f}  was_far={was_far}")

            if left is None or right is None:
                was_far = False
                continue

            lx, ly = cx(left),  cy(left)
            rx, ry = cx(right), cy(right)
            dist = ((lx - rx) ** 2 + (ly - ry) ** 2) ** 0.5

            if dist > self._far:
                was_far = True

            if was_far and dist < self._near:
                now_v = time.time()
                if now_v - last_visual_clap >= visual_cooldown:
                    with self._lock:
                        self._last_event = now_v
                    last_visual_clap = now_v
                    print(f"  👁  Visual clap (dist {dist:.2f})")
                was_far = False

        cap.release()


def _is_clap_spectrum(block: np.ndarray, sample_rate: int) -> bool:
    """
    FFT spectral gate: claps have broadband energy (significant content above 3 kHz).
    Voice concentrates below 3 kHz, so this rejects speech without needing a higher
    amplitude threshold.
    """
    flat = block.flatten().astype(np.float32)
    fft_mag = np.abs(np.fft.rfft(flat))
    freqs   = np.fft.rfftfreq(len(flat), d=1.0 / sample_rate)
    total   = float(np.sum(fft_mag ** 2))
    if total == 0:
        return False
    high = float(np.sum(fft_mag[freqs >= 3000] ** 2))
    return (high / total) > 0.18  # claps: ~0.35–0.60, voice: ~0.05–0.15


def run_forever(wake=None) -> None:
    """
    wake: optional WakeWordDetector. When provided, clap detection only fires
    while the detector is armed (i.e. after the wake word was heard).
    """
    s = _load_settings()

    threshold   = float(s["clap_threshold"])
    clap_window = float(s["clap_interval_ms"]) / 1000.0
    cooldown    = float(s["cooldown_ms"]) / 1000.0
    post_guard  = float(s["post_trigger_guard_sec"])
    min_gap     = float(s["double_clap_min_gap_sec"])
    # Stay deaf long enough for state_runner to finish (YouTube settle + app open)
    trigger_guard = max(cooldown, post_guard, 12.0)

    require_visual = bool(s["visual_clap_require"])
    visual_window  = float(s["visual_clap_window_sec"])
    cam_idx        = int(s["camera_index"])
    visual_dist    = float(s["visual_clap_distance"])

    cam_debug = "--cam-debug" in sys.argv

    # Pre-load CNN at startup (not lazily) so it's ready before first wake word
    _get_cnn()

    visual: VisualClapDetector | None = None
    if require_visual:
        visual = VisualClapDetector(camera_index=cam_idx, near_threshold=visual_dist, debug=cam_debug)
        if not visual.start():
            print("  ⚠  Camera unavailable — falling back to audio-only mode")
            visual = None

    sample_rate = 44100
    block_size  = 1024

    last_clap_time = 0.0
    clap_count     = 0
    last_trigger   = 0.0
    env_high       = False
    release_floor  = threshold * 0.30

    def on_audio(indata, frames, time_info, status):
        nonlocal last_clap_time, clap_count, last_trigger, env_high

        now = time.time()
        if now - last_trigger < trigger_guard:
            return

        # Wake-word gate: ignore claps until "Wendy" has been said
        if wake is not None and not wake.is_armed():
            return

        amplitude = float(np.max(np.abs(indata)))

        # Release env_high by amplitude OR by time (whichever comes first)
        if amplitude < release_floor or (env_high and now - last_clap_time > min_gap):
            env_high = False

        if amplitude <= threshold:
            if clap_count == 1 and now - last_clap_time > clap_window:
                print("  ✗ Second clap missed — reset.")
                clap_count = 0
            return

        # Spectral gate: CNN if trained model available, else FFT rule
        clf = _get_cnn()
        if clf is not None:
            clf.push(indata)
            if not clf.is_clap():
                return
        elif not _is_clap_spectrum(indata, sample_rate):
            return

        if env_high:
            return

        # Rising-edge dedup
        if clap_count == 1 and (now - last_clap_time) < min_gap:
            env_high = True
            return
        if clap_count == 0 and last_clap_time > 0 and (now - last_clap_time) < 0.05:
            env_high = True
            return

        env_high = True
        clap_count += 1
        last_clap_time = now
        print(f"  ⬤  Clap {clap_count} (amp {amplitude:.2f})")

        if clap_count < 2:
            return

        # Double clap confirmed — check visual gate
        if visual is not None:
            vt = visual.last_event_time()
            age = now - vt
            if age > visual_window:
                print(f"  ✗ No visual clap within {visual_window}s (last was {age:.1f}s ago) — reset.")
                clap_count = 0
                env_high = True
                return

        print("  ✦ Double clap — applying configured state…\n")
        last_trigger = now
        clap_count   = 0
        env_high     = True
        if wake is not None:
            wake.disarm()
        subprocess.Popen([sys.executable, str(STATE_RUNNER)], cwd=str(ROOT))

    mode = "mic + camera" if (visual and visual.available) else "mic only"
    print(f"\n  Wendy listener ({mode}). Double-clap → config.json state.")
    print(
        f"  threshold={threshold}  window={clap_window}s  "
        f"retrigger_guard={trigger_guard:.1f}s  min_gap={min_gap}s"
    )
    if visual and visual.available:
        print(f"  visual: near<{visual_dist}  window={visual_window}s")
    print("  (Ctrl+C to stop)\n")

    with sd.InputStream(
        samplerate=sample_rate,
        blocksize=block_size,
        channels=1,
        callback=on_audio,
    ):
        while True:
            time.sleep(0.1)


if __name__ == "__main__":
    run_forever()
