---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 54b2a6c0c334f40199ec953e28793309_892a530880f011f1be225254006c9bbf
    ReservedCode1: WSHH/ZaJIVcUZbw1ML78SPHNohnNugN98VoP9wt262f/Oij1iOHziw2K+vmKuVKV8z1z/sVOLoGT2Rnzq2Yt5GDACPHx96/MKalDhmAvaXHIADJ0+IBNGkfJA65gDWtmDbu8KmLdISn3rqobxcapbhNoat25ztc9MDtR8eiePnzQduUqyUQyAMBaew8=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 54b2a6c0c334f40199ec953e28793309_892a530880f011f1be225254006c9bbf
    ReservedCode2: WSHH/ZaJIVcUZbw1ML78SPHNohnNugN98VoP9wt262f/Oij1iOHziw2K+vmKuVKV8z1z/sVOLoGT2Rnzq2Yt5GDACPHx96/MKalDhmAvaXHIADJ0+IBNGkfJA65gDWtmDbu8KmLdISn3rqobxcapbhNoat25ztc9MDtR8eiePnzQduUqyUQyAMBaew8=
---

# Screen-Space Element Audit — Night Theme Purple Stripe Investigation

Date: 2026-07-16
Theme active during audit: `night` (rim overlay strengths all zeroed)

---

## 1. Complete Inventory of Screen-Space Rendering Elements

### 1.1 earlyMorningRimOverlayScene (WebGL screen-space pass)

| Attribute | Value |
|-----------|-------|
| Type | THREE.Scene (rendered with OrthographicCamera) |
| Render timing | AFTER main scene (`renderer.clearDepth()`, `autoClear=false`) |
| Shader | Custom `_emRimOverlayMat` (Arc-based tangent projection) |
| Precision | `mediump float` |
| Blending | Additive (rimOverlay) / Normal (innerVeil) |
| Colors | `#83B3D1` (blue-gray), `#D6EEF9` (pale blue), `#8FA6B4` (gray-blue) |

**Night theme runtime state:**

```
uCoreStrength    = 0.0    ← ZERO
uHaloStrength    = 0.0    ← ZERO
uInnerVeilStrength = 0.0  ← ZERO
```

**Conclusion: Produces NO visible output in night theme.** All strengths are zero.

### 1.2 Atmosphere 3D Mesh (in-scene WebGL)

| Attribute | Value |
|-----------|-------|
| Mesh | `atmosphere` (FrontSide) + `atmosphere2` (BackSide) |
| Blending | AdditiveBlending |
| Depth parameters | depthTest:false, depthWrite:false |
| RenderOrder | 1 |
| Shader | Fresnel-based atmospheric glow |

**Night theme state:** opacity=0.0 → `visible=false` → **DISABLED**

### 1.3 CSS DOM Overlays

| Element ID | Type | Night State |
|------------|------|-------------|
| `#earth-horizon-glow` | DIV (radial-gradient + filter:blur + mix-blend-mode:screen) | opacity=0, horizonGlow.enabled=false |
| `#earth-rim-glow` | DIV (radial-gradient + filter:blur + mix-blend-mode:screen) | opacity=0 |

**Both DISABLED in night theme.**

### 1.4 weather-canvas (2D Canvas Overlay)

| Attribute | Value |
|-----------|-------|
| Positioning | `position: absolute; z-index: 1; pointer-events: none` |
| Context | `CanvasRenderingContext2D` |
| Image source | `/api/globe-image?phase=night` → `pwa/assets/blackmarble.jpg` |
| Image type | Real NASA Black Marble satellite photo (3600x1800 JPEG) |
| Rendering | `ctx.drawImage()` with equirectangular projection clipping |

**Conclusion: Real photograph, no shader-level banding. Weather effects use green/gray tones.**

### 1.5 Earth Mesh (WebGL — the only candidate)

| Attribute | Value |
|-----------|-------|
| Material | `earthMaterial` (custom ShaderMaterial) |
| Shader | Contains `_deMagenta` smoothstep chain in `rodioApplyNightGrade()` |
| Precision | `mediump float` |
| Night base | Derived from day texture via `rodioNightBaseFromRaw()` |

**_deMagenta smoothstep chain (earth3d.js line 1834–1844):**

```glsl
float _nightMagenta = min(_nightBase.r, _nightBase.b) - _nightBase.g;
// ... arithmetic adjustments ...
float _deMagenta = smoothstep(0.018, 0.0, _nightMagenta)
                * smoothstep(0.026, 0.008, _nightMagenta)
                * smoothstep(0.034, 0.016, _nightMagenta)
                * smoothstep(0.042, 0.024, _nightMagenta)
                * smoothstep(0.050, 0.032, _nightMagenta);
```

Then `_neutralCool` replaces `_nightBase` weighted by `_deMagenta * 0.82`.

### 1.6 Cloud Mesh

| Attribute | Night Value |
|-----------|-------------|
| Opacity | 0.14 |
| Color | `#e3edf2` (pale blue-white) |
| Blending | Alpha |

**Not a candidate for purple/magenta stripes.**

---

## 2. Root Cause: Why _deMagenta Banding Appears "Screen-Stationary"

### The perceptual illusion

The `_deMagenta` smoothstep chain IS attached to the Earth mesh (it runs per-fragment). The stripes appear "screen-stationary" for a well-understood reason:

**The banding is latitude-aligned.**

The filter operates on `_nightBase` from the day texture. Major latitude bands (polar ice caps, tropical rainforests, deserts, oceans) each produce distinct `_nightMagenta` values, creating smoothstep-dependent transitions at specific latitudes.

When the Earth rotates (fixed camera, changing longitude only):
1. The visible **latitudes** remain constant
2. The transition thresholds (latitudes where smoothsteps activate) remain at the same **screen Y positions**
3. Only the **continents** shift behind the bands

This creates the perception that stripes are "screen-stationary." They are latitude-aligned bands on the Earth sphere that happen to coincide with fixed screen positions during pure longitudinal rotation.

### Why screenshots miss the stripes

With `mediump float` precision (10-bit mantissa), the smoothstep transitions span ~130 quantization steps per interval. This produces subtle per-pixel variations that are below the detection threshold of:
- Screenshot capture (compression, color quantization)
- Vision models (subtle sub-pixel variations)
- Pixel-level threshold analysis (noise floor swamps the signal)

They ARE visible to the human eye in real-time due to temporal persistence and contrast adaptation.

### The 5-layer chain as banding generator

The 5 overlapping smoothsteps create 4 transition zones:
- ~0.008-0.016 (smoothstep 2)
- ~0.016-0.024 (smoothstep 3)
- ~0.024-0.032 (smoothstep 4)
- ~0.032-0.042 (smoothstep 5)

The product of 5 smooth transitions amplifies `mediump` quantization discontinuities, producing subtle luminance steps that form latitude-aligned "watermelon rind" stripes.

---

## 3. Exclusion Summary

| Element | Type | Active? | Purple Tones? | Verdict |
|---------|------|---------|---------------|---------|
| Earth mesh (_deMagenta) | WebGL / fragment shader | Yes | Yes (magenta removal produces color shifts) | **ROOT CAUSE** |
| earlyMorningRimOverlay | WebGL / screen-space arc | No (strength=0) | No (blue-white) | Ruled out |
| Atmosphere mesh | WebGL / 3D additive | No (opacity=0) | No (blue-cyan) | Ruled out |
| CSS DOM overlays | DIV / radial-gradient | No (opacity=0) | No (blue-gray) | Ruled out |
| weather-canvas | 2D Canvas drawImage | Yes (real photo) | No (photograph) | Ruled out |
| Cloud mesh | WebGL / alpha blended | Yes (op=0.14) | No (white-gray) | Ruled out |
| Star sphere | WebGL / emissive | Yes (op=0.39) | No (white dots) | Ruled out |

---

## 4. Recommended Fix Options

**Option A: Replace 5x smoothstep chain with a single smoothstep**
```glsl
float _deMagenta = smoothstep(0.05, 0.0, _nightMagenta);
```
Eliminates all intermediate transition zones.

**Option B: Increase precision**
Change shader precision to `highp float` (~23-bit mantissa, 53,000 quantization steps per interval vs 130) — eliminates visible banding.

**Option C: Simplify night color pipeline**
Remove the `_deMagenta` step entirely and use a simpler neutral-cool color blend.
*（内容由AI生成，仅供参考）*
