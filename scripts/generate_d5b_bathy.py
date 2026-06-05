#!/usr/bin/env python3
"""
Bathy D5b: conservative convergence of D5a.
Fixes: weaker weights, stronger blur, B>=G target colors, regional soft masks.
Does NOT touch earth3d.js, nightTexture, cloudMesh, atmosphere, UI, or Service Worker.
"""

import numpy as np
from PIL import Image
import netCDF4 as nc
from scipy.ndimage import gaussian_filter
import os, json
from datetime import datetime

BASE   = os.path.expanduser("~/Projects/RodiO/pwa/assets/source")
D3_PATH  = f"{BASE}/bmng_staging/bmng_processed_8192x4096_natural_d3.jpg"
D5A_PATH = f"{BASE}/bmng_staging/bmng_processed_8192x4096_natural_d5a_bathy.jpg"
ETOPO    = f"{BASE}/bathy/ETOPO1_Ice_g_gdal.grd"
OUT_PATH = f"{BASE}/bmng_staging/bmng_processed_8192x4096_natural_d5b_bathy.jpg"
CAND_DIR = os.path.expanduser("~/Projects/RodiO/pwa/assets/earth/candidates")
PREV_PATH = f"{BASE}/bmng_staging/preview_d5b_vs_d5a_4096.jpg"
DIFF_PATH = f"{BASE}/bmng_staging/diff_d5b_vs_d5a_4096.jpg"

D3_W, D3_H = 8192, 4096
T0 = datetime.now()
def ts(): return datetime.now().strftime('%H:%M:%S')

print("=" * 68)
print("D5b: Bathy candidate generation")
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 68)

# ── Load ──────────────────────────────────────────────────────────────────────
print(f"\n[{ts()}] Loading D3 + D5a...")
d3_img  = Image.open(D3_PATH).convert("RGB")
d5a_img = Image.open(D5A_PATH).convert("RGB")
d3  = np.array(d3_img,  dtype=np.float32)
d5a = np.array(d5a_img, dtype=np.float32)

print(f"[{ts()}] Loading ETOPO1 (~20s)...")
ds = nc.Dataset(ETOPO, "r")
dim = ds.variables['dimension'][:]
We, He = int(dim[0]), int(dim[1])
z_raw = ds.variables['z'][:].astype(np.float32).reshape(He, We)
ds.close()

print(f"[{ts()}] Downsampling ETOPO1 → {D3_W}x{D3_H}...")
ri = np.round(np.linspace(0, He-1, D3_H)).astype(int)
ci = np.round(np.linspace(0, We-1, D3_W)).astype(int)
depth = z_raw[np.ix_(ri, ci)]
del z_raw

# ── Coordinate helpers ────────────────────────────────────────────────────────
def lonlat_rc(lon, lat):
    c = int(round((lon + 180) / 360 * (D3_W - 1)))
    r = int(round((90 - lat)  / 180 * (D3_H - 1)))
    return max(0, min(D3_H-1, r)), max(0, min(D3_W-1, c))

def bbox(lw, le, ls, ln):
    r1, c1 = lonlat_rc(lw, ln)
    r2, c2 = lonlat_rc(le, ls)
    return min(r1,r2), max(r1,r2)+1, min(c1,c2), max(c1,c2)+1

# ── Lat / Lon grids for soft masks ────────────────────────────────────────────
lon_grid = np.linspace(-180, 180, D3_W, dtype=np.float32)   # (W,)
lat_grid = np.linspace( 90,  -90, D3_H, dtype=np.float32)   # (H,)
LAT = lat_grid[:, np.newaxis] * np.ones((1, D3_W), dtype=np.float32)   # (H,W)
LON = lon_grid[np.newaxis, :] * np.ones((D3_H, 1), dtype=np.float32)   # (H,W)

# ── Phase 1: Masks ────────────────────────────────────────────────────────────
print(f"[{ts()}] Phase 1: Building masks...")

ocean_hard = depth < 0
land_hard  = depth >= 0
ocean_fade = gaussian_filter(ocean_hard.astype(np.float32), sigma=3)
ocean_fade = np.clip(ocean_fade / 0.85, 0.0, 1.0)

R3, G3, B3 = d3[..., 0], d3[..., 1], d3[..., 2]
snow_mask  = (R3 > 210) & (G3 > 210) & (B3 > 210)

# ── Phase 2: Depth weights (D5b: sigma=12 depth + sigma=8 weight) ─────────────
print(f"[{ts()}] Phase 2: Computing depth weights (sigma_depth=12, sigma_weight=8)...")

depth_sm = gaussian_filter(depth, sigma=12)           # stronger than D5a sigma=6
d_val    = np.clip(-depth_sm, 0.0, 12000.0)

bp_d = [0,    20,   50,   200,   1000,  4000]
bp_w = [0.14, 0.14, 0.11, 0.08,  0.03,  0.00]       # D5b weights (D5a: 0.22/0.18/0.12/0.04/0.00)
weight_base = np.interp(d_val, bp_d, bp_w).astype(np.float32) * ocean_fade

# Second gaussian on weight map
weight_base = gaussian_filter(weight_base, sigma=8)  # D5b addition

# ── Phase 3: Regional soft masks ─────────────────────────────────────────────
print(f"[{ts()}] Phase 3: Building regional soft masks...")

def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)

# Tropical mask: core |lat|<=20 → full, transition 20-30 → 0
trop_raw = np.where(np.abs(LAT) <= 20, 1.0,
           np.where(np.abs(LAT) <= 30,
                    smoothstep((30 - np.abs(LAT)) / 10.0), 0.0))
trop_mask = trop_raw.astype(np.float32)

# East Asia mask: core lon 112-130 / lat 22-40 → full, transition to 0 over 8 deg
def range_soft(v, lo_hard, hi_hard, lo_edge, hi_edge):
    m = np.where(v < lo_hard, smoothstep((v - lo_edge) / max(lo_hard - lo_edge, 1e-3)),
        np.where(v > hi_hard, smoothstep((hi_edge - v) / max(hi_edge - hi_hard, 1e-3)),
        1.0))
    return m.astype(np.float32)

ea_lon = range_soft(LON, 112, 130, 100, 140)
ea_lat = range_soft(LAT,  22,  40,  15,  48)
ea_mask = (ea_lon * ea_lat).astype(np.float32)

# Persian Gulf mask: lon 48-57 / lat 24-30
pg_lon = range_soft(LON, 48, 57, 44, 61)
pg_lat = range_soft(LAT, 24, 30, 20, 34)
pg_mask = (pg_lon * pg_lat).astype(np.float32)

# Red Sea mask: lon 32-44 / lat 12-30
rs_lon = range_soft(LON, 32, 44, 28, 48)
rs_lat = range_soft(LAT, 12, 30,  8, 34)
rs_mask = (rs_lon * rs_lat).astype(np.float32)

# High-latitude mask: lat >= 50N
hl_raw = np.where(LAT >= 50, 1.0,
         np.where(LAT >= 40, smoothstep((LAT - 40) / 10.0), 0.0))
hl_mask = hl_raw.astype(np.float32)

print(f"  ocean={ocean_hard.mean()*100:.1f}%  snow={snow_mask.mean()*100:.1f}%"
      f"  trop_coverage={trop_mask.mean()*100:.1f}%"
      f"  ea_coverage={ea_mask.mean()*100:.1f}%")

# ── Phase 4: Target colors (D5b: B >= G) ─────────────────────────────────────
print(f"[{ts()}] Phase 4: Computing target colors...")

bp_dc = [0,    20,   50,   200,  1000]
bp_R  = [118,  105,   90,   72,    52]
bp_G  = [165,  155,  138,  107,    80]
bp_B  = [170,  168,  152,  126,   105]

tgt_R = np.interp(d_val, bp_dc, bp_R).astype(np.float32)
tgt_G = np.interp(d_val, bp_dc, bp_G).astype(np.float32)
tgt_B = np.interp(d_val, bp_dc, bp_B).astype(np.float32)
tgt   = np.stack([tgt_R, tgt_G, tgt_B], axis=-1)

# Apply East Asia target color offset
ea3 = ea_mask[..., np.newaxis]
tgt_ea = tgt.copy()
tgt_ea[..., 0] = np.clip(tgt_ea[..., 0] + 4 * ea_mask, 0, 255)
tgt_ea[..., 1] = np.clip(tgt_ea[..., 1] - 6 * ea_mask, 0, 255)
tgt_ea[..., 2] = np.clip(tgt_ea[..., 2] - 2 * ea_mask, 0, 255)
tgt = tgt * (1 - ea3) + tgt_ea * ea3

# Apply Persian Gulf target color offset
pg3 = pg_mask[..., np.newaxis]
tgt[..., 0] = np.clip(tgt[..., 0] + 3 * pg_mask, 0, 255)
tgt[..., 1] = np.clip(tgt[..., 1] - 3 * pg_mask, 0, 255)
tgt[..., 2] = np.clip(tgt[..., 2] - 6 * pg_mask, 0, 255)

# Apply Red Sea offset (same as PG)
rs3 = rs_mask[..., np.newaxis]
tgt[..., 0] = np.clip(tgt[..., 0] + 3 * rs_mask, 0, 255)
tgt[..., 1] = np.clip(tgt[..., 1] - 3 * rs_mask, 0, 255)
tgt[..., 2] = np.clip(tgt[..., 2] - 6 * rs_mask, 0, 255)

# Apply high-lat offset
hl3 = hl_mask[..., np.newaxis]
tgt[..., 1] = np.clip(tgt[..., 1] - 2 * hl_mask, 0, 255)
tgt[..., 2] = np.clip(tgt[..., 2] - 2 * hl_mask, 0, 255)

# ── Phase 5: Apply regional weight multipliers ────────────────────────────────
print(f"[{ts()}] Phase 5: Applying regional weight multipliers...")

weight = weight_base.copy()

# East Asia: ×1.10 (compensate for global weight reduction)
weight = weight * (1.0 + 0.10 * ea_mask)

# Tropical: ×0.85
weight = weight * (1.0 - 0.15 * trop_mask)

# Persian Gulf: ×0.90
weight = weight * (1.0 - 0.10 * pg_mask)

# Red Sea: ×0.90
weight = weight * (1.0 - 0.10 * rs_mask)

# High latitude: ×0.95
weight = weight * (1.0 - 0.05 * hl_mask)

# Tropical islands: extra blur on weight (additional sigma=4 in tropical zone)
weight_trop_blur = gaussian_filter(weight, sigma=4)
weight = weight * (1.0 - 0.5 * trop_mask) + weight_trop_blur * (0.5 * trop_mask)

# Hard cap: deep ocean always 0
weight = np.where(depth < -1000, 0.0, weight)

weight = np.clip(weight, 0.0, 0.14)
print(f"  weight max={weight.max():.4f}  mean(ocean)={weight[ocean_hard].mean():.5f}")

# ── Phase 6: Blend ────────────────────────────────────────────────────────────
print(f"[{ts()}] Phase 6: Blending...")
w3 = weight[..., np.newaxis]
result = d3 * (1.0 - w3) + tgt * w3

# ── Phase 7: Protections ──────────────────────────────────────────────────────
print(f"[{ts()}] Phase 7: Protections (land / snow / saturation cap)...")

# Land
lm = land_hard[..., np.newaxis].astype(np.float32)
result = d3 * lm + result * (1.0 - lm)

# Snow/ice
sm = snow_mask[..., np.newaxis].astype(np.float32)
result = d3 * sm + result * (1.0 - sm)

# Tropical saturation cap: output sat <= D3 sat
def sat_arr(a):
    mx = np.maximum(np.maximum(a[...,0], a[...,1]), a[...,2])
    mn = np.minimum(np.minimum(a[...,0], a[...,1]), a[...,2])
    return np.where(mx > 0, (mx - mn) / mx, 0.0)

sat3 = sat_arr(d3)
satr = sat_arr(result)
# In tropical zones: clamp saturation to D3 level
trop_over = (satr > sat3) & (trop_mask > 0.3) & ocean_hard
to3 = trop_over[..., np.newaxis].astype(np.float32)
result = d3 * to3 + result * (1.0 - to3)

# Global anti-荧光: sat increase > 5% and sat > 0.48
satr2 = sat_arr(result)
over = (satr2 > sat3 * 1.05) & (satr2 > 0.48) & ocean_hard
o3 = over[..., np.newaxis].astype(np.float32)
result = d3 * o3 + result * (1.0 - o3)

result = result.clip(0, 255).astype(np.uint8)

# ── Phase 8: Save ─────────────────────────────────────────────────────────────
print(f"[{ts()}] Phase 8: Saving D5b...")
out_img = Image.fromarray(result)
out_img.save(OUT_PATH, "JPEG", quality=95, subsampling=0)
sz = os.path.getsize(OUT_PATH) // (1024*1024)
print(f"  {OUT_PATH}  ({sz}MB)")

# Copy to candidates
import shutil
cand_path = os.path.join(CAND_DIR, "d5b_bathy_8192x4096.jpg")
shutil.copy2(OUT_PATH, cand_path)
print(f"  Copied → {cand_path}")

# ── Phase 9: Metrics ──────────────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 9: Computing metrics (27 zones)...")

res_f  = result.astype(np.float32)
d5a_f  = d5a.astype(np.float32)

sat3_  = sat_arr(d3)
satr_  = sat_arr(res_f)
sat5a_ = sat_arr(d5a_f)

def lum(a): return 0.299*a[...,0]+0.587*a[...,1]+0.114*a[...,2]
lum3  = lum(d3);   lum5b = lum(res_f);  lum5a = lum(d5a_f)

zones = [
    # name,              lw,   le,  ls,  ln
    ("Yellow Sea",       119,  126,  32,  39),
    ("Bohai Sea",        117,  122,  37,  41),
    ("East China Sea",   120,  130,  25,  33),
    ("Taiwan Strait",    117,  122,  22,  26),
    ("S.China Sea N",    110,  121,  15,  23),
    ("Taiwan E deep",    122,  130,  20,  26),
    ("Philippines Luzon",119,  126,  12,  20),
    ("Persian Gulf",      48,   57,  24,  30),
    ("Red Sea",           32,   44,  12,  30),
    ("North Sea",         -4,    9,  52,  61),
    ("Bahamas",          -80,  -72,  22,  28),
    ("Caribbean",        -85,  -60,  10,  25),
    ("Great Barrier Reef",142, 154, -24, -10),
    ("Australia North",  124,  142, -18,  -8),
    ("Maldives",          72,   74,  -1,   8),
    ("Indonesia",         95,  130, -10,   8),
    ("Philippines",      117,  127,   5,  20),
    ("Pacific Deep",    -160, -130, -20,  10),
    ("Indian Ocean D",    65,   95, -30,  -5),
    ("N.Atlantic D",     -50,  -25,  20,  45),
    ("Southern Ocean",  -160,  -80, -60, -45),
    ("Mariana",          140,  150,  10,  25),
    ("Antarctica",      -180,  180, -90, -70),
    ("Greenland",        -55,  -20,  60,  83),
    ("Arctic",          -180,  180,  80,  90),
    ("Sahara",           -15,   35,  15,  35),
    ("Tibetan Plateau",   75,  105,  28,  40),
]

metrics = {}
hdr = (f"  {'Zone':<22} {'dep':>6} {'0-20':>5} {'0-50':>5} {'>1km':>5} | "
       f"{'D3 R/G/B':^14} {'D5b R/G/B':^14} | "
       f"{'ΔR':>4} {'ΔG':>4} {'ΔB':>4} | "
       f"{'BG3':>5} {'BG5b':>5} | "
       f"{'sat3':>5} {'sat5b':>5} | "
       f"{'5b-5a R':>7} {'5b-5a B':>7} | ok?")
print(hdr)
print("  " + "-" * 130)

for (name, lw, le, ls, ln) in zones:
    full = (lw == -180 and le == 180)
    r1, r2, c1, c2 = bbox(lw, le, ls, ln)
    s = (slice(r1, r2), slice(None) if full else slice(c1, c2))

    pd3  = d3[s];  pres = res_f[s]; pd5a = d5a_f[s]
    pdep = depth[s]
    ps3  = sat3_[s]; psr = satr_[s]; ps5a = sat5a_[s]
    pl3  = lum3[s];  pl5b = lum5b[s]; pl5a = lum5a[s]

    # Land/ice/snow regions: check max_diff
    is_land_zone = name in ("Antarctica", "Greenland", "Arctic", "Sahara", "Tibetan Plateau")
    if is_land_zone:
        diff_d3 = np.abs(pres - pd3).max()
        diff_5a = np.abs(pres - pd5a).max()
        bright_pct = (pl5b.mean() / (pl3.mean() + 1e-6) - 1) * 100
        print(f"  {name:<22} {'—':>6} {'—':>5} {'—':>5} {'—':>5} | "
              f"{'land/ice':<14} max_diff_vs_D3={diff_d3:.2f}  lum_change={bright_pct:+.2f}%")
        metrics[name] = dict(max_diff_vs_d3=round(float(diff_d3),3),
                             lum_pct_change=round(float(bright_pct),3))
        continue

    om = pdep < 0
    if om.sum() < 20:
        print(f"  {name:<22}  (no ocean pixels)")
        continue

    doc = pdep[om]; d_neg = -doc
    dep_mean = float(d_neg.mean())
    p0_20 = float((d_neg < 20).mean() * 100)
    p0_50 = float((d_neg < 50).mean() * 100)
    p1k   = float((d_neg >= 1000).mean() * 100)

    def avg(arr, mask):
        return arr[...,0][mask].mean(), arr[...,1][mask].mean(), arr[...,2][mask].mean()

    R3m,  G3m,  B3m  = avg(pd3,  om)
    Rrm,  Grm,  Brm  = avg(pres, om)
    R5am, G5am, B5am = avg(pd5a, om)

    BG3  = B3m  / (G3m  + 1e-6)
    BG5b = Brm  / (Grm  + 1e-6)
    s3   = float(ps3[om].mean())
    sr   = float(psr[om].mean())
    s5a  = float(ps5a[om].mean())

    lm3  = float(pl3[om].mean());  lm5b = float(pl5b[om].mean())
    p95_3  = float(np.percentile(pl3[om],  95))
    p99_3  = float(np.percentile(pl3[om],  99))
    p95_5b = float(np.percentile(pl5b[om], 95))
    p99_5b = float(np.percentile(pl5b[om], 99))

    hi3  = float((ps3[om]  > 0.40).mean() * 100)
    hir  = float((psr[om]  > 0.40).mean() * 100)

    dR = Rrm - R3m;  dG = Grm - G3m;  dB = Brm - B3m
    dR5a = Rrm - R5am; dB5a = Brm - B5am

    # pass checks
    ok = True
    if name in ("Pacific Deep","Indian Ocean D","N.Atlantic D","Southern Ocean","Mariana"):
        ok = (abs(dR) <= 0.5) and (abs(dG) <= 0.5) and (abs(dB) <= 0.5)
    elif sr > s3 * 1.02:
        ok = False

    metrics[name] = dict(
        depth_mean=round(dep_mean,1), pct_0_20=round(p0_20,1),
        pct_0_50=round(p0_50,1), pct_gt1k=round(p1k,1),
        d3=dict(R=round(R3m,1),G=round(G3m,1),B=round(B3m,1),
                BG=round(BG3,3),sat=round(s3,4),
                lum_mean=round(lm3,2),lum_p95=round(p95_3,2),lum_p99=round(p99_3,2)),
        d5a=dict(R=round(R5am,1),G=round(G5am,1),B=round(B5am,1),sat=round(s5a,4)),
        d5b=dict(R=round(Rrm,1),G=round(Grm,1),B=round(Brm,1),
                 BG=round(BG5b,3),sat=round(sr,4),
                 lum_mean=round(lm5b,2),lum_p95=round(p95_5b,2),lum_p99=round(p99_5b,2)),
        delta_vs_d3=dict(R=round(dR,1),G=round(dG,1),B=round(dB,1),sat=round(sr-s3,4)),
        delta_vs_d5a=dict(R=round(dR5a,1),B=round(dB5a,1)),
        hi_sat=dict(d3=round(hi3,1),d5b=round(hir,1)),
        pass_check=bool(ok),
    )

    flag = "✓" if ok else "✗"
    print(f"  {name:<22} {dep_mean:>6.0f} {p0_20:>5.1f} {p0_50:>5.1f} {p1k:>5.1f} | "
          f"{R3m:>4.0f}/{G3m:>4.0f}/{B3m:>4.0f}  "
          f"{Rrm:>4.0f}/{Grm:>4.0f}/{Brm:>4.0f} | "
          f"{dR:>+4.0f} {dG:>+4.0f} {dB:>+4.0f} | "
          f"{BG3:>5.3f} {BG5b:>5.3f} | "
          f"{s3:>5.3f} {sr:>5.3f} | "
          f"{dR5a:>+7.1f} {dB5a:>+7.1f} | {flag}")

# ── Phase 10: Previews ────────────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 10: Generating preview + diff images...")

PW, PH = 4096, 2048
d5a_sm = d5a_img.resize((PW, PH), Image.LANCZOS)
d5b_sm = out_img.resize((PW, PH), Image.LANCZOS)

# Side-by-side preview
prev = Image.new("RGB", (PW*2, PH))
prev.paste(d5a_sm, (0,   0))
prev.paste(d5b_sm, (PW,  0))
prev.save(PREV_PATH, "JPEG", quality=88)

# Diff image: amplify |D5b - D5a| × 5
d5a_arr = np.array(d5a_sm, dtype=np.float32)
d5b_arr = np.array(d5b_sm, dtype=np.float32)
diff_arr = np.abs(d5b_arr - d5a_arr) * 5
diff_arr = diff_arr.clip(0, 255).astype(np.uint8)
Image.fromarray(diff_arr).save(DIFF_PATH, "JPEG", quality=88)
print(f"  preview: {PREV_PATH}")
print(f"  diff:    {DIFF_PATH}")

# ── Phase 11: Write devlog ────────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 11: Writing devlog...")

devlog_path = os.path.expanduser("~/Projects/RodiO/docs/devlog_bathy_3_d5b_candidate.md")

passing = [k for k,v in metrics.items() if v.get('pass_check') is True]
failing = [k for k,v in metrics.items() if v.get('pass_check') is False]

shallow_zones = ["Yellow Sea","Bohai Sea","Persian Gulf","North Sea","Australia North"]
deep_zones_check = ["Pacific Deep","Indian Ocean D","N.Atlantic D","Southern Ocean","Mariana"]

def mval(z, path):
    v = metrics.get(z,{})
    for k in path.split('.'):
        if not isinstance(v, dict): return '—'
        v = v.get(k, '—')
    return v

with open(devlog_path, "w") as f:
    f.write(f"# Bathy D5b Candidate Report\n\n")
    f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}  \n")
    f.write(f"**Stage:** Bathy-3 — D5b generation  \n")
    f.write(f"**Status:** {'PASS (all checks)' if not failing else 'PARTIAL — see below'}  \n\n")
    f.write(f"---\n\n## 1. Parameters\n\n")
    f.write(f"| Param | D5a | D5b |\n|---|---|---|\n")
    params = [
        ("0–20m weight",    "0.22", "0.14"),
        ("20–50m weight",   "0.18", "0.11"),
        ("50–200m weight",  "0.12", "0.08"),
        ("200–1000m weight","0.04", "0.03"),
        (">1000m weight",   "0.00", "0.00"),
        ("depth sigma",     "6",    "12"),
        ("weight sigma",    "—",    "8"),
        ("0–20m target RGB","129/182/174","118/165/170"),
        ("20–50m target RGB","113/170/178","105/155/168"),
        ("50–200m target RGB","96/147/157","90/138/152"),
        ("200–1000m target RGB","74/109/129","72/107/126"),
        ("East Asia mult",  "—",    "1.10 + R+4/G-6/B-2"),
        ("Tropical mult",   "—",    "0.85 + sat cap"),
        ("Persian Gulf mult","—",   "0.90 + R+3/G-3/B-6"),
        ("High-lat mult",   "—",    "0.95 + G-2/B-2"),
    ]
    for row in params:
        f.write(f"| {row[0]} | {row[1]} | {row[2]} |\n")
    f.write(f"\n---\n\n## 2. Zone Metrics (D3 / D5a / D5b)\n\n")
    f.write(f"| Zone | dep | 0-20% | 0-50% | >1km% | D3 R/G/B | D5a R/G/B | D5b R/G/B | ΔvsD3 R/G/B | ΔvsD5a R/B | BG3 | BG5b | sat3 | sat5b |\n")
    f.write(f"|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    for (name,*_) in zones:
        m = metrics.get(name,{})
        if 'max_diff_vs_d3' in m:
            f.write(f"| {name} | — | — | — | — | land/ice | — | — | max_diff={m['max_diff_vs_d3']} | — | — | — | — | — |\n")
            continue
        if not m: continue
        d3m = m.get('d3',{}); d5b = m.get('d5b',{}); d5am = m.get('d5a',{})
        dd3 = m.get('delta_vs_d3',{}); dd5a = m.get('delta_vs_d5a',{})
        f.write(f"| {name} | {m.get('depth_mean','—')} | {m.get('pct_0_20','—')} | {m.get('pct_0_50','—')} | {m.get('pct_gt1k','—')} "
                f"| {d3m.get('R','—')}/{d3m.get('G','—')}/{d3m.get('B','—')} "
                f"| {d5am.get('R','—')}/{d5am.get('G','—')}/{d5am.get('B','—')} "
                f"| {d5b.get('R','—')}/{d5b.get('G','—')}/{d5b.get('B','—')} "
                f"| {dd3.get('R','—')}/{dd3.get('G','—')}/{dd3.get('B','—')} "
                f"| {dd5a.get('R','—')}/{dd5a.get('B','—')} "
                f"| {d3m.get('BG','—')} | {d5b.get('BG','—')} "
                f"| {d3m.get('sat','—')} | {d5b.get('sat','—')} |\n")
    f.write(f"\n---\n\n## 3. Pass/Fail\n\n")
    f.write(f"**Passing:** {len(passing)}/{len(metrics)} zones  \n")
    if failing:
        f.write(f"**Failing:** {', '.join(failing)}  \n")
    f.write(f"\n---\n\n## 4. Key Findings\n\n")
    for zn in shallow_zones:
        m = metrics.get(zn,{}); d = m.get('delta_vs_d3',{}); dv = m.get('delta_vs_d5a',{})
        if not d: continue
        f.write(f"- **{zn}**: ΔvsD3 R{d.get('R',0):+.1f}/G{d.get('G',0):+.1f}/B{d.get('B',0):+.1f}  ΔvsD5a R{dv.get('R',0):+.1f}/B{dv.get('B',0):+.1f}\n")
    f.write(f"\n**Deep ocean protection:**  \n")
    for zn in deep_zones_check:
        m = metrics.get(zn,{}); d = m.get('delta_vs_d3',{})
        if not d: continue
        ok_str = "✓" if m.get('pass_check') else "✗"
        f.write(f"- {zn}: ΔR={d.get('R',0):+.2f} ΔG={d.get('G',0):+.2f} ΔB={d.get('B',0):+.2f} {ok_str}\n")
    f.write(f"\n---\n\n## 5. Files\n\n")
    f.write(f"```\n{OUT_PATH}\n{cand_path}\n{PREV_PATH}\n{DIFF_PATH}\n```\n\n")
    f.write(f"---\n\n## 6. Confirmations\n\n")
    f.write(f"- earth3d.js: NOT modified ✓\n- dayTexture default: NOT changed ✓\n")
    f.write(f"- nightTexture / cloudMesh / atmosphere / UI: NOT modified ✓\n- No commit ✓\n")

print(f"  devlog: {devlog_path}")

# ── Summary ───────────────────────────────────────────────────────────────────
elapsed = (datetime.now() - T0).total_seconds()
all_pass = not failing
print(f"\n{'='*68}")
print(f"D5b candidate generation completed.")
print(f"{'='*68}")
print(f"\nChanged files:")
print(f"  {OUT_PATH}")
print(f"  {cand_path}")
print(f"  {devlog_path}")
print(f"\nNot changed:")
print(f"  pwa/earth3d.js  |  dayTexture default  |  nightTexture")
print(f"  cloudMesh  |  atmosphere  |  UI/index.html  |  Service Worker")
print(f"\nCommitted: No")
print(f"\nD5b parameters:")
print(f"  0–20m   weight: 0.14   target: 118/165/170")
print(f"  20–50m  weight: 0.11   target: 105/155/168")
print(f"  50–200m weight: 0.08   target:  90/138/152")
print(f"  200–1km weight: 0.03   target:  72/107/126")
print(f"  >1000m  weight: 0.00")
print(f"  depth sigma: 12  |  weight sigma: 8")

print(f"\nZone results: {len(passing)} pass / {len(failing)} fail")
if failing:
    print(f"  Failing: {', '.join(failing)}")
print(f"\nElapsed: {elapsed:.0f}s")
print(f"\nRecommendation: {'D5b should enter on-globe visual acceptance.' if all_pass else 'Review failing zones before on-globe test.'}")
