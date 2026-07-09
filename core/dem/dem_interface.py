"""Shared abstractions for lazy DEM access.

This module intentionally does not resample, merge, or generate masks. It only
normalizes coordinates, maps them to native raster pixels, and reads the minimum
native raster region needed for a query.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import numpy as np
import tifffile as tiff


BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class DEMWindow:
    """A native-raster window returned by an adapter."""

    source: str
    bbox: BBox
    row_range: Tuple[int, int]
    col_range: Tuple[int, int]
    data: np.ndarray


class DEMInterface:
    """Uniform interface for DEM/bathymetry sources."""

    def get_value(self, lon: float, lat: float) -> Optional[int]:
        """Return elevation/depth at coordinate, or None for nodata/out of bounds."""

        raise NotImplementedError

    def get_window(self, bbox: BBox) -> Any:
        """Lazy fetch native raster region for bbox=(west, south, east, north)."""

        raise NotImplementedError

    def get_stats(self) -> Dict[str, Any]:
        """Return min/max, nodata, coverage, and source metadata."""

        raise NotImplementedError

    def get_crs(self) -> str:
        """Return CRS identifier. RodiO DEM adapters must expose EPSG:4326."""

        raise NotImplementedError

    def validate_alignment(self) -> Dict[str, Any]:
        """Check internal source consistency."""

        raise NotImplementedError


class GeoTiffDEMAdapter(DEMInterface):
    """Base adapter for one north-up EPSG:4326 GeoTIFF."""

    def __init__(self, path: str | Path, name: str):
        self.path = Path(path)
        self.name = name
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        self._metadata: Optional[Dict[str, Any]] = None
        self._array: Optional[np.ndarray] = None

    @staticmethod
    def normalize_lon(lon: float) -> float:
        """Normalize longitude into [-180, 180), keeping 180 addressable."""

        if lon == 180:
            return 179.999999999
        return ((float(lon) + 180.0) % 360.0) - 180.0

    @staticmethod
    def clamp_lat(lat: float) -> float:
        """Clamp latitude into the addressable north-up raster extent."""

        return min(89.999999999, max(-89.999999999, float(lat)))

    @property
    def metadata(self) -> Dict[str, Any]:
        if self._metadata is None:
            with tiff.TiffFile(str(self.path)) as tf:
                page = tf.pages[0]
                scale = page.tags.get("ModelPixelScaleTag")
                tiepoint = page.tags.get("ModelTiepointTag")
                nodata = page.tags.get("GDAL_NODATA")
                compression = page.tags.get("Compression")
                if scale is None or tiepoint is None:
                    raise ValueError(f"{self.path} is missing GeoTIFF scale/tiepoint tags")
                tie = tuple(float(v) for v in tiepoint.value)
                sc = tuple(float(v) for v in scale.value)
                self._metadata = {
                    "path": str(self.path),
                    "shape": tuple(int(v) for v in page.shape),
                    "dtype": str(page.dtype),
                    "origin_x": tie[3],
                    "origin_y": tie[4],
                    "pixel_x": sc[0],
                    "pixel_y": sc[1],
                    "nodata": _parse_nodata(nodata.value if nodata else None),
                    "compression": compression.value if compression else None,
                    "is_memmappable": bool(page.is_memmappable),
                    "coverage": _coverage_from_metadata(page.shape, tie[3], tie[4], sc[0], sc[1]),
                    "crs": "EPSG:4326",
                }
        return self._metadata

    def get_crs(self) -> str:
        return self.metadata["crs"]

    def _load_array(self) -> np.ndarray:
        if self._array is None:
            with tiff.TiffFile(str(self.path)) as tf:
                page = tf.pages[0]
                if page.is_memmappable:
                    self._array = tiff.memmap(str(self.path))
                else:
                    self._array = page.asarray()
        return self._array

    def _row_col(self, lon: float, lat: float) -> Tuple[int, int]:
        meta = self.metadata
        norm_lon = self.normalize_lon(lon)
        norm_lat = self.clamp_lat(lat)
        rows, cols = meta["shape"]
        col = int(np.floor((norm_lon - meta["origin_x"]) / meta["pixel_x"]))
        row = int(np.floor((meta["origin_y"] - norm_lat) / meta["pixel_y"]))
        return min(rows - 1, max(0, row)), min(cols - 1, max(0, col))

    def get_value(self, lon: float, lat: float) -> Optional[int]:
        row, col = self._row_col(lon, lat)
        value = int(self._load_array()[row, col])
        if value == self.metadata["nodata"]:
            return None
        return value

    def get_window(self, bbox: BBox) -> DEMWindow:
        west, south, east, north = bbox
        if east <= west or north <= south:
            raise ValueError("bbox must be (west, south, east, north)")
        r0, c0 = self._row_col(west, north)
        r1, c1 = self._row_col(east, south)
        rows, cols = self.metadata["shape"]
        row_range = (max(0, min(r0, r1)), min(rows, max(r0, r1) + 1))
        col_range = (max(0, min(c0, c1)), min(cols, max(c0, c1) + 1))
        data = self._load_array()[row_range[0] : row_range[1], col_range[0] : col_range[1]]
        return DEMWindow(str(self.path), bbox, row_range, col_range, data)

    def get_stats(self) -> Dict[str, Any]:
        meta = dict(self.metadata)
        arr = self._load_array()
        nodata = meta["nodata"]
        if nodata is None:
            valid = arr
        else:
            valid = arr[arr != nodata]
        meta.update(
            {
                "min": int(valid.min()) if valid.size else None,
                "max": int(valid.max()) if valid.size else None,
                "valid_pixels": int(valid.size),
                "total_pixels": int(arr.size),
            }
        )
        return meta

    def validate_alignment(self) -> Dict[str, Any]:
        meta = self.metadata
        west, south, east, north = meta["coverage"]
        issues = []
        if self.get_crs() != "EPSG:4326":
            issues.append("crs_not_epsg4326")
        if not _close(west, -180.0) or not _close(east, 180.0):
            issues.append("longitude_coverage_not_global")
        if not _close(north, 90.0, 0.01) or not _close(south, -90.0, 0.01):
            issues.append("latitude_coverage_not_global")
        return {
            "adapter": self.name,
            "ok": not issues,
            "issues": issues,
            "metadata": meta,
        }


class DEMRegistry:
    """Priority glue layer for canonical RodiO DEM access.

    Priority rule:
    land -> Copernicus, ocean -> GEBCO, fallback -> ETOPO1.
    Without a mask, land/ocean routing is inferred from native source validity:
    a valid Copernicus value is treated as land refinement; a negative GEBCO
    value is treated as ocean bathymetry; ETOPO1 is always the fallback truth.
    """

    def __init__(
        self,
        primary: DEMInterface,
        ocean: Optional[DEMInterface] = None,
        land: Optional[DEMInterface] = None,
    ):
        self.primary = primary
        self.ocean = ocean
        self.land = land

    @classmethod
    def from_source_cache(cls, source_cache_root: str | Path) -> "DEMRegistry":
        """Build the canonical RodiO DEM registry from the existing source cache."""

        from .copernicus_adapter import CopernicusDEMAdapter
        from .etopo_adapter import ETOPO1Adapter
        from .gebco_adapter import GEBCOAdapter

        root = Path(source_cache_root)
        return cls(
            primary=ETOPO1Adapter(root / "exported_8k/etopo1_bedrock_8192x4096.tif"),
            ocean=GEBCOAdapter(root / "external_raw/gebco/gebco_2026_sub_ice_topo_geotiff"),
            land=CopernicusDEMAdapter(root / "exported_8k/copernicus_dem_glo30_elevation_8192x4096.tif"),
        )

    def query(self, lon: float, lat: float) -> Optional[int]:
        if self.land is not None:
            value = self.land.get_value(lon, lat)
            # Only treat as land when Copernicus returns a strictly positive value.
            # Zero is ambiguous (nearshore fill or true sea-level coast); negative
            # values mean the source has no valid land reading at this pixel.
            # Both cases fall through to GEBCO bathymetry.
            if value is not None and value > 0:
                return value
        if self.ocean is not None:
            value = self.ocean.get_value(lon, lat)
            if value is not None and value < 0:
                return value
        return self.primary.get_value(lon, lat)

    def validate(self) -> Dict[str, Any]:
        adapters = {
            "primary": self.primary,
            "ocean": self.ocean,
            "land": self.land,
        }
        results = {
            role: adapter.validate_alignment()
            for role, adapter in adapters.items()
            if adapter is not None
        }
        return {
            "ok": all(result["ok"] for result in results.values()),
            "priority": "land -> Copernicus, ocean -> GEBCO, fallback -> ETOPO1",
            "adapters": results,
        }


def _coverage_from_metadata(
    shape: Iterable[int], origin_x: float, origin_y: float, pixel_x: float, pixel_y: float
) -> BBox:
    rows, cols = tuple(shape)
    west = origin_x
    east = origin_x + cols * pixel_x
    north = origin_y
    south = origin_y - rows * pixel_y
    return (west, south, east, north)


def _parse_nodata(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _close(a: float, b: float, tolerance: float = 1e-6) -> bool:
    return abs(float(a) - float(b)) <= tolerance
