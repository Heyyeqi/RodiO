#!/usr/bin/env python3
"""
rdl_coral_atlas_proof.py — minimal Allen Coral Atlas reef extent proof.

Uses only Python stdlib sqlite3/zipfile plus Pillow. It reads GeoPackage
geometry blobs directly, parses GeoPackageBinary + WKB Polygon/MultiPolygon,
and rasterizes reef extent polygons into an RDL-region mask/preview.
"""

from __future__ import annotations

import argparse
import ast
import json
import sqlite3
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
REGION_SOURCE = ROOT / "scripts/geo/rdl_mapbox_poc.py"
CORAL_ROOT = ROOT / "d5b_processor_v3/source_cache/gee_global/external_raw/allen_coral_atlas"
RDL_ROOT = ROOT / "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions"
DEFAULT_OUT = ROOT / "docs/preview_archives/rdl_m2_coral_atlas_proof_20260626"


CORAL_PACKAGES = {
    "hawaii": "Hawaiian-Islands-20230309235255.zip",
    "maldives": "Central-Indian-Ocean-20230310001123.zip",
    "great_barrier_reef": "Great-Barrier-Reef-and-Torres-Strait-20230310013521.zip",
    "philippines_central": "Philippines-20230310023925.zip",
    "caribbean_bahamas": "Northern-Caribbean--Florida---Bahamas-20230310014129.zip",
}


@dataclass
class Region:
    region_id: str
    lon_w: float
    lon_e: float
    lat_s: float
    lat_n: float
    description: str = ""


class WKBReader:
    def __init__(self, data: bytes, offset: int = 0):
        self.data = data
        self.offset = offset

    def _endian(self) -> str:
        flag = self.data[self.offset]
        self.offset += 1
        if flag == 0:
            return ">"
        if flag == 1:
            return "<"
        raise ValueError(f"unsupported WKB endian flag: {flag}")

    def _u32(self, endian: str) -> int:
        value = struct.unpack_from(endian + "I", self.data, self.offset)[0]
        self.offset += 4
        return value

    def _f64(self, endian: str) -> float:
        value = struct.unpack_from(endian + "d", self.data, self.offset)[0]
        self.offset += 8
        return value

    def read_geometry(self) -> list[list[list[tuple[float, float]]]]:
        endian = self._endian()
        raw_type = self._u32(endian)
        geom_type = raw_type % 1000
        has_z = raw_type in (1001, 1002, 1003, 1004, 1005, 1006, 3001, 3002, 3003, 3004, 3005, 3006)
        has_m = raw_type in (2001, 2002, 2003, 2004, 2005, 2006, 3001, 3002, 3003, 3004, 3005, 3006)
        if geom_type == 3:
            return [self._read_polygon(endian, has_z, has_m)]
        if geom_type == 6:
            count = self._u32(endian)
            polygons: list[list[list[tuple[float, float]]]] = []
            for _ in range(count):
                polygons.extend(self.read_geometry())
            return polygons
        raise ValueError(f"unsupported WKB geometry type: {raw_type}")

    def _read_polygon(self, endian: str, has_z: bool, has_m: bool) -> list[list[tuple[float, float]]]:
        ring_count = self._u32(endian)
        rings: list[list[tuple[float, float]]] = []
        for _ in range(ring_count):
            point_count = self._u32(endian)
            ring: list[tuple[float, float]] = []
            for _ in range(point_count):
                x = self._f64(endian)
                y = self._f64(endian)
                if has_z:
                    self._f64(endian)
                if has_m:
                    self._f64(endian)
                ring.append((x, y))
            rings.append(ring)
        return rings


def load_regions() -> dict[str, Region]:
    tree = ast.parse(REGION_SOURCE.read_text())
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "REGIONS":
            raw = ast.literal_eval(node.value)
            return {
                key: Region(
                    region_id=key,
                    lon_w=float(value["bounds"][0]),
                    lon_e=float(value["bounds"][1]),
                    lat_s=float(value["bounds"][2]),
                    lat_n=float(value["bounds"][3]),
                    description=value.get("description", ""),
                )
                for key, value in raw.items()
            }
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "REGIONS":
                    raw = ast.literal_eval(node.value)
                    return {
                        key: Region(
                            region_id=key,
                            lon_w=float(value["bounds"][0]),
                            lon_e=float(value["bounds"][1]),
                            lat_s=float(value["bounds"][2]),
                            lat_n=float(value["bounds"][3]),
                            description=value.get("description", ""),
                        )
                        for key, value in raw.items()
                    }
    raise RuntimeError(f"REGIONS not found in {REGION_SOURCE}")


def ensure_reef_gpkg(region_id: str, out_dir: Path) -> Path:
    package = CORAL_PACKAGES.get(region_id)
    if not package:
        raise SystemExit(f"No Coral Atlas package mapping for {region_id}")
    package_path = CORAL_ROOT / package
    if not package_path.exists():
        raise SystemExit(f"Missing Coral Atlas package: {package_path}")
    gpkg_cache = out_dir / "_gpkg_cache" / region_id
    gpkg_cache.mkdir(parents=True, exist_ok=True)
    gpkg_path = gpkg_cache / "reefextent.gpkg"
    if gpkg_path.exists() and gpkg_path.stat().st_size > 0:
        return gpkg_path
    with zipfile.ZipFile(package_path) as zf:
        member = "Reef-Extent/reefextent.gpkg"
        with zf.open(member) as src, gpkg_path.open("wb") as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                dst.write(chunk)
    return gpkg_path


def gpkg_table_info(gpkg_path: Path) -> tuple[str, str, tuple[float, float, float, float]]:
    with sqlite3.connect(gpkg_path) as con:
        row = con.execute("select table_name, min_x, max_x, min_y, max_y from gpkg_contents where data_type='features' limit 1").fetchone()
        geom = con.execute("select column_name from gpkg_geometry_columns where table_name=? limit 1", (row[0],)).fetchone()
    return row[0], geom[0], (float(row[1]), float(row[2]), float(row[3]), float(row[4]))


def gpkg_wkb_offset(blob: bytes) -> int:
    if blob[:2] != b"GP":
        return 0
    flags = blob[3]
    envelope_code = (flags >> 1) & 0b111
    envelope_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    return 8 + envelope_sizes.get(envelope_code, 0)


def parse_gpkg_geometry(blob: bytes) -> list[list[list[tuple[float, float]]]]:
    return WKBReader(blob, gpkg_wkb_offset(blob)).read_geometry()


def iter_region_geometries(gpkg_path: Path, region: Region) -> Iterable[bytes]:
    table, geom_col, _ = gpkg_table_info(gpkg_path)
    rtree = f"rtree_{table}_{geom_col}"
    sql = (
        f'select t."{geom_col}" from "{table}" t '
        f'join "{rtree}" r on t.fid = r.id '
        "where r.maxx >= ? and r.minx <= ? and r.maxy >= ? and r.miny <= ?"
    )
    with sqlite3.connect(gpkg_path) as con:
        for (blob,) in con.execute(sql, (region.lon_w, region.lon_e, region.lat_s, region.lat_n)):
            yield blob


def lonlat_to_px(lon: float, lat: float, region: Region, width: int, height: int, scale: int) -> tuple[float, float]:
    x = (lon - region.lon_w) / (region.lon_e - region.lon_w) * (width * scale - 1)
    y = (region.lat_n - lat) / (region.lat_n - region.lat_s) * (height * scale - 1)
    return x, y


def rasterize_reef_mask(gpkg_path: Path, region: Region, size: tuple[int, int], oversample: int) -> tuple[Image.Image, dict]:
    width, height = size
    mask = Image.new("L", (width * oversample, height * oversample), 0)
    draw = ImageDraw.Draw(mask)
    feature_count = 0
    polygon_count = 0
    ring_count = 0
    parse_errors = 0
    for blob in iter_region_geometries(gpkg_path, region):
        feature_count += 1
        try:
            polygons = parse_gpkg_geometry(blob)
        except Exception:
            parse_errors += 1
            continue
        for rings in polygons:
            if not rings:
                continue
            polygon_count += 1
            exterior = [lonlat_to_px(lon, lat, region, width, height, oversample) for lon, lat in rings[0]]
            draw.polygon(exterior, fill=255)
            for hole in rings[1:]:
                ring_count += 1
                hole_px = [lonlat_to_px(lon, lat, region, width, height, oversample) for lon, lat in hole]
                draw.polygon(hole_px, fill=0)
    if oversample > 1:
        mask = mask.resize((width, height), Image.Resampling.LANCZOS)
    nonzero = mask.point(lambda p: 255 if p else 0).getbbox() is not None
    reef_pixels = sum(mask.histogram()[17:])
    stats = {
        "features_in_bbox": feature_count,
        "polygons_rasterized": polygon_count,
        "holes_rasterized": ring_count,
        "parse_errors": parse_errors,
        "reef_pixels_gt16": reef_pixels,
        "reef_pixel_ratio_gt16": reef_pixels / float(width * height),
        "nonzero": nonzero,
    }
    return mask, stats


def make_preview(base: Image.Image, mask: Image.Image) -> Image.Image:
    base_rgb = base.convert("RGB")
    overlay = Image.new("RGB", base_rgb.size, (72, 224, 214))
    alpha = mask.point(lambda p: min(170, int(p * 0.70)))
    out = Image.composite(overlay, base_rgb, alpha)
    return Image.blend(base_rgb, out, 0.75)


def make_contact_sheet(base: Image.Image, mask: Image.Image, preview: Image.Image) -> Image.Image:
    thumb_w = 900
    panels = []
    for img in (base.convert("RGB"), Image.merge("RGB", (mask, mask, mask)), preview.convert("RGB")):
        h = round(img.height * thumb_w / img.width)
        panels.append(img.resize((thumb_w, h), Image.Resampling.LANCZOS))
    label_h = 46
    width = thumb_w * 3
    height = max(p.height for p in panels) + label_h
    sheet = Image.new("RGB", (width, height), (12, 18, 28))
    labels = ["M0/M1 base", "ACA reef mask", "reef overlay preview"]
    draw = ImageDraw.Draw(sheet)
    for i, (panel, label) in enumerate(zip(panels, labels)):
        x = i * thumb_w
        sheet.paste(panel, (x, label_h))
        draw.text((x + 18, 14), label, fill=(224, 232, 235))
    return sheet


def run(region_id: str, out_dir: Path, oversample: int) -> dict:
    regions = load_regions()
    if region_id not in regions:
        raise SystemExit(f"Unknown region: {region_id}")
    region = regions[region_id]
    out_dir.mkdir(parents=True, exist_ok=True)
    gpkg_path = ensure_reef_gpkg(region_id, out_dir)
    base_path = RDL_ROOT / region_id / "tile_noon_air_mapbox.jpg"
    if not base_path.exists():
        raise SystemExit(f"Missing RDL base tile: {base_path}")
    base = Image.open(base_path).convert("RGB")
    mask, stats = rasterize_reef_mask(gpkg_path, region, base.size, oversample)
    preview = make_preview(base, mask)
    contact = make_contact_sheet(base, mask, preview)
    prefix = f"{region_id}_aca_reef"
    mask_path = out_dir / f"{prefix}_mask.png"
    preview_path = out_dir / f"{prefix}_overlay_preview.jpg"
    contact_path = out_dir / f"{prefix}_contact_sheet.jpg"
    mask.save(mask_path)
    preview.save(preview_path, quality=92)
    contact.save(contact_path, quality=92)
    table, geom_col, gpkg_bounds = gpkg_table_info(gpkg_path)
    meta = {
        "region": region.__dict__,
        "package": CORAL_PACKAGES[region_id],
        "gpkg_path": str(gpkg_path.relative_to(ROOT)),
        "gpkg_table": table,
        "gpkg_geometry_column": geom_col,
        "gpkg_bounds": gpkg_bounds,
        "base_tile": str(base_path.relative_to(ROOT)),
        "base_size": base.size,
        "oversample": oversample,
        "outputs": {
            "mask": str(mask_path.relative_to(ROOT)),
            "preview": str(preview_path.relative_to(ROOT)),
            "contact_sheet": str(contact_path.relative_to(ROOT)),
        },
        "stats": stats,
        "method": "sqlite3 + GeoPackageBinary/WKB parser + Pillow rasterization",
    }
    (out_dir / f"{prefix}_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def write_readme(out_dir: Path, metas: list[dict]) -> None:
    lines = [
        "# RDL M2 Coral Atlas Reef Proof — 2026-06-26",
        "",
        "Minimal proof for Allen Coral Atlas reef extent rasterization.",
        "",
        "No geopandas, rasterio, fiona, pyproj, shapely, or GDAL was used.",
        "The pipeline is `zip/gpkg -> sqlite3 -> GeoPackageBinary/WKB parser -> Pillow mask/preview`.",
        "",
        "## Outputs",
        "",
    ]
    for meta in metas:
        stats = meta["stats"]
        lines.extend([
            f"### {meta['region']['region_id']}",
            "",
            f"- Package: `{meta['package']}`",
            f"- Features in region bbox: {stats['features_in_bbox']}",
            f"- Polygons rasterized: {stats['polygons_rasterized']}",
            f"- Reef pixel ratio: {stats['reef_pixel_ratio_gt16']:.6f}",
            f"- Contact sheet: `{meta['outputs']['contact_sheet']}`",
            f"- Preview: `{meta['outputs']['preview']}`",
            f"- Mask: `{meta['outputs']['mask']}`",
            "",
        ])
    lines.extend([
        "## Notes",
        "",
        "- This proof uses reef extent only. Benthic and geomorphic classes are intentionally deferred because their GeoPackages are much larger.",
        "- Reef extent should be treated as a shallow-water detail mask, not as a full color replacement layer.",
        "- The next production step is to feed this mask into the RDL compositor with depth-gated, feathered color treatment.",
        "",
    ])
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal Coral Atlas reef extent proof for RDL regions.")
    parser.add_argument("--region", action="append", default=None, help="RDL region id. Can repeat.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--oversample", type=int, default=2)
    args = parser.parse_args()
    region_ids = args.region or ["maldives"]
    metas = [run(region_id, args.out_dir, max(1, args.oversample)) for region_id in region_ids]
    write_readme(args.out_dir, metas)
    print(json.dumps({"out_dir": str(args.out_dir), "regions": [m["region"]["region_id"] for m in metas]}, indent=2))


if __name__ == "__main__":
    main()
