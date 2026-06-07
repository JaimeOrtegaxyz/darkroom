"""SD card detection + read-only scan (spec 4.3).

READ-ONLY DISCIPLINE (spec 1.9): this module only ever *opens files for
reading*. Nothing here — or anywhere else — may create, modify, move or
delete anything under a card root. On the Pi the mount itself should also
be read-only (mount -o ro); on a dev machine the discipline is by code.

Two ways a "card" appears:
  * fixed path (dev): a folder standing in for the card, given via --card.
    Present at start counts as inserted (running the command IS the insertion).
  * watch roots (real use): e.g. /Volumes on macOS or /media/<user> on the Pi.
    Any directory appearing there that contains a DCIM folder is a card.
"""

from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path

log = logging.getLogger("card")

JPEG_EXTS = {".jpg", ".jpeg"}


def is_card(path: Path) -> bool:
    try:
        return (path / "DCIM").is_dir()
    except OSError:
        return False


def find_photos(card_root: Path) -> list[Path]:
    """JPEGs on the card, DCIM-first.

    Skips dotfiles and AppleDouble junk ("._IMG_0001.JPG") that macOS sprinkles
    onto FAT cards. If there is no DCIM folder (a loose dev folder), scans the
    top level only — never recurses into an arbitrary tree.
    """

    def ok(p: Path) -> bool:
        return p.is_file() and p.suffix.lower() in JPEG_EXTS and not p.name.startswith(".")

    dcim = card_root / "DCIM"
    if dcim.is_dir():
        return sorted(p for p in dcim.rglob("*") if ok(p))
    log.info("[card] no DCIM folder in %s — scanning its top level instead", card_root)
    return sorted(p for p in card_root.iterdir() if ok(p))


class CardWatcher(threading.Thread):
    """Polls for insertion/removal and posts events onto the app bus.

    Emits {"type": "card_inserted", "path": Path} and
          {"type": "card_removed",  "path": Path}.
    On the Pi this could become udev-driven later; polling at 1s is plenty
    and identical across dev and device (spec 2.2 allows either).
    """

    def __init__(self, bus: queue.Queue, *, fixed_path: Path | None = None,
                 watch_roots: list[Path] | None = None, poll_s: float = 1.0):
        super().__init__(name="card-watcher", daemon=True)
        self.bus = bus
        self.fixed_path = fixed_path
        self.watch_roots = watch_roots or []
        self.poll_s = poll_s
        self._stop = threading.Event()
        self._present: set[Path] = set()

    def stop(self) -> None:
        self._stop.set()

    def _current_cards(self) -> set[Path]:
        if self.fixed_path is not None:
            return {self.fixed_path} if self.fixed_path.is_dir() else set()
        found: set[Path] = set()
        for root in self.watch_roots:
            try:
                children = [c for c in root.iterdir() if c.is_dir() and not c.name.startswith(".")]
            except OSError:
                continue  # root not there (yet) — fine
            found.update(c for c in children if is_card(c))
        return found

    def run(self) -> None:
        while not self._stop.is_set():
            cards = self._current_cards()
            for path in sorted(cards - self._present):
                log.info("[card] card detected: %s", path)
                self.bus.put({"type": "card_inserted", "path": path})
            for path in sorted(self._present - cards):
                log.info("[card] card removed: %s", path)
                self.bus.put({"type": "card_removed", "path": path})
            self._present = cards
            self._stop.wait(self.poll_s)
