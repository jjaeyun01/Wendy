"""
Pure-numpy Mel spectrogram — no librosa needed at inference time.

SR = 44100, hop_length = 1024 → 32 frames ≈ 742ms rolling window.
Used by ClapCNNClassifier at runtime and by train.py during training.
"""

from __future__ import annotations
import numpy as np

# ── Default parameters (must match between training and inference) ──────────
SR          = 44100
N_FFT       = 1024
HOP_LENGTH  = 1024   # 32 hops × 1024 = 32768 samples ≈ 742ms
N_MELS      = 64
FMIN        = 80.0
FMAX        = 8000.0
N_FRAMES    = 32     # target time frames per spectrogram


def mel_filterbank(
    n_mels: int  = N_MELS,
    n_fft:  int  = N_FFT,
    sr:     int  = SR,
    fmin:   float = FMIN,
    fmax:   float = FMAX,
) -> np.ndarray:
    """Return (n_mels, n_fft//2+1) float32 mel filterbank matrix."""

    def hz_to_mel(hz: float) -> float:
        return 2595.0 * np.log10(1.0 + hz / 700.0)

    def mel_to_hz(mel: float) -> float:
        return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)

    mel_pts = np.linspace(hz_to_mel(fmin), hz_to_mel(fmax), n_mels + 2)
    hz_pts  = np.array([mel_to_hz(m) for m in mel_pts])
    bins    = np.floor((n_fft + 1) * hz_pts / sr).astype(int)
    n_bins  = n_fft // 2 + 1

    fb = np.zeros((n_mels, n_bins), dtype=np.float32)
    for m in range(1, n_mels + 1):
        lo, mid, hi = bins[m - 1], bins[m], bins[m + 1]
        if mid > lo:
            fb[m - 1, lo:mid] = np.linspace(0.0, 1.0, mid - lo, endpoint=False)
        if hi > mid:
            fb[m - 1, mid:hi] = np.linspace(1.0, 0.0, hi - mid, endpoint=False)
    return fb


# Module-level cached filterbank (built once on first use)
_FB: np.ndarray | None = None


def _get_filterbank() -> np.ndarray:
    global _FB
    if _FB is None:
        _FB = mel_filterbank()
    return _FB


def compute_mel(
    audio:      np.ndarray,
    n_frames:   int   = N_FRAMES,
    n_fft:      int   = N_FFT,
    hop_length: int   = HOP_LENGTH,
    sr:         int   = SR,
    n_mels:     int   = N_MELS,
    fmin:       float = FMIN,
    fmax:       float = FMAX,
) -> np.ndarray:
    """
    Convert 1-D float32 audio → mel spectrogram of shape (n_mels, n_frames).

    Audio is zero-padded or trimmed to exactly n_frames * hop_length samples
    before computing the STFT.  Returns log1p-compressed values.
    """
    audio = audio.flatten().astype(np.float32)

    target = hop_length * n_frames
    if len(audio) < target:
        audio = np.pad(audio, (0, target - len(audio)))
    else:
        audio = audio[-target:]   # keep the most recent samples

    window = np.hanning(n_fft).astype(np.float32)
    n_stft = (len(audio) - n_fft) // hop_length + 1

    # Build STFT frames
    frames = np.stack([
        audio[i * hop_length : i * hop_length + n_fft] * window
        for i in range(n_stft)
    ])                                                # (n_stft, n_fft)

    power = np.abs(np.fft.rfft(frames, n=n_fft)) ** 2  # (n_stft, n_fft//2+1)

    fb = _get_filterbank() if (n_mels == N_MELS and n_fft == N_FFT
                                and sr == SR and fmin == FMIN and fmax == FMAX) \
         else mel_filterbank(n_mels, n_fft, sr, fmin, fmax)

    mel = np.dot(fb, power.T)                        # (n_mels, n_stft)
    mel = np.log1p(mel)

    # Resize to exactly n_frames columns
    if mel.shape[1] != n_frames:
        idx = np.linspace(0, mel.shape[1] - 1, n_frames).astype(int)
        mel = mel[:, idx]

    return mel.astype(np.float32)
