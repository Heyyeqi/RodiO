"""
RealSignalProvider test suite.
Run from repo root: python3 -m core.m1._test_real_signal_provider
"""

from pathlib import Path

from core.m1 import M1Pipeline, RealSignalProvider, TileBBox
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
        and signals_ds["climate_signal"] == "land"
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
            and samples["Dead Sea"]["climate_signal"] == "land"
            and samples["Shanghai"]["climate_signal"] == "land"
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


if __name__ == "__main__":
    run_tests()
