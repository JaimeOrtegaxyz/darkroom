"""Buttons (spec 2.2 / 3.2): Up / Down / Select.

Dev backend: the keyboard, raw (no Enter needed) —
    u / k / ↑   up
    d / j / ↓   down
    s / ⏎ / ␣  select
    i           simulate re-inserting the current card
    q / Ctrl-C  quit

Pi backend (build step 2): gpiozero Buttons with internal pull-ups and
software debounce; Select gets hold_time≈3s wired to safe shutdown
(spec 1.7), alongside the PiSugar power button. Same events, same bus.
"""

from __future__ import annotations

import logging
import queue
import select
import sys
import threading

log = logging.getLogger("inputs")


class KeyboardInput(threading.Thread):
    def __init__(self, bus: queue.Queue):
        super().__init__(name="keyboard", daemon=True)
        self.bus = bus
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    @staticmethod
    def usable() -> bool:
        return sys.stdin.isatty()

    def _emit(self, event: dict) -> None:
        self.bus.put(event)

    def run(self) -> None:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while not self._stop.is_set():
                r, _, _ = select.select([sys.stdin], [], [], 0.2)
                if not r:
                    continue
                ch = sys.stdin.read(1)
                if ch == "\x1b":  # arrow keys arrive as ESC [ A/B
                    r, _, _ = select.select([sys.stdin], [], [], 0.05)
                    seq = sys.stdin.read(2) if r else ""
                    ch = {"[A": "u", "[B": "d"}.get(seq, "")
                if ch in ("u", "k"):
                    self._emit({"type": "button", "button": "up"})
                elif ch in ("d", "j"):
                    self._emit({"type": "button", "button": "down"})
                elif ch in ("s", "\n", "\r", " "):
                    self._emit({"type": "button", "button": "select"})
                elif ch == "i":
                    self._emit({"type": "simulate_insert"})
                elif ch in ("q", "\x03"):
                    self._emit({"type": "quit"})
                    return
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def start_inputs(bus: queue.Queue) -> KeyboardInput | None:
    if not KeyboardInput.usable():
        log.info("[inputs] stdin is not a TTY — keyboard buttons disabled")
        return None
    kb = KeyboardInput(bus)
    kb.start()
    log.info("[inputs] keys: u/d=navigate  s=select  i=re-insert card  q=quit")
    return kb
