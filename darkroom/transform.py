"""THE SWAPPABLE SEAM (spec 4.4 / 1.10).

One interface: take image bytes + a prompt, return transformed image bytes.
Backends must be swappable with NO change to main.py, card.py or gallery.py.

Backends here:
  * MockBackend    — no network, no key: a darkroom-print duotone done with
                     PIL, plus configurable fake latency so the whole
                     glow/progress/reveal choreography is testable anywhere.
  * OpenAIBackend  — images/edits with gpt-image-1 (model configurable).

A future local-model backend slots in by subclassing TransformBackend and
adding a case to get_backend(). Nothing else moves.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import time

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .config import Config

log = logging.getLogger("transform")

OPENAI_EDITS_URL = "https://api.openai.com/v1/images/edits"


class TransformError(Exception):
    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class TransformBackend:
    name = "base"

    def transform(self, image_bytes: bytes, prompt: str) -> bytes:
        """Take an image + a prompt, return a transformed image. Backend-agnostic."""
        raise NotImplementedError


def _reencode_jpeg(image_bytes: bytes, max_px: int, quality: int = 90) -> Image.Image:
    """Open, honor EXIF rotation, cap the long edge. Returns a PIL image."""
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    img.thumbnail((max_px, max_px))
    return img


def _to_jpeg_bytes(img: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


class MockBackend(TransformBackend):
    """A 'development' you can see without spending a cent: red-duotone print."""

    name = "mock"

    def __init__(self, delay_s: float = 2.5):
        self.delay_s = delay_s

    def transform(self, image_bytes: bytes, prompt: str) -> bytes:
        time.sleep(self.delay_s)  # simulated API latency
        img = _reencode_jpeg(image_bytes, max_px=1024)
        gray = ImageOps.autocontrast(img.convert("L"))
        # Safelight duotone: shadows near-black red, highlights warm paper.
        toned = ImageOps.colorize(gray, black="#1a0404", white="#ffe9d6", mid="#b01c10")
        print_ = ImageOps.expand(toned, border=22, fill="#f6f1e7")
        draw = ImageDraw.Draw(print_)
        try:
            font = ImageFont.load_default(size=14)
        except TypeError:  # older Pillow
            font = ImageFont.load_default()
        caption = "developed (mock) " + time.strftime("%H:%M:%S")
        draw.text((26, print_.height - 19), caption, fill="#7a2017", font=font)
        return _to_jpeg_bytes(print_, quality=90)


class OpenAIBackend(TransformBackend):
    name = "openai"

    def __init__(self, *, api_key: str, model: str, size: str,
                 max_upload_px: int, timeout_s: float, extra: dict | None = None):
        self.api_key = api_key
        self.model = model
        self.size = size
        self.max_upload_px = max_upload_px
        self.timeout_s = timeout_s
        self.extra = dict(extra or {})

    def transform(self, image_bytes: bytes, prompt: str) -> bytes:
        # Shrink before upload: keychain-cam JPEGs can be several MB and the
        # device may be on a hotspot — smaller uploads are faster and cheaper.
        img = _reencode_jpeg(image_bytes, max_px=self.max_upload_px)
        upload = _to_jpeg_bytes(img, quality=90)

        data = {"model": self.model, "prompt": prompt, "n": "1", "size": self.size}
        data.update(self.extra)
        try:
            resp = requests.post(
                OPENAI_EDITS_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"image": ("photo.jpg", io.BytesIO(upload), "image/jpeg")},
                data=data,
                timeout=(10, self.timeout_s),
            )
        except (requests.ConnectionError, requests.Timeout) as e:
            raise TransformError(f"network problem talking to OpenAI: {e}", retryable=True)

        if resp.status_code in (401, 403):
            raise TransformError("OpenAI rejected the API key — check OPENAI_API_KEY")
        if resp.status_code == 429:
            raise TransformError("OpenAI rate limit hit", retryable=True)
        if resp.status_code >= 500:
            raise TransformError(f"OpenAI server error ({resp.status_code})", retryable=True)
        if resp.status_code != 200:
            try:
                msg = resp.json()["error"]["message"]
            except Exception:
                msg = resp.text[:200]
            raise TransformError(f"OpenAI error {resp.status_code}: {msg}")

        try:
            b64 = resp.json()["data"][0]["b64_json"]
        except (KeyError, IndexError, ValueError) as e:
            raise TransformError(f"unexpected OpenAI response shape: {e}")
        out = base64.b64decode(b64)
        # Normalize whatever came back (usually PNG) to JPEG for the store.
        return _to_jpeg_bytes(Image.open(io.BytesIO(out)).convert("RGB"), quality=92)


def get_backend(cfg: Config) -> TransformBackend:
    if cfg.backend == "mock":
        return MockBackend(delay_s=cfg.mock_delay_s)
    if cfg.backend == "openai":
        key = os.environ.get(cfg.api_key_env, "").strip()
        if not key:
            raise TransformError(
                f"backend is 'openai' but ${cfg.api_key_env} is not set — "
                f"export it, or run with --backend mock"
            )
        return OpenAIBackend(
            api_key=key,
            model=cfg.openai_model,
            size=cfg.openai_size,
            max_upload_px=cfg.max_upload_px,
            timeout_s=cfg.request_timeout_s,
            extra=cfg.openai_extra,
        )
    raise TransformError(f"unknown backend {cfg.backend!r} (expected 'mock' or 'openai')")
