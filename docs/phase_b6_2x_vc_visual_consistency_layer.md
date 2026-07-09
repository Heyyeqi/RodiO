# VC — Visual Consistency Layer
**Phase B6-2x | Status: Implemented & Tested**
*Generated: 2026-06-24*

---

## 1. Overview

The Visual Consistency Layer (VC) sits between M1 (semantic mask tiles) and D6 (renderer), transforming hard-edged discrete classifications into spatially and temporally smooth visual fields.

```
M1 SemanticMaskTile
    { ocean_mask, land_mask, biome_mask, uncertainty_mask }
                    ↓
         VisualConsistencyEngine
                    ↓
         VCRenderContext
    { base_color_field, biome_blend_field,
      coastline_gradient_field,
      temporal_stability_field,
      uncertainty_modulation_field }
                    ↓
            D6 Renderer
```

VC produces **numpy arrays only** — no raster output, no GPU calls, no modification of M1, SAL, or D6 core logic.

---

## 2. Module Structure

```
core/vc/
    vc_types.py                  — VCRenderContext, BIOME_BASE_COLORS, constants
    _kernels.py                  — pure-numpy Gaussian blur, morphological ops
    biome_transition.py          — BiomeTransition: hard boundaries → colour gradients
    coastline_smoother.py        — CoastlineSmoother: binary edge → probability band
    temporal_stabilizer.py       — TemporalStabilizer: EMA frame-to-frame continuity
    visual_consistency_engine.py — VisualConsistencyEngine: orchestrator
    __init__.py
    _test_vc.py
```

---

## 3. M1 → VC → D6 Pipeline

### 3.1 Per-Tile Pipeline Steps

```
SemanticMaskTile
       ↓
  Step 1: BiomeTransition.apply_transition()
          biome_mask → base_color_field (H,W,3)
                     + biome_blend_field (H,W)

       ↓
  Step 2: CoastlineSmoother.smooth()
          ocean_mask + uncertainty_mask
          → coastline_gradient_field (H,W) ∈ [0,1]

       ↓
  Step 3: TemporalStabilizer.update_ema_and_stability()
          EMA applied to color_field + coastline
          → temporal_stability_field (H,W) ∈ [0,1]

       ↓
  Step 4: Uncertainty modulation
          uncertainty_mask → gaussian-smoothed softness field

       ↓
  VCRenderContext
```

### 3.2 D6 Consumption

| VCRenderContext field | D6 shader uniform |
|---|---|
| `base_color_field` | `u_baseColor` (tile tint) |
| `biome_blend_field` | `u_biomeBlend` (edge softness) |
| `coastline_gradient_field` | `u_coastGrad` (coast SDF proxy) |
| `temporal_stability_field` | `u_stability` (TAA weight) |
| `uncertainty_modulation_field` | `u_softness` (blur radius) |

---

## 4. Biome Transition Model

### 4.1 Design

Each pixel in the biome_mask is mapped to its base colour from `BIOME_BASE_COLORS`. A Gaussian blur is then applied to the colour field, with width proportional to the mean tile uncertainty.

```
sigma = base_sigma + BLEND_SIGMA_SCALE × uncertainty × 0.5
final_color = lerp(raw_color, blurred_color, blend_field)
```

`blend_field` is highest at biome boundaries (detected via 3×3 local max/min variance) and decays toward tile interiors.

### 4.2 compute_blend() Formula

For a point on the boundary between biome A and B:

```
color_distance = ||rgb_A − rgb_B||₂
conf_factor    = 1 − clamp(confidence / 0.80)
blend          = MIN_BLEND + (MAX_BLEND − MIN_BLEND) × dist × conf_factor
```

- Higher confidence → lower blend (preserve sharp boundary)
- Greater colour distance → wider transition
- Range: [0.05, 0.90]

### 4.3 Test Results

| Scenario | Boundary detected | blend_field mean | Color channel dominance |
|---|---|---|---|
| Dead Sea (all land) | No | 0.050 (minimum) | R(0.520) > B(0.220) ✓ |
| Pacific Ocean (all ocean) | No | 0.050 (minimum) | B(0.440) > R(0.040) ✓ |
| Coastal (50/50 mixed) | Yes | 0.540 | Mixed gradient ✓ |

---

## 5. Coastline Smoothing Model

### 5.1 Design

The binary ocean/land boundary is replaced by a continuous field:

```
land_float = 1.0 − ocean_mask        # 0=ocean, 1=land
sigma      = base_σ + (max_σ − base_σ) × uncertainty
coastline_gradient = gaussian_blur(land_float, sigma)
```

| Parameter | Value |
|---|---|
| base_sigma | 1.2 px |
| max_sigma | 4.0 px |
| Clear ocean uncertainty≈0.18 | σ ≈ 1.7 px |
| Ambiguous coastal uncertainty≈0.43 | σ ≈ 2.4 px |
| High ambiguity uncertainty≈0.85 | σ ≈ 3.6 px |
| Equivalent gradient band width | ~12 px (3σ) |

### 5.2 gradient_edge()

For explicit boundary detection:

```
boundary_band = gaussian_blur(boundary_pixels, sigma=2.4)
normalised = boundary_band / max(boundary_band)
```

Outputs a smooth ridge at the coastline, decaying to zero inland and offshore.

### 5.3 Test Results

| Scenario | Coastline range | Gradient present |
|---|---|---|
| Dead Sea (all land) | [1.000, 1.000] | No (single class) |
| Pacific Ocean (all ocean) | [0.000, 0.000] | No (single class) |
| Coastal 50/50 | [0.000, 1.000] | Yes — span=1.000 ✓ |

The coastal tile shows a full-range smooth transition band — no binary edge artifact.

---

## 6. Temporal Stabilization Model

### 6.1 EMA Algorithm

```
ema_t = α × ema_{t−1} + (1−α) × raw_t
delta_t = |raw_t − ema_{t−1}|
stability = clamp(1.0 − delta / (change_threshold × 5))
```

| Parameter | Value |
|---|---|
| α (alpha) | 0.85 |
| change_threshold | 0.02 |
| Convergence time | ~7 frames |

### 6.2 damp_transition()

Tanh damping for large deltas:

```
damped = tanh(8 × delta)
```

Small deltas (< 0.02) → near-zero damped value (change is suppressed).
Large deltas (> 0.2) → tanh saturates at 1 (change acknowledged but not hidden).

### 6.3 Test Results

| Scenario | Stability | Notes |
|---|---|---|
| Same coastal tile ×7 (EMA warmed up) | 1.000 | EMA converged, delta≈0 |
| Switch to all-ocean | 0.228 | delta across coastline fields, stability drops |
| Delta (stability difference) | **0.772** | Clear signal for TAA weight |

Temporal test confirms: same-state → stability ≈ 1.0; state-switch → stability ≈ 0.23. D6 can use stability as a TAA (temporal anti-aliasing) blend weight to prevent flickering.

---

## 7. Uncertainty-to-Visual Mapping

```
uncertainty_modulation = gaussian_blur(uncertainty_mask, sigma=0.8)
```

This provides a spatially smooth softness weight. In combination with `biome_blend_field`:

| uncertainty | biome_blend | Visual effect |
|---|---|---|
| High + high blend | At boundary | Wide soft gradient transition |
| High + low blend | Interior point | Slight softening, no hard edges |
| Low + any | Any | Crisp colour, minimal softening |

The `uncertainty_modulation_field` is the primary driver for D6's `u_softness` uniform (blur radius in shader), while `biome_blend_field` drives `u_biomeBlend` (interpolation weight in colour LUT lookup).

---

## 8. Core Rules — Verification

| Rule | Implementation | Test confirmed |
|---|---|---|
| No hard edges | Gaussian blur on biome colour field | ✓ blend_field > 0 at all boundaries |
| Uncertainty = softness | sigma driven by margin-based uncertainty_mask mean | ✓ clean ocean no longer max-blurred |
| Coastline = probability band | gaussian_blur on land_float | ✓ span=1.000 for mixed tile |
| Time continuity enforced | EMA α=0.85 across frames | ✓ Δstability=0.772 when perturbed |

---

## 9. Limitations

### 9.1 No Inter-Tile Continuity

VC operates tile-by-tile. Biome boundaries that cross tile edges may show discontinuities at tile seams. The blur kernel is padded with edge-replication (`mode='edge'`), which reduces but does not eliminate seam artifacts.

### 9.2 Pure Python Convolution

The `_kernels.py` Gaussian blur uses a nested Python loop (O(H × W × k²)). At 8×8 test tiles this is imperceptible, but at production 1024×1024 tiles it would be very slow. Vectorised numpy implementation (scipy.ndimage or stride-based) is required for production.

### 9.3 EMA Requires Per-Location State

`TemporalStabilizer` maintains an EMA dict keyed by field name. If the tile being processed changes location between frames (e.g., camera pan), the EMA must be reset or location-keyed. Current API provides `reset()` for this but doesn't auto-detect location change.

### 9.4 Entropy Still Saturates

SAL entropy still sits near the 9-class maximum, but VC now receives margin-derived uncertainty from M1/Binding. Remaining risk is calibration: `_CLEAR_WINNER_MARGIN = 0.08` may need tuning once real signal providers replace synthetic tests.

---

## 10. GPU Shader Mapping (Future)

When VC moves to GPU execution:

| Current CPU field | GPU equivalent |
|---|---|
| `gaussian_blur(land_float, σ)` | Gaussian blur pass (render target) or SDF generation |
| `biome_blend_field` | Bilinear-weighted colour LUT sample |
| `temporal_stability_field` | TAA accumulation buffer weight |
| `uncertainty_modulation_field` | Blur radius uniform per tile region |
| EMA in TemporalStabilizer | TAA history buffer (ping-pong RT) |

The VC pipeline is GPU-friendly: all operations are separable convolutions + linear interpolations, mapping directly to existing real-time rendering techniques.

---

## 11. API Reference

```python
from core.vc import VisualConsistencyEngine, VCRenderContext
from core.m1 import M1Pipeline, TileBBox
from core.binding import TemporalState

# Build M1 tile
pipeline = M1Pipeline(signal_provider=my_signals, tile_px_size=32)
tile = pipeline.run_tile(TileBBox(lon_min=34.5, lon_max=36.5,
                                  lat_min=30.5, lat_max=32.5))

# Run VC
vce = VisualConsistencyEngine(temporal_alpha=0.85)
ctx: VCRenderContext = vce.process(tile)

# Inspect output
print(ctx.coastline_gradient_field)     # (32, 32) float32, 0=ocean→1=land
print(ctx.temporal_stability_field)     # (32, 32) float32, 1=stable
print(ctx.mean_temporal_stability())    # scalar summary
print(ctx.has_gradient_transition())    # True if coastline gradient exists

# Re-apply for second frame (EMA advances)
ctx2 = vce.process(tile)               # stability=1.0 (same input)
ctx3 = vce.process(ocean_tile)         # stability drops — location changed
```
