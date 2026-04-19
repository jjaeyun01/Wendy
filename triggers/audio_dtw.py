"""
Wendy — audio DTW trigger (MFCC feature extraction).

Extracts 13 MFCC coefficients per audio block (pure numpy, no librosa).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import numpy as np

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from triggers.dtw import DTWTrigger, load_templates

SR      = 44100
N_MFCC  = 13
N_FFT   = 512


def _dct2_matrix(n: int) -> np.ndarray:
    """Pre-compute DCT-II matrix of shape (n, n)."""
    k = np.arange(n)
    M = np.cos(np.pi / n * np.outer(k + 0.5, k))
    M[:, 0] *= 0.5
    return (2.0 / n * M).astype(np.float32)


_DCT_MATRIX = _dct2_matrix(N_FFT // 2 + 1)


def extract_mfcc(block: np.ndarray, n_mfcc: int = N_MFCC) -> np.ndarray:
    """
    block: (N,) float32  →  mfcc: (n_mfcc,) float32
    """
    audio  = block.flatten().astype(np.float32)
    n      = len(audio)
    frame  = audio[:N_FFT] if n >= N_FFT else np.pad(audio, (0, N_FFT - n))
    window = np.hanning(N_FFT).astype(np.float32)
    power  = np.abs(np.fft.rfft(frame * window)) ** 2   # (N_FFT//2+1,)

    # Mel filterbank (simplified: 26 triangular filters)
    mel_fb = _mel_fb_fast(SR, N_FFT, 26)
    mel    = np.dot(mel_fb, power)
    log_mel = np.log1p(mel)

    # DCT-II via matrix multiply → pick first n_mfcc
    dct_mat = _DCT_MATRIX[:, :26] if _DCT_MATRIX.shape[1] >= 26 else _DCT_MATRIX
    mfcc    = np.dot(dct_mat[:26, :26], log_mel)[:n_mfcc]
    return mfcc.astype(np.float32)


def _mel_fb_fast(sr: int, n_fft: int, n_filters: int) -> np.ndarray:
    """Quick triangular mel filterbank (26 filters)."""
    def hz2mel(h): return 2595.0 * np.log10(1.0 + h / 700.0)
    def mel2hz(m): return 700.0 * (10.0 ** (m / 2595.0) - 1.0)
    pts  = mel2hz(np.linspace(hz2mel(80), hz2mel(sr / 2), n_filters + 2))
    bins = np.floor((n_fft + 1) * pts / sr).astype(int)
    fb   = np.zeros((n_filters, n_fft // 2 + 1), dtype=np.float32)
    for m in range(1, n_filters + 1):
        lo, mid, hi = bins[m-1], bins[m], bins[m+1]
        if mid > lo:
            fb[m-1, lo:mid] = np.linspace(0, 1, mid-lo, endpoint=False)
        if hi > mid:
            fb[m-1, mid:hi] = np.linspace(1, 0, hi-mid, endpoint=False)
    return fb


class AudioDTWTrigger(DTWTrigger):
    """
    DTWTrigger that extracts MFCC features from raw audio blocks.

    Each detect(audio_block) call appends one MFCC frame to the rolling
    buffer; DTW comparison runs every `stride` calls.
    """

    def __init__(
        self,
        name:      str,
        templates: list[np.ndarray],
        threshold: float,
        action:    Callable[[], None] | None = None,
        cooldown:  float = 1.5,
        seq_len:   int   = 32,
        stride:    int   = 2,
        n_mfcc:    int   = N_MFCC,
    ) -> None:
        super().__init__(name=name, templates=templates, threshold=threshold,
                         action=action, cooldown=cooldown, seq_len=seq_len)
        self._stride  = stride
        self._n_mfcc  = n_mfcc
        self._call_n  = 0

    def extract_features(self, data: np.ndarray) -> np.ndarray | None:
        self._call_n += 1
        if self._call_n % self._stride != 0:
            return None
        return extract_mfcc(data, self._n_mfcc).astype(np.float64)

    # ── factory ──────────────────────────────────────────────────────────────

    @classmethod
    def from_file(                               # type: ignore[override]
        cls,
        name:      str,
        action:    Callable[[], None] | None = None,
        threshold: float | None = None,
        **kwargs,
    ) -> "AudioDTWTrigger":
        templates, meta = load_templates(name)
        thr     = threshold if threshold is not None else float(meta.get("threshold", 100.0))
        seq_len = int(meta.get("seq_len", 32))
        return cls(name=name, templates=templates, threshold=thr,
                   action=action, seq_len=seq_len, **kwargs)
