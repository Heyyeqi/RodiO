# Phase B-6.2G-3A River / Delta / Wetland Feasibility Audit

Stage: B-6.2G-3A  
Type: Asset / Feasibility Audit  
Date: 2026-06-10  
Scope: read-only audit plus planning document

This audit does not implement new masks. It does not run the structure mask generator, d6, calibration, full-res generation, or any visual rebuild. It does not write to `pwa/`, `production/`, or `candidates/`.

## 1. Current Related Structure Layer Recap

The current B-6 structure layer already has useful base and terrain semantics:

- `land_mask` / `ocean_mask`
- `coastline_distance_mask`
- `lake_mask_from_GSHHG_L2`
- `inland_water_mask`
- `large_lake_mask`
- `lake_island_mask`
- `high_mountain_mask`
- `plateau_refined_mask`
- `lowland_or_basin_proxy`
- `hill_or_relief_proxy`

These masks give RodiO a stronger base than the old RGB / luminance / bbox route, but the hydrology semantic layer is still incomplete. The following masks are not yet available:

- `major_river_proxy`
- `river_delta_proxy`
- `estuary_mask`
- `floodplain_proxy`
- `wetland_mask`
- `marsh_mask`
- `seasonal_floodplain_proxy`

This matters because rivers, deltas, floodplains, and wetlands influence visual color application differently from lakes, oceans, terrain, or generic lowland masks. They should not be inferred from source texture color, broad lowland elevation, or bbox patches.

## 2. WDBII Rivers Asset Audit

Read-only inspection found WDBII river shapefiles under:

`pwa/assets/source/coastline/gshhg/WDBII_shp/`

All five tiers are present:

- `c`
- `l`
- `i`
- `h`
- `f`

Each tier contains river levels `L01` through `L11`. The `h` tier is the practical first choice for a 2K prototype because it is detailed enough for validation while avoiding the heavier full tier.

| Tier | Levels Present | Shape Type | Fields | Name Field? | L01 Count | Readable? |
| ---- | -------------- | ---------- | ------ | ----------- | --------: | --------- |
| `c` | L01-L11 | Polyline, type 3 | `id`, `level` | no | 55 | yes |
| `l` | L01-L11 | Polyline, type 3 | `id`, `level` | no | 55 | yes |
| `i` | L01-L11 | Polyline, type 3 | `id`, `level` | no | 55 | yes |
| `h` | L01-L11 | Polyline, type 3 | `id`, `level` | no | 55 | yes |
| `f` | L01-L11 | Polyline, type 3 | `id`, `level` | no | 55 | yes |

The `h` tier counts are:

| Level | Count | Shape Type | Fields |
| ----- | ----: | ---------- | ------ |
| L01 | 55 | Polyline, type 3 | `id`, `level` |
| L02 | 2371 | Polyline, type 3 | `id`, `level` |
| L03 | 4410 | Polyline, type 3 | `id`, `level` |
| L04 | 7499 | Polyline, type 3 | `id`, `level` |
| L05 | 8923 | Polyline, type 3 | `id`, `level` |
| L06 | 244 | Polyline, type 3 | `id`, `level` |
| L07 | 873 | Polyline, type 3 | `id`, `level` |
| L08 | 964 | Polyline, type 3 | `id`, `level` |
| L09 | 105 | Polyline, type 3 | `id`, `level` |
| L10 | 92 | Polyline, type 3 | `id`, `level` |
| L11 | 240 | Polyline, type 3 | `id`, `level` |

Important boundary conclusion:

WDBII rivers are line geometry, not filled water polygons. They cannot be directly rasterized as a filled water mask. Any 2K river mask must be explicitly treated as a buffered line proxy, not a true river-width or floodplain dataset.

## 3. River Proxy Design Feasibility

WDBII rivers can support a conservative river proxy prototype.

| Candidate Mask | Feasibility | Method | Reliability | Notes |
| -------------- | ----------- | ------ | ----------- | ----- |
| `major_river_proxy` | conditional yes | Rasterize WDBII `h` L01 lines, optionally L02 after validation | medium for global corridors | Should be a proxy flag, not true water extent |
| `river_buffer_proxy` | conditional yes | Dilate rasterized L01 or L01+L02 lines by a small pixel radius | medium | Required because 2K line width is otherwise too thin |
| `river_mouth_proxy` | experimental | Detect river endpoints near coastline and buffer locally | low-medium | Useful for future estuary planning, but easy to misclassify |
| `estuary_proxy` | weak / defer by default | Combine river mouth candidate with coastline distance and lowland | low | Not a real estuary dataset |

2K major rivers are meaningful only as visual / semantic corridors. They should not be interpreted as accurate water width. A draft prototype should start with `h/L01` only, or at most `h/L01 + h/L02` after a validation check. Lower levels should not be included by default because they may create excessive noise and over-dense inland line texture.

Recommended draft constraints for B-6.2G-3B if it proceeds:

- Use WDBII `h` tier first.
- Start with L01 major rivers.
- Consider L02 only as an optional second output or validation variant.
- Use a small documented buffer / dilation radius, likely 1-3 px at 2048x1024.
- Clip the proxy to land semantics unless generating a separate river-mouth / estuary proxy.
- Keep river proxy separate from lake and inland-water masks.
- Give lake and inland-water masks higher priority than river proxy.
- Mark all outputs as `proxy`, not data-derived filled hydrology.

## 4. Delta / Estuary / Wetland Data Feasibility

Current repository assets do not provide enough data for true delta, wetland, floodplain, marsh, or mangrove masks.

| Feature Class | Current Data Available? | Feasibility Now | Reason |
| ------------- | ----------------------- | --------------- | ------ |
| Deltas | no dedicated data found | defer | WDBII line endpoints are not delta polygons |
| Estuaries | no dedicated data found | weak proxy only | Could infer approximate mouths, but not true estuary extent |
| Wetlands | no wetland dataset found | defer | Requires land cover / wetland data |
| Floodplains | no floodplain dataset found | defer | Lowland terrain is insufficient as structural truth |
| Marshes | no marsh dataset found | defer | Requires land cover / wetland data |
| Mangrove coast | no mangrove dataset found | defer | Needs external mangrove / land cover source |

Asset observations:

- `pwa/assets/source/coastline/naturalearth/` exists but no usable files were found in the read-only scan.
- `pwa/assets/source/dem/copernicus_glo30/` exists but no usable files were found.
- ETOPO1 and GSHHG / WDBII are present, but they do not provide true wetlands or deltas.
- No OSM, VIIRS, global land-cover, wetland, mangrove, or floodplain dataset was found in the scanned source assets.
- Existing day texture color classes must not be treated as structural truth.

Known-region bbox lists could be useful for review checklists, but they should not become formal structure masks. Using bbox as structure truth would repeat the same failure mode that B-6 was designed to eliminate.

## 5. Key Region Audit

### Major Rivers

| Region | Current Data Coverage | Validation Role | Feasibility Judgment |
| ------ | --------------------- | --------------- | -------------------- |
| Yangtze River | likely WDBII L01/L02 line coverage, no name field | hard or watchlist by bbox sample | usable as corridor proxy if spatially validated |
| Yellow River | likely WDBII line coverage | watchlist | may need L02; do not assume name-based selection |
| Pearl River | likely WDBII line coverage | watchlist | delta complexity requires separate phase |
| Mekong River | likely WDBII line coverage | hard/watchlist | suitable major-river corridor check |
| Nile River | likely WDBII line coverage | hard | suitable major-river corridor check |
| Amazon River | likely WDBII line coverage | hard | suitable major-river corridor check |
| Mississippi River | likely WDBII line coverage | hard | suitable major-river corridor check |
| Ganges / Brahmaputra | likely WDBII line coverage | watchlist | delta and distributary complexity deferred |
| Danube | likely WDBII line coverage | hard/watchlist | suitable European corridor check |
| Volga | likely WDBII line coverage | hard/watchlist | suitable corridor check |
| Congo River | likely WDBII line coverage | hard | suitable corridor check |
| Ob / Yenisei / Lena | likely WDBII line coverage | hard/watchlist | suitable high-latitude corridor checks |

Because WDBII river files have no `name` field, implementation and validation cannot rely on river names inside the shapefile. Region checks must use geographic sample points, bbox coverage, or visual validation.

### Deltas / Estuaries

| Region | Current Data Coverage | Validation Role | Feasibility Judgment |
| ------ | --------------------- | --------------- | -------------------- |
| Yangtze Delta | river lines only | deferred watchlist | no true delta polygon |
| Pearl River Delta | river lines only | deferred watchlist | no true delta polygon |
| Mekong Delta | river lines only | deferred watchlist | distributary/wetland complexity not solved |
| Nile Delta | river lines only | deferred watchlist | needs delta/land-cover source |
| Ganges-Brahmaputra Delta | river lines only | deferred watchlist | too complex for line proxy alone |
| Mississippi Delta | river lines only | deferred watchlist | no marsh / delta polygon |
| Amazon mouth | river lines only | deferred watchlist | mouth/floodplain cannot be inferred reliably |
| Rhine-Meuse-Scheldt Delta | river lines only | deferred watchlist | human-modified hydrology absent |
| Irrawaddy Delta | river lines only | deferred watchlist | no true delta source |
| Red River Delta | river lines only | deferred watchlist | no true delta source |

Delta and estuary masks should not be included in the first river proxy prototype unless clearly labeled as experimental review-only outputs. They should not be used for d6 visual color decisions until validated with better data.

### Wetlands / Floodplains

| Region | Current Data Coverage | Validation Role | Feasibility Judgment |
| ------ | --------------------- | --------------- | -------------------- |
| Pantanal | no wetland source | deferred | requires external wetland / land-cover data |
| Sudd | no wetland source | deferred | requires external wetland / floodplain data |
| Okavango Delta | no wetland source | deferred | delta/wetland source required |
| Amazon floodplain | no wetland source | deferred | cannot infer from river line alone |
| West Siberian wetlands | no wetland source | deferred | land-cover/wetland source required |
| Everglades | no wetland source | deferred | global wetland/land-cover source required |
| Mesopotamian Marshes | no wetland source | deferred | global wetland/land-cover source required |

## 6. Interaction With Existing Masks

River / delta / wetland semantics must be integrated carefully with the existing mask stack:

- River proxy should generally be clipped to `land_mask`.
- River proxy may touch `inland_water_mask`, but should remain a separate mask and not merge into lake semantics.
- River proxy should not cover `ocean_mask` unless a separate mouth / estuary proxy is explicitly designed.
- Lake and inland-water masks should have higher priority than river proxy.
- Terrain color application should avoid overpainting major river corridors only after validation and API priority design.
- Wetlands and floodplains may overlap `lowland_or_basin_proxy`; this overlap is semantically expected and needs group / priority metadata.
- Deltas and estuaries may cross the land-ocean boundary and therefore should not be forced into the same clipping rule as inland river lines.
- API design must support mask groups, priority, parent-child relationships where needed, and a `proxy` vs `data_derived` flag.

The key risk is semantic overclaiming. A buffered WDBII line can support a `major_river_proxy`, but it cannot support true river width, wetland, floodplain, or delta masks.

## 7. Proposed B-6.2G-3B Scope

If B-6.2G-3B proceeds, it should be explicitly framed as a proxy prototype.

Allowed for B-6.2G-3B:

- `major_river_proxy`
- `river_buffer_proxy`
- optional review-only `river_mouth_proxy`

Conditional / likely defer:

- `estuary_proxy`, unless clearly marked experimental and not used as visual truth

Must be deferred:

- true `wetland_mask`
- true `floodplain_mask`
- true `river_delta_proxy`
- true `marsh_mask`
- `seasonal_floodplain_proxy`
- `mangrove_coast_proxy`
- detailed river width model

Recommended B-6.2G-3B technical boundary:

- Modify only the independent structure mask generator.
- Use WDBII `h` river polylines.
- Start with L01 only, with L02 considered only after validation.
- Rasterize as line, then apply documented 2K dilation.
- Clip inland river proxy to land semantics.
- Exclude ocean except for separately named mouth / estuary experimental masks.
- Do not alter lake, terrain, ocean, pwa, production, or d6 behavior.
- Write generated outputs only under `d5b_processor_v3/d5b_output/structure_masks/`.
- Follow with B-6.2G-3C validation before any API or visual use.

## 8. API / d6 / Visual Boundary

B-6.2G-3A is an audit only.

Not allowed now:

- d6 integration
- visual rebuild
- color application / 上色
- API freeze
- production texture changes
- `DAY_TEXTURE_VARIANT` changes
- writes to `pwa/`, `production/`, or `candidates/`

The API may continue to be drafted conceptually, but not frozen. River / delta / wetland semantics must remain unavailable to d6 until after implementation and validation gates.

## 9. Final Recommendation

- Is WDBII rivers usable for major river proxy? Conditional yes.
- Can B-6.2G-3B start after this audit? Conditional yes.
- What can be implemented now? A conservative `major_river_proxy` / `river_buffer_proxy` from WDBII `h/L01`, optionally with L02 as a separate validation variant.
- What must be deferred? True delta, wetland, marsh, floodplain, mangrove, seasonal floodplain, and river width models.
- Which datasets are missing? Global wetland / floodplain / land-cover / mangrove / delta datasets; usable Natural Earth assets are not present in the current source tree.
- Should wetland/delta be separate from river? Yes. They require different geometry and data semantics.
- Can d6 be touched? No.
- Can visual rebuild / 上色 start? No.
- Is git state safe? Conditional. The repository already has unrelated modified and untracked files; implementation can proceed only if future commits keep d6, root previews, generated outputs, and unrelated changes out of scope.

## 10. Completion Notes

This document was generated as a planning/audit artifact only.

- Code modified: no
- Masks generated: no
- Structure mask generator run: no
- d6 run: no
- pwa / production / candidates written: no
- Commit / push: no
- Critical issue found: no blocker for a proxy-only river prototype, but no current asset supports true wetland / floodplain / delta masks

