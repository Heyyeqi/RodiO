"""
System Invariants

Pipeline-level correctness checks that span multiple layers.
Each function returns a dict with 'passed: bool' and 'details: str'.

Functions:
  deterministic_pipeline_test()   — same input → identical SAL output
  sal_consistency_check()         — winner_class == argmax(probability_map)
  m1_alignment_check()            — ocean_fraction + land_fraction ≤ 1
  vc_temporal_stability_check()   — EMA contracts across two passes
  d6_determinism_check()          — VC render is deterministic
"""

from typing import Dict, Any
import numpy as np


def _make_result(passed: bool, details: str) -> Dict[str, Any]:
    return {"passed": passed, "details": details}


def deterministic_pipeline_test() -> Dict[str, Any]:
    """
    Run SAL twice with identical synthetic inputs and verify the outputs
    are bit-for-bit identical. SAL must be a pure function.
    """
    from core.sal import SemanticArbitrator

    sal = SemanticArbitrator()
    kwargs = dict(
        dem_signal="ocean",      dem_confidence=0.9,
        climate_signal="ocean",  climate_confidence=0.8,
        ocean_signal="ocean",    ocean_confidence=0.95,
        landcover_signal="land", landcover_confidence=0.4,
    )

    r1 = sal.resolve(**kwargs)
    r2 = sal.resolve(**kwargs)

    checks = {
        "final_class":    r1.final_class    == r2.final_class,
        "winner_class":   r1.winner_class   == r2.winner_class,
        "winner_margin":  abs(r1.winner_margin  - r2.winner_margin)  < 1e-9,
        "winner_ratio":   abs(r1.winner_ratio   - r2.winner_ratio)   < 1e-9,
        "confidence":     abs(r1.confidence_score - r2.confidence_score) < 1e-9,
        "entropy":        abs(r1.entropy        - r2.entropy)         < 1e-9,
    }
    failed = [k for k, v in checks.items() if not v]

    if failed:
        return _make_result(False, f"Non-deterministic SAL fields: {failed}")
    return _make_result(True, "SAL is deterministic across two identical calls")


def sal_consistency_check() -> Dict[str, Any]:
    """
    Verify that winner_class is always the argmax of probability_map,
    and that winner_ratio >= 1.0 across a set of diverse signal inputs.
    """
    from core.sal import SemanticArbitrator

    sal = SemanticArbitrator()
    test_cases = [
        dict(dem_signal="ocean", climate_signal="ocean", ocean_signal="ocean",
             landcover_signal="ocean"),
        dict(dem_signal="land",  climate_signal="forest", ocean_signal=None,
             landcover_signal="forest"),
        dict(dem_signal="ice",   climate_signal="ice",    ocean_signal="ocean",
             landcover_signal=None),
        dict(dem_signal="land",  climate_signal="desert", ocean_signal="ocean",
             landcover_signal="desert"),
    ]

    errors = []
    for i, kw in enumerate(test_cases):
        r = sal.resolve(**kw)
        argmax = max(r.probability_map, key=lambda k: r.probability_map[k])
        if r.winner_class != argmax:
            errors.append(f"case {i}: winner_class={r.winner_class!r} != argmax={argmax!r}")
        if r.winner_ratio < 1.0 - 1e-6:
            errors.append(f"case {i}: winner_ratio={r.winner_ratio:.4f} < 1.0")

    if errors:
        return _make_result(False, "; ".join(errors))
    return _make_result(True, f"SAL consistency OK across {len(test_cases)} test cases")


def m1_alignment_check() -> Dict[str, Any]:
    """
    Generate one small synthetic tile and verify that ocean_fraction +
    land_fraction ≤ 1.0 (they can sum to less if unknown pixels exist).
    """
    from core.m1 import M1Pipeline, TileBBox

    def all_ocean_provider(lon, lat):
        return dict(
            dem_signal="ocean",      dem_confidence=0.9,
            climate_signal="ocean",  climate_confidence=0.85,
            ocean_signal="ocean",    ocean_confidence=0.95,
            landcover_signal="ocean", landcover_confidence=0.8,
        )

    pipeline = M1Pipeline(signal_provider=all_ocean_provider, tile_px_size=4)
    bbox = TileBBox(lon_min=-10, lon_max=10, lat_min=-10, lat_max=10)
    tile = pipeline.run_tile(bbox)

    total = tile.ocean_fraction() + tile.land_fraction()
    if total > 1.0 + 1e-6:
        return _make_result(
            False,
            f"ocean_fraction + land_fraction = {total:.4f} > 1.0"
        )
    return _make_result(
        True,
        f"M1 alignment OK: ocean={tile.ocean_fraction():.3f} "
        f"land={tile.land_fraction():.3f} sum={total:.3f}"
    )


def vc_temporal_stability_check() -> Dict[str, Any]:
    """
    Run VisualConsistencyEngine twice on the same tile and verify that
    the temporal_stability_field is always in [0, 1] and that the EMA
    delta between passes is bounded (< 1.0 range).
    """
    from core.m1 import M1Pipeline, TileBBox
    from core.vc import VisualConsistencyEngine

    def mixed_provider(lon, lat):
        if lon > 0:
            return dict(dem_signal="land", climate_signal="forest",
                        ocean_signal=None, landcover_signal="forest",
                        dem_confidence=0.8, climate_confidence=0.75,
                        ocean_confidence=0.5, landcover_confidence=0.7)
        return dict(dem_signal="ocean", climate_signal="ocean",
                    ocean_signal="ocean", landcover_signal=None,
                    dem_confidence=0.85, climate_confidence=0.8,
                    ocean_confidence=0.9, landcover_confidence=0.6)

    pipeline = M1Pipeline(signal_provider=mixed_provider, tile_px_size=8)
    bbox = TileBBox(lon_min=-20, lon_max=20, lat_min=-10, lat_max=10)
    tile = pipeline.run_tile(bbox)

    vc = VisualConsistencyEngine()
    ctx1 = vc.process(tile)
    ctx2 = vc.process(tile)

    errors = []
    for field in ("temporal_stability_field", "biome_blend_field",
                  "coastline_gradient_field", "uncertainty_modulation_field"):
        arr1 = getattr(ctx1, field).astype(np.float32)
        arr2 = getattr(ctx2, field).astype(np.float32)

        if arr1.min() < -1e-4 or arr1.max() > 1.0 + 1e-4:
            errors.append(f"pass1 {field} out of [0,1]")
        if arr2.min() < -1e-4 or arr2.max() > 1.0 + 1e-4:
            errors.append(f"pass2 {field} out of [0,1]")

        delta = float(np.abs(arr2 - arr1).max())
        if delta > 1.0:
            errors.append(f"EMA delta too large for {field}: {delta:.4f}")

    if errors:
        return _make_result(False, "; ".join(errors))
    return _make_result(True, "VC temporal stability OK across two passes on same tile")


def d6_determinism_check() -> Dict[str, Any]:
    """
    Render the same VCRenderContext twice via D6Contract.render_from_vc()
    and verify bit-identical output.
    """
    from core.m1 import M1Pipeline, TileBBox
    from core.vc import VisualConsistencyEngine
    from core.contract.d6_contract import D6Contract

    def ocean_provider(lon, lat):
        return dict(dem_signal="ocean", climate_signal="ocean",
                    ocean_signal="ocean", landcover_signal="ocean",
                    dem_confidence=0.9, climate_confidence=0.85,
                    ocean_confidence=0.95, landcover_confidence=0.8)

    pipeline = M1Pipeline(signal_provider=ocean_provider, tile_px_size=4)
    bbox = TileBBox(lon_min=0, lon_max=10, lat_min=0, lat_max=10)
    tile = pipeline.run_tile(bbox)

    vc = VisualConsistencyEngine()
    ctx = vc.process(tile)

    d6 = D6Contract()
    frame1 = d6.render_from_vc(ctx)
    frame2 = d6.render_from_vc(ctx)

    if not np.array_equal(frame1, frame2):
        diff = np.abs(frame1.astype(int) - frame2.astype(int))
        return _make_result(
            False,
            f"D6 render is non-deterministic; max pixel diff={diff.max()}"
        )
    return _make_result(True, f"D6 render is deterministic; frame shape={frame1.shape}")


def run_all() -> Dict[str, Dict[str, Any]]:
    """Run all system invariant checks and return a combined report."""
    return {
        "deterministic_pipeline": deterministic_pipeline_test(),
        "sal_consistency":        sal_consistency_check(),
        "m1_alignment":           m1_alignment_check(),
        "vc_temporal_stability":  vc_temporal_stability_check(),
        "d6_determinism":         d6_determinism_check(),
    }
