"""D6 texture bake helpers for visual Earth texture activation.

This layer handles RGB visual textures only. It does not read or modify SAL,
M1, VC, DEM, climate, ocean, or landcover semantics.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from core.runtime import SpatialProfile
from .lod_manager import LODManager


class D6TextureBaker:
    """Bake BMNG-style RGB textures into WebGL-friendly numpy arrays."""

    def __init__(self, resolution_mode: str = "21k") -> None:
        SpatialProfile().get_resolution(resolution_mode)
        self.resolution_mode = resolution_mode
        self.lod_manager = LODManager()

    def bake(self, bmng_base, bmng_topo) -> Dict[str, np.ndarray]:
        """
        Build base + overlay textures from RGB inputs.

        Args:
            bmng_base: RGB array shaped (H, W, 3), uint8-compatible
            bmng_topo: RGB array shaped (H, W, 3), uint8-compatible

        Returns:
            {
                "base_texture": uint8 RGB array,
                "overlay_texture": uint8 RGB array,
                "resolution": "WxH",
                "resolution_mode": "8k" | "21k",
            }
        """
        base = self._normalize_rgb(bmng_base, name="bmng_base")
        topo = self._normalize_rgb(bmng_topo, name="bmng_topo")
        if base.shape != topo.shape:
            raise ValueError(f"base/topo shape mismatch: {base.shape} != {topo.shape}")

        # Overlay is the visual topo/bathy delta encoded around mid-gray.
        # A shader or bake compositor can add it back without treating it as
        # semantic elevation data.
        delta = topo.astype(np.int16) - base.astype(np.int16)
        overlay = np.clip(delta + 128, 0, 255).astype(np.uint8)

        height, width = base.shape[:2]
        source_resolution = f"{width}x{height}"
        render_width, render_height = self.lod_manager.select_render_resolution(source_resolution)
        return {
            "base_texture": np.ascontiguousarray(base),
            "overlay_texture": np.ascontiguousarray(overlay),
            "resolution": source_resolution,
            "canonical_render_resolution": f"{render_width}x{render_height}",
            "resolution_mode": self.resolution_mode,
        }

    def _normalize_rgb(self, value: Any, name: str) -> np.ndarray:
        arr = np.asarray(value)
        if arr.ndim != 3 or arr.shape[2] != 3:
            raise ValueError(f"{name} must be an RGB array shaped (H, W, 3), got {arr.shape}")
        if arr.dtype != np.uint8:
            arr = np.clip(arr, 0, 255).astype(np.uint8)
        return np.ascontiguousarray(arr)
