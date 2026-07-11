---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 54b2a6c0c334f40199ec953e28793309_f03f8b1e7ce411f1a75b525400826444
    ReservedCode1: BsDcfFV4PjdIMR9PcHPJUpfMcDo62F3uagXxA6DjAXh3c3Gt26/3Lwn4ZdUzPH3TFcKCV3vMNzCF5R97KlvND77JtNCuNz8wD9fRXnZ9xg2ScglRRgFj3gDXDAwL7BkqdApOmtsiZ053MXGJA6ocfgP+WEXwatqZNz+dGUQAuwMISFApd1+skqDR4H0=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 54b2a6c0c334f40199ec953e28793309_f03f8b1e7ce411f1a75b525400826444
    ReservedCode2: BsDcfFV4PjdIMR9PcHPJUpfMcDo62F3uagXxA6DjAXh3c3Gt26/3Lwn4ZdUzPH3TFcKCV3vMNzCF5R97KlvND77JtNCuNz8wD9fRXnZ9xg2ScglRRgFj3gDXDAwL7BkqdApOmtsiZ053MXGJA6ocfgP+WEXwatqZNz+dGUQAuwMISFApd1+skqDR4H0=
---

# E7 — 相机 / 地球朝向审计 & 预设参数草案

> **产出日期**：2026-07-11  
> **范围**：只读审计 + 参数设计草案。不写实现代码，不做转场动画，不碰音乐/情绪联动，不改现有定位逻辑。  
> **下一步**：RW 审阅后决定实现路径。

---

## 一、分支清理

- **本地** `tune-earlyMorning-v1`：已删除（was f75a3fc）
- **远端** `origin/tune-earlyMorning-v1`：远端本就不存在，无需操作

当前分支状态干净，仅保留 `exp/b6-2x-source-cache-setup`（27 commits）一个独有分支。

---

## 二、只读审计：地球朝向 / 相机逻辑

### 2.1 相机初始化

```
pwa/earth3d.js L250-252
```

- 相机类型：`PerspectiveCamera(28, 1, 0.1, 1000)`
- 初始位置：`(0, 0, 4.8)` —— 地球半径 = 2（R=2 的球体），相机在 Z 轴正方向，距球心 4.8 单位
- 初始朝向：`lookAt(0, 0, 0)` —— 注视球心

**关键事实**：相机在世界空间的 position 从不被核心逻辑移动（只有 `_AUDIT_VIEW_ANGLES` debug 系统会改）。"视角变化"完全通过旋转地球（`earth.quaternion`）来实现——地球转，相机不动。

### 2.2 地球朝向核心：`getTargetOrientation()`

```
pwa/earth3d.js L4799-4828
```

输入参数：
- `targetDirOverride`：可选，若传入则覆盖默认的 `visualTargetDir`

执行流程：

```
1. 读取 window.__rodioVisualState.lon/lat（默认上海 121.47°E, 31.23°N）
   ↓
2. lonLatToVector3(lon, lat) → targetPoint（地球表面该经纬度对应的球面单位向量）
   ↓
3. lonLatToNorthTangent(lon, lat) → sourceNorth（该点指向北极的切向）
   ↓
4. targetNormal = targetDirOverride || visualTargetDir（要"朝向相机"的方向）
   ↓
5. 将世界 Y 轴投影到 targetNormal 的垂直平面上 → targetNorth
   ↓
6. quaternionFromBasis(targetPoint, sourceNorth, targetNormal, targetNorth)
   → 返回使地球旋转到"targetPoint 对齐到 targetNormal 方向"的四元数
```

**本质**：`getTargetOrientation()` 计算一个四元数，使得指定经纬度的地球表面点（如上海）"面向"相机方向（即 `visualTargetDir`）。经纬度决定"哪个城市在屏幕中央"，`visualTargetDir` 决定"屏幕前方对应地球的哪个方向"。

`visualTargetDir` 由 `updateVisualTargetDir()`（L2417-2431）计算：通过 `VISUAL_TARGET_NDC = (0.25, -0.24)` 这个屏幕归一化坐标，从相机投射射线到未旋转的地球表面，得到球面法线方向。这实现了"屏幕右上区域始终是对准点"的视觉效果。

### 2.3 旋转动画：`earth.quaternion.slerp()`

```
pwa/earth3d.js L5854-5856
```

```js
const target = getTargetOrientation(useAuditCenterTarget ? auditCenterDir : null)
const isAnimating = earth.quaternion.angleTo(target) > 0.0002
earth.quaternion.slerp(target, 0.02)
```

- 每帧（requestAnimationFrame）执行
- `slerp(target, 0.02)`：以 2% 的插值率向目标四元数靠拢，产生平滑旋转
- `isAnimating` 标志控制 RDL streaming 是否激活（旋转期间持续更新瓦片）
- `if (!isAnimating) _animDirty = false`：停止时清除脏标记

**这是地球唯一的方向控制机制。不存在直接的"设置旋转角度"API，所有朝向变化都通过修改 `__rodioVisualState.lon/lat` 或 `targetDirOverride` 来驱动。**

### 2.4 `auditCenterDir` 模式

```
pwa/earth3d.js L2414-2415, L5925, L5932
```

- `auditCenterDir = new THREE.Vector3(0, 0, 1)`（始终指向 Z 轴正方向，即相机位置方向）
- 当 `setDebugLocation(lon, lat, { center: true })` 时：`useAuditCenterTarget = true`
- 此时地球的 `targetPoint`（上海等城市点）被旋转到**正对相机中心**（而不是屏幕右上侧的视觉锚点）
- 这是 debug 用途的"居中"模式，目前通过 Theme Tuner 面板的 checkbox 控制

### 2.5 `_AUDIT_VIEW_ANGLES` — Debug 审计视角系统

```
pwa/earth3d.js L5820-5829
```

```js
const _AUDIT_VIEW_ANGLES = {
  top:     { y: 0.0,  z: 4.8,  lookY: -1.4 },
  oblique: { y: 1.35, z: 5.05, lookY: -1.2 },
  low:     { y: 2.15, z: 5.45, lookY: -0.9 },
  asiaTilt:{ y: 0.65, z: 5.4,  lookY: -1.10 },
  asiaWide:{ y: 0.28, z: 7.2,  lookY: -0.65 },
  tilt:    { y: 0.82, z: 6.1,  lookY: -1.52 },
  global:  { y: 0.18, z: 7.85, lookY: -0.72 },
}
```

每个预设 3 个参数：
| 参数 | 含义 | 示例 (top) |
|------|------|-----------|
| `y` | 相机 Y 轴偏移（抬高俯视） | 0.0（正顶） |
| `z` | 相机 Z 轴偏移（远离/靠近球心） | 4.8（标准距离） |
| `lookY` | lookAt 注视点的 Y 偏移 | -1.4（向下看） |

`setAuditViewAngle(angle)`（L6083）：
1. 直接硬设 `camera.position.set(0, preset.y, preset.z)`
2. 直接硬设 `camera.lookAt(0, preset.lookY, 0)`
3. 如果开启了 audit lighting mode，强制重新 apply 当前主题
4. 触发 `updateEarlyMorningGlowMode()`、`refreshRDLTextureSampling()`、`updateSunPosition()`

**调用路径**：仅在 Theme Tuner debug 面板（`index.html` L1568 按钮组）通过用户点击触发，功能入口标题为 "EARTH · AUDIT VIEW ANGLES"。

### 2.6 FOV Zoom（scroll-wheel / `setRDLZoomLevel`）

```
pwa/earth3d.js L5817-5834
```

- 滚轮缩放改变的是 `camera.fov`，范围 28°（全局）→ 8°（最大放大）
- `_rdlZoomLevel` 驱动 RDL 地域叠加层 opacity
- `setRDLZoomLevel(level)`（L6069）：可编程控制，0=全局 1=最大放大
- Theme Tuner 中标注为 "DIST" 滑动条（L1558-1564 `setAuditDistance` 实际调用 `setRDLZoomLevel`）

**注意**：这不是真正的距离缩放。FOV 缩小让画面放大，但相机物理位置不变，地球球体也不会更大。近距离观察时球面曲率感知不变，与真实相机推拉有视觉差异。

### 2.7 核心机制总结

```
用户输入 / 外部 API
       │
       ├─ → __rodioVisualState.lon / lat      (地球哪个点面对相机)
       ├─ → visualTargetDir (NDC 锚点)        (屏幕哪个位置是视觉中心)
       ├─ → auditCenterDir 模式               (debug: 城市居中 vs 右上侧)
       └─ → camera.fov (_rdlZoomLevel)        (缩放)
              │
              ▼
       getTargetOrientation()  ──→  earth.quaternion.slerp(target, 0.02)
              │                              (每帧平滑旋转)
              ▼
       地球朝向实时更新 ──→ 渲染帧
```

### 2.8 关键边界澄清

| 项目 | 现状 | 说明 |
|------|------|------|
| `_AUDIT_VIEW_ANGLES` | **纯 debug 工具** | 只在 Theme Tuner 面板暴露，硬改 camera.position / lookAt。不是产品功能。 |
| 正式用户可见镜头预设 | **不存在** | 当前没有面向终端用户的镜头预设系统。用户看到的永远是默认 top-down 视角 + 滚轮 FOV 缩放。 |
| 相机距离（物理） | **固定 4.8** | `_AUDIT_VIEW_ANGLES` 的 z/y 参数可以改，但没有公开的产品级 API。 |
| 转场动画 | **仅 slerp 0.02** | 只有地球旋转有平滑过渡，相机位置/距离变化是瞬切的。 |

---

## 三、E7 预设参数设计草案

### 3.1 设计原则

1. **与 `_AUDIT_VIEW_ANGLES` 完全解耦**：正式预设是独立的数据结构，不依赖 debug 系统的 camera.position 硬设方式。
2. **参数驱动，不写实现逻辑**：只定义每个预设需要哪些参数及其语义，不规定如何应用这些参数。
3. **7 个预设，覆盖从宏观到微观的叙事层次**：Globe → Horizon → Low Orbit → Deep Space → Hemisphere → City Focus → Ocean View。

### 3.2 通用参数模型

每个预设由以下参数组成：

| 参数分类 | 字段 | 类型 | 语义 | 默认值 / 范围 |
|----------|------|------|------|--------------|
| **朝向** | `lat` | float | 地球面向相机的纬度 | -80 ~ 80 |
| | `lon` | float | 地球面向相机的经度 | -180 ~ 180 |
| | `centerMode` | bool | true=城市居中(类似 auditCenterDir) / false=依视觉锚点 | false |
| | `visualAnchorNdcX` | float | 视觉锚点屏幕 X (NDC) | 0.25 |
| | `visualAnchorNdcY` | float | 视觉锚点屏幕 Y (NDC) | -0.24 |
| **距离/缩放** | `fov` | float | 相机视场角（度） | 28（全局）~ 8（最大放大） |
| **相机偏移** | `cameraOffsetY` | float | 相机 Y 轴偏移（抬高俯视） | 0.0 |
| | `cameraOffsetZ` | float | 相机 Z 轴偏移（推远/拉近） | 4.8 |
| | `lookAtY` | float | 注视点 Y 偏移 | 0.0（看球心水平面） |
| **语义标签** | `label` | string | 预设显示名称 | — |
| | `description` | string | 一句话描述叙事意图 | — |
| | `layer` | enum | 叙事层级：macro / meso / micro | — |

### 3.3 七个预设的具体参数草案

#### 1. Globe（全局地球）

叙事意图：从太空俯瞰完整地球，适合开幕/章节过渡/世界感。

```json
{
  "label": "Globe",
  "description": "从太空俯瞰完整地球，展示全球尺度",
  "layer": "macro",
  "lat": 31.23,
  "lon": 121.47,
  "centerMode": false,
  "fov": 28,
  "cameraOffsetY": 0.0,
  "cameraOffsetZ": 4.8,
  "lookAtY": 0.0
}
```

- 约等于当前的默认初始状态 (top-down, fov=28)
- 纬度可调：想展示北半球 vs 南半球可改 lat

#### 2. Hemisphere（半球俯视）

叙事意图：聚焦某一半球（如东亚-东南亚），展示区域格局。

```json
{
  "label": "Hemisphere",
  "description": "半球俯视，展示区域格局",
  "layer": "macro",
  "lat": 35.0,
  "lon": 110.0,
  "centerMode": false,
  "fov": 22,
  "cameraOffsetY": 0.5,
  "cameraOffsetZ": 5.5,
  "lookAtY": -0.3
}
```

- 稍微推远（z=5.5）、放大（fov=22）、略微俯视
- 纬度提高到 35°N 覆盖欧亚大陆主体

#### 3. Horizon（地平线视角）

叙事意图：低角度贴近地表，看到地球的弧线和大气边缘，有"站在星球表面"的沉浸感。

```json
{
  "label": "Horizon",
  "description": "低角度贴近地表，看到地球弧线和大气边缘",
  "layer": "meso",
  "lat": 25.0,
  "lon": 121.0,
  "centerMode": true,
  "fov": 14,
  "cameraOffsetY": 2.0,
  "cameraOffsetZ": 4.0,
  "lookAtY": -0.5
}
```

- 相机压低（y=2.0）、拉近（z=4.0），注视点下移，产生"站在地表仰望弧线"的效果
- fov=14 增强透视感
- centerMode=true，城市居中强化聚焦

#### 4. Low Orbit（低轨道）

叙事意图：类似国际空间站视角，地球占据大部分画面，能看到大陆轮廓但细节已清晰。

```json
{
  "label": "Low Orbit",
  "description": "低轨道视角，地球占据大部分画面",
  "layer": "meso",
  "lat": 30.0,
  "lon": 121.0,
  "centerMode": true,
  "fov": 12,
  "cameraOffsetY": 1.2,
  "cameraOffsetZ": 3.5,
  "lookAtY": -0.8
}
```

- 相机大幅拉近（z=3.5）、放大（fov=12）
- 略微倾斜俯视

#### 5. City Focus（城市聚焦）

叙事意图：极度拉近到城市级别，RDL 叠加层清晰可辨。

```json
{
  "label": "City Focus",
  "description": "城市级别特写，RDL 叠加层清晰可辨",
  "layer": "micro",
  "lat": 31.23,
  "lon": 121.47,
  "centerMode": true,
  "fov": 8,
  "cameraOffsetY": 0.6,
  "cameraOffsetZ": 3.0,
  "lookAtY": -1.0
}
```

- fov=8 最大放大
- 相机最近（z=3.0），注视点下移
- 定位到上海（默认城市）

#### 6. Ocean View（海洋视角）

叙事意图：远离大陆，面向开阔海面，强调蓝色星球的静谧感。

```json
{
  "label": "Ocean View",
  "description": "面向开阔海面，蓝色星球的静谧感",
  "layer": "macro",
  "lat": -10.0,
  "lon": -140.0,
  "centerMode": false,
  "fov": 24,
  "cameraOffsetY": 0.3,
  "cameraOffsetZ": 5.0,
  "lookAtY": -0.2
}
```

- 定位到南太平洋（-10°S, -140°W），几乎看不到陆地
- 略微放大（fov=24），推远（z=5.0）

#### 7. Deep Space（深空）

叙事意图：极远距离，地球成为画面中一个小球，强调宇宙尺度。

```json
{
  "label": "Deep Space",
  "description": "深空视角，地球在画面中很小",
  "layer": "macro",
  "lat": 31.23,
  "lon": 121.47,
  "centerMode": false,
  "fov": 28,
  "cameraOffsetY": 0.0,
  "cameraOffsetZ": 10.0,
  "lookAtY": 0.0
}
```

- 大幅推远（z=10.0）、保持宽 FOV
- 地球在画面中像一颗弹珠

### 3.4 参数组合速览表

| 预设 | fov | cameraZ | cameraY | lookAtY | lat | lon | centerMode | layer |
|------|-----|---------|---------|---------|-----|-----|------------|-------|
| Globe | 28 | 4.8 | 0.0 | 0.0 | 31.23 | 121.47 | false | macro |
| Hemisphere | 22 | 5.5 | 0.5 | -0.3 | 35.0 | 110.0 | false | macro |
| Horizon | 14 | 4.0 | 2.0 | -0.5 | 25.0 | 121.0 | true | meso |
| Low Orbit | 12 | 3.5 | 1.2 | -0.8 | 30.0 | 121.0 | true | meso |
| City Focus | 8 | 3.0 | 0.6 | -1.0 | 31.23 | 121.47 | true | micro |
| Ocean View | 24 | 5.0 | 0.3 | -0.2 | -10.0 | -140.0 | false | macro |
| Deep Space | 28 | 10.0 | 0.0 | 0.0 | 31.23 | 121.47 | false | macro |

### 3.5 与 `_AUDIT_VIEW_ANGLES` 的差异

| 对比维度 | `_AUDIT_VIEW_ANGLES` (debug) | E7 预设系统 (草案) |
|----------|------------------------------|-------------------|
| 访问方式 | 硬设 camera.position / lookAt | 通过修改 `__rodioVisualState` + FOV + (可能的相机移动) |
| 地球朝向 | 不控制（地球方向保持当前 lerp 目标） | 通过 lat/lon 精确控制 |
| 面向用户 | Theme Tuner debug 面板 | 待定（debug-only 开关 or 正式入口） |
| 平滑过渡 | 瞬切 | 待实现（不在本轮范围） |
| 定位逻辑 | 不影响 `__rodioVisualState` | 通过 `setDebugLocation` 等价逻辑驱动 |
| 数量 | 7（top/oblique/low/asiaTilt/asiaWide/tilt/global） | 7（语义完全不同的叙事预设） |

---

## 四、明确不做（本轮）

- 转场动画细节（相机飞行路径、缓动函数、时长控制）
- 音乐 / 情绪联动
- 现有定位逻辑（`__rodioVisualState` 更新路径、`setDebugLocation` 行为）
- 接入正式播放流程（Playlist / Timeline / Theme Tuner 正式面板）
- 任何实现代码

---

## 五、待确认问题

1. 相机偏移（cameraOffsetY / cameraOffsetZ / lookAtY）是否需要平滑过渡？如需要，参数草案中应增加 `transitionDuration` 字段，但动画实现本身放后续轮次。
2. City Focus 的城市是否可配置？草案默认上海，是否需要支持运行时传入任意经纬度？
3. 预设的"输出通道"：是 debug-only 切换开关（Theme Tuner 内），还是暴露为 `window.earth3d` 的公开 API？
4. Deep Space 的 z=10.0 时，渲染对象（大气层、RDL 叠加层、星星球幕）是否需要在远距离下做可见性裁剪？
*（内容由AI生成，仅供参考）*
