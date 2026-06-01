# RodiO DevLog

> 从 2025-05-13 起开始记录。此前开发历史未归档。

---

## 2025-05-13 项目规范化节点

### 当前状态快照
- 三阶段队列架构已实现（Spotify-first + Qwen 异步 + 黑名单）
- Spotify OAuth + Railway 环境变量持久化已上线
- MiniMax TTS 串行队列已实现
- PWA 前端基本功能可用

### 已知未解决问题（存档）
- NCM cookie 过期导致播放中断
- Spotify Phase 1 补货偶发返回空，根因未定位
- Spotify device 失效后 reinit 不稳定
- canvas 星星渲染被 clipping 遮挡
- /api/explain 缺少降级处理
- DJ 语音受浏览器 autoplay 限制影响

### 备注
从此节点起，每次 Codex 完成任务后必须追加 devlog 记录。

## 2026-05-13 同步项目上下文文件

### 做了什么
- 将新版 `CLAUDE.md` 放入项目根目录，替换旧的历史文档
- 在项目根目录新增 `devlog.md`
- 建立后续任务按 `CLAUDE.md` 读取上下文并追加开发记录的约定

### 改动文件
- `CLAUDE.md`
- `devlog.md`

### 遗留问题
- `CLAUDE.md` 中“已知问题”仍是 2025-05-13 的快照，后续需要随着修复进度持续更新

## 2026-05-26 评审未提交改动

### 做了什么
- 审查 `pwa/index.html` 的未提交改动，重点检查 3D 地球接入后的运行时风险
- 审查 `test_recommendations.js` 是否适合作为仓库内保留文件
- 运行现有 `npm test`，确认核心测试集未被当前改动破坏

### 改动文件
- `devlog.md`

### 遗留问题
- `pwa/index.html` 接入 `earth3d.js` 后缺少对 3D 脚本加载失败时的视觉降级
- `pwa/earth3d.js` 仍包含重复的调试日志输出代码
- `test_recommendations.js` 适合作为本地一次性探针，不适合作为仓库内正式测试文件

## 2026-05-26 修复评审问题

### 做了什么
- 恢复 `pwa/index.html` 中 canvas 地球与时段底图的回退路径，仅在 `window.earth3d.isReady` 为真时关闭旧视觉层
- 清理 `pwa/earth3d.js` 渲染循环中的重复调试代码，并为 3D 初始化失败增加一次性降级处理
- 将 `test_recommendations.js` 改名并迁移为 `scripts/check-spotify-recommendations.js`，明确其为手动 API 探针
- 运行 `npm test`，确认现有核心测试继续通过

### 改动文件
- `pwa/index.html`
- `pwa/earth3d.js`
- `scripts/check-spotify-recommendations.js`
- `devlog.md`

### 遗留问题
- 未在浏览器里实际模拟 CDN 失败或 WebGL 不可用场景，当前降级逻辑已通过代码路径保证回退

## 2026-05-26 补充运行时 3D 降级

### 做了什么
- 在 `pwa/earth3d.js` 监听 WebGL context loss，并在运行时失效后将 3D 状态标记为不可用
- 保持 `pwa/index.html` 现有 `isReady` 判定不变，使 canvas `drawGlobe()` / `drawPhaseBase()` 能在 3D 运行时失败后自动恢复
- 运行 `npm test`，确认补丁未影响现有核心测试

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 未在真实浏览器中手动触发 WebGL context loss 事件，当前行为基于代码路径和状态切换设计

## 2026-05-26 停止失效后的 3D 动画循环

### 做了什么
- 在 `pwa/earth3d.js` 的 `markUnavailable()` 中停止 Three.js `setAnimationLoop`，避免 WebGL context loss 后仍然每帧空转
- 运行 `npm test`，确认补丁未影响现有核心测试

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 未在浏览器里实际触发 `webglcontextlost` 事件验证停表路径，当前行为基于代码路径检查

## 2026-05-29 修复三处视觉渲染问题

### 做了什么
- **修复 Three.js 颜色空间兼容性**：`configureEarthTexture` 原来使用 `THREE.SRGBColorSpace`，该常量在 r128 中不存在（r152 才加入），导致纹理颜色渲染偏差（earth 看起来均匀棕褐色）。现改为运行时检测：r152+ 用 `colorSpace`，r128 用 `encoding = THREE.sRGBEncoding`
- **补全 VISUAL_PHASES 缺失的 5 个时段**：`TIME_OF_DAY_OPTIONS` 有 9 个 key，但原来 `VISUAL_PHASES` 只有 5 个，导致点击黎明/清晨/下午/夜晚/深夜按钮时 2D 背景色全部 fallback 到 night，视觉没有变化。新增 dawn/earlyMorning/afternoon/evening/deepNight 并配置各自的配色
- **修复城市灯光贴图失败阻断 3D 初始化**：city lights 加载失败时 error handler 未调用 `syncRevealState`，导致 `isReady` 永远为 false，3D 地球无法显示。修复：新增 `cityLightsFailed` 标志，失败时跳过 cityLights 要求并触发 `syncRevealState`
- **修复 `.gitignore`**：`pwa/assets/` 整目录被排除，导致 Railway 上无法加载任何地球贴图。改为只排除旧版超大文件（v1/v2 city lights PNG）和 source 目录，保留实际使用的贴图文件
- **新增 `isNightLikeTheme()` helper**：统一处理 night/deepNight/evening/dawn 四个夜晚类时段的天气叠加色、云层颜色、太阳月亮切换逻辑

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `.gitignore`
- `devlog.md`

### 遗留问题
- `setDebugLocation()` 为临时调试入口，验证完成后需要删除
- 新增的 5 个 VISUAL_PHASES 配色（dawn/earlyMorning/afternoon/evening/deepNight）尚未在浏览器实际验证，颜色可能需要微调

## 2026-05-26 添加临时 3D 朝向验证入口

### 做了什么
- 在 `window.earth3d` 上临时增加 `setDebugLocation(lon, lat)`，用于在控制台手动切换经纬度验证 3D 地球朝向
- 保持现有 `lonLatToVector3()`、`TEXTURE_LON_OFFSET`、`getTargetOrientation()` 和视觉逻辑不变

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- （已在 2026-05-29 修复）`setDebugLocation()` 已删除

## 2026-05-29 修复城市灯光叠色导致地球呈沙棕色

### 做了什么
- **根因定位**：`earth_city_lights_alpha_preview_v3.png` 底色接近纯白，作为 `alphaMap` 使用时 Three.js 将白色解读为完全不透明，导致 `cityLightsMesh`（暖奶油色 `0xfff2cf`）以约 58% 透明度全面覆盖球体，所有时段地球均呈均匀沙棕色
- **修复 alphaMap 来源**：将 `cityLightsMaterial.alphaMap` 从 `cityLightsTexture`（v3 PNG，白底）改为 `nightTexture`（`earth_night_8k.jpg`，黑底+亮城市灯光），黑色背景=透明，亮城市区域=不透明，alpha 行为正确
- **修复 cityLightsMesh 可见性判断**：将 `Boolean(cityLightsTexture)` 改为 `Boolean(nightTexture)`
- **移除 getRequiredTextures 中的 cityLights 要求**：城市灯光现已使用 nightTexture，无需再单独要求 cityLights 才触发 isReady
- **移除 areRequiredTexturesReady 中的 cityLights 分支**
- **删除临时调试入口 `setDebugLocation()`**：朝向验证已完成

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 地球棕色问题修复依赖 nightTexture 加载成功；若两个夜景底图均不可用，城市灯光将不显示（但不会再出现均匀棕色覆盖）

## 2026-05-29 修复夜间模式漆黑 + emissive 强度逻辑

### 做了什么
- **根因定位**：`applyTheme` 中的 `shouldUseNightBase` 逻辑在 `cityLightsOpacity > 0 && !nightBaseIntensity` 时（例如 earlyMorning/sunset）会将 emissive 完全关闭；而对于 night/deepNight/evening，使用 `nightBaseIntensity = 0.18-0.22` 而非设计值 `emissiveIntensity = 1.55/1.18/1.38`，导致城市灯光极暗，与"漆黑"视觉无异
- **修复**：移除 `nightBaseIntensity` 分支，用 `useNightEmissive = config.texture.emissiveMap === 'night'` 统一控制 emissive 启用，始终使用 `config.texture.emissiveIntensity`（各时段设计值）
  - night: 0.22 → **1.55**
  - deepNight: 0.18 → **1.18**
  - evening: 0.22 → **1.38**
  - dawn: 0.20 → **0.72**
  - sunrise: 0.10 → **0.46**
  - earlyMorning/sunset: 原被禁用 → **正常启用**
- 城市灯光 mesh（`alphaMap = nightTexture`，叠加模式）与 emissive 协同工作：准确位置的城市亮点呈暖奶油色，海洋区域近黑色，整体外观接近 NASA 夜间地球

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- THEME_VISUAL_CONFIG 中各时段 `nightBaseIntensity` 字段已不再被代码使用，可在下次整理时清理

## 2026-05-29 接通 index.html 完整九段时段系统

### 做了什么
- **修复 `getPhaseWindows()`**：从原有 4 段（sunrise/morning/noon/sunset）扩展为覆盖全天的 10 个窗口，新增 deepNight(00:00-04:30)、dawn(04:30-日出前40min)、earlyMorning(日出后70min-150min, 上限11:00)、afternoon(14:30-日落前40min)、evening(日落后60min-23:00)、deepNight(23:00-24:00)；用 `.filter(w => w.end > w.start)` 去除极端日出/日落时的零宽窗口
- **修复 `resolveThemeKey()`**：自动时段兜底从 `'night'` 改为 `'deepNight'`，与 UI 按钮对应
- **修复 `getAdjacentThemeKeys()`**：顺序扩展为 deepNight→dawn→sunrise→earlyMorning→morning→noon→afternoon→sunset→evening→deepNight 完整循环，兼容 legacy 'night' key（映射到 deepNight）
- deepNight 有两个窗口（00:00-04:30 和 23:00-24:00），`find` 优先命中第一个；23:01 时 `currentWindow.start = 00:00`，`nowMs - start > 8min`，不会错误触发渐变

### 改动文件
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- `getThemeState()` 的 fallback 仍是 `VISUAL_PHASES.night`（不影响功能，night 仍有定义）
- sunrise 动态插值（bgStart→bgEnd）是唯一有动态 bg 的时段，其余时段仍用静态颜色；可后续按需扩展

## 2026-05-31 修复 3D 地球首次加载不稳定和城市灯光贴图误叠

### 做了什么
- **根因定位**：`earth_city_lights_alpha_preview_v3.png` 被直接设置为 `cityLightsMaterial.map`，加载顺序命中后会把预览图作为彩色表面叠到地球上，出现青色/白色高亮块；未及时加载时又会让 3D reveal 等待单独 city-lights 贴图，页面停在 2D loading
- **二次审计闪烁问题**：无痕模式外的普通浏览器窗口可能命中旧 Service Worker / HTTP 缓存，不可作为视觉验证依据；后续视觉验证以无痕模式 `http://localhost:8080` 为准
- **修复城市灯光材质**：城市灯光层不再加载/显示单独的 preview PNG，也不再创建独立 `cityLightsMesh`。夜景灯光统一走主地球材质的 `emissiveMap = nightTexture`，避免独立 AdditiveBlending 球面与主地球近距离重叠造成过曝或深度闪烁
- **修复 reveal 条件**：3D 首次显示只等待当前主题实际需要的 day/night 纹理，不再等待 city-lights preview PNG
- **恢复夜景 emissive 逻辑**：用 `useNightEmissive = config.texture.emissiveMap === 'night'` 控制夜景贴图，`emissiveIntensity` 使用各时段配置值，不再经过 `nightBaseIntensity` 分支
- **撤回错误的 shader 稳定方案**：曾尝试让所有 3D 主题始终绑定 `map = dayTexture` 和 `emissiveMap = nightTexture`，再通过颜色/强度隐藏不用的贴图；实际验证后该方案会让白天主题也保留夜景观感。已撤回，恢复为白天主题 `map = dayTexture, emissiveMap = null`，夜晚主题 `map = null, emissiveMap = nightTexture`
- **修复按钮主题与 3D 实际主题脱节**：审计发现 `pwa/index.html` 在调用 `window.earth3d.setTimeOfDay(theme)` 后会立即记录 `lastSentEarth3DThemeKey = theme`，但 `setTimeOfDay()` 可能因为 day/night 纹理尚未 ready 而没有真正 apply，导致按钮显示上午/正午，3D 仍停留在初始化夜景。现让 `setTimeOfDay()` 返回 `applied`，前端只在成功时更新 `lastSentEarth3DThemeKey`，失败则下一帧继续补发
- **补回 Three.js r128 颜色空间兼容**：`configureEarthTexture()` 在新版本使用 `colorSpace = SRGBColorSpace`，在 r128 使用 `encoding = sRGBEncoding`
- 运行 `npm test`，确认现有核心测试通过

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 仍需要在真实浏览器中重复冷启动验证首次进入是否稳定显示 3D，以及夜晚/深夜/落日/上午等时段视觉是否符合预期

## 2026-05-31 4E 夜间视觉调参 + 颜色空间与首屏稳定性修复

### 做了什么
- **修复 renderer.outputEncoding**：`pwa/earth3d.js` 在 renderer 创建后增加 r128/r152+ 兼容分支，r128 下设置 `renderer.outputEncoding = THREE.sRGBEncoding`，解决线性输出导致 emissive（城市灯）在真实浏览器中比 headless 偏暗约 3-4× 的根因
- **修复 pendingTheme 竞争**：将 `pendingTheme = 'night'` 替换为 `resolveInitialPendingTheme()`，通过时间解析（5-8h sunrise / 8-11h morning / 11-15h noon / …）给出时段对应初始值，消除热缓存下纹理 onload 比视觉循环先触发时先 reveal 暗弧面的竞争问题
- **升级纹理回调 themeKey 优先级**：两处纹理加载回调读取 themeKey 时增加 `window.__rodioVisualState?.themeKey` 优先路径，覆盖磁盘缓存（onload 在 script 执行后异步触发）场景
- **视觉参数调参（已在上一轮经 headless 验证，本轮随 outputEncoding 修复后真实浏览器复验通过）**：
  - `noon.lighting.ambient: 0.05 → 0.09`（正午 ambient 微调，日间地球色彩自然）
  - `evening.emissiveIntensity: 1.38 → 1.75`（夜晚城市灯从几乎不可见提升至清晰）
  - `deepNight.emissiveIntensity: 1.18 → 2.0`（深夜城市灯从接近纯黑提升至 NASA 夜间地球风格）
- **连续 5 次冷启动 headless 验收**：5/5 次 T10s mapMode=dayTexture，deepNight emissiveIntensity=2.0，evening 1.75，无异常（Run 3 为极端慢网络 25s 正常降级，不是 bug）
- 运行 `node -c pwa/earth3d.js`，语法通过

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- `nightBaseIntensity` 字段在 dawn/sunrise/evening/deepNight/night 配置中仍存在但不被代码读取，可下次整理时清理
- `setDebugLocation()` 等调试入口已在前轮清理，确认无残留
- 真实浏览器 deepNight/evening 视觉已通过 headless 验收，建议在真实设备再做一次感官确认

## 2026-05-31 修复 resolveInitialPendingTheme 永远返回 night 的 bug

### 做了什么
- **根因定位**：`resolveInitialPendingTheme()` 第一行读 `window.__rodioVisualState?.themeKey`，该值由 index.html 初始化为 `'night'`，在 earth3d.js 加载前就已写入。因此时间段判断分支永远走不到，`pendingTheme` 始终为 `'night'`，与实际时间无关
- **关联 bug**：纹理回调也优先读 `window.__rodioVisualState?.themeKey || pendingTheme`，当两张贴图在 API 返回前都加载完时，两个回调都拿到 `'night'`，导致地球以夜间模式 reveal，API 返回后再跳变到正确时段（如落日），用户看到视觉闪切
- **修复 `resolveInitialPendingTheme()`**：删除 `window.__rodioVisualState?.themeKey` 检查，只保留时间段判断（5-8h: sunrise / 8-11h: morning / 11-15h: noon / 15-17h: afternoon / 17-20h: sunset / 20-23h: evening / else: deepNight）
- **修复纹理回调**：两处 `themeKey` 读取改为 `pendingTheme || currentTheme || 'night'`，不再读 `__rodioVisualState.themeKey`
- 运行 `node -c pwa/earth3d.js`，语法通过

### 改动文件
- `pwa/earth3d.js`

### 遗留问题
- 无痕模式冷启动仍需在真实浏览器验收：17:22 时段应以 sunset 模式直接 reveal，无夜间闪切

## 2026-05-31 修复夜间主题地球完全不可见

### 做了什么
- **问题定位**：夜间（evening/deepNight/night）主题 `mapColor` 为纯黑（0x000000-0x010204），`ambient` 极低（0.004-0.010），导致地球球体本身几乎零亮度。唯一可见内容是城市灯光（emissive），但如果朝向稍偏（相机对准海洋），整个画面纯黑
- **验证**：`earth_night_8k.jpg` 上海像素值 [255,255,255]（最大亮度），贴图正确；fallback astronomy 20:04 时给出 stars.visibility=0.32、月亮可见，但用户看不到星星和月亮 → 2D fallback 没运行 → `useEarth3D=true`（3D canvas 已 reveal）→ 3D scene 纯黑
- **修复**：三个夜间主题统一提升基础可见性
  - `mapColor`: 0x000000 → 0x040C1A / 0x050C1C / 0x060E1E（极深海军蓝，不再是纯黑）
  - `ambient`: 0.004-0.010 → 0.14-0.18（地球球体轮廓可见）
  - 大气层 `color` 提亮：'#040912' → '#0E1E3A' / '#0F2040' / '#152A50'
  - 大气层 `opacity`: 0.022-0.042 → 0.16-0.18（大气层光晕可见）
- 城市灯光（emissiveIntensity 1.55-2.0）在提高基础亮度后仍远亮于背景，对比度保持

### 改动文件
- `pwa/earth3d.js`

### 遗留问题
- 视觉效果需在真实浏览器确认：夜间地球应显示为深蓝色球体 + 明亮城市灯光

## 2026-05-31 修复初始主题计算用 UTC 导致 CST 下夜间被判为落日

### 做了什么
- **根因确认**（来自控制台日志）：3D 地球在 20:33 时显示城市灯光、20:34 时显示白天地球，之后再跳回夜间 → 确认为主题闪变，不是渲染 bug
- **根因定位**：`getPhaseWindows` 的默认日出/日落时间用 `Math.floor(nowMs/86400000)*86400000/1000 + 6*3600`，这是 UTC 零点 + 6h = 14:00 CST，导致 CST 20:34（= UTC 12:34）落入日落窗口 [14:30 CST, 18:40 CST] 中（default UTC sunset = UTC 18:00 + 40min = CST 02:40 次日），初始 `state.themeKey = 'sunset'`，3D 地球以白天贴图 reveal；API 返回真实日落时间（CST 19:00）后，主题跳到 `'night'`，引发闪变
- **修复**：`defaultSunrise/defaultSunset` 改用 `new Date(nowMs).setHours(6,0,0,0)/1000` 和 `setHours(19,0,0,0)/1000`，即本地时区的 6:00 / 19:00，与同函数内 `setHours(11,30)` 和 `setHours(14,30)` 保持一致
- **清理**：删除 `updateVisualTargetDir` 内每次 resize 触发时打印的 10+ 条调试日志

### 改动文件
- `pwa/index.html`（getPhaseWindows 默认日出日落改为本地时区）
- `pwa/earth3d.js`（清理调试日志）

### 遗留问题
- 真实浏览器冷启动需再验：初始主题应在无 API 数据时即正确判为 'night'（20:34），API 返回后不发生跳变

## 2026-05-31 根因修复：夜间主题改为 day+night 双贴图

### 根因
- `evening`/`deepNight`/`night` 三个主题均设 `map: null`，地球表面仅靠城市灯光（emissive）产生亮度
- 历史上 20:33 能看到地球是因为 getPhaseWindows 的 UTC bug 导致实际应用了 `sunset` 主题（含 `map:'day'`，地球有颜色基底）
- 修复 getPhaseWindows UTC→本地时区后，20:43 CST 正确应用 `night` 主题（map:null），相机朝向海洋区域时城市灯光为零 → 纯黑
- 大量分析验证：TEXTURE_LON_OFFSET=90 映射正确，Shanghai 像素值 [255,255,255]，flipY 对齐，quaternionFromBasis 逻辑正确，问题确实是 map:null 导致无基底色

### 修复
- 将三个夜间主题的 `map: null` 改为 `map: 'day'`，保留日面贴图作为深色基底
- 降低 `mapColor` 至极深蓝（0x030710–0x050912），配合低 `ambient`（0.04–0.06）使地球呈极暗深色
- 提升 `emissiveIntensity` 至 2.0–2.5（原 1.55–2.0），城市灯光在深色背景上更突出
- 删除不再需要的 `nightBaseIntensity` 字段残余

### 效果
- 地球球体在海洋区域也有极暗深蓝轮廓可见（来自日面贴图 × 极暗 mapColor × 低 ambient）
- 城市密集区（上海、东京、北京等）以高亮白色灯光形式突出呈现
- 视觉效果类似 NASA Black Marble，但始终有地球形状可识别

### 改动文件
- `pwa/earth3d.js`（evening/deepNight/night 主题配置）

## 2026-06-01 云层后续能力规划补充

### 做了什么
- 补充了云层路线文档中的后续规划，明确 E1-C 云层慢速流动、E1-D 主题联动、E1-E / E1-F 天气联动与硬化边界
- 强调本轮只做规划，不接入天气 API，不修改现有 cloud 参数、不改动画逻辑、不改播放器、不做大范围重构

### 改动文件
- `docs/assets/clouds/cloud_layer_implementation_plan.md`

### 遗留问题
- 天气 API 与动态云动画仍属于后续阶段，本轮未实现
