"""
Wendy App — macOS control panel (PyQt6)
Iron Man / JARVIS theme.

Install: pip install PyQt6
Run:     python3 wendy_app.py
"""

from __future__ import annotations

import sys
import random
import subprocess
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QFrame, QScrollArea, QTextEdit,
)

ROOT = Path(__file__).resolve().parent

# ── Palette ───────────────────────────────────────────────────────────────────
BG       = "#0a0e14"
BG_CARD  = "#0d1117"
BG_LOG   = "#060a10"
RED      = "#d4453d"
GREEN    = "#34c759"
YELLOW   = "#ffcc00"
TEXT     = "#e8e6e3"
MUTED    = "#4b5563"
BORDER   = "#1c2330"
BORDER_L = "#2d3748"

LOGO = """\
 ██╗    ██╗███████╗███╗   ██╗██████╗ ██╗   ██╗
 ██║    ██║██╔════╝████╗  ██║██╔══██╗╚██╗ ██╔╝
 ██║ █╗ ██║█████╗  ██╔██╗ ██║██║  ██║ ╚████╔╝
 ██║███╗██║██╔══╝  ██║╚██╗██║██║  ██║  ╚██╔╝
 ╚███╔███╔╝███████╗██║ ╚████║██████╔╝   ██║
  ╚══╝╚══╝ ╚══════╝╚═╝  ╚═══╝╚═════╝    ╚═╝"""


# ── Daemon thread ─────────────────────────────────────────────────────────────
class Signals(QObject):
    line   = pyqtSignal(str)
    status = pyqtSignal(str)   # "running" | "stopped"


class DaemonThread(QThread):
    def __init__(self, sig: Signals):
        super().__init__()
        self._sig  = sig
        self._proc = None

    def run(self):
        self._proc = subprocess.Popen(
            [sys.executable, str(ROOT / "wendy_daemon.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(ROOT),
        )
        self._sig.status.emit("running")
        for raw in self._proc.stdout:
            line = raw.rstrip()
            if line:
                self._sig.line.emit(line)
        self._proc.wait()
        self._sig.status.emit("stopped")

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()


# ── Custom widgets ────────────────────────────────────────────────────────────
class Dot(QWidget):
    def __init__(self, color=GREEN, size=8, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._size  = size
        self.setFixedSize(size + 8, size + 8)

    def set_color(self, c: str):
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
    def __init__(self, n=36, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self._n      = n
        self._h      = [random.uniform(0.05, 0.2)] * n
        self._active = False
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(80)

    def set_active(self, v: bool):
        self._active = v

    def _tick(self):
        if self._active:
            self._h = [random.uniform(0.15, 1.0) for _ in range(self._n)]
        else:
            self._h = [max(0.04, h * 0.55 + random.uniform(0, 0.06))
                       for h in self._h]
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bw   = w / self._n
        p.setBrush(QBrush(QColor(RED if self._active else MUTED)))
        p.setPen(Qt.PenStyle.NoPen)
        for i, frac in enumerate(self._h):
            bh = max(2, int(h * frac))
            p.drawRect(int(i * bw) + 1, (h - bh) // 2, max(1, int(bw) - 2), bh)


def lbl(text, size=11, color=TEXT, bold=False, spacing=0) -> QLabel:
    lb = QLabel(text)
    st = f"color:{color};font-size:{size}px;"
    if bold:    st += "font-weight:600;"
    if spacing: st += f"letter-spacing:{spacing}px;"
    lb.setStyleSheet(st)
    return lb


def sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color:{BORDER_L};max-height:1px;")
    return f


class SystemCard(QFrame):
    def __init__(self, tag, name, status, active=True, parent=None):
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

    def update_status(self, status: str, active: bool):
        c = GREEN if active else MUTED
        self.dot.set_color(c)
        self.status_lb.setText(f"● {status}")
        self.status_lb.setStyleSheet(f"color:{c};font-size:10px;")


class TriggerCard(QFrame):
    def __init__(self, name, meta, on=True, add=False, parent=None):
        super().__init__(parent)
        b = f"1px dashed {BORDER_L}" if add else f"1px solid {BORDER}"
        self.setStyleSheet(f"QFrame{{background:{BG_CARD};border:{b};}}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        info = QVBoxLayout()
        info.setSpacing(2)
        info.addWidget(lbl(name, 12, MUTED if add else TEXT))
        info.addWidget(lbl(meta, 10, MUTED))
        lay.addLayout(info)
        lay.addStretch()
        if not add:
            lay.addWidget(lbl("ON" if on else "OFF", 10, GREEN if on else MUTED))


# ── Main window ───────────────────────────────────────────────────────────────
class WendyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wendy")
        self.setMinimumSize(740, 840)
        self.setFont(QFont("Menlo", 11))
        self.setStyleSheet(f"QWidget{{background:{BG};color:{TEXT};}}")

        self._daemon  = None
        self._running = False
        self._sig     = Signals()
        self._sig.line.connect(self._on_line)
        self._sig.status.connect(self._on_status)

        # Scroll container
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;}"
                             "QScrollBar:vertical{width:6px;background:transparent;}"
                             f"QScrollBar::handle:vertical{{background:{BORDER_L};border-radius:3px;}}")
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll)

        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        lay.addLayout(self._titlebar())
        lay.addLayout(self._logo())
        lay.addWidget(self._quote())
        lay.addLayout(self._system_grid())
        lay.addWidget(self._waveform_section())
        lay.addLayout(self._triggers_section())
        lay.addWidget(self._log_section())
        lay.addStretch()
        lay.addWidget(sep())
        lay.addLayout(self._footer())

        QTimer.singleShot(600, self.start_daemon)

    # ── Builders ──────────────────────────────────────────────────────────────

    def _titlebar(self):
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

    def _logo(self):
        lay = QVBoxLayout()
        lay.setSpacing(8)
        logo_lb = QLabel(LOGO)
        logo_lb.setStyleSheet(f"color:{RED};font-family:Menlo,monospace;font-size:10px;")
        logo_lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_lb = lbl("v1.0.0  —  REACTOR ONLINE", 10, MUTED, spacing=2)
        ver_lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo_lb)
        lay.addWidget(ver_lb)
        return lay

    def _quote(self):
        lb = QLabel(f'<span style="color:{RED};">›</span>'
                    '  "All systems nominal. Awaiting your command, sir."')
        lb.setStyleSheet(f"background:{BG_CARD};border-left:2px solid {RED};"
                         f"color:{TEXT};font-size:12px;padding:10px 16px;")
        return lb

    def _system_grid(self):
        lay = QHBoxLayout()
        lay.setSpacing(10)
        self._cam_card  = SystemCard("OPTICAL", "Camera",     "INITIALIZING",        False)
        self._mic_card  = SystemCard("AUDIO",   "Microphone", "INITIALIZING",        False)
        self._wake_card = SystemCard("NEURAL",  "Wake Word",  'STANDBY · "Wendy"',   False)
        lay.addWidget(self._cam_card)
        lay.addWidget(self._mic_card)
        lay.addWidget(self._wake_card)
        return lay

    def _waveform_section(self):
        f = QFrame()
        f.setStyleSheet(f"QFrame{{background:{BG_CARD};border:1px solid {BORDER};}}")
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

    def _triggers_section(self):
        lay = QVBoxLayout()
        lay.setSpacing(10)
        lay.addWidget(lbl("[ ACTIVE TRIGGERS ]", 9, MUTED, spacing=1))
        g = QGridLayout()
        g.setSpacing(8)
        g.addWidget(TriggerCard("CLAP  ×  2",  "audio + motion · CNN", on=True),  0, 0)
        g.addWidget(TriggerCard("SNAP",          "audio · DTW",          on=False), 0, 1)
        g.addWidget(TriggerCard("WAVE",          "motion · MediaPipe",   on=False), 1, 0)
        g.addWidget(TriggerCard("+ NEW TRIGGER", "record gesture",       add=True), 1, 1)
        lay.addLayout(g)
        return lay

    def _log_section(self):
        f = QFrame()
        f.setStyleSheet(f"QFrame{{background:{BG_LOG};border:1px solid {BORDER};}}")
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

    def _footer(self):
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

    def _mk_btn(self, text, color, fn) -> QPushButton:
        b = QPushButton(text)
        b.setFixedHeight(32)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet(f"""
            QPushButton{{background:transparent;border:1px solid {color}70;
                color:{color};padding:0 16px;font-size:11px;
                font-family:Menlo,monospace;letter-spacing:1px;}}
            QPushButton:hover{{background:{color}18;}}
            QPushButton:disabled{{color:{MUTED};border-color:{BORDER};}}
        """)
        b.clicked.connect(fn)
        return b

    # ── Daemon control ─────────────────────────────────────────────────────────

    def start_daemon(self):
        if self._running:
            return
        self._daemon = DaemonThread(self._sig)
        self._daemon.start()

    def stop_daemon(self):
        if self._daemon:
            self._daemon.stop()

    # ── Signal handlers ────────────────────────────────────────────────────────

    def _on_status(self, s: str):
        if s == "running":
            self._running = True
            self._start_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)
            self._online_dot.set_color(GREEN)
            self._set_label(self._online_lb,  "ONLINE",    GREEN)
            self._set_label(self._status_lb,  "LISTENING", GREEN)
            self._wave.set_active(True)
        else:
            self._running = False
            self._start_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
            self._online_dot.set_color(MUTED)
            self._set_label(self._online_lb, "OFFLINE", MUTED)
            self._set_label(self._status_lb, "OFFLINE", MUTED)
            self._wave.set_active(False)
            for card in (self._cam_card, self._mic_card, self._wake_card):
                card.update_status("OFFLINE", False)

    def _on_line(self, line: str):
        lo = line.lower()

        # Camera / mic
        if "mic + camera" in lo:
            self._cam_card.update_status("ACTIVE · 30fps",    True)
            self._mic_card.update_status("ACTIVE · 44.1kHz",  True)
        elif "mic only" in lo:
            self._cam_card.update_status("UNAVAILABLE",       False)
            self._mic_card.update_status("ACTIVE · 44.1kHz",  True)

        # CNN
        if "clap cnn loaded" in lo:
            self._mic_card.update_status("ACTIVE · CNN", True)

        # Wake word states
        if "say «" in lo:
            self._wake_card.update_status('STANDBY · "Wendy"', False)
        if "armed for" in lo:
            self._wake_card.update_status("ARMED · LISTENING", True)
            self._set_label(self._status_lb, "ARMED", YELLOW)
            QTimer.singleShot(10_000, self._reset_status)
        if "disarmed" in lo:
            self._reset_status()
        if "double clap" in lo:
            self._wake_card.update_status("TRIGGERED  ✦", True)
            self._set_label(self._status_lb, "TRIGGERED", RED)
            QTimer.singleShot(3_000, self._reset_status)

        # Skip noisy lines from log
        if any(k in lo for k in ("clap blocked", "second clap missed")):
            return

        # Append to log
        ts   = datetime.now().strftime("%H:%M:%S")
        hot  = any(k in lo for k in ["clap", "✦", "armed", "wake", "wendy"])
        col  = TEXT if hot else MUTED
        safe = line.strip().replace("&", "&amp;").replace("<", "&lt;")
        self._log.append(
            f'<span style="color:{MUTED};">{ts}</span>'
            f'&nbsp;&nbsp;<span style="color:{col};">{safe}</span>'
        )
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _reset_status(self):
        if not self._running:
            return
        self._wake_card.update_status('STANDBY · "Wendy"', False)
        self._set_label(self._status_lb, "LISTENING", GREEN)

    def _set_label(self, lb: QLabel, text: str, color: str):
        lb.setText(text)
        lb.setStyleSheet(f"color:{color};font-size:10px;letter-spacing:1px;")

    # ── Cleanup ────────────────────────────────────────────────────────────────

    def closeEvent(self, e):
        self.stop_daemon()
        if self._daemon:
            self._daemon.wait(3000)
        e.accept()


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = WendyApp()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
