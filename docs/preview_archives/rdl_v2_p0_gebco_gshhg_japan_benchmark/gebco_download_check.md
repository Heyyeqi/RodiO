# GEBCO Download Check — Japan Subset

**Date:** 2026-06-08  
**Region key:** 118_150_22_50 (lon 118–150°E, lat 22–50°N)  
**Bounds:** W=118°E, E=150°E, S=22°N, N=50°N  

---

## Dataset Confirmed: GEBCO 2026

The latest release is **GEBCO 2026** (published 2026-04-23), superseding GEBCO 2023/2024.  
Resolution: **15 arc-second** (~450 m/px at equator, ~390 m/px at 30°N)

> All pipeline files and directories use `gebco_2026` — version name matches the data source URL exactly.

---

## Download Tool

**URL:** https://download.gebco.net  
**Method:** Web-based Grid Subsetting App (JavaScript UI)  
**Input:** Bounding box in decimal degrees  
**Formats:** netCDF · GeoTIFF · Esri ASCII raster  
**Registration:** Not required  

---

## Japan Subset Size Estimate

| Parameter | Value |
|---|---|
| Lon extent | 32° (118°E → 150°E) |
| Lat extent | 28° (22°N → 50°N) |
| Grid cells (15 arc-sec) | 7,680 × 6,720 = 51,609,600 |
| Fraction of global grid | ~1.4% |
| Global netCDF compressed | ~4.0–4.9 GB |
| **Japan subset estimate (netCDF)** | **~56–70 MB** |
| Japan subset (GeoTIFF float32 uncompressed) | ~197 MB |
| Japan subset (GeoTIFF with LZW/DEFLATE) | ~50–80 MB |

**Conclusion: Japan subset is ~60–80 MB, well within acceptable range.**  
This is significantly smaller than the preliminary estimate of 200–400 MB.  
**RW confirmation to download is now requested.**

---

## Download Parameters (ready to use)

```
Tool:      https://download.gebco.net
Format:    netCDF (recommended) or GeoTIFF
West:      118
East:      150
South:     22
North:     50
Variable:  elevation (negative = depth below sea level)
```

---

## Alternative: Pre-built Tile Download

GEBCO also provides 8 pre-built 90°×90° tiles. Japan falls in:
- **Tile SE-Asia/Pacific**: lon 90–180°E, lat 0–90°N

Tile size: ~600–700 MB (compressed) — covers Japan but contains unnecessary area.  
**Subset download via the app is preferred** for Japan-only benchmark.

---

## Checklist

- [x] Dataset confirmed (GEBCO 2026, 15 arc-second)
- [x] Download tool confirmed (download.gebco.net, no registration)
- [x] Format confirmed (netCDF or GeoTIFF)
- [x] Bounds confirmed (118°E, 150°E, 22°N, 50°N)
- [x] Size estimate confirmed (~60–80 MB — acceptable)
- [ ] **Awaiting RW confirmation to proceed with download**

---

## Post-Download Plan

1. Place file at: `pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc`
2. Run: `scripts/geo/gebco_bathymetry_tint.py --bounds 118 150 22 50`
3. Output: `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/gebco_bathymetry_tint.png`
