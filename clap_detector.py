"""
Wendy — clap detector
Listens for 2 claps within 1.2s and triggers wendy.sh
"""

import sounddevice as sd
import numpy as np
import subprocess
import time
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Config ───────────────────────────────
THRESHOLD       = 0.25   # amplitude spike to count as a clap (0.0 - 1.0)
CLAP_WINDOW     = 1.2    # seconds to wait for second clap after first
COOLDOWN        = 3.0    # seconds to ignore after triggering
SAMPLE_RATE     = 44100
BLOCK_SIZE      = 1024

# ── State ────────────────────────────────
last_clap_time  = 0
clap_count      = 0
last_trigger    = 0

def on_audio(indata, frames, time_info, status):
    global last_clap_time, clap_count, last_trigger

    now = time.time()

    # Skip if in cooldown
    if now - last_trigger < COOLDOWN:
        return

    amplitude = np.max(np.abs(indata))

    if amplitude > THRESHOLD:
        # Debounce — ignore if too close to last clap
        if now - last_clap_time < 0.15:
            return

        clap_count += 1
        last_clap_time = now
        print(f"  ⬤  Clap {clap_count} detected (amplitude: {amplitude:.2f})")

        if clap_count == 2:
            print("  ✦ Double clap! Launching Wendy...\n")
            last_trigger = now
            clap_count = 0
            subprocess.Popen(["bash", os.path.join(SCRIPT_DIR, "wendy.sh")])

    # Reset clap count if window expired
    if clap_count == 1 and now - last_clap_time > CLAP_WINDOW:
        print("  ✗ Second clap missed — resetting.")
        clap_count = 0


if __name__ == "__main__":
    print("\n  Wendy clap detector running.")
    print(f"  Threshold: {THRESHOLD}  |  Window: {CLAP_WINDOW}s  |  Cooldown: {COOLDOWN}s")
    print("  Clap twice to launch your workspace.\n")
    print("  (Ctrl+C to stop)\n")

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        channels=1,
        callback=on_audio
    ):
        while True:
            time.sleep(0.1)
