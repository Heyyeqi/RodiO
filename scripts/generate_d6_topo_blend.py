#!/usr/bin/env python3
"""
Bathy-3 / A-3: Generate D6 topo-blend candidate texture.

Strategy:
  Base:    D5a (already has ETOPO1 bathy layer, best existing candidate)
  Signal:  bmng_topo_bathy 8k — extract ocean luminance as depth proxy
           High luminance = shallow (coastal, shelf) → high blend weight
           Low luminance  = deep → low/zero weight
  Mask:    ETOPO1 ocean/land + deep-sea protection (>1000m weight=0)
  Target:  topo image's own RGB (pre-calibrated NASA color at each depth)

Does NOT modify earth3d.js default or any rendering code.
Does copy to candidates/ and registers the variant in earth3d.js comment block.
"""

import numpy as np
from PIL import Image
import netCDF4 as nc
from scipy.ndimage import gaussian_filter
import os, json, shutil
from datetime import datetime

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.bool_):    return bool(obj)
        return super().default(obj)

BASE     = os.path.expanduser("~/Projects/RodiO/pwa/assets/source")
D5A_PATH = f"{BASE}/bmng_staging/bmng_processed_8192x4096_natural_d5a_bathy.jpg"
TOPO_PATH= f"{BASE}/bmng_staging/bmng_topo_bathy_oct_8192x4096.jpg"
ETOPO    = f"{BASE}/bathy/ETOPO1_Ice_g_gdal.grd"

OUT_STAGING = f"{BASE}/bmng_staging/bmng_processed_8192x4096_natural_d6_topo_blend.jpg"
CAND_DIR    = os.path.expanduser("~/Projects/RodiO/pwa/assets/earth/candidates")
CAND_OUT    = f"{CAND_DIR}/d6_topo_blend_8192x4096.jpg"
METRICS_OUT = f"{BASE}/bathy/d6_topo_blend_metrics.json"
PREV_GLOBAL = f"{BASE}/bathy/d6_topo_blend_preview_global.jpg"
PREV_REGION = f"{BASE}/bathy/d6_topo_blend_preview_regions.jpg"

W, H = 8192, 4096
T0 = datetime.now()
def ts(): return datetime.now().strftime('%H:%M:%S')

print("=" * 68)
print("D6 topo-blend candidate  (Bathy-3 / A-3)")
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 68)

# ── Phase 1: Load D5a + topo ──────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 1: Loading D5a and topo 8k...")
d5a_img  = Image.open(D5A_PATH).convert("RGB")
topo_img = Image.open(TOPO_PATH).convert("RGB")

assert d5a_img.size == (W, H), f"D5a size mismatch: {d5a_img.size}"
if topo_img.size != (W, H):
    print(f"  Resizing topo from {topo_img.size} → {W}x{H} (LANCZOS)...")
    topo_img = topo_img.resize((W, H), Image.LANCZOS)

d5a  = np.array(d5a_img,  dtype=np.float32)
topo = np.array(topo_img, dtype=np.float32)
print(f"  D5a:  {d5a_img.size}  topo: {topo_img.size}")

# ── Phase 2: Load ETOPO1 (deep-sea mask only) ─────────────────────────────────
print(f"\n[{ts()}] Phase 2: Loading ETOPO1 for deep-sea mask (~20s)...")
ds    = nc.Dataset(ETOPO, "r")
dim   = ds.variables['dimension'][:]
We, He = int(dim[0]), int(dim[1])
z_raw  = ds.variables['z'][:].astype(np.float32).reshape(He, We)
ds.close()
print(f"  ETOPO1: {We}x{He}  range [{z_raw.min():.0f}, {z_raw.max():.0f}]m")

print(f"[{ts()}] Phase 2b: Downsampling ETOPO1 → {W}x{H}...")
ri    = np.round(np.linspace(0, He-1, H)).astype(int)
ci    = np.round(np.linspace(0, We-1, W)).astype(int)
depth = z_raw[np.ix_(ri, ci)]   # negative=ocean, positive=land/ice
del z_raw

# ── Phase 3: Masks ────────────────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 3: Building masks...")
ocean_hard = depth < 0
land_hard  = depth >= 0

# Soft coastal fade (taper blend weight near land)
ocean_fade = gaussian_filter(ocean_hard.astype(np.float32), sigma=3)
ocean_fade = np.clip(ocean_fade / 0.85, 0.0, 1.0)

# Snow/ice: protect near-white D5a pixels (already protected in D5a, but double-check)
R5, G5, B5 = d5a[...,0], d5a[...,1], d5a[...,2]
snow_mask  = (R5 > 210) & (G5 > 210) & (B5 > 210)

print(f"  ocean: {ocean_hard.mean()*100:.1f}%  land/ice: {land_hard.mean()*100:.1f}%"
      f"  snow(D5a): {snow_mask.mean()*100:.1f}%")

# Deep-sea protection: soft ramp from -800m to -1200m (0.0 at -800, 1.0 at -1200+)
deep_prot = np.clip((-depth - 800.0) / 400.0, 0.0, 1.0)   # 1 = fully protected deep
# Extra: hard zero below -4000m (abyss, no change whatsoever)
deep_prot = np.where(depth < -4000, 1.0, deep_prot)

# ── Phase 4: Topo luminance → blend weight ────────────────────────────────────
print(f"\n[{ts()}] Phase 4: Computing topo luminance depth proxy...")

topo_lum = (0.299 * topo[...,0] + 0.587 * topo[...,1] + 0.114 * topo[...,2])
topo_lum_n = topo_lum / 255.0   # 0–1

# Ocean-only luminance stats (diagnostic)
if ocean_hard.sum() > 0:
    oc_lum = topo_lum_n[ocean_hard]
    print(f"  topo ocean lum: p5={np.percentile(oc_lum,5):.3f}  "
          f"p25={np.percentile(oc_lum,25):.3f}  "
          f"p50={np.percentile(oc_lum,50):.3f}  "
          f"p75={np.percentile(oc_lum,75):.3f}  "
          f"p95={np.percentile(oc_lum,95):.3f}")

# Weight curve: high topo luminance = shallow = high weight
# Breakpoints chosen so that:
#   very dark (<lum 0.08) → weight 0.0  (abyssal, won't appear due to deep_prot anyway)
#   dark shelf (0.08-0.25) → 0.0–0.04  (deep shelf, minimal touch)
#   mid shelf (0.25-0.50) → 0.04–0.16  (200-500m shelf)
#   shallow (0.50-0.72) → 0.16–0.28    (0-200m coastal shelf)
#   very shallow (0.72-1.0) → 0.28–0.30 (intertidal, bay, estuary)
bp_l = [0.00, 0.08, 0.25, 0.50, 0.72, 1.00]
bp_w = [0.00, 0.00, 0.04, 0.16, 0.28, 0.30]
weight = np.interp(topo_lum_n, bp_l, bp_w).astype(np.float32)

# Apply deep-sea protection (shallow ramp 800-1200m, hard 0 at deep)
weight *= (1.0 - deep_prot)

# Apply coastal fade (smooth transition at land/sea boundary)
weight *= ocean_fade

# Restrict to ocean only
weight *= ocean_hard.astype(np.float32)

# Smooth the weight field slightly to avoid topo JPEG artefact edges
weight = gaussian_filter(weight, sigma=2)
weight = np.clip(weight, 0.0, 0.30)

print(f"  weight: max={weight.max():.4f}  "
      f"mean(ocean)={weight[ocean_hard].mean():.5f}  "
      f"p90(ocean)={np.percentile(weight[ocean_hard], 90):.4f}")

# ── Phase 5: Blend D5a → topo ─────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 5: Blending D5a → topo (per-pixel)...")
w3     = weight[..., np.newaxis]
result = d5a * (1.0 - w3) + topo * w3

# ── Phase 6: Protections ──────────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 6: Protections (land / snow / anti-荧光)...")

# Hard land restore from D5a (topo has land colors; don't let them bleed into land)
lm = land_hard[..., np.newaxis].astype(np.float32)
result = d5a * lm + result * (1.0 - lm)

# Hard snow/ice restore from D5a
sm = snow_mask[..., np.newaxis].astype(np.float32)
result = d5a * sm + result * (1.0 - sm)

# Anti-荧光: revert pixels where saturation increased >6% AND sat > 0.50
def sat_arr(a):
    mx = np.maximum(np.maximum(a[...,0], a[...,1]), a[...,2])
    mn = np.minimum(np.minimum(a[...,0], a[...,1]), a[...,2])
    return np.where(mx > 0, (mx - mn) / mx, 0.0)

sat5 = sat_arr(d5a)
satr = sat_arr(result)
overshoot = (satr > sat5 * 1.06) & (satr > 0.50) & ocean_hard
om_  = overshoot[..., np.newaxis].astype(np.float32)
result = d5a * om_ + result * (1.0 - om_)
print(f"  anti-荧光 reverted: {overshoot.sum()} px ({overshoot.mean()*100:.2f}%)")

result = result.clip(0, 255).astype(np.uint8)

# ── Phase 7: Save ─────────────────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 7: Saving D6...")
out_img = Image.fromarray(result)
out_img.save(OUT_STAGING, "JPEG", quality=95, subsampling=0)
shutil.copy2(OUT_STAGING, CAND_OUT)
sz = os.path.getsize(OUT_STAGING) // (1024*1024)
print(f"  {OUT_STAGING}  ({sz}MB)")
print(f"  Copied → {CAND_OUT}")

# ── Phase 8: Zone metrics ─────────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 8: Zone metrics (D5a vs D6)...")

res_f = result.astype(np.float32)
d5a_f = d5a

def lum(a): return 0.299*a[...,0] + 0.587*a[...,1] + 0.114*a[...,2]

def lonlat_rc(lon, lat):
    c = int(round((lon + 180) / 360 * (W - 1)))
    r = int(round((90 - lat)  / 180 * (H - 1)))
    return max(0, min(H-1, r)), max(0, min(W-1, c))

def bbox(lw, le, ls, ln):
    r1, c1 = lonlat_rc(lw, ln)
    r2, c2 = lonlat_rc(le, ls)
    return min(r1,r2), max(r1,r2)+1, min(c1,c2), max(c1,c2)+1

zones = [
    # name,                  lon_w, lon_e, lat_s, lat_n
    ("Yellow Sea",           119,   127,    31,    38),
    ("Bohai Sea",            117,   122,    37,    41),
    ("East China Sea",       120,   130,    25,    33),
    ("Taiwan Strait",        117,   122,    22,    26),
    ("S.China Sea N",        110,   121,    15,    23),
    ("Taiwan E deep",        122,   130,    20,    26),
    ("Philippines Luzon",    119,   126,    12,    20),
    ("Persian Gulf",          48,    57,    24,    30),
    ("Red Sea",               32,    44,    12,    30),
    ("North Sea",             -4,     9,    52,    61),
    ("Bahamas",              -80,   -72,    22,    28),
    ("Caribbean",            -85,   -60,    10,    25),
    ("Great Barrier Reef",   142,   154,   -24,   -10),
    ("Australia North",      124,   142,   -18,    -8),
    ("Maldives",              72,    74,    -1,     8),
    ("Indonesia",             95,   130,   -10,     8),
    ("Philippines",          117,   127,     5,    20),
    ("Pacific Deep",        -160,  -130,   -20,    10),
    ("Indian Ocean D",        65,    95,   -30,    -5),
    ("N.Atlantic D",         -50,   -25,    20,    45),
    ("Southern Ocean",      -160,   -80,   -60,   -45),
    ("Mariana",              140,   150,    10,    25),
    ("Antarctica",          -180,   180,   -90,   -70),
    ("Greenland",            -55,   -20,    60,    83),
    ("Arctic",              -180,   180,    80,    90),
    ("Tibetan Plateau",       75,   105,    28,    40),
    ("Sahara",               -15,    35,    15,    35),
    ("Amazon",               -65,   -45,   -10,     5),
]
LAND_ZONES = {"Antarctica", "Greenland", "Arctic", "Tibetan Plateau", "Sahara", "Amazon"}
DEEP_ZONES  = {"Pacific Deep", "Indian Ocean D", "N.Atlantic D", "Southern Ocean",
               "Mariana", "Taiwan E deep"}

metrics = {}
hdr = (f"  {'Zone':<22} {'dep':>6} {'0-20':>5} {'0-50':>5} {'>1k':>4} | "
       f"{'D5a R/G/B':^14} {'D6  R/G/B':^14} | "
       f"{'Δ R/G/B':^12} | {'sat5a':>6} {'satD6':>6} | ok?")
print(hdr)
print("  " + "-"*118)

for (name, lw, le, ls, ln) in zones:
    full = (lw == -180 and le == 180)
    r1,r2,c1,c2 = bbox(lw,le,ls,ln)
    s = (slice(r1,r2), slice(None) if full else slice(c1,c2))

    p5a = d5a_f[s]; pr = res_f[s]; pdep = depth[s]

    if name in LAND_ZONES:
        diff3 = float(np.abs(pr - p5a).max())
        lc = (lum(pr).mean() / (lum(p5a).mean()+1e-6) - 1)*100
        print(f"  {name:<22}  land/ice  max_diff_D5a={diff3:.1f}  lum_Δ={lc:+.2f}%")
        metrics[name] = dict(max_diff_d5a=round(diff3,2), lum_change=round(lc,3))
        continue

    om = pdep < 0
    if om.sum() < 20:
        continue

    doc = pdep[om]; dn = -doc
    dep_m = float(dn.mean())
    p0_20 = float((dn < 20).mean()*100)
    p0_50 = float((dn < 50).mean()*100)
    p1k   = float((dn >= 1000).mean()*100)

    def avg(arr, m):
        return arr[...,0][m].mean(), arr[...,1][m].mean(), arr[...,2][m].mean()

    R5m,G5m,B5m = avg(p5a, om)
    Rrm,Grm,Brm = avg(pr,  om)

    BG5 = B5m/(G5m+1e-6); BG6 = Brm/(Grm+1e-6)
    s5  = float(sat_arr(p5a)[om].mean())
    s6  = float(sat_arr(pr)[om].mean())
    dR  = Rrm-R5m; dG = Grm-G5m; dB = Brm-B5m

    ok = True
    if name in DEEP_ZONES:
        ok = abs(dR)<=0.5 and abs(dG)<=0.5 and abs(dB)<=0.5
    elif s6 > s5 + 0.025:
        ok = False

    metrics[name] = dict(
        depth_mean=round(dep_m,1), pct_0_20=round(p0_20,1),
        pct_0_50=round(p0_50,1), pct_gt1k=round(p1k,1),
        d5a=dict(R=round(R5m,1),G=round(G5m,1),B=round(B5m,1),BG=round(BG5,3),sat=round(s5,4)),
        d6 =dict(R=round(Rrm,1),G=round(Grm,1),B=round(Brm,1),BG=round(BG6,3),sat=round(s6,4)),
        delta=dict(R=round(dR,1),G=round(dG,1),B=round(dB,1),sat=round(s6-s5,4)),
        pass_check=bool(ok),
    )

    flag = "✓" if ok else "✗"
    print(f"  {name:<22} {dep_m:>6.0f} {p0_20:>5.1f} {p0_50:>5.1f} {p1k:>4.0f} | "
          f"{R5m:>4.0f}/{G5m:>4.0f}/{B5m:>4.0f}   "
          f"{Rrm:>4.0f}/{Grm:>4.0f}/{Brm:>4.0f} | "
          f"{dR:>+4.0f}/{dG:>+4.0f}/{dB:>+4.0f}   | "
          f"{s5:>6.3f} {s6:>6.3f} | {flag}")

passing = [k for k,v in metrics.items() if v.get('pass_check') is True]
failing  = [k for k,v in metrics.items() if v.get('pass_check') is False]

# Spot checks: land/snow not modified
check_pts = [
    ("Sahara",          10,  22),
    ("Amazon",         -60,  -5),
    ("Greenland ctr",  -42,  72),
    ("Antarctica",       0, -85),
]
print("\n  ── Land/Snow protection checks ──")
for (pname, lon, lat) in check_pts:
    row, col = lonlat_rc(lon, lat)
    orig = d5a[row, col]
    new  = result[row, col].astype(float)
    diff = abs(new - orig).max()
    print(f"  {pname:<18} D5a={orig.astype(int)}  D6={new.astype(int)}"
          f"  max_diff={diff:.0f}  {'✓' if diff < 2 else '✗ MODIFIED'}")

with open(METRICS_OUT, "w") as f:
    json.dump(metrics, f, indent=2, cls=NpEncoder, ensure_ascii=False)
print(f"\n  Metrics: {METRICS_OUT}")

# ── Phase 9: Previews ─────────────────────────────────────────────────────────
print(f"\n[{ts()}] Phase 9: Generating previews...")

PW, PH = 2048, 1024
d5a_s  = d5a_img.resize((PW, PH), Image.LANCZOS)
d6_s   = out_img.resize((PW, PH), Image.LANCZOS)
glob   = Image.new("RGB", (PW*2, PH))
glob.paste(d5a_s, (0,  0))
glob.paste(d6_s,  (PW, 0))
glob.save(PREV_GLOBAL, "JPEG", quality=88)
print(f"  Global (D5a|D6): {PREV_GLOBAL}")

crop_defs = [
    ("Yellow+ECS",     119, 130,  22,  42),
    ("Taiwan Strait",  115, 125,  20,  28),
    ("South China",    105, 125,   5,  25),
    ("Philippines",    115, 132,   4,  20),
    ("Indonesia",      100, 145, -12,   8),
    ("Carib+Bahamas",  -88, -60,  10,  28),
    ("Aus+GBR",        120, 158, -26,  -8),
    ("Persian+Red",     30,  60,  10,  32),
    ("North Sea",       -8,  12,  49,  62),
    ("Bering Sea",     160, 200,  50,  67),
    ("Maldives",        70,  78,  -4,  10),
]

TARGET_W = 1400
rows = []
for (tag, lw, le, ls, ln) in crop_defs:
    r1, r2, c1, c2 = bbox(lw, le, ls, ln)
    if r2 <= r1 or c2 <= c1:
        continue
    cd5a = d5a_img.crop((c1, r1, c2, r2))
    cd6  = out_img.crop((c1, r1, c2, r2))
    cw, ch = c2-c1, r2-r1
    pair = Image.new("RGB", (cw*2, ch))
    pair.paste(cd5a, (0,  0))
    pair.paste(cd6,  (cw, 0))
    scale  = TARGET_W / max(cw*2, 1)
    pair_s = pair.resize((TARGET_W, max(1, int(ch * scale))), Image.LANCZOS)
    rows.append(pair_s)

total_h = sum(img.height + 1 for img in rows)
comp = Image.new("RGB", (TARGET_W, total_h), (20, 20, 20))
y = 0
for img in rows:
    comp.paste(img, (0, y))
    y += img.height + 1
comp.save(PREV_REGION, "JPEG", quality=88)
print(f"  Regions (D5a|D6): {PREV_REGION}  ({len(rows)} crops)")

# ── Phase 10: Summary ─────────────────────────────────────────────────────────
elapsed = (datetime.now() - T0).total_seconds()
all_pass = not failing

print(f"\n{'='*68}")
print("D6 topo-blend generation completed.")
print(f"{'='*68}")
print(f"\nChanged files:")
print(f"  {OUT_STAGING}")
print(f"  {CAND_OUT}")
print(f"  {METRICS_OUT}")
print(f"  {PREV_GLOBAL}")
print(f"  {PREV_REGION}")
print(f"\nNot changed:")
print(f"  pwa/earth3d.js  (earth3d.js NOT modified — register manually or run register step)")
print(f"  dayTexture default (bmng_d2 unchanged)")
print(f"  nightTexture / cloudMesh / atmosphere / UI / SW")
print(f"\nZone results: {len(passing)} pass / {len(failing)} fail")
if failing:
    print(f"  Failing: {', '.join(failing)}")
print(f"\nElapsed: {elapsed:.0f}s")
print(f"\nBrowser test:")
print(f"  http://localhost:8080/?dayTexture=d6_topo_blend")
print(f"  (after registering d6_topo_blend in earth3d.js candidates)")
print(f"\nOverall: {'PASS ✓' if all_pass else 'PARTIAL — review failing zones'}")
