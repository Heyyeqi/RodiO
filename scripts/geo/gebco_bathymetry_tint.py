#!/usr/bin/env python3
"""
gebco_bathymetry_tint.py — GEBCO NetCDF bathymetry 5-level tint renderer

Depth levels:
  0 to -50m      shallow shelf / nearshore
  -50 to -200m   continental shelf
  -200 to -1500m upper slope / sea margin
  -1500 to -4000m abyssal plain approach
  <-4000m        deep trench / basin

Usage:
  python3 gebco_bathymetry_tint.py --bounds lon_w lon_e lat_s lat_n --nc path/to/gebco.nc
  python3 gebco_bathymetry_tint.py --bounds 118 150 22 50 --nc pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc
"""

import argparse
import sys
import os
import numpy as np
from PIL import Image

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '../../previews/rdl_v2_p0_gebco_gshhg_japan_benchmark')
ETOPO_PATH = os.path.join(os.path.dirname(__file__), '../../pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd')

# 5-level depth palette (R, G, B) — designed for dark globe compositing
DEPTH_PALETTE = [
    # (max_depth, color)
    (    0,  (180, 160, 120)),  # land / 0m — not used for ocean rendering
    (  -50,  ( 30,  90, 140)),  # 0 to -50m: shallow turquoise-navy
    ( -200,  ( 20,  65, 120)),  # -50 to -200m: shelf blue
    (-1500,  ( 12,  45,  95)),  # -200 to -1500m: slope deep blue
    (-4000,  (  6,  28,  70)),  # -1500 to -4000m: abyssal dark
    (  -99999, (  2,  12,  45)),  # < -4000m: trench ultra-dark
]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--bounds', nargs=4, type=float, required=True,
                   metavar=('lon_w', 'lon_e', 'lat_s', 'lat_n'))
    p.add_argument('--nc', type=str, help='Path to GEBCO NetCDF file')
    p.add_argument('--resolution', type=int, default=4096)
    return p.parse_args()


def load_gebco_nc(nc_path, lon_w, lon_e, lat_s, lat_n):
    """Load elevation data from GEBCO NetCDF, return (elevation_array, lon_arr, lat_arr)."""
    import netCDF4 as nc
    ds = nc.Dataset(nc_path)
    # GEBCO uses 'lon'/'lat' or 'x'/'y' depending on version
    lon_var = 'lon' if 'lon' in ds.variables else 'x'
    lat_var = 'lat' if 'lat' in ds.variables else 'y'
    elev_var = 'elevation' if 'elevation' in ds.variables else 'z'

    lons = np.array(ds.variables[lon_var][:])
    lats = np.array(ds.variables[lat_var][:])

    # Subset to bounding box
    lon_mask = (lons >= lon_w) & (lons <= lon_e)
    lat_mask = (lats >= lat_s) & (lats <= lat_n)
    lons_sub = lons[lon_mask]
    lats_sub = lats[lat_mask]
    elev = ds.variables[elev_var]
    lat_idx = np.where(lat_mask)[0]
    lon_idx = np.where(lon_mask)[0]
    elev_sub = np.array(elev[lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1], dtype=np.float32)
    if hasattr(elev_sub, 'filled'):
        elev_sub = elev_sub.filled(0)
    ds.close()

    # Ensure north-at-top (row 0 = highest latitude)
    if lats_sub[0] < lats_sub[-1]:  # south-to-north → flip
        elev_sub = np.flipud(elev_sub)
        lats_sub = lats_sub[::-1]

    return elev_sub, lons_sub, lats_sub


def load_etopo1_subset(lon_w, lon_e, lat_s, lat_n):
    """Load ETOPO1 .grd (GMT format) subset for comparison.
    ETOPO1 stores z as a flat 1D array (row-major, south-to-north, west-to-east).
    """
    import netCDF4 as nc
    if not os.path.exists(ETOPO_PATH):
        return None, None, None
    ds = nc.Dataset(ETOPO_PATH)
    dim = ds.variables['dimension'][:]
    W_e, H_e = int(dim[0]), int(dim[1])
    x_range = ds.variables['x_range'][:]
    y_range = ds.variables['y_range'][:]
    z_flat = ds.variables['z'][:].astype(np.float32)
    ds.close()

    # Reconstruct coordinate axes
    lons = np.linspace(float(x_range[0]), float(x_range[1]), W_e)
    lats = np.linspace(float(y_range[0]), float(y_range[1]), H_e)  # south → north

    # Reshape to 2D (H_e rows, W_e cols); row 0 = south
    z_2d = z_flat.reshape(H_e, W_e)

    # Subset to bounding box
    lon_mask = (lons >= lon_w) & (lons <= lon_e)
    lat_mask = (lats >= lat_s) & (lats <= lat_n)
    lons_sub = lons[lon_mask]
    lats_sub = lats[lat_mask]
    elev_sub = z_2d[np.ix_(lat_mask, lon_mask)]

    # Flip so row 0 = north (image convention)
    elev_sub = np.flipud(elev_sub)
    lats_sub = lats_sub[::-1]

    return elev_sub, lons_sub, lats_sub


def elevation_to_tint(elev_arr):
    """Map elevation values to 5-level bathymetry tint RGB."""
    h, w = elev_arr.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)

    # Land
    land = elev_arr >= 0
    rgb[land] = (130, 115, 90)

    # Depth levels (in order shallow → deep)
    rgb[(elev_arr < 0) & (elev_arr >= -50)]   = DEPTH_PALETTE[1][1]
    rgb[(elev_arr < -50) & (elev_arr >= -200)] = DEPTH_PALETTE[2][1]
    rgb[(elev_arr < -200) & (elev_arr >= -1500)] = DEPTH_PALETTE[3][1]
    rgb[(elev_arr < -1500) & (elev_arr >= -4000)] = DEPTH_PALETTE[4][1]
    rgb[elev_arr < -4000] = DEPTH_PALETTE[5][1]

    return rgb


def resize_to(arr_rgb, target_w, target_h):
    img = Image.fromarray(arr_rgb)
    return np.array(img.resize((target_w, target_h), Image.LANCZOS))


def add_depth_legend(rgb_arr):
    """Add a small depth legend bar to bottom-right."""
    img = Image.fromarray(rgb_arr)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    labels = [
        ('0 to -50m',       DEPTH_PALETTE[1][1]),
        ('-50 to -200m',    DEPTH_PALETTE[2][1]),
        ('-200 to -1500m',  DEPTH_PALETTE[3][1]),
        ('-1500 to -4000m', DEPTH_PALETTE[4][1]),
        ('< -4000m',        DEPTH_PALETTE[5][1]),
        ('Land',            (130, 115, 90)),
    ]
    x0 = rgb_arr.shape[1] - 200
    y0 = rgb_arr.shape[0] - (len(labels) * 22 + 10)
    for i, (label, color) in enumerate(labels):
        y = y0 + i * 22
        draw.rectangle([x0, y, x0 + 18, y + 16], fill=color)
        draw.text((x0 + 24, y), label, fill=(230, 230, 230))
    return np.array(img)


def make_side_by_side(left_rgb, right_rgb, left_label, right_label, target_h=2048):
    """Create a side-by-side comparison image."""
    lh, lw = left_rgb.shape[:2]
    rh, rw = right_rgb.shape[:2]
    # resize both to same height
    lw2 = int(lw * target_h / lh)
    rw2 = int(rw * target_h / rh)
    left_r = np.array(Image.fromarray(left_rgb).resize((lw2, target_h), Image.LANCZOS))
    right_r = np.array(Image.fromarray(right_rgb).resize((rw2, target_h), Image.LANCZOS))
    canvas = np.zeros((target_h + 30, lw2 + rw2 + 10, 3), dtype=np.uint8)
    canvas[:target_h, :lw2] = left_r
    canvas[:target_h, lw2 + 10:] = right_r
    img = Image.fromarray(canvas)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.text((10, target_h + 5), left_label, fill=(200, 200, 200))
    draw.text((lw2 + 20, target_h + 5), right_label, fill=(200, 200, 200))
    return np.array(img)


def main():
    args = parse_args()
    lon_w, lon_e, lat_s, lat_n = args.bounds
    region_key = f'{int(lon_w)}_{int(lon_e)}_{int(lat_s)}_{int(lat_n)}'
    out_dir = os.path.abspath(OUTPUT_DIR)
    os.makedirs(out_dir, exist_ok=True)

    # --- ETOPO1 comparison (always available) ---
    print('[gebco] Loading ETOPO1 for comparison...')
    etopo_elev, etopo_lons, etopo_lats = load_etopo1_subset(lon_w, lon_e, lat_s, lat_n)
    if etopo_elev is not None:
        print(f'[gebco] ETOPO1 subset shape: {etopo_elev.shape}')
        etopo_rgb = elevation_to_tint(etopo_elev)
        etopo_rgb = add_depth_legend(etopo_rgb)
        etopo_out = os.path.join(out_dir, 'etopo1_bathymetry_tint.png')
        Image.fromarray(etopo_rgb).save(etopo_out)
        print(f'[gebco] Saved ETOPO1 tint: {etopo_out}')
    else:
        print('[gebco] ETOPO1 not found, skipping')
        etopo_rgb = None

    # --- GEBCO (if provided) ---
    if args.nc:
        if not os.path.exists(args.nc):
            print(f'[gebco] NetCDF not found: {args.nc}')
            print('[gebco] Skipping GEBCO rendering — awaiting download confirmation')
        else:
            print(f'[gebco] Loading GEBCO from: {args.nc}')
            gebco_elev, gebco_lons, gebco_lats = load_gebco_nc(args.nc, lon_w, lon_e, lat_s, lat_n)
            print(f'[gebco] GEBCO subset shape: {gebco_elev.shape}')
            gebco_rgb = elevation_to_tint(gebco_elev)
            gebco_rgb = add_depth_legend(gebco_rgb)
            gebco_out = os.path.join(out_dir, 'gebco_bathymetry_tint.png')
            Image.fromarray(gebco_rgb).save(gebco_out)
            print(f'[gebco] Saved GEBCO tint: {gebco_out}')

            if etopo_rgb is not None:
                print('[gebco] Generating ETOPO1 vs GEBCO comparison...')
                comp = make_side_by_side(etopo_rgb, gebco_rgb,
                                         'ETOPO1 (1.85km/px)', 'GEBCO 2026 (450m/px)')
                comp_out = os.path.join(out_dir, 'etopo_vs_gebco_compare.png')
                Image.fromarray(comp).save(comp_out)
                print(f'[gebco] Saved comparison: {comp_out}')
    else:
        print('[gebco] No --nc provided; ETOPO1-only output complete')
        print('[gebco] Run with --nc <path> after GEBCO download is confirmed')

    print('[gebco] Phase 2 complete (partial if GEBCO not yet downloaded).')


if __name__ == '__main__':
    main()
