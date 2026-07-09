# SAL — Semantic Arbitration Layer
**Phase B6-2x | Status: Implemented & Tested**
*Generated: 2026-06-24*

---

## 1. Overview

The Semantic Arbitration Layer (SAL) resolves conflicting signals from four independent earth-observation data sources into a single, confidence-weighted semantic class for any geographic point.

```
DEM + Climate + Ocean + Landcover
              ↓
     SemanticArbitrator
              ↓
  final_class + confidence_score
```

SAL is a pure-compute Python layer. It produces no rasters, modifies no rendering pipeline, and downloads no data. It is designed to be called per-point or over a small grid for window-level inference.

---

## 2. Module Structure

```
core/sal/
    sal_types.py           — shared dataclasses and constants
    signal_registry.py     — unified input collector
    confidence_model.py    — weighted probabilistic fusion
    decision_engine.py     — argmax + entropy + winner margin + conflict detection
    semantic_arbitrator.py — top-level entry point
    __init__.py
    _test_sal.py           — test suite (Dead Sea, Caspian, Pacific)
```

---

## 3. Architecture

### 3.1 Pipeline

```
[Source layers]          [SAL pipeline]                [Output]
DEM signal    ──┐
Climate signal──┤─→ SignalRegistry
Ocean signal  ──┤        ↓
Landcover sig.──┘  De-correlation step
                         ↓
                   ConfidenceModel
                   (weighted voting + softmax)
                         ↓
                   DecisionEngine
                   (argmax + entropy + winner margin + conflict flag)
                         ↓
                   ArbitrationResult
                   { final_class, confidence_score,
                     probability_map, conflict_detected,
                     entropy, winner_margin, explanation_trace }
```

### 3.2 Key Data Types

```python
@dataclass
class SemanticSignal:
    source: str           # "dem" | "climate" | "ocean" | "landcover"
    inferred_class: str   # one of SEMANTIC_CLASSES
    raw_confidence: float # 0.0–1.0
    weight: float         # priority weight
    metadata: Dict

@dataclass
class ArbitrationResult:
    final_class: str
    confidence_score: float
    probability_map: Dict[str, float]
    conflict_detected: bool
    entropy: float
    winner_class: str
    runner_up_class: str
    winner_margin: float
    explanation_trace: List[str]
```

**Canonical semantic classes:**
`ocean`, `land`, `ice`, `shallow_water`, `wetland`, `desert`, `forest`, `urban`, `unknown`

---

## 4. Signal Weighting System

### 4.1 Priority Weights

| Signal | Weight | Rationale |
|--------|--------|-----------|
| DEM | 0.35 | Primary physical indicator — elevation is ground truth |
| Climate | 0.30 | Land anchor (Köppen-based) — stable multi-decadal signal |
| Ocean | 0.20 | Negative elevation / GEBCO-ETOPO baseline |
| Landcover | 0.15 | Surface confirmation layer |

Weights sum to 1.00 and are configurable per instantiation.

### 4.2 Effective Vote Mass

Each signal contributes `weight × raw_confidence` to its inferred class. This means a low-confidence DEM signal is automatically down-weighted relative to a high-confidence Climate signal.

---

## 5. Conflict Resolution Logic

### 5.1 De-correlation of Elevation Signals

DEM and Ocean signals both derive from elevation data (DEM = surface elevation; Ocean = GEBCO/ETOPO bathymetry baseline). Counting them as two independent votes would systematically bias the distribution toward elevation-driven classes, unfairly outweighing independent observational signals (Climate, Landcover).

**Rule:** When DEM and Ocean agree on the same class, they are merged into one composite signal carrying:
- `weight = max(w_dem, w_ocean)` = 0.35
- `confidence = mean(conf_dem, conf_ocean)`

When they disagree, they are kept separate (genuine physical conflict).

**Effect on Dead Sea / Caspian pattern:**

| Configuration | Effective ocean-class mass | Effective land-class mass | Winner |
|---|---|---|---|
| Before de-corr | 0.35 × 0.90 + 0.20 × 0.75 = 0.465 | 0.30 × 0.85 + 0.15 × 0.80 = 0.375 | ocean ❌ |
| After de-corr | 0.35 × 0.82 (merged) = 0.287 | 0.30 × 0.85 + 0.15 × 0.80 = 0.375 | **land ✓** |

### 5.2 Conflict Detection

```python
conflict = True  when  max_class_share_of_weighted_votes < 0.55
```

Conflict flag triggers the explanation trace to log disagreement explicitly. It does not change the decision algorithm — the probability distribution already handles conflict via weighted fusion.

### 5.3 Final Decision

```
final_class     = argmax(probability_map)
confidence_score = probability_map[final_class]
```

---

## 6. Confidence Model Design

### 6.1 Probabilistic Fusion

```python
raw_scores[cls] = ε + Σ (weight_i × confidence_i)  for each signal i voting for cls
```

Where `ε = 1e-6` is a uniform prior ensuring no class has zero probability.

### 6.2 Softmax Normalisation

```python
exp_vals[i] = exp((raw_scores[i] - max_score) / T)
prob[i]     = exp_vals[i] / Σ exp_vals
```

Temperature `T = 1.0` (no sharpening). The max-shift is applied for numerical stability.

### 6.3 Entropy

Shannon entropy is computed over the final distribution:

```
H = -Σ p(c) log₂ p(c)
```

Low entropy → high certainty. High entropy → diffuse probability mass.

With 9 semantic classes, maximum possible entropy is `log₂(9) ≈ 3.17 bits`. Observed entropy of ~3.15 in current tests reflects the small but meaningful probability mass separation achieved by the weighting system.

For downstream visual uncertainty, SAL exposes a top-class margin:

```
winner_margin = p(top_1_class) − p(top_2_class)
```

This is more useful than entropy for Binding / M1 / VC because it measures how clearly the winning semantic class beats the runner-up, even when absolute softmax confidence remains low.

---

## 7. Test Case Results

### 7.1 Dead Sea

| Parameter | Value |
|---|---|
| Location | ~31.5°N, 35.5°E |
| DEM signal | `ocean` (conf=0.90) — elevation ≈ −430 m |
| Climate signal | `land` (conf=0.85) — Köppen BWh (hot desert) |
| Ocean signal | `ocean` (conf=0.75) — GEBCO sees sub-zero elevation |
| Landcover signal | `land` (conf=0.80) — bare rock / salt flat |
| Expected | **land** |
| Result | **land ✓** |
| Confidence | 0.1486 |
| Entropy | 3.154 bits |
| Conflict | False |

De-correlation merged DEM+Ocean (both "ocean") → single elevation vote (w=0.35). Climate+Landcover combined land mass (0.375) exceeded merged ocean mass (0.287). Land wins correctly.

### 7.2 Caspian Basin

| Parameter | Value |
|---|---|
| Location | ~40°N, 52°E |
| DEM signal | `ocean` (conf=0.85) — elevation ≈ −28 m |
| Climate signal | `land` (conf=0.80) — steppe/semi-arid |
| Ocean signal | `ocean` (conf=0.70) |
| Landcover signal | `land` (conf=0.75) |
| Expected | **land** |
| Result | **land ✓** |
| Confidence | 0.1461 |
| Entropy | 3.156 bits |
| Conflict | False |

Same endorheic basin pattern. De-correlation resolves correctly.

### 7.3 Pacific Ocean (mid-ocean)

| Parameter | Value |
|---|---|
| Location | Open Pacific |
| DEM signal | `ocean` (conf=0.99) |
| Climate signal | absent — no Köppen zone over open water |
| Ocean signal | `ocean` (conf=0.99) |
| Landcover signal | `ocean` (conf=0.95) |
| Expected | **ocean** |
| Result | **ocean ✓** |
| Confidence | 0.1693 |
| Entropy | 3.148 bits |
| Conflict | False |

DEM+Ocean merged, reinforced by landcover. Clean ocean decision.

### 7.4 Aggregate

| Test | Result | Final Class | Confidence |
|---|---|---|---|
| Dead Sea | ✓ PASS | land | 0.1486 |
| Caspian Basin | ✓ PASS | land | 0.1461 |
| Pacific Ocean | ✓ PASS | ocean | 0.1693 |
| **Average** | **3/3** | — | **0.1547** |

---

## 8. Limitations

### 8.1 Confidence Magnitude

Absolute confidence values (~0.15) are low because softmax distributes probability across all 9 semantic classes, including irrelevant ones (e.g., "urban" receives ε mass for an ocean point). Confidence should be interpreted **relatively** (winning class vs. runner-up), not as an absolute probability of correctness. `winner_margin` is the current ranking-based certainty metric for downstream layers.

### 8.2 Single-Point Inference Only

The current implementation is purely point-level. No spatial context, no neighbourhood smoothing, no tile-level consistency enforcement. Adjacent points with slightly different input signals may receive conflicting classifications.

### 8.3 Binary Class Inputs

Each source layer provides a single `inferred_class` + confidence. SAL would benefit from receiving a full class distribution from each source rather than a single hard vote, enabling richer probabilistic fusion.

### 8.4 Static Weights

Priority weights are fixed at init time. Adaptive weighting based on geographic region (e.g., reducing Climate weight over high-latitude ice sheets) would improve accuracy.

### 8.5 No Temporal Signal

SAL operates on static layers. Dynamic signals (seasonal sea ice, seasonal flood extent) are not yet modelled.

---

## 9. Future Integration with D6 Renderer

SAL is designed as the semantic ground-truth provider upstream of the D6 rendering pipeline:

```
[Raw layers: DEM, Climate, Ocean, Landcover]
              ↓
            SAL
              ↓
    ArbitrationResult (per tile)
              ↓
   D6 Semantic Mask Generator (M1)
              ↓
    OTK Texture Synthesis
              ↓
    Renderer
```

**Integration points:**
- M1 (semantic mask derivation) should consume `ArbitrationResult.final_class` and `confidence_score` per grid point
- D6 can use `winner_margin` as a measure of spatial ambiguity to drive LOD decisions
- `conflict_detected` can flag boundary zones for blended treatment
- The `explanation_trace` can feed the D6 debug overlay for visual arbitration inspection

**Not in scope for SAL:**
- Texture generation
- Raster output
- 8K batch processing
- Rendering pipeline modification

---

## 10. API Reference

```python
from core.sal import SemanticArbitrator, ArbitrationResult

arb = SemanticArbitrator()  # uses default weights

result: ArbitrationResult = arb.resolve(
    dem_signal="ocean",       dem_confidence=0.90,
    climate_signal="land",    climate_confidence=0.85,
    ocean_signal="ocean",     ocean_confidence=0.75,
    landcover_signal="land",  landcover_confidence=0.80,
)

print(result.final_class)        # "land"
print(result.confidence_score)   # 0.1486
print(result.conflict_detected)  # False
print(result.entropy)            # 3.154
print(result.winner_margin)      # 0.012
for line in result.explanation_trace:
    print(line)
```

Custom weights:
```python
arb = SemanticArbitrator(weights={
    "dem": 0.40, "climate": 0.35, "ocean": 0.15, "landcover": 0.10
})
```
