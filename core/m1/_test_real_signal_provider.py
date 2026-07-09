"""
RealSignalProvider test suite.
Run from repo root: python3 -m core.m1._test_real_signal_provider
"""

from pathlib import Path

from core.m1 import M1Pipeline, RealSignalProvider, TileBBox
from core.m1.mask_types import BIOME_NAMES, BIOME_DESERT, BIOME_FOREST, BIOME_ICE, BIOME_OCEAN
from core.runtime import FeatureVector, SpatialRuntime, SpatialState


class FakeRuntime:
    def __init__(self, state: SpatialState):
        self.state = state

    def query_point(self, lon: float, lat: float) -> SpatialState:
        return self.state


def make_state(elevation, ocean, climate_class, ocean_rule="DEM < 0"):
    fv = FeatureVector(
        elevation=float(elevation),
        ocean_flag=1.0 if ocean else 0.0,
        climate_class=float(climate_class or 0),
        slope_proxy=0.0,
    )
    return SpatialState(
        elevation=float(elevation),
        ocean=bool(ocean),
        climate_class=climate_class,
        biome_proxy=0.0,
        slope_proxy=0.0,
        feature_vector=fv,
        normalized_vector=fv,
        source={"ocean_rule": ocean_rule},
    )


def run_tests():
    results = []
    print("=" * 68)
    print("REAL SIGNAL PROVIDER TEST SUITE")
    print("=" * 68)

    print("\n[TEST 1] Below-sea-level land with Köppen veto")
    dead_sea = make_state(
        elevation=-430,
        ocean=False,
        climate_class=5,
        ocean_rule="DEM < 0 overridden by Köppen land class",
    )
    provider_ds = RealSignalProvider(FakeRuntime(dead_sea))
    signals_ds = provider_ds(35.5, 31.5)
    ds_pass = (
        signals_ds["dem_signal"] == "ocean"
        and signals_ds["climate_signal"] == "desert"   # Köppen 5 = BWk (arid)
        and signals_ds["ocean_signal"] == "land"
        and signals_ds["landcover_signal"] == "desert"
    )
    results.append(("Dead Sea mapping", ds_pass))
    print(f"  signals: {signals_ds}")
    print(f"  Result: {'PASS' if ds_pass else 'FAIL'}")

    print("\n[TEST 2] Deep ocean mapping")
    ocean = make_state(elevation=-4200, ocean=True, climate_class=None)
    provider_oc = RealSignalProvider(FakeRuntime(ocean))
    signals_oc = provider_oc(-140.0, 10.0)
    oc_pass = (
        signals_oc["dem_signal"] == "ocean"
        and signals_oc["climate_signal"] is None
        and signals_oc["ocean_signal"] == "ocean"
        and signals_oc["landcover_signal"] == "ocean"
        and signals_oc["ocean_confidence"] > 0.85
    )
    results.append(("Ocean mapping", oc_pass))
    print(f"  signals: {signals_oc}")
    print(f"  Result: {'PASS' if oc_pass else 'FAIL'}")

    print("\n[TEST 3] M1Pipeline runtime auto-wiring")
    pipeline = M1Pipeline(runtime=FakeRuntime(ocean), tile_px_size=4)
    tile = pipeline.run_tile(TileBBox(lon_min=-141.0, lon_max=-140.0, lat_min=9.0, lat_max=10.0))
    pipe_pass = tile.ocean_fraction() == 1.0 and tile.land_fraction() == 0.0
    results.append(("M1 runtime wiring", pipe_pass))
    print(f"  ocean_fraction={tile.ocean_fraction():.3f} land_fraction={tile.land_fraction():.3f}")
    print(f"  Result: {'PASS' if pipe_pass else 'FAIL'}")

    print("\n[TEST 4] Real source-cache smoke")
    root = Path("d5b_processor_v3/source_cache/gee_global")
    if root.exists():
        provider_real = RealSignalProvider.from_source_cache(root)
        samples = {
            "Pacific": provider_real(-140.0, 10.0),
            "Dead Sea": provider_real(35.5, 31.5),
            "Shanghai": provider_real(121.5, 31.2),
        }
        real_pass = (
            samples["Pacific"]["ocean_signal"] == "ocean"
            and samples["Dead Sea"]["climate_signal"] == "desert"  # Köppen arid
            and samples["Shanghai"]["climate_signal"] == "land"    # temperate
        )
        results.append(("Real source smoke", real_pass))
        for name, signals in samples.items():
            print(f"  {name}: {signals}")
        print(f"  Result: {'PASS' if real_pass else 'FAIL'}")
    else:
        print("  SKIP: source cache not found")

    print("\n" + "=" * 68)
    passed = sum(1 for _, ok in results if ok)
    print(f"Results: {passed}/{len(results)} passed")
    print("=" * 68)

    if passed != len(results):
        raise SystemExit(1)


def run_biome_acceptance():
    """
    5-point biome acceptance: verifies that biome_mask output from
    MaskGenerator matches expected biomes for well-known geographic anchors.

    Requires real source cache at d5b_processor_v3/source_cache/gee_global/.
    """
    root = Path("d5b_processor_v3/source_cache/gee_global")
    if not root.exists():
        print("\n[BIOME ACCEPTANCE] SKIP: source cache not found")
        return

    from core.m1.mask_generator import MaskGenerator

    provider  = RealSignalProvider.from_source_cache(root)
    generator = MaskGenerator(signal_provider=provider, tile_px_size=1)

    anchors = [
        # (name,  lon,    lat,   expected_biome_code)
        ("Sahara",    15.0,   20.0,  BIOME_DESERT),
        ("Singapore", 103.8,   1.4,  BIOME_FOREST),
        ("Himalayas", 86.9,   27.9,  BIOME_ICE),
        ("Pacific",  -150.0,  20.0,  BIOME_OCEAN),
        ("Dead Sea",   35.5,  31.5,  BIOME_DESERT),  # ocean veto + arid
    ]

    print("\n" + "=" * 68)
    print("BIOME ACCEPTANCE TEST (5 geographic anchors)")
    print("=" * 68)

    all_pass = True
    for name, lon, lat, expected in anchors:
        half = 0.05
        mask = generator.generate_mask(
            lon_range=(lon - half, lon + half),
            lat_range=(lat - half, lat + half),
            resolution=1,
        )
        got = int(mask.biome_mask[0, 0])
        ok  = got == expected
        all_pass = all_pass and ok
        sym = "✓" if ok else "✗"
        print(
            f"  {sym} {name:<12}  got={BIOME_NAMES.get(got,'?'):<8} "
            f"expected={BIOME_NAMES.get(expected,'?')}"
        )

    print(f"\n  {'ALL PASS' if all_pass else 'SOME FAILED'}")
    if not all_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()
    run_biome_acceptance()
