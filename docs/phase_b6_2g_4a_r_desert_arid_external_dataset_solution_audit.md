# Phase B-6.2G-4A-R Desert / Arid / Bare Land External Dataset Solution Audit

Stage: B-6.2G-4A-R  
Type: External Dataset Solution Audit  
Date: 2026-06-10  
Scope: external dataset research plus implementation planning only

This audit does not implement masks. It does not modify code, download data, run the structure mask generator, run d6, generate Noon Air imagery, write to `pwa/`, `production/`, or `candidates/`, commit, or push.

Sources reviewed:

- ESA WorldCover 10m v200: <https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200>
- Copernicus CGLS-LC100 Collection 3: <https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_Landcover_100m_Proba-V-C3_Global>
- NASA MODIS MCD12Q1 V061: <https://lpdaac.usgs.gov/products/mcd12q1v061/>
- CGIAR-CSI Global Aridity and PET Database: <https://cgiarcsi.community/data/global-aridity-and-pet-database/>
- Koppen-Geiger climate maps by GloH2O: <https://www.gloh2o.org/koppen/>
- Dynamic World V1: <https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1>

## 1. Problem Restatement

B-6.2G-4A did not terminate desert / arid / bare land work. It established a narrower fact: the current repository does not contain a usable global desert, arid, bare land, salt flat, or sparse vegetation dataset.

This round answers the next question: what external data sources should be used to build desert / arid / bare land semantics without polluting the structure layer.

Hard constraints:

- Do not use current day texture / RGB / color-graded output to infer structure truth.
- Do not use known-region bbox masks as formal structure masks.
- Do not treat ETOPO1 as desert truth. ETOPO1 can only provide terrain context.
- Do not mix desert, aridity, bare ground, sparse vegetation, salt flats, and rocky terrain into one unqualified truth layer.

The structure layer should distinguish:

- land-cover evidence: bare / sparse / shrub / grass / vegetation classes;
- climate evidence: aridity, hyper-aridity, semi-arid transition;
- terrain context: dry basins, plateaus, depressions;
- review-only or deferred features: salt flats, sand desert, rocky desert where no reliable global source exists.

## 2. Candidate Dataset Audit

| Dataset | Type | Resolution | Global? | Classes Useful for RodiO | License / Access | Pros | Cons | Recommended Role |
| ------- | ---- | ---------: | ------- | ------------------------ | ---------------- | ---- | ---- | ---------------- |
| ESA WorldCover 2021 v200 | land cover | 10m | yes | bare / sparse vegetation, shrubland, grassland, cropland, tree cover, water, wetland, snow/ice | CC-BY-4.0; Earth Engine and ESA access | Strong primary source for `bare_sparse_land_mask`; simple class table; modern Sentinel-derived product | Full global 10m is too large for direct local ingestion; one-year snapshot; bare/sparse does not equal desert | Primary land-cover source for bare/sparse land |
| ESA WorldCover 2020 v100 | land cover | 10m | yes | same broad WorldCover taxonomy | CC-BY-4.0; ESA/Earth Engine | Useful temporal cross-check for 2021 | Not needed for first prototype if using 2021 | Optional cross-year check |
| Copernicus CGLS-LC100 Collection 3 | land cover + fractional cover | 100m | yes | bare-coverfraction, shrub-coverfraction, grass-coverfraction, discrete classes, water, snow, urban | free/open access; Earth Engine / Copernicus | Fractional `bare-coverfraction` is very useful for soft masks; smaller than 10m data; 2015-2019 time series | Older than WorldCover 2021; 100m still large; taxonomy differs from ESA WorldCover | Strong secondary land-cover source; cross-check and soft bare fraction |
| MODIS MCD12Q1 V061 | yearly land cover | 500m | yes | IGBP, UMD, LAI, BIOME-BGC, PFT, FAO LCCS layers | NASA Earthdata; openly shared with citation guidance | Long annual time series; small enough for robust global processing; useful independent cross-check | Coarse; not ideal for 2K coast/desert boundaries; 2021+ caution noted by NASA | Cross-check dataset, not primary visual-quality source |
| Global Aridity Index / PET, CGIAR-CSI | climate aridity | 30 arc-second, about 1km | yes | aridity index, PET; hyper-arid / arid / semi-arid thresholds | non-commercial use; ARC/INFO Grid | Best fit for `arid_land_mask`, `hyper_arid_mask`, `semi_arid_transition_mask`; directly measures climate dryness | License restricts usage; older WorldClim-derived climatology; format may require GIS tooling | Primary aridity source if license fits project use |
| Koppen-Geiger climate maps, GloH2O | climate classification | 1km and other downloads | yes | BWh, BWk, BSh, BSk dry climate classes | CC BY 4.0 | Good climate context and dry-class cross-check; easy semantic classes | Climate class is not land cover; can classify non-bare dry grass/shrub zones; should not be sole desert truth | Cross-check / climate context |
| Dynamic World V1 | near-real-time land cover probabilities | 10m | near-global Sentinel-2 coverage | bare probability, shrub/scrub, grass, crops, water, trees, flooded vegetation | CC-BY 4.0 via Earth Engine | Probability bands enable confidence masks; modern and flexible | Requires compositing; arid bright surfaces can be tricky; Earth Engine workflow needed | Optional future validation / update source |
| WorldClim / CHELSA derived aridity | climate inputs | variable, commonly 30 arc-sec to km scale | yes | precipitation, temperature, PET-derived aridity | depends on product | Can reproduce or update aridity indices | Requires method design and processing | Later replacement/upgrade path |
| GLAD / FROM-GLC / other global land cover | land cover | varies | yes | bare / vegetation classes depending product | varies | Potential independent checks | Additional acquisition complexity | optional future cross-check |
| FAO / HWSD / global soil | soil / bare substrate | coarse | yes/partial | soil, sand/rock context | varies | Could help sand/rock distinction | Not enough alone for desert mask; may be coarse/old | future enrichment only |
| Global salt flat / playa datasets | salt flat / playa | varies | uncertain | salt flats, dry lake beds | varies | Needed for true `salt_flat_mask` | No current project asset; candidate quality/license must be separately audited | deferred |

### Dataset Notes

ESA WorldCover 2021 is the best current candidate for `bare_sparse_land_mask` because it is global, 10m, CC-BY-4.0, and includes a direct bare / sparse vegetation class.

Copernicus CGLS-LC100 is a strong secondary source because it includes both discrete land-cover classes and continuous cover fraction layers, including `bare-coverfraction`. It may be better for soft masks than class-only data.

MODIS MCD12Q1 should not be the primary source for final 2K visual-quality land cover, but it is valuable for cross-checking because it is global, yearly, and relatively small.

Global Aridity Index / PET is the best conceptual fit for aridity classes, but its non-commercial usage language must be reviewed before any production pipeline depends on it.

Koppen-Geiger is useful for climate context, especially BWh / BWk / BSh / BSk dry classes, but it should not be the only desert truth because a climate zone does not guarantee bare ground.

## 3. Recommended Multi-source Design

The recommended design uses land cover and aridity as separate sources, then combines them only in explicitly named derived masks.

### Data-derived Masks

| Mask | Primary Source | Method Draft | Status |
| ---- | -------------- | ------------ | ------ |
| `bare_sparse_land_mask` | ESA WorldCover class 60 and/or Copernicus `bare-coverfraction` | land AND not inland water/ocean/polar ice; class 60 or bare fraction threshold | suitable after data acquisition |
| `arid_land_mask` | Global Aridity Index | land AND AI below arid threshold; draft thresholds require validation | suitable after license/download audit |
| `hyper_arid_mask` | Global Aridity Index | land AND AI in hyper-arid range | suitable after license/download audit |
| `semi_arid_transition_mask` | Global Aridity Index + land cover | semi-arid AI range intersect sparse/shrub/grass classes | suitable after data acquisition |
| `desert_core_mask` | aridity + bare/sparse land cover | hyper-arid/arid AND bare/sparse land cover | best formal desert-core candidate |

Draft aridity thresholds should use a documented standard such as UNEP P/PET ranges, but must be verified against the chosen dataset scale and encoding before implementation.

### Proxy Masks

| Mask | Source | Method Draft | Status |
| ---- | ------ | ------------ | ------ |
| `dry_basin_proxy` | ETOPO1 terrain context + aridity | lowland/basin or depression context AND arid/semi-arid | proxy only |
| `high_cold_desert_proxy` | Koppen-Geiger + aridity + plateau/high elevation | dry climate class AND plateau/high elevation | proxy or cross-check |

### Deferred / Review-only Masks

| Mask | Reason |
| ---- | ------ |
| `salt_flat_proxy` | Requires reliable salt flat / playa source or curated review-only polygons |
| `sandy_desert_proxy` | Requires sand/soil/geology or specialized desert surface source |
| `rocky_desert_proxy` | Requires bare rock/geology/soil source |
| known-region desert bbox masks | Review-only checklists, not formal structure masks |

### Recommended First Formal Prototype

Do not start B-6.2G-4B until B-6.2G-4D data acquisition is complete.

After data acquisition, first prototype should include:

- `bare_sparse_land_mask`
- `arid_land_mask`
- `hyper_arid_mask`
- `semi_arid_transition_mask`
- `desert_core_mask`

Do not include salt flat / sand desert / rocky desert as formal masks in the first prototype.

## 4. Downsampling / Runtime Feasibility

### Data Size / Processing

Global 10m land-cover data is too large for naive local processing on a Mac. It should not be downloaded wholesale into the repository. Practical options:

- use Earth Engine export to create a pre-downsampled global raster at 2048x1024 or 21600x10800;
- download tiled ESA WorldCover / COG data only into a gitignored source cache;
- use Copernicus 100m or MODIS 500m for lower-friction initial prototypes;
- use Global Aridity Index at about 1km for aridity masks.

### Repository Policy

- Raw external data should be gitignored.
- Source cache should live outside tracked assets or in a clearly gitignored source cache.
- 2K generated masks should continue to be written only under `d5b_processor_v3/d5b_output/structure_masks/`.
- Generated `.npz`, metadata, metrics, and previews should remain uncommitted unless a later policy changes.

### Tooling

Local environment check:

- `rasterio`: missing
- `osgeo` / GDAL Python bindings: missing
- `gdalinfo`: not found
- `ogrinfo`: not found
- `xarray`: available
- `netCDF4`: available
- `numpy`: available
- `scipy`: available, but current environment reports a SciPy/NumPy version warning

Implication:

- GeoTIFF / COG processing is not ready locally without installing rasterio/GDAL or using external preprocessing.
- NetCDF-style climate data can be easier with current `xarray`/`netCDF4`.
- Earth Engine export may be the most practical first path for ESA WorldCover / Dynamic World / Copernicus land-cover products.

No data was downloaded in this audit.

## 5. Proposed Phase Plan

| Phase | Goal | Allowed | Forbidden | Exit Criteria |
| ----- | ---- | ------- | --------- | ------------- |
| B-6.2G-4D — Desert / Arid Data Acquisition Plan | Decide exact datasets and storage policy | write docs, inspect licenses, design paths | no large downloads, no masks, no d6 | primary bare/sparse and aridity sources selected |
| B-6.2G-4D-1 — License / Download / Storage Audit | Confirm licenses and cache layout | license review, small metadata checks | no production use | license-compatible dataset list |
| B-6.2G-4D-2 — Low-res Sample Import Test | Test one small region or low-res global export | small authorized sample only, gitignored cache | no formal masks, no d6 | import path validated |
| B-6.2G-4B — Desert / Arid Minimal Prototype | Generate 2K prototype masks | structure generator changes, 2K generated output only | no d6, no production, no candidates | masks created with metadata and limitations |
| B-6.2G-4C — Validation Audit | Validate masks | read-only numeric/geographic audit | no regeneration, no d6 | pass/conditional/fail verdict |

If Earth Engine export is chosen, the acquisition plan must specify:

- exact dataset IDs;
- class mappings;
- export resolution and projection;
- attribution requirements;
- whether exported rasters may be stored locally;
- whether any terms restrict commercial use.

## 6. Key Region Validation Design

### Core Deserts

| Region | Role | Validation Type |
| ------ | ---- | --------------- |
| Sahara | core desert | hard for `desert_core_mask` / `hyper_arid_mask` |
| Arabian Desert | core desert | hard |
| Iranian deserts | core desert | hard/watchlist |
| Thar | arid desert edge | watchlist |
| Taklamakan | sandy/cold desert | hard for arid/bare; watchlist for sand |
| Gobi | cold desert / steppe transition | watchlist |
| Kalahari | semi-arid to arid | watchlist |
| Namib | coastal hyper-arid | hard |
| Australian deserts | core arid interior | hard |
| Atacama | hyper-arid coastal desert | hard |
| Sonoran / Mojave / Chihuahuan | North American deserts | hard/watchlist |

### Semi-arid / Transition

| Region | Role | Validation Type |
| ------ | ---- | --------------- |
| Sahel | semi-arid transition | hard for `semi_arid_transition_mask`, not desert core |
| Central Asian steppe margins | semi-arid transition | watchlist |
| Patagonian steppe | cold semi-arid | watchlist |
| Great Basin | dry basin / semi-arid | watchlist |
| Altiplano dry regions | high cold arid | watchlist |

### Salt Flats / Dry Basins

| Region | Role | Validation Type |
| ------ | ---- | --------------- |
| Salar de Uyuni | salt flat | watchlist/deferred |
| Qaidam Basin | dry basin / salt flats | watchlist/deferred |
| Turpan Depression | dry basin | watchlist |
| Bonneville / Great Salt Lake Desert | salt flat / dry basin | watchlist/deferred |
| Lake Eyre Basin | dry basin / ephemeral lake | watchlist |
| Aral dry basin surroundings | historical water / dry basin | watchlist with historical-risk note |

Salt flats should not be hard validation targets until a salt flat / playa dataset exists.

## 7. API / d6 Boundary

B-6.2G-4A-R is an external dataset solution audit only.

Not allowed:

- d6 integration
- visual rebuild
- color application / 上色
- API freeze
- production texture changes
- pwa / production / candidates writes
- generated Noon Air images

Any desert / arid masks must complete:

1. data acquisition plan;
2. license / storage audit;
3. import test;
4. prototype generation;
5. validation audit;

before d6 may consume them.

## 8. Final Recommendation

- Best primary data source for bare / sparse land: **ESA WorldCover 2021 v200**, with **Copernicus CGLS-LC100 `bare-coverfraction`** as an important secondary / soft-mask source.
- Best primary data source for aridity: **Global Aridity Index / PET**, subject to license review.
- Best cross-check dataset: **MODIS MCD12Q1** for broad land-cover consistency and **Koppen-Geiger** for dry-climate context.
- Whether B-6.2G-4B can start immediately: **No.**
- Whether B-6.2G-4D data acquisition should happen first: **Yes.**
- Whether salt flat / sand desert / rocky desert should be deferred: **Yes.**
- Whether desert / arid should be solved before island / reef: **Conditional.** It should not block reef/island data planning, but it must be solved before any final multi-theme land-color API freeze or Noon Air visual rebuild that depends on desert semantics.
- Can d6 be touched? **No.**
- Can visual rebuild / 上色 start? **No.**
- Is git state safe? **Conditional.** Current worktree has unrelated modified and untracked files; future commits must isolate docs/script work and exclude d6, generated outputs, and root previews unless explicitly reviewed.

Recommended next stage:

**B-6.2G-4D — Desert / Arid Data Acquisition Plan**

Minimum next decisions:

1. Confirm whether CGIAR-CSI Global Aridity non-commercial terms are compatible with RodiO usage.
2. Decide Earth Engine export vs local tiled downloads for ESA WorldCover.
3. Define a gitignored source-cache path.
4. Define 2K first-prototype class mapping and metadata schema.

## 9. Completion Notes

- Code modified: no
- Data downloaded: no
- Masks generated: no
- Structure mask generator run: no
- d6 run: no
- pwa / production / candidates written: no
- Commit / push: no
- Critical issue: no technical blocker found, but data license/acquisition is now the required gate

