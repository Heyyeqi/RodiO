"""
RasterIndexer — lightweight lat/lon → pixel value lookup for global equirectangular arrays.

For full GeoTIFF files with embedded metadata, use GeoTiffDEMAdapter instead.
RasterIndexer is intended for any numpy array that is known to be a global
EPSG:4326 equirectangular grid (covering the full extent -180/+180, -90/+90).

Formula (equirectangular assumption):
    SpatialAlignmentLock(width, height).normalize(lon, lat)

Constraints:
    - No GDAL dependency
    - Lazy load: the array is not read until the first sample() call
    - Thread-safety: not guaranteed; use one instance per thread if needed
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from core.runtime.spatial_alignment import SpatialAlignmentLock, SpatialProfile


class RasterIndexer:
    """
    Nearest-neighbour sampler for a global equirectangular raster.

    Args:
        dataset_path: path to a GeoTIFF or any format readable by numpy/tifffile.
                      Pass None to construct with a pre-loaded array (use from_array).
        nodata:       value to treat as missing data; returned as None on match.
    """

    def __init__(
        self,
        dataset_path: str | Path,
        nodata: Optional[int] = None,
        resolution: int = 8192,
        resolution_mode: str = "8k",
    ) -> None:
        self.dataset_path = Path(dataset_path)
        self.nodata = nodata
        self.resolution_mode = resolution_mode
        self.resolution = _resolve_width(resolution=resolution, resolution_mode=resolution_mode)
        self._array: Optional[np.ndarray] = None

    @classmethod
    def from_array(
        cls,
        array: np.ndarray,
        nodata: Optional[int] = None,
        resolution: Optional[int] = None,
        resolution_mode: Optional[str] = None,
    ) -> "RasterIndexer":
        """Construct directly from an in-memory array (no file I/O)."""
        instance = cls.__new__(cls)
        instance.dataset_path = None
        instance.nodata = nodata
        instance.resolution_mode = resolution_mode
        instance.resolution = _resolve_width(
            resolution=resolution or array.shape[1],
            resolution_mode=resolution_mode,
        )
        instance._array = array
        return instance

    def _load(self) -> np.ndarray:
        if self._array is None:
            import tifffile as tiff
            self._array = tiff.imread(str(self.dataset_path))
        return self._array

    @property
    def shape(self):
        return self._load().shape

    def sample(self, lon: float, lat: float) -> Optional[int]:
        """
        Return the raster value at (lon, lat), or None for nodata / out-of-range.

        Coordinates outside [-180, 180] × [-90, 90] are clamped to the array edge.
        """
        arr = self._load()
        height, width = arr.shape[:2]

        lock = SpatialAlignmentLock(
            base_resolution=self.resolution,
            height_resolution=height if width == self.resolution else None,
            resolution_mode=self.resolution_mode,
        )
        col, row = lock.normalize(lon, lat)

        if width != self.resolution:
            col = int(col / max(1, self.resolution - 1) * (width - 1))
            row = int(row / max(1, lock.height - 1) * (height - 1))

        value = int(arr[row, col])
        if self.nodata is not None and value == self.nodata:
            return None
        return value


def _resolve_width(resolution: int, resolution_mode: Optional[str]) -> int:
    if resolution_mode is None:
        return int(resolution)
    width, _height = SpatialProfile().get_resolution(resolution_mode)
    return int(width)
