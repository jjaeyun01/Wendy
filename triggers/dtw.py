"""
Wendy — DTW-based gesture trigger.

Users can record their own audio gestures and map them to any action.

Record a new trigger
--------------------
    python3 triggers/dtw.py record snap

    Follow the prompts: perform your gesture N times.
    Templates are saved to triggers/templates/snap.json.

List saved triggers
-------------------
    python3 triggers/dtw.py list

Test matching live
------------------
    python3 triggers/dtw.py test snap

Use in code
-----------
    from triggers.audio_dtw import AudioDTWTrigger

    trigger = AudioDTWTrigger.from_file("snap", action=my_fn)
    # call trigger.detect(audio_block) in your audio loop
"""

from __future__ import annotations

import json
import sys
import time
import threading
from pathlib import Path
from typing import Callable

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TEMPLATES_DIR  = ROOT / "triggers" / "templates"


# ── Pure-numpy DTW ───────────────────────────────────────────────────────────

def dtw_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    Dynamic Time Warping distance between two (T, D) sequences.
    Both arrays are cast to float64 before comparison.
    """
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    n, m = len(a), len(b)

    cost = np.full((n + 1, m + 1), np.inf)
    cost[0, 0] = 0.0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d = float(np.linalg.norm(a[i - 1] - b[j - 1]))
            cost[i, j] = d + min(cost[i - 1, j],
                                  cost[i, j - 1],
                                  cost[i - 1, j - 1])
    return float(cost[n, m])


def min_dtw(query: np.ndarray, templates: list[np.ndarray]) -> float:
    """Return the minimum DTW distance between query and any template."""
    if not templates:
        return float("inf")
    return min(dtw_distance(query, t) for t in templates)


# ── Template I/O ─────────────────────────────────────────────────────────────

def save_templates(name: str, templates: list[np.ndarray],
                   meta: dict | None = None) -> Path:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    path = TEMPLATES_DIR / f"{name}.json"
    payload = {
        "name":      name,
        "version":   1,
        "n_templates": len(templates),
        "meta":      meta or {},
        "templates": [t.tolist() for t in templates],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_templates(name: str) -> tuple[list[np.ndarray], dict]:
    path = TEMPLATES_DIR / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"No template file for «{name}»: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    templates = [np.array(t, dtype=np.float64) for t in data["templates"]]
    return templates, data.get("meta", {})


# ── DTWTrigger ───────────────────────────────────────────────────────────────

class DTWTrigger:
    """
    Compares a rolling feature sequence to stored templates via DTW.
    Fires (calls `action`) when the minimum template distance drops below
    `threshold` and the cooldown has passed.

    Subclass and override `extract_features(data) → np.ndarray` to adapt
    to different sensor modalities.
    """

    def __init__(
        self,
        name: str,
        templates: list[np.ndarray],
        threshold: float,
        action:    Callable[[], None] | None = None,
        cooldown:  float = 1.5,
        seq_len:   int   = 32,
    ) -> None:
        self.name       = name
        self._templates = templates
        self._threshold = threshold
        self._action    = action
        self._cooldown  = cooldown
        self._seq_len   = seq_len
        self._buffer:  list[np.ndarray] = []
        self._last_fire: float = 0.0

    # ── public interface ─────────────────────────────────────────────────────

    def detect(self, data: np.ndarray) -> bool:
        feat = self.extract_features(data)
        if feat is None:
            return False
        self._buffer.append(feat)
        if len(self._buffer) > self._seq_len:
            self._buffer.pop(0)
        if len(self._buffer) < self._seq_len // 2:
            return False
        if time.time() - self._last_fire < self._cooldown:
            return False

        seq  = np.stack(self._buffer)
        dist = min_dtw(seq, self._templates)
        if dist < self._threshold:
            self._last_fire = time.time()
            return True
        return False

    def on_triggered(self) -> None:
        print(f"  ✦ DTW trigger «{self.name}» fired")
        if self._action:
            self._action()

    def add_template(self, seq: np.ndarray) -> None:
        self._templates.append(np.asarray(seq, dtype=np.float64))

    def extract_features(self, data: np.ndarray) -> np.ndarray | None:
        """Override in subclass to transform raw data into a feature vector."""
        return data.flatten().astype(np.float64)

    # ── persistence ──────────────────────────────────────────────────────────

    def save(self) -> Path:
        path = save_templates(self.name, self._templates,
                               meta={"threshold": self._threshold,
                                     "seq_len":   self._seq_len})
        print(f"  ✓ Saved {len(self._templates)} templates → {path.relative_to(ROOT)}")
        return path

    @classmethod
    def from_file(cls, name: str, action: Callable[[], None] | None = None,
                  threshold: float | None = None) -> "DTWTrigger":
        templates, meta = load_templates(name)
        thr = threshold if threshold is not None else float(meta.get("threshold", 100.0))
        seq_len = int(meta.get("seq_len", 32))
        return cls(name=name, templates=templates, threshold=thr,
                   action=action, seq_len=seq_len)


# ── CLI recording helper ──────────────────────────────────────────────────────

def _record_audio_templates(name: str, n: int = 5, duration: float = 0.8) -> list[np.ndarray]:
    """Record N audio snippets via mic; return list of raw float32 arrays."""
    import sounddevice as sd
    SR = 44100
    samples_per_rec = int(SR * duration)
    templates = []

    print(f"\n  Recording {n} samples for «{name}»  ({duration:.1f}s each)")
    print("  Press ENTER before each gesture, Q to finish early.\n")

    for i in range(n):
        inp = input(f"  [{i+1}/{n}] Press ENTER to record (Q = done): ")
        if inp.strip().lower() == "q":
            break
        print("  ● Recording...", end="", flush=True)
        audio = sd.rec(samples_per_rec, samplerate=SR, channels=1,
                       dtype="float32", blocking=True)
        audio = audio[:, 0]
        templates.append(audio)
        amp = float(np.max(np.abs(audio)))
        print(f"\r  ✓ Captured  (peak amp: {amp:.3f})")

    return templates


def _cmd_record(name: str) -> None:
    from triggers.audio_dtw import AudioDTWTrigger
    raw = _record_audio_templates(name)
    if not raw:
        print("  No samples recorded.")
        return
    trigger = AudioDTWTrigger(name=name, templates=[], threshold=0.0)
    seqs = [trigger.extract_features(r) for r in raw]
    seqs = [s for s in seqs if s is not None]
    trigger._templates = seqs
    # Auto-calibrate threshold: 2× average pairwise distance
    if len(seqs) >= 2:
        dists = [dtw_distance(seqs[i], seqs[j])
                 for i in range(len(seqs)) for j in range(i + 1, len(seqs))]
        trigger._threshold = float(np.mean(dists) * 2.0)
        print(f"  Auto threshold: {trigger._threshold:.1f}  (mean pairwise dist: {np.mean(dists):.1f})")
    trigger.save()
    print(f"  ✓ Trigger «{name}» ready.\n")


def _cmd_list() -> None:
    paths = sorted(TEMPLATES_DIR.glob("*.json"))
    if not paths:
        print("  No saved triggers found.")
        return
    print(f"\n  Saved gesture triggers ({len(paths)}):\n")
    for p in paths:
        try:
            data = json.loads(p.read_text())
            thr  = data.get("meta", {}).get("threshold", "?")
            n    = data.get("n_templates", "?")
            print(f"    {p.stem:20s}  templates={n}  threshold={thr}")
        except Exception:
            print(f"    {p.stem}  (unreadable)")
    print()


def _cmd_test(name: str) -> None:
    from triggers.audio_dtw import AudioDTWTrigger
    import sounddevice as sd

    trigger = AudioDTWTrigger.from_file(name)
    print(f"\n  Testing «{name}» live (Ctrl+C to stop)  threshold={trigger._threshold:.1f}\n")

    def cb(indata, frames, time_info, status):
        if trigger.detect(indata[:, 0]):
            trigger.on_triggered()

    with sd.InputStream(samplerate=44100, channels=1, dtype="float32",
                        blocksize=1024, callback=cb):
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
    print()


def main() -> None:
    cmds = {"record", "list", "test"}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print("Usage:")
        print("  python3 triggers/dtw.py record <name>   — record a new gesture")
        print("  python3 triggers/dtw.py list             — show saved triggers")
        print("  python3 triggers/dtw.py test <name>      — live test a trigger")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "list":
        _cmd_list()
    elif cmd in ("record", "test"):
        if len(sys.argv) < 3:
            print(f"Usage: python3 triggers/dtw.py {cmd} <name>")
            sys.exit(1)
        name = sys.argv[2].strip().lower()
        if cmd == "record":
            _cmd_record(name)
        else:
            _cmd_test(name)


if __name__ == "__main__":
    main()
