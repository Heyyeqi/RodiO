"""Copernicus DEM land-refinement adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .dem_interface import GeoTiffDEMAdapter


class CopernicusDEMAdapter(GeoTiffDEMAdapter):
    """Land refinement DEM adapter.

    The source may contain nodata over water. The registry treats valid
    Copernicus values as land refinement before falling back to GEBCO/ETOPO1.
    """

    def __init__(self, path: str | Path):
        super().__init__(path, "CopernicusDEM")

    def validate_alignment(self) -> Dict[str, Any]:
        result = super().validate_alignment()
        meta = self.metadata
        expected_shape = (4096, 8192)
        if meta["shape"] != expected_shape:
            result["issues"].append(f"unexpected_shape_{meta['shape']}")
        if meta["nodata"] != -32768:
            result["issues"].append("unexpected_nodata")
        if abs(meta["pixel_x"] - 0.0439453125) > 1e-12:
            result["issues"].append("unexpected_pixel_x")
        if abs(meta["pixel_y"] - 0.0439453125) > 1e-12:
            result["issues"].append("unexpected_pixel_y")
        result["ok"] = not result["issues"]
        return result
