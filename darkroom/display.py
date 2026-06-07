"""The little screen (spec 1.6 / 3.3).

Division of labor to preserve: screen = the decision + device feedback;
phone = looking at images. During DEVELOPING the screen shows only the tiny
progress glyph so the safelight owns the moment.

ConsoleDisplay simulates the device screen as log lines on a dev machine.
The Pi backend (build step 2) implements the same interface against an SPI
panel; nothing above this seam changes.
"""

from __future__ import annotations

import logging

import qrcode

log = logging.getLogger("screen")

# Closing-pie progress glyph, themed as "developing" (spec 3.3).
PIE = "○◔◑◕●"


def pie_glyph(done: int, total: int) -> str:
    if total <= 0:
        return PIE[0]
    return PIE[round((done / total) * (len(PIE) - 1))]


class Display:
    def show_idle(self, filter_name: str, gallery_url: str) -> None: ...
    def show_menu(self, names: list[str], selected: int) -> None: ...
    def show_developing(self, done: int, total: int) -> None: ...
    def show_done(self, new_count: int, gallery_url: str) -> None: ...
    def show_error(self, message: str) -> None: ...
    def show_qr(self, url: str) -> None: ...


class ConsoleDisplay(Display):
    """Each call logs one '[screen]' line; identical repeats are suppressed."""

    def __init__(self):
        self._last = ""

    def _line(self, text: str) -> None:
        if text != self._last:
            self._last = text
            log.info("[screen] %s", text)

    def show_idle(self, filter_name: str, gallery_url: str) -> None:
        self._line(f"READY — will transform to: {filter_name}  ·  insert card to develop  ·  {gallery_url}")

    def show_menu(self, names: list[str], selected: int) -> None:
        row = "  ".join(f"▶{n}◀" if i == selected else n for i, n in enumerate(names))
        self._line(f"MENU  {row}")

    def show_developing(self, done: int, total: int) -> None:
        # Mostly-dark screen, one small glyph — red glow owns the moment (1.6).
        self._line(f"{pie_glyph(done, total)}  {done}/{total}")

    def show_done(self, new_count: int, gallery_url: str) -> None:
        if new_count:
            self._line(f"DONE — {new_count} developed · scan to view · {gallery_url}")
        else:
            self._line(f"DONE — nothing new on this card · {gallery_url}")

    def show_error(self, message: str) -> None:
        self._line(f"ERROR — {message}")

    def show_qr(self, url: str) -> None:
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make()
        print()  # raw print: the QR is boot-time, before threads start chattering
        qr.print_ascii(invert=True)
        print(f"  gallery → {url}\n")


def get_display(_cfg) -> Display:
    return ConsoleDisplay()  # Pi SPI panel backend slots in here later
