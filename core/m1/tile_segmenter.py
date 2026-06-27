"""
Tile Segmenter

Splits a global geographic grid into TileBBox objects for independent
processing, and stitches per-tile SemanticMaskTile results back into
global-scale numpy arrays.

No image I/O, no RGB output. Pure coordinate geometry + array operations.
"""

import math
from typing import List, Tuple, Optional
import numpy as np

from .mask_types import TileBBox, SemanticMaskTile, BIOME_UNKNOWN


class TileSegmenter:
    """
    Produces tile coordinates for a lon/lat grid and reassembles results.

    Default global grid: 8192 × 4096 pixels covering −180→180 lon, −90→90 lat.
    Default tile size:   1024 × 1024 pixels.

    Tile order: row-major, top-left origin (lat 90 → −90, lon −180 → 180).
    """

    def __init__(
        self,
        global_width: int  = 8192,
        global_height: int = 4096,
        tile_size: int     = 1024,
    ):
        self.global_width  = global_width
        self.global_height = global_height
        self.tile_size     = tile_size

    # ------------------------------------------------------------------
    # Tile coordinate generation
    # ------------------------------------------------------------------

    def split_grid(
        self,
        width: Optional[int]  = None,
        height: Optional[int] = None,
        tile_size: Optional[int] = None,
    ) -> List[TileBBox]:
        """
        Return a list of TileBBox objects covering the global grid.

        Args:
            width, height, tile_size: override instance defaults if provided.

        Returns:
            List of TileBBox in row-major order (top → bottom, left → right).
        """
        w   = width     or self.global_width
        h   = height    or self.global_height
        ts  = tile_size or self.tile_size

        n_cols = math.ceil(w / ts)
        n_rows = math.ceil(h / ts)

        # Degrees per pixel
        deg_per_px_lon = 360.0 / w
        deg_per_px_lat = 180.0 / h

        tiles: List[TileBBox] = []
        for row in range(n_rows):
            for col in range(n_cols):
                px_x0 = col * ts
                px_y0 = row * ts
                px_x1 = min(px_x0 + ts, w)
                px_y1 = min(px_y0 + ts, h)

                lon_min = -180.0 + px_x0 * deg_per_px_lon
                lon_max = -180.0 + px_x1 * deg_per_px_lon
                # y=0 is top (lat=90), y increases downward
                lat_max =  90.0 - px_y0 * deg_per_px_lat
                lat_min =  90.0 - px_y1 * deg_per_px_lat

                tiles.append(TileBBox(
                    lon_min=lon_min, lon_max=lon_max,
                    lat_min=lat_min, lat_max=lat_max,
                    col_idx=col, row_idx=row,
                ))
        return tiles

    def pixel_to_lonlat(self, px: int, py: int, width: int, height: int) -> Tuple[float, float]:
        """Convert pixel coordinates to (lon, lat) at pixel centre."""
        lon = -180.0 + (px + 0.5) * (360.0 / width)
        lat =  90.0  - (py + 0.5) * (180.0 / height)
        return lon, lat

    def tile_lonlat_grid(
        self,
        bbox: TileBBox,
        tile_px_w: int,
        tile_px_h: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Return (lons, lats) meshgrid arrays for a tile at the given pixel resolution.

        Args:
            bbox:       tile geographic bounds
            tile_px_w:  pixel width of this tile
            tile_px_h:  pixel height of this tile

        Returns:
            lons: float32 array (tile_px_h, tile_px_w)
            lats: float32 array (tile_px_h, tile_px_w)
        """
        lons_1d = np.linspace(bbox.lon_min, bbox.lon_max, tile_px_w, dtype=np.float32)
        lats_1d = np.linspace(bbox.lat_max, bbox.lat_min, tile_px_h, dtype=np.float32)
        lons, lats = np.meshgrid(lons_1d, lats_1d)
        return lons, lats

    # ------------------------------------------------------------------
    # Tile stitching
    # ------------------------------------------------------------------

    def stitch_tiles(
        self,
        tiles: List[SemanticMaskTile],
        field: str = "biome_mask",
    ) -> np.ndarray:
        """
        Recombine per-tile mask arrays into a single global array.

        This is a semantic stitch — no RGB, no image blending.
        Gaps between tiles (if any) are filled with BIOME_UNKNOWN / NaN.

        Args:
            tiles: list of SemanticMaskTile from one global pass
            field: which mask field to stitch ("biome_mask", "ocean_mask",
                   "land_mask", "uncertainty_mask", "confidence_mask")

        Returns:
            Global numpy array. Shape derived from tile extents.
        """
        if not tiles:
            raise ValueError("No tiles provided")

        # Infer global shape from tile positions and sizes
        max_row = max(t.bbox.row_idx for t in tiles)
        max_col = max(t.bbox.col_idx for t in tiles)
        tile_h, tile_w = tiles[0].shape

        global_h = (max_row + 1) * tile_h
        global_w = (max_col + 1) * tile_w

        sample = getattr(tiles[0], field)
        if sample.dtype == bool:
            canvas = np.zeros((global_h, global_w), dtype=bool)
        elif sample.dtype == np.uint8:
            canvas = np.full((global_h, global_w), BIOME_UNKNOWN, dtype=np.uint8)
        else:
            canvas = np.full((global_h, global_w), np.nan, dtype=np.float32)

        for tile in tiles:
            r0 = tile.bbox.row_idx * tile_h
            c0 = tile.bbox.col_idx * tile_w
            canvas[r0:r0 + tile_h, c0:c0 + tile_w] = getattr(tile, field)

        return canvas

    def tile_count(
        self,
        width: Optional[int]  = None,
        height: Optional[int] = None,
        tile_size: Optional[int] = None,
    ) -> Tuple[int, int]:
        """Return (n_cols, n_rows) for the given grid parameters."""
        w  = width     or self.global_width
        h  = height    or self.global_height
        ts = tile_size or self.tile_size
        return math.ceil(w / ts), math.ceil(h / ts)
