#!/usr/bin/env python3
"""render_texture.py — turn color_rgba.bin into the deliverable texture + preview.

Outputs (in temp/ocean_color_real/):
  global_watercolor_rgba.png    4096x2048 RGBA, land/cloud = transparent (DELIVERABLE)
  global_watercolor_preview.png  2048x1024 RGB preview on neutral backdrop;
                                  invalid pixels -> sentinel dark slate (shows mask)
"""
import json, os
import numpy as np
from PIL import Image

DIR = "temp/ocean_color_real"
meta = json.load(open(os.path.join(DIR, "grid_meta.json")))
W, H = meta["W"], meta["H"]
rgba = np.fromfile(os.path.join(DIR, "color_rgba.bin"), dtype=np.uint8).reshape(H, W, 4)
rgb = rgba[..., :3].copy()
alpha = rgba[..., 3]

# ---- deliverable: true RGBA (transparent where masked) ----
img_rgba = np.dstack([rgb, alpha]).astype(np.uint8)
Image.fromarray(img_rgba, "RGBA").save(os.path.join(DIR, "global_watercolor_rgba.png"))

# ---- preview: composite on neutral backdrop, sentinel for mask ----
ph, pw = 1024, 2048
sentinel = np.array([30, 34, 42], dtype=np.uint8)
backdrop = np.full((ph, pw, 3), 18, dtype=np.uint8)  # deep neutral
# downsample by nearest
step_r = H // ph; step_c = W // pw
prev = rgb[::step_r, ::step_c][:ph, :pw]
preva = alpha[::step_r, ::step_c][:ph, :pw]
out = backdrop.copy()
mask_px = preva == 0
out[~mask_px] = prev[~mask_px]
out[mask_px] = sentinel
Image.fromarray(out, "RGB").save(os.path.join(DIR, "global_watercolor_preview.png"))

n_invalid = int((alpha == 0).sum())
print(f"RGBA deliverable : global_watercolor_rgba.png  ({W}x{H})  transparent={n_invalid} ({100*n_invalid/(W*H):.1f}%)")
print(f"Preview          : global_watercolor_preview.png ({pw}x{ph})  sentinel=dark slate for masked")

# ---- validation cross-check ----
stats = json.load(open(os.path.join(DIR, "pipeline_stats.json")))
print("\n=== 5 validation points (real ocean-color tones) ===")
expect = {
  "South Pacific gyre (clear oligotrophic)": "blue (low CHL, high clarity)",
  "Sargasso / N Atlantic gyre (clear)": "blue",
  "Yangtze R. mouth (turbid estuary)": "yellow-brown (high SPM/turbidity)",
  "Amazon R. mouth (turbid estuary)": "yellow-brown",
  "Benguela upwelling (productive, high CHL)": "green-tinted (phytoplankton)",
}
ok = True
for name, s in stats["samples"].items():
    if s.get("hex"):
        print(f"  {name:42s} lat={s['lat']:>6} lon={s['lon']:>7}  {s['hex']}  expect: {expect[name]}")
    else:
        print(f"  {name:42s} lat={s['lat']:>6} lon={s['lon']:>7}  MASKED  ({s.get('note')})")
        ok = False
print(f"\nhue range: {stats['hueRange']['min']}..{stats['hueRange']['max']} deg")
print(f"clear(clarity>0.6)={stats['clearPixels']}  turbid(turbidity>0.3)={stats['turbidPixels']}")
