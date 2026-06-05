#!/usr/bin/env python3
"""
D5c / Ocean Palette v6.1 — offline candidate generation.
Slightly stronger shallow-water signal vs D5b, v5-aligned tropical anchor,
lighter East Asia offset, preserved Gulf/Red Sea warm-gray.
NO turbid coastal. NO abyss. NO deep-ocean texture. NO earth3d.js changes.
"""

import numpy as np
from PIL import Image
import netCDF4 as nc
from scipy.ndimage import gaussian_filter
import os, json, shutil
from datetime import datetime

BASE    = os.path.expanduser("~/Projects/RodiO/pwa/assets/source")
D3_PATH  = f"{BASE}/bmng_staging/bmng_processed_8192x4096_natural_d3.jpg"
D5A_PATH = f"{BASE}/bmng_staging/bmng_processed_8192x4096_natural_d5a_bathy.jpg"
D5B_PATH = f"{BASE}/bmng_staging/bmng_processed_8192x4096_natural_d5b_bathy.jpg"
ETOPO    = f"{BASE}/bathy/ETOPO1_Ice_g_gdal.grd"
OUT_PATH = f"{BASE}/bmng_staging/bmng_processed_8192x4096_natural_d5c_palette_v6_1_bathy.jpg"
CAND_DIR = os.path.expanduser("~/Projects/RodiO/pwa/assets/earth/candidates")
CAND_OUT = f"{CAND_DIR}/d5c_palette_v6_1_bathy_8192x4096.jpg"
DEVLOG   = os.path.expanduser("~/Projects/RodiO/docs/devlog_bathy_3_d5c_palette_v6_1_candidate.md")

D3_W, D3_H = 8192, 4096
T0 = datetime.now()
def ts(): return datetime.now().strftime('%H:%M:%S')

print("=" * 68)
print("D5c / Ocean Palette v6.1 candidate")
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 68)

# ── Load ──────────────────────────────────────────────────────────────────────
print(f"\n[{ts()}] Loading D3 / D5a / D5b...")
d3_img  = Image.open(D3_PATH).convert("RGB")
d5a_img = Image.open(D5A_PATH).convert("RGB")
d5b_img = Image.open(D5B_PATH).convert("RGB")
d3  = np.array(d3_img,  dtype=np.float32)
d5a = np.array(d5a_img, dtype=np.float32)
d5b = np.array(d5b_img, dtype=np.float32)

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

# ── Helpers ───────────────────────────────────────────────────────────────────
def lonlat_rc(lon, lat):
    c = int(round((lon + 180) / 360 * (D3_W - 1)))
    r = int(round((90 - lat) / 180 * (D3_H - 1)))
    return max(0, min(D3_H-1, r)), max(0, min(D3_W-1, c))

def bbox(lw, le, ls, ln):
    r1, c1 = lonlat_rc(lw, ln)
    r2, c2 = lonlat_rc(le, ls)
    return min(r1,r2), max(r1,r2)+1, min(c1,c2), max(c1,c2)+1

lon_g = np.linspace(-180, 180, D3_W, dtype=np.float32)
lat_g = np.linspace(  90,  -90, D3_H, dtype=np.float32)
LAT = lat_g[:, np.newaxis] * np.ones((1, D3_W), dtype=np.float32)
LON = lon_g[np.newaxis, :] * np.ones((D3_H, 1), dtype=np.float32)

def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)

def range_soft(v, lo_h, hi_h, lo_e, hi_e):
    return np.where(v < lo_h,
                    smoothstep((v - lo_e) / max(lo_h - lo_e, 1e-3)),
           np.where(v > hi_h,
                    smoothstep((hi_e - v) / max(hi_e - hi_h, 1e-3)),
                    1.0)).astype(np.float32)

# ── Phase 1: Ocean masks ──────────────────────────────────────────────────────
print(f"[{ts()}] Phase 1: Building masks...")
ocean_hard = depth < 0
land_hard  = depth >= 0
ocean_fade = gaussian_filter(ocean_hard.astype(np.float32), sigma=3)
ocean_fade = np.clip(ocean_fade / 0.85, 0.0, 1.0)
R3, G3, B3 = d3[...,0], d3[...,1], d3[...,2]
snow_mask  = (R3 > 210) & (G3 > 210) & (B3 > 210)
print(f"  ocean={ocean_hard.mean()*100:.1f}%  snow={snow_mask.mean()*100:.1f}%")

# ── Phase 2: Depth weights ────────────────────────────────────────────────────
print(f"[{ts()}] Phase 2: Depth weights (sigma_d=12, sigma_w=8)...")
depth_sm = gaussian_filter(depth, sigma=12)
d_val    = np.clip(-depth_sm, 0.0, 12000.0)

# v6.1 weights — slightly higher than D5b
bp_d = [0,    20,   50,   200,   1000,  4000]
bp_w = [0.16, 0.16, 0.13, 0.09,  0.03,  0.00]
weight_base = np.interp(d_val, bp_d, bp_w).astype(np.float32) * ocean_fade
weight_base = gaussian_filter(weight_base, sigma=8)

# ── Phase 3: Regional soft masks ─────────────────────────────────────────────
print(f"[{ts()}] Phase 3: Regional soft masks...")

# East Asia
ea_lon = range_soft(LON, 112, 130, 100, 140)
ea_lat = range_soft(LAT,  22,  40,  15,  48)
ea_mask = (ea_lon * ea_lat).astype(np.float32)

# Tropical (v6.1: core ≤20°, transition 20-30°)
trop_mask = np.where(np.abs(LAT) <= 20, 1.0,
            np.where(np.abs(LAT) <= 30,
                     smoothstep((30 - np.abs(LAT)) / 10.0), 0.0)
            ).astype(np.float32)

# Persian Gulf
pg_lon = range_soft(LON, 48, 57, 44, 61)
pg_lat = range_soft(LAT, 24, 30, 20, 34)
pg_mask = (pg_lon * pg_lat).astype(np.float32)

# Red Sea
rs_lon = range_soft(LON, 32, 44, 28, 48)
rs_lat = range_soft(LAT, 12, 30,  8, 34)
rs_mask = (rs_lon * rs_lat).astype(np.float32)

# High latitude
hl_mask = np.where(LAT >= 50, 1.0,
          np.where(LAT >= 40, smoothstep((LAT - 40) / 10.0), 0.0)
          ).astype(np.float32)

print(f"  ea={ea_mask.mean()*100:.1f}%  trop={trop_mask.mean()*100:.1f}%"
      f"  pg={pg_mask.mean()*100:.2f}%  rs={rs_mask.mean()*100:.2f}%"
      f"  hl={hl_mask.mean()*100:.1f}%")

# ── Phase 4: Per-region target colors ────────────────────────────────────────
print(f"[{ts()}] Phase 4: Building regional target colors...")

# Global v6.1 (B >= G everywhere)
bp_dc = [0,    20,   50,   200,  1000]
glo_R = [120,  102,   85,   72,    52]
glo_G = [170,  157,  137,  107,    80]
glo_B = [178,  174,  159,  126,   105]

tgt_R = np.interp(d_val, bp_dc, glo_R).astype(np.float32)
tgt_G = np.interp(d_val, bp_dc, glo_G).astype(np.float32)
tgt_B = np.interp(d_val, bp_dc, glo_B).astype(np.float32)

# East Asia palette (v6.1 lighter offset: R+2 / G-2 / B-1)
ea_R = [130, 112,  92,  70,  52]
ea_G = [175, 158, 135, 106,  80]
ea_B = [174, 165, 150, 122, 105]
ea_tR = np.interp(d_val, bp_dc, ea_R).astype(np.float32)
ea_tG = np.interp(d_val, bp_dc, ea_G).astype(np.float32)
ea_tB = np.interp(d_val, bp_dc, ea_B).astype(np.float32)

# Tropical palette (v6.1: v5-aligned anchor #8ED8C8)
tr_R = [142, 103,  74,  58,  52]
tr_G = [216, 176, 143, 111,  80]
tr_B = [200, 184, 168, 134, 105]
tr_tR = np.interp(d_val, bp_dc, tr_R).astype(np.float32)
tr_tG = np.interp(d_val, bp_dc, tr_G).astype(np.float32)
tr_tB = np.interp(d_val, bp_dc, tr_B).astype(np.float32)

# Persian Gulf / Red Sea palette (warm gray)
pg_R = [169, 126,  90,  70,  52]
pg_G = [191, 165, 135, 106,  80]
pg_B = [175, 162, 148, 120, 105]
pg_tR = np.interp(d_val, bp_dc, pg_R).astype(np.float32)
pg_tG = np.interp(d_val, bp_dc, pg_G).astype(np.float32)
pg_tB = np.interp(d_val, bp_dc, pg_B).astype(np.float32)

# Composite: EA takes priority over tropical; PG/RS are geographic exclusions
# Priority order: EA > PG > RS > trop > global
# Build composite target via weighted blend
ea3  = ea_mask[..., np.newaxis]
# Tropical applies where NOT EA
tr_eff = (trop_mask * (1.0 - ea_mask)).astype(np.float32)
tr3  = tr_eff[..., np.newaxis]
pg3  = pg_mask[..., np.newaxis]
rs3  = rs_mask[..., np.newaxis]

# Residual global weight (what's left after regions)
residual = np.clip(1.0 - ea_mask - tr_eff - pg_mask - rs_mask, 0.0, 1.0)
res3 = residual[..., np.newaxis]

tgt = (np.stack([tgt_R, tgt_G, tgt_B], -1) * res3 +
       np.stack([ea_tR, ea_tG, ea_tB],  -1) * ea3 +
       np.stack([tr_tR, tr_tG, tr_tB],  -1) * tr3 +
       np.stack([pg_tR, pg_tG, pg_tB],  -1) * (pg3 + rs3)).astype(np.float32)
# Normalize in rare overlap zones (shouldn't happen but guard)
total_w = res3 + ea3 + tr3 + pg3 + rs3
tgt = np.where(total_w > 0, tgt / total_w, tgt)

# ── Phase 5: Regional weight multipliers ─────────────────────────────────────
print(f"[{ts()}] Phase 5: Regional weight multipliers...")

weight = weight_base.copy()
weight *= (1.0 + 0.15 * ea_mask)                           # EA:  +15%
weight *= (1.0 - 0.10 * trop_mask * (1.0 - ea_mask))       # trop: -10% (not where EA)
weight *= (1.0 - 0.05 * pg_mask)                            # PG:  -5%
weight *= (1.0 - 0.05 * rs_mask)                            # RS:  -5%
weight *= (1.0 - 0.05 * hl_mask)                            # HL:  -5%

# Tropical islands extra blur (soft mask only)
w_trop_blur = gaussian_filter(weight, sigma=4)
weight = weight * (1.0 - 0.5 * trop_mask) + w_trop_blur * (0.5 * trop_mask)

# Hard zero for deep ocean (> 1000m), no exceptions
weight = np.where(depth < -1000, 0.0, weight)
weight = np.clip(weight, 0.0, 0.16)

print(f"  weight max={weight.max():.4f}  mean(ocean)={weight[ocean_hard].mean():.5f}")

# ── Phase 6: Blend ────────────────────────────────────────────────────────────
print(f"[{ts()}] Phase 6: Blending D3 + v6.1 target...")
w3 = weight[..., np.newaxis]
result = d3 * (1.0 - w3) + tgt * w3

# ── Phase 7: Protections ──────────────────────────────────────────────────────
print(f"[{ts()}] Phase 7: Protections...")

# Land
lm = land_hard[..., np.newaxis].astype(np.float32)
result = d3 * lm + result * (1.0 - lm)

# Snow / ice
sm = snow_mask[..., np.newaxis].astype(np.float32)
result = d3 * sm + result * (1.0 - sm)

# Tropical saturation cap: output sat <= D3 sat + 0.015
def sat_arr(a):
    mx = np.maximum(np.maximum(a[...,0], a[...,1]), a[...,2])
    mn = np.minimum(np.minimum(a[...,0], a[...,1]), a[...,2])
    return np.where(mx > 0, (mx - mn) / mx, 0.0)

sat3 = sat_arr(d3)
satr = sat_arr(result)
trop_over = (satr > sat3 + 0.015) & (trop_mask > 0.2) & ocean_hard
to3 = trop_over[..., np.newaxis].astype(np.float32)
result = d3 * to3 + result * (1.0 - to3)

# Global anti-荧光: sat increase > 6% AND sat > 0.50
satr2 = sat_arr(result)
over = (satr2 > sat3 * 1.06) & (satr2 > 0.50) & ocean_hard
o3 = over[..., np.newaxis].astype(np.float32)
result = d3 * o3 + result * (1.0 - o3)

result = result.clip(0, 255).astype(np.uint8)

# ── Phase 8: Save ─────────────────────────────────────────────────────────────
print(f"[{ts()}] Phase 8: Saving D5c...")
out_img = Image.fromarray(result)
out_img.save(OUT_PATH, "JPEG", quality=95, subsampling=0)
shutil.copy2(OUT_PATH, CAND_OUT)
sz = os.path.getsize(OUT_PATH) // (1024*1024)
print(f"  {OUT_PATH}  ({sz}MB)")
print(f"  Copied → {CAND_OUT}")

# ── Phase 9: Metrics (D3 / D5a / D5b / D5c) ──────────────────────────────────
print(f"\n[{ts()}] Phase 9: Metrics (D3 / D5a / D5b / D5c, 28 zones)...")

res_f  = result.astype(np.float32)
d5a_f  = d5a.astype(np.float32)
d5b_f  = d5b.astype(np.float32)

def lum(a): return 0.299*a[...,0] + 0.587*a[...,1] + 0.114*a[...,2]

zones = [
    ("Yellow Sea",       119,126, 32,39),
    ("Bohai Sea",        117,122, 37,41),
    ("East China Sea",   120,130, 25,33),
    ("Taiwan Strait",    117,122, 22,26),
    ("S.China Sea N",    110,121, 15,23),
    ("Taiwan E deep",    122,130, 20,26),
    ("Philippines Luzon",119,126, 12,20),
    ("Persian Gulf",      48, 57, 24,30),
    ("Red Sea",           32, 44, 12,30),
    ("North Sea",         -4,  9, 52,61),
    ("Bahamas",          -80,-72, 22,28),
    ("Caribbean",        -85,-60, 10,25),
    ("Great Barrier Reef",142,154,-24,-10),
    ("Australia North",  124,142,-18, -8),
    ("Maldives",          72, 74, -1,  8),
    ("Indonesia",         95,130,-10,  8),
    ("Philippines",      117,127,  5, 20),
    ("Pacific Deep",    -160,-130,-20, 10),
    ("Indian Ocean D",    65, 95,-30, -5),
    ("N.Atlantic D",     -50,-25, 20, 45),
    ("Southern Ocean",  -160,-80,-60,-45),
    ("Mariana",          140,150, 10, 25),
    ("Antarctica",      -180,180,-90,-70),
    ("Greenland",        -55,-20, 60, 83),
    ("Arctic",          -180,180, 80, 90),
    ("Tibetan Plateau",   75,105, 28, 40),
    ("Sahara",           -15, 35, 15, 35),
    ("Amazon",           -65,-45,-10,  5),
]

LAND_ZONES = {"Antarctica","Greenland","Arctic","Tibetan Plateau","Sahara","Amazon"}

metrics = {}
hdr = (f"  {'Zone':<22} {'dep':>6} {'0-20':>5} {'0-50':>5} {'>1k':>4} | "
       f"{'D3 R/G/B':^13} {'D5c R/G/B':^13} | "
       f"{'5c-3':>8} {'5c-a':>8} {'5c-b':>8} | "
       f"{'BG3':>5}{'BG5c':>5} | "
       f"{'s3':>5}{'s5c':>5} | ok?")
print(hdr)
print("  " + "-"*118)

for (name, lw, le, ls, ln) in zones:
    full = (lw == -180 and le == 180)
    r1,r2,c1,c2 = bbox(lw,le,ls,ln)
    s = (slice(r1,r2), slice(None) if full else slice(c1,c2))

    pd3=d3[s]; pr=res_f[s]; pa=d5a_f[s]; pb=d5b_f[s]
    pdep=depth[s]

    if name in LAND_ZONES:
        diff3 = float(np.abs(pr - pd3).max())
        lum_d = (lum(pr).mean() / (lum(pd3).mean()+1e-6) - 1)*100
        print(f"  {name:<22} {'—':>6} {'—':>5} {'—':>5} {'—':>4} | "
              f"{'land/ice':<13} {'':^13} | max_diff_D3={diff3:.1f}  lum_Δ={lum_d:+.2f}%")
        metrics[name] = dict(max_diff_d3=round(diff3,2), lum_change_pct=round(lum_d,3))
        continue

    om = pdep < 0
    if om.sum() < 20:
        continue

    doc = pdep[om]; dn = -doc
    dep_m = float(dn.mean())
    p0_20 = float((dn<20).mean()*100)
    p0_50 = float((dn<50).mean()*100)
    p1k   = float((dn>=1000).mean()*100)

    def avg(arr, m):
        return arr[...,0][m].mean(), arr[...,1][m].mean(), arr[...,2][m].mean()

    R3m,G3m,B3m = avg(pd3, om)
    Rrm,Grm,Brm = avg(pr,  om)
    Ram,Gam,Bam = avg(pa,  om)
    Rbm,Gbm,Bbm = avg(pb,  om)

    BG3  = B3m/(G3m+1e-6); BG5c = Brm/(Grm+1e-6)
    s3   = float(sat_arr(pd3)[om].mean())
    sc   = float(sat_arr(pr)[om].mean())

    l3 = lum(pd3); lc_arr = lum(pr)
    lm3 = float(l3[om].mean()); lmc = float(lc_arr[om].mean())
    p95_3 = float(np.percentile(l3[om], 95)); p99_3 = float(np.percentile(l3[om], 99))
    p95_c = float(np.percentile(lc_arr[om], 95)); p99_c = float(np.percentile(lc_arr[om], 99))

    dR3=Rrm-R3m; dG3=Grm-G3m; dB3=Brm-B3m
    dRa=Rrm-Ram; dBa=Brm-Bam
    dRb=Rrm-Rbm; dBb=Brm-Bbm

    # Pass/fail
    ok = True
    if name in ("Pacific Deep","Indian Ocean D","N.Atlantic D","Southern Ocean","Mariana","Taiwan E deep"):
        ok = abs(dR3)<=0.5 and abs(dG3)<=0.5 and abs(dB3)<=0.5
    elif sc > s3 + 0.020:
        ok = False

    metrics[name] = dict(
        depth_mean=round(dep_m,1), pct_0_20=round(p0_20,1),
        pct_0_50=round(p0_50,1), pct_gt1k=round(p1k,1),
        d3 =dict(R=round(R3m,1),G=round(G3m,1),B=round(B3m,1),
                 BG=round(BG3,3),sat=round(s3,4),
                 lum=round(lm3,2),p95=round(p95_3,2),p99=round(p99_3,2)),
        d5a=dict(R=round(Ram,1),G=round(Gam,1),B=round(Bam,1)),
        d5b=dict(R=round(Rbm,1),G=round(Gbm,1),B=round(Bbm,1)),
        d5c=dict(R=round(Rrm,1),G=round(Grm,1),B=round(Brm,1),
                 BG=round(BG5c,3),sat=round(sc,4),
                 lum=round(lmc,2),p95=round(p95_c,2),p99=round(p99_c,2)),
        delta_d3 =dict(R=round(dR3,1),G=round(dG3,1),B=round(dB3,1),sat=round(sc-s3,4)),
        delta_d5a=dict(R=round(dRa,1),B=round(dBa,1)),
        delta_d5b=dict(R=round(dRb,1),B=round(dBb,1)),
        pass_check=bool(ok),
    )

    flag = "✓" if ok else "✗"
    d3_str = f"{R3m:>4.0f}/{G3m:>4.0f}/{B3m:>4.0f}"
    dc_str = f"{Rrm:>4.0f}/{Grm:>4.0f}/{Brm:>4.0f}"
    d3d = f"{dR3:>+3.0f}/{dG3:>+3.0f}/{dB3:>+3.0f}"
    dad = f"{dRa:>+3.0f}/{dBa:>+3.0f}"
    dbd = f"{dRb:>+3.0f}/{dBb:>+3.0f}"
    print(f"  {name:<22} {dep_m:>6.0f} {p0_20:>5.1f} {p0_50:>5.1f} {p1k:>4.0f} | "
          f"{d3_str}  {dc_str} | "
          f"{d3d:>8} {dad:>8} {dbd:>8} | "
          f"{BG3:>5.3f}{BG5c:>5.3f} | "
          f"{s3:>5.3f}{sc:>5.3f} | {flag}")

# ── Phase 10: Devlog ──────────────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 10: Writing devlog...")

passing = [k for k,v in metrics.items() if v.get('pass_check') is True]
failing  = [k for k,v in metrics.items() if v.get('pass_check') is False]

with open(DEVLOG, "w") as f:
    f.write(f"# D5c / Ocean Palette v6.1 Candidate Report\n\n")
    f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}  \n")
    f.write(f"**Stage:** Bathy-3 — D5c generation  \n")
    f.write(f"**Palette:** Ocean Palette v6.1  \n")
    f.write(f"**Status:** {'PASS' if not failing else 'PARTIAL — ' + ', '.join(failing)}  \n\n")
    f.write("---\n\n## 1. Parameters\n\n")
    f.write("| Param | D5b | D5c / v6.1 |\n|---|---|---|\n")
    rows = [
        ("0–20m weight",   "0.14","0.16"),
        ("20–50m weight",  "0.11","0.13"),
        ("50–200m weight", "0.08","0.09"),
        ("200–1km weight", "0.03","0.03"),
        (">1000m weight",  "0.00","0.00"),
        ("depth sigma",    "12",  "12"),
        ("weight sigma",   "8",   "8"),
        ("0–20m global",   "118/165/170","120/170/178"),
        ("0–20m tropical", "same as global","142/216/200 (#8ED8C8 v5 anchor)"),
        ("0–20m EA",       "offset R+2/G-6/B-2","130/175/174, offset R+2/G-2/B-1"),
        ("0–20m Gulf/RS",  "169/191/175","169/191/175 (unchanged)"),
        ("Turbid coastal", "disabled","disabled"),
        ("Abyss / deep",   "disabled","disabled"),
    ]
    for r in rows:
        f.write(f"| {r[0]} | {r[1]} | {r[2]} |\n")

    f.write("\n### Turbid Coastal — intentionally disabled\n\n")
    f.write("> Turbid coastal colors are intentionally disabled in D5c / v6.1. "
            "The reason is not only the lack of a reliable turbidity mask, but also that "
            "the Blue Marble / D3 base texture already contains organic sediment and coastal "
            "color information in regions such as the Yellow Sea, Yangtze River Estuary, "
            "Pearl River Estuary and other major nearshore zones. Re-applying an additional "
            "turbid blend would likely cause double contamination, making nearshore waters "
            "dirtier rather than more realistic.\n\n")
    f.write("### Abyss / Deep Ocean Palette — not used\n\n")
    f.write("> Weight = 0.00 for all pixels deeper than 1000 m. "
            "No ETOPO1 texture is applied to the deep ocean. "
            "Deep ocean information deficit is deferred to the cloud/atmosphere/lighting phase.\n\n")

    f.write("---\n\n## 2. Zone Metrics — D3 / D5a / D5b / D5c\n\n")
    f.write("| Zone | dep | 0-20% | 0-50% | >1k% | D3 R/G/B | D5a | D5b | D5c | "
            "D5c-D3 R/G/B | D5c-D5a R/B | D5c-D5b R/B | BG-D3 | BG-D5c | sat3 | satD5c |\n")
    f.write("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    for (name,*_) in zones:
        m = metrics.get(name, {})
        if 'max_diff_d3' in m:
            f.write(f"| {name} | — | — | — | — | land/ice | — | — | — | "
                    f"max_diff={m['max_diff_d3']} | — | — | — | — | — | — |\n")
            continue
        if not m:
            continue
        d3m=m['d3']; da=m.get('d5a',{}); db=m.get('d5b',{}); dc=m['d5c']
        dd3=m['delta_d3']; dda=m['delta_d5a']; ddb=m['delta_d5b']
        f.write(f"| {name} | {m['depth_mean']} | {m['pct_0_20']} | {m['pct_0_50']} | {m['pct_gt1k']} | "
                f"{d3m['R']}/{d3m['G']}/{d3m['B']} | "
                f"{da.get('R','—')}/{da.get('G','—')}/{da.get('B','—')} | "
                f"{db.get('R','—')}/{db.get('G','—')}/{db.get('B','—')} | "
                f"{dc['R']}/{dc['G']}/{dc['B']} | "
                f"{dd3['R']:+}/{dd3['G']:+}/{dd3['B']:+} | "
                f"{dda['R']:+}/{dda['B']:+} | "
                f"{ddb['R']:+}/{ddb['B']:+} | "
                f"{d3m['BG']} | {dc['BG']} | {d3m['sat']} | {dc['sat']} |\n")

    f.write(f"\n---\n\n## 3. Pass/Fail\n\n")
    f.write(f"Passing: {len(passing)} / {len(metrics)} zones  \n")
    if failing:
        f.write(f"Failing: {', '.join(failing)}  \n")

    f.write(f"\n---\n\n## 4. Files\n\n```\n{OUT_PATH}\n{CAND_OUT}\n```\n\n")
    f.write("---\n\n## 5. Confirmations\n\n")
    f.write("- pwa/earth3d.js: NOT modified ✓\n"
            "- dayTexture default: NOT changed ✓\n"
            "- nightTexture / cloudMesh / atmosphere / UI: NOT modified ✓\n"
            "- No commit ✓\n")

print(f"  {DEVLOG}")

# ── Summary ───────────────────────────────────────────────────────────────────
elapsed = (datetime.now() - T0).total_seconds()
print(f"\n{'='*68}")
print("D5c / Ocean Palette v6.1 candidate generation completed.")
print(f"{'='*68}")
print(f"\nChanged files:")
print(f"  {OUT_PATH}")
print(f"  {CAND_OUT}")
print(f"  {DEVLOG}")
print(f"\nNot changed:")
print(f"  pwa/earth3d.js  |  dayTexture default  |  nightTexture")
print(f"  cloudMesh  |  atmosphere  |  theme visual config")
print(f"  UI/index.html  |  Service Worker  |  shader  |  mesh")
print(f"\nCommitted: No")
print(f"\nPalette: Ocean Palette v6.1")
print(f"Key parameters:")
print(f"  weights:  0.16 / 0.13 / 0.09 / 0.03 / 0.00")
print(f"  depth sigma: 12  |  weight sigma: 8")
print(f"  global 0-20m:   120/170/178")
print(f"  tropical 0-20m: 142/216/200  (#8ED8C8, v5 anchor)")
print(f"  turbid coastal: disabled")
print(f"  abyss:          disabled")
print(f"  deep ocean:     protected (weight=0)")
print(f"\nZone results: {len(passing)} pass / {len(failing)} fail")
if failing:
    print(f"  Failing: {', '.join(failing)}")
print(f"\nElapsed: {elapsed:.0f}s")
rec = "D5c should enter browser visual acceptance." if not failing else \
      "Review failing zones before on-globe test."
print(f"\nRecommendation: {rec}")
