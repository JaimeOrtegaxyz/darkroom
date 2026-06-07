"""The red safelight (spec 1.5 / 3.4).

The pattern engine is the product: named phases with tunable timings,
computed as smooth brightness curves at ~30fps. Renderers are the hardware
seam — the engine runs identically on a dev machine (NullRenderer ignores
frames; phase changes are logged) and on the Pi (a NeoPixel renderer pushes
frames to the LED).

Pi renderer, when we get to build step 3: a class with
    show(rgb: tuple[int,int,int]) -> None
backed by rpi_ws281x / adafruit-circuitpython-neopixel. Mind the pin
constraint from spec 2.2: WS2812 timing wants the PWM/DMA pin (GPIO18) or
the SPI pin (GPIO10); document whichever the library needs.
"""

from __future__ import annotations

import logging
import math
import threading
import time

log = logging.getLogger("safelight")

RED = (255, 28, 8)
AMBER = (255, 120, 0)

# All timings tunable via config.safelight (merged over these). Spec 3.4 table.
DEFAULT_PATTERNS: dict[str, dict] = {
    "idle":       {"kind": "breathe", "period_s": 8.0, "min": 0.0, "max": 0.05, "color": RED},
    "developing": {"kind": "breathe", "period_s": 4.0, "min": 0.08, "max": 0.85, "color": RED},
    "uploading":  {"kind": "breathe", "period_s": 1.6, "min": 0.15, "max": 0.90, "color": RED},
    "done":       {"kind": "solid", "level": 0.9, "color": RED, "hold_s": 2.0, "then": "idle"},
    "error":      {"kind": "blink", "period_s": 0.5, "level": 0.7, "color": AMBER},
    "off":        {"kind": "off"},
}


def _describe(p: dict) -> str:
    k = p["kind"]
    if k == "breathe":
        return f"breathing, {p['period_s']}s period, {p['min']:.0%}–{p['max']:.0%}"
    if k == "blink":
        return f"blinking every {p['period_s']}s"
    if k == "solid":
        return f"solid {p['level']:.0%}" + (f" for {p['hold_s']}s then '{p['then']}'" if "then" in p else "")
    return k


class NullRenderer:
    """Dev machine: no LED. Frames are dropped; set_phase logging suffices."""

    def show(self, rgb: tuple[int, int, int]) -> None:
        pass


class Safelight:
    def __init__(self, renderer=None, overrides: dict | None = None, fps: int = 30):
        self.renderer = renderer or NullRenderer()
        self.patterns = {k: dict(v) for k, v in DEFAULT_PATTERNS.items()}
        for name, over in (overrides or {}).items():
            self.patterns.setdefault(name, {}).update(over)
        self.fps = fps
        self._lock = threading.Lock()
        self._phase = "off"
        self._phase_start = time.monotonic()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="safelight", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.renderer.show((0, 0, 0))

    def set_phase(self, name: str) -> None:
        with self._lock:
            if name == self._phase:
                return
            self._phase = name
            self._phase_start = time.monotonic()
        p = self.patterns.get(name, self.patterns["off"])
        log.info("[safelight] %s — %s", name, _describe(p))

    def _frame(self) -> tuple[int, int, int]:
        with self._lock:
            name, t0 = self._phase, self._phase_start
        p = self.patterns.get(name, self.patterns["off"])
        t = time.monotonic() - t0
        kind = p["kind"]

        if kind == "off":
            level = 0.0
        elif kind == "solid":
            level = p["level"]
            if "then" in p and t >= p.get("hold_s", 2.0):
                self.set_phase(p["then"])
        elif kind == "breathe":
            # Sine ramp starting from the dim end — the "slow glow" (spec 1.5).
            level = p["min"] + (p["max"] - p["min"]) * (0.5 - 0.5 * math.cos(2 * math.pi * t / p["period_s"]))
        elif kind == "blink":
            level = p["level"] if (t % p["period_s"]) < p["period_s"] / 2 else 0.0
        else:
            level = 0.0

        r, g, b = p.get("color", RED)
        return (int(r * level), int(g * level), int(b * level))

    def _run(self) -> None:
        frame_dt = 1.0 / self.fps
        while not self._stop.is_set():
            self.renderer.show(self._frame())
            self._stop.wait(frame_dt)
