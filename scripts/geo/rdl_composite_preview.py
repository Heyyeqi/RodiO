#!/usr/bin/env python3
"""
rdl_composite_preview.py — RDL v2 P0 minimal composite preview

Generates a 4-panel comparison:
  Panel A: baseline (earth day texture crop, no overlay)
  Panel B: GEBCO bathymetry tint only
  Panel C: GSHHG coastline edge clarity only
  Panel D: GEBCO + GSHHG combined

Usage:
  python3 rdl_composite_preview.py --bounds 118 150 22 50
"""

import argparse
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
OUTPUT_DIR = os.path.join(BASE_DIR, 'previews/rdl_v2_p0_gebco_gshhg_japan_benchmark')
SOURCE_DIR = os.path.join(BASE_DIR, 'pwa/assets/source')

# Day texture — use high-res source for cropping
DAY_TEXTURE_CANDIDATES = [
    os.path.join(SOURCE_DIR, 'earth_day_source_21600x10800.jpg'),
    os.path.join(BASE_DIR, 'pwa/assets/earth_day_8k.jpg'),
]

PREVIEW_W = 4096  # each panel width (before compositing into 2x2 grid)
PANEL_TILE = 1024  # final panel size in 2x2 grid


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--bounds', nargs=4, type=float, required=True,
                   metavar=('lon_w', 'lon_e', 'lat_s', 'lat_n'))
    return p.parse_args()


def lon_lat_to_img_px(lon, lat, img_w, img_h):
    """Convert lon/lat to pixel coordinates in equirectangular image (north-up)."""
    px = (lon + 180) / 360 * img_w
    py = (90 - lat) / 180 * img_h
    return px, py


def crop_equirect(img, lon_w, lon_e, lat_s, lat_n):
    """Crop equirectangular image to geographic bounds."""
    w, h = img.size
    x0, y0 = lon_lat_to_img_px(lon_w, lat_n, w, h)
    x1, y1 = lon_lat_to_img_px(lon_e, lat_s, w, h)
    return img.crop((int(x0), int(y0), int(x1), int(y1)))


def load_baseline(lon_w, lon_e, lat_s, lat_n):
    """Load the best available day texture and crop to region."""
    src = None
    for c in DAY_TEXTURE_CANDIDATES:
        if os.path.exists(c):
            src = c
            break
    if src is None:
        print('[composite] No day texture found — using synthetic baseline')
        # Synthetic fallback: blue gradient
        w = int((lon_e - lon_w) / 180 * 4096)
        h = int((lat_n - lat_s) / 90 * 2048)
        arr = np.zeros((h, w, 3), dtype=np.uint8)
        arr[:, :, 2] = 60
        return Image.fromarray(arr)
    print(f'[composite] Loading baseline from: {os.path.basename(src)}')
    Image.MAX_IMAGE_PIXELS = None  # large source textures are expected
    img = Image.open(src)
    return crop_equirect(img, lon_w, lon_e, lat_s, lat_n)


def load_panel(filename):
    """Load a preview panel PNG from OUTPUT_DIR if it exists."""
    path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(path):
        return Image.open(path).convert('RGB')
    return None


def blend_overlay(base, overlay, opacity=0.55):
    """Alpha-blend overlay onto base."""
    base_arr = np.array(base, dtype=np.float32)
    ov_arr = np.array(overlay.resize(base.size, Image.LANCZOS), dtype=np.float32)
    blended = base_arr * (1 - opacity) + ov_arr * opacity
    return Image.fromarray(blended.clip(0, 255).astype(np.uint8))


def extract_coastline_edges(coastline_mask_img, base_size):
    """Extract white edge pixels from coastline mask as an RGBA overlay."""
    mask = coastline_mask_img.convert('RGB').resize(base_size, Image.LANCZOS)
    arr = np.array(mask)
    # White pixels (>200 on all channels) are coastline edges
    edge = (arr[:, :, 0] > 200) & (arr[:, :, 1] > 200) & (arr[:, :, 2] > 200)
    # Build RGBA: edge pixels = cyan-white, rest = transparent
    rgba = np.zeros((*base_size[::-1], 4), dtype=np.uint8)
    rgba[edge, 0] = 220
    rgba[edge, 1] = 240
    rgba[edge, 2] = 255
    rgba[edge, 3] = 200
    return Image.fromarray(rgba, mode='RGBA')


def paste_coastline(base_rgb, coastline_rgba):
    base = base_rgb.convert('RGBA')
    base.paste(coastline_rgba, (0, 0), coastline_rgba)
    return base.convert('RGB')


def make_panel_grid(panels, labels, tile=PANEL_TILE):
    """Arrange 4 panels in a 2x2 grid with labels."""
    assert len(panels) == 4
    label_h = 28
    grid_w = tile * 2
    grid_h = tile * 2 + label_h * 2
    canvas = Image.new('RGB', (grid_w, grid_h), (10, 10, 10))
    draw = ImageDraw.Draw(canvas)
    positions = [(0, 0), (tile, 0), (0, tile + label_h), (tile, tile + label_h)]
    for i, (panel, label) in enumerate(zip(panels, labels)):
        thumb = panel.resize((tile, tile), Image.LANCZOS)
        x, y = positions[i]
        canvas.paste(thumb, (x, y))
        draw.text((x + 6, y + tile + 4), label, fill=(200, 200, 200))
    return canvas


def main():
    args = parse_args()
    lon_w, lon_e, lat_s, lat_n = args.bounds
    out_dir = os.path.abspath(OUTPUT_DIR)
    os.makedirs(out_dir, exist_ok=True)

    print(f'[composite] Bounds: {lon_w}°E–{lon_e}°E, {lat_s}°N–{lat_n}°N')

    # Panel A: baseline
    print('[composite] Building Panel A: baseline...')
    base = load_baseline(lon_w, lon_e, lat_s, lat_n)
    base_size = (PANEL_TILE * 2, int(PANEL_TILE * 2 * (lat_n - lat_s) / (lon_e - lon_w)))
    base = base.resize(base_size, Image.LANCZOS)

    # Panel B: GEBCO overlay
    gebco_mask = load_panel('gebco_bathymetry_tint.png')
    if gebco_mask is None:
        gebco_mask = load_panel('etopo1_bathymetry_tint.png')
        b_label = 'B: ETOPO1 tint (GEBCO pending)'
    else:
        b_label = 'B: GEBCO 2026 tint'

    if gebco_mask:
        panel_b = blend_overlay(base, gebco_mask, opacity=0.65)
    else:
        panel_b = base.copy()
        b_label = 'B: GEBCO (not yet downloaded)'

    # Panel C: GSHHG coastline edges only
    gshhg_mask = load_panel('gshhg_coastline_mask.png')
    if gshhg_mask:
        coast_rgba = extract_coastline_edges(gshhg_mask, base_size)
        panel_c = paste_coastline(base.copy(), coast_rgba)
        c_label = 'C: GSHHG coastline'
    else:
        panel_c = base.copy()
        c_label = 'C: GSHHG (not yet processed)'

    # Panel D: combined
    if gebco_mask and gshhg_mask:
        panel_d = blend_overlay(base, gebco_mask, opacity=0.55)
        coast_rgba2 = extract_coastline_edges(gshhg_mask, base_size)
        panel_d = paste_coastline(panel_d, coast_rgba2)
        d_label = 'D: GEBCO + GSHHG combined'
    elif gebco_mask:
        panel_d = panel_b.copy()
        d_label = 'D: GEBCO only (GSHHG pending)'
    elif gshhg_mask:
        panel_d = panel_c.copy()
        d_label = 'D: GSHHG only (GEBCO pending)'
    else:
        panel_d = base.copy()
        d_label = 'D: (both pending)'

    panels = [base, panel_b, panel_c, panel_d]
    labels = ['A: baseline', b_label, c_label, d_label]

    grid = make_panel_grid(panels, labels)
    out_path = os.path.join(out_dir, 'combined_gebco_gshhg_preview.png')
    grid.save(out_path)
    print(f'[composite] Saved 4-panel preview: {out_path}')
    print('[composite] Phase 3 complete.')


if __name__ == '__main__':
    main()
