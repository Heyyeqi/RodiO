"""Tile streaming helpers for high-resolution Earth textures."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass(frozen=True, order=True)
class TextureTile:
    """Tile coordinate in a global equirectangular texture."""

    x: int
    y: int
    lod: str = "16k"


def get_visible_tiles(camera_state) -> list[TextureTile]:
    """Return deterministic tile IDs required by a camera view.

    camera_state accepts either a dict or an object with lon/lat/fov fields.
    The default grid is 4 columns × 2 rows for a 16K texture split into 4K
    tiles.  The view picks the center tile and immediate neighbors based on FOV.
    """
    state = _as_camera_dict(camera_state)
    cols = int(state.get("tile_cols", 4))
    rows = int(state.get("tile_rows", 2))
    lod = str(state.get("lod", "16k"))
    lon = _normalize_lon(float(state.get("lon", 0.0)))
    lat = max(-89.999, min(89.999, float(state.get("lat", 0.0))))
    fov = max(1.0, float(state.get("fov_degrees", state.get("fov", 45.0))))

    center_x = min(cols - 1, max(0, int((lon + 180.0) / 360.0 * cols)))
    center_y = min(rows - 1, max(0, int((90.0 - lat) / 180.0 * rows)))
    radius_x = max(0, int(np.ceil(fov / (360.0 / cols) / 2.0)))
    radius_y = max(0, int(np.ceil(fov / (180.0 / rows) / 2.0)))

    tiles: set[TextureTile] = set()
    for dy in range(-radius_y, radius_y + 1):
        y = center_y + dy
        if y < 0 or y >= rows:
            continue
        for dx in range(-radius_x, radius_x + 1):
            x = (center_x + dx) % cols
            tiles.add(TextureTile(x=x, y=y, lod=lod))
    return sorted(tiles)


class TextureStreamingLayer:
    """Split textures into reusable tile views and maintain an MRU cache."""

    def __init__(
        self,
        tile_size: int = 4096,
        max_cached_tiles: int = 16,
        source_resolution: tuple[int, int] = (16384, 8192),
    ) -> None:
        if tile_size <= 0:
            raise ValueError("tile_size must be positive")
        if max_cached_tiles <= 0:
            raise ValueError("max_cached_tiles must be positive")
        self.tile_size = int(tile_size)
        self.max_cached_tiles = int(max_cached_tiles)
        self.source_resolution = source_resolution
        self.tile_cache: OrderedDict[TextureTile, np.ndarray] = OrderedDict()

    @property
    def tile_grid(self) -> tuple[int, int]:
        width, height = self.source_resolution
        return (
            max(1, int(np.ceil(width / self.tile_size))),
            max(1, int(np.ceil(height / self.tile_size))),
        )

    def split_16k_texture(self, texture: np.ndarray) -> dict[TextureTile, np.ndarray]:
        """Return 4K tile views over a 16K-like texture without copying pixels."""
        arr = _as_texture_array(texture)
        height, width = arr.shape[:2]
        self.source_resolution = (width, height)
        cols, rows = self.tile_grid
        tiles: dict[TextureTile, np.ndarray] = {}
        for y in range(rows):
            for x in range(cols):
                x0 = x * self.tile_size
                y0 = y * self.tile_size
                x1 = min(width, x0 + self.tile_size)
                y1 = min(height, y0 + self.tile_size)
                tiles[TextureTile(x=x, y=y, lod=_lod_for_resolution(width))] = arr[y0:y1, x0:x1]
        return tiles

    def lazy_load_tiles(
        self,
        texture: np.ndarray,
        camera_state,
    ) -> dict[TextureTile, np.ndarray]:
        """Load only visible tiles into the MRU cache and return those views."""
        arr = _as_texture_array(texture)
        height, width = arr.shape[:2]
        self.source_resolution = (width, height)
        cols, rows = self.tile_grid
        state = _as_camera_dict(camera_state)
        state.setdefault("tile_cols", cols)
        state.setdefault("tile_rows", rows)
        state.setdefault("lod", _lod_for_resolution(width))

        visible = get_visible_tiles(state)
        loaded: dict[TextureTile, np.ndarray] = {}
        for tile in visible:
            if tile in self.tile_cache:
                view = self.tile_cache.pop(tile)
            else:
                view = self._tile_view(arr, tile)
            self.tile_cache[tile] = view
            loaded[tile] = view
        self._trim_cache()
        return loaded

    def cache_most_recently_used_tiles(
        self,
        tiles: Iterable[tuple[TextureTile, np.ndarray]],
    ) -> None:
        for tile, view in tiles:
            if tile in self.tile_cache:
                self.tile_cache.pop(tile)
            self.tile_cache[tile] = view
        self._trim_cache()

    def _tile_view(self, arr: np.ndarray, tile: TextureTile) -> np.ndarray:
        height, width = arr.shape[:2]
        x0 = tile.x * self.tile_size
        y0 = tile.y * self.tile_size
        x1 = min(width, x0 + self.tile_size)
        y1 = min(height, y0 + self.tile_size)
        return arr[y0:y1, x0:x1]

    def _trim_cache(self) -> None:
        while len(self.tile_cache) > self.max_cached_tiles:
            self.tile_cache.popitem(last=False)


def _as_camera_dict(camera_state) -> dict:
    if camera_state is None:
        return {}
    if isinstance(camera_state, dict):
        return dict(camera_state)
    return {
        key: getattr(camera_state, key)
        for key in ("lon", "lat", "fov", "fov_degrees", "tile_cols", "tile_rows", "lod")
        if hasattr(camera_state, key)
    }


def _as_texture_array(texture) -> np.ndarray:
    arr = np.asarray(texture)
    if arr.ndim != 3:
        raise ValueError("texture must be an image array shaped (H, W, C)")
    return arr


def _normalize_lon(lon: float) -> float:
    while lon < -180.0:
        lon += 360.0
    while lon >= 180.0:
        lon -= 360.0
    return lon


def _lod_for_resolution(width: int) -> str:
    if width >= 16000:
        return "16k"
    if width >= 8000:
        return "8k"
    if width >= 4000:
        return "4k"
    return f"{width}px"
