# RodiO 下一阶段整合建设规划与任务清单

> 版本：v1.0  
> 日期：2026-07-17  
> 定位：在既有 RodiO 产品方案、视觉系统 v3.1 文件包、RDL 方案、Living Earth 初始方案、Claude Code 代码核查反馈，以及“三态收缩 UI”方案基础上，形成下一阶段唯一执行主线。  
> 核心原则：不推翻现有系统；不因界面极简而削弱产品深度；先解决真实冲突，再开放交互；优先复用既有能力，避免平行系统与重复造轮子。

---

# 一、整合后的产品判断

RodiO 的长期目标仍然成立：

> RodiO 是一个以音乐为入口的 AI 生活陪伴空间，也是一个与时间、地点、地球和天文状态相连的宇宙电台。

但下一阶段不能同时施工全部愿景。现阶段需要完成的，不是增加更多“功能点”，而是形成一个稳定的核心体验：

1. 页面能够在完整态、极简态、地球态之间自然切换；
2. 用户可以直接触摸和转动地球；
3. 地球在自动导演与用户接管之间不会冲突；
4. 白天背景不再单调，夜晚星空修复可见；
5. 已有镜头与运动能力真正产品化；
6. 更远期的天文、文化和音乐联动继续保留，但不提前混入本轮施工。

RodiO 应呈现为：

> 默认安静，能力丰富；界面极简，系统不单薄；玩法隐藏，不主动炫耀。

---

# 二、现有规划之间的关系

## 1. 产品方案负责“为什么做”

产品方案已经明确：

- RodiO 不是传统播放器；
- 音乐是低打扰 AI 陪伴的入口；
- 产品价值是“更少、但更正确的选择”；
- 默认界面应安静、克制、沉浸；
- 控件应在需要时出现，使用后退回；
- 地球、天空、时间和音乐共同形成情境空间。

## 2. v3.1 文件包负责“怎么安全做”

现有 v3.1 文件包的价值仍然保留：

- 主路线图管理阶段边界；
- Earth、Sky、资源、镜头、天体分别施工；
- 每轮只允许一种任务类型；
- 先审计、再候选、再接入、再验收；
- 禁止把天气、天体、云、大气、镜头等混在同一个提交中。

## 3. Living Earth 初始方案负责“未来能力蓝图”

初始方案提出：

- 用户拖拽；
- 顺时针、逆时针、上下和斜向运动；
- 镜头库；
- 白天空间氛围；
- 夜间星空；
- Surprise、Journey、音乐联动；
- 天文和低频事件。

其中一部分仍作为长期蓝图保留，但执行顺序需要根据真实代码状态修订。

## 4. Claude Code 反馈负责“纠正真实代码假设”

必须吸收的修正：

- 星空系统不是从零开始，已有 Points、twinkle 和时段透明度，应先审计和修复；
- 当前页面已有翻页手势和控件唤出逻辑，未来地球拖拽会形成直接冲突；
- 完整 Earth Director 重构不应成为用户交互的前置条件；
- 应先做最小控制仲裁，复用现有 `transitionToComposition()`；
- `astronomy.js` 比通用节日特效更值得作为后续视觉驱动来源。

## 5. 三态 UI 方案负责“用户表层状态”

三态 UI 不是与 Living Earth 冲突的另一套方案，而是其上层入口：

```text
完整态：操作与信息完整
极简态：信息保留，控件退出
地球态：只保留地球空间
```

它决定用户当前看到多少 UI；Living Earth 决定地球本身有多深。

---

# 三、下一阶段的唯一总目标

下一阶段建议命名为：

# P4 · Touch the Earth

目标不是一次完成所有 Living Earth 功能，而是完成以下闭环：

```text
三态 UI
→ 统一手势仲裁
→ 可拖动地球
→ 自动系统暂停与恢复
→ 现有星空修复
→ 白天背景第一轮增强
→ 已有运动方向产品化
```

这一阶段结束时，用户应明显感知到：

- RodiO 的界面会主动退后；
- 地球成为真正的视觉中心；
- 用户可以摸到、转动和停留；
- 地球仍然保持安静和电影感；
- 夜晚更有空间，白天不再只是平面渐变。

---

# 四、三态 UI 的正式定义

## 1. 完整态 Full

显示：

- 时间；
- 位置；
- Logo；
- ON AIR；
- 歌名；
- 歌手；
- 天外来信或讲解；
- 进度条；
- 播放按钮组；
- 底部翻页把手；
- 地球。

触发：

- 新歌开始；
- 切歌；
- 用户从极简态或地球态唤出控件；
- 用户操作播放器控件；
- 异常状态需要用户处理。

行为：

- 进入完整态后启动 5 秒空闲计时；
- 任意有效 UI 操作重置计时；
- 5 秒无操作进入极简态。

## 2. 极简态 Minimal

显示：

- 时间；
- 位置；
- Logo；
- ON AIR；
- 歌名；
- 歌手；
- 天外来信或讲解；
- 地球。

隐藏：

- 进度条；
- 播放按钮组；
- 底部翻页把手。

隐藏方式：

```text
opacity → 0
pointer-events → none
visibility 延迟切换
```

行为：

- 短触空白区域唤出完整态；
- 地球区域慢拖可旋转地球；
- 快速垂直甩动仍可切页；
- 可以继续自动进入地球态，但不建议第一轮默认自动进入。

## 3. 地球态 Earth Only

只显示：

- 地球；
- Sky / Atmosphere / Stars；
- 必要的极弱状态提示（默认无）。

隐藏：

- 时间；
- 位置；
- Logo；
- ON AIR；
- 歌曲信息；
- 天外来信；
- 所有播放器控件；
- 翻页把手。

建议触发方式：

第一阶段不做“自动 5 秒进入地球态”。优先采用以下之一：

- 长按空白区域；
- 点击 ON AIR 后的隐藏入口；
- 双击空白区域；
- 菜单中的“只看地球”；
- 地球态候选参数验证。

退出：

- 短触任意空白区域回到极简态或完整态；
- 切歌时可选择回到完整态；
- 播放异常时强制回到完整态。

## 4. 为什么不建议第一轮自动进入地球态

自动从极简态继续隐藏全部信息，可能带来：

- 用户不知道正在播放什么；
- 不理解如何恢复；
- 与拖拽手势冲突；
- 切歌时页面频繁闪动；
- 新功能过多，难以判断问题来源。

因此建议：

```text
第一轮：完整态 ↔ 极简态自动切换
第二轮：地球态作为手动/隐藏候选
验收后再决定是否自动进入
```

---

# 五、统一手势仲裁系统

## 1. 为什么必须先做

当前同一屏幕存在或计划存在：

- 点按空白唤出控件；
- 纵向滑动切换 page1/page2；
- 地球横向、纵向、斜向拖动；
- 播放器按钮和进度条；
- 未来双指缩放；
- 地球态退出。

这些不能分别各自注册一套独立判定。

## 2. 建议建立 `GestureRouter`

统一接收：

```text
pointerdown
pointermove
pointerup
pointercancel
lostpointercapture
```

记录：

```js
{
  pointerId,
  startX,
  startY,
  lastX,
  lastY,
  startTime,
  totalDx,
  totalDy,
  velocityX,
  velocityY,
  pointerCount,
  startedInEarthZone,
  startedInUIZone,
  resolvedIntent
}
```

## 3. 手势优先级

```text
播放器控件命中
>
双指手势
>
快速垂直翻页
>
地球慢拖
>
短触唤出/隐藏
```

## 4. 意图判定建议

### UI 操作

起点位于按钮、进度条、菜单、ON AIR 等区域：

- 交给 DOM UI；
- 不触发地球拖动；
- 不触发翻页；
- 重置完整态倒计时。

### 短触 Tap

建议条件：

- 总位移 < 8～12px；
- 持续时间 < 300～450ms；
- 未命中 UI；
- 没有第二指针。

用途：

- 极简态 → 完整态；
- 地球态 → 极简态或完整态；
- 完整态仅重置倒计时，不立即隐藏。

### 地球拖动 Drag

建议条件：

- 起点在地球安全交互区；
- 位移超过 8～12px；
- 速度低于快速翻页阈值；
- 拖动持续连续；
- 一旦确定为 Drag，本次手势不可再变成 Tap。

用途：

- 横向 → longitude；
- 纵向 → latitude；
- 斜向 → longitude + latitude。

### 翻页 Swipe

建议条件：

- `abs(dy) > abs(dx) × directionRatio`；
- `abs(dy) > 60px`；
- 速度超过阈值；
- 可考虑只允许从屏幕边缘或非地球核心区域起手。

用途：

- page1 ↔ page2。

### 双指

第一轮只预留，不立即实现 Pinch。

## 5. 地球交互区

建议不要全屏都能拖地球。

可定义：

- 地球球体投影包围区域；
- 适当扩大 10%～20%；
- 顶部文字区排除；
- 底部播放器区排除；
- 屏幕边缘保留翻页优先区。

---

# 六、最小化地球交互仲裁

## 1. 不做完整 Director 重构

下一阶段不全量重写 Preset、Composition、Sequence、Motion。

原因：

- 现有系统已经运行；
- 全量抽象没有直接用户价值；
- 容易重新解释错 `anchorNdcY`、`lookAtY` 等语义；
- 回归范围太大；
- 会延迟最有差异化的“可触摸地球”。

## 2. 也不只使用一个布尔值

仅有 `isUserDragging` 不足以覆盖松手、停留、回归等过程。

建议最小状态机：

```js
const earthInteractionState = {
  mode: 'auto',
  // auto | dragging | inertia | holding | returning

  pointerId: null,

  lonOffset: 0,
  latOffset: 0,

  velocityLon: 0,
  velocityLat: 0,

  holdUntil: 0,
  returnCompositionId: null
};
```

## 3. 与现有系统的关系

### dragging

暂停：

- `_updateGramTransition`
- `_updateGramMotion`
- `_updateGramAutoPilot`

但不销毁它们。

应用：

- 用户拖动增量；
- 更新目标 quaternion 或可控 orientation offset。

### inertia

第一轮可不做，或者只做极轻版本。

### holding

用户松手后保留当前角度 2～5 秒。

### returning

调用已有：

```js
transitionToComposition(currentOrSafeComposition)
```

回到当前应有构图。

### auto

恢复现有自动运动与序列。

## 4. 第一轮交互范围

必须做：

- 横向拖动；
- 纵向拖动；
- 斜向拖动；
- 自动运动暂停；
- 松手停留；
- 平滑回归；
- UI 与翻页冲突处理。

暂不做：

- Pinch；
- 双指旋转；
- 用户自由 Roll；
- 强惯性；
- 手动镜头菜单；
- 无限缩放；
- 完整 Director。

---

# 七、镜头与运动系统的下一步

## 1. 现状判断

现有代码已经有较丰富素材：

- CAMERA_PRESETS；
- CAMERA_COMPOSITIONS；
- CAMERA_SEQUENCES；
- longitudeDrift；
- latitudeDrift；
- diagonalDrift；
- orbitalArc；
- approach / retreat / flyby；
- 多种审计视角。

当前缺口主要不是镜头数量，而是：

- 用户不可感知；
- 方向单一；
- 没有正式 Motion Profile；
- 自动与手动没有协调。

## 2. 本阶段只产品化现有能力

建议只建立以下正式运动候选：

1. `gentleClockwise`
2. `gentleCounterClockwise`
3. `verticalDrift`
4. `diagonalLeft`
5. `diagonalRight`
6. `polarDrift`
7. `hold`

通过配置复用现有原语，不新建复杂引擎。

## 3. 正式视角候选

优先使用已有构图：

- portraitMarble；
- farOrbit；
- polarDiagonal；
- oceanExpanse；
- horizonSkim；
- limbHero；
- cityAnchor；
- deepSpace。

暂不新增几十个地理点位。

## 4. 用户可见方式

第一轮不增加明显按钮。

可通过：

- 自动低频选择；
- 地球态内部隐藏切换；
- debug candidate；
- 后续 Explore 入口。

## 5. RDL 与近景镜头的关系

RDL 解决的是近景精度，不是下一阶段首要任务。

原因：

- 当前主要建设是交互闭环；
- 用户拖拽并不必然要求 Low Orbit；
- RDL 需要位置预加载、区域瓦片和 LOD；
- 它会增加网络、缓存和 shader 复杂度。

建议：

- 保留 RDL 方案；
- 下一阶段仅做一次只读现状复核；
- 不与拖拽、手势、UI 同批施工；
- 只有 Low Orbit/City Focus 的近景模糊成为真实用户痛点后，再启动 Japan benchmark。

---

# 八、星空系统：修复，不重建

## 1. 已确认的现状

当前已有：

- `buildStarField(...)`；
- Points 星尘；
- `starSphereMaterial`；
- `uTime` twinkle；
- 时段透明度；
- 既有星场设计资料。

因此原方案中“星空无、从零建设双层 Points”的判断应废止。

## 2. 下一步审计顺序

1. 星场对象是否已加入正确 scene；
2. 是否错误加入 earthGroup；
3. renderOrder；
4. depthTest；
5. depthWrite；
6. frustum culling；
7. clipping planes；
8. canvas/container 裁切；
9. skyMesh 是否覆盖；
10. opacity 最终计算值；
11. toneMapping / exposure；
12. Bloom；
13. 星点尺寸与 DPR；
14. 背景颜色是否吞没星点；
15. CLAUDE.md 已知问题是否过期。

## 3. 修复路径

优先修复现有系统。

只有满足以下条件才新增第二层：

- 现有 900/1200 点修复后仍缺少层次；
- 亮星与星尘无法通过现有 material 分离；
- 性能允许；
- 不需要复制一套时段控制。

第二层应作为现有 Star System 的子层，而不是新建平行系统。

---

# 九、白天背景建设

## 1. 当前问题

白天的核心问题是：

- 背景平；
- 方向感不足；
- 地球大气与背景分离；
- 纯渐变容易单调；
- 但不能用白天星星来填空。

## 2. 第一轮只做三件事

### A. 垂直大气层次

强化：

- 天顶；
- 中层；
- 地平线；
- 下部空间。

先复用现有 Sky LUT / skyMesh，不新建第二套背景系统。

### B. 太阳方向场

使用与地球太阳光照同源的方向数据。

目标：

- 一侧略暖、略亮；
- 对侧略冷、略深；
- 不直接显示太阳；
- 不形成明显 radial 光斑。

### C. Sky-Earth 色彩一致性

重点检查：

- noon；
- dawn；
- sunset；
- evening；
- deepNight。

## 3. 第二轮候选

在第一轮稳定后再做：

- Air Volume；
- 高空卷云；
- UI 中央安全区衰减。

## 4. 不应同时施工

同一轮禁止同时修改：

- Earth texture；
- cloud shell；
- rimGlow；
- toneMapping；
- star system；
- UI 状态；
- 手势。

白天背景应作为单独视觉候选轮次。

---

# 十、Astronomy Visual Bridge 的位置

## 1. 不进入当前开发批次

虽然 `astronomy.js` 是比通用节日特效更好的长期方向，但当前不应在拖拽和 UI 建设期间接入。

## 2. 后续优先级高于通用事件

后续建议使用同一份天文数据驱动：

- 月相 → 夜间亮度、星场上限、海洋反光；
- 节气 → 天空温度、空气清澈度、镜头高度倾向；
- 季节 → 运动速度与构图权重；
- 文化节点 → 一次性低频构图或来信。

## 3. 彩蛋保留方式

万圣节血雾等已有彩蛋不删除，但应：

- 人工触发；
- 隐藏入口；
- 不进入默认 Living Earth 自动调度；
- 不抢占 Astronomy Bridge 主路线。

---

# 十一、下一阶段任务拆分

# Stage 0：只读联合审计

## 目标

在任何施工前，形成真实的 UI、手势、镜头和星空地图。

## 任务

1. 审计三态 UI 所涉及 DOM；
2. 审计现有 `dj-speaking` 淡入淡出机制；
3. 审计 page1/page2 翻页手势；
4. 审计空白点击唤出控件逻辑；
5. 审计 canvas pointer-events；
6. 审计播放器 UI hit zone；
7. 审计地球 quaternion 写入点；
8. 审计 `_updateGramTransition/_updateGramMotion/_updateGramAutoPilot`；
9. 审计现有星空；
10. 审计 `astronomy.js` 输出字段；
11. 审计 RDL 当前代码是否已接入或仅为方案；
12. 输出冲突矩阵和最小修改文件清单。

## 禁止

- 修改代码；
- 修改 CSS；
- 新增资源；
- commit。

## 产物

```text
P4_Stage0_Current_State_Audit.md
P4_Gesture_Conflict_Matrix.md
P4_Minimum_Change_Map.md
```

---

# Stage 1：完整态 ↔ 极简态

## 目标

先实现 UI 退后，不引入地球拖拽。

## 修改范围

优先：

- `index.html`
- UI 状态相关 JS/CSS 文件

暂不修改：

- earth3d.js 镜头和 quaternion；
- sky；
- star；
- cloud；
- service worker。

## 任务

1. 建立 `uiMode = full | minimal | earthOnly`；
2. 先接入 full/minimal；
3. 复用 `dj-speaking` 的 class-based 动画方式；
4. 新歌开始进入 full；
5. 5 秒无操作进入 minimal；
6. UI 操作重置倒计时；
7. minimal 短触恢复 full；
8. pointer-events 正确关闭；
9. 切歌、暂停、失败状态处理；
10. Reduced Motion 下缩短或取消动画。

## 验收

- 无布局跳动；
- 淡出后不可误触；
- 切歌可靠回到 full；
- 点击按钮不会触发页面空白点击；
- 移动端与桌面一致；
- 不影响 page2；
- 不影响 DJ speaking。

---

# Stage 2：GestureRouter

## 目标

统一 Tap、Drag、Swipe 和 UI 命中。

## 任务

1. 建立统一 pointer 入口；
2. 建立 UI zone；
3. 建立 Earth zone；
4. 建立 edge/swipe zone；
5. 定义距离、速度、方向阈值；
6. 接管或适配旧 page swipe；
7. 接管空白 Tap；
8. 输出 debug intent；
9. pointercancel 正确恢复；
10. 多指时取消单指意图。

## 验收

- Tap 不误判 Drag；
- 慢拖不误判翻页；
- 快速纵向甩动可翻页；
- 控件始终优先；
- 同一手势只能解析为一种意图。

---

# Stage 3：最小地球拖拽

## 目标

让用户第一次真正“摸到地球”。

## 任务

1. Drag intent 接入地球；
2. 拖动开始暂停 gram update；
3. 横向增量映射 longitude；
4. 纵向增量映射 latitude；
5. 纬度 clamp；
6. 斜向复合；
7. 松手进入 holding；
8. holding 结束复用 `transitionToComposition()`；
9. 恢复 auto；
10. 切歌、翻页、切后台中断处理；
11. debug state；
12. 桌面和移动真机测试。

## 第一轮不做

- Pinch；
- 强惯性；
- roll；
- Director；
- 镜头选择菜单。

## 验收

- 无抢控制；
- 无跳动；
- 无翻转；
- 无穿透；
- 3～8 秒内自然回归；
- 原有自动镜头无退化。

---

# Stage 4：地球态候选

## 目标

验证只有地球的纯视觉模式。

## 任务

1. 接入 `earthOnly`；
2. 先使用隐藏/debug 入口；
3. 所有 DOM 信息淡出；
4. 地球拖拽仍可用；
5. Tap 可恢复；
6. 切歌策略 A/B：
   - A：保持 Earth Only；
   - B：短暂回 Full，再退回；
7. 对比两种策略。

## 验收

- 用户知道如何退出；
- 不出现黑屏感；
- 地球视觉足以独立成立；
- UI 恢复无跳动；
- 不自动默认上线，先候选。

---

# Stage 5：现有星空修复

## 目标

让夜晚背景真正显示现有星场。

## 任务

按审计结果修复：

- clipping；
- renderOrder；
- depth；
- opacity；
- size；
- Bloom；
- skyMesh 遮挡；
- DPR。

## 禁止

- 新建平行星空；
- 同轮修改白天背景；
- 同轮修改云层；
- 同轮修改地球材质。

---

# Stage 6：白天背景第一轮

## 目标

解决白天单调，但保持克制。

## 任务

1. 5 个时段锚点审计；
2. 垂直 LUT 层次；
3. 太阳方向场；
4. Sky-Earth 同源；
5. UI 可读性；
6. 移动端性能；
7. 11 时段扩展。

## 暂不做

- 高空云；
- Air Volume；
- 天气；
- 真实太阳盘；
- 白天星星。

---

# Stage 7：运动方向产品化

## 目标

将已有运动原语整理成少量正式 Profile。

## 任务

1. 顺时针；
2. 逆时针；
3. 上下；
4. 左斜；
5. 右斜；
6. 极地；
7. hold；
8. 自动选择权重；
9. 与 full/minimal/earthOnly 的行为适配。

## 验收

- 方向变化低频；
- 不像屏保；
- 不像音游；
- 不在一首歌内频繁反向；
- 用户拖拽后自动运动正确恢复。

---

# 十二、本轮明确不做

为防止任务失控，以下内容不进入下一阶段主线：

- 完整 Earth Director；
- RDL Mapbox 动态瓦片接入；
- 全球 GIS；
- Pinch；
- 双指旋转；
- 大规模新镜头库；
- 每首歌 AI 语义驱动；
- FFT 鼓点联动；
- 实时天气；
- 七曜交接；
- 真实星表；
- 真实行星；
- 流星、卫星、极光默认事件；
- 节日自动主题系统；
- 高空云与 Air Volume 同时施工；
- service worker 大改；
- WebGPU 迁移。

这些内容不是永久删除，而是冻结。

---

# 十三、建议优先级

| 优先级 | 任务 | 用户价值 | 工程风险 |
|---|---|---:|---:|
| P0 | Stage 0 联合审计 | 间接但必要 | 低 |
| P0 | Stage 1 Full/Minimal | 高 | 低至中 |
| P0 | Stage 2 GestureRouter | 高 | 中 |
| P0 | Stage 3 地球拖拽 | 极高 | 中 |
| P1 | Stage 4 Earth Only 候选 | 高 | 低至中 |
| P1 | Stage 5 星空修复 | 中高 | 中 |
| P1 | Stage 6 白天背景 | 高 | 中 |
| P1 | Stage 7 Motion Profiles | 中高 | 中 |
| P2 | Astronomy Bridge | 长期高 | 中 |
| P2 | RDL Japan benchmark | 特定场景高 | 高 |
| P3 | Journey/Surprise | 可选 | 中 |
| P3 | 彩蛋与事件 | 可选 | 中 |

---

# 十四、下一条应下达给 Claude Code 的任务

下一步不应直接施工拖拽，也不应先改天空。

应先下达：

> P4 Stage 0：三态 UI、现有手势、地球控制与星空联合只读审计。

建议指令：

```text
你是 RodiO P4 · Touch the Earth 阶段的执行审计助手。

本轮阶段：只读联合审计
本轮目标：建立三态 UI、页面手势、地球交互控制和现有星空的真实代码地图。
允许修改文件：无
禁止修改文件：全部
允许生成资源：否
允许 commit：否

请阅读：
1. 00_Master_Roadmap_v3.1_FullExecution.md
2. 01_Current_Workflow_How_To_Use_This_Pack.md
3. 03_Sky_Visual_System_Implementation_v3.1.md
4. 05_Earth_Camera_Motion_Music_Implementation_v3.1.md
5. 07_Claude_Codex_Execution_Protocol_v3.1.md
6. RodiO 产品方案 v4
7. 当前 earth3d.js、index.html 及 UI 相关文件
8. CLAUDE.md

请只读核查并输出：

A. 三态 UI 基础
- 当前完整播放 UI 的 DOM 与 CSS 结构；
- #app.dj-speaking 使用的 class、transition、pointer-events 逻辑；
- 哪些元素应分别属于 full、minimal、earthOnly；
- 新歌、切歌、暂停、DJ speaking 的现有事件入口；
- 最小化状态适合复用的代码位置。

B. 手势系统
- page1/page2 当前 touch/pointer 监听；
- 点击空白唤出控件的现有实现；
- 播放器按钮与进度条的事件处理；
- canvas/#earth3d-layer 的 pointer-events；
- 手势监听是否重复；
- Tap/Drag/Swipe 三者的冲突矩阵。

C. 地球控制
- quaternion、lat/lon、camera、FOV 的全部写入点；
- _updateGramTransition/_updateGramMotion/_updateGramAutoPilot 的调用位置；
- transitionToComposition() 的入口、参数和中断行为；
- 最小 earthInteractionState 可以插入的位置；
- 拖拽期间暂停哪些函数最安全；
- 松手后如何复用现有回归。

D. 星空
- buildStarField、stars、starSphereMaterial 的真实实现；
- scene 挂载层级；
- renderOrder/depth/frustum/clipping；
- uTime/twinkle；
- 时段 opacity；
- CLAUDE.md “星星被 canvas clipping 遮挡”是否仍准确；
- 为什么当前视觉上像没有星星。

E. 输出
1. 当前真实状态；
2. 冲突矩阵；
3. 推荐最小修改文件；
4. Stage 1 Full/Minimal 的施工方案；
5. Stage 2 GestureRouter 的施工方案；
6. Stage 3 地球拖拽的施工方案；
7. 星空修复建议；
8. 风险与回滚；
9. 不应处理的事项。

不得修改任何文件，不得生成候选，不得 commit。
```

---

# 十五、最终结论

下一阶段最重要的不是继续增加更多天空、镜头或彩蛋，而是完成一个明确的产品闭环：

> 界面退后，地球接管；用户触摸，系统让权；用户离开，系统自然恢复。

三态 UI 与丰富玩法不冲突。三态 UI 决定信息密度，Living Earth 决定体验深度。

因此，正式执行顺序确定为：

```text
联合审计
→ Full/Minimal
→ GestureRouter
→ 地球拖拽
→ Earth Only 候选
→ 星空修复
→ 白天背景
→ 运动方向产品化
```

这条路线既保留了初始 Living Earth 的方向，也吸收了 Claude Code 对真实代码的纠偏，同时遵守 v3.1 文件包的单任务、先审计、后候选、再验收原则。

完成上述阶段后，RodiO 将第一次从“看起来像一个地球播放器”，进入“用户能够真正进入并触摸的音乐空间”。
