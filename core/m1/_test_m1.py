"""
M1 Pipeline test suite.
Run from repo root: python3 -m core.m1._test_m1

Tests:
  1. Dead Sea tile    — land_mask=1, ocean_mask=0, conflicted margin remains high
  2. Open Ocean tile  — ocean_mask=1, low margin-derived uncertainty
  3. Coastal tile     — mixed, spatial uncertainty/probability gradients present
"""

import numpy as np
from core.m1 import M1Pipeline, TileBBox, BIOME_DESERT, BIOME_OCEAN, BIOME_NAMES
from core.binding import TemporalState


# ---------------------------------------------------------------------------
# Signal providers for each test scenario
# ---------------------------------------------------------------------------

def dead_sea_signals(lon: float, lat: float) -> dict:
    """Dead Sea: below sea level but arid land."""
    return dict(
        dem_signal="ocean",       dem_confidence=0.90,
        climate_signal="land",    climate_confidence=0.85,
        ocean_signal="ocean",     ocean_confidence=0.75,
        landcover_signal="land",  landcover_confidence=0.80,
    )


def pacific_signals(lon: float, lat: float) -> dict:
    """Mid-Pacific: unambiguous deep ocean."""
    return dict(
        dem_signal="ocean",       dem_confidence=0.99,
        climate_signal=None,
        ocean_signal="ocean",     ocean_confidence=0.99,
        landcover_signal="ocean", landcover_confidence=0.95,
    )


def coastal_signals(lon: float, lat: float) -> dict:
    """
    Coastal ambiguity: simulate a gradient by using lon position to blend
    between land-dominant and ocean-dominant signals across the tile.
    Points in the left half lean ocean; right half leans land.
    """
    # Tile covers lon [119, 123] — left = open water, right = land
    t = (lon - 119.0) / 4.0   # 0 at left edge, 1 at right
    t = max(0.0, min(1.0, t))

    dem_class   = "land"  if t > 0.5 else "ocean"
    ocn_class   = "shallow_water" if 0.2 < t < 0.8 else ("land" if t >= 0.8 else "ocean")
    clm_class   = "land"  if t > 0.3 else "ocean"
    lc_class    = "land"  if t > 0.6 else "ocean"

    return dict(
        dem_signal=dem_class,      dem_confidence=0.55 + 0.10 * abs(t - 0.5),
        climate_signal=clm_class,  climate_confidence=0.60,
        ocean_signal=ocn_class,    ocean_confidence=0.65,
        landcover_signal=lc_class, landcover_confidence=0.50 + 0.15 * abs(t - 0.5),
    )


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_tests():
    results = []

    print("=" * 65)
    print("M1 PIPELINE TEST SUITE")
    print("=" * 65)

    # --- Test 1: Dead Sea tile (8×8 points) ---
    print("\n[TEST 1] Dead Sea Tile")
    pipeline_ds = M1Pipeline(
        signal_provider=dead_sea_signals,
        temporal=TemporalState(month=7, hour=12, lat=31.5, climate_zone="arid"),
        tile_px_size=8,
    )
    bbox_ds = TileBBox(lon_min=34.5, lon_max=36.5, lat_min=30.5, lat_max=32.5)
    tile_ds = pipeline_ds.run_tile(bbox_ds)

    ds_ocean_frac   = tile_ds.ocean_fraction()
    ds_land_frac    = tile_ds.land_fraction()
    ds_mean_unc     = tile_ds.mean_uncertainty()
    ds_mean_conf    = tile_ds.mean_confidence()
    ds_land_pass    = ds_land_frac == 1.0
    ds_ocean_pass   = ds_ocean_frac == 0.0
    ds_pass         = ds_land_pass and ds_ocean_pass
    results.append(("Dead Sea", ds_pass, ds_mean_unc))

    print(f"  Shape:           {tile_ds.shape}")
    print(f"  ocean_fraction:  {ds_ocean_frac:.3f}  (expect 0.0)")
    print(f"  land_fraction:   {ds_land_frac:.3f}  (expect 1.0)")
    print(f"  mean_confidence: {ds_mean_conf:.4f}")
    print(f"  mean_uncertainty:{ds_mean_unc:.4f}")
    print(f"  biome_codes:     {np.unique(tile_ds.biome_mask).tolist()}  "
          f"({[BIOME_NAMES.get(c,'?') for c in np.unique(tile_ds.biome_mask)]})")
    print(f"  land_mask ALL 1: {'✓' if ds_land_pass else '✗'}")
    print(f"  ocean_mask ALL 0:{'✓' if ds_ocean_pass else '✗'}")
    print(f"  Result: {'PASS' if ds_pass else 'FAIL'}")

    # --- Test 2: Open Ocean tile ---
    print("\n[TEST 2] Open Ocean Tile (Pacific)")
    pipeline_oc = M1Pipeline(
        signal_provider=pacific_signals,
        temporal=TemporalState(month=6, hour=12, lat=10.0),
        tile_px_size=8,
    )
    bbox_oc = TileBBox(lon_min=-145.0, lon_max=-135.0, lat_min=5.0, lat_max=15.0)
    tile_oc = pipeline_oc.run_tile(bbox_oc)

    oc_ocean_frac   = tile_oc.ocean_fraction()
    oc_land_frac    = tile_oc.land_fraction()
    oc_mean_unc     = tile_oc.mean_uncertainty()
    oc_mean_conf    = tile_oc.mean_confidence()
    oc_ocean_pass   = oc_ocean_frac == 1.0
    oc_land_pass    = oc_land_frac == 0.0
    oc_unc_lower    = oc_mean_unc < ds_mean_unc
    oc_pass         = oc_ocean_pass and oc_land_pass and oc_unc_lower
    results.append(("Open Ocean", oc_pass, oc_mean_unc))

    print(f"  Shape:           {tile_oc.shape}")
    print(f"  ocean_fraction:  {oc_ocean_frac:.3f}  (expect 1.0)")
    print(f"  land_fraction:   {oc_land_frac:.3f}  (expect 0.0)")
    print(f"  mean_confidence: {oc_mean_conf:.4f}")
    print(f"  mean_uncertainty:{oc_mean_unc:.4f}")
    print(f"  biome_codes:     {np.unique(tile_oc.biome_mask).tolist()}  "
          f"({[BIOME_NAMES.get(c,'?') for c in np.unique(tile_oc.biome_mask)]})")
    print(f"  ocean_mask ALL 1:{'✓' if oc_ocean_pass else '✗'}")
    print(f"  land_mask ALL 0: {'✓' if oc_land_pass else '✗'}")
    print(f"  unc < Dead Sea:  {'✓' if oc_unc_lower else '✗'}  ocean={oc_mean_unc:.4f} dead_sea={ds_mean_unc:.4f}")
    print(f"  Result: {'PASS' if oc_pass else 'FAIL'}")

    # --- Test 3: Coastal transition tile ---
    print("\n[TEST 3] Coastal Transition Tile (Taiwan Strait region)")
    pipeline_co = M1Pipeline(
        signal_provider=coastal_signals,
        temporal=TemporalState(month=6, hour=12, lat=24.0, climate_zone="tropical"),
        tile_px_size=16,
    )
    bbox_co = TileBBox(lon_min=119.0, lon_max=123.0, lat_min=22.0, lat_max=26.0)
    tile_co = pipeline_co.run_tile(bbox_co)

    co_ocean_frac   = tile_co.ocean_fraction()
    co_land_frac    = tile_co.land_fraction()
    co_mean_unc     = tile_co.mean_uncertainty()
    co_std_unc      = float(tile_co.uncertainty_mask.std())
    co_unique_biomes = np.unique(tile_co.biome_mask).tolist()
    co_mixed        = co_ocean_frac > 0.0 and co_land_frac > 0.0
    co_has_gradient = co_std_unc > 0.001          # spatial uncertainty variation
    co_prob_span    = (float(tile_co.ocean_prob_mask.max())
                       - float(tile_co.ocean_prob_mask.min())) > 0.01  # prob gradient
    co_pass         = co_mixed and co_has_gradient and co_prob_span
    results.append(("Coastal Transition", co_pass, co_mean_unc))

    print(f"  Shape:           {tile_co.shape}")
    print(f"  ocean_fraction:  {co_ocean_frac:.3f}")
    print(f"  land_fraction:   {co_land_frac:.3f}")
    print(f"  mean_confidence: {tile_co.mean_confidence():.4f}")
    print(f"  mean_uncertainty:{co_mean_unc:.4f}")
    print(f"  std_uncertainty: {co_std_unc:.6f}")
    print(f"  biome_codes:     {co_unique_biomes}  "
          f"({[BIOME_NAMES.get(c,'?') for c in co_unique_biomes]})")
    print(f"  ocean_prob range:[{tile_co.ocean_prob_mask.min():.3f}, "
          f"{tile_co.ocean_prob_mask.max():.3f}]")
    print(f"  mixed classes:   {'✓' if co_mixed else '✗'}  "
          f"(ocean={co_ocean_frac:.2f} land={co_land_frac:.2f})")
    print(f"  unc std > 0.001: {'✓' if co_has_gradient else '✗'}  "
          f"std={co_std_unc:.6f}")
    print(f"  prob gradient:   {'✓' if co_prob_span else '✗'}  "
          f"span={tile_co.ocean_prob_mask.max()-tile_co.ocean_prob_mask.min():.4f}")
    print(f"  Result: {'PASS' if co_pass else 'FAIL'}")

    # --- Tile segmenter: 8K grid dry-run consistency ---
    print("\n[TEST 4] Global Grid Dry-Run (8K tile coverage)")
    pipeline_global = M1Pipeline(tile_px_size=8)
    summary = pipeline_global.run_global(dry_run=True)
    n_cols, n_rows = pipeline_global._segmenter.tile_count()
    expected_tiles = n_cols * n_rows
    grid_consistent = summary.total_tiles == expected_tiles
    results.append(("Grid Coverage", grid_consistent, 0.0))

    print(f"  Grid:            {n_cols} cols × {n_rows} rows = {expected_tiles} tiles")
    print(f"  Reported tiles:  {summary.total_tiles}")
    print(f"  Coverage match:  {'✓' if grid_consistent else '✗'}")
    print(f"  Result: {'PASS' if grid_consistent else 'FAIL'}")

    # --- Summary ---
    print("\n" + "=" * 65)
    passed = sum(1 for _, p, _ in results if p)
    print(f"Results: {passed}/{len(results)} passed")
    print()
    print("Uncertainty distribution across test tiles:")
    for name, p, unc in results:
        if unc > 0:
            print(f"  {name:25s}  mean_unc={unc:.4f}  {'PASS' if p else 'FAIL'}")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
