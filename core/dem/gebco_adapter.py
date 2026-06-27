"""GEBCO bathymetry adapter backed by native tiles."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import tifffile as tiff

from .dem_interface import BBox, DEMInterface, DEMWindow, GeoTiffDEMAdapter


_GEBCO_TILE_RE = re.compile(
    r"gebco_\d+_sub_ice_n(?P<north>-?\d+(?:\.\d+)?)"
    r"_s(?P<south>-?\d+(?:\.\d+)?)"
    r"_w(?P<west>-?\d+(?:\.\d+)?)"
    r"_e(?P<east>-?\d+(?:\.\d+)?)_geotiff\.tif$"
)


@dataclass
class GEBCOTile:
    path: Path
    west: float
    south: float
    east: float
    north: float
    shape: Tuple[int, int]
    dtype: str
    pixel_x: float
    pixel_y: float
    origin_x: float
    origin_y: float
    nodata: Optional[int]
    crs: str = "EPSG:4326"

    @property
    def bbox(self) -> BBox:
        return (self.west, self.south, self.east, self.north)


class GEBCOAdapter(DEMInterface):
    """Lazy GEBCO adapter.

    Supports extracted tile directories, valid archives, and NetCDF placeholders.
    Tile directories are the preferred mode because they support native tile
    mapping without a global merge.
    """

    def __init__(self, source_path: str | Path):
        self.source_path = Path(source_path)
        if not self.source_path.exists():
            raise FileNotFoundError(self.source_path)
        self.source_type = self.detect_source_type()
        self._tiles: Optional[List[GEBCOTile]] = None
        self._arrays: Dict[Path, np.ndarray] = {}

    def detect_source_type(self) -> str:
        if self.source_path.is_dir():
            if list(self.source_path.glob("gebco_*_sub_ice_*_geotiff.tif")):
                return "tiles"
            return "directory"
        suffix = self.source_path.suffix.lower()
        if suffix == ".nc":
            return "netcdf"
        if suffix == ".zip":
            try:
                with zipfile.ZipFile(self.source_path) as zf:
                    names = zf.namelist()
                if any(name.endswith(".tif") for name in names):
                    return "archive"
                if any(name.endswith(".nc") for name in names):
                    return "netcdf_archive"
                return "archive"
            except zipfile.BadZipFile:
                return "invalid_archive"
        if suffix in {".tif", ".tiff"}:
            return "single_tiff"
        return "unknown"

    @property
    def tiles(self) -> List[GEBCOTile]:
        if self.source_type != "tiles":
            raise NotImplementedError(f"GEBCO source type {self.source_type!r} is not tile-backed")
        if self._tiles is None:
            self._tiles = [self._read_tile_metadata(path) for path in sorted(self.source_path.glob("*.tif"))]
        return self._tiles

    def _read_tile_metadata(self, path: Path) -> GEBCOTile:
        match = _GEBCO_TILE_RE.match(path.name)
        if not match:
            raise ValueError(f"Unrecognized GEBCO tile name: {path.name}")
        bounds = {key: float(value) for key, value in match.groupdict().items()}
        with tiff.TiffFile(str(path)) as tf:
            page = tf.pages[0]
            scale = page.tags["ModelPixelScaleTag"].value
            tiepoint = page.tags["ModelTiepointTag"].value
            nodata_tag = page.tags.get("GDAL_NODATA")
            nodata = int(float(nodata_tag.value)) if nodata_tag else None
            return GEBCOTile(
                path=path,
                west=bounds["west"],
                south=bounds["south"],
                east=bounds["east"],
                north=bounds["north"],
                shape=tuple(int(v) for v in page.shape),
                dtype=str(page.dtype),
                pixel_x=float(scale[0]),
                pixel_y=float(scale[1]),
                origin_x=float(tiepoint[3]),
                origin_y=float(tiepoint[4]),
                nodata=nodata,
            )

    def _array_for_tile(self, tile: GEBCOTile) -> np.ndarray:
        if tile.path not in self._arrays:
            with tiff.TiffFile(str(tile.path)) as tf:
                page = tf.pages[0]
                self._arrays[tile.path] = tiff.memmap(str(tile.path)) if page.is_memmappable else page.asarray()
        return self._arrays[tile.path]

    def _tile_for_coordinate(self, lon: float, lat: float) -> GEBCOTile:
        norm_lon = GeoTiffDEMAdapter.normalize_lon(lon)
        norm_lat = GeoTiffDEMAdapter.clamp_lat(lat)
        for tile in self.tiles:
            lon_in = tile.west <= norm_lon < tile.east or (tile.east == 180.0 and norm_lon <= tile.east)
            lat_in = tile.south <= norm_lat < tile.north or (tile.north == 90.0 and norm_lat <= tile.north)
            if lon_in and lat_in:
                return tile
        raise ValueError(f"No GEBCO tile covers lon={lon}, lat={lat}")

    def _row_col(self, tile: GEBCOTile, lon: float, lat: float) -> Tuple[int, int]:
        norm_lon = GeoTiffDEMAdapter.normalize_lon(lon)
        norm_lat = GeoTiffDEMAdapter.clamp_lat(lat)
        rows, cols = tile.shape
        col = int(np.floor((norm_lon - tile.origin_x) / tile.pixel_x))
        row = int(np.floor((tile.origin_y - norm_lat) / tile.pixel_y))
        return min(rows - 1, max(0, row)), min(cols - 1, max(0, col))

    def get_value(self, lon: float, lat: float) -> Optional[int]:
        tile = self._tile_for_coordinate(lon, lat)
        row, col = self._row_col(tile, lon, lat)
        value = int(self._array_for_tile(tile)[row, col])
        if value == tile.nodata:
            return None
        return value

    def get_window(self, bbox: BBox) -> List[DEMWindow]:
        west, south, east, north = bbox
        if east <= west or north <= south:
            raise ValueError("bbox must be (west, south, east, north)")
        windows: List[DEMWindow] = []
        for tile in self.tiles:
            overlap_w = max(west, tile.west)
            overlap_e = min(east, tile.east)
            overlap_s = max(south, tile.south)
            overlap_n = min(north, tile.north)
            if overlap_w >= overlap_e or overlap_s >= overlap_n:
                continue
            r0, c0 = self._row_col(tile, overlap_w, overlap_n)
            r1, c1 = self._row_col(tile, overlap_e, overlap_s)
            row_range = (min(r0, r1), max(r0, r1) + 1)
            col_range = (min(c0, c1), max(c0, c1) + 1)
            data = self._array_for_tile(tile)[row_range[0] : row_range[1], col_range[0] : col_range[1]]
            windows.append(DEMWindow(str(tile.path), (overlap_w, overlap_s, overlap_e, overlap_n), row_range, col_range, data))
        return windows

    def get_stats(self) -> Dict[str, Any]:
        if self.source_type != "tiles":
            return {"source_type": self.source_type, "path": str(self.source_path)}
        tiles = self.tiles
        return {
            "source_type": self.source_type,
            "path": str(self.source_path),
            "tile_count": len(tiles),
            "nodata": sorted({tile.nodata for tile in tiles}),
            "dtype": sorted({tile.dtype for tile in tiles}),
            "coverage": _tile_coverage(tiles),
            "native_tile_shape": sorted({tile.shape for tile in tiles}),
        }

    def get_crs(self) -> str:
        return "EPSG:4326"

    def validate_tiles(self) -> Dict[str, Any]:
        if self.source_type != "tiles":
            return {
                "ok": False,
                "source_type": self.source_type,
                "issues": ["source_not_tile_directory"],
            }
        tiles = self.tiles
        expected_bounds = {
            (-180.0, 0.0, -90.0, 90.0),
            (-90.0, 0.0, 0.0, 90.0),
            (0.0, 0.0, 90.0, 90.0),
            (90.0, 0.0, 180.0, 90.0),
            (-180.0, -90.0, -90.0, 0.0),
            (-90.0, -90.0, 0.0, 0.0),
            (0.0, -90.0, 90.0, 0.0),
            (90.0, -90.0, 180.0, 0.0),
        }
        actual_bounds = {(tile.west, tile.south, tile.east, tile.north) for tile in tiles}
        issues = []
        missing = sorted(expected_bounds - actual_bounds)
        extra = sorted(actual_bounds - expected_bounds)
        if missing:
            issues.append(f"missing_tiles={missing}")
        if extra:
            issues.append(f"unexpected_tiles={extra}")
        if {tile.crs for tile in tiles} != {"EPSG:4326"}:
            issues.append("crs_inconsistent")
        if {tile.shape for tile in tiles} != {(21600, 21600)}:
            issues.append("shape_inconsistent")
        if {tile.dtype for tile in tiles} != {"int16"}:
            issues.append("dtype_inconsistent")
        if {round(tile.pixel_x, 12) for tile in tiles} != {round(1 / 240, 12)}:
            issues.append("pixel_x_inconsistent")
        if {round(tile.pixel_y, 12) for tile in tiles} != {round(1 / 240, 12)}:
            issues.append("pixel_y_inconsistent")
        for tile in tiles:
            if abs(tile.origin_x - tile.west) > 1e-9 or abs(tile.origin_y - tile.north) > 1e-9:
                issues.append(f"origin_mismatch={tile.path.name}")
        return {
            "ok": not issues,
            "issues": issues,
            "source_type": self.source_type,
            "tile_count": len(tiles),
            "missing_tiles": missing,
            "extra_tiles": extra,
            "coverage": _tile_coverage(tiles),
        }

    def validate_alignment(self) -> Dict[str, Any]:
        return self.validate_tiles()


def _tile_coverage(tiles: List[GEBCOTile]) -> BBox:
    return (
        min(tile.west for tile in tiles),
        min(tile.south for tile in tiles),
        max(tile.east for tile in tiles),
        max(tile.north for tile in tiles),
    )
