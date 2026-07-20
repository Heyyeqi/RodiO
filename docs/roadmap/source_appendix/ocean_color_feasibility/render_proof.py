#!/usr/bin/env python3
"""render_proof.py — turn colorfield.json into a PNG water-color texture proof."""
import json
import numpy as np
from PIL import Image

try:
    from PIL import Image
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "pillow"], check=True)
    from PIL import Image

d = json.load(open("colorfield.json"))
W, H, rgb = d["W"], d["H"], d["rgb"]
img = np.zeros((H, W, 3), dtype=np.uint8)
for i in range(H):
    for j in range(W):
        px = rgb[i][j]
        if px is None:
            img[i, j] = (10, 12, 18)        # ocean-mask / void -> near-black
        else:
            img[i, j] = (int(round(px[0]*255)), int(round(px[1]*255)), int(round(px[2]*255)))

out = "proof_watercolor_texture.png"
Image.fromarray(img, "RGB").save(out)
print(f"wrote {out}  ({W}x{H})  lat[{d['lat0']:.1f},{d['lat1']:.1f}] lon[{d['lon0']:.1f},{d['lon1']:.1f}]")
