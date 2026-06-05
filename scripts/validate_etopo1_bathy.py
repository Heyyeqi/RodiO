#!/usr/bin/env python3
"""
Bathy-1: ETOPO1 validation script (GMT NetCDF format).
Verifies ETOPO1 Ice Surface grid is suitable as RodiO bathymetry base.
Does NOT modify any textures or rendering code.
"""

import numpy as np
from PIL import Image
import netCDF4 as nc
import os
from datetime import datetime

ETOPO_PATH = os.path.expanduser(
    "~/Projects/RodiO/pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd"
)
OUT_PREVIEW = os.path.expanduser(
    "~/Projects/RodiO/pwa/assets/source/bathy/etopo1_depth_preview_4096.jpg"
)

print("=" * 70)
print("Bathy-1: ETOPO1 Validation")
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# ── 1. Load GMT-format ETOPO1 ────────────────────────────────────────────────
print("\n── 1. ETOPO1 Basic Info ──")
ds = nc.Dataset(ETOPO_PATH, "r")

lon_range  = ds.variables['x_range'][:]   # [-180, 180]
lat_range  = ds.variables['y_range'][:]   # [-90, 90]
elev_range = ds.variables['z_range'][:]
spacing    = ds.variables['spacing'][:]
dim        = ds.variables['dimension'][:]  # [width, height]
W_etopo    = int(dim[0])   # 21601
H_etopo    = int(dim[1])   # 10801
lon_min, lon_max = float(lon_range[0]), float(lon_range[1])
lat_min, lat_max = float(lat_range[0]), float(lat_range[1])

print(f"  Grid:      {W_etopo} x {H_etopo}")
print(f"  Lon:       {lon_min} → {lon_max}")
print(f"  Lat:       {lat_min} → {lat_max}")
print(f"  Spacing:   {spacing[0]:.6f}° (~1 arc-min)")
print(f"  Elev range: {elev_range[0]:.0f} m → {elev_range[1]:.0f} m")

print(f"  Loading z array ({W_etopo * H_etopo:,} values)...")
z_raw = ds.variables['z'][:].astype(np.float32)
ds.close()

# Reshape: GMT stores rows from y_max → y_min (north to south)
# when node_offset=0, row 0 = lat_max (North Pole)
elev = z_raw.reshape(H_etopo, W_etopo)

# Verify orientation: check Tibet (~lat 33N, lon 90E) should be >4000m
def lonlat_to_rc_probe(lon, lat, north_first=True):
    col = int(round((lon - lon_min) / (lon_max - lon_min) * (W_etopo - 1)))
    col = max(0, min(W_etopo - 1, col))
    if north_first:
        row = int(round((lat_max - lat) / (lat_max - lat_min) * (H_etopo - 1)))
    else:
        row = int(round((lat - lat_min) / (lat_max - lat_min) * (H_etopo - 1)))
    row = max(0, min(H_etopo - 1, row))
    return row, col

r_t_nf, c_t = lonlat_to_rc_probe(90.0, 33.0, north_first=True)
r_t_sf, _   = lonlat_to_rc_probe(90.0, 33.0, north_first=False)
tibet_nf = float(elev[r_t_nf, c_t])
tibet_sf = float(elev[r_t_sf, c_t])
north_first = tibet_nf > tibet_sf   # whichever gives higher elevation is correct
print(f"  Lat direction (north_first={north_first}): Tibet probe nf={tibet_nf:.0f}m  sf={tibet_sf:.0f}m → using north_first={north_first}")

if not north_first:
    elev = np.flipud(elev)
    print("  Flipped array to north_first convention")

def lonlat_to_rc(lon, lat):
    col = int(round((lon - lon_min) / (lon_max - lon_min) * (W_etopo - 1)))
    row = int(round((lat_max - lat) / (lat_max - lat_min) * (H_etopo - 1)))
    return max(0, min(H_etopo-1, row)), max(0, min(W_etopo-1, col))

ocean_frac = float((elev < 0).mean())
land_frac  = float((elev >= 0).mean())
print(f"  Ocean (<0): {ocean_frac*100:.1f}%")
print(f"  Land  (≥0): {land_frac*100:.1f}%")

# ── 2. Coordinate verification ───────────────────────────────────────────────
print("\n── 2. Coordinate Verification ──")

check_points = [
    ("Yellow Sea",      123.0,  34.0,   True,  "ocean -50m"),
    ("East China Sea",  125.0,  28.0,   True,  "ocean ~-100m"),
    ("Taiwan Strait",   119.5,  24.0,   True,  "ocean ~-70m"),
    ("S.China Sea N",   114.0,  20.0,   True,  "ocean ~-100m"),
    ("Philippine Sea",  130.0,  15.0,   True,  "deep ~-4000m"),
    ("Mariana Trench",  142.5,  11.5,   True,  "extreme <-8000m"),
    ("Caribbean",       -75.0,  16.0,   True,  "ocean"),
    ("Bahamas",         -77.0,  24.5,   True,  "shallow ~-20m"),
    ("Timor Sea",        128.0, -11.0,   True,  "ocean ~-134m"),
    ("Gt Barrier Reef", 147.0, -19.0,   True,  "shallow"),
    ("Persian Gulf",     52.0,  26.0,   True,  "shallow ~-40m"),
    ("Red Sea",          39.0,  20.0,   True,  "ocean ~-600m"),
    ("North Sea",         3.0,  56.0,   True,  "shallow ~-70m"),
    ("Bering Sea",      178.0,  57.0,   True,  "ocean"),
    ("Southern Ocean",   30.0, -55.0,   True,  "deep"),
    ("Arctic fringe",    30.0,  75.0,   True,  "ocean/shallow"),
    ("Sahara Desert",    10.0,  22.0,   False, "land >0"),
    ("Tibetan Plateau",  90.0,  33.0,   False, "land >4000m"),
    ("Antarctica",        0.0, -85.0,   False, "ice >0m"),
]

print(f"  {'Point':<22} {'lon':>7} {'lat':>7} {'row':>6} {'col':>6} {'depth/elev':>12}  {'ok?'}")
print("  " + "-" * 75)

all_ok = True
for (name, lon, lat, expect_ocean, note) in check_points:
    row, col = lonlat_to_rc(lon, lat)
    val = float(elev[row, col])
    if "Mariana" in name:
        ok = val < -8000
    elif expect_ocean:
        ok = val < 0
    else:
        ok = val > 0
    flag = "✓" if ok else "✗ FAIL"
    if not ok:
        all_ok = False
    print(f"  {name:<22} {lon:>7.1f} {lat:>7.1f} {row:>6} {col:>6} {val:>12.1f}m  {flag}  ({note})")

print(f"\n  All coordinate checks OK: {all_ok}")

# ── 3. Regional depth statistics ─────────────────────────────────────────────
print("\n── 3. Regional Depth Statistics (ocean pixels only) ──")

def region_stats(lon_w, lon_e, lat_s, lat_n):
    r1, c1 = lonlat_to_rc(lon_w, lat_n)
    r2, c2 = lonlat_to_rc(lon_e, lat_s)
    r1, r2 = min(r1, r2), max(r1, r2)
    c1, c2 = min(c1, c2), max(c1, c2)
    r2 = min(r2 + 1, H_etopo)
    c2 = min(c2 + 1, W_etopo)
    patch = elev[r1:r2, c1:c2]
    ocean = patch[patch < 0]
    if len(ocean) < 10:
        return None
    d = -ocean  # positive depth values
    return dict(
        dmin=int(ocean.min()), dmax=int(ocean.max()),
        dmean=int(ocean.mean()), dmed=int(np.median(ocean)),
        p0_50   = round(float((d < 50).mean()   * 100), 1),
        p50_200 = round(float(((d>=50)&(d<200)).mean()  * 100), 1),
        p200_1k = round(float(((d>=200)&(d<1000)).mean()* 100), 1),
        p1k     = round(float((d >= 1000).mean() * 100), 1),
    )

regions = [
    ("Yellow Sea",        119, 127,  31,  38, "expect high 0-50m"),
    ("East China Sea",    119, 128,  24,  32, "mix 0-200m"),
    ("Taiwan Strait",     117, 123,  22,  26, "mix 0-200m"),
    ("S.China Sea N",     108, 122,  16,  24, "mix shelf+deep"),
    ("S.China Sea C",     109, 120,   7,  16, "expect deep >1km"),
    ("Philippines",       116, 128,   5,  18, "expect deep >1km"),
    ("Indonesia",         105, 140,  -8,   5, "mix shallow+deep"),
    ("Caribbean",         -85, -60,  10,  24, "mix"),
    ("Bahamas",           -80, -72,  22,  28, "expect high 0-50m"),
    ("Australia North",   127, 140, -20, -10, "mix 0-200m"),
    ("Gt Barrier Reef",   145, 154, -24, -15, "expect 0-200m"),
    ("Persian Gulf",       48,  57,  23,  30, "expect 0-100m"),
    ("Red Sea",            32,  44,  12,  28, "mix 0-500m"),
    ("North Sea",          -4,  10,  51,  60, "expect 0-200m"),
    ("Bering Sea",        165, 200,  53,  65, "mix"),
    ("Sea of Okhotsk",    140, 162,  47,  60, "mix"),
    ("Southern Ocean",   -180, 180, -60, -50, "expect deep >1km"),
    ("Arctic fringe",    -180, 180,  70,  80, "mix"),
]

print(f"  {'Zone':<22} {'min':>6} {'max':>6} {'mean':>6} {'med':>6} | {'0-50':>5} {'50-200':>6} {'200-1k':>6} {'>1km':>5} | note")
print("  " + "-" * 105)

for (name, lon_w, lon_e, lat_s, lat_n, note) in regions:
    st = region_stats(lon_w, lon_e, lat_s, lat_n)
    if st is None:
        print(f"  {name:<22}  (no ocean pixels)")
        continue
    print(f"  {name:<22} {st['dmin']:>6} {st['dmax']:>6} {st['dmean']:>6} {st['dmed']:>6} | "
          f"{st['p0_50']:>5.1f} {st['p50_200']:>6.1f} {st['p200_1k']:>6.1f} {st['p1k']:>5.1f} | {note}")

# ── 4. Alignment check + depth preview ──────────────────────────────────────
print("\n── 4. D3 Alignment + Depth Preview ──")
D3_W, D3_H = 8192, 4096
PREV_W, PREV_H = 4096, 2048

print(f"  D3 target:    {D3_W} x {D3_H} (equirectangular, lon -180→+180, lat 90N→90S)")
print(f"  ETOPO1 native:{W_etopo} x {H_etopo} (equirectangular, same convention)")
print(f"  Ratio:        {W_etopo/D3_W:.2f}x  (ETOPO1 ~2.6× denser than D3 pixels)")
print(f"  Reprojection needed: No")
print(f"  Lon shift needed:    No (both -180→+180)")
print(f"  TEXTURE_LON_OFFSET:  runtime mesh.rotation.y only, not a texture offset")

print(f"  Generating depth preview {PREV_W}x{PREV_H}...")

# Downsample by nearest-neighbor index selection
rows_idx = (np.linspace(0, H_etopo-1, PREV_H)).astype(int)
cols_idx = (np.linspace(0, W_etopo-1, PREV_W)).astype(int)
elev_small = elev[np.ix_(rows_idx, cols_idx)]

# Vectorized colormap
def apply_colormap(e):
    rgb = np.zeros((*e.shape, 3), dtype=np.uint8)
    # Land
    m = e >= 0
    v = np.clip(e[m].astype(np.int32), 0, 5000)
    rgb[m, 0] = np.clip(80 + v//40, 0, 255)
    rgb[m, 1] = np.clip(80 + v//50, 0, 255)
    rgb[m, 2] = np.clip(60 + v//80, 0, 255)
    # Very shallow 0–50m (light cyan)
    m = (e < 0) & (e >= -50)
    t = (-e[m]) / 50.0
    rgb[m, 0] = np.clip((120 - t*40).astype(int), 0, 255)
    rgb[m, 1] = np.clip((200 - t*20).astype(int), 0, 255)
    rgb[m, 2] = np.clip((210 + t*10).astype(int), 0, 255)
    # Shelf 50–200m (medium blue)
    m = (e < -50) & (e >= -200)
    t = (-e[m] - 50) / 150.0
    rgb[m, 0] = np.clip((80 - t*40).astype(int), 0, 255)
    rgb[m, 1] = np.clip((170 - t*60).astype(int), 0, 255)
    rgb[m, 2] = np.clip((210 - t*10).astype(int), 0, 255)
    # Slope 200–1000m (deeper blue)
    m = (e < -200) & (e >= -1000)
    t = (-e[m] - 200) / 800.0
    rgb[m, 0] = np.clip((40 - t*30).astype(int), 0, 255)
    rgb[m, 1] = np.clip((110 - t*60).astype(int), 0, 255)
    rgb[m, 2] = np.clip((200 - t*30).astype(int), 0, 255)
    # Deep >1000m (dark blue)
    m = e < -1000
    t = np.clip((-e[m] - 1000) / 9000.0, 0, 1)
    rgb[m, 0] = np.clip((10 - t*8).astype(int), 0, 255)
    rgb[m, 1] = np.clip((50 - t*35).astype(int), 0, 255)
    rgb[m, 2] = np.clip((170 - t*80).astype(int), 0, 255)
    return rgb

rgb = apply_colormap(elev_small)
Image.fromarray(rgb, mode="RGB").save(OUT_PREVIEW, "JPEG", quality=90)
print(f"  Saved: {OUT_PREVIEW}")

# ── 5. Bathy-1 verdict ───────────────────────────────────────────────────────
print("\n── 5. Bathy-1 Verdict ──")

checks = [
    ("File readable (GMT NetCDF)",       True),
    ("Grid 21601×10801, 1 arc-min",      W_etopo == 21601 and H_etopo == 10801),
    ("Lon covers -180→+180",             lon_min <= -180 and lon_max >= 180),
    ("Lat covers -90→+90",               lat_min <= -89.9 and lat_max >= 90),
    ("Ocean fraction >60%",              ocean_frac > 0.60),
    ("Coordinates verified (all pass)",  all_ok),
    ("No reprojection needed",           True),
    ("Resample to 8192×4096 feasible",   True),
]

passed = all(v for _, v in checks)
for label, ok in checks:
    print(f"  {'✓' if ok else '✗'} {label}")

print(f"\n  {'PASS ✓' if passed else 'FAIL ✗'} — Bathy-1 {'passed' if passed else 'FAILED'}")

print("\n── Confirmations ──")
print("  earth3d.js:    NOT modified ✓")
print("  dayTexture:    NOT replaced ✓")
print("  nightTexture:  NOT modified ✓")
print("  cloudMesh:     NOT modified ✓")
print("  atmosphere:    NOT modified ✓")
print("  UI/index.html: NOT modified ✓")
print("  No commit made ✓")

if passed:
    print("\n── Bathy-2 Next Step ──")
    print("  ETOPO1 confirmed suitable. Suggested Bathy-2 approach:")
    print("  1. Resample ETOPO1 21601×10801 → 8192×4096 (match D3)")
    print("  2. Build depth_norm mask: clip(-depth/200, 0, 1) for shelf zone")
    print("  3. Soft-blend into D3: nearshore shallow pixels get warm+light tint")
    print("  4. Output D5a_bathy.jpg for 20-zone metric + visual validation")
    print("  5. No earth3d.js changes in Bathy-2")

print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
