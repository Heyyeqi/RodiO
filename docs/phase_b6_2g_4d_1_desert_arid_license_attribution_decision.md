# Phase B-6.2G-4D-1 Desert / Arid License / Attribution Decision

Stage: B-6.2G-4D-1  
Type: License / Attribution Decision  
Date: 2026-06-10  
Scope: decision document only

This stage does not download data, generate masks, modify code, run the structure mask generator, run d6, generate Noon Air imagery, write to `pwa/`, `production/`, or `candidates/`, commit, or push.

Sources reviewed:

- ESA WorldCover v200 Earth Engine catalog: <https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200>
- Copernicus CGLS-LC100 Earth Engine catalog: <https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_Landcover_100m_Proba-V-C3_Global>
- CGIAR-CSI Global Aridity and PET Database: <https://cgiarcsi.community/data/global-aridity-and-pet-database/>
- MODIS MCD12Q1 V061 / NASA Earthdata: <https://lpdaac.usgs.gov/products/mcd12q1v061/>
- Koppen-Geiger / GloH2O: <https://www.gloh2o.org/koppen/>

## 1. Decision Scope

This phase only decides whether candidate datasets can enter RodiO's current research / non-commercial prototype planning and how future commercial gates must be recorded.

It does not authorize:

- downloading full-resolution data;
- generating desert / arid masks;
- changing `scripts/generate_b6_structure_masks.py`;
- touching d6;
- visual rebuild / 上色;
- production, candidates, or pwa writes.

User decision context:

- RodiO is currently non-commercial.
- Highest-quality and highest-resolution sources may be preferred for research prototypes.
- Future commercialization must remain gated by explicit license review and replacement/permission decisions where needed.

## 2. Dataset License Decision

### ESA WorldCover 2021 v200

Decision: approved for current prototype planning and B-6.2G-4D-2 export/import testing.

Evidence:

- Earth Engine catalog lists ESA WorldCover 2021 v200 as global 10m land cover with 11 classes.
- Terms of use are CC-BY-4.0.
- Class 60 is bare / sparse vegetation.

Interpretation for RodiO:

- Research / non-commercial use: allowed.
- Future commercial use: allowed under CC-BY-4.0 attribution, subject to normal attribution compliance.
- Derived masks: allowed, with attribution and source/version metadata.
- Local cache: allowed for working copies, but raw data must remain gitignored.
- Role: primary `bare_sparse_land_mask` source.
- Attribution: cite ESA WorldCover 10 m 2021 v200 and Zenodo DOI / producer attribution in source manifest and project docs.

### Copernicus CGLS-LC100

Decision: approved as optional bare-fraction / soft-mask cross-check after attribution wording is captured.

Evidence:

- Earth Engine catalog states CGLS-LC100 is 100m global land cover for 2015-2019.
- It includes discrete classes plus continuous field layers.
- `bare-coverfraction` is available.
- Access is described as fully free and open to all users.

Interpretation for RodiO:

- Research / non-commercial use: allowed.
- Future commercial use: likely allowed under Copernicus free/open policy, but D-2 manifest must record exact citation/terms.
- Derived masks: acceptable as cross-check / soft mask.
- Local cache: acceptable if license and source attribution are preserved.
- Role: optional `bare-coverfraction` source, not required for first D-2 if ESA WorldCover export is enough.

### Global Aridity Index / PET

Decision: conditionally approved for current research / non-commercial prototype planning only; not commercial-cleared.

Evidence:

- CGIAR-CSI page states Global Aridity / PET are provided for non-commercial use.
- It prohibits commercial, non-free resale, or redistribution without explicit written permission.
- It asks users to acknowledge CGIAR-CSI Global-Aridity and Global-PET Database in derived reports, publications, new datasets, derived products, or services.
- It states commercial use requires permission.

Interpretation for RodiO:

- Research / non-commercial use: allowed for prototype planning and D-2 sample/import testing, assuming no redistribution outside project.
- Future commercial use: not cleared.
- Derived masks: allowed only within research/non-commercial scope and with attribution; commercial derived products require permission or replacement source.
- Local cache: acceptable for research prototype cache if gitignored and not redistributed.
- Publishing derived outputs: restricted; any public/commercial release must be reviewed.
- Role: primary aridity source for `arid_land_mask`, `hyper_arid_mask`, `semi_arid_transition_mask`, but all derived masks must be marked research-only until commercial clearance.

Mandatory metadata for any Global Aridity-derived mask:

- `commercial_clearance: false`
- `commercial_clearance_status: pending`
- `usage_scope: research_noncommercial_prototype`
- `replacement_required_before_commercial: true`
- `redistribution_allowed: false_without_permission`

### MODIS MCD12Q1

Decision: approved as cross-check dataset.

Evidence:

- NASA Earthdata / LP DAAC lists MCD12Q1 V061 as global 500m yearly land cover.
- The dataset is openly shared without restriction under EOSDIS data use and citation guidance.
- Citation is explicitly provided by LP DAAC.

Interpretation for RodiO:

- Research / non-commercial use: allowed.
- Future commercial use: allowed under NASA/EOSDIS open data norms, with citation.
- Derived masks: acceptable as cross-check.
- Local cache: acceptable if source, date accessed, and citation are recorded.
- Role: coarse cross-check only; not primary source for final desert boundaries.

### Koppen-Geiger / GloH2O

Decision: approved as climate cross-check.

Evidence:

- GloH2O states Koppen-Geiger maps are CC BY 4.0.
- The page says use, adaptation, and sharing are allowed for commercial and non-commercial purposes with attribution to Beck et al. (2023).

Interpretation for RodiO:

- Research / non-commercial use: allowed.
- Future commercial use: allowed under CC BY 4.0 attribution.
- Derived climate context masks: allowed.
- Local cache: allowed if attribution and version are recorded.
- Role: climate cross-check, not sole desert truth.

## 3. Decision Table

| Dataset | Role | Current Research Use | Future Commercial Use | Derived Mask Allowed | Attribution Needed | License Risk | Decision |
| ------- | ---- | -------------------- | --------------------- | -------------------- | ------------------ | ------------ | -------- |
| ESA WorldCover 2021 v200 | primary bare/sparse land source | yes | yes, CC-BY-4.0 attribution required | yes | yes | low | approve for D-2 |
| Copernicus CGLS-LC100 | bare fraction / soft-mask cross-check | yes | likely yes, record exact Copernicus terms | yes | yes | low-medium | approve as optional D-2/D-4B cross-check |
| Global Aridity Index / PET | primary aridity source | yes, research/non-commercial only | no / pending permission | conditional within research scope | yes | high | approve for research prototype only; commercial gate required |
| MODIS MCD12Q1 | land-cover cross-check | yes | yes under open NASA/EOSDIS use/citation guidance | yes | citation required | low | approve as cross-check |
| Koppen-Geiger / GloH2O | climate cross-check | yes | yes, CC BY 4.0 attribution required | yes | yes | low | approve as cross-check |

## 4. Attribution / Metadata Policy

Every derived mask must record:

- `source_dataset`
- `source_version`
- `license`
- `attribution`
- `access_url`
- `export_method`
- `export_date`
- `resolution`
- `commercial_clearance`
- `research_only`
- `caveats`

Recommended metadata examples:

```json
{
  "bare_sparse_land_mask": {
    "source_dataset": "ESA WorldCover",
    "source_version": "2021 v200",
    "license": "CC-BY-4.0",
    "attribution": "ESA WorldCover 10 m 2021 v200",
    "commercial_clearance": true,
    "research_only": false,
    "caveats": "Bare/sparse vegetation is not equivalent to desert."
  }
}
```

Global Aridity-derived masks must additionally record:

```json
{
  "arid_land_mask": {
    "source_dataset": "CGIAR-CSI Global Aridity and PET Database",
    "commercial_clearance": false,
    "commercial_clearance_status": "pending",
    "usage_scope": "research_noncommercial_prototype",
    "research_only": true,
    "replacement_required_before_commercial": true,
    "redistribution_allowed": "false_without_permission"
  }
}
```

Attribution should be recorded in:

- structure mask metadata JSON;
- source cache manifest;
- docs for B-6 data provenance;
- future app/about attribution surface if these masks become production dependencies.

## 5. Highest Resolution Policy

RodiO may choose highest-quality source truth during research, but this does not authorize full-resolution raw-data ingestion into the repository.

Policy:

- ESA WorldCover 10m may be treated as source truth for bare/sparse land.
- First import should use Earth Engine exported 2048x1024 or otherwise controlled low-resolution global raster.
- Full 10m raw global data must not enter git.
- Future 21600x10800 export may be considered as an intermediate only after separate authorization.
- Any source cache must be gitignored.
- Raw source data, exported rasters, and generated masks must stay out of tracked runtime assets unless explicitly reviewed.

## 6. Final Recommendation

- Can ESA WorldCover be used now? **Yes.**
- Can Global Aridity be used now for non-commercial research prototype? **Yes, conditional.**
- Is Global Aridity cleared for future commercial use? **No / pending.**
- Can B-6.2G-4D-2 Low-res Export / Import Test start? **Yes.**
- Should full-resolution global raw download start now? **No.**
- Should Earth Engine export be preferred? **Yes.**
- Can B-6.2G-4B start now? **No.**
- Can d6 be touched? **No.**
- Can visual rebuild / 上色 start? **No.**

Immediate next stage:

**B-6.2G-4D-2 — Low-res Export / Import Test**

Allowed in D-2:

- create or document small/low-res Earth Engine export instructions;
- import a controlled 2K or sample raster if separately authorized;
- validate orientation, projection, class values, and metadata handling;
- keep all data in gitignored cache/output paths.

Forbidden in D-2:

- formal desert/arid masks;
- d6 integration;
- production/candidates/pwa writes;
- full 10m global raw downloads;
- commits/pushes unless explicitly requested after review.

## 7. Completion Notes

- Code modified: no
- Data downloaded: no
- Masks generated: no
- Structure mask generator run: no
- d6 run: no
- pwa / production / candidates written: no
- Commit / push: no
- Critical issue: Global Aridity remains a future-commercial license gate, but is usable for current non-commercial research prototype with strict metadata flags.

