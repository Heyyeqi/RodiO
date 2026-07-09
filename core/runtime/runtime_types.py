"""Shared runtime data types for in-memory spatial computation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class GridIndex:
    row: int
    col: int


@dataclass(frozen=True)
class GlobalGridLock:
    """RodiO global 8K north-up EPSG:4326 grid lock."""

    width: int = 8192
    height: int = 4096
    origin_x: float = -180.0
    origin_y: float = 90.0
    pixel_x: float = 0.0439453125
    pixel_y: float = 0.0439453125
    crs: str = "EPSG:4326"

    def normalize_lon(self, lon: float) -> float:
        if lon == 180:
            return 179.999999999
        return ((float(lon) + 180.0) % 360.0) - 180.0

    def clamp_lat(self, lat: float) -> float:
        return min(89.999999999, max(-89.999999999, float(lat)))

    def index_for(self, lon: float, lat: float) -> GridIndex:
        norm_lon = self.normalize_lon(lon)
        norm_lat = self.clamp_lat(lat)
        col = int((norm_lon - self.origin_x) / self.pixel_x)
        row = int((self.origin_y - norm_lat) / self.pixel_y)
        return GridIndex(
            row=min(self.height - 1, max(0, row)),
            col=min(self.width - 1, max(0, col)),
        )

    def validate_layer_metadata(self, metadata: Dict[str, object], tolerance: float = 1e-9) -> Dict[str, object]:
        shape = tuple(metadata.get("shape", ()))
        origin_x = float(metadata.get("origin_x", float("nan")))
        origin_y = float(metadata.get("origin_y", float("nan")))
        pixel_x = float(metadata.get("pixel_x", float("nan")))
        pixel_y = float(metadata.get("pixel_y", float("nan")))
        crs = str(metadata.get("crs", ""))
        issues = []
        if shape != (self.height, self.width):
            issues.append(f"shape_mismatch={shape}")
        if abs(origin_x - self.origin_x) > tolerance:
            issues.append(f"origin_x_mismatch={origin_x}")
        if abs(origin_y - self.origin_y) > tolerance:
            issues.append(f"origin_y_mismatch={origin_y}")
        if abs(pixel_x - self.pixel_x) > tolerance:
            issues.append(f"pixel_x_mismatch={pixel_x}")
        if abs(pixel_y - self.pixel_y) > tolerance:
            issues.append(f"pixel_y_mismatch={pixel_y}")
        if crs and crs != self.crs:
            issues.append(f"crs_mismatch={crs}")
        return {"ok": not issues, "issues": issues}


@dataclass(frozen=True)
class FeatureVector:
    elevation: float
    ocean_flag: float
    climate_class: float
    slope_proxy: float

    def as_list(self) -> List[float]:
        return [self.elevation, self.ocean_flag, self.climate_class, self.slope_proxy]


@dataclass(frozen=True)
class SpatialState:
    elevation: float
    ocean: bool
    climate_class: Optional[int]
    biome_proxy: float
    slope_proxy: float
    feature_vector: FeatureVector
    normalized_vector: FeatureVector
    source: Dict[str, object]


@dataclass(frozen=True)
class WindowState:
    bbox: BBox
    sample_count: int
    ocean_fraction: float
    mean_elevation: float
    min_elevation: float
    max_elevation: float
    climate_histogram: Dict[int, int]
    consistency_score: float
