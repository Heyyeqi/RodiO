"""Spatial alignment lock for global equirectangular Earth rasters."""

from __future__ import annotations

from dataclasses import dataclass


class SpatialProfile:
    """Named global raster profiles for scale-only transitions."""

    BASE_MODE = "8k"
    RESOLUTIONS = {
        "8k": (8192, 4096),
        "21k": (21600, 10800),
    }

    def get_resolution(self, mode: str = "8k") -> tuple[int, int]:
        """Return (width, height) for a supported resolution mode."""
        if mode not in self.RESOLUTIONS:
            raise ValueError(
                f"Unsupported spatial resolution mode {mode!r}; "
                f"expected one of {sorted(self.RESOLUTIONS)}"
            )
        return self.RESOLUTIONS[mode]

    def scale(self, mode: str = "8k", base_mode: str = BASE_MODE) -> float:
        """Return horizontal resolution scale relative to base_mode."""
        width, _height = self.get_resolution(mode)
        base_width, _base_height = self.get_resolution(base_mode)
        return width / base_width


@dataclass(frozen=True)
class SpatialAlignmentLock:
    """
    Deterministic lon/lat to pixel mapping for global EPSG:4326 rasters.

    base_resolution is the horizontal pixel count. A global equirectangular
    Earth raster uses a 2:1 aspect ratio, so the vertical pixel count defaults
    to base_resolution / 2 (8192×4096, 21600×10800, etc.).
    """

    base_resolution: int = 8192
    height_resolution: int | None = None
    resolution_mode: str | None = None

    @property
    def width(self) -> int:
        if self.resolution_mode is not None:
            return SpatialProfile().get_resolution(self.resolution_mode)[0]
        return int(self.base_resolution)

    @property
    def height(self) -> int:
        if self.resolution_mode is not None:
            return SpatialProfile().get_resolution(self.resolution_mode)[1]
        if self.height_resolution is not None:
            return int(self.height_resolution)
        return max(1, int(self.base_resolution) // 2)

    def normalize(self, lon: float, lat: float) -> tuple[int, int]:
        """Return clamped integer (x, y) pixel coordinates for lon/lat."""
        lon_n = (float(lon) + 180.0) / 360.0
        lat_n = (90.0 - float(lat)) / 180.0

        x = int(lon_n * self.width)
        y = int(lat_n * self.height)

        x = min(self.width - 1, max(0, x))
        y = min(self.height - 1, max(0, y))
        return x, y
