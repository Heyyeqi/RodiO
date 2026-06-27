"""
M1 Pipeline — Integration Layer

Orchestrates the full SAL → D6 Binding → Mask Generation pipeline
across a tile grid. Provides both single-tile and global-grid entry points.

run_tile()   : process one TileBBox and return a SemanticMaskTile
run_global() : iterate all tiles in the 8K grid, return GlobalMaskSummary

No image I/O, no GPU, no modification of SAL or D6.
"""

from typing import Optional, List, Callable
import numpy as np

from core.sal import SemanticArbitrator
from core.binding import SALD6Bridge, TemporalState
from core.runtime import SpatialProfile
from core.signal.providers.m1_bridge import M1BridgeProvider
from .mask_types import (
    TileBBox, SemanticMaskTile, GlobalMaskSummary, SignalProvider,
)
from .mask_generator import MaskGenerator
from .tile_segmenter import TileSegmenter


class M1Pipeline:
    """
    Full M1 semantic mask pipeline.

    Args:
        sal:             SemanticArbitrator (shared across tiles)
        d6:              SALD6Bridge (optional; MaskGenerator creates its own
                         if not provided — kept for API symmetry)
        runtime:         M0 spatial runtime (reserved for future integration)
        signal_provider: callable(lon, lat) → SAL signal dict
        temporal:        TemporalState for season/time modulation
        tile_px_size:    pixel resolution per tile axis (default 16 for tests)
        global_width:    total grid width in pixels (default 8192)
        global_height:   total grid height in pixels (default 4096)
        global_tile_size: tile size in pixels for global run (default 1024)
        on_tile_done:    optional callback(tile_idx, total, mask_tile) for progress
    """

    def __init__(
        self,
        sal: Optional[SemanticArbitrator]   = None,
        d6:  Optional[SALD6Bridge]          = None,
        runtime                             = None,
        signal_provider: Optional[SignalProvider] = None,
        temporal: Optional[TemporalState]   = None,
        tile_px_size: int                   = 16,
        global_width: int                   = 8192,
        global_height: int                  = 4096,
        global_tile_size: int               = 1024,
        resolution_mode: Optional[str]      = None,
        on_tile_done: Optional[Callable]    = None,
    ):
        self._sal      = sal or SemanticArbitrator()
        self._runtime  = runtime
        self._temporal = temporal or TemporalState(month=6, hour=12, lat=0.0)
        self._provider = signal_provider or (
            M1BridgeProvider(runtime) if runtime is not None else None
        )
        self._tile_px  = tile_px_size
        self._on_done  = on_tile_done
        self.resolution_mode = resolution_mode or getattr(runtime, "resolution_mode", "8k")
        profile_w, profile_h = SpatialProfile().get_resolution(self.resolution_mode)
        if resolution_mode is not None and global_width == 8192 and global_height == 4096:
            global_width, global_height = profile_w, profile_h

        self._segmenter = TileSegmenter(
            global_width=global_width,
            global_height=global_height,
            tile_size=global_tile_size,
        )
        self._generator = MaskGenerator(
            sal=self._sal,
            runtime=runtime,
            signal_provider=self._provider,
            temporal=self._temporal,
            tile_px_size=tile_px_size,
            resolution_mode=self.resolution_mode,
        )

    def set_resolution(self, mode: str) -> None:
        """Set resolution mode for future global segmentation and mask metadata."""
        width, height = SpatialProfile().get_resolution(mode)
        self.resolution_mode = mode
        self._segmenter.global_width = width
        self._segmenter.global_height = height
        self._generator.set_resolution(mode)

    def full_resolution_shape(self) -> tuple[int, int]:
        """Return full global raster shape (rows, cols) for this profile."""
        width, height = SpatialProfile().get_resolution(self.resolution_mode)
        return height, width

    def visual_tile_px_size(self) -> int:
        """Return profile-scaled tile sample size for visual previews."""
        return self._generator.visual_tile_px_size()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_tile(self, tile_bbox: TileBBox) -> SemanticMaskTile:
        """
        Run the full pipeline for a single tile.

        Pipeline steps:
            1. Enumerate (lon, lat) grid points inside tile_bbox
            2. Call SAL.resolve() at each point via signal_provider
            3. Call D6Bridge.convert() to get visual context
            4. Populate SemanticMaskTile arrays

        Args:
            tile_bbox: geographic bounds and grid position of the tile

        Returns:
            SemanticMaskTile with all mask arrays populated.
        """
        return self._generator.generate_tile_mask(tile_bbox)

    def run_global(self, dry_run: bool = False) -> GlobalMaskSummary:
        """
        Iterate all tiles in the configured global grid.

        Args:
            dry_run: if True, enumerate tiles but do not actually generate
                     masks (useful for validating tile coverage without
                     running inference). Returns a summary with zero stats.

        Returns:
            GlobalMaskSummary with aggregate statistics.
        """
        all_tiles = self._segmenter.split_grid()
        n_tiles   = len(all_tiles)

        completed: List[SemanticMaskTile] = []
        tile_summaries = []

        for idx, bbox in enumerate(all_tiles):
            if dry_run:
                tile_summaries.append({
                    "tile_idx": idx,
                    "bbox": repr(bbox),
                    "status": "skipped (dry_run)",
                })
                continue

            mask = self.run_tile(bbox)
            completed.append(mask)

            summary = {
                "tile_idx":         idx,
                "bbox":             repr(bbox),
                "ocean_fraction":   mask.ocean_fraction(),
                "land_fraction":    mask.land_fraction(),
                "mean_uncertainty": mask.mean_uncertainty(),
                "mean_confidence":  mask.mean_confidence(),
            }
            tile_summaries.append(summary)

            if self._on_done:
                self._on_done(idx, n_tiles, mask)

        if not completed:
            return GlobalMaskSummary(
                total_tiles=n_tiles,
                completed_tiles=0,
                global_ocean_fraction=0.0,
                global_land_fraction=0.0,
                mean_uncertainty=0.0,
                tile_summaries=tile_summaries,
            )

        ocean_fracs = [t.ocean_fraction() for t in completed]
        land_fracs  = [t.land_fraction()  for t in completed]
        unc_means   = [t.mean_uncertainty() for t in completed]

        return GlobalMaskSummary(
            total_tiles=n_tiles,
            completed_tiles=len(completed),
            global_ocean_fraction=float(np.mean(ocean_fracs)),
            global_land_fraction=float(np.mean(land_fracs)),
            mean_uncertainty=float(np.mean(unc_means)),
            tile_summaries=tile_summaries,
        )

    def stitch(
        self,
        tiles: List[SemanticMaskTile],
        field: str = "biome_mask",
    ) -> np.ndarray:
        """Convenience: stitch a list of completed tiles into a global array."""
        return self._segmenter.stitch_tiles(tiles, field=field)
