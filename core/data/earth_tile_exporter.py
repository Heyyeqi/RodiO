"""Batch exporter for the BMNG Earth tile pyramid."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping, Tuple

from .earth_tile_generator import (
    FRONTEND_TILE_SIZE_BY_LOD,
    LOD_PYRAMID,
    EarthTileGenerator,
)


SOURCE_CACHE_ROOT = Path(
    "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG"
)

DATASETS = {
    "topo_bathy": [
        "21600x10800_jpeg_preview/world.topo.bathy.200408.3x21600x10800_geo.jpg",
        "21600x10800_jpeg_preview/world.topo.bathy.200407.3x21600x10800_geo.jpg",
    ],
    "base_map": [
        "21600x10800_jpeg_preview/world.200408.3x21600x10800_geo.jpg",
        "21600x10800_jpeg_preview/world.200407.3x21600x10800_geo.jpg",
    ],
}

EXPORT_LODS = ("16k", "8k", "4k")


@dataclass(frozen=True)
class ExportResult:
    dataset: str
    lod: str
    output_dir: Path
    tiles_x: int
    tiles_y: int
    missing: Tuple[Path, ...]
    manifest_path: Path

    @property
    def complete(self) -> bool:
        return not self.missing


class EarthTileExporter:
    """Generate and validate BMNG tiles for every frontend-served dataset."""

    def __init__(
        self,
        source_cache_root: str | Path = SOURCE_CACHE_ROOT,
        tile_size_by_lod: Mapping[str, int] | None = None,
        lod_pyramid: Mapping[str, Tuple[int, int]] | None = None,
        overwrite: bool = False,
        color_profile: str = "raw",
    ) -> None:
        self.source_cache_root = Path(source_cache_root)
        self.tile_size_by_lod = dict(tile_size_by_lod or FRONTEND_TILE_SIZE_BY_LOD)
        self.lod_pyramid = dict(lod_pyramid or LOD_PYRAMID)
        self.overwrite = bool(overwrite)
        self.color_profile = color_profile
        if self.color_profile not in {"raw", "noon_air"}:
            raise ValueError("color_profile must be 'raw' or 'noon_air'")

    def generate_all(
        self,
        datasets: Iterable[str] = DATASETS.keys(),
        lods: Iterable[str] = EXPORT_LODS,
    ) -> list[ExportResult]:
        results: list[ExportResult] = []
        for dataset in datasets:
            generator = self._generator(dataset)
            for lod in lods:
                generator.generate_lod(lod)
                results.append(self.write_manifest(dataset, lod, generator))
        return results

    def validate_completeness(
        self,
        datasets: Iterable[str] = DATASETS.keys(),
        lods: Iterable[str] = EXPORT_LODS,
    ) -> Dict[str, Dict[str, list[Path]]]:
        missing: Dict[str, Dict[str, list[Path]]] = {}
        for dataset in datasets:
            generator = self._generator(dataset)
            missing[dataset] = {lod: generator.missing_tiles(lod) for lod in lods}
        return missing

    def detect_missing_tiles(self, dataset: str, lod: str) -> list[Path]:
        return self._generator(dataset).missing_tiles(lod)

    def write_manifest(self, dataset: str, lod: str, generator: EarthTileGenerator | None = None) -> ExportResult:
        generator = generator or self._generator(dataset)
        tiles_x, tiles_y = generator.compute_tile_grid(lod)
        output_dir = generator.output_root / generator.output_tile_dir / lod
        output_dir.mkdir(parents=True, exist_ok=True)
        missing = tuple(generator.missing_tiles(lod))
        manifest = {
            "lod": lod,
            "tiles_x": tiles_x,
            "tiles_y": tiles_y,
            "tile_size": generator.tile_size_by_lod[lod],
            "width": self.lod_pyramid[lod][0],
            "height": self.lod_pyramid[lod][1],
            "source": "BMNG_21K",
            "source_image": str(generator.source),
            "dataset": dataset,
            "projection": "EPSG:4326",
            "color_profile": self.color_profile,
            "tile_pattern": "tile_{x}_{y}.jpg",
            "complete": not missing,
            "missing_tiles": [path.name for path in missing],
        }
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        return ExportResult(dataset, lod, output_dir, tiles_x, tiles_y, missing, manifest_path)

    def generate_root_manifest(self) -> Path:
        manifest = {
            "source": "BMNG_21K",
            "projection": "EPSG:4326",
            "datasets": sorted(DATASETS),
            "lods": list(EXPORT_LODS),
            "tile_size_by_lod": self.tile_size_by_lod,
            "lod_pyramid": {lod: list(size) for lod, size in self.lod_pyramid.items()},
            "color_profile": self.color_profile,
        }
        name = "tiles_manifest.json" if self.color_profile == "raw" else f"tiles_{self.color_profile}_manifest.json"
        path = self.source_cache_root / name
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        return path

    def _generator(self, dataset: str) -> EarthTileGenerator:
        source = self.resolve_source(dataset)
        colorizer = None
        output_tile_dir = "tiles"
        if self.color_profile == "noon_air":
            from core.rendering.noon_air_colorizer import NoonAirColorizer

            colorizer = NoonAirColorizer()
            output_tile_dir = "tiles_noon_air"
        return EarthTileGenerator(
            source,
            tile_size=self.tile_size_by_lod,
            output_root=self.source_cache_root / dataset,
            lod_pyramid=self.lod_pyramid,
            overwrite=self.overwrite,
            colorizer=colorizer,
            output_tile_dir=output_tile_dir,
            dataset=dataset,
        )

    def resolve_source(self, dataset: str) -> Path:
        if dataset not in DATASETS:
            raise ValueError(f"Unknown BMNG dataset {dataset!r}; expected one of {sorted(DATASETS)}")
        for relative in DATASETS[dataset]:
            candidate = self.source_cache_root / dataset / relative
            if candidate.exists():
                return candidate
        expected = ", ".join(str(self.source_cache_root / dataset / rel) for rel in DATASETS[dataset])
        raise FileNotFoundError(f"No BMNG source image found for {dataset}; checked {expected}")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate BMNG frontend tile pyramid")
    parser.add_argument("--source-root", default=str(SOURCE_CACHE_ROOT))
    parser.add_argument("--dataset", choices=sorted(DATASETS), action="append")
    parser.add_argument("--lod", choices=list(EXPORT_LODS), action="append")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--color-profile", choices=("raw", "noon_air"), default="raw")
    args = parser.parse_args(argv)

    exporter = EarthTileExporter(args.source_root, overwrite=args.overwrite, color_profile=args.color_profile)
    results = exporter.generate_all(args.dataset or DATASETS.keys(), args.lod or EXPORT_LODS)
    exporter.generate_root_manifest()
    missing = [path for result in results for path in result.missing]
    if missing:
        for path in missing:
            print(f"missing: {path}")
        return 1
    for result in results:
        print(f"generated {result.dataset}/{result.lod}: {result.tiles_x}x{result.tiles_y} -> {result.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
