# RDL M0/M1 Acceptance Snapshot — 2026-06-26

## Scope

This snapshot verifies the current RDL Mapbox + GEBCO M0/M1 outputs after the Hawaii visual pass.

No generator was run for this report. No runtime code, source data, Railway settings, or git staging was changed.

## Inventory Check

| Item | Count | Result |
|---|---:|---|
| RDL region directories | 84 | PASS |
| `tile_mapbox.jpg` | 84 | PASS |
| `tile_noon_air_mapbox.jpg` | 84 | PASS |
| `mapbox_meta.json` | 84 | PASS |

The local output inventory is complete for all currently registered RDL regions.

## Visual Acceptance

Hawaii is accepted as the first M0/M1 visual pass based on the side-by-side browser screenshot supplied by the user:

- Enhanced version shows clearer island edges.
- Shallow-water cyan/blue bands separate better from deep ocean.
- GEBCO depth structure is visible without overpowering Mapbox satellite texture.

Additional sample review was generated for:

- `hawaii`
- `maldives`
- `great_barrier_reef`
- `philippines_central`
- `caribbean_bahamas`

Evidence files:

- `m0_m1_contact_sheet.jpg`
- `m0_m1_sample_metrics.json`

## Sample Metrics

| Region | RGB RMSE | Mean RGB Delta | Luma Std Raw | Luma Std Enhanced | RGB Spread Raw | RGB Spread Enhanced | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| hawaii | 4.819 | 2.327 | 14.805 | 19.011 | 10.000 | 12.451 | PASS |
| maldives | 7.199 | 4.949 | 8.398 | 10.788 | 31.916 | 42.606 | PASS |
| great_barrier_reef | 16.006 | 11.489 | 45.095 | 57.661 | 32.310 | 42.877 | PASS |
| philippines_central | 9.552 | 6.276 | 29.583 | 37.872 | 24.447 | 32.076 | PASS |
| caribbean_bahamas | 9.893 | 6.214 | 30.922 | 39.671 | 25.595 | 33.602 | PASS |

Interpretation: the enhanced M0/M1 outputs consistently increase local contrast and color separation across the high-risk tropical/island samples. This matches the intended role of M1: preserve Mapbox shallow/coastal detail while adding readable bathymetric depth separation.

## Current Verdict

M0/M1 is ready to continue as the accepted baseline for RDL regional visual review.

Do not merge M2 Coral Atlas into the same acceptance step. Coral Atlas remains a separate vector-to-raster workflow with additional GIS dependencies.

## Deployment Blocker

The visual output is locally complete, but deployment packaging is not yet solved.

`/assets/earth/bmng21k` is served from:

`d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG`

However, `d5b_processor_v3/source_cache/` is excluded locally by `.git/info/exclude`, so ordinary `git add` will not include the 84 RDL assets. Before commit/push/Railway deployment, choose one asset strategy:

1. Force-add the required RDL output subtree.
2. Move/copy deployable assets into a tracked static asset directory.
3. Serve the RDL assets from external object storage/CDN.

No deployment should be treated as ready until one of these is explicitly chosen and verified.
