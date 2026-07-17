# RodiO Living Earth 建设方案与差距审计计划

> 版本：v1.0  
> 适用对象：RodiO `pwa/earth3d.js` 当前架构  
> 建设原则：在不推翻现有 3D 地球视觉基础、不引入超出现有工程能力的大型技术栈、不牺牲移动端稳定性的前提下，逐步将 RodiO 从“自动展示型 3D 地球播放器”升级为“具有统一氛围、电影镜头、有限交互与低频探索乐趣的 Living Earth”。

---

# 一、项目可行性评估

## 1. 总体判断

本方案整体可实现，且不需要更换 Three.js 技术路线，也不需要引入重型物理引擎、GIS 引擎或复杂后端服务。

现有代码已经具备较好的基础：

- 已存在 `CAMERA_PRESETS`；
- 已存在 `CAMERA_COMPOSITIONS`；
- 已存在 `CAMERA_SEQUENCES`；
- 已存在 `longitudeDrift`、`latitudeDrift`、`diagonalDrift`、`orbitalArc` 等运动原语；
- 已存在 quaternion 平滑插值；
- 已存在 FOV 缩放；
- 已存在 11 时段视觉系统；
- 已存在地球、大气、云层、灯光、辉光等视觉管线；
- 已具备自动化开发、审计、PR 与回归流程。

因此，下一阶段不是从零建设，而是：

1. 收口现有控制系统；
2. 补足用户交互；
3. 扩展镜头与运动模式；
4. 增强昼夜背景空间；
5. 最后加入趣味玩法。

## 2. 能力边界

### 当前能力内可以完成

- 鼠标和触摸拖拽旋转；
- 双指缩放；
- 顺时针、逆时针、上下、斜向自动运动；
- 多套地球角度与电影构图；
- 自动回归；
- 镜头随机与低频切换；
- 星空 Points；
- 太阳方向背景；
- 高空薄云；
- 低频空气纹理；
- 音乐标签驱动镜头选择；
- 简单流星、极光、卫星掠过效果；
- 11 时段统一驱动；
- 性能等级与降级策略。

### 暂不建议进入本期

以下内容并非完全不能做，而是投入、风险或维护成本明显超出当前阶段收益：

- Google Earth 级别自由导航；
- 真实 GIS 地理检索；
- 高精度地形；
- 实时全球天气云图；
- 实时卫星轨道数据；
- 真实天文星图；
- 真实太阳、月球、行星天体计算全套系统；
- 基于音频 FFT 的高频实时镜头抖动或节奏响应；
- 全场景多 Pass 复杂后处理重构；
- 为每首歌实时生成专属镜头动画；
- 手机端六自由度姿态控制；
- 大规模 WebGPU 管线迁移。

这些内容应在 RodiO 用户规模、产品定位和性能数据进一步明确后再评估。

---

# 二、建设目标

## 1. 产品目标

将 RodiO 建设为：

> 一个以音乐为入口，由现实时间、视觉主题、镜头语言和低频环境事件共同驱动的数字地球空间。

## 2. 用户体验目标

用户打开 RodiO 后，应获得以下体验：

- 地球不再只有一个固定方向；
- 白天背景不空、不平、不像纯色贴片；
- 夜晚具有真实而克制的星空纵深；
- 用户可以拖动地球观察不同区域；
- 用户松手后，系统不会突兀抢回控制；
- 自动镜头具备顺时针、逆时针、上下、斜向、远近、极地等多种变化；
- 每次打开或连续播放时，镜头有轻微不同；
- 趣味事件低频出现，不破坏播放器的安静感；
- 桌面与移动端都有合理交互；
- 低性能设备仍可稳定运行。

---

# 三、总体技术架构

建议建立统一的 Living Earth Engine。

```text
Living Earth Engine
│
├── Earth Director
│   ├── Control Arbitration
│   ├── Composition Resolver
│   ├── Motion Resolver
│   ├── Interaction Offset
│   └── Return Controller
│
├── Camera System
│   ├── Camera Presets
│   ├── Camera Compositions
│   ├── Camera Sequences
│   ├── Geographic Angles
│   └── Cinematic Angles
│
├── Motion System
│   ├── Longitude Motion
│   ├── Latitude Motion
│   ├── Roll Motion
│   ├── Orbit Motion
│   └── Music-linked Motion
│
├── Interaction System
│   ├── Pointer Drag
│   ├── Touch Drag
│   ├── Pinch Zoom
│   ├── Inertia
│   └── Auto Return
│
├── Environment System
│   ├── Background Atmosphere
│   ├── Directional Sky
│   ├── Air Volume
│   ├── High-altitude Clouds
│   ├── Star Field
│   └── Ambient Events
│
├── State Orchestrator
│   ├── Time Segment
│   ├── Theme State
│   ├── Playback State
│   ├── Camera State
│   ├── Performance Tier
│   └── Reduced Motion
│
└── Audit & Diagnostics
    ├── State Snapshot
    ├── Active Controller
    ├── Performance Metrics
    ├── Visual Candidate
    └── Regression Hooks
```

---

# 四、建设阶段总览

| 阶段 | 名称 | 核心任务 | 优先级 |
|---|---|---|---|
| P4-A | Earth Director 收口 | 统一镜头、运动、交互控制权 | 必须先做 |
| P4-B | 用户交互 | 拖拽、捏合、惯性、回归 | 必做 |
| P4-C | 镜头与运动扩展 | 逆时针、上下、斜向、角度库 | 必做 |
| P4-D | 白天空间系统 | 大气背景、太阳方向、空气层 | 必做 |
| P4-E | 夜间空间系统 | 双层星空、夜间层次 | 推荐 |
| P4-F | 探索玩法 | Surprise、Journey、音乐映射 | 推荐 |
| P4-G | 低频事件 | 流星、极光、卫星、节日 | 可做 |
| P4-H | 审计与发布 | 性能、视觉、交互、回归 | 必做 |

---

# 五、P4-A：Earth Director 控制系统收口

## 1. 建设目的

解决当前多套镜头和运动系统并存的问题，避免后续加入拖拽后出现控制冲突。

当前已知控制来源包括：

- `CAMERA_PRESETS`
- `CAMERA_COMPOSITIONS`
- `CAMERA_SEQUENCES`
- `_AUDIT_VIEW_ANGLES`
- `longitudeDrift`
- `latitudeDrift`
- `diagonalDrift`
- `orbitalArc`
- `level1Motion`
- `precomputeMotion`
- 直接 quaternion slerp
- FOV wheel zoom

## 2. 实现路径

### 2.1 新增统一状态对象

建议定义：

```js
const earthDirectorState = {
  mode: 'auto',
  activeController: 'composition',

  basePose: {
    lat: 31.23,
    lon: 121.47,
    roll: 0,
    fov: 27,
    cameraOffsetY: 0,
    cameraOffsetZ: 5.2,
    lookAtY: 0,
    anchorNdcX: 0,
    anchorNdcY: -0.08
  },

  motionOffset: {
    lat: 0,
    lon: 0,
    roll: 0,
    cameraY: 0,
    cameraZ: 0
  },

  interactionOffset: {
    lat: 0,
    lon: 0,
    zoom: 0
  },

  transition: {
    active: false,
    progress: 0,
    durationMs: 1800,
    easing: 'easeInOutCubic'
  },

  returnState: {
    active: false,
    idleDelayMs: 5000,
    durationMs: 2200
  }
};
```

### 2.2 建立统一解析出口

所有 Preset、Composition、Sequence、Motion、Interaction 最终解析为：

```js
ResolvedEarthFrame = {
  targetLat,
  targetLon,
  targetRoll,
  earthQuaternion,
  cameraPosition,
  cameraFov,
  lookAt,
  screenAnchor
};
```

### 2.3 控制权优先级

建议固定优先级：

```text
用户实时交互
>
用户惯性
>
自动回归
>
镜头序列
>
自动运动模式
>
静态构图
```

### 2.4 兼容旧系统

不建议一次性删除现有系统。

应采用适配器：

```text
CAMERA_PRESETS
        ↓
Preset Adapter
        ↓
Resolved Base Pose
```

```text
CAMERA_COMPOSITIONS
        ↓
Composition Adapter
        ↓
Resolved Base Pose
```

```text
CAMERA_SEQUENCES
        ↓
Sequence Scheduler
        ↓
Transition Target
```

## 3. 资源需要

- 不需要外部贴图；
- 不需要新依赖；
- 需要对现有 camera、quaternion、FOV 写入点进行全量检索；
- 需要新增状态调试面板或 console snapshot；
- 需要自动化测试脚本覆盖控制权。

## 4. 实现效果

- 同一帧只有一个最终姿态；
- 用户拖拽不会被自动系统立即覆盖；
- 镜头切换不再互相叠加；
- 后续新增运动模式只需新增 profile；
- 审计时可明确知道当前由谁控制地球。

## 5. 验收标准

- 所有地球 quaternion 写入均通过 Director；
- 所有 camera position/FOV 写入均可追溯；
- 无重复自转；
- 无无来源跳动；
- 旧镜头效果基本保持；
- URL 调试模式仍可用，但不能绕过 Director。

---

# 六、P4-B：用户交互系统

## 1. 建设目的

让用户可以直接拖动地球，同时保持 RodiO 的电影构图和播放器属性。

## 2. 交互原则

RodiO 不做完全自由相机，而做有限接管：

- 用户可以探索；
- 用户不能破坏画面；
- 用户松手后保留短暂停留；
- 系统随后平滑回到合适构图；
- UI 区域优先响应播放器操作。

## 3. 实现路径

### 3.1 解除事件阻断

当前 `#earth3d-layer` 为 `pointer-events: none`。

建议改为：

```css
#earth3d-layer {
  pointer-events: auto;
  touch-action: none;
}
```

但必须对 UI 元素设置更高层级，并在交互命中判断中排除：

- 播放按钮；
- 进度条；
- 音量；
- 歌曲信息；
- 菜单；
- 模态窗口。

### 3.2 Pointer Events

使用统一 Pointer Events，不分别维护 mouse/touch 两套逻辑。

监听：

```text
pointerdown
pointermove
pointerup
pointercancel
lostpointercapture
```

使用 `setPointerCapture()` 保证拖动过程中不丢事件。

### 3.3 旋转映射

建议：

```text
横向拖动 → longitude offset
纵向拖动 → latitude offset
斜向拖动 → longitude + latitude
```

初始灵敏度建议：

```text
桌面：0.15°～0.25° / px
移动：0.12°～0.20° / px
```

需根据不同 FOV 动态缩放灵敏度，近景时应降低。

### 3.4 纬度限制

建议用户交互纬度限制：

```text
-75° ～ +75°
```

原因：

- 避免极点翻转；
- 避免 quaternion 方向突变；
- 保持构图稳定；
- 避免地球上下颠倒。

### 3.5 经度策略

经度可以无限累计，但显示层归一化到：

```text
-180° ～ +180°
```

### 3.6 惯性

记录最近若干帧 pointer delta，计算释放速度。

建议：

- 惯性持续 0.5～1.2 秒；
- 采用指数衰减；
- 低速拖动不触发明显惯性；
- Reduced Motion 模式关闭惯性；
- 移动端惯性应比桌面更弱。

### 3.7 自动回归

流程：

```text
拖动
→ 松手
→ 惯性
→ 停留
→ 寻找最近安全构图
→ 平滑回归
→ 恢复自动模式
```

回归不应简单回到原始角度。

应优先选择：

1. 当前最近的地理视角；
2. 当前主题允许的安全构图；
3. 当前镜头尺寸最接近的 Composition；
4. 无合适结果时回到原基础构图。

### 3.8 双指缩放

移动端增加 pinch：

- 记录两个 pointer；
- 计算 distance delta；
- 映射至 FOV 或 camera distance；
- 与现有 `_rdlZoomLevel` 接轨；
- 禁止同时触发页面缩放；
- 设置安全范围。

### 3.9 双击/双点

建议后续加入：

- 双击：回到主构图；
- 双点：切换下一安全角度。

第一期可只做双击回归。

## 4. 资源需要

- 无外部资源；
- 需要多设备测试；
- 需要桌面鼠标、触控板、iPhone Safari、Android Chrome；
- 需要 UI hit-test 规则；
- 需要日志记录交互状态。

## 5. 实现效果

- 用户可顺畅拖动；
- 斜向拖动自然；
- 缩放更符合移动端习惯；
- 松手后地球继续轻微滑动；
- 自动系统不会突然抢回；
- 画面最终恢复到稳定构图。

## 6. 验收标准

- 拖动不误触播放器；
- 页面不跟随滚动；
- 手机不触发浏览器缩放；
- 无极点翻转；
- 无地球穿透；
- 无 quaternion 跳变；
- 交互后 3～8 秒内可平滑恢复；
- 暂停、切歌、切后台时状态正确。

---

# 七、P4-C：镜头与运动系统扩展

## 1. 建设目的

丰富地球运动方向和角度，避免长期观看单调。

## 2. Motion Profile 体系

建议将现有运动原语统一为 Profile。

```js
const MOTION_PROFILES = {
  gentleClockwise: {
    longitudeSpeed: 0.30,
    latitudeAmplitude: 2,
    latitudePeriodSec: 55,
    rollAmplitude: 0
  },

  gentleCounterClockwise: {
    longitudeSpeed: -0.30,
    latitudeAmplitude: 2,
    latitudePeriodSec: 55,
    rollAmplitude: 0
  },

  verticalDrift: {
    longitudeSpeed: 0,
    latitudeAmplitude: 10,
    latitudePeriodSec: 48,
    rollAmplitude: 0
  },

  diagonalDriftLeft: {
    longitudeSpeed: -0.22,
    latitudeAmplitude: 8,
    latitudePeriodSec: 52,
    rollAmplitude: 2
  },

  diagonalDriftRight: {
    longitudeSpeed: 0.22,
    latitudeAmplitude: 8,
    latitudePeriodSec: 52,
    rollAmplitude: -2
  },

  polarPass: {
    longitudeSpeed: 0.12,
    latitudeAmplitude: 18,
    latitudePeriodSec: 70,
    rollAmplitude: 4
  },

  hold: {
    longitudeSpeed: 0,
    latitudeAmplitude: 0,
    rollAmplitude: 0
  }
};
```

## 3. 明确建设内容

### 必做

- 顺时针慢速；
- 逆时针慢速；
- 上下漂移；
- 左斜角运动；
- 右斜角运动；
- 停留；
- 自动反向；
- 低速极地掠过。

### 推荐做

- 近景降低速度；
- 远景提高少量速度；
- 播放状态与速度轻度联动；
- 暂停时不完全静止，而是进入更慢状态；
- 不同主题使用不同运动权重。

### 不建议

- 高频摇摆；
- 快速翻滚；
- 音乐鼓点驱动镜头抖动；
- 持续 roll；
- 每首歌强制切换方向。

## 4. 地球角度库

建议建立正式 Geographic Angle Library。

```js
const EARTH_VIEWPOINTS = {
  eastAsia: { lat: 31, lon: 121 },
  pacific: { lat: 5, lon: -150 },
  europe: { lat: 48, lon: 12 },
  africa: { lat: 5, lon: 20 },
  northAmerica: { lat: 40, lon: -100 },
  southAmerica: { lat: -15, lon: -60 },
  australia: { lat: -25, lon: 135 },
  northPole: { lat: 72, lon: 30 },
  southPole: { lat: -72, lon: 20 },
  indianOcean: { lat: -15, lon: 80 },
  atlantic: { lat: 15, lon: -35 }
};
```

注意：

- 不追求精确 GIS；
- 用于视觉构图即可；
- 每个视角需配合 screen anchor；
- 不能只给经纬度，还需给推荐构图与镜头距离。

## 5. 电影镜头库

建议正式定义：

- `portraitMarble`
- `farOrbit`
- `hemisphere`
- `horizonSkim`
- `limbHero`
- `planetRise`
- `halfPlanet`
- `closeFlyby`
- `polarDiagonal`
- `oceanExpanse`
- `cityAnchor`
- `deepSpace`

每个镜头应包含：

```text
基础视角
地球屏幕占比
屏幕锚点
FOV
camera offset
lookAt
roll
允许的运动模式
允许的时段
允许的设备等级
```

## 6. 镜头转场

建议统一过渡：

- 常规切换：1.6～2.4 秒；
- 远近跨度大：2.5～4 秒；
- Deep Space：4～6 秒；
- 用户交互回归：1.8～2.8 秒。

禁止：

- 直接跳 FOV；
- 同时突变经纬度和 camera distance；
- 近景穿越地球；
- 大角度使用线性插值造成机械感。

## 7. 资源需要

- 无外部资源；
- 需要截图审计；
- 需要每个镜头在桌面与移动端生成基准图；
- 需要镜头配置表；
- 需要主题兼容表。

## 8. 实现效果

- 同一首歌持续观看不再单调；
- 用户能够看到海洋、极地、不同大陆；
- 镜头变化有电影感；
- 逆时针、上下、斜角不再是临时实验，而是正式 motion profile；
- 自动镜头不破坏 UI。

---

# 八、P4-D：白天空间氛围系统

## 1. 建设目的

解决白天纯色渐变缺少深度、背景与地球分离的问题。

## 2. 基础结构

```text
Base Color
↓
Vertical Sky Gradient
↓
Directional Sun Field
↓
Low-frequency Air Volume
↓
High-altitude Cloud Layer
↓
Earth Atmosphere
↓
Earth
```

## 3. 背景大气渐变

### 实现方式

优先采用 CSS/Canvas/Shader 中成本最低、与现有架构兼容的方式。

建议第一期使用：

- CSS 多层 radial-gradient；
- 或现有 WebGL 背景 plane shader；
- 不建议立即引入完整物理天空 shader。

### 参数

每个时段至少定义：

```js
skyAtmosphere: {
  zenithColor,
  midColor,
  horizonColor,
  lowerColor,
  verticalCurve,
  horizonStrength
}
```

### 效果

- 顶部更深；
- 中部更通透；
- 地平线附近略亮；
- 画面从平面渐变变为有空气厚度的天空。

## 4. 太阳方向场

### 实现路径

增加统一的屏幕空间太阳方向：

```js
directionalSky: {
  sunNdcX,
  sunNdcY,
  warmColor,
  coolColor,
  strength,
  radius,
  falloff
}
```

通过大尺寸 radial gradient 或 shader 形成：

- 太阳一侧偏暖；
- 对侧偏冷；
- 不显示太阳实体；
- 与地球光照方向保持一致。

### 关键要求

太阳方向必须与地球 sunlight 使用同一来源或同一映射关系。

不能出现：

- 地球右侧受光；
- 背景左侧却更暖。

## 5. Air Volume

### 实现路径

使用低频、低透明度噪声：

- 一张 512 或 1024 无缝灰度纹理；
- 或程序化 FBM；
- 极慢 UV 漂移；
- 透明度控制在 0.3%～1.5%。

### 建议

优先使用小尺寸无缝纹理，成本低、容易调试。

### 作用

- 打破纯色；
- 提供空气存在感；
- 不应被直接识别为噪点。

## 6. 高空卷云

### 实现路径

- 一层全屏透明纹理；
- 使用 1024 或 2048 灰度/透明云图；
- 混合模式采用普通 Alpha 或低强度 Screen；
- 运动周期 180～600 秒；
- 可做两层不同速度，但第一期一层即可。

### 白天透明度建议

```text
dawn：1%～3%
sunrise：2%～4%
earlyMorning：1%～3%
morning：1%～2%
noon：0.5%～1.5%
afternoon：1%～2%
goldenApproach：2%～4%
sunset：2%～5%
```

### 注意

- 不能像天气云；
- 不与地球云层重复；
- UI 区域应减弱；
- 低性能移动端可关闭。

## 7. 资源需要

- 1 张无缝低频空气纹理；
- 1～2 张高空卷云透明纹理；
- 可选 1 张柔和大尺度光场 mask；
- 纹理必须压缩为 WebP/AVIF 或适配 WebGL 的格式；
- 需要明确授权来源，优先自行生成或使用公共领域资源；
- 不建议依赖远程 CDN。

## 8. 实现效果设想

白天打开 RodiO 时：

- 背景仍然保持干净；
- 但不再像简单蓝色渐变；
- 画面有明显但克制的方向性；
- 地球大气与背景颜色自然衔接；
- 高空纹理几乎不可察觉，但画面不空；
- 不牺牲文字可读性。

## 9. 验收标准

- noon 不显脏；
- sunrise/sunset 有方向感；
- 不出现明显云贴图边缘；
- 背景纹理不抢歌名；
- 不形成粉紫滤镜；
- 白天关闭星空；
- 移动端低档可降级。

---

# 九、P4-E：夜间星空系统

## 1. 建设目的

为夜间背景提供真实纵深，避免纯色宇宙背景的贴片感。

## 2. 推荐方案

采用双层 `THREE.Points`。

### Layer A：远层星尘

- 1500～2500 点；
- 球面均匀采样；
- 小尺寸；
- 低亮度；
- 无 twinkle；
- 固定世界坐标。

### Layer B：主星

- 150～300 点；
- 尺寸有差异；
- 亮度有差异；
- 少量色温差异；
- 3%～8% 轻微闪烁。

## 3. 均匀采样

避免经纬度简单随机。

建议使用：

```js
const z = Math.random() * 2 - 1;
const theta = Math.random() * Math.PI * 2;
const r = Math.sqrt(1 - z * z);

x = r * Math.cos(theta);
y = z;
z2 = r * Math.sin(theta);
```

或 Fibonacci Sphere。

## 4. 星空材质

建议使用自定义 ShaderMaterial，以支持：

- 每点 size；
- 每点 brightness；
- 每点 phase；
- 全局 opacity；
- 少量 twinkle；
- 屏幕尺寸适配。

## 5. 时段可见度

建议：

| 时段 | 可见度 |
|---|---:|
| dawn | 0.10～0.20 |
| sunrise | 0 |
| earlyMorning | 0 |
| morning | 0 |
| noon | 0 |
| afternoon | 0 |
| goldenApproach | 0 |
| sunset | 0.02～0.08 |
| evening | 0.25～0.45 |
| lateEvening | 0.65～0.80 |
| deepNight | 1.00 |

## 6. Bloom 控制

必须验证：

- 星星不被 Bloom 放成大圆；
- 星星不穿过地球；
- 星星不透过大气错误显示；
- 亮星数量必须克制；
- UI 区域密度适当减弱。

## 7. 资源需要

优先程序化，无需星空贴图。

仅需要：

- 可选圆形 soft particle texture；
- 或 shader 内直接绘制圆点；
- 不需要高分辨率天空盒。

## 8. 实现效果

- 夜晚空间不再空；
- 星空有远近层次；
- 深夜更有沉浸感；
- 星星不表演、不抢地球；
- 黄昏和黎明自然渐入渐出。

---

# 十、P4-F：探索玩法

## 1. Surprise View

### 玩法

用户每次打开、每隔若干首歌或手动触发时，进入一个不同安全镜头。

### 实现

维护最近历史：

```js
recentViewHistory = [];
```

选择规则：

- 最近 5 次不重复；
- 不连续两次近景；
- 不连续两次极地；
- 根据时段筛选；
- 根据设备性能筛选；
- 用户刚操作后暂停 Surprise。

### 资源

无外部资源。

### 效果

用户每次打开都有微小新鲜感。

## 2. Auto Journey

### 玩法

系统播放一组有叙事性的镜头：

```text
城市/大陆锚点
→ 半球
→ 海洋
→ 极地
→ 地平线
→ 主视觉
```

### 实现

新增 Journey 配置：

```js
const JOURNEYS = {
  pacificNight: [...],
  sunriseAsia: [...],
  polarCalm: [...],
  globalAmbient: [...]
};
```

每个步骤包含：

- composition；
- viewpoint；
- motionProfile；
- duration；
- transition；
- allowedTimeSegments。

### 建议

- Journey 不应频繁触发；
- 一组 30～90 秒；
- 用户交互立即中止；
- 播放器暂停可进入 hold。

## 3. 音乐镜头映射

### 第一阶段可实现方式

不做复杂音频分析，使用已有歌曲元数据：

- genre；
- energy；
- tempo；
- mood；
- valence；
- 手动分类标签。

### 映射示例

| 标签 | 镜头 |
|---|---|
| ambient | farOrbit / deepSpace |
| piano | portraitMarble / slowDrift |
| electronic | diagonalOrbit |
| jazz | cityAnchor / evening |
| classical | hemisphere / horizonSkim |
| lo-fi | cityAnchor / gentleClockwise |
| cinematic | planetRise / limbHero |

### 资源

- 需要歌曲标签；
- 无标签时使用默认；
- 不需要后端 AI。

## 4. 用户可见入口

建议最终提供一个轻量入口：

```text
Auto
Explore
Hold
Reset
```

第一期甚至可以隐藏在菜单中，不需要占主界面。

---

# 十一、P4-G：低频环境事件

## 1. 建设原则

事件必须：

- 低频；
- 短时；
- 不可预测；
- 不抢音乐；
- 可以关闭；
- 低性能设备可禁用。

## 2. 可做事件

### 流星

- 一条短暂光线；
- 0.5～1.2 秒；
- 低频；
- 夜间可用；
- 每次不超过 1～2 条。

### 极光

- 高纬度主题下出现；
- 使用透明 ribbon 或 shader；
- 低强度；
- 不追求真实物理。

### 卫星掠过

- 一个小点沿弧线移动；
- 不使用真实轨道；
- 偶尔出现；
- 可与星空共存。

### 节日天空

- 万圣节血雾；
- 圣诞节冷色星尘；
- 新年短暂流光；
- 地球日绿色呼吸。

## 3. 不建议本期做

- 真实 ISS 数据；
- 真实卫星 API；
- 实时天气；
- 日月食精确计算。

---

# 十二、性能分级与降级策略

## 1. 设备等级

建议：

```js
performanceTier = 'high' | 'medium' | 'low';
```

判断依据：

- DPR；
- 屏幕尺寸；
- GPU renderer；
- 首屏帧率；
- 移动端型号；
- `prefers-reduced-motion`。

## 2. 分级策略

| 能力 | High | Medium | Low |
|---|---|---|---|
| 星空远层 | 2500 | 1500 | 600 |
| 主星 | 300 | 180 | 80 |
| 高空云 | 双层 | 单层 | 关闭 |
| Air Volume | 开 | 低 | 关闭 |
| Twinkle | 开 | 少量 | 关闭 |
| 惯性 | 完整 | 简化 | 关闭 |
| Journey | 完整 | 简化 | 少镜头 |
| Bloom | 当前 | 降低 | 最低或关闭 |
| DPR | 设备值限制 | 1.5 | 1.0 |

## 3. 性能目标

- 桌面高性能：稳定接近 60 FPS；
- 集成显卡桌面：45～60 FPS；
- 高端手机：45～60 FPS；
- 普通手机：不低于 30 FPS；
- 拖拽时不得显著低于静态帧率；
- 切后台后暂停更新；
- 页面隐藏时停止星空闪烁和云漂移。

---

# 十三、资源需求清单

## 1. 必要资源

| 资源 | 数量 | 用途 |
|---|---:|---|
| 无缝低频空气纹理 | 1 | 白天背景体积 |
| 高空卷云透明纹理 | 1～2 | 白天空间纹理 |
| 可选 soft particle | 1 | 星空点精细形态 |
| 镜头基准截图 | 每镜头多端 | 验收 |
| 11 时段背景参考图 | 5 个锚点优先 | 调色 |
| 设备测试矩阵 | 至少 4 档 | 性能审计 |

## 2. 可选资源

- 极光 ribbon 纹理；
- 流星 soft streak；
- 节日事件纹理；
- 低频 noise texture。

## 3. 资源管理要求

- 资源必须本地化；
- 建立来源与授权记录；
- 控制总大小；
- 使用 WebP/AVIF 或适合 WebGL 的压缩格式；
- Railway 部署前确认已进入 Git；
- 资源失败时必须有 fallback；
- 移动端缓存策略需单独验证。

---

# 十四、关键实现风险

## 1. 控制冲突

风险：

- 自动旋转与拖拽同时写 quaternion；
- sequence 与 return 同时运行；
- URL candidate 绕过正式状态；
- FOV 与 camera distance 双重缩放。

措施：

- 建立唯一控制入口；
- 每帧输出 activeController；
- 对直接写入点做审计阻断。

## 2. 移动端误触

风险：

- 页面无法滚动；
- 控件误操作；
- Safari passive listener；
- 多指状态未清除。

措施：

- UI 命中排除；
- pointer capture；
- pointercancel 清理；
- touch-action 精细配置；
- 真机测试。

## 3. 视觉变脏

风险：

- 白天高空云过强；
- noise 像胶片颗粒；
- 星空撒盐；
- Bloom 放大星星；
- 背景方向场形成明显光斑。

措施：

- 所有新增层从极低值开始；
- 使用视觉锚点截图对比；
- 建立强度上限；
- UI 区域局部衰减。

## 4. 性能回退

风险：

- 多层透明 overdraw；
- 高 DPR；
- Bloom；
- 大纹理；
- 移动端 points 尺寸过大。

措施：

- performance tier；
- DPR clamp；
- 动态降级；
- 纹理尺寸控制；
- 开发阶段记录 GPU/CPU 时间。

## 5. 功能过度

风险：

- 变成炫技屏保；
- 趣味事件过多；
- 镜头切换频繁；
- 音乐与视觉争夺注意力。

措施：

- 低频；
- 用户可关闭；
- 默认克制；
- 事件加入冷却时间；
- 镜头变化按分钟而非按秒。

---

# 十五、差距审计方案

## 1. 审计目标

对比：

- 当前能力；
- 目标能力；
- 实现状态；
- 缺失项；
- 风险；
- 是否达到发布条件。

## 2. 审计维度

### A. 架构审计

检查：

- 是否存在唯一 Director；
- 是否仍有直接写 quaternion；
- 是否仍有直接写 camera position；
- Preset/Composition/Sequence 是否统一；
- activeController 是否可观测；
- 旧系统是否存在重复旋转；
- audit API 是否与生产隔离。

### B. 交互审计

检查：

- 桌面横向拖动；
- 桌面纵向拖动；
- 桌面斜向拖动；
- 快速甩动；
- 鼠标滚轮；
- 移动单指；
- 移动斜向；
- 移动双指；
- pointercancel；
- 切后台；
- UI 误触；
- 自动回归。

### C. 镜头审计

每个镜头检查：

- 地球是否遮挡 UI；
- 地球占屏比例；
- 大气是否裁切；
- 大陆是否有辨识度；
- 近景纹理质量；
- 海洋是否自然；
- 灯光是否过曝；
- 转场是否安全；
- 移动端是否成立；
- 横屏是否成立。

### D. 11 时段视觉审计

重点锚点：

- dawn；
- noon；
- sunset；
- evening；
- deepNight。

检查：

- 背景与大气同源；
- 太阳方向一致；
- 高空云强度；
- Air Volume；
- 星空渐入；
- 星星 Bloom；
- 文字可读性；
- 主题过渡。

### E. 性能审计

设备：

- Desktop High；
- Desktop Integrated GPU；
- Mobile High；
- Mobile Low。

检查：

- FPS；
- frame time；
- 内存；
- 首屏加载；
- 资源缓存；
- 交互延迟；
- 切后台；
- 长时间运行；
- 发热；
- Railway 生产差异。

### F. 回归审计

检查：

- 海洋；
- 云层；
- rimGlow；
- 城市灯光；
- 彩蛋主题；
- 歌曲切换；
- 暂停；
- 恢复；
- 刷新；
- 缓存；
- 手机加载；
- URL candidate；
- 自动化流程。

---

# 十六、差距审计表模板

| 模块 | 当前状态 | 目标状态 | 差距 | 风险等级 | 建设阶段 | 验收状态 |
|---|---|---|---|---|---|---|
| 控制权 | 多套系统并存 | 唯一 Director | 高 | 高 | P4-A | 未开始 |
| 桌面拖拽 | 无 | 横/纵/斜向 | 高 | 中 | P4-B | 未开始 |
| 移动拖拽 | 无 | 单指拖动 | 高 | 高 | P4-B | 未开始 |
| Pinch | 无 | 双指缩放 | 中 | 高 | P4-B | 未开始 |
| 自动回归 | 无 | 惯性+停留+回归 | 高 | 中 | P4-B | 未开始 |
| 逆时针 | 无正式模式 | Motion Profile | 中 | 低 | P4-C | 未开始 |
| 上下漂移 | ±3°原型 | 正式模式 | 中 | 低 | P4-C | 部分具备 |
| 斜向运动 | 有原型 | 正式模式 | 低 | 低 | P4-C | 部分具备 |
| 地理角度 | 零散 | 正式角度库 | 中 | 低 | P4-C | 部分具备 |
| 白天背景 | 渐变 | 大气+方向光场 | 高 | 中 | P4-D | 未开始 |
| Air Volume | 无 | 低频空气层 | 中 | 中 | P4-D | 未开始 |
| 高空卷云 | 无 | 低透明背景云 | 中 | 中 | P4-D | 未开始 |
| 星空 | 无 | 双层 Points | 中 | 中 | P4-E | 未开始 |
| Surprise | 无用户入口 | 安全随机镜头 | 中 | 低 | P4-F | 未开始 |
| Journey | 有序列基础 | 正式叙事序列 | 中 | 中 | P4-F | 部分具备 |
| 音乐映射 | 无 | 标签驱动 | 中 | 中 | P4-F | 未开始 |
| 流星/极光 | 无 | 低频事件 | 低 | 中 | P4-G | 可选 |

---

# 十七、阶段验收与发布门槛

## P4-A Go/No-Go

必须满足：

- 唯一控制状态；
- 无重复写入；
- 旧视觉无明显退化；
- 调试状态可观测；
- 现有镜头全部可通过新入口调用。

## P4-B Go/No-Go

必须满足：

- 桌面/移动交互可用；
- 无 UI 误触；
- 无极点翻转；
- 无突然抢回；
- pinch 可控；
- Reduced Motion 生效。

## P4-C Go/No-Go

必须满足：

- 至少 6 个正式 motion profile；
- 至少 8 个稳定构图；
- 至少 8 个地理视角；
- 所有转场无穿透和跳变。

## P4-D Go/No-Go

必须满足：

- noon 不脏；
- sunset 有方向；
- 背景与地球大气统一；
- 高空云不抢 UI；
- 低性能模式可关闭。

## P4-E Go/No-Go

必须满足：

- 星空不穿透；
- 不被 Bloom 放大；
- 白天完全隐藏；
- deepNight 层次明显；
- 移动端性能稳定。

## P4-F Go/No-Go

必须满足：

- Surprise 不重复；
- Journey 可被用户中断；
- 用户操作后自动功能暂停；
- 镜头变化不过频；
- 音乐标签缺失时有稳定 fallback。

---

# 十八、建议实施顺序

## 第一阶段：控制系统

1. 全量检索 camera/quaternion/FOV 写入点；
2. 建立 DirectorState；
3. 建立 Resolver；
4. 适配 Preset；
5. 适配 Composition；
6. 适配 Sequence；
7. 合并重复运动；
8. 建立 activeController 日志；
9. 回归现有视觉。

## 第二阶段：交互

1. Pointer Events；
2. 桌面横向；
3. 桌面纵向；
4. 斜向；
5. 惯性；
6. UI 排除；
7. 移动单指；
8. Pinch；
9. 自动回归；
10. Reduced Motion；
11. 真机审计。

## 第三阶段：镜头扩展

1. Motion Profile；
2. 逆时针；
3. 上下；
4. 斜角；
5. 极地；
6. 地理角度库；
7. 电影镜头；
8. 转场统一；
9. 截图审计。

## 第四阶段：白天背景

1. 5 个时段锚点；
2. 垂直大气渐变；
3. 太阳方向场；
4. Air Volume；
5. 高空卷云；
6. UI 安全区；
7. 11 时段扩展；
8. 移动端降级。

## 第五阶段：夜间星空

1. 500 点原型；
2. Bloom 审计；
3. 扩展双层；
4. twinkle；
5. 11 时段；
6. 性能分级；
7. 深夜截图审计。

## 第六阶段：探索与趣味

1. Surprise；
2. Journey；
3. 音乐标签映射；
4. 流星；
5. 极光；
6. 节日事件；
7. 频率控制；
8. 用户开关。

---

# 十九、当前建设成熟度判断

基于目前审计：

| 领域 | 当前成熟度 |
|---|---:|
| 地球基础视觉 | 80%～90% |
| 自动构图素材 | 65%～75% |
| 自动镜头序列 | 45%～60% |
| 统一导演架构 | 20%～30% |
| 用户交互 | 10% 以下 |
| 白天空间背景 | 25%～35% |
| 夜间空间背景 | 15%～25% |
| 探索玩法 | 10%～20% |
| 低频趣味事件 | 0%～10% |
| 移动端交互完整性 | 10%～20% |

总体判断：

> RodiO 已经完成了“视觉基础”和“镜头素材”的大部分积累，但距离完整 Living Earth 体验的主要差距，集中在控制系统、交互、环境空间和用户可感知入口上。

---

# 二十、最终建设结论

本方案可以实现，但必须遵守以下顺序：

> 先收口控制权，再开放交互；先稳定镜头，再扩展环境；先形成统一体验，再加入趣味事件。

最不建议的做法是：

- 直接往现有代码中加入大量 pointer 监听；
- 继续零散增加更多镜头参数；
- 未完成控制权收口就做音乐联动；
- 同时开发星空、高空云、极光、流星和卫星；
- 为了“丰富”而牺牲白天的纯净；
- 让用户自由操作到破坏构图。

最合理的产品方向是：

> 自动导演系统主导，用户有限接管；地球每天略有变化，但始终保持同一种审美。

当 P4-A 至 P4-E 完成后，RodiO 才真正具备从“高质量 3D 地球播放器”进入“Living Earth 数字空间”的基础。P4-F 与 P4-G 应建立在这一基础之上，而不是提前堆叠。
