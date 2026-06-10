# Phase B-6.2G-4A Desert / Arid / Bare Land Feasibility Audit

Stage: B-6.2G-4A  
Type: Asset / Feasibility Audit  
Date: 2026-06-10  
Scope: read-only audit plus planning document

This audit does not implement masks. It does not modify `scripts/generate_b6_structure_masks.py`, does not run the structure mask generator, does not run d6, does not generate Noon Air imagery, and does not write to `pwa/`, `production/`, or `candidates/`.

## 1. Current Structure Layer Recap

The current B-6 structure layer includes the following validated or conditionally validated mask groups.

### Base / Ocean

- `land_mask`
- `ocean_mask`
- `coastline_distance_mask`
- `deep_ocean_mask`
- `mid_ocean_mask`
- `continental_shelf_mask`
- `shallow_sea_mask`

### Polar

- `antarctica_ice_mask`
- `greenland_ice_mask`
- `polar_land_ice_mask`

### Inland Water

- `lake_mask_from_GSHHG_L2`
- `lake_island_mask`
- `inland_water_mask`
- `large_lake_mask`

### Terrain

- `mountain_mask`
- `plateau_mask`
- `high_mountain_mask`
- `plateau_refined_mask`
- `lowland_or_basin_proxy`
- `hill_or_relief_proxy`

### River

- `major_river_proxy`
- `river_buffer_proxy`
- `major_river_proxy_l01_l02`
- `river_buffer_proxy_l01_l02`

Current gap: there is still no reliable global `desert_mask`, `arid_land_proxy`, `semi_arid_transition_proxy`, `bare_land_proxy`, `salt_flat_proxy`, `dry_basin_proxy`, `sandy_desert_proxy`, `rocky_desert_proxy`, or `high_cold_desert_proxy`.

The existing terrain masks are elevation and relief proxies. They do not encode climate, vegetation absence, soil exposure, sand, salt flats, rocky desert, or aridity. A lowland basin is not automatically a dry basin, and a plateau is not automatically a cold desert.

## 2. Desert / Arid / Bare Land Data Source Audit

Read-only asset scan covered:

- `pwa/assets/source/landcover/`
- `pwa/assets/source/naturalearth/`
- `pwa/assets/source/dem/`
- `pwa/assets/source/viirs/`
- `pwa/assets/source/rdl/`
- `pwa/assets/source/osm/`
- existing source texture assets
- ETOPO1 / GEBCO assets

Observed source directories:

- `pwa/assets/source/coastline/gshhg/`
- `pwa/assets/source/coastline/naturalearth/`
- `pwa/assets/source/dem/copernicus_glo30/`
- `pwa/assets/source/bathy/`

`pwa/assets/source/coastline/naturalearth/` exists but no usable files were found in the read-only scan.  
`pwa/assets/source/dem/copernicus_glo30/` exists but no usable files were found.  
No `landcover`, `viirs`, `rdl`, or `osm` source directories were found under `pwa/assets/source/`.

| Data Source | Available? | Supports | Cannot Support | Suitable Phase | Risk |
| ----------- | ---------- | -------- | -------------- | -------------- | ---- |
| ETOPO1 Ice Surface | yes | coarse elevation, dry basin candidate context, terrain overlap checks | desert truth, aridity, vegetation absence, sand/rock distinction, salt flats | already used for terrain; proxy-only in B-6.2G-4 | high if treated as desert source |
| GSHHG / WDBII | yes | land/ocean, lakes, rivers, coastline context | desert, arid, bare land, salt flat, biome | not suitable for B-6.2G-4 except exclusions | high if overused |
| GEBCO Japan subset | yes, regional | regional bathymetry benchmark only | global desert/arid/bare land | not suitable | not global |
| Natural Earth directory | directory exists, no files found | none currently | global desert/arid truth | deferred until assets added | empty / unavailable |
| Copernicus GLO30 directory | directory exists, no files found | none currently | high-resolution terrain or arid classes | deferred until assets added | empty / unavailable |
| ESA WorldCover | not found | would support bare/sparse vegetation and land-cover classes | not currently available | B-6.2G-4/B-6.2G-5 if added | missing |
| MODIS Land Cover | not found | would support land-cover / vegetation / barren classes | not currently available | B-6.2G-4/B-6.2G-5 if added | missing |
| Copernicus Land Cover | not found | would support global land-cover classes | not currently available | B-6.2G-4/B-6.2G-5 if added | missing |
| Koppen climate / aridity index | not found | would support arid/semi-arid climate truth | not currently available | B-6.2G-4 if added | missing |
| Global soil / bare land | not found | would support sand/rock/bare ground distinction | not currently available | later semantic enrichment | missing |
| Current day texture color | yes | visual reference only | structural truth | review only | high risk: bakes current color artifacts into structure |
| Existing generated masks | yes | exclusions and overlap context | desert truth | support only | cannot classify aridity |

Conclusion: there is no current usable global desert / arid / bare land dataset in the repository.

## 3. Feature Class Feasibility

| Proposed Mask | Current Data Support | Proxy Possible Now? | Recommended Status | Notes |
| ------------- | ------------------- | ------------------- | ------------------ | ----- |
| `desert_mask` | no true data | only via known regions or external data | defer | Requires land cover / aridity / biome data |
| `arid_land_proxy` | no true data | limited known-region or climate proxy if data added | defer or review-only | ETOPO1 cannot define aridity |
| `semi_arid_transition_proxy` | no true data | no reliable current proxy | defer | Highly biome/climate dependent |
| `bare_land_proxy` | no true data | possible only with external land-cover dataset | defer | Needs ESA WorldCover / MODIS / Copernicus classes |
| `salt_flat_proxy` | no true data | known-region review-only possible | defer | Needs specialized land-cover or curated polygons |
| `dry_basin_proxy` | terrain context only | limited ETOPO1 + known-region review mask | proxy-only if implemented | Not equivalent to arid basin |
| `sandy_desert_proxy` | no true data | no reliable current proxy | defer | Needs sand/soil/land-cover data |
| `rocky_desert_proxy` | no true data | no reliable current proxy | defer | Needs bare rock / geology / land-cover data |
| `high_cold_desert_proxy` | terrain context only | limited overlap with plateau/high elevation, but not truth | defer or review-only | Tibetan/Altiplano dry zones require climate/land-cover data |

The only defensible near-term implementation is either no implementation or a clearly labeled review-only proxy. A formal `desert_mask` should not be created from RGB color or ETOPO1.

## 4. Key Region Audit

### Hot Deserts / Arid Regions

| Region | Current Data Coverage | Validation Role | Feasibility Judgment |
| ------ | --------------------- | --------------- | -------------------- |
| Sahara | no desert dataset | hard validation only after external data | must defer true mask |
| Arabian Desert | no desert dataset | hard validation only after external data | must defer true mask |
| Syrian Desert | no desert dataset | watchlist | must defer true mask |
| Iranian deserts / Dasht-e Kavir / Dasht-e Lut | terrain context only | watchlist | external aridity / land-cover needed |
| Thar Desert | no desert dataset | watchlist | external data needed |
| Taklamakan Desert | terrain basin context possible | watchlist | true desert requires external data |
| Gobi Desert | terrain/plateau context possible | watchlist | true arid/cold desert requires external data |
| Kalahari | no desert dataset | watchlist | external data needed |
| Namib | no desert dataset | watchlist | external data needed |
| Australian Outback deserts | no desert dataset | hard/watchlist after data | external data needed |
| Atacama Desert | terrain/coastal context possible | watchlist | true aridity requires external data |
| Sonoran / Mojave / Chihuahuan deserts | no desert dataset | watchlist | external data needed |

### Cold / High Deserts

| Region | Current Data Coverage | Validation Role | Feasibility Judgment |
| ------ | --------------------- | --------------- | -------------------- |
| Tibetan Plateau dry regions | plateau/high elevation proxy only | watchlist | cannot separate dry plateau from non-desert plateau |
| Altiplano dry regions | plateau/high elevation proxy only | watchlist | external climate/land-cover needed |
| Great Basin | basin/elevation context possible | watchlist | aridity source required |
| Patagonian steppe | no steppe/desert dataset | watchlist | land-cover/biome data required |
| Central Asian deserts | basin/terrain context possible | watchlist | aridity/land-cover data required |

### Salt Flats / Dry Basins

| Region | Current Data Coverage | Validation Role | Feasibility Judgment |
| ------ | --------------------- | --------------- | -------------------- |
| Salar de Uyuni | elevation context only | watchlist | true salt flat needs external/curated data |
| Bonneville Salt Flats / Great Salt Lake desert | lake/basin context only | watchlist | true salt flat needs external/curated data |
| Qaidam Basin | terrain basin context possible | watchlist | external arid/salt data required |
| Turpan Depression | ETOPO1 elevation context possible | watchlist | not enough for salt/dry basin truth |
| Caspian / Aral dry basin surroundings | lake historical context only | watchlist | high historical extent risk |
| Lake Eyre basin | basin context possible | watchlist | external aridity/land-cover required |

No region should be used as a hard validation target until a real desert/aridity/land-cover dataset is available. For a review-only known-region prototype, these regions can be watchlist anchors, not truth labels.

## 5. Proxy Risk Analysis

The desert/arid class has unusually high semantic risk because it sits at the intersection of climate, vegetation, soil, terrain, and visual color.

Key risks:

- RGB / texture color classification would copy the current visual texture into the structure layer. That would pollute structural truth with color grading artifacts.
- ETOPO1 elevation cannot determine whether an area is desert. High mountains, wet plateaus, dry plateaus, forests, and urban land can share elevation bands.
- `lowland_or_basin_proxy` cannot be treated as `dry_basin_proxy`; Amazon, Congo, Mississippi, and West Siberian lowlands are not deserts.
- Known bbox masks are not acceptable as formal global structure truth. They can be review scaffolding only.
- Desert / arid / bare land are tightly linked to biome / vegetation. Building them separately from land-cover data risks contradictory masks.
- A wrong desert mask would heavily affect Noon Air land color, especially Sahara, Arabian Peninsula, Central Asia, Australia, and western North America.
- Sand desert, rocky desert, bare land, salt flat, dry basin, and semi-arid transition should not be collapsed into one hard truth layer.

## 6. Possible B-6.2G-4B Scope

### Option A — Defer Implementation

Only record this feasibility conclusion and wait for an external global land-cover / aridity dataset.

Pros:

- Protects structure truth from proxy pollution.
- Avoids premature d6 color coupling.
- Keeps desert/arid masks aligned with future biome/vegetation phase.

Cons:

- No immediate desert semantic mask.
- Noon Air rebuild still lacks desert-specific structure until later data is added.

### Option B — Conservative Proxy Only

Implement only `arid_land_proxy` and/or `dry_basin_proxy` with explicit proxy metadata, no d6 use, and no claim of true desert classification.

Pros:

- Could provide early experimentation for dry-basin review.
- Uses existing terrain/inland-water exclusions.

Cons:

- Still weak without climate/land-cover data.
- Easy to misinterpret as true desert mask.
- Could pollute downstream API semantics if not clearly isolated.

### Option C — Known-Region Review Mask

Create review-only known-region bbox / polygon checklist masks for Sahara, Arabian Desert, Gobi, Taklamakan, Atacama, etc., explicitly not part of formal structure layer.

Pros:

- Useful for validation planning and visual review anchors.
- Avoids pretending current assets can derive desert truth.

Cons:

- Bbox / hand-coded polygons are not global truth.
- Should not be used by d6 or API as a structural mask.

Recommended current choice: **Option A**, with a possible **Option C review-only checklist** if future validation needs visual anchors. Option B should be avoided unless there is a strong short-term reason and explicit `proxy_review_only` metadata.

## 7. Interaction With Existing Masks

Future desert / arid / bare land masks should obey these rules:

- Must be constrained to `land_mask`.
- Must exclude `ocean_mask`.
- Must exclude `inland_water_mask`.
- Should not overpaint lake and river corridors in visual application.
- May overlap `plateau_refined_mask`, `lowland_or_basin_proxy`, `hill_or_relief_proxy`, and `high_mountain_mask`.
- Cold arid highlands must coexist with terrain masks rather than replace them.
- Oasis, lake, river, coastline, and wetland semantics should have higher visual priority than desert color application.
- API must support `proxy`, `confidence`, `source_dataset`, `priority`, and `mask_group` metadata.

Desert and terrain are not mutually exclusive. Desert and vegetation/biome are related but should be separated by source semantics: aridity/climate, land cover, and terrain must not be collapsed.

## 8. API / d6 / Visual Boundary

B-6.2G-4A is audit only.

Not allowed:

- d6 integration
- visual rebuild
- color application / 上色
- API freeze
- production texture changes
- `DAY_TEXTURE_VARIANT` changes
- writes to `pwa/`, `production/`, or `candidates/`

Desert / arid / bare land masks must not enter d6 until a source-backed implementation and validation gate exist.

## 9. Final Recommendation

- Is there a usable current global desert / arid / bare land dataset? **No.**
- Can B-6.2G-4B start after this audit? **No for formal masks; conditional only for review-only known-region scaffolding.**
- What can be implemented now? Preferably nothing formal. If needed, only `review_only_desert_region_checklist` or similar non-structure validation aid.
- What must be deferred? `desert_mask`, `arid_land_proxy`, `semi_arid_transition_proxy`, `bare_land_proxy`, `salt_flat_proxy`, `sandy_desert_proxy`, `rocky_desert_proxy`, and `high_cold_desert_proxy` as formal masks.
- Which datasets are missing? ESA WorldCover / MODIS / Copernicus Land Cover, Koppen climate, aridity index, global soil/bare-land, salt flat or geology data.
- Should desert / arid be merged with biome / vegetation phase? **They should be coordinated with biome/vegetation and land-cover acquisition, but not semantically merged into one mask.**
- Can d6 be touched? **No.**
- Can visual rebuild / 上色 start? **No.**
- Is git state safe? **Conditional.** The working tree has unrelated modified and untracked files; future commits must isolate docs/script changes and exclude d6, generated outputs, and root previews unless explicitly reviewed.

## 10. Completion Notes

This document was generated as a planning/audit artifact only.

- Code modified: no
- Masks generated: no
- Structure mask generator run: no
- d6 run: no
- pwa / production / candidates written: no
- Commit / push: no
- Critical issue found: no implementation blocker because formal implementation is not recommended; missing global land-cover/aridity data is the main gate

