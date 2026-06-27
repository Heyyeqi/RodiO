"""Export baked texture arrays into frontend-friendly payloads."""

from __future__ import annotations

from io import BytesIO
from typing import Dict, Literal

import numpy as np
from PIL import Image


TextureFormat = Literal["raw", "png"]


def export_texture_payload(textures: Dict[str, object], fmt: TextureFormat = "raw") -> Dict[str, object]:
    """
    Convert D6TextureBaker output to a frontend payload.

    Raw payloads keep bytes uncompressed for WebGL upload paths. PNG payloads
    are useful for HTTP/file export and test fixtures.
    """
    base = _as_rgb(textures["base_texture"], "base_texture")
    overlay = _as_rgb(textures["overlay_texture"], "overlay_texture")
    if base.shape != overlay.shape:
        raise ValueError(f"base/overlay shape mismatch: {base.shape} != {overlay.shape}")

    height, width = base.shape[:2]
    payload = {
        "baseTexture": _encode(base, fmt),
        "overlayTexture": _encode(overlay, fmt),
        "resolution": textures.get("resolution", f"{width}x{height}"),
        "canonicalRenderResolution": textures.get("canonical_render_resolution", f"{width}x{height}"),
        "resolutionMode": textures.get("resolution_mode", "unknown"),
        "format": fmt,
        "width": width,
        "height": height,
        "channels": 3,
    }
    return payload


def _as_rgb(value, name: str) -> np.ndarray:
    arr = np.asarray(value)
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError(f"{name} must be RGB (H, W, 3), got {arr.shape}")
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(arr)


def _encode(arr: np.ndarray, fmt: TextureFormat) -> bytes:
    if fmt == "raw":
        return arr.tobytes(order="C")
    if fmt == "png":
        buf = BytesIO()
        Image.fromarray(arr, mode="RGB").save(buf, format="PNG")
        return buf.getvalue()
    raise ValueError(f"Unsupported texture export format {fmt!r}")
