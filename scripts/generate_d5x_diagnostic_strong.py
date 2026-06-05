#!/usr/bin/env python3
"""
D5x Diagnostic Strong — verify texture layer headroom.
Stronger weights (0.20/0.16/0.12/0.04/0.00), same blur as D5b/D5c.
NOT a final candidate. NOT modifying earth3d.js or any runtime code.
"""

import numpy as np
from PIL import Image
import netCDF4 as nc
from scipy.ndimage import gaussian_filter
import os, json, shutil
from datetime import datetime

BASE    = os.path.expanduser("~/Projects/RodiO/pwa/assets/source")
D3_PATH  = f"{BASE}/bmng_staging/bmng_processed_8192x4096_natural_d3.jpg"
D5B_PATH = f"{BASE}/bmng_staging/bmng_processed_8192x4096_natural_d5b_bathy.jpg"
D5C_PATH = f"{BASE}/bmng_staging/bmng_processed_8192x4096_natural_d5c_palette_v6_1_bathy.jpg"
ETOPO    = f"{BASE}/bathy/ETOPO1_Ice_g_gdal.grd"
OUT_PATH = f"{BASE}/bmng_staging/bmng_processed_8192x4096_natural_d5x_diagnostic_strong_bathy.jpg"
CAND_DIR = os.path.expanduser("~/Projects/RodiO/pwa/assets/earth/candidates")
CAND_OUT = f"{CAND_DIR}/d5x_diagnostic_strong_bathy_8192x4096.jpg"
DEVLOG   = os.path.expanduser("~/Projects/RodiO/docs/devlog_bathy_3_d5x_diagnostic_strong_candidate.md")

D3_W, D3_H = 8192, 4096
T0 = datetime.now()
def ts(): return datetime.now().strftime('%H:%M:%S')

print("=" * 68)
print("D5x Diagnostic Strong candidate")
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 68)

# ── Load ──────────────────────────────────────────────────────────────────────
print(f"\n[{ts()}] Loading D3 / D5b / D5c...")
d3_img  = Image.open(D3_PATH).convert("RGB")
d5b_img = Image.open(D5B_PATH).convert("RGB")
d5c_img = Image.open(D5C_PATH).convert("RGB")
d3  = np.array(d3_img,  dtype=np.float32)
d5b = np.array(d5b_img, dtype=np.float32)
d5c = np.array(d5c_img, dtype=np.float32)

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
    r = int(round((90 - lat)  / 180 * (D3_H - 1)))
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

def sat_arr(a):
    mx = np.maximum(np.maximum(a[...,0], a[...,1]), a[...,2])
    mn = np.minimum(np.minimum(a[...,0], a[...,1]), a[...,2])
    return np.where(mx > 0, (mx - mn) / mx, 0.0)

# ── Phase 1: Masks ────────────────────────────────────────────────────────────
print(f"[{ts()}] Phase 1: Masks...")
ocean_hard = depth < 0
land_hard  = depth >= 0
ocean_fade = gaussian_filter(ocean_hard.astype(np.float32), sigma=3)
ocean_fade = np.clip(ocean_fade / 0.85, 0.0, 1.0)
R3, G3, B3 = d3[...,0], d3[...,1], d3[...,2]
snow_mask  = (R3 > 210) & (G3 > 210) & (B3 > 210)
print(f"  ocean={ocean_hard.mean()*100:.1f}%  snow={snow_mask.mean()*100:.1f}%")

# ── Phase 2: Depth weights (D5x: stronger, same blur) ────────────────────────
print(f"[{ts()}] Phase 2: Depth weights (sigma_d=12, sigma_w=8)...")
depth_sm = gaussian_filter(depth, sigma=12)
d_val    = np.clip(-depth_sm, 0.0, 12000.0)

# D5x weights — meaningfully stronger than D5c (0.16/0.13/0.09)
bp_d = [0,    20,   50,   200,   1000,  4000]
bp_w = [0.20, 0.20, 0.16, 0.12,  0.04,  0.00]
weight_base = np.interp(d_val, bp_d, bp_w).astype(np.float32) * ocean_fade
weight_base = gaussian_filter(weight_base, sigma=8)  # same second-pass blur

# ── Phase 3: Regional soft masks ─────────────────────────────────────────────
print(f"[{ts()}] Phase 3: Regional soft masks...")

ea_lon = range_soft(LON, 112, 130, 100, 140)
ea_lat = range_soft(LAT,  22,  40,  15,  48)
ea_mask = (ea_lon * ea_lat).astype(np.float32)

trop_mask = np.where(np.abs(LAT) <= 20, 1.0,
            np.where(np.abs(LAT) <= 30,
                     smoothstep((30 - np.abs(LAT)) / 10.0), 0.0)
            ).astype(np.float32)

pg_lon = range_soft(LON, 48, 57, 44, 61)
pg_lat = range_soft(LAT, 24, 30, 20, 34)
pg_mask = (pg_lon * pg_lat).astype(np.float32)

rs_lon = range_soft(LON, 32, 44, 28, 48)
rs_lat = range_soft(LAT, 12, 30,  8, 34)
rs_mask = (rs_lon * rs_lat).astype(np.float32)

hl_mask = np.where(LAT >= 50, 1.0,
          np.where(LAT >= 40, smoothstep((LAT - 40) / 10.0), 0.0)
          ).astype(np.float32)

print(f"  ea={ea_mask.mean()*100:.1f}%  trop={trop_mask.mean()*100:.1f}%"
      f"  pg={pg_mask.mean()*100:.2f}%  rs={rs_mask.mean()*100:.2f}%")

# ── Phase 4: Target colors ────────────────────────────────────────────────────
print(f"[{ts()}] Phase 4: Target colors (v6.1 base, no new palette)...")

bp_dc = [0,    20,   50,   200,  1000]

# Global base (same as D5c / v6.1)
glo_R = [120,  102,   85,   72,    52]
glo_G = [170,  157,  137,  107,    80]
glo_B = [178,  174,  159,  126,   105]

tgt_R = np.interp(d_val, bp_dc, glo_R).astype(np.float32)
tgt_G = np.interp(d_val, bp_dc, glo_G).astype(np.float32)
tgt_B = np.interp(d_val, bp_dc, glo_B).astype(np.float32)

# East Asia (same as D5c, softer offset)
ea_R = [130, 112,  92,  70,  52]
ea_G = [175, 158, 135, 106,  80]
ea_B = [174, 165, 150, 122, 105]
ea_tR = np.interp(d_val, bp_dc, ea_R).astype(np.float32)
ea_tG = np.interp(d_val, bp_dc, ea_G).astype(np.float32)
ea_tB = np.interp(d_val, bp_dc, ea_B).astype(np.float32)

# Tropical (v5 anchor, same as D5c)
tr_R = [142, 103,  74,  58,  52]
tr_G = [216, 176, 143, 111,  80]
tr_B = [200, 184, 168, 134, 105]
tr_tR = np.interp(d_val, bp_dc, tr_R).astype(np.float32)
tr_tG = np.interp(d_val, bp_dc, tr_G).astype(np.float32)
tr_tB = np.interp(d_val, bp_dc, tr_B).astype(np.float32)

# Persian Gulf / Red Sea (same as D5c)
pg_R = [169, 126,  90,  70,  52]
pg_G = [191, 165, 135, 106,  80]
pg_B = [175, 162, 148, 120, 105]
pg_tR = np.interp(d_val, bp_dc, pg_R).astype(np.float32)
pg_tG = np.interp(d_val, bp_dc, pg_G).astype(np.float32)
pg_tB = np.interp(d_val, bp_dc, pg_B).astype(np.float32)

# Composite: EA > PG/RS > trop > global
ea3  = ea_mask[..., np.newaxis]
tr_eff = (trop_mask * (1.0 - ea_mask)).astype(np.float32)
tr3  = tr_eff[..., np.newaxis]
pg3  = pg_mask[..., np.newaxis]
rs3  = rs_mask[..., np.newaxis]
residual = np.clip(1.0 - ea_mask - tr_eff - pg_mask - rs_mask, 0.0, 1.0)
res3 = residual[..., np.newaxis]

tgt = (np.stack([tgt_R, tgt_G, tgt_B], -1) * res3 +
       np.stack([ea_tR, ea_tG, ea_tB],  -1) * ea3 +
       np.stack([tr_tR, tr_tG, tr_tB],  -1) * tr3 +
       np.stack([pg_tR, pg_tG, pg_tB],  -1) * (pg3 + rs3)).astype(np.float32)
total_w = res3 + ea3 + tr3 + pg3 + rs3
tgt = np.where(total_w > 0, tgt / total_w, tgt)

# ── Phase 5: Regional weight multipliers (D5x specific) ──────────────────────
print(f"[{ts()}] Phase 5: Regional weight multipliers (D5x)...")

weight = weight_base.copy()
weight *= (1.0 + 0.20 * ea_mask)                            # EA:  +20%
weight *= (1.0 - 0.05 * trop_mask * (1.0 - ea_mask))        # trop: -5%
weight *= (1.0 - 0.00 * pg_mask)                             # PG:  ×1.00
weight *= (1.0 - 0.00 * rs_mask)                             # RS:  ×1.00
weight *= (1.0 - 0.05 * hl_mask)                             # HL:  -5%

# Tropical islands extra blur (soft mask)
w_trop_blur = gaussian_filter(weight, sigma=4)
weight = weight * (1.0 - 0.5 * trop_mask) + w_trop_blur * (0.5 * trop_mask)

# Hard zero for deep ocean
weight = np.where(depth < -1000, 0.0, weight)
weight = np.clip(weight, 0.0, 0.20)

print(f"  weight max={weight.max():.4f}  mean(ocean)={weight[ocean_hard].mean():.5f}")

# ── Phase 6: Blend ────────────────────────────────────────────────────────────
print(f"[{ts()}] Phase 6: Blending...")
w3 = weight[..., np.newaxis]
result = d3 * (1.0 - w3) + tgt * w3

# ── Phase 7: Protections ──────────────────────────────────────────────────────
print(f"[{ts()}] Phase 7: Protections (land / snow / sat cap)...")

lm = land_hard[..., np.newaxis].astype(np.float32)
result = d3 * lm + result * (1.0 - lm)

sm = snow_mask[..., np.newaxis].astype(np.float32)
result = d3 * sm + result * (1.0 - sm)

sat3 = sat_arr(d3)
satr = sat_arr(result)
# Tropical sat cap: D3 + 0.020
trop_over = (satr > sat3 + 0.020) & (trop_mask > 0.2) & ocean_hard
to3 = trop_over[..., np.newaxis].astype(np.float32)
result = d3 * to3 + result * (1.0 - to3)
# Global anti-荧光
satr2 = sat_arr(result)
over = (satr2 > sat3 * 1.08) & (satr2 > 0.52) & ocean_hard
o3 = over[..., np.newaxis].astype(np.float32)
result = d3 * o3 + result * (1.0 - o3)

result = result.clip(0, 255).astype(np.uint8)

# ── Phase 8: Save ─────────────────────────────────────────────────────────────
print(f"[{ts()}] Phase 8: Saving D5x...")
out_img = Image.fromarray(result)
out_img.save(OUT_PATH, "JPEG", quality=95, subsampling=0)
shutil.copy2(OUT_PATH, CAND_OUT)
sz = os.path.getsize(OUT_PATH) // (1024*1024)
print(f"  {OUT_PATH}  ({sz}MB)")
print(f"  Copied → {CAND_OUT}")

# ── Phase 9: Difference strength ─────────────────────────────────────────────
print(f"\n[{ts()}] Phase 9: Difference strength vs D5b / D5c...")

res_f = result.astype(np.float32)

def diff_stats(a, b, label_a, label_b):
    diff = np.abs(a.astype(np.float32) - b.astype(np.float32))
    max_ch = diff.max(axis=-1)
    total  = max_ch.size
    print(f"\n  {label_a} vs {label_b}:")
    print(f"    global mean abs delta (all channels): {diff.mean():.4f}")
    print(f"    global mean abs delta (max channel):  {max_ch.mean():.4f}")
    pct3 = (max_ch > 3).mean() * 100
    pct5 = (max_ch > 5).mean() * 100
    pct8 = (max_ch > 8).mean() * 100
    print(f"    any-channel diff > 3: {pct3:.2f}%")
    print(f"    any-channel diff > 5: {pct5:.2f}%")
    print(f"    any-channel diff > 8: {pct8:.2f}%")
    # Ocean-only
    om = ocean_hard
    diff_oc = diff[om]
    max_oc  = diff_oc.max(axis=-1) if diff_oc.ndim > 1 else diff[om].max(axis=-1)
    print(f"    ocean mean abs delta: {diff[om].mean():.4f}")
    return dict(mean_abs=round(float(diff.mean()),4),
                mean_max_ch=round(float(max_ch.mean()),4),
                pct_gt3=round(pct3,3), pct_gt5=round(pct5,3), pct_gt8=round(pct8,3),
                ocean_mean_abs=round(float(diff[om].mean()),4))

stats_vs_d5b = diff_stats(res_f, d5b.astype(np.float32), "D5x", "D5b")
stats_vs_d5c = diff_stats(res_f, d5c.astype(np.float32), "D5x", "D5c")

# ── Phase 10: Zone metrics ────────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 10: Zone metrics (D3/D5b/D5c/D5x)...")

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
       f"{'D3':^13} {'D5x':^13} | "
       f"{'5x-3':>9} {'5x-b':>9} {'5x-c':>9} | "
       f"{'BG3':>5}{'BG5x':>5} | ok?")
print(hdr)
print("  " + "-"*115)

deep_zones = {"Pacific Deep","Indian Ocean D","N.Atlantic D","Southern Ocean","Mariana","Taiwan E deep"}

for (name, lw, le, ls, ln) in zones:
    full = (lw == -180 and le == 180)
    r1,r2,c1,c2 = bbox(lw,le,ls,ln)
    s = (slice(r1,r2), slice(None) if full else slice(c1,c2))

    pd3=d3[s]; pr=res_f[s]; pb=d5b[s].astype(np.float32); pc=d5c[s].astype(np.float32)
    pdep=depth[s]

    if name in LAND_ZONES:
        diff3 = float(np.abs(pr - pd3).max())
        lc = (lum(pr).mean() / (lum(pd3).mean()+1e-6) - 1)*100
        print(f"  {name:<22} {'land/ice':>6}  max_diff_D3={diff3:.1f}  lum_Δ={lc:+.2f}%")
        metrics[name] = dict(max_diff_d3=round(diff3,2), lum_change=round(lc,3))
        continue

    om = pdep < 0
    if om.sum() < 20: continue

    doc = pdep[om]; dn = -doc
    dep_m = float(dn.mean())
    p0_20 = float((dn<20).mean()*100)
    p0_50 = float((dn<50).mean()*100)
    p1k   = float((dn>=1000).mean()*100)

    def avg(arr, m):
        return arr[...,0][m].mean(), arr[...,1][m].mean(), arr[...,2][m].mean()

    R3m,G3m,B3m = avg(pd3, om)
    Rrm,Grm,Brm = avg(pr,  om)
    Rbm,Gbm,Bbm = avg(pb,  om)
    Rcm,Gcm,Bcm = avg(pc,  om)

    BG3  = B3m/(G3m+1e-6); BG5x = Brm/(Grm+1e-6)
    s3   = float(sat_arr(pd3)[om].mean())
    sx   = float(sat_arr(pr)[om].mean())
    lm3  = float(lum(pd3)[om].mean()); lmx = float(lum(pr)[om].mean())

    dR3=Rrm-R3m; dG3=Grm-G3m; dB3=Brm-B3m
    dRb=Rrm-Rbm; dBb=Brm-Bbm
    dRc=Rrm-Rcm; dBc=Brm-Bcm

    ok = True
    if name in deep_zones:
        ok = abs(dR3)<=0.5 and abs(dG3)<=0.5 and abs(dB3)<=0.5
    elif sx > s3 + 0.025:
        ok = False

    metrics[name] = dict(
        depth_mean=round(dep_m,1), pct_0_20=round(p0_20,1),
        pct_0_50=round(p0_50,1), pct_gt1k=round(p1k,1),
        d3 =dict(R=round(R3m,1),G=round(G3m,1),B=round(B3m,1),BG=round(BG3,3),sat=round(s3,4),lum=round(lm3,2)),
        d5b=dict(R=round(Rbm,1),G=round(Gbm,1),B=round(Bbm,1)),
        d5c=dict(R=round(Rcm,1),G=round(Gcm,1),B=round(Bcm,1)),
        d5x=dict(R=round(Rrm,1),G=round(Grm,1),B=round(Brm,1),BG=round(BG5x,3),sat=round(sx,4),lum=round(lmx,2)),
        delta_d3 =dict(R=round(dR3,1),G=round(dG3,1),B=round(dB3,1)),
        delta_d5b=dict(R=round(dRb,1),B=round(dBb,1)),
        delta_d5c=dict(R=round(dRc,1),B=round(dBc,1)),
        pass_check=bool(ok),
    )

    flag = "✓" if ok else "✗"
    d3s = f"{R3m:>4.0f}/{G3m:>4.0f}/{B3m:>4.0f}"
    dxs = f"{Rrm:>4.0f}/{Grm:>4.0f}/{Brm:>4.0f}"
    d3d = f"{dR3:>+3.0f}/{dG3:>+3.0f}/{dB3:>+3.0f}"
    dbd = f"{dRb:>+3.0f}/{dBb:>+3.0f}"
    dcd = f"{dRc:>+3.0f}/{dBc:>+3.0f}"
    print(f"  {name:<22} {dep_m:>6.0f} {p0_20:>5.1f} {p0_50:>5.1f} {p1k:>4.0f} | "
          f"{d3s}  {dxs} | "
          f"{d3d:>9} {dbd:>9} {dcd:>9} | "
          f"{BG3:>5.3f}{BG5x:>5.3f} | {flag}")

passing = [k for k,v in metrics.items() if v.get('pass_check') is True]
failing  = [k for k,v in metrics.items() if v.get('pass_check') is False]

# ── Phase 11: Devlog ──────────────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 11: Writing devlog...")
with open(DEVLOG, "w") as f:
    f.write("# D5x Diagnostic Strong Candidate Report\n\n")
    f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}  \n")
    f.write(f"**Purpose:** Diagnostic only — verify texture layer headroom  \n")
    f.write(f"**Status:** {'PASS' if not failing else 'PARTIAL — ' + ', '.join(failing)}  \n\n")
    f.write("---\n\n## 1. Parameters\n\n")
    f.write("| Param | D5c | D5x |\n|---|---|---|\n")
    rows = [
        ("0–20m weight",  "0.16","**0.20**"),
        ("20–50m weight", "0.13","**0.16**"),
        ("50–200m weight","0.09","**0.12**"),
        ("200–1km weight","0.03","0.03"),
        (">1000m weight", "0.00","0.00"),
        ("depth sigma",   "12",  "12"),
        ("weight sigma",  "8",   "8"),
        ("EA multiplier", "1.15","**1.20**"),
        ("trop multiplier","0.90","**0.95**"),
        ("PG/RS multiplier","0.95","**1.00**"),
        ("trop sat cap",  "D3+0.015","D3+0.020"),
        ("global target 0-20m","120/170/178","120/170/178 (unchanged)"),
        ("trop target 0-20m","142/216/200","142/216/200 (unchanged)"),
        ("turbid coastal","disabled","disabled"),
        ("abyss","disabled","disabled"),
    ]
    for r in rows:
        f.write(f"| {r[0]} | {r[1]} | {r[2]} |\n")

    f.write("\n---\n\n## 2. Difference Strength\n\n")
    f.write("| Metric | D5x vs D5b | D5x vs D5c |\n|---|---|---|\n")
    for k in ["mean_abs","mean_max_ch","pct_gt3","pct_gt5","pct_gt8","ocean_mean_abs"]:
        f.write(f"| {k} | {stats_vs_d5b[k]} | {stats_vs_d5c[k]} |\n")
    f.write(f"\n> Reference: D5c vs D5b pct_gt3 ≈ 2.4%,  pct_gt5 ≈ 0.6%\n\n")
    f.write(f"> D5x target: pct_gt3 clearly higher, proving meaningful visual increase.\n\n")

    f.write("---\n\n## 3. Zone Metrics\n\n")
    f.write("| Zone | dep | 0-20% | 0-50% | >1k% | D3 R/G/B | D5b | D5c | D5x | "
            "D5x-D3 | D5x-D5b R/B | D5x-D5c R/B | BG3 | BG5x | sat3 | satD5x |\n")
    f.write("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    for (name,*_) in zones:
        m = metrics.get(name,{})
        if 'max_diff_d3' in m:
            f.write(f"| {name} | — | — | — | — | land/ice | — | — | — | "
                    f"max_diff={m['max_diff_d3']} | — | — | — | — | — | — |\n")
            continue
        if not m: continue
        d3m=m['d3']; db=m.get('d5b',{}); dc=m.get('d5c',{}); dx=m['d5x']
        dd3=m['delta_d3']; ddb=m['delta_d5b']; ddc=m['delta_d5c']
        f.write(f"| {name} | {m['depth_mean']} | {m['pct_0_20']} | {m['pct_0_50']} | {m['pct_gt1k']} | "
                f"{d3m['R']}/{d3m['G']}/{d3m['B']} | "
                f"{db.get('R','—')}/{db.get('G','—')}/{db.get('B','—')} | "
                f"{dc.get('R','—')}/{dc.get('G','—')}/{dc.get('B','—')} | "
                f"{dx['R']}/{dx['G']}/{dx['B']} | "
                f"{dd3['R']:+}/{dd3['G']:+}/{dd3['B']:+} | "
                f"{ddb['R']:+}/{ddb['B']:+} | "
                f"{ddc['R']:+}/{ddc['B']:+} | "
                f"{d3m['BG']} | {dx['BG']} | {d3m['sat']} | {dx['sat']} |\n")

    f.write("\n---\n\n## 4. Pass/Fail\n\n")
    f.write(f"Passing: {len(passing)} / {len(metrics)} zones  \n")
    if failing: f.write(f"Failing: {', '.join(failing)}  \n")
    f.write("\n---\n\n## 5. Confirmations\n\n")
    f.write("- pwa/earth3d.js: NOT modified ✓\n"
            "- dayTexture default: NOT changed ✓\n"
            "- nightTexture / cloudMesh / atmosphere / UI: NOT modified ✓\n"
            "- turbid coastal: disabled ✓\n- abyss: disabled ✓\n- No commit ✓\n")

print(f"  {DEVLOG}")

# ── Summary ───────────────────────────────────────────────────────────────────
elapsed = (datetime.now() - T0).total_seconds()
print(f"\n{'='*68}")
print("D5x diagnostic strong candidate generation completed.")
print(f"{'='*68}")
print(f"\nChanged files:")
print(f"  {OUT_PATH}")
print(f"  {CAND_OUT}")
print(f"  {DEVLOG}")
print(f"\nNot changed:")
print(f"  pwa/earth3d.js · dayTexture default · nightTexture")
print(f"  cloudMesh · atmosphere · theme visual config · UI · SW · shader · mesh")
print(f"\nCommitted: No")
print(f"\nKey parameters:")
print(f"  weights:           0.20 / 0.16 / 0.12 / 0.04 / 0.00")
print(f"  depth sigma:       12  |  weight sigma: 8")
print(f"  EA multiplier:     1.20  |  Tropical: 0.95  |  PG/RS: 1.00")
print(f"  deep ocean:        protected (weight=0)")
print(f"  turbid coastal:    disabled  |  abyss: disabled")
print(f"\nDifference strength:")
print(f"  D5x vs D5b  any-channel > 3: {stats_vs_d5b['pct_gt3']:.2f}%"
      f"  > 5: {stats_vs_d5b['pct_gt5']:.2f}%"
      f"  > 8: {stats_vs_d5b['pct_gt8']:.2f}%")
print(f"  D5x vs D5c  any-channel > 3: {stats_vs_d5c['pct_gt3']:.2f}%"
      f"  > 5: {stats_vs_d5c['pct_gt5']:.2f}%"
      f"  > 8: {stats_vs_d5c['pct_gt8']:.2f}%")
print(f"\nZone results: {len(passing)} pass / {len(failing)} fail")
if failing: print(f"  Failing: {', '.join(failing)}")
print(f"\nElapsed: {elapsed:.0f}s")
rec = "D5x should enter browser diagnostic acceptance." if not failing else \
      "Review failing zones before browser test."
print(f"\nRecommendation: {rec}")
