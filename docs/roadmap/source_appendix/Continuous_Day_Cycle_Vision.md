对，这个必须做，而且它的重要性其实高于继续增加新的主题。

现在 11 个时段更像 11 张已经调好的“关键帧”：

```text
dawn → sunrise → earlyMorning → morning → noon
→ afternoon → goldenApproach → sunset
→ evening → lateEvening → deepNight
```

当前逻辑如果是到达某个时间点后，整套参数直接从 A 切换成 B，那么即使每个时段单独看都很好，连续观看时仍会出现：

- 天空突然换色
- 海洋瞬间变亮或变暗
- 城市灯光跳变
- 云层突然被染色
- 星空突然出现
- 大气辉光形态突变

正确方向不是增加更多时段，而是把这 11 个时段重新定义为：

> **11 个视觉锚点，而不是 11 个互斥模式。**

# 一、建立 Continuous Day Cycle

系统始终计算当前时刻处于哪两个相邻锚点之间，然后对参数连续插值。

例如当前时间在 `sunrise` 和 `earlyMorning` 之间：

```js
currentVisual =
  interpolate(
    SUNRISE_CONFIG,
    EARLY_MORNING_CONFIG,
    progress
  );
```

假设：

```text
sunrise       06:00
earlyMorning  07:30
当前时间      06:45
```

则：

```text
progress = 0.5
```

此时不是 sunrise，也不是 earlyMorning，而是两者之间自然生成的状态。

但不能简单对所有参数做同样的线性插值。真正需要设计的是一套**分轨演变系统**。

# 二、不要用统一进度控制所有视觉

日出后，现实中的变化并不是同步发生的：

- 太阳位置持续移动
- 地平线暖光较快消退
- 天空顶部蓝色较慢恢复
- 城市灯光可能稍后才熄灭
- 海面亮度会跟太阳高度变化
- 星空比城市灯光更早消失
- 云底暖色可能比天空霞光保留更久
- 阴影方向连续变化，但强度变化并不均匀

因此应把视觉拆成多个独立的 transition track。

```text
Solar Track
Sky Track
Atmosphere Track
Earth Surface Track
Ocean Track
Cloud Track
City Light Track
Stars Track
Bloom/Post Track
```

每条轨道共享当前时间，但拥有不同的曲线、延迟和持续时间。

------

# 三、太阳位置应成为系统主时钟

未来不要只用“几点钟”决定画面，而应优先用太阳高度角。

核心变量可以是：

```js
solarElevation
solarAzimuth
```

太阳高度角大致对应：

```text
太阳低于地平线很多：深夜
太阳接近地平线下方：黎明、暮光
太阳刚越过地平线：日出、日落
太阳逐渐升高：清晨、上午
太阳最高：正午
太阳逐渐降低：下午、金色时刻
```

这样同样是 18:00：

- 夏季可能还接近白天
- 冬季可能已经进入夜色
- 不同纬度也会有完全不同的视觉状态

所以未来推荐：

```text
日期 + 经纬度 + 当前时间
        ↓
计算真实太阳位置
        ↓
映射到 11 个视觉锚点
        ↓
连续插值生成当前画面
```

11 个时段继续保留，但它们从“时间开关”变成太阳周期上的艺术化控制点。

# 四、每个参数都要有插值类型

## 1. 数值参数

例如：

- exposure
- saturation
- oceanDarken
- cloudDensity
- starOpacity
- cityLightStrength
- rimGlowStrength

可以连续插值：

```js
value = lerp(from, to, easedProgress);
```

但大多数情况下不要使用纯线性 `progress`，而应使用缓入缓出：

```js
const t = progress * progress * (3 - 2 * progress);
```

这样变化开始和结束都更柔和。

## 2. 颜色参数

颜色不能直接在普通 RGB 中插值。

例如从深蓝过渡到橙色，RGB 中间值很容易变成灰脏色或粉棕色。

建议优先使用：

- OKLab
- OKLCH
- 线性空间 RGB

RodiO 尤其适合 OKLCH，因为可以分别控制：

```text
L：亮度
C：色彩浓度
H：色相
```

这样晚霞从金色转向粉紫时，可以控制色相旋转方向，而不是直接穿过一段脏灰色。

```js
color = interpolateOklch(colorA, colorB, t);
```

还要处理色相环的最短路径，否则可能从橙色错误地绕过绿色再到紫色。

## 3. 开关类参数

例如：

- starsVisible
- cityLightsEnabled
- moonVisible
- auroraEnabled
- cloudLayerEnabled

不能再用 boolean 突然开关。

应改成连续权重：

```js
starOpacity: 0 → 1
cityLightOpacity: 0 → 1
moonVisibility: 0 → 1
```

只有资源加载、渲染管线启停仍可以保持布尔值，但视觉呈现必须由透明度或强度渐变完成。

## 4. 枚举或纹理参数

例如云类型、天空 LUT、海洋纹理、星空贴图不能直接插值枚举。

可以用双源混合：

```text
Texture A
Texture B
Blend Weight
```

过渡过程中同时保留两个资源：

```glsl
result = mix(textureA, textureB, blend);
```

完成后再卸载旧资源。

但要避免每个时段都更换纹理。大多数连续变化最好由统一 shader 参数完成，纹理切换只用于真正不同的结构状态。

------

# 五、建立非对称过渡

从 A 到 B 和从 B 到 A，不应该总是镜像。

例如：

## 日出方向

```text
dawn → sunrise → earlyMorning
```

可能表现为：

- 地平线暖光快速增强
- 天空顶部仍保持深蓝
- 星星快速消退
- 城市灯光延迟减弱
- 云顶首先变金
- 云底稍后变亮

## 日落方向

```text
goldenApproach → sunset → evening
```

可能表现为：

- 地表直射光先下降
- 云层暖色继续增强
- 天空顶部迅速转深蓝
- 城市灯光在环境尚未完全变黑时开始出现
- 晚霞在太阳落山后仍保留一段时间
- 星空随后逐渐出现

所以不能假设：

```text
sunrise → morning
```

只是：

```text
evening → sunset
```

的倒放。

两条方向需要独立的曲线和视觉节奏。

# 六、11 个时段建议重新定义为锚点区间

不要让锚点平均分布在 24 小时里。晨昏变化快，正午和深夜变化慢。

建议采用“非均匀密度”：

| 锚点           | 主要职责                   |
| -------------- | -------------------------- |
| dawn           | 日出前冷蓝、地平线初亮     |
| sunrise        | 太阳越过地平线、暖光爆发   |
| earlyMorning   | 霞光退去、环境亮度恢复     |
| morning        | 稳定清晨蓝、较柔和日光     |
| noon           | 高太阳角、最清晰的白昼基线 |
| afternoon      | 暖度缓慢增加、阴影拉长     |
| goldenApproach | 金色时刻开始、地表转暖     |
| sunset         | 太阳贴近或越过地平线       |
| evening        | 晚霞残留、城市开始亮灯     |
| lateEvening    | 天空进入深蓝、灯光主导     |
| deepNight      | 夜景稳定基线               |

注意：锚点不一定绑定固定钟点，而应绑定太阳角度和艺术偏移。

例如可以定义：

```js
const TIME_ANCHORS = [
  { id: 'dawn',            solarElevation: -10 },
  { id: 'sunrise',         solarElevation:  -1 },
  { id: 'earlyMorning',    solarElevation:   7 },
  { id: 'morning',         solarElevation:  20 },
  { id: 'noon',            solarElevation:  55 },
  { id: 'afternoon',       solarElevation:  30 },
  { id: 'goldenApproach',  solarElevation:  10 },
  { id: 'sunset',          solarElevation:   0 },
  { id: 'evening',         solarElevation:  -5 },
  { id: 'lateEvening',     solarElevation: -11 },
  { id: 'deepNight',       solarElevation: -18 }
];
```

这里只是结构示意，最终数值需要结合你已经调好的视觉结果反推，而不是生搬硬套真实天文阈值。

# 七、必须处理太阳高度相同但阶段不同的问题

上午和下午可能拥有相同太阳高度角，但视觉不能一样。

例如太阳高度都是 `20°`：

- 上午天空更清冷
- 下午地表更暖
- 下午空气可能更有薄雾
- 云色和阴影气质不同

所以不能只用 `solarElevation` 一个变量。

至少还需要：

```js
dayPhaseDirection: 'ascending' | 'descending'
```

即太阳正在升高还是降低。

最终状态由三部分决定：

```text
太阳高度
+ 太阳方位
+ 上升/下降阶段
```

这才能区分 morning 和 goldenApproach。

# 八、建议加入“残留效应”

自然天空有记忆，不是太阳一移动，所有颜色立即跟着变。

可以设计若干滞后参数：

```text
Afterglow：日落后的晚霞残留
CloudHeatRetention：云层暖色残留
CityLightDelay：城市灯光启闭延迟
StarAdaptation：星空出现与消失延迟
OceanResponseLag：海面整体色调响应延迟
```

例如太阳落下后：

- 直射光快速消失
- 地平线暖光仍维持
- 高层云仍呈粉红
- 低层云已经变成紫灰
- 城市灯光逐渐出现
- 星空尚未完全显现

这正是“日落之后仍然很美”的来源。

一个基础实现可以使用阻尼而不是直接赋值：

```js
currentValue +=
  (targetValue - currentValue) *
  (1 - Math.exp(-deltaTime / responseTime));
```

不同系统拥有不同 `responseTime`：

```text
太阳方向：几乎立即
天空环境色：较快
云层染色：中等
海洋色调：中等
城市灯光：有延迟
星空：更慢
```

------

# 九、云系统必须单独设计时间过渡

你前面希望云与天空颜色、光照共同形成各种美景，这里正好统一起来。

云的时间演变至少要拆成：

```text
cloudAmbientColor
cloudSunColor
cloudShadowColor
cloudTransmission
cloudSilverLining
cloudWarmth
cloudOpacity
cloudCoverage
```

例如 `sunset → evening`：

### 太阳刚落下

- 云边缘仍有强金光
- 云面出现橙粉
- 云底为冷紫灰
- 天空地平线保持橙红

### 过渡中期

- 金色减弱
- 粉色扩散
- 云阴影加深
- 天空顶部转深蓝
- 地球表面直射光消失

### evening 稳定

- 云高光变为冷粉或银灰
- 云底接近深蓝灰
- 城市灯光开始成为主要光源
- 霞光只残留在低地平线

不能只把 `cloudColor` 从橙色 lerp 到蓝色，那会失去层次。

------

# 十、城市灯光需要按“环境暗度”控制

城市灯不应该在某个时段统一打开。

建议将灯光强度与环境亮度、太阳高度以及时间方向结合：

```js
cityLightTarget =
  darknessFactor *
  eveningActivation *
  cloudOcclusionBoost;
```

这样：

- 阴天时可能较早显现
- 晴朗晚霞中不会过早抢画面
- 深夜达到最亮
- 黎明时不会瞬间全部熄灭，而是逐渐退去
- 云层遮挡区域可以略微增强灯光可见度

但不要模拟每个真实城市开灯时间。RodiO 需要的是可信、稳定的艺术效果。

# 十一、用户手动拖动时间时要采用不同策略

自然运行和手动拖动不能用完全相同的缓慢阻尼。

## 实时时钟模式

按真实时间连续变化，使用正常过渡和残留效应。

## 加速时间模式

例如用户观看 24 小时缩时：

- 保留插值
- 缩短残留时间
- 保证昼夜变化仍然流畅
- 不允许云色、灯光严重滞后于太阳

## 手动拖动时间轴

用户拖动时需要立即接近目标状态，否则操作会显得迟钝。

建议：

```text
拖动中：直接按时间求值，不加长期阻尼
松手后：用 1–2 秒完成最后收敛
```

## 直接选择时段

如果用户点选“深夜”：

不要瞬间切换，可以使用：

```text
1.5–3 秒艺术化过渡
```

但这只是交互动画，不是自然昼夜演变本身。

------

# 十二、架构上建议建立 DayCycleController

不要继续在各个 shader、云系统、灯光系统里分别判断当前时段。

统一输出一个完整的环境状态：

```js
class DayCycleController {
  evaluate({
    date,
    time,
    latitude,
    longitude,
    playbackMode
  }) {
    return {
      phase,
      previousAnchor,
      nextAnchor,
      progress,

      solarElevation,
      solarAzimuth,
      sunDirection,
      moonDirection,

      sky,
      atmosphere,
      earth,
      ocean,
      clouds,
      cityLights,
      stars,
      postProcessing
    };
  }
}
```

各视觉模块只负责消费结果：

```js
applySkyState(state.sky);
applyOceanState(state.ocean);
applyCloudState(state.clouds);
applyCityLightState(state.cityLights);
```

而不是每个模块自己写：

```js
if (theme === 'sunset') ...
```

这一步非常关键。否则以后增加 Cloud、Flight、Horizon、Underwater 后，每个模式都会复制一套时段判断，最终极难维护。

# 十三、11 个锚点要分成“共享环境”与“视角解释”

同一个时间状态，应当被不同空间模式以不同方式表现。

例如 sunset：

### Orbit

- 地球边缘出现暖色大气
- 昼夜交界明显
- 城市灯光开始出现

### Cloud

- 云顶金色
- 云底紫灰
- 光束穿过云隙

### Flight

- 地平线长条霞光
- 云海被侧光照亮
- 航线前方进入夜色

### Horizon

- 太阳靠近海平线或山线
- 天空垂直颜色梯度最明显
- 地表阴影拉长

### Underwater

- 海面上方出现暖色微光
- 水体深处仍保持冷蓝
- 暖色随深度快速消失

所以 `DayCycleController` 应输出统一的物理与艺术环境变量，各 View 再进行自己的映射，而不是每个 View 有一套完全独立的 11 时段色表。

------

# 十四、建议建立参数分级

不是所有参数都允许跨锚点自由变化。

## A 级：连续物理参数

始终连续变化：

- 太阳方向
- 太阳高度
- 天空亮度
- 阴影方向
- 星光可见度
- 城市灯光权重

## B 级：艺术调色参数

在锚点间平滑过渡：

- 海洋色调
- 陆地饱和度
- 大气辉光颜色
- 云阴影颜色
- Bloom
- exposure

## C 级：结构状态

只在安全区间切换：

- 云类型
- 云纹理
- 后处理 LUT
- 特殊天气层
- 极光、雷暴等事件

结构状态不能在任意时刻反复交叉混合，应设计隐藏切换点或较长的淡入淡出。

------

# 十五、最终目标不是“11 段渐变”

需要避免把它做成普通的：

```text
A 配色 → B 配色 → C 配色
```

最终应该是一个连续环境系统：

```text
Astronomical State
真实太阳、日期、经纬度
        ↓
Art Direction Layer
11 个视觉锚点与人工曲线
        ↓
Environment State
天空、云、海、陆地、灯光、星空
        ↓
View Interpretation
Orbit / Cloud / Flight / Horizon / Underwater
        ↓
Final Rendering
```

这能保证现有 11 个时段的成果不被推翻，而是被提升为整个系统的美术基准。

# 推荐实施顺序

第一步，保留现有 11 份配置不动，把强制切换改成**相邻配置插值**。

第二步，把 RGB 颜色插值改成 OKLCH 或线性颜色空间，并将所有视觉开关改为连续权重。

第三步，拆分天空、海洋、云、城市灯光、星空的独立过渡曲线。

第四步，引入太阳高度角、太阳方位和升降方向，替代固定钟点作为主要驱动。

第五步，加入晚霞残留、云层余晖、灯光延迟和星空适应等滞后机制。

第六步，让 Orbit、Cloud、Flight、Horizon、Underwater 共享同一套环境状态，再分别解释。

## 最终判断

你的方向是对的。现在的 11 个时段应该继续保留，因为它们是已经完成的艺术锚点；但未来不能再被当作 11 个互斥主题。

最终需要建设的是：

> **一个以太阳运动为主轴、以 11 个时段为关键帧、各视觉系统按独立曲线连续演变的 Day Cycle。**

这样用户即使一直停留在同一个画面里，也能逐渐看到：

- 黎明从深蓝中出现
- 日出金光扩散
- 霞光慢慢退去
- 清晨变得通透
- 正午稳定
- 下午逐渐变暖
- 晚霞重新出现
- 城市灯光逐盏显现
- 夜空与云层慢慢进入深夜

不是“系统换了一个主题”，而是**世界真的经过了一天**。