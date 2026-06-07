"""Configuration (spec 4.7).

Layers, later wins:
  1. built-in defaults below
  2. config.toml (optional; --config to point elsewhere)
  3. environment variables (DARKROOM_BACKEND, DARKROOM_PORT, DARKROOM_DATA_DIR)
  4. CLI flags (applied in main.py)

The *loaded filter* is deliberately NOT configuration: it is mutable device
state (the "film stock currently loaded", spec 1.4) and persists in
<data_dir>/state.json via StateFile, so editing config.toml never silently
un-loads the stock the user chose with the buttons.
"""

from __future__ import annotations

import getpass
import json
import logging
import os
import sys
import threading
from dataclasses import dataclass, field, fields
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - py<3.11
    tomllib = None

log = logging.getLogger("config")


def _default_watch_roots() -> list[Path]:
    """Where removable media shows up if no --card/--watch is given."""
    if sys.platform == "darwin":
        return [Path("/Volumes")]
    user = getpass.getuser()
    return [Path("/media") / user, Path("/run/media") / user]


@dataclass
class Config:
    # -- storage ------------------------------------------------------------
    data_dir: Path = Path("data")

    # -- card source (spec 4.3) ----------------------------------------------
    # Either a fixed folder standing in for the card (dev), or roots that are
    # watched for mounts containing a DCIM folder (real SD card via a reader).
    card_path: Path | None = None
    watch_roots: list[Path] = field(default_factory=_default_watch_roots)
    reprocess: bool = False  # ignore the already-developed index this run

    # -- gallery (spec 4.5) ---------------------------------------------------
    gallery_host: str = "0.0.0.0"
    gallery_port: int = 8000

    # -- transform seam (spec 4.4 / 1.10) -------------------------------------
    backend: str = "mock"  # "mock" | "openai"
    workers: int = 2  # parallel transforms; API-bound so >1 helps batches
    openai_model: str = "gpt-image-1"
    openai_size: str = "auto"
    openai_extra: dict = field(default_factory=dict)  # extra form fields for /images/edits
    api_key_env: str = "OPENAI_API_KEY"
    max_upload_px: int = 1536  # long edge sent to the API (speed + cost)
    request_timeout_s: float = 180.0
    mock_delay_s: float = 2.5  # fake latency so the glow/progress choreography is testable

    # -- behavior --------------------------------------------------------------
    single_filter_mode: bool = False  # spec 1.4: same hardware, MENU skipped
    default_filter: str = "turn-to-cheese"
    error_return_s: float = 6.0  # ERROR auto-returns to IDLE after this

    # -- safelight (spec 3.4): overrides merged over safelight.DEFAULT_PATTERNS --
    safelight: dict = field(default_factory=dict)

    @property
    def state_path(self) -> Path:
        return self.data_dir / "state.json"


_PATH_FIELDS = {"data_dir", "card_path"}
_PATH_LIST_FIELDS = {"watch_roots"}


def load_config(config_path: Path | None = None) -> Config:
    cfg = Config()
    path = config_path or Path("config.toml")
    if path.exists():
        if tomllib is None:
            raise SystemExit("config.toml found but this Python lacks tomllib (need 3.11+)")
        raw = tomllib.loads(path.read_text())
        known = {f.name for f in fields(Config)}
        for key, value in raw.items():
            if key not in known:
                log.warning("[config] unknown key %r in %s — ignored", key, path)
                continue
            if key in _PATH_FIELDS and value is not None:
                value = Path(value).expanduser()
            elif key in _PATH_LIST_FIELDS:
                value = [Path(v).expanduser() for v in value]
            setattr(cfg, key, value)

    if v := os.environ.get("DARKROOM_BACKEND"):
        cfg.backend = v
    if v := os.environ.get("DARKROOM_PORT"):
        cfg.gallery_port = int(v)
    if v := os.environ.get("DARKROOM_DATA_DIR"):
        cfg.data_dir = Path(v).expanduser()
    return cfg


def atomic_write_json(path: Path, obj) -> None:
    """Write JSON via tmp+rename so a power cut never leaves a torn file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


class StateFile:
    """Mutable device state that must survive reboots (currently: loaded filter)."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._data: dict = {}
        if path.exists():
            try:
                self._data = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                log.warning("[config] state file %s unreadable — starting fresh", path)

    def get(self, key: str, default=None):
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        with self._lock:
            self._data[key] = value
            self.path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_json(self.path, self._data)
