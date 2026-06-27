"""
Mask Generator

Generates per-tile SemanticMaskTile arrays by running the full
SAL → D6 Binding → SemanticFieldBuilder pipeline at each grid point.

The caller supplies a SignalProvider callable that returns SAL signal
kwargs for any (lon, lat) coordinate. This keeps MaskGenerator decoupled
from any specific data source.

All output is in-memory numpy. No image export, no GPU, no rendering.
"""

from typing import Optional, Tuple
import numpy as np

from core.sal import SemanticArbitrator
from core.binding import SALD6Bridge, TemporalState
from core.runtime import SpatialProfile
from core.signal.providers.m1_bridge import M1BridgeProvider
from .mask_types import (
    TileBBox, SemanticMaskTile, SignalProvider,
    SEMANTIC_TO_BIOME, BIOME_UNKNOWN,
)
from .tile_segmenter import TileSegmenter
from .semantic_field_builder import SemanticFieldBuilder


def _default_signal_provider(lon: float, lat: float) -> dict:
    """Fallback: everything is ambiguous unknown land."""
    return dict(
        dem_signal="land",      dem_confidence=0.50,
        climate_signal="land",  climate_confidence=0.50,
        ocean_signal="land",    ocean_confidence=0.50,
        landcover_signal="land", landcover_confidence=0.50,
    )


class MaskGenerator:
    """
    Generates SemanticMaskTile objects for geographic tiles.

    Args:
        sal:             SemanticArbitrator instance
        runtime:         reserved for M0 integration (unused)
        signal_provider: callable(lon, lat) → dict of SAL signal kwargs
        temporal:        TemporalState for seasonal/diurnal modulation
        tile_px_size:    pixel resolution per tile dimension
    """

    def __init__(
        self,
        sal: Optional[SemanticArbitrator] = None,
        runtime=None,
        signal_provider: Optional[SignalProvider] = None,
        temporal: Optional[TemporalState] = None,
        tile_px_size: int = 16,
        resolution_mode: str = "8k",
    ):
        self._sal      = sal or SemanticArbitrator()
        self._runtime  = runtime
        self._bridge   = SALD6Bridge(sal=self._sal)
        self._provider = signal_provider or (
            M1BridgeProvider(runtime) if runtime is not None else _default_signal_provider
        )
        self._temporal = temporal or TemporalState(month=6, hour=12, lat=0.0)
        self._tile_px  = tile_px_size
        self.resolution_mode = resolution_mode
        self._segmenter = TileSegmenter()
        self._field_builder = SemanticFieldBuilder()

    def set_resolution(self, mode: str) -> None:
        """Set resolution profile for future mask sampling metadata."""
        SpatialProfile().get_resolution(mode)
        self.resolution_mode = mode

    def full_resolution_shape(self) -> tuple[int, int]:
        """Return full global raster shape (rows, cols) for this profile."""
        width, height = SpatialProfile().get_resolution(self.resolution_mode)
        return height, width

    def visual_tile_px_size(self) -> int:
        """
        Return profile-scaled tile sample size for visual previews.

        This is intentionally a recommendation. generate_tile_mask() still uses
        the configured tile_px_size so callers never allocate a full 21K tile
        by accident.
        """
        scale = SpatialProfile().scale(self.resolution_mode)
        return max(1, int(round(self._tile_px * scale)))

    def generate_mask(
        self,
        lon_range: Tuple[float, float],
        lat_range: Tuple[float, float],
        resolution: Optional[int] = None,
    ) -> SemanticMaskTile:
        """
        Generate a semantic mask for a rectangular geographic region.

        Args:
            lon_range: (lon_min, lon_max) in degrees
            lat_range: (lat_min, lat_max) in degrees
            resolution: number of sample points per axis;
                        defaults to self._tile_px

        Returns:
            SemanticMaskTile with ocean/land/biome/uncertainty arrays.
        """
        res = resolution or self._tile_px
        bbox = TileBBox(
            lon_min=lon_range[0], lon_max=lon_range[1],
            lat_min=lat_range[0], lat_max=lat_range[1],
        )
        return self._generate_tile(bbox, tile_px_w=res, tile_px_h=res)

    def generate_tile_mask(self, bbox: TileBBox) -> SemanticMaskTile:
        """Generate a mask for a pre-defined TileBBox at default resolution."""
        return self._generate_tile(bbox, self._tile_px, self._tile_px)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _generate_tile(
        self,
        bbox: TileBBox,
        tile_px_w: int,
        tile_px_h: int,
    ) -> SemanticMaskTile:
        lons, lats = self._segmenter.tile_lonlat_grid(bbox, tile_px_w, tile_px_h)

        ocean_mask       = np.zeros((tile_px_h, tile_px_w), dtype=bool)
        land_mask        = np.zeros((tile_px_h, tile_px_w), dtype=bool)
        biome_mask       = np.full((tile_px_h, tile_px_w), BIOME_UNKNOWN, dtype=np.uint8)
        uncertainty_mask = np.zeros((tile_px_h, tile_px_w), dtype=np.float32)
        confidence_mask  = np.zeros((tile_px_h, tile_px_w), dtype=np.float32)
        ocean_prob_mask  = np.zeros((tile_px_h, tile_px_w), dtype=np.float32)

        for row in range(tile_px_h):
            for col in range(tile_px_w):
                lon = float(lons[row, col])
                lat = float(lats[row, col])

                # Fetch signals from provider
                signals = self._provider(lon, lat)

                # Temporal state with correct latitude
                t = TemporalState(
                    month=self._temporal.month,
                    hour=self._temporal.hour,
                    lat=lat,
                    climate_zone=self._temporal.climate_zone,
                    snow_cover=self._temporal.snow_cover,
                    cloud_cover=self._temporal.cloud_cover,
                )

                # Run SAL once, then reuse the result for D6 binding and M1 fields.
                sal_result = self._sal.resolve(
                    dem_signal=signals.get("dem_signal"),
                    dem_confidence=signals.get("dem_confidence", 1.0),
                    climate_signal=signals.get("climate_signal"),
                    climate_confidence=signals.get("climate_confidence", 1.0),
                    ocean_signal=signals.get("ocean_signal"),
                    ocean_confidence=signals.get("ocean_confidence", 1.0),
                    landcover_signal=signals.get("landcover_signal"),
                    landcover_confidence=signals.get("landcover_confidence", 1.0),
                )
                d6 = self._bridge.convert_from_sal_result(sal_result, time_state=t)

                # Field values
                fields = self._field_builder.build(sal_result, d6)
                pts    = self._field_builder.fields_to_point_masks(fields)

                ocean_mask[row, col]       = pts["ocean_mask"]
                land_mask[row, col]        = pts["land_mask"]
                biome_mask[row, col]       = pts["biome_code"]
                uncertainty_mask[row, col] = pts["uncertainty"]
                confidence_mask[row, col]  = pts["confidence"]
                ocean_prob_mask[row, col]  = pts["ocean_prob"]

        return SemanticMaskTile(
            bbox=bbox,
            ocean_mask=ocean_mask,
            land_mask=land_mask,
            biome_mask=biome_mask,
            uncertainty_mask=uncertainty_mask,
            confidence_mask=confidence_mask,
            ocean_prob_mask=ocean_prob_mask,
        )
