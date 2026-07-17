# RodiO 天空视觉系统设计文档

**版本** v3.2  
**日期** 2026-06-01  
**作者** RW + 苏衡  
**关联项目** RodiO PWA · GitHub: Heyyeqi/RodiO  
**本版变更**（相对 v3.1）
- 过渡机制从"CPU 端每帧插值 + 单 LUT 上传"改为"双 LUT + GPU 端 mix()"，消除每帧纹理上传
- DataTexture 格式从 RGBFormat 改为 RGBAFormat（RGBFormat 在 Three.js r137+ 废弃）
- 显存预算从单一 200MB 改为分级预算（移动端 128MB / 桌面端 512MB，8K 纹理必须压缩）
- Shader t 值从 worldPosition.y 改为基于 viewDir（修正相机偏移时渐变方向错误的问题）
- LUT 生成从 Catmull-Rom 改为按 pos 线性采样（消除 overshoot 风险，逻辑更简单）
- CSS 降级补充 OKLab 语法
- Tone Mapping exposure 标注为初始标定值，标注微调范围

---

## 一、背景与起点

RodiO 是一个宇宙电台 PWA，核心视觉是一个 Three.js 驱动的 3D 地球背景层。整个界面的情绪基调由"此刻是几点、此刻在哪里"决定。

**天空不是装饰，是叙事的一部分。**

当前版本（截至 2026-06-01）已实现：

- 基于用户地理位置的地球朝向（quaternion 定位，上海为默认锚点）
- 9 个时段的主题切换（本版扩展为 11 个）
- 地球昼夜纹理混合（NASA Blue Marble 8K 日图 + Black Marble 夜图）
- 城市灯光 emissive 层，随时段淡入淡出
- 星场粒子系统（1200 点，程序化生成）
- 大气层半透明球壳（BackSide MeshPhongMaterial）

---

## 二、当前问题诊断

### 2.1 天空色与地球光照脱节（核心问题）

```
index.html #app { background: linear-gradient(...) }   ← CSS 静态，不感知时段
earth3d.js THEME_VISUAL_CONFIG                         ← Three.js 动态，控制地球
```

两套系统互不感知。代码定位：`index.html` 第 63–67 行，`#app` 的 `background` 属性。

### 2.2 时段分布不均

原有 9 个时段中：
- 下午（14:00–17:00）跨越三小时只有一段，错过了 16:00 后侧光质感显现的"暮前"节点
- 夜晚（19:00–22:00）跨越三小时只有一段，错过了蓝色时刻结束后天空快速暗落的"入夜"节点

### 2.3 城市灯光色调单一

所有时段 emissiveColor 均在 `#ffbe63`–`#ffd08a` 的琥珀黄范围内，没有变化。真实城市灯光在不同背景亮度下的感知色温不同，这种差异可以通过 emissiveColor 微调来模拟。

### 2.4 其余问题

- 天空渐变锚点不足，RGB 插值在互补色区间经过泥灰区
- 星场透明度未与天空系统联动
- 大气边缘光晕缺失
- 地球纹理缺少云层和海水高光分离

---

## 三、设计目标

> 对真实世界的诗意展示。

**真实**：天空颜色来自大气光学物理，不是主观选色。  
**诗意**：提炼了真实之后的美化版本，色彩更干净，渐变更顺滑，但不偏离真实色相方向。

**边界声明**：本方案色值基于典型晴天条件下中纬度（30°–50°N）春秋分、人眼视觉记忆与摄影参考的加权提炼，非辐射度计实测数据。所有色值标注为 **sRGB 8-bit**。

---

## 四、物理基础

### 4.1 瑞利散射
天顶蓝（光路最短），地平线偏白（光路最长），正午天顶最蓝。

### 4.2 米氏散射
气溶胶（水汽、尘埃）产生白色/灰色雾化。下午积累了一天的尘埃，地平线比上午更白更暖。

### 4.3 太阳角度与橙色
日出/落日时橙色经过厚大气衰减后是掺了灰调的**赭石、赤陶、琥珀**，不是饱和铬橙。

### 4.4 品红过渡带
天顶深蓝与地平橙红之间的玫瑰洋红/品红，对应民用曙暮光时段。
- **日出品红带**：大气洁净，偏玫瑰色（HSL 色相约 330°–345°）
- **落日品红带**：气溶胶积累，偏紫调（HSL 色相约 310°–325°），域更宽更重

### 4.5 黄金时刻与侧光
太阳高度角约 10°–25° 时，色温约 2500–4000K，产生强烈侧向暖光。暮前（16:00–17:00）是"黄金时刻前的准备阶段"，地平线已有琥珀金黄。

### 4.6 航海曙暮光与星场渐显
太阳在地平线以下 6°–18° 时，天空蓝调亮度快速下降，星场从隐约可见转为清晰。入夜（20:30–22:00）对应这个时段。

### 4.7 城市灯光感知色温与背景亮度的关系
灯光本身光谱不随时间变化，但人眼对其色温的感知受背景亮度对比影响：
- **深夜/入夜**：背景最暗，对比最强，橙色感最突出 → emissive 用深橙金
- **夜晚（蓝色时刻）**：蓝调余辉仍在，灯光与天空有互补感 → emissive 用明亮暖橙
- **黎明**：天空开始亮起，灯光对比度降低 → emissive 用低饱和暖黄
- **日出**：灯光已非主角 → emissive 极低，偏冷的黄白

---

## 五、11 时段完整序列

### 5.1 时段划分

```
22:00    04:00  05:15  06:45       09:00       11:30       14:00 16:00 17:00       19:00 20:30       22:00
  |        |      |      |           |           |            |     |     |           |     |           |
深夜     黎明   日出   清晨        上午        正午        下午  暮前  落日        夜晚  入夜        深夜
deepNight dawn sunrise earlyMorning morning     noon     afternoon golden sunset  evening lateEvening deepNight
                                                                   Approach
```

### 5.2 每个时段的独立性

| 时段 key | 中文 | 核心视觉特征 | 与前段的本质区别 |
|----------|------|------------|----------------|
| deepNight | 深夜 | 极深靛蓝，星场全亮，城市灯光主导 | — |
| dawn | 黎明 | 夜色主导，地平紫调隐约渗入 | 有曙光信号 |
| sunrise | 日出 | 橙蓝极差最大，品红带最鲜明 | 太阳出现，暖色主导地平 |
| earlyMorning | 清晨 | 冷蓝回归，低角度清冽感 | 橙色退场，蓝调接管 |
| morning | 上午 | 标准晴天蓝，均匀饱和 | 低角度感消失 |
| noon | 正午 | 天顶最深蓝，地平最白，最强纵深感 | 瑞利散射路径最短最纯 |
| afternoon | 下午 | 天顶微暖，地平黄绿白 | 方向感出现 |
| goldenApproach | 暮前 | 侧光金质感，暖调扩散至中层 | 橙调进入中层，影最长 |
| sunset | 落日 | 橙红主导，品红带宽重 | 暖色全面主导 |
| evening | 夜晚 | 蓝色时刻，均匀深蓝，无方向感 | 橙色消退，蓝调沉静 |
| lateEvening | 入夜 | 天空暗落，星场从隐约到清晰 | 蓝调亮度快速下降 |

---

## 六、配色方案

### 6.1 设计原则

- 每段 8–12 个锚点，按时段色彩复杂度分配密度
- 方向：从天顶（0%）到地平线（100%）
- 锚点间感知色差（ΔE）：暗部时段控制在 3–5，亮部时段 5–8
- 所有色值为 sRGB 8-bit
- LUT 生成时在 sRGB 空间线性插值（Phase 1）；后续可升级为 OKLab（Phase 2）
- 时段过渡在 GPU 端用 `mix()` 完成（双 LUT 方案），不在 CPU 端做帧间插值

### 6.2 十一时段完整锚点

格式：`位置% — #色值 — 描述`，方向从天顶（0%）到地平线（100%）。

---

#### 深夜 deepNight · 22:00–04:00 · 8 锚点
极深靛蓝底，锚点间差距极小，天顶到地平线梯度几乎消失（趋近均质）。

```
  0%  #020308  天顶，极深靛，趋近纯黑
 14%  #030509
 28%  #04060C
 42%  #050810
 55%  #060A14
 67%  #080C18
 80%  #09101C
100%  #0B1220  地平，大气曲率蓝
```

---

#### 黎明 dawn · 04:00–05:15 · 9 锚点
夜色主导，紫调从地平渗入。整体极暗，层次在深靛和深靛紫之间。

```
  0%  #04050D  天顶，近黑，极深靛底
 14%  #08091A
 28%  #0E0F26
 40%  #130F30  蓝靛转紫，色相开始偏移
 52%  #1C1138
 63%  #261440
 74%  #2E1744
 85%  #351A47
100%  #3C1E4A  地平，紫红底，黎明信号
```

---

#### 日出 sunrise · 05:15–06:45 · 11 锚点
品红带（43%–53%）是核心，日出品红偏玫瑰调（色相 330°–345°）。地平线收在淡金暖白，非饱和橙。

```
  0%  #111830  天顶，普鲁士蓝
 11%  #1A1E42
 22%  #281C52  深靛带紫，向品红过渡
 33%  #432048  蓝紫交界
 43%  #622840  暗玫瑰（品红带关键锚点，日出偏玫瑰调）
 53%  #8C3A42  砖玫红
 62%  #A84E3C  赭红
 71%  #BE6038  赭橙
 80%  #C87038  琥珀橙
 90%  #CFA060  淡金
100%  #D4B87A  地平，暖金白
```

---

#### 清晨 earlyMorning · 06:45–09:00 · 9 锚点
橙色退场，冷调回归。地平线保留极淡冰蓝，整体轻盈、清冽。

```
  0%  #182E5C  天顶，钢蓝
 12%  #1E3A70
 25%  #264884
 37%  #345C98
 50%  #4A72AA  明蓝（中层）
 62%  #6A94C0
 74%  #90B4D4
 86%  #B4D0E8
100%  #D0E4F2  地平，极淡冰蓝
```

---

#### 上午 morning · 09:00–11:30 · 9 锚点
标准晴天，蓝度均匀饱和，地平线轻微雾白。

```
  0%  #123270  天顶，深钴蓝
 12%  #183E86
 25%  #1E4C98
 37%  #2860A8
 50%  #3E76B8  天蓝（中层）
 62%  #5A8EC8
 74%  #7AAAD8
 86%  #A0C4E4
100%  #C4DCF0  地平，浅雾白
```

---

#### 正午 noon · 11:30–14:00 · 9 锚点
天顶蓝全天最深，地平线最白，最强明度对比产生纵深感。

```
  0%  #0C2C68  天顶，最深钴蓝
 12%  #12387C
 25%  #1A4890
 37%  #245CA0
 50%  #3272B0  明蓝（中层）
 62%  #4E8CC4
 74%  #72A8D6
 86%  #A4C8E6
100%  #CCE2F4  地平，白蓝散射
```

---

#### 下午 afternoon · 14:00–16:00 · 8 锚点
天顶依然钴蓝，地平线染上极淡暖调（黄绿白），中等浑浊度条件下的真实色彩。

```
  0%  #12347A  天顶，钴蓝
 14%  #1A4490
 28%  #2C5CA4
 42%  #4478B8  天蓝（中层）
 56%  #6696C8
 70%  #8CB4D4
 85%  #B0CCD8  冷蓝白
100%  #D0DCC8  地平，黄绿白
```

---

#### ★ 暮前 goldenApproach · 16:00–17:00 · 10 锚点
黄金时刻前的准备阶段。天顶仍是蓝色但色相比下午偏暖 5°–8°，暖调从地平线向中层天空扩散。地平线的琥珀金黄是本时段最鲜明的标志。

与下午的区别：橙调进入中层（60% 以下明显）。  
与落日的区别：橙色尚未主导，品红带未出现。

```
  0%  #0F2E6E  天顶，偏暖的深蓝
 11%  #163680  暖蓝
 22%  #224A90  中蓝，微暖
 33%  #3862A4  天蓝偏暖
 44%  #5880B8  暖天蓝（中层，开始感知到暖）
 55%  #7EA0C8  蓝白偏暖
 66%  #A8BED0  暖蓝白（暖调开始主导）
 77%  #C8C8A8  黄白
 88%  #D4B880  琥珀白（侧光感）
100%  #DCC070  地平，暖金黄白
```

---

#### 落日 sunset · 17:00–19:00 · 12 锚点
品红带（40%–50%）偏紫调（色相 310°–325°），比日出更宽更重。整体偏赭石/赤陶。

```
  0%  #0C1A38  天顶，沉暮蓝
 10%  #141E48
 20%  #201840  蓝转靛紫
 30%  #36183E  深靛紫
 40%  #542238  暗玫瑰（品红带关键锚点，落日偏紫调）
 50%  #783040  砖玫红（比日出更宽的品红域）
 60%  #944038  赭红
 68%  #A85030  赭橙
 76%  #B86030  赤陶橙
 84%  #C07840  琥珀
 92%  #C89858  淡金
100%  #D0B070  地平，暖白金
```

---

#### 夜晚 evening · 19:00–20:30 · 8 锚点
蓝色时刻（Blue Hour）。天空均匀深蓝，无方向感，地平线保留极微弱大气余辉。

```
  0%  #060A18  天顶，深夜蓝
 14%  #080E22
 28%  #0C142E
 42%  #101C3A
 55%  #141E42
 67%  #182240
 80%  #1C2848
100%  #202C50  地平，大气余辉蓝
```

---

#### ★ 入夜 lateEvening · 20:30–22:00 · 10 锚点
航海曙暮光时段。蓝调亮度快速下降，星场从隐约可见转为清晰。

与夜晚的区别：整体明度低约 40%，但天顶到地平线的明度梯度仍保留（"尚未完全进入深夜"的关键视觉信号）。  
与深夜的区别：深夜这个梯度几乎消失，天空趋近均质。

```
  0%  #04070F  天顶，极深，介于深夜和夜晚之间
 11%  #060A18  深靛
 22%  #08101E  靛蓝
 33%  #0A1426  深海蓝
 44%  #0C1830  海军靛蓝
 55%  #0F1E3A  深蓝（中层）
 66%  #121E3C  蓝，比夜晚略暗
 77%  #142036  偏亮蓝
 88%  #182440
100%  #1C2A48  地平，大气余辉，比夜晚更暗的蓝
```

---

### 6.3 时段间过渡节奏

**过渡机制**：双 LUT + GPU 端 `mix()`（详见第八章 8.1 节）。

**双轨时序**：

| 过渡段 | 变化幅度 | 自动推进 | 用户交互 |
|--------|----------|---------|---------|
| 深夜 → 黎明 | 小 | 5s | 2s |
| 黎明 → 日出 | 中 | 7s | 3s |
| 日出 → 清晨 | 大（最剧烈） | 10s | 4s |
| 清晨 → 上午 | 小 | 3s | 1.5s |
| 上午 → 正午 | 极小 | 3s | 1.5s |
| 正午 → 下午 | 小 | 4s | 2s |
| 下午 → 暮前 | 中（暖调扩散） | 5s | 2.5s |
| 暮前 → 落日 | 中大（品红带出现） | 6s | 3s |
| 落日 → 夜晚 | 大 | 8s | 3s |
| 夜晚 → 入夜 | 中（快速压暗） | 5s | 2.5s |
| 入夜 → 深夜 | 小 | 4s | 2s |

### 6.4 星场透明度

| 时段 | opacity | 说明 |
|------|---------|------|
| deepNight | 1.00 | 完全可见 |
| lateEvening | 0.72 | 星场清晰，接近深夜 |
| evening | 0.45 | 星场隐约可见，蓝色时刻 |
| dawn | 0.38 | 微弱残留，黎明信号 |
| sunrise | 0.12 | 几乎不可见 |
| earlyMorning | 0.00 | 完全隐藏 |
| morning | 0.00 | — |
| noon | 0.00 | — |
| afternoon | 0.00 | — |
| goldenApproach | 0.00 | — |
| sunset | 0.15 | 刚刚出现，极弱 |

---

## 七、地球视觉参数（完整 THEME_VISUAL_CONFIG）

### 7.1 城市灯光 emissiveColor 设计逻辑

| 阶段 | emissiveColor | 感知效果 |
|------|--------------|---------|
| 深夜/入夜 | `#ffbe63`–`#ffc068` 深橙金 | 背景最暗，对比最强，橙色感最突出 |
| 夜晚 | `#ffd08a` 明亮暖橙 | 蓝色时刻余辉与灯光产生互补感 |
| 黎明 | `#ffe0aa` 淡黄白 | 天空开始亮起，灯光对比度降低 |
| 日出/落日 | `#ffdca3`–`#ffd08a` 暖橙 | 灯光与天空暖调协调 |
| 白天 | 不使用（emissiveMap = null） | — |

### 7.2 完整时段参数表

---

#### deepNight（深夜）
```js
deepNight: {
  themeHour: 22.5,
  texture: {
    map: 'day', emissiveMap: 'night',
    mapColor: 0x02050B,
    emissiveColor: 0xffbe63,     // 深橙金，背景最暗时对比最强
    emissiveIntensity: 2.5,
    nightBaseIntensity: 0.58,
  },
  material: { specular: 0x000001, shininess: 0.08 },
  atmosphere: { color: '#0d2136', opacity: 0.16 },
  lighting: { ambient: 0.025, sun: 0.008, stars: 0.94, cityLightsOpacity: 0.58 },
}
```

#### dawn（黎明）
```js
dawn: {
  themeHour: 4.5,
  texture: {
    map: 'day', emissiveMap: 'night',
    mapColor: 0x667780,
    emissiveColor: 0xffe0aa,     // 淡黄白，天空亮起灯光对比降低
    emissiveIntensity: 0.72,
    nightBaseIntensity: 0.34,
  },
  material: { specular: 0x000102, shininess: 0.12 },
  atmosphere: { color: '#5f8fa9', opacity: 0.082 },
  lighting: { ambient: 0.032, sun: 0.18, stars: 0.55, cityLightsOpacity: 0.60 },
}
```

#### sunrise（日出）
```js
sunrise: {
  themeHour: 6.3,
  texture: {
    map: 'day', emissiveMap: 'night',
    mapColor: 0x96a6ae,
    emissiveColor: 0xffdca3,     // 暖橙，灯光与天空橙调协调
    emissiveIntensity: 0.46,
    nightBaseIntensity: 0.20,
  },
  material: { specular: 0x000102, shininess: 0.16 },
  atmosphere: { color: '#8ad0ff', opacity: 0.115 },
  lighting: { ambient: 0.055, sun: 0.48, stars: 0.24, cityLightsOpacity: 0.26 },
}
```

#### earlyMorning（清晨）
```js
earlyMorning: {
  themeHour: 7.4,
  texture: {
    map: 'day', emissiveMap: 'night',
    mapColor: 0xc3d1da,
    emissiveColor: 0xffddb0,
    emissiveIntensity: 0.10,
  },
  material: { specular: 0x020407, shininess: 0.55 },
  atmosphere: { color: '#8ecfff', opacity: 0.12 },
  lighting: { ambient: 0.052, sun: 0.72, stars: 0.12, cityLightsOpacity: 0.10 },
}
```

#### morning（上午）
```js
morning: {
  themeHour: 9.5,
  texture: {
    map: 'day', emissiveMap: null,
    mapColor: 0xffffff,
    emissiveColor: 0x000000, emissiveIntensity: 0,
  },
  material: { specular: 0x05070a, shininess: 1 },
  atmosphere: { color: '#88ccff', opacity: 0.15 },
  lighting: { ambient: 0.06, sun: 1.05, stars: 0.08, cityLightsOpacity: 0 },
}
```

#### noon（正午）
```js
noon: {
  themeHour: 13,
  texture: {
    map: 'day', emissiveMap: null,
    mapColor: 0xffffff,
    emissiveColor: 0x000000, emissiveIntensity: 0,
  },
  material: { specular: 0x05070a, shininess: 1 },
  atmosphere: { color: '#B7E3FF', opacity: 0.15 },
  lighting: { ambient: 0.09, sun: 1.25, stars: 0.02, cityLightsOpacity: 0 },
}
```

#### afternoon（下午）
```js
afternoon: {
  themeHour: 15.0,
  texture: {
    map: 'day', emissiveMap: null,
    mapColor: 0xf2f4f5,
    emissiveColor: 0x000000, emissiveIntensity: 0,
  },
  material: { specular: 0x04060a, shininess: 0.9 },
  atmosphere: { color: '#84bdf0', opacity: 0.14 },
  lighting: { ambient: 0.048, sun: 0.96, stars: 0.01, cityLightsOpacity: 0 },
}
```

#### ★ goldenApproach（暮前）
```js
goldenApproach: {
  themeHour: 16.5,
  texture: {
    map: 'day', emissiveMap: null,
    mapColor: 0xEEE8DC,          // 比下午更暖，侧光金质感
    emissiveColor: 0x000000, emissiveIntensity: 0,
  },
  material: { specular: 0x060402, shininess: 0.75 },
  atmosphere: {
    color: '#C0A878',            // ★ 大气壳偏金暖色，而非蓝白
                                 // 模拟低角度侧光散射进入大气层边缘的暖调
    opacity: 0.10,
  },
  lighting: { ambient: 0.052, sun: 0.88, stars: 0.00, cityLightsOpacity: 0 },
}
```

**设计说明**：
- `mapColor: 0xEEE8DC`：比下午（0xf2f4f5 冷白）明显偏暖，模拟低角度金色侧光打在地球表面的整体暖化
- `atmosphere.color: '#C0A878'`：暮前最重要的地球视觉特征——大气壳偏向琥珀金，与天空地平线锚点色（`#DCC070`）形成协调
- `shininess: 0.75`：比正午低，侧光条件下镜面反射角度不佳

#### sunset（落日）
```js
sunset: {
  themeHour: 18.2,
  texture: {
    map: 'day', emissiveMap: 'night',
    mapColor: 0xb4c2cb,
    emissiveColor: 0xffd08a,     // 明亮暖橙，灯光刚刚点亮
    emissiveIntensity: 0.16,
  },
  material: { specular: 0x000102, shininess: 0.18 },
  atmosphere: { color: '#6a9fd1', opacity: 0.075 },
  lighting: { ambient: 0.046, sun: 0.40, stars: 0.34, cityLightsOpacity: 0.18 },
}
```

#### evening（夜晚）
```js
evening: {
  themeHour: 20.0,
  texture: {
    map: 'day', emissiveMap: 'night',
    mapColor: 0x050912,
    emissiveColor: 0xffd08a,     // 明亮暖橙，蓝色时刻灯光与蓝天产生互补
    emissiveIntensity: 2.2,
  },
  material: { specular: 0x000102, shininess: 0.10 },
  atmosphere: { color: '#203750', opacity: 0.18 },
  lighting: { ambient: 0.06, sun: 0.04, stars: 0.78, cityLightsOpacity: 0.58 },
}
```

#### ★ lateEvening（入夜）
```js
lateEvening: {
  themeHour: 21.0,
  texture: {
    map: 'day', emissiveMap: 'night',
    mapColor: 0x030710,          // 比 evening 更暗，地球表面几乎全黑
    emissiveColor: 0xffc068,     // 比 evening 略深的橙金，背景更暗对比更强
    emissiveIntensity: 2.35,
  },
  material: { specular: 0x000102, shininess: 0.09 },
  atmosphere: { color: '#162840', opacity: 0.17 },
  lighting: { ambient: 0.038, sun: 0.015, stars: 0.72, cityLightsOpacity: 0.58 },
}
```

**设计说明**：
- `mapColor: 0x030710`：比夜晚（0x050912）更暗，城市灯光相对亮度更突出
- `emissiveColor: 0xffc068`：比夜晚（0xffd08a）更深橙金，模拟背景最暗时灯光感知最橙
- `atmosphere.color: '#162840'`：比夜晚（#203750）更深，为深夜做视觉铺垫

### 7.3 参数对比一览

| 时段 | mapColor | emissiveColor | emissiveIntensity | atm color | sun | cityLights |
|------|----------|--------------|-------------------|-----------|-----|-----------|
| deepNight | 0x02050B | 0xffbe63 | 2.5 | #0d2136 | 0.008 | 0.58 |
| dawn | 0x667780 | 0xffe0aa | 0.72 | #5f8fa9 | 0.18 | 0.60 |
| sunrise | 0x96a6ae | 0xffdca3 | 0.46 | #8ad0ff | 0.48 | 0.26 |
| earlyMorning | 0xc3d1da | 0xffddb0 | 0.10 | #8ecfff | 0.72 | 0.10 |
| morning | 0xffffff | — | 0 | #88ccff | 1.05 | 0 |
| noon | 0xffffff | — | 0 | #B7E3FF | 1.25 | 0 |
| afternoon | 0xf2f4f5 | — | 0 | #84bdf0 | 0.96 | 0 |
| **goldenApproach** | **0xEEE8DC** | **—** | **0** | **#C0A878** | **0.88** | **0** |
| sunset | 0xb4c2cb | 0xffd08a | 0.16 | #6a9fd1 | 0.40 | 0.18 |
| evening | 0x050912 | 0xffd08a | 2.2 | #203750 | 0.04 | 0.58 |
| **lateEvening** | **0x030710** | **0xffc068** | **2.35** | **#162840** | **0.015** | **0.58** |

---

## 八、实现架构

### 8.1 天空球 + 双 LUT 过渡方案

**核心设计**：双 LUT（skyLUTCurrent / skyLUTNext）+ GPU 端 `mix()`。

时段切换时：
1. 把当前 LUT 复制为 Current（或直接保留引用）
2. 生成新时段的 LUT 为 Next，**一次性上传至 GPU**
3. 重置 `mixRatio = 0`，开始按过渡时长递增至 1.0
4. 每帧只更新 `mixRatio` 这一个 float uniform，**不再每帧上传纹理**

这彻底消除了"10s 过渡 = 600 帧连续纹理上传"的问题。

```js
// 天空球材质
const skyMaterial = new THREE.ShaderMaterial({
  side: THREE.BackSide,
  depthWrite: false,
  depthTest: false,
  uniforms: {
    skyLUTCurrent: { value: null },   // 当前时段 LUT
    skyLUTNext:    { value: null },   // 目标时段 LUT
    mixRatio:      { value: 0.0 },    // 过渡进度 0→1
    glowIntensity: { value: 0.0 },    // Phase 2 激活
    glowColor:     { value: new THREE.Color(0.6, 0.8, 1.0) },
  },
  vertexShader: `
    varying vec3 vWorldPosition;
    void main() {
      vWorldPosition = (modelMatrix * vec4(position, 1.0)).xyz;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D skyLUTCurrent;
    uniform sampler2D skyLUTNext;
    uniform float mixRatio;
    uniform float glowIntensity;
    uniform vec3 glowColor;
    varying vec3 vWorldPosition;

    void main() {
      // ★ 基于视线方向计算 t（修正相机偏移时渐变方向错误的问题）
      // viewDir 从相机指向天空片元，y 分量对应"仰角"，与相机位置无关
      vec3 viewDir = normalize(vWorldPosition - cameraPosition);
      float t = clamp(1.0 - viewDir.y, 0.0, 1.0);
      // t = 0：天顶（对应锚点 0%）
      // t = 1：地平线（对应锚点 100%）
      // 注：若 Phase 0 审计发现上述映射在当前相机视角下
      // 导致渐变比例不理想，可调整为：
      // float t = clamp((1.0 - viewDir.y) * 0.5, 0.0, 1.0);
      // 由 Phase 0 审计报告最终确认使用哪个版本

      // 从双 LUT 采样并在 GPU 端混合
      vec3 colorA = texture2D(skyLUTCurrent, vec2(t, 0.5)).rgb;
      vec3 colorB = texture2D(skyLUTNext,    vec2(t, 0.5)).rgb;
      vec3 color  = mix(colorA, colorB, mixRatio);

      // Fresnel 大气边缘光晕（Phase 2 激活，Phase 1 中 glowIntensity = 0）
      vec3 sphereNormal = normalize(vWorldPosition);
      float fresnel = pow(1.0 - abs(dot(normalize(-viewDir), sphereNormal)), 3.0);
      vec3 horizonColor = mix(
        texture2D(skyLUTCurrent, vec2(0.85, 0.5)).rgb,
        texture2D(skyLUTNext,    vec2(0.85, 0.5)).rgb,
        mixRatio
      );
      color += mix(glowColor, horizonColor, 0.35) * fresnel * glowIntensity;

      gl_FragColor = vec4(color, 1.0);
    }
  `
})

const skyMesh = new THREE.Mesh(
  new THREE.SphereGeometry(500, 32, 32),
  skyMaterial
)
skyMesh.renderOrder = -100
scene.add(skyMesh)  // 不加入 earthGroup
```

### 8.2 LUT 生成函数

**格式：RGBA + UnsignedByteType**（RGBFormat 在 Three.js r137+ 废弃，r152+ 已移除）

LUT 生成采用**按 pos 线性采样**，不用 Catmull-Rom（消除 overshoot 风险）：

```js
function buildSkyLUT(stops) {
  // stops: [{ pos: 0.0–1.0, hex: '#xxxxxx' }, ...]，已按 pos 升序排列
  const SIZE = 16
  const data = new Uint8Array(SIZE * 4)  // RGBA，第 4 通道固定为 255

  for (let i = 0; i < SIZE; i++) {
    const t = i / (SIZE - 1)

    // 找到 t 所在的锚点区间（线性插值，无 overshoot）
    let lo = stops[0]
    let hi = stops[stops.length - 1]
    for (let j = 0; j < stops.length - 1; j++) {
      if (t >= stops[j].pos && t <= stops[j + 1].pos) {
        lo = stops[j]
        hi = stops[j + 1]
        break
      }
    }

    const span = hi.pos - lo.pos
    const alpha = span < 1e-6 ? 0 : (t - lo.pos) / span

    const loRGB = hexToLinearRGB(lo.hex)
    const hiRGB = hexToLinearRGB(hi.hex)

    // 在 linear RGB 空间插值（Phase 1）
    // Phase 2 可升级为：先转 OKLab，插值，再转回 linear RGB
    data[i * 4 + 0] = Math.round((loRGB[0] + (hiRGB[0] - loRGB[0]) * alpha) * 255)
    data[i * 4 + 1] = Math.round((loRGB[1] + (hiRGB[1] - loRGB[1]) * alpha) * 255)
    data[i * 4 + 2] = Math.round((loRGB[2] + (hiRGB[2] - loRGB[2]) * alpha) * 255)
    data[i * 4 + 3] = 255
  }

  const texture = new THREE.DataTexture(
    data, SIZE, 1,
    THREE.RGBAFormat,           // ★ 不用 RGBFormat（已废弃）
    THREE.UnsignedByteType      // ★ 不用 FloatType（移动端兼容优先）
  )
  texture.minFilter = THREE.LinearFilter
  texture.magFilter = THREE.LinearFilter
  texture.needsUpdate = true
  return texture
}

function hexToLinearRGB(hex) {
  // sRGB → linear（gamma 2.2 近似）
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255
  return [
    Math.pow(r, 2.2),
    Math.pow(g, 2.2),
    Math.pow(b, 2.2),
  ]
}
```

### 8.3 时段切换逻辑

```js
let skyTransitionStart = null
let skyTransitionDuration = 3000  // ms，按时段配置

function startSkyTransition(nextThemeKey, triggerType = 'auto') {
  const config = THEME_VISUAL_CONFIG[nextThemeKey]
  if (!config?.sky) return

  // 生成目标 LUT
  const nextLUT = buildSkyLUT(config.sky.stops)

  // 当前 LUT 升级为 Current（如果已有 Next，先把 Next 变成 Current）
  const currentLUT = skyMaterial.uniforms.skyLUTNext.value
    || skyMaterial.uniforms.skyLUTCurrent.value

  // 释放旧的 Current
  if (skyMaterial.uniforms.skyLUTCurrent.value &&
      skyMaterial.uniforms.skyLUTCurrent.value !== currentLUT) {
    skyMaterial.uniforms.skyLUTCurrent.value.dispose()
  }

  skyMaterial.uniforms.skyLUTCurrent.value = currentLUT
  skyMaterial.uniforms.skyLUTNext.value    = nextLUT
  skyMaterial.uniforms.mixRatio.value      = 0.0

  // 按触发类型选择过渡时长
  const dur = config.sky.transitionDuration
  skyTransitionDuration = triggerType === 'interactive'
    ? dur.interactive
    : dur.auto
  skyTransitionStart = performance.now()
}

// 在 renderer.setAnimationLoop 回调中每帧调用
function tickSkyTransition() {
  if (skyTransitionStart === null) return
  const elapsed = performance.now() - skyTransitionStart
  const progress = Math.min(elapsed / skyTransitionDuration, 1.0)
  // ease-in-out cubic
  const eased = progress < 0.5
    ? 4 * progress * progress * progress
    : 1 - Math.pow(-2 * progress + 2, 3) / 2
  skyMaterial.uniforms.mixRatio.value = eased
  if (progress >= 1.0) skyTransitionStart = null
}
```

### 8.4 色彩空间与 Tone Mapping

- 所有 HEX 为 sRGB 8-bit，LUT 生成时转为 linear RGB（`Math.pow(v, 2.2)`）
- `renderer.outputColorSpace = THREE.SRGBColorSpace`（r152+，已有）
- `renderer.toneMapping = THREE.ACESFilmicToneMapping`（Phase 1 设置）
- **Phase 1：`renderer.toneMappingExposure` 保持现有值不变，不按时段动态修改**
- **Phase 2 起**：按时段动态调整 exposure（初始标定值，部署后根据目标显示设备微调）

| 时段 | exposure 初始标定值 | 可调范围 |
|------|-------------------|---------|
| deepNight | 0.45 | 0.30–0.60 |
| lateEvening | 0.50 | 0.35–0.65 |
| evening | 0.55 | 0.40–0.70 |
| dawn | 0.60 | 0.45–0.75 |
| sunrise | 0.80 | 0.65–0.95 |
| earlyMorning | 0.92 | 0.75–1.10 |
| morning | 1.05 | 0.90–1.20 |
| noon | 1.20 | 1.00–1.50 |
| afternoon | 1.10 | 0.95–1.35 |
| goldenApproach | 0.88 | 0.70–1.05 |
| sunset | 0.80 | 0.65–0.95 |

### 8.5 星场透明度实现策略

**优先接入现有主题过渡插值系统**，将 star opacity 作为过渡参数之一，与 emissive、atmosphere 等同步插值。

若现有架构不支持，Phase 1 暂时在 `applyTheme()` 末尾直接设置目标值：

```js
const STAR_OPACITY_MAP = {
  deepNight: 1.00, lateEvening: 0.72, evening: 0.45,
  dawn: 0.38, sunrise: 0.12, earlyMorning: 0.00,
  morning: 0.00, noon: 0.00, afternoon: 0.00,
  goldenApproach: 0.00, sunset: 0.15,
}
if (stars?.material) {
  stars.material.opacity = STAR_OPACITY_MAP[resolvedTheme] ?? 0
  stars.material.needsUpdate = true
}
```

若暂时直接设置，Phase 1 验收标准改为"星场随时段更新"，而非"星场同步过渡"。

### 8.6 CSS 降级方案

WebGL 不可用时，取该时段 sky.stops 中最接近 0%/25%/50%/75%/100% 的 5 个关键锚点，生成渐变字符串写入 `appEl.style.background`。

优先使用 OKLab 语法（现代浏览器已支持），同时保留 sRGB fallback：

```js
function applyCssFallbackSky(themeKey) {
  const stops = THEME_VISUAL_CONFIG[themeKey]?.sky?.stops
  if (!stops) return

  const targets = [0, 0.25, 0.5, 0.75, 1.0]
  const keyStops = targets.map(target => {
    return stops.reduce((prev, curr) =>
      Math.abs(curr.pos - target) < Math.abs(prev.pos - target) ? curr : prev
    )
  })

  const colorList = keyStops.map((s, i) => `${s.hex} ${(i / 4 * 100).toFixed(0)}%`).join(', ')

  // 优先 OKLab（更准确的感知过渡）
  const oklabGradient = `linear-gradient(in oklab to bottom, ${colorList})`
  // sRGB fallback（旧浏览器）
  const srgbGradient  = `linear-gradient(to bottom, ${colorList})`

  // CSS supports() 检测
  appEl.style.background = CSS.supports('background', oklabGradient)
    ? oklabGradient
    : srgbGradient
}
```

`index.html` 的 `#app background` 修改为纯色兜底 `#06080F`。

### 8.7 显存预算（分级）

| 级别 | 目标设备 | 纹理配置 | 显存目标 |
|------|---------|---------|---------|
| Level 0 | 桌面端 | 8K 日图+夜图+4K 云+4K spec | ≤512MB（**必须使用 KTX2/Basis Universal 压缩，未压缩 8K RGBA = 128MB/张**） |
| Level 1 | 主流移动端（maxTex ≥ 4096） | 4K 日图+夜图，关闭云层 | ≤128MB |
| Level 2 | 低端移动端（maxTex ≥ 2048） | 2K 日图+夜图，关闭云层+星场 | ≤64MB |
| Level 3 | WebGL 不可用 | CSS OKLab 渐变+静态地球图片 | — |

**注意**：未压缩的 8K RGBA 纹理单张约 128MB，日图+夜图=256MB，已超过移动端预算。8K 纹理必须使用 KTX2/Basis Universal 压缩格式，压缩后约减少 70%。

---

## 九、大气边缘光晕参数（Phase 2）

Phase 1 中 `glowIntensity` 全部设为 0.0，Phase 2 激活：

| 时段 | glowIntensity | glowColor |
|------|--------------|-----------|
| deepNight | 0.08 | #3050A0 |
| lateEvening | 0.10 | #2840A8 |
| evening | 0.12 | #2840A8 |
| dawn | 0.15 | #403060 |
| sunrise | 0.35 | #C07038 |
| earlyMorning | 0.18 | #6090C0 |
| morning | 0.20 | #5080C0 |
| noon | 0.22 | #4878C8 |
| afternoon | 0.20 | #5080B8 |
| goldenApproach | 0.28 | #B08840 |
| sunset | 0.38 | #B06030 |

---

## 十、后续规划

### 10.1 地球自转
`skyMesh` 不在 `earthGroup` 内，加自转不影响天空系统。

### 10.2 OKLab 插值升级（Phase 2 LUT 生成）
Phase 1 的 LUT 生成在 linear RGB 空间插值（`hexToLinearRGB` + 线性 mix）。Phase 2 升级为：锚点 sRGB → linear RGB → OKLab → 插值 → linear RGB → DataTexture。彻底消除蓝橙互补区间的幽灵青绿色。

### 10.3 云层叠加（Phase 3）
- 独立 mesh，半径 2.04，`transparent: true`，`depthWrite: false`
- 自转用独立 quaternion：`copy(earth.quaternion)` 后 `rotateY(offset)`
- LOD：桌面 8K（KTX2 压缩），主流移动 4K，低端 2K，极低端跳过
- Phase 3 前必须执行资源审计（确认文件名、路径、格式、尺寸）

### 10.4 海水高光分离（Phase 4）
保留 `MeshPhongMaterial`，使用 `specularMap`（非 PBR 的 `roughnessMap`）。Phase 4 前同样需要资源审计。

---

## 十一、施工方案

> **施工原则**：审计先行，分阶段实施，每阶段有明确验收标准。Codex 每次施工前必须完成代码审计，施工后必须对照验收标准逐项确认，不得以"已完成"替代逐项检查。

---

### Phase 0：施工前代码审计

**在任何代码修改之前执行，不得跳过。**

---

**Codex 指令 — Phase 0**

```
你是 RodiO 天空视觉系统改造的代码审计员。
严格按以下清单审计，不修改任何代码，只输出审计报告。

【审计范围文件】
- index.html
- earth3d.js

【审计清单】

1. 天空背景现状
   - index.html 中 #app 的 background 属性完整内容（粘贴原文，含行号）
   - 是否有其他 CSS 规则也在控制 #app 背景色？
   - index.html 中是否有 JS 动态修改 #app background 的代码？

2. earth3d.js 的主题切换入口
   - THEME_VISUAL_CONFIG 包含哪些时段 key？（列出全部）
   - applyTheme() 函数的签名和调用时机？（粘贴函数签名 + 所有调用处的行号）
   - setTimeOfDay() 函数的签名和调用时机？
   - 星场（stars）的 opacity 目前在哪里控制？（行号）
   - 现有主题切换是否包含插值过渡系统？
     （是/否。如是，插值哪些参数？粘贴相关代码。）

3. 渲染系统现状
   - renderer.outputColorSpace / outputEncoding 当前设置？（粘贴代码行 + 行号）
   - renderer.toneMapping 和 toneMappingExposure 当前值？
   - renderer.toneMapping 影响哪些对象？（地球/星场/大气/城市灯光是否全部受影响）
   - scene 中目前有哪些 Mesh？
     （列出每个：geometry 类型 + material 类型 + renderOrder + depthWrite + depthTest）
   - Three.js 版本号是多少？（从 package.json 或 importmap 中读取）

4. 兼容性与性能
   - renderer.capabilities.maxTextureSize 在哪里获取？（行号）
   - 是否有现有的性能降级逻辑？
   - WebGL context lost 的处理逻辑在哪里？（函数名 + 行号）

5. 时段系统现状
   - 目前共有几个时段 key？列出全部。
   - resolveInitialPendingTheme() 完整函数体（粘贴）
   - index.html 中的时段切换按钮完整 HTML（粘贴）

6. 文档与代码一致性核查
   - VISUAL_TARGET_NDC 实际值（粘贴赋值行）
   - earthGroup.position 实际值（粘贴赋值行）
   - TEXTURE_LON_OFFSET 实际值（粘贴赋值行）
   - camera.position 实际值（粘贴赋值行）

7. 潜在冲突点
   - 是否有代码在 applyTheme() 之外修改 renderer.toneMapping 或 toneMappingExposure？
   - atmosphere mesh 的 renderOrder 是什么？天空球加入后是否存在渲染顺序冲突？
   - CSS transition 是否作用于 #app 的 background？

8. Shader t 值审计
   文档 v3.2 已采用基于视线方向的 t 值计算：
     vec3 viewDir = normalize(vWorldPosition - cameraPosition);
     float t = clamp(1.0 - viewDir.y, 0.0, 1.0);
   
   请结合当前 camera.position、earthGroup.position、VISUAL_TARGET_NDC 判断：
   a. 在正常使用状态下，viewDir.y 的实际范围大约是多少？
   b. t = 0 对应屏幕上方，t = 1 对应屏幕下方，渐变铺展比例是否合理？
   c. 如果 t 值范围偏窄（如实际最小值约 0.3），可考虑调整为：
      float t = clamp((1.0 - viewDir.y) * K, 0.0, 1.0);
      其中 K 由审计结果确定。给出 K 的建议值（或确认 K=1 即可）。

9. DataTexture 兼容性审计
   - Three.js 版本是否已移除 RGBFormat？（r137+ 废弃，r152+ 移除）
   - 确认 v3.2 使用 RGBAFormat + UnsignedByteType 在当前版本是否正确
   - 是否需要任何 WebGL 扩展支持？

10. 双 LUT 方案可行性审计
    - 当前 Three.js 版本支持 ShaderMaterial 中声明多个 sampler2D uniform 吗？
    - 在 renderer.setAnimationLoop 回调中，skyTransitionStart / mixRatio 的更新
      会与现有主题切换逻辑产生冲突吗？
    - 给出"双 LUT 方案"在当前代码架构下是否存在技术阻碍（是/否 + 理由）。

11. Tone Mapping 风险审计
    - 修改 toneMappingExposure 是否影响地球纹理、城市灯光、星场、大气层？
    - Phase 1 暂不启用动态 exposure 的建议是否合理？（是/否 + 理由）

12. 星场过渡审计
    - 现有主题切换是否已包含 stars.material.opacity 的插值过渡？
    - 若否，直接设置目标 opacity 在哪些时段过渡中最明显（hardcut 问题）？
    - 建议处理方式。

【输出格式】
逐条回答，每条给出代码行号。
最后输出"施工风险列表"，标注 高/中/低 风险。
高风险项必须说明应对方案，否则不得推进 Phase 1。
第 8–12 条必须给出明确的单一结论，不接受"视情况而定"的模糊答案。
```

---

### Phase 1：天空球系统 + 双 LUT 过渡 + 星场联动

**前置条件**：Phase 0 审计完成，无未解决高风险项，第 8–12 条审计结论已明确。

---

**Codex 指令 — Phase 1**

```
基于 Phase 0 审计报告，执行 RodiO 天空视觉系统第一阶段施工。
施工前必须再次确认：Phase 0 审计报告中第 8–12 条的结论，
并严格按报告结论执行（尤其是 t 值的 K 参数、DataTexture 格式确认）。

【修改文件】
- earth3d.js（主要）
- index.html（仅修改 #app background 和时段按钮两处）

【禁止修改以下内容，违反则本次施工无效】
- 地球纹理加载逻辑（loadTextureWithFallback 函数）
- 城市灯光 emissive 逻辑
- 地球朝向 quaternion 逻辑（getTargetOrientation、quaternionFromBasis）
- canvas 2D fallback 逻辑（#weather-canvas 相关所有代码）
- 任何播放器 UI 逻辑
- atmosphere mesh 的现有逻辑

【任务 1：时段系统扩展至 11 个】

在 THEME_VISUAL_CONFIG 中新增 goldenApproach 和 lateEvening。
完整参数严格按照本文档第七章 7.2 节，不得自行修改任何数值。

goldenApproach 参数抽查点（施工完成后必须粘贴确认）：
- texture.mapColor === 0xEEE8DC
- atmosphere.color === '#C0A878'
- lighting.sun === 0.88

lateEvening 参数抽查点：
- texture.emissiveColor === 0xffc068
- texture.emissiveIntensity === 2.35
- atmosphere.color === '#162840'
- lighting.ambient === 0.038

同步更新 resolveInitialPendingTheme()：
- h >= 16 && h < 17 → 'goldenApproach'
- h >= 20 && h < 22 → 'lateEvening'
- afternoon 边界改为 h >= 14 && h < 16

同步更新 index.html 时段按钮，加入"暮前"和"入夜"。

【任务 2：天空球 + 双 LUT 系统创建】

严格按本文档第八章 8.1 节实现。

关键点：
- Shader 中有三个过渡相关 uniform：skyLUTCurrent / skyLUTNext / mixRatio
- t 值使用 viewDir 方案，K 值按 Phase 0 审计第 8 条结论填入
- skyMesh.renderOrder = -100，depthWrite = false，depthTest = false
- skyMesh 直接 scene.add，不加入 earthGroup
- Phase 1 中 glowIntensity uniform 初始值为 0.0

【任务 3：LUT 生成函数】

严格按本文档第八章 8.2 节实现。

格式：RGBAFormat + UnsignedByteType（不用 RGBFormat，不用 FloatType）
插值：按 pos 线性采样，不用 Catmull-Rom
颜色转换：hexToLinearRGB（gamma 2.2 近似）

【任务 4：时段切换逻辑】

严格按本文档第八章 8.3 节实现 startSkyTransition() 和 tickSkyTransition()。
tickSkyTransition() 在 renderer.setAnimationLoop 回调中每帧调用。

时段切换触发规则：
- 用户点击按钮 → triggerType = 'interactive'
- 系统自动时间推进 → triggerType = 'auto'

【任务 5：THEME_VISUAL_CONFIG 扩展 sky 字段】

在所有 11 个时段配置中新增 sky 字段，包含：
- stops：严格按本文档第六章 6.2 节各时段的精确色值和百分比
- glowIntensity：Phase 1 全部设为 0.0
- glowColor：按第九章填入，但 Phase 1 不生效
- transitionDuration：按第六章 6.3 节

天空锚点色值抽查（施工完成后必须粘贴每条确认）：
- sunrise，pos=0.43，hex 应为 #622840
- sunset，pos=0.40，hex 应为 #542238
- goldenApproach，pos=1.00，hex 应为 #DCC070
- lateEvening，pos=1.00，hex 应为 #1C2A48
- noon，pos=0.00，hex 应为 #0C2C68
- deepNight，pos=0.00，hex 应为 #020308

【任务 6：applyTheme() 扩展】

在现有 applyTheme() 函数内，currentTheme 赋值后，return true 前，追加：
1. startSkyTransition(resolvedTheme, options.triggerType ?? 'auto')
2. updateStarOpacity(resolvedTheme)
3. ⚠ Phase 1 不修改 renderer.toneMappingExposure
   仅在 renderer.toneMapping 尚未设置时初始化为 ACESFilmicToneMapping

【任务 7：星场透明度联动】

按 Phase 0 审计第 12 条结论执行。
STAR_OPACITY_MAP 严格按本文档第六章 6.4 节。

【任务 8：Tone Mapping 初始化】

仅在 renderer.toneMapping 尚未设置时执行：
renderer.toneMapping = THREE.ACESFilmicToneMapping
不修改 toneMappingExposure（保持现有值）。

【任务 9：index.html CSS 修改】

将 #app 的 background 属性替换为：background: #06080F;
仅修改这一处，其他所有 CSS 保持原样。

【任务 10：CSS 降级方案】

新增 applyCssFallbackSky(themeKey) 函数，
严格按本文档第八章 8.6 节实现（含 OKLab + sRGB fallback）。
在 markUnavailable() 中调用。

【任务 11：dispose() 更新】

加入：
- skyMesh geometry / material dispose + scene.remove
- skyLUTCurrent / skyLUTNext dispose
- skyMesh = null（防止悬空引用）

【施工完成后自检清单（全部需粘贴代码，不得只说"是"）】

□ skyMesh.renderOrder === -100（粘贴赋值行）
□ skyMaterial.depthWrite === false（粘贴）
□ skyMaterial.depthTest === false（粘贴）
□ skyMesh 未加入 earthGroup（粘贴 scene.add 行）
□ Shader 中三个过渡 uniform 名称（粘贴 uniforms 定义）
□ Fragment Shader 中 t 值计算完整代码（粘贴 main() 函数）
□ t 值使用的 K 参数（粘贴 + 说明来自 Phase 0 第 8 条）
□ DataTexture 构造行（粘贴，确认 RGBAFormat + UnsignedByteType）
□ buildSkyLUT 中插值方式（粘贴循环体，确认线性采样而非 Catmull-Rom）
□ startSkyTransition / tickSkyTransition 函数存在（粘贴函数签名）
□ tickSkyTransition 在 setAnimationLoop 中的调用位置（粘贴）
□ THEME_VISUAL_CONFIG 时段数量 = 11（粘贴所有 key 列表）
□ resolveInitialPendingTheme() 完整函数体（粘贴，确认含 goldenApproach / lateEvening）
□ 6 个抽查天空锚点色值均正确（粘贴每条 stops 条目）
□ 3 个 goldenApproach 参数抽查点均正确（粘贴）
□ 3 个 lateEvening 参数抽查点均正确（粘贴）
□ applyTheme() 中未修改 toneMappingExposure（粘贴 applyTheme 结尾 10 行）
□ renderer.toneMapping 已设置为 ACESFilmicToneMapping（粘贴）
□ STAR_OPACITY_MAP 完整内容（粘贴）
□ updateStarOpacity 实现方式（粘贴，说明是插值还是直接设置）
□ applyCssFallbackSky 函数实现（粘贴，确认含 OKLab + fallback）
□ index.html #app background = #06080F（粘贴 CSS）
□ index.html 时段按钮含暮前和入夜（粘贴 HTML）
□ dispose() 含 skyMesh 资源释放（粘贴）
□ 未修改以下任何逻辑（逐一确认）：
  loadTextureWithFallback / 城市灯光 emissive / getTargetOrientation /
  quaternionFromBasis / #weather-canvas 相关代码
```

---

**Phase 1 验收标准**

| 类别 | 验收项 | 标准 |
|------|--------|------|
| 架构 | 驱动统一 | #app background 为纯色，天空由 Three.js 驱动 |
| 架构 | 时段数量 | THEME_VISUAL_CONFIG 共 11 个时段 key |
| 架构 | 双 LUT | 时段切换时只上传一次目标 LUT，mixRatio 每帧递增 |
| 视觉 | 正午 | 天顶深钴蓝，不荧光；地平线接近白蓝 |
| 视觉 | 日出 | 可见品红过渡带（玫瑰调）；橙色为低饱和赭石/琥珀 |
| 视觉 | 落日 | 可见品红过渡带（紫调，比日出更宽）；赤陶/琥珀橙 |
| 视觉 | 暮前 | 天顶蓝中带暖，大气壳偏金（#C0A878）；地平线琥珀金黄可见 |
| 视觉 | 夜晚 | 均匀深蓝，蓝色时刻特征明显，无方向感 |
| 视觉 | 入夜 | 比夜晚明显更暗，天顶到地平线仍有明度梯度 |
| 视觉 | 深夜 | 极深靛蓝，趋近均质，星场全亮 |
| 视觉 | 城市灯光 | deepNight（#ffbe63）比 dawn（#ffe0aa）明显更橙，差异可感知 |
| 视觉 | 过渡平滑 | 时段切换时天空颜色平滑过渡，无硬切或闪烁 |
| 联动 | 星场白天 | morning/noon/afternoon/goldenApproach 星场不可见（opacity 0） |
| 联动 | 星场夜晚 | deepNight 1.00，lateEvening 0.72，evening 0.45 |
| 性能 | 帧率 | 不低于改造前的 85%（过渡期间 mixRatio 更新无明显开销） |
| 性能 | 纹理上传 | 切换时段只触发一次纹理上传，不持续每帧上传 |
| 降级 | CSS 兜底 | 强制触发降级时，11 个时段均有 CSS 渐变；OKLab 语法可用时优先使用 |
| 回归 | 不破坏 | 地球纹理、城市灯光、朝向定位、canvas fallback 全部正常 |

---

**Codex 指令 — Phase 1 验收审计**

```
Phase 1 施工已完成。执行验收审计，不修改代码，只输出审计报告。

【检查清单（全部需粘贴代码，不得只说"是"）】

1. THEME_VISUAL_CONFIG 时段 key 完整列表
2. goldenApproach.sky.stops 完整列表
3. lateEvening.sky.stops 完整列表
4. goldenApproach.texture.mapColor / atmosphere.color / lighting.sun 实际值
5. lateEvening.texture.emissiveColor / emissiveIntensity / atmosphere.color 实际值
6. sunrise.sky.stops pos=0.43 的 hex（应为 #622840）
7. sunset.sky.stops pos=0.40 的 hex（应为 #542238）
8. Fragment Shader 完整 main() 函数（重点：t 值计算方式）
9. skyMesh 的 renderOrder / depthWrite / depthTest 实际值
10. Shader uniforms 定义（确认含 skyLUTCurrent / skyLUTNext / mixRatio）
11. DataTexture 构造行（确认 RGBAFormat + UnsignedByteType）
12. buildSkyLUT 中的插值实现（线性采样的循环体）
13. tickSkyTransition 在 setAnimationLoop 中的调用位置
14. STAR_OPACITY_MAP 完整内容
15. applyTheme() 结尾是否有修改 toneMappingExposure 的代码
16. renderer.toneMapping 当前值
17. index.html #app background 当前值
18. index.html 时段按钮完整 HTML（含暮前和入夜）
19. resolveInitialPendingTheme() 完整函数体

【输出】
- 已通过验收项（列出）
- 未通过验收项（列出，说明原因和差异）
- 需要修复的问题清单（按严重程度排序）
- 结论：Phase 1 是否达到验收标准（是/否，不得模糊）
```

---

### Phase 2：OKLab LUT 生成 + Tone Mapping 曝光联动 + 大气边缘光晕激活

**前置条件**：Phase 1 验收通过，运行稳定一个测试周期。

```
执行 Phase 2 施工：OKLab 升级 + Tone Mapping 曝光联动 + 光晕激活。

【任务 1：OKLab LUT 生成升级】
在 buildSkyLUT 中，将颜色插值从 linear RGB 空间升级为 OKLab：
- sRGB → linear RGB → OKLab（使用 OKLab 转换矩阵或引入 oklab 库）
- 在 OKLab 空间线性插值
- OKLab → linear RGB → Uint8Array 写入 DataTexture
OKLab 转换矩阵（手写版本，无需外部库）：
  linear_to_oklab: 先乘 M1（RGB→LMS 立方根空间），再乘 M2（LMS→Lab）
  具体系数参考 https://bottosson.github.io/posts/oklab/

【任务 2：exposure 联动】
在 applyTheme() 中追加：
renderer.toneMappingExposure = config.sky.exposure ?? 1.0
各时段 sky.exposure 值按本文档第八章 8.4 节表格填入。

【任务 3：光晕激活】
将 THEME_VISUAL_CONFIG 中各时段的 sky.glowIntensity 从 0.0
改为本文档第九章的对应值。
在 applyTheme() 中追加：
skyMaterial.uniforms.glowIntensity.value = config.sky.glowIntensity ?? 0.0
skyMaterial.uniforms.glowColor.value.set(config.sky.glowColor ?? '#4878C8')

【自检】
□ buildSkyLUT 中颜色转换经过 OKLab（粘贴转换代码）
□ noon.sky.exposure === 1.20（粘贴）
□ deepNight.sky.exposure === 0.45（粘贴）
□ goldenApproach.sky.glowIntensity === 0.28（粘贴）
□ 视觉确认：日出/落日天空无幽灵青绿色
□ 视觉确认：正午天空与地球色温协调，无过曝
□ 视觉确认：深夜光晕极弱，暗部层次保留
□ Phase 1 所有验收项仍然通过
```

---

### Phase 3：纹理资源审计 + 云层叠加

**分两步执行：**

**步骤 3A：纹理资源审计（不写代码）**
```
执行纹理资源审计，不修改代码。

检查以下资源是否存在并可访问：
1. /assets/cloud_combined_4k.jpg — fetch 验证返回 200？图像尺寸？颜色模式（RGB/灰度）？
2. /assets/cloud_combined_8k.jpg — 同上（可选）
3. 当前已使用的地球纹理文件名和路径（从代码中读取）
4. 是否使用了 KTX2/Basis Universal 压缩格式？

输出：
- 可用资源列表（名称/路径/尺寸/格式/颜色模式）
- 不可用资源列表（说明原因）
- 云层图像是 RGB 合成图还是灰度遮罩？
  （若为 RGB，需预处理为灰度，不能直接用作 alphaMap）
- 云层施工前提条件是否满足（满足/不满足）
```

**步骤 3B：云层施工**（仅在 3A 确认资源可用后执行）

施工要点：独立 mesh，半径 2.04，`depthWrite: false`，独立 quaternion 自转，按时段控制 opacity，LOD 分级，加载失败静默跳过。

---

### Phase 4：纹理资源审计 + 海水高光分离

先执行资源审计确认 `/assets/earth_spec_4k.jpg` 实际存在（文件名和路径以审计结果为准，不得假设），再执行施工。

**施工约束**：保持 `MeshPhongMaterial`，使用 `specularMap`（非 PBR 的 `roughnessMap`）。

---

## 十二、最终验收标准

| 类别 | 验收项 | 标准 |
|------|--------|------|
| 架构 | 驱动统一 | 天空、地球、灯光、星场均由 earth3d.js 统一驱动 |
| 架构 | 时段覆盖 | 11 个时段全部实现，每个有独立视觉特征 |
| 架构 | 双 LUT | 时段切换后纹理上传次数 = 1，非每帧 |
| 架构 | CSS 降级 | WebGL 不可用时，11 个时段均有 CSS 渐变兜底 |
| 视觉 | 正午 | 天顶最深钴蓝，地平线白蓝，不荧光 |
| 视觉 | 日出 | 品红带（玫瑰调），橙色为赭石/琥珀，无幽灵青绿 |
| 视觉 | 落日 | 品红带（紫调，比日出更宽），赤陶/琥珀橙 |
| 视觉 | 暮前 | 天顶蓝偏暖，大气壳偏金（#C0A878），地平线琥珀金黄 |
| 视觉 | 夜晚 | 均匀深蓝，蓝色时刻特征明显，无方向感 |
| 视觉 | 入夜 | 比夜晚明显更暗，天顶到地平线仍有明度梯度 |
| 视觉 | 深夜 | 极深靛蓝，趋近均质，城市灯光主导 |
| 视觉 | 城市灯光 | 深夜橙感最强，黎明最淡，差异可感知 |
| 视觉 | 过渡 | 时段切换平滑，无硬切或闪烁 |
| 视觉 | 大气光晕 | 日出/落日地球边缘带橙调光晕，深夜极弱 |
| 视觉 | 云层 | 可见且缓慢自转，与地球旋转无耦合 |
| 视觉 | 海水 | 正午海洋有镜面高光，陆地无，夜晚高光消失 |
| 联动 | 星场 | 白天不可见；入夜清晰（0.72）；夜晚隐约（0.45）；黎明微弱（0.38） |
| 联动 | 切换同步 | 天空/地球/星场/曝光同步过渡 |
| 性能 | 帧率 | 桌面 60fps，主流移动 ≥30fps |
| 性能 | 显存 | 移动端 ≤128MB，桌面端 ≤512MB（8K 纹理必须 KTX2 压缩） |
| 回归 | 不破坏 | 地球纹理、城市灯光、朝向定位、canvas fallback 全部正常 |

---

*本文档随项目迭代持续更新。Codex 施工指令可直接复制使用。*
