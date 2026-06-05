#!/usr/bin/env python3
"""
D4a post-processing: generate metrics JSON + preview images from already-saved D4a file.
"""

import numpy as np
from PIL import Image
import os, json
from datetime import datetime

BASE     = os.path.expanduser("~/Projects/RodiO/pwa/assets/source/bmng_staging")
D3_PATH  = os.path.join(BASE, "bmng_processed_8192x4096_natural_d3.jpg")
D4A_PATH = os.path.join(BASE, "bmng_processed_8192x4096_natural_d4a_nearshore.jpg")
PREV_DIR = os.path.join(BASE, "d4a_previews")
os.makedirs(PREV_DIR, exist_ok=True)

print(f"[{datetime.now().strftime('%H:%M:%S')}] Loading D3 + D4a...")
d3_img  = Image.open(D3_PATH).convert("RGB")
d4a_img = Image.open(D4A_PATH).convert("RGB")
W, H = d3_img.size
print(f"  {W}x{H}")

d3  = np.array(d3_img,  dtype=np.float32)
d4a = np.array(d4a_img, dtype=np.float32)

# ── Rebuild ocean mask (same as main script) ─────────────────────────────────
def rgb_to_hsv(rgb):
    r, g, b = rgb[...,0]/255.0, rgb[...,1]/255.0, rgb[...,2]/255.0
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    delta = mx - mn
    s = np.where(mx > 0, delta / mx, 0.0)
    v = mx
    return s, v

R, G, B    = d3[...,0], d3[...,1], d3[...,2]
S_ch, V_ch = rgb_to_hsv(d3)

snow_mask   = (R > 210) & (G > 210) & (B > 210) & (S_ch < 0.12)
veg_mask    = (G > R + 5) & (G > B + 3) & (V_ch < 0.72) & (~snow_mask)
desert_mask = (R > G + 10) & (R > B + 10) & (V_ch > 0.45) & (~snow_mask)

ocean_mask = (
    (B > 40) &
    ((B.astype(np.int16) - R) > 8) &
    (V_ch < 0.78) &
    (~snow_mask) & (~veg_mask) & (~desert_mask)
)

# ── Helper ────────────────────────────────────────────────────────────────────
def lonlat_to_rc(lon, lat):
    col = int((lon + 180) / 360 * W)
    row = int((90 - lat) / 180 * H)
    return max(0, min(H-1, row)), max(0, min(W-1, col))

def zone_bbox(lon_w, lon_e, lat_s, lat_n):
    r1, c1 = lonlat_to_rc(lon_w, lat_n)
    r2, c2 = lonlat_to_rc(lon_e, lat_s)
    return max(0,r1), min(H,r2), max(0,c1), min(W,c2)

def zone_stats(arr, mask):
    mr = arr[...,0][mask]
    mg = arr[...,1][mask]
    mb = arr[...,2][mask]
    if len(mr) < 100:
        return None
    Rm, Gm, Bm = float(mr.mean()), float(mg.mean()), float(mb.mean())
    Bstd = float(mb.std())
    BG   = Bm / (Gm + 1e-6)
    mx = np.maximum(np.maximum(mr, mg), mb)
    mn = np.minimum(np.minimum(mr, mg), mb)
    per_sat = np.where(mx > 0, (mx - mn) / mx, 0.0)
    sat = float(per_sat.mean())
    V   = float((mx / 255.0).mean())
    hi_sat_pct = float((per_sat > 0.35).mean() * 100)
    return dict(R=round(Rm,1), G=round(Gm,1), B=round(Bm,1),
                BG=round(BG,3), B_std=round(Bstd,2),
                sat=round(sat,4), V=round(V,4), hi_sat_pct=round(hi_sat_pct,2))

zones = [
    ("Yellow Sea",        119, 127, 31, 38),
    ("East China Sea",    119, 128, 24, 32),
    ("Taiwan Strait",     117, 123, 22, 26),
    ("South China Sea N", 108, 122, 16, 24),
    ("South China Sea C", 109, 120,  7, 16),
    ("Philippines",       116, 128,  5, 18),
    ("Indonesia",         105, 140, -8,  5),
    ("Caribbean",         -85, -60, 10, 24),
    ("Bahamas",           -80, -72, 22, 28),
    ("Gulf of Mexico",    -97, -80, 18, 30),
    ("Australia North",   127, 140,-20,-10),
    ("Great Barrier Reef",145, 154,-24,-15),
    ("Persian Gulf",       48,  57, 23, 30),
    ("Red Sea",            32,  44, 12, 28),
    ("North Sea",          -4,  10, 51, 60),
    ("Mediterranean",       0,  36, 30, 46),
    ("Bering Sea",        165, 200, 53, 65),
    ("Sea of Okhotsk",    140, 162, 47, 60),
    ("Southern Ocean",   -180, 180,-60,-50),
    ("Arctic fringe",    -180, 180, 70, 80),
]

print(f"\n{'Zone':<25} {'R':>5} {'G':>5} {'B':>5} {'B/G':>5} {'B_std':>6} {'Sat':>5} {'V':>5} {'HiSat%':>7} | dB_std")
print("-" * 95)

metrics = {}
for (name, lon_w, lon_e, lat_s, lat_n) in zones:
    r1, r2, c1, c2 = zone_bbox(lon_w, lon_e, lat_s, lat_n)
    full_lat = (lon_w == -180 and lon_e == 180)
    if full_lat:
        pd3  = d3[r1:r2, :, :]
        pd4a = d4a[r1:r2, :, :]
        om   = ocean_mask[r1:r2, :]
    else:
        pd3  = d3[r1:r2, c1:c2, :]
        pd4a = d4a[r1:r2, c1:c2, :]
        om   = ocean_mask[r1:r2, c1:c2]

    s3  = zone_stats(pd3,  om)
    s4a = zone_stats(pd4a, om)
    if s3 is None or s4a is None:
        continue

    dBstd     = round(s4a["B_std"] - s3["B_std"], 3)
    dBstd_pct = round(dBstd / (s3["B_std"] + 1e-6) * 100, 1)
    metrics[name] = {"d3": s3, "d4a": s4a,
                     "delta_Bstd": dBstd, "delta_Bstd_pct": dBstd_pct}

    print(f"{name:<25} {s4a['R']:>5.1f} {s4a['G']:>5.1f} {s4a['B']:>5.1f} "
          f"{s4a['BG']:>5.3f} {s4a['B_std']:>6.2f} {s4a['sat']:>5.3f} "
          f"{s4a['V']:>5.3f} {s4a['hi_sat_pct']:>7.2f}% | {dBstd:+.3f} ({dBstd_pct:+.1f}%)")

report_path = os.path.join(PREV_DIR, "d4a_metrics.json")
with open(report_path, "w") as f:
    json.dump(metrics, f, indent=2, ensure_ascii=False)
print(f"\nMetrics saved: {report_path}")

# ── Preview images ────────────────────────────────────────────────────────────
print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Generating previews...")
PREV_W, PREV_H = 2048, 1024

d3_sm  = d3_img.resize((PREV_W, PREV_H), Image.LANCZOS)
d4a_sm = d4a_img.resize((PREV_W, PREV_H), Image.LANCZOS)

comp = Image.new("RGB", (PREV_W*2, PREV_H))
comp.paste(d3_sm,  (0, 0))
comp.paste(d4a_sm, (PREV_W, 0))
comp.save(os.path.join(PREV_DIR, "global_compare_d3_vs_d4a.jpg"), quality=88)
print("  global_compare_d3_vs_d4a.jpg")

crops = [
    ("yellow_east_china_sea",  119, 128, 22, 40),
    ("taiwan_strait",          115, 125, 20, 28),
    ("south_china_sea",        105, 125,  5, 25),
    ("philippines",            115, 132,  4, 20),
    ("indonesia",              100, 145,-12,  8),
    ("caribbean_bahamas",      -88, -60, 10, 28),
    ("australia_gbr",          120, 158,-26, -8),
    ("persian_gulf_red_sea",    30,  60, 10, 32),
    ("north_sea",               -8,  12, 49, 62),
    ("bering_sea",             160, 200, 50, 67),
    ("southern_ocean",         -60,  60,-65,-45),
]

for (tag, lon_w, lon_e, lat_s, lat_n) in crops:
    r1, r2, c1, c2 = zone_bbox(lon_w, lon_e, lat_s, lat_n)
    if r2 <= r1 or c2 <= c1:
        continue
    cd3  = d3_img.crop((c1, r1, c2, r2))
    cd4a = d4a_img.crop((c1, r1, c2, r2))
    cw, ch = c2-c1, r2-r1
    side = Image.new("RGB", (cw*2, ch))
    side.paste(cd3,  (0,  0))
    side.paste(cd4a, (cw, 0))
    side.save(os.path.join(PREV_DIR, f"crop_{tag}.jpg"), quality=90)
    print(f"  crop_{tag}.jpg  ({cw}x{ch}px each)")

print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Done.")
print(f"Previews: {PREV_DIR}/")
