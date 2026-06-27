"""
SAL test suite — Dead Sea, Caspian Basin, Pacific Ocean.

Run from repo root:
    python3 -m core.sal._test_sal
"""

from core.sal import SemanticArbitrator

arb = SemanticArbitrator()

CASES = [
    {
        "name": "Dead Sea",
        "desc": "Below sea level, but saline lake in an arid land region",
        "dem":       ("ocean", 0.90),
        "climate":   ("land",  0.85),
        "ocean":     ("ocean", 0.75),
        "landcover": ("land",  0.80),
        "expected":  "land",
    },
    {
        "name": "Caspian Basin",
        "desc": "Endorheic basin, negative elevation, surrounded by steppe",
        "dem":       ("ocean", 0.85),
        "climate":   ("land",  0.80),
        "ocean":     ("ocean", 0.70),
        "landcover": ("land",  0.75),
        "expected":  "land",
    },
    {
        "name": "Pacific Ocean (mid-ocean)",
        "desc": "Deep ocean — all signals point to ocean",
        "dem":       ("ocean", 0.99),
        "climate":   None,
        "ocean":     ("ocean", 0.99),
        "landcover": ("ocean", 0.95),
        "expected":  "ocean",
    },
]

results = []
print("=" * 60)
print("SAL TEST SUITE")
print("=" * 60)

for case in CASES:
    dem_sig, dem_conf = case["dem"]        if case["dem"]        else (None, 1.0)
    clm_sig, clm_conf = case["climate"]    if case["climate"]    else (None, 1.0)
    ocn_sig, ocn_conf = case["ocean"]      if case["ocean"]      else (None, 1.0)
    lc_sig,  lc_conf  = case["landcover"]  if case["landcover"]  else (None, 1.0)

    result = arb.resolve(
        dem_signal=dem_sig,       dem_confidence=dem_conf,
        climate_signal=clm_sig,   climate_confidence=clm_conf,
        ocean_signal=ocn_sig,     ocean_confidence=ocn_conf,
        landcover_signal=lc_sig,  landcover_confidence=lc_conf,
    )

    passed = result.final_class == case["expected"]
    status = "PASS" if passed else "FAIL"

    print(f"\n[{status}] {case['name']}")
    print(f"       {case['desc']}")
    print(f"       expected={case['expected']!r}  got={result.final_class!r}")
    print(
        f"       confidence={result.confidence_score:.3f}  entropy={result.entropy:.3f}  "
        f"margin={result.winner_margin:.3f}  runner_up={result.runner_up_class!r}  "
        f"conflict={result.conflict_detected}"
    )
    print("       Trace:")
    for line in result.explanation_trace:
        print(f"         {line}")

    results.append({
        "name": case["name"],
        "passed": passed,
        "final_class": result.final_class,
        "confidence": result.confidence_score,
        "margin": result.winner_margin,
    })

print("\n" + "=" * 60)
passed_count = sum(1 for r in results if r["passed"])
avg_conf = sum(r["confidence"] for r in results) / len(results)
avg_margin = sum(r["margin"] for r in results) / len(results)
print(f"Results: {passed_count}/{len(results)} passed")
print(f"Average confidence score: {avg_conf:.4f}")
print(f"Average winner margin: {avg_margin:.4f}")
print("=" * 60)
