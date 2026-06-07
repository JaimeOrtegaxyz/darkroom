"""Boot, orchestration, and the state machine (spec 3.1 / 3.2 / 4.2).

States: IDLE, MENU, DEVELOPING, DONE, ERROR. "CARD_INSERTED" is a transition
trigger, not a state: insertion commits the loaded filter and starts the
batch immediately — the card slot is the shutter (spec 1.4). No confirmation.

Threads:
  main           this state machine, consuming the event bus
  card-watcher   posts card_inserted / card_removed
  keyboard       posts button events (dev stand-in for GPIO)
  develop-N      transform workers (ThreadPoolExecutor)
  gallery        Flask
  safelight      LED pattern engine
Workers touch only Store/Broadcaster (both locked); all state-machine
mutation happens on the main thread via bus events.
"""

from __future__ import annotations

import argparse
import logging
import queue
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import __version__, prompts
from .card import CardWatcher, find_photos
from .config import Config, StateFile, load_config
from .display import get_display
from .gallery import Broadcaster, create_app, get_lan_ip, run_in_thread
from .inputs import start_inputs
from .safelight import Safelight
from .store import Store, sha256_bytes
from .transform import TransformError, get_backend

log = logging.getLogger("main")


class Darkroom:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.bus: queue.Queue = queue.Queue()
        self.store = Store(cfg.data_dir)
        self.statefile = StateFile(cfg.state_path)
        self.backend = get_backend(cfg)
        self.display = get_display(cfg)
        self.safelight = Safelight(overrides=cfg.safelight)
        self.broadcaster = Broadcaster()
        self.executor = ThreadPoolExecutor(cfg.workers, thread_name_prefix="develop")
        self.gallery_url = f"http://{get_lan_ip()}:{cfg.gallery_port}/"

        # The loaded film stock (spec 1.4): persistent until changed in MENU.
        loaded = self.statefile.get("loaded_filter", cfg.default_filter)
        if prompts.get(loaded) is None:
            log.warning("[main] unknown loaded filter %r — falling back to %r",
                        loaded, prompts.PROMPTS[0]["id"])
            loaded = prompts.PROMPTS[0]["id"]
        self.loaded_filter: str = loaded

        self.state = "IDLE"
        self.menu_idx = 0
        self.batch_ids: list[str] = []
        self.batch_done = 0
        self.last_done_count = 0
        self.error_msg = ""
        self._error_deadline = 0.0
        self.last_card: Path | None = cfg.card_path

    # -- state plumbing --------------------------------------------------------

    def current_filter(self) -> dict:
        return prompts.get(self.loaded_filter)  # validated at boot

    def gallery_state(self) -> dict:
        return {
            "state": self.state,
            "filter": self.current_filter()["name"],
            "message": self.error_msg if self.state == "ERROR" else "",
            "progress": {"done": self.batch_done, "total": len(self.batch_ids)},
            "counts": self.store.counts(),
        }

    def publish_state(self) -> None:
        self.broadcaster.publish("state", self.gallery_state())

    def publish_item(self, item: dict) -> None:
        self.broadcaster.publish("item", {"item": self.store.to_api(item)})

    _PHASES = {"IDLE": "idle", "MENU": "idle", "DEVELOPING": "developing",
               "DONE": "done", "ERROR": "error"}

    def set_state(self, new: str) -> None:
        self.state = new
        self.safelight.set_phase(self._PHASES[new])
        if new == "IDLE":
            self.display.show_idle(self.current_filter()["name"], self.gallery_url)
        elif new == "MENU":
            self.display.show_menu(prompts.names(), self.menu_idx)
        elif new == "DEVELOPING":
            self.display.show_developing(self.batch_done, len(self.batch_ids))
        elif new == "DONE":
            self.display.show_done(self.last_done_count, self.gallery_url)
        elif new == "ERROR":
            self.display.show_error(self.error_msg)
        self.publish_state()

    def fail(self, msg: str) -> None:
        log.warning("[main] ERROR: %s", msg)
        self.error_msg = msg
        self._error_deadline = time.monotonic() + self.cfg.error_return_s
        self.set_state("ERROR")

    # -- the batch (spec 4.3 / 4.5) ----------------------------------------------

    def start_batch(self, card_path: Path) -> None:
        fltr = self.current_filter()
        try:
            photos = find_photos(card_path)
        except OSError as e:
            self.fail(f"could not read card: {e}")
            return
        if not photos:
            self.fail("no photos found on card")
            return

        # Enumerate now, copying originals on-device, so the develop finishes
        # even if the card is pulled mid-batch. The card itself: read-only (1.9).
        new_items: list[dict] = []
        skipped = 0
        for path in photos:
            try:
                data = path.read_bytes()
            except OSError as e:
                log.warning("[main] unreadable, skipping %s (%s)", path.name, e)
                continue
            sha = sha256_bytes(data)
            if not self.cfg.reprocess and self.store.seen(sha, fltr["id"]):
                skipped += 1
                continue
            item = self.store.add_item(
                src_name=path.name, sha=sha, filter_id=fltr["id"],
                filter_name=fltr["name"], prompt=fltr["prompt"], original_bytes=data,
            )
            new_items.append(item)

        if not new_items:
            log.info("[main] nothing new on this card with '%s' loaded (%d already developed)",
                     fltr["name"], skipped)
            self.last_done_count = 0
            self.set_state("DONE")
            return

        log.info("[main] developing %d photo(s) with '%s' (%d skipped as already developed)",
                 len(new_items), fltr["name"], skipped)
        self.batch_ids = [i["id"] for i in new_items]
        self.batch_done = 0
        self.set_state("DEVELOPING")
        for item in new_items:
            self.publish_item(item)
            self.executor.submit(self._develop, item["id"])

    def _develop(self, item_id: str) -> None:
        """Worker thread: one photo, original copy -> transform -> output."""
        item = self.store.get(item_id)
        try:
            self.publish_item(self.store.update(item_id, status="working"))
            data = self.store.original_path(item_id).read_bytes()
            for attempt in (1, 2):
                try:
                    out = self.backend.transform(data, item["prompt"])
                    break
                except TransformError as e:
                    if e.retryable and attempt == 1:
                        log.warning("[develop] %s: %s — retrying once", item["src_name"], e)
                        time.sleep(2)
                        continue
                    raise
            self.store.save_output(item_id, out)
            done = self.store.update(item_id, status="done",
                                     finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
            self.publish_item(done)
            log.info("[develop] ✓ %s", item["src_name"])
        except TransformError as e:
            self.publish_item(self.store.update(item_id, status="error", error=str(e)))
            log.warning("[develop] ✗ %s: %s", item["src_name"], e)
        except Exception as e:  # never let a worker die silently
            self.publish_item(self.store.update(item_id, status="error",
                                                error=f"unexpected: {e}"))
            log.exception("[develop] unexpected failure on %s", item["src_name"])
        finally:
            self.bus.put({"type": "item_done"})

    def _on_item_done(self) -> None:
        self.batch_done += 1
        total = len(self.batch_ids)
        self.display.show_developing(self.batch_done, total)
        self.publish_state()
        if self.batch_done < total:
            return
        statuses = [self.store.get(i)["status"] for i in self.batch_ids]
        failed = statuses.count("error")
        self.last_done_count = total - failed
        log.info("[main] batch complete: %d developed, %d failed", self.last_done_count, failed)
        if failed == total:
            first_err = next((self.store.get(i)["error"] for i in self.batch_ids
                              if self.store.get(i)["status"] == "error"), "transform failed")
            self.fail(f"all {total} failed — {first_err}")
        else:
            self.set_state("DONE")

    # -- events --------------------------------------------------------------------

    def _on_button(self, button: str) -> None:
        if self.state == "DEVELOPING":
            return  # buttons don't interrupt a develop
        if self.cfg.single_filter_mode:
            return  # spec 1.4: same hardware, MENU skipped entirely
        if self.state in ("IDLE", "DONE", "ERROR") and button in ("up", "down"):
            self.menu_idx = max(prompts.index_of(self.loaded_filter), 0)
            self.set_state("MENU")
        elif self.state == "MENU":
            n = len(prompts.PROMPTS)
            if button == "up":
                self.menu_idx = (self.menu_idx - 1) % n
                self.display.show_menu(prompts.names(), self.menu_idx)
            elif button == "down":
                self.menu_idx = (self.menu_idx + 1) % n
                self.display.show_menu(prompts.names(), self.menu_idx)
            elif button == "select":
                self.loaded_filter = prompts.PROMPTS[self.menu_idx]["id"]
                self.statefile.set("loaded_filter", self.loaded_filter)
                log.info("[main] stock loaded: %s", self.current_filter()["name"])
                self.set_state("IDLE")

    def _on_card_inserted(self, path: Path) -> None:
        self.last_card = path
        if self.state == "DEVELOPING":
            log.warning("[main] already developing — ignoring %s", path)
            return
        self.start_batch(path)

    def _on_card_removed(self, path: Path) -> None:
        if self.state == "DEVELOPING":
            # Originals were copied at enumeration; the batch finishes anyway.
            log.info("[main] card removed mid-develop — finishing from on-device copies")
        elif self.state == "DONE":
            self.set_state("IDLE")

    # -- main loop ---------------------------------------------------------------------

    def run(self) -> None:
        self.safelight.start()
        self.set_state("IDLE")
        while True:
            try:
                ev = self.bus.get(timeout=0.25)
            except queue.Empty:
                ev = None
            if ev:
                t = ev["type"]
                if t == "quit":
                    break
                elif t == "card_inserted":
                    self._on_card_inserted(ev["path"])
                elif t == "card_removed":
                    self._on_card_removed(ev["path"])
                elif t == "button":
                    self._on_button(ev["button"])
                elif t == "item_done":
                    self._on_item_done()
                elif t == "simulate_insert":
                    if self.last_card:
                        log.info("[main] simulating re-insert of %s", self.last_card)
                        self._on_card_inserted(self.last_card)
                    else:
                        log.info("[main] no card seen yet — nothing to re-insert")
            if self.state == "ERROR" and time.monotonic() > self._error_deadline:
                self.set_state("IDLE")

    def shutdown(self) -> None:
        log.info("[main] shutting down")
        self.safelight.stop()
        self.executor.shutdown(wait=False, cancel_futures=True)


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="darkroom",
        description="The Darkroom — slot in a card, watch the photos develop.",
    )
    p.add_argument("--card", type=Path, metavar="DIR",
                   help="folder standing in for the SD card (dev mode); present = inserted")
    p.add_argument("--watch", type=Path, action="append", metavar="ROOT",
                   help="watch this root for mounted cards (default: /Volumes on macOS); repeatable")
    p.add_argument("--config", type=Path, help="path to config.toml")
    p.add_argument("--data", type=Path, help="data directory (default ./data)")
    p.add_argument("--port", type=int, help="gallery port (default 8000)")
    p.add_argument("--backend", choices=["mock", "openai"], help="transform backend")
    p.add_argument("--filter", dest="filter_id", metavar="ID",
                   help="load this film stock at boot (persists, like choosing in MENU)")
    p.add_argument("--workers", type=int, help="parallel transforms (default 2)")
    p.add_argument("--mock-delay", type=float, help="fake latency for the mock backend, seconds")
    p.add_argument("--reprocess", action="store_true",
                   help="ignore the already-developed index this run")
    p.add_argument("--list-filters", action="store_true", help="list film stocks and exit")
    return p.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    if args.list_filters:
        for pr in prompts.PROMPTS:
            print(f"{pr['id']:20} {pr['name']}")
        return

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")

    cfg = load_config(args.config)
    if args.card:
        cfg.card_path = args.card.expanduser().resolve()
    if args.watch:
        cfg.watch_roots = [w.expanduser() for w in args.watch]
    if args.data:
        cfg.data_dir = args.data
    if args.port:
        cfg.gallery_port = args.port
    if args.backend:
        cfg.backend = args.backend
    if args.workers:
        cfg.workers = args.workers
    if args.mock_delay is not None:
        cfg.mock_delay_s = args.mock_delay
    if args.reprocess:
        cfg.reprocess = True
    # Absolute data_dir: send_file resolves relative paths against the package
    # dir, and the Pi will run this as a service with an arbitrary CWD anyway.
    cfg.data_dir = cfg.data_dir.expanduser().resolve()

    if cfg.card_path and not cfg.card_path.is_dir():
        raise SystemExit(f"--card {cfg.card_path} is not a directory")
    if args.filter_id and prompts.get(args.filter_id) is None:
        ids = ", ".join(p["id"] for p in prompts.PROMPTS)
        raise SystemExit(f"unknown filter {args.filter_id!r} — choose from: {ids}")

    try:
        app = Darkroom(cfg)
    except TransformError as e:
        raise SystemExit(f"error: {e}")
    if args.filter_id:
        app.loaded_filter = args.filter_id
        app.statefile.set("loaded_filter", args.filter_id)

    interrupted = app.store.mark_interrupted()
    if interrupted:
        log.info("[main] swept %d item(s) left mid-develop by a previous run", interrupted)

    log.info("[main] darkroom v%s — backend=%s, data=%s", __version__, cfg.backend, cfg.data_dir)
    if cfg.card_path:
        log.info("[main] card source: fixed folder %s (press 'i' to re-insert)", cfg.card_path)
    else:
        log.info("[main] card source: watching %s for mounts with a DCIM folder",
                 ", ".join(map(str, cfg.watch_roots)))

    flask_app = create_app(app.store, app.gallery_state, app.broadcaster)
    gallery_thread = run_in_thread(flask_app, cfg.gallery_host, cfg.gallery_port)
    time.sleep(0.4)
    if not gallery_thread.is_alive():
        raise SystemExit(f"gallery failed to start — is port {cfg.gallery_port} already in use?")
    app.display.show_qr(app.gallery_url)

    watcher = CardWatcher(app.bus, fixed_path=cfg.card_path,
                          watch_roots=None if cfg.card_path else cfg.watch_roots)
    watcher.start()
    kb = start_inputs(app.bus)

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        watcher.stop()
        if kb:
            kb.stop()
        app.shutdown()


if __name__ == "__main__":
    main()
