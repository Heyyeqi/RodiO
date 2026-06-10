# Phase B-6.2G Global Surface Feature Taxonomy & Gap Audit

Date: 2026-06-10

Scope: planning and gap audit only. This document does not modify code, does not regenerate masks, does not run d6, does not write to `pwa`, `production`, or `candidates`, and does not commit or push.

## 0. Current State

B-6 currently has a useful but incomplete global structure layer. The latest generated `.npz` contains 23 masks:

- `land_mask`
- `ocean_mask`
- `deep_ocean_mask`
- `mid_ocean_mask`
- `continental_shelf_mask`
- `shallow_sea_mask`
- `coastline_distance_mask`
- `antarctica_ice_mask`
- `greenland_ice_mask`
- `polar_land_ice_mask`
- `mountain_mask`
- `plateau_mask`
- 11 special sea water-only masks:
  - `red_sea_water_mask`
  - `yellow_sea_water_mask`
  - `east_china_sea_water_mask`
  - `japan_sea_water_mask`
  - `mediterranean_water_mask`
  - `aegean_sea_water_mask`
  - `caribbean_water_mask`
  - `persian_gulf_water_mask`
  - `north_sea_water_mask`
  - `baltic_sea_water_mask`
  - `south_china_sea_water_mask`

This is not yet a complete global surface structure layer. It covers global land/ocean separation, broad ocean depth classes, rough terrain elevation classes, polar land-ice supplements, and selected named seas. It does not yet represent inland lakes, rivers, wetlands, vegetation biomes, deserts/arid classes, global glaciers, detailed relief, islands, reefs, banks, or coastal ecological structures.

## 1. Global Missing Feature Classes

### A. Inland Water

Missing masks:

- `large_lake_mask`
- `inland_water_mask`
- `reservoir_mask`
- `seasonal_lake_mask`
- `wetland_mask`
- `river_major_mask`
- `river_delta_mask`

Priority regions:

- Caspian Sea
- Great Lakes
- Lake Baikal
- Lake Victoria
- Lake Tanganyika
- Lake Titicaca
- Aral Sea
- Qinghai Lake
- Dongting Lake
- Poyang Lake
- Taihu Lake
- Qiandao Lake
- Mekong Delta
- Nile Delta
- Amazon mouth
- Ganges-Brahmaputra Delta
- Mississippi Delta

Current capability:

- GSHHG L2 lake polygons are present and can support a first `lake_mask_from_GSHHG_L2`.
- GSHHG L3/L4/L5/L6 are present and can preserve islands-in-lakes and ponds-in-islands semantics if implemented carefully.
- WDBII rivers are present and can support a coarse `major_river_proxy`, especially using river levels 1-3 first.
- Current `land_mask` uses GSHHG L1 land only plus polar supplement. It does not subtract lakes from land, so major inland water bodies are currently treated as land unless separately masked later.

Gap:

- Reservoirs, seasonal lakes, wetlands, deltas, and modern hydrological variability are not reliably covered by GSHHG/WDBII alone.
- WDBII is old and line-based; it can support visual/selector proxies, not high-confidence hydrology.
- Deltas need either river endpoint logic, land cover/wetland data, or manual regional masks.

Verdict: inland water is the highest-priority missing global class because current land/ocean semantics hide major lakes and deltas inside land.

### B. Vegetation / Biome

Missing masks:

- `rainforest_mask`
- `forest_mask`
- `boreal_forest_mask`
- `grassland_mask`
- `savanna_mask`
- `tundra_mask`
- `shrubland_mask`
- `cropland_or_human_modified_mask`

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

Current capability:

- There is no confirmed global land cover or biome dataset in the repository.
- `pwa/assets/source/coastline/naturalearth/` exists but is empty.
- `pwa/assets/source/dem/copernicus_glo30/` exists but is empty.
- The day source texture could provide RGB/HSL proxies, but texture color is not a stable structure dataset.

Potential data sources for later phases:

- MODIS land cover
- ESA WorldCover
- Copernicus Global Land Cover
- Natural Earth biome/ecoregion layers, if added
- WWF ecoregions or similar thematic data, if licensing and resolution are acceptable

Verdict: vegetation/biome masks cannot be built reliably from current assets. RGB texture proxies may help aesthetic review but should not be promoted as structure masks.

### C. Desert / Arid / Bare Land

Missing masks:

- `desert_mask`
- `arid_mask`
- `semi_arid_mask`
- `bare_rock_mask`
- `dune_field_mask`

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

Current capability:

- ETOPO1 can provide elevation context but not aridity.
- Source texture color can identify tan/bare areas, but that is not a true structure mask.
- Existing older scripts contain RGB desert heuristics, but those are visual/color proxies, not a global physical mask.

Gap:

- No global aridity, land cover, or biome dataset is currently available.
- Deserts and dry grasslands are easy to confuse if relying on color alone.
- Snow, salt flats, dry lake beds, and bare rock can false-positive under simple RGB rules.

Verdict: desert/arid masks are important for Noon Air land color stability, but should wait for either land cover/aridity data or a clearly labeled proxy phase.

### D. Cryosphere

Missing masks:

- `permanent_snow_mask`
- `glacier_mask`
- `icefield_mask`
- `ice_cap_mask`
- `seasonal_snow_proxy`
- `sea_ice_proxy`

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

Current capability:

- `antarctica_ice_mask`, `greenland_ice_mask`, and `polar_land_ice_mask` exist.
- These masks are polar land/ice supplements derived from ETOPO1 Ice and bbox/latitude logic.
- They solve the previous Antarctica land/ocean critical issue, but they are not a global glacier/snow system.

Gap:

- No global glacier inventory is available in the repository.
- No seasonal snow product is available.
- No sea ice product is available.
- Mountain snow requires distinguishing snow/ice from clouds, salt flats, deserts, and bright bare rock.

Verdict: current polar masks are necessary but not sufficient. Global cryosphere work should be a separate phase and should not be inferred from ETOPO1 elevation alone except as a low-confidence proxy.

### E. Terrain / Relief

Current masks:

- `mountain_mask`
- `plateau_mask`

Missing or underdeveloped masks:

- `high_mountain_mask`
- `hill_mask`
- `basin_mask`
- `valley_or_lowland_mask`
- `escarpment_proxy`
- `volcanic_island_mask`

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

Current capability:

- ETOPO1 is present globally and can support elevation classes.
- Current `mountain_mask` and `plateau_mask` are coarse threshold masks.

Gap:

- Current plateau semantics are too broad and can flag deserts or elevated basins without real plateau morphology.
- There is no slope/local relief analysis yet.
- There is no basin/valley/hill separation.
- Volcanic islands require small-island structure plus elevation/relief profile, not elevation alone.

Verdict: terrain refinement is feasible with current ETOPO1 but should be designed as a clear relief taxonomy, not just more elevation thresholds.

### F. Coastal / Island / Reef / Bank

Missing masks:

- `small_island_mask`
- `island_proximity_mask`
- `tropical_island_group_mask`
- `reef_or_atoll_proxy_mask`
- `shallow_bank_mask`
- `mangrove_coast_proxy`
- `delta_coast_proxy`

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

Current capability:

- GSHHG can support small island detection if connected components and geodesic area are implemented.
- ETOPO1 shallow/depth classes can support broad banks and shelves but are too coarse for many reefs.
- Japan-only GEBCO exists and is useful as a regional quality reference, not global coverage.

Gap:

- No global GEBCO dataset is present.
- No global coral reef or atoll dataset is present.
- ETOPO1 cannot reliably capture Maldives, Tuamotu, Bahamas Bank, Great Barrier Reef, or narrow reef shelves at production quality.
- Mangroves and delta coasts require land cover or specialized coastal ecology data.

Verdict: reef/island/bank is the most important missing ocean-adjacent class for Noon Air visual quality, but much of it must be proxy-labeled or deferred until better global bathymetry/reef data exists.

## 2. Current Data Source Capability Audit

| Data Source | Currently Available? | Can Support | Cannot Support |
| ----------- | -------------------- | ----------- | -------------- |
| ETOPO1 Ice grid | Yes: `pwa/assets/source/bathy/ETOPO1_Ice_g_gdal.grd`, about 890M | Global topography, broad bathymetry, terrain classes, polar ice-surface proxy, broad shallow/deep ocean classes | Biomes, real glaciers, wetlands, rivers, reefs, modern lakes/reservoirs, high-confidence reef banks |
| GSHHG L1-L6 | Yes: `pwa/assets/source/coastline/gshhg/GSHHS_shp/{c,l,i,h,f}` | Land polygons, lake polygons, islands in lakes, ponds, coastline, small island polygons, inland water foundation | Biomes, aridity, vegetation, glaciers, reef ecology, modern reservoirs/seasonal lakes |
| WDBII rivers / borders | Yes: `pwa/assets/source/coastline/gshhg/WDBII_shp/`, river levels present | Major river proxy, river-lake proxy, coarse river network, delta seed points with extra logic | Modern hydrology, river width/seasonality, wetlands, reservoirs, accurate deltas |
| GEBCO Japan subset | Yes: `pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc`, about 46M | Japan/East Asia benchmark, regional comparison, GEBCO pipeline testing | Global shelf/bank/reef masks |
| Existing ocean masks | Yes in generated B-6 `.npz` | Ocean selectors, special seas, broad depth classes | Inland water, biomes, desert, global reef detail |
| Source day texture color classes | Yes: `earth_day_source_21600x10800.jpg` | Visual proxies, review comparisons, potential low-confidence RGB masks | Auditable physical structure masks; stable biomes; true hydrology |
| Copernicus GLO30 directory | Directory exists but empty | Nothing currently | DEM replacement, slope/relief refinement until data is added |
| Natural Earth directory | Directory exists but empty | Nothing currently | Landcover/biome/coarse water until data is added |
| RDL / GEBCO / GSHHG scripts | Yes under `scripts/geo/` and B-6 generator | Implementation references for rasterization, regional bathymetry, previews | Does not provide missing global datasets by itself |
| VIIRS / OSM assets | No confirmed global asset found | None currently | Urban/human, reservoirs, roads/rivers, land use |

Key answers:

- GSHHG L2 can support `lake_mask` / `large_lake_mask` and should be the next immediate candidate.
- WDBII rivers can support a coarse `major_river_proxy`, but it should be marked proxy and reviewed carefully.
- ETOPO1 can support terrain class refinement, but not vegetation, aridity, wetlands, rivers, or reefs.
- Current repository does not contain a usable global land cover / biome dataset.
- Current repository does not contain a usable global glacier dataset.
- Current repository does not contain a usable global reef dataset.

## 3. Mask Roadmap

### B-6.2G-1 — Inland Water Masks

Goal: fix the largest semantic gap in current land/ocean structure: major lakes and inland water currently sit inside land.

Recommended order:

1. `lake_mask_from_GSHHG_L2`
2. `large_lake_mask`
3. `inland_water_mask`
4. `lake_island_mask` from GSHHG L3
5. `major_river_proxy` from WDBII river L01-L03, if line rasterization is acceptable
6. `river_delta_proxy`, deferred unless a clear method is defined
7. `reservoir_mask`, `seasonal_lake_mask`, `wetland_mask`, deferred pending new data

Implementation status: feasible now for lakes; proxy only for major rivers; defer deltas/wetlands/reservoirs.

### B-6.2G-2 — Terrain / Relief Refinement

Goal: improve terrain control beyond coarse `mountain_mask` / `plateau_mask`.

Recommended order:

1. `high_mountain_mask`
2. `plateau_refined_mask`
3. `hill_mask`
4. `basin_lowland_mask`
5. local relief / slope auxiliary metrics

Implementation status: feasible now with ETOPO1. Reliability is moderate due to 1 arc-min smoothing.

### B-6.2G-3 — Desert / Arid Masks

Goal: establish stable dryland controls for Sahara, Arabia, Gobi, Taklamakan, Australian interior, Namib, Kalahari, Atacama, and Central Asian deserts.

Recommended order:

1. Audit whether any usable landcover/aridity source can be added.
2. If not, define explicit `desert_proxy_mask` as a temporary RGB/region/elevation composite.
3. Avoid calling texture-color masks physical structure masks.

Implementation status: needs external land cover/aridity data for robust global masks.

### B-6.2G-4 — Vegetation / Biome Masks

Goal: build forest/rainforest/grassland/savanna/tundra/shrubland/cropland selectors.

Recommended order:

1. Asset/data-source audit for MODIS, ESA WorldCover, Copernicus Land Cover, or Natural Earth alternatives.
2. Add `forest_mask`, `rainforest_mask`, `grassland_mask`, `savanna_mask`, `tundra_mask` only after source selection.
3. Use source texture RGB only as review/proxy, not as canonical structure.

Implementation status: defer to B-7 or Phase C unless a dataset is added.

### B-6.2G-5 — Cryosphere Masks

Goal: extend beyond Antarctica/Greenland land-ice to global snow/glacier/icefield selectors.

Recommended order:

1. `high_elevation_snow_proxy` only if clearly labeled proxy.
2. Audit global glacier inventories before true `glacier_mask`.
3. Keep `sea_ice_proxy` separate from land ice; do not infer modern sea ice from ETOPO1.

Implementation status: polar land ice exists; global cryosphere needs new data.

### B-6.2G-6 — Reef / Island / Bank Masks

Goal: address Noon Air's known weak points: islands, reefs, banks, atolls, and shallow coastal aesthetics.

Recommended order:

1. `small_island_mask` from GSHHG connected components.
2. `island_proximity_mask` from distance transform around small island polygons.
3. `shallow_bank_mask` from ETOPO1 shallow + named regions, clearly marked proxy.
4. `bahamas_bank_mask` proxy, with GEBCO/global reef data deferred.
5. `reef_or_atoll_proxy_mask` using island proximity + shallow anomaly + tropical band + known island groups.

Implementation status: proxy feasible now; production-grade reef/bank requires global GEBCO and/or reef datasets.

## 4. Proposed Mask Implementation Table

| Proposed Mask | Category | Priority | Current Data Enough? | Method | Reliability | Implement Now? | Needs New Data? | Risk |
| ------------- | -------- | -------- | -------------------- | ------ | ----------- | -------------- | --------------- | ---- |
| `lake_mask_from_GSHHG_L2` | Inland water | P0 | Yes | Rasterize GSHHG L2 lake polygons to 2K/8K; subtract/track L3 islands if needed | High for large lakes | Yes | No | GSHHG age/offset, lake islands semantics |
| `large_lake_mask` | Inland water | P0 | Yes | Area-filter GSHHG L2 polygons; include Caspian/Great Lakes/Baikal/Victoria/etc. | High for major lakes | Yes | No | Area threshold must be geodesic |
| `inland_water_mask` | Inland water | P0 | Partial | Union GSHHG L2 plus selected river-lake features | Medium | Yes, scoped | No for lakes; yes for wetlands/reservoirs | Over/under-inclusion |
| `major_river_proxy` | Inland water | P1 | Partial | Rasterize WDBII river L01-L03 lines with pixel-width buffers | Medium-low | Audit first | Better hydro data later | Line width not physical |
| `river_delta_proxy` | Inland water/coastal | P2 | No | Combine river endpoints, coast distance, lowland, named regions | Low | No | Yes | False deltas, bbox artifacts |
| `wetland_mask` | Inland water/biome | P2 | No | Land cover/wetland dataset | High if data exists | No | Yes | Texture color false positives |
| `high_mountain_mask` | Terrain | P0 | Yes | ETOPO1 elevation > 3000m or region-tuned threshold | Medium-high | Yes | No | Misses lower rugged ranges |
| `plateau_refined_mask` | Terrain | P1 | Yes | Elevation + low local relief; optionally named plateaus | Medium | Yes | No | Needs local relief computation |
| `hill_mask` | Terrain | P1 | Yes | Elevation/local relief bands | Medium | Yes | No | ETOPO1 smoothing |
| `basin_lowland_mask` | Terrain | P2 | Partial | Low elevation inland + relief context | Medium-low | Audit first | Maybe | Semantic ambiguity |
| `desert_mask` | Desert/arid | P0 for Noon Air | No | Prefer land cover/aridity; proxy only if RGB+region+land | Medium with data, low as proxy | No as canonical | Yes | Confuses bare rock/salt/snow |
| `arid_mask` | Desert/arid | P1 | No | Aridity/land cover dataset | Medium-high with data | No | Yes | Dry grassland confusion |
| `semi_arid_mask` | Desert/arid | P2 | No | Land cover/aridity | Medium | No | Yes | Blurry semantic class |
| `forest_mask` | Vegetation | P1 | No | MODIS/ESA/Copernicus land cover | High with data | No | Yes | Seasonal/source mismatch |
| `rainforest_mask` | Vegetation | P1 | No | Land cover + tropical humid class | High with data | No | Yes | Cloud/color proxy failures |
| `grassland_mask` | Vegetation | P2 | No | Land cover | High with data | No | Yes | Savanna/steppe overlap |
| `savanna_mask` | Vegetation | P2 | No | Land cover/ecoregions | Medium-high with data | No | Yes | Regional variability |
| `tundra_mask` | Vegetation/cryo | P2 | No | Land cover/ecoregions | Medium-high with data | No | Yes | Seasonal snow ambiguity |
| `glacier_mask` | Cryosphere | P1 | No | Global glacier inventory | High with data | No | Yes | Bright-source proxy unreliable |
| `permanent_snow_mask` | Cryosphere | P2 | Partial | High elevation + source brightness proxy | Low-medium | Proxy only | Yes for reliable | Clouds/salt/snow confusion |
| `sea_ice_proxy` | Cryosphere/ocean | P2 | No | Seasonal sea ice dataset or review proxy | Low without data | No | Yes | Strong seasonality |
| `small_island_mask` | Coastal/island | P0 for Noon Air | Yes | Connected components from GSHHG L1; geodesic area threshold | Medium-high | Yes | No | 2K subpixel islands |
| `island_proximity_mask` | Coastal/island | P0 for Noon Air | Yes | Distance transform around `small_island_mask` | Medium | Yes | No | Equirectangular distance distortion |
| `tropical_island_group_mask` | Coastal/island | P1 | Partial | Island proximity + lat band + named groups | Medium | Proxy only | Better group data optional | Manual grouping bias |
| `shallow_bank_mask` | Coastal/bank | P0 for Noon Air | Partial | ETOPO1 shallow + special regions + ocean mask | Medium-low | Proxy only | Global GEBCO recommended | Misses Bahamas/GBR detail |
| `reef_or_atoll_proxy_mask` | Reef | P0 for Noon Air | Partial | Tropical small island proximity + shallow anomaly + anchors | Low-medium | Proxy only | Yes for production-grade | False circles/bands if overused |
| `mangrove_coast_proxy` | Coastal ecology | P2 | No | Land cover/coastal ecology dataset | Medium with data | No | Yes | Not derivable from ETOPO1 |
| `delta_coast_proxy` | Coastal/inland water | P1 | Partial | River mouths + lowland + coastline distance + named deltas | Low-medium | Audit first | Better hydro/landcover | Bbox artifacts |

Noon Air importance ranking:

1. Inland water/lakes: prevents major lakes from being treated as ordinary land.
2. Island/proximity/bank/reef proxies: directly addresses Maldives, Bahamas, Tuamotu, Hawaii, Caribbean, GBR visual failures.
3. Desert/arid masks: stabilizes land color in Sahara/Arabia/Gobi/Australia/Atacama.
4. Terrain refinement: improves mountains/plateaus without adding new datasets.
5. Vegetation/biome and cryosphere: important but data-dependent.

## 5. Impact on Current B-6.2S

1. Should B-6.2S-2 continue immediately?
   Answer: Conditional. B-6.2S-2 should not continue as "more ocean masks only" until inland water is scheduled. If B-6.2S-2 remains shelf/bank work, it should explicitly acknowledge B-6.2G-1 as a parallel or preceding dependency.

2. Should inland water masks happen before more ocean supplements?
   Answer: Yes. `lake_mask_from_GSHHG_L2`, `large_lake_mask`, and `inland_water_mask` are the next smallest high-confidence improvement using current data.

3. Should B-6.2S be split from land supplements?
   Answer: Yes. Keep B-6.2S as ocean/special-sea/shelf supplements. Add a separate land/water/terrain supplement track, for example:
   - B-6.2G-1 Inland Water
   - B-6.2T Terrain / Relief
   - B-6.2L Land Cover / Biome, data-dependent

4. Should B-6.4 API freeze pause?
   Answer: Yes. Do not freeze the API yet. API draft can proceed, but it must remain flexible for optional/future masks.

5. Must the API support optional/missing/future masks?
   Answer: Yes. The structure layer is incomplete and will expand. API consumers must handle missing masks, unknown mask versions, mask groups, priorities, and dependencies.

6. Is d6 still forbidden?
   Answer: Yes. d6 integration should remain blocked until the API can represent optional masks and until inland water/island-bank priorities are resolved.

## 6. Final Recommendation

```text
Final Recommendation:
- Is current B-6 structure layer globally complete? No.
- Biggest missing feature classes:
  inland water/lakes/rivers/deltas; vegetation/biomes; desert/arid/bare land; global glaciers/snow/sea ice; refined terrain/relief; islands/reefs/banks/coastal ecology.
- Highest priority next action:
  B-6.2G-1 Inland Water Masks using GSHHG L2/L3 first, with WDBII major rivers only as a reviewed proxy.
- Should implement inland water masks before more ocean supplements?
  Yes. Major lakes and inland waters are currently a fundamental semantic gap.
- Should commit current audit docs first?
  Yes. Commit docs before more implementation, but do not commit generated masks/previews or d6 changes unless explicitly approved.
- Can proceed to B-6.4 API draft?
  Yes, but not API freeze and not runtime integration. The draft must support optional/future masks, mask groups, parent/child priority, and missing-mask behavior.
- Can integrate d6?
  No.
- Can resume B-5.3 visual patch?
  No.
```

## 7. Next Smallest Safe Action

Create a B-6.2G-1 implementation plan for inland water only:

- audit GSHHG L2/L3/L4 semantics and shapefile attributes;
- define `lake_mask_from_GSHHG_L2`, `large_lake_mask`, and `inland_water_mask`;
- decide whether `land_mask` remains pure land or whether `surface_land_mask` / `inland_water_mask` semantics need separation;
- define validation points for Caspian, Great Lakes, Baikal, Victoria, Tanganyika, Titicaca, Aral, Qinghai, Dongting, Poyang, Taihu, Mekong Delta, Nile Delta, Amazon mouth, Ganges-Brahmaputra Delta, and Mississippi Delta;
- keep WDBII rivers as a separate proxy audit, not bundled into lake masks.
