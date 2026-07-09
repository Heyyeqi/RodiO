"""Deterministic BMNG tile pyramid generation.

This module is CPU-only and writes static WebGL texture tiles into the existing
BMNG source-cache tree served by ``server.js``.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Tuple

import numpy as np
from PIL import Image


Image.MAX_IMAGE_PIXELS = None

LOD_PYRAMID: Dict[str, Tuple[int, int]] = {
    "l0": (21600, 10800),
    "16k": (16384, 8192),
    "8k": (8192, 4096),
    "4k": (4096, 2048),
}

FRONTEND_TILE_SIZE_BY_LOD: Dict[str, int] = {
    "16k": 4096,
    "8k": 4096,
    "4k": 2048,
}


@dataclass(frozen=True)
class TileCoordinateSystem:
    """Global equirectangular tile math for EPSG:4326 BMNG rasters."""

    lod_pyramid: Mapping[str, Tuple[int, int]] = None
    tile_size_by_lod: Mapping[str, int] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "lod_pyramid", self.lod_pyramid or LOD_PYRAMID)
        object.__setattr__(self, "tile_size_by_lod", self.tile_size_by_lod or FRONTEND_TILE_SIZE_BY_LOD)

    def compute_tile_grid(self, lod: str) -> Tuple[int, int]:
        width, height = self._lod_size(lod)
        tile_size = self._tile_size(lod)
        return ceil(width / tile_size), ceil(height / tile_size)

    def lonlat_to_tile(self, lon: float, lat: float, lod: str) -> Tuple[int, int]:
        tiles_x, tiles_y = self.compute_tile_grid(lod)
        lon = min(180.0, max(-180.0, float(lon)))
        lat = min(90.0, max(-90.0, float(lat)))
        x = int((lon + 180.0) / 360.0 * tiles_x)
        y = int((90.0 - lat) / 180.0 * tiles_y)
        return min(tiles_x - 1, max(0, x)), min(tiles_y - 1, max(0, y))

    def tile_to_bounds(self, x: int, y: int, lod: str) -> Tuple[float, float, float, float]:
        tiles_x, tiles_y = self.compute_tile_grid(lod)
        if not (0 <= x < tiles_x and 0 <= y < tiles_y):
            raise ValueError(f"tile ({x}, {y}) outside {lod} grid {tiles_x}x{tiles_y}")
        lon_min = -180.0 + (x / tiles_x) * 360.0
        lon_max = -180.0 + ((x + 1) / tiles_x) * 360.0
        lat_max = 90.0 - (y / tiles_y) * 180.0
        lat_min = 90.0 - ((y + 1) / tiles_y) * 180.0
        return lon_min, lat_min, lon_max, lat_max

    def _lod_size(self, lod: str) -> Tuple[int, int]:
        if lod not in self.lod_pyramid:
            raise ValueError(f"Unknown LOD {lod!r}; expected one of {sorted(self.lod_pyramid)}")
        return self.lod_pyramid[lod]

    def _tile_size(self, lod: str) -> int:
        if lod not in self.tile_size_by_lod:
            raise ValueError(f"No tile size configured for LOD {lod!r}")
        return int(self.tile_size_by_lod[lod])


class EarthTileGenerator:
    """Slice one BMNG source image into deterministic LOD tiles."""

    def __init__(
        self,
        source_image_path: str | Path,
        tile_size: int | Mapping[str, int] = 512,
        output_root: str | Path | None = None,
        lod_pyramid: Mapping[str, Tuple[int, int]] | None = None,
        overwrite: bool = False,
        jpeg_quality: int = 95,
        colorizer: Any | None = None,
        output_tile_dir: str = "tiles",
        dataset: str | None = None,
    ) -> None:
        self.source = Path(source_image_path)
        self.tile_size = tile_size
        self.lod_pyramid = dict(lod_pyramid or LOD_PYRAMID)
        self.tile_size_by_lod = self._normalise_tile_sizes(tile_size)
        self.output_root = Path(output_root) if output_root is not None else self._infer_output_root()
        self.overwrite = bool(overwrite)
        self.jpeg_quality = int(jpeg_quality)
        self.colorizer = colorizer
        self.output_tile_dir = output_tile_dir
        self.dataset = dataset or self._infer_dataset_name()
        self.coordinate_system = TileCoordinateSystem(self.lod_pyramid, self.tile_size_by_lod)

    def load_source(self) -> np.ndarray:
        """Load the source image as an RGB numpy array."""
        with Image.open(self.source) as image:
            return np.asarray(image.convert("RGB"))

    def compute_tile_grid(self, lod: str) -> Tuple[int, int]:
        return self.coordinate_system.compute_tile_grid(lod)

    def slice_tiles(self, lod: str) -> Iterator[Tuple[int, int, Image.Image]]:
        """Yield ``(x, y, image)`` tiles for a concrete render LOD."""
        if lod == "l0":
            raise ValueError("L0 is a logical reference only and is not tiled")
        lod_image = self._build_lod_image(lod)
        tile_size = self.tile_size_by_lod[lod]
        tiles_x, tiles_y = self.compute_tile_grid(lod)
        for y in range(tiles_y):
            for x in range(tiles_x):
                left = x * tile_size
                upper = y * tile_size
                right = min(left + tile_size, lod_image.width)
                lower = min(upper + tile_size, lod_image.height)
                tile = lod_image.crop((left, upper, right, lower))
                if self.colorizer is not None:
                    metadata = self.tile_metadata(lod, x, y)
                    tile_array = np.asarray(tile.convert("RGB"))
                    tile = Image.fromarray(self.colorizer.process_tile(tile_array, metadata), "RGB")
                yield x, y, tile

    def save_tile(self, lod: str, x: int, y: int, image: Image.Image) -> Path:
        """Write one tile to ``tiles/{lod}/tile_{x}_{y}.jpg`` atomically."""
        tile_dir = self.output_root / self.output_tile_dir / lod
        tile_dir.mkdir(parents=True, exist_ok=True)
        tile_path = tile_dir / f"tile_{x}_{y}.jpg"
        if tile_path.exists() and not self.overwrite:
            return tile_path

        tmp_path = tile_path.with_suffix(".jpg.tmp")
        image.convert("RGB").save(
            tmp_path,
            format="JPEG",
            quality=self.jpeg_quality,
            subsampling=0,
            optimize=False,
            progressive=False,
        )
        tmp_path.replace(tile_path)
        return tile_path

    def generate_lod(self, lod: str) -> list[Path]:
        """Generate all tiles for one LOD, safely resuming existing outputs."""
        written: list[Path] = []
        for x, y, tile in self.slice_tiles(lod):
            written.append(self.save_tile(lod, x, y, tile))
        return written

    def expected_tile_paths(self, lod: str) -> list[Path]:
        tiles_x, tiles_y = self.compute_tile_grid(lod)
        return [
            self.output_root / self.output_tile_dir / lod / f"tile_{x}_{y}.jpg"
            for y in range(tiles_y)
            for x in range(tiles_x)
        ]

    def missing_tiles(self, lod: str) -> list[Path]:
        return [path for path in self.expected_tile_paths(lod) if not path.exists()]

    def tile_metadata(self, lod: str, x: int, y: int) -> Dict[str, Any]:
        lon_min, lat_min, lon_max, lat_max = self.coordinate_system.tile_to_bounds(x, y, lod)
        return {
            "dataset": self.dataset,
            "lod": lod,
            "x": x,
            "y": y,
            "bounds": (lon_min, lat_min, lon_max, lat_max),
            "projection": "EPSG:4326",
            "tile_size": self.tile_size_by_lod[lod],
        }

    def _build_lod_image(self, lod: str) -> Image.Image:
        if lod not in self.lod_pyramid:
            raise ValueError(f"Unknown LOD {lod!r}; expected one of {sorted(self.lod_pyramid)}")
        target_size = self.lod_pyramid[lod]
        with Image.open(self.source) as image:
            rgb = image.convert("RGB")
            if rgb.size == target_size:
                return rgb.copy()
            return rgb.resize(target_size, Image.Resampling.LANCZOS)

    def _normalise_tile_sizes(self, tile_size: int | Mapping[str, int]) -> Dict[str, int]:
        if isinstance(tile_size, Mapping):
            return {str(k): int(v) for k, v in tile_size.items()}
        size = int(tile_size)
        return {lod: size for lod in self.lod_pyramid if lod != "l0"}

    def _infer_output_root(self) -> Path:
        for parent in [self.source.parent, *self.source.parents]:
            if parent.name in {"topo_bathy", "base_map"}:
                return parent
        return self.source.parent

    def _infer_dataset_name(self) -> str | None:
        for parent in [self.source.parent, *self.source.parents]:
            if parent.name in {"topo_bathy", "base_map"}:
                return parent.name
        return None
