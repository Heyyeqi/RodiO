"""ETOPO1 canonical fallback DEM adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .dem_interface import GeoTiffDEMAdapter


class ETOPO1Adapter(GeoTiffDEMAdapter):
    """Fast global fallback DEM.

    ETOPO1 remains the registry's global fallback truth. This adapter performs
    native-pixel reads only; it never resamples or rewrites the source raster.
    """

    def __init__(self, path: str | Path):
        super().__init__(path, "ETOPO1")

    def validate_alignment(self) -> Dict[str, Any]:
        result = super().validate_alignment()
        meta = self.metadata
        expected_shape = (4096, 8192)
        if meta["shape"] != expected_shape:
            result["issues"].append(f"unexpected_shape_{meta['shape']}")
        if abs(meta["pixel_x"] - 0.0439453125) > 1e-12:
            result["issues"].append("unexpected_pixel_x")
        if abs(meta["pixel_y"] - 0.0439453125) > 1e-12:
            result["issues"].append("unexpected_pixel_y")
        result["ok"] = not result["issues"]
        return result
