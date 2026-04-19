"""
Wendy — CNN clap classifier.

Model
-----
Input : (batch, 1, 64, 32) mel spectrogram
Output: (batch,) logit  →  sigmoid → P(clap)

Real-time wrapper
-----------------
    clf = ClapCNNClassifier.load()   # returns None if no model found
    if clf:
        clf.push(audio_block)        # 1024-sample chunk
        if clf.is_clap():
            ...

Training
--------
See ml/train.py
"""

from __future__ import annotations

import sys
import time
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MODELS_DIR = ROOT / "ml" / "models"


# ── Model architecture ───────────────────────────────────────────────────────

def _build_model():
    import torch.nn as nn
    return nn.Sequential(
        # Block 1
        nn.Conv2d(1, 16, kernel_size=3, padding=1),
        nn.BatchNorm2d(16),
        nn.ReLU(),
        nn.MaxPool2d(2),                # → (16, 32, 16)
        # Block 2
        nn.Conv2d(16, 32, kernel_size=3, padding=1),
        nn.BatchNorm2d(32),
        nn.ReLU(),
        nn.MaxPool2d(2),                # → (32, 16, 8)
        # Block 3
        nn.Conv2d(32, 64, kernel_size=3, padding=1),
        nn.BatchNorm2d(64),
        nn.ReLU(),
        nn.AdaptiveAvgPool2d((4, 4)),   # → (64, 4, 4) = 1024 features
        # Classifier
        nn.Flatten(),
        nn.Linear(1024, 128),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(128, 1),
    )


# ── Real-time inference wrapper ──────────────────────────────────────────────

class ClapCNNClassifier:
    """
    Rolling-buffer mel spectrogram classifier for real-time audio.

    One instance lives for the duration of the daemon.  Call push() in the
    audio callback (same thread), then call is_clap() immediately after.
    The deque is GIL-safe for single-producer / single-consumer use.
    """

    N_FRAMES    = 32
    HOP_LENGTH  = 1024
    BUFFER_SIZE = N_FRAMES * HOP_LENGTH    # 32768 samples ≈ 742ms

    def __init__(self, model, threshold: float = 0.72) -> None:
        self._model    = model
        self._threshold = threshold
        self._buf: deque[np.ndarray] = deque(maxlen=self.N_FRAMES)
        self._stride    = 0
        self._last_fire = 0.0

    # ── factory ─────────────────────────────────────────────────────────────

    @classmethod
    def load(cls, threshold: float = 0.72) -> "ClapCNNClassifier | None":
        """Load the most recent model from ml/models/.  Returns None if absent."""
        try:
            import torch
        except ImportError:
            return None

        candidates = sorted(MODELS_DIR.glob("clap_cnn_*.pt"), reverse=True)
        if not candidates:
            return None

        path = candidates[0]
        try:
            model = _build_model()
            model.load_state_dict(
                __import__("torch").load(path, map_location="cpu", weights_only=True)
            )
            model.eval()
            print(f"  ✓ Clap CNN loaded: {path.name}")
            return cls(model, threshold)
        except Exception as exc:
            print(f"  ⚠  Clap CNN load failed ({path.name}): {exc}")
            return None

    # ── real-time API ────────────────────────────────────────────────────────

    MIN_AMP     = 0.04   # skip CNN entirely when signal is near-silent
    FIRE_COOLDOWN = 0.6  # seconds before the same clap can fire again

    def push(self, block: np.ndarray) -> None:
        """Append one audio block to the rolling buffer."""
        self._buf.append(block.flatten().astype(np.float32))
        self._stride += 1

    def is_clap(self) -> bool:
        """
        Returns True once per physical clap event.
        - Skips when amplitude is near-zero (rolling buffer tail suppression)
        - Applies post-fire cooldown so one clap = one True
        """
        if self._stride % 4 != 0:
            return False   # never carry over stale True between calls

        if len(self._buf) < self.N_FRAMES:
            return False

        # Gate 1: must have a real signal in the most recent blocks
        recent = np.concatenate(list(self._buf)[-4:])
        if float(np.max(np.abs(recent))) < self.MIN_AMP:
            return False

        # Gate 2: cooldown after last fire
        if time.time() - self._last_fire < self.FIRE_COOLDOWN:
            return False

        try:
            import torch
            from ml.mel import compute_mel

            audio = np.concatenate(list(self._buf))
            mel   = compute_mel(audio)
            x     = torch.from_numpy(mel[None, None])
            with torch.no_grad():
                prob = torch.sigmoid(self._model(x).squeeze()).item()

            if prob >= self._threshold:
                self._last_fire = time.time()
                return True
        except Exception:
            pass

        return False
