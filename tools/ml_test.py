"""
Wendy — CNN clap classifier live test.

Usage
-----
    python3 ml/test.py

소리를 내면서 결과를 확인하세요:
    박수   → ✅ CLAP  (prob: 0.92)
    목소리 → ─        (prob: 0.08)
    타이핑 → ─        (prob: 0.11)

Ctrl+C to stop.
"""

from __future__ import annotations
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import sounddevice as sd
from ml.clap_cnn import ClapCNNClassifier

THRESHOLD   = 0.72   # same as ClapCNNClassifier default
BLOCK_SIZE  = 1024
SR          = 44100


def main() -> None:
    clf = ClapCNNClassifier.load(threshold=THRESHOLD)
    if clf is None:
        print("  ✗ No trained model found in ml/models/")
        print("    Run: python3 ml/train.py")
        sys.exit(1)

    print(f"\n  Wendy — CNN live test  (threshold={THRESHOLD})")
    print("  Make sounds to see classification. Ctrl+C to stop.\n")

    call_n = [0]

    def on_audio(indata, frames, time_info, status):
        block = indata[:, 0]
        amp   = float(np.max(np.abs(block)))
        clf.push(block)
        call_n[0] += 1

        if call_n[0] % 4 != 0:
            return
        if amp < 0.05:   # skip near-silent blocks
            return

        try:
            import torch
            from ml.mel import compute_mel

            # Compute prob for display (bypasses cooldown so we see raw output)
            recent = np.concatenate(list(clf._buf)[-4:])
            if float(np.max(np.abs(recent))) < clf.MIN_AMP:
                return

            audio = np.concatenate(list(clf._buf))
            mel   = compute_mel(audio)
            x     = torch.from_numpy(mel[None, None])
            with torch.no_grad():
                prob = torch.sigmoid(clf._model(x).squeeze()).item()

            bar   = "█" * int(prob * 20)
            label = "✅ CLAP " if prob >= THRESHOLD else "─       "
            print(f"  {label}  |{bar:<20}|  prob={prob:.2f}  amp={amp:.2f}")
        except Exception as e:
            print(f"  error: {e}")

    with sd.InputStream(samplerate=SR, channels=1, dtype="float32",
                        blocksize=BLOCK_SIZE, callback=on_audio):
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n  Done.\n")


if __name__ == "__main__":
    main()
