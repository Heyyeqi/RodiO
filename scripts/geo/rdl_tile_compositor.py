#!/usr/bin/env python3
"""
rdl_tile_compositor.py — RDL Regional Detail Layer tile compositor

Globally reusable via --bounds. No region-name hardcoding.
Tier A = 4096 output (high detail)
Tier B = 2048 output (standard)
Tier C = global auto (skip manual refinement layers)

Usage:
  python3 rdl_tile_compositor.py --bounds 118 150 22 50 --tier A \\
    --base <d5b_path> --visual-source <21k_path> \\
    --gebco-tint <gebco_tint_png> --etopo-tint <etopo_tint_png> \\
    --gshhg-mask <mask_png> --out <output_dir>
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from scipy.ndimage import distance_transform_edt

VERSION = "1.0.0"
SCRIPT_NAME = "rdl_tile_compositor.py"

# ─── Geometry ─────────────────────────────────────────────────────────────────

def equirect_crop_box(lon_w, lon_e, lat_s, lat_n, img_w, img_h):
    left   = round((lon_w + 180) / 360 * img_w)
    right  = round((lon_e + 180) / 360 * img_w)
    top    = round((90 - lat_n) / 180 * img_h)
    bottom = round((90 - lat_s) / 180 * img_h)
    return (left, top, right, bottom)

def tile_wh(lon_w, lon_e, lat_s, lat_n, base_width):
    h = round(base_width * (lat_n - lat_s) / (lon_e - lon_w))
    return base_width, h

def uv_bounds(lon_w, lon_e, lat_s, lat_n):
    return {
        "uMin": round((lon_w + 180) / 360, 6),
        "uMax": round((lon_e + 180) / 360, 6),
        "vMin": round((lat_s + 90) / 180, 6),
        "vMax": round((lat_n + 90) / 180, 6),
    }

def pixels_per_km(lon_w, lon_e, lat_s, lat_n, tw):
    mid = (lat_s + lat_n) / 2
    km_per_deg = 111.0 * np.cos(np.radians(mid))
    return tw / ((lon_e - lon_w) * km_per_deg)

def crop_box_in_tile(lon_l, lon_r, lat_b, lat_t, bounds, tw, th):
    lon_w, lon_e, lat_s, lat_n = bounds
    left   = round((lon_l - lon_w) / (lon_e - lon_w) * tw)
    right  = round((lon_r - lon_w) / (lon_e - lon_w) * tw)
    top    = round((lat_n - lat_t) / (lat_n - lat_s) * th)
    bottom = round((lat_n - lat_b) / (lat_n - lat_s) * th)
    left, top = max(0, left), max(0, top)
    right, bottom = min(tw, right), min(th, bottom)
    return (left, top, right, bottom)

# ─── Image utilities ──────────────────────────────────────────────────────────

def load_crop_resize(path, crop_box, target_wh):
    img = Image.open(path).convert('RGB')
    return np.array(img.crop(crop_box).resize(target_wh, Image.LANCZOS))

def save_png(arr, path, quality=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img = Image.fromarray(arr.astype(np.uint8))
    img.save(path)

def match_histogram_linear(source, reference):
    """Per-channel linear normalization to match reference mean/std."""
    result = np.empty_like(source, dtype=np.float32)
    for c in range(3):
        s = source[:, :, c].astype(np.float32)
        r = reference[:, :, c].astype(np.float32)
        s_std = s.std()
        if s_std < 1.0:
            result[:, :, c] = r.mean()
        else:
            result[:, :, c] = (s - s.mean()) / s_std * r.std() + r.mean()
    return np.clip(result, 0, 255).astype(np.uint8)

def apply_clarity(arr, mask, strength, radius=1.5, amount=80):
    """Unsharp mask at coastal zone pixels only."""
    img = Image.fromarray(arr.astype(np.uint8))
    sharp = np.array(img.filter(ImageFilter.UnsharpMask(radius=radius, percent=amount, threshold=2)))
    result = arr.astype(np.float32).copy()
    result[mask] = arr[mask].astype(np.float32) * (1 - strength) + sharp[mask].astype(np.float32) * strength
    return np.clip(result, 0, 255).astype(np.uint8)

def make_contact_sheet(images, labels, title, max_panel_w=1024):
    """Side-by-side contact sheet, all images rescaled to same height."""
    n = len(images)
    sample = images[0]
    h, w = sample.shape[:2]
    panel_w = min(max_panel_w, w)
    panel_h = round(panel_w * h / w)
    label_h = 28
    total_w = panel_w * n
    total_h = panel_h + label_h
    canvas = np.zeros((total_h, total_w, 3), dtype=np.uint8)
    canvas[:, :] = [30, 30, 30]
    pil_canvas = Image.fromarray(canvas)
    draw = ImageDraw.Draw(pil_canvas)
    for i, (img, lbl) in enumerate(zip(images, labels)):
        panel = Image.fromarray(img.astype(np.uint8)).resize((panel_w, panel_h), Image.LANCZOS)
        pil_canvas.paste(panel, (i * panel_w, 0))
        draw.text((i * panel_w + 4, panel_h + 4), lbl, fill=(220, 220, 220))
    if title:
        draw.text((4, panel_h + 4), title + " | ", fill=(180, 180, 100))
    return np.array(pil_canvas)

def make_comparison(cols, labels, max_panel_w=1024):
    """Alias for make_contact_sheet."""
    return make_contact_sheet(cols, labels, "", max_panel_w=max_panel_w)

# ─── Layer builders ───────────────────────────────────────────────────────────

def build_layer0(base_path, bounds, tw, th):
    lon_w, lon_e, lat_s, lat_n = bounds
    img = Image.open(base_path).convert('RGB')
    iw, ih = img.size
    box = equirect_crop_box(lon_w, lon_e, lat_s, lat_n, iw, ih)
    print(f"  [L0] d5b crop box {box}, native {box[2]-box[0]}×{box[3]-box[1]} → {tw}×{th}")
    return np.array(img.crop(box).resize((tw, th), Image.LANCZOS))

def build_layer1(visual_path, bounds, tw, th, reference):
    lon_w, lon_e, lat_s, lat_n = bounds
    Image.MAX_IMAGE_PIXELS = 250_000_000  # allow 21.6K source (233M px)
    img = Image.open(visual_path).convert('RGB')
    iw, ih = img.size
    box = equirect_crop_box(lon_w, lon_e, lat_s, lat_n, iw, ih)
    native_w, native_h = box[2]-box[0], box[3]-box[1]
    print(f"  [L1] 21.6K crop box {box}, native {native_w}×{native_h} → {tw}×{th}")
    print(f"  [L1] Note: {native_w}×{native_h} upsampled {round(tw/native_w,1)}×, not true 4096 land detail")
    resized = np.array(img.crop(box).resize((tw, th), Image.LANCZOS))
    matched = match_histogram_linear(resized, reference)
    return matched, native_w, native_h

def build_layer2(tint_path, tw, th):
    img = Image.open(tint_path).convert('RGB')
    print(f"  [L2] GEBCO tint {img.size} → {tw}×{th}")
    return np.array(img.resize((tw, th), Image.LANCZOS))

def build_gshhg(mask_path, tw, th):
    # Mask encoding: sea=(15,30,60), land=(120,105,85), coast_edge=(255,255,240)
    # Use red channel thresholds: sea<50, land 50–200, coast_edge>200
    img = Image.open(mask_path).convert('RGB')
    if img.size != (tw, th):
        img = img.resize((tw, th), Image.NEAREST)
    arr = np.array(img)
    red = arr[:, :, 0]
    coast_edge = red > 200
    land  = (red > 50) & ~coast_edge
    ocean = ~land & ~coast_edge
    print(f"  [GSHHG] land {100*land.mean():.1f}%, ocean {100*ocean.mean():.1f}%, "
          f"coast_edge {100*coast_edge.mean():.2f}%")
    return arr, land, ocean

def build_coastal_zone(land, ppkm, zone_km):
    print(f"  [L3] computing coastal zone {zone_km}km ({round(zone_km*ppkm,1)} px)...")
    ocean_dist = distance_transform_edt(land.astype(np.uint8))
    land_dist  = distance_transform_edt((~land).astype(np.uint8))
    zone_px = zone_km * ppkm
    coastal = (
        ((ocean_dist > 0) & (ocean_dist < zone_px)) |
        ((land_dist  > 0) & (land_dist  < zone_px))
    )
    print(f"  [L3] coastal zone pixels: {coastal.sum():,} ({100*coastal.mean():.2f}%)")
    return coastal

# ─── Composite ────────────────────────────────────────────────────────────────

def composite(base, layer1, tint, land, ocean, coastal,
              visual_blend, gebco_blend, gshhg_strength):
    result = base.astype(np.float32)

    # Layer 1: visual texture compensation — land only
    if layer1 is not None and visual_blend > 0:
        result[land] = (result[land] * (1 - visual_blend)
                        + layer1[land].astype(np.float32) * visual_blend)

    # Layer 2: GEBCO tint — ocean only
    result[ocean] = (result[ocean] * (1 - gebco_blend)
                     + tint[ocean].astype(np.float32) * gebco_blend)

    result = np.clip(result, 0, 255).astype(np.uint8)

    # Layer 3: GSHHG coastal clarity (both sides of coast)
    if gshhg_strength > 0 and coastal is not None:
        result = apply_clarity(result, coastal, gshhg_strength)

    return result

# ─── Crop comparison ──────────────────────────────────────────────────────────

CROP_REGIONS = [
    ("crop_01_japan_sea_basin",        "Japan Sea Basin",       130, 140, 37, 43),
    ("crop_02_japan_trench",           "Japan Trench",          141, 149, 33, 40),
    ("crop_03_east_china_shelf",       "East China Shelf",      119, 128, 25, 32),
    ("crop_04_okinawa_trough_ryukyu",  "Okinawa Trough/Ryukyu", 122, 132, 23, 29),
    ("crop_05_tokyo_bay",              "Tokyo Bay",             138.5, 141.0, 34.5, 36.5),
    ("crop_06_osaka_seto",             "Osaka/Seto Inland Sea", 132.0, 137.0, 33.0, 36.0),
    ("crop_07_ise_bay",                "Ise Bay",               135.5, 138.5, 33.5, 35.5),
    ("crop_08_ryukyu_islands",         "Ryukyu Islands",        123.0, 131.0, 24.0, 28.0),
    ("crop_09_kyushu_west",            "Kyushu West",           127.0, 132.0, 30.0, 34.0),
]

def make_crop_compare(tiles_dict, crop_name, label, lon_l, lon_r, lat_b, lat_t,
                      bounds, tw, th, out_dir, max_panel_w=640):
    box = crop_box_in_tile(lon_l, lon_r, lat_b, lat_t, bounds, tw, th)
    bw, bh = box[2]-box[0], box[3]-box[1]
    if bw < 4 or bh < 4:
        print(f"  [crop] {crop_name}: too small ({bw}×{bh}), skipping")
        return
    panels = []
    lbls = []
    for key, arr in tiles_dict.items():
        crop = arr[box[1]:box[3], box[0]:box[2]]
        panels.append(crop)
        lbls.append(key)
    sheet = make_contact_sheet(panels, lbls, label, max_panel_w=max_panel_w)
    save_png(sheet, os.path.join(out_dir, f"{crop_name}_compare.png"))
    print(f"  [crop] {crop_name}: {bw}×{bh} px per panel")

# ─── UV bounds outline ────────────────────────────────────────────────────────

def make_uv_outline(base_path, bounds, out_path, color=(255, 60, 60), thickness=6):
    lon_w, lon_e, lat_s, lat_n = bounds
    img = Image.open(base_path).convert('RGB')
    iw, ih = img.size
    box = equirect_crop_box(lon_w, lon_e, lat_s, lat_n, iw, ih)
    draw = ImageDraw.Draw(img)
    l, t, r, b = box
    for i in range(thickness):
        draw.rectangle([l+i, t+i, r-i, b-i], outline=color)
    # Downscale for readability
    preview_w = 2160
    preview_h = round(ih * preview_w / iw)
    img = img.resize((preview_w, preview_h), Image.LANCZOS)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path)
    print(f"  [UV outline] saved {out_path}")

# ─── Demo HTML ────────────────────────────────────────────────────────────────

def write_demo_html(out_path, uv, region_key):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>RDL v2 Japan Visual Tile — Isolated Prototype Demo</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0a0a0a; color:#ccc; font-family:monospace; overflow:hidden; }}
#canvas {{ display:block; }}
#hud {{
  position:fixed; top:12px; left:12px;
  background:rgba(0,0,0,0.7); padding:10px 14px; border-radius:6px;
  font-size:12px; line-height:1.8; pointer-events:none;
}}
#controls {{
  position:fixed; bottom:12px; left:50%; transform:translateX(-50%);
  background:rgba(0,0,0,0.75); padding:10px 16px; border-radius:8px;
  display:flex; gap:12px; align-items:center; font-size:12px; flex-wrap:wrap;
}}
.group {{ display:flex; gap:6px; align-items:center; }}
.group label {{ color:#999; margin-right:4px; }}
button {{
  background:#222; color:#bbb; border:1px solid #444;
  padding:4px 10px; border-radius:4px; cursor:pointer; font-size:11px;
}}
button.active {{ background:#2a4a6a; color:#7af; border-color:#4a8aaa; }}
input[type=range] {{ width:120px; }}
#notice {{
  position:fixed; top:12px; right:12px; max-width:320px;
  background:rgba(180,80,0,0.85); color:#fff; padding:10px 14px;
  border-radius:6px; font-size:11px; line-height:1.6;
}}
</style>
</head>
<body>
<canvas id="canvas"></canvas>
<div id="hud">
  <div id="fps">FPS: --</div>
  <div id="info-tile">Tile: --</div>
  <div id="info-blend">Blend: --</div>
  <div id="info-dist">Camera dist: --</div>
  <div id="info-uv" style="color:#666;font-size:10px">
    UV [{uv['uMin']}, {uv['uMax']}] × [{uv['vMin']}, {uv['vMax']}]
  </div>
</div>
<div id="notice">
  ⚠ ISOLATED PROTOTYPE DEMO<br>
  For visual validation only. Not earth3d.js integration.<br>
  Not final Japan high-quality texture. Not RodiO production.<br>
  4096 new detail = GEBCO bathy + GSHHG coast only.<br>
  Land terrain = d5b 8K upsampled (~5.6×), no DEM.
</div>
<div id="controls">
  <div class="group">
    <label>Tile:</label>
    <button id="btn-baseline" onclick="setTile('baseline')">baseline</button>
    <button id="btn-etopo" onclick="setTile('etopo_reference')">etopo_ref</button>
    <button id="btn-v2_2048" onclick="setTile('v2_2048')">v2 2048</button>
    <button id="btn-v2_4096" class="active" onclick="setTile('v2_4096')">v2 4096</button>
  </div>
  <div class="group">
    <label>Blend:</label>
    <input type="range" id="blend-slider" min="0" max="1" step="0.05" value="1"
           oninput="setBlend(this.value)">
    <span id="blend-val">1.00</span>
  </div>
  <div class="group">
    <label>Dist:</label>
    <button onclick="setDist(1.50)">1.50</button>
    <button onclick="setDist(1.35)">1.35</button>
    <button onclick="setDist(1.25)">1.25</button>
  </div>
</div>

<script src="https://unpkg.com/three@0.128.0/build/three.min.js"></script>
<script>
const UV_REGION = {{ x: {uv['uMin']}, y: {uv['uMax']}, z: {uv['vMin']}, w: {uv['vMax']} }};
const TILES = {{
  baseline:       '../02_tiles/baseline_d5b_crop_2048.png',
  etopo_reference:'../02_tiles/etopo_reference_2048.png',
  v2_2048:        '../02_tiles/v2_gebco_gshhg_tile_2048.png',
  v2_4096:        '../02_tiles/v2_gebco_gshhg_tile_4096.png',
}};
const BASE_TEX_PATH = '../../../pwa/assets/earth/candidates/d5b_design_v3_2_1_8192x4096.jpg';

const VS = `
varying vec2 vUv;
void main() {{
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0);
}}`;

const FS = `
uniform sampler2D uBase;
uniform sampler2D uTile;
uniform float uBlend;
uniform vec4 uRegion;
varying vec2 vUv;
void main() {{
  vec4 base = texture2D(uBase, vUv);
  float u = vUv.x;
  float v = vUv.y;
  float fw = 0.003;
  float mu = smoothstep(uRegion.x, uRegion.x+fw, u)
           * smoothstep(uRegion.y, uRegion.y-fw, u);
  float mv = smoothstep(uRegion.z, uRegion.z+fw, v)
           * smoothstep(uRegion.w, uRegion.w-fw, v);
  float mask = mu * mv;
  float tu = (u - uRegion.x) / (uRegion.y - uRegion.x);
  float tv = (v - uRegion.z) / (uRegion.w - uRegion.z);
  vec4 tile = texture2D(uTile, vec2(clamp(tu,0.,1.), clamp(tv,0.,1.)));
  gl_FragColor = mix(base, tile, mask * uBlend);
}}`;

const renderer = new THREE.WebGLRenderer({{ canvas: document.getElementById('canvas'), antialias:true }});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.setSize(innerWidth, innerHeight);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, innerWidth/innerHeight, 0.01, 100);
camera.position.z = 1.50;

const loader = new THREE.TextureLoader();
loader.crossOrigin = 'anonymous';

const uniforms = {{
  uBase:   {{ value: null }},
  uTile:   {{ value: null }},
  uBlend:  {{ value: 1.0 }},
  uRegion: {{ value: new THREE.Vector4(UV_REGION.x, UV_REGION.y, UV_REGION.z, UV_REGION.w) }},
}};

const geo = new THREE.SphereGeometry(1, 64, 48);
const mat = new THREE.ShaderMaterial({{ vertexShader:VS, fragmentShader:FS, uniforms }});
const globe = new THREE.Mesh(geo, mat);
scene.add(globe);

let tileTexCache = {{}};
let currentTile = 'v2_4096';
let frameCount=0, lastFpsTime=performance.now(), fps=0;

function loadTex(path, cb) {{
  if (tileTexCache[path]) {{ cb(tileTexCache[path]); return; }}
  loader.load(path, t => {{ tileTexCache[path]=t; cb(t); }});
}}

loadTex(BASE_TEX_PATH, t => {{ uniforms.uBase.value = t; }});
function setTile(name) {{
  currentTile = name;
  document.querySelectorAll('button[id^=btn-]').forEach(b=>b.classList.remove('active'));
  const btn = document.getElementById('btn-'+name.replace('_','_'));
  // map button IDs
  const btnMap={{'baseline':'btn-baseline','etopo_reference':'btn-etopo','v2_2048':'btn-v2_2048','v2_4096':'btn-v2_4096'}};
  document.getElementById(btnMap[name])?.classList.add('active');
  loadTex(TILES[name], t => {{ uniforms.uTile.value = t; }});
  document.getElementById('info-tile').textContent = 'Tile: '+name;
}}
function setBlend(v) {{
  uniforms.uBlend.value = parseFloat(v);
  document.getElementById('blend-val').textContent = parseFloat(v).toFixed(2);
  document.getElementById('info-blend').textContent = 'Blend: '+parseFloat(v).toFixed(2);
}}
function setDist(d) {{
  camera.position.z = d;
  document.getElementById('info-dist').textContent = 'Camera dist: '+d;
}}

setTile('v2_4096');
setDist(1.50);

let isDragging=false, prevMouse={{x:0,y:0}};
renderer.domElement.addEventListener('mousedown', e=>{{ isDragging=true; prevMouse={{x:e.clientX,y:e.clientY}}; }});
window.addEventListener('mouseup', ()=>isDragging=false);
window.addEventListener('mousemove', e=>{{
  if(!isDragging) return;
  globe.rotation.y += (e.clientX-prevMouse.x)*0.005;
  globe.rotation.x += (e.clientY-prevMouse.y)*0.005;
  prevMouse={{x:e.clientX,y:e.clientY}};
}});
renderer.domElement.addEventListener('wheel', e=>{{
  camera.position.z = Math.max(1.15, Math.min(3.0, camera.position.z+e.deltaY*0.001));
  document.getElementById('info-dist').textContent='Camera dist: '+camera.position.z.toFixed(2);
  e.preventDefault();
}}, {{passive:false}});
window.addEventListener('resize', ()=>{{
  renderer.setSize(innerWidth,innerHeight);
  camera.aspect=innerWidth/innerHeight; camera.updateProjectionMatrix();
}});

(function animate() {{
  requestAnimationFrame(animate);
  globe.rotation.y += 0.0008;
  renderer.render(scene, camera);
  frameCount++;
  const now=performance.now();
  if(now-lastFpsTime>=500) {{
    fps=Math.round(frameCount*1000/(now-lastFpsTime));
    document.getElementById('fps').textContent='FPS: '+fps;
    frameCount=0; lastFpsTime=now;
  }}
}})();
</script>
</body>
</html>
"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        f.write(html)
    print(f"  [demo] wrote {out_path}")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="RDL Regional Detail Layer tile compositor")
    ap.add_argument('--bounds', nargs=4, type=float, required=True,
                    metavar=('LON_W','LON_E','LAT_S','LAT_N'))
    ap.add_argument('--tier', choices=['A','B','C'], default='A')
    ap.add_argument('--base', required=True, help='d5b base texture path')
    ap.add_argument('--visual-source', required=True, help='21.6K source texture path')
    ap.add_argument('--gebco-tint', required=True, help='Pre-generated GEBCO tint PNG')
    ap.add_argument('--etopo-tint', default=None, help='ETOPO1 tint PNG for reference composite')
    ap.add_argument('--gshhg-mask', required=True, help='GSHHG land mask PNG (white=land)')
    ap.add_argument('--out', required=True, help='Output root directory')
    ap.add_argument('--gebco-blend', type=float, default=0.35)
    ap.add_argument('--gshhg-zone-km', type=float, default=10.0)
    ap.add_argument('--gshhg-strength', type=float, default=0.15)
    ap.add_argument('--visual-blend', type=float, default=0.30)
    args = ap.parse_args()

    t_start = time.time()
    generated_at = datetime.now(timezone.utc).isoformat()

    lon_w, lon_e, lat_s, lat_n = args.bounds
    bounds = (lon_w, lon_e, lat_s, lat_n)
    region_key = f"{int(lon_w)}_{int(lon_e)}_{int(lat_s)}_{int(lat_n)}"
    TIER_WIDTHS = {'A': 4096, 'B': 2048, 'C': 2048}
    tw, th = tile_wh(lon_w, lon_e, lat_s, lat_n, TIER_WIDTHS[args.tier])
    ppkm = pixels_per_km(lon_w, lon_e, lat_s, lat_n, tw)
    uv = uv_bounds(lon_w, lon_e, lat_s, lat_n)

    d = args.out
    L = os.path.join(d, '01_layers')
    T = os.path.join(d, '02_tiles')
    DM = os.path.join(d, '03_demo')
    C = os.path.join(d, '04_crops')
    R = os.path.join(d, '05_reports')
    for sub in [L, T, DM, C, R]:
        os.makedirs(sub, exist_ok=True)

    print(f"\n=== RDL Tile Compositor v{VERSION} ===")
    print(f"region_key: {region_key}  bounds: {bounds}")
    print(f"tier: {args.tier}  target: {tw}×{th}  ppkm: {ppkm:.2f}")
    print(f"params: gebco_blend={args.gebco_blend}  gshhg_zone={args.gshhg_zone_km}km  "
          f"gshhg_str={args.gshhg_strength}  visual_blend={args.visual_blend}\n")

    # ── Load all layers ──
    print("[L0] Building baseline d5b crop...")
    layer0 = build_layer0(args.base, bounds, tw, th)
    save_png(layer0, os.path.join(L, 'layer0_baseline_d5b_crop.png'))

    print("[L1] Building visual texture compensation...")
    layer1, native_w, native_h = build_layer1(
        args.visual_source, bounds, tw, th, layer0)
    save_png(layer1, os.path.join(L, 'layer1_visual_texture_matched.png'))

    print("[L2] Loading GEBCO tint...")
    gebco_tint = build_layer2(args.gebco_tint, tw, th)
    save_png(gebco_tint, os.path.join(L, f'layer2_gebco_bathymetry_tint_{int(args.gebco_blend*100):03d}.png'))

    print("[GSHHG] Loading mask...")
    gshhg_arr, land, ocean = build_gshhg(args.gshhg_mask, tw, th)

    print("[L3] Building GSHHG coastal zone clarity...")
    coastal_main = build_coastal_zone(land, ppkm, args.gshhg_zone_km)
    # Visualize coastal zone
    zone_vis = layer0.copy()
    zone_vis[coastal_main] = np.clip(
        zone_vis[coastal_main].astype(np.float32) * 0.5 + np.array([0, 120, 200], dtype=np.float32) * 0.5,
        0, 255).astype(np.uint8)
    save_png(zone_vis, os.path.join(L, f'layer3_gshhg_clarity_{int(args.gshhg_zone_km):02d}km_{int(args.gshhg_strength*100):03d}.png'))

    # ── Main composites ──
    print("\n[composite] Building main v2 tile...")
    v2_4096 = composite(layer0, layer1, gebco_tint, land, ocean, coastal_main,
                        args.visual_blend, args.gebco_blend, args.gshhg_strength)
    save_png(v2_4096, os.path.join(T, 'v2_gebco_gshhg_tile_4096.png'))
    print(f"  [tile] v2_4096 saved ({tw}×{th})")

    # 2048 version — re-run at Tier B resolution
    tw2, th2 = tile_wh(lon_w, lon_e, lat_s, lat_n, 2048)
    ppkm2 = pixels_per_km(lon_w, lon_e, lat_s, lat_n, tw2)
    print("[composite] Building v2 2048 tile...")
    layer0_2k = build_layer0(args.base, bounds, tw2, th2)
    layer1_2k, _, _ = build_layer1(args.visual_source, bounds, tw2, th2, layer0_2k)
    gebco_2k = build_layer2(args.gebco_tint, tw2, th2)
    gshhg_2k, land_2k, ocean_2k = build_gshhg(args.gshhg_mask, tw2, th2)
    coastal_2k = build_coastal_zone(land_2k, ppkm2, args.gshhg_zone_km)
    v2_2048 = composite(layer0_2k, layer1_2k, gebco_2k, land_2k, ocean_2k, coastal_2k,
                        args.visual_blend, args.gebco_blend, args.gshhg_strength)
    save_png(v2_2048, os.path.join(T, 'v2_gebco_gshhg_tile_2048.png'))
    print(f"  [tile] v2_2048 saved ({tw2}×{th2})")

    # Baseline tiles for demo
    save_png(layer0, os.path.join(T, 'baseline_d5b_crop_4096.png'))
    v2_2048_scale = np.array(Image.fromarray(layer0).resize((tw2, th2), Image.LANCZOS))
    save_png(v2_2048_scale, os.path.join(T, 'baseline_d5b_crop_2048.png'))

    # etopo_reference composite
    if args.etopo_tint and os.path.exists(args.etopo_tint):
        print("[etopo_ref] Building etopo_reference composite...")
        etopo_t = build_layer2(args.etopo_tint, tw, th)
        etopo_ref = composite(layer0, layer1, etopo_t, land, ocean, coastal_main,
                              args.visual_blend, args.gebco_blend, args.gshhg_strength)
        save_png(etopo_ref, os.path.join(T, 'etopo_reference_4096.png'))
        etopo_2k = build_layer2(args.etopo_tint, tw2, th2)
        etopo_ref_2k = composite(layer0_2k, layer1_2k, etopo_2k, land_2k, ocean_2k, coastal_2k,
                                 args.visual_blend, args.gebco_blend, args.gshhg_strength)
        save_png(etopo_ref_2k, os.path.join(T, 'etopo_reference_2048.png'))
    else:
        etopo_ref = layer0.copy()
        etopo_ref_2k = v2_2048_scale.copy()
        save_png(etopo_ref, os.path.join(T, 'etopo_reference_4096.png'))
        save_png(etopo_ref_2k, os.path.join(T, 'etopo_reference_2048.png'))
        print("  [etopo_ref] etopo tint not found, using baseline as placeholder")

    # ── Comparison images ──
    print("\n[compare] baseline vs etopo_reference vs v2...")
    # Downsample for comparison display
    DW = 1024
    def ds(a, w=DW):
        h = round(a.shape[0] * w / a.shape[1])
        return np.array(Image.fromarray(a.astype(np.uint8)).resize((w,h), Image.LANCZOS))

    comp_main = make_contact_sheet(
        [ds(layer0), ds(etopo_ref), ds(v2_2048, 1024), ds(v2_4096)],
        ['baseline', 'etopo_reference', 'v2_2048', 'v2_4096'],
        "", max_panel_w=1024)
    save_png(comp_main, os.path.join(T, 'baseline_vs_etopo_vs_v2_compare.png'))

    comp_res = make_contact_sheet(
        [ds(v2_2048, 2048), ds(v2_4096, 2048)],
        ['v2_2048', 'v2_4096'],
        "2048 vs 4096 (displayed at same 2048px width)", max_panel_w=2048)
    save_png(comp_res, os.path.join(T, 'tile_2048_vs_4096_compare.png'))

    # ── GEBCO blend contact sheet ──
    print("\n[contact] GEBCO blend variations (0.25/0.35/0.40)...")
    blend_panels, blend_labels = [], []
    for gb in [0.25, 0.35, 0.40]:
        v = composite(layer0, layer1, gebco_tint, land, ocean, coastal_main,
                      args.visual_blend, gb, args.gshhg_strength)
        blend_panels.append(ds(v))
        blend_labels.append(f'gebco_blend={gb}')
    save_png(make_contact_sheet(blend_panels, blend_labels, "GEBCO blend", max_panel_w=1024),
             os.path.join(T, 'gebco_blend_contact_sheet.png'))

    # ── GSHHG zone contact sheet ──
    print("[contact] GSHHG zone variations (5/10/20km)...")
    zone_panels, zone_labels = [], []
    for zk in [5.0, 10.0, 20.0]:
        cz = build_coastal_zone(land, ppkm, zk)
        v = composite(layer0, layer1, gebco_tint, land, ocean, cz,
                      args.visual_blend, args.gebco_blend, args.gshhg_strength)
        zone_panels.append(ds(v))
        zone_labels.append(f'zone={int(zk)}km')
    save_png(make_contact_sheet(zone_panels, zone_labels, "GSHHG zone", max_panel_w=1024),
             os.path.join(T, 'gshhg_zone_contact_sheet.png'))

    # ── GSHHG strength contact sheet ──
    print("[contact] GSHHG strength variations (0.10/0.15/0.20)...")
    str_panels, str_labels = [], []
    for gs in [0.10, 0.15, 0.20]:
        v = composite(layer0, layer1, gebco_tint, land, ocean, coastal_main,
                      args.visual_blend, args.gebco_blend, gs)
        str_panels.append(ds(v))
        str_labels.append(f'gshhg_str={gs}')
    save_png(make_contact_sheet(str_panels, str_labels, "GSHHG strength", max_panel_w=1024),
             os.path.join(T, 'gshhg_strength_contact_sheet.png'))

    # ── Layer stack contact sheet ──
    print("[contact] Layer stack contact sheet...")
    stack_sheet = make_contact_sheet(
        [ds(layer0), ds(layer1), ds(gebco_tint), ds(zone_vis), ds(v2_4096)],
        ['L0: d5b_base', 'L1: visual_texture', 'L2: gebco_tint', 'L3: coastal_zone', 'composite'],
        "Layer stack", max_panel_w=1024)
    save_png(stack_sheet, os.path.join(L, 'layer_stack_contact_sheet.png'))

    # ── Crop comparisons ──
    print("\n[crops] Generating 9 crop comparisons...")
    tiles_4panel = {
        'baseline': layer0,
        'etopo_reference': etopo_ref,
        'v2_2048': np.array(Image.fromarray(v2_2048).resize((tw, th), Image.LANCZOS)),
        'v2_4096': v2_4096,
    }
    for fname, label, lon_l, lon_r, lat_b, lat_t in CROP_REGIONS:
        make_crop_compare(tiles_4panel, fname, label, lon_l, lon_r, lat_b, lat_t,
                          bounds, tw, th, C)

    # ── UV bounds outline ──
    print("\n[UV outline] Generating bounds verification image...")
    make_uv_outline(args.base,
                    bounds,
                    os.path.join(DM, 'demo_uv_bounds_outline.png'))

    # ── Demo HTML ──
    print("[demo] Writing demo HTML...")
    write_demo_html(os.path.join(DM, 'demo_japan_v2_tile.html'), uv, region_key)

    # ── metadata.json ──
    elapsed = round(time.time() - t_start, 1)
    cmd = (f"python3 scripts/geo/rdl_tile_compositor.py "
           f"--bounds {lon_w} {lon_e} {lat_s} {lat_n} --tier {args.tier} "
           f"--gebco-blend {args.gebco_blend} --gshhg-zone-km {args.gshhg_zone_km} "
           f"--gshhg-strength {args.gshhg_strength} --visual-blend {args.visual_blend}")
    meta = {
        "region_key": region_key,
        "bounds": {"lon_w": lon_w, "lon_e": lon_e, "lat_s": lat_s, "lat_n": lat_n},
        "uv_bounds": uv,
        "output_sizes": [f"{tw}x{th}", f"{tw2}x{th2}"],
        "tier": args.tier,
        "data_sources": {
            "base_texture": os.path.relpath(args.base, d),
            "visual_source_21k": os.path.relpath(args.visual_source, d),
            "gebco_2026_tint_png": os.path.relpath(args.gebco_tint, d),
            "etopo1_reference_png": os.path.relpath(args.etopo_tint, d) if args.etopo_tint else None,
            "gshhg_mask_png": os.path.relpath(args.gshhg_mask, d),
            "gshhg_source": "GSHHG 2.3.7 full resolution (GSHHS_f_L1.shp, ~25m accuracy). "
                            "L1 = Level 1 land boundary polygons (not low-resolution; "
                            "'f' prefix = full resolution). 7820 polygons in Japan region."
        },
        "blends": {
            "visual_texture_blend": args.visual_blend,
            "gebco_blend": args.gebco_blend,
            "gshhg_zone_km": args.gshhg_zone_km,
            "gshhg_strength": args.gshhg_strength
        },
        "layer1_upsampling_note": (
            f"21.6K source effective crop ~{native_w}×{native_h} px, "
            f"upsampled {round(tw/native_w,1)}× to {tw}×{th}. "
            "Not true 4096-grade land texture. Land mountain precision pending DEM Phase."
        ),
        "baseline_upsampling_note": (
            "Layer 0 baseline cropped from d5b 8K (~727×637 px for this region), "
            f"upsampled ~5.6× to {tw}×{th}. "
            "Used as comparison baseline only. 4096 new detail comes from GEBCO + GSHHG."
        ),
        "demo_boundary_note": (
            "demo_japan_v2_tile.html is an isolated prototype demo for visual validation only. "
            "It does not represent formal earth3d.js integration, RodiO production deployment, "
            "or final Japan high-quality texture."
        ),
        "generation_commands": [cmd],
        "generated_at": generated_at,
        "elapsed_seconds": elapsed,
        "scripts_used": [f"scripts/geo/{SCRIPT_NAME} v{VERSION}"],
        "notes": [
            "Prototype only: validates GEBCO 2026 + GSHHG natural geography layer.",
            "4096 new detail = GEBCO 15 arc-sec bathymetry + GSHHG full-res coastline.",
            "Land area: d5b 8K upsampled ~5.6×. Land mountain precision NOT addressed.",
            "Copernicus DEM / ALOS DEM: out of scope, pending DEM Phase.",
            "OSM, city lights, VIIRS Night Lights: Layer 6 scope, not done here.",
            "Do not describe this output as final Japan high-quality texture.",
            "Do not describe this output as global texture upgrade."
        ]
    }
    meta_path = os.path.join(R, 'metadata.json')
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"\n[meta] wrote {meta_path}")

    print(f"\n=== DONE in {elapsed}s ===")
    print(f"  01_layers/  — 5 layer images + stack contact sheet")
    print(f"  02_tiles/   — v2 4096 + 2048, baseline, etopo_ref, compare, contact sheets")
    print(f"  03_demo/    — demo HTML + UV bounds outline")
    print(f"  04_crops/   — 9 crop comparisons")
    print(f"  05_reports/ — metadata.json")

if __name__ == '__main__':
    main()
