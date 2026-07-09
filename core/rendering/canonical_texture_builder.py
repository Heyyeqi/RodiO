"""Build canonical Earth texture LODs from higher-resolution RGB sources."""

from __future__ import annotations

from typing import Tuple

import numpy as np
from PIL import Image


class CanonicalTextureBuilder:
    """Downsample RGB textures into deterministic canonical LOD sizes."""

    def build(self, texture, target_resolution: Tuple[int, int]) -> np.ndarray:
        """Return uint8 RGB array resized to target (width, height)."""
        if isinstance(texture, Image.Image):
            return np.asarray(self.build_image(texture, target_resolution), dtype=np.uint8)

        arr = _as_rgb(texture)
        return np.asarray(self.build_image(Image.fromarray(arr, mode="RGB"), target_resolution), dtype=np.uint8)

    def build_image(self, image: Image.Image, target_resolution: Tuple[int, int]) -> Image.Image:
        """Return PIL RGB image resized to target (width, height)."""
        target_w, target_h = int(target_resolution[0]), int(target_resolution[1])
        if target_w <= 0 or target_h <= 0:
            raise ValueError(f"target_resolution must be positive, got {target_resolution!r}")

        if image.mode != "RGB":
            image = image.convert("RGB")
        resized = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
        return resized


def _as_rgb(value) -> np.ndarray:
    arr = np.asarray(value)
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError(f"texture must be RGB (H, W, 3), got {arr.shape}")
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(arr)
