#!/usr/bin/env python3
"""
prep_copernicus.py — read the 3 real Copernicus GlobColour BGC-L4 monthly parts
(CHL / SPM+KD490 / CDM), mask fill + out-of-physical-range, resample to an
equirectangular target grid, and dump a compact binary interchange for the
per-pixel deriveWaterParams() runner.

This EXTENDS the Step 0 validated pipeline (the MODIS sample lacked native
SPM/CDM, so it derived them; here the real product provides them directly).

Output:
  inputs.bin     float32 [H*W*4] = [chl, spm, kd490, cdm]  (NaN = invalid)
  grid_meta.json {W,H, lat0,lat1,lon0,lon1, sources, bounds, fill_note}
"""
import sys, json, os
import netCDF4
import numpy as np

OUTDIR = "temp/ocean_color_real"
W = int(sys.argv[1]) if len(sys.argv) > 1 else 4096
H = int(sys.argv[2]) if len(sys.argv) > 2 else 2048

FILES = {
    "CHL":   ("chl_2024-06.nc",     "CHL"),
    "SPM":   ("spm_kd490_2024-06.nc", "SPM"),
    "KD490": ("spm_kd490_2024-06.nc", "KD490"),
    "CDM":   ("cdm_2024-06.nc",     "CDM"),
}
# physical sanity bounds (units match Copernicus product)
BOUNDS = {
    "CHL":   (0.0, 200.0),    # mg/m3
    "SPM":   (0.0, 500.0),    # g/m3
    "KD490": (0.0, 10.0),     # 1/m
    "CDM":   (0.0, 10.0),     # 1/m
}

def load_var(fname, vname):
    p = os.path.join(OUTDIR, fname)
    ds = netCDF4.Dataset(p)
    v = ds.variables[vname]
    arr = np.array(v[:]).astype(np.float32)
    fv = getattr(v, "_FillValue", None)
    lat = np.array(ds.variables["latitude"][:]).astype(np.float64)
    lon = np.array(ds.variables["longitude"][:]).astype(np.float64)
    ds.close()
    # collapse time axis if present
    if arr.ndim == 3:
        arr = arr[0]
    elif arr.ndim == 4:
        arr = arr[0, 0]
    return arr, lat, lon, fv

def mask(arr, fv, lo, hi):
    a = arr.copy()
    if fv is not None:
        a[a == fv] = np.nan
    a[a <= lo] = np.nan
    a[a > hi] = np.nan
    return a

def nearest_index(target, src):
    """vectorized nearest index into 1D src for each target value."""
    order = np.argsort(src, kind="stable")
    s_asc = src[order]
    idx = np.searchsorted(s_asc, target)
    idx = np.clip(idx, 1, len(src) - 1)
    left = order[idx - 1]
    right = order[idx]
    dl = np.abs(target - src[left])
    dr = np.abs(target - src[right])
    return np.where(dl < dr, left, right)

# target equirectangular grid (row0 = +90 N, col0 = -180)
tlat = 90.0 - (np.arange(H) + 0.5) / H * 180.0
tlon = -180.0 + (np.arange(W) + 0.5) / W * 360.0

fields = {}
src_meta = {}
for key, (fname, vname) in FILES.items():
    arr, lat, lon, fv = load_var(fname, vname)
    lo, hi = BOUNDS[key]
    arr = mask(arr, fv, lo, hi)
    # build resample index from this file's own lat/lon (they should match)
    li = nearest_index(tlat, lat)
    lj = nearest_index(tlon, lon)
    res = arr[np.ix_(li, lj)].astype(np.float32)
    fields[key] = res
    src_meta[key] = {"file": fname, "var": vname, "fill": (float(fv) if fv is not None else None),
                     "src_shape": list(arr.shape),
                     "src_lat": [float(lat.min()), float(lat.max())],
                     "src_lon": [float(lon.min()), float(lon.max())]}
    nvalid = int(np.isfinite(res).sum())
    print(f"  {key:5s}: src {arr.shape} -> target {res.shape} valid={nvalid}/{H*W} "
          f"range={np.nanmin(res):.4g}..{np.nanmax(res):.4g}")

# validity: require core CHL + KD490; SPM/CDM optional (fallback small)
core = np.isfinite(fields["CHL"]) & np.isfinite(fields["KD490"])
fields["SPM"][~np.isfinite(fields["SPM"])] = 0.1     # fallback (matches Step0)
fields["CDM"][~np.isfinite(fields["CDM"])] = 0.01    # fallback
n_core = int(core.sum())
print(f"CORE valid (CHL&KD490): {n_core}/{H*W}  ({100*n_core/(H*W):.1f}%)")

# pack into binary [H*W*4]
pack = np.full((H, W, 4), np.nan, dtype=np.float32)
pack[..., 0] = fields["CHL"]
pack[..., 1] = fields["SPM"]
pack[..., 2] = fields["KD490"]
pack[..., 3] = fields["CDM"]
pack[~core] = np.nan   # mark invalid rows fully NaN
with open(os.path.join(OUTDIR, "inputs.bin"), "wb") as f:
    f.write(pack.astype(np.float32).tobytes())

meta = {
    "W": W, "H": H,
    "lat0": 90.0, "lat1": -90.0, "lon0": -180.0, "lon1": 180.0,
    "channels": ["chl", "spm", "kd490", "cdm"],
    "n_core_valid": n_core,
    "sources": src_meta,
    "fill_note": "NaN in inputs.bin = invalid (land/cloud/masked). SPM/CDM fallback applied where missing.",
    "month": "2024-06",
}
json.dump(meta, open(os.path.join(OUTDIR, "grid_meta.json"), "w"), indent=2)
print(f"wrote inputs.bin ({H*W*4*4/1e6:.1f} MB) + grid_meta.json")
