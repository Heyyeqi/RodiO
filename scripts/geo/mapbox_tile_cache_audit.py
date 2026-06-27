#!/usr/bin/env python3.11
"""
Audit and optionally fill the local Mapbox Static Tiles cache.

Default mode is read-only:
  - computes the expected tile coverage for RDL regions
  - reports which tiles are already cached and which are missing
  - does not read MAPBOX_TOKEN
  - does not make network requests

Network download is explicit and bounded:
  python3.11 scripts/geo/mapbox_tile_cache_audit.py --region hawaii --download --max-new-requests 50

This script is intentionally not a token/usage bypass. Mapbox requires a valid
access token for Static Tiles API requests, and requests are billable API usage.
Use --download only for compliant, bounded private development cache repair.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_ROOT = ROOT / "d5b_processor_v3/source_cache/mapbox_static_tiles"
DEFAULT_REPORT_PATH = ROOT / "d5b_processor_v3/source_cache/mapbox_static_tiles/audit_report.json"

STYLE_USER = "mapbox"
STYLE_ID = "satellite-v9"
TILE_SIZE = 512
DEFAULT_ZOOM = 10
MIN_VALID_BYTES = 1024

# Keep this list aligned with scripts/geo/rdl_mapbox_poc.py and
# scripts/geo/rdl_regional_generator.py. Bounds are lon_w, lon_e, lat_s, lat_n.
REGIONS: dict[str, dict] = {
    "hawaii": {
        "label": "Hawaii",
        "bounds": (-161.5, -154.0, 18.0, 23.0),
    },
    "maldives": {
        "label": "Maldives",
        "bounds": (71.5, 74.5, -1.5, 8.5),
    },
    "ryukyu": {
        "label": "Ryukyu / Okinawa",
        "bounds": (122.5, 132.5, 23.5, 30.0),
    },
    "philippines_central": {
        "label": "Central Philippines",
        "bounds": (117.0, 127.0, 6.0, 18.0),
    },
    "south_china_sea": {
        "label": "South China Sea",
        "bounds": (108.0, 120.0, 8.0, 22.0),
    },
    "great_barrier_reef": {
        "label": "Great Barrier Reef",
        "bounds": (142.5, 153.5, -25.0, -10.0),
    },
    "caribbean_bahamas": {
        "label": "Caribbean / Bahamas",
        "bounds": (-85.0, -70.0, 17.0, 27.5),
    },
    "indonesia_east": {
        "label": "Eastern Indonesia",
        "bounds": (120.0, 135.0, -10.0, 1.0),
    },
}


@dataclass(frozen=True)
class Tile:
    z: int
    x: int
    y: int


@dataclass
class RegionAudit:
    region_id: str
    label: str
    zoom: int
    bounds: tuple[float, float, float, float]
    expected_tiles: int
    cached_tiles: int
    missing_tiles: int
    invalid_tiles: int
    cache_dir: str

    @property
    def complete(self) -> bool:
        return self.missing_tiles == 0 and self.invalid_tiles == 0


def _lon_to_tx(lon: float, z: int) -> float:
    return (lon + 180.0) / 360.0 * (2**z)


def _lat_to_ty(lat: float, z: int) -> float:
    lat = max(min(lat, 85.05112878), -85.05112878)
    lat_rad = math.radians(lat)
    return (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * (2**z)


def tiles_for_bounds(bounds: tuple[float, float, float, float], zoom: int) -> list[Tile]:
    lon_w, lon_e, lat_s, lat_n = bounds
    x_w = _lon_to_tx(lon_w, zoom)
    x_e = _lon_to_tx(lon_e, zoom)
    y_n = _lat_to_ty(lat_n, zoom)
    y_s = _lat_to_ty(lat_s, zoom)

    tx0, tx1 = math.floor(x_w), math.floor(x_e)
    ty0, ty1 = math.floor(y_n), math.floor(y_s)
    max_idx = 2**zoom - 1
    tx0, tx1 = max(0, tx0), min(max_idx, tx1)
    ty0, ty1 = max(0, ty0), min(max_idx, ty1)
    return [Tile(zoom, x, y) for y in range(ty0, ty1 + 1) for x in range(tx0, tx1 + 1)]


def tile_path(cache_root: Path, style_id: str, region_id: str, tile: Tile) -> Path:
    return cache_root / style_id / region_id / f"z{tile.z}" / f"{tile.z}_{tile.x}_{tile.y}.jpg"


def is_valid_tile(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size >= MIN_VALID_BYTES


def _load_token() -> str | None:
    token = os.environ.get("MAPBOX_TOKEN")
    if token:
        return token.strip()

    env_path = ROOT / ".env"
    if not env_path.exists():
        return None
    for raw in env_path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "MAPBOX_TOKEN":
            return value.strip().strip('"').strip("'")
    return None


def expected_regions(selected: Iterable[str]) -> dict[str, dict]:
    selected = tuple(selected)
    if not selected or selected == ("all",):
        return REGIONS

    unknown = [region_id for region_id in selected if region_id not in REGIONS]
    if unknown:
        raise SystemExit(f"Unknown region(s): {', '.join(unknown)}")
    return {region_id: REGIONS[region_id] for region_id in selected}


def audit_region(cache_root: Path, style_id: str, region_id: str, region: dict, zoom: int) -> tuple[RegionAudit, list[Tile], list[Path]]:
    tiles = tiles_for_bounds(region["bounds"], zoom)
    missing: list[Tile] = []
    invalid: list[Path] = []

    for tile in tiles:
        path = tile_path(cache_root, style_id, region_id, tile)
        if not path.exists():
            missing.append(tile)
        elif not is_valid_tile(path):
            invalid.append(path)

    audit = RegionAudit(
        region_id=region_id,
        label=region["label"],
        zoom=zoom,
        bounds=tuple(region["bounds"]),
        expected_tiles=len(tiles),
        cached_tiles=len(tiles) - len(missing) - len(invalid),
        missing_tiles=len(missing),
        invalid_tiles=len(invalid),
        cache_dir=str(cache_root / style_id / region_id / f"z{zoom}"),
    )
    return audit, missing, invalid


def download_tile(token: str, style_id: str, tile: Tile, output_path: Path, sleep_s: float) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = urllib.parse.quote(token, safe="")
    url = (
        f"https://api.mapbox.com/styles/v1/{STYLE_USER}/{style_id}"
        f"/tiles/{TILE_SIZE}/{tile.z}/{tile.x}/{tile.y}?access_token={encoded}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "RodiO-mapbox-cache-audit/1.0"})
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    last_error: Exception | None = None
    for attempt in range(3):
        if attempt > 0:
            time.sleep(max(sleep_s, 1.0) * attempt)
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
            if len(data) < MIN_VALID_BYTES:
                raise RuntimeError(f"short response: {len(data)} bytes")
            tmp_path.write_bytes(data)
            tmp_path.replace(output_path)
            if sleep_s > 0:
                time.sleep(sleep_s)
            return
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:240]
            raise RuntimeError(f"Mapbox HTTP {exc.code}: {body}") from exc
        except (OSError, urllib.error.URLError, RuntimeError) as exc:
            last_error = exc

    raise RuntimeError(f"failed after 3 attempts: {last_error}") from last_error


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit and optionally fill local Mapbox Static Tiles cache")
    parser.add_argument("--region", action="append", choices=sorted(REGIONS), help="Region to audit; repeatable. Omit for all.")
    parser.add_argument("--all", action="store_true", help="Audit all known regions.")
    parser.add_argument("--list", action="store_true", help="List known regions and exit.")
    parser.add_argument("--zoom", type=int, default=DEFAULT_ZOOM)
    parser.add_argument("--style-id", default=STYLE_ID)
    parser.add_argument("--cache-root", type=Path, default=DEFAULT_CACHE_ROOT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--download", action="store_true", help="Download missing tiles. Requires MAPBOX_TOKEN and --max-new-requests > 0.")
    parser.add_argument("--max-new-requests", type=int, default=0, help="Hard cap on new Mapbox API requests for this run.")
    parser.add_argument("--sleep", type=float, default=0.15, help="Seconds to sleep after each successful download.")
    parser.add_argument("--no-report", action="store_true", help="Do not write an audit JSON report.")
    args = parser.parse_args()

    if args.list:
        for region_id, region in REGIONS.items():
            print(f"{region_id:22s} {region['label']:24s} bounds={region['bounds']}")
        return 0

    selected = ["all"] if args.all or not args.region else args.region
    regions = expected_regions(selected)

    token = None
    remaining_downloads = args.max_new_requests
    if args.download:
        if args.max_new_requests <= 0:
            raise SystemExit("--download requires --max-new-requests N, with N > 0")
        token = _load_token()
        if not token:
            raise SystemExit("MAPBOX_TOKEN not found in environment or .env")

    audits: list[RegionAudit] = []
    downloaded = 0
    failed: list[dict] = []

    print(f"cache_root={args.cache_root}")
    print(f"style={STYLE_USER}/{args.style_id} zoom={args.zoom} download={args.download}")

    for region_id, region in regions.items():
        audit, missing, invalid = audit_region(args.cache_root, args.style_id, region_id, region, args.zoom)
        audits.append(audit)
        status = "complete" if audit.complete else "missing"
        print(
            f"{region_id:22s} {status:8s} "
            f"cached={audit.cached_tiles}/{audit.expected_tiles} "
            f"missing={audit.missing_tiles} invalid={audit.invalid_tiles}"
        )

        if not args.download or not missing:
            continue

        for tile in missing:
            if remaining_downloads <= 0:
                break
            path = tile_path(args.cache_root, args.style_id, region_id, tile)
            try:
                download_tile(token, args.style_id, tile, path, args.sleep)
                downloaded += 1
                remaining_downloads -= 1
            except Exception as exc:  # noqa: BLE001 - CLI needs to report and continue.
                failed.append({"region_id": region_id, "tile": asdict(tile), "error": str(exc)})
                print(f"  ERROR {region_id} z{tile.z}/{tile.x}/{tile.y}: {exc}", file=sys.stderr)
                break

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "style": f"{STYLE_USER}/{args.style_id}",
        "zoom": args.zoom,
        "cache_root": str(args.cache_root),
        "download_enabled": args.download,
        "max_new_requests": args.max_new_requests,
        "downloaded": downloaded,
        "failed": failed,
        "regions": [asdict(audit) | {"complete": audit.complete} for audit in audits],
        "note": (
            "Default audit mode makes no Mapbox requests. Download mode uses the Mapbox "
            "Static Tiles API and requires a valid token; requests may count as billable API usage."
        ),
    }

    if not args.no_report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
        print(f"report={args.report}")

    if failed:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
