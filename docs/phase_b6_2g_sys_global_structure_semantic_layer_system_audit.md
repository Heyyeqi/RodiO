# Phase B-6.2G-SYS Global Structure Semantic Layer System Audit

Date: 2026-06-10

Scope: system-level audit and roadmap only. This document does not modify code, does not run `scripts/generate_b6_structure_masks.py`, does not generate masks, does not run d6, does not write to `pwa`, `production`, or `candidates`, and does not commit or push.

## 0. Current Phase Position

Current B-6 is not a d6 refactor phase, not a visual rebuild phase, not an API freeze phase, and not a B-5.3 visual patch phase.

Current main line:

```text
B-6.2G - Global Surface Feature Taxonomy & Gap Audit
B-6.2G-SYS - Global Structure Semantic Layer System Audit
Future split phases - lake / terrain / desert / vegetation / cryosphere / reef / island / river supplements
```

B-6.2S-1 special sea masks passed validation, but that only proves named special sea water-only selectors are feasible. It does not prove the global ocean semantic layer is complete.

B-6.2G-1A inland water asset audit shows GSHHG L2/L3 can support lake masks. It does not prove the global structure semantic layer is complete, and it does not authorize d6 integration.

Current production remains `d5z_b`. `DAY_TEXTURE_VARIANT` and production texture must not be changed.

## 1. Existing Structure Mask Capability Audit

| Existing Mask | Current Role | Reliable For | Not Reliable For | Gap |
| ------------- | ------------ | ------------ | ---------------- | --- |
| `land_mask` | Final land selector from GSHHG L1 plus polar supplement | Broad land/ocean separation | Land biomes, inland water, wetlands, deserts, forests, plains, human land use | Land is still a binary shell, not land semantics. |
| `ocean_mask` | Inverse of corrected land mask | Broad water selection outside land | Lakes, rivers, wetlands, sea ice, narrow semantic seas | Inland water is not represented as water semantics yet. |
| `deep_ocean_mask` | ETOPO1 deep ocean class | Broad deep basin selection | Trenches, upwelling, currents, banks, reefs | Ocean geomorphology remains coarse. |
| `mid_ocean_mask` | ETOPO1 mid-depth ocean class | Broad mid-depth water | Marginal seas, shelves, banks, straits | Needs named/morphological ocean classes. |
| `continental_shelf_mask` | ETOPO1 shelf depth class | Large continental shelf signal | Fine shelves, banks, reef platforms, turbid shelf semantics | Needs GEBCO/reef/bank refinement later. |
| `shallow_sea_mask` | ETOPO1 shallow water class | Broad shallow seas | Maldives, Tuamotu, Bahamas Bank, GBR, narrow lagoons | Too coarse for reef/atoll quality. |
| `coastline_distance_mask` | Ocean-side pixel distance from coast | Generic coastal influence | Km-accurate distance, cliffs, deltas, mangroves, estuaries | Needs coastal semantic subtypes. |
| `mountain_mask` | Coarse elevation proxy | High elevation land selector | Local relief, high mountains vs plateaus, volcanic islands, snow mountains | Needs relief/slope/curvature classes. |
| `plateau_mask` | Coarse elevation band proxy | First pass elevated terrain | True plateaus, basins, hills, plains | Needs refined morphology. |
| `antarctica_ice_mask` | Antarctica land-ice supplement | Preventing Antarctica from being ocean/depth | Global glaciers, snowfields, sea ice | Polar land ice only. |
| `greenland_ice_mask` | Greenland land-ice supplement | Preventing Greenland interior from being ocean/depth | Global glaciers, mountain snow, sea ice | Polar land ice only. |
| `polar_land_ice_mask` | Union of Antarctica/Greenland supplements | Polar land/ocean correction | Complete cryosphere semantics | Not a glacier/snow layer. |
| 11 special sea water-only masks | Named water selectors for selected seas | Red Sea, Yellow Sea, East China Sea, Japan Sea, Mediterranean, Aegean, Caribbean, Persian Gulf, North Sea, Baltic Sea, South China Sea | Full bay/gulf/strait/marginal sea taxonomy | First batch only; requires parent/child/priority API rules. |

System conclusion: current B-6 masks form a useful foundation but not a global semantic layer. Missing classes include lakes, rivers, wetlands, deltas, islands, reefs, banks, vegetation, deserts, refined landforms, global cryosphere, and human-modified surfaces.

## 2. Global Structure Semantic Taxonomy

### A. Base Land / Ocean / Coast

Required semantics:

- `land_mask`
- `ocean_mask`
- `coastline_distance_mask`
- `coastal_zone_mask`
- `coastal_plain_mask`
- `estuary_coast_proxy`
- `cliff_or_steep_coast_proxy`
- `mangrove_coast_proxy`
- `delta_coast_proxy`

Priority regions:

- East China coast
- Japan coast
- Korean Peninsula
- Southeast Asia coasts
- Nile Delta coast
- Ganges-Brahmaputra Delta
- Amazon mouth
- Mississippi Delta
- Netherlands / North Sea coast
- Chile fjords
- Norway fjords

Assessment:

- Current coast support is broad only: land/ocean boundary and ocean-side distance.
- It does not distinguish deltas, estuaries, fjords, mangroves, cliffs, coastal plains, or heavily modified coasts.
- ETOPO1 can support rough steep coast and low coastal plain proxies; reliable deltas/mangroves require hydrology/landcover data.

Needed later: `coastal_zone_mask`, `coastal_plain_mask`, `delta_coast_proxy`, `estuary_mask`, fjord/steep coast proxies.

### B. Ocean / Sea / Shelf / Strait / Bay

Required semantics:

- `deep_ocean_mask`
- `mid_ocean_mask`
- `continental_shelf_mask`
- `shallow_sea_mask`
- `special_sea_water_mask`
- `bay_mask`
- `gulf_mask`
- `strait_mask`
- `marginal_sea_mask`
- `enclosed_sea_mask`
- `upwelling_coast_proxy`
- `ocean_bank_mask`

Priority regions:

- Red Sea
- Yellow Sea
- East China Sea
- Japan Sea
- South China Sea
- Mediterranean
- Aegean
- Caribbean
- Persian Gulf
- North Sea
- Baltic Sea
- Gulf of Mexico
- Bay of Bengal
- Hudson Bay
- Bering Sea
- Sea of Okhotsk
- Indonesian seas
- Malacca Strait
- Taiwan Strait
- Bosporus / Dardanelles
- Gibraltar Strait

Assessment:

- B-6.2S-1 is only the first batch of special sea selectors.
- Bay/strait/gulf/marginal/enclosed sea semantics are not yet fully modeled.
- Continuing ocean supplement work is useful, but not more important than inland water and terrain foundations.
- API must support parent/child/priority masks because Mediterranean/Aegean and Yellow/East China overlap by design.

Recommendation:

- Continue B-6.2S only after inland water and core taxonomy boundaries are clear.
- Bay/strait/gulf expansion should be B-6.2G-8, not mixed into lake or terrain work.

### C. Inland Water / Lakes / Reservoirs

Required semantics:

- `lake_mask_from_GSHHG_L2`
- `inland_water_mask`
- `large_lake_mask`
- `reservoir_mask`
- `seasonal_lake_mask`
- `salt_lake_mask`
- `lake_island_mask`
- `inland_water_distance_mask`

Priority regions:

- Caspian Sea
- Great Lakes
- Lake Baikal
- Lake Victoria
- Lake Tanganyika
- Lake Titicaca
- Aral Sea
- Lake Chad
- Qinghai Lake
- Dongting Lake
- Poyang Lake
- Taihu Lake
- Qiandao Lake

B-6.2G-1A conclusions to preserve:

- GSHHG h/L2 is usable for 2K lake masks.
- L2 must filter `area > 0`.
- Negative-area L2 river-lake widening zones must be excluded from lake masks.
- h/L3 can support lake island hole-punching.
- Implementation must use real L3 `parent_id -> L2 id` mapping.
- Taihu, Qiandao, Dongting, and Poyang are sub-threshold or absent at 2K and should not be hard failures.
- Aral Sea and Lake Chad have historical extent risks.

Assessment:

- Inland water should be the next implementation stage because current land semantics treat major lakes as ordinary land unless separately selected.
- Reservoirs, seasonal lakes, and wetlands need additional data or a separate proxy phase.

### D. Rivers / Deltas / Wetlands

Required semantics:

- `major_river_proxy`
- `river_delta_proxy`
- `estuary_mask`
- `floodplain_proxy`
- `wetland_mask`
- `marsh_mask`
- `seasonal_floodplain_proxy`

Priority regions:

- Yangtze River / Yangtze Delta
- Pearl River Delta
- Mekong Delta
- Nile Delta
- Amazon mouth
- Ganges-Brahmaputra Delta
- Mississippi Delta
- Pantanal
- Sudd
- Okavango Delta
- Amazon floodplain
- West Siberian wetlands

Assessment:

- WDBII rivers exist in the repository.
- WDBII rivers are polyline shapefiles, not filled polygons.
- Rivers must not be directly rasterized as filled water bodies.
- Rivers must not be mixed into B-6.2G-1B lake masks.
- No reliable wetland dataset is currently available.
- Delta masks can be proxied from river endpoints plus coast/lowland information, but that is a separate audit and validation problem.

Recommendation: create a separate river/delta/wetland proxy audit phase, B-6.2G-3.

### E. Terrain / Relief / Landform

Required semantics:

- `mountain_mask`
- `high_mountain_mask`
- `plateau_mask`
- `plateau_refined_mask`
- `hill_mask`
- `basin_mask`
- `valley_or_lowland_mask`
- `lowland_plain_mask`
- `coastal_plain_mask`
- `escarpment_proxy`
- `rift_valley_proxy`
- `volcanic_island_mask`
- `island_relief_mask`

Priority regions:

- Himalaya
- Tibetan Plateau
- Andes
- Rockies
- Alps
- Ethiopian Highlands
- East African Rift
- Iranian Plateau
- Anatolian Plateau
- Deccan Plateau
- Great Rift Valley
- Hawaii / volcanic island chains
- Japan mountain arcs
- Indonesia volcanic arcs
- New Zealand Alps
- Central Asian basins
- Amazon Basin
- Congo Basin
- North China Plain
- European Plain
- Mississippi Basin
- Sichuan Basin
- Tarim Basin

Assessment:

- Current `mountain_mask` and `plateau_mask` are coarse elevation proxies.
- ETOPO1 can support coarse terrain classes now.
- True relief taxonomy needs slope, local elevation range, curvature, relative height, and basin/plain logic.
- `pwa/assets/source/dem/copernicus_glo30/` is present but empty, so no usable high-resolution DEM exists in the repository.
- Texture color must not be treated as terrain semantic truth.

Recommendation: terrain/relief should be B-6.2G-2.

### F. Desert / Arid / Bare Land

Required semantics:

- `desert_mask`
- `arid_mask`
- `semi_arid_mask`
- `bare_rock_mask`
- `dune_field_mask`
- `salt_flat_mask`
- `dry_basin_mask`

Priority regions:

- Sahara
- Arabian Desert
- Gobi
- Taklamakan
- Australian interior
- Namib
- Kalahari
- Atacama
- Iranian Plateau drylands
- Central Asian deserts
- Great Basin
- Patagonia drylands
- Thar Desert

Assessment:

- No real desert/arid dataset is currently available.
- Source texture color can provide a visual proxy, but it is not structural truth.
- ETOPO1 can help identify basins and elevation context but not aridity.
- Robust desert/arid masks likely need MODIS/ESA WorldCover/Copernicus/Koppen/aridity-index style data.

Recommendation: desert/arid work should be a separate B-6.2G-4 phase. Do not hard-code it into B-6.2G-1B.

### G. Vegetation / Biome / Land Cover

Required semantics:

- `rainforest_mask`
- `forest_mask`
- `boreal_forest_mask`
- `grassland_mask`
- `savanna_mask`
- `tundra_mask`
- `shrubland_mask`
- `cropland_or_human_modified_mask`
- `urban_or_built_proxy`
- `mixed_vegetation_mask`

Priority regions:

- Amazon
- Congo Basin
- Southeast Asia rainforest
- Siberian taiga
- Canadian boreal forest
- African savanna
- Eurasian Steppe
- North American Great Plains
- Pampas
- Australian outback edge
- European agricultural plains
- North China Plain
- Indo-Gangetic Plain

Assessment:

- No usable global land cover or biome dataset is currently present.
- `pwa/assets/source/coastline/naturalearth/` exists but is empty.
- Without data, biome masks should not be hard-coded from texture color.
- Vegetation/biome remains essential for global visual semantics but should be B-6.2G-5 or deferred to B-7 / Phase C.

### H. Cryosphere / Glacier / Snow / Ice

Required semantics:

- `permanent_snow_mask`
- `glacier_mask`
- `icefield_mask`
- `ice_cap_mask`
- `seasonal_snow_proxy`
- `sea_ice_proxy`
- `polar_land_ice_mask`

Priority regions:

- Antarctica
- Greenland
- Himalaya glaciers
- Tibetan Plateau snow
- Alps
- Andes
- Alaska
- Canadian Arctic
- Svalbard
- Patagonia icefields
- Iceland
- New Zealand Southern Alps

Assessment:

- Current `antarctica_ice_mask` and `greenland_ice_mask` are polar land-ice correction masks, not a global glacier system.
- No global glacier dataset is available.
- ETOPO1 elevation can only support rough high-elevation snow/ice proxies.
- High elevation is not equivalent to glacier.
- Sea ice should not be inferred from static land/ocean masks.

Recommendation: cryosphere should be B-6.2G-6, with real glacier/snow/sea-ice data deferred until available.

### I. Island / Archipelago / Reef / Atoll / Bank

Required semantics:

- `small_island_mask`
- `island_proximity_mask`
- `tropical_island_group_mask`
- `archipelago_mask`
- `reef_or_atoll_proxy_mask`
- `shallow_bank_mask`
- `coral_sea_proxy`
- `volcanic_island_mask`
- `island_shelf_mask`

Priority regions:

- Maldives
- Tuamotu
- Bahamas Bank
- Belize Barrier Reef
- Great Barrier Reef
- Seychelles
- Chagos
- Marshall Islands
- Kiribati
- Micronesia / Palau
- Fiji / Tonga / Samoa
- Indonesia archipelago
- Philippines
- Caribbean islands
- Hawaii
- Galapagos
- Canary Islands
- Azores
- Japan islands
- Ryukyu Islands

Assessment:

- GSHHG L1 can support small-island and archipelago proxies if connected components and geodesic area are implemented.
- ETOPO1 can support coarse shallow bank proxies but is not enough for reef/atoll production quality.
- GEBCO Japan subset is regional benchmark only, not global reef/bank coverage.
- Global GEBCO and/or reef datasets should be deferred.

Recommendation: island/reef/bank should be B-6.2G-7.

### J. Human-Modified / Urban / Infrastructure Proxy

Required semantics:

- `urban_proxy`
- `cropland_or_human_modified_mask`
- `reservoir_mask`
- `port_coast_proxy`
- `nightlight_proxy`

Priority regions:

- Yangtze River Delta
- Pearl River Delta
- Tokyo Bay
- Seoul / Incheon
- North China Plain
- Indo-Gangetic Plain
- Nile Delta
- Western Europe
- US East Coast
- Great Lakes urban belt

Assessment:

- No confirmed VIIRS, OSM, or global urban dataset is currently available.
- Human-modified masks are relevant for RodiO's cultural/geographic color semantics, but they should not be mixed into B-6.2G-1B.
- Reservoir detection especially needs external hydro/human dataset or manual region work.

Recommendation: defer to B-6.2G-9 or Phase C.

## 3. Current Data Source Capability Audit

| Data Source | Currently Available? | Supports Now | Cannot Support | Suitable Phase | Risk |
| ----------- | -------------------- | ------------ | -------------- | -------------- | ---- |
| ETOPO1 Ice Surface | Yes: `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd` | Global elevation, broad bathymetry, terrain proxies, polar ice-surface supplement | Biomes, real glaciers, wetlands, rivers, reefs, modern lake extent | B-6.2G-2, broad ocean/depth | Coarse for reefs; ice surface not bedrock. |
| GSHHG L1-L6 | Yes | Land/ocean polygons, coastline, lakes, islands in lakes, small islands | Biomes, aridity, glaciers, reefs, modern reservoirs | B-6.2G-1, B-6.2G-7 | Old data; offsets; level semantics must be preserved. |
| GSHHG L2 | Yes | Lake polygons, large lakes, inland water foundation | Rivers, wetlands, reservoirs, seasonal lakes | B-6.2G-1 | Negative-area river-lake zones must be excluded. |
| GSHHG L3 | Yes | Lake island hole-punching | General land islands, rivers | B-6.2G-1 | Must use real `parent_id -> L2 id`; do not mix tiers. |
| WDBII rivers | Yes | Major river polyline proxy after separate audit | Filled lake masks, wetlands, true river width | B-6.2G-3 | Polyline only; no names; must buffer carefully. |
| WDBII borders | Yes | Political context if needed | Surface physical semantics | Not current B-6 priority | Should not drive physical masks. |
| GEBCO Japan subset | Yes | Regional benchmark around Japan / East Asia | Global reef/bank/shelf masks | RDL/regional validation | Not global. |
| Current day texture color classes | Yes as source image | Visual proxy and review | Structural truth for biomes/deserts/terrain | Review only | Color depends on source aesthetics. |
| Existing ocean masks | Yes in generated B-6 `.npz` | Broad ocean selectors and special seas | Inland water, biomes, reef quality | B-6 foundation | Incomplete semantics. |
| NaturalEarth directory | Present but empty | Nothing now | Biomes/water/urban until data added | Deferred | Placeholder only. |
| `dem/copernicus_glo30` directory | Present but empty | Nothing now | High-res terrain until data added | Deferred | Placeholder only. |
| RDL assets/scripts | Present | Regional bathymetry/coastline reference, Japan benchmarks | Global semantic masks by themselves | Reference / validation | Regional focus. |
| OSM assets | Not confirmed | Nothing now | Urban, roads, water, reservoirs | Deferred | Missing data. |
| VIIRS assets | Not confirmed | Nothing now | Nightlights, urban proxy | Deferred | Missing data. |
| Land cover / biome dataset | Not confirmed | Nothing now | Biome/desert/cropland truth | B-7 / Phase C | Missing data. |
| Glacier dataset | Not confirmed | Nothing now | Global glaciers / icefields | B-6.2G-6 deferred | Missing data. |
| Reef dataset | Not confirmed | Nothing now | Reef/atoll truth | B-6.2G-7 deferred | Missing data. |

## 4. Global Mask Roadmap

| Phase | Scope | Data Readiness | Implementation Readiness | Priority | Should Implement Now? | Dependencies | Validation Gate |
|---|---|---|---|---|---|---|---|
| B-6.2G-1 | Inland Water / Lake Masks: `lake_mask_from_GSHHG_L2`, `inland_water_mask`, `large_lake_mask`, `lake_island_mask`; rivers deferred | High for lakes using GSHHG L2/L3 | High after B-6.2G-1A R2 cleanup | P0 | Yes, next | GSHHG L2/L3, existing land mask, output safety | B-6.2G-1C validation: required lakes, watchlist, area filters, no river-lake merge. |
| B-6.2G-2 | Terrain / Relief / Landform Refinement | Medium using ETOPO1 | Medium | P0/P1 | After lakes | ETOPO1; slope/local relief methods | Region samples for Himalaya, Andes, Rockies, Tibet, plains, basins. |
| B-6.2G-3 | River / Delta / Wetland Proxy Audit | Medium for rivers, low for wetlands | Audit first | P1 | Not yet | WDBII river polylines; maybe extra wetland data | Verify polyline buffering, no lake merge, delta false positives. |
| B-6.2G-4 | Desert / Arid / Bare Land Masks | Low without external data | Low | P1 | No | Land cover/aridity source selection | Sahara/Arabia/Gobi/Atacama/Australia validation; proxy labeling. |
| B-6.2G-5 | Vegetation / Biome / Land Cover Masks | Low without data | Low | P1/P2 | No | MODIS/ESA/Copernicus/NaturalEarth or equivalent | Amazon/Congo/SEA/taiga/grassland/savanna validation. |
| B-6.2G-6 | Cryosphere / Glacier / Snow Masks | Low beyond polar masks | Low | P1/P2 | No | Glacier/snow/sea-ice data; ETOPO1 only for proxy | Antarctica/Greenland plus mountain glaciers; distinguish sea ice. |
| B-6.2G-7 | Island / Reef / Atoll / Bank Masks | Medium for islands, low for reefs | Medium for proxy | P0 for Noon Air visual | After lake/terrain foundation or in parallel audit | GSHHG L1 components, ETOPO1 shallow, later GEBCO/reef data | Maldives, Tuamotu, Bahamas, GBR, Hawaii, Caribbean. |
| B-6.2G-8 | Bay / Strait / Gulf / Marginal Sea Expansion | Medium using ocean mask + named bboxes | Medium | P2 | Not before lakes | Existing ocean/special sea masks, parent/child API | Malacca, Taiwan Strait, Gibraltar, Bosporus, Gulf of Mexico, Bay of Bengal. |
| B-6.2G-9 | Human-Modified / Urban / Cultural Geography Proxy | Low | Low | P3 | No | VIIRS/OSM/landcover or manual sources | Urban belts, deltas, croplands, ports; no production use without data. |

## 5. B-6.2G-1B Implementation Boundary

Is B-6.2G-1B ready?

Answer: Yes. B-6.2G-1A-R2 has resolved the remaining wording/count consistency issue. B-6.2G-1B must remain narrowly scoped.

Allowed in B-6.2G-1B:

- `lake_mask_from_GSHHG_L2`
- `inland_water_mask`
- `large_lake_mask`
- `lake_island_mask` / `lake_land_hole_mask`
- 2K prototype outputs only
- Output only under `d5b_processor_v3/d5b_output/structure_masks/`
- Metadata and metrics for lake masks
- Preview output only under ignored d5b output preview directory

Forbidden in B-6.2G-1B:

- Rivers
- Deltas
- Wetlands
- Terrain refinement
- Desert
- Vegetation / biome
- Glacier / snow
- Reef / island / bank
- Bay / strait / gulf expansion
- Human-modified masks
- d6 integration
- pwa / production / candidates writes
- generated output commits

Must be validated in B-6.2G-1C:

- All output masks shape/dtype/range/NaN/Inf.
- `area > 0` filtering confirmed.
- Negative-area river-lake zones excluded.
- L3 hole-punching uses real `parent_id -> L2 id` mapping.
- Required lake points: Caspian, Great Lakes, Baikal, Victoria, Tanganyika, Titicaca, Aral, Qinghai, Dongting, Poyang, Taihu, Qiandao.
- Watchlist behavior: Aral excluded/flagged, Lake Chad flagged, Titicaca/Qinghai not erased by feather, Taihu/Qiandao/Dongting/Poyang handled as sub-threshold or absent without hard failure.
- Generated masks remain ignored and uncommitted.

## 6. API / d6 / Visual Pipeline Boundary

- B-6.4 API can be drafted, but must not be frozen.
- API must support optional masks, missing masks, future masks, mask groups, priority, parent-child relationships, mask versioning, provenance, and per-mask limitations.
- d6 must not be touched.
- B-6.5 refactor plan has not started.
- B-6.6 visual rebuild has not started.
- B-6.7 8K candidate gate has not started.
- B-5.3 visual patch must not resume.
- `DAY_TEXTURE_VARIANT = d5z_b` and production texture must not be changed.

## 7. Git Safety Audit

Current `git status --short` at audit start:

```text
 M d5b_processor_v3/d6_noon_air_earth_generator.py
 M devlog.md
?? docs/phase_b6_2g_1a_inland_water_asset_feasibility_audit.md
?? docs/phase_b6_2g_global_surface_feature_taxonomy_gap_audit.md
?? docs/phase_b6_2s_1a_special_sea_mask_validation_audit.md
?? previews/e1_r4a_d5b_design_v3_2_1/
?? previews/e1_r4a_d5b_design_v3_2_1_rerun/
?? previews/e1_r4b_d5z_on_globe_preview/
?? previews/e1_r5_full_acceptance/
?? previews/e1_r6_production_deployment_verification/
?? previews/rdl_v2_global_data_source_upgrade_audit/
?? previews/rdl_v2_japan_visual_retuning/
?? previews/rdl_v2_japan_visual_tile_prototype/
?? previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/
?? previews/regional_detail_mvp_japan_eastsea/
?? previews/regional_detail_mvp_japan_eastsea_v2_audit/
```

Safe-to-consider docs:

- `docs/phase_b6_2g_1a_inland_water_asset_feasibility_audit.md`
- `docs/phase_b6_2g_global_surface_feature_taxonomy_gap_audit.md`
- `docs/phase_b6_2s_1a_special_sea_mask_validation_audit.md`
- `docs/phase_b6_2g_sys_global_structure_semantic_layer_system_audit.md`

Unsafe-to-commit files:

- `d5b_processor_v3/d6_noon_air_earth_generator.py` unless separately reviewed and explicitly approved.
- Root `previews/` directories.
- Any generated `d5b_processor_v3/d5b_output/` masks, metadata, metrics, or previews.
- Any `pwa/assets/earth/production/` or `pwa/assets/earth/candidates/` output.

Files requiring diff review:

- `devlog.md`
- `d5b_processor_v3/d6_noon_air_earth_generator.py`
- All new docs before commit.

Recommended commit strategy:

1. Do not commit in this audit turn.
2. Later, create a docs-only commit for reviewed B-6 audit docs.
3. Exclude d6, devlog, previews, generated masks, and pwa assets unless explicitly approved.
4. Do not push until user authorizes.

## 8. Final Verdict

| Question | Answer |
| -------- | ------ |
| Is current B-6 structure layer globally complete? | No |
| Are global landform / surface feature gaps fully preserved in roadmap? | Yes |
| Is B-6.2G-1A clean enough after R2? | Yes — B-6.2G-1A-R2 has resolved the remaining wording/count consistency issue. |
| Can B-6.2G-1B start? | Yes |
| Should B-6.2G-1B be limited to inland water / lake masks only? | Yes |
| Should terrain / relief be separate B-6.2G-2? | Yes |
| Should river / delta / wetland be separate B-6.2G-3? | Yes |
| Should desert / arid be separate B-6.2G-4? | Yes |
| Should vegetation / biome be separate B-6.2G-5 or deferred? | Yes |
| Should cryosphere be separate B-6.2G-6? | Yes |
| Should island / reef / bank be separate B-6.2G-7? | Yes |
| Can d6 be touched? | No |
| Can pwa / production / candidates be touched? | No |
| Can B-6.4 API be frozen? | No |
| Can B-5.3 visual patch resume? | No |
| Is git state safe for implementation? | Conditional: only after isolating docs and leaving existing d6/devlog/previews untouched |

## 9. Next Step

Next smallest safe action:

1. B-6.2G-1A-R2 has resolved the remaining wording/count consistency issue.
2. Proceed to B-6.2G-1B only under strict lake / inland water scope, then run B-6.2G-1C validation audit.
