"""
Wendy — wake-word listener.

Runs a background thread that streams 16 kHz audio through Vosk.
When the configured word (default "wendy") appears in the transcript,
the detector becomes "armed" for `arm_seconds`.  While armed, the
clap+visual detector will actually fire.

Setup (one-time):
    pip install vosk
    # Download a model zip from https://alphacephei.com/vosk/models and unzip into:
    #   models/vosk/<model-folder>/
    # (Unpacking next to wake_word.py at the repo root still works as a fallback.)
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"

# Prefer models under models/vosk/ so the repo root stays small; root is legacy.
_VOSK_SEARCH_DIRS = (
    ROOT / "models" / "vosk",
    ROOT,
)

_DEFAULT_MODEL_GLOBS = (
    "vosk-model-small-en-us*",
    "vosk-model-en-us*",
    "vosk-model-small-ko*",
    "vosk-model-ko*",
)


def _find_model() -> Path | None:
    for base in _VOSK_SEARCH_DIRS:
        if not base.is_dir():
            continue
        for pattern in _DEFAULT_MODEL_GLOBS:
            for m in sorted(base.glob(pattern)):
                if m.is_dir():
                    return m
    return None


def _load_wake_settings() -> dict:
    defaults: dict = {
        "enabled": True,
        "word": "wendy",
        "aliases": ["when the", "when d", "wendi"],
        "arm_seconds": 10.0,
    }
    if not CONFIG_PATH.is_file():
        return defaults
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return defaults
    w = cfg.get("settings", {}).get("wake_word")
    if not isinstance(w, dict):
        return defaults
    out = dict(defaults)
    if "word" in w:
        out["word"] = str(w["word"]).lower().strip()
    if "aliases" in w and isinstance(w["aliases"], list):
        out["aliases"] = [str(a).lower().strip() for a in w["aliases"] if a]
    for k in ("arm_seconds",):
        if k in w:
            try:
                out[k] = float(w[k])
            except (TypeError, ValueError):
                pass
    if "enabled" in w:
        out["enabled"] = bool(w["enabled"])
    return out


class WakeWordDetector:
    """
    Background thread: listens for the wake word via Vosk (offline STT).
    When heard, arms the system for `arm_seconds`.
    """

    def __init__(self, word: str = "wendy", aliases: list[str] | None = None, arm_seconds: float = 10.0):
        self._word = word.lower().strip()
        self._triggers = {self._word} | {a.lower().strip() for a in (aliases or [])}
        self._arm_seconds = arm_seconds
        self._armed_until: float = 0.0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.available = False  # set True when Vosk + model load OK

    # ── public API ──────────────────────────────────────────────────────────

    def is_armed(self) -> bool:
        with self._lock:
            return time.time() < self._armed_until

    def arm(self) -> None:
        until = time.time() + self._arm_seconds
        with self._lock:
            self._armed_until = until
        print(f"\n  🎤 Wake word «{self._word}» — armed for {self._arm_seconds:.0f}s. Clap now!\n")

    def disarm(self) -> None:
        with self._lock:
            self._armed_until = 0.0
        print("  🔒 Wendy disarmed — say 'Wendy' again to re-arm.\n")

    def stop(self) -> None:
        self._stop.set()

    def start(self) -> bool:
        """Start background thread. Returns True if Vosk + model are available."""
        ready = threading.Event()
        t = threading.Thread(
            target=self._run, args=(ready,), daemon=True, name="wendy-wake"
        )
        t.start()
        ready.wait(timeout=8.0)
        return self.available

    # ── internals ───────────────────────────────────────────────────────────

    def _run(self, ready: threading.Event) -> None:
        try:
            import numpy as np
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model, SetLogLevel  # type: ignore
        except ImportError as exc:
            print(f"  ⚠  Wake word disabled — missing dependency: {exc}")
            print("     pip install vosk")
            ready.set()
            return

        model_path = _find_model()
        if model_path is None:
            print("  ⚠  Wake word disabled — Vosk model not found.")
            print("     Download a model from https://alphacephei.com/vosk/models/")
            print(f"     and unzip into: {ROOT / 'models' / 'vosk'}/  (or repo root as fallback)")
            ready.set()
            return

        SetLogLevel(-1)  # suppress Vosk verbose output
        try:
            model = Model(str(model_path))
            rec = KaldiRecognizer(model, 16000)
        except Exception as exc:
            print(f"  ⚠  Wake word disabled — Vosk model load failed: {exc}")
            ready.set()
            return

        self.available = True
        ready.set()
        print(f"  🎤 Say «{self._word.capitalize()}» to arm clap detection  (model: {model_path.name})")

        def on_audio(indata: np.ndarray, frames: int, time_info, status) -> None:
            if self._stop.is_set():
                return
            pcm = (indata[:, 0] * 32767).astype(np.int16).tobytes()
            if rec.AcceptWaveform(pcm):
                result = json.loads(rec.Result())
                text = result.get("text", "").lower()
            else:
                partial = json.loads(rec.PartialResult())
                text = partial.get("partial", "").lower()

            if text.strip() and any(t in text for t in self._triggers):
                self.arm()

        with sd.InputStream(
            samplerate=16000,
            blocksize=4000,
            channels=1,
            dtype="float32",
            callback=on_audio,
        ):
            while not self._stop.is_set():
                time.sleep(0.05)


def build_from_config() -> WakeWordDetector | None:
    """Return a configured WakeWordDetector, or None if disabled."""
    s = _load_wake_settings()
    if not s["enabled"]:
        return None
    return WakeWordDetector(word=s["word"], aliases=s.get("aliases", []), arm_seconds=s["arm_seconds"])


def _run_diagnostics() -> None:
    """Standalone diagnostic: check vosk install, model, mic, and live transcription."""
    print("\n  Wendy — wake word diagnostics\n")

    # 1. vosk
    try:
        from vosk import KaldiRecognizer, Model, SetLogLevel  # type: ignore
        import vosk  # type: ignore
        print(f"  ✓ vosk installed  (version: {getattr(vosk, '__version__', '?')})")
    except ImportError:
        print("  ✗ vosk not installed\n    → pip install vosk\n")
        return

    # 2. model
    model_path = _find_model()
    if model_path is None:
        print("  ✗ model not found under", ROOT / "models" / "vosk", "or", ROOT)
        print("    → download from https://alphacephei.com/vosk/models/")
        print("    → unzip into:", ROOT / "models" / "vosk")
        return
    print(f"  ✓ model found: {model_path.name}")

    # 3. sounddevice
    try:
        import sounddevice as sd
        import numpy as np
        dev = sd.query_devices(kind="input")
        print(f"  ✓ microphone: {dev['name']}")
    except Exception as exc:
        print(f"  ✗ microphone error: {exc}")
        return

    # 4. live test
    SetLogLevel(-1)
    model = Model(str(model_path))
    rec = KaldiRecognizer(model, 16000)
    print("\n  Live test — speak now (say 'Wendy', Ctrl+C to stop):\n")

    def on_audio(indata, frames, time_info, status):
        pcm = (indata[:, 0] * 32767).astype(np.int16).tobytes()
        if rec.AcceptWaveform(pcm):
            result = json.loads(rec.Result())
            text = result.get("text", "").strip()
            if text:
                s = _load_wake_settings()
                triggers = {s["word"]} | set(s.get("aliases", []))
                marker = "  ← ✦ WAKE WORD!" if any(t in text.lower() for t in triggers) else ""
                print(f"  heard: \"{text}\"{marker}")
        else:
            partial = json.loads(rec.PartialResult()).get("partial", "").strip()
            if partial:
                print(f"  ...   {partial}", end="\r")

    with sd.InputStream(samplerate=16000, blocksize=4000, channels=1,
                        dtype="float32", callback=on_audio):
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\n  Diagnostics done.")


if __name__ == "__main__":
    _run_diagnostics()
