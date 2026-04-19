"""
Wendy — audio sample collector for CNN training.

Usage
-----
    # Record clap samples (positive class)
    python3 ml/collect.py clap

    # Record noise samples (negative class)
    python3 ml/collect.py noise

Controls
--------
    SPACE   → record one sample (~750ms burst)
    Q       → quit

Samples are saved as .npy float32 arrays in:
    ml/data/<label>/sample_NNNN.npy
"""

from __future__ import annotations

import sys
import time
import threading
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
import sounddevice as sd

ROOT     = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "ml" / "data"

SR          = 44100
N_FRAMES    = 32
HOP_LENGTH  = 1024
SAMPLE_LEN  = N_FRAMES * HOP_LENGTH   # 32768 samples ≈ 742ms


def _next_path(out_dir: Path) -> Path:
    existing = sorted(out_dir.glob("sample_*.npy"))
    n = len(existing)
    return out_dir / f"sample_{n:04d}.npy"


def collect(label: str) -> None:
    out_dir = DATA_DIR / label
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  Wendy — collecting «{label}» samples")
    print(f"  Output: {out_dir.relative_to(ROOT)}/")
    print("  SPACE = record one sample  |  Q = quit\n")

    recording   = False
    buf: list   = []
    lock        = threading.Lock()
    done_event  = threading.Event()
    saved_count = len(list(out_dir.glob("sample_*.npy")))

    def on_audio(indata, frames, time_info, status):
        nonlocal recording, buf
        with lock:
            if recording:
                buf.append(indata[:, 0].copy())

    stream = sd.InputStream(samplerate=SR, channels=1, dtype="float32",
                             blocksize=1024, callback=on_audio)
    stream.start()

    try:
        while not done_event.is_set():
            try:
                ch = _getch()
            except KeyboardInterrupt:
                break

            if ch in (" ", "\r", "\n"):
                with lock:
                    recording = True
                    buf = []
                print(f"  ● Recording...", end="", flush=True)
                time.sleep(SAMPLE_LEN / SR + 0.05)
                with lock:
                    recording = False
                    captured = np.concatenate(buf) if buf else np.zeros(SAMPLE_LEN)

                # Trim / pad to exact length
                if len(captured) > SAMPLE_LEN:
                    captured = captured[:SAMPLE_LEN]
                else:
                    captured = np.pad(captured, (0, SAMPLE_LEN - len(captured)))

                path = _next_path(out_dir)
                np.save(path, captured.astype(np.float32))
                saved_count += 1
                print(f"\r  ✓ Saved {path.name}  (total: {saved_count})")

            elif ch.lower() == "q":
                break
    finally:
        stream.stop()
        stream.close()

    print(f"\n  Done. {saved_count} samples in {out_dir.relative_to(ROOT)}/\n")


def _getch() -> str:
    """Read a single keypress without Enter (Unix/macOS)."""
    import tty
    import termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("clap", "noise"):
        print("Usage: python3 ml/collect.py <clap|noise>")
        print()
        print("  clap  — record positive samples (박수 소리)")
        print("  noise — record negative samples (목소리, 타이핑, 주변 소음)")
        sys.exit(1)
    collect(sys.argv[1])


if __name__ == "__main__":
    main()
