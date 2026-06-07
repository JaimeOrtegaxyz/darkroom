"""On-device home of original copies, transformed outputs, and the index
(spec 4.2). The SD card is never written (spec 1.9); everything lands here.

Layout under <data_dir>:
  store.json          the index (source of truth, written atomically)
  originals/<id>.jpg  copy taken from the card at enumeration time — so
                      developing finishes even if the card is yanked mid-batch
  outputs/<id>.jpg    transformed results

Dedupe key is (source sha256, filter id), spec 4.3: re-inserting the same
card with the same stock loaded redoes nothing; loading a *different* stock
re-develops everything with the new look — changing stock IS asking.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import logging
import threading
from pathlib import Path

from .config import atomic_write_json

log = logging.getLogger("store")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Store:
    def __init__(self, root: Path):
        self.root = root
        self.originals = root / "originals"
        self.outputs = root / "outputs"
        self.index_path = root / "store.json"
        for d in (self.root, self.originals, self.outputs):
            d.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._items: dict[str, dict] = {}
        self._order: list[str] = []  # insertion order, oldest first
        self._seen: set[tuple[str, str]] = set()  # (sha, filter_id)
        self._load()

    # -- persistence ---------------------------------------------------------

    def _load(self) -> None:
        if not self.index_path.exists():
            return
        try:
            raw = json.loads(self.index_path.read_text())
        except (json.JSONDecodeError, OSError):
            log.warning("[store] index unreadable — starting a fresh one")
            return
        for item in raw.get("items", []):
            self._items[item["id"]] = item
            self._order.append(item["id"])
            self._seen.add((item["sha"], item["filter_id"]))

    def _save_locked(self) -> None:
        atomic_write_json(self.index_path, {"items": [self._items[i] for i in self._order]})

    # -- queries ---------------------------------------------------------------

    def seen(self, sha: str, filter_id: str) -> bool:
        with self._lock:
            return (sha, filter_id) in self._seen

    def items_newest_first(self) -> list[dict]:
        with self._lock:
            return [dict(self._items[i]) for i in reversed(self._order)]

    def get(self, item_id: str) -> dict | None:
        with self._lock:
            item = self._items.get(item_id)
            return dict(item) if item else None

    def counts(self) -> dict:
        with self._lock:
            done = sum(1 for i in self._items.values() if i["status"] == "done")
            return {"total": len(self._items), "done": done}

    # -- mutations ---------------------------------------------------------------

    def add_item(
        self,
        *,
        src_name: str,
        sha: str,
        filter_id: str,
        filter_name: str,
        prompt: str,
        original_bytes: bytes,
    ) -> dict:
        now = _dt.datetime.now()
        base = f"{now:%Y%m%d-%H%M%S}-{sha[:8]}-{filter_id}"
        with self._lock:
            item_id, n = base, 1
            while item_id in self._items:  # only possible with --reprocess
                n += 1
                item_id = f"{base}-{n}"
            item = {
                "id": item_id,
                "src_name": src_name,
                "sha": sha,
                "filter_id": filter_id,
                "filter_name": filter_name,
                "prompt": prompt,
                "status": "pending",  # pending -> working -> done | error
                "error": None,
                "created_at": now.isoformat(timespec="seconds"),
                "finished_at": None,
            }
            (self.originals / f"{item_id}.jpg").write_bytes(original_bytes)
            self._items[item_id] = item
            self._order.append(item_id)
            self._seen.add((sha, filter_id))
            self._save_locked()
            return dict(item)

    def update(self, item_id: str, **fields) -> dict:
        with self._lock:
            item = self._items[item_id]
            item.update(fields)
            self._save_locked()
            return dict(item)

    def save_output(self, item_id: str, data: bytes) -> None:
        (self.outputs / f"{item_id}.jpg").write_bytes(data)

    def mark_interrupted(self) -> int:
        """Boot sweep: anything left pending/working died with a previous run."""
        with self._lock:
            n = 0
            for item in self._items.values():
                if item["status"] in ("pending", "working"):
                    item["status"] = "error"
                    item["error"] = "interrupted — device stopped mid-develop"
                    n += 1
            if n:
                self._save_locked()
            return n

    # -- paths / API shape ---------------------------------------------------------

    def original_path(self, item_id: str) -> Path:
        return self.originals / f"{item_id}.jpg"

    def output_path(self, item_id: str) -> Path:
        return self.outputs / f"{item_id}.jpg"

    def to_api(self, item: dict) -> dict:
        """Shape served to the gallery page."""
        out = {
            "id": item["id"],
            "name": item["src_name"],
            "filter": item["filter_name"],
            "status": item["status"],
            "error": item["error"],
            "created_at": item["created_at"],
            "orig_url": f"/img/{item['id']}/orig",
            "out_url": f"/img/{item['id']}/out" if item["status"] == "done" else None,
        }
        return out
