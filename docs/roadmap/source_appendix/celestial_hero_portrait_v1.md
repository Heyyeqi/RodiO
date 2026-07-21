# 天体渲染 v2：修复两个真实 bug + 新增"行星独立 Hero 视角"

> 状态：**方案文档，尚未实现**。承接 `celestial_body_texture_fix_v1.md`（已实现，commit `318e344`）之后的第二轮：一是修那一轮遗留的两个真实 bug，二是新增用户明确提出的新需求——每颗行星一个独立的"主角视角"。
> 工作方式：本文档由 Claude 撰写，**实现工作全部交给 workbuddy**，Claude 只做方案设计和事后独立复核（不直接改代码）。

---

## 第一部分：修复 v1 遗留的两个真实 bug

用户在真机上测试 `318e344` 后反馈两个问题，逐一核实过 diff，确认都是真实 bug，不是主观视觉偏好问题。

### Bug 1：`sunHalo` 在默认近景视角下也会显示（不该出现的地方出现了太阳）

**现象**：用户截图显示，正常播放页面（相机在默认 `homeGlobe` 附近，离地心距离远小于 `SUN_VISIBLE_DIST=50`）里，地球旁边出现了一个明显的白色发光球。

**根因**（已读 `pwa/real-celestial.js` 当前代码确认）：v1 把原来单一的 `sun`（`THREE.Sprite`，光斑）拆成了 `sunHalo`（保留的光晕）+ `sun`（新增的真实贴图核心盘）两个独立对象。`tick()` 里唯一控制可见性的这行代码：

```js
sun.visible = showSun   // 这行只管 sun（真实贴图核心盘），没有任何一行管 sunHalo
```

`sunHalo` 从创建到现在从没有被设置过 `visible = false`，也没有在 `tick()` 里被 `showSun` 门控——`THREE.Sprite` 默认 `visible: true`，所以 `sunHalo` **从页面加载那一刻起就永远可见**，不管相机离地球多近多远。

**修复**：在 `initCelestial()` 创建 `sunHalo` 之后立即加一行 `sunHalo.visible = false`；并在 `tick()` 里跟 `sun.visible = showSun`相邻的地方补一行 `sunHalo.visible = showSun`（现有代码里 `sunHalo.position.copy(sunPos)` 那段 `if (showSun) {...}` 块内就可以顺手加，逻辑上跟 `sun`/`sunHalo` 的缩放语句放一起最自然）。

### Bug 2：非正方形贴图被强制拉伸成正方形，导致行星"歪掉/不完整"

**现象**：用户截图里，土星等行星看起来不是规整的圆形，像没做完的半成品。

**根因**（已用 `PIL` 实测确认尺寸）：`saturn_truecolor.jpg` 是 **1001×1628**（明显的竖长方形，不是正方形），但代码里 `THREE.Sprite` 的缩放逻辑是：

```js
const d = 2 * camToP * Math.tan((P.ang * DEG) / 2)
P.sprite.scale.set(d, d, 1)   // x、y 强制用同一个值 d —— 假设贴图是正方形
```

`Sprite` 会把整张贴图不做任何裁剪地映射到 `scale.x × scale.y` 这个矩形里。贴图本身不是正方形时，图像内容就会被水平或垂直拉伸/挤压，圆形的星球会变成椭圆，或者贴图里的圆盘部分因为不在画面中央而显得"缺了一块"。

**修复**：贴图加载完成后，读取 `texture.image.width`/`texture.image.height`，按贴图原始长宽比设置 `sprite.scale.x`/`sprite.scale.y`（以较长边对齐视觉尺寸 `d`，另一边按比例缩放，保证圆盘本身不被拉伸）。具体做法：

```js
function loadSpriteTexture(sprite, path) {
  new THREE.TextureLoader().load(path, function (tex) {
    if (THREE.sRGBEncoding !== undefined) tex.encoding = THREE.sRGBEncoding
    sprite.material.map = tex
    sprite.material.needsUpdate = true
    // 记录原始长宽比，供 tick() 缩放时使用（长边对齐 d，短边按比例缩小，避免拉伸变形）
    sprite.userData.aspect = tex.image.width / tex.image.height   // >1 = 更宽，<1 = 更高
  }, undefined, function (e) { console.error('[realCelestial] 贴图加载失败:', path, e) })
}
```

然后在 `tick()` 里，凡是 `sprite.scale.set(d, d, 1)` 这种写法，改成：

```js
const aspect = sprite.userData.aspect || 1
const sx = aspect >= 1 ? d : d * aspect
const sy = aspect >= 1 ? d / aspect : d
sprite.scale.set(sx, sy, 1)
```

这个逻辑对太阳（`sun`，`sun_sdo_hmi_luminance.jpg` 是 2048×2048 正方形，aspect=1，行为不变）、8 颗行星、5 颗卫星统一适用，建议抽成一个共用的小函数（比如 `applyAspectScale(sprite, d)`）而不是在每处复制一份计算逻辑。

**验证方式**：改完后，`window.realCelestial.getState()` 目前没有暴露贴图宽高信息，建议加一个调试字段（如 `planets[].texAspect`）方便直接读数字核对，而不是只能靠肉眼截图判断"看起来圆不圆"。

---

## 第二部分：每颗行星独立的 Hero 视角（新需求）

### 背景

用户明确诉求（附参考图：Apple 动态壁纸的火星、土星单独展示效果）：每颗行星除了"跟地球共享一个远景画面里的一个小点"这种现有构图之外，还应该有**至少一个专属的、独立的展示视角**——相机直接对准这颗行星本身，让它填满大部分画面，展示这颗星球自己的美感（表面细节、色彩、光影，土星的话还有环），**不强制要求同框出现地球**。参考图的观感是"真实 3D 球体+光照"级别的精致度，不是"放大的平面照片"。

用户已经确认：**为了达到参考图级别的真实感，这次先做资源调研（找到真正能包裹成球体的等距柱状全球贴图），再做真 3D 球体 + 光照渲染**（而不是先拿现有圆盘照片凑合放大）。

### 为什么现有的 8 张贴图不能直接拿来做 Hero 视角

`celestial_body_texture_fix_v1.md` 已经确认：Step 0 下载的 `mercury_messenger_truecolor.jpg`/`venus_mariner10_truecolor.jpg`/`mars_truecolor.jpg`/`jupiter_pia01369.jpg`/`saturn_truecolor.jpg`/`uranus_pia18182.jpg`/`neptune_pia01492.jpg`/`pluto_pia19708.jpg` 全部是探测器拍的"全圆盘快照"（近正方形或不规则长宽比），**不是**能包住整个球体的等距柱状全球图。这批贴图当"远景小点"合适（第一部分的 Sprite 方案），但拿来做"占满画面的 Hero 视角"会立刻暴露问题：
- 分辨率有限（多数 900–2000px 量级），放大到接近全屏时会明显模糊/糊状。
- 只是一张静态照片，没有"球体+光照"该有的立体感、明暗过渡、环绕感——跟 Apple 参考图那种真 3D 渲染质感有本质差距。
- 依然是 Sprite 恒朝向相机的公告板，不是真实几何体，无法配合任何未来的镜头运动（哪怕只是轻微环绕）。

### Step 0.5（新）：调研并获取真实等距柱状全球贴图（workbuddy 执行）

**目标**：为 8 颗行星各找一张真正的等距柱状投影全球贴图（2:1 长宽比，经度 0–360° 横向展开、纬度 -90°–90° 纵向展开，可以直接无畸变贴到 `THREE.SphereGeometry` 默认 UV 上）——判断标准完全参照月亮已经验证成功的 `moon_lroc_color_2k.jpg`（2048×1024，2:1）。

**候选来源方向（供 workbuddy 调研时参考，不是确定的最终链接，需要 workbuddy 自己核实版权和可用性）**：
1. **Solar System Scope 的免费行星贴图包**——业界（含大量 three.js 太阳系可视化项目）常用的一套 CC BY 4.0 授权等距柱状全球贴图，覆盖水星到冥王星 + 各类环，分辨率有 1k/2k/8k 可选，是这类"风格化但真实"项目最常用的起点，建议优先核实这个来源。
2. **NASA Planetary Photojournal / USGS Astrogeology 行星制图服务**（火星 Viking/MRO 全球镶嵌图、水星 MESSENGER 全球镶嵌图等本身就有官方等距柱状版本，公共领域）——比 Solar System Scope 更"官方"，但需要额外确认每颗星是否都有现成的等距柱状版本（外行星大气层没有固定地表，等距柱状图通常是"云层纹理"而非"地表"，这是气态巨行星的正常情况，不是数据缺失）。
3. 如果某颗行星实在找不到合适的等距柱状真实图（比如冥王星，New Horizons 只飞掠拍到半个球），需要明确记录"用什么代替"（比如仍用现有全圆盘照片做 Sprite，Hero 视角这颗暂缺，或者接受一张分辨率较低但视觉可用的版本），不要为了凑齐 8 颗而用不合适的素材硬凑。

**每颗星除了主表面贴图，如果要匹配参考图的效果，还应该确认**：
- 土星、木星、天王星、海王星：环系统贴图（`celestial_texture_resources.md` §8.2-8.4 已经有环的径向条带贴图，可以复用，不需要重新找）。
- 是否需要法线图/云层图来增加立体感（可选，先用漫反射贴图 + 简单光照跑通，视效果决定要不要加）。

**产出要求**：跟第一次 Step 0 一样的规格——每个文件下载到 `pwa/assets/textures/planets_equirect/`（新目录，跟现有"全圆盘照片"的 `planets/` 目录区分开，避免两种不同用途的贴图混在一起造成后续维护混乱），写一份跟 `celestial_texture_resources.md` 同规格的资源报告（来源、分辨率、版权、每个文件是不是真的等距柱状 2:1——用 `PIL` 读取实际尺寸核实，不能只看文件名）。

### Step 1（新）：真 3D 球体 + 光照渲染 + 独立 Hero 相机构图

在 Step 0.5 资源到位后：

1. **渲染**：每颗行星用 `THREE.SphereGeometry` + 等距柱状贴图（做法完全参照月亮 `moonGeo`/`moonMat`/`BODY_VERT`/`BODY_FRAG` 那一套已经验证成功的 shader——贴图 × terminator 明暗过渡，`uAmbient` 按"这颗星在 Hero 视角下应该呈现多少暗部细节"来调，不需要每颗都跟月亮一模一样）。气态巨行星（木星/土星/天王星/海王星）如果贴图带环，额外加一个 `THREE.RingGeometry` + 环贴图（复用已下载的环贴图资源）。
2. **新增 Hero 相机构图**：每颗行星一个独立构图（例如 `marsHero`/`saturnHero`/`jupiterHero`…），相机直接对准该行星在其真实轨道位置上的当前坐标（复用已有的 `planetGeoDir()` 计算），行星在画面里占比大（比如占屏幕高度 50-70%），不要求地球在同一帧出现——这跟现有的 `venusView`/`marsView`等"以地球为锚点，行星只是配角"的构图是两套不同的相机逻辑，需要新的构图计算方式（可能要新增一个"相机看向任意天体"的通用函数，而不是复用现有"相机看向地球，天体只是画面里的一个点"的框架）。
3. **明暗光照**：`uSunDir` 復用第一部分已有的"行星→太阳方向"计算方式，这部分逻辑不用重新发明。
4. Theme Tuner 调试面板加对应按钮，方式跟现有 `gramCompositions` 数组一致。

### 明确排除/延后的范围

- 这次不要求所有 8 颗行星的 Hero 视角一次性做完——**建议先跑通 1-2 颗（比如土星带环、火星表面细节最明显，参考图也正好是这两颗）验证整套技术路线（等距柱状贴图源+真3D球体+光照+独立相机构图）站得住，再批量复制到剩余行星**，避免一次性踩坑范围太大。
- 卫星（Io/Europa/Ganymede/Callisto/Titan）暂不做 Hero 视角，优先级低于 8 大行星。
- 行星自转、真实轨道镜头运动（比如慢慢环绕行星）不在本次范围，先出静态构图。

---

## 验收标准（比第一部分更主观，需要用户肉眼判断）

1. 数值/结构性验证（跟第一部分一样）：贴图路径可访问、`node --check` 语法通过、默认路径零回归。
2. **主观验收（这次的重点）**：截图 Hero 视角下的行星，跟用户提供的参考图（Apple 火星/土星动态壁纸）做直接对比，判断"真实的球体质感、光影层次"这个主观标准是否达标——这是本次任务能不能算完成的最终标准，不是任何数值断言可以代替的。
