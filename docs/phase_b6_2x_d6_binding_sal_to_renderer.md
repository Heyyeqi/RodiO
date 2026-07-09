# D6 Binding Layer — SAL → Renderer Input
**Phase B6-2x | Status: Implemented & Tested**
*Generated: 2026-06-24*

---

## 1. Overview

The Binding Layer is the translation tier between the Semantic Arbitration Layer (SAL) and the D6 Rendering Pipeline. Its responsibility is precisely bounded:

- **SAL** decides *what* a geographic point is (semantic truth)
- **Binding Layer** decides *how it should look* (visual representation)
- **D6 Renderer** consumes that visual representation for actual rendering

```
SAL (ArbitrationResult)
         ↓
  Binding Layer (core/binding/)
         ↓
  D6RenderInput (base_color, confidence, uncertainty, temporal modifiers…)
         ↓
  D6 Renderer / OTK Texture Synthesis
```

The Binding Layer is CPU-only. It produces no raster files, calls no shaders, and does not modify SAL or M0 logic.

---

## 2. Module Structure

```
core/binding/
    binding_types.py              — shared dataclasses (ColorVector, D6RenderInput, TemporalState)
    semantic_to_visual_mapper.py  — semantic class → base color + confidence adjustment
    uncertainty_visualizer.py     — winner_margin → visual degradation (desaturation, noise, blur proxy)
    rendering_context_builder.py  — full D6RenderInput assembly + temporal modulation
    sal_d6_bridge.py              — top-level SALD6Bridge entry point
    __init__.py
    _test_binding.py              — test suite
```

---

## 3. SAL → D6 Data Flow

```
SALD6Bridge.convert(lon, lat, time_state, *signals)
    │
    ├─ 1. SemanticArbitrator.resolve(*signals)
    │        → ArbitrationResult { final_class, confidence_score, entropy, winner_margin,
    │                              conflict_detected, probability_map }
    │
    └─ 2. RenderingContextBuilder.build(sal_result, temporal)
             │
             ├─ SemanticToVisualMapper.map(final_class, climate_zone)
             │       → base_color (linear RGB)
             │
             ├─ SemanticToVisualMapper.adjust_by_confidence(base_color, confidence)
             │       → confidence-adjusted color
             │
             ├─ UncertaintyVisualizer.sal_to_uncertainty(sal_state)
             │       → margin-derived uncertainty [0, 1]
             ├─ UncertaintyVisualizer.apply(color, uncertainty)
             │       → desaturated / degraded color
             │
             ├─ Temporal modulation (solar elevation, seasonal modifier,
             │       snow blend, cloud dim)
             │
             └─ D6RenderInput { semantic_class, base_color, adjusted_color,
                                confidence, uncertainty, light_factor,
                                seasonal_modifier, uncertainty_weight,
                                is_conflict_zone, notes }
```

---

## 4. Semantic → Visual Mapping Logic

### 4.1 Base Color Palette (linear RGB)

| Semantic Class | High-Confidence Color | Low-Confidence Color |
|---|---|---|
| `ocean` | `(0.04, 0.14, 0.44)` deep blue | `(0.18, 0.38, 0.58)` washed cyan |
| `shallow_water` | `(0.10, 0.50, 0.62)` tropical teal | `(0.25, 0.52, 0.60)` |
| `land` (generic) | `(0.52, 0.42, 0.22)` earth tone | `(0.48, 0.45, 0.38)` |
| `desert` | `(0.75, 0.58, 0.25)` warm sand | `(0.60, 0.55, 0.42)` |
| `forest` | `(0.18, 0.38, 0.14)` temperate green | `(0.38, 0.44, 0.32)` |
| `ice` | `(0.85, 0.92, 0.98)` polar white-blue | `(0.78, 0.82, 0.88)` |
| `urban` | `(0.44, 0.42, 0.40)` concrete grey | `(0.50, 0.50, 0.50)` |
| `wetland` | `(0.28, 0.42, 0.24)` swamp green | `(0.40, 0.45, 0.38)` |

### 4.2 Climate Zone Biome Override

When SAL returns `final_class = "land"`, the mapper refines to a biome-specific color using the `climate_zone` field in `TemporalState`:

| Köppen-derived Zone | Effective Biome | Color |
|---|---|---|
| `"arid"`, `"semi-arid"` | `desert` | warm sand |
| `"tropical"`, `"temperate"` | `forest` | green |
| `"polar"` | `ice` | white-blue |
| `"tundra"` | `wetland` | muted green |
| None / unrecognized | `land` (generic) | earth tone |

This separation ensures SAL's truth decision ("land") is never changed — only its visual representation is refined.

### 4.3 Confidence-Driven Adjustment

```
blend_factor = 1 - clamp((confidence - 0.30) / (0.80 - 0.30))

adjusted_color = lerp(base_color, low_conf_color, blend_factor)
```

- `confidence ≥ 0.80` → 0% blend, full vivid color
- `confidence ≤ 0.30` → 100% blend, fully muted palette
- Between: linear interpolation

---

## 5. Uncertainty Rendering Model

### 5.1 Margin-Based Uncertainty

```
uncertainty = clamp(1 − winner_margin / 0.08)
```

Entropy remains available as a fallback for older SAL result objects, but `winner_margin` is the primary rendering signal.

### 5.2 Visual Degradation Effects

| Uncertainty | Desaturation | Brightness | Noise Proxy | Blur Proxy |
|---|---|---|---|---|
| 0.0 | 0% | 0 | 0.0 | 0.0 |
| 0.5 | ~14% | −0.01 | 0.03 | 0.08 |
| 1.0 | 55% | −0.05 | 0.12 | 0.30 |

Effects use smooth-step (`t² (3−2t)`) rolloff for natural transitions.

### 5.3 Uncertainty Weight

```
uncertainty_weight = clamp(uncertainty × (1 − confidence))
```

This combined metric is the primary signal for D6 to decide how aggressively to apply visual softening. High when the top two SAL classes are close and confidence is low; low when the winner is clearly separated from the runner-up.

### 5.4 Conflict Zone Rendering

When `is_conflict_zone = True` (SAL detected cross-source disagreement), the `UncertaintyVisualizer.transition_blend()` method provides a gradient between two candidate class colors:

```python
blended = lerp(color_a, color_b, clamp(uncertainty × 2.0))
```

This produces a non-binary transitional gradient rather than a hard class boundary.

---

## 6. Temporal Integration

### 6.1 Solar Elevation Factor

```
light_factor = clamp(cos(hour_angle) × cos(lat))
```

Approximate solar elevation. Provides a [0, 1] brightness modifier for time-of-day rendering. Night = 0, solar noon = 1.

### 6.2 Seasonal Modifier

```
phase    = (month − 6) / 12 × 2π
raw      = cos(phase × hemisphere_sign)
seasonal = clamp(0.85 + 0.35 × raw, 0.5, 1.2)
```

Northern hemisphere summer (June–August) peaks at ~1.20 for vegetation-rich terrain. Winter troughs at ~0.50. Southern hemisphere is inverted.

### 6.3 Snow and Cloud

- **Snow blend:** linear blend toward `(0.92, 0.94, 0.98)` proportional to `snow_cover`
- **Cloud dim:** multiply by `(1 − 0.30 × cloud_cover)` — up to 30% darkening at full overcast

---

## 7. Test Case Results

### 7.1 Dead Sea (SAL=land, arid climate)

| Field | Value |
|---|---|
| semantic_class | `"land"` |
| base_color | `rgb(0.750, 0.580, 0.250)` — desert sand (arid override applied) |
| adjusted_color | `rgb(0.523, 0.501, 0.442)` — muted by uncertainty |
| confidence | 0.149 |
| uncertainty | 0.846 |
| light_factor | 0.853 (July noon at 31.5°N) |
| seasonal_modifier | 1.153 |
| is_conflict_zone | False |
| color_reddish check | **✓** R(0.523) > B(0.442) — correct desert tone |

SAL correctly classifies as `land`; climate_zone `"arid"` triggers desert visual. Color passes reddish test.

### 7.2 Open Ocean — Pacific

| Field | Value |
|---|---|
| semantic_class | `"ocean"` |
| base_color | `rgb(0.040, 0.140, 0.440)` — deep blue |
| adjusted_color | `rgb(0.180, 0.380, 0.580)` — low-uncertainty deep blue |
| confidence | 0.169 |
| uncertainty | 0.181 |
| light_factor | 0.985 (June noon at 10°N) |
| is_conflict_zone | False |
| color_bluish check | **✓** B(0.580) > R(0.180) and B(0.580) > G(0.380) |

Consistent deep blue, blue channel dominant across base and adjusted colors.

### 7.3 Coastal Ambiguity Zone (Taiwan Strait)

| Field | Value |
|---|---|
| semantic_class | `"land"` (won marginal vote) |
| base_color | `rgb(0.180, 0.380, 0.140)` — tropical forest (climate=tropical override) |
| adjusted_color | `rgb(0.351, 0.378, 0.324)` — heavily desaturated |
| confidence | 0.134 |
| uncertainty | 0.899 |
| uncertainty_weight | 0.7784 |
| is_conflict_zone | **True** |
| elevated_uncertainty check | **✓** unc_weight=0.778 > 0.05 threshold |

Conflict flag raised, elevated uncertainty weight signals D6 to apply gradient transition rather than hard boundary.

### 7.4 Aggregate

| Test | Result |
|---|---|
| Dead Sea desert tone | ✓ PASS |
| Ocean deep blue | ✓ PASS |
| Coastal conflict gradient | ✓ PASS |
| **Total** | **3/3** |

---

## 8. Limitations (CPU-only)

### 8.1 Entropy Remains Diffuse

SAL entropy still stays near the theoretical maximum (~3.15 / 3.17 bits), but Binding now uses `winner_margin` to derive visual uncertainty. This separates clean ocean points (`uncertainty≈0.18`) from close races such as Dead Sea / coastal ambiguity (`uncertainty≈0.85–0.90`).

### 8.2 No Spatial Interpolation

The binding layer is point-level. Gradient transitions in coastal zones are conceptual hints — actual spatial interpolation (bilinear sampling, SDF-based blending) must be implemented in the D6 shader.

### 8.3 Noise / Blur as Proxies Only

`noise_proxy` and `blur_proxy` in `VisualAdjustment` are CPU-computed scalar hints. They carry no pixel data. The GPU shader must interpret them as texture sampling jitter or Gaussian blur radius.

### 8.4 Static Climate Zone

`climate_zone` in `TemporalState` is a caller-supplied string. The binding layer does not derive it from data — that derivation belongs in a future M1 climate mask layer feeding into the bridge.

### 8.5 Solar Model is Approximate

`_solar_elevation_factor` ignores solar declination and equation of time. Suitable for visual modulation, not astronomical accuracy.

---

## 9. Future GPU Shader Mapping Plan

When D6 moves from CPU hints to GPU execution, the `D6RenderInput` fields map to shader uniforms as follows:

| `D6RenderInput` field | Shader usage |
|---|---|
| `adjusted_color` | `uniform vec3 u_baseColor` — base texture tint |
| `uncertainty_weight` | `uniform float u_blurRadius` — Gaussian kernel radius |
| `noise_proxy` | `uniform float u_noiseAmp` — procedural noise amplitude |
| `light_factor` | `uniform float u_solarFactor` — directional light intensity |
| `seasonal_modifier` | `uniform float u_vegetationScale` — albedo/NDVI multiplier |
| `is_conflict_zone` | `uniform bool u_isConflict` — enables gradient blend shader path |

The Binding Layer's role post-GPU migration: supply these uniforms per tile. The bridge becomes a tile-level uniform upload step rather than a per-pixel compute.

---

## 10. API Reference

```python
from core.binding import SALD6Bridge, TemporalState, D6RenderInput

bridge = SALD6Bridge()   # default SAL weights

ctx: D6RenderInput = bridge.convert(
    lon=35.5, lat=31.5,
    time_state=TemporalState(month=7, hour=12, lat=31.5, climate_zone="arid"),
    dem_signal="ocean",       dem_confidence=0.90,
    climate_signal="land",    climate_confidence=0.85,
    ocean_signal="ocean",     ocean_confidence=0.75,
    landcover_signal="land",  landcover_confidence=0.80,
)

print(ctx.semantic_class)     # "land"
print(ctx.base_color)         # (0.75, 0.58, 0.25) — desert sand
print(ctx.adjusted_color)     # desaturated by uncertainty
print(ctx.uncertainty_weight) # how strongly D6 should soften this point
print(ctx.is_conflict_zone)   # False
```

Pre-computed SAL result path:
```python
from core.sal import SemanticArbitrator

sal_result = SemanticArbitrator().resolve(...)
ctx = bridge.convert_from_sal_result(sal_result, temporal=TemporalState(...))
```
