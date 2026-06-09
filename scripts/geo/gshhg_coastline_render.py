#!/usr/bin/env python3
"""
gshhg_coastline_render.py — GSHHG coastline mask + distance field generator

Outputs:
  gshhg_coastline_mask.png     — binary land/sea mask from GSHHG L1 polygons
  gshhg_distance_field.png     — distance-to-coast field (normalized 0–1)
  key_crops_contact_sheet.png  — 5 key region crops

Usage:
  python3 gshhg_coastline_render.py --bounds lon_w lon_e lat_s lat_n
  python3 gshhg_coastline_render.py --bounds 118 150 22 50
"""

import argparse
import sys
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import shapefile

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GSHHG_DIR = os.path.join(os.path.dirname(__file__), '../../pwa/assets/source/coastline/gshhg')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '../../previews/rdl_v2_p0_gebco_gshhg_japan_benchmark')
GSHHG_L1 = os.path.join(GSHHG_DIR, 'GSHHS_shp/f/GSHHS_f_L1.shp')  # full-res land polygons

# Output resolution for the regional mask
MASK_W = 4096
MASK_H_PER_DEG = MASK_W  # pixels per degree of lon — height derived from aspect ratio

# Key crop definitions (region_id, lon_center, lat_center, half_span_deg)
KEY_CROPS = [
    ('tokyo_bay',         139.8, 35.4, 1.5),
    ('osaka_kii_seto',    135.0, 34.2, 2.5),
    ('ise_bay',           136.8, 34.7, 1.2),
    ('ryukyu_arc',        128.0, 26.5, 3.0),
    ('kyushu_west',       129.5, 32.5, 2.0),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--bounds', nargs=4, type=float, required=True,
                   metavar=('lon_w', 'lon_e', 'lat_s', 'lat_n'))
    p.add_argument('--resolution', type=int, default=4096,
                   help='Width in pixels (height derived from aspect ratio)')
    p.add_argument('--shp', type=str, default=None,
                   help='Override shapefile path (default: GSHHG L1 full-res)')
    p.add_argument('--source-label', type=str, default=None,
                   help='Source label for output metadata')
    return p.parse_args()


def lon_to_px(lon, lon_w, lon_e, width):
    return (lon - lon_w) / (lon_e - lon_w) * width


def lat_to_px(lat, lat_s, lat_n, height):
    # image origin is top-left → north at top → invert
    return (lat_n - lat) / (lat_n - lat_s) * height


def load_etopo1_land_mask(lon_w, lon_e, lat_s, lat_n, width, height):
    """Derive land/sea mask from ETOPO1 elevation (elev >= 0 = land).
    Returns a PIL 'L' image (255=land, 0=sea) at the requested resolution.
    """
    import netCDF4 as nc
    etopo_path = os.path.join(os.path.dirname(__file__),
                              '../../pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd')
    if not os.path.exists(etopo_path):
        print('[gshhg] ETOPO1 not found, using blank land mask')
        return Image.new('L', (width, height), 0)

    ds = nc.Dataset(etopo_path)
    dim = ds.variables['dimension'][:]
    W_e, H_e = int(dim[0]), int(dim[1])
    x_range = ds.variables['x_range'][:]
    y_range = ds.variables['y_range'][:]
    z_flat = ds.variables['z'][:].astype(np.float32)
    ds.close()

    lons = np.linspace(float(x_range[0]), float(x_range[1]), W_e)
    lats = np.linspace(float(y_range[0]), float(y_range[1]), H_e)
    z_2d = z_flat.reshape(H_e, W_e)

    lon_mask = (lons >= lon_w) & (lons <= lon_e)
    lat_mask = (lats >= lat_s) & (lats <= lat_n)
    elev_sub = z_2d[np.ix_(lat_mask, lon_mask)]
    elev_sub = np.flipud(elev_sub)  # row 0 = north

    land_arr = ((elev_sub >= 0).astype(np.uint8) * 255)
    mask_native = Image.fromarray(land_arr, mode='L')
    return mask_native.resize((width, height), Image.NEAREST)


def _ring_to_px(ring, lon_w, lon_e, lat_s, lat_n, width, height):
    return [(lon_to_px(x, lon_w, lon_e, width), lat_to_px(y, lat_s, lat_n, height))
            for x, y in ring]


def load_coastline_lines(shp_path, lon_w, lon_e, lat_s, lat_n):
    """Load polyline shapefile (NE coastline) as list of point sequences."""
    sf = shapefile.Reader(shp_path)
    lines = []
    for sr in sf.iterShapeRecords():
        bb = sr.shape.bbox
        if bb[2] < lon_w or bb[0] > lon_e or bb[3] < lat_s or bb[1] > lat_n:
            continue
        pts = sr.shape.points
        parts = list(sr.shape.parts) + [len(pts)]
        for i in range(len(parts) - 1):
            segment = pts[parts[i]:parts[i+1]]
            if len(segment) >= 2:
                lines.append(segment)
    return lines


def _is_gshhg_polygon(rings):
    """Return True if this polygon looks like a GSHHG land polygon (small bbox, single ring)."""
    if not rings:
        return False
    # GSHHG L1 polygons are single-ring with geographically bounded extent
    # NE global polygons have bbox spanning [-180,-90,180,90]
    if len(rings) == 1:
        pts = rings[0]
        if len(pts) < 3:
            return False
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bbox_span = (max(xs) - min(xs)) * (max(ys) - min(ys))
        return True  # single-ring polygons always ok
    return True  # multi-ring: we'll do the two-pass


def draw_land_mask(polys, lon_w, lon_e, lat_s, lat_n, width, height):
    """Rasterize land polygons to binary mask.
    Strategy:
    - If polys look like valid GSHHG land polygons (single-ring, bounded):
        rasterize with PIL polygon fill (exterior + hole erase)
    - Otherwise (no polys, or NE global polygons):
        fall back to ETOPO1 elev>=0
    """
    # Heuristic: if any polygon has a very large bbox (NE global polygon issue),
    # fall back to ETOPO1. GSHHG polygons are always geographically bounded.
    use_etopo = False
    if not polys:
        use_etopo = True
    else:
        # Check first polygon for global bbox sign
        first_rings = polys[0]
        if first_rings:
            pts = first_rings[0]
            xs = [p[0] for p in pts]
            bbox_lon_span = max(xs) - min(xs)
            if bbox_lon_span > 350:  # global polygon → NE format
                print('[gshhg]   Global polygon detected (NE format), using ETOPO1 land mask')
                use_etopo = True

    if use_etopo:
        print('[gshhg]   Loading ETOPO1 land mask...')
        return load_etopo1_land_mask(lon_w, lon_e, lat_s, lat_n, width, height)

    # GSHHG polygon rasterization
    mask = Image.new('L', (width, height), 0)  # start all sea
    draw = ImageDraw.Draw(mask)
    rendered = 0
    for rings in polys:
        if not rings:
            continue
        exterior = _ring_to_px(rings[0], lon_w, lon_e, lat_s, lat_n, width, height)
        holes = [_ring_to_px(r, lon_w, lon_e, lat_s, lat_n, width, height)
                 for r in rings[1:] if len(r) >= 3]
        if len(exterior) < 3:
            continue
        draw.polygon(exterior, fill=255)
        for hole in holes:
            if len(hole) >= 3:
                draw.polygon(hole, fill=0)
        rendered += 1

    print(f'[gshhg]   Rasterized {rendered}/{len(polys)} GSHHG polygons')
    return mask


def compute_distance_field(mask_arr):
    """Compute normalized distance-to-coast (0=coast, 1=far from coast)."""
    from scipy.ndimage import distance_transform_edt
    land = (mask_arr > 128).astype(np.float32)
    sea = 1.0 - land
    # distance from land pixels to nearest sea
    dist_land = distance_transform_edt(land)
    # distance from sea pixels to nearest land
    dist_sea = distance_transform_edt(sea)
    # combined: coast = 0, interior = positive
    dist_combined = np.where(land > 0.5, dist_land, -dist_sea)
    # normalize to [0, 1] for visualization
    d_min = dist_combined.min()
    d_max = dist_combined.max()
    norm = (dist_combined - d_min) / (d_max - d_min + 1e-8)
    return norm


def crop_region(img, lon_w, lon_e, lat_s, lat_n, width, height,
                crop_lon_c, crop_lat_c, half_span):
    """Crop a sub-region from a full-bounds image."""
    cx = lon_to_px(crop_lon_c, lon_w, lon_e, width)
    cy = lat_to_px(crop_lat_c, lat_s, lat_n, height)
    # half-span in pixels
    hpx_lon = half_span / (lon_e - lon_w) * width
    hpx_lat = half_span / (lat_n - lat_s) * height
    x0 = int(max(0, cx - hpx_lon))
    x1 = int(min(width, cx + hpx_lon))
    y0 = int(max(0, cy - hpx_lat))
    y1 = int(min(height, cy + hpx_lat))
    return img.crop((x0, y0, x1, y1))


def make_contact_sheet(crops, labels, tile_size=512):
    """Arrange crop thumbnails in a horizontal strip with labels."""
    from PIL import ImageFont
    n = len(crops)
    sheet = Image.new('RGB', (tile_size * n, tile_size + 30), (20, 20, 20))
    for i, (crop, label) in enumerate(zip(crops, labels)):
        thumb = crop.convert('RGB').resize((tile_size, tile_size), Image.LANCZOS)
        sheet.paste(thumb, (i * tile_size, 0))
        draw = ImageDraw.Draw(sheet)
        draw.text((i * tile_size + 4, tile_size + 4), label, fill=(220, 220, 220))
    return sheet


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    lon_w, lon_e, lat_s, lat_n = args.bounds
    width = args.resolution
    aspect = (lat_n - lat_s) / (lon_e - lon_w)
    height = int(width * aspect)

    region_key = f'{int(lon_w)}_{int(lon_e)}_{int(lat_s)}_{int(lat_n)}'
    out_dir = os.path.abspath(OUTPUT_DIR)
    os.makedirs(out_dir, exist_ok=True)

    shp_path = args.shp if args.shp else GSHHG_L1
    source_label = args.source_label if args.source_label else os.path.basename(shp_path)

    print(f'[gshhg] Region: {region_key}  ({width}×{height} px)')
    print(f'[gshhg] Shapefile: {shp_path}')
    print(f'[gshhg] Source: {source_label}')

    # --- Phase 1a: Land mask ---
    print('[gshhg] Loading polygons from shapefile...')
    polys = []
    if os.path.exists(shp_path):
        sf = shapefile.Reader(shp_path)
        for sr in sf.iterShapeRecords():
            bb = sr.shape.bbox
            if bb[2] < lon_w or bb[0] > lon_e or bb[3] < lat_s or bb[1] > lat_n:
                continue
            pts = sr.shape.points
            parts = list(sr.shape.parts) + [len(pts)]
            rings = [pts[parts[i]:parts[i+1]] for i in range(len(parts) - 1)]
            if not rings or len(rings[0]) < 3:
                continue
            polys.append(rings)
    print(f'[gshhg] {len(polys)} polygons in region')

    print('[gshhg] Rasterizing land mask...')
    mask_img = draw_land_mask(polys, lon_w, lon_e, lat_s, lat_n, width, height)
    mask_arr = np.array(mask_img)

    # Coastline edge: derive from GSHHG mask boundary (morphological edge)
    # This gives more accurate edges than NE10m lines when GSHHG polygons are used
    print('[gshhg] Detecting coastline edges from mask...')
    mask_pil = Image.fromarray(mask_arr)
    # Dilate edges slightly for visibility at full resolution
    eroded = mask_pil.filter(ImageFilter.MinFilter(3))
    dilated = mask_pil.filter(ImageFilter.MaxFilter(3))
    # Edge = border between land and sea (pixels that change when eroded/dilated)
    edge_land = np.clip(mask_arr.astype(int) - np.array(eroded).astype(int), 0, 255)
    edge_sea = np.clip(np.array(dilated).astype(int) - mask_arr.astype(int), 0, 255)
    edge_arr = np.clip(edge_land + edge_sea, 0, 255).astype(np.uint8)

    # Composite: land=dark-blue, sea=midnight, coast=white
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    rgb[mask_arr > 128] = [120, 105, 85]   # land: warm grey-brown
    rgb[mask_arr <= 128] = [15, 30, 60]    # sea: dark navy
    rgb[edge_arr > 50] = [255, 255, 240]   # coastline: near-white

    mask_out = os.path.join(out_dir, 'gshhg_coastline_mask.png')
    Image.fromarray(rgb).save(mask_out)
    print(f'[gshhg] Saved: {mask_out}')

    # --- Phase 1b: Distance field ---
    print('[gshhg] Computing distance field...')
    dist_norm = compute_distance_field(mask_arr)

    # Colorize: deep sea=dark blue, coast=cyan-green, deep land=brown
    dist_rgb = np.zeros((height, width, 3), dtype=np.uint8)
    # Sea side (dist_norm < 0.5 in original combined, need to re-derive sea/land)
    land_px = mask_arr > 128
    dist_arr_full = np.abs(dist_norm - 0.5) * 2  # 0=coast in either direction

    # Sea: gradient dark blue → cyan near coast
    sea_t = np.clip(1.0 - dist_arr_full, 0, 1)
    dist_rgb[~land_px, 0] = (sea_t[~land_px] * 0 + (1 - sea_t[~land_px]) * 5).astype(np.uint8)
    dist_rgb[~land_px, 1] = (sea_t[~land_px] * 200 + (1 - sea_t[~land_px]) * 20).astype(np.uint8)
    dist_rgb[~land_px, 2] = (sea_t[~land_px] * 180 + (1 - sea_t[~land_px]) * 60).astype(np.uint8)

    # Land: gradient greenish near coast → brown inland
    land_t = np.clip(1.0 - dist_arr_full, 0, 1)
    dist_rgb[land_px, 0] = (land_t[land_px] * 80 + (1 - land_t[land_px]) * 140).astype(np.uint8)
    dist_rgb[land_px, 1] = (land_t[land_px] * 130 + (1 - land_t[land_px]) * 100).astype(np.uint8)
    dist_rgb[land_px, 2] = (land_t[land_px] * 60 + (1 - land_t[land_px]) * 60).astype(np.uint8)

    dist_out = os.path.join(out_dir, 'gshhg_distance_field.png')
    Image.fromarray(dist_rgb).save(dist_out)
    print(f'[gshhg] Saved: {dist_out}')

    # --- Phase 1c: Key crops ---
    print('[gshhg] Generating key crops...')
    mask_rgb = Image.fromarray(rgb)
    crops = []
    labels = []
    for crop_id, clon, clat, hspan in KEY_CROPS:
        if lon_w <= clon <= lon_e and lat_s <= clat <= lat_n:
            c = crop_region(mask_rgb, lon_w, lon_e, lat_s, lat_n, width, height, clon, clat, hspan)
            crops.append(c)
            labels.append(crop_id)

    if crops:
        sheet = make_contact_sheet(crops, labels)
        sheet_out = os.path.join(out_dir, 'key_crops_contact_sheet.png')
        sheet.save(sheet_out)
        print(f'[gshhg] Saved: {sheet_out}')
    else:
        print('[gshhg] No key crops within bounds')

    print('[gshhg] Phase 1 complete.')


if __name__ == '__main__':
    main()
