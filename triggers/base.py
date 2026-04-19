"""
Wendy — GestureTrigger ABC + GestureEngine.

Define a new gesture by subclassing GestureTrigger, implementing
`detect(data)` and `on_triggered()`, then registering it with GestureEngine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable
import numpy as np


class GestureTrigger(ABC):
    """Abstract base for any sensor-driven trigger (audio or motion)."""

    name: str = "unnamed"

    @abstractmethod
    def detect(self, data: np.ndarray) -> bool:
        """Return True if this trigger fires on the given data block."""

    @abstractmethod
    def on_triggered(self) -> None:
        """Called once each time detect() returns True."""


class GestureEngine:
    """
    Orchestrates multiple GestureTriggers against a common data stream.

    Usage
    -----
    engine = GestureEngine()
    engine.register(ClapTrigger(action=my_fn))

    # inside audio callback:
    fired = engine.process(audio_block)   # → list of trigger names that fired
    """

    def __init__(self) -> None:
        self._triggers: list[GestureTrigger] = []

    def register(self, trigger: GestureTrigger) -> "GestureEngine":
        self._triggers.append(trigger)
        return self  # allow chaining

    def unregister(self, name: str) -> None:
        self._triggers = [t for t in self._triggers if t.name != name]

    def process(self, data: np.ndarray) -> list[str]:
        """Push data to all triggers; return names of those that fired."""
        fired: list[str] = []
        for t in self._triggers:
            try:
                if t.detect(data):
                    t.on_triggered()
                    fired.append(t.name)
            except Exception as exc:
                print(f"  ⚠  GestureTrigger «{t.name}» error: {exc}")
        return fired

    def __repr__(self) -> str:
        names = [t.name for t in self._triggers]
        return f"GestureEngine(triggers={names})"
