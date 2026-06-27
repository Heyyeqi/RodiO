"""
KoppenProvider — thin adapter exposing Köppen-Geiger climate class from a raster.

Wraps a RasterIndexer whose array contains integer Köppen-Geiger class codes
(1–30 = land climate zones, 0 = no data / ocean). No GDAL dependency.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.signal.raster_indexer import RasterIndexer


class KoppenProvider:
    """
    Adapter for a global Köppen-Geiger raster loaded as a RasterIndexer.

    Args:
        indexer: RasterIndexer wrapping the climate array (values 0–30).
                 Construct with nodata=0 so ocean pixels return None.
    """

    def __init__(self, indexer: "RasterIndexer", resolution_mode: str = "8k") -> None:
        self.resolution_mode = resolution_mode
        self.indexer = _coerce_indexer(indexer, resolution_mode)

    def get_climate(self, lon: float, lat: float) -> Optional[int]:
        """
        Return Köppen-Geiger class integer (1–30) at (lon, lat).

        Returns None for ocean pixels or points with no coverage.
        """
        value = self.indexer.sample(lon, lat)
        if value is None or int(value) <= 0:
            return None
        return int(value)


def _coerce_indexer(indexer, resolution_mode: str):
    if hasattr(indexer, "sample"):
        return indexer
    from core.signal.raster_indexer import RasterIndexer
    return RasterIndexer(indexer, resolution_mode=resolution_mode)
