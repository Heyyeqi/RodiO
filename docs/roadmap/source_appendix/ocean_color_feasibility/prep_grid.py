#!/usr/bin/env python3
"""
prep_grid.py — extract per-pixel water-quality inputs from a real ocean-color
NetCDF and dump a downsampled grid for the per-pixel pipeline proof.

Input provenance (every field is either from the real product or a clearly
labelled empirical link from real Rrs/CHL):
  - CHL   : real `chl_ocx` if present & valid, else OC3 band-ratio from real Rrs
  - KD490 : Morel & Maritorena (2001) empirical Kd490 = 0.016 + 0.023*CHL^0.54
  - SPM   : empirical turbidity proxy from REAL Rrs ratio (Rrs547/Rrs443)
  - CDOM  : estimated from CHL/SPM (matches water_params_reference.js fallback)

Output: grid_inputs.json  {W,H, lat0,lat1,lon0,lon1, valid[], chl[],spm[],kd490[]}
"""
import sys, json, math
import netCDF4
import numpy as np

SRC = sys.argv[1] if len(sys.argv) > 1 else "sample_modis_real.nc"
OUT = sys.argv[2] if len(sys.argv) > 2 else "grid_inputs.json"
TARGET_W = int(sys.argv[3]) if len(sys.argv) > 3 else 360

ds = netCDF4.Dataset(SRC)
# find lat/lon
lat = np.array(ds.variables['latitude'][:]).astype(float)
lon = np.array(ds.variables['longitude'][:]).astype(float)
H, W = lat.shape
lat0, lat1 = float(lat.min()), float(lat.max())
lon0, lon1 = float(lon.min()), float(lon.max())

# --- CHL (real product field preferred) ---
def load(name):
    v = ds.variables[name]
    a = np.array(v[:]).astype(float)
    # HDF fill sentinels vary by product: chl_ocx -> 9.993e+06, Rrs_* -> 9.993e+10.
    # Real CHL never exceeds ~100 mg/m3 and real Rrs < 0.1, so any value > 1e4 is fill.
    a[a > 1e4] = np.nan
    return a

chl = None
if 'chl_ocx' in ds.variables:
    c = load('chl_ocx')
    if np.isfinite(c).sum() > 100:
        chl = c
        chl_src = "chl_ocx (real product)"
if chl is None:
    # OC3 band-ratio from real Rrs (MODIS-appropriate coefficients)
    r443 = load('Rrs_443'); r488 = load('Rrs_488'); r531 = load('Rrs_531'); r547 = load('Rrs_547')
    rmax = np.maximum(np.maximum(r443, r488), r531)
    with np.errstate(divide='ignore'):
        X = np.log10(np.where((rmax > 0) & (r547 > 0), rmax / r547, np.nan))
    chl = np.full_like(rmax, np.nan)
    ok = np.isfinite(X)
    a0, a1, a2, a3, a4 = 0.26203, -2.19718, 1.14715, 0.44279, -0.20246
    chl[ok] = 10 ** (a0 + a1*X[ok] + a2*X[ok]**2 + a3*X[ok]**3 + a4*X[ok]**4)
    chl_src = "OC3 from real Rrs_443/488/531/547"

# --- KD490 empirical from CHL ---
kd490 = 0.016 + 0.023 * np.power(np.where(chl > 0, chl, np.nan), 0.54)
kd_src = "Morel & Maritorena (2001) Kd490 = 0.016 + 0.023*CHL^0.54"

# --- SPM empirical turbidity proxy from REAL Rrs ratio ---
r547 = load('Rrs_547'); r443 = load('Rrs_443')
with np.errstate(divide='ignore'):
    TI = np.log10(np.where((r547 > 0) & (r443 > 0), r547 / r443, np.nan))  # >0 turbid
spm = np.where(np.isfinite(TI), 10 ** (1.1 * TI + 0.2), np.nan)
spm_src = "empirical SPM ~ 10^(1.1*log10(Rrs547/Rrs443)+0.2) from real Rrs"

ds.close()

# --- downsample to target width (nearest, keep valid coverage) ---
step = max(1, W // TARGET_W)
cols = list(range(0, W, step))[:TARGET_W]
ow = len(cols)
oh = H // step
chl_d = chl[::step, cols]
kd_d = kd490[::step, cols]
spm_d = spm[::step, cols]
valid = np.isfinite(chl_d) & np.isfinite(kd_d)
n_valid = int(valid.sum())

out = {
    "source": SRC,
    "W": ow, "H": oh,
    "lat0": lat0, "lat1": lat1, "lon0": lon0, "lon1": lon1,
    "provenance": {"chl": chl_src, "kd490": kd_src, "spm": spm_src,
                   "cdm": "estimated from CHL/SPM inside water_params_reference.js"},
    "n_valid": n_valid,
    "chl": [[None if not valid[i, j] else round(float(chl_d[i, j]), 4)
             for j in range(ow)] for i in range(oh)],
    "spm": [[None if not (valid[i, j] and np.isfinite(spm_d[i, j])) else round(float(spm_d[i, j]), 4)
             for j in range(ow)] for i in range(oh)],
    "kd490": [[None if not valid[i, j] else round(float(kd_d[i, j]), 4)
               for j in range(ow)] for i in range(oh)],
}
json.dump(out, open(OUT, "w"))
print(f"wrote {OUT}: grid {ow}x{oh}, valid pixels={n_valid}/{ow*oh}")
print(f"  CHL src : {chl_src}")
print(f"  KD490   : {kd_src}")
print(f"  SPM src : {spm_src}")
print(f"  CHL  range: {np.nanmin(chl_d):.4g} .. {np.nanmax(chl_d):.4g} mg/m3")
print(f"  KD490 range: {np.nanmin(kd_d):.4g} .. {np.nanmax(kd_d):.4g} 1/m")
