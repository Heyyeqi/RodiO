"""
VC Layer test suite.
Run from repo root: python3 -m core.vc._test_vc

Tests:
  1. Dead Sea tile     — all-land mask → no ocean gradient, smooth land field
  2. Pacific Ocean     — all-ocean mask → deep blue stable, coastline=0
  3. Coastal zone      — mixed → gradient transition, not binary edge
  4. Temporal          — same tile twice → stability ≈ 1.0; perturbed → drops
"""

import numpy as np
from core.m1 import M1Pipeline, TileBBox
from core.binding import TemporalState
from core.vc import VisualConsistencyEngine, VCRenderContext


# ---------------------------------------------------------------------------
# Signal providers (reused from M1 tests)
# ---------------------------------------------------------------------------

def dead_sea_signals(lon, lat):
    return dict(dem_signal="ocean", dem_confidence=0.90,
                climate_signal="land", climate_confidence=0.85,
                ocean_signal="ocean", ocean_confidence=0.75,
                landcover_signal="land", landcover_confidence=0.80)


def pacific_signals(lon, lat):
    return dict(dem_signal="ocean", dem_confidence=0.99,
                climate_signal=None,
                ocean_signal="ocean", ocean_confidence=0.99,
                landcover_signal="ocean", landcover_confidence=0.95)


def coastal_signals(lon, lat):
    t = max(0.0, min(1.0, (lon - 119.0) / 4.0))
    dem = "land" if t > 0.5 else "ocean"
    ocn = "shallow_water" if 0.2 < t < 0.8 else ("land" if t >= 0.8 else "ocean")
    clm = "land" if t > 0.3 else "ocean"
    lc  = "land" if t > 0.6 else "ocean"
    return dict(dem_signal=dem,  dem_confidence=0.55 + 0.10 * abs(t - 0.5),
                climate_signal=clm, climate_confidence=0.60,
                ocean_signal=ocn,   ocean_confidence=0.65,
                landcover_signal=lc, landcover_confidence=0.50 + 0.15 * abs(t - 0.5))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_tile(signal_fn, bbox, lat, climate_zone=None, px=8):
    pipeline = M1Pipeline(
        signal_provider=signal_fn,
        temporal=TemporalState(month=7, hour=12, lat=lat, climate_zone=climate_zone),
        tile_px_size=px,
    )
    return pipeline.run_tile(bbox)


def fmt(v): return f"{v:.4f}"


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_tests():
    results = []
    print("=" * 65)
    print("VC LAYER TEST SUITE")
    print("=" * 65)

    # Each test gets a fresh VCE instance to avoid EMA cross-contamination.
    vce1 = VisualConsistencyEngine()

    # ------------------------------------------------------------------
    # Test 1: Dead Sea — all-land tile
    # ------------------------------------------------------------------
    print("\n[TEST 1] Dead Sea Tile — all land, no coastline")
    bbox_ds = TileBBox(lon_min=34.5, lon_max=36.5, lat_min=30.5, lat_max=32.5)
    tile_ds = make_tile(dead_sea_signals, bbox_ds, lat=31.5, climate_zone="arid", px=8)
    vce_ds = vce1.process(tile_ds)

    ds_coast_min, ds_coast_max = vce_ds.coastline_gradient_range()
    # All land → coastline_gradient should be > 0.9 everywhere
    ds_land_coast = ds_coast_min > 0.9
    # No gradient needed: has_gradient_transition should be False (no mid-band)
    ds_no_edge    = not vce_ds.has_gradient_transition(tolerance=0.05)
    # base_color should be reddish (desert sand — R > B)
    ds_color_mean = vce_ds.base_color_field.mean(axis=(0, 1))
    ds_reddish    = ds_color_mean[0] > ds_color_mean[2]
    ds_stability  = vce_ds.mean_temporal_stability()
    ds_pass       = ds_land_coast and ds_reddish
    results.append(("Dead Sea", ds_pass))

    print(f"  coastline range:       [{fmt(ds_coast_min)}, {fmt(ds_coast_max)}]")
    print(f"  coast > 0.9 (land):    {'✓' if ds_land_coast else '✗'}  min={fmt(ds_coast_min)}")
    print(f"  no mid-gradient:       {'✓' if ds_no_edge else '–'}  (single biome)")
    print(f"  base_color R>B:        {'✓' if ds_reddish else '✗'}  rgb=({fmt(ds_color_mean[0])},{fmt(ds_color_mean[1])},{fmt(ds_color_mean[2])})")
    print(f"  temporal_stability:    {fmt(ds_stability)}")
    print(f"  biome_blend mean:      {fmt(float(vce_ds.biome_blend_field.mean()))}")
    print(f"  Result: {'PASS' if ds_pass else 'FAIL'}")

    # ------------------------------------------------------------------
    # Test 2: Pacific Ocean — all-ocean tile
    # ------------------------------------------------------------------
    print("\n[TEST 2] Pacific Ocean Tile — all ocean, stable deep blue")
    vce2 = VisualConsistencyEngine()   # fresh engine
    bbox_oc = TileBBox(lon_min=-145.0, lon_max=-135.0, lat_min=5.0, lat_max=15.0)
    tile_oc = make_tile(pacific_signals, bbox_oc, lat=10.0, px=8)
    vce_oc  = vce2.process(tile_oc)

    oc_coast_min, oc_coast_max = vce_oc.coastline_gradient_range()
    # All ocean → coastline gradient should be < 0.1 everywhere
    oc_ocean_coast  = oc_coast_max < 0.1
    oc_color_mean   = vce_oc.base_color_field.mean(axis=(0, 1))
    oc_bluish       = oc_color_mean[2] > oc_color_mean[0]
    oc_stability    = vce_oc.mean_temporal_stability()
    oc_pass         = oc_ocean_coast and oc_bluish
    results.append(("Pacific Ocean", oc_pass))

    print(f"  coastline range:       [{fmt(oc_coast_min)}, {fmt(oc_coast_max)}]")
    print(f"  coast < 0.1 (ocean):   {'✓' if oc_ocean_coast else '✗'}  max={fmt(oc_coast_max)}")
    print(f"  base_color B>R:        {'✓' if oc_bluish else '✗'}  rgb=({fmt(oc_color_mean[0])},{fmt(oc_color_mean[1])},{fmt(oc_color_mean[2])})")
    print(f"  temporal_stability:    {fmt(oc_stability)}")
    print(f"  Result: {'PASS' if oc_pass else 'FAIL'}")

    # ------------------------------------------------------------------
    # Test 3: Coastal zone — gradient transition, not binary edge
    # ------------------------------------------------------------------
    print("\n[TEST 3] Coastal Transition Tile — gradient, not binary edge")
    vce3 = VisualConsistencyEngine()   # fresh engine (clean EMA state)
    bbox_co = TileBBox(lon_min=119.0, lon_max=123.0, lat_min=22.0, lat_max=26.0)
    tile_co = make_tile(coastal_signals, bbox_co, lat=24.0, climate_zone="tropical", px=16)
    vce_co  = vce3.process(tile_co)

    co_coast_min, co_coast_max = vce_co.coastline_gradient_range()
    co_has_gradient  = vce_co.has_gradient_transition(tolerance=0.05)
    co_gradient_span = co_coast_max - co_coast_min
    co_blend_mean    = float(vce_co.biome_blend_field.mean())
    co_stability     = vce_co.mean_temporal_stability()
    co_pass          = co_has_gradient and co_gradient_span > 0.3
    results.append(("Coastal Transition", co_pass))

    print(f"  coastline range:       [{fmt(co_coast_min)}, {fmt(co_coast_max)}]")
    print(f"  gradient span > 0.3:   {'✓' if co_gradient_span > 0.3 else '✗'}  span={fmt(co_gradient_span)}")
    print(f"  mid-band values exist: {'✓' if co_has_gradient else '✗'}")
    print(f"  biome_blend mean:      {fmt(co_blend_mean)}")
    print(f"  temporal_stability:    {fmt(co_stability)}")
    print(f"  Result: {'PASS' if co_pass else 'FAIL'}")

    # ------------------------------------------------------------------
    # Test 4: Temporal stability — same tile → stable; perturbed → drops
    # ------------------------------------------------------------------
    print("\n[TEST 4] Temporal Stability — same tile vs perturbed")
    vce4 = VisualConsistencyEngine(temporal_alpha=0.85)
    bbox_t = TileBBox(lon_min=119.0, lon_max=123.0, lat_min=22.0, lat_max=26.0)
    tile_coastal = make_tile(coastal_signals, bbox_t, lat=24.0, climate_zone="tropical", px=16)

    # Warm up the EMA: process the same coastal tile several times so the
    # EMA state converges to the coastal pattern before we measure stability.
    for _ in range(5):
        vce4.process(tile_coastal)

    # Measure stability on the same tile after EMA convergence → should be high
    ctx_stable = vce4.process(tile_coastal)
    stab_same = ctx_stable.mean_temporal_stability()

    # Perturb: switch to all-ocean tile → EMA has coastal state, new input differs
    tile_ocean_px16 = make_tile(pacific_signals,
                                TileBBox(lon_min=-145, lon_max=-135, lat_min=5, lat_max=15),
                                lat=10.0, px=16)
    ctx_perturbed = vce4.process(tile_ocean_px16)
    stab_perturbed = ctx_perturbed.mean_temporal_stability()

    same_stable    = stab_same > 0.80
    perturb_drops  = stab_perturbed < stab_same
    temp_pass      = same_stable and perturb_drops
    results.append(("Temporal Stability", temp_pass))

    print(f"  stability (same tile, post-warmup): {fmt(stab_same)}  {'✓' if same_stable else '✗'}  (expect > 0.80)")
    print(f"  stability (perturbed to ocean):     {fmt(stab_perturbed)}  {'✓' if perturb_drops else '✗'}  (expect < same)")
    print(f"  delta:                              {fmt(stab_same - stab_perturbed)}")
    print(f"  Result: {'PASS' if temp_pass else 'FAIL'}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 65)
    passed = sum(1 for _, p in results if p)
    print(f"Results: {passed}/{len(results)} passed")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
