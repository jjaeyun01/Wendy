"""
Wendy — visual clap detector live test.

Usage
-----
    python3 scripts/vision_test.py

카메라 앞에서 박수를 치면:
    👁  Visual clap (dist 0.12)  ← 감지됨
    ─   dist=0.45  was_far=True  ← 손이 벌어진 상태

Ctrl+C to stop.
"""

from __future__ import annotations
import sys
import time
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
from clap_detector import VisualClapDetector


def main() -> None:
    detector = VisualClapDetector(camera_index=0, near_threshold=0.30, debug=False)

    print("\n  Wendy — visual clap test")
    print(f"  near<{detector._near:.2f}  far>{detector._far:.2f}")
    print("  Clap in front of the camera. Ctrl+C to stop.\n")

    if not detector.start():
        print("  ✗ Camera not available")
        sys.exit(1)

    last_event = 0.0
    kernel = np.ones((5, 5), np.uint8)
    cap = cv2.VideoCapture(0)
    prev_gray = None
    warmup = 8
    tick = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.03)
                continue

            fh, fw = frame.shape[:2]
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

            diff = cv2.absdiff(prev_gray, gray)
            prev_gray = gray.copy()
            _, thresh = cv2.threshold(diff, 18, 255, cv2.THRESH_BINARY)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            thresh = cv2.dilate(thresh, kernel, iterations=1)

            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            min_area = rw * rh * 0.003
            blobs = sorted([c for c in contours if cv2.contourArea(c) > min_area],
                           key=cv2.contourArea, reverse=True)

            def cx(c): M = cv2.moments(c); return (M["m10"]/M["m00"]/rw) if M["m00"] else 0.5
            def cy(c): M = cv2.moments(c); return (M["m01"]/M["m00"]/rh) if M["m00"] else 0.5

            left  = next((c for c in blobs if cx(c) < 0.5), None)
            right = next((c for c in blobs if cx(c) >= 0.5), None)

            tick += 1
            if tick % 10 == 0:
                vt = detector.last_event_time()
                if vt != last_event:
                    last_event = vt
                elif left is not None and right is not None:
                    dist = ((cx(left)-cx(right))**2 + (cy(left)-cy(right))**2)**0.5
                    was_far = dist > detector._far
                    print(f"  ─   dist={dist:.2f}  was_far={was_far}  "
                          f"L={cx(left):.2f} R={cx(right):.2f}")

            # Check for new visual clap event
            vt = detector.last_event_time()
            if vt != last_event and vt > 0:
                last_event = vt
                print(f"  👁  Visual clap detected!")

            time.sleep(0.03)

    except KeyboardInterrupt:
        print("\n  Done.\n")
    finally:
        cap.release()
        detector.stop()


if __name__ == "__main__":
    main()
