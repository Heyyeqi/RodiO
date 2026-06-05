#!/usr/bin/env python3
"""
Bathy-2: Generate D5a depth-tinted bathymetry candidate texture.
Blends D3 daylight texture with depth-tinted colors derived from ETOPO1.
Does NOT modify earth3d.js or any rendering code.
"""

import numpy as np
from PIL import Image
import netCDF4 as nc
from scipy.ndimage import gaussian_filter
import os, json
from datetime import datetime

BASE     = os.path.expanduser("~/Projects/RodiO/pwa/assets/source")
D3_PATH  = f"{BASE}/bmng_staging/bmng_processed_8192x4096_natural_d3.jpg"
ETOPO    = f"{BASE}/bathy/ETOPO1_Ice_g_gdal.grd"
OUT_PATH = f"{BASE}/bmng_staging/bmng_processed_8192x4096_natural_d5a_bathy.jpg"
METRICS  = f"{BASE}/bathy/d5a_bathy_metrics.json"
PREV_G   = f"{BASE}/bathy/d5a_bathy_preview_global.jpg"
PREV_R   = f"{BASE}/bathy/d5a_bathy_preview_regions.jpg"

D3_W, D3_H = 8192, 4096
T0 = datetime.now()
def ts(): return datetime.now().strftime('%H:%M:%S')

print("=" * 68)
print("Bathy-2: D5a depth-tinted candidate")
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 68)

# ── Phase 1: Load D3 ──────────────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 1: Loading D3...")
d3_img = Image.open(D3_PATH).convert("RGB")
d3 = np.array(d3_img, dtype=np.float32)

# ── Phase 2: Load + Downsample ETOPO1 ────────────────────────────────────────
print(f"[{ts()}] Phase 2: Loading ETOPO1 (large array, ~20s)...")
ds = nc.Dataset(ETOPO, "r")
dim = ds.variables['dimension'][:]
W_e, H_e = int(dim[0]), int(dim[1])
z_raw = ds.variables['z'][:].astype(np.float32).reshape(H_e, W_e)
ds.close()
print(f"  ETOPO1: {W_e}x{H_e}, range [{z_raw.min():.0f}, {z_raw.max():.0f}]m")

print(f"[{ts()}] Phase 2b: Downsampling to {D3_W}x{D3_H} (nearest-neighbor)...")
ri = np.round(np.linspace(0, H_e - 1, D3_H)).astype(int)
ci = np.round(np.linspace(0, W_e - 1, D3_W)).astype(int)
depth = z_raw[np.ix_(ri, ci)]   # (4096, 8192) float32; neg=ocean, pos=land/ice
del z_raw   # free ~880MB

# ── Phase 3: Masks ───────────────────────────────────────────────────────────
print(f"[{ts()}] Phase 3: Building masks...")

ocean_hard = depth < 0
land_hard  = depth >= 0

# Soft coastal fade: taper blend weight to 0 within ~6px of land boundary
ocean_fade = gaussian_filter(ocean_hard.astype(np.float32), sigma=3)
ocean_fade = np.clip(ocean_fade / 0.85, 0.0, 1.0)

# Snow/ice: protect near-white D3 pixels regardless of ETOPO
R3, G3, B3 = d3[..., 0], d3[..., 1], d3[..., 2]
snow_mask = (R3 > 210) & (G3 > 210) & (B3 > 210)

print(f"  ocean: {ocean_hard.mean()*100:.1f}%  land/ice: {land_hard.mean()*100:.1f}%"
      f"  snow(D3): {snow_mask.mean()*100:.1f}%")

# ── Phase 4: Depth weights (smoothed) ────────────────────────────────────────
print(f"[{ts()}] Phase 4: Computing depth weights (gaussian sigma=6)...")

# Smooth depth field → prevents visible isobath contour lines
depth_sm = gaussian_filter(depth, sigma=6)

# Positive depth (ocean only)
d_val = np.clip(-depth_sm, 0.0, 12000.0)

# Piecewise linear blend weight, conservative (max 0.22)
# d=0–20m: 0.22, d=20–50m: 0.22→0.18, d=50–200m: 0.18→0.12,
# d=200–1000m: 0.12→0.04, d=1000–4000m: 0.04→0.00
bp_d = [0,    20,   50,   200,   1000,  4000]
bp_w = [0.22, 0.22, 0.18, 0.12,  0.04,  0.00]
weight = np.interp(d_val, bp_d, bp_w).astype(np.float32) * ocean_fade

print(f"  weight max={weight.max():.3f}  mean(ocean)={weight[ocean_hard].mean():.4f}")

# ── Phase 5: Target colors ────────────────────────────────────────────────────
print(f"[{ts()}] Phase 5: Computing target colors per pixel...")

# Target color anchors (low-saturation cyan-blue, not tropical vivid)
# 0m: warm-cyan  20m: soft-cyan  50m: shelf-blue  200m: slate  1000m+: deep-slate
bp_dc = [0,    20,   50,   200,  1000]
bp_R  = [129,  113,   96,   74,    52]
bp_G  = [182,  170,  147,  109,    80]
bp_B  = [174,  178,  157,  129,   105]

tgt_R = np.interp(d_val, bp_dc, bp_R).astype(np.float32)
tgt_G = np.interp(d_val, bp_dc, bp_G).astype(np.float32)
tgt_B = np.interp(d_val, bp_dc, bp_B).astype(np.float32)
tgt   = np.stack([tgt_R, tgt_G, tgt_B], axis=-1)

# ── Phase 6: Blend ────────────────────────────────────────────────────────────
print(f"[{ts()}] Phase 6: Blending D3 + depth tint...")

w3 = weight[..., np.newaxis]
result = d3 * (1.0 - w3) + tgt * w3

# ── Phase 7: Protections ──────────────────────────────────────────────────────
print(f"[{ts()}] Phase 7: Applying protections (land / snow / anti-荧光)...")

# Hard land restore
lm = land_hard[..., np.newaxis].astype(np.float32)
result = d3 * lm + result * (1.0 - lm)

# Hard snow/ice restore
sm = snow_mask[..., np.newaxis].astype(np.float32)
result = d3 * sm + result * (1.0 - sm)

# Anti-荧光: clamp pixels where saturation increased >6% and sat>0.48
def sat_arr(a):
    mx = np.maximum(np.maximum(a[...,0], a[...,1]), a[...,2])
    mn = np.minimum(np.minimum(a[...,0], a[...,1]), a[...,2])
    return np.where(mx > 0, (mx - mn) / mx, 0.0)

sat3 = sat_arr(d3)
satr = sat_arr(result)
overshoot = (satr > sat3 * 1.06) & (satr > 0.48) & ocean_hard
om_ = overshoot[..., np.newaxis].astype(np.float32)
result = d3 * om_ + result * (1.0 - om_)

result = result.clip(0, 255).astype(np.uint8)

# ── Phase 8: Save ─────────────────────────────────────────────────────────────
print(f"[{ts()}] Phase 8: Saving D5a...")
out_img = Image.fromarray(result)
out_img.save(OUT_PATH, "JPEG", quality=95, subsampling=0)
import os as _os
print(f"  {OUT_PATH}  ({_os.path.getsize(OUT_PATH)//1024//1024}MB)")

# ── Phase 9: Metrics ──────────────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 9: Computing metrics (23 zones)...")

res_f = result.astype(np.float32)

def rgb_to_sv(arr):
    mx = np.maximum(np.maximum(arr[...,0], arr[...,1]), arr[...,2])
    mn = np.minimum(np.minimum(arr[...,0], arr[...,1]), arr[...,2])
    s  = np.where(mx > 0, (mx - mn) / mx, 0.0)
    v  = mx / 255.0
    return s, v

S3, V3 = rgb_to_sv(d3)
Sr, Vr = rgb_to_sv(res_f)

def lonlat_rc(lon, lat):
    c = int(round((lon + 180) / 360 * (D3_W - 1)))
    r = int(round((90 - lat) / 180 * (D3_H - 1)))
    return max(0, min(D3_H-1, r)), max(0, min(D3_W-1, c))

def bbox(lw, le, ls, ln):
    r1, c1 = lonlat_rc(lw, ln)
    r2, c2 = lonlat_rc(le, ls)
    return min(r1,r2), max(r1,r2)+1, min(c1,c2), max(c1,c2)+1

zones = [
    # name,                  lon_w, lon_e, lat_s, lat_n
    ("Yellow Sea",           119,   127,    31,    38),
    ("East China Sea",       119,   128,    24,    32),
    ("Taiwan Strait",        117,   123,    22,    26),
    ("S.China Sea N",        108,   122,    16,    24),
    ("S.China Sea C",        109,   120,     7,    16),
    ("Philippines",          116,   128,     5,    18),
    ("Indonesia",            105,   140,    -8,     5),
    ("Caribbean",            -85,   -60,    10,    24),
    ("Bahamas",              -80,   -72,    22,    28),
    ("Gulf of Mexico",       -97,   -80,    18,    30),
    ("Australia North",      127,   140,   -20,   -10),
    ("Great Barrier Reef",   145,   154,   -24,   -15),
    ("Persian Gulf",          48,    57,    23,    30),
    ("Red Sea",               32,    44,    12,    28),
    ("North Sea",             -4,    10,    51,    60),
    ("Mediterranean",          0,    36,    30,    46),
    ("Bering Sea",           165,   200,    53,    65),
    ("Sea of Okhotsk",       140,   162,    47,    60),
    ("Southern Ocean",      -180,   180,   -60,   -50),
    ("Arctic fringe",       -180,   180,    70,    80),
    ("Pacific Deep",        -150,   -90,   -30,    10),
    ("Indian Ocean Deep",     60,    90,   -40,   -10),
    ("N.Atlantic Deep",      -55,   -30,    30,    55),
]

metrics_out = {}
print(f"\n  {'Zone':<22} {'dep':>6} {'0-50':>5} {'>1km':>5} | "
      f"{'D3 R/G/B':^14} {'D5 R/G/B':^14} | "
      f"{'BG_d3':>6} {'BG_d5':>6} | {'ΔR':>4} {'ΔG':>4} {'ΔB':>4} | {'sat3':>5} {'satr':>5} | ok?")
print("  " + "-" * 115)

for (name, lw, le, ls, ln) in zones:
    full = (lw == -180 and le == 180)
    r1, r2, c1, c2 = bbox(lw, le, ls, ln)
    s = (slice(r1, r2), slice(None) if full else slice(c1, c2))

    pd3  = d3[s]
    pr   = res_f[s]
    pd   = depth[s]
    ps3  = S3[s];  psr = Sr[s]

    om = pd < 0
    if om.sum() < 50:
        continue

    d_oc = pd[om]
    dep_mean = -d_oc.mean()
    p0_50 = ((d_oc >= -50) & (d_oc < 0)).mean() * 100
    p1k   = (d_oc < -1000).mean() * 100

    def avg(arr, mask):
        return arr[...,0][mask].mean(), arr[...,1][mask].mean(), arr[...,2][mask].mean()

    R3m, G3m, B3m = avg(pd3, om)
    Rrm, Grm, Brm = avg(pr, om)
    BG3 = B3m / (G3m + 1e-6)
    BGr = Brm / (Grm + 1e-6)
    s3  = ps3[om].mean()
    sr  = psr[om].mean()
    hi3 = (ps3[om] > 0.40).mean() * 100
    hir = (psr[om] > 0.40).mean() * 100

    dR, dG, dB = Rrm-R3m, Grm-G3m, Brm-B3m

    # pass/fail: saturation must not spike, G must not dominate excessively
    ok = (hir <= hi3 * 1.08) and (dG < 15) and (dB < 15)

    metrics_out[name] = dict(
        depth_mean=round(float(dep_mean), 1),
        pct_0_50=round(float(p0_50), 1),
        pct_gt1k=round(float(p1k), 1),
        d3=dict(R=round(float(R3m),1), G=round(float(G3m),1), B=round(float(B3m),1),
                BG=round(float(BG3),3), sat=round(float(s3),4)),
        d5a=dict(R=round(float(Rrm),1), G=round(float(Grm),1), B=round(float(Brm),1),
                 BG=round(float(BGr),3), sat=round(float(sr),4)),
        delta=dict(R=round(float(dR),1), G=round(float(dG),1), B=round(float(dB),1),
                   sat=round(float(sr-s3),4)),
        hi_sat=dict(d3=round(float(hi3),1), d5a=round(float(hir),1)),
        pass_check=bool(ok),
    )

    flag = "✓" if ok else "✗"
    print(f"  {name:<22} {dep_mean:>6.0f} {p0_50:>5.1f} {p1k:>5.1f} | "
          f"{R3m:>4.0f}/{G3m:>4.0f}/{B3m:>4.0f}  "
          f"{Rrm:>4.0f}/{Grm:>4.0f}/{Brm:>4.0f} | "
          f"{BG3:>6.3f} {BGr:>6.3f} | "
          f"{dR:>+4.0f} {dG:>+4.0f} {dB:>+4.0f} | "
          f"{s3:>5.3f} {sr:>5.3f} | {flag}")

# Spot checks: land and snow not modified
# Sample a few land/snow points
check_pts = [
    ("Sahara",         10,  22),
    ("Amazon",        -60,  -5),
    ("Greenland ctr", -42,  72),
    ("Antarctica",      0, -85),
]
print("\n  ── Land/Snow protection checks ──")
for (pname, lon, lat) in check_pts:
    r, c = lonlat_rc(lon, lat)
    orig = d3[r, c]
    new  = result[r, c].astype(float)
    diff = abs(new - orig).max()
    print(f"  {pname:<18} D3={orig.astype(int)}  D5a={new.astype(int)}  max_diff={diff:.0f}  "
          f"{'✓' if diff < 2 else '✗ MODIFIED'}")

with open(METRICS, "w") as f:
    json.dump(metrics_out, f, indent=2, ensure_ascii=False)
print(f"\n  Metrics: {METRICS}")

# ── Phase 10: Previews ────────────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 10: Generating preview images...")

# Global side-by-side at 2048×1024 each
PW, PH = 2048, 1024
d3s  = d3_img.resize((PW, PH), Image.LANCZOS)
d5as = out_img.resize((PW, PH), Image.LANCZOS)
glob = Image.new("RGB", (PW*2, PH))
glob.paste(d3s,  (0,  0))
glob.paste(d5as, (PW, 0))
glob.save(PREV_G, "JPEG", quality=88)
print(f"  Global: {PREV_G}")

# Regional crops composite (D3 left | D5a right), stacked vertically
crop_defs = [
    ("Yellow+ECS",    119, 128,  22,  40),
    ("Taiwan Strait", 115, 125,  20,  28),
    ("South China",   105, 125,   5,  25),
    ("Philippines",   115, 132,   4,  20),
    ("Indonesia",     100, 145, -12,   8),
    ("Carib+Bahamas", -88, -60,  10,  28),
    ("Aus+GBR",       120, 158, -26,  -8),
    ("Persian+Red",    30,  60,  10,  32),
    ("North Sea",      -8,  12,  49,  62),
    ("Bering Sea",    160, 200,  50,  67),
    ("Southern Ocn",  -60,  60, -65, -45),
]

TARGET_W = 1400   # width of each side-by-side pair (D3+D5a combined)
rows = []
for (tag, lw, le, ls, ln) in crop_defs:
    r1, r2, c1, c2 = bbox(lw, le, ls, ln)
    if r2 <= r1 or c2 <= c1:
        continue
    cd3  = d3_img.crop((c1, r1, c2, r2))
    cd5a = out_img.crop((c1, r1, c2, r2))
    cw, ch = c2-c1, r2-r1
    pair = Image.new("RGB", (cw*2, ch))
    pair.paste(cd3,  (0,  0))
    pair.paste(cd5a, (cw, 0))
    scale = TARGET_W / max(cw*2, 1)
    pair_s = pair.resize((TARGET_W, max(1, int(ch * scale))), Image.LANCZOS)
    rows.append(pair_s)

total_h = sum(img.height + 1 for img in rows)
comp = Image.new("RGB", (TARGET_W, total_h), (20, 20, 20))
y = 0
for img in rows:
    comp.paste(img, (0, y))
    y += img.height + 1
comp.save(PREV_R, "JPEG", quality=88)
print(f"  Regions: {PREV_R}  ({len(rows)} crops)")

# ── Summary ───────────────────────────────────────────────────────────────────
elapsed = (datetime.now() - T0).total_seconds()
all_pass = all(v["pass_check"] for v in metrics_out.values())

print(f"\n── Summary ──")
print(f"  Zones passed: {sum(v['pass_check'] for v in metrics_out.values())}/{len(metrics_out)}")
print(f"  Overall:      {'PASS ✓' if all_pass else 'PARTIAL — check flagged zones'}")
print(f"  Elapsed:      {elapsed:.0f}s")

print(f"\n── Confirmations ──")
print("  earth3d.js:    NOT modified ✓")
print("  dayTexture:    NOT replaced ✓")
print("  nightTexture:  NOT modified ✓")
print("  cloudMesh:     NOT modified ✓")
print("  atmosphere:    NOT modified ✓")
print("  UI/index.html: NOT modified ✓")
print("  No commit made ✓")
print(f"\nOutput: {OUT_PATH}")
