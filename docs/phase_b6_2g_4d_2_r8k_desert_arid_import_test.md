# Phase B-6.2G-4D-2-R8K Desert / Arid 8K Export Import Test

Stage: B-6.2G-4D-2-R8K  
Type: Export / Import Test  
Date: 2026-06-10  
Scope: source-cache sample availability audit and ESA 8K import-test decision

This stage is not formal mask implementation. It does not generate `structure_masks_2048x1024.npz`, any formal 8K mask `.npz`, or any d6-ready output. It does not run the structure mask generator, does not run d6, does not write to `pwa/`, `production/`, or `candidates/`, and does not generate Noon Air imagery.

## 1. Input Files

Expected 8K files:

```text
d5b_processor_v3/source_cache/desert_arid/exported_8k/esa_worldcover_2021_v200_map_8192x4096.tif
d5b_processor_v3/source_cache/desert_arid/exported_8k/global_aridity_index_8192x4096.tif
```

Acceptable Global Aridity alternative:

```text
d5b_processor_v3/source_cache/desert_arid/exported_8k/global_aridity_index_8192x4096.nc
```

Observed file status:

| File | Exists | Import Status | Notes |
| ---- | ------ | ------------- | ----- |
| `exported_8k/esa_worldcover_2021_v200_map_8192x4096.tif` | yes | pass | downloaded from user-provided Google Drive export link into gitignored source cache |
| `exported_8k/global_aridity_index_8192x4096.tif` | no | blocked | Global Aridity sample not present |
| `exported_8k/global_aridity_index_8192x4096.nc` | no | blocked | alternative sample not present |

Current result:

```text
ESA WorldCover: import passed
Global Aridity: blocked until sample exists
```

Observed ESA file:

```text
d5b_processor_v3/source_cache/desert_arid/exported_8k/esa_worldcover_2021_v200_map_8192x4096.tif
size: 1.3 MB
sha256: f1e9a1bec3165af222dfe5680015e7c9aa52ce0b54128c2e4ac74a8d714744a6
```

The file is inside the gitignored source cache.

## 2. ESA WorldCover Import Test

ESA import test was executed after the user provided the Google Drive export.

Read result:

```text
format: TIFF
shape: 4096x8192
dtype: uint8
value_range: 0..100
NaN: false
Inf: false
frames: 1
```

Class histogram:

| Class | Meaning | Pixels |
| -----: | ------- | -----: |
| 0 | masked / no data / ocean background in this export | 24,407,626 |
| 10 | Tree cover | 2,799,895 |
| 20 | Shrubland | 423,809 |
| 30 | Grassland | 1,772,080 |
| 40 | Cropland | 719,114 |
| 50 | Built-up | 25,128 |
| 60 | Bare / sparse vegetation | 1,147,537 |
| 70 | Snow and ice | 365,442 |
| 80 | Permanent water bodies | 1,361,700 |
| 90 | Herbaceous wetland | 176,756 |
| 95 | Mangroves | 6,279 |
| 100 | Moss and lichen | 349,066 |

Class mapping to validate:

```text
10 Tree cover
20 Shrubland
30 Grassland
40 Cropland
50 Built-up
60 Bare / sparse vegetation
70 Snow and ice
80 Permanent water bodies
90 Herbaceous wetland
95 Mangroves
100 Moss and lichen
```

Import judgment:

- file is readable;
- shape matches `4096x8192`;
- class values match expected ESA WorldCover classes plus `0`;
- class `60` bare / sparse vegetation is non-empty;
- no formal structure mask was generated;
- no d6 output was generated.

The large class `0` count should be treated as masked / no-data / ocean background for this export. B-6.2G-4B must domain-clip any derived land-cover mask using the existing `land_mask` / `ocean_mask` structure layer and must not treat class `0` as a land class.

Diagnostic outputs generated in gitignored source cache:

```text
d5b_processor_v3/source_cache/desert_arid/diagnostics/esa_worldcover_2021_v200_map_8192x4096_import_stats.json
d5b_processor_v3/source_cache/desert_arid/diagnostics/esa_worldcover_2021_v200_map_8192x4096_class_preview.jpg
```

## 3. Global Aridity Import Test

Global Aridity import test was not executed because no 8K `.tif` or `.nc` sample exists.

Required sample:

```text
d5b_processor_v3/source_cache/desert_arid/exported_8k/global_aridity_index_8192x4096.tif
```

or:

```text
d5b_processor_v3/source_cache/desert_arid/exported_8k/global_aridity_index_8192x4096.nc
```

Required metadata flags:

```text
research_only: true
commercial_clearance: false
replacement_required_before_commercial: true
```

Required checks once the sample exists:

- file readable;
- shape is `4096x8192`;
- dtype;
- value range;
- nodata;
- scale / encoding;
- NaN / Inf;
- ESA 8K grid alignment;
- y-axis flip requirement.

Draft diagnostic thresholds after encoding confirmation:

- hyper-arid candidate;
- arid candidate;
- semi-arid candidate.

No diagnostic arrays were generated in this run.

## 4. 21.6K Existence Check

Expected 21.6K files:

```text
d5b_processor_v3/source_cache/desert_arid/exported_21600/esa_worldcover_2021_v200_map_21600x10800.tif
d5b_processor_v3/source_cache/desert_arid/exported_21600/global_aridity_index_21600x10800.tif
```

Acceptable Global Aridity alternative:

```text
d5b_processor_v3/source_cache/desert_arid/exported_21600/global_aridity_index_21600x10800.nc
```

Observed file status:

| File | Exists | Size | Status |
| ---- | ------ | ---: | ------ |
| `exported_21600/esa_worldcover_2021_v200_map_21600x10800.tif` | no | n/a | missing |
| `exported_21600/global_aridity_index_21600x10800.tif` | no | n/a | missing |
| `exported_21600/global_aridity_index_21600x10800.nc` | no | n/a | missing |

No checksum was computed because no 21.6K files exist.

No 21.6K array processing was attempted.

## 5. Diagnostic Region Check

ESA-only region diagnostics were computed. Global Aridity remains blocked until its 8K sample exists.

| Region | ESA bare/sparse response | Aridity response | Diagnostic Verdict | Notes |
| ------ | ------------------------ | ---------------- | ------------------ | ----- |
| Sahara | 91.88% | blocked | ESA pass | strong bare/sparse response |
| Arabian Desert | 74.79% | blocked | ESA pass | strong bare/sparse response, water/background in bbox present |
| Namib | 21.33% | blocked | watchlist | bbox includes ocean/coast and mixed classes |
| Atacama | 44.50% | blocked | ESA partial | expected aridity cross-check needed |
| Australian deserts | 7.60% | blocked | watchlist | WorldCover classifies much of bbox as grassland/shrubland; aridity required |
| Taklamakan | 85.75% | blocked | ESA pass | strong bare/sparse response |
| Sahel | 29.02% | blocked | transition watchlist | expected transition behavior |
| Gobi | 66.40% | blocked | ESA pass | strong bare/sparse response |
| Kalahari | 2.56% | blocked | watchlist | likely shrubland/grassland dominated; aridity required |
| Great Basin | 28.15% | blocked | watchlist | mixed land cover; aridity required |
| Altiplano dry regions | 30.82% | blocked | watchlist | mixed highland classes; aridity required |

The ESA-only result is useful but not sufficient for desert truth. `bare / sparse vegetation` is a land-cover class, not an aridity class. Desert-core masks still require Global Aridity or an equivalent aridity source.

## 6. Output Rules

Allowed diagnostic output locations:

```text
d5b_processor_v3/source_cache/desert_arid/diagnostics/
```

Diagnostic stats and preview were generated only in the gitignored source cache. They are not formal masks.

Forbidden outputs respected:

- no formal structure mask `.npz`;
- no 8K mask `.npz`;
- no d6 output;
- no pwa output;
- no production/candidates output;
- no Noon Air image.

## 7. Decision Gate

| Gate | Result | Reason |
| ---- | ------ | ------ |
| ESA 8K import | pass | file readable, shape/value/classes valid |
| Global Aridity 8K import | blocked | sample missing |
| 8K data can enter B-6.2G-4B | no / conditional | ESA alone is validated, but aridity source is still missing for desert-core masks |
| 21.6K exists and registered | no | files missing |
| Need D-2-R8K repeat | yes | repeat after Global Aridity sample exists |
| Can begin Desert / Arid 8K Prototype | no | ESA-only is insufficient for arid/desert semantic masks |
| d6 / visual rebuild / 上色 | still forbidden | no validated masks |

## 8. Final Recommendation

Do not enter full B-6.2G-4B yet.

ESA WorldCover 8K can proceed as the land-cover input for a future prototype, but Global Aridity is still required before building `arid_land_mask`, `hyper_arid_mask`, `semi_arid_transition_mask`, or `desert_core_mask`.

Next required file:

```text
d5b_processor_v3/source_cache/desert_arid/exported_8k/global_aridity_index_8192x4096.tif
```

or Global Aridity `.nc`:

```text
d5b_processor_v3/source_cache/desert_arid/exported_8k/global_aridity_index_8192x4096.nc
```

Minimum next action:

- provide Global Aridity 8K export;
- rerun B-6.2G-4D-2-R8K after Global Aridity exists;
- do not process 21.6K until existence/checksum registration is needed.

## 9. Completion Notes

- ESA 8K sample read: no
- Global Aridity 8K sample read: no
- 21.6K existence checked: yes
- Diagnostic outputs generated: no
- Formal masks generated: no
- Structure mask generator run: no
- d6 run: no
- pwa / production / candidates written: no
- Commit / push: no
- Critical issue: expected 8K sample files are missing
