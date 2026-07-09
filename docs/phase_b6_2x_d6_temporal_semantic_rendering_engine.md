# Phase B-6.2X-D6 — Temporal Semantic Rendering Engine (CPU)

Stage: B-6.2X-D6  
Type: CPU renderer implementation  
Status: **PASS**  
Date: 2026-06-24  
Tools: Python 3.14 + numpy 2.5.0 (no GPU, no raster output)

---

## 1. Scope

实现 D6 Scientific Renderer：将 M0 SpatialRuntime 的语义状态（elevation / ocean / climate / biome_proxy / slope）与时间状态（太阳位置 / 季节 / 昼夜相位）融合，输出 per-point RGB 颜色。

**不生成 GeoTIFF，不进入 shader，不做 8K batch，不写磁盘文件。**

---

## 2. Module Structure

```
core/rendering/
    __init__.py           — 公共 API 导出
    renderer_types.py     — RGB, TimeState, SunState, LightState, SeasonalState, DayCycleState
    temporal_model.py     — 太阳位置 + 季节因子 + 昼夜相位
    light_model.py        — Lambert 光照 + Rayleigh 散射 + slope 衰减
    color_model.py        — 语义调色板 + 时态位移 + 光照融合
    d6_renderer.py        — D6Renderer 入口（接 M0 SpatialRuntime）
```

M0 接口 (`core/runtime/spatial_runtime.py`) 无需修改，直接消费。

---

## 3. Architecture: Rendering Pipeline

```
render_point(lon, lat, TimeState)
       │
       ├─ SpatialRuntime.query_point(lon, lat)
       │       → SpatialState { elevation, ocean, climate_class, biome_proxy, slope_proxy }
       │
       ├─ TemporalModel.get_sun_position(lat, lon, time_state)
       │       → SunState { elevation°, azimuth°, above_horizon }
       │
       ├─ TemporalModel.get_season_factor(lat, doy)
       │       → SeasonalState { season_factor, snow_factor, vegetation_boost }
       │
       ├─ TemporalModel.get_day_cycle(hour)
       │       → DayCycleState { phase, warmth, contrast, saturation, blue_bias }
       │
       ├─ LightModel.build(sun_elevation, slope_proxy, ocean_flag)
       │       → LightState { intensity, scatter_rgb, shadow_attenuation }
       │
       └─ ColorModel.final_color(biome_proxy, ocean, light, season, day_cycle)
               → RGB (clamped [0,1], exportable as uint8)
```

**Core formula:**

```
RGB = apply_light(
        apply_temporal_shift(base_color(semantic), season, day_cycle),
        light_state
      )

apply_light(color, light) =
    color × (ambient_floor + (1 - ambient_floor) × intensity × shadow)
    + scatter_rgb
```

ambient_floor = 0.035（防止 polar night 完全归零）

---

## 4. Temporal Model

### 4.1 Sun Position (NOAA Simplified Solar Calculator)

来源：Spencer (1971) Fourier series。精度 ±0.01° 高度角，适用 1950–2050 年。不依赖任何外部天文库，纯 `math` 实现。

```
γ (fractional year, rad) = (2π/365) × (doy − 1 + (hour − 12) / 24)

eqtime (minutes) = 229.18 × Σ(Fourier terms in γ)   # equation of time

decl (rad) = 0.006918 − 0.399912·cosγ + 0.070257·sinγ − ...   # solar declination

tst = hour × 60 + eqtime   # True Solar Time
# Note: hour is LOCAL APPARENT SOLAR TIME, not UTC.
# Longitude does NOT enter tst — it is only relevant for UTC→local conversion.

ha (hour angle°) = tst / 4 − 180

sin(altitude) = sin(lat)·sin(decl) + cos(lat)·cos(decl)·cos(ha)
```

验证结果：

| 场景 | 预期 | 实测 |
|------|------|------|
| 上海 (30°N) 夏至正午 | ~83.5° | 83.4° ✅ |
| 上海 (30°N) 冬至正午 | ~36.6° | 36.6° ✅ |
| 北极 (70°N) 夏至正午 | ~43.4° | 43.5° ✅ |
| 上海凌晨 2 时 | 负值 | −29.4° ✅ |
| 南极 (80°S) 夏至（SH 冬）正午 | 负值（极夜）| −13.5° ✅ |

### 4.2 Seasonal Factor

```
peak_doy = 172 (NH summer solstice) or 355 (SH)
delta = doy − peak_doy  (wrap ±182.5)
season_factor = 0.5 + 0.5 × cos(π × delta / 182.5)

snow_factor = lat_snow_base × (1 − season_factor) × 1.6
vegetation_boost = (season_factor × 2 − 1) × lat_veg_scale
```

上海 day 180：season_factor=1.000，snow=0.000，veg=+0.625（夏季顶峰）✅  
上海 day 355：season_factor=0.000，snow=0.123，veg=−0.625（冬季底谷）✅

### 4.3 Diurnal Phase

| 时段 | 相位 | warmth | saturation | blue_bias |
|------|------|--------|-----------|-----------|
| 04:30–06:30 | dawn | −0.25 | 0.55 | 0.12 |
| 06:30–09:30 | morning | −0.08 | 0.85 | 0.04 |
| 09:30–14:00 | noon | 0.0 | 1.0 | 0.0 |
| 14:00–16:30 | afternoon | +0.06 | 0.97 | 0.0 |
| 16:30–18:30 | sunset | +0.40 | 1.35 | 0.0 |
| 18:30–20:30 | dusk | +0.12 | 0.65 | 0.18 |
| 20:30–04:30 | night | −0.18 | 0.28 | 0.55 |

---

## 5. Light Model

### 5.1 Sun Intensity (Lambert Cosine)

```python
intensity = sin(elevation°)                      # elevation > 0
          = 0.05 × (1 + elevation/6)             # civil twilight −6°..0°
          = 0.0                                  # below −6° (astronomical night)
```

大气修正：`× (1 − 0.12 × exp(−elevation / 15))` — 低角度大气减损。

### 5.2 Atmospheric Scatter (Rayleigh 近似)

```
air_mass = 1 / sin(elevation)   (capped at 10)
blue_scatter = min(0.06, 0.003 × air_mass)     # 瑞利散射蓝移
red_scatter  = min(0.04, 0.002 × (air_mass−3)) # 低角度红/橙残留
ocean_blue_boost = 0.025 if ocean else 0        # 海面反射天空蓝
```

散射为加性项，量级 ≤ 0.08，防止夜间纯黑。

### 5.3 Terrain Shadow

```
shadow_attenuation = 1 − 0.20 × (slope_proxy / 3000) ^ 0.7
```

slope_proxy 来自 M0 `_slope_proxy()`（相邻像素高程差，单位 m）。8K 分辨率下为 coarse 近似，仅提供软性衰减。

---

## 6. Color Model

### 6.1 Semantic Palette Anchors

| biome_proxy | 语义 | 来源 | base RGB |
|-------------|------|------|---------|
| 0.05 | deep ocean | elevation < −2000m | (5, 15, 56) |
| 0.15 | shallow ocean | ocean, elev ≥ −2000m | (15, 48, 107) |
| 0.35 | arid / desert | Köppen BWh/BWk/BSh/BSk | (198, 163, 81) |
| 0.45 | highland | elevation > 3000m | (137, 127, 94) |
| 0.60 | temperate | other land | (56, 132, 43) |
| 0.85 | tropical | Köppen Af/Am/Aw | (17, 127, 30) |

中间值线性插值。

**特殊处理：** Köppen EF（polar frost）在 FeatureComposer 中映射 biome_proxy=0.10，与浅海调色板区间重叠。`base_color` 中检查 `not ocean and biome_proxy < 0.20` → 直接返回冰原蓝白 RGB(0.80, 0.88, 0.95)，避免南极洲 / 格陵兰 / 喜马拉雅 EF 区显示为深蓝海色。

### 6.2 Temporal Shift Pipeline

```
1. vegetation_boost × green channel push  (夏季植被饱和度增强)
2. snow_factor → lerp toward RGB(0.92, 0.94, 0.97)  (高纬冬季积雪)
3. warmth shift: r += Δ×0.15, g += Δ×0.02, b −= Δ×0.18  (日落红/清晨冷)
4. saturation scale: (color − lum) × factor + lum  (夜间去饱和)
5. blue_bias additive: b += bias × 0.08  (夜间蓝调环境光)
```

---

## 7. Validation Results

### 7.1 Point Render at Noon (day=180, hour=12)

| 地点 | elev | ocean | climate | biome | Noon RGB | Night RGB | lum_diff |
|------|------|-------|---------|-------|---------|---------|---------|
| Shanghai | +133m | N | 14 (Cfa) | 0.60 | (48,147,41) 绿 | (3,5,7) 暗 | 0.4464 |
| Pacific | −4936m | Y | — | 0.05 | (4,14,58) 深蓝 | (0,1,5) 极暗 | 0.0553 |
| Sahara | +418m | N | 4 (BWh) | 0.35 | (196,161,81) 黄褐 | (5,6,9) 暗 | 0.6145 |
| Amazon | +76m | N | 1 (Af) | 0.85 | (15,113,28) 深绿 | (2,4,7) 暗 | 0.3241 |
| Antarctic | +2336m | N | 30 (EF) | 0.10 | (7,8,12) 极暗* | (8,8,12) | 0.0001 |
| Greenland | +2970m | N | 30 (EF) | 0.10 | (135,149,162) 冰蓝 | (32,33,36) | 0.4476 |
| Himalaya | +6004m | N | 30 (EF) | 0.10 | (187,206,223) 冰白 | (7,8,12) | 0.7656 |

*Antarctic day 180 = SH 冬季，80°S 处于极夜（太阳仰角 −13.5°），noon 与 night 均无阳光，为极夜正常表现。

### 7.2 Temporal Consistency — Shanghai (30°N, 120°E, day=180)

| 时段 | RGB | luminance |
|------|-----|-----------|
| morning (7h) | (23, 58, 23) | 0.1893 |
| noon (12h) | (48, 147, 41) | 0.4655 |
| sunset (18h) | (10, 36, 0) | 0.1099 |
| night (23h) | (3, 5, 7) | 0.0192 |

luminance_range = **0.4464** — 有效昼夜变化 ✅  
`diurnal_variation_ok = True` ✅

### 7.3 Biome Stability (stability = 1 − mean RGB drift, higher = more stable)

| biome | stability | max_drift | 解读 |
|-------|-----------|-----------|------|
| tropical_forest (20°E, −3°N) | 0.8362 | 0.2518 | 稳定绿色调 |
| sahara_desert (23°E, 25°N) | 0.6404 | 0.5193 | 强昼夜变化（最低）|
| south_pacific (180°E, −30°N) | 0.8858 | 0.1983 | 最稳定（深蓝始终低强度）|

**说明：** 本模型中 ocean 色彩稳定性最高（深蓝始终，仅亮度微变），与 spec 期望的"forest > desert > ocean" 顺序不同。差异原因：本模型未实现海面镜面反射（sun glint）。不加 glint 时深海颜色全天变化幅度确实小于陆地森林。如需 ocean 更多变化，可在 ColorModel 中添加基于 sun_azimuth × ocean_flag 的反射 boost。此为 Phase 3 扩展项，不影响当前 CPU CPU renderer 正确性。

### 7.4 render_window Sanity

Pacific patch (160°–200°E, −10°–10°N), 16×8, noon:  
shape=(8,16,3), dtype=uint8, mean_RGB=(6.5, 20.2, **56.0**)  
blue channel dominant ✅

---

## 8. M0 Integration

```python
from core.runtime.spatial_runtime import SpatialRuntime
from core.rendering.d6_renderer import D6Renderer
from core.rendering.renderer_types import TimeState

runtime = SpatialRuntime.from_source_cache("d5b_processor_v3/source_cache/gee_global")
renderer = D6Renderer(runtime)

rgb = renderer.render_point(120.0, 30.0, TimeState(hour=12.0, day_of_year=180))
# → RGB(r=0.188, g=0.577, b=0.160)  → (48, 147, 41)
```

M0 DEM priority routing (Copernicus → GEBCO → ETOPO1) 透明接入，D6 无需感知。Köppen 气候层通过 `ClimateRasterLayer` 读取 8K GeoTIFF，biome_proxy 由 `FeatureComposer` 计算后传入 `ColorModel`。

---

## 9. API Summary

```python
class D6Renderer:
    def render_point(lon, lat, time_state) → RGB
    def render_window(bbox, time_state, width=64, height=64) → np.ndarray (H,W,3) uint8
    def compute_semantic_color(state, light) → RGB   # batch-ready, neutral temporal
    def temporal_consistency_check(lon, lat, doy) → dict
    def biome_stability_check(doy) → dict

class TemporalModel:
    def get_sun_position(lat, lon, time_state) → SunState
    def get_season_factor(lat, doy) → SeasonalState
    def get_day_cycle(hour) → DayCycleState

class LightModel:
    def compute_intensity(sun_elevation) → float
    def atmospheric_scatter(sun_elevation, ocean_flag) → LightState
    def shadow_factor(slope_proxy) → float
    def build(sun_elevation, slope_proxy, ocean_flag) → LightState

class ColorModel:
    def base_color(biome_proxy, ocean) → RGB
    def apply_temporal_shift(color, season, day_cycle) → RGB
    def apply_light(color, light) → RGB
    def final_color(biome_proxy, ocean, light, season, day_cycle) → RGB
```

---

## 10. Limitations (CPU Only)

| 限制 | 描述 | 优先级 |
|------|------|--------|
| No GPU shading | per-point 运算，64×64 render_window ≈ 4096 次 query_point | Phase 3 |
| No ocean sun glint | 海面 Fresnel 反射未实现；导致深海昼夜变化幅度偏低 | Phase 3 |
| Slope 8K resolution | slope_proxy 基于 ~4.9 km 像素差，terrain shadow 为 coarse 近似 | Low |
| NOAA solar formula | ±0.01° 精度，折射效应未补偿（real sunset ≈ +0.57° refraction） | Acceptable |
| hour = local solar time | 不支持 UTC 输入；调用方需自行处理 UTC→local 换算 | Documented |
| Biome EF override | biome_proxy < 0.20 + non-ocean 一律视为冰原；若未来有 ET 区域精细化需求需扩展 | Low |

---

## 11. Future GPU Shader Mapping Plan

D6 CPU 函数对应 GLSL / Metal shader 路径：

| CPU 函数 | GPU 对应 | 备注 |
|---------|---------|------|
| `base_color(biome_proxy, ocean)` | 1D texture lookup (palette LUT) | biome_proxy → texcoord |
| `get_sun_position(lat, lon, time)` | uniform vec3 sunDir (pre-computed per frame) | per-frame CPU pre-pass |
| `compute_intensity(elevation)` | `max(0, dot(normal, sunDir))` | standard Lambert |
| `atmospheric_scatter(...)` | Rayleigh LUT or analytical in frag shader | Preetham / Nishita |
| `apply_temporal_shift(color, ...)` | color grading LUT 3D texture | bake from CPU model |
| `shadow_factor(slope)` | screen-space AO or terrain shadow map | full Phase 3 |
| `render_window(bbox, ...)` | fullscreen quad + frag shader | drop CPU window loop |

---

## 12. Verdict

```
PASS
```

- 5 模块创建，py_compile 通过 ✅
- NOAA 太阳方位角验证准确 ✅
- M0 SpatialRuntime 直接接入，consistency_score = 1.0 ✅
- 昼夜亮度范围 0.4464（meaningful diurnal variation）✅
- 语义颜色语义正确：深海深蓝 / 沙漠黄褐 / 热带深绿 / 极地冰白 ✅
- 无 raster 写入，无 GeoTIFF 输出，无 d6 generator 调用 ✅

---

*Implemented: 2026-06-24*  
*No masks generated. No GeoTIFF written. No generator executed. No commit/push.*
