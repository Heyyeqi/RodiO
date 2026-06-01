#!/usr/bin/env python3
"""
Generate ocean specular masks for RodiO from Natural Earth land polygons.

Data source:
  - Natural Earth 1:10m Physical Vectors
  - ne_10m_land.zip

License:
  - Natural Earth data is public domain.

This script renders a grayscale equirectangular mask where:
  - ocean = white
  - land = black

It intentionally treats inland water as non-specular by filling all land polygons
black on a white background. That keeps the output conservative for a specular
map control layer.
"""

from __future__ import annotations

import argparse
import math
import struct
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple
from urllib.request import Request, build_opener, ProxyHandler

try:
    from PIL import Image, ImageDraw
except Exception as exc:  # pragma: no cover - import guard
    raise SystemExit(
        "Pillow is required to generate the mask. Run with a Python environment that has PIL installed."
    ) from exc


DEFAULT_SOURCE_URL = "https://naturalearth.s3.amazonaws.com/10m_physical/ne_10m_land.zip"
DEFAULT_OUTPUT_DIR = Path("pwa/assets/earth/masks")
TARGET_SIZES = [(4096, 2048), (2048, 1024)]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def natural_earth_download(source_url: str, tmp_dir: Path) -> Path:
    """
    Download the Natural Earth zip to a temporary directory and return its path.
    """
    tmp_dir.mkdir(parents=True, exist_ok=True)
    zip_path = tmp_dir / "ne_10m_land.zip"
    request = Request(source_url, headers={"User-Agent": "RodiO-mask-generator/1.0"})
    opener = build_opener(ProxyHandler({}))
    with opener.open(request, timeout=120) as response, zip_path.open("wb") as out:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
    return zip_path


def find_shp_path(extracted_dir: Path) -> Path:
    shp_files = sorted(extracted_dir.glob("*.shp"))
    if not shp_files:
        raise FileNotFoundError(f"No .shp file found in {extracted_dir}")
    return shp_files[0]


def iter_shapefile_polygons(shp_path: Path) -> Iterable[List[List[Tuple[float, float]]]]:
    """
    Yield polygon records as lists of rings. Each ring is a list of (lon, lat).
    The function supports Polygon/PolygonZ/PolygonM shapefile records.
    """
    with shp_path.open("rb") as fh:
        header = fh.read(100)
        if len(header) != 100:
            raise ValueError(f"{shp_path} is too small to be a valid shapefile")

        while True:
            record_header = fh.read(8)
            if len(record_header) < 8:
                break

            _record_number, content_length = struct.unpack(">2i", record_header)
            content = fh.read(content_length * 2)
            if len(content) < 4:
                break

            shape_type = struct.unpack("<i", content[:4])[0]
            if shape_type == 0:
                continue
            if shape_type not in (5, 15, 25):
                continue

            # Polygon record layout:
            #   shape type (4)
            #   bbox (32)
            #   numParts (4)
            #   numPoints (4)
            #   parts[numParts] (4 each)
            #   points[numPoints] (16 each)
            if len(content) < 44:
                continue

            num_parts, num_points = struct.unpack("<2i", content[36:44])
            parts_offset = 44
            parts_end = parts_offset + 4 * num_parts
            points_offset = parts_end
            points_end = points_offset + 16 * num_points
            if len(content) < points_end:
                continue

            parts = list(struct.unpack(f"<{num_parts}i", content[parts_offset:parts_end])) if num_parts else []
            points_blob = content[points_offset:points_end]
            points = [
                struct.unpack_from("<2d", points_blob, index * 16)
                for index in range(num_points)
            ]

            rings: List[List[Tuple[float, float]]] = []
            for part_index, start in enumerate(parts):
                end = parts[part_index + 1] if part_index + 1 < len(parts) else len(points)
                ring = points[start:end]
                if len(ring) >= 3:
                    rings.append(ring)

            if rings:
                yield rings


def unwrap_ring(long_lat_ring: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Make longitude continuous across the antimeridian by adding/subtracting 360°
    whenever the delta between consecutive points would otherwise jump across the globe.
    """
    if not long_lat_ring:
        return []

    unwrapped: List[Tuple[float, float]] = [long_lat_ring[0]]
    prev_lon, prev_lat = long_lat_ring[0]
    adjusted_prev_lon = prev_lon

    for lon, lat in long_lat_ring[1:]:
        adjusted_lon = lon
        delta = adjusted_lon - adjusted_prev_lon
        while delta > 180.0:
            adjusted_lon -= 360.0
            delta = adjusted_lon - adjusted_prev_lon
        while delta < -180.0:
            adjusted_lon += 360.0
            delta = adjusted_lon - adjusted_prev_lon
        unwrapped.append((adjusted_lon, lat))
        adjusted_prev_lon = adjusted_lon
        prev_lon, prev_lat = lon, lat

    return unwrapped


def ring_to_points(
    ring: Sequence[Tuple[float, float]],
    width: int,
    height: int,
    x_shift: float,
) -> List[Tuple[float, float]]:
    pts: List[Tuple[float, float]] = []
    for lon, lat in ring:
        x = ((lon + 180.0) / 360.0) * width + x_shift
        y = ((90.0 - lat) / 180.0) * height
        pts.append((x, y))
    return pts


def render_mask(
    shp_path: Path,
    output_path: Path,
    width: int,
    height: int,
) -> None:
    # We render on a 3x-wide canvas and draw three shifted copies of each land ring.
    # That keeps antimeridian-crossing polygons continuous without needing heavy GIS
    # dependencies or expensive polygon clipping.
    canvas_width = width * 3
    image = Image.new("L", (canvas_width, height), 255)
    draw = ImageDraw.Draw(image)

    ring_count = 0
    point_count = 0
    for polygon_rings in iter_shapefile_polygons(shp_path):
        for ring in polygon_rings:
            unwrapped = unwrap_ring(ring)
            if len(unwrapped) < 3:
                continue

            base_points = ring_to_points(unwrapped, width, height, float(width))
            point_count += len(base_points)
            ring_count += 1

            for extra_shift in (-float(width), 0.0, float(width)):
                shifted = [(x + extra_shift, y) for x, y in base_points]
                draw.polygon(shifted, fill=0)

    cropped = image.crop((width, 0, width * 2, height))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(output_path, format="PNG", optimize=True)

    print(
        f"[mask] wrote {output_path} ({width}x{height}) from {shp_path.name}; "
        f"rings={ring_count}, points={point_count}, mode=L"
    )


def extract_zip(zip_path: Path, extract_dir: Path) -> Path:
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    return extract_dir


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate RodiO ocean specular masks from Natural Earth land polygons.")
    parser.add_argument(
        "--source-zip",
        type=Path,
        default=None,
        help="Local Natural Earth zip file. If omitted, the script downloads ne_10m_land.zip.",
    )
    parser.add_argument(
        "--source-url",
        type=str,
        default=DEFAULT_SOURCE_URL,
        help="Natural Earth download URL used when --source-zip is omitted.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where the generated PNG masks will be written.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep the temporary download/extraction directory for inspection.",
    )
    args = parser.parse_args(argv)

    root = repo_root()
    output_dir = (root / args.output_dir).resolve() if not args.output_dir.is_absolute() else args.output_dir

    if args.source_zip is not None:
        source_zip = args.source_zip.resolve()
        if not source_zip.exists():
            raise FileNotFoundError(f"Source zip not found: {source_zip}")
        cleanup_context = None
        work_dir = source_zip.parent
    else:
        cleanup_context = tempfile.TemporaryDirectory(prefix="rodio-natural-earth-")
        work_dir = Path(cleanup_context.name)
        print(f"[mask] downloading Natural Earth data from {args.source_url}")
        source_zip = natural_earth_download(args.source_url, work_dir)

    try:
        extract_dir = work_dir / "natural-earth"
        extract_zip(source_zip, extract_dir)
        shp_path = find_shp_path(extract_dir)

        for width, height in TARGET_SIZES:
            output_path = output_dir / f"ocean_specular_{width}x{height}.png"
            render_mask(shp_path, output_path, width, height)

        print("[mask] done")
    finally:
        if cleanup_context is not None and not args.keep_temp:
            cleanup_context.cleanup()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
