# Phase B-6.2G-4D Desert / Arid Data Acquisition Plan

Stage: B-6.2G-4D  
Type: Data Acquisition / License / Storage Planning  
Date: 2026-06-10  
Scope: planning only

This stage does not generate desert masks. It does not implement the structure mask generator, run d6, generate Noon Air imagery, write to `pwa/`, `production/`, or `candidates/`, download large files, commit, or push.

Reference sources:

- ESA WorldCover v200: <https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200>
- Copernicus CGLS-LC100: <https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_Landcover_100m_Proba-V-C3_Global>
- MODIS MCD12Q1 V061: <https://lpdaac.usgs.gov/products/mcd12q1v061/>
- CGIAR-CSI Global Aridity and PET: <https://cgiarcsi.community/data/global-aridity-and-pet-database/>
- Koppen-Geiger / GloH2O: <https://www.gloh2o.org/koppen/>

## 1. Goal

B-6.2G-4D is not a mask-generation phase and not a visual rebuild phase. Its goal is to decide whether desert / arid / bare land source data can legally, stably, and reproducibly enter the RodiO structure mask pipeline.

This plan must answer:

- license and attribution requirements;
- whether derived masks are allowed;
- where raw and intermediate data may be stored;
- how downloads or exports should be reproduced;
- how high-resolution land-cover data should be downsampled;
- whether local tooling is sufficient;
- what must happen before B-6.2G-4B can generate any 2K prototype masks.

The immediate follow-up phases are:

- B-6.2G-4D-1 License / Attribution Decision;
- B-6.2G-4D-2 Low-res Sample Import Test;
- B-6.2G-4B Desert / Arid Minimal Prototype;
- B-6.2G-4C Desert / Arid Validation Audit.

## 2. License Compatibility Audit

| Dataset | License | Commercial Use? | Derived Masks Allowed? | Local Cache Allowed? | Attribution Needed? | Risk | Verdict |
| ------- | ------- | --------------- | ---------------------- | -------------------- | ------------------- | ---- | ------- |
| ESA WorldCover 2021 v200 | CC-BY-4.0 | yes, subject to attribution | yes, derived masks should be allowed under attribution | likely yes, if license and source attribution are preserved | yes | low-medium: must carry attribution into docs/about/source manifest | usable after attribution plan |
| Copernicus CGLS-LC100 | free/open access terms via Copernicus / Earth Engine | likely yes under Copernicus data policy, verify exact citation text | likely yes | likely yes | yes | medium: exact Copernicus attribution wording must be captured | usable after D-1 confirmation |
| Global Aridity Index / PET | CGIAR-CSI page states non-commercial use and permission requirement for commercial use | uncertain / restricted | uncertain for commercial downstream masks | uncertain; likely research cache only unless permission obtained | yes | high: non-commercial restriction may conflict with product usage | license decision required before production use |
| MODIS MCD12Q1 | NASA / LP DAAC open data with citation guidance | generally yes | yes, for derived analysis with citation | yes | citation recommended/required by publication norms | low | suitable as cross-check |
| Koppen-Geiger / GloH2O | CC BY 4.0 | yes, subject to attribution | yes | yes | yes | low-medium: climate context only, not desert truth | suitable as cross-check |

### License Conclusions

ESA WorldCover is the safest primary source for `bare_sparse_land_mask` if RodiO records CC-BY-4.0 attribution in docs and any user-visible attribution surface if needed.

Copernicus CGLS-LC100 is attractive for `bare-coverfraction`, but B-6.2G-4D-1 must record the exact Copernicus attribution and redistribution terms before local caching.

Global Aridity Index / PET is the main blocker. The public source explicitly frames usage as non-commercial and asks commercial users to contact the authors. It must not be used in a product-facing pipeline until compatibility is decided. It may be research-only unless permission or an alternative source is selected.

MODIS and Koppen-Geiger are suitable cross-checks, not primary desert truth.

## 3. Data Access Strategy

### Option A — Google Earth Engine Export

Applies to:

- ESA WorldCover;
- Copernicus CGLS-LC100;
- MODIS MCD12Q1;
- Dynamic World if later needed.

Assessment:

- Best route for a first global 2048x1024 raster export.
- Can export class rasters or precomputed binary/probability rasters.
- Can control projection and target resolution.
- Avoids downloading and mosaicking global 10m tiles locally.
- Requires Earth Engine account and export script reproducibility.
- Export scripts and parameters must be documented, not hidden in manual UI steps.

Recommended use:

- ESA WorldCover class raster exported at 2048x1024 for D-2.
- Optional 21600x10800 intermediate export only after D-2 succeeds.
- Copernicus bare-coverfraction exported at 2048x1024 as soft-mask candidate.

### Option B — Local Tiled Downloads

Applies to:

- ESA WorldCover COG / tiles;
- Copernicus files.

Assessment:

- More reproducible if scripted and checksummed.
- Much heavier locally.
- Current environment lacks `rasterio`, `osgeo` / GDAL Python bindings, `gdalinfo`, and `ogrinfo`.
- Full 10m global processing on a local Mac is likely too expensive for this phase.

Recommended use:

- Defer.
- Reconsider only after a dedicated tooling/install plan or if Earth Engine export is unavailable.

### Option C — Lower-res First Prototype

Applies to:

- MODIS MCD12Q1;
- Koppen-Geiger;
- Global Aridity Index / PET.

Assessment:

- Easier for 2K proof-of-concept.
- Good for aridity and climate-context logic.
- Not sufficient for final desert boundaries.
- Useful for D-2 import testing if data license permits.

Recommended use:

- Use MODIS / Koppen as cross-checks.
- Use Global Aridity only after D-1 license decision.

### Recommended Access Path

1. Use Earth Engine export for ESA WorldCover 2021 2K class raster.
2. Use Earth Engine export for Copernicus bare-coverfraction 2K raster if license/attribution is confirmed.
3. Do not use Global Aridity in generated masks until D-1 license decision is complete.
4. Use MODIS/Koppen as low-resolution cross-checks, not as primary mask sources.

## 4. Storage / Cache Policy

Recommended local cache root:

```text
d5b_processor_v3/source_cache/desert_arid/
  README.md
  manifest.json
  raw/
  intermediate/
  exported_2k/
  checksums/
  licenses/
```

Policy:

- Entire `d5b_processor_v3/source_cache/` should be gitignored before any data is placed there.
- Raw full-resolution data must never be committed.
- Intermediate exports must not be committed unless explicitly small, reviewed, and approved.
- `manifest.json` should record `dataset`, `version`, `source_url`, `license`, `attribution`, `downloaded_at`, `export_method`, `projection`, `resolution`, `checksum`, and `allowed_use`.
- A short tracked README may be acceptable if it contains instructions only and no data.
- Generated 2K structure masks must continue to be written only to `d5b_processor_v3/d5b_output/structure_masks/`.
- Generated `.npz`, metadata, metrics, and previews remain uncommitted.

Alternative `pwa/assets/source/external/desert_arid/` is not recommended for raw data because `pwa/assets` is too close to runtime assets and increases accidental production/front-end coupling risk.

## 5. First Prototype Data Mapping

This is a mapping draft only. B-6.2G-4D must not generate masks.

### ESA WorldCover

Draft use:

- class 60 bare / sparse vegetation -> `bare_sparse_land_mask` candidate;
- exclude water, snow/ice, built-up, cropland, tree cover from bare/sparse mask;
- shrubland and grassland should not directly become desert;
- shrubland / grassland may contribute to `semi_arid_transition_mask` only when crossed with aridity.

### Global Aridity Index

Draft classes, subject to dataset scale and encoding verification:

- hyper-arid: AI < 0.03;
- arid: 0.03 <= AI < 0.20;
- semi-arid: 0.20 <= AI < 0.50;
- dry sub-humid: 0.50 <= AI < 0.65, optional context only.

These thresholds must be checked against the actual raster scale before any prototype. Some datasets store scaled integer values rather than direct float AI.

### Derived Candidate Masks

| Mask | Source | Type | Expected Role | Caveat |
| ---- | ------ | ---- | ------------- | ------ |
| `bare_sparse_land_mask` | ESA WorldCover class 60, optionally Copernicus bare fraction | data-derived land-cover | bare/sparse surface selector | bare/sparse is not always desert |
| `arid_land_mask` | Global Aridity Index | data-derived climate | arid climate selector | blocked by license decision |
| `hyper_arid_mask` | Global Aridity Index | data-derived climate | extreme dry climate core | blocked by license decision |
| `semi_arid_transition_mask` | aridity + shrub/grass/sparse classes | derived intersection | transition-zone selector | must avoid overpainting savanna/grassland truth |
| `desert_core_mask` | arid/hyper-arid + bare/sparse land cover | derived intersection | best first formal desert-core mask | depends on both license and alignment |

Salt flat, sand desert, and rocky desert masks remain deferred.

## 6. Tooling Plan

Current local tooling:

- `rasterio`: missing
- `osgeo` / GDAL Python bindings: missing
- `gdalinfo`: not found
- `ogrinfo`: not found
- `xarray`: available
- `netCDF4`: available
- `numpy`: available
- `scipy`: available, with an existing SciPy/NumPy version warning

Implications:

- Do not start local tiled GeoTIFF / COG processing now.
- Prefer Earth Engine export for ESA WorldCover / Copernicus initial data.
- Global Aridity may be easier if available in NetCDF-compatible or simple grid form, but license comes first.
- A low-resolution sample import test is required before B-6.2G-4B.
- Installing GDAL/rasterio is not recommended inside this stage. If needed, create a separate tooling task with explicit approval.

Recommended B-6.2G-4D-2 test:

- use a tiny or already downsampled exported raster;
- confirm read path;
- confirm lon/lat orientation;
- confirm 2048x1024 alignment;
- confirm class mapping and no y-flip / 180-degree offset;
- write only to a gitignored cache/output path.

## 7. Risk Register

| Risk | Impact | Likelihood | Mitigation |
| ---- | ------ | ---------- | ---------- |
| Global Aridity license incompatible | blocks arid masks | medium-high | D-1 license decision before use; identify alternative aridity source |
| Earth Engine export not reproducible | weak provenance | medium | commit/export script later; record parameters in manifest |
| 10m global data too large | local processing fails | high | export 2K/21.6K rasters; avoid local full-resolution tiles initially |
| WorldCover bare class not equal desert | false desert positives | high | combine with aridity; keep bare/sparse separate |
| MODIS too coarse | poor boundaries | high | use only cross-check |
| Koppen-Geiger climate not land cover | overbroad dry zones | high | use only climate context |
| projection/resampling artifacts | wrong masks | medium | D-2 alignment validation |
| small salt flats disappear after downsampling | missing detail | medium | defer specialized salt flat dataset |
| salt/sandy/rocky desert data missing | incomplete semantics | high | explicitly defer |
| d6 consumes unvalidated masks | visual regressions | high | forbid d6 until B-6.2G-4C passes and API priority is designed |

## 8. Phase Plan

| Phase | Goal | Allowed | Forbidden | Exit Criteria |
| ----- | ---- | ------- | --------- | ------------- |
| B-6.2G-4D-1 License / Attribution Decision | Confirm exact use rights | read licenses, write doc, define attribution text | no downloads, no masks, no d6 | dataset verdict table accepted |
| B-6.2G-4D-2 Low-res Sample Import Test | Test one low-res exported/global sample | small authorized sample only, gitignored cache, read/resample validation | no formal masks, no d6, no pwa | sample reads, aligns, and documents checksum/projection |
| B-6.2G-4B Desert / Arid Minimal Prototype | Generate 2K prototype masks | modify structure generator, write d5b_output only | no d6, no production, no candidates | masks/metadata/metrics/previews generated |
| B-6.2G-4C Desert / Arid Validation Audit | Validate geography and semantics | read-only audit | no regeneration, no d6 | pass/conditional/fail verdict |

## 9. Final Recommendation

- Which dataset should be acquired first? **ESA WorldCover 2021 v200 2K export**, because license is straightforward and it supports `bare_sparse_land_mask`.
- Which dataset requires license decision before use? **Global Aridity Index / PET**.
- Should Earth Engine export be preferred? **Yes**, for ESA WorldCover and Copernicus initial exports.
- Should local GDAL/rasterio be installed now? **No**, not in this phase. Decide later if Earth Engine export is insufficient.
- Should B-6.2G-4B start now? **No.**
- Should B-6.2G-4D-1 start next? **Yes.**
- Should B-6.2G-4D-2 start next? **Yes, after D-1 establishes license-compatible sources and with only small/downsampled samples.**
- Can d6 be touched? **No.**
- Can visual rebuild / 上色 start? **No.**
- Is git state safe? **Conditional.** Existing modified/untracked files require commit discipline; d6, generated outputs, and root previews must remain out of scope.

## 10. Completion Notes

- Code modified: no
- Data downloaded: no
- Masks generated: no
- Structure mask generator run: no
- d6 run: no
- pwa / production / candidates written: no
- Commit / push: no
- Critical issue: Global Aridity license is the main decision gate before formal aridity masks

