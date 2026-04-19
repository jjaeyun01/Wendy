"""
Hand motion features for template recording and matching (MediaPipe hands).
Each frame → fixed-length vector: Left hand (21×3) + Right hand (21×3), wrist-normalized.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Sequence

import numpy as np


def _normalize_hand(pts: np.ndarray) -> np.ndarray:
    """pts: (21, 3) in MediaPipe normalized image coords."""
    wrist = pts[0].astype(np.float64)
    mid = pts[9].astype(np.float64)
    scale = float(np.linalg.norm(mid[:2] - wrist[:2]) + 1e-5)
    out = (pts.astype(np.float64) - wrist) / scale
    return out.reshape(-1)


def encode_hands(
    multi_hand_landmarks,
    multi_handedness,
) -> np.ndarray:
    """
    Build 126-dim vector: Left (63) + Right (63), zeros if hand missing.
    """
    left = np.zeros(63, dtype=np.float64)
    right = np.zeros(63, dtype=np.float64)

    if not multi_hand_landmarks:
        return np.concatenate([left, right])
    if not multi_handedness or len(multi_handedness) != len(multi_hand_landmarks):
        return np.concatenate([left, right])

    for idx, hand_landmarks in enumerate(multi_hand_landmarks):
        label = multi_handedness[idx].classification[0].label
        pts = np.array(
            [[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark],
            dtype=np.float64,
        )
        flat = _normalize_hand(pts)
        if label == "Left":
            left = flat
        else:
            right = flat

    return np.concatenate([left, right])


def resample_sequence(frames: Sequence[np.ndarray], target_len: int) -> np.ndarray:
    """Variable-length list of same-dim vectors → (target_len, dim) via linear interpolation."""
    if not frames:
        raise ValueError("empty frames")
    dim = int(frames[0].shape[0])
    arr = np.stack([np.asarray(f, dtype=np.float64) for f in frames], axis=0)
    t = arr.shape[0]
    if t == target_len:
        return arr
    old_x = np.linspace(0.0, 1.0, t)
    new_x = np.linspace(0.0, 1.0, target_len)
    out = np.zeros((target_len, dim), dtype=np.float64)
    for d in range(dim):
        out[:, d] = np.interp(new_x, old_x, arr[:, d])
    return out


def sequence_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Mean L2 norm per time step; a, b same shape (T, dim)."""
    return float(np.mean(np.linalg.norm(a - b, axis=1)))


def compare_buffer_to_template(
    buffer: Sequence[np.ndarray],
    template_frames: Sequence[np.ndarray],
    compare_len: int,
) -> float:
    """
    Compare the tail of `buffer` to `template_frames`, both resampled to compare_len.
    """
    if len(buffer) < 8 or len(template_frames) < 4:
        return float("inf")
    sub = list(buffer)[-max(len(template_frames), len(buffer) // 2) :]
    sub = sub[-min(len(sub), max(len(template_frames) * 2, 24)) :]
    a = resample_sequence(sub, compare_len)
    b = resample_sequence(template_frames, compare_len)
    return sequence_distance(a, b)


def load_template(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    frames = [np.asarray(row, dtype=np.float64) for row in data["frames"]]
    data["_path"] = str(path)
    data["_stem"] = path.stem
    data["_vectors"] = frames
    return data


def save_template(path: Path, name: str, frames: List[np.ndarray], meta: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": name,
        "version": 1,
        "dim": int(frames[0].shape[0]) if frames else 126,
        "frames": [f.astype(float).tolist() for f in frames],
        "meta": meta or {},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
