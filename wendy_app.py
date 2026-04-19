"""
Wendy App — macOS control panel (PyQt6)
Iron Man / JARVIS theme.

Run: python3 wendy_app.py
"""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush
from PyQt6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QScrollArea, QTextEdit,
    QVBoxLayout, QWidget,
)

ROOT       = Path(__file__).resolve().parent
TMPL_DIR   = ROOT / "triggers" / "templates"

# ── Palette ───────────────────────────────────────────────────
BG      = "#0a0e14"
BG_CARD = "#0d1117"
BG_LOG  = "#060a10"
RED     = "#d4453d"
GREEN   = "#34c759"
YELLOW  = "#ffcc00"
TEXT    = "#e8e6e3"
MUTED   = "#4b5563"
BORDER  = "#1c2330"
BORDER_L= "#2d3748"

LOGO = """\
 ██╗    ██╗███████╗███╗   ██╗██████╗ ██╗   ██╗
 ██║    ██║██╔════╝████╗  ██║██╔══██╗╚██╗ ██╔╝
 ██║ █╗ ██║█████╗  ██╔██╗ ██║██║  ██║ ╚████╔╝
 ██║███╗██║██╔══╝  ██║╚██╗██║██║  ██║  ╚██╔╝
 ╚███╔███╔╝███████╗██║ ╚████║██████╔╝   ██║
  ╚══╝╚══╝ ╚══════╝╚═╝  ╚═══╝╚═════╝    ╚═╝"""


# ── Background threads ────────────────────────────────────────────────────────

class Signals(QObject):
    line   = pyqtSignal(str)
    status = pyqtSignal(str)   # "running" | "stopped"


class DaemonThread(QThread):
    def __init__(self, sig: Signals) -> None:
        super().__init__()
        self._sig  = sig
        self._proc = None

    def run(self) -> None:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        self._proc = subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "wendy_daemon.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(ROOT),
            env=env,
        )
        self._sig.status.emit("running")
        for raw in self._proc.stdout:
            line = raw.rstrip()
            if line:
                self._sig.line.emit(line)
        self._proc.wait()
        self._sig.status.emit("stopped")

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()


class MicMonitor(QThread):
    """Reads mic amplitude in real-time for the waveform display."""
    level = pyqtSignal(float)

    def run(self) -> None:
        try:
            import sounddevice as sd
        except ImportError:
            return

        def cb(indata, frames, time_info, status):
            amp = float(np.max(np.abs(indata)))
            self.level.emit(amp)

        try:
            with sd.InputStream(samplerate=44100, channels=1, dtype="float32",
                                blocksize=1024, callback=cb):
                while not self.isInterruptionRequested():
                    self.msleep(20)
        except Exception:
            pass

    def stop_monitor(self) -> None:
        self.requestInterruption()


# ── Custom widgets ────────────────────────────────────────────────────────────

class Dot(QWidget):
    def __init__(self, color: str = GREEN, size: int = 8, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._size  = size
        self.setFixedSize(size + 8, size + 8)

    def set_color(self, c: str) -> None:
        self._color = QColor(c)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        glow = QColor(self._color)
        glow.setAlpha(45)
        p.setBrush(glow)
        p.setPen(Qt.PenStyle.NoPen)
        s = self._size
        p.drawEllipse(1, 1, s + 6, s + 6)
        p.setBrush(QBrush(self._color))
        p.drawEllipse(4, 4, s, s)


class Waveform(QWidget):
    """Rolling waveform driven by real mic levels via push()."""

    def __init__(self, n: int = 36, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self._n      = n
        self._h      = [0.04] * n
        self._active = False
        QTimer(self).timeout.connect(self.update)
        QTimer(self).start(50)

    def push(self, amp: float) -> None:
        """Call with mic amplitude (0-1) every audio block."""
        self._h.pop(0)
        display = min(1.0, amp * 2.5 + random.uniform(-0.03, 0.03))
        self._h.append(max(0.04, display))

    def set_active(self, v: bool) -> None:
        self._active = v
        if not v:
            self._h = [max(0.04, h * 0.5) for h in self._h]

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bw = w / self._n
        p.setBrush(QBrush(QColor(RED if self._active else MUTED)))
        p.setPen(Qt.PenStyle.NoPen)
        for i, frac in enumerate(self._h):
            bh = max(2, int(h * frac))
            p.drawRect(int(i * bw) + 1, (h - bh) // 2, max(1, int(bw) - 2), bh)


def lbl(text: str, size: int = 11, color: str = TEXT,
        bold: bool = False, spacing: int = 0) -> QLabel:
    lb = QLabel(text)
    st = f"color:{color};font-size:{size}px;"
    if bold:    st += "font-weight:600;"
    if spacing: st += f"letter-spacing:{spacing}px;"
    lb.setStyleSheet(st)
    return lb


def hsep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color:{BORDER_L};max-height:1px;")
    return f


class SystemCard(QFrame):
    def __init__(self, tag: str, name: str, status: str,
                 active: bool = False, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"QFrame{{background:{BG_CARD};border:1px solid {BORDER};}}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(5)

        row = QHBoxLayout()
        row.addWidget(lbl(f"[ {tag} ]", 9, MUTED, spacing=1))
        row.addStretch()
        self.dot = Dot(GREEN if active else MUTED, 6)
        row.addWidget(self.dot)
        lay.addLayout(row)

        lay.addWidget(lbl(name, 13, TEXT, bold=True))
        c = GREEN if active else MUTED
        self.status_lb = lbl(f"● {status}", 10, c)
        lay.addWidget(self.status_lb)

    def update_status(self, status: str, active: bool) -> None:
        c = GREEN if active else MUTED
        self.dot.set_color(c)
        self.status_lb.setText(f"● {status}")
        self.status_lb.setStyleSheet(f"color:{c};font-size:10px;")


class TriggerCard(QFrame):
    def __init__(self, name: str, meta: str,
                 state: str = "READY", add: bool = False, parent=None):
        super().__init__(parent)
        b = f"1px dashed {BORDER_L}" if add else f"1px solid {BORDER}"
        self.setStyleSheet(f"QFrame{{background:{BG_CARD};border:{b};}}")
        self._add = add

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)

        info = QVBoxLayout()
        info.setSpacing(2)
        info.addWidget(lbl(name, 12, MUTED if add else TEXT))
        info.addWidget(lbl(meta, 10, MUTED))
        lay.addLayout(info)
        lay.addStretch()

        if not add:
            c = GREEN if state == "READY" else (RED if state == "FIRED" else MUTED)
            self.state_lb = lbl(state, 10, c)
            lay.addWidget(self.state_lb)

    def flash_fired(self) -> None:
        if self._add:
            return
        self.state_lb.setText("FIRED")
        self.state_lb.setStyleSheet(f"color:{RED};font-size:10px;font-weight:600;")
        self.setStyleSheet(f"QFrame{{background:{BG_CARD};border:1px solid {RED}40;}}")
        QTimer.singleShot(2000, self._reset)

    def _reset(self) -> None:
        self.state_lb.setText("READY")
        self.state_lb.setStyleSheet(f"color:{GREEN};font-size:10px;")
        self.setStyleSheet(f"QFrame{{background:{BG_CARD};border:1px solid {BORDER};}}")


# ── Main window ───────────────────────────────────────────────────────────────

class WendyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wendy")
        self.setMinimumSize(740, 860)
        self.setFont(QFont("Menlo", 11))
        self.setStyleSheet(f"QWidget{{background:{BG};color:{TEXT};}}")

        self._daemon:  DaemonThread | None = None
        self._mic_mon: MicMonitor   | None = None
        self._running  = False
        self._sig      = Signals()
        self._sig.line.connect(self._on_line)
        self._sig.status.connect(self._on_status)

        self._clap_card: TriggerCard | None = None   # ref for flash

        # Build UI
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea{border:none;}"
            "QScrollBar:vertical{width:6px;background:transparent;}"
            f"QScrollBar::handle:vertical{{background:{BORDER_L};border-radius:3px;}}"
        )
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll)

        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        lay.addLayout(self._titlebar())
        lay.addLayout(self._logo_section())
        lay.addWidget(self._quote())
        lay.addLayout(self._system_grid())
        lay.addWidget(self._waveform_section())
        lay.addLayout(self._trigger_section())
        lay.addWidget(self._log_section())
        lay.addStretch()
        lay.addWidget(hsep())
        lay.addLayout(self._footer())

        # Auto-start
        QTimer.singleShot(400, self.start_daemon)

    # ── Section builders ──────────────────────────────────────────────────────

    def _titlebar(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        for col in [RED, YELLOW, GREEN]:
            d = QLabel()
            d.setFixedSize(12, 12)
            d.setStyleSheet(f"background:{col};border-radius:6px;")
            lay.addWidget(d)
        lay.addWidget(lbl("  wendy.app", 11, MUTED))
        lay.addStretch()
        self._online_dot = Dot(MUTED, 7)
        self._online_lb  = lbl("OFFLINE", 10, MUTED, spacing=1)
        lay.addWidget(self._online_dot)
        lay.addWidget(self._online_lb)
        return lay

    def _logo_section(self) -> QVBoxLayout:
        lay = QVBoxLayout()
        lay.setSpacing(8)
        logo_lb = QLabel(LOGO)
        logo_lb.setStyleSheet(
            f"color:{RED};font-family:Menlo,monospace;font-size:10px;")
        logo_lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_lb = lbl("v1.0.0  —  REACTOR ONLINE", 10, MUTED, spacing=2)
        ver_lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo_lb)
        lay.addWidget(ver_lb)
        return lay

    def _quote(self) -> QLabel:
        lb = QLabel(
            f'<span style="color:{RED};">›</span>'
            '  "All systems nominal. Awaiting your command, sir."'
        )
        lb.setStyleSheet(
            f"background:{BG_CARD};border-left:2px solid {RED};"
            f"color:{TEXT};font-size:12px;padding:10px 16px;"
        )
        return lb

    def _system_grid(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.setSpacing(10)
        self._cam_card  = SystemCard("OPTICAL", "Camera",     "OFFLINE", False)
        self._mic_card  = SystemCard("AUDIO",   "Microphone", "OFFLINE", False)
        self._wake_card = SystemCard("NEURAL",  "Wake Word",  "OFFLINE", False)
        lay.addWidget(self._cam_card)
        lay.addWidget(self._mic_card)
        lay.addWidget(self._wake_card)
        return lay

    def _waveform_section(self) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            f"QFrame{{background:{BG_CARD};border:1px solid {BORDER};}}")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        row = QHBoxLayout()
        row.addWidget(lbl("[ AUDIO STREAM ]", 9, MUTED, spacing=1))
        row.addStretch()
        self._db_lb = lbl("─  dB", 10, MUTED)
        row.addWidget(self._db_lb)
        lay.addLayout(row)

        self._wave = Waveform(36)
        lay.addWidget(self._wave)
        return f

    def _trigger_section(self) -> QVBoxLayout:
        lay = QVBoxLayout()
        lay.setSpacing(10)

        header = QHBoxLayout()
        header.addWidget(lbl("[ ACTIVE TRIGGERS ]", 9, MUTED, spacing=1))
        header.addStretch()
        refresh_btn = self._mk_btn("↺  REFRESH", MUTED, self._rebuild_trigger_grid)
        refresh_btn.setFixedHeight(22)
        header.addWidget(refresh_btn)
        lay.addLayout(header)

        self._trigger_grid_widget = QWidget()
        self._trigger_grid_layout = QGridLayout(self._trigger_grid_widget)
        self._trigger_grid_layout.setSpacing(8)
        lay.addWidget(self._trigger_grid_widget)

        self._rebuild_trigger_grid()
        return lay

    def _rebuild_trigger_grid(self) -> None:
        # Clear old cards
        while self._trigger_grid_layout.count():
            item = self._trigger_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._clap_card = None

        cards: list[tuple[str, str, bool]] = []  # (name, meta, add)

        # Built-in: clap
        cards.append(("CLAP  ×  2", "audio + motion · CNN", False))

        # Dynamic: templates
        if TMPL_DIR.is_dir():
            for f in sorted(TMPL_DIR.glob("*.json")):
                try:
                    meta_raw = json.loads(
                        f.read_text(encoding="utf-8")
                    ).get("meta", {})
                    threshold = meta_raw.get("threshold", "─")
                    cards.append((
                        f.stem.upper(),
                        f"audio · DTW  thr={threshold:.0f}" if isinstance(threshold, float)
                        else "audio · DTW",
                        False,
                    ))
                except Exception:
                    cards.append((f.stem.upper(), "audio · DTW", False))

        # + new trigger
        cards.append(("+ NEW TRIGGER", "record: python3 triggers/dtw.py record <name>", True))

        cols = 2
        for i, (name, meta, add) in enumerate(cards):
            card = TriggerCard(name, meta, add=add)
            self._trigger_grid_layout.addWidget(card, i // cols, i % cols)
            if name == "CLAP  ×  2":
                self._clap_card = card

    def _log_section(self) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            f"QFrame{{background:{BG_LOG};border:1px solid {BORDER};}}")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)
        lay.addWidget(lbl("[ EVENT LOG ]", 9, MUTED, spacing=1))

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(150)
        self._log.setStyleSheet(
            f"QTextEdit{{background:transparent;border:none;"
            f"color:{MUTED};font-size:11px;font-family:Menlo,monospace;}}"
        )
        lay.addWidget(self._log)
        return f

    def _footer(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        self._start_btn = self._mk_btn("▶  START", GREEN, self.start_daemon)
        self._stop_btn  = self._mk_btn("⏹  STOP",  RED,   self.stop_daemon)
        self._stop_btn.setEnabled(False)
        lay.addWidget(self._start_btn)
        lay.addWidget(self._stop_btn)
        lay.addSpacing(12)
        self._status_lb = lbl("OFFLINE", 10, MUTED, spacing=1)
        lay.addWidget(self._status_lb)
        lay.addStretch()
        self._res_lb = lbl("", 10, MUTED)
        lay.addWidget(self._res_lb)
        return lay

    def _mk_btn(self, text: str, color: str, fn) -> QPushButton:
        b = QPushButton(text)
        b.setFixedHeight(28)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(
            f"QPushButton{{background:transparent;border:1px solid {color}70;"
            f"color:{color};padding:0 14px;font-size:11px;"
            f"font-family:Menlo,monospace;letter-spacing:1px;}}"
            f"QPushButton:hover{{background:{color}18;}}"
            f"QPushButton:disabled{{color:{MUTED};border-color:{BORDER};}}"
        )
        b.clicked.connect(fn)
        return b

    # ── Daemon control ─────────────────────────────────────────────────────────

    def start_daemon(self) -> None:
        if self._running:
            return
        self._daemon = DaemonThread(self._sig)
        self._daemon.start()

        # Real-time mic monitor for waveform
        self._mic_mon = MicMonitor()
        self._mic_mon.level.connect(self._on_mic_level)
        self._mic_mon.start()

    def stop_daemon(self) -> None:
        if self._daemon:
            self._daemon.stop()
        if self._mic_mon:
            self._mic_mon.stop_monitor()
            self._mic_mon.wait(3000)
            self._mic_mon = None

    # ── Signal handlers ────────────────────────────────────────────────────────

    def _on_mic_level(self, amp: float) -> None:
        self._wave.push(amp)
        level = min(100, max(0, int(amp * 200)))
        self._db_lb.setText(f"LVL  {level:3d}")

    def _on_status(self, s: str) -> None:
        if s == "running":
            self._running = True
            self._start_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)
            self._online_dot.set_color(GREEN)
            self._set_lbl(self._online_lb,  "ONLINE",    GREEN)
            self._set_lbl(self._status_lb,  "LISTENING", GREEN)
            self._wave.set_active(True)
        else:
            self._running = False
            self._start_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._online_dot.set_color(MUTED)
            self._set_lbl(self._online_lb, "OFFLINE", MUTED)
            self._set_lbl(self._status_lb, "OFFLINE", MUTED)
            self._wave.set_active(False)
            self._db_lb.setText("─  dB")
            for c in (self._cam_card, self._mic_card, self._wake_card):
                c.update_status("OFFLINE", False)

    def _on_line(self, line: str) -> None:
        lo = line.lower()

        # No «Wendy» gate (disabled in config or vosk/model/mic init failed)
        if "clap detection always active" in lo:
            self._wake_card.update_status("BYPASS · claps always on", True)

        # ── Camera / mic activation ───────────────────────────
        if "mic + camera" in lo:
            self._cam_card.update_status("ACTIVE · 30fps",   True)
            self._mic_card.update_status("ACTIVE · 44.1kHz", True)
        elif "mic only" in lo:
            self._cam_card.update_status("UNAVAILABLE",      False)
            self._mic_card.update_status("ACTIVE · 44.1kHz", True)

        if "clap cnn loaded" in lo:
            self._mic_card.update_status("ACTIVE · CNN gate", True)

        # ── Wake word states ──────────────────────────────────
        if "say «" in lo:
            self._wake_card.update_status('STANDBY · "Wendy"', False)
            self._set_lbl(self._status_lb, "LISTENING", GREEN)

        if "armed for" in lo:
            self._wake_card.update_status("ARMED · LISTENING", True)
            self._set_lbl(self._status_lb, "ARMED", YELLOW)
            QTimer.singleShot(10_000, self._reset_to_listening)

        if "disarmed" in lo:
            self._reset_to_listening()

        # ── Double clap triggered ─────────────────────────────
        if "double clap" in lo:
            self._wake_card.update_status("TRIGGERED  ✦", True)
            self._set_lbl(self._status_lb, "TRIGGERED", RED)
            if self._clap_card:
                self._clap_card.flash_fired()
            QTimer.singleShot(3_000, self._reset_to_listening)

        # ── Suppress noisy lines from log ─────────────────────
        noisy = ("clap blocked", "second clap missed", "👁", "visual clap",
                 "[cam]", "no blobs", "only right", "only left")
        if any(k in lo for k in noisy):
            return

        # ── Append to log ─────────────────────────────────────
        ts   = datetime.now().strftime("%H:%M:%S")
        hot  = any(k in lo for k in
                   ["clap", "✦", "armed", "wake", "wendy", "✓", "trigger"])
        col  = TEXT if hot else MUTED
        safe = line.strip().replace("&", "&amp;").replace("<", "&lt;")
        self._log.append(
            f'<span style="color:{MUTED};">{ts}</span>'
            f'&nbsp;&nbsp;<span style="color:{col};">{safe}</span>'
        )
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _reset_to_listening(self) -> None:
        if not self._running:
            return
        self._wake_card.update_status('STANDBY · "Wendy"', False)
        self._set_lbl(self._status_lb, "LISTENING", GREEN)

    def _set_lbl(self, lb: QLabel, text: str, color: str) -> None:
        lb.setText(text)
        lb.setStyleSheet(
            f"color:{color};font-size:10px;letter-spacing:1px;")

    # ── Cleanup ────────────────────────────────────────────────────────────────

    def closeEvent(self, e):
        self.stop_daemon()
        if self._daemon:
            self._daemon.wait(3000)
        if self._mic_mon:
            self._mic_mon.wait(1000)
        e.accept()


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = WendyApp()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
