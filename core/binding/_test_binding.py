"""
Binding Layer test suite.
Run from repo root: python3 -m core.binding._test_binding

Tests:
  1. Dead Sea      — SAL=land(high conf) → desert tone expected
  2. Open ocean    — SAL=ocean           → deep stable blue
  3. Coastal ambiguity — conflict zone   → gradient transition visual
"""

from core.binding import SALD6Bridge, TemporalState

bridge = SALD6Bridge()

CASES = [
    {
        "name": "Dead Sea",
        "desc": "SAL=land (high conf, arid climate) → desert tone",
        "lon": 35.5, "lat": 31.5,
        "time_state": TemporalState(month=7, hour=12, lat=31.5, climate_zone="arid"),
        "signals": dict(
            dem_signal="ocean",       dem_confidence=0.90,
            climate_signal="land",    climate_confidence=0.85,
            ocean_signal="ocean",     ocean_confidence=0.75,
            landcover_signal="land",  landcover_confidence=0.80,
        ),
        "checks": {
            "final_class": "land",
            "is_conflict_zone": False,
            # desert tone: red channel dominant over blue
            "color_reddish": lambda c: c[0] > c[2],
        },
    },
    {
        "name": "Open Ocean (Pacific)",
        "desc": "SAL=ocean (all signals agree) → deep stable blue",
        "lon": -140.0, "lat": 10.0,
        "time_state": TemporalState(month=6, hour=12, lat=10.0, climate_zone=None),
        "signals": dict(
            dem_signal="ocean",       dem_confidence=0.99,
            climate_signal=None,
            ocean_signal="ocean",     ocean_confidence=0.99,
            landcover_signal="ocean", landcover_confidence=0.95,
        ),
        "checks": {
            "final_class": "ocean",
            "is_conflict_zone": False,
            # deep blue: blue channel dominant
            "color_bluish": lambda c: c[2] > c[0] and c[2] > c[1],
        },
    },
    {
        "name": "Coastal Ambiguity Zone",
        "desc": "DEM=ocean vs Climate=land vs Ocean=shallow → conflict, gradient",
        "lon": 121.0, "lat": 24.0,
        "time_state": TemporalState(month=6, hour=12, lat=24.0, climate_zone="tropical"),
        "signals": dict(
            dem_signal="ocean",            dem_confidence=0.55,
            climate_signal="land",         climate_confidence=0.60,
            ocean_signal="shallow_water",  ocean_confidence=0.65,
            landcover_signal="land",       landcover_confidence=0.50,
        ),
        "checks": {
            # Any non-"unknown" class is acceptable in a conflict zone
            "not_unknown": lambda cls: cls != "unknown",
            # Uncertainty weight should be elevated
            "elevated_uncertainty": lambda uw: uw > 0.05,
        },
    },
]


def fmt_color(c):
    return f"rgb({c[0]:.3f}, {c[1]:.3f}, {c[2]:.3f})"


results = []
print("=" * 65)
print("BINDING LAYER TEST SUITE")
print("=" * 65)

for case in CASES:
    ctx = bridge.convert(
        lon=case["lon"], lat=case["lat"],
        time_state=case["time_state"],
        **case["signals"],
    )

    check_results = {}
    for check_name, check_fn in case["checks"].items():
        if check_name == "final_class":
            val = ctx.semantic_class
            passed = val == check_fn
            check_results[check_name] = (passed, f"got={val!r} expected={check_fn!r}")
        elif check_name == "is_conflict_zone":
            val = ctx.is_conflict_zone
            passed = val == check_fn
            check_results[check_name] = (passed, f"got={val}")
        elif check_name in ("color_reddish", "color_bluish"):
            val = ctx.adjusted_color
            passed = check_fn(val)
            check_results[check_name] = (passed, f"color={fmt_color(val)}")
        elif check_name == "not_unknown":
            val = ctx.semantic_class
            passed = check_fn(val)
            check_results[check_name] = (passed, f"class={val!r}")
        elif check_name == "elevated_uncertainty":
            val = ctx.uncertainty_weight
            passed = check_fn(val)
            check_results[check_name] = (passed, f"uncertainty_weight={val:.4f}")

    all_pass = all(r[0] for r in check_results.values())
    status = "PASS" if all_pass else "FAIL"
    results.append({"name": case["name"], "passed": all_pass, "ctx": ctx})

    print(f"\n[{status}] {case['name']}")
    print(f"       {case['desc']}")
    print(f"       semantic_class={ctx.semantic_class!r}  confidence={ctx.confidence:.3f}")
    print(f"       base_color    = {fmt_color(ctx.base_color)}")
    print(f"       adjusted_color= {fmt_color(ctx.adjusted_color)}")
    print(f"       uncertainty={ctx.uncertainty:.3f}  unc_weight={ctx.uncertainty_weight:.4f}")
    print(f"       light={ctx.light_factor:.3f}  seasonal={ctx.seasonal_modifier:.3f}")
    print(f"       conflict_zone={ctx.is_conflict_zone}")
    print("       Checks:")
    for cname, (cp, cdesc) in check_results.items():
        print(f"         {'✓' if cp else '✗'} {cname}: {cdesc}")
    print("       Builder notes:")
    for note in ctx.notes:
        print(f"         {note}")

print("\n" + "=" * 65)
passed_count = sum(1 for r in results if r["passed"])
print(f"Results: {passed_count}/{len(results)} passed")
print("=" * 65)
