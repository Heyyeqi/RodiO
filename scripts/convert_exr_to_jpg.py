#!/usr/bin/env python3
"""
Convert star/milkyway EXR textures to web-friendly JPEG.

Usage:
    python scripts/convert_exr_to_jpg.py

Output goes to pwa/assets/textures/stars/ alongside the source EXRs.

Requires:
    pip install OpenEXR Imath numpy Pillow
  OR (simpler, no OpenEXR C lib needed):
    pip install imageio[freeimage] numpy Pillow
  Fallback: uses ImageMagick `convert` CLI if Python EXR libs are absent.
"""

import os
import subprocess
import sys
from pathlib import Path

STARS_DIR = Path(__file__).parent.parent / "pwa" / "assets" / "textures" / "stars"

# Priority order: smallest → largest, skip gal variants if equatorial already done
TARGETS = [
    ("hiptyc_2020_8k.exr",       "hiptyc_2020_8k.jpg",       90),
    ("hiptyc_2020_8k_gal.exr",   "hiptyc_2020_8k_gal.jpg",   90),
    ("milkyway_2020_8k.exr",     "milkyway_2020_8k.jpg",     92),
    ("milkyway_2020_8k_gal.exr", "milkyway_2020_8k_gal.jpg", 92),
    ("starmap_2020_8k.exr",      "starmap_2020_8k.jpg",      92),
    ("starmap_2020_8k_gal.exr",  "starmap_2020_8k_gal.jpg",  92),
]


def _has_python_exr():
    try:
        import OpenEXR  # noqa: F401
        return True
    except ImportError:
        return False


def _has_imageio_freeimage():
    try:
        import imageio
        import imageio.plugins.freeimage  # noqa: F401
        return True
    except ImportError:
        return False


def _has_imagemagick():
    result = subprocess.run(["which", "magick"], capture_output=True)
    if result.returncode == 0:
        return "magick"
    result = subprocess.run(["which", "convert"], capture_output=True)
    return "convert" if result.returncode == 0 else None


def convert_via_openexr(src: Path, dst: Path, quality: int):
    import OpenEXR, Imath, numpy as np
    from PIL import Image

    print(f"  [OpenEXR] reading {src.name} …")
    exr = OpenEXR.InputFile(str(src))
    header = exr.header()
    dw = header["dataWindow"]
    w = dw.max.x - dw.min.x + 1
    h = dw.max.y - dw.min.y + 1

    FLOAT = Imath.PixelType(Imath.PixelType.FLOAT)
    r = np.frombuffer(exr.channel("R", FLOAT), dtype=np.float32).reshape(h, w)
    g = np.frombuffer(exr.channel("G", FLOAT), dtype=np.float32).reshape(h, w)
    b = np.frombuffer(exr.channel("B", FLOAT), dtype=np.float32).reshape(h, w)

    # Tone-map: reinhard on luminance, then gamma
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    scale = lum / (1.0 + lum + 1e-9)
    factor = np.where(lum > 1e-9, scale / (lum + 1e-9), 0.0)
    r, g, b = r * factor, g * factor, b * factor

    gamma = 2.2
    rgb = np.stack([
        np.clip(r ** (1 / gamma), 0, 1),
        np.clip(g ** (1 / gamma), 0, 1),
        np.clip(b ** (1 / gamma), 0, 1),
    ], axis=-1)

    img = Image.fromarray((rgb * 255).astype("uint8"), "RGB")
    img.save(str(dst), "JPEG", quality=quality, optimize=True)
    print(f"  → saved {dst.name} ({dst.stat().st_size / 1e6:.1f} MB)")


def convert_via_imagemagick(src: Path, dst: Path, quality: int, cmd: str):
    print(f"  [ImageMagick] converting {src.name} …")
    # -auto-level normalises HDR → 8-bit, -colorspace sRGB ensures correct gamma
    args = [
        cmd, str(src),
        "-auto-level",
        "-colorspace", "sRGB",
        "-quality", str(quality),
        str(dst),
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}")
        return False
    print(f"  → saved {dst.name} ({dst.stat().st_size / 1e6:.1f} MB)")
    return True


def main():
    print(f"Stars dir: {STARS_DIR}\n")

    # Detect available backend
    if _has_python_exr():
        backend = "openexr"
        print("Backend: OpenEXR (Python)")
    elif _has_imageio_freeimage():
        backend = "imageio"
        print("Backend: imageio + FreeImage")
    else:
        im_cmd = _has_imagemagick()
        if im_cmd:
            backend = "imagemagick"
            print(f"Backend: ImageMagick ({im_cmd})")
        else:
            print("ERROR: No EXR backend found.")
            print("Install one of:")
            print("  pip install OpenEXR Imath numpy Pillow")
            print("  brew install imagemagick")
            sys.exit(1)

    print()
    for exr_name, jpg_name, quality in TARGETS:
        src = STARS_DIR / exr_name
        dst = STARS_DIR / jpg_name

        if not src.exists():
            print(f"SKIP (not found): {exr_name}")
            continue
        if dst.exists():
            print(f"SKIP (exists):    {jpg_name}")
            continue

        print(f"Converting: {exr_name} → {jpg_name} (q={quality})")
        try:
            if backend == "openexr":
                convert_via_openexr(src, dst, quality)
            elif backend == "imagemagick":
                convert_via_imagemagick(src, dst, quality, im_cmd)
            else:
                print("  imageio backend not yet implemented, skipping")
        except Exception as e:
            print(f"  FAILED: {e}")

    print("\nDone.")


if __name__ == "__main__":
    main()
