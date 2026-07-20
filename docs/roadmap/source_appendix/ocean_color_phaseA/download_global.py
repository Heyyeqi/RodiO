import os, re, subprocess, json, time
env = open('.env').read()
u = re.search(r'COPERNICUS_MARINE_USERNAME=([^\n]+)', env).group(1).strip()
p = re.search(r'COPERNICUS_MARINE_PASSWORD=([^\n]+)', env).group(1).strip()
os.environ['COPERNICUSMARINE_SERVICE_USERNAME'] = u
os.environ['COPERNICUSMARINE_SERVICE_PASSWORD'] = p
CP = "/Users/rw-mac/.workbuddy/binaries/python/envs/default/bin/copernicusmarine"
OUT = "temp/ocean_color_real"
os.makedirs(OUT, exist_ok=True)
MONTH = ("2024-06-01", "2024-06-30")
parts = [
  ("chl_2024-06.nc",     "cmems_obs-oc_glo_bgc-plankton_my_l4-multi-4km_P1M", ["CHL"]),
  ("spm_kd490_2024-06.nc","cmems_obs-oc_glo_bgc-transp_my_l4-multi-4km_P1M",  ["SPM","KD490"]),
  ("cdm_2024-06.nc",     "cmems_obs-oc_glo_bgc-optics_my_l4-multi-4km_P1M",  ["CDM"]),
]
manifest = []
for fname, dsid, vars_ in parts:
    outpath = os.path.join(OUT, fname)
    cmd = [CP, "subset", "-i", dsid] + sum([["-v", v] for v in vars_], []) \
          + ["-t", MONTH[0], "-T", MONTH[1], "-o", OUT,
             "--output-filename", fname.replace(".nc",""), "--overwrite"]
    ok = False
    for attempt in range(1, 4):
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True)
        dt = time.time() - t0
        if r.returncode == 0 and os.path.exists(outpath) and os.path.getsize(outpath) > 1000:
            sz = os.path.getsize(outpath)
            print(f"OK {fname} attempt={attempt} size={sz} ({sz/1e6:.1f} MB) dt={dt:.0f}s")
            ok = True
            manifest.append({"file": fname, "size_bytes": sz, "vars": vars_, "dataset": dsid, "dt_s": round(dt,1)})
            break
        else:
            print(f"FAIL {fname} attempt={attempt} rc={r.returncode} dt={dt:.0f}s")
            print("  stderr:", r.stderr[-200:].replace(chr(10),' '))
            time.sleep(3)
    if not ok:
        print(f"GAVEUP {fname}")
        manifest.append({"file": fname, "error": "download failed after retries"})
json.dump(manifest, open(os.path.join(OUT, "download_manifest.json"), "w"), indent=2)
print("MANIFEST:", json.dumps(manifest, indent=2))
