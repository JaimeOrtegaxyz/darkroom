"""Local web server + live gallery (spec 1.8 / 4.5).

No app, no login: one page, served from the device. Photos appear one by one
as they finish — the reveal is the payoff, so updates stream over SSE (with
EventSource's built-in reconnect as the safety net).

Events published here:
  state  {state, filter, progress:{done,total}, counts}
  item   {item}   (any status change: pending -> working -> done | error)
"""

from __future__ import annotations

import json
import logging
import queue
import socket
import threading
from pathlib import Path

from flask import Flask, Response, abort, jsonify, send_file

from .store import Store

log = logging.getLogger("gallery")

WEB_DIR = Path(__file__).parent / "web"


class Broadcaster:
    """Tiny pub-sub: one queue per connected gallery page."""

    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers: set[queue.Queue] = set()

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=256)
        with self._lock:
            self._subscribers.add(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            self._subscribers.discard(q)

    def publish(self, kind: str, payload: dict) -> None:
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait((kind, payload))
            except queue.Full:
                pass  # slow client; EventSource will reconnect and re-fetch


def get_lan_ip() -> str:
    """Best-effort LAN address for the QR code. No traffic is actually sent."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def create_app(store: Store, get_state, broadcaster: Broadcaster) -> Flask:
    app = Flask("darkroom")

    @app.get("/")
    def index():
        return send_file(WEB_DIR / "index.html")

    @app.get("/api/state")
    def api_state():
        return jsonify(get_state())

    @app.get("/api/items")
    def api_items():
        return jsonify({"items": [store.to_api(i) for i in store.items_newest_first()]})

    @app.get("/img/<item_id>/<kind>")
    def img(item_id: str, kind: str):
        if kind == "orig":
            path = store.original_path(item_id)
        elif kind == "out":
            path = store.output_path(item_id)
        else:
            abort(404)
        if not path.is_file():
            abort(404)
        resp = send_file(path, mimetype="image/jpeg", conditional=True)
        # Item ids are unique and outputs are written once: cache hard.
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp

    @app.get("/events")
    def events():
        def stream():
            q = broadcaster.subscribe()
            try:
                yield "retry: 2000\n\n"
                yield _sse("state", get_state())
                while True:
                    try:
                        kind, payload = q.get(timeout=15)
                        yield _sse(kind, payload)
                    except queue.Empty:
                        yield ": keepalive\n\n"
            finally:
                broadcaster.unsubscribe(q)

        return Response(
            stream(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


def _sse(kind: str, payload: dict) -> str:
    return f"event: {kind}\ndata: {json.dumps(payload)}\n\n"


def run_in_thread(app: Flask, host: str, port: int) -> threading.Thread:
    logging.getLogger("werkzeug").setLevel(logging.WARNING)  # quiet request spam

    def serve():
        # Flask's dev server, threaded, is plenty for a one-phone appliance.
        app.run(host=host, port=port, threaded=True, use_reloader=False)

    t = threading.Thread(target=serve, name="gallery", daemon=True)
    t.start()
    return t
