"""
Generate a tangent-space normal map from ETOPO1 elevation TIFF.

Usage:
    python3.11 scripts/geo/gen_normalmap.py [--strength 0.004] [--out pwa/assets/earth_normal_8k.png]

Output: 8192×4096 RGB PNG, tangent-space encoded (R=X, G=Y, B=Z).
"""

import argparse
import numpy as np
import tifffile
from PIL import Image
from pathlib import Path

SRC = Path('d5b_processor_v3/source_cache/gee_global/exported_8k/etopo1_ice_surface_8192x4096.tif')
OCEAN_MASK = Path('pwa/assets/earth/masks/ocean_mask_4096x2048_soft.png')
DEFAULT_OUT = Path('pwa/assets/earth_normal_8k.png')

def load_elevation(path: Path) -> np.ndarray:
    elev = tifffile.imread(str(path)).astype(np.float32)
    # Replace nodata (< -8000) with sea level 0
    elev[elev < -8000] = 0.0
    return elev

def elevation_to_normalmap(elev: np.ndarray, strength: float) -> np.ndarray:
    """
    Compute tangent-space normal map from equirectangular elevation grid.
    strength: scales how steep the normals appear (0.002 = subtle, 0.01 = dramatic).
    """
    # Gradient in pixel units; wrap horizontally (longitude wraps at ±180°)
    dy, dx = np.gradient(elev)

    # Build unnormalised tangent-space vector: right-hand, Z up
    nx = -dx * strength
    ny = -dy * strength
    nz = np.ones_like(nx)

    # Normalise per-pixel
    length = np.sqrt(nx**2 + ny**2 + nz**2)
    nx /= length
    ny /= length
    nz /= length

    # Encode to uint8 RGB: [-1, 1] → [0, 255]
    r = np.clip((nx * 0.5 + 0.5) * 255, 0, 255).astype(np.uint8)
    g = np.clip((ny * 0.5 + 0.5) * 255, 0, 255).astype(np.uint8)
    b = np.clip((nz * 0.5 + 0.5) * 255, 0, 255).astype(np.uint8)

    return np.dstack([r, g, b])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--strength', type=float, default=0.004,
                        help='Normal exaggeration (default 0.004)')
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    print(f'[normalmap] loading elevation from {SRC}...')
    elev = load_elevation(SRC)
    print(f'[normalmap] shape={elev.shape}, range=[{elev.min():.0f}, {elev.max():.0f}] m')

    print(f'[normalmap] computing normals (strength={args.strength})...')
    rgb = elevation_to_normalmap(elev, args.strength)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Downscale to 4096×2048 — normals change gradually, half-res is sufficient
    img = Image.fromarray(rgb, 'RGB').resize((4096, 2048), Image.LANCZOS)

    # Mask ocean to flat normal (128,128,255): ocean floor bathymetry must not
    # appear as bumps on the sea surface when viewed from space
    print(f'[normalmap] applying ocean mask...')
    mask = np.array(Image.open(str(OCEAN_MASK)).resize((4096, 2048), Image.LANCZOS))
    land_w = (mask / 255.0)[..., np.newaxis]
    flat = np.array([[[128, 128, 255]]], dtype=np.float32)
    blended = np.array(img, dtype=np.float32) * land_w + flat * (1.0 - land_w)
    img = Image.fromarray(blended.clip(0, 255).astype(np.uint8), 'RGB')

    # Lossy WEBP q90: ~3 MB, artefacts invisible on a normal map
    out_webp = args.out.with_suffix('.webp')
    img.save(str(out_webp), format='WEBP', lossless=False, quality=90)
    size_mb = out_webp.stat().st_size / 1024 / 1024
    print(f'[normalmap] saved {out_webp} — {size_mb:.1f} MB')

if __name__ == '__main__':
    main()
