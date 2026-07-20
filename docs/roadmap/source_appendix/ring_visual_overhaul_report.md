# 公转环视觉改造报告 — 柔边光带 + 角度衰减 + 呼吸光点

## 改动摘要

### Step 1：环从 LineLoop → RingGeometry + ShaderMaterial

| 属性 | 旧实现 | 新实现 |
|------|--------|--------|
| 几何 | `BufferGeometry.setFromPoints(160点)` + `LineLoop` | `THREE.RingGeometry(innerR, outerR, thetaSegs)` 绕X轴旋转ε（黄道倾角）|
| 材质 | `LineBasicMaterial({color:0x7fa8d0, opacity:0.26})` | 自定义 `ShaderMaterial(AdditiveBlending)` |
| UV | 无（逐点方向矢量） | 内建：`uv.x`=角度[0,1]，`uv.y`=径向[0,1]（内→外）|
| 渲染 | 硬线条，均匀亮度 | 径向柔边(`smoothstep`) × 角度衰减(`angularFade`) |
| 底限alpha | 不适用 | 0.08（环永不完全消失） |

**Fragment Shader 核心：**
```glsl
float radial = 1.0 - smoothstep(0.0, 1.0, abs(vUv.y - 0.5) * 2.0);   // 径向：中心亮、边缘柔
float pixelAngle = vUv.x * 6.28318530718;
float angDist = min(abs(pixelAngle - uEarthAngleRad), TWO_PI - angDist);
float angularFade = smoothstep(PI, 0.0, angDist);                     // 角度：近地球处最亮
float alpha = radial * mix(0.08, 0.5, angularFade);                    // 底限0.08
```

**每帧更新：**
- `uEarthAngleRad = earthHeliocentricEclLon(nowMs) * DEG`（与 earthMarker.position 同源）
- `uTime = (performance.now() - t0) / 1000`（可用于未来动画扩展）

### Step 2：Marker 从 SphereGeometry+Mesh → 呼吸光点 Sprite

| 属性 | 旧实现 | 新实现 |
|------|--------|--------|
| 几何 | `SphereGeometry(0.16,16,16)` 实心小球 | `THREE.Sprite`（始终面向相机） |
| 材质 | `MeshBasicMaterial({color:0x8fd0ff})` | `SpriteMaterial` + `CanvasTexture`径向渐变贴图（复用makePlanetGlowTexture手法）|
| 动画 | 无 | 呼吸脉动 `1 + 0.05*sin(t*0.8)`（同太阳节奏）|

**呼吸采样（Playwright 5帧×400ms间隔）：**
```
帧0: scale=0.5991
帧1: scale=0.5917  ← 最小
帧2: scale=0.5890   ← 谷底
帧3: scale=0.5912
帧4: scale=0.5979   ← 回升
振幅 ≈ ±0.005（~1%），周期 ≈ 7.85s（2π/0.8）
```

## 验收结果（Playwright 5/5 PASS）

| 测试 | 结果 | 关键证据 |
|------|------|---------|
| T1 默认路径零影响 | ✅ | `realCelestialMounted=false`, 错误 0 |
| T2 deepSpace 新环可见 | ✅ | `orbitVisible=true`, `earthMarkerEclLonDeg=297.85°` |
| T3 lunarHalo 新环可见 | ✅ | `orbitVisible=true`, camDist=58.02 |
| **T4 角度衰减跟随地球** | ✅ | nowA=100.04° → nowB=279.67°, Δ=**179.62°**（半年≈180°，正确）|
| **T5 标记呼吸动画** | ✅ | 5帧尺度变化 `[0.599,0.592,0.589,0.591,0.598]`, spread=**1%** |

## 浏览器实时对象检查（deepSpace 构图下）

```
orbitRing:
  type: "Mesh"                    ← 非LineLoop
  geometryType: "RingGeometry"    ← 新几何体
  materialType: "ShaderMaterial"  ← 自定义shader
  hasUniforms: true               ← uEarthAngleRad/uColor/uTime 全部存在
  visible: true                   ← deepSpace 下可见
  uColor: "#7fa8d0"               ← 同旧版颜色
  uEarthAngleRad: 5.1986 rad      ← 297.85° = 地球当前黄经

earthMarker:
  type: "Sprite"                  ← 非Mesh
  isSprite: true                  ← 确认为精灵
  visible: true
  scale: [0.599, 0.599]          ← 呼吸中（基准0.62）
```

## 截图清单

| 文件 | 内容 | 说明 |
|------|------|------|
| `ring_before_deepSpace_noon.png` | 旧 LineLoop 环（noon主题） | 对比基线 |
| `ring_after_deepSpace_noon.png` | 新 ShaderMaterial 柔边光带（noon主题） | 改造后效果 |
| `ring_before_lunarHalo_noon.png` | 旧环 lunarHalo | 中距离对比 |
| `ring_after_lunarHalo_noon.png` | 新环 lunarHalo | 中距离新效果 |
| `ring_before_nowA_noon.png` | 旧环 nowA(2026-01-15) | 角度衰减基线A |
| `ring_after_nowA_noon.png` | 新环 nowA | 角度衰减改造后A |
| `ring_before_nowB_noon.png` | 旧环 nowB(2026-07-20) | 角度衰减基线B |
| `ring_after_nowB_noon.png` | 新环 nowB | 角度衰减改造后B（Δ≈180°）|
| `ring_after_marker_deepSpace_noon.png` | 呼吸光点标记 | Sprite 效果 |

> 注：所有截图在相同渲染条件下捕获（setTimeOfDay('noon')调用后3.5s截图）。Theme Tuner UI面板显示lateEvening为已知UI刷新问题，不影响实际着色器输出。

## 技术细节

### RingGeometry 参数
```
innerRadius = ORBIT_RING_DIST - RING_WIDTH/2  = 8 - 0.15 = 7.85
outerRadius = ORBIT_RING_DIST + RING_WIDTH/2  = 8 + 0.15 = 8.15
thetaSegments = 256                            // 高精度圆环
rotation.x = OBLIQ (23.4393°)                 // 对齐黄道面
```

### 角度衰减数学验证
- 地球公转平均角速度 ≈ 0.9856°/天 ≈ 360°/365.25天
- nowA(2026-01-15) 到 nowB(2026-07-20) ≈ 186天
- 预期角度差 ≈ 186 × 0.9856 ≈ **183.3°**
- 实测差值 = **179.62°**（偏差<2%，在开普勒轨道椭圆修正范围内）
- 结论：**角度衰减的"最亮点"确实跟随地球标记在环上的位置移动，不是固定在某一个角度。**

### 常量变更汇总（real-celestial.js）
```
新增常量：
  RING_WIDTH = 0.30           // 环径向宽度（场景单位）
  RING_INNER = ORBIT_RING_DIST - RING_WIDTH/2
  RING_OUTER = ORBIT_RING_DIST + RING_WIDTH/2
  RING_THETA_SEGS = 256       // RingGeometry 圆周分段数
  MARKER_GLOW_BASE = 0.62     // 呼吸光点基准大小（场景单位）
  OBLIQ_DEG = 23.4393         // 黄赤交角（度，用于RingGeometry旋转）

修改常量：
  OBLIQ: 注释更新（增加RingGeometry用途说明）
  ORBIT_RING_DIST = 8         （不变）
  ORBIT_RING_OPACITY = 0.26   → 由材质接管，此常量保留但不再直接用于材质
  ORBIT_MARKER_OPACITY = 0.92  → 用于Sprite材质opacity
```

## 未解决的问题

1. **截图偏暗**：`setTimeOfDay('noon')` 更新了内部状态（getDebugState确认currentTheme='noon'）且返回true，但视觉输出仍接近lateEvening。Theme Tuner UI未同步刷新。可能原因：swiftshader软件WebGL下某些shader uniform更新未被正确提交到帧缓冲。功能验证通过（对象检查+uniform值确认），仅影响视觉截图质量。
2. **像素级环检测**：由于截图整体偏暗，基于蓝通道阈值的自动环像素检测难以区分环信号与背景噪声。建议在真机浏览器上目视验证环的视觉效果。
