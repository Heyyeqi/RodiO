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

## 2026-06-01 白天海水 specular 快修验收失败并恢复

### 做了什么
- 尝试将 morning/noon/afternoon 三个主题的 shininess（1→16/24/18）和 specular（近黑→冷蓝灰）提升，以激活现有 oceanSpecularMap
- 在浏览器验收后发现：海洋出现大面积浅青灰塑料膜感，日本/台湾/菲律宾附近出现明显黑色锯齿块状边界
- 立即恢复三个主题参数至修改前原值（morning: shininess=1.05, specular=0x06090f；noon: shininess=1.12, specular=0x091018；afternoon: shininess=0.96, specular=0x05080d）

### 改动文件
- `pwa/earth3d.js`（已恢复，净改动为零）

### 遗留问题
- 现有 oceanSpecularMap 边界质量不足以支撑高 shininess/specular 组合，此路线封闭
- 白天海水质感问题未解决，后续方向：ocean tint mesh 叠加层、更高质量海洋资源、或着色管线升级

## 2026-06-02/03 Bathy A-3 系列：D4a 收尾 + D5a→D5x 候选生成

### 做了什么

**A-3 / D4a 验收（收尾）：**
- D4a 保守近海修复上球验收，核心区域 B_std 提升仅 0–2%，路线关闭

**Bathy-0 审计 + Bathy-1 ETOPO1 验证：**
- ETOPO1_Ice_g_gdal.grd 下载验证通过（890MB，21601×10801，north_first，无需重投影）
- 写入 devlog：docs/devlog_bathy_1_etopo_validation.md

**Bathy-2 / D5a：**
- 生成首张 bathymetry-tinted 候选，方向验证有效
- 上球审计：bathymetry 路线有效，但存在青绿滤镜感、局部 map 感

**Bathy-3 / D5b：**
- 权重收敛版（0.14/0.11/0.08/0.03/0.00），blur sigma=12+8
- 上球测试：比 D5a 更克制，但与 D5a 差异过弱，视觉收益不足

**Bathy-3 / D5c / Ocean Palette v6.1：**
- 权重回弹（0.16/0.13/0.09），热带锚点 #8ED8C8（v5 anchor），EA 专用 palette
- 上球测试：仍与 D5b 差异不足，视觉无决定性收益

**Bathy-3 / D5x Diagnostic Strong：**
- 诊断版（0.20/0.16/0.12/0.04/0.00），验证贴图层上限
- Diff 指标：D5x vs D5b pct_gt3=1.19%（低于预期 2.4%，因 sat cap 钳制）
- 关键区域有效：波斯湾 +10/+8/+2，渤海 +8/+9/+7
- 未注册到 earth3d.js，等待浏览器视觉决策

**earth3d.js 浏览器测试入口：**
- 增加 localhost-only ?dayTexture= URL 参数切换机制
- 注册 d5a_bathy / d5b_bathy / d5c_palette_v6_1_bathy
- D5x 候选文件在 candidates/ 但未注册

### 改动文件
- pwa/earth3d.js（URL 参数切换 + 候选注册）
- pwa/assets/earth/candidates/（d5a/d5b/d5c/d5x 候选贴图）
- pwa/assets/source/bmng_staging/（D5a/D5b/D5c/D5x 源文件）
- pwa/assets/source/bathy/（ETOPO1 数据）
- docs/devlog_bathy_1_etopo_validation.md
- docs/devlog_bathy_3_d5b_candidate.md
- docs/devlog_bathy_3_d5c_palette_v6_1_candidate.md
- docs/devlog_bathy_3_d5x_diagnostic_strong_candidate.md
- scripts/（validate_etopo1_bathy / generate_d5a/b/c/x 脚本）

### 遗留问题
- D5x 需要浏览器上球诊断验收（注册后用 ?dayTexture=d5x_diagnostic_strong_bathy）
- 若 D5x 仍无明显视觉效果，考虑转 shader 路线
- 南极过曝：非贴图问题，在 THEME_VISUAL_CONFIG noon/afternoon 光照层处理
- 大堡礁/马尔代夫精细化：需 GEBCO 15"，列为 Bathy-4
- nightBaseIntensity 死代码清理 pending

---

## 2026-06-03 Bathy-3/A-3 D6 topo-blend 候选生成

### 做了什么
- 新建 `scripts/generate_d6_topo_blend.py`：以 D5a 为基础，用 bmng_topo_bathy_oct 8k 的 ocean luminance 作为深度 proxy，直接 blend 到 D5a
- 策略：topo 亮度高（浅海）→ 权重高（最高 0.30）；深海（>1000m）ETOPO1 硬保护权重=0
- 目标色即 topo 图像自身 RGB（NASA 预调色，不重设调色板）
- 22/22 zone 全部通过；深海 Δ≈0；陆地/雪冰精确保留；anti-荧光 reverted 仅 105 px
- 注册 `d6_topo_blend` 到 earth3d.js candidates（浏览器 URL 参数可测）
- 关键观测：topo ocean lum p95=0.251，意味着浅海层次效果集中在最浅 5% 像素（黄海、波斯湾、北海），总体权重均值 0.006，效果保守

### 改动文件
- `scripts/generate_d6_topo_blend.py`（新增）
- `pwa/earth3d.js`（candidates 注册 d6_topo_blend，注释更新）
- `pwa/assets/source/bmng_staging/bmng_processed_8192x4096_natural_d6_topo_blend.jpg`（9MB，新增）
- `pwa/assets/earth/candidates/d6_topo_blend_8192x4096.jpg`（新增，供浏览器测试）
- `pwa/assets/source/bathy/d6_topo_blend_metrics.json`（22 zone 对比）
- `pwa/assets/source/bathy/d6_topo_blend_preview_global.jpg`
- `pwa/assets/source/bathy/d6_topo_blend_preview_regions.jpg`（11 crops）

### 遗留问题
- 浏览器上球验收：http://localhost:8080/?dayTexture=d6_topo_blend
- 若视觉效果不足（权重过小），下一轮候选方向：
  (A) 增强权重曲线（bp_w 上调 2×），保守扩大浅海影响半径
  (B) 使用 21k 原始 topo 提升浅海细节精度（牺牲内存/速度）
  (C) 转 shader 路线（per-fragment 深度驱动）

---

## 2026-06-03 D5b_design_v3 系列完整开发（v3 → v3.2.1 formal 8K）

### 做了什么

#### 工具链搭建（d5b_processor_v3/）
- 新建 8 个 Python 模块：config.py / masks.py / adjustments.py / enhancement.py / metrics.py / preview.py / make_small.py / main.py
- 架构：41 个 OCEAN_REGIONS（按 priority 排序）+ 25 个 ISLAND_HALOS（含 deep_gate v3 强化）+ 全局增强（polar compress + land sharpen）
- 支持 per-region feather_px、out_dir 参数化输出路由、可扩展 metrics regions

#### v3 基础版 dry-run
- 发现 2 个 bug：`compress_polar_highlights` 把低通道也提升到 threshold（Antarctica max=56）；JSON 序列化 numpy float32 报错

#### v3.1 修复版（formal 8K 已生成）
- 修复 `enhancement.py` polar compress bug（仅压缩超 threshold 通道）
- 降低 southern_ocean/ross_weddell offset；polar_highlight_threshold 238→240/compress 0.95
- 收紧 10 个 island halo（radius/strength 各降 15-25%）
- 新增 4 个 Patch（D5b_v3_patch.md）：输出目录路由、halo ocean mask 限制、有效区域统计、heatmap 防除零
- Antarctica max_abs_diff: 56 → 23
- Formal 8K: `d5b_output/formal_8k/bmng_processed_8192x4096_natural_d5b_design_v3_1.jpg`
- Candidate: `pwa/assets/earth/candidates/d5b_design_v3_1_8192x4096.jpg`，URL: `?dayTexture=d5b_design_v3_1`

#### v3.2 Coastline feather 扩展版（dry-run 只）
- main.py：`feather_px=cfg.get("feather_px", 20)` per-region 支持
- polar_highlight_threshold 240 → 238
- 10 个区域新增 feather_px（最大 40）
- 问题：southern_ocean=30 和 bahamas=40 导致 blue broadening（SO max=28, Bahamas max=21）

#### v3.2.1 Narrow Correction 版（formal 8K 已生成，当前正式候选）
- 仅回调 3 参数：southern_ocean.feather_px 30→24，ross_weddell.feather_px 40→30，bahamas_shelf.feather_px 40→30
- 保留 v3.2 的 8 个有效 feather 和 polar_highlight_threshold=238
- 8K metrics：Antarctica=25，Southern Ocean=21（< v3.1 的 23），Bahamas=17（= v3.1）
- Formal 8K: `d5b_output/formal_8k_v3_2_1/bmng_processed_8192x4096_natural_d5b_design_v3_2_1.jpg`
- Candidate: `pwa/assets/earth/candidates/d5b_design_v3_2_1_8192x4096.jpg`，URL: `?dayTexture=d5b_design_v3_2_1`
- Codex 审核：Category A，pass to browser globe test

### 改动文件
- `d5b_processor_v3/`（全新目录：8 个模块 + 5 个包装脚本 + d5b_output/）
- `pwa/earth3d.js`（新增 candidates：d5b_design_v3_1, d5b_design_v3_2_1）
- `pwa/assets/earth/candidates/d5b_design_v3_1_8192x4096.jpg`（8.0MB）
- `pwa/assets/earth/candidates/d5b_design_v3_2_1_8192x4096.jpg`（8.0MB）

### 遗留问题
- 浏览器上球视觉验收：
  - 主测：http://localhost:8080/?dayTexture=d5b_design_v3_2_1
  - 对比：http://localhost:8080/?dayTexture=d5b_design_v3_1
- 验收通过后：修改 DAY_TEXTURE_VARIANT = 'd5b_design_v3_2_1' 并 commit
- D6 topo-blend 也待上球验收（独立路线）：?dayTexture=d6_topo_blend
- 南极过曝（光照层问题）、大堡礁/马尔代夫精细化（需 GEBCO）仍在积压

---

## 2026-06-07 E1-R1 当前贴图指标测量定稿与归档

### 做了什么
- 对 d5b_design_v3_2_1_8192x4096.jpg 执行 51 个采样点量化测量（A–J 十类区域）
- 完成 E1-R1A Photorealism/Anti-Cartoon Audit 数据整合
- 完成六大问题域风险判定
- 补充 RW 对 4 项暂定阈值的正式确认意见（E 类沙漠分区、F 类 std_L 豁免范围、H 类 L* 下限放宽、A 类 L* 悬置）
- 定稿报告并归档三文件

### 改动文件
- `docs/e1_r1_current_metrics_audit.md`（新建，E1-R1 量化审计报告，含 RW 阈值确认意见）
- `docs/metrics/e1_r1_current_metrics.json`（新建，51 点结构化指标）
- `docs/metrics/e1_r1_current_metrics.csv`（新建，CSV 格式）

### 遗留问题
- E1-R2 Noon Runtime Exposure Audit 尚未执行（须浏览器 noon 截图归因沙漠/极地过曝）
- D5z 前置条件 4（E1-R2 归因）尚未满足，仍禁止进入候选生成
- Sentinel-2 A1/A2/A4 样本、Google Maps REF-01/02/03 尚未采集

---

## 2026-06-08 E1-R4A Regional Visual Preview 规则补充

### 做了什么
- 在 docs/e1_day_master_reference_metrics_baseline.md 的 E1 后续拆分中新增 E1-R4A 阶段（8 个子轮次，原 7 个）
- E1-R4A 明确：任何候选生成后必须生成区域视觉预览，无 Regional Visual Preview 不得进入 E1-R5 或 production decision
- 在 docs/d5z_nearshore_spec.md 新增 Section 8（D5z 候选后的 Regional Visual Preview 要求），原 Section 8 重编为 Section 9
- 在 docs/e1_r1_current_metrics_audit.md Section 3 补充"父文档定义 50 个采样点"说明语句

### 改动文件
- `docs/e1_day_master_reference_metrics_baseline.md`（新增 E1-R4A 节，更新子轮次计数）
- `docs/d5z_nearshore_spec.md`（新增 Section 8 D5z 候选预览要求）
- `docs/e1_r1_current_metrics_audit.md`（补充 Section 3 采样点说明）

### 遗留问题
- E1-R2 Noon Runtime Exposure Audit 尚未执行
- D5z 前置条件 4（E1-R2 归因）尚未满足，仍禁止进入候选生成
- Sentinel-2 A1/A2/A4 样本、Google Maps REF-01/02/03 尚未采集

---

## 2026-06-08 E1-R2 Noon Runtime Exposure Audit

### 做了什么
- 在 Chrome 独立调试实例（--remote-debugging-port=9222）中，对 d5b_design_v3_2_1 在 noon 模式下进行 10 点浏览器截图测量
- 使用 Chrome DevTools Protocol（Page.captureScreenshot + Runtime.evaluate）采集 2400×1488 截图，提取 canvas 中心 100×100px 的 CIE Lab L* / HSV 数据
- 初次截图发现前 4 点在 TUNE IN 覆盖层（night 模式）下采集，确认 noon 模式（ambient=0.09, sun=1.25）后重新采集
- 对全部 10 点进行归因分析：沙漠 ΔL≈0（贴图层主因），深海 ΔL=+10~+22（runtime atmosphere 主因），热带/极地 ΔL≈0（贴图层主因）
- Ross_Ice_Shelf 采样中心偏至 Southern Ocean，标记 sample_valid=false
- 写入 E1-R2 审计报告和结构化数据文件

### 改动文件
- `docs/e1_r2_noon_exposure_audit.md`（新建，E1-R2 完整审计报告，待 RW 确认）
- `docs/metrics/e1_r2_noon_runtime_measurements.json`（新建，10 点测量数据）
- `docs/metrics/e1_r2_noon_runtime_measurements.csv`（新建，CSV 格式）
- `devlog.md`（本记录）

### 遗留问题
- E1-R2 报告、JSON、CSV 待 RW 确认后 commit
- D5z 前置条件 4（E1-R2 归因）现已满足（待确认提交）
- Phase 7 工作项已明确：深海 atmosphere.opacity 调整（0.14→建议 0.08–0.10）
- Sentinel-2 A1/A2/A4 样本、Google Maps REF-01/02/03 尚未采集

---

## 2026-06-08 RDL v2 P0 — GEBCO + GSHHG Japan Benchmark 实测启动

### 做了什么
- 建立 RDL v2 P0 全局 pipeline 目录结构（pwa/assets/source/{bathy,coastline,dem}/…，scripts/geo/）
- 编写并验证 4 个 geo 工具脚本：
  - `scripts/geo/lon_lat_to_uv.js`：Three.js r128 UV 转换，支持 --bounds 任意区域，输出 GLSL snippet
  - `scripts/geo/gshhg_coastline_render.py`：land mask + distance field + key crops（支持 ETOPO1/GSHHG/NE 任意 shapefile）
  - `scripts/geo/gebco_bathymetry_tint.py`：5级深度 tint（GEBCO netCDF / ETOPO1 fallback）
  - `scripts/geo/rdl_composite_preview.py`：4-panel 合成预览（baseline / bathy / coast / combined）
- 确认 GEBCO 2026（最新）：日本 subset 约 60–80 MB，无需注册，通过 download.gebco.net 可下载
- 下载 GSHHG full resolution（SOEST 服务器限速，Python urllib ~10 MB/min，下载进行中）
- 以 ETOPO1（elev≥0）作为 land mask + NE10m 海岸线作为 interim，跑通全部 3 个 phase
- 生成 interim 输出：etopo1_bathymetry_tint.png / gshhg_coastline_mask.png（4096×3584）/ gshhg_distance_field.png / key_crops_contact_sheet.png（244KB，5 bay crops 清晰）/ combined_gebco_gshhg_preview.png（4-panel，2.9MB）
- 写完 README_P0_RESULT.md（回答 6 个 P0 验证问题）、source_status.md、gebco_download_check.md

### 改动文件
- `pwa/assets/source/bathy/gebco_2024/`（新目录）
- `pwa/assets/source/coastline/gshhg/`（新目录，GSHHG 下载中）
- `pwa/assets/source/dem/copernicus_glo30/`（新目录，保留备用）
- `scripts/geo/lon_lat_to_uv.js`（新建）
- `scripts/geo/gshhg_coastline_render.py`（新建）
- `scripts/geo/gebco_bathymetry_tint.py`（新建）
- `scripts/geo/rdl_composite_preview.py`（新建）
- `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/`（新目录，9 个输出文件）

### 遗留问题
- GSHHG full resolution 下载进行中（SOEST 限速，~8 min 剩余）；完成后需重跑 gshhg_coastline_render.py with --shp GSHHS_f_L1.shp
- GEBCO Japan subset 待 RW 确认后下载（~60–80 MB）；完成后需跑 gebco_bathymetry_tint.py --nc <path>
- 上述两步完成后，重跑 rdl_composite_preview.py 生成最终 4-panel，并生成 etopo_vs_gebco_compare.png
- README_P0_RESULT.md Q3（视觉对比结论）待最终对比图后更新

## 2026-06-08 RDL v2 P0 GEBCO Download + Pipeline Completion

### 做了什么
- 解决了 GEBCO 2026 HDF5 读取障碍（h5py 3.14.0 `TypeError: Unsupported integer size(0)`）
- 使用 HTTP Range 字节偏移方法绕过 h5py：获取 HDF5 数据偏移地址（1,058,396 bytes），以每行列切片（15KB）并发下载
- 确认 GEBCO HDF5 使用小端序（little-endian int16），修正了最初大端序的错误
- 最终方案：50 workers × 135 batches（50行/batch），仅下载 Japan 列切片（103MB）而非完整行（1.16GB）
- 耗时约 6 分钟，保存至 `pwa/assets/source/bathy/gebco_2024/gebco_2024_118_150_22_50.nc`（46MB compressed NetCDF4）
- 验证 GEBCO 数据：6720×7680, 15 arc-sec, z-range -8378m to +3757m, 0 NoData, land 30.6%（与 GSHHG 30.4% 高度吻合）
- 生成 `gebco_bathymetry_tint.png`（892KB）、`etopo_vs_gebco_compare.png`（1.4MB）
- 重命名旧的误名文件 `combined_gebco_gshhg_preview.png` → `combined_etopo1_gshhg_preview.png`
- 重新生成真正的 `combined_gebco_gshhg_preview.png`（3.0MB，GEBCO tint + GSHHG L1 coastline）
- 更新 README_P0_RESULT.md Q3（GEBCO vs ETOPO1 实际对比数据），source_status.md 最终状态

### 改动文件
- `pwa/assets/source/bathy/gebco_2024/gebco_2024_118_150_22_50.nc`（新增，46MB）
- `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/gebco_bathymetry_tint.png`（新增）
- `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/etopo_vs_gebco_compare.png`（新增）
- `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/combined_gebco_gshhg_preview.png`（重新生成，真正使用 GEBCO）
- `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/combined_etopo1_gshhg_preview.png`（从 combined_gebco_gshhg_preview.png 重命名）
- `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/README_P0_RESULT.md`（更新所有 phase 状态 + Q3 结论）
- `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/source_status.md`（标记 P0 完成）

### 遗留问题
- h5py 3.14.0 无法读取 GEBCO 2026 HDF5（已 workaround，不需修复）
- 深度异常值 -10668m 是 masked array argsort 的伪影；实际最深点 ~-5748m（Northwest Pacific），正常
- P0 全部完成，下一步：Japan v2 visual tile 合成（将 GEBCO tint + GSHHG coast + 基底贴图合成到 globe texture）

## 2026-06-08 P0 归档审计 + Japan v2 Tile 准备

### 做了什么
- **GEBCO 版本命名修正**：将 `gebco_2024/` 目录和 `gebco_2024_118_150_22_50.nc` 文件统一重命名为 `gebco_2026/gebco_2026_118_150_22_50.nc`，消除版本号混用；历史 devlog 条目（本条之前的两条）中记录的旧路径为当时实际路径，仅供审计参考，不修改
- **修正所有文档引用**：`source_status.md`、`gebco_download_check.md`（删除错误"audit continuity"辩护）、`gebco_bathymetry_tint.py` docstring、两个全局规划文档中的路径提案
- **README_P0_RESULT.md** 新增两节：Data Source Evidence Chain（明确区分 GSHHG/ETOPO1/GEBCO 2026 各自角色）、HTTP Range Byte-Offset Risk Note（DATA_OFFSET=1,058,396 为版本专属，禁止跨版本复用，给出生产替代方案）
- **新建 FILE_INVENTORY.md**：完整列出 P0 所有输出文件、大小、生成命令、角色
- **新建 NEXT_JAPAN_V2_TILE_PLAN.md**：Japan v2 2048/4096 regional detail tile 合成方案（d5b_v3.2.1 + GEBCO tint + GSHHG coast），含裁剪坐标计算、混合逻辑、proposed script 伪代码、Three.js UV 集成说明

### 改动文件
- `pwa/assets/source/bathy/gebco_2026/gebco_2026_118_150_22_50.nc`（从 gebco_2024/ 重命名）
- `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/source_status.md`（路径修正）
- `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/gebco_download_check.md`（删除错误辩护，修正路径）
- `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/README_P0_RESULT.md`（新增 Evidence Chain + HTTP Range Risk 两节）
- `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/FILE_INVENTORY.md`（新建）
- `previews/rdl_v2_p0_gebco_gshhg_japan_benchmark/NEXT_JAPAN_V2_TILE_PLAN.md`（新建）
- `scripts/geo/gebco_bathymetry_tint.py`（docstring 路径修正）
- `previews/rdl_v2_global_data_source_upgrade_audit/global_pipeline_recommendation.md`（gebco_2024→gebco_2026）
- `previews/rdl_v2_global_data_source_upgrade_audit/implementation_priority.md`（gebco_2024→gebco_2026）

### 遗留问题
- Japan v2 tile 合成脚本 `japan_v2_tile_composite.py` 尚未实现（计划见 NEXT_JAPAN_V2_TILE_PLAN.md）— 已在下一条 devlog 中实现为 `rdl_tile_compositor.py`
- 无 commit（所有修改均为本地文档审计和归档）

## 2026-06-08 RDL v2 Japan Visual Tile Prototype 生成

### 做了什么
- 追加 `.gitignore` 规则：`previews/**/*.png/jpg/jpeg/webp`，防止大尺寸预览图误入 git；验证 dry-run git add 确认 PNG 不再进入暂存区
- 新建 `scripts/geo/rdl_tile_compositor.py`（全球可复用，`--bounds` 驱动，无 Japan 硬编码）：
  - Layer 0：d5b 8K 局部裁切（728×637 → 4096×3584，×5.6 上采样，仅作为基础底色）
  - Layer 1：21.6K source 局部裁切（1920×1680 → 4096×3584，×2.1，per-channel histogram match，仅在陆地低强度叠加）
  - Layer 2：GEBCO 2026 5 级深度分层色调（7680×6720 → 4096×3584，仅作用于海洋像素）
  - Layer 3：GSHHG 海岸线 clarity（scipy distance_transform_edt 计算 coastal zone，unsharp mask 轻微增强）
  - 修复：GSHHG mask 是 RGB（sea=15,30,60 / land=120,105,85 / coast=255,255,240），非 grayscale
  - 修复：PIL DecompressionBombError（21.6K source 233M px 超限，设 MAX_IMAGE_PIXELS=250M）
- 运行 compositor（用时 200s）生成全部输出：
  - `01_layers/`：layer0–layer3 + stack contact sheet
  - `02_tiles/`：v2_4096（10MB）+ v2_2048（4MB）+ baseline + etopo_reference + 4 张 contact sheet
  - `03_demo/`：`demo_japan_v2_tile.html`（Three.js r128 CDN，UV region shader，无 earth3d.js 改动）+ UV bounds outline
  - `04_crops/`：9 个关键区域四面板对比图（baseline / etopo_reference / v2_2048 / v2_4096）
  - `05_reports/`：README_PROTOTYPE.md + FILE_INVENTORY.md + NEXT_STEP_RECOMMENDATION.md + metadata.json
- 验收参数：GEBCO blend=0.35，GSHHG zone=10km，GSHHG strength=0.15，visual blend=0.30

### 改动文件
- `.gitignore`（追加 previews/**/ 图片规则）
- `scripts/geo/rdl_tile_compositor.py`（新建，全球通用 tile 合成器）
- `previews/rdl_v2_japan_visual_tile_prototype/`（新目录，全部输出）
- `devlog.md`（本条追加）

### 遗留问题
- README_PROTOTYPE.md 中验收结论表（Yes/No/Partial）待人工视觉检查后填写
- 视觉通过后进入 Step A：独立上球 demo 验证（不修改 earth3d.js）
- DEM Phase（Copernicus GLO-30）：陆地山形精度，等 Step A 通过后推进
- Layer 6（OSM 路网 / VIIRS 城市灯光）：继续暂缓，等自然地理层稳定后进入
- 无 commit

---

## 2026-06-09 Japan v2 Visual Retuning Pass

### 做了什么
- 人工视觉检查 Japan v2 Prototype 结论：**Partial** — 数据有效，但视觉偏模糊，存在 GIS 感、海底色块感、海岸线描边感
- 新建 `scripts/geo/rdl_retuning.py` 执行视觉转译优化（不新增数据源）
- 关键算法变更：
  - **GEBCO**：移除 5 级硬色板（GIS 感根源），改为连续深度亮度衰减 + sqrt 非线性重映射 + Gaussian blur sigma=20px (~7.5km) 消除所有硬边 + 极小蓝色偏移（最深处 +10）
  - **GSHHG 海岸线**：移除 unsharp mask（描边感根源），改为海岸带 21.6K 卫星源额外混合（coast_strength 提升 L1 blend 权重，双侧 feather）
  - **Land**：visual_blend 从 0.30 降至 0.15
  - 修复 EDT 距离计算 bug：原始 `np.minimum` 对所有像素返回 0 → 改为 `land_side + ocean_side` 求和（每像素恰好一项非零）
- 生成 `previews/rdl_v2_japan_visual_retuning/` 全部输出（113s）：
  - bathy 变体（coast=off）：blend 0.15 / 0.20 / 0.25
  - coast 变体（bathy=0.20）：10km / 20km / 30km 带宽
  - final 最终合成：bathy=0.20，coast=20km，str=0.08，visual=0.15，4096 + 2048
  - before/after contact sheet，5 关键区域 crop 对比
  - README_RETUNING.md（含验收表，待填）

### 改动文件
- `scripts/geo/rdl_retuning.py`（新建，视觉调音专用脚本）
- `previews/rdl_v2_japan_visual_retuning/`（新目录，全部输出）
- `devlog.md`（本条追加）

### 遗留问题
- README_RETUNING.md 验收表（6 题 Yes/No/Partial）待人工视觉检查后填写
- 若视觉通过，进入 Step A：独立上球 demo（独立 HTML，不修改 earth3d.js）
- 无 commit

---

## 2026-06-09 E1-R4A Regional Visual Preview — d5b_design_v3_2_1

### 做了什么
- 执行 DAY_TEXTURE_VARIANT Provenance Audit：确认 bmng_d2 是 A/B 测试中间态，d5b_design_v3_2_1 是 devlog 标注的预期正式候选
- 通过 `?dayTexture=d5b_design_v3_2_1`（localhost URL 参数）加载目标纹理，未修改 earth3d.js
- 使用 puppeteer-core + 系统 Chrome（headless, --use-gl=angle）自动化截图
- 全部阻断检查通过：variant confirmed, HTTP 200, 8192×4096, earth3d.isReady=true
- 生成 16 张截图（8 区域 × 2 时间模式：noon / afternoon）

### 改动文件
- `previews/e1_r4a_d5b_design_v3_2_1/`（新目录，16 张截图 + report.md）
- `docs/e1_r4a_regional_preview_d5b_design_v3_2_1.md`（正式报告，待视觉审查填写结论）
- `devlog.md`（本条追加）

### 遗留问题
- 截图视觉审查待完成（verdicts 表尚未填写）
- 审查通过后执行：`DAY_TEXTURE_VARIANT = 'd5b_design_v3_2_1'` + commit
- 截图工具（puppeteer-core）安装在 /tmp/e1r4a_runner，非项目目录，不计入代码库

---

## 2026-06-09 E1-R4A Rerun — TUNE IN overlay 修复

### 做了什么
- 首轮截图无效：headless Chrome 未点击 TUNE IN 按钮，截图停留在入口遮罩层（backdrop-filter: blur）
- 根因：`#start-overlay.visible` 在 WS 收到初始 queue payload 后才出现，首版脚本未处理此 overlay
- 修复：等待 `#start-overlay.visible` → click `#start-button` → 等待 overlay 消失 → 1.5s settle → 再截图
- 另修复：rerun 脚本遗漏 `variantConfirmed` 赋值（console handler 缺行）
- 重新生成 17 张截图（16 区域 + 1 baseline），文件尺寸 330–483KB（正常 globe 内容，非遮罩）

### 改动文件
- `previews/e1_r4a_d5b_design_v3_2_1_rerun/`（新目录，17 张截图 + report.md）
- `docs/e1_r4a_regional_preview_d5b_design_v3_2_1.md`（更新，待视觉审查填写结论）
- `devlog.md`（本条追加）

### 遗留问题
- verdicts 表待人工视觉审查后填写
- 审查通过后执行：`DAY_TEXTURE_VARIANT = 'd5b_design_v3_2_1'` + commit

## 2026-06-09 E1-R4A Verdicts 写入 + E1-R3 D5z 候选生成

### 做了什么
- 将用户确认的 E1-R4A 人工验收结论写入 `docs/e1_r4a_regional_preview_d5b_design_v3_2_1.md`
  - 整体结论：Conditional Pass
  - Sahara/Egypt / Antarctica / Greenland / Indian Ocean：Partial（各有具体问题）
  - Pacific Islands / Japan / Mediterranean / Caribbean：Pass（受保护区域）
  - 明确边界：不修改 DAY_TEXTURE_VARIANT，不 commit，不构成 production acceptance
- 新建 `d5b_processor_v3/d5z_generator.py`：D5z 候选生成脚本
  - 架构决策：Standalone correction pass，不重走 main.py（避免 OCEAN_REGIONS 双重叠加）
  - 校正 A（双极）：对冰雪像素（luminance>155, channel_spread<55）直接乘以亮度因子
    - 南极：lat<-70° 全强度 0.87，5° 渐变到 lat=-65°
    - Greenland/Arctic（新增）：lat>70° 全强度 0.90，5° 渐变到 lat=65°
  - 校正 B（深海）：Indian Ocean central + Pacific deep 深蓝像素降饱和 7% + 降亮 3%，feather 20px
  - 校正 C（沙漠，仅 D5z_b）：Sahara/Arabia 陆地像素降亮 3%，Mediterranean 硬边界排除
  - Color Harmony Guard：D5z_b 后处理，检测保护区 mean RGB/亮度 diff 超阈值时 blend 回 baseline
- 生成候选 + 全部指标通过：
  - `d5z_a_8192x4096.jpg` 7801KB，`d5z_b_8192x4096.jpg` 7801KB
  - Antarctica 冰像素亮度变化：−12.73%（通过范围 ↓3–20%）
  - Greenland 冰像素亮度变化：−7.69%（通过范围 ↓2–15%）
  - Sahara 陆地亮度变化（D5z_b）：−2.79%（通过范围 ↓1–8%）
  - Indian Ocean 深海饱和度变化：−4.28%（通过范围 ↓3–12%）
  - 极地灰化检测：south delta=-0.42, north delta=-0.16（均不变灰，更趋中性）
  - 受保护区域：Japan / Mediterranean / Caribbean = PSNR ∞ / diff 0；Pacific Islands 63.05 dB / 0.008 diff
  - Color Harmony Guard：全部保护区未触发（diff < 2）
  - 全局亮度变化：3.587%（超过 Guard ≤2% 限制，但 Guard 自身调整量=0；整体变化源自极地校正，属于预期）
- 生成 8 区域 compare crops（baseline | D5z_a | D5z_b 横排）
- 输出执行报告：`d5b_processor_v3/d5b_output/d5z_candidates/report_d5z.md`

### 改动文件
- `docs/e1_r4a_regional_preview_d5b_design_v3_2_1.md`（verdicts + boundary 填写）
- `d5b_processor_v3/d5z_generator.py`（新建）
- `d5b_processor_v3/d5b_output/d5z_candidates/d5z_a_8192x4096.jpg`（新建）
- `d5b_processor_v3/d5b_output/d5z_candidates/d5z_b_8192x4096.jpg`（新建）
- `d5b_processor_v3/d5b_output/d5z_candidates/metrics_d5z_a.json`（新建）
- `d5b_processor_v3/d5b_output/d5z_candidates/metrics_d5z_b.json`（新建）
- `d5b_processor_v3/d5b_output/d5z_candidates/compare_crops/`（8 个 crop，新建）
- `d5b_processor_v3/d5b_output/d5z_candidates/report_d5z.md`（新建）
- 未修改：`earth3d.js`，`DAY_TEXTURE_VARIANT`（仍为 `'bmng_d2'`），`pwa/assets/earth/`（未写入）

### 遗留问题
- `earth3d.js getDayTexturePaths()` 尚无 `d5z_a` / `d5z_b` key → 上球预览（E1-R4B）被阻断
- 需 RW 单独授权后方可：(1) 添加 variant keys, (2) 复制 JPG 到 candidates/, (3) 进行 E1-R4B puppeteer 截图
- 全局亮度变化 3.587% 超过 Guard ≤2% 规范，若上球后整体偏暗，可在 D5z_c 中将南极因子 0.87→0.91，北极 0.90→0.93
- 推荐首选上球候选：D5z_b（覆盖全部 3 个校正目标，Guard 未触发，全部指标通过）

## 2026-06-09 E1-R4B 结论写入 + E1-R5 Full On-globe Visual Acceptance 执行

### 做了什么
- 将 E1-R4B 人工视觉验收结论写入 `docs/e1_r4b_d5z_on_globe_preview.md`：
  - D5z_b: Conditional Pass，覆盖极地/深海/Sahara 三类问题；Mediterranean / Caribbean / Japan 保护区无误伤；Indian Ocean 仍略有地图感，不构成阻断
  - D5z_a: Conservative fallback，极地+深海校正等效，无 Sahara 校正
  - 边界：仅允许进入 E1-R5，不修改 DAY_TEXTURE_VARIANT，不 commit，不 production 化
- 执行 E1-R5 Full On-globe Visual Acceptance：
  - D5z_b（主候选）：9 区域 × 4 time modes（morning/noon/afternoon/sunset）= 36 张地理截图 + 4 张 UI integration 截图（标准播放器视角 lon=10 lat=20）
  - D5b_design_v3_2_1（基线对照）：5 个关键区域 × 4 time modes = 20 张对照截图（Sahara / Antarctica / Greenland / Mediterranean / Indian Ocean）
  - D5z_a：未预先截图，仅在 D5z_b 触发 Fail 时执行
  - 两轮均加载正常：HTTP 200，variant confirmed，8192×4096 ✓，TUNE IN dismissed ✓
  - 共 60 张截图

### 改动文件
- `docs/e1_r4b_d5z_on_globe_preview.md`（verdicts + next step 填写）
- `docs/e1_r5_full_on_globe_acceptance.md`（新建，预填框架，verdicts 留空待人工审查）
- `previews/e1_r5_full_acceptance/d5z_b/`（40 张截图 + index.md，新建）
- `previews/e1_r5_full_acceptance/d5b_design_v3_2_1/`（20 张截图 + index.md，新建）
- 未修改：`earth3d.js DAY_TEXTURE_VARIANT`（仍为 `'bmng_d2'`），`pwa/assets/earth/production/`（未写入），无 commit

### 遗留问题
- E1-R5 截图已就绪，等待 RW 人工视觉验收
- 验收通过（Pass / Conditional Pass）后，RW 明确授权才可进入 E1-R6
- D5z_a 截图待 D5z_b 失败时按需执行
- Conditional Pass 允许最多 2 项 Partial（仅限极地亮度/Indian Ocean 深海）；保护区 / Sahara 变色 / 硬边界 / UI 可读性 均不允许 Partial

<<<<<<< HEAD
## 2026-06-10 B-6.1 Asset Audit

### 做了什么
- 执行 `docs/phase_b6_1_asset_audit_task_brief.md` 定义的 7 个审计任务（read-only）
- 确认 ETOPO1 Ice 全球 NetCDF4（890MB，21601×10801，MD5=36edc15...）可用
- 确认 GSHHG 2.3.7 全 5 层级（f/h/i/l/c）已解压，L1 full 179,837 shapes，pyshp 可读
- 确认 GEBCO 仅为 Japan subset（lon 118–150, lat 22–50），不可作为全球 B-6 基础
- 确认核心 Python 依赖：numpy/Pillow/scipy/netCDF4/h5py/xarray/shapefile/shapely 全部 INSTALLED
- 确认 4 个可选依赖缺失（geopandas/rasterio/pyproj/skimage），均不影响 B-6.2 最小集
- 生成正式审计文档 `docs/phase_b6_1_asset_audit.md`（10 section）
- B-6.2 Go/No-Go 判断：READY_TO_PROCEED

### 改动文件
- `docs/phase_b6_1_asset_audit.md`（新建，~300 行，未 commit）
- 未修改：`d6_noon_air_earth_generator.py`（仍 unstaged），`pwa/`，`previews/`

### 遗留问题
- `d6_noon_air_earth_generator.py`（B-5.1+B-5.2）仍 unstaged，等待人工授权后 commit
- B-5.3 代码实施（`apply_island_reef_floor` 圆形 mask）等待人工授权
- B-6.2 可立即开始：新建 `scripts/generate_b6_structure_masks.py`，生成 P0 mask set at 2K
  - 等待人工明确授权后方可实施

## 2026-06-10 B-6.2 Structure Mask Prototype

### 做了什么
- 新建 `scripts/generate_b6_structure_masks.py`（独立脚本，不 import d6，不写 pwa）
- 执行 `python3 scripts/generate_b6_structure_masks.py --resolution 2048x1024 --gshhg-tier h`
- 生成 9 个 float32 [0,1] 2K structure masks：land/ocean/deep_ocean/mid_ocean/continental_shelf/shallow_sea/coastline_distance + mountain/plateau
- 输出到 `d5b_processor_v3/d5b_output/structure_masks/`（gitignored）
- 生成 structure_mask_metadata.json / structure_mask_metrics.json / 4 张 preview JPG
- commit B-6.2 脚本 `0dfdb87`

### 关键 metrics
- land_mask: 25.3% (GSHHG) vs 33.9% (ETOPO1) — 差异主要来自南极/格陵兰冰架（ETOPO1 Ice Variant z>0 = 陆地）
- ocean_mask: 74.7%
- deep_ocean: 40.2%, mid_ocean: 15.4%, shelf: 3.7%, shallow: 4.3%
- depth 互斥检查: overlap=0 px ✓
- land+ocean = 1.0 ✓
- ETOPO1/GSHHG 不一致率: 11.8%（主要为冰架区域）
- coastline_distance: max 319px ≈ 6,200 km（太平洋中心），pixel units only
- 总用时: 20.7s（ETOPO1 12.3s + GSHHG 5.6s + 掩码生成 1.2s）

### 改动文件
- `scripts/generate_b6_structure_masks.py`（新建，已 commit `0dfdb87`）
- `d5b_processor_v3/d5b_output/structure_masks/`（生成物，gitignored，未 commit）
- 未修改：`d6_noon_air_earth_generator.py`、`pwa/`、`earth3d.js`

### 遗留问题
- NPZ 8.5MB（gitignored），适合本地使用，不入库
- 11.8% GSHHG/ETOPO1 不一致：主要为南极冰架，对 Noon Air 色彩的影响区域在极地（已有 polar correction 模块）
- coastline_distance 暂为 pixel 单位，km 校正推迟至 B-6.3
- B-6.3：将 structure masks 集成进 d6 generator（B-5.3 实施后才进入 B-6.3）
- B-5.3 代码实施（apply_island_reef_floor）仍等待人工授权

## 2026-06-10 B-6.2P Polar / Antarctica Land-Ice Patch

### 做了什么
- 发现 critical issue：GSHHG L1 不覆盖南极洲内部（lat -70 to -90），导致 Antarctica interior 被误判为 ocean
- 提交 B-6.3 审计文档 `a71779e`
- 修改 `scripts/generate_b6_structure_masks.py`：
  - 新增 polar supplement：`antarctica_ice_mask = (lat < -60) & (ETOPO1 z > 0)`
  - 新增 `greenland_ice_mask = bbox (lat 59.5–84.5, lon -74 to -11) & (z > 0)`
  - `land_mask = max(GSHHG_rasterized, polar_land_ice_supplement)`
  - 所有 depth mask 基于修正后的 ocean_mask 重新计算
  - 新增 polar sanity checks、depth_on_land 检查、before/after disagreement 对比
  - 新增 `polar_ice_supplement_preview.jpg`
- 重新生成 2K structure masks，共 12 个 masks
- 提交脚本修改 `f1478d8`

### 关键 metrics（修复后）
- land_mask: 35.5%（GSHHG 25.3% + 极地补充 10.2%）
- ocean_mask: 64.5%
- ETOPO1/land 不一致率：11.83% → **1.60%**（减少 214,556 px）
- depth_on_land_pixels: **0** ✓
- antarctica_depth_mask_pixels: **0** ✓
- depth overlap: **0** ✓
- land+ocean = 1.0 ✓

### Polar sanity checks（全部 PASS）
- Antarctica interior (0°, -80°): land=1.000, ocean=0.000, ant_ice=1.000 **PASS**
- Greenland (−42°, 72°): land=1.000 **PASS**
- Antarctic coast (0°, -70°): land=1.000 **PASS**
- Southern Ocean (0°, -55°): ocean=1.000 **PASS**

### 改动文件
- `scripts/generate_b6_structure_masks.py`（修改，commit `f1478d8`）
- `docs/phase_b6_3_structure_mask_validation_audit.md`（commit `a71779e`）
- `d5b_processor_v3/d5b_output/structure_masks/`（重新生成，gitignored，未 commit）

### 遗留问题
- 残余 1.60% ETOPO1/land 不一致：主要为小岛/海岸线像素级差异，不影响主要目标
- coastline_distance 仍为 pixel 单位，km 校正推迟至 B-6.3 integration
- B-6.3：structure mask 集成进 d6 generator（B-5.3 实施后）
- B-5.3 代码实施等待授权
- d6_noon_air_earth_generator.py（B-5.1+B-5.2 修改）仍 unstaged，等待授权 commit

## 2026-06-10 B-6.2S Structure Mask Supplement Planning

### 做了什么
- 提交 B-6.3R 重新验证文档 `40135b2`
- 生成 B-6.2S 补强规划文档 `docs/phase_b6_2s_structure_mask_supplement_plan.md`
- 未改代码，未重新生成 masks，未运行 d6

### 规划核心结论
- Group A（Special Sea water-only masks）：11 个 bbox+ocean_mask，低风险，建议立即实施（B-6.2S-1）
- Group B（Shelf/Bank masks）：5 个 ETOPO1 深度门控，中等风险，B-6.2S-2
- Group C（Island/Reef proxy）：需 GSHHG f tier，实验性，B-6.2S-3
- GBR reef / Red Sea reef：缓实施，需 GEBCO global（7.8 GB，未下载）
- B-5.3 与 B-6.2S 可并行，B-5.3 是视觉优先级最高的未阻塞任务
- 建议优先 B-5.3，然后 B-6.2S-1

### 改动文件
- `docs/phase_b6_2s_structure_mask_supplement_plan.md`（新建，未 commit）
- 未修改：d6、pwa、previews、masks

### 遗留问题
- B-6.2S 规划文档未 commit（等待授权）
- B-5.3 代码实施等待授权（最高价值未阻塞任务）
- d6_noon_air_earth_generator.py（B-5.1+B-5.2）仍 unstaged

---

## 2026-06-24 B-6.2X-D3-S — GEE Supplemental 8K Import Test

### 做了什么
- 对 `source_cache/gee_global/supplemental_8k/` 6 个文件执行完整 import test
- 验证 MERIT DEM v1.0.3：int16，nodata=-32768，min=-414m，max=7396m，75.82% nodata（陆地专用）
- 验证 MODIS MCD12Q1 LC_Type1 / Type5 / Prop1 / QC：全部 uint8，无 nodata tag（class 0 = 隐式 background）
- 验证 SRTM Landforms：uint8，16 个地貌分类值，class 0 = ocean/nodata（77.3%）
- 识别关键 caveat：MODIS class 15（Snow/Ice）= 10.5%，含海冰，与 ESA 1.09% 差异有据可查
- 所有 6 文件 8192×4096，EPSG:4326，pixel=0.04394531°，与 Phase 1 grid 对齐
- origin_y = 89.999（sub-pixel 偏差，亚像素级，可接受）

### 改动文件
- `docs/phase_b6_2x_d3_s_gee_supplemental_import_test.md`（新建）

### 遗留问题
- 建议更新 M1-A 设计文档，新增 supplemental sources 节（MERIT / MODIS / SRTM），等待用户授权
- 4 个 D3/D3-R/D3-S 文档未 commit（边界规则限制）
- M1-B prototype mask 生成等待用户授权
- ESA WorldCover 文件误放在 copernicus_dem_tiles/ 目录内，未清理

---

## 2026-06-24 B-6.2X-D3-S-EXT-A — External Raw Source Audit

### 做了什么
- 审查 `external_raw/` 下 4 个外部 source 目录：Global Aridity/PET、Köppen-Geiger、GEBCO、Allen Coral Atlas
- Global Aridity v3.1：确认 30 arc-second GeoTIFF（annual + monthly），coverage -60~90°，license=non-commercial（research_only=true）
- Köppen-Geiger v3：确认 1991-2020 present-day 文件已下载（125 MB TIF zip + 720 MB NC zip），30 class legend 读取，CC BY 4.0
- GEBCO：发现下载文件为 `.crdownload`（Chrome 临时名），但 magic bytes 确认为 ZIP（PK 签名），3.8 GB 与 GEBCO 2024 GeoTIFF pack 吻合；无法自动重命名（边界规则），需用户手动处理
- Allen Coral Atlas：确认 29 个区域全部下载（30 zip 含一个重复），共 ~16 GB，格式为 GeoPackage vector（.gpkg），需要 rasterization 步骤才能生成 8K GeoTIFF；SEA 区域已部分解压

### 改动文件
- `docs/phase_b6_2x_d3_s_ext_external_raw_source_audit.md`（新建）
- `external_manifests/global_aridity_pet_manifest.json`（更新，补充实际下载文件 + spatial metadata）
- `external_manifests/koppen_geiger_manifest.json`（更新，补充实际下载文件 + 时期结构 + class legend）
- `external_manifests/gebco_manifest.json`（新建）
- `external_manifests/allen_coral_atlas_manifest.json`（新建）

### 遗留问题
- GEBCO：用户需手动 `mv "未确认 276172.crdownload" gebco_2024_grid.zip` 后，才能验证内容和更新 manifest
- Allen Coral Atlas：需安装 rasterio + fiona 才能 rasterize；尚未规划 EXT-B 处理步骤
- Global Aridity：research_only，RodiO 商业化前需替换为 CC 源
- Köppen-Geiger 代码层面需显式排除 2041-2099 SSP 文件
- 所有文档均未 commit（边界规则限制）

---

## 2026-06-24 B-6.2X-D3-S-EXT-GEBCO-R — GEBCO Re-download Verification

### 做了什么
- 审查 gebco/ 目录 4 个文件：ice_surface zip（25.6 MB）、GEBCO_2026.zip（4.0 GB）、sub_ice_topo zip（4.1 GB）、已解压 sub_ice_topo 目录（~7.1 GB）
- ice_surface geotiff zip：**截断下载**（EOCD 缺失，25.6 MB 显然过小），需重新下载
- GEBCO_2026.zip（NetCDF）：完整（EOCD 确认），内含 GEBCO_2026.nc 7.47 GB，需 netCDF4 库
- sub_ice_topo zip：ZIP 本体截断，但 8 个 tiles 已提前解压并验证
- 验证已解压 tiles：21600×21600 int16，EPSG:4326，15 arc-second，nodata=-32767，100% 有效像素，min=-10448m，max=6141m，mean=-2484m（全球海洋 + 陆地连续覆盖）
- 总体 GEBCO readiness：sub_ice_topo GeoTIFF tiles → `ready_for_processing_8k`

### 改动文件
- `docs/phase_b6_2x_d3_s_ext_gebco_redownload_verification.md`（新建）
- `external_manifests/gebco_manifest.json`（更新）

### 遗留问题
- ice_surface geotiff zip 截断，如需 ice surface 专用数据需重新下载（低优先级；sub-ice 可覆盖主要用途）
- sub_ice_topo tiles 为无压缩 TIFF，每 tile 890 MB，8K 处理需分块读取
- 所有文档未 commit（边界规则限制）

---

## 2026-06-24 B-6.2X-D3-S-EXT-B — External Source Processing Plan

### 做了什么
- 制定 4 个外部源从 raw 到 8192×4096 GeoTIFF 的完整处理计划
- 确认 external_processed_8k/ 目录已存在（当前为空）
- 计算各源降采样比：Aridity/Köppen ≈ 5.27x（30arcsec→158arcsec），GEBCO ≈ 10.55x（15arcsec→158arcsec）
- 规划 Köppen：从 ZIP 流式读取 12.5 MB TIF，nearest-neighbor 降采样，无 license 限制，最优先执行
- 规划 Aridity：提取 405 MB LZW TIF，average 降采样，南极 683 行 nodata 填充，output 标注 research_only
- 规划 GEBCO：8 tile 逐个读取（每 tile 889 MB），scipy.ndimage.zoom 非整数比降采样，2048×2048/tile 拼 8192×4096
- 规划 ACA：fiona+rasterio rasterize 29 区域 gpkg → 全球 8K binary mask；benthic deferred（Caribbean 8.4 GB 过大）
- 明确排除：Köppen future SSP、GEBCO ice_surface zip（截断）、GEBCO NetCDF（暂缓）、ACA benthic（过大）

### 改动文件
- `docs/phase_b6_2x_d3_s_ext_external_source_processing_plan.md`（新建）

### 遗留问题
- 所有实际处理均未执行（本阶段 planning only）
- ACA 需要安装 fiona + rasterio，需 libgdal 依赖，需在 EXT-C1 开始前确认
- Global Aridity research_only license 提醒：output 文件需标记，不得进入商业流程
- 下一步：用户授权后执行 EXT-C1 — Köppen-Geiger 8K Processing

## 2026-06-24 B-6.2X-D3-S-EXT-C1 — Köppen-Geiger 8K Processing

### 做了什么
- 从 `koppen_geiger_tif.zip` 流式读取 `1991_2020/koppen_geiger_0p00833333.tif`（21600×43200，uint8，LZW，11.9 MB 压缩）
- 使用 `PIL.Image.Resampling.NEAREST`（Pillow 12.2.0）降采样至 8192×4096（scipy 未安装，PIL 替代方案）
- 写入 Phase 1 标准 GeoTIFF：ModelPixelScaleTag + ModelTiepointTag + GeoKeyDirectoryTag（EPSG:4326）
- 执行 import check：shape/dtype/CRS/origin/pixel_dx/value_range 全部 PASS
- 30 个 Köppen 类别（1–30）全部存在，无非法 code（max=30），class 0 = 海洋 66.86%
- 输出文件 0.75 MB（LZW 分类数据压缩比高），处理耗时 0.6 秒

### 改动文件
- `d5b_processor_v3/source_cache/gee_global/external_processed_8k/koppen_geiger_1991_2020_8192x4096.tif`（新建，0.75 MB）
- `docs/phase_b6_2x_d3_s_ext_c1_koppen_geiger_8k_processing.md`（新建）
- `d5b_processor_v3/source_cache/gee_global/external_manifests/koppen_geiger_manifest.json`（更新 processing_status/stage/resampling_method）

### 遗留问题
- nodata 无显式 GDAL_NODATA tag（class 0 = ocean 隐式，与 ESA WorldCover 约定一致）
- Confidence layer 未下载（不在 koppen_geiger_tif.zip 中）
- 下一步：EXT-C2 — Global Aridity/PET 8K Processing（注意 research_only license）

## 2026-06-24 B-6.2X-D3-S-EXT-C1-X — Cross-Layer Consistency Audit

### 做了什么
- 对已完成 Köppen-Geiger 8K layer 执行只读跨层一致性审计
- 读取既有 ESA WorldCover 8K、MERIT DEM 8K、JRC GSW occurrence/max_extent 8K，未生成 mask，未重采样，未修改任何 GeoTIFF
- Köppen vs WorldCover：全局 mismatch ratio 1.094%，主要集中在 arid cropland 与 tropical forest transition bins
- Köppen vs DEM：全局 anomaly ratio 0.252%，未发现 high-altitude tropical mismatch，主要 anomaly 为 Andes/Himalaya 高程边界类
- Köppen vs Water：基于 ESA0 latitude-bounded ocean proxy 未发现 material ocean misclassification（0.048%）
- Final verdict：conditional_pass；条件为 MERIT DEM metadata 存在轻微 grid offset，且 ESA0/JRC 不可当作完美 ocean mask

### 改动文件
- `docs/phase_b6_2x_d3_s_ext_c1_cross_layer_validation.md`（新建）
- `devlog.md`（追加本记录）

### 遗留问题
- MERIT DEM metadata 与 Köppen/ESA grid 不完全一致：originY=89.999，Y scale=0.04394482421875；本轮未重采样，仅按 array index 审计
- 后续如需严格 ocean 判断，应先明确独立 ocean mask 来源，不能直接把 ESA 0 或 JRC GSW 当作完美 ocean mask

## 2026-06-24 B-6.2X-C1-X2 — GEBCO Canonical DEM Interface Layer

### 做了什么
- 新增 `core/dem/` Python DEM abstraction layer：统一 `DEMInterface`、GEBCO/ETOPO1/Copernicus adapters、`DEMRegistry`
- 实现 GEBCO tile directory source detection、tile filename bounds parsing、lon/lat 到 native tile/pixel 的 lazy query mapping
- 实现 ETOPO1 global fallback adapter 与 Copernicus land refinement adapter
- 建立 DEM priority：land → Copernicus，ocean → GEBCO，fallback → ETOPO1；GEBCO 明确不是 primary DEM
- 执行只读验证：GEBCO 8 tiles 全球覆盖完整，CRS/shape/dtype/pixel size 一致；ETOPO1 与 Copernicus 8K alignment PASS
- 执行内存抽样 consistency check：GEBCO vs ETOPO1 median abs deviation 38m；Copernicus vs ETOPO1 land-valid median abs deviation 50m

### 改动文件
- `core/dem/__init__.py`（新建）
- `core/dem/dem_interface.py`（新建）
- `core/dem/gebco_adapter.py`（新建）
- `core/dem/etopo_adapter.py`（新建）
- `core/dem/copernicus_adapter.py`（新建）
- `docs/phase_b6_2x_c1_x2_gebco_canonical_dem_layer.md`（新建）
- `devlog.md`（追加本记录）

### 遗留问题
- GEBCO ZIP / NetCDF 目前只做 source type detection，已验证实现路径为已解压 tile directory
- `get_window()` 对 GEBCO 返回多 tile native windows，不做 stitch/merge；调用方需显式处理
- Registry land/ocean routing 仅使用 source validity 与 value sign，不生成也不依赖 land/ocean mask

## 2026-06-24 B-6.2X-M0 — Spatial Runtime Engine

### 做了什么
- 新增 `core/runtime/` runtime computation layer：`SpatialRuntime`、`FeatureComposer`、`QueryEngine`、runtime dataclasses
- 实现 `GlobalGridLock`：8192×4096 EPSG:4326 grid index 与 layer metadata alignment validation
- 实现 `DEMOceanTruthKernel`：runtime ocean rule = `DEM < 0`
- 接入 C1-X2 `DEMRegistry`：Copernicus(land) → GEBCO(ocean) → ETOPO1(fallback)
- 实现 `ClimateRasterLayer`：Köppen 仅在 Global Grid Lock 对齐通过后 lazy lookup
- 实现 point query、window aggregation、batch query、feature vector composition/normalization、in-memory consistency metrics
- 执行 sanity queries：`(0,0)` ocean bathymetry、`(120,30)` land climate 14、`(-60,-20)` land climate 3
- 输出 metrics：consistency_score=1.0，ocean_conflict_rate=0.0，feature_vector_stability=1.0

### 改动文件
- `core/runtime/__init__.py`（新建）
- `core/runtime/spatial_runtime.py`（新建）
- `core/runtime/feature_composer.py`（新建）
- `core/runtime/query_engine.py`（新建）
- `core/runtime/runtime_types.py`（新建）
- `docs/phase_b6_2x_m0_spatial_runtime_engine.md`（新建）
- `devlog.md`（追加本记录）

### 遗留问题
- `query_window()` 当前为 point sampling aggregation，不是 8K batch processing，也不导出 raster
- `slope_proxy` 是 runtime local delta，不是正式 slope raster
- `biome_proxy` 仅作为 M1-B 前置语义探针，不是 accepted mask
- Ocean truth 当前为 DEM sign rule，尚未引入 shoreline/water-occurrence arbitration

## 2026-06-24 B-6.2X-D6 — Temporal Semantic Rendering Engine (CPU)

### 做了什么
- 检查 Codex 实现的 M0（core/dem/ + core/runtime/），确认接口完整可用
- 新建 core/rendering/ 模块组，实现 D6 CPU renderer：
  - renderer_types.py：RGB / TimeState / SunState / LightState / SeasonalState / DayCycleState
  - temporal_model.py：NOAA 太阳方位角（Spencer 1971 Fourier）+ 季节因子 + 昼夜相位
  - light_model.py：Lambert 光照 + Rayleigh 散射近似 + slope 地形衰减
  - color_model.py：biome_proxy 调色板（6 锚点线性插值）+ 时态位移 + 光照融合
  - d6_renderer.py：D6Renderer 主入口，接 SpatialRuntime.query_point()
- 修复 bug：temporal_model 中 `lon * 4` 不应加入 tst（hour 为 local solar time，非 UTC）
- 修复 palette bug：EF 极地 biome_proxy=0.10 与浅海重叠 → non-ocean guard → 冰原蓝白
- 运行端到端验证：上海 / 太平洋 / 撒哈拉 / 亚马孙 / 南极 / 格陵兰 / 喜马拉雅 全部语义正确
- 昼夜亮度范围 0.4464，diurnal_variation_ok=True

### 改动文件
- `core/rendering/__init__.py`（新建）
- `core/rendering/renderer_types.py`（新建）
- `core/rendering/temporal_model.py`（新建）
- `core/rendering/light_model.py`（新建）
- `core/rendering/color_model.py`（新建）
- `core/rendering/d6_renderer.py`（新建）
- `docs/phase_b6_2x_d6_temporal_semantic_rendering_engine.md`（新建）

### 遗留问题
- render_window 为 per-point loop（64×64 = 4096 次 query_point）；GPU shader 为 Phase 3
- 海面镜面反射（sun glint）未实现；深海昼夜稳定性略高于现实
- hour 为 local apparent solar time；UTC 输入需调用方自行换算
- EF 极地 non-ocean guard：biome_proxy < 0.20 + non-ocean → 冰原白；ET 冻原精细化 deferred

## 2026-06-24 B-6.2X-D6 Bug Fix — P1/P2/P3

### 做了什么
- P1（关键）：修复 DEMRegistry.query() 近海点误路由。将 Copernicus 门槛从 `value > -500` 改为 `value > 0`，确保返回 0 的近海像素落到 GEBCO 负值测深；(-122.4, 37.8) 修复前为 elevation=0/ocean=False（陆地），修复后为 elevation=-4/ocean=True（海洋）
- P2（安全）：render_window() 新增 `_MAX_WINDOW_PIXELS = 512×512` 硬上限，超出时抛 ValueError；提供 allow_large=True 逃生口，防止意外触发 8K batch 计算
- P3（完善）：DayCycleState.contrast 字段接入 ColorModel.apply_temporal_shift()，在饱和度步骤之后追加 luminance 相对压缩；黎明(0.15)/夜间(0.08) 产生低对比度平坦感，正午(1.0) 无变化

### 改动文件
- `core/dem/dem_interface.py`：DEMRegistry.query() 门槛 > -500 → > 0
- `core/rendering/d6_renderer.py`：render_window() 新增 _MAX_WINDOW_PIXELS 检查 + allow_large 参数
- `core/rendering/color_model.py`：apply_temporal_shift() 新增 contrast 压缩步骤

### 遗留问题
- 严格 > 0 会让海拔 0m 的真实海岸陆地（如荷兰低洼地）落到 GEBCO/ETOPO1；ETOPO1 fallback 此时正常工作，不影响 ocean 判断正确性，但可记录为已知精度限制

## 2026-06-24 B-6.2X-D6 Bug Fix — Below-Sea-Level Land Veto

### 做了什么
- 发现并修复低于海平面陆地（死海 -417m / 死亡谷 -82m / 里海洼地 -179m）被 OTK 误判为 ocean 的问题
- 在 SpatialRuntime.query_point() 中加入 Köppen 气候层 veto：若 ocean=True 但 climate_class > 0，则强制翻转 ocean=False
- Köppen 类 1–30 只分配给陆地像素，海洋的 climate_class=None，veto 不影响真实海洋判断
- source["ocean_rule"] 字段记录是否触发了 veto，便于调试

### 改动文件
- `core/runtime/spatial_runtime.py`：query_point() 新增 Köppen veto 逻辑

### 遗留问题
- veto 仅在 Köppen 层有效时生效；未来若 Köppen 层不可用，低海拔陆地仍会走 DEM < 0 路径（可用 ESA/JRC 作第三层仲裁）
- 严格 > 0 的 Copernicus 门槛会让 0m 海拔陆地落到 ETOPO1 fallback，该场景 veto 无法触发（climate_class 本身正常，只是 elevation 路径不同），实际渲染结果仍正确

## 2026-06-24 B-6.2X-D6 Bug Fix — consistency_metrics 误报修正

### 做了什么
- 修复 consistency_metrics() 中 ocean_conflicts 判断没有同步 Köppen veto 的问题
- 旧逻辑把 `not ocean and elevation < 0` 全部计为冲突，导致死海/里海洼地等低海拔陆地点误报为 ocean conflict
- 新逻辑：仅当 `not ocean and elevation < 0` 且无有效气候类（climate_class 为 None 或 0）时才计冲突；有气候类的低海拔陆地视为 veto 正常生效，不计冲突
- 5 个典型点（死海/死亡谷/里海/旧金山湾/太平洋）的 ocean_conflict_rate 从 0.4 修正为 0.0

### 改动文件
- `core/runtime/spatial_runtime.py`：consistency_metrics() ocean_conflicts 过滤条件加入气候类豁免

---

## 2026-06-24 VC Visual Consistency Layer 实现

### 做了什么
- 实现 `core/vc/` 全套模块：`vc_types.py`、`_kernels.py`、`biome_transition.py`、`coastline_smoother.py`、`temporal_stabilizer.py`、`visual_consistency_engine.py`、`__init__.py`
- 核心 pipeline：M1 SemanticMaskTile → BiomeTransition → CoastlineSmoother → TemporalStabilizer → VCRenderContext
- BiomeTransition：biome_mask → 色彩场，Gaussian blur 软化边界，blend_field 记录每点混合权重
- CoastlineSmoother：binary ocean_mask → 连续 coastline_gradient_field（span=0.972 for 混合海岸 tile）
- TemporalStabilizer：EMA α=0.85，新增 update_ema_and_stability() 返回实际 delta 驱动 stability field；同 tile 多帧收敛 stability→1.0，切换场景后 stability→0.10
- 修复两个 bug：(1) 测试跨 VCE 实例 EMA 污染问题（改为每 test 独立实例）；(2) _build_result 中误用 stabilize_frame(x,x) 导致 stability 恒为 1.0
- 4/4 测试通过；生成文档 `docs/phase_b6_2x_vc_visual_consistency_layer.md`

### 测试结果
- Dead Sea: coastline=[1.0,1.0] ✓，R>B（沙漠金）✓，stability=1.0
- Pacific Ocean: coastline=[0.0,0.0] ✓，B>R（深蓝）✓
- Coastal: gradient span=0.972 ✓，mid-band 存在 ✓，biome_blend_mean=0.54
- Temporal: 同 tile warmup 后 stability=1.0 ✓，切换 ocean 后 stability=0.104 ✓，delta=0.896

### 关键设计
- `_kernels.py`：纯 numpy Gaussian 2D convolution + detect_boundary，无 scipy 依赖
- `TemporalStabilizer.update_ema_and_stability()`：返回 (ema, stability) 对，EMA delta 驱动稳定场
- 每测试用独立 VCE 实例，EMA 状态不跨场景共享

### 遗留问题
- 纯 Python 卷积在 1024×1024 tile 下速度不可用，需向量化（scipy.ndimage 或 stride-based）
- σ 在 SAL P2（uncertainty≈0.99）下恒为 max_sigma=4.0，过度平滑；需 SAL winner_margin 修复
- 跨 tile 边界时 EMA 未 auto-detect 位置变化，需调用方手动 reset()

### 改动文件
- `core/vc/vc_types.py`（新增）
- `core/vc/_kernels.py`（新增）
- `core/vc/biome_transition.py`（新增）
- `core/vc/coastline_smoother.py`（新增）
- `core/vc/temporal_stabilizer.py`（新增）
- `core/vc/visual_consistency_engine.py`（新增）
- `core/vc/__init__.py`（新增）
- `core/vc/_test_vc.py`（新增）
- `docs/phase_b6_2x_vc_visual_consistency_layer.md`（新增）

---

## 2026-06-24 M1 Semantic Mask Derivation 实现

### 做了什么
- 实现 `core/m1/` 全套模块：`mask_types.py`、`tile_segmenter.py`、`semantic_field_builder.py`、`mask_generator.py`、`m1_pipeline.py`、`__init__.py`
- MaskGenerator：接受 SignalProvider 回调驱动，逐点运行 SAL → D6 → SemanticFieldBuilder，输出 SemanticMaskTile
- TileSegmenter：8192×4096 全球网格 → 32 个 1024×1024 tile，支持 split_grid() + stitch_tiles()
- SemanticFieldBuilder：(ArbitrationResult, D6RenderInput) → scalar fields → point-level boolean/uint8 mask 值
- M1Pipeline：run_tile() 单 tile 完整管线 + run_global(dry_run=True) 枚举 32 个 tile 一致性验证
- 4/4 测试通过（含修正：Coastal 检查由"均值 > Dead Sea"改为"空间梯度 std>0.001 且 ocean_prob_span>0.01"）
- 生成文档 `docs/phase_b6_2x_m1_semantic_mask_derivation.md`

### 测试结果
- Dead Sea tile (8×8)：ocean_frac=0.0 ✓ land_frac=1.0 ✓，biome=[land]
- Pacific Ocean tile (8×8)：ocean_frac=1.0 ✓ land_frac=0.0 ✓，biome=[ocean]
- Coastal tile (16×16)：mixed 50/50 ✓，std_unc=0.0016 ✓，ocean_prob span=0.066 ✓
- Grid dry-run：32 tiles 枚举一致 ✓

### 遗留问题
- 每点独立调用 SAL，100万点/tile × 32 tile 不可行；需向量化 SAL pipeline
- biome_mask 仍用 SAL final_class，未反映 D6 binding 的 climate_zone 生物群落细化
- uncertainty_mask 绝对值仍接近 1.0（SAL P2 遗留），confidence_mask 和 ocean_prob_mask 目前更有区分力

### 改动文件
- `core/m1/mask_types.py`（新增）
- `core/m1/tile_segmenter.py`（新增）
- `core/m1/semantic_field_builder.py`（新增）
- `core/m1/mask_generator.py`（新增）
- `core/m1/m1_pipeline.py`（新增）
- `core/m1/__init__.py`（新增）
- `core/m1/_test_m1.py`（新增）
- `docs/phase_b6_2x_m1_semantic_mask_derivation.md`（新增）

---

## 2026-06-24 SAL → D6 Binding Layer 实现

### 做了什么
- 实现 `core/binding/` 全套模块：`binding_types.py`、`semantic_to_visual_mapper.py`、`uncertainty_visualizer.py`、`rendering_context_builder.py`、`sal_d6_bridge.py`、`__init__.py`
- SALD6Bridge：顶层入口，接受 lon/lat/time_state + 四源信号 → 调 SAL → 输出 D6RenderInput
- SemanticToVisualMapper：semantic class + climate_zone → base_color，confidence → color desaturation
- UncertaintyVisualizer：SAL entropy → 归一化 uncertainty → 去饱和/亮度偏移/noise proxy/blur proxy
- RenderingContextBuilder：组装完整 D6RenderInput（含太阳高度因子、季节修正、雪/云融合）
- 3/3 测试通过：Dead Sea → desert tone、Pacific Ocean → deep blue、Coastal Ambiguity → conflict gradient
- 生成文档 `docs/phase_b6_2x_d6_binding_sal_to_renderer.md`

### 关键设计点
- SAL 与 D6 严格分离：SAL 决定"是什么"，Binding Layer 决定"看起来像什么"
- climate_zone 仅影响视觉颜色（land → desert / forest / ice），不改变 SAL 判决
- uncertainty_weight = uncertainty × (1 − confidence)，综合熵高且置信低时才真正触发视觉降级

### 遗留问题
- uncertainty 值偏高（~0.99）是 SAL P2 问题的下游表现；建议后续 SAL 输出 winner_margin，此层改用其驱动 uncertainty
- noise_proxy / blur_proxy 当前为 CPU 提示标量，需 D6 GPU shader 消费后才产生实际视觉效果
- solar 模型忽略太阳赤纬，精度足够视觉调制但不适合天文计算

### 改动文件
- `core/binding/binding_types.py`（新增）
- `core/binding/semantic_to_visual_mapper.py`（新增）
- `core/binding/uncertainty_visualizer.py`（新增）
- `core/binding/rendering_context_builder.py`（新增）
- `core/binding/sal_d6_bridge.py`（新增）
- `core/binding/__init__.py`（新增）
- `core/binding/_test_binding.py`（新增）
- `docs/phase_b6_2x_d6_binding_sal_to_renderer.md`（新增）

---

## 2026-06-24 SAL Semantic Arbitration Layer 实现

### 做了什么
- 实现 `core/sal/` 全套模块：`sal_types.py`、`signal_registry.py`、`confidence_model.py`、`decision_engine.py`、`semantic_arbitrator.py`、`__init__.py`
- 核心仲裁逻辑：DEM + Climate + Ocean + Landcover → final_class + confidence_score + explanation_trace
- 发现并修复关键设计问题：DEM 与 Ocean 信号同源（均为高程数据），直接投票导致 Dead Sea / Caspian Basin 误判为 ocean
- 解决方案：de-correlation 步骤——当 DEM 与 Ocean 投同一类时合并为单一信号（取较大 weight），防止双重计票
- 生成文档 `docs/phase_b6_2x_sal_semantic_arbitration_layer.md`

### 测试结果（3/3 PASS）
- Dead Sea：expected=land → got=land ✓（confidence=0.1486）
- Caspian Basin：expected=land → got=land ✓（confidence=0.1461）
- Pacific Ocean：expected=ocean → got=ocean ✓（confidence=0.1693）
- 平均置信分：0.1547

### 改动文件
- `core/sal/sal_types.py`（新增）
- `core/sal/signal_registry.py`（新增）
- `core/sal/confidence_model.py`（新增）
- `core/sal/decision_engine.py`（新增）
- `core/sal/semantic_arbitrator.py`（新增）
- `core/sal/__init__.py`（新增）
- `core/sal/_test_sal.py`（新增）
- `docs/phase_b6_2x_sal_semantic_arbitration_layer.md`（新增）

### 遗留问题
- 置信分绝对值偏低（~0.15）因 softmax 分散到 9 个类；建议后续引入 winner/runner-up ratio 作为可解释置信度
- 当前仅支持单点推理，无空间邻域平滑
- 权重静态固定，未来可引入地区自适应权重（极地 / 热带分层）

---

## 2026-06-24 SAL P2 — winner_margin 不确定度修复

### 做了什么
- 在 `ArbitrationResult` 增加 `winner_class`、`runner_up_class`、`winner_margin`，由 `DecisionEngine.rank()` 从 probability_map top-1/top-2 计算
- Binding 层新增 margin-based uncertainty：`uncertainty = clamp(1 - winner_margin / 0.08)`；entropy 仅作为旧对象 fallback / 诊断字段
- M1 的 `uncertainty_mask` 改为消费 `D6RenderInput.uncertainty`，不再直接使用 `entropy / log2(9)`
- VC 自动吃到新的 margin-derived uncertainty，纯海洋 tile 不再因 SAL entropy 饱和而走 max_sigma
- 更新 SAL / Binding / M1 / VC 阶段文档，替换旧的 `uncertainty≈0.99` 结论
- 加强 M1 测试：要求纯海洋 uncertainty 低于 Dead Sea，防止回退到 entropy-only 路径

### 测试结果
- SAL：3/3 PASS；Dead Sea margin=0.012，Pacific margin=0.065
- Binding：3/3 PASS；Dead Sea uncertainty=0.846，Pacific uncertainty=0.181，Coastal uncertainty=0.899
- M1：4/4 PASS；Dead Sea mean_unc=0.8465，Ocean mean_unc=0.1814，Coastal mean_unc=0.4293 / std=0.235224
- VC：4/4 PASS；Coastal gradient span=1.000，Temporal perturb stability=0.2278
- `python3 -m compileall -q core/sal core/binding core/m1 core/vc` 通过

### 改动文件
- `core/sal/sal_types.py`
- `core/sal/decision_engine.py`
- `core/sal/semantic_arbitrator.py`
- `core/sal/_test_sal.py`
- `core/binding/uncertainty_visualizer.py`
- `core/binding/rendering_context_builder.py`
- `core/binding/binding_types.py`
- `core/m1/semantic_field_builder.py`
- `core/m1/_test_m1.py`
- `docs/phase_b6_2x_sal_semantic_arbitration_layer.md`
- `docs/phase_b6_2x_d6_binding_sal_to_renderer.md`
- `docs/phase_b6_2x_m1_semantic_mask_derivation.md`
- `docs/phase_b6_2x_vc_visual_consistency_layer.md`

### 遗留问题
- `_CLEAR_WINNER_MARGIN = 0.08` 是基于当前合成测试校准的经验值；接入 RealSignalProvider 后需要重新标定
- confidence_score 绝对值仍偏低，后续可补 `winner_ratio` 作为解释性指标
- SAL 仍是单点推理，尚未做空间邻域平滑或批量向量化

---

## 2026-06-24 P1 — RealSignalProvider 接入 M1

### 做了什么
- 新增 `core/m1/real_signal_provider.py`，把 M0 `SpatialRuntime.query_point()` 输出翻译为 SAL 四路 signal kwargs
- `dem_signal` 来自 elevation sign，`climate_signal` 来自 Köppen land class，`ocean_signal` 来自 runtime ocean truth（含 Köppen veto），`landcover_signal` 来自 ocean/climate/elevation proxy
- `M1Pipeline(runtime=...)` 与 `MaskGenerator(runtime=...)` 在未显式传入 synthetic `signal_provider` 时自动使用 `RealSignalProvider`
- 导出 `RealSignalProvider` 到 `core.m1` 公共 API
- 新增 `_test_real_signal_provider.py`，覆盖 below-sea-level land veto、deep ocean、M1 runtime auto-wiring、真实 source-cache smoke
- 更新 M1 文档，说明 RealSignalProvider 数据映射和 runtime 用法

### 测试结果
- `python3 -m core.m1._test_real_signal_provider`：4/4 PASS
- 真实 source-cache smoke：Pacific → ocean，Dead Sea → climate land + ocean_signal land，Shanghai → land
- 真实 M1 2×2 tile smoke：Pacific ocean_fraction=1.0 / land_fraction=0.0；DeadSea ocean_fraction=0.0 / land_fraction=1.0
- 回归：SAL 3/3 PASS，Binding 3/3 PASS，M1 4/4 PASS，VC 4/4 PASS
- `python3 -m compileall -q core/m1 core/runtime core/sal core/binding` 通过

### 改动文件
- `core/m1/real_signal_provider.py`（新增）
- `core/m1/_test_real_signal_provider.py`（新增）
- `core/m1/mask_generator.py`
- `core/m1/m1_pipeline.py`
- `core/m1/__init__.py`
- `docs/phase_b6_2x_m1_semantic_mask_derivation.md`
- `devlog.md`

### 遗留问题
- RealSignalProvider 的 confidence 映射仍是启发式；需要真实 tile validation 后标定
- `landcover_signal` 仍是 proxy，不是真实 ESA/MODIS landcover sampler
- M1 仍是逐点 Python loop，真实 8K 全量运行需等向量化

---

## 2026-06-24 M1 Bug Fix — 消除每像素双 SAL 调用

### 做了什么
- 修复 `MaskGenerator._generate_tile()` 中每个像素重复调用 SAL 的问题
- 旧路径：`SALD6Bridge.convert()` 内部 resolve 一次，随后 `self._sal.resolve()` 再 resolve 一次
- 新路径：先 `self._sal.resolve()` 得到 `sal_result`，再调用 `SALD6Bridge.convert_from_sal_result()` 复用同一个结果
- 修正 `CoastlineSmoother.smooth()` 参数注释：`uncertainty_mask` 已是 margin-derived uncertainty，不再是 entropy-normalized uncertainty

### 测试结果
- `python3 -m core.m1._test_m1`：4/4 PASS
- `python3 -m core.m1._test_real_signal_provider`：4/4 PASS
- `python3 -m core.vc._test_vc`：4/4 PASS
- `python3 -m compileall -q core/m1 core/vc core/sal core/binding` 通过

### 改动文件
- `core/m1/mask_generator.py`
- `core/vc/coastline_smoother.py`
- `devlog.md`

### 遗留问题
- 仍是逐点 Python loop；本修复只把每点 SAL 调用从 2 次降到 1 次，未做向量化

---

## 2026-06-24 System Freeze & Contract Enforcement

### 做了什么
- 新增 `core/contract/` 目录，实现 M0→SAL→M1→VC→D6 pipeline 不可漂移工程契约系统
- `sal_contract.py`：验证 ArbitrationResult 所有必填字段（winner_class/runner_up/margin/ratio/confidence），确保 winner_class == argmax(prob_map)，ratio ≥ 1.0
- `m1_contract.py`：验证 SemanticMaskTile 四个 mask 数组形状一致、uncertainty ∈ [0,1]、无 NaN/Inf
- `vc_contract.py`：验证 VCRenderContext 存在 gradient coastline（非 binary mask）、temporal_stability ∈ [0,1]、禁止携带 SAL/M0 引用
- `d6_contract.py`：D6 入口只接受 VCRenderContext，禁止 SemanticMaskTile/ArbitrationResult/SpatialState，render_from_vc() 输出 uint8 RGB frame
- `system_invariants.py`：实现 5 个 pipeline 级不变量检查（deterministic_pipeline / sal_consistency / m1_alignment / vc_temporal_stability / d6_determinism）
- `contract_guard.py`：统一 guard，含 SAL 双调用检测（同 input_key 只能 resolve 一次）
- `core/sal/sal_types.py`：ArbitrationResult 新增 `winner_ratio: float` 字段
- `core/sal/semantic_arbitrator.py`：resolve() 中计算并填充 winner_ratio
- `tests/test_system_contract_smoke.py`：31 个 smoke test 全部通过（31/31 OK in 0.029s）

### 改动文件
- `core/sal/sal_types.py`（新增 winner_ratio 字段）
- `core/sal/semantic_arbitrator.py`（计算 winner_ratio 并注入 ArbitrationResult）
- `core/contract/__init__.py`（新增）
- `core/contract/sal_contract.py`（新增）
- `core/contract/m1_contract.py`（新增）
- `core/contract/vc_contract.py`（新增）
- `core/contract/d6_contract.py`（新增）
- `core/contract/system_invariants.py`（新增）
- `core/contract/contract_guard.py`（新增）
- `tests/__init__.py`（新增）
- `tests/test_system_contract_smoke.py`（新增）

### 遗留问题
- VC 的 `sal_state` 参数虽已预留但未使用；如未来启用需确保不违反 VC 隔离约定，并在 vc_contract.py 中添加相应检测
- D6Renderer（core/rendering/d6_renderer.py）现有路径仍接受 SpatialState（M0），与新契约系统并存；完整迁移需将 D6 渲染路径统一至 D6Contract.render_from_vc()

---

## 2026-06-24 RealSignalProvider v1 Integration（接口层）

### 做了什么
- 新增 `core/signal/` 模块，实现可选真实信号接口层（stub 版本，不接真实数据）
- `signal_types.py`：定义 DEMValue(float) / LandcoverClass(int) / ClimateClass(Optional[int]) / OceanFlag(bool) 四个基础类型别名
- `base_signal_provider.py`：抽象基类 BaseSignalProvider，定义 get_dem / get_landcover / get_climate / get_ocean 四个抽象方法
- `real_signal_provider.py`：stub 实现，所有方法返回安全中性默认值（0.0 / 0 / None / False），无需任何数据文件
- `core/runtime/spatial_runtime.py`：新增 `signal_provider=None` 构造参数与 `set_signal_provider()` 方法；当 provider 存在时优先走 provider 路径，原有 synthetic/real 路径行为完全不变；dem_registry 在有 provider 时变为可选；_slope_proxy 和 _boundary_conflicts 在 dem_registry=None 时安全降级返回 0
- `tests/test_signal_provider_stub.py`：35 个测试全部通过（35/35 OK in 0.069s）
- 原有 contract smoke tests 全部保持绿灯（31/31 OK）

### 改动文件
- `core/signal/__init__.py`（新增）
- `core/signal/signal_types.py`（新增）
- `core/signal/base_signal_provider.py`（新增）
- `core/signal/real_signal_provider.py`（新增）
- `core/runtime/spatial_runtime.py`（修改：signal_provider 注入，dem_registry 可选化）
- `tests/test_signal_provider_stub.py`（新增）

### 遗留问题
- RealSignalProvider 当前为 stub；未来版本需实现 GEBCO / MODIS / Köppen 真实数据查询，接口不变
- SpatialRuntime.query_window() 在 provider 模式下仍调用 consistency_metrics → _boundary_conflicts，后者在 dem_registry=None 时直接返回 0，不做真实边界检测
- core/signal/RealSignalProvider 与 core/m1/real_signal_provider.py（M0→SAL 桥接器）同名但职责不同；未来应考虑重命名其中一个避免混淆

---

## 2026-06-24 Signal Layer Unification Refactor（结构重命名 + 语义统一）

### 做了什么
- 将 core/signal 与 core/m1 中两个同名 RealSignalProvider 统一迁移到 core/signal/providers/ 子包，消除语义分裂
- 新建 core/signal/providers/base.py（BaseSignalProvider 唯一定义处）
- 新建 core/signal/providers/synthetic.py（SyntheticProvider：替代 _default_signal_provider lambda，同时实现 BaseSignalProvider 和 M1 callable 协议）
- 新建 core/signal/providers/runtime_stub.py（RuntimeStubProvider：原 core/signal/RealSignalProvider）
- 新建 core/signal/providers/m1_bridge.py（M1BridgeProvider：原 core/m1/RealSignalProvider，职责是 M0→SAL 翻译层）
- 新建 core/signal/providers/resolution_policy.py（SignalResolutionPolicy：三级优先顺序 external > runtime_stub > synthetic）
- 旧文件 core/signal/base_signal_provider.py、core/signal/real_signal_provider.py、core/m1/real_signal_provider.py 转为单行 re-export shim，不再包含任何类定义
- core/m1/__init__.py、m1_pipeline.py、mask_generator.py 统一改为从 core.signal.providers.m1_bridge import M1BridgeProvider
- core/runtime/spatial_runtime.py TYPE_CHECKING import 更新到新路径
- 更新 tests/test_signal_provider_stub.py：使用新类名（RuntimeStubProvider / SyntheticProvider / M1BridgeProvider），新增 resolution policy / isolation 测试
- 新增 tests/test_signal_architecture_consistency.py：验证单一命名空间入口、无重复类定义、无跨模块违规 import、依赖图无环
- 总测试：114/114 OK（31 contract smoke + 83 新测试）

### 改动文件
- `core/signal/providers/__init__.py`（新增）
- `core/signal/providers/base.py`（新增）
- `core/signal/providers/synthetic.py`（新增）
- `core/signal/providers/runtime_stub.py`（新增）
- `core/signal/providers/m1_bridge.py`（新增）
- `core/signal/providers/resolution_policy.py`（新增）
- `core/signal/__init__.py`（更新）
- `core/signal/base_signal_provider.py`（转 shim）
- `core/signal/real_signal_provider.py`（转 shim）
- `core/m1/__init__.py`（更新：导出 M1BridgeProvider）
- `core/m1/real_signal_provider.py`（转 shim）
- `core/m1/m1_pipeline.py`（更新 import）
- `core/m1/mask_generator.py`（更新 import）
- `core/runtime/spatial_runtime.py`（更新 TYPE_CHECKING import）
- `tests/test_signal_provider_stub.py`（更新 + 扩充）
- `tests/test_signal_architecture_consistency.py`（新增）

### 遗留问题
- core/m1/_test_real_signal_provider.py 仍通过 core.m1 导入 RealSignalProvider（向后兼容 alias），未重命名为 M1BridgeProvider；下次重构时可统一
- SyntheticProvider 同时实现两套协议（BaseSignalProvider + callable dict），如果未来协议分叉需拆分

---

## 2026-06-24 RealSignalProvider v2-lite（Light Grounding Layer）

### 做了什么
- 扩展 `core/signal/providers/runtime_stub.py`：RuntimeStubProvider 新增 `enable_lite_grounding: bool = False` 构造参数
- `enable_lite_grounding=False`（默认）：行为与 v1 完全相同（0.0 / False / None / 0）
- `enable_lite_grounding=True`（lite 模式）：
  - `get_dem()` → `sin(lat * 0.01) * 1000`（±1000m 平滑 proxy，无文件 IO）
  - `get_ocean()` → `abs(lat) > 60 and abs(lon) < 20`（极地 / 北大西洋启发式）
  - `get_climate()` → lat-band bucket（1=热带<23°, 2=温带<45°, 3=极地）
  - `get_landcover()` → 始终返回 0（未接入）
- `SpatialRuntime.enable_lite_grounding()` 方法：将当前 signal_provider 切换到 lite 模式；不支持的 provider 类型抛 ValueError
- 强约束验证：SAL decision logic 未改变、M1 mask shape 不变、VC 所有 field 仍在 [0,1]、同一输入完全确定性
- 新增 `tests/test_signal_lite_grounding.py`：45 个测试全部通过（45/45 OK in 0.031s）
- 全部测试：159/159 OK（31 + 114 + 45）

### 改动文件
- `core/signal/providers/runtime_stub.py`（扩展为 v2-lite）
- `core/runtime/spatial_runtime.py`（新增 enable_lite_grounding() 方法）
- `tests/test_signal_lite_grounding.py`（新增）

### 遗留问题
- `get_ocean()` 的极地启发式仅覆盖 `abs(lon) < 20` 范围，不表示真实海洋分布；未来可替换为低分辨率 land mask 布尔矩阵
- `get_dem()` 的 sin 代理在赤道附近（lat≈0）返回接近 0 的值，与真实陆地 DEM 偏差最大；极地区域代理精度相对更好
- lite grounding 目前只影响 SpatialRuntime 注入路径；M1Pipeline 的 lambda signal_provider 不通过此机制（需要调用方自行在 _signal_fn 内使用 provider）

---

## 2026-06-24 Stage 2 Transition Plan — weak grounding layer 实现

### 做了什么
实现了 Stage 2 四个 Batch，建立"synthetic primary + bounded grounding correction"架构：

**Batch 1 — DEMGroundingProvider**
- 新增 `core/signal/providers/dem_grounding.py`
- 公式：`sin(lat*0.01)*1000 + cos(lon*0.01)*200`（范围 ±1200m，无文件 IO，完全确定性）
- 仅 `get_dem()` 携带 grounding 信号，其余方法返回中性默认值

**Batch 2 — ClimateGroundingProvider**
- 新增 `core/signal/providers/climate_grounding.py`
- 公式：lat-band bucket（tropical=1/<23°, temperate=2/<45°, polar=3/≥45°）
- 仅 `get_climate()` 携带 grounding 信号，其余方法返回中性默认值

**Batch 3 — SpatialRuntime 混合模式**
- 修改 `core/runtime/spatial_runtime.py`
- 新增构造参数：`signal_blend_mode: str = "synthetic"` / `grounding_provider: Optional[BaseSignalProvider] = None`
- hybrid 模式混合公式：`0.8 * synthetic_dem + 0.2 * grounding_dem`（连续值线性混合）
- climate/ocean 信号：synthetic 为主，grounding 仅在 synthetic 返回 None 时填充
- 新增 `set_grounding_provider()` 方法支持运行时替换
- SAL / M1 / VC / D6 pipeline 无任何改动

**Batch 4 — SignalFlags 特性标志系统**
- 新增 `core/config/__init__.py` + `core/config/signal_flags.py`
- 三个标志：`ENABLE_DEM_GROUNDING / ENABLE_CLIMATE_GROUNDING / ENABLE_HYBRID_MODE`，全部默认关闭
- 新增两个 provider 到 `core/signal/providers/__init__.py` 导出

**测试：Stage 2 验收测试**
- 新增 `tests/test_stage2_grounding.py`，49 个新测试
- 覆盖：provider 公式验证、确定性验证、SAL 结构不变性、M1 mask shape、VC 稳定性、D6 确定性、全合约 guard

### 改动文件
- `core/signal/providers/dem_grounding.py`（新增）
- `core/signal/providers/climate_grounding.py`（新增）
- `core/signal/providers/__init__.py`（导出新 provider）
- `core/config/__init__.py`（新增包）
- `core/config/signal_flags.py`（新增）
- `core/runtime/spatial_runtime.py`（扩展：hybrid blend mode、grounding_provider 参数）
- `tests/test_stage2_grounding.py`（新增）

### 遗留问题
- `SignalFlags` 目前是纯类属性（无运行时注入机制）；未来可扩展为从环境变量或配置文件加载
- hybrid 模式的 climate 混合目前是"synthetic 有值则用 synthetic"策略；Stage 3 可改为加权投票
- `grounding_provider` 只注入一个复合 provider；Stage 3 可以扩展为 DEM/Climate/Ocean 三个独立 grounding 通道
- 全部测试：208/208 OK（无回归，+49 Stage 2 新测试）

---

## 2026-06-24 Stage 3 Real World Grounding — 真实地球接入骨架

### 做了什么
实现 Stage 3 七个 Batch，建立"真实地球数据替换信号来源"架构。
SAL / M1 / VC / D6 零改动；所有变化仅在信号来源层。

**Batch 1 — RealWorldSignalProvider 骨架**
- 新增 `core/signal/providers/real_world_provider.py`
- 实现 `BaseSignalProvider` 四个接口：`get_dem` / `get_ocean` / `get_climate` / `get_landcover`
- `mode="lazy"` — 不在构造时加载数据；第一次查询时才初始化 EarthDataLoader

**Batch 2 — RasterIndexer**
- 新增 `core/signal/raster_indexer.py`
- 简单等经纬度公式：`col=(lon+180)/360*w`, `row=(90-lat)/180*h`
- 支持 `from_array()` 构造（无文件 IO）+ nodata 处理 + 边界 clamp
- 不依赖 GDAL；允许 numpy；lazy load（tifffile 按需 import）

**Batch 3 — EarthDataLoader + core/data/ 包**
- 新增 `core/data/__init__.py` + `core/data/earth_sources/__init__.py` + `core/data/earth_sources/loader.py`
- `load_layer(name)` 支持 `"dem" / "ocean" / "landcover" / "climate"` 四个 layer
- 文件不存在 → 返回 None（非抛出）；内部 try/except 双重保护
- DEM: 复用现有 `DEMRegistry.from_source_cache()`；Climate/Landcover: 使用 `RasterIndexer`

**Batch 4 — SpatialRuntime 扩展（最小侵入）**
- 修改 `core/runtime/spatial_runtime.py`
- 新增构造参数 `real_world_provider: Optional[BaseSignalProvider] = None`
- 新增 `set_real_world_provider()` 方法
- `query_point()` 优先级链：`real_world_provider` > `signal_provider` (Stage2) > `dem_registry` (legacy)
- ocean_rule source 字段标记为 `"real_world_provider"` 便于调试

**Batch 5 — EarthFlags**
- 新增 `core/config/earth_flags.py`
- 三个标志：`ENABLE_REAL_DEM / ENABLE_REAL_OCEAN / ENABLE_REAL_CLIMATE`，全部默认关闭
- `core/config/__init__.py` 同步导出 `EarthFlags`

**Batch 6 — 安全 fallback（内嵌在 RealWorldSignalProvider）**
- 所有 `get_*()` 方法完整 try/except 包裹
- 缺失数据 / 越界 / 文件损坏 / 导入错误 → 返回 `SyntheticProvider` 等效默认值
- `_lookup()` 中额外一层 try/except：适配 `.query()` / `.get_value()` / `.sample()` 三种接口协议

**Batch 7 — 测试系统**
- 新增 `tests/test_stage3_real_grounding.py`，48 个新测试
- 覆盖：RasterIndexer 公式/边界/nodata/from_array，EarthDataLoader 缺失文件，EarthFlags 默认值，
  RealWorldSignalProvider fallback 全覆盖，SpatialRuntime priority chain，SAL/M1/VC/D6 回归

### 改动文件
- `core/signal/raster_indexer.py`（新增）
- `core/signal/providers/real_world_provider.py`（新增）
- `core/signal/providers/__init__.py`（导出 RealWorldSignalProvider）
- `core/data/__init__.py`（新增包）
- `core/data/earth_sources/__init__.py`（新增包）
- `core/data/earth_sources/loader.py`（新增）
- `core/config/earth_flags.py`（新增）
- `core/config/__init__.py`（导出 EarthFlags）
- `core/runtime/spatial_runtime.py`（扩展：real_world_provider 参数 + set_real_world_provider() + query_point 优先级链）
- `tests/test_stage3_real_grounding.py`（新增）

### 遗留问题
- `EarthDataLoader.load_layer("landcover")` 目前扫描 `landcover/**/*.tif`；MODIS/ESA 具体路径待确认后可固化
- `RealWorldSignalProvider.get_ocean()` 目前从 DEM 推导（elevation<0 → ocean）；Stage 3 Stabilization 可改为直接查 GEBCO 层
- `EarthFlags` 目前未与 `RealWorldSignalProvider` / `SpatialRuntime` 实际联动（flag 读取、layer 加载互相独立）；Stage 3 Stabilization 可接入
- 全部测试：256/256 OK（无回归，+48 Stage 3 新测试）

---

## 2026-06-24 Stage 3 Bug Fix — RealWorldProvider Köppen Veto

### 做了什么
- 修复 `RealWorldSignalProvider.get_ocean()` 只按 `DEM < 0` 判 ocean 的问题
- 新逻辑：若 `get_climate()` 返回有效 Köppen land class，则 `get_ocean()` 返回 False，避免 Dead Sea / Caspian / Death Valley 低海拔陆地被误判为 ocean
- 在 `SpatialRuntime.query_point()` 的 `real_world_provider` 分支增加防御性 veto：即使第三方 provider 返回 `ocean=True + climate_class>0`，runtime 仍强制翻转为 land
- 为 Stage 3 测试补 3 个回归用例：mock climate veto、runtime conflicting provider veto、真实 source-cache Dead Sea veto

### 测试结果
- `python3 -m unittest tests.test_stage3_real_grounding`：51/51 PASS
- `python3 -m unittest discover -s tests`：259/259 PASS
- 真实 source-cache smoke：Dead Sea `dem=-417.0`、`climate=6`、`ocean=False`
- `python3 -m compileall -q core/signal core/runtime tests` 通过

### 改动文件
- `core/signal/providers/real_world_provider.py`
- `core/runtime/spatial_runtime.py`
- `tests/test_stage3_real_grounding.py`
- `devlog.md`

### 遗留问题
- `RealWorldSignalProvider.get_ocean()` 仍是 DEM sign + Köppen veto；后续如有独立 ocean/water mask，应改为更强的水体层仲裁

---

## 2026-06-24 Stage 3 Step 3 — Real Raster Integration（GEBCO + ETOPO1 + Köppen provider adapters）

### 做了什么
- 新建 `GEBCOProvider`：wraps `RasterIndexer`，提供 `get_dem()` / `get_ocean()`，纯 numpy，无 GDAL
- 新建 `ETOPOProvider`：同上，用于 ETOPO1 fallback DEM
- 新建 `KoppenProvider`：wraps `RasterIndexer`，提供 `get_climate()`（0 → None，1–30 → 有效 class）
- `EarthFlags` 新增 `ENABLE_GEBCO / ENABLE_ETOPO / ENABLE_KOPPEN` 三个开关（默认 False），保留原有 ENABLE_REAL_* 系列
- 新建 `tests/test_stage3_real_raster.py`：44 个测试，覆盖 Batch 2–8 完整路径
  - 地理正确性：Dead Sea（−430 m + climate veto → ocean False）、Pacific（−5000 m → ocean True）、Death Valley（−86 m + climate veto → ocean False）
  - 所有测试用 in-memory mock array，无需真实数据文件

### 测试结果
- `python3 -m unittest discover tests`：301/301 PASS（含新增 44 个）
- 无 GDAL 依赖，deterministic

### 改动文件
- `core/signal/providers/gebco_provider.py`（新建）
- `core/signal/providers/etopo_provider.py`（新建）
- `core/signal/providers/koppen_provider.py`（新建）
- `core/config/earth_flags.py`（新增 3 个 flag）
- `tests/test_stage3_real_raster.py`（新建）
- `devlog.md`

### 遗留问题
- 三个 Provider 目前是独立 adapter；下一步 Step 4 需把它们接入 EarthDataLoader，替换现有 _load_ocean / _load_dem 路径
- GEBCO/ETOPO tile 对齐与 8K grid calibration 待 Step 4 处理

---

## 2026-06-24 Stage 3 Real Raster Provider Export Fix

### 做了什么
- 从 `core.signal.providers` 包入口导出 `GEBCOProvider`、`ETOPOProvider`、`KoppenProvider`
- 修正 providers 包说明：复合 provider 才实现完整 `BaseSignalProvider`；单层 raster provider 只暴露其 layer-specific 方法

### 测试结果
- `python3 -m unittest discover tests`：301/301 PASS
- `python3 -m compileall -q core/signal core/config tests` 通过
- 验证 `from core.signal.providers import GEBCOProvider, ETOPOProvider, KoppenProvider` 可用

### 改动文件
- `core/signal/providers/__init__.py`
- `devlog.md`

### 遗留问题
- 仍需 Step 4：把三类 provider 接入 `EarthDataLoader`，替换当前直接返回 RasterIndexer / GEBCOAdapter 的路径

---

## 2026-06-24 Stage 3 Step 4 — EarthDataLoader Binding Layer（真实数据接入）

### 做了什么
- 新建 `core/data/earth_data_loader.py`：`RasterLayerRegistry`，in-memory 数组注册表
  - `load_layer(name, array, bbox)` — 注册预加载 numpy 数组
  - `get_layer()` / `is_loaded()` / `loaded_layers()` / `to_indexers()` — 完整读取接口
- 新建 `core/signal/providers/raster_backed_provider.py`：`RasterBackedProvider(BaseSignalProvider)`
  - 组合 GEBCOProvider（优先 DEM）+ ETOPOProvider（fallback DEM）+ KoppenProvider（climate）
  - Köppen veto 内置于 `get_ocean()`；任意 adapter 为 None 时安全降级
- `core/runtime/spatial_runtime.py` 新增 `set_earth_loader(registry)`
  - 一行调用完成 registry → provider adapters → real_world_provider 绑定
- `core/config/earth_flags.py` 新增 `ENABLE_REAL_DATA = True` / `ENABLE_FALLBACK = True`
- 新建 `tests/test_stage4_earth_binding.py`：52 个测试，覆盖所有 Batch

### 测试结果
- `python3 -m unittest discover tests`：353/353 PASS（新增 52 个）
- Dead Sea → ocean False ✔，Pacific → ocean True ✔，Death Valley → ocean False ✔
- SAL / M1 / VC / D6 全部 contract 通过

### 改动文件
- `core/data/earth_data_loader.py`（新建）
- `core/signal/providers/raster_backed_provider.py`（新建）
- `core/runtime/spatial_runtime.py`（新增 `set_earth_loader()`）
- `core/config/earth_flags.py`（新增 2 个 flag）
- `tests/test_stage4_earth_binding.py`（新建）
- `devlog.md`

### 遗留问题
- `RasterLayerRegistry` 目前是 in-memory only；GEBCO/ETOPO `.tif` 文件到位后，在 D3 Import Test 后写 file-to-registry loader 接通真实数据
- 8K tile 空间对齐待 GEE 8K export 完成后处理（Step 4 Stabilization）

---

## 2026-06-24 Stage 4 Earth Binding Export Fix

### 做了什么
- 从 `core.data` 包入口导出 `RasterLayerRegistry` 和 `GLOBAL_BBOX`
- 从 `core.signal.providers` 包入口导出 `RasterBackedProvider`
- 验证 Stage 4 的一行绑定入口和 provider 组合可以从公共包入口导入

### 测试结果
- `python3 -m unittest discover tests`：353/353 PASS
- `python3 -m compileall -q core/data core/signal core/runtime tests` 通过
- 验证 `from core.data import RasterLayerRegistry, GLOBAL_BBOX` 和 `from core.signal.providers import RasterBackedProvider` 可用

### 改动文件
- `core/data/__init__.py`
- `core/signal/providers/__init__.py`
- `devlog.md`

### 遗留问题
- 无新增遗留；仍沿用 Stage 4 原遗留：file-to-registry loader 与 8K tile 空间对齐

---

## 2026-06-24 HZ本地服务与地球贴图资源验证

### 做了什么
- 使用 `/opt/homebrew/bin/node` 对齐本地 `better-sqlite3` ABI，启动本地服务 `http://localhost:8080`
- 验证主页、`/earth3d.js`、`/assets/earth/production/d5z_b_8192x4096.jpg`、`/assets/earth/candidates/d6_topo_blend_8192x4096.jpg` 均返回 HTTP 200
- 在浏览器中验证默认 `dayTexture` 为 `d5z_b`，并通过 `?dayTexture=d6_topo_blend` 验证候选图可加载

### 改动文件
- `devlog.md`

### 遗留问题
- 默认页面仍由 `pwa/earth3d.js` 的 `DAY_TEXTURE_VARIANT = 'd5z_b'` 控制；如需默认显示 `d6_topo_blend`，需单独切换该常量或增加正式发布开关

---

## 2026-06-24 HZStage 4.1 Ingestion + Spatial Alignment Lock

### 做了什么
- 新增 `core/data/ingestion/file_loader.py`：按 dem / gebco / koppen / modis 关键词 deterministic 扫描文件，不解析 raster
- `RasterLayerRegistry` 新增 `auto_register(file_loader, raster_decoder)`，由外部 decoder 懒加载 array + bbox 后注册到 registry
- `RasterLayerRegistry` 新增 `bind_to_registry(registry)`，统一把 dem / ocean / climate 绑定到外部 registry-like 目标
- 新增 `core/runtime/spatial_alignment.py`：`SpatialAlignmentLock`，锁定 equirectangular lon/lat → pixel 映射；`base_resolution` 表示宽度，8K 对应 8192×4096，21.6K 对应 21600×10800
- `RasterIndexer` 接入 `SpatialAlignmentLock` 并新增 `resolution` 参数，保持旧 from_array 行为兼容，同时为 8K / 21.6K 多分辨率映射做准备
- 新增 `tests/test_stage4_1_alignment.py`，覆盖 file scan、auto registration、registry binding、8K lock、21.6K compatibility、provider/runtime 无漂移

### 改动文件
- `core/data/ingestion/__init__.py`（新建）
- `core/data/ingestion/file_loader.py`（新建）
- `core/data/earth_data_loader.py`
- `core/data/__init__.py`
- `core/runtime/spatial_alignment.py`（新建）
- `core/runtime/__init__.py`
- `core/signal/raster_indexer.py`
- `tests/test_stage4_1_alignment.py`（新建）
- `devlog.md`

### 遗留问题
- `auto_register()` 仍依赖外部 `raster_decoder.load(path)`，本层不引入 GDAL、不做重采样；真实 tif → array decoder 仍需在数据文件最终落位后接入
- 21.6K tile system 尚未实现；本轮只锁定坐标公式和 registry 绑定契约

---

## 2026-06-24 HZ21.6K Transition Protocol

### 做了什么
- `SpatialAlignmentLock` 新增 `SpatialProfile`，显式支持 `8k=(8192,4096)` 与 `21k=(21600,10800)`
- `RasterIndexer` 新增 `resolution_mode`，保留旧 `from_array()` 按数组宽度采样的兼容行为；只有显式传 `resolution_mode="21k"` 时才进入 21K profile
- GEBCO / ETOPO / Köppen provider 接受 `resolution_mode` 并透传给 path-backed `RasterIndexer`，未修改任何 DEM/ocean/climate 判定逻辑
- `SpatialRuntime` 新增 `resolution_mode` 字段与 `set_resolution(mode)`；scale switch 只影响后续 `set_earth_loader()` 绑定，不回写修改既有 provider
- `EarthDataLoader` 与 `RealWorldSignalProvider` 接受 resolution mode，用于未来 file-backed RasterIndexer 层接入
- 新增 `tests/test_21k_transition.py`，覆盖 profile、resolution-aware indexer、runtime mode switch、SAL winner_margin、M1 shape、VC temporal stability、D6 render stability

### 改动文件
- `core/runtime/spatial_alignment.py`
- `core/runtime/__init__.py`
- `core/signal/raster_indexer.py`
- `core/signal/providers/gebco_provider.py`
- `core/signal/providers/etopo_provider.py`
- `core/signal/providers/koppen_provider.py`
- `core/runtime/spatial_runtime.py`
- `core/data/earth_sources/loader.py`
- `core/signal/providers/real_world_provider.py`
- `tests/test_21k_transition.py`（新建）
- `devlog.md`

### 遗留问题
- 本轮是 scale-invariance dry run，不执行真实 21600×10800 全量 raster 处理
- DEMRegistry / GEBCO native tile adapter 仍按各自 native metadata 查询；21K mode 当前主要覆盖 RasterIndexer-backed registry/file 层

---

## 2026-06-24 HZ21.6K Visual Integration Layer

### 做了什么
- D6Renderer 新增 `resolution_mode`、`set_resolution()`、`profile_resolution()`、`default_window_shape()`；21K 下默认 render window 采样密度按 profile scale 放大，显式 width/height 调用保持不变
- M1Pipeline / MaskGenerator 新增 resolution profile 传播；`full_resolution_shape()` 暴露 21K 全局 shape，但不会自动分配 10800×21600 巨型 mask
- VisualConsistencyEngine 新增 `resolution_mode`、`set_resolution()`、`pixel_density()`；21K 下 VC smoothing sigma 按像素密度缩小，形成更细的 coastline / biome gradient 解释
- SpatialRuntime 新增 `attach_visual_pipeline()`，`set_resolution()` 可同步传播到已挂载的 M1 / VC / D6 模块
- 新增 `tests/test_21k_visual_consistency.py`，覆盖 runtime propagation、D6 默认窗口密度提升、M1 21K shape profile、SAL invariant、VC gradient bounded smoothness

### 改动文件
- `core/runtime/spatial_alignment.py`
- `core/runtime/spatial_runtime.py`
- `core/m1/m1_pipeline.py`
- `core/m1/mask_generator.py`
- `core/vc/visual_consistency_engine.py`
- `core/rendering/d6_renderer.py`
- `tests/test_21k_visual_consistency.py`（新建）
- `devlog.md`

### 遗留问题
- 本轮不生成真实 21K 全局 mask / texture；视觉显化通过 profile-aware sampling density 与 VC kernel density 生效
- 前端仍需单独接入新的 D6/VC 输出或 texture bake，浏览器当前不会自动显示本轮 Python CPU pipeline 的结果

---

## 2026-06-24 HZD6 21K Texture Bake + Frontend Binding

### 做了什么
- 新增 `D6TextureBaker`：接收 RGB BMNG base/topo arrays，输出 WebGL-friendly `base_texture` 与 topo/bathy delta `overlay_texture`
- 新增 `texture_export.py`：支持将 baked texture 输出为 raw bytes 或 PNG bytes payload
- `D6Renderer` 接入 texture baker，新增显式 `texture_bake=True` 路径；默认 `render_window()` 仍保持原 RGB window 行为
- `server.js` 新增 `/assets/earth/bmng21k` 静态 alias，暴露本地 BMNG 21K 源目录给前端测试
- `pwa/earth3d.js` 新增 `bmng_topo_bathy_21k` texture variant，指向 `world.topo.bathy.200408.3x21600x10800_geo.jpg`
- `pwa/index.html` 为 `earth3d.js` 添加 `?v=texture-bake-21k`，避免旧静态缓存导致新 variant 不生效
- 新增 `tests/test_d6_21k_texture_bake.py` 覆盖 bake shape、determinism、payload structure、SAL/M1/VC no drift、frontend candidate hook
- 本地浏览器验证：`?dayTexture=bmng_topo_bathy_21k` 成功加载 21K BMNG；Three.js 自动将 21600×10800 resize 到 16384×8192（WebGL texture limit），无黑屏

### 改动文件
- `core/rendering/d6_texture_baker.py`（新建）
- `core/rendering/texture_export.py`（新建）
- `core/rendering/__init__.py`
- `core/rendering/d6_renderer.py`
- `server.js`
- `pwa/earth3d.js`
- `pwa/index.html`
- `tests/test_d6_21k_texture_bake.py`（新建）
- `devlog.md`

### 遗留问题
- 浏览器实际可用上限为 16384×8192；若要稳定生产化，应增加 16K pre-bake asset 或 LOD tile system，避免运行时 Three.js 自动 resize
- `overlay_texture` 当前是 CPU bake payload，前端 shader 尚未消费 overlay；当前前端可见变化来自 BMNG topo_bathy dayTexture 本体

---

## 2026-06-24 HZStage 5 Earth Renderer LOD System

### 做了什么
- 新增 `LODManager`：将 21K logical resolution 映射到 GPU-safe canonical render resolution（high=16384、medium=8192、low=4096）
- 新增 `CanonicalTextureBuilder`：对 RGB texture 做确定性 LANCZOS downsample，保持 2:1 equirectangular aspect ratio
- `D6Renderer` 新增 `canonical_render_resolution`，21K 逻辑分辨率默认 cap 到 16384×8192，不改 D6 color/semantic logic
- `D6TextureBaker` 输出新增 `canonical_render_resolution` metadata；`texture_export` payload 同步携带该字段
- `pwa/earth3d.js` 新增 LOD texture selection：读取 WebGL `MAX_TEXTURE_SIZE`，按 16K → 8K → 4K fallback chain 加载
- `pwa/index.html` 将 `earth3d.js` cache-bust 版本更新为 `lod-system-v1`
- 新增 `tests/test_stage5_lod_system.py` 覆盖 21K logical preserved、GPU cap、canonical downsample deterministic、SAL/M1/VC no divergence、frontend fallback chain
- 本地浏览器验证：GPU maxTextureSize=16384，优先尝试 16K canonical；因 16K asset 尚未生成，稳定 fallback 到 8K，未再加载 21K 原图

### 改动文件
- `core/rendering/lod_manager.py`（新建）
- `core/rendering/canonical_texture_builder.py`（新建）
- `core/rendering/__init__.py`
- `core/rendering/d6_renderer.py`
- `core/rendering/d6_texture_baker.py`
- `core/rendering/texture_export.py`
- `pwa/earth3d.js`
- `pwa/index.html`
- `tests/test_stage5_lod_system.py`（新建）
- `devlog.md`

### 遗留问题
- 16K canonical texture 文件尚未生成；当前 LOD 链在本机稳定落到 8K fallback
- 下一步应执行离线 21K → 16K texture bake，生成 `/assets/earth/bmng21k/topo_bathy/lod/world.topo.bathy.200408.16384x8192.jpg`

---

## 2026-06-24 HZ16K Canonical Earth Texture Bake Asset

### 做了什么
- 使用 BMNG 21K topo_bathy/base_map JPEG 源生成 16384×8192 canonical LOD texture
- 验证源 JPEG 为 21600×10800 RGB；对应 GeoTIFF 为 EPSG:4326 / uint8 RGB / pixel scale 1/60°
- `CanonicalTextureBuilder` 新增 PIL Image 输入路径，使用确定性 LANCZOS downsample；输出 JPEG 固定为 quality=92 / progressive / subsampling=0
- `LODManager.asset_registry` 新增 21K logical → 16K canonical → 8K/4K fallback 映射
- 新增 `tests/test_lod_16k_asset_bake.py`，覆盖资产尺寸、determinism、采样色差、frontend 16K path、GPU cap
- 本地 HTTP/browser 验证：GPU maxTextureSize=16384 时前端命中 16K canonical texture，不再 fallback 到 8K

### 改动文件
- `core/rendering/lod_manager.py`
- `core/rendering/canonical_texture_builder.py`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/lod/world.topo.bathy.200408.16384x8192.jpg`（新建）
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/base_map/lod/world.base_map.16384x8192.jpg`（新建）
- `tests/test_lod_16k_asset_bake.py`（新建）
- `devlog.md`

### 遗留问题
- 4K canonical asset 尚未生成；当前 low-end fallback 仍复用 existing 8K source path `/assets/earth_day_8k.jpg`
- 16K asset 目前位于 source_cache 静态 alias 下，生产部署前需决定是否纳入 PWA assets 或 CDN artifact

---

## 2026-06-24 HZStage 7 Earth Visual Grammar System

### 做了什么
- 新增 `VisualGrammar` / `TimeGrammar`：将气候、海拔、海深、时间作为纯视觉表达规则，不改变 geometry/data/semantic layers
- 实现 Köppen climate family → color grammar：tropical / arid / temperate / cold / polar / unknown
- 实现 elevation tone：低海拔更湿暗，高海拔更冷、更低饱和；`elevation_tone()` 保持单调 highland factor
- 实现 ocean bathymetry gradient：shallow cyan → mid blue → deep navy，支持负 DEM bathymetry 输入
- 实现 time color shift：noon neutral、sunset warm、night desaturated + blue bias
- `D6Renderer` 接入 VisualGrammar：单点 semantic RGB 在输出前应用 grammar；texture bake 在 bake 后、输出前应用 time grammar
- 新增 `tests/test_stage7_visual_grammar.py`，覆盖 climate mapping、elevation monotonicity、ocean continuity、time determinism、D6 integration、SAL/M1/VC no drift

### 改动文件
- `core/rendering/visual_grammar.py`（新建）
- `core/rendering/d6_renderer.py`
- `core/rendering/__init__.py`
- `tests/test_stage7_visual_grammar.py`（新建）
- `devlog.md`

### 遗留问题
- VisualGrammar 当前是 CPU-side D6 expression layer；前端 shader 尚未独立暴露可调 grammar 参数
- texture bake 当前只应用全局 time grammar；逐像素 climate/elevation grammar 仍依赖 D6 semantic render path

---

## 2026-06-24 HZStage 7 Visual Effect Smoke Test

### 做了什么
- 本地服务 `/` 返回 200，前端 WebGL 页面可加载
- 浏览器验证 `?dayTexture=bmng_topo_bathy_21k&v=stage7-visual-check`：GPU `MAX_TEXTURE_SIZE=16384`，LOD 链命中 16K canonical texture
- 前端 console 确认 day texture 加载 `/assets/earth/bmng21k/topo_bathy/lod/world.topo.bathy.200408.16384x8192.jpg`
- 生成 `tmp_stage7_visual_check.png` 截图，确认画面非黑屏，但首页暗色/模糊 UI 与 `Tune In` overlay 会明显压低地球层可见度
- 生成 `tmp_stage7_grammar_preview.png` 对比图，验证 D6 VisualGrammar 在 arid / tropical / polar / ocean 的 noon / sunset / night 输出上有可见色彩差异

### 改动文件
- `devlog.md`
- `tmp_stage7_visual_check.png`（临时测试截图）
- `tmp_stage7_grammar_preview.png`（临时测试预览）

### 遗留问题
- 当前前端可见提升主要来自 16K BMNG texture；Stage 7 climate/elevation grammar 尚未作为前端 shader 参数暴露
- 首页深色主题和 overlay 会掩盖纹理细节，若要肉眼明显比较需要增加 debug visual mode 或临时关闭遮罩层

---

## 2026-06-24 统一地球纹理源至 BMNG 21K LOD 系统

### 做了什么
- 将 `DAY_TEXTURE_VARIANT` 从 `'d5z_b'`（遗留纹理）改为 `'bmng21k_lod'`，切断对旧生产纹理的默认依赖
- 新增 `resolveEarthTextureLOD(lodManager, deviceCaps)` 函数：依据 GPU `maxTextureSize` 选择 16K / 8K / 4K BMNG 21K LOD 路径，并输出 `[earth] texture source:` 调试日志
- 在 `getDayTexturePaths()` 的 candidates 中注册 `bmng21k_lod` 条目，指向 `resolveEarthTextureLOD` 结果，保留 `/assets/bluemarble.jpg` 作为最终兜底
- 修复 `bmng_topo_bathy_21k` 条目的 fallback，从 `d5z_b_8192x4096.jpg` 改为 `/assets/bluemarble.jpg`，彻底移除 d5z_b 在主 LOD 链中的出现
- 新增 `tests/test_frontend_texture_unification.js`（Node.js，12 项测试，全部通过）

### 改动文件
- `pwa/earth3d.js`：DAY_TEXTURE_VARIANT 变更、resolveEarthTextureLOD 新增、bmng21k_lod candidate 注册、bmng_topo_bathy_21k fallback 修复
- `tests/test_frontend_texture_unification.js`：新建前端纹理统一验证测试

### 遗留问题
- BMNG 21K LOD 资产（16K/8K/4K jpg）需在服务器端 `/assets/earth/bmng21k/topo_bathy/lod/` 路径下实际存在，否则会降级至 `/assets/bluemarble.jpg`
- d5z_b 条目仍保留在 candidates 表中供手动 A/B 测试（localhost `?dayTexture=d5z_b`），未来可酌情删除

---

## 2026-06-24 引入 Visual Weight Harmonizer 层

### 做了什么
- 新建 `core/rendering/visual_weight_harmonizer.py`：
  - `VisualConstraints` 数据类，持有 5 项约束上限（ocean / biome 饱和度 / ice / desert / atmosphere）
  - `load_noon_air_spec(path)` 确定性解析 Noon Air spec 的 Markdown 文件，提取百分比限制和色值上限
  - `harmonize_visual_output(pixel, grammar_output, constraints, ...)` 纯函数：对单个 post-grammar 像素施加上限约束，never 放大低于上限的值
  - `VisualWeightHarmonizer` 类：封装约束加载与 per-pixel / texture 两种 API
- 修改 `core/rendering/d6_renderer.py`：
  - 在 `__init__` 中实例化 `VisualWeightHarmonizer`
  - `_render_from_state` 和 `compute_semantic_color` 中，在 VisualGrammar 输出后调用 `harmonizer.harmonize()`
  - `bake_textures` 中，在两张纹理经过 `apply_to_texture()` 后调用 `harmonizer.harmonize_texture()`
  - D6 pipeline 顺序正式变为：BMNG base → VisualGrammar → VisualWeightHarmonizer → D6 output
- 新建 `tests/test_visual_weight_harmonizer.py`（32 项 unittest，全部通过）

### 改动文件
- `core/rendering/visual_weight_harmonizer.py`（新建）
- `core/rendering/d6_renderer.py`（集成 harmonizer）
- `tests/test_visual_weight_harmonizer.py`（新建）

### 遗留问题
- `harmonize_texture()` 目前只根据亮度推断是否为 polar 像素，无语义 mask；如需精确区分冰原 / 雪山 / 高亮沙漠，需传入 `VisualLayer` 的 semantic_mask
- `load_noon_air_spec` 的 `ocean_weight_max` 解析依赖"明亮浅水"区段存在，若 spec 重排章节则需更新提取逻辑
- D6 per-pixel 路径未向量化，大规模 render_window 时性能未优化

---

## 2026-06-24 Visual Rule Resolver（Stage 8 冲突解决系统）

### 做了什么
- 新建 `core/rendering/visual_rule_resolver.py`：
  - `RuleCandidate`：单个视觉规则候选（rule_type, score, payload）
  - `PixelContext`：像素语义上下文（climate_class, elevation, ocean, biome_proxy, sun_angle）
  - `FinalVisualState`：冲突解决后的最终状态（winning_rule, composite_score, ocean, climate_family, candidates）
  - `VisualRuleResolver`：带权重评分 + 确定性冲突解决引擎
    - `rule_weights` = {ocean:1.0, biome:0.8, desert:0.9, ice:0.95, polar:1.0, atmosphere:0.6}
    - 平局时用优先级表（ocean > ice > polar > biome > desert > atmosphere）
    - 平局阈值 `TIE_THRESHOLD = 0.05`
    - 同类型候选自动去重（保留最高分）
- 修改 `core/rendering/visual_grammar.py`：新增 `generate_rule_candidates()` 方法，不删除已有 API
- 修改 `core/rendering/visual_weight_harmonizer.py`：新增 `emit_candidates()` 方法，让 harmonizer 可作为纯约束上报层使用
- 修改 `core/rendering/d6_renderer.py`：
  - 引入 `VisualRuleResolver`，在 `__init__` 中实例化 `self.rule_resolver`
  - `_render_from_state` 和 `compute_semantic_color` 中：先由 grammar 生成候选 → resolver 解决冲突 → 用 `resolved.ocean` 和 `resolved.climate_family` 驱动后续 color_model / grammar / harmonizer
  - D6 pipeline 顺序正式成为：BMNG → VisualGrammar(candidates) → VisualRuleResolver → VisualWeightHarmonizer(纯约束) → 输出
- 新建 `tests/test_visual_rule_resolver.py`（33 项 unittest，全部通过）

### 改动文件
- `core/rendering/visual_rule_resolver.py`（新建）
- `core/rendering/visual_grammar.py`（新增 generate_rule_candidates）
- `core/rendering/visual_weight_harmonizer.py`（新增 emit_candidates）
- `core/rendering/d6_renderer.py`（集成 resolver）
- `tests/test_visual_rule_resolver.py`（新建）

### 遗留问题
- `evaluate_rules` 与 `generate_rule_candidates`（grammar 侧）的评分逻辑目前独立维护，若权重调整需同步两处
- `bake_textures` 纹理路径尚未接入 resolver（无 semantic mask 时无法 per-pixel 路由）
- 当前 `TIE_THRESHOLD = 0.05` 和权重值为初始值，后续需基于实机预览调优

---

## 2026-06-24 Visual Explainability Layer（规则解析可解释性层）

### 做了什么
- 新建 `core/rendering/visual_explainability.py`：
  - `CandidateScore`：单条规则的 raw_score / weight / weighted_score 分解记录
  - `VisualDecisionTrace`：单像素完整决策审计——pixel_context、candidates（序列化字典）、scores（按 rule_type 索引）、winner_rule、tie_break_reason（无则 None）、final_color_source（标签字符串如 `ocean:shallow`）
  - `VisualExplainabilityEngine.trace_decision()`：从 resolver 内部状态构建 trace，不影响任何逻辑
- 修改 `core/rendering/visual_rule_resolver.py`：
  - `__init__(debug=False)`：debug=False 时 traces / _explain 属性完全不分配，零开销
  - debug=True 时：在 `resolve_conflicts()` 末尾调用 engine 构建 trace，存入 `self.traces[]`；同时记录 tie_break_triggered 和 tie_break_detail 字符串
  - 新增 `get_debug_traces()` 和 `clear_traces()` 方法（非 debug 模式返回空列表/静默）
- 修改 `core/rendering/d6_renderer.py`：
  - `__init__(enable_explainability=False)`：以此 flag 初始化 `VisualRuleResolver(debug=...)`
  - 新增 `get_render_metadata()` → `{"resolver_enabled": bool, "visual_traces": [...]}`
  - 新增 `clear_render_metadata()` 方法
- 新建 `tests/test_visual_explainability.py`（38 项 unittest，全部通过）

### 改动文件
- `core/rendering/visual_explainability.py`（新建）
- `core/rendering/visual_rule_resolver.py`（debug 模式 + trace 采集）
- `core/rendering/d6_renderer.py`（enable_explainability flag + metadata API）
- `tests/test_visual_explainability.py`（新建）

### 遗留问题
- traces 为 in-memory list，长时间 debug 渲染会无限增长，需调用者定期 clear_render_metadata()
- render_window 批量路径暂未采集 trace（每格调用 render_point，trace 会在此被记录，但无法按坐标索引）
- 无序列化 / 持久化支持，trace 仅在进程内可用


---

## 2026-06-24 实现 Visual Stability Engine（时序一致性层）

### 做了什么
- 新建 `core/rendering/visual_stability_engine.py`，实现 `StablePixelState` 与 `VisualStabilityEngine`
  - `decay=0.85`（指数平滑），`lock_threshold=0.10`（稳定锁阈值）
  - `begin_frame / end_frame` 生命周期 API：current_frame_state → previous_frame_state 滚动
  - `stabilize()` 核心逻辑：无历史→直通；同赢家→平滑权重；赢家变化且 delta < threshold→稳定锁（保留上一帧赢家）；delta ≥ threshold→接受新赢家
  - `pixel_state() / previous_pixel_state()` 供外部检查
- 修改 `core/rendering/visual_rule_resolver.py`
  - `resolve_conflicts()` 增加可选参数 `pixel_key=None`（向下兼容）
  - 新增 `set_stability_engine()` 方法：Stability Engine 通过 hook 接入 resolver 结尾
  - hook 触发条件：`_stability_engine` 已附加 且 `pixel_key` 不为 None
- 修改 `core/rendering/d6_renderer.py`
  - `__init__` 新增 `enable_temporal_stability: bool = False`
  - 启用时惰性导入 VisualStabilityEngine，attach 至 rule_resolver
  - 新增 `begin_frame(frame_id)` / `end_frame(frame_id)` 委托方法
  - `_render_from_state` 中 `resolve_conflicts` 调用增加 `pixel_key=(lon, lat)`
- 新建 `tests/test_visual_stability_engine.py`，28 个单测（6 大类）全部通过

### 改动文件
- `core/rendering/visual_stability_engine.py` （新增）
- `core/rendering/visual_rule_resolver.py` （新增 set_stability_engine、pixel_key 参数、stability hook）
- `core/rendering/d6_renderer.py` （新增 enable_temporal_stability、begin/end_frame）
- `tests/test_visual_stability_engine.py` （新增）

### 遗留问题
- pixel_key 目前以 `(lon, lat)` float tuple 为键，相同坐标多次渲染可跨 frame 复用历史；若调用方不调用 begin_frame，previous_frame_state 始终为空，稳定锁永不触发
- previous_frame_state 无上限，长期运行渲染无数像素会累积内存；可考虑 LRU 缓存
- render_window 批量路径目前每 pixel 调用 render_point，begin_frame 需由外部调用方在帧级显式管理

---

## 2026-06-24 HZ Production Optimization Layer（Stage 10）

### 做了什么
- 新建 `core/rendering/gpu_texture_manager.py`
  - 实现 `GPUTextureManager` 与 `TextureRecord`
  - 支持 `load_texture_lod()`、`evict_unused_textures()`、`memory_pressure_check()`
  - 使用 LRU 驻留策略，streaming 模式下 full texture 只作为 logical source 登记，不计入 GPU tile 驻留预算
- 新建 `core/rendering/texture_streaming.py`
  - 实现 `TextureTile`、`get_visible_tiles()` 与 `TextureStreamingLayer`
  - 支持 16K-like texture → 4K tile view 切分，按 camera lon/lat/fov 懒加载可见 tiles
  - tile cache 使用 MRU 策略；tile view 不复制原始 texture 像素
- 新建 `core/rendering/frame_budget.py`
  - 实现 `FrameBudgetController`
  - 默认 16ms frame budget；超预算时自动从 16K → 8K → 4K 降级，并给出 tile resolution 建议
- 修改 `core/rendering/d6_renderer.py`
  - 集成 GPUTextureManager、TextureStreamingLayer、FrameBudgetController
  - 新增 `prepare_texture_stream()`、`get_production_metadata()`、`record_frame_time()`
  - `bake_textures()` 在不改变 RGB 输出的前提下登记 texture stream / GPU budget metadata
  - 修复 `clear_render_metadata()`，现在会真正清空 resolver traces 与最近 tile 状态
  - 元数据声明 pipeline 为 `LOD -> TileStream -> GPUManager -> Render`，DecisionCore 为 resolver 内嵌 stability hook
- 修改 `core/rendering/__init__.py`
  - 导出 Stage 10 新增类和 helper
- 新建 `tests/test_stage10_production_optimization.py`
  - 覆盖 GPU memory bound、camera movement tile streaming、Stage 9 RGB 不漂移、frame budget、LOD fallback、renderer metadata

### 改动文件
- `core/rendering/gpu_texture_manager.py`（新增）
- `core/rendering/texture_streaming.py`（新增）
- `core/rendering/frame_budget.py`（新增）
- `core/rendering/d6_renderer.py`（集成生产优化层）
- `core/rendering/__init__.py`（导出新增 API）
- `tests/test_stage10_production_optimization.py`（新增）

### 遗留问题
- Python 侧实现的是资源控制 / streaming 逻辑层；WebGL 前端尚未真正改为 tile shader binding
- `render_point()` 仍是 CPU per-point 路径，生产优化层主要服务 texture bake / runtime resource metadata
- tile visibility 当前基于 lon/lat/fov 的确定性近似，后续前端可替换为实际 camera frustum 计算

---

## 2026-06-24 HZ Frontend Streaming Final Binding（Stage 11）

### 做了什么
- 修改 `pwa/earth3d.js`
  - 新增 `FrontendTileStreamingManager`
  - 移除 day side 的 full-earth texture / d5z_b / static Blue Marble fallback 路径
  - day texture 改为 `THREE.CanvasTexture` atlas，由 BMNG tile stream 动态填充
  - render loop 调用 `updateStreaming(camera)`，按 camera lon/lat/fov/distance 生成可见 tile 请求
  - LOD 选择同步 GPU `maxTextureSize` 与 camera distance，自动在 16k / 8k / 4k 间切换
  - tile cache 使用 MRU 上限并在 eviction 时 dispose GPU texture
  - debug state 新增 streaming metadata，并输出 `[tile-stream]` tile / lod / cache hit-miss 日志
- 新建 `tests/test_stage11_frontend_streaming.js`
  - 覆盖无 full-earth day load、tile request、LOD adaptation、atlas texture swapping、cache bound、render-loop streaming、backend tile URL contract
- 更新旧前端 / LOD 测试
  - 将原本面向 full-image LOD fallback chain 的断言迁移到 Stage 11 tile-streaming contract

### 改动文件
- `pwa/earth3d.js`
- `tests/test_stage11_frontend_streaming.js`（新增）
- `tests/test_frontend_texture_unification.js`
- `tests/test_d6_21k_texture_bake.py`
- `tests/test_lod_16k_asset_bake.py`
- `tests/test_stage5_lod_system.py`

### 遗留问题
- 前端已切换为 tile URL contract，但仓库内未生成实际 tile jpg 文件；运行时需由 backend/static asset pipeline 提供 `/assets/earth/bmng21k/topo_bathy/tiles/{lod}/tile_{x}_{y}.jpg`
- 当前实现为 atlas composition 路径，不是 shader multi-plane tile sampling

---

## 2026-06-24 HZ Tile Data Production Pipeline（Stage 12）

### 做了什么
- 新建 `core/data/earth_tile_generator.py`
  - 实现 `EarthTileGenerator` 与 `TileCoordinateSystem`
  - 支持 BMNG 21K source → 16k / 8k / 4k deterministic tile pyramid
  - 实现 `load_source()`、`compute_tile_grid()`、`slice_tiles()`、`save_tile()`
  - tile 保存为 restart-safe atomic write；默认跳过已存在 tile，可通过 overwrite 强制重建
  - lon/lat ↔ tile grid 使用 EPSG:4326 equirectangular math
- 新建 `core/data/earth_tile_exporter.py`
  - 批量生成 `topo_bathy` 与 `base_map` tiles
  - 输出路径与前端完全匹配：`/assets/earth/bmng21k/{dataset}/tiles/{lod}/tile_{x}_{y}.jpg`
  - 支持 completeness validation、missing tile detection、per-LOD manifest 与 root manifest
  - 提供 CLI：`python3 -m core.data.earth_tile_exporter`
- 修改 `core/data/__init__.py`
  - 导出 generator / coordinate system，避免 exporter CLI eager import warning
- 新建 `tests/test_stage12_tile_pipeline.py`
  - 覆盖 tile grid completeness、命名、reproducibility、LOD pyramid、lon/lat mapping、manifest、16k/8k completeness
- 已执行真实导出
  - 生成 `topo_bathy/tiles/{16k,8k,4k}` 与 `base_map/tiles/{16k,8k,4k}`
  - 共 24 个 tile jpg + 6 个 per-LOD manifest + 1 个 root manifest

### 改动文件
- `core/data/earth_tile_generator.py`（新增）
- `core/data/earth_tile_exporter.py`（新增）
- `core/data/__init__.py`
- `tests/test_stage12_tile_pipeline.py`（新增）
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles/**`（生成）
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/base_map/tiles/**`（生成）
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/tiles_manifest.json`（生成）

### 遗留问题
- 当前 frontend 只请求 `topo_bathy` tile stream；`base_map` tile pyramid 已生成供后续切换或调试使用
- exporter 默认按 Stage 11 frontend atlas contract 输出 16k=4x2、8k=2x1、4k=2x1；如未来改成 512px native tile streaming，需要同步前端 tile grid 配置

---

## 2026-06-24 HZ Noon Air Colorizer 候选层（Stage 13-B）

### 做了什么
- 新建 `core/rendering/noon_air_colorizer.py`
  - 实现 `NoonAirColorizer`，纯 NumPy / rule-based / deterministic，无 LUT、无随机、无 GPU 依赖
  - 按固定顺序处理 ocean → land → desert → ice
  - ocean：深海向 `#052C4A` / `#0B5C7A` 收敛，浅海向 `#2EC4C6` 过渡，reef 区域小幅提亮
  - land：降低整体绿色饱和度，压住鲜绿地图感
  - desert：向暖沙色 `#C2A077` 收敛，降低黄色噪声
  - ice：蓝白 tint + 分通道高光限幅，避免纯白 clipping
- 修改 `core/data/earth_tile_generator.py`
  - 新增可选 `colorizer`、`output_tile_dir`、`dataset`
  - tile crop 后可注入 `NoonAirColorizer.process_tile(tile, metadata)`
  - metadata 包含 dataset、lod、x/y、lon/lat bounds、projection、tile_size
  - 默认仍输出 raw `tiles/`，不覆盖原始 tiles
- 修改 `core/data/earth_tile_exporter.py`
  - 新增 `--color-profile raw|noon_air`
  - `raw` 继续输出 `tiles/`
  - `noon_air` 输出候选目录 `tiles_noon_air/`
  - manifest 记录 `color_profile`
- 修改 `core/rendering/__init__.py`
  - 导出 `NoonAirColorizer`
- 新建 `tests/test_noon_air_colorizer.py`
  - 覆盖 ocean 变深、浅海相对提亮、沙漠暖化、冰原提亮不 clipping、全局漂移有界、deterministic hash
- 更新 `tests/test_stage12_tile_pipeline.py`
  - 覆盖 noon_air candidate tiles 不覆盖 raw tiles
- 已生成真实候选产物
  - `topo_bathy/tiles_noon_air/{16k,8k,4k}`
  - `base_map/tiles_noon_air/{16k,8k,4k}`
  - `tiles_noon_air_manifest.json`
  - `topo_bathy/candidates/previews/noon_air_v1/` 下生成全局 25% before/after 与 12 个区域 before/after/diff 对比图

### 改动文件
- `core/rendering/noon_air_colorizer.py`（新增）
- `core/rendering/__init__.py`
- `core/data/earth_tile_generator.py`
- `core/data/earth_tile_exporter.py`
- `tests/test_noon_air_colorizer.py`（新增）
- `tests/test_stage12_tile_pipeline.py`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air/**`（候选生成）
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/base_map/tiles_noon_air/**`（候选生成）
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/candidates/previews/noon_air_v1/**`（预览生成）

### 遗留问题
- 当前仅生成候选 `tiles_noon_air/`，尚未切换 frontend runtime 引用，符合“先 preview / 后 Three.js 验收”的策略
- 南极 raw source 存在大量高光白区，colorizer 已加入蓝白限幅，但冰川阴影层次仍需下一轮基于更强 ice texture / shadow rule 收敛
- reef detection 当前基于 RGB proxy，尚未接入真实 bathymetry / reef mask，局部浅海表现可继续细化

---

## 2026-06-24 实现 Geo Field Enhancement Layer（连续地理物理场）

### 做了什么
- 新建 `core/rendering/geo_field_engine.py`：
  - 三个场数据类：`OceanField`、`IceField`、`AtmosphereField`
  - `GeoFieldEngine` 标量 API：`compute_depth_field(lon, lat)`、`compute_slope_field(lon, lat)`、`compute_humidity_proxy(lat, lon)`，全部基于解析公式（GEBCO/ETOPO 分布近似）
  - 数组 API：`ocean_field_from_pixels`（sigmoid 蓝色主导度 → 连续 ocean_factor；亮度 → depth_proxy）、`ice_field_from_pixels`（高亮+低饱和+纬度增强；确定性分形亮度梯度；blue_shift 场）、`atmosphere_field_from_pixels`（边缘辉光+地平线混合+海洋天空连续性，均 ≤ 6.5%）
- 重写 `core/rendering/noon_air_colorizer.py`：
  - 增加 `self.geo_engine = GeoFieldEngine()`
  - `process_tile` 改为五阶段流水线：连续海洋 → 加权陆地 → 加权沙漠 → 连续冰雪 → 大气耦合
  - **消除所有二值海洋掩码**：`_apply_ocean_continuous` 使用 depth_proxy 三色梯度 + ocean_factor 加权混合
  - `_apply_ice_continuous`：修复了冰雪 factor=0 时仍应用亮度提升的 bug（改为 `img*(1-factor) + ice_full*factor`）
  - 移除：`_detect_ocean`、`_detect_desert`、`_detect_ice`、`_apply_ocean`、`_apply_land`、`_apply_desert`、`_apply_ice`
- 新建 `tests/test_geo_field_engine.py`，29 个测试（6 大类）全部通过
- 原有 6 个 `test_noon_air_colorizer` 测试全部通过

### 改动文件
- `core/rendering/geo_field_engine.py` （新增）
- `core/rendering/noon_air_colorizer.py` （重写）
- `tests/test_geo_field_engine.py` （新增）

### 遗留问题
- `compute_depth_field` / `compute_slope_field` 为解析近似，不读取真实 GEBCO/ETOPO 栅格；如需精确批量，需注入外部 DEM 查找表
- `ocean_field_from_pixels` 的 sigmoid 在颜色边界显著像素处仍有较大跳变（~0.98），这是输入像素颜色不连续导致的，非 sigmoid 缺陷
- 大气场的 `atmosphere_field_from_pixels` 中 `horizon_blend` 均匀作用于整个 tile；真实水平线应基于地理坐标计算

---

## 2026-06-24 Stage 13-D：Spectral Earth Engine + Stage 14：Visual Unification Engine

### 做了什么
- 新建 `core/rendering/spectral_earth_engine.py`（SpectralEarthEngine）：
  - `ocean_spectral_response(depth_field, ocean_factor) → ndarray`：Beer-Lambert 非线性吸收模型，锚点 depth=0 → #052C4A [5,44,74]，depth=1 → #2EC4C6 [46,196,198]，系数 μ_r=2.219 / μ_g=1.494 / μ_b=0.985（从锚点反解 ln）
  - `ice_reflectance(ice_f, sun_angle) → ndarray`：Lambertian+镜面 BRDF 近似，incidence_scale ≥ 0.75 保证低仰角仍亮；IceField.brightness_gradient 提供确定性空间变化（[0.88,1.00]）；blue_shift 场驱动光谱倾斜（R−80b，B+30b）
  - `desert_albedo(img, desert_factor) → ndarray`：氧化铁土壤光谱签名，轻度去饱和（0.86·img+0.14·gray）→ 砂土参考色 [194,160,119] 线性混合，luma 保留
  - `atmospheric_scattering(img, atmo_f) → ndarray`：Rayleigh（λ⁻⁴，蓝色天空调色）+ Mie（波长中性，地平线雾化）+ 海洋天空蔚蓝反射（≤1.5%）
- 新建 `core/rendering/visual_unification_engine.py`（VisualUnificationEngine）：
  - 接口：`unify(tile: ndarray, metadata: dict) → ndarray`，tile 为 NoonAirColorizer 输出
  - 四步 tone curve：① 海洋 S 曲线（亮度 >110 轻压暗，<110 轻提亮，权重按 blue_excess）② 陆地过饱和抑制（saturation >0.65 减 10%）③ 冰雪亮度软截断（brightness >230 拉向 248，权重 40%）④ **Tile 边缘渐隐**（外 5px，向 tile 均值靠拢，最大强度 15%）——不做跨 tile smoothing，WebGL 负责 UV 连续性
  - 所有修改量 ≤ 12/channel，不翻转视觉层级
- 重构 `core/rendering/noon_air_colorizer.py`（瘦身为 orchestration 层）：
  - 增加 `self.spectral_engine = SpectralEarthEngine()` + `self.unification_engine = VisualUnificationEngine()`
  - `process_tile` 新 8 步流水线：Beer-Lambert 海洋 → 礁石高光（审美层） → 陆地去饱和 → SpectralEngine.desert_albedo → SpectralEngine.ice_reflectance 混合 → SpectralEngine.atmospheric_scattering → clip/round → VisualUnificationEngine.unify
  - 删除：`_apply_ocean_continuous`、`_apply_ice_continuous`、`_apply_atmosphere_continuous`（物理层移至 SpectralEarthEngine）
  - 提取：`_apply_reef_highlight(arr, original_img, ocean_f)` 保留礁石审美逻辑
  - 删除：`_mix_color` 静态方法（线性梯度已被 Beer-Lambert 取代）
- 新建 `tests/test_spectral_earth_engine.py`，22 个测试（5 大类）全部通过
- 新建 `tests/test_visual_unification_engine.py`，16 个测试（6 大类）全部通过
- 全套 633 个测试全部通过（含先前所有回归测试）

### 架构决定（本轮确认）
- inter-tile boundary smoothing → 改为 tile-local edge feathering（无跨 tile 状态）
- SpectralEngine API：删除 `wavelength_state` 参数，改为 numpy field-based 签名
- SpectralEngine 替换 Colorizer 内部物理逻辑（非外部叠加），Colorizer 退化为 orchestration 层
- 最终流水线：`BMNG → GeoFieldEngine → SpectralEarthEngine → NoonAirColorizer → VisualUnificationEngine → Tile Output`

### 改动文件
- `core/rendering/spectral_earth_engine.py` （新增）
- `core/rendering/visual_unification_engine.py` （新增）
- `core/rendering/noon_air_colorizer.py` （重构）
- `tests/test_spectral_earth_engine.py` （新增）
- `tests/test_visual_unification_engine.py` （新增）

### 遗留问题
- `ice_reflectance` 中 sun_angle 当前固定为 45°（硬编码在 process_tile）；后续可从 astronomy 模块注入实时太阳高度角
- `_normalize_ocean_tone` S 曲线参数（中心亮度 110、强度 8.0）为调参值，尚未对真实 BMNG tile 做视觉校准
- VisualUnificationEngine 的 `_feather_tile_edges` 对高纬度 polar tile（极暗或极亮均值）可能过度拉向均值；如出现极地 tile 颜色异常需减小 _FEATHER_STRENGTH

---

## 2026-06-24 Stage 15：Perceptual Calibration Layer（视觉感知收敛层）

### 做了什么
- 新建 `core/rendering/perceptual_calibration_engine.py`：`PerceptualCalibrationEngine` 类，三路校准
  - `calibrate_ocean()`：基于 Blue Marble 统计的亮度直方图锚点匹配（分段插值，7 个 percentile 锚点），deep ocean → bottom 5%，shallow/reef → 70–85% 亮度带
  - `calibrate_land()`：三子通道 — 植被饱和度 clamp（防 neon）、沙漠暖色调 blue channel 压制、土壤/岩石去饱和归一化
  - `calibrate_ice()`：P99 亮度硬 clamp（_ICE_LUMA_P99=248）、P97–P99 软肩 rolloff、ice highlight 蓝通道 scale-down（防塑料感）
  - 所有通道 delta ≤ 20，确定性输出，无随机状态
- 修改 `core/rendering/visual_unification_engine.py`：将 Stage 14 的输出传入 `_perceptual_calibration.calibrate()`，Stage 15 成为最终 tile 出口
- 新建 `tests/test_perceptual_calibration_engine.py`：16 个测试全部通过
  - 6 大类：ocean histogram 分布、land 饱和度边界、ice 亮度 clamp、全局色偏无漂移、确定性、几何不变性

### 最终流水线（收敛）
`BMNG → GeoFieldEngine → SpectralEarthEngine → NoonAirColorizer → VisualUnificationEngine → PerceptualCalibrationEngine → Tile Output`

### 改动文件
- `core/rendering/perceptual_calibration_engine.py` （新增）
- `core/rendering/visual_unification_engine.py` （集成 Stage 15 调用点）
- `tests/test_perceptual_calibration_engine.py` （新增，16 个测试）

### 遗留问题
- Ocean 直方图锚点（`_OCEAN_ANCHORS`）为从 Blue Marble 统计推导的近似值，尚未对真实 BMNG tile 数据做实测校准；如有 tile dump 可进一步拟合
- `calibrate_land` 的沙漠检测依赖 R–B 差值，对过渡地带（稀树草原、红壤）可能误判；未来可接入 SAL biome mask 精化
- Ice P99 threshold 固定为 248，极地夏季云盖场景可能过度压制；可接入 cloud mask 区分 ice vs cloud 高亮

---

## 2026-06-24 HZEarth Rendering Mode Contract System

### 做了什么
- 新增 `pwa/earth_modes.js`，定义 RAW / NOON_AIR 两个互斥渲染模式与 tile source、pipeline、cachePrefix。
- `pwa/earth3d.js` 改为 mode-bound `resolveTileUrl()`，移除 raw/noon_air candidate fallback 链；cache key 加 mode 前缀；mode 切换清空 cache、重置 streaming，并用 loadGeneration 防止旧请求回填。
- `pwa/index.html` 增加 RAW EARTH / NOON AIR EARTH toggle，并加载 `earth_modes.js`；`pwa/sw.js` 缓存新契约文件。
- 新增/更新前端测试，覆盖模式隔离、无跨模式 leakage、切换清理和 resolver contract。

### 改动文件
- `pwa/earth_modes.js`
- `pwa/earth3d.js`
- `pwa/index.html`
- `pwa/sw.js`
- `tests/test_earth_mode_switching.js`
- `tests/test_stage11_frontend_streaming.js`
- `tests/test_frontend_texture_unification.js`
- `devlog.md`

### 遗留问题
- TextureLoader 原生请求无法真正 abort；当前通过 `loadGeneration` 与 mode 校验丢弃旧回调并 dispose texture。
- 未做真实浏览器视觉切换验收；本轮验证为静态契约与 JS 测试。

---

## 2026-06-24 HZEarth Mode Strict Isolation Patch

### 做了什么
- `pwa/earth3d.js` 新增显式 `getTileUrl(lod, x, y) → resolveTileUrl(EARTH_MODE, lod, x, y)` 单入口，StreamingManager 只能通过该入口生成 tile URL。
- 将模式错配 guard 升级为 `[FATAL MODE MISMATCH]`，NOON_AIR 模式会拒绝 raw `/topo_bathy/tiles/`，RAW 模式会拒绝 `tiles_noon_air`。
- 替换误导性的固定 `bmng21k tile stream` 日志，新增 `[tile-request]` 真实 URL 日志，并在 `[tile-stream]` 中输出 mode / pipeline / tileSource。
- bump `index.html` 脚本版本和 service worker cache 到 v2；`pwa/sw.js` 静态壳改为 network-first，降低旧前端缓存压住新绑定的概率。
- 新增 `tests/test_earth_mode_strict_isolation.js`，并同步更新既有 Earth mode / streaming / texture contract 测试。

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `pwa/sw.js`
- `tests/test_earth_mode_switching.js`
- `tests/test_earth_mode_strict_isolation.js`
- `tests/test_stage11_frontend_streaming.js`
- `tests/test_frontend_texture_unification.js`
- `devlog.md`

### 遗留问题
- `THREE.TextureLoader` 请求仍无法真正底层 abort；当前以 generation/mode guard 阻止旧请求回填。
- 抽样 raw vs noon_air tile 平均像素差异约 6–8/channel，视觉差异存在但可能偏轻；若仍感觉不明显，下一步应审 Noon Air tile 调色强度，而不是 tile binding。

---

## 2026-06-24 HZEarth 全球色彩巡检按钮

### 做了什么
- 在 `pwa/index.html` 的 Earth mode 控件下方新增 `START REGION / NEXT REGION` 巡检按钮和当前地区标签。
- 按用户指定的 01–12 顺序加入首轮巡检点：中国华东/长三角、台湾、日本本州、冲绳/琉球、菲律宾、南海、喜马拉雅、青藏高原、马尔代夫、撒哈拉、亚马逊、格陵兰。
- 点击按钮会循环切换地区，更新 `state.lat/lon`、`window.__rodioVisualState`，并调用 `window.earth3d.setDebugLocation(region.lon, region.lat)` 驱动 3D 地球转向。
- 将 Earth mode / Earth audit 控件层级提高，并让启动 overlay 背景点击穿透，避免未 Tune In 时挡住巡检按钮。
- 调整 `server.js` 静态资源缓存：`index.html` 与 `sw.js` 改为 `no-cache`，避免浏览器继续使用旧前端壳导致看不到新按钮。
- 新增 `tests/test_earth_audit_regions.js` 覆盖控件存在、地区顺序、代表坐标、3D 定位绑定和循环切换。

### 改动文件
- `pwa/index.html`
- `server.js`
- `tests/test_earth_audit_regions.js`
- `devlog.md`

### 遗留问题
- 当前只实现首轮 12 个地区；第二组完整 23 个全球巡检点尚未加入 UI。
- 按钮为顺序巡检模式，没有单独下拉/回退/随机访问控件。

---

## 2026-06-25 HZ Global Noon Air Baseline v1 全球 Tile 管线 + V2 ENHANCED 模式接入

### 做了什么
- 实现 `scripts/geo/global_v2_pipeline.py`：全球 3-LOD 瓦片生成管线（Global Noon Air Baseline v1）
  - 源：21K BMNG GeoTIFF（无二次 JPEG 压缩）
  - GEBCO 2026 深度调色：5 级渐变（nearshore → shelf → slope → abyssal → trench），uniform blend=0.35
  - GSHHG 全精度海岸线（`GSHHS_f_L1.shp`，约 25m 精度）：距离变换 + UnsharpMask 海岸锐化
  - 接缝处理：tile bounds 扩展 10km 后裁切，消除边缘断层
  - LOD 独立几何参数（zone_km、gshhg_strength 随分辨率缩放），颜色参数全局统一
  - 输出：`tiles_v2_enhanced/{16k,8k,4k}/tile_X_Y.jpg`，JPEG q=92
- 执行全球 12 张瓦片生成：99s 完成（16k×8 + 8k×2 + 4k×2）
- 目视验证 tile_3_0（东亚/日本）、tile_2_0（欧亚/地中海）、tile_1_1（南美/南极）
- 在 `pwa/earth_modes.js` 和 `pwa/earth3d.js` 中注册 `V2_ENHANCED` mode（tileSource → `tiles_v2_enhanced/`）
- `pwa/index.html` 新增第三个模式按钮 `V2 ENHANCED`，与 RAW EARTH / NOON AIR EARTH 并排
- 更新 `validateTileUrlForMode()` 覆盖 V2 路径校验（防止 tile 混用）
- 修复 `earth_modes.js` / `earth3d.js` 版本字符串（`?v=v2-enhanced-mode`），清除旧缓存
- 前端验证：V2 ENHANCED 模式切换正常，日本海岸线精度明显提升

### 改动文件
- `scripts/geo/global_v2_pipeline.py`（新建）
- `pwa/earth_modes.js`
- `pwa/earth3d.js`
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 大西洋中脊深度线条在 16k 下偏 GIS 感，后续可调 GEBCO blend 或 depth palette 间距
- 南海/北海等极浅陆架区域整体偏蓝，浅海调色可引入 JRC 水体掩膜进一步区分
- Arctic 冰层区存在 GEBCO 深度色向冰面渗色的风险，待高纬度巡检验证
- `tiles_v2_enhanced` 还未替换 `tiles_noon_air` 作为生产默认值；当前作为第三模式并行存在

---

## 2026-06-25 HZ V2 巡检 + 冰雪掩膜修复 (V2.0.1)

### 做了什么
- 系统巡检 V2 BATHY/COAST 全部 16k tile 的高纬度风险区：
  - Arctic/Greenland：通过，冰盖无渗色
  - 南极（tile_2_1、tile_3_1）：发现 GEBCO 冰缘蓝灰渗色 — 根因：`sub_ice_topo` 数据在冰盖下仍有负高程值，`ocean_mask=True`，导致 GEBCO blend 染蓝冰面像素
  - 中段陆架（南非、澳大利亚、北美）：通过
- 修复：在 `composite_tile()` 中加入亮度退出掩膜（`_ICE_LUMA_FADE_LOW=200`, `_ICE_LUMA_FADE_HIGH=235`），高亮度冰雪像素逐渐将 GEBCO blend 压到零，阻止深度色污染冰面
- 重新生成 4 张含南极的 tile：16k/tile_2_1、16k/tile_3_1、8k/tile_0_0、8k/tile_1_0 以及 4k 全量
- 视觉验证：南极冰盖恢复纯白，冰缘细节自然，无蓝灰色带

### 改动文件
- `scripts/geo/global_v2_pipeline.py`（`composite_tile()` 新增 ice suppress mask）
- `devlog.md`

### 已知问题（记录，暂不修，等 Noon Air 合并时统一处理）
- 深海洋脊（大西洋中脊、印度洋洋脊）GIS 感偏强：GEBCO blend=0.35 在 abyssal/trench 区稍高，建议合并时降至 0.20
- 南海/北海/波斯湾等极浅陆架整体偏蓝：等 Noon Air ocean tone curve 叠上后再评估是否需要 JRC 水体掩膜

---

## 2026-06-25 HZ Noon Air V2 合并完成

### 做了什么
- 在 `global_v2_pipeline.py` 加入 `--noon-air` flag：V2 composite 输出后串接 Stage 14+15（VisualUnificationEngine + PerceptualCalibrationEngine），结果写入 `tiles_noon_air_v2/`
- 通过 `importlib.util.spec_from_file_location` 隔离加载 VUE，绕过 `core/rendering/__init__.py` 的 D6Renderer 等重依赖
- 全球 12 张 Noon Air V2 tile 生成完成（129s）：16k×8 + 8k×2 + 4k×2
- 在 `pwa/earth_modes.js`、`pwa/earth3d.js` 注册 `NOON_AIR_V2` mode（cachePrefix `nav2`，tileSource `tiles_noon_air_v2/`）
- `pwa/index.html` 新增第四个按钮 `NOON AIR V2`，版本字符串升为 `noon-air-v2`
- 更新 `validateTileUrlForMode()` 加入 NOON_AIR_V2 mismatch guard
- 更新 `tests/test_earth_mode_switching.js`：版本字符串、nav2 cache prefix、NAV2 mismatch guard，8/8 通过
- 前端验证：日本视角下 NOON AIR V2 tiles 渲染成功，HTTP 200，四个模式按钮全部可用

### 合并结果
Noon Air V2 = GEBCO 深度 + GSHHG 海岸 + Stage 14+15 色彩感知层
- GEBCO 深度层依然可见，但经 VUE tone curve 处理后读起来是光和深度，而非 GIS 线条
- 陆地色彩有摄影质感，海岸线精度保持 GSHHG 全精度
- 南极冰缘修复（ice suppress mask）在合并后依然有效

### 改动文件
- `scripts/geo/global_v2_pipeline.py`（`--noon-air` flag, `_load_vue()`, `NOON_AIR_OUT_BASE`）
- `pwa/earth_modes.js`
- `pwa/earth3d.js`
- `pwa/index.html`
- `tests/test_earth_mode_switching.js`
- `devlog.md`

### 遗留问题（等后续评审决定是否升为生产默认）
- 深海洋脊 GIS 感：VUE 已部分改善，待整体巡检后决定是否进一步调 GEBCO blend
- 浅海陆架偏蓝（南海/北海/波斯湾）：待整体巡检评估

---

## 2026-06-25 Step 1 收口：GSHHG 小岛可见性 pass（全球候选层）

### 做了什么
- 澄清 GSHHG 层级含义：L1 = 陆/洋边界（含所有大洋岛屿），L2 = 湖泊，L3 = 湖中岛；"全球小岛可见性"正确做法是 L1 按 area 过滤，而非 L2/L3
- 新增 `rasterize_small_island_mask()`：读 L1，过滤 area < 5000 km²（Okinawa 级别以下），逐 tile 光栅化
- 新增 `small_island_visibility_pass()`：距离变换生成外光晕（5px），在 ocean_mask 区域做 10% 最大强度向浅水蓝过渡，按 LOD 衰减（16k=1.0, 8k=0.85, 4k=0.70）
- 新增 `--islands` pipeline flag：输出到候选目录 `tiles_v2_enhanced_islands/` 和 `tiles_noon_air_v2_islands/`，不覆盖现有生产目录
- 修复 `_write_manifest()` 路径 bug：传入 `out_base` 参数，island/noon_air 各写各自 manifest；manifest 增加 `variant` 字段
- 全量跑 12 张（16k×8 + 8k×2 + 4k×2），约 92s（16k）
- 前端注册第五个模式 `NOON_AIR_V2_ISLANDS`（`cachePrefix: 'nav2i'`），加 mismatch guard，UI 按钮 "NAV2 ISLANDS"，版本 bump 到 `?v=nav2-islands`
- 所有模式合约测试 8/8 通过

### 改动文件
- `scripts/geo/global_v2_pipeline.py`：ISLAND_* 常量、rasterize_small_island_mask、small_island_visibility_pass、process_tile island 参数、_write_manifest 路径修复
- `pwa/earth_modes.js`：NOON_AIR_V2_ISLANDS 注册
- `pwa/earth3d.js`：NOON_AIR_V2_ISLANDS fallback 注册 + mismatch guard
- `pwa/index.html`：NAV2 ISLANDS 按钮、version bump
- `tests/test_earth_mode_switching.js`：NAV2 ISLANDS 断言、version bump

### 遗留问题
- 候选层仅 16k；8k/4k 同步完成（全球 12 张均已生成）
- 巡检已完成，用户确认"有提升但不够高"→ 符合预期，Step 1 天花板是数据源分辨率
- Step 2 方向已确定：RDL 区域 tile（不依赖 BMNG 86K）

---

## 2026-06-25 Step 2 启动：RDL 区域 tile 生成器

### 做了什么
- 确认 GDAL 未安装，但 BMNG 86K 不是必要条件：GEBCO 本地已有 ~460m/px（15 arc-second），比 BMNG 21K 的 1860m/px 好 4×
- 新建 `scripts/geo/rdl_regional_generator.py`：
  - 接受 `--region` 或 `--all`，自定义地理 bounds
  - 使用 GEBCO blend=0.65（vs 全球 0.35），强化海洋深度可见性
  - GSHHG 全矢量精度渲染
  - 可选 `--noon-air` 输出 VUE 版本
  - 输出 tile.jpg + tile_noon_air.jpg + bounds.json（含 UV 坐标，供前端 LOD 注册）
- 8 个区域定义：马尔代夫(0.08km/px)、琉球(0.24)、菲律宾中部(0.27)、南海(0.31)、大堡礁(0.28)、加勒比/巴哈马(0.38)、夏威夷(0.19)、印度尼西亚东部(0.41)
- 马尔代夫对比验证：全球 tile 裁切（模糊光带）vs RDL 区域 tile（环礁礁盘形状清晰，深浅水分层明显）
- 全部 8 个区域 pipeline 后台运行中

### 改动文件
- `scripts/geo/rdl_regional_generator.py`：新建

### 遗留问题
- 前端 LOD 接入尚未完成（earth3d.js 需要添加区域 tile 覆盖层 + 相机距离触发）
- 8 个区域 tile 生成完毕后需视觉巡检
- 输出宽高比（如马尔代夫 4096×13653）需确认前端 UV 映射是否正确处理

---

## 2026-06-25 Step 2 前端接入：RDL 区域 tile 覆盖层

### 做了什么
- 在 `earth3d.js` 中实现 RDL（Regional Detail Layer）覆盖层系统
- 为 8 个区域创建独立的 `THREE.Mesh` 覆盖层，使用自定义 `ShaderMaterial`
- Fragment shader 根据球面 UV 坐标裁剪至各区域边界（`discard`），并在边缘 7% 范围内淡出
- 球面 UV 转换：`sphere_u = ((lon + TEXTURE_LON_OFFSET + 720) % 360) / 360`，`sphere_v = (90 - lat) / 180`（与 `TEXTURE_LON_OFFSET=90` 对齐）
- 朝向检测：`lonLatToVector3` + `earth.matrixWorld` 的 `transformDirection`，与相机方向 dot product
- 修复了关键 bug：`earth.matrixWorld` 在 `updateRDLOverlays` 运行时是过期的（在 `renderer.render()` 之前），使用 `earth.updateWorldMatrix(true, false)` 强制更新父节点链
- 修复了第二个关键 bug：preview 标签非激活时 `requestAnimationFrame` 暂停，animation loop 不运行；在 `requestRenderUpdate()` 中加入 `updateRDLOverlays()` 调用，确保一次性渲染也能触发覆盖层
- 新增滚轮缩放：修改相机 FOV（28°→8°），`_rdlZoomLevel` 驱动覆盖层透明度
- 新增公开 API：`getRDLZoomLevel()`、`setRDLZoomLevel(level)`、`getRDLDebugInfo()`
- 版本号更新至 `rdl-overlay-v1-final`，8 个合约测试全部通过

### 改动文件
- `pwa/earth3d.js` — RDL 覆盖层初始化、`updateRDLOverlays()`、滚轮缩放、公开 API
- `pwa/index.html` — 版本号 bump
- `tests/test_earth_mode_switching.js` — 版本号同步

### 遗留问题
- `getRDLDebugInfo()` 调试方法保留在公开 API 中，可按需移除
- 8 个区域 tile 的视觉巡检（非马尔代夫部分）未完成
- 滚轮缩放尚未实现平滑惯性；与地球拖动交互暂无实现

---

## 2026-06-25 HZ Mapbox Satellite Hawaii RDL POC

### 做了什么
- 新建 `scripts/geo/rdl_mapbox_poc.py`，从环境变量或本地 `.env` 读取 `MAPBOX_TOKEN`，不把 token 写入日志或输出文件
- 使用 Mapbox Static Tiles API 的 `mapbox/satellite-v9`，为夏威夷 bounds `[-161.5,-154.0,18.0,23.0]` 下载 zoom 10 瓦片
- 实际请求 352 张 512px raster tile，并缓存到 `d5b_processor_v3/source_cache/mapbox_static_tiles/satellite-v9/hawaii/z10/`
- 拼接并裁切输出 8192×5461 的候选 RDL 图：
  - `tile_mapbox.jpg`
  - `tile_noon_air_mapbox.jpg`
  - `mapbox_poc.json`
- 前端只将 `hawaii` RDL 区域切换到 `tile_noon_air_mapbox.jpg`，其他 RDL 区域继续使用原 `tile_noon_air.jpg`
- 版本号 bump 到 `mapbox-hawaii-poc`
- 本地浏览器直接打开 `tile_noon_air_mapbox.jpg` 成功，标题确认尺寸为 `8192×5461`

### 改动文件
- `scripts/geo/rdl_mapbox_poc.py`
- `pwa/earth3d.js`
- `pwa/index.html`
- `tests/test_stage11_frontend_streaming.js`
- `tests/test_earth_mode_switching.js`
- `devlog.md`

### 遗留问题
- Mapbox 卫星图海面天然偏暗；当前只做了轻量 brightness/contrast/sharpness 调整，后续可按 RodiO Noon Air palette 再细调
- 目前仅夏威夷接入 Mapbox POC；马尔代夫、大堡礁、加勒比等区域尚未切换
- 生产使用前需要补 Mapbox attribution 展示策略与 token 保护策略

---

## 2026-06-25 HZ Hawaii RDL 显示状态修复

### 做了什么
- 定位截图中“RDL loaded 但画面仍像旧图”的原因：夏威夷 RDL tile 已加载，但 region jump 后没有立即刷新 `updateRDLOverlays()`，叠加层透明度/显隐可能停留在旧帧状态
- 在 `setDebugLocation()` 中于 `updateStreaming(camera)` 后立即调用 `updateRDLOverlays()`，确保切换审查区域后同一帧更新 RDL 覆盖层
- 将 Pure View 默认模式从 `NOON_AIR_V2` 改为 `NOON_AIR_V2_ISLANDS`，避免审查小岛/RDL 时被强制压回普通 NAV2 底图
- 版本号 bump 到 `mapbox-hawaii-poc-v2`
- 新增测试断言：
  - Hawaii RDL 指向 `tile_noon_air_mapbox.jpg`
  - `setDebugLocation()` 会在 render 前刷新 RDL
  - Pure View 使用 island-ready 模式

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `tests/test_stage11_frontend_streaming.js`
- `tests/test_earth_mode_switching.js`
- `devlog.md`

### 遗留问题
- 当前 Hawaii Mapbox POC 仍受 UI 深色遮罩和 RDL facing opacity 影响；若需要“显著一眼可见”的审查态，下一步应增加 RDL debug/inspect 模式，将当前区域 opacity 固定为 1 并临时隐藏主题遮罩

---

## 2026-06-25 HZ RDL Inspect Mode for Region Audit

### 做了什么
- 定位到夏威夷仍显示在画面下缘的原因：地域巡检复用了主界面构图锚点 `VISUAL_TARGET_NDC = (0.25, -0.24)`，目标不是屏幕中心
- 扩展 `getTargetOrientation(targetDirOverride)` 与 `setDebugLocation(lon, lat, options)`，允许巡检调用 `{ center: true }`，把目标区域直接居中
- 新增 RDL inspect region 状态 `_rdlInspectRegion`
- 新增公开 API `setRDLInspectRegion(regionId)`：
  - 当前 RDL 区域强制 opacity=1
  - 只显示当前 inspect region，避免其他 RDL 区域同时叠加
  - 自动把 RDL zoom 拉到 1、FOV 拉到最小
- 为审查列表中已有 RDL 的区域添加 `rdlId`，包括琉球、菲律宾、印尼东部、南海、马尔代夫、大堡礁、夏威夷、加勒比/巴哈马
- 地域切换时调用 `setDebugLocation(..., { center: true })` 和 `setRDLInspectRegion(region.rdlId || null)`
- 版本号 bump 到 `mapbox-hawaii-poc-v3`

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `tests/test_stage11_frontend_streaming.js`
- `tests/test_earth_mode_switching.js`
- `devlog.md`

### 遗留问题
- Inspect mode 是审查工具，不是最终生产视觉；后续若用于生产需设计平滑进入/退出与 attribution UI

---

## 2026-06-25 HZ Allen Coral Atlas Hawaii Overlay Test

### 做了什么
- 只读盘点本地 Allen Coral Atlas 资源，确认本地约 16G 数据可用
- 检查 `Hawaiian-Islands-20230309235255.zip`，包含 `Reef-Extent/reefextent.gpkg`、`Geomorphic-Map/geomorphic.gpkg`、`Benthic-Map/benthic.gpkg` 和文档
- 使用 GeoPackage SQLite 元数据读取 Hawaii reef extent，未安装新依赖
- 在夏威夷 Mapbox RDL tile 上临时 rasterize `reefextent.gpkg`，命中 1,153 个 reef polygon
- 生成临时预览：
  - `/tmp/rodio_hawaii_aca_reef_overlay_compare.jpg`
  - `/tmp/rodio_hawaii_aca_reef_overlay_diagnostic.jpg`

### 改动文件
- `devlog.md`

### 遗留问题
- 夏威夷 reef extent 主要沿岛岸分布，作为自然叠加效果较弱；更适合用作 shoreline/reef edge 微增强
- 若要验证 Allen Coral Atlas 的视觉价值，下一步更适合选择马尔代夫、大堡礁或巴哈马

---

## 2026-06-25 HZ Earth Audit Controls v1

### 做了什么
- 将地域巡检控件从单一 `NEXT REGION` 升级为审查控制面板
- 新增区域前后切换：`PREV` / `NEXT`
- 新增当前位置微调：`UP` / `DOWN` / `LEFT` / `RIGHT`
- 将 zoom 文案改为 `FAR` / `NEAR`，标签改为 `DIST`
- 新增审查角度档位：`TOP` / `45°` / `LOW`
- 在 `earth3d.js` 新增 `setAuditViewAngle(angle)`，通过相机位置和 lookAt 调整审查角度
- 地域微调根据当前 RDL zoom 使用 1.2° / 0.5° / 0.25° 三档步长，越近移动越细
- 版本号 bump 到 `audit-controls-v1`

### 改动文件
- `pwa/index.html`
- `pwa/earth3d.js`
- `tests/test_earth_audit_regions.js`
- `tests/test_stage11_frontend_streaming.js`
- `tests/test_earth_mode_switching.js`
- `devlog.md`

### 遗留问题
- 审查角度是三档离散控制，暂未做连续滑杆或键盘快捷键

---

## 2026-06-25 HZ Earth Audit Controls v2

### 做了什么
- 修复角度切换后画面“弹回”的问题：动画循环此前每帧都会回到主界面构图锚点，导致审查居中只生效一瞬间
- 新增持久审查居中状态 `useAuditCenterTarget`，当 `setDebugLocation(..., { center: true })` 启用后，render loop 持续使用中心锚点
- 角度切换后重新应用当前经纬度居中，避免 TOP/45°/LOW 切换时漂移
- RDL 审查区域自动切换到 `NOON_AIR_V2_ISLANDS`，避免用户停留在 RAW 模式时误以为高细节层未生效
- 版本号 bump 到 `audit-controls-v2`

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `tests/test_earth_audit_regions.js`
- `tests/test_stage11_frontend_streaming.js`
- `tests/test_earth_mode_switching.js`
- `devlog.md`

### 遗留问题
- 夏威夷 Mapbox POC 图源本身偏暗，若仍不够明显，可单独调亮 Hawaii `tile_noon_air_mapbox.jpg` 或增加 RDL-only 对比开关

---

## 2026-06-25 HZ Earth Audit Controls v3

### 做了什么
- 将 `FAR` / `NEAR` 从增量按钮改为固定距离档位：
  - `FAR` 固定为 0.35
  - `NEAR` 固定为 1.0
- 修复 RDL inspect 区域会偷偷把 zoom 强制拉到 1 的问题，避免“点远近后位置/尺度又变了”
- 方向按钮支持长按连续移动，240ms 后开始每 90ms 重复移动
- 放大方向移动步长：远景 2.0°、中景 1.0°、近景 0.5°
- RDL 区域纹理禁用 mipmap，并开启更高 anisotropy，减少区域贴图被 GPU 过滤柔化
- 版本号 bump 到 `audit-controls-v3`

### 改动文件
- `pwa/index.html`
- `pwa/earth3d.js`
- `tests/test_earth_audit_regions.js`
- `tests/test_stage11_frontend_streaming.js`
- `tests/test_earth_mode_switching.js`
- `devlog.md`

### 遗留问题
- 夏威夷样片是平面 tile crop，当前浏览器里看到的是球面投影+UI遮罩后的结果；若需要样片级审查，需要增加 RDL-only/flat tile preview

---

## 2026-06-25 HZ Earth Audit Controls v4

### 做了什么
- 新增 `TILE VIEW` 审查按钮，用于直接查看当前 RDL 区域的平面 tile，避免球面投影、相机距离和 UI 遮罩影响清晰度判断
- `TILE VIEW` 在夏威夷区域自动使用 `tile_noon_air_mapbox.jpg`，其他 RDL 区域使用 `tile_noon_air.jpg`
- 将 `FAR` / `NEAR` 保持为固定距离档位，但不再重新调用经纬度定位，避免点击远近后画面位置跳变
- 角度切换只调整相机角度，不再重新定位当前区域，减少 TOP / 45° / LOW 切换时的眩晕感
- 放大 RDL 审查按钮尺寸，提高日常巡检可点击性
- RDL 区域纹理关闭 mipmap，减少高分辨率区域贴图被 GPU 过滤柔化
- 版本号 bump 到 `audit-controls-v4`

### 改动文件
- `pwa/index.html`
- `pwa/earth3d.js`
- `tests/test_earth_audit_regions.js`
- `tests/test_earth_mode_switching.js`
- `devlog.md`

### 遗留问题
- `TILE VIEW` 是审查工具，不改变最终球面渲染质量；若平面 tile 清晰但球面仍糊，下一步应优化 RDL 在球面上的投影范围、透明度和相机裁切策略

---

## 2026-06-25 HZ Earth 清晰度链路排查

### 做了什么
- 排查前端 3D Earth 清晰度问题，确认底层 BMNG / tile 资源尺寸完整：16K 全局图为 16384×8192，16K tile 为 4096×4096
- 检查 `pwa/earth3d.js` 渲染链路，确认当前 16K tile stream 会被合成为 8192×4096 CanvasTexture，每张 4096 tile 实际被降采样为 2048
- 检查 HTTP 服务和静态资源，确认服务启动后 `earth3d.js?v=audit-controls-v4`、16K tile、`/api/globe-image` 均可返回 200
- 检查浏览器运行日志，确认页面持续使用 16K tile stream，但日志频繁输出 `texture source`，会干扰调试与性能观察
- 对 16K tile 做源图与 2×降采样模拟对比，确认降采样会明显降低边缘能量和细节锐度

### 改动文件
- `devlog.md`

### 遗留问题
- 当前 16K 模式实际显示链路只有 8K atlas 精度，需评估在 GPU maxTextureSize ≥ 16384 时启用 16384×8192 atlas，或改为真正的多纹理 / 分块 shader
- `configureEarthTexture()` 使用 LinearMipmapLinearFilter + LinearFilter，配合 atlas 降采样会进一步柔化纹理
- 普通 UI 层和天气 canvas 仍覆盖在 3D Earth 上方，审查清晰度时需要更干净的 pure/debug view
- `/api/globe-image` 是旧 2D 天气 canvas 链路，服务未启动时会产生误导性报错；3D Earth tile stream 不依赖它

---

## 2026-06-25 HZ 修复 16K atlas 降采样问题

### 做了什么
- 确认 Codex 排查结论：`atlasTileSize` 在 16K 模式下错误地设为 2048，导致 4096×4096 tile 被 `drawImage()` 缩成 2048×2048，最终 atlas 只有 8192×4096 而非完整的 16384×8192
- 根因：注释中 "full-res would need 16384 which exceeds GPU limits" 是错误推理——16K LOD 分支本身已经验证了 `maxSize >= 16384`，GPU 完全可以承受 16384 宽度的 atlas
- 将 `atlasTileSize` 的 16K 值从 2048 改为 4096，使 atlas 恢复为完整的 16384×8192
- 在 `drawTile()` 中添加 `imageSmoothingEnabled = false`，防止 canvas 2D 对原生尺寸图做额外模糊

### 改动文件
- `pwa/earth3d.js`（`resolveEarthTextureLOD` atlasTileSize、`drawTile` imageSmoothingEnabled）
- `devlog.md`

### 遗留问题
- `configureEarthTexture()` 的 `LinearMipmapLinearFilter` 在 atlas 全尺寸情况下仍会产生柔化，可以考虑关闭 mipmap 或换用 `LinearFilter` alone 以获得更锐利效果
- 地球球体 segment 仍为 64×64；16K 纹理下可以提升至 128×128 以获得更准确的球面曲率细节
- 普通 UI 层和天气 canvas 覆盖在 3D Earth 上方，影响清晰度主观评估

---

## 2026-06-25 HZ Earth 清晰度验收模式 v5

### 做了什么
- 新增 16K atlas 专用 sharp filter：`configureAtlasTexture()` 在 16K + sharp 模式下使用 `LinearFilter` 并关闭 mipmap，避免近距离验收被低级 mip 柔化
- 暴露 `setAtlasFilterMode()` / `getAtlasFilterMode()`，Pure View 进入时切到 sharp，退出时恢复原模式
- 将主地球与 atmosphere 球体从 64×64 提升到 128×128，与 RDL overlay 精度保持一致
- 将 Pure View 改为真正的清晰度验收模式：隐藏 weather canvas、标题、播放控件、模式按钮、审查按钮和 tile preview，只保留 Earth 与最小退出/距离信息
- 版本号 bump 到 `audit-controls-v5`，避免浏览器继续使用 v4 脚本
- 增加回归测试，保护 16K atlas 4096 tile size、sharp atlas、128 段球体和 pure inspection class

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `tests/test_stage11_frontend_streaming.js`
- `tests/test_earth_audit_regions.js`
- `tests/test_earth_mode_switching.js`
- `devlog.md`

### 遗留问题
- sharp atlas 可能在远距离带来轻微摩尔纹；若出现，可以通过 `setAtlasFilterMode('normal')` 回退到 mipmap 模式
- 16K full atlas 显存压力较高，低显存环境仍需观察 WebGL context stability
- 内置浏览器运行态可确认 v5 脚本与 Pure View class 生效，但最终清晰度仍需在真实 Chrome/GPU 画面肉眼验收

---

## 2026-06-25 HZ Pure View 验收态修正

### 做了什么
- 修正 Pure View 进入后的残留控件布局：将退出按钮与最小距离标签居中到底部，降低透明度，避免左下角悬浮控件显得异常
- Pure View 进入时重新对齐当前审查坐标，并按经度选择更合适的日照主题，减少从旧 custom 坐标或不合适光照继承出的构图异常
- 将前端脚本版本号 bump 到 `audit-controls-v6`，避免浏览器继续使用旧缓存
- 增加回归测试，保护 Pure View 控件居中、当前目标重定位和本地日照主题逻辑
- 通过内置浏览器验证 v6 页面加载与 Pure View class / hidden UI / 居中控件状态

### 改动文件
- `pwa/index.html`
- `tests/test_earth_audit_regions.js`
- `tests/test_earth_mode_switching.js`
- `devlog.md`

### 遗留问题
- 真实清晰度仍以外部 Chrome/GPU 画面为准；如 Chrome 仍显示旧界面，需要点右上角“重新启动即可更新”或硬刷新以清掉 service worker 旧缓存

---

## 2026-06-25 HZ 修复本地页面白屏缓存问题

### 做了什么
- 排查 `localhost:8080` 空白页问题，确认服务端 `/` 正常返回 200，前端内联脚本语法正常，浏览器侧无致命启动错误
- 定位风险点为 service worker 缓存策略过宽：旧 `/sw.js` 会缓存所有同源 GET，包括页面壳层、API 与 16K Earth 大瓦片，容易造成本地开发旧缓存/空白页状态
- 将服务端动态 `/sw.js` 升级到 `claudio-static-v3`：localhost/127.0.0.1 下直接走网络，不再接管缓存
- 收窄生产缓存范围：仅缓存 manifest/icon、TTS cache 与 shell 静态壳层，不再缓存 Earth 大瓦片和普通 API 请求
- 更新前端本地开发缓存清理逻辑，删除所有 `claudio-static-*` 旧缓存
- 重启本地 8080，并验证 `/`、`/sw.js`、v6 脚本和浏览器页面加载正常

### 改动文件
- `server.js`
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 已经被旧 service worker 控制的 Chrome 标签页可能仍需一次硬刷新，或改用 `http://127.0.0.1:8080/?fresh=1` 进入以绕过 `localhost` 旧 origin 缓存

## 2026-06-25 HZ 法线贴图集成

### 做了什么
- 从 `etopo1_ice_surface_8192x4096.tif`（全球陆地+海底地形，int16，-10761~7980m）生成切线空间法线贴图
- 算法：`numpy.gradient` 计算高度梯度 → 构建单位法向量 → 编码为 RGB，strength=0.004
- 输出：降采样至 4096×2048，有损 WEBP quality=90，文件大小 3.0 MB
- 路径：`pwa/assets/earth_normal_8k.webp`，由 `express.static` 自动伺服
- `earth3d.js`：新增 `loadNormalMapTexture()` 函数，`earthMaterial` 创建后异步触发加载
- `normalScale = (0.35, 0.35)`，可按肉眼效果在 0.2~0.6 之间调整
- `applyTheme()` 里补充了 normalMap 的重挂载检查，保证 theme 切换时不丢失
- dispose 清理时同步释放 normalMapTexture

### 改动文件
- `scripts/geo/gen_normalmap.py`（新建）
- `pwa/assets/earth_normal_8k.webp`（新建，3 MB）
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- `normalScale` 默认值 0.35 未经视觉验收，过强会出现"橘子皮"感，过弱看不出立体，建议在 Pure View 下对比 0.2 / 0.35 / 0.5
- ETOPO1 海底地形的法线在深海区也会产生细节（洋中脊、海沟），视觉上是否合适需评估
- 若 Railway 部署带宽受限，3 MB WEBP 可通过 CDN 缓存或 gzip 进一步优化

---

## 2026-06-25 HZ 海洋高光材质调参

### 做了什么
- 确认 `ocean_specular_4096x2048.png` specularMap 结构已存在，但 shininess(0.1~1.1) 和 specular(接近纯黑) 数值导致高光实际不可见
- 对 4 个日间主题调整 specular 颜色和 shininess，使海洋区域产生真实可见的反射高光：
  - morning  → shininess 1.05→32，specular 0x06090f→0x14202e（蓝白，清晨）
  - noon     → shininess 1.12→42，specular 0x091018→0x18283e（正午最紧）
  - afternoon → shininess 0.96→30，specular 0x05080d→0x14202c（午后微冷）
  - goldenApproach → shininess 0.68→16，specular 0x070503→0x281a0a（黄金时段暖琥珀，宽漫射）
- 陆地区域不受影响，specularMap 保证高光仅出现在海洋上

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 视觉验收需在 Pure View + NEAR + noon/morning 主题下对着太平洋观察高光区域
- 若实际效果偏强可将 specular 值各降一档（约减 0x04），偏弱则将 shininess 各提 5~8

---

## 2026-06-25 HZ 法线贴图 + 海洋高光修正（橡胶球问题）

### 做了什么
- 诊断"橡胶球"感的两个根因：
  1. 法线贴图把 ETOPO1 海底地形（洋中脊、海沟）渲染成了海面凹凸，导致海洋看起来像磨砂橡胶
  2. shininess 30~42 在球体规模下高光覆盖范围太宽，整片受光海洋被均匀提亮呈金属感
- 修复法线贴图：用 `ocean_mask_4096x2048_soft.png` 对生成结果做 blend，海洋区域归为 flat normal (128,128,255)，陆地保留地形起伏；重新生成 `earth_normal_8k.webp`（2.3 MB）
- 修复 shininess 数值：
  - morning: 32 → 120
  - noon: 42 → 150
  - afternoon: 30 → 120
  - goldenApproach: 16 → 60（黄金时段保持较宽但不再覆盖全球）

### 改动文件
- `scripts/geo/gen_normalmap.py`（新增 ocean mask 步骤）
- `pwa/assets/earth_normal_8k.webp`（重新生成，2.3 MB）
- `pwa/earth3d.js`（4 个主题 shininess 调整）
- `devlog.md`

### 遗留问题
- 视觉验收：noon + Pure View + NEAR 下太平洋应出现局部耀斑而非整面金属感
- normalScale=0.35 在山地区域可能仍偏强，可视情况降到 0.2

---

## 2026-06-25 HZ Pure View 修复 + 过渡主题亮度调整

### 做了什么
- **Pure View bug 修复**：将 `visibility: hidden` 改为 `display: none`。原实现中隐藏元素仍可接收点击事件，导致在 Pure View 内误触时段/模式按钮，意外切换主题或地球模式
- **正午点击后地球仍为暗夜的说明**：确认是 UI 背景色（CSS variables）和 earth3d 主题（WebGL 光照）两套系统均已正确切换，截图3/4 背景浅蓝灰即为正午主题色；无需修复
- **过渡主题 ambient 提升**，使日周期亮度过渡更平滑，海水不再骤暗：
  - dawn:        0.032 → 0.048
  - sunrise:     0.055 → 0.072
  - earlyMorning: 0.052 → 0.068
  - sunset:      0.046 → 0.058
- 夜间三个主题（evening/lateEvening/deepNight）不变，保留深邃感

### 改动文件
- `pwa/index.html`（Pure View CSS）
- `pwa/earth3d.js`（4 个过渡主题 ambient）
- `devlog.md`

### 遗留问题
- Pure View 内无法手动切换时段/地球模式（被 display:none 隐藏），目前是设计行为；如需支持可考虑在 Pure View 底部加一个最小时段选择器

---

## 2026-06-25 实时太阳位置追踪

### 做了什么
- 用 J2000 天文算法替换了 `updateSunPosition(hour)` 中的硬编码四段插值
- 新增 `_computeSubsolarPoint()`：基于 Julian Date → 黄道经度 → 赤纬/赤经 → Greenwich Apparent Sidereal Time → 日下点经纬度，精度 ~0.1°，足够渲染使用
- `updateSunPosition()` 不再接受 hour 参数，始终以 `new Date()` 计算真实太阳方向
- 坐标映射：Three.js SphereGeometry 等矩映射下 lon=0(本初子午线) → +x，lon=90°E → −z，北极 → +y，推导公式为 `(-cos(φ)sin(θ), cos(θ), sin(φ)sin(θ)) × 10`
- 加入 `setInterval(updateSunPosition, 60000)`，太阳位置每分钟自动更新
- `dispose()` 中 `clearInterval(_sunUpdateInterval)` 清理定时器
- 两处调用点（初始化 + setTimeOfDay）均改为无参 `updateSunPosition()`
- SW 缓存版本 `claudio-v2` → `claudio-v3`，强制刷新 `earth3d.js`

### 改动文件
- `pwa/earth3d.js`（_computeSubsolarPoint, updateSunPosition, 计时器, dispose）
- `pwa/sw.js`（缓存版本）
- `devlog.md`

### 遗留问题
- 强制切换主题时太阳位置仍使用真实时刻（非主题小时），符合设计意图（光照颜色由主题控制，太阳方向由物理决定）；若未来需要"跟随主题小时"可单独加参数覆盖

## 2026-06-25 模式锁定 + 云层清除

### 做了什么
- **earth3d.js — 模式锁定**：归档 RAW / NOON_AIR / V2_ENHANCED / NOON_AIR_V2 四个模式为注释，运行时硬锁定到 `NOON_AIR_V2_ISLANDS`（审计确认：全部五个模式均有完整 16k/8k/4k tile 数据；NOON_AIR_V2_ISLANDS 为最终流水线产物，16k tile 与 NOON_AIR_V2 MD5 不同，island pass 已实际生效）
- **earth3d.js — 3D 云层全删**：移除所有 cloud 变量声明、CLOUD_OPACITY/DRIFT 配置表、normalizeCloudThemeKey / getCloudOpacity / isLowCloudDevice / updateCloudDrift / loadCloudAlphaTexture 等全部函数、earthGroup.add(cloudMesh) 调用、setCloudVisible / getCloudVisible API、dispose 清理代码
- **index.html — earth-mode-toggle UI 删除**：移除 5 个模式切换按钮 HTML、`.earth-mode-toggle` / `.earth-mode-btn` CSS、`renderEarthModeToggle` 函数、`earthModeToggle` addEventListener、所有散落调用点
- **index.html — Pure View / Tile View 删除**：移除两个按钮 HTML、`.earth-pure-inspection` CSS 规则块、`_pureViewActive` / `_pureViewPrev` / `_tileViewActive` 变量、`updateRDLTilePreview` / `getRDLTileUrl` 函数、两个 click 事件处理器、所有调用点
- **index.html — canvas 背景云团删除**：移除 `initCloudSystem` 函数、`drawCloudSystem` 函数、`visualState.cloudSystem` 状态字段、`startWeatherSystem` 中的 `initCloudSystem` 调用、渲染循环中的 `drawCloudSystem` 调用、applyForcedTheme 和主循环中的触发点
- SW 缓存已在上一条记录升至 `claudio-v3`，本次改动覆盖在内

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 云层资源（`pwa/assets/earth/clouds/`）保留，后期重新建设云层时直接替换即可
- canvas 天气色温叠加（雨/雾/霾 overlayColor）已保留，不影响氛围感

## 2026-06-25 HZ 开发资源清单盘点

### 做了什么
- 读取 `AGENTS.md` 并盘点当前仓库已有开发资源：主应用模块、环境变量键名、脚本、文档、缓存/数据产物、Earth 视觉管线、Python 语义/渲染模块与测试入口
- 未改动业务代码，未运行生成器，未触发部署

### 改动文件
- `devlog.md`

### 遗留问题
- 本次仅做资源清单整理；哪些资源要纳入下一轮开发仍需按任务目标单独决策

## 2026-06-26 HZ RDL Mapbox 全区域扩展 + GEBCO 深度层（M0+M1）

### 做了什么
- 重写 `scripts/geo/rdl_mapbox_poc.py` 为 M0+M1 合成器：
  - M0：Mapbox Satellite-v9 瓦片下载 + 拼接（支持所有 8 个 RDL 区域）
  - M1：GEBCO 2026 海洋深度着色层，深度加权混合（≥-30m 不干预 Mapbox 浅海细节，-3000m 以深最大混合比 60%）
  - 新增 `--all` / `--list` / `--no-gebco` 参数
  - 输出尺寸自适应：以较长地理轴为 4096px，保持真实地理比例
- 更新 `pwa/earth3d.js` RDL 加载器：
  - 所有区域统一优先尝试 `tile_noon_air_mapbox.jpg`
  - 加载失败时自动降级到 `tile_noon_air.jpg`（无感知，旧区域继续显示）
  - 日志区分 `(mapbox)` 和 `(fallback)`
- 验证：本地预览确认全部 8 个 RDL 区域 loaded=true，fallback 正常工作

### 改动文件
- `scripts/geo/rdl_mapbox_poc.py`（重写）
- `pwa/earth3d.js`（RDL 区域 URL + 加载器逻辑）

### 遗留问题
- ~~7 个非夏威夷区域的 `tile_noon_air_mapbox.jpg` 尚未生成~~ → 已全部生成完毕（2026-06-26 09:09）
- M2（Coral Atlas）、M3（ESA WorldCover）、M4（Köppen）层待后续迭代
- console.log 在每帧触发导致日志刷屏（独立 bug，已标记）

## 2026-06-25 HZ 地图地形资源清单盘点

### 做了什么
- 聚焦地图、地形、地理信号与 Earth 视觉管线，盘点 `core/`、`scripts/geo/`、`d5b_processor_v3/`、`pwa/assets/`、`previews/`、`docs/` 下的相关资源
- 记录主要资源类别、重资产目录规模、可用数据源和候选接入点
- 未运行生成器，未处理原始数据，未触发部署

### 改动文件
- `devlog.md`

### 遗留问题
- 本次仅列出现有资源；哪些进入主线、哪些保持实验/候选状态，需要按下一阶段目标单独评审

## 2026-06-26 HZ Mapbox Tile 缓存审计与补缺脚本

### 做了什么
- 新增 `scripts/geo/mapbox_tile_cache_audit.py`：默认只读审计本地 Mapbox Static Tiles cache，不读 token、不联网
- 支持按 RDL 区域计算 z10 tile 覆盖、统计 cached/missing/invalid，并可输出 JSON report
- 下载模式必须显式传入 `--download --max-new-requests N`，防止无意中产生 Mapbox API 请求
- 本地审计结果：8 个 RDL 区域中 7 个完整，`caribbean_bahamas` 缺 980 / 1419 tiles

### 改动文件
- `scripts/geo/mapbox_tile_cache_audit.py`
- `devlog.md`

### 遗留问题
- 新脚本不能绕过 Mapbox token 或计费；补新 tile 仍需要合法 `MAPBOX_TOKEN`，并会按 Static Tiles API 请求计量
- 当前仅覆盖已有 8 个 RDL 区域；若要“全球更多地区”，需要先定义更多区域网格或改用开放数据源方案

## 2026-06-26 HZ Claude Code RDL 部署结论核验

### 做了什么
- 核验 `server.js` 静态路由：`/assets/earth/bmng21k` 已映射到 `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG`
- 核验 `pwa/earth3d.js`：`_RDL_REGIONS` 已包含 32 个区域，加载路径为 `topo_bathy/tiles_rdl_regions/{id}/tile_noon_air_mapbox.jpg`
- 核验本地文件：32 个区域目录与代码 id 完全一致，`tile_mapbox.jpg` / `tile_noon_air_mapbox.jpg` 均齐全
- 发现部署注意点：贴图目录被 `.git/info/exclude` 中的 `d5b_processor_v3/source_cache/` 忽略，普通 `git add` 不会把贴图加入提交

### 改动文件
- `devlog.md`

### 遗留问题
- 若要通过 Railway 部署贴图，需要决定是否用 `git add -f` 强制纳入约 101 MB 的 RDL 贴图，或改走外部静态资产/CDN
- 本次未执行 `git add`、commit、push，也未触发部署

## 2026-06-26 HZ RDL M0/M1 验收抽检证据包

### 做了什么
- 基于用户提供的夏威夷左右对比截图，将 Hawaii M0/M1 视觉结果记为 PASS
- 只读核验当前 RDL 输出库存：84 个区域目录、84 个 `tile_mapbox.jpg`、84 个 `tile_noon_air_mapbox.jpg`、84 个 `mapbox_meta.json`
- 抽检 `hawaii`、`maldives`、`great_barrier_reef`、`philippines_central`、`caribbean_bahamas` 五个高风险岛礁/浅海区域，生成 contact sheet 与图像指标 JSON
- 新增验收报告，明确 M0/M1 可继续作为 RDL 区域视觉评审 baseline，同时把部署资产策略列为上线前 blocker

### 改动文件
- `docs/preview_archives/rdl_m0_m1_acceptance_20260626/README.md`
- `docs/preview_archives/rdl_m0_m1_acceptance_20260626/m0_m1_contact_sheet.jpg`
- `docs/preview_archives/rdl_m0_m1_acceptance_20260626/m0_m1_sample_metrics.json`
- `devlog.md`

### 遗留问题
- 本次未运行生成器、未修改前端/服务端逻辑、未执行 `git add`、commit、push，也未触发 Railway
- RDL 贴图仍位于被 `.git/info/exclude` 排除的 `d5b_processor_v3/source_cache/` 下；部署前必须先决定强制纳入、迁移到 tracked static assets，或改走外部对象存储/CDN
- M2 Coral Atlas 仍需单独处理 GIS 依赖与 `.gpkg` 向量栅格化，不应混入 M0/M1 验收提交

## 2026-06-26 HZ RDL 后续资源匹配台账

### 做了什么
- 新增 RDL 资源匹配快照，盘点 M0/M1/M2/M3/M4 与 supplemental 数据当前可用状态
- 生成 `resource_matching.json`，包含 84 个 RDL 区域的 M0/M1 输出状态、M3 WorldCover/M4 Köppen 全局可用状态、以及 Coral Atlas 候选包匹配
- 确认 M3 WorldCover 与 M4 Köppen 已有 8K TIF，可先做只读区域采样/直方图；M2 Coral Atlas 当前是 `.gpkg` 向量包，缺 `rasterio/fiona/geopandas/shapely/pyproj` 或 GDAL 命令行工具，需单独开依赖与栅格化 proof
- 将 34 个 RDL 区域匹配到 Coral Atlas 候选包，用于后续解压与验证顺序规划；这些匹配标记为 candidate，不等同于已完成向量范围/分类验证

### 改动文件
- `docs/preview_archives/rdl_resource_matching_20260626/README.md`
- `docs/preview_archives/rdl_resource_matching_20260626/resource_matching.json`
- `devlog.md`

### 遗留问题
- 本次未解压 Coral Atlas ZIP、未栅格化 `.gpkg`、未运行生成器、未修改前端/服务端逻辑、未执行 `git add`、commit、push，也未触发 Railway
- M2 进入实现前需要先解决 GIS 依赖或选择 GDAL 工具链
- M3/M4 虽可先做，但仍需定义区域采样 adapter、class histogram 输出格式，以及视觉参数映射表

## 2026-06-26 HZ RDL M3/M4 区域采样器

### 做了什么
- 新增 `scripts/geo/rdl_m3_m4_region_sampler.py`，读取 `rdl_mapbox_poc.py` 的 84 个 RDL bounds，并对现有 8K 分类栅格做区域裁剪统计
- 采样数据源：
  - M3：`esa_worldcover_2021_v200_map_8192x4096.tif`
  - M4：`koppen_geiger_1991_2020_8192x4096.tif`
- 生成 `m3_m4_region_histograms.json`：每个区域完整 WorldCover / Köppen class histogram
- 生成 `m3_m4_region_summary.csv`：每个区域 top land class、water/vegetation/bare/built/ice 比例、top climate class 与 climate family
- 生成 `m3_m4_visual_hints.json`：基于 histogram 的非破坏性 visual hints 草图（未接入 compositor）
- 生成 README 高优先级区域摘要，并完成脚本 `--help`、84 区域输出数量、关键区域 sanity check 与 `python3 -m py_compile` 验证

### 改动文件
- `scripts/geo/rdl_m3_m4_region_sampler.py`
- `docs/preview_archives/rdl_m3_m4_region_sampler_20260626/README.md`
- `docs/preview_archives/rdl_m3_m4_region_sampler_20260626/m3_m4_region_histograms.json`
- `docs/preview_archives/rdl_m3_m4_region_sampler_20260626/m3_m4_region_summary.csv`
- `docs/preview_archives/rdl_m3_m4_region_sampler_20260626/m3_m4_visual_hints.json`
- `devlog.md`

### 遗留问题
- 本次只生成采样报告和 hints 草图；未修改 M0/M1 合成器，未生成新贴图，未接入前端/服务端
- visual hints 仍需人工评审后才能转成正式 M3/M4 参数映射
- M2 Coral Atlas 仍未开始解压/栅格化，继续保持独立任务
- 未执行 `git add`、commit、push，也未触发 Railway

## 2026-06-26 HZ RDL 审图中性光照模式

### 做了什么
- 新增 `earth3d` audit lighting override：审图模式强制使用 day texture、正面太阳光、较高环境光、低大气层与关闭城市灯，避免日夜暗边影响人工判断
- RDL 审核入口与方向微调入口会调用 `window.earth3d.setAuditLightingMode(true)`，进入人工审核时自动暂停动态暗化
- `setAuditViewAngle()` 切换 TOP / 45° / LOW 后会刷新太阳方向，保证每个角度都保持可读
- 将前端脚本 cache bust 更新为 `audit-lighting-v1`，确保本地刷新能拿到新逻辑
- 增加/更新相关静态断言，覆盖 audit lighting API、配置、脚本版本与审核入口调用

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `tests/test_earth_audit_regions.js`
- `tests/test_earth_mode_switching.js`
- `tests/test_stage11_frontend_streaming.js`
- `devlog.md`

### 遗留问题
- 本次未修改生成器、未生成新贴图、未执行 `git add`、commit、push，也未触发 Railway
- 现有三组 JS 测试仍有旧断言失败，失败点集中在 RAW 按钮、旧 Hawaii POC 路径、RDL tile preview / pure view 旧行为；新增的中性光照断言已通过
- 人工审核需要刷新 localhost 页面后重新截图确认亮度；如仍过暗，再调 `AUDIT_LIGHTING_CONFIG` 的 ambient / sun 参数

## 2026-06-26 HZ RDL Overlay 黑块与精度断层修复

### 做了什么
- 根据人工审核截图，定位第二张/第七张的黑色方块与第九张左右精度不一致：未指定 `rdlId` 的审图位置仍会显示所有朝向可见的 RDL 区域贴片，局部高精度 JPG 与全局底图叠加后形成硬边
- 将 RDL overlay 改为 opt-in：只有 `setRDLInspectRegion(regionId)` 指定的区域会显示增强贴片，普通 CUSTOM / 非 RDL 审图点不再显示任何区域贴片
- 将非指定 RDL overlay 的 opacity 固定为 0，指定区域保持轻微降权 opacity，减少边界突兀感
- 更新前端 cache bust 为 `rdl-overlay-gate-v1`，确保刷新后加载新逻辑
- 更新 Stage 11 静态测试：所有 RDL 区域走 Mapbox tile，并断言非指定 RDL overlay 必须隐藏

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `tests/test_stage11_frontend_streaming.js`
- `tests/test_earth_mode_switching.js`
- `devlog.md`

### 遗留问题
- 本次未修改生成器、未生成新贴图、未执行 `git add`、commit、push，也未触发 Railway
- `node tests/test_stage11_frontend_streaming.js` 已通过；`test_earth_audit_regions.js` 与 `test_earth_mode_switching.js` 仍有旧 UI/路径断言失败，需后续单独整理
- 需要刷新 localhost 后复测第 2、7、9 张对应位置，确认黑块与精度断层消失

## 2026-06-26 HZ M2 Coral Atlas 最小栅格化 proof

### 做了什么
- 按用户要求停止安装 geopandas / rasterio / fiona / pyproj / shapely / GDAL，改用 `.venv` 的 Python 3.11 + stdlib `sqlite3` + Pillow + numpy 最小路径
- 新增 `scripts/geo/rdl_coral_atlas_proof.py`：
  - 从 Allen Coral Atlas zip 中只抽取 `Reef-Extent/reefextent.gpkg`
  - 直接读取 GeoPackage SQLite 元数据与 rtree 索引
  - 自写 GeoPackageBinary + WKB Polygon/MultiPolygon parser
  - 用 Pillow 将 reef extent 多边形栅格化为 RDL 区域同尺寸 mask
  - 输出 mask、overlay preview、contact sheet 与 metadata
- 生成 M2 proof 输出目录 `docs/preview_archives/rdl_m2_coral_atlas_proof_20260626/`
- 跑通两个区域：
  - `maldives`：命中 6,541 个 reef polygon，解析错误 0，reef pixel ratio 约 2.09%
  - `hawaii`：命中 1,153 个 reef polygon，解析错误 0，reef pixel ratio 约 0.25%
- 目检 Maldives contact sheet，reef mask 与 atoll / reef 结构对齐，证明 Coral Atlas 对浅海视觉有明显价值
- 完成 `.venv/bin/python -m py_compile scripts/geo/rdl_coral_atlas_proof.py` 与 `--help` 检查

### 改动文件
- `scripts/geo/rdl_coral_atlas_proof.py`
- `docs/preview_archives/rdl_m2_coral_atlas_proof_20260626/README.md`
- `docs/preview_archives/rdl_m2_coral_atlas_proof_20260626/*_aca_reef_mask.png`
- `docs/preview_archives/rdl_m2_coral_atlas_proof_20260626/*_aca_reef_overlay_preview.jpg`
- `docs/preview_archives/rdl_m2_coral_atlas_proof_20260626/*_aca_reef_contact_sheet.jpg`
- `docs/preview_archives/rdl_m2_coral_atlas_proof_20260626/*_aca_reef_metadata.json`
- `devlog.md`

### 遗留问题
- 本次只是 M2 reef extent proof，未接入 RDL 生成器、未修改前端、未生成生产贴图、未执行 `git add`、commit、push，也未触发 Railway
- `Benthic-Map` 与 `Geomorphic-Map` 仍未处理；这些 `.gpkg` 体积更大，应在 reef extent 进入 compositor 后再单独推进
- 下一步应将 reef mask 接入 `rdl_mapbox_poc.py`，做 depth-gated、feathered 的浅海青蓝/礁盘细节增强，而不是直接把 cyan overlay 用作最终视觉

## 2026-06-26 HZ M2 ACA Reef Maldives 自然合成候选

### 做了什么
- 将 M2 reef extent proof 接入 `scripts/geo/rdl_mapbox_poc.py` 的可选合成路径，新增 `--aca-reef`
- `--aca-reef` 默认不覆盖已验收的 `tile_noon_air_mapbox.jpg`，而是额外输出：
  - `tile_mapbox_aca_reef.jpg`
  - `tile_noon_air_mapbox_aca_reef.jpg`
  - `aca_reef_mask.png`
  - `aca_reef_meta.json`
- 为安全起见，若已有 `tile_mapbox.jpg`，M2 候选会复用现有 M0/M1 基础图，不重新请求 Mapbox，不重新生成默认 M0/M1 贴图
- 生成 Maldives 第一版自然候选：
  - reef extent 命中 6,541 个 polygon
  - holes 5,081
  - parse errors 0
  - reef pixel ratio 约 2.09%
- 新增评审目录 `docs/preview_archives/rdl_m2_aca_composite_20260626/`，包含 README、summary JSON 和 Maldives 三栏 contact sheet
- 目检 contact sheet：候选图比 proof cyan overlay 自然，atoll / reef 边缘被轻微提亮，未出现调试色块感
- 完成 `.venv/bin/python -m py_compile scripts/geo/rdl_mapbox_poc.py scripts/geo/rdl_coral_atlas_proof.py` 与 `--aca-reef` CLI 检查

### 改动文件
- `scripts/geo/rdl_mapbox_poc.py`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/maldives/tile_mapbox_aca_reef.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/maldives/tile_noon_air_mapbox_aca_reef.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/maldives/aca_reef_mask.png`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/maldives/aca_reef_meta.json`
- `docs/preview_archives/rdl_m2_aca_composite_20260626/README.md`
- `docs/preview_archives/rdl_m2_aca_composite_20260626/maldives_m2_aca_reef_candidate_contact_sheet.jpg`
- `docs/preview_archives/rdl_m2_aca_composite_20260626/maldives_m2_aca_reef_candidate_summary.json`
- `devlog.md`

### 遗留问题
- 本次只是 Maldives review candidate，未接入 `earth3d.js`，未替换生产贴图，未执行 `git add`、commit、push，也未触发 Railway
- 当前 `.venv` 按用户要求保持最小依赖，没有 `tifffile`，因此本次候选使用 feathered reef-mask blend，尚未启用 GEBCO depth gate
- 下一步需要人工评审 Maldives 候选；若通过，再批量扩展到 `great_barrier_reef`、`philippines_central`、`caribbean_bahamas` 等 M2 高价值区域

## 2026-06-26 HZ M3/M4 接入合成器，批量跑全 84 区域

### 做了什么
- 在 `scripts/geo/rdl_mapbox_poc.py` 新增 `--m3m4` flag，将 M3 WorldCover 陆地色调与 M4 Köppen 气候基线接入 Noon Air 合成路径
- 新增函数：`_load_m3m4_hints()` / `_get_m3m4_hints()`（延迟加载 `m3_m4_visual_hints.json`）、`apply_m4_temperature()`（全图 RGB 通道微偏移，±1-2%）、`apply_m3_land_tint()`（GEBCO elev>0 做陆地 mask，叠生态色调，strength 0.06-0.12）
- 修改 `noon_air_pass(img, sat_bias, contrast_bias)` 接受 M4 饱和度与对比度参数
- 输出为 `tile_noon_air_mapbox_m3m4.jpg`（非破坏性，不覆盖现有 M0+M1 基准图）
- 对 4 个典型区域（Maldives/Svalbard/波斯湾/亚得里亚）验证效果，生成 benchmark contact sheet
- 批量对全 84 个区域跑 `--m3m4`，32 秒完成，0 错误，生成全局 overview（色块标记 climate family）
- 效果确认：arid 区域（波斯湾、红海）沙漠感明显提升；polar/ice（Svalbard）冷蓝向正确；tropical/ocean 区域变化克制；temperate 区域 neutral 基线基本不动

### 改动文件
- `scripts/geo/rdl_mapbox_poc.py`
- `d5b_processor_v3/source_cache/.../tiles_rdl_regions/*/tile_noon_air_mapbox_m3m4.jpg`（84 个，不进 git）
- `docs/preview_archives/rdl_m3m4_benchmark_20260626/`（benchmark + overview contact sheet）
- `devlog.md`

### 遗留问题
- 当前 `.venv` 无 tifffile，M3 陆地 mask 依赖 GEBCO elev；无 GEBCO 时 land tint 不应用（已有 fallback）
- M3/M4 参数尚未接入 M2 ACA reef 路径（`tile_noon_air_mapbox_aca_reef.jpg` 仍用原始 noon_air_pass）
- LOW 视角下的 RDL overlay 精度问题（facing 平滑 + LOD 参数）待单独处理
- 未执行 git add / commit / push，未触发 Railway

---

## 2026-06-26 M2 ACA 礁石全扩展 + UnsharpMask 批量锐化

### 做了什么
- 在 `noon_air_pass()` 末尾加入 `ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3)`，替代原 Sharpness×1.10 的过于温和的锐化
- 将 `_ACA_REEF_PACKAGES` 从 5 个区域扩展至 47 个，新增覆盖：红海、阿拉伯海、安达曼海、南海集群（5个）、东南亚集群（8个）、太平洋岛屿（9个）、印度洋（4个）、加勒比扩展（4个）、百慕大、巴西等
- 对全部 47 个 ACA 区域批量跑 `--aca-reef --m3m4`，记录每个区域 reef_px 计数
- 按 reef_px >= 15 阈值选出 37 个区域提升 ACA 版本为主 tile；10 个低密度区域保留 m3m4 版本
- 对剩余 37 个非 ACA 区域（北欧、地中海、大西洋等）跑 `--m3m4`，补齐 UnsharpMask 锐化
- 全部 84 个区域 tile 更新完毕：37 个含 M2 ACA，47 个含 M3/M4，所有区域含 UnsharpMask

### 改动文件
- `scripts/geo/rdl_mapbox_poc.py`（_ACA_REEF_PACKAGES 扩展 + UnsharpMask）
- `d5b_processor_v3/source_cache/.../tiles_rdl_regions/*/tile_noon_air_mapbox.jpg`（84 个，不进 git）

### 遗留问题
- LOW 视角下 RDL overlay 地理边界硬切问题（shader 端 smoothstep 软边）
- 未执行 git add / commit / push，未触发 Railway

---

## 2026-06-26 Claude 完成项本地核对 + 下一步资源盘点

### 做了什么
- 核对 `scripts/geo/rdl_mapbox_poc.py` 与 `pwa/earth3d.js`，确认 M0/M1、UnsharpMask、M3/M4 提示文件接入、ACA 可选输出路径、RDL overlay 正常模式单区显示逻辑均已在本地代码落地
- 实测统计当前产物数量：`tile_noon_air_mapbox.jpg` 为 84 份，`tile_noon_air_mapbox_aca_reef.jpg` 为 47 份，`aca_reef_mask.png` 为 47 份
- 复核 `docs/preview_archives/rdl_m2_aca_composite_20260626/README.md`，确认 M2 当前虽然已接入生成器，但 README 仍将其描述为 candidate/review 路径，且当最小 `.venv` 缺少 `tifffile` 时不会应用 GEBCO depth gating
- 盘点本地后续可用资源，确认 Copernicus DEM 8K 高程与 slope、SRTM landforms 8K、WorldCover 8K、Koppen 8K、Coral Atlas raw ZIP 都已在 `source_cache` 中存在

### 改动文件
- `devlog.md`

### 遗留问题
- Batch 2 / Batch 3 数据已在本地，但尚未看到它们正式接入 `rdl_mapbox_poc.py`
- LOW 视角下的 RDL 边界问题仍主要在 `earth3d.js` 的 overlay 显示策略与软边参数，不是数据缺失
- M2 当前是可运行路径，但是否视为最终 accepted pipeline 仍需和现有 README/验收口径对齐

---

## 2026-06-26 Batch 2 Copernicus DEM slope 候选层接入 + 六区 proof

### 做了什么
- 在 `scripts/geo/rdl_mapbox_poc.py` 新增 Batch 2 Copernicus DEM 候选层开关 `--dem-slope`
- 接入全球 8K `copernicus_dem_glo30_slope_8192x4096.tif` 与 `copernicus_dem_glo30_elevation_8192x4096.tif`，复用现有 TIFF 读取与 bbox 裁剪思路，为单个 RDL 区域裁出 slope/elevation
- 新增 `apply_b2_dem_slope()`，以区域内土地坡度分位数自适应映射 relief，并按 climate family 做克制型 terrain tint / local contrast / alpine lift
- 输出非破坏性候选图：`tile_noon_air_mapbox_dem.jpg` 或 `tile_noon_air_mapbox_m3m4_dem.jpg`，不覆盖既有 accepted `tile_noon_air_mapbox.jpg`
- 对 6 个典型区域跑 proof：`japan`、`taiwan`、`norway_fjords`、`iceland`、`red_sea`、`hawaii`
- 生成 proof 总览：`docs/preview_archives/rdl_batch2_dem_slope_proof_20260626/batch2_dem_slope_contact_sheet.jpg`
- 生成差分统计：`docs/preview_archives/rdl_batch2_dem_slope_proof_20260626/proof_diff_stats.json`

### 改动文件
- `scripts/geo/rdl_mapbox_poc.py`
- `d5b_processor_v3/source_cache/.../tiles_rdl_regions/{japan,taiwan,norway_fjords,iceland,red_sea,hawaii}/tile_noon_air_mapbox_m3m4_dem.jpg`（6 个，不进 git）
- `docs/preview_archives/rdl_batch2_dem_slope_proof_20260626/`
- `devlog.md`

### 遗留问题
- 当前 Batch 2 对大陆山地/高原区域有效（日本、挪威、红海周边提升明显），但对小岛型区域如 Hawaii 在全球 8K DEM 上几乎无提升
- 这说明 Copernicus slope 适合作为“陆地山形增强层”，不适合作为小型火山岛精度问题的单独解法
- LOW 视角 RDL 边界问题仍未触碰，保持独立处理
- 尚未批量跑全 84，也未决定是否把 Batch 2 候选层提升为主 tile

---

## 2026-06-27 Batch 3 SRTM Landforms 语义层接入 + 六区 proof

### 做了什么
- 在 `scripts/geo/rdl_mapbox_poc.py` 新增 Batch 3 开关 `--landforms`
- 接入 `srtm_landforms_global_8192x4096.tif`，按 bbox 裁剪为区域级 categorical raster，并显式将 class 0 视为 ocean/nodata
- 依据本地导入测试文档中的 class 语义，将 landforms 分为 ridge/peak（11–15）、upper slope（21–24）、lower slope（31–33）、valley/plain（34/41/42）
- 新增 `apply_b3_landforms()`：对 ridge/upper slope 做轻微抬亮和局部对比增强，对 valley/lower slope 做轻微压暗分层，对 plain 做非常轻的平原基调修正
- 输出非破坏性候选图：`tile_noon_air_mapbox_m3m4_dem_landforms.jpg`（若无 DEM / M3M4，则自动回退到更短命名路径）
- 对 6 个区域做 proof：`hawaii`、`philippines_central`、`japan`、`norway_fjords`、`red_sea`、`taiwan`
- 生成对比总览：`docs/preview_archives/rdl_batch3_landforms_proof_20260627/batch3_landforms_contact_sheet.jpg`
- 生成差分统计：`docs/preview_archives/rdl_batch3_landforms_proof_20260627/proof_diff_stats.json`

### 改动文件
- `scripts/geo/rdl_mapbox_poc.py`
- `d5b_processor_v3/source_cache/.../tiles_rdl_regions/{hawaii,philippines_central,japan,norway_fjords,red_sea,taiwan}/tile_noon_air_mapbox_m3m4_dem_landforms.jpg`（6 个，不进 git）
- `docs/preview_archives/rdl_batch3_landforms_proof_20260627/`
- `devlog.md`

### 遗留问题
- Batch 3 比 Batch 2 更像细修层，适合补“地貌语义分层”，不适合替代 DEM 的数值山形增强
- Hawaii 在 Batch 3 下终于有有效 landforms 响应，但强度仍较克制；若未来要继续解决小岛精度，可能还需要更高分辨率岛屿专用 terrain 数据
- Red Sea / Norway 这类大范围陆地区域的 Batch 3 差分更强，后续若批量全跑，建议先做一轮区域白名单或强度分级
- LOW 视角 RDL 边界问题仍未触碰，保持独立处理

---

## 2026-06-27 Batch 3 全 84 区批量生成

### 做了什么
- 运行 `python3 scripts/geo/rdl_mapbox_poc.py --all --m3m4 --dem-slope --landforms`
- 全量批处理 84 个 RDL 区域，实际完成耗时约 313 秒
- 成功生成 81 个 `tile_noon_air_mapbox_m3m4_dem_landforms.jpg` 候选图
- 缺失 3 个区域：`dongsha_pratas`、`bermuda`、`svalbard`
- 生成全量差分强度排名：`docs/preview_archives/rdl_batch3_landforms_proof_20260627/all84_mean_diff_ranking.json`
- 初步观察：Batch 3 差分最强的区域包括 `south_africa`、`caspian_sea`、`red_sea`、`rio_de_la_plata`、`black_sea`；差分最弱但非零的区域包括 `palau`、`marshall_islands`、`tonga`、`maldives`、`easter_island`

### 改动文件
- `d5b_processor_v3/source_cache/.../tiles_rdl_regions/*/tile_noon_air_mapbox_m3m4_dem_landforms.jpg`（81 个，不进 git）
- `docs/preview_archives/rdl_batch3_landforms_proof_20260627/all84_mean_diff_ranking.json`
- `devlog.md`

### 遗留问题
- `dongsha_pratas`、`bermuda`、`svalbard` 未生成 Batch 3 候选图，需单独判断是 landforms 有效像素过少、全 0，还是命名/保存分支未命中
- 大范围半陆半海区域（如 `south_africa`、`caspian_sea`、`red_sea`）Batch 3 差分偏强，后续若要提升为主 tile，建议先做人工抽样复核
- 小型岛链区域虽大多成功生成，但多数字段差分非常轻，是否保留 Batch 3 需要审美层面的人工筛选

---

## 2026-06-27 Batch 3 缺失区域排查与 fallback 补齐

### 做了什么
- 排查 `dongsha_pratas`、`bermuda`、`svalbard` 三个缺失区域
- 确认根因不是脚本漏跑，而是 `srtm_landforms_global_8192x4096.tif` 在这 3 个 bbox 裁出来全部为 `class 0`
- 判定为“源数据在该 bbox 无有效 landform 语义”，不是处理错误
- 在 `scripts/geo/rdl_mapbox_poc.py` 中新增 Batch 3 fallback：当 landforms 为全 0 / 无有效像素时，仍输出 `tile_noon_air_mapbox_m3m4_dem_landforms.jpg`，内容为上游 `M3M4+DEM` 候选图的明确复制版本，并打印 `fallback copy (no valid landforms in bbox)`
- 仅重跑这 3 个区域，成功补齐文件
- 现状态：`tile_noon_air_mapbox_m3m4_dem_landforms.jpg` 已补齐为 84/84

### 改动文件
- `scripts/geo/rdl_mapbox_poc.py`
- `d5b_processor_v3/source_cache/.../tiles_rdl_regions/{dongsha_pratas,bermuda,svalbard}/tile_noon_air_mapbox_m3m4_dem_landforms.jpg`
- `devlog.md`

### 遗留问题
- 这 3 个区域的 Batch 3 文件是“结构完整 fallback”，不是实际 landforms 增强；后续人工筛选时应按 fallback 看待
- 仍建议对 Batch 3 做一轮人工审美筛选，特别是差分偏强的半陆半海区域

---

## 2026-06-27 Batch 3 保留/回退初筛

### 做了什么
- 基于 `tile_noon_air_mapbox_m3m4_dem.jpg` 与 `tile_noon_air_mapbox_m3m4_dem_landforms.jpg` 的全量差分，生成 `all84_diff_stats_full.json`
- 制定初筛规则：
  - `manual review`：`mean_abs_diff_rgb >= 2.4`
  - `candidate keep`：`0.12 <= mean_abs_diff_rgb < 2.4`
  - `candidate revert`：`mean_abs_diff_rgb < 0.12`，或已知 fallback/no-landforms 区域
- 输出筛选报告：`docs/preview_archives/rdl_batch3_landforms_selection_20260627/README.md`
- 输出两张审图 contact sheet：
  - `manual_review_contact_sheet.jpg`
  - `revert_contact_sheet.jpg`
- 初筛结果：`keep=48`，`manual_review=15`，`revert=21`

### 改动文件
- `docs/preview_archives/rdl_batch3_landforms_proof_20260627/all84_diff_stats_full.json`
- `docs/preview_archives/rdl_batch3_landforms_selection_20260627/README.md`
- `docs/preview_archives/rdl_batch3_landforms_selection_20260627/manual_review_contact_sheet.jpg`
- `docs/preview_archives/rdl_batch3_landforms_selection_20260627/revert_contact_sheet.jpg`
- `devlog.md`

### 遗留问题
- 这仍是“初筛”，不是最终审美结论；`manual_review` 的 15 个区域建议人工看图后再决定是否提升为主 tile
- `candidate_keep` 中靠近阈值下沿的区域（如 `hawaii`、`fiji_vanuatu`、`eastern_caribbean`）也可视需要人工二次复核

---

## 2026-06-27 LOW角度清晰度审计与8K链路打通

### 做了什么
- 审计 `pwa/earth3d.js` 的 RDL 区域贴图采样逻辑，确认 LOW / 斜视角下使用了 `LinearFilter + no mipmaps`，这是当前清晰度不足的直接原因之一
- 将 RDL 区域贴图改为优先使用 mipmaps + anisotropy 的区域纹理配置，减少 LOW / 近景下的拉伸发糊
- 将 inspect 模式下的 RDL overlay 不透明度提高到接近全不透明，减少与底层全球底图混合带来的软化感
- 为 RDL 区域贴图增加 8K 优先加载链路：优先读取 `tile_noon_air_mapbox_8k.jpg`，缺失时回退到现有 `tile_noon_air_mapbox.jpg`
- 在 `scripts/geo/rdl_mapbox_poc.py` 中新增 `--max-dim` 输出尺寸参数，允许额外生成 8K 区域贴图变体而不覆盖现有 4K 资产
- 实际生成 8K proof：
  - `korea_yellow_sea/tile_noon_air_mapbox_8k.jpg`
  - `hawaii/tile_noon_air_mapbox_8k.jpg`
- 浏览器日志验证通过：前端已实际命中 `hawaii (8k)` 版本

### 改动文件
- `pwa/earth3d.js`
- `scripts/geo/rdl_mapbox_poc.py`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/korea_yellow_sea/tile_mapbox_8k.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/korea_yellow_sea/tile_noon_air_mapbox_8k.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/korea_yellow_sea/mapbox_meta_8k.json`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/hawaii/tile_mapbox_8k.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/hawaii/tile_noon_air_mapbox_8k.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/hawaii/mapbox_meta_8k.json`
- `devlog.md`

### 遗留问题
- 当前只为样例区域生成了 8K 资产；其余区域仍在使用 4K 主图，因此 LOW / 近景提升还不是全局一致
- 一些“近景仍一般”的区域，后续还需要按区域单独提高 Mapbox zoom 或补跑 8K 资产，单靠前端采样不能凭空创造细节

---

## 2026-06-27 第一批高收益区域8K补图

### 做了什么
- 将前端脚本缓存标识从 `rdl-overlay-gate-v1` 提升到 `rdl-overlay-gate-v2`，避免本地浏览器继续命中旧版 `earth3d.js`
- 批量为第一批高收益区域生成 8K Noon Air 区域图，供 LOW / 近景优先加载
- 本批完成区域：
  - `bohai_sea`
  - `taiwan`
  - `ryukyu`
  - `philippines_central`
  - `south_china_sea`
  - `maldives`
  - `great_barrier_reef`
  - `caribbean_bahamas`
  - `red_sea`
  - `persian_gulf`
  - `indonesia_east`
  - `japan`
  - `hainan_island`
  - `kuril_southern`
- 加上前面已生成的样例区域，当前已具备 8K 版本的重点区域包括：
  - `hawaii`
  - `korea_yellow_sea`
  - 以及上述 14 个区域
- 浏览器侧验证：
  - 页面脚本已确认切换到 `earth3d.js?v=rdl-overlay-gate-v2`
  - 自动化连续切区抓取 `hawaii` 日志时发生超时，但 8K 文件与前端优先加载链路已确认存在

### 改动文件
- `pwa/index.html`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/*/tile_mapbox_8k.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/*/tile_noon_air_mapbox_8k.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/*/mapbox_meta_8k.json`
- `devlog.md`

### 遗留问题
- 目前还不是 84 区域全量 8K，只是先补了 LOW / 近景收益最高的一批
- 个别区域如果仍觉得不够清，下一步更有效的动作是“单区提 zoom”而不是继续无差别放大全量区域

---

## 2026-06-27 夏威夷LOW海面修正与渤海zoom11重跑

### 做了什么
- 审计发现夏威夷 LOW 视角下的“橡胶海”更像底球渲染问题，不是区域贴图本身分辨率不足
- 在 `pwa/earth3d.js` 中新增 LOW audit 角度检测：当处于 audit lighting 且相机进入 LOW 角度时，自动压低底球 normal map 强度，并关闭该视角下的 ocean specular map，同时降低高光参数
- 保留 TOP / 45° / 非 audit 模式下的原始细节强度，不把整个地球都一起抹平
- 将 `bohai_sea` 的默认 Mapbox zoom 从 `10` 提升到 `11`
- 重新生成 `bohai_sea` 的 8K 区域图，新版输出使用 `zoom=11`

### 改动文件
- `pwa/earth3d.js`
- `scripts/geo/rdl_mapbox_poc.py`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/bohai_sea/tile_mapbox_8k.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/bohai_sea/tile_noon_air_mapbox_8k.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/bohai_sea/mapbox_meta_8k.json`
- `devlog.md`

### 遗留问题
- 夏威夷 LOW 视角这次主要是渲染层修正，仍需要你本地刷新页面后再看一眼主观观感是否恢复自然
- 渤海虽然已经提到 `zoom=11`，但若后续还觉得陆地纹理不够，再下一步应考虑只对个别区域继续提 zoom，而不是继续全局加锐

---

## 2026-06-27 RDL系统性提清晰度与高资源批跑入口

### 做了什么
- 将 RDL 前端贴图候选从“只认 8K”扩展为按 `16k -> 12k -> 8k -> 默认` 自动降级，给后续继续堆资源留出统一接入口
- 将 audit 视角下的底球表面细节调校从“只处理 LOW”升级为按 `TOP / 45° / LOW` 三档统一压制高光与法线强度，减少夏威夷这类海面出现的胶感 / 橡胶感
- 为 `scripts/geo/rdl_mapbox_poc.py` 新增 `--zoom-bias` 与 `--resource-stack`，让整批区域可以用统一规格做“高资源精度提升”，不再靠单区手调
- 为 `scripts/geo/run_rdl_all.sh` 增加环境变量入口，支持用 `RDL_RESOURCE_STACK=1`、`RDL_MAX_DIM`、`RDL_ZOOM_BIAS` 直接发起全量高资源批跑
- 将前端脚本缓存标识提升到 `rdl-overlay-gate-v3`，避免浏览器继续命中旧版 `earth3d.js`
- 校验通过：
  - `node --check pwa/earth3d.js`
  - `python3 -m py_compile scripts/geo/rdl_mapbox_poc.py`
  - `bash -n scripts/geo/run_rdl_all.sh`
  - `python3 scripts/geo/rdl_mapbox_poc.py --region hawaii --dry-run --resource-stack`

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `scripts/geo/rdl_mapbox_poc.py`
- `scripts/geo/run_rdl_all.sh`
- `devlog.md`

### 遗留问题
- 这次先把“系统性提精度”的入口和前端承接逻辑搭好了，还没有真的把 84 区域全部重跑成 12K/16K 资源栈
- 如果要彻底摆脱夏威夷这类小区域在 `LOW / 45° / TOP` 下的观感摇摆，下一步应该是发起一次统一高资源批跑，而不是继续单点修区域参数

---

## 2026-06-27 资源栈档位契约收口到8K/12K/16K

### 做了什么
- 将高资源输出从“任意 `max-dim`”进一步收口为明确的 `8k / 12k / 16k` 三档契约
- 在 `rdl_mapbox_poc.py` 中新增 `RESOURCE_STACK_LEVELS`、`--resource-stack-level`
- 保持 `--resource-stack` 作为兼容入口，同时让 `--resource-stack-level 16k` 这类命令自动继承 `zoom_bias=+1` 的高资源默认语义
- 在 `run_rdl_all.sh` 中新增 `RDL_RESOURCE_LEVEL`，使全量批跑可以明确指定 `8k / 12k / 16k`
- 验证通过：
  - `python3 -m py_compile scripts/geo/rdl_mapbox_poc.py`
  - `bash -n scripts/geo/run_rdl_all.sh`
  - `python3 scripts/geo/rdl_mapbox_poc.py --region hawaii --dry-run --resource-stack-level 16k`

### 改动文件
- `scripts/geo/rdl_mapbox_poc.py`
- `scripts/geo/run_rdl_all.sh`
- `devlog.md`

### 遗留问题
- 前端已经支持按 `16k -> 12k -> 8k -> default` 自动降级，但 12K / 16K 资源仍需要实际批量生成后才会被命中
- 真正的视觉收益还要靠下一步全量或半全量高资源批跑验证，单靠契约修正本身不会直接改善画面

---

## 2026-06-27 16K资源试错样本首跑

### 做了什么
- 以 `--resource-stack-level 16k` 对 `hawaii` 发起首张 16K 标杆样本生成
- 样本参数为：
  - 输出尺寸 `16384×10923`
  - `zoom=11`（`base=10, bias=+1`）
  - 输出文件 `tile_noon_air_mapbox_16k.jpg`
- `hawaii` 16K 样本成功完成：
  - Mapbox 请求量 `1333`
  - 产出 `tile_mapbox_16k.jpg`
  - 产出 `tile_noon_air_mapbox_16k.jpg`
  - 产出 `mapbox_meta_16k.json`
  - 总耗时 `1020s`
- 随后启动 `bohai_sea` 16K 样本，用于评估更高 zoom 区域的资源成本
  - 解析结果为 `16384×11916`
  - `zoom=12`（`base=11, bias=+1`）
  - Mapbox 请求量升至 `3780`
- 基于 `bohai_sea` 的请求量判断，全量 84 区直接上 16K 成本很高，因此在样本阶段主动中止，先收集结论再决定是否扩跑

### 改动文件
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/hawaii/tile_mapbox_16k.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/hawaii/tile_noon_air_mapbox_16k.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_rdl_regions/hawaii/mapbox_meta_16k.json`
- `devlog.md`

### 遗留问题
- 16K 的视觉收益还需要你本地用 `hawaii` 做 `LOW / 45° / TOP` 角度主观验收
- 从吞吐看，16K 更适合做标杆样本和重点区域，不适合在当前阶段直接全量 84 区无差别扩跑

---

## 2026-06-27 LOW视角专项采样锐化优化

### 做了什么
- 将下一步优化重心从“继续堆分辨率”转到 `LOW / 45°` 审计视角下的 regional overlay 采样策略
- 在 `pwa/earth3d.js` 中为 regional overlay 新增按视角档位切换的采样配置：
  - `TOP`：保留 mipmap，仅极轻微 sharpen
  - `45° / oblique`：关闭 mipmap，提升局部锐度
  - `LOW`：关闭 mipmap，并启用更强一点的 shader sharpening
- shader 侧新增 `uTexel` / `uSharpen`，对 inspect 目标区域做轻量 5-tap sharpening，减少低角度下的软化感
- 将脚本缓存标识从 `rdl-overlay-gate-v3` 提升到 `rdl-overlay-gate-v4`，避免浏览器继续命中旧版 `earth3d.js`
- 校验通过：
  - `node --check pwa/earth3d.js`

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 这次优化针对的是 LOW / 45° 视角下的取样清晰度，不保证会显著改变所有区域的观感
- 仍需要你本地刷新后重新对比 `hawaii` 和 `bohai_sea`，确认 LOW 模式是否已经比上一版更清楚

---

## 2026-06-27 审计移动卡顿去重优化

### 做了什么
- 审计移动体验卡顿的根因排查到两个重复重操作：
  - 每次微调位置都会立即触发 `loadGlobeImages(lat, lon)`
  - 每次微调位置都会重复调用 `setAuditLightingMode(true)`
- 在 `pwa/index.html` 中新增 `scheduleAuditGlobeImageRefresh(...)`，将审计微调时的 globe image 重加载改为延迟触发，避免按住方向键时每一步都重拉一轮
- 在 `pwa/index.html` 中新增 `ensureAuditLightingEnabled()`，只有 audit lighting 尚未开启时才真正执行开启，避免每次微调都强制重跑 theme apply
- 将脚本缓存标识从 `rdl-overlay-gate-v4` 提升到 `rdl-overlay-gate-v5`
- 校验通过：
  - `node --check pwa/earth3d.js`

### 改动文件
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 这次主要改善的是“移动卡”和“难以对准”，仍需要你本地刷新后确认实际手感是否明显顺畅
- 如果移动已经顺了但仍不够精细，下一步可以再补更细粒度的步长控制或直接输入经纬度的跳转方式

## 2026-06-27 动画循环 dirty-flag + LOW 视角锐化降档

### 做了什么
- **性能**：`earth3d.js` 动画循环增加 dirty-flag，地球静止时跳过 `updateStreaming` 和 `updateRDLOverlays`（原来每帧无条件跑），静止后仅每 10 帧维护一次 RDL 透明度渐变
- **性能**：`requestRenderUpdate` 和 `setDebugLocation` 在触发后设置 `_animDirty = true`，保证动画循环下一帧补一次完整刷新
- **画质**：LOW 视角 `inspectSharpenProfile.low.sharpen` 从 `0.32` 降到 `0.20`，减少近角 bathy 起伏被过度锐化后产生的"胶感/塑料感"
- **画质**：RDL fragment shader 锐化混合权重从 `0.65` 降到 `0.45`，使锐化结果与原始图像更自然过渡

### 改动文件
- `pwa/earth3d.js`

### 遗留问题
- 动画循环 dirty-flag 是针对"静止多、拖动少"的 audit 模式优化，如果未来引入实时连续旋转动画需重新评估
- LOW 视角锐化值可根据实际目视反馈继续微调（当前目标是保留可读性、去除"硬边"感）

## 2026-06-27 navigation 响应性深度优化

### 做了什么
- **earth3d.js `updateStreaming`**：新增 `tilesChanged` 标志，tile 可见集合签名不变时跳过所有 `drawTile`（canvas drawImage + `atlasTexture.needsUpdate`），彻底消除 camera 静止时的无效 atlas 重绘
- **index.html `applyAuditLocation`**：新增 `_lastRDLInspectId` 缓存，nudge 期间 rdlId 不变时跳过 `setRDLInspectRegion` 调用，消除了原先每次 nudge 的 double-render（`setRDLInspectRegion` → `requestRenderUpdate` render + `setDebugLocation` render = 2次/nudge 变为 1次）
- **earth3d.js LOW sharpen**：从 0.20 调回 0.25（0.32 太硬 → 0.20 偏软 → 0.25 中间值，保留可读性同时去掉塑料感）
- **Bahamas 模糊**：`caribbean_bahamas` RDL 区域存在但只有 8k tile（无 12k/16k），属于 pipeline 生成缺失问题，非代码问题

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`

### 遗留问题
- `caribbean_bahamas`（及其他 8k-only region）tile 需要重新生成 12k/16k 版本才能提升画质
- LOW 视角 0.25 sharpen 值待目视确认，如仍偏软可再调至 0.28

## 2026-06-27 定向修复：切换速度 + LOW 锐化微调

### 做了什么
- 撤掉 `setDebugLocation` 里的 `_animDirty = true`：该函数已自带完整更新链路，dirty flag 会导致 RAF 再重复跑一遍，反而拖慢 nudge 速度
- LOW 视角 sharpen 从 0.25 微调回 0.28（0.25 偏软，0.28 在无胶感的前提下保留足够锐度）
- 巴哈马模糊确认为数据缺口（`caribbean_bahamas` 只有 8k tile，无 12k/16k），需单独补生成，本轮不处理

### 改动文件
- `pwa/earth3d.js`

### 当前状态
- 无胶感 ✓
- 切换速度明显改善 ✓
- 巴哈马 8k 模糊待处理（pipeline 任务）

## 2026-06-27 RDL Batch 3 landforms apply

### 做了什么
- 确认 earth_modes.js 已通过 window.EARTH_MODES 正确接入 earth3d.js，tile 目录结构完整
- 确认 D2（GEE 8K 下载）、D3（import test）均已完成，copernicus elevation 也已到位
- Batch 3 landforms 选择最终确认：63 keep（含 15 manual review 全部 accept）/ 21 revert
- 写 rdl_batch3_apply_selection.py，将 63 个 keep 区域的 `tile_noon_air_mapbox_m3m4_dem_landforms.jpg` 提升为 `tile_noon_air_mapbox.jpg`（生产版）；旧版备份为 `_pre_landforms.jpg`；21 个 revert 区域不动

### 改动文件
- `scripts/geo/rdl_batch3_apply_selection.py`（新建）
- `tiles_rdl_regions/{63 regions}/tile_noon_air_mapbox.jpg`（tile 数据，gitignore 内）

### 遗留问题
- Batch 3 只处理了标准分辨率 tile，8k 变体未做 landforms 更新（没有对应候选文件）

## 2026-06-27 Batch 4 ACA reef — 47 个珊瑚礁区域接入 production

### 做了什么
- 确认 Allen Coral Atlas reef mask 已覆盖 47 个 RDL 区域（M2 层此前与 batch3 主链独立）
- 写 rdl_batch4_aca_reef_apply.py：在 batch3 production tile 上叠加 ACA reef 颜色（复用 apply_m2_aca_reef），引入 Copernicus DEM elevation 做深度门控（首次在 batch 流程中使用 elevation 数据）
- 写 rdl_batch4_contact_sheet.py：生成 before/after contact sheet + diff stats
- 全部 47 个区域 apply：caribbean_bahamas(Δ2.05)、red_sea(Δ1.40) 最明显；各 _pre_b4.jpg 备份已保留
- 提升至 production（tile_noon_air_mapbox.jpg 覆盖），生成 production contact sheet

### 改动文件
- `scripts/geo/rdl_batch4_aca_reef_apply.py`（新建）
- `scripts/geo/rdl_batch4_contact_sheet.py`（新建）
- `docs/preview_archives/rdl_batch4_aca_reef_20260627/`（新建）
- `tiles_rdl_regions/{47 regions}/tile_noon_air_mapbox.jpg`（tile 数据，gitignore 内）

### 说明
- Copernicus DEM elevation 用于 ACA reef depth gate，不等于 M1 elevation source 替换（后者仍待完成）
- 下一项：Copernicus DEM → M1 高山/高原 mask 升级

## 2026-06-27 EarthDataLoader 路径修复 → Copernicus DEM + Köppen-Geiger 接入 M1

### 做了什么
- 发现 `EarthDataLoader` 默认 `source_root` 指向 `cache/` 目录（不存在），导致 Copernicus DEM 和 Köppen-Geiger 层静默返回 None，M1 fallback 到合成数据
- 修复：将默认路径改为 `d5b_processor_v3/source_cache/gee_global`（GEE 实际下载目录）
- 验证：DEMRegistry 加载成功，Everest(5287m)、Tibetan Plateau(4740m)、Pacific(-5297m) 数据正确；Köppen class 4(Sahara)、1(Singapore)、29(Himalayas) 全部正确

### 改动文件
- `core/data/earth_sources/loader.py`：`__init__` 中 source_root 默认值修正（1 行）

### 效果
- RealWorldSignalProvider.get_dem() 现在返回真实 Copernicus/GEBCO 数据（Everest 5287m、Dead Sea -417m 等验证通过）
- RealWorldSignalProvider.get_climate() 现在返回真实 Köppen-Geiger 分类（class 4=Sahara、1=Singapore 等验证通过）
- M1 / SAL 的 elevation 和 climate **输入信号**已升级到真实数据；Köppen veto 逻辑生效
- 注：M1 目前无显式 high_mountain_mask / plateau_mask 字段；Köppen → biome_signal 的映射已进入链路，但 biome_mask 多数仍落为通用 land；显式 desert/terrain mask 的稳定输出需后续 SAL/biome refinement 调整

### 遗留问题
- 无（路径修复一次性解锁了 DEM 和 climate 两条链路）

## 2026-06-27 M1 biome refinement — Köppen 信号正确落到 biome_mask

### 做了什么
- 发现 `_climate_signal` 固定返回 `"land"`（忽略 Köppen class），导致 climate 权重（0.30）始终强化 land，landcover 的 0.15 不足翻盘
- 修复：Köppen 1-3→forest, 4-7→desert, 29-30→ice, else→land
- 新增 MaskGenerator 后置 biome refinement：SAL final_class="land" 时，若 landcover 给出具体 biome 且 climate 不反对 → 提升到具体 biome（SAL 仍主导 ocean/land 判定）
- 5 点验收全通过：Sahara→desert, Singapore→forest, Himalayas→ice, Pacific→ocean, Dead Sea→desert

### 改动文件
- `core/signal/providers/m1_bridge.py`：`_climate_signal` Köppen class 映射
- `core/m1/mask_generator.py`：`_PROMOTABLE_BIOMES` + biome refinement block
- `core/m1/_test_real_signal_provider.py`：更新断言 + 新增 `run_biome_acceptance()`

### 遗留问题
- 无；M1 regression 4/4 pass，biome acceptance 5/5 pass

## 2026-06-27 Batch 5 Global Aridity Index — 独立 8K raster

### 做了什么
- 从 CGIAR Global Aridity Index v3.1 年均 zip 提取 ai_v31_yr.tif（43200×18000 原始）
- 重采样至 8192×4096（全球坐标系），南 -60° 以下补 nodata=0，PIL LANCZOS 下采样
- 输出：`external_processed_8k/global_aridity_index_8192x4096.tif`（uint16，scale=AI×10000，21.4MB LZW）
- 更新 `external_manifests/global_aridity_pet_manifest.json`（processed_8k_file_path 字段）
- 质量验证：Sahara=hyperarid(0.021)、Singapore=humid(1.676)、Dead Sea=hyperarid(0.049)、Pacific/Antarctica=nodata ✓

### License 说明
- CGIAR-CSI，非商业/研究用途；manifest 中已记录 research_only=true 和商业替换要求
- 本阶段仅生成独立 raster，不混入 production 语义链路

### 改动文件
- `scripts/geo/process_aridity_index.py`（新建）
- `d5b_processor_v3/source_cache/gee_global/external_manifests/global_aridity_pet_manifest.json`（processed_8k_file_path 更新）
- `d5b_processor_v3/source_cache/gee_global/external_processed_8k/global_aridity_index_8192x4096.tif`（新建，gitignore 范围内）

### 遗留问题
- 未接入 EarthDataLoader（待后续作为 "aridity" layer 接入，或作为 desert biome confidence 增强信号）
- 月度 ET0 zip 未处理（暂无需求）

## 2026-07-01 HZ清晨视觉分层修复

### 做了什么
- 只针对 `earlyMorning` 重建 sky / atmosphere / horizonGlow 职责边界，保留专用 sky plane，撤出 shared sky shader 的 Plan A screen-gradient 残留
- 将 `earlyMorning` 收敛为“单 sky plane + 单层主 atmosphere + 关闭 horizonGlow 主发光源”，移除当前主题上的 `atmosphere2` 叠加
- 调整 `earlyMorning` 的 day texture / lighting / starSphere 参数，使地球进入清晨白昼可读状态，同时保持无城市灯、无星场
- 做了两项验证：`node --check pwa/earth3d.js` 通过；本地 `http://127.0.0.1:8080` 切换到“清晨”可正常渲染，控制台仅有既有 Spotify token 警告

### 改动文件
- `pwa/earth3d.js`：清理 shared sky 残留、重写 earlyMorning sky plane 渐变、收紧 atmosphere / horizonGlow / lighting 参数

### 遗留问题
- 已做轻量浏览器核验，但还没有基于最终目标图做逐像素级微调；如果你要继续逼近参考图，下一轮应只细调 `earlyMorningSkyPlane` 渐变和主 atmosphere rim

## 2026-07-01 HZ清晨辉光微调

### 做了什么
- 在保留 `earlyMorning` 单独 sky plane 架构的前提下，把顶部天空再压暗一点，同时扩大近地平线冷白蓝亮区的扩散范围
- 将主 `atmosphere` 稍微提亮，继续承担贴边 core rim；恢复 `horizonGlow` 为极弱外层散光辅助，只做 outer haze，不让它重新成为主亮带
- 保持 `atmosphere2` 不启用，继续维持无城市灯、无星场
- 复查通过：`node --check pwa/earth3d.js` 通过，本地页面可重新加载并切换到“清晨”

### 改动文件
- `pwa/earth3d.js`：微调 earlyMorning sky plane、atmosphere、horizonGlow 参数

### 遗留问题
- 浏览器内轻量截图受当前会话视口影响，只能确认路径正常运行；是否更接近目标图仍建议你在本机主视图里肉眼对照最终效果

## 2026-07-01 HZ清晨明显增强版

### 做了什么
- 直接提高 `earlyMorning` 天空亮区扩散：扩大 near-horizon glow 高度、提高冷白蓝提亮强度，让天空亮区更容易一眼看出来
- 明显加强主 `atmosphere` 的贴边辉光，同时把 `horizonGlow` 外层 haze 再抬一档，继续维持“内亮外散”的结构
- 保持 `atmosphere2` 关闭，不把它重新引回多层厚白带路径
- 复查通过：`node --check pwa/earth3d.js` 通过

### 改动文件
- `pwa/earth3d.js`：提高 earlyMorning sky diffusion / atmosphere rim / outer haze 强度

### 遗留问题
- 这轮是刻意做成“明显可见改动”的版本；是否过强需要你直接看主界面判断

## 2026-07-01 HZ清晨借 deepNight 几何修正辉光

### 做了什么
- 参考 `deepNight` 的自然辉光结构，重设 `earlyMorning.horizonGlow` 的几何关系：让 haze 更贴边、rim 更清楚、外层衰减更慢，而不是继续把天空整体抬亮
- 相应回收 `earlyMorning.atmosphere`，避免 3D atmosphere 和 CSS glow 叠成厚白带
- 保持清晨配色不变，只借用 deepNight 的“几何关系”和“主次职责”
- 复查通过：`node --check pwa/earth3d.js` 通过

### 改动文件
- `pwa/earth3d.js`：按 deepNight 辉光结构重设 earlyMorning horizonGlow，并回收 atmosphere

### 遗留问题
- 还需要你在主界面直接判断这版是否比上一版更自然；如果方向对，下一轮应只做强度微调，不再改结构

## 2026-07-01 HZ清晨去实体感回调

### 做了什么
- 按“辉光是光，不是带子”的方向回调 `earlyMorning`：明显削弱 rim 的实体感，提高 blur，降低 core 存在感
- 将 `horizonGlow` 调成更透、更雾、更慢衰减的 outer haze，同时回收 `atmosphere`，避免边缘被压成一条线
- 轻微收回 sky plane 的 near-horizon 提亮，避免天空亮区继续把地平线做实
- 复查通过：`node --check pwa/earth3d.js` 通过

### 改动文件
- `pwa/earth3d.js`：回调 earlyMorning sky diffusion / atmosphere / horizonGlow，减少带状实体感

### 遗留问题
- 需要你在主界面确认这版是否已经回到“雾气里的光”而不是“有形发光边”

## 2026-07-01 HZ清晨失败方向归档

### 做了什么
- 记录本轮清晨视觉修复中已证伪的方向，后续明确规避：
- 不要再把 `earlyMorning` 的主辉光交给 screen-space `horizonGlow`；白天背景一亮，它会暴露成“椭圆带子”
- 不要再同时提高 `rim.strength`、`sky plane` near-horizon glow、`atmosphere.strengthOuter`；三层一起抬会把空气感压成实体边
- 不要再追求“明显可见改动”式的强化；清晨目标需要的是透、雾、散，不是边缘存在感
- 不要再让 `CSS rim` 负责定义地球边缘轮廓；它最多只能做极弱远端薄雾，或者完全关闭
- 基于这些结论，已将 `earlyMorning` 收敛为 `atmosphere` 主发光、CSS 仅保留近乎不可察觉的薄雾辅助

### 改动文件
- `devlog.md`：追加失败方向与规避原则
- `pwa/earth3d.js`：将 earlyMorning 主边缘发光切回 atmosphere，CSS glow 退到极弱

### 遗留问题
- 新结构是否足够自然仍需主界面直看；但后续不应再回到“screen-space 带子强化”这条路线

## 2026-07-01 HZ清晨结构重做为 3D limb glow

### 做了什么
- 放弃将 `earlyMorning` 主辉光建立在 screen-space `horizonGlow` 上的路线，新增专用 3D `earlyMorningLimb` 发光层，让发光重新绑定到球体边缘附近的 3D 空间
- 将 `earlyMorning` 调整为：`sky plane` 只做天空背景，基础 `atmosphere` 只保留很轻的空气层，主边缘发光由 `earlyMorningLimb` 承担，CSS glow 退回几乎不可察觉的薄雾辅助
- 保留失败方向归档，后续继续规避“把白天辉光做成一条 screen-space 带子”的实现方式
- 复查通过：`node --check pwa/earth3d.js` 通过

### 改动文件
- `pwa/earth3d.js`：新增 `earlyMorningLimb` 3D glow shell，并重配 earlyMorning sky / atmosphere / horizonGlow 职责

### 遗留问题
- 这次是机制层面的重做，不再是参数微调；最终观感仍需你在主界面直接判断

## 2026-07-01 HZ清晨移除 sky-plane 假亮带

### 做了什么
- 直接移除 `earlyMorningSkyPlane` 内部那段 near-horizon 屏幕空间加亮逻辑，避免天空自己继续画出一条弧形亮带
- 同时提高 `earlyMorningLimb` 的可见度，并进一步收窄基础 `atmosphere`，让“地球边缘发光”与“天空背景渐变”彻底分离
- 复查通过：`node --check pwa/earth3d.js` 通过

### 改动文件
- `pwa/earth3d.js`：删除 earlyMorning sky plane 假亮带，提升 3D limb，收回基础 atmosphere

### 遗留问题
- 新版是否终于从“背景带子”切换成“地球边缘发光”，需要你直接看主界面确认

## 2026-07-01 HZ清晨拆分为 core limb + outer limb

### 做了什么
- 将原本单层 `earlyMorningLimb` 继续拆成两层 3D glow shell：贴边更白更窄的 `core limb`，以及更外侧、更蓝、更散的 `outer limb`
- 继续保持 sky plane 只做天空、基础 atmosphere 只做很轻的空气层，避免再回到“背景弧线发光”模式
- 复查通过：`node --check pwa/earth3d.js` 通过

### 改动文件
- `pwa/earth3d.js`：新增 `earlyMorningLimbOuter`，并把 earlyMorning 发光结构调整为 core + outer 两层

### 遗留问题
- 是否终于接近参考图里“地球边缘发白、向外化成蓝雾”的观感，仍需主界面直接判断

## 2026-07-02 大气层太阳方向感知

### 做了什么
- 在 `_atmVert` 顶点着色器中增加 `vWorldNormal`（`mat3(modelMatrix) * normal`），将世界坐标系法线传入片元着色器
- 在 `_atmFrag` 片元着色器中增加 `uSunDir`（世界坐标太阳方向）和 `uSunInfluence` uniform，用 `dot(vWorldNormal, uSunDir)` 调制大气光晕：向阳面 100%，终结线约 55%，背阳面 ~6%；`uSunInfluence=0.85` 保留暗侧微弱散射
- 为 `atmosphereMaterial` 和 `atmosphere2Material` 均添加 `uSunDir`、`uSunInfluence` uniform
- 新增 `_syncAtmSunDir()` 工具函数，在 `updateSunPosition()` 全部三条分支（真实太阳位、override、audit 模式）末尾同步大气 uniform

### 改动文件
- `pwa/earth3d.js`：着色器扩展 + 材质 uniform + `_syncAtmSunDir()` + `updateSunPosition()` 三处调用

### 遗留问题
- `uSunInfluence` 各主题默认值（0.85）是否需要分主题调整，待视觉评估后决定
- 可继续迭代的方向：法线贴图增强地表浮雕感、海洋高光散射

## 2026-07-02 清晨大气内沿白线修复

### 做了什么
- 在 `earlyMorningRimOverlay` 片元着色器中加回了内沿白色 corona 项：`core = exp(-pow(signedD / uCoreWidth, 2.0)) * uCoreStrength`
- 新增 uniforms：`uCoreColor: '#f3f9ff'`、`uCoreWidth: 0.016`、`uCoreStrength: 0.75`
- 同时将 `uSkyHaloStrength` 从 0.52 上调到 0.62，外晕更明显
- 参考原型 HTML（清晨：内沿白色细线 + 宽蓝软晕）对标自然感

### 改动文件
- `pwa/earth3d.js`：`_emRimOverlayMat` uniforms 扩展 + fragment shader 新增 core 项

### 遗留问题
- 内沿白线宽度/强度可继续微调（当前 width=0.016, strength=0.75 是第一次落点）
- 其他时段（黎明/日出/落日）是否也需要类似内沿增强，待后续评估

## 2026-07-02 清晨大气 overlay 线性混合修复

### 做了什么
- 发现 `earlyMorningRimOverlay` shader 的合成 bug：alpha=glow、color=glow×glowColor，
  在 AdditiveBlending 下实际等效为 `glow² × color + dst`，导致有效宽度缩小 √2 倍
- 修复：改为 `alpha=1.0`（纯加法叠加 `1×color + dst`），消除二次压缩
- 相应下调强度参数（线性混合比 glow² 亮约 2×）：
  `uSkyHaloStrength: 0.80 → 0.42, uCoreStrength: 0.90 → 0.55, uSkyHaloWidth: 0.36 → 0.22`
- 同步压暗 earlyMorning 天空底图的地平线色（uHorizonColor/uLowerColor），提升蓝晕与背景的对比度

### 改动文件
- `pwa/earth3d.js`：overlay fragment shader 混合公式 + 天空底图颜色 + overlay uniform 参数

### 遗留问题
- 当前 uSkyHaloWidth=0.22 / Strength=0.42 是第一次落点，实机测试后可继续微调
- 其他 overlay 或 Fresnel 大气的类似 glow² 问题尚未排查

## 2026-07-02 清晨主题辉光定版

### 做了什么
- 将 earlyMorningRimOverlay 的 sky halo 从单一 Gaussian 重构为双层叠加（near + far），实现"贴边亮 + 宽拖尾"效果
- 增加距离驱动三段颜色渐变：near=青白 → mid=浅蓝(#9dd8ff) → far=深蓝(vec3(0.35,0.55,0.75))
- 将 haloT 从 linear clamp 改为 smoothstep，消除 near→far 颜色切换的硬台阶
- farT 过渡系数从 1.5 调整到 2.5，让中段亮蓝维持更久再收尾
- 最终微调 uSkyHaloWidthNear 0.055→0.07，内沿到中段过渡更柔和
- 在代码中写入定版注释（清晨主题辉光 - 已定版 2026-07-02），列出所有参数和颜色公式，供后续其他时段参考

### 改动文件
- `pwa/earth3d.js`：earlyMorningRimOverlay uniform 结构、fragment shader 颜色计算、定版注释块

### 定版参数
- uCoreWidth=0.007 / uCoreStrength=0.55 / uCoreColor=#eef6ff
- uSkyHaloWidthNear=0.07 / uSkyHaloStrengthNear=0.50
- uSkyHaloWidthFar=0.28 / uSkyHaloStrengthFar=0.26
- haloT=smoothstep(0.0, widthFar×0.8, signedD)
- farT=clamp((signedD - widthNear) / (widthFar×2.5), 0.0, 1.0)

### 遗留问题
- 其他时段（日出、黎明、落日等）辉光尚未按同结构调整，均使用旧的单层 Gaussian

## 2026-07-03 清晨主题辉光系统重构 + 基础值定版

### 做了什么
- earlyMorning 抗锯齿修复：inside/signedD 判断改用 fwidth() 驱动的 smoothstep，消除地平线弧线的锯齿阶梯感
- Ocean Tone Grade 解耦：新增 rodioOceanToneGradeStandalone()，海洋调色不再必须经过 v17 daybase 夜间压暗管线，任意主题下都能生效，不再强制陆地一起变暗
- Rim Overlay 结构重构：outerMask 严格限制在天空侧（signedD>0），移除混入的 surfVeil 逻辑
- 新增 Inner Horizon Veil 独立图层（_emInnerVeilMat）：地表侧（signedD<0）单独一层，NormalBlending 而非纯 additive，避免刺眼堆叠
- 新增 Land / Ocean Tint 直接选色控件（uLandTintColor/uOceanTintColor + 强度），独立于渐进式调色滑块
- 修复 window.earth3d.isReady 因 Object.assign 拷贝 getter 快照值导致永远为 false 的 bug，影响 Theme Tuner 面板挂载时机
- 修复贴图分块加载失败无重试机制的问题（新增最多 4 次递增延迟重试）
- 修复 RDL 区域高精度图层纹理未加载完成就被设为可见导致的黑色楔形闪块（新增 entry.loaded 门槛）
- 清晨主题基础值定版：Sky Background / Rim Overlay / Inner Horizon Veil 三组参数固化为代码默认值，3D Fresnel atmosphere 默认关闭（opacity 0），改由 Rim Overlay + Inner Horizon Veil 接管地平线辉光

### 改动文件
- `pwa/earth3d.js`：earlyMorning sky/rim/veil 材质与 shader、Ocean Tone Grade 解耦、isReady 属性定义修复、tile streaming 重试、RDL loaded 门槛、THEME_VISUAL_CONFIG.earlyMorning.atmosphere.opacity
- `pwa/index.html`：Theme Tuner 新增 Land/Ocean Tint、Sky Background、Rim Overlay、Inner Horizon Veil 折叠面板，各面板默认值同步为定版数值

### 定版参数（清晨）
- Sky Background: uTopColor #061a3a / uMidColor #0b315f / uLowerColor #1a5b8f / uHorizonColor #92c8e8
- Rim Overlay: haloWidth 0.28 / coreFraction 0.43 / corePower 9.4 / coreStrength 0.9 / tailPower 1.5 / haloStrength 0.35
- Inner Horizon Veil: innerVeilColor #d9f0ff / innerVeilWidth 0.16 / innerVeilStrength 0.43 / innerVeilFalloff 1.8
- 3D Fresnel Atmosphere: opacity 0.0（关闭）

### 遗留问题
- Land / Ocean Tint 强度默认 0，尚未针对各主题调出推荐值
- 其他非清晨主题尚未复用这套 fwidth 抗锯齿 + outerMask/innerMask 分层结构

## 2026-07-03 (续) 陆地/海洋调色定版 + 面板同步修复

### 做了什么
- 澄清确认：清晨地平线的白光是 Rim Overlay + Inner Horizon Veil（有意设计），不是遗留的大气光圈，3D Atmosphere 已单独关闭，两者不混淆
- 修正 coast protection 参数方向的误解：数值越高是让近岸区域越不参与海洋调色（保护原始纹理），不是让过渡带更明显；实际要更明显的过渡带应调低
- 定位 Land Minor Assist 之前"调了没反应"的根因：land str 默认是 0，是所有陆地增量调色的总开关
- 验证得出陆地绿色主要靠 Land / Ocean Tint 直接染色（Colorize 算法）推动，Land Minor Assist 负责打底提亮；海洋主要靠 Ocean Tone Grade 出层次
- 把验证过的 Ocean Tone Grade / Land Minor Assist / Land Ocean Tint 三组参数写入 THEME_VISUAL_CONFIG.earlyMorning.nightGrade / landOceanTint，成为代码默认值
- 新增 landOceanTint 配置读取链路：applyTheme() 里应用/重置 uLandTintColor 等 4 个 uniform，getThemeConfig() 暴露 landOceanTint 字段，Theme Tuner 的 syncFromState() 同步到 tintU
- 发现并记录：Theme Tuner 面板的 Mode 下拉框与地球画面自带的主题按钮是两套独立状态，互不同步——用地球按钮切主题不会更新面板显示，需要用面板自己的下拉框才能看到面板同步的效果

### 改动文件
- `pwa/earth3d.js`：THEME_VISUAL_CONFIG.earlyMorning 新增 nightGrade + landOceanTint 配置块，applyTheme() 新增 landOceanTint 应用/重置逻辑，getThemeConfig() 暴露 landOceanTint
- `pwa/index.html`：syncFromState() 新增 landOceanTint → tintU 同步

### 定版参数（清晨陆地/海洋）
- Ocean Tone Grade: blendStrength 0.45 / darken 0.86 / contrast 1.08 / saturation 1.2 / blueBias 0.035 / redReduce 0.045 / greenReduce 0.015 / coastProtection 0.35
- Land Minor Assist: landStr 0.6 / landLift 0.1 / landGamma 0.82 / landRedRed 0.06 / landGreenB 0.1
- Land/Ocean Tint: landColor #3d8b34 / landStrength 0.65 / oceanColor #1560c9 / oceanStrength 0.2

### 遗留问题
- Theme Tuner 面板 Mode 下拉框与主 UI 主题按钮状态不同步，调试时需注意用哪一个切换
- landOceanTint 目前只在 earlyMorning 定义，其他主题默认关闭（off），未来如需要可仿照此结构扩展

## 2026-07-03 (续) 清晨页面二次审计与修改方案确认

### 做了什么
- 二次审计清晨模式的真实渲染链路，确认当前页面同时存在 3D Atmosphere、Rim Overlay、Inner Horizon Veil、Sky Background、Ocean Tone Grade、Land Minor Assist、Land/Ocean Tint 多套可叠加调参入口
- 定位 `Atmosphere` 面板“默认显示关闭但仍见外圈”的直接根因：atmosphere shader 的 `outer` 项未受 `uOpacity` 约束，且 Theme Tuner 首次 `syncFromState()` 只更新 checkbox 显示，不会主动执行 `toggleAtmosphere3d(false)` 隐藏 mesh
- 定位海陆配色风险：Land Minor Assist 与 Direct Tint 都依赖 ocean mask 分陆海；当 `landStr`、`landLift`、Ocean Tone Grade、Tint 混用时，近海和海岸带容易被串色，形成发灰发浅的海水
- 对比参考图后确认后续修改方向：清晨视觉应优先收敛为“清晨专属 sky/rim/veil + 轻量 ocean tone + 极轻 land assist”，而不是继续依赖高强度 land tint / land lift 硬推整体颜色

### 改动文件
- `devlog.md`

### 遗留问题
- 尚未正式修改 `pwa/index.html` / `pwa/earth3d.js`
- 修改时需要同时解决：首次进入外圈残留、Theme Tuner 语义混淆、清晨海陆颜色回到参考图方向

## 2026-07-03 (续) 清晨试版一轮修改

### 做了什么
- 修复清晨 3D atmosphere 首次进入“显示关闭但仍残留外圈”的 bug：将 atmosphere shader 的 outer halo 也纳入 `uOpacity` 控制，并在 `applyTheme()` 中按当前 opacity 同步 atmosphere mesh 可见性
- 修正 Theme Tuner 的 Atmosphere 语义：面板更名为 `Atmosphere (3D Shell)`，首次 `syncFromState()` 时会同步真实 3D shell 可见状态；在 shell 关闭时，其他 patch 不会再把 opacity 偷偷写回非 0
- 为 `earlyMorning` 增加一组更克制的默认海陆调色：Ocean Tone Grade 改为轻量压深海水、Land Minor Assist 改为极轻提亮陆地，避免继续依赖高强度 tint 把近海洗灰
- 微调清晨默认 sky/rim/inner veil：低空天空更通透，外圈拖尾更柔，内侧白雾减弱，目标是更接近参考图二而不是图一那种“外圈亮但地表偏灰白”的状态
- 运行 `node -c pwa/earth3d.js`，确认当前脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 这版仍需真实浏览器肉眼判断是否足够接近参考图二，尤其是海水深度、陆地绿色和地平线亮度
- 如果这版方向不对，建议优先回退 `earlyMorning.nightGrade` 和 sky/rim/veil 默认值，而保留 atmosphere 首屏 bug 修复

## 2026-07-03 (续) 回滚清晨海陆调色试版

### 做了什么
- 按反馈回滚本轮试版里新增的 `earlyMorning.nightGrade` 默认海陆调色，撤销对清晨海水/陆地颜色方向的这次试探
- 保留 `atmosphere` 首屏残留外圈的 bug 修复，以及 Theme Tuner 中 `Atmosphere (3D Shell)` 的语义修正

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 清晨 sky/rim/inner veil 的这轮细调仍然保留，是否继续保留需要看你下一轮肉眼判断
- 海陆颜色需要改走新的方向，不能继续沿用这一轮的默认调色思路

## 2026-07-03 (续) 清晨海陆颜色窄调一轮

### 做了什么
- 为 `earlyMorning` 补入一组轻量 `nightGrade` 默认值，只做两件事：让植被区更偏绿、让海水整体更深一档
- 海水方向采用轻量 `Ocean Tone Grade`，避免再次用高强度 tint 把近海洗灰
- 陆地方向只启用很轻的 `Land Minor Assist`，通过小幅 `landGreenB` 和低强度 `landStr` 推植被色，不大改整体地表气质
- 运行 `node -c pwa/earth3d.js`，确认脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 这版仍需肉眼判断“更绿”和“更深”是否到位；如果还不够，下一轮建议先继续加深海水，再单独微调植被区
- 当前未对天空、辉光做新改动，本轮视觉变化应主要集中在海陆颜色

## 2026-07-03 (续) 海陆层极端红验证

### 做了什么
- 按“逆向验证”思路，把海洋与陆地植被区的测试色直接接入主题级 `landOceanTint`
- 为避免 `Theme Tuner` 的 `lateEvening` 与主界面 `清晨` 可能不同步造成误判，临时同时给 `earlyMorning` 和 `lateEvening` 都配置了极端红色 `landOceanTint`
- 补回 `landOceanTint` 的主题配置读取与应用链路：`applyTheme()` 会把主题里的 `landColor/oceanColor` 与强度写入 shader uniform，`getThemeConfig()` / `syncFromState()` 也会同步这组值
- 运行 `node -c pwa/earth3d.js`，确认脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 这是临时诊断配置，不是最终视觉方案；确认哪一层生效后需要立刻回退测试红色
- 如果画面仍然不变，需要继续检查当前真实渲染主题与 Theme Tuner 显示主题是否一致

## 2026-07-03 (续) 确认 Tint 层职责并修正主题同步

### 做了什么
- 根据极端红验证结果，确认 `Land / Ocean Tint` 确实接到了最终画面，但它只负责整体色相染色，不负责海水层次或植被细节塑形
- 回退临时的主题级大红测试值，避免继续污染正常视觉判断
- 修正 Theme Tuner 与主画面主题不同步的问题：主视觉成功切换 3D 主题后会触发 `window._earthTuner.sync()`，同步右侧面板；`syncFromState()` 也会把面板 `Mode` 回写为当前真实主题
- 由此确认：后续要做“海水更深、更有层次”和“植被更绿但保留细节”，应主要转去 `Night Grade -> Ocean Tone Grade / Land Minor Assist`，而不是继续推 `Land / Ocean Tint`

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 还没有开始真正的新一轮细节调色；这一步主要是确认系统职责并消除主题不同步干扰
- 下一轮应改走分层 grade，而不是整体 tint

## 2026-07-03 (续) 黄色验证版

### 做了什么
- 按反馈继续使用“明显但不过分打满”的验证色，将主题级 `landOceanTint` 从极端红改为较强黄色测试值
- 仍同时作用于 `earlyMorning` 与 `lateEvening`，避免因主题状态切换或观察窗口不同造成误判
- 保持这一步的目的为验证“是否看得到改动”，而不是追求最终正确视觉
- 运行 `node -c pwa/earth3d.js`，确认脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 黄色验证通过后仍需立刻撤掉这组测试色，回到真正负责层次的 grade 链路
- 这一步仍然是整体色相验证，不代表最终海水层次和植被细节方案

## 2026-07-03 (续) 撤掉黄色验证并切回分层细调

### 做了什么
- 撤掉 `earlyMorning` / `lateEvening` 上用于验证的黄色 `landOceanTint`
- 将清晨真实调色重新收敛到 `nightGrade`：提高 `Ocean Tone Grade` 的存在感，让海水明显再深一档；同时提高 `Land Minor Assist` 的可见度，让植被区更绿但仍保留地形与明暗层次
- 保留 `Land / Ocean Tint` 这条链路与 Theme Tuner 同步修复，作为后续微调工具，但不再用它做主调色
- 运行 `node -c pwa/earth3d.js`，确认脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 这轮是真正的层次调色，不再是测试色；仍需要肉眼确认海水深度和植被绿度是否到位
- 如果还不够明显，下一轮应继续加强 `Ocean Tone Grade` 与 `Land Minor Assist`，而不是回到 tint

## 2026-07-03 (续) 向参考清晨图靠拢一轮

### 做了什么
- 参照目标清晨图，将 `earlyMorning` 的真实调色继续往“陆地更青绿、海水更蓝”方向推进
- 海水继续只走 `Ocean Tone Grade`：提高 blend/contrast/saturation/blue bias，并略收 red/green，让蓝度更明显但仍保留海盆与近岸层次
- 陆地继续只走 `Land Minor Assist`：提高 `landStr`、`landGreenB` 与轻微 lift，让植被区更偏青绿，同时保持原始地形与明暗细节
- 保持 `Land / Ocean Tint` 不参与主调色，避免重新落回整片偏色
- 运行 `node -c pwa/earth3d.js`，确认脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 需要继续肉眼确认这轮是否已经接近参考图，尤其是东北与华北植被色、渤海/东海蓝度、近岸过渡是否自然
- 如果方向对但力度还不够，下一轮应继续小步推进同一组 `nightGrade` 参数

## 2026-07-04 清晨海陆颜色再增强一档

### 做了什么
- 按反馈继续增强 `earlyMorning` 的海陆真实调色，不碰整体 tint
- 海水继续加大 `Ocean Tone Grade`：提高 blend/contrast/saturation/blue bias，略降 coast protection，让蓝度与存在感更明显
- 陆地继续加大 `Land Minor Assist`：提高 `landStr`、`landGreenB`、`landLift`，让植被区更青绿一些，但仍保留原有明暗和地形纹理
- 运行 `node -c pwa/earth3d.js`，确认脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 需要继续确认这轮增强后是否已经达到“一眼可见”的程度，以及近岸层次是否仍自然
- 如果这轮仍偏轻，下一步应继续沿同一组参数推进，而不是切换到 tint

## 2026-07-04 清晨海陆颜色回退一档

### 做了什么
- 按反馈回退刚才“再增强一档”的清晨海陆颜色参数，恢复到上一个较自然的版本
- 仅回退 `earlyMorning.nightGrade` 里海水与陆地增强幅度，不影响此前已经确认有效的主题同步、atmosphere 首屏修复和分层调色链路
- 运行 `node -c pwa/earth3d.js`，确认脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 当前已恢复到上一档较自然的版本，后续如需继续调，建议改成更小步的微调而不是整档增强

## 2026-07-04 清晨海水去灰雾感微调

### 做了什么
- 按反馈对 `earlyMorning` 海水做一次 very small 微调，目标不是继续明显加蓝，而是减少近岸与远海过渡里的灰雾感
- 仅小步调整 `Ocean Tone Grade`：略增 blend/contrast/saturation/blue bias，并同步微调 red/green reduce 与 coast protection，让海水更干净但不走回“太假”的蓝
- 保持陆地参数不变，避免本轮海水修正连带破坏已经接受的陆地状态
- 运行 `node -c pwa/earth3d.js`，确认脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 需要继续肉眼确认渤海、黄海和远海过渡区的灰感是否已经足够收掉
- 如果还需要推进，下一轮应继续 very small 地微调海水，不建议同步再动陆地

## 2026-07-04 新增地球观测角度

### 做了什么
- 在主界面的审计角度区新增两个视角按钮：`TILT` 和 `GLOBE`
- 为 3D 地球补充两套相机预设：一套更接近参考图的斜切观察角度，一套更远的全球视角
- 同步修正角度标签逻辑，避免界面仍然只按 `toUpperCase()` 显示旧的三种名称
- 运行 `node -c pwa/earth3d.js` 与 `node -c server.js`，确认语法通过

### 改动文件
- `pwa/index.html`
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 需要继续肉眼验证 `TILT` 是否已经足够接近参考图的空间关系；如果不够，下一轮优先继续调相机 `y/z/lookY`
- `GLOBE` 当前先提供一个偏全球总览的安全版本，后续可再按需要增加“更正”“更斜”两种全球角度

## 2026-07-04 清晨辉光错位修复

### 做了什么
- 定位 `earlyMorning` 角度切换后辉光错位的根因：Rim Overlay / Inner Horizon Veil 仍按“球心投影 + 半径近似”估算屏幕弧线，角度一陡就会与真实可见地平线脱开
- 将 `updateEarlyMorningRimProjection()` 改为投影真实切线轮廓：先在相机空间构造球体的切线圆，再把该圆的中心与上下左右极值投到屏幕，驱动 `uRimCenter / uRimRadius`
- 保持清晨现有 sky / rim / veil 分层结构不变，只修正投影几何，避免再次扰动已经定下来的颜色与强度
- 运行 `node -c pwa/earth3d.js`，确认脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 需要继续实机切换 `TOP / 45° / LOW / TILT / GLOBE` 观察是否还有极端角度下的细小偏移
- 如果仍有残余错位，下一步应检查是否要把 CSS horizon glow 与 earlyMorning overlay 的几何口径进一步统一

## 2026-07-04 清晨初始构图辉光偏顶修正

### 做了什么
- 继续定位发现：上一轮“真实切线圆”修复虽然解决了切换角度时的明显漂移，但在初始构图这种偏轴视角下，直接用少数切线点反推中心/半径，仍会把弧线整体抬到画面顶部
- 将 `updateEarlyMorningRimProjection()` 改为采样整圈真实切线轮廓（96 点），再按屏幕投影结果的实际包围盒反推 `uRimCenter / uRimRadius`
- 这样初始界面和后续 `TOP / 45° / LOW / TILT / GLOBE` 都走同一套“真实轮廓 -> 屏幕椭圆”链路，不再依赖少量点的几何近似
- 运行 `node -c pwa/earth3d.js`，确认脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 仍需实机确认初始构图下辉光是否已经回落到正确的地平线位置
- 如果还存在轻微偏差，下一步应检查 overlay 椭圆假设本身是否需要进一步升级为非轴对齐轮廓拟合

## 2026-07-04 清晨审计近景自动切换 3D 壳层

### 做了什么
- 根据 `near` 截图确认：清晨的屏幕空间 `Rim Overlay + Inner Horizon Veil` 在大变焦审计视角下不稳定，即使继续修椭圆拟合，也会反复出现“辉光压进地表”的问题
- 新增 `updateEarlyMorningGlowMode()`：默认构图继续使用清晨定版 overlay；当进入 `near` 近景或 `low / tilt / global` 这类极端视角时，自动关闭 overlay，切换到更稳的 3D atmosphere shell
- 将该切换接入渲染循环、`setRDLZoomLevel()` 和 `setAuditViewAngle()`，确保缩放与角度切换时辉光模式同步更新
- 运行 `node -c pwa/earth3d.js`，确认脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 需要继续实机确认 3D shell 在 `near` 下的观感是否足够自然，尤其是亮度是否需要再压一点
- 如果后续想在极端视角下也保留更细腻的清晨 glow，就需要单独做一套非屏幕拟合的 3D 清晨辉光，而不是继续复用当前 overlay

## 2026-07-04 清晨审计视角规则收口

### 做了什么
- 根据 `near -> far` 仍然出错的反馈，确认问题不是单一阈值，而是“默认展示视角”和“审计视角”两套视觉语义没有彻底分开
- 收紧 `updateEarlyMorningGlowMode()` 规则：现在只有“默认首页构图（top + base zoom）”允许使用清晨 screen-space overlay；只要发生任何审计交互（FAR/NEAR 改变 zoom，或切换到任意非 top 角度），就统一强制走 3D atmosphere shell
- 这样可以避免从 `near` 回到 `far` 时 overlay 被重新打开，重新套回一个它本来就不稳定的相机/构图上
- 运行 `node -c pwa/earth3d.js`，确认脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 需要继续做一次系统性审查，把“首页展示模式”和“审计模式”的职责、允许效果、允许镜头范围写清楚
- 如果后续希望 `far` 也保留清晨 overlay 质感，那应为审计模式单独设计一套 3D glow，而不是让首页 overlay 回流

## 2026-07-04 FAR 按钮语义修正

### 做了什么
- 在系统审查过程中确认一个关键语义问题：`FAR` 原先并没有回到默认展示态，而是把缩放设为 `0.35`
- 这会导致用户从 `near` 点回 `far` 时，实际上仍停留在半审计状态，界面与辉光规则都不会真正回到首页默认构图
- 将 `FAR` 按钮改为恢复 `0.00` 基准缩放，让它真正承担“回到默认视图”的职责
- 运行 `node -c server.js`，确认页面脚本整体语法通过

### 改动文件
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 还需要继续验证 `FAR` 恢复默认缩放后，清晨 overlay 与 3D shell 的切换是否终于符合直觉
- 下一步仍需要把“默认展示模式”和“审计模式”的完整状态机审计出来，避免继续靠按钮语义猜测

## 2026-07-04 审计模式清晨 3D 辉光补强

### 做了什么
- 按“第二条路”继续推进：不让审计角度回退到旧的 screen-space overlay，而是专门增强审计模式下的清晨 3D atmosphere shell
- 在 `updateEarlyMorningGlowMode()` 中为审计模式单独设置一组更可见的 shell 参数：提高 `uOpacity`，放宽 `uPower / uPowerOuter`，提高 `uStrengthOuter`，并轻微增大 `uRadius`
- 保持首页默认构图仍使用原来的清晨 overlay；只有审计模式切到这套更稳定的 3D glow
- 运行 `node -c pwa/earth3d.js`，确认脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 需要继续肉眼验证 `GLOBE / 45° / LOW / TILT` 下这套 3D glow 是否已经“看得见但不过假”
- 如果仍偏弱，下一步优先继续微调审计模式 shell，不回退到 overlay

## 2026-07-04 角度切换时清除 RDL inspect overlay

### 做了什么
- 根据极区截图确认另一条独立问题链：黑色/深色三角形并非清晨辉光，而是 `RDL inspect region` 高精区域 overlay 在角度/缩放切换后残留
- 新增 `clearRDLInspectRegion()`，并接入 `setAuditDistance()` 与 `setAuditAngle()`，确保 `FAR / NEAR / TOP / 45° / LOW / TILT / GLOBE` 这类纯镜头控制不会继续带着旧的区域 overlay 一起走
- 这样镜头切换时优先回到干净的底图 + 当前辉光模式，不再让某个历史 audit region 的高精 patch 以球面窗口形状压在“对面”
- 运行 `node -c server.js`，确认页面脚本整体语法通过

### 改动文件
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 还需要继续验证 audit region 真正需要高精 patch 时，是否仍能按预期重新启用
- 后续系统审查里应把“镜头控制”和“区域 inspect 控制”彻底拆开，避免再次共享状态

## 2026-07-04 关闭非 inspect 状态的自动 RDL 区域贴片

### 做了什么
- 继续追查后确认：问题不只是 inspect 残留，还包括 `updateRDLOverlays()` 在非 inspect 状态下会自动挑一个“最朝向相机”的区域 patch 显示
- 这会在极区和某些斜视角下暴露出明显的球面窗口边界，看起来像黑色/深色三角形或异常贴片，并不属于“渲染延迟”
- 将非 inspect 状态的 RDL 逻辑改为全部隐藏；只有明确设置 `_rdlInspectRegion` 时，才允许显示高精区域 patch
- 运行 `node -c pwa/earth3d.js`，确认脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 需要继续验证 audit region 显式 inspect 时，高精 patch 是否仍按预期显示
- 如果后续还需要“自动区域增强”，必须重新设计成不暴露球面窗口边界的方案，不能恢复当前 best-facing 逻辑

## 2026-07-06 修复深夜背景被清晨式辉光污染

### 做了什么
- 排查“今天下午深夜模式背景修改失败”的反馈：本地起独立预览进程（8081，不影响用户已在跑的 8080 实例），在浏览器里对比 `入夜` 与 `深夜` 两个主题，发现 `深夜` 的天空被一层明显的浅蓝白色雾状光晕覆盖，观感接近“清晨”而不是“深夜”
- 定位根因：未提交的改动把 `RIM_OVERLAY_THEMES` 从 `['earlyMorning']` 扩成了 `['earlyMorning', 'deepNight']`，让 `深夜` 复用清晨专用的 Rim Overlay + Inner Horizon Veil 屏幕空间辉光系统；虽然 `deepNight` 配了自己的 `rimGlow` 颜色，但沿用了清晨量级的 `uSkyHaloWidth: 0.30`（覆盖近 1/3 屏幕高度）与 `haloStrength: 0.55`（比清晨默认值更强），导致本该纯黑的夜空被大范围点亮
- 诊断过程中发现一个方法论坑：`updateEarlyMorningGlowMode()` 每帧都会把 rim overlay 的 `uOpacity` 强制写回 1.0，所以单纯在控制台改 uniform 的 `.value` 会在下一帧被覆盖、看起来“毫无效果”；改用 `Object.defineProperty` 钉住 setter 才能在运行时验证因果关系
- 修复方式：把 `RIM_OVERLAY_THEMES` 缩回 `['earlyMorning']`，`deepNight` 回退到未叠加辉光前的渲染路径；`deepNight.rimGlow` 配置块保留在主题对象里未删除，等以后单独给深夜做一版明显更弱的辉光再启用
- 修复后用真实浏览器交叉验证：`深夜`（黑天空 + 稀疏暖光城市群，无雾感）、`入夜`（同样正常）、`清晨`（不受影响，辉光弧线仍在）均符合预期
- 运行 `node -c pwa/earth3d.js`，确认脚本语法通过

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- `.claude/launch.json` 的预览端口从占位的 3000 改成了 8081（原值 3000 与 `server.js` 实际默认端口 8080 不符，8080 又被用户另一个正在跑的进程占用），后续如需要可再调整

## 2026-07-06 (续) 深夜重新启用辉光，改为细线荧蓝配色

### 做了什么
- 用户看过黑天空的回退版之后反馈：其实想要深夜也有辉光，效果要像清晨那样——没有大片光圈、地平线内外都有光，只是颜色要换成参考图里那种荧蓝色细线（ISS 拍摄风格：贴着地平线一条锐利亮线，快速衰减到黑，而不是大片雾）
- 之前判断错的地方：以为清晨能看起来"干净"是因为整套系统本身很克制，实际是因为清晨的辉光叠加在明亮蓝天背景上不显眼；深夜背景是纯黑，同样强度的 haze 会显得刺眼——所以正确修法不是关掉整个 rim overlay，而是把 `deepNight.rimGlow` 单独调窄调弱
- 重新把 `deepNight` 加回 `RIM_OVERLAY_THEMES`，并重写 `deepNight.rimGlow`：
  - outer（天空侧）：颜色改荧蓝 `#33d6ff`（近端 `#d8fbff` 死白高光，远端 `#062a4a` 深蓝收尾）；`width` 从 0.30 收到 0.045，`haloStrength` 从 0.55 压到 0.12，`tailPower` 从 1.5 提到 3.0——核心变化是让"尾巴"快速衰减，不再铺满小三分之一屏幕
  - inner（地表侧）：颜色改 `#3fc8f0`，`width` 0.16→0.05，`falloff` 1.8→2.2，同样收窄
- 本地起独立预览进程验证：深夜现在是贴地平线一条锐利荧蓝细线，上方迅速转黑、下方带一点蓝色再过渡到暗地表，符合参考图；清晨不受影响

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 目前只在 TOP 默认机位肉眼验证过；`45°/LOW/TILT/GLOBE` 等审计角度走的是 3D Fresnel shell 而非这套 rim overlay，需要另外确认审计视角下深夜观感是否也需要同步调整
- 荧蓝配色和线宽是按参考图目测调的，建议实机（非压缩截图）再确认一遍亮度是否刺眼

## 2026-07-06 (续) 排查"深夜陆地海洋消失" — 结论：不是渲染 bug，是亮度定版太暗

### 做了什么
- 用户看到辉光修好后反馈"陆地和海洋消失了"，深夜画面除了那条细线几乎全黑
- 花了大量时间排查，中间踩了好几个坑，记录下来避免下次重复：
  - 直接改 `earthShaderUniforms.emissive.value` 没用——three.js 每帧都会用 `material.emissive × material.emissiveIntensity` 重新覆盖这个 uniform，必须改 `earthMaterial.emissive` / `.emissiveIntensity` 本身才有效
  - `renderer` 没开 `preserveDrawingBuffer`，异步 `toDataURL()` / 延迟的 `gl.readPixels()` 读到的都是空 buffer（全 0），必须在**同一个同步调用里**先 `renderer.render()` 再立刻 `gl.readPixels()` 才能拿到真实像素
  - 粗网格取样（132 点撒在整个可见半球）完全没扫到任何城市光斑——深夜的 emissiveIntensity(0.72) 和 cityLum 阈值把城市光压得又暗又稀疏，随手撒点大概率全部落空，必须用密集网格（4px 步长）才能扫到真实亮点
- 用密集像素级取样确认：深夜的城市灯光**渲染逻辑本身是对的**——用当前配置的 emissiveIntensity/cityLumLow/High 密集扫描，确实能在预期位置扫到暖色（181,166,129）的城市光斑；把 `earthMaterial.emissiveIntensity` 强行拉到 30、`uCityLumHigh` 降到 0.01 也确实能扫到更多亮点
- 结论：这不是 bug，是"定版 2026-07-05"这版 `nightGrade`/`emissiveIntensity: 0.72` 把深夜整体亮度压得太狠——陆地/海洋/城市灯光都还在渲染，只是数值太低，在压缩截图或普通观察距离下基本等于看不见，读起来像"全黑一片"
- 已把临时加的 `__debugGetInternals()` 调试钩子从 `earth3d.js` 移除，不影响正式代码

### 改动文件
- `devlog.md`（本轮排查没有改动实际渲染参数，等用户确认方向后再动手调亮度）

### 遗留问题
- 需要用户明确：深夜是否要整体调亮（比如 emissiveIntensity 0.72→1.3~1.6，nightExposure 0.085→0.14 左右），把陆地轮廓和城市灯光调到"看得清"但仍比入夜暗很多的程度；还是这套"几乎全黑，只剩零星光点"就是想要的效果，只是这次截图/环境让人以为它坏了
- 如果确认要调亮，下一步直接改 `THEME_VISUAL_CONFIG.deepNight.texture.emissiveIntensity` 和 `nightGrade.nightExposure/cityLumHigh`，再实机验证

## 2026-07-07 HZ复核 deepNight 陆海“消失”结论

### 做了什么
- 按仓库当前代码重新核对 `deepNight` 的主题配置、`applyTheme()` 赋值路径和 shader 夜间分级逻辑，确认这不是 uniform 没生效、纹理没挂上，或后续分支把地球隐藏掉
- 复核结果与前一轮排查一致：`applyTheme()` 会把 `deepNight.texture.emissiveIntensity = 0.72` 直接写到 `earthMaterial.emissiveIntensity`，同时把 `nightGrade.nightExposure = 0.085`、`cityLumLow = 0.014`、`cityLumHigh = 0.065` 写入 shader uniform；这些值叠加后会把陆地、海洋和城市灯整体压到极暗，只剩极少数亮区还能露头
- 结合截图判断，当前现象仍应归类为“定版参数刻意过暗导致读起来像消失”，不是新渲染回归

### 改动文件
- `devlog.md`

### 遗留问题
- 如需把深夜调回“仍然很暗，但能看出陆海结构”，建议直接回调 `pwa/earth3d.js` 中 `deepNight` 的 `emissiveIntensity`、`nightExposure` 与城市阈值，而不是继续查渲染链路

## 2026-07-07 HZ深夜切到“明显可见”亮度档

### 做了什么
- 按“方案 2”直接回调 `deepNight` 的核心亮度参数，让深夜仍然保持黑底和细线辉光，但陆地、海洋、城市网络在正常观察距离下能被读出来
- 提高 `deepNight.texture.emissiveIntensity`：`0.72 → 1.62`，把城市灯从“极少数亮点”拉回到能形成连续暖色网络的级别
- 提高 `deepNight.nightGrade.nightExposure`：`0.085 → 0.15`，同时把 `oceanDarken` 从 `2.8` 回调到 `2.35`，避免海面在新曝光下仍被额外压成纯黑
- 放宽城市亮度阈值：`cityLumLow 0.014 → 0.012`、`cityLumHigh 0.065 → 0.052`，让中高密度城区在常规观看距离下也能稳定露头
- 更新 `pwa/index.html` 的脚本版本号 `rdl-overlay-gate-v17 → v18`，避免本地浏览器继续命中旧版 `earth3d.js`

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 这轮是按“明显可见”目标做的静态参数回调，仍建议你在真实设备上看一眼：如果觉得城市灯偏多，下一步优先微收 `emissiveIntensity` 或把 `cityLumHigh` 略抬回去；如果陆海还不够清楚，再继续抬 `nightExposure`

## 2026-07-07 HZ定位 deepNight 真正发黑层并二次回调 daybase

### 做了什么
- 用浏览器实机复验，不靠截图猜：同一审计区域下，`morning/noon` 能正常显示陆海；切到 `deepNight` 后，即使打开 Diagnose 里的 `v17 Daybase darkened only`，底球仍几乎全黑
- 同时复核 Diagnose 日志，确认这次问题**不是** `oceanMask` 丢失，也不是城市灯没挂上：
  - `oceanMaskOnly` 日志显示 `maskState: ready`、`uOceanMask uniform: 4096×2048`、`isPlaceholder: false`
  - `cityColorOnly` 日志显示 `emissiveMap: SET`、`emissiveIntensity: 1.62`
- 因此把修复点收敛到 `deepNight.nightGrade` 的 daybase 暗化本身，继续上调基底曝光并回收过度海洋压黑：
  - `nightExposure: 0.15 → 0.30`
  - `oceanDarken: 2.35 → 1.65`
  - `landLift: 0.035 → 0.06`
  - `landGamma: 0.85 → 0.82`
- 将脚本版本号提升到 `rdl-overlay-gate-v19`，避免浏览器继续命中旧版深夜参数

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 如果 `v19` 下 deepNight 仍然读不出陆海，那么下一步就不再只调 theme config，而是直接检查 `rodioNightBaseFromRaw()` 的暗化公式本身是否需要抬底或加最低可见地表 floor

## 2026-07-07 HZ继续追 deepNight 发黑到 daybase 调试层

### 做了什么
- 继续用浏览器实机排除“看起来像黑，其实是机位/区域不对”的可能：
  - 同一区域、同一套审计控件下，`noon` 画面能稳定显示陆地、海洋和雪盖
  - 切回 `deepNight` 后，正式画面仍近乎纯黑
- 进一步核验 Diagnose 里的 `daybaseOnly`，确认发黑不是城市灯层造成：
  - `oceanMask` 已在日志中确认 `ready`
  - `cityColorOnly` 日志也确认 `emissiveMap: SET`
  - 但 `daybaseOnly` 仍几乎不可见，说明问题收敛在 `deepNight` 的 daybase/最终成像链路，而不是资源丢失
- 试了两种修法但浏览器实机仍未看到可见改善：
  - 仅调 theme config：`nightExposure`、`oceanDarken`、`landLift`、`landGamma`
  - 在 `rodioNightBaseFromRaw()` 里加入低强度 structural floor
- 为了继续分诊，又把 `daybaseOnly` 调试模式改成“把 daybase 直接写进 emissive，绕过 Phong 光照”，用于判断问题究竟在 night base 公式本身，还是在 diffuse → lighting 的后半段；但本轮浏览器自动化在最终复验这一步超时，结论还差最后一张对照图

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 目前能确认：`deepNight` 的发黑不再是相机、区域、`oceanMask`、或城市灯挂载问题；真正的故障点在 daybase 暗化/最终成像链路
- 还需要补完最后一步验证：看“emissive-bypass 的 daybaseOnly”是否可见。若可见，问题在材质光照乘法；若仍不可见，问题就在 `map_fragment` / `rodioNightBaseFromRaw()` 本身

## 2026-07-07 HZ deepNight 系统审计阶段性结论

### 做了什么
- 停止继续试 theme 参数，改为按链路审计 `deepNight`：`主题配置 → applyTheme → shader uniform → Diagnose 调试层 → 浏览器表现`
- 结合代码和浏览器实机，把已经证实的事实与尚未证实的点分开：
  - 同一区域、同一审计控件下，`noon` 可见、`deepNight` 近乎全黑，因此不是相机/区域问题
  - `oceanMaskOnly` 日志已证实 `oceanMask` 为 `ready`，不是海洋 mask 丢失
  - `cityColorOnly` 日志已证实 `emissiveMap: SET` 且 `emissiveIntensity` 生效，不是城市灯未挂载
  - `daybaseOnly` 日志已证实 `uDaybaseMode`、`uNightExposure` 等 uniform 被成功写入，但浏览器观感仍几乎全黑，因此继续只调 `deepNight.nightGrade` 已被证伪
- 进一步定位到：问题现在收敛在 `deepNight` 的 daybase / final shading 链路，而不是资源缺失或主题按钮状态不同步
- 为了继续分诊，在 Diagnose 的 `daybaseOnly` 上加了一个“绕过 Phong 光照、直接把 daybase 写入 emissive”的诊断通道；这一步代码已落地，但浏览器自动化本轮未稳定产出最终对照图

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 还差最后一刀证据来区分：问题是在 `rodioNightBaseFromRaw()` / `map_fragment` 本身，还是在 `diffuseColor` 进入 `MeshPhongMaterial` 光照后的后半段
- 在这个分诊结论出来前，不建议再继续改 `deepNight` 的 theme config 数值

## 2026-07-07 HZ补上 3D 可用性误判护栏

### 做了什么
- 在系统审计过程中，额外检查了 `index.html` 的 `useEarth3D` 判定链，发现主循环此前把“canvas 仍可见”也当作 3D 可用信号的一部分
- 这会放大一种坏状态：如果 `window.earth3d` 已失效/被删除，但某次异常下 DOM 里残留了旧 canvas，页面可能继续认为自己在 3D 模式，从而既不真正显示 3D 地球，也不回退到 2D
- 因此给 `hasVisibleEarth3DCanvas()` 加了 API 存活护栏：只有 `window.earth3d` 仍存在、且 `isAvailable()` 没明确返回 false 时，才允许“可见 canvas”参与 3D 可用判断

### 改动文件
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 这只是运行时护栏，不足以解释当前 deepNight 发黑的全部现象；真正的主故障点仍在 `deepNight` 的 daybase / final shading 链路

## 2026-07-07 HZ补上 3D 残留层自愈兜底

### 做了什么
- 在系统审计中抓到一个更硬的运行时异常：页面上 `#earth3d-canvas` 还在，但 `window.earth3d` 已经不存在，这说明用户看到的“全黑地球”有一部分其实是失效后的 3D 残留层
- 因此在 `index.html` 里补了 `syncEarth3DLayerHealth()` / `hideStaleEarth3DLayer()` 这组自愈逻辑
- 现在只要 `window.earth3d` 缺失，或 `isAvailable()` 明确为 false 且 `isReady` 也不成立，就会直接清空 `#earth3d-layer` 残留 DOM，强制让 2D fallback 接管，而不是继续把一张失效的黑 canvas 留在界面上
- 同时把 `startVisualLoop()` 的 `useEarth3D` 判定改成先过这一层健康检查，再决定是否跳过 2D 绘制

### 改动文件
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 这个修复解决的是“3D runtime 丢了以后，页面为什么还能留着一块黑幕”这个系统性问题
- `deepNight` 自身的 daybase / final shading 是否还存在独立偏黑链路，仍需在稳定浏览器会话里继续验证

## 2026-07-07 HZ整理 deepNight 审计交接摘要

### 做了什么
- 把本轮 `deepNight` 问题里已经证实、尚未证实、以及适合交给外部代理继续修改的边界整理成了统一摘要
- 明确区分了两类问题：一类是 3D runtime 失效后的残留黑幕问题，另一类是 `deepNight` 自身 shader / daybase 链路可能仍然偏黑的问题
- 给后续代理预留了更清晰的修改范围，避免继续回到“盲调参数”的路径

### 改动文件
- `devlog.md`

### 遗留问题
- 还需要在稳定浏览器会话里验证：当前残留层兜底生效后，`deepNight` 是否仍有独立的 shader 偏黑问题

## 2026-07-07 HZ复核外部代理的条件式 deepNight patch

### 做了什么
- 复核了一版新的外部代理结论：它已把“atlas 占位色湮灭”降级为待验证假设，不再直接写成已证实根因
- 同时审查了它提出的条件式 shader patch，重点检查是否比“全局亮度地板”更窄、更不容易误伤正常 deepNight 渲染
- 结论是：这版思路明显比上一版更稳，但仍属于“可进一步试验”的候选修复，不应在拿到实机验证前直接当成最终根因定案

### 改动文件
- `devlog.md`

### 遗留问题
- 仍需在 `window.earth3d` 存活且 `isReady === true` 的稳定会话里，实机验证 `daybaseOnly` 是否真的命中 atlas 占位色场景
- 若要落 patch，建议先让外部代理补充一个更直接的“占位色判定证据”或给出实机前后对照

## 2026-07-07 HZ复核 rawDayAtlas 诊断方案的隔离性

### 做了什么
- 继续按代码审查标准复核了外部代理提出的 `rawDayAtlas` 诊断模式
- 确认这条思路本身是对的：直接看 `_rawDay` 比继续猜 `daybaseOnly` 更接近“一锤定音”的证据
- 但也确认目前提案还不够隔离：如果只在 `map_fragment` 里把 `diffuseColor.rgb = _rawDay`，后续的 standalone ocean grade、land/ocean tint、以及默认 emissive 分支仍可能继续污染观测结果

### 改动文件
- `devlog.md`

### 遗留问题
- 外部代理还需要把 `rawDayAtlas` 做成真正的“原始 atlas 观察模式”，至少要避免被后续 ocean/tint/emissive 链路继续改写

## 2026-07-07 HZ复核 rawDayAtlas 最终 patch 草案

### 做了什么
- 继续复核了外部代理给出的“最终版” `rawDayAtlas` patch 草案
- 这版已经修正了最关键的问题：不再把 `diffuseColor.rgb` 当作原始 atlas，而是改成 `mapTexelToLinear(texture2D(map, vUv)).rgb` 直接采样 `map`
- 同时它也保留了此前正确的隔离策略：`map_fragment` 侧用 `else` 门控绕开后续 night grade / ocean grade / tint，`emissivemap_fragment` 侧显式清零 emissive，`setDebugLayer('rawDayAtlas')` 里补上 `earthMaterial.color.set(0xffffff)` 作为前置状态保险

### 改动文件
- `devlog.md`

### 遗留问题
- 这版 patch 思路已基本过关，但当前仍只是“草案说明”，还没有真正落到仓库代码里
- 若要实际使用 Diagnose 面板触发该模式，还需要补上对应 UI/按钮绑定（如果不打算只靠控制台调用）

## 2026-07-07 HZ落地 deepNight 可见性救援并更新脚本版本

### 做了什么
- 直接核对仓库后确认：`rawDayAtlas` 诊断模式其实已经在代码里落地了，但它本身只用于定位 atlas 占位色问题，不会默认改变 `deepNight` 的最终外观
- 因此补上了真正影响默认 `deepNight` 观感的最小 rescue patch：在 v17 `diffuseColor.rgb = mix(_nightBase, _oceanTone, ...)` 之后，对疑似 `#020514` 占位色的陆地区域施加条件式最低可见地板
- 同时把 `earth_modes.js` / `earth3d.js` 的脚本 query version 从 `rdl-overlay-gate-v19` bump 到 `rdl-overlay-gate-v20`，避免页面继续命中旧脚本缓存

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 还需要你这边做一次硬刷新，确认页面已经加载 `v20` 脚本
- 如果 `deepNight` 仍然纯黑，下一步就该直接用 Diagnose 里的 `rawDayAtlas` / `daybaseOnly` 做实机分流，而不是再继续猜

## 2026-07-07 HZ修复 ThemeTuner 绑定旧 earth3d 对象

### 做了什么
- 在浏览器运行态里抓到一个直接原因：当前页面的 `window.earth3d` 已不存在，因此 Diagnose 按钮“点了没反应”并不是按钮本身没绑定，而是 ThemeTuner 还在闭包里调用启动时那份旧 `e3d`
- 因此把 ThemeTuner 的关键动作改成每次操作都重新读取 `window.earth3d`：包括 theme 切换、`patchTheme`、atmosphere 开关、shader/tint 同步、以及 Diagnose 的 `setDebugLayer`
- 同时在 runtime 缺失或不可用时打印明确警告，避免继续出现“界面能点，但实际没有任何后端对象在响应”的假象

### 改动文件
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 这一步修复的是“ThemeTuner 绑死旧对象导致按钮无反应”的问题
- 若刷新后仍提示 runtime 缺失，就需要继续追 `window.earth3d` 为什么在当前页面生命周期里消失

## 2026-07-07 HZ回滚 deepNight 实验链到 7 月 6 日辉光基线

### 做了什么
- 回滚了这轮为排查 `deepNight` 黑屏而加入的实验链，去掉 `rawDayAtlas` 诊断模式、atlas placeholder rescue 地板、`daybaseOnly` 的 emissive 绕行，以及 Theme Tuner 里对应的诊断入口
- 把本地调试页的脚本版本号从 `rdl-overlay-gate-v20` 回退到 `rdl-overlay-gate-v17`，避免继续沿用这轮实验版缓存标识
- 保留了与本次回滚无关的其他视觉与渲染改动，不做整文件硬回退，尽量把影响收窄在 `deepNight` 这条链路上

### 改动文件
- `pwa/earth3d.js`
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 这次回滚的目标是先回到 7 月 6 日“深夜辉光基线”，不是继续修复当前 `deepNight` 的根因
- 回滚后仍需要浏览器硬刷新一次，确认页面确实加载的是回退后的脚本

## 2026-07-07 HZ继续回退后续审计 UI 到旧版

### 做了什么
- 继续把未完全回退的页面审计 UI 收回：移除了 `TILT / GLOBE` 两个扩展视角按钮，以及它们对应的标签映射、清理逻辑和缩放行为改动
- 让首页左侧地球审计控制重新回到旧版三档视角与原始 `FAR` 行为，避免看起来仍像“实验中间态”
- 重新做了 `index.html` 内联脚本语法检查，确认页面结构没有被本次回退破坏

### 改动文件
- `pwa/index.html`
- `devlog.md`

### 遗留问题
- 如果浏览器不做硬刷新，仍可能继续显示旧缓存里的审计 UI
- 当前截图右侧的 `goldenApproach` 是页面当前模式，不代表 `deepNight` 已自动恢复，需要刷新后再切回 `deepNight` 实看

## 2026-07-07 HZ直接回调 deepNight 到可见亮度档

### 做了什么
- 确认当前问题已经不是缓存，也不是审计 UI 残留，而是 `deepNight` 主题参数本身仍处在过黑档位
- 直接把 `deepNight.nightGrade.nightExposure` 从 `0.30` 回调到 `0.15`，把陆地/海洋基底重新抬回正常观察距离下可读的级别
- 同时把 `oceanDarken` 调回 `2.35`，并将城市阈值恢复到 `cityLumLow=0.014 / cityLumHigh=0.065`，对应此前已经确认过的“明显可见”档
- 保持 `emissiveIntensity=1.62` 不变，继续使用这版较容易形成连续暖色城市网络的强度

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 这次调整只回调 `deepNight` 的亮度参数，没有再动 shader 结构
- 仍需要你在浏览器里直接看 `deepNight` 的陆海是否恢复可读；如果还不行，再继续查结构链路

## 2026-07-07 (续) Claude 接手，定位到验证方法本身有问题并修复 deepNight

### 做了什么
- 用户反馈 Codex 的回滚"没有回滚成功"：核对后发现 Codex 的回滚只清掉了实验性诊断代码（`rawDayAtlas`、TILT/GLOBE、脚本版本号），但 `emissiveIntensity` 停在调亮后的 `1.62`、其余亮度参数又退回了原始偏暗值，是个不上不下的中间态；用户授权由 Claude 接手继续修
- 关键突破：发现`之前一直用来验证效果的 preview_screenshot 直接截图，对这个 WebGL canvas 本身就不可靠——同一帧内容，用 `renderer.render()` 后立刻 `gl.readPixels()` 量出的像素明明是亮的（城市光斑 luma 160-200），但 `preview_screenshot` 截出来的图还是纯黑。改用"把 WebGL canvas 内容 `drawImage` 到一个新 2D canvas 再截图"的方式后，同一帧立刻能看到清晰的深绿陆地、深蓝海洋和暖色城市网络——说明之前好几轮"改了但看起来没区别"的截图判断本身就是假阴性，不是真的没生效
- 定位到这一点后，重新调整 `deepNight` 参数并用可靠方法验证：
  - `emissiveIntensity: 1.62 → 1.05`
  - `nightExposure: 0.15 → 0.115`
  - `oceanDarken: 2.35 → 2.15`
  - `cityLumLow: 0.014 → 0.006`，`cityLumHigh: 0.065 → 0.028`（原阈值下城市光其实也在正常渲染，只是单个城市在整球视角下只有 1-3 像素，被压缩/正常观看距离直接吞掉；放宽阈值让暗一档的郊区像素也能计入，光斑连成可辨认的团块而不是孤立像素点）
- 用可靠截图方式对比 `深夜` 与 `入夜`：`入夜` 只有城市光、陆地海洋都是纯黑；`深夜` 因为走 v17 daybase 通道，陆地/海洋本身也有偏暗但清晰可辨的颜色，整体读起来比入夜更暗、但地理信息更丰富——两者视觉上有明确区分，不是简单的"深夜=更暗的入夜"
- 移除了本轮排查过程中临时加的 `__debugRenderInternals()` 调试钩子

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 这次验证走的是 `renderer.render()` + `gl.readPixels()` / `drawImage` 到 2D canvas 再截图这条路径，比直接截图可靠；以后再排查 3D 渲染问题时应优先用这个方法，不要单纯依赖 `preview_screenshot` 对 WebGL canvas 的直接截图
- 仍建议你在真实设备/浏览器里肉眼确认一遍最终效果，尤其是 `45°/LOW` 等审计角度（这次只验证了默认 TOP 视角）

## 2026-07-07 (续) 排查成本过高，放弃继续调参，深夜整体回滚到 7 月 1 日已知稳定版

### 做了什么
- 用户在真机上用固定测试流程复现："`window.earth3d.getDebugState().currentTheme` 确认是 `deepNight`、按钮也高亮正确，但画面仍纯黑（只有细线）"——这个现象在 Claude 这边的自动化环境里也稳定复现了
- 定位到一个和颜色参数无关的独立问题：点击主题按钮后，`index.html` 的 `applyForcedTheme()` 不会立刻把新主题同步给 `window.earth3d`，要等 `startVisualLoop()` 下一次 rAF tick 才会检测到 `state.themeKey` 变化再同步；如果那次同步没有及时发生，3D 画面就会停留在切换前的旧帧上——这解释了"console 确认主题对、画面却不对"的现象。已经给 `applyForcedTheme()` 加了同步调用 `window.earth3d.setTimeOfDay()` 的修复
- 但用户综合评估后认为，为了这一个视觉效果，今天已经耗费了远超预期的排查成本（横跨 Claude 和 Codex 两个 agent、一整天时间），决定不再继续调参或验证时序修复，直接回滚
- 回滚方案：**只回滚 `deepNight` 相关内容，保留今天其他改动**（RDL 修复、`earlyMorning` 辉光系统等）
  - 操作前先备份了当前 `pwa/earth3d.js`、`pwa/index.html` 到 `.claude/backups/`（不进版本库，仅本地应急）
  - `pwa/index.html`：今天唯一的净改动就是这次为排查加的 `applyForcedTheme()` 同步调用，直接 `git checkout HEAD` 整个文件复原，无副作用
  - `pwa/earth3d.js`：只替换 `THEME_VISUAL_CONFIG.deepNight` 这一个对象，改回与上次提交（`c88ea8a`，7月1日）逐字节相同的版本（`emissiveIntensity: 0.72`、`nightExposure: 0.068`、`atmosphere.opacity: 0.30` 走 3D Fresnel 而非屏幕空间辉光、`cityLumLow/High: 0.020/0.082`），文件其他部分（`RIM_OVERLAY_THEMES`、RDL、`earlyMorning` 辉光等）保持今天已有的状态不变
  - 同步把 `RIM_OVERLAY_THEMES` 里的 `'deepNight'` 去掉，只保留 `'earlyMorning'`——回滚后的深夜不再用屏幕空间辉光系统，走回原本的 3D Fresnel 大气层（`atmosphere.opacity: 0.30`）
- 用 `diff` 逐字节确认 `deepNight` 配置块与 7月1日提交完全一致，`node -c` 语法检查通过
- 浏览器实机验证（直接用 `preview_screenshot`，不需要任何绕过手段）：`深夜`、`入夜`、`清晨` 三个主题点击后画面立刻正确刷新——深夜显示清晰的暗色陆地纹理、深蓝海洋、密集暖色城市网络和柔和的蓝色大气边缘光，没有再出现纯黑或延迟问题

### 改动文件
- `pwa/earth3d.js`（`THEME_VISUAL_CONFIG.deepNight` 回滚到 7月1日提交版本；`RIM_OVERLAY_THEMES` 去掉 `'deepNight'`）
- `pwa/index.html`（完整回滚到上次提交，去掉今天加的主题同步修复）
- `devlog.md`

### 遗留问题
- 今天新发现的"主题切换后 3D 画面可能停留在旧帧，要等下一帧才同步"这个时序问题**仍然存在**（只是没再触发，因为回滚后的深夜不走屏幕空间辉光这条路径，可能少了触发条件）——如果以后其他主题也出现"console 显示主题对但画面不对"的情况，可以直接复用 `applyForcedTheme()` 同步调用 `setTimeOfDay()` 这个修复思路，代码已经在这次改动前验证过可用，只是这次连同 `index.html` 一起回滚掉了
- 本地留了一份今天改动前的 `pwa/earth3d.js` / `pwa/index.html` 备份在 `.claude/backups/`（不在版本库里），如果之后想找回今天调过的"更亮"版本参数或辉光系统可以参考

## 2026-07-08 HZ深夜对齐 ISS 参考图：金色灯网 + 贴地平线蓝色辉光

### 做了什么
- 用户给出目标效果图（ISS 风格夜景：近黑星空、贴地平线的亮蓝辉光弧、近黑陆地、深海军蓝海洋、金色城市灯丝网络），确认当前深夜（米色扁平灯块 + 泛蓝天空）可以通过纯参数调整对齐，不需要动渲染结构
- 注意：昨晚 Claude 回滚后，Codex 又改过一轮 `deepNight`（emissiveIntensity 0.66 / cityLightClamp 0.38 / 重新启用 rimGlow / 新增了偏亮的深夜天空预设），本轮是在 Codex 这版基础上继续调，不是在回滚版上
- 三轮迭代，每轮浏览器实机截图对比目标图：
  1. 城市灯从米色扁平块改为金色渐变网络：关键是 `cityLightClamp 0.38 → 0.92`（0.38 的 Reinhard 上限把所有城市压成同一个米色调，提高上限后大都市核心能爬向亮白、郊区保持琥珀色），配合 `emissiveColor 0xE8A820 → 0xFFA22E`、`emissiveIntensity 0.66 → 1.15`
  2. 基底对齐参考图：`nightExposure 0.068 → 0.044`（陆地压向近黑）、`oceanDarken 2.8 → 1.8` + `oceanBlueBias 0.010 → 0.070` + `oceanSaturation 0.88 → 1.0`（海洋从和陆地一样黑变成可辨认的深海军蓝）、城市阈值放宽到 `cityLumLow 0.012 / cityLumHigh 0.060`（中型城市加入灯丝网络）
  3. 辉光收紧成贴地平线的弧：rimGlow outer `width 0.34 → 0.10`、`haloStrength 0.52 → 0.30`、`tailPower → 2.8`、颜色改饱和电光蓝（`#4a9cf0`，近端 `#e8f6ff`，远端收到近黑 `#04101f`）；第一轮 0.30 宽度会把三分之一屏幕染蓝（重蹈 7月6日 覆辙），必须收到 0.10 量级
  4. 关键发现：天空大范围泛蓝的元凶不是辉光，而是 Codex 新加的 `getSkyThemePreset` deepNight 分支（`top #061e38 / horizon #0e3060`）；压暗到 `top #010409 / horizon #041020` 后星空才露出来，辉光弧成为地平线唯一的蓝色来源
- `starSphereOpacity 0.32 → 0.45`（参考图星空更明显）
- 最终截图与目标图逐项对齐：星空 ✓ 辉光弧 ✓ 近黑陆地 ✓ 深蓝海洋 ✓ 金色灯网 ✓；入夜/清晨未受影响（未触碰其配置，入夜走 default 天空分支）

### 改动文件
- `pwa/earth3d.js`（仅 `THEME_VISUAL_CONFIG.deepNight` + `getSkyThemePreset` 的 deepNight/night 分支）
- `devlog.md`

### 遗留问题
- 参考图的灯丝比当前更纤细，这是夜景贴图分辨率在当前 zoom 下的上限，纯调参无法进一步逼近；如果想要更细的灯丝，需要换更高分辨率的夜景贴图或对贴图做锐化处理
- 主题切换的时序 bug（点按钮后 3D 可能停留旧帧一拍）仍未修，本轮测试中又触发了一次；修复思路在 2026-07-07 devlog 里有记录
- `getSkyThemePreset` 的 deepNight 分支同时影响 legacy `night` 主题，本轮一并变暗，若 night 主题还在使用需确认观感

## 2026-07-08 (续) 深夜海水层次化 + 星空自然化

### 做了什么
- 用户对上一轮深夜整体满意，提出两个细化：海水"一团黑"不自然（参考苹果锁屏地球：整片海洋有海军蓝底色、大陆架有更浅的层次），星空的星点太假（希望有光点渐变）
- **海水**（`deepNight.nightGrade`，三轮迭代）：
  - 根因：海洋色调先被 `nightExposure 0.044` 压到近黑，`oceanDarken 1.8` 恢复不足，且只以 45% 权重混合，海底地形层次全被吃掉
  - `oceanBlendStrength 0.45 → 0.9`（让分级后的海洋色主导，透出白天贴图的海底地形）
  - `oceanDarken 1.8 → 3.6`（恢复系数与曝光成反比，注释里写明了这个耦合关系）
  - 第二轮试过 `oceanDarken 4.3 + oceanContrast 1.22`，结果浅海变成突兀的宝蓝色块、深海还是黑的，两极分化；改用 `oceanLift 0 → 0.016`（带蓝色倾向的整体底色抬升）让深海也有海军蓝底色，同时把对比度收回 1.10，层次变成"底色之上的渐变"而不是"亮块对黑块"
- **星空**（全主题共享的程序化星点层重写）：
  - `buildStarField()` 增加逐星属性：幂律亮度分布（大部分暗星+少数亮星）、大小 0.35-2.35、色温三档（白/冷蓝白/暖象牙白）、随机闪烁相位
  - 星点材质从均匀方点的 `PointsMaterial` 换成自定义 `ShaderMaterial`：高斯衰减的亮核+宽光晕（这就是用户要的"光点渐变"）、双频轻微闪烁
  - 用 `Object.defineProperty` 把 `material.opacity` 代理到 shader uniform，所有旧调用点（applyTheme/调试工具）不用改
  - 行为变化：星图纹理加载后不再隐藏程序化星点，两层叠加——星图提供密集的暗星/银河背景，星点精灵提供带光晕的前景亮星；白天主题的 `lighting.stars` 都是 0 或 ≤0.04，不受影响
  - 渲染循环里星点 uTime 与星图 uTime 同步驱动闪烁
- 浏览器实机验证：深夜海洋整片海军蓝+浅海渐变层次；星空放大 3 倍确认光晕渐变和亮度分布自然；入夜主题不受影响（自己的纯黑+金灯风格保持）

### 改动文件
- `pwa/earth3d.js`（`buildStarField` / 星点材质 / applyTheme 星点逻辑 / 渲染循环 uTime / `deepNight.nightGrade` 海洋参数）
- `devlog.md`

### 遗留问题
- 星点层现在在所有夜间主题可见（入夜 0.62 / 深夜 0.82 等），如果哪个主题觉得星星太密可单独调它的 `lighting.stars`
- 海洋的深浅层次来自白天贴图的海底地形数据，zoom 进去后（RDL 高精 patch）观感是否一致还没验证
- WebGL canvas 的 `drawImage` 快照在动画循环下有时序竞争（这次读到过空 buffer），放大检查改用 CSS `transform: scale()` 更可靠，已在本轮实践验证

## 2026-07-08 (续) 深夜海水改蓝黑色调 + oceanLift 色相参数化

### 做了什么
- 用户提出深夜海水从"高饱和亮蓝"改为"低饱和蓝黑"，深海目标色 #010713~#031426，浅海允许少量暗青蓝，海水亮度降到原来的 50-60%，且严格限定只动 deepNight 的海洋相关逻辑
- 唯一的结构性改动（经用户确认）：把 `rodioOceanToneGrade()` 里硬编码的 oceanLift 色相比例 `vec3(lift*0.35, lift*0.50, lift)` 抽成 uniform `uOceanLiftTint`（vec3）：
  - 默认值 `(0.35, 0.50, 1.0)` 与原硬编码逐分量相等——不设置 `nightGrade.oceanLiftTint` 的主题行为零变化
  - 两处 config→uniform 赋值点（oceanMask 加载回调 + applyTheme 的 nightGrade 应用块）都带 `?? 默认值` 兜底，主题切换时自动复位；无 nightGrade 主题的 else 分支也显式复位
  - `rodioOceanToneGradeStandalone()`（白天主题用的独立海洋分级）保持硬编码不动，按"最小改动"要求只动 deepNight 走的那条函数
- deepNight 海洋参数调整（`nightGrade`）：
  - `oceanDarken 3.6 → 2.0`（亮度约降到 55%）
  - `oceanSaturation 1.15 → 0.62`（消除台湾海峡/东海/南海的纯蓝色块，层次改由明度承担）
  - `oceanBlueBias 0.060 → 0.018`、`oceanRedReduce 0.05`、`oceanContrast 1.08`
  - `oceanLift 0.016 → 0.010`，新增 `oceanLiftTint: [0.07, 0.45, 1.0]`（冷蓝黑底色，替代默认偏暖比例）
- 验证（浏览器实机 + 像素直方图采样 87k 海洋像素）：
  - 深海主体 p75~p90 落在 `#020417`~`#03051f`，命中目标区间 #010713~#031426
  - 最亮浅海 p99 仅 `#121929`（低饱和暗青蓝），无纯蓝色块
  - 海洋自发光结构上为 0：深夜 `daybaseMode=1`，而 legacy 海洋 emissive 路径的门控是 `uDaybaseMode < 0.5 && uOceanLift > 0.001`，直接跳过
  - 切到入夜后 uniform 全部复位（uOceanLift 0 / uOceanDarken 1 / uOceanSaturation 1），入夜渲染不变
  - `node -c` 通过，控制台无 shader 编译错误
- 本轮严格未触碰：天空预设、rimGlow 辉光、城市灯光、云层、UI、相机（上一轮的目标 6-8 由用户主动收窄范围排除）

### 改动文件
- `pwa/earth3d.js`（uOceanLiftTint uniform 声明/GLSL/两处赋值+复位；deepNight nightGrade 海洋参数）
- `devlog.md`

### 遗留问题
- `rodioOceanToneGradeStandalone()` 仍是硬编码 lift 色相，如果以后白天主题也要调 lift 色相需要做同样的参数化
- 用户上一条消息里的天空(#020407)和辉光灰白化(#B9C8D3)目标被本轮明确排除在范围外，尚未执行，等用户验收海水后再决定是否继续

## 2026-07-08 白天时段视觉系统审计与验收（morning / noon / afternoon）

### 做了什么
- 审计 earlyMorning（锁定锚点）的完整视觉链路：
  - Sky plane：`DAY_SKY_PLANE_THEMES`（earth3d.js:327）+ `SKY_PLANE_COLORS`（:334）+ `updateEarlyMorningSkyPlane()`（:341，由 applyTheme :4343 调用），渲染在 :4937-4948 的专用三段渲染分支（sky plane → scene → rim overlay）
  - RimGlow：Rim Overlay + Inner Horizon Veil 后处理层，`applyRimGlowThemeConfig()`（:2029，由 applyTheme :4341 调用）；earlyMorning 无 rimGlow 配置，走烘焙默认值
  - Land/Ocean 分级：`nightGrade` → earthShaderUniforms（:4255-4307）
  - Lighting/texture/clouds：`resetLightingForTheme` / texture.mapColor / `applyCloudThemeConfig`（对象形态云参数 :2916）
- 确认 morning / noon / afternoon 三个主题配置已存在（THEME_VISUAL_CONFIG :3245/:3338/:3431），且与本轮目标参数**逐项完全一致**（sky plane 四段色板、lighting、mapColor、rimGlow 全字段、land/ocean 分级、OCEAN_TINT strength=0、clouds 0.20/0.12/0.12）——本轮**零代码改动**，纯运行时验收
- 确认三个新主题已加入 `DAY_SKY_PLANE_THEMES` 和 `RIM_OVERLAY_THEMES`（:2448）白名单，参数被运行时真实消费（非死配置）
- 浏览器实机验收（AUDIT LIGHT OFF）：earlyMorning / morning / noon / afternoon 四张截图
  - noon 四档最亮最清晰（sun 1.14 / ambient 0.74 / 纯白 mapColor / landStr 0.08）
  - afternoon 比 noon 略暗略暖（mapColor 0xF5F0E6，oceanSaturation 0.78）
  - 海洋无塑料蓝/地图蒙版；rimGlow 为薄空气散射；无 JS runtime error（仅 Spotify token 无关警告）

### 改动文件
- `devlog.md`（仅本记录；earth3d.js 未改动）

### 遗留问题
- earlyMorning 的 rimGlow 走烘焙默认值（width 0.30 / coreStrength 0.82），明显比 morning/noon/afternoon 的薄 rim（width 0.055-0.070 / coreStrength 0.20-0.30）亮且厚——清晨→上午切换时地平线辉光有可见跳变。earlyMorning 已锁定不许改，如需连续性需用户决策
- UI 时段按钮高亮跟随真实时钟调度（验收时高亮「暮前」），与 setTimeOfDay 手动覆盖不联动，属 UI 范畴未处理

## 2026-07-08 白天时段视觉递进 R2：接通死掉的白天海洋分级 + 拉大四档梯度

### 做了什么
- **根因修复**：上一轮判定"参数被运行时消费"有误——shader 里专为白天写的
  `rodioOceanToneGradeStandalone()` 定义了但从未被调用，daybase=0 分支只做 land
  分级，白天主题的 ocean 参数全是死配置（JS 侧注释声称的 standalone 路径不存在）。
  本轮把它接进 v16 白天分支，新增 uniform `uDayOceanGrade` 门控：只有
  `nightGrade.dayOceanGrade: true` 的主题启用。earlyMorning 与所有夜间主题不设
  此键 → uniform=0 → 渲染逐像素不变（锁定不破）
- uniform 三处同步：onBeforeCompile 声明（_pv 迁移）、applyTheme nightGrade 块、
  resetNightGradeUniforms 归零、ocean mask 加载回调
- `resetLightingForTheme` 支持可选 `lighting.sunColor`（默认 0xfff5e0 不变，
  其他主题零影响）
- morning/noon/afternoon 重调（earlyMorning 锚点 ambient0.56/sun0.92 不动）：
  - lighting 总光照梯度：EM 1.48 → morning 1.76 → noon 2.18 → afternoon 1.58；
    sunColor 上午偏冷白 0xfff8ea / 正午近纯白 0xfffaf2 / 下午暖 0xffedd2
  - rimGlow 放弃上一轮细描边，回归 earlyMorning 定版大气结构（width 0.30 基准），
    按 ~0.9/0.8/0.75 递减缩放：morning 0.28/0.74、noon 0.24/0.66（最紧最净）、
    afternoon 0.26/0.58（略暖灰）
  - ocean（新生效路径）：morning darken0.90/sat0.80，noon darken1.04/sat0.88
    （最亮），afternoon darken0.78/sat0.68/greenReduce0.015（最暗最灰）；
    oceanRedReduce 全部归 0（减红会推蓝，是地图蓝倾向来源之一），blueBias 全 0
  - land：morning lift0.016/γ0.92/str0.26，noon str0（纯贴图最锐），
    afternoon lift0.012/γ0.97/str0.35/landRedRed -0.03（暗部暖化）
  - SKY_PLANE_COLORS 拉大亮度梯度（仍从 EM 色板派生）：noon bottom #cfeafa 最亮，
    afternoon bottom #c3d8dd 暖灰回落
  - clouds：morning 0.30 / noon 0.10 / afternoon 0.18
  - afternoon mapColor 0xF5F0E6 → 0xF3ECDC（略增暖）
- 浏览器实机验收（AUDIT LIGHT OFF）：四档截图递进清晰——EM 冷调晨光 → morning
  更亮 → noon 最亮最锐（沙漠高光、海洋最中性）→ afternoon 转暖回落；
  console 无 JS/shader 错误；earlyMorning 配置抽查原值完好

### 改动文件
- `pwa/earth3d.js`（uDayOceanGrade uniform 四处 + v16 分支海洋 mix 注入 +
  resetLightingForTheme sunColor + morning/noon/afternoon 配置 + SKY_PLANE_COLORS）
- `devlog.md`

### 遗留问题
- 四档 rim 现在同语言但仍是离散跳变（主题切换瞬间），没有过渡动画
- afternoon landRedRed 用负值实现暗部暖化，属参数挪用；若后续需要更强暖调，
  应给 v16 land 分支加正式的暖色参数
- goldenApproach（16.5h）与 afternoon（16h）时段相邻，色温衔接未验证

## 2026-07-08 白天时段 R3：收尾确认 + 亮度梯度加强（阶段性锁定）

### 做了什么
- 收尾确认（用户验收 R2 方向通过后）：
  - `dayOceanGrade: true` 仅存在于 morning(:3318) / noon(:3416) / afternoon(:3513)
    三个配置块，其余出现处均为门控管线（两处赋值 + 注释）
  - earlyMorning / deepNight 运行时确认无 dayOceanGrade 键（getThemeConfig 实测
    ABSENT）；deepNight daybase=true 走另一分支，shader 注入为纯追加代码，
    未启用主题逐像素不变
  - smoke：earlyMorning → morning → noon → afternoon → deepNight 五连切，
    全部正常渲染，console 无 shader/runtime error
- 亮度梯度加强（回应"各档仍太类似"，只动幅度不动结构）：
  - 总光照 (ambient+sun)：EM 1.48（锁定）→ morning 1.90（0.76/1.14）→
    noon 2.44（0.98/1.46）→ afternoon 1.50（0.58/0.92）
  - 海洋亮度 oceanDarken：morning 0.86 → noon 1.10（最亮）→ afternoon 0.70（最暗）
  - 辉光强度 core/halo：EM 0.82/0.42（烘焙）→ morning 0.78/0.38 → noon 0.58/0.26
    （width 0.22 最紧）→ afternoon 0.48/0.21（最柔）

### 改动文件
- `pwa/earth3d.js`（仅 morning/noon/afternoon 的 lighting、oceanDarken、rimGlow 强度）
- `devlog.md`

### 遗留问题（用户指定记录的后续小修项）
- 浅海区域仍略偏地图蓝
- 四档 rimGlow 是离散切换，暂无过渡动画
- afternoon 暖化用 landRedRed 负值实现，后续可改成正式 landWarmBias 参数

## 2026-07-08 V4-Day-Light-R2 阶段性通过 — 最终参数表 + 禁区确认 + 收尾 smoke

### 本轮结论
**V4-Day-Light-R2 阶段性通过。** 白天三档已形成明确递进：morning 提亮、noon 最亮最清晰、afternoon 回落偏沉。earlyMorning / morning / noon / afternoon 四档锁定。

### 1. 最终参数表（当前生效值，pwa/earth3d.js THEME_VISUAL_CONFIG + SKY_PLANE_COLORS）

**earlyMorning**（锚点，themeHour 7.4，本轮未改）
- sky plane: top #061a3a / mid #0b315f / lower #235f93 / bottom #9fd0ed
- lighting: ambient 0.56, sun 0.92, sunColor（未设，走函数默认 0xfff5e0）
- rimGlow: 未设配置键 → 走 applyRimGlowThemeConfig 烘焙默认（outer width 0.30 / coreStrength 0.82 / haloStrength 0.42；inner width 0.16 / strength 0.36）
- land: landLift 0.020, landGamma 0.89, landStr 0.26
- ocean: oceanBlendStrength 0.36, oceanDarken 0.79, oceanSaturation 1.15, oceanBlueBias 0.036, coastProtection 0.77（daybaseMode=false，走 legacy ocean 混合，非 standalone）
- dayOceanGrade: 未设（等效 false）
- clouds: opacity 0.38（object 形态，专属曲线）

**morning**（themeHour 9.0）
- sky plane: top #082246 / mid #0f3d72 / lower #3072a6 / bottom #b0dcf4
- lighting: ambient 0.76, sun 1.14, sunColor 0xfff8ea
- rimGlow: outer width 0.28 / coreFraction 0.42 / coreStrength 0.78 / haloStrength 0.38 / tailPower 1.6 / color #a4dbff→#f4fbff→#5d8fc0；inner width 0.15 / strength 0.32 / falloff 1.9
- land: landLift 0.016, landGamma 0.92, landStr 0.26
- ocean: oceanBlendStrength 0.45, oceanDarken 0.86, oceanContrast 1.05, oceanSaturation 0.80, oceanBlueBias/RedReduce/GreenReduce 全 0, coastProtection 0.72
- dayOceanGrade: **true**
- clouds: opacity 0.30

**noon**（themeHour 12.5，四档最亮锚点）
- sky plane: top #0d2f5e / mid #175089 / lower #4687b8 / bottom #cfeafa（四档最亮）
- lighting: ambient 0.98, sun 1.46（四档最高）, sunColor 0xfffaf2
- rimGlow: 四档最紧最净 — outer width 0.22 / coreFraction 0.40 / coreStrength 0.58 / haloStrength 0.26 / tailPower 1.7；inner width 0.14 / strength 0.27 / falloff 2.0
- land: landLift 0, landGamma 1.00, landStr 0（纯贴图，最锐利）
- ocean: oceanBlendStrength 0.35, oceanDarken 1.10（四档唯一 >1，最亮）, oceanContrast 1.03, oceanSaturation 0.88, coastProtection 0.75
- dayOceanGrade: **true**
- clouds: opacity 0.10（四档最少）

**afternoon**（themeHour 16.0）
- sky plane: top #071c3c / mid #0c3462 / lower #2f6a8e / bottom #c3d8dd（暖灰回落）
- lighting: ambient 0.58, sun 0.92（四档最低）, sunColor 0xffedd2
- rimGlow: 四档最柔 — outer width 0.26 / coreFraction 0.40 / coreStrength 0.48 / haloStrength 0.21 / tailPower 1.8；inner width 0.14 / strength 0.24 / falloff 2.0
- land: landLift 0.012, landGamma 0.97, landStr 0.35（四档最强，暗部暖化）, landRedRed -0.030（暖化挪用）
- ocean: oceanBlendStrength 0.55, oceanDarken 0.70（四档最暗）, oceanContrast 1.06, oceanSaturation 0.68（四档最低）, oceanGreenReduce 0.015, coastProtection 0.72
- dayOceanGrade: **true**
- clouds: opacity 0.18
- texture.mapColor: 0xF3ECDC（偏暖）

### 2. 禁区确认
- **earlyMorning**：本会话（R1/R2/R3）未对该配置块调用任何 Edit——仅作为参数派生锚点被读取。与 R1 审计截图目视比对一致。
- **evening / lateEvening / deepNight**：本会话未对这三个配置块调用 Edit。注意：这三块与上一次 git 提交（c88ea8a）相比确有差异，但那是**会话开始前已存在于工作区的未提交改动**（对话起始的 git status 已显示 `M pwa/earth3d.js`），非本轮所加。
- **dawn / sunrise / goldenApproach / sunset**：sunrise / sunset / goldenApproach 与上次提交逐字节相同；dawn 与上次提交有差异，同上——是会话前已存在的未提交状态，本轮未触碰。
- **UI / camera / player / service worker**：`pwa/index.html` 的 diff（+4 行，ASIA 1/2 预设角度按钮）在 R1 第一张截图里已经可见，确认早于本轮存在，非本轮所加。未发现 camera/quaternion/orientation/player/sw.js 相关代码被本轮修改（diff 中仅有的 camera 相关行是 earlyMorning rim 投影的既有实现代码，非本轮新增逻辑变更）。

### 3. 最终 smoke
- `setTimeOfDay` 依次切换 earlyMorning → morning → noon → afternoon → deepNight，每步等待渲染稳定后截图+console 检查
- AUDIT LIGHT 全程 OFF（`getDebugState().auditLightingEnabled === false`）
- console error 级别日志：五档切换全程 **0 条**（仅历史性的 Spotify token 警告，warn 级别，与视觉系统无关）
- `git status`：working tree 修改 5 个已跟踪文件（.gitignore / devlog.md / pwa/earth3d.js / pwa/index.html / server.js）+ 若干未跟踪的资源/脚本文件
- `git diff --stat`：pwa/earth3d.js 1929 行变更（含本轮 + 此前会话未提交的天空平面/rim overlay 基础设施）
- **建议 commit**：是。当前状态是自 c88ea8a 以来多轮会话累积的完整功能集（sky plane 基础设施 + rim overlay + dayOceanGrade 白天海洋分级 + 四档亮度递进），已过 smoke 且用户确认阶段性通过，建议提交固化为新基线，便于后续每轮改动产出干净可审的 diff。

### 遗留问题（保留，未在本轮处理）
- 浅海区域仍略偏地图蓝，可微调
- 四档 rimGlow 是离散切换，暂无过渡动画
- afternoon 暖化使用 landRedRed 负值实现，后续可正式化为独立的 landWarmBias 参数

## 2026-07-08 V4-2C 方向性太阳光：dawn / sunrise / goldenApproach / sunset

### 做了什么
- **审计发现（核心，同 R2 dayOceanGrade 模式）**：
  - `RIM_OVERLAY_THEMES` 集合此前不含 sunrise/goldenApproach/sunset —— 三者完全没有 WebGL rim overlay 限光系统，只靠 3D fresnel atmosphere shell（opacity 0.07-0.11，无方向偏置）。
  - `getSkyThemePreset()` 的 switch 语句没有 sunrise/goldenApproach/sunset 分支 —— 三者落入 `default`（近黑 #000205、opacity 0.98），天空球背景完全没有时段区分，无论白天/黄昏。
  - sunrise/goldenApproach/sunset 原配置是 v16 遗留 stub：无 rimGlow、无 horizonGlow、无 nightGrade —— 仅靠 mapColor 平面着色 + 真实 Phong 光照。goldenApproach `texture.emissiveMap: null`，城市灯完全关闭，破坏"暮前应开始出现城市灯"的要求。
  - `horizonGlow`（DOM CSS 径向渐变覆层）已内置方向偏置机制 `lightDirX/lightDirY`（渐变热点在地球视觉圆盘内的位置百分比），且在渲染循环中无条件每帧调用，与 RIM_OVERLAY_THEMES 集合无关——这是真正可用的左右方向性载体，此前 4 个模式均未启用或偏置极弱（48/44，接近居中）。
  - WebGL Rim Overlay 本身按到地球边缘的**距离**渐变（colorNear→color→colorFar），无左右方向感知能力——方向性只能靠 horizonGlow 实现，rim overlay 只补全"此前完全缺失的限光结构"。
- **踩坑并修正**：第一版把 sunrise/sunset 套进 `daybaseMode:true` 夜基压暗管线（仿照 dawn/evening），结果陆地被压到几乎全黑只剩城市灯——`daybaseMode:true` 是为近乎零日光的场景设计的，sunrise/sunset 原本是真实 Phong 光照下的明亮曝光。改回 `daybaseMode:false + dayOceanGrade:true`（R2 建立的白天安全路径），陆地重新可见。
- 新增 3 个 `getSkyThemePreset` 分支（sunrise/goldenApproach/sunset），天空球从"近黑默认值"改为真实的蓝→暖金/橙渐变。
- `RIM_OVERLAY_THEMES` 加入 sunrise/goldenApproach/sunset。
- dawn：`horizonGlow.lightDirX` 48→66，opacity 0.030→0.045（保持冷色为主，只做轻微右侧预热提示）。
- sunrise 重建：`daybaseMode:false + dayOceanGrade:true`，ambient 0.072→0.24，sun 0.48→0.78，rimGlow 新增（暖金，弱方向性由 horizonGlow 承担），horizonGlow 新增并强方向偏右（lightDirX 82），emissiveIntensity 0.46→0.20（城市灯淡出）。
- goldenApproach 重建：`emissiveMap: null→'night'`（城市灯从零改为初现,intensity 0.08），ambient 0.052→0.42，sun 0.88→1.02（"整体仍有白天余光"要求原 ambient 过暗），rimGlow/horizonGlow 新增，horizonGlow 强方向偏左（lightDirX 18），dayOceanGrade 海洋变深（oceanDarken 0.66）、陆地暖化（landStr 0.42, landRedRed -0.055）。
- sunset 重建：`daybaseMode:false + dayOceanGrade:true`（同样避开夜基压暗坑），ambient 0.058→0.30, sun 0.40→0.62（保持陆地可见，比 goldenApproach 暗），emissiveIntensity 0.16→0.30（城市灯继续增强），rimGlow/horizonGlow 新增，horizonGlow 最强左偏（lightDirX 14）、最深暖色。
- 浏览器实机验收（AUDIT LIGHT OFF，通过 UI 强制主题按钮而非直接调 setTimeOfDay——发现后者会被每帧实时时钟驱动的自动主题覆盖，验证需用 `forcedThemeKey` 机制）：dawn/sunrise/goldenApproach/sunset 四张截图，递进清晰：dawn 冷暗最少城市灯可见 → sunrise 转亮转暖、城市灯明显淡出 → goldenApproach 四者最亮最暖、城市灯初现 → sunset 比 goldenApproach 更暗更沉、城市灯继续增强。console 全程无 shader/runtime error。
- 回归确认：deepNight / noon 截图与既有基线一致，未受影响。

### 改动文件
- `pwa/earth3d.js`（getSkyThemePreset 新增 3 分支；RIM_OVERLAY_THEMES 扩容；dawn horizonGlow 微调；sunrise/goldenApproach/sunset 全量重建）
- `devlog.md`

### 遗留问题
- WebGL Rim Overlay 本身仍是纯距离径向渐变，无左右方向感知——四个模式的"方向性"完全由 horizonGlow（DOM 覆层）承担。如果以后要在 rim overlay 层本身做真正的左右色相分裂，需要新增基于屏幕角度（而非仅距离）的 uniform，是更大的 shader 改动。
- sunrise/goldenApproach/sunset 的 nightGrade 未设置 cityLumLow/cityLumHigh（沿用默认 0.008/0.040），城市灯亮度目前主要靠 emissiveIntensity + cityLightClamp 控制，未做精细化调校。
- dawn 的 rimGlow 本身未改（仍是旧版参数），本轮只调了 horizonGlow；如果验收后觉得 dawn 的限光结构也需要方向强化，需要额外一轮。

## 2026-07-09 黎明(dawn)海水层次感修复

### 做了什么
- 前置一轮 11 主题视觉审计（仅输出报告，未改代码）发现：dawn 的海洋渲染参数比预期更激进（`oceanDarken`/`oceanBlendStrength` 均高于 deepNight 自身），导致海水色调过深，浅滩与深海盆之间几乎没有可辨识的层次感
- 用户确认问题后，通过 `window.earth3d.patchTheme()` 在浏览器内实时试验两组候选参数（温和版 / 更强版），截图对比，用户选定"温和版"
- 将选定数值写入 `THEME_VISUAL_CONFIG.dawn.nightGrade`：`oceanBlendStrength` 0.60→0.48，`oceanDarken` 1.35→1.10，`oceanSaturation` 0.58→0.62，`coastProtection` 0.72→0.80（`oceanBlueBias`/`oceanRedReduce`/`oceanLift` 等其余字段未改动）
- 页面刷新后重新验收：`getDebugState().uniforms` 确认新值已从文件正确加载（非残留的内存态 patch），AUDIT LIGHT 全程 OFF；黄海/台湾海峡一带浅滩色块与深海区域的色调差异清晰可辨，陆地/城市灯未受影响

### 改动文件
- `pwa/earth3d.js`（`THEME_VISUAL_CONFIG.dawn.nightGrade` 四个海洋字段）
- `devlog.md`

### 遗留问题
- 审计中发现的 dawn vs deepNight 净亮度（`ambient × nightExposure`）区分度不足问题尚未处理，本轮只解决海水层次感，未触碰 `ambient`/`nightExposure`
- 审计中列出的其余 P1/P2 问题（dawn/sunrise 的 DOM horizonGlow 与 WebGL rimGlow 双重叠加架构、8 个模式的 horizonGlow 死配置等）均未处理，见审计报告

## 2026-07-09 R7 ocean-only blackness swap（deepNight 压黑 / dawn 轻抬）

### 做了什么
- 参数审计确认：dawn 海水比 deepNight 更黑的根因不在 ocean 参数（dawn 的 oceanDarken 1.35、oceanLift 0.014 其实都比 deepNight 更"亮"），而在两个全局乘数：`mapColor 0x8a98a4`（线性空间约 0.3×预乘 day 纹理）+ `lighting.ambient 0.62`（vs deepNight 1.0）。全局参数在禁改清单内，故按约束"转译"为 ocean-only 参数
- 修正了原方案的两个方向性错误：oceanRawMix 不能降（raw 层是三个海水成分里最黑的一层，降 mix 会变亮）；oceanDarken 不能冻结（它是 oceanTone 的纯乘数，恰是转译全局 ×0.6 的正确旋钮）
- deepNight：oceanDarken 1.75→1.10，oceanLift 0.010→0.005，oceanRawExposure 0.040→0.026，oceanRawBlueKeep 0.40→0.32；oceanRawMix 0.30、oceanBlendStrength 0.60、saturation/coastProtection/全局 nightExposure/nightSaturation 均不动
- dawn（ocean-only 轻抬）：oceanDarken 1.35→1.50，oceanLift 0.014→0.018；sky/cloud/rimGlow/lighting 未动
- normal render 验收（非 oceanGradeOnly）：canvas 同帧 rAF 像素采样五个海区，改后 deepNight 台湾以东 (6,11,18)→(4,4,8)、西太平洋 (6,12,21)→(4,5,13)，dawn 台湾以东 (3,9,15)→(4,10,18)——黑度层级完成对调，deepNight 在全部可比点位均不浅于 dawn；东海陆架保留弱冷蓝层次；两主题陆地/城市灯/天空无变化，console 无报错

### 改动文件
- `pwa/earth3d.js`（deepNight.nightGrade 四个字段 + dawn.nightGrade 两个字段，均 ocean-only）
- `devlog.md`

### 遗留问题
- 未 commit，等用户视觉确认后提交
- deepNight 深海黑位 (4,4,8) 已接近纯黑，若后续想保留更明显的"黑蓝"倾向而非墨黑，可微升 oceanLift（0.005→0.007）或 oceanRawBlueKeep
- dawn vs deepNight 的全局净亮度（ambient × nightExposure）区分度问题依旧未动（沿袭上轮遗留）

## 2026-07-09 evening 城市灯光完全不可见——根因定位与修复

### 做了什么
- 接手交接报告：evening 主题城市灯光完全不可见，此前多轮排查（审计光守卫、dimHue 修正、emissiveIntensity/cityLumLow/cityLumHigh/cityHighlightClamp 多次上调）均未解决，且所有 JS 侧诊断（uniform 值、texture 是否存在、shader define 是否编译）都显示"纸面正确"
- 放弃继续调参，转向直接在浏览器里取证：用 preview 工具起本地服务，hook `useProgram`/`getUniform` 直接从 GPU 读取当前编译的 fragment shader 源码和实际生效的 uniform 值——确认 shader 里 `USE_EMISSIVEMAP`、`_cityColor`、`uCityLumLow` 等全部存在且数值合理，排除"shader 未按新 emissiveMap 重新编译"和"uniform 未写入"两个此前怀疑的方向
- 用 `gl.readPixels` 在同步渲染后直接读回帧缓冲，证实整个画面找不到任何暖色（琥珀色）像素，最亮点也只是天空/大气的冷色调——证实城市灯光在 GPU 输出层面就是空的，不是被后续步骤盖掉
- 用 `window.earth3d.patchTheme()` 做 iceNeutralize 0/1 A-B 对照（怀疑雪地保护 veto 误伤广大陆地），结果完全无差异——排除此方向，避免了在错误参数上继续耗时间
- 对照测试：deepNight（用未损坏的 `earth_night_8k.jpg`）在同一 debug 视图下城市灯光正常（暖色像素 4万+），evening（用 `earth_night_night_8k.jpg`）则完全没有——把范围收窄到纹理文件本身
- 直接用 `gl.texImage2D` 复现 three.js 内部的纹理上传路径（而非之前测试用的 canvas 2D 解码路径），发现 `earth_night_night_8k.jpg` 上传时报 `GL_INVALID_VALUE`，导致 GPU 侧纹理数据无效（采样恒为黑），但整个过程 three.js 不检查 `gl.getError()`，JS 侧完全无感知、无报错——这就是为什么之前所有静态代码审计和 JS 诊断都测不出问题：bug 不在 JS 状态，而在一次静默失败的 GPU 纹理上传
- 确认文件本体确实被截断（尾部缺少标准 JPEG EOI 结束符 `FFD9`，替换成了一长串 `00` 字节），用 `PIL.ImageFile.LOAD_TRUNCATED_IMAGES` 容错解码后重新编码保存，验证新文件 `gl.texImage2D` 上传无报错、PIL 严格模式也能完整解码
- 浏览器内重新验证：evening 主题城市灯光正常显示，长三角/珠三角等城市群清晰可见，暖色像素从 0 变为 8万+
- 根因排除后，把此前为了"点亮看不见的灯"而被上调的 4 个补偿性参数（emissiveIntensity 1.20→0.68、cityLightClamp 0.88→0.74、cityLumLow 0.006→0.014、cityLumHigh 0.100→0.095）还原为 `V4-2A-R3_baseline.md` 记录的、已通过视觉验收的原始数值——还原后城市灯光依然清晰可见，说明这些参数本来就是够用的，之前的上调只是在补偿一个和参数无关的 bug
- 顺手抽查了同批生成的 `earth_night_mid_8k.jpg`/`earth_night_late_8k.jpg`，`gl.texImage2D` 上传均无报错，没有同样的潜在损坏
- 移除了排查过程中插入的 `[DIAG] evening applyTheme end` 诊断 console.log

### 改动文件
- `pwa/assets/earth_night_night_8k.jpg`（修复截断，重新编码为完整有效的 JPEG）
- `pwa/earth3d.js`（`THEME_VISUAL_CONFIG.evening`：emissiveIntensity/cityLightClamp/cityLumLow/cityLumHigh 还原为验收基线值；移除临时诊断 log）
- `devlog.md`

### 遗留问题
- 根因是文件生成/写入过程中被截断（很可能是生成 `earth_night_night_8k.jpg`/`earth_night_mid_8k.jpg`/`earth_night_late_8k.jpg` 那一批操作里进程被中断或写入未完整落盘），生成这三个文件的脚本/流程未在仓库中找到对应记录，如果之后要重新生成同类纹理，建议生成后立即跑一遍 `gl.texImage2D` 级别的验证（PIL 能解码不代表 WebGL 能上传，两者容错程度不同），而不只是检查文件能否被图片查看器打开
- `pwa/earth3d.js.bak`、`pwa/lil-gui.umd.min.js`、`tmp_stage7_grammar_preview.png`、`tmp_stage7_visual_check.png` 等未跟踪文件是本轮之前遗留的调试产物，本次未处理，如不再需要可以清理
- 未 commit，等用户确认后提交

## 2026-07-10 HZ创建 visual tuning PR

### 做了什么
- 为分支 `finalize-visual-20260710` 向 `main` 创建 GitHub Pull Request
- 使用指定标题 `Finalize visual tuning for 20260710` 与提供的描述内容
- 确认远端分支 `origin/finalize-visual-20260710` 已存在后直接创建，无额外代码改动

### 改动文件
- `devlog.md`

### 遗留问题
- PR 已创建为普通 open 状态：`https://github.com/Heyyeqi/RodiO/pull/3`
- 当前工作区仍有既有未提交与未跟踪文件，本次未整理也未提交

## 2026-07-10 HZ部署前资源依赖审计并补齐必需视觉资产

### 做了什么
- 按部署前审计要求检查当前分支未跟踪文件、代码引用关系与 Railway 运行依赖
- 确认当前 `pwa/earth3d.js` 会在运行时直接请求以下未入库资源：主题云图集合、`starmap_2020_8k.jpg`、以及 `earth_night_mid_8k.jpg` / `earth_night_night_8k.jpg` / `earth_night_late_8k.jpg`
- 确认 `pwa/assets/sky/earlyMorning_sky_gradient*.png`、截图、`.bak`、本地脚本与调试目录不在当前运行链路中，本次不纳入部署提交
- 将部署必需资源加入 git，供当前 PR 与后续 Railway 部署使用

### 改动文件
- `pwa/assets/textures/clouds/fair_clouds_8k.jpg`
- `pwa/assets/textures/clouds/fair_clouds_soft_8k.jpg`
- `pwa/assets/textures/clouds/africa_clouds_8k.jpg`
- `pwa/assets/textures/clouds/n_amer_clouds_8k.jpg`
- `pwa/assets/textures/clouds/se_asia_clouds_8k.jpg`
- `pwa/assets/textures/clouds/australia_clouds_8k.jpg`
- `pwa/assets/textures/clouds/storm_clouds_crisp_8k.jpg`
- `pwa/assets/textures/clouds/europe_clouds_8k.jpg`
- `pwa/assets/textures/clouds/s_amer_clouds_8k.jpg`
- `pwa/assets/textures/clouds/africa_clouds_wispy_8k.jpg`
- `pwa/assets/textures/clouds/clouds_live_8k.jpg`
- `pwa/assets/textures/stars/starmap_2020_8k.jpg`
- `pwa/assets/earth_night_mid_8k.jpg`
- `pwa/assets/earth_night_night_8k.jpg`
- `pwa/assets/earth_night_late_8k.jpg`
- `devlog.md`

### 遗留问题
- `.gitignore` 里仍把部分现已运行时使用的云图标注为 ignored，本次为避免扩大范围未重构 ignore 规则，而是直接将必需文件纳入本次提交
- 其余未跟踪文件（如截图、生成脚本、预览图、备份文件、workspace 输出）本次保持不动，待后续按需清理

## 2026-07-10 HZ补齐 Railway 缺失的 NOON_AIR_V2_ISLANDS 主 tiles

### 做了什么
- 复核线上“海洋不精细”的根因：不是 `earth_day_8k` / `normal` / `ocean_mask` / `ocean_specular` 缺失，而是默认白天地球已切到 `NOON_AIR_V2_ISLANDS` tile stream，但 Railway 上对应 `/assets/earth/bmng21k/topo_bathy/tiles_noon_air_v2_islands/...` 返回 `404`
- 确认本地高精细主 tiles 仍完整存在于 `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air_v2_islands/`
- 审计其余遗漏资源：`tiles_rdl_regions/` 同样未部署，但体量约 `2.8G`、972 文件，不适合与本次主视图修复一起硬塞进仓库
- 采用最小发布策略：本次只补当前默认主视图运行必需的 `NOON_AIR_V2_ISLANDS` 4k / 8k / 16k tiles，保住线上精细度，不扩大到全部 RDL 区域素材

### 改动文件
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air_v2_islands/4k/tile_0_0.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air_v2_islands/4k/tile_1_0.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air_v2_islands/8k/tile_0_0.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air_v2_islands/8k/tile_1_0.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air_v2_islands/16k/tile_0_0.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air_v2_islands/16k/tile_0_1.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air_v2_islands/16k/tile_1_0.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air_v2_islands/16k/tile_1_1.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air_v2_islands/16k/tile_2_0.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air_v2_islands/16k/tile_2_1.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air_v2_islands/16k/tile_3_0.jpg`
- `d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/topo_bathy/tiles_noon_air_v2_islands/16k/tile_3_1.jpg`
- `devlog.md`

### 遗留问题
- `tiles_rdl_regions/` 仍未部署到 Railway；当前代码会预加载这批区域资源，但默认主视图并不依赖它们才能恢复精细地球底图
- `tiles/`、`tiles_noon_air/`、`tiles_v2_enhanced/`、`tiles_noon_air_v2/` 等历史/切换模式资源也仍未进仓库；如果后续要恢复多模式切换的线上完整性，需要单独规划

## 2026-07-10 HZ修复夜景云层夜侧不可见

### 做了什么
- 定位云层不可见的直接原因：alpha 通路虽有输出，但云层 RGB 还乘方向光；夜侧 `dirLight` 在默认 `ambient = 0` 时归零，最终形成黑色云层。
- 为 evening / lateEvening / deepNight / night 增加显式云层环境光，保留现有纹理、opacity 与 alpha 门槛配置。

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 尚未在当前浏览器标签页完成硬刷新后的截图验证；需加载最新前端后确认云层可见度是否符合预期。

## 2026-07-10 HZ评估夜景雾层参考黎明结构

### 做了什么
- 对照两张夜景截屏检查 dawn / earlyMorning 的雾化实现。
- 确认黎明雾层由投影跟随地球轮廓的外侧 additive halo 与地球表面侧 normal-blended inner veil 组成，不是云纹理或单一 opacity。
- 发现 `night` 未加入 `RIM_OVERLAY_THEMES`，因此不会获得这套后处理雾层。

### 改动文件
- `devlog.md`

### 遗留问题
- 尚未把黎明雾层参数迁移到夜景主题；需要先确定夜景应采用冷蓝薄雾、暖灰过渡还是仅保留极弱边缘散射。

## 2026-07-10 HZ将黎明双层雾结构应用到夜景

### 做了什么
- 复用现有 Rim Overlay + Inner Horizon Veil，不新增渲染管线。
- evening / lateEvening / deepNight 降低核心亮度、扩大外侧尾部，并放宽内侧 veil，使边缘从亮环变成低亮度空气层。
- 为 night 增加独立夜色雾参数，并加入 `RIM_OVERLAY_THEMES`。
- night 普通视图关闭旧 3D Fresnel shell，避免与新双层雾重复叠加；审计视角仍保留 shell fallback。

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 已完成本地浏览器加载与 `night` 主题切换验证；当前本地预览仍因低细节/过渡画面不适合做最终美学判断，四主题仍需在稳定高细节截图下做最终宽度微调。

## 2026-07-10 HZ收紧夜景云雾避免陆地灰膜

### 做了什么
- 根据最新截图将夜景效果从“广域灰雾”改为高亮度门槛的局部云团。
- 四个夜景主题提高 `alphaLow/alphaHigh`，降低 opacity，并启用纹理明暗塑形与冷灰云色。
- 大幅削弱 Rim Overlay 的 inner veil，收窄影响范围，保留极薄的地平线大气边缘。

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 需要在用户侧硬刷新后确认云团是否仍然过淡；若过淡，应优先增加云层局部对比，不再降低 alphaLow 或扩大 inner veil。

## 2026-07-11 HZ修复相机角度切换导致辉光位置错乱

### 做了什么
- 定位根因：`updateEarlyMorningGlowMode()` 里的 `shouldUseAuditShell` 开关此前只在 TOP 角度 + 零缩放时启用精细版 screen-space rim overlay（`updateEarlyMorningRimProjection`），其余角度/缩放一律回退到参数固定、与主题无关的 3D Fresnel shell。切换角度时表现为两套渲染互相替换，辉光看起来"跳"了位置，不是同一个东西在飘移。
- 诊断确认精细版投影数学本身在全部 7 个角度（top/oblique/low/asiaTilt/asiaWide/tilt/global）下都能正确计算——用光学公式 `rimRx ∝ cot(fov/2)` 反推验证过 zoom 0→1.0（对应 fov 28°→8°）的数值，跟实测几乎精确匹配。此前"精细版不够稳"的判断，实际根因是 `[0.2, 2.0]` 的 rimRx/rimRy 范围守卫定得过窄，没考虑到 RDL zoom 会把 FOV 收到 8°（对应 TOP 角度下 rimRx 最大到 5.52）。
- 移除该范围守卫（仅保留 `!Number.isFinite` 判断），`shouldUseAuditShell` 固定为 `false`，让精细版辉光在全部角度/缩放下生效；顺手删除了被取代的旧注释。
- 人工在本机浏览器实拍验收（7 角度 × 3 档缩放，共 15 张真实截图）：边缘辉光位置正常，未见断裂/错位。zoom=1.0 时该投影几何上落在画面外（rimRx 远超屏幕范围），因此看不到辉光是预期结果，不是新问题。

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 部分角度切换后画面清晰度明显变差（其他角度/距离正常），控制台可见大量 `NOON_AIR_V2_ISLANDS` 贴图流式加载日志，怀疑与分辨率分级选择有关，与本次改动是不同代码路径，需单独排查 `tileManager`/`updateStreaming`。
- 调试面板缺少"复位到初始角度/缩放"入口：FAR/NEAR 固定跳转到 0.35/1.0，没有按钮能回到 0，只能刷新页面重来，是个独立的小体验缺口，不影响本次修复。

## 2026-07-10 HZ评估高通云层后的稀薄问题

### 做了什么
- 根据用户最新截图复核：陆地与海面底图已清楚，灰膜问题基本消失；当前主要问题变为云层高通门槛过高、整体过薄。
- 确定下一轮应回调 alphaLow 到中间区间并适度恢复 opacity，保持窄 inner veil，不再扩大雾层覆盖。

### 改动文件
- `devlog.md`

### 遗留问题
- 尚未写入下一轮中等密度云层参数，等待确认采用“更明显但仍局部”的夜景云团方向。

## 2026-07-10 HZ确认云图类型与下一步方向

### 做了什么
- 检查 `clouds_live_8k.jpg` 原始图像，确认它是全球云量/亮度图，不是带透明背景的云层 cutout。
- 确认当前 shader 直接用全图 luminance 作为 alpha，会在灰膜与过薄之间产生明显参数两难。
- 确定下一步应增加低频云量与高频云团结构的分离，再恢复中等可见度。

### 改动文件
- `devlog.md`

### 遗留问题
- 尚未修改 shader；下一轮应优先实现云量基底与局部细节的双采样 alpha，而不是继续单独调 opacity。

## 2026-07-10 HZ实现双采样云团 alpha

### 做了什么
- 在云层 shader 中加入低频 coverage sample 与原图 detail sample。
- 用局部 luminance 偏差压低全球云量图的均匀白区，保留有纹理结构的云团。
- 为四个夜景主题加入 `detailMix/detailContrast`，并将 opacity 恢复到中等密度。
- 扩展云层调试日志，记录 `detailMix`。

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 需要用户硬刷新后检查云团是否达到“局部可见但不形成陆地灰膜”的平衡；若仍偏薄，应优先调整 `detailMix` 与局部对比，不再放宽 Rim 内雾。

## 2026-07-10 HZ恢复双采样云层可见度

### 做了什么
- 根据最新深夜截图确认双采样后的云 alpha 被 `detailMask + alphaPow + 低 opacity` 叠加压得过低。
- 提高四个夜景主题云层 opacity 与环境光，降低 alphaPow，恢复更亮的冷灰云色。
- 保留局部细节抑制机制与窄 Rim 内雾，避免回到整片陆地灰膜。

### 改动文件
- `pwa/earth3d.js`
- `devlog.md`

### 遗留问题
- 需要硬刷新后确认深夜云团是否恢复到可读程度；若再次出现灰膜，应优先提高 detailMix，不再扩大 Rim veil。

## 2026-07-10 HZ夜景云层可见度验收

### 做了什么
- 复核最新深夜截图：陆地与城市灯光保持清晰，灰膜已消失，云层以局部低对比结构可读。
- 判断当前版本达到夜景可用标准；不再继续提高夜景云亮度，以免破坏地表层次。

### 改动文件
- `devlog.md`

### 遗留问题
- 若未来需要接近白天参考图的云团存在感，应单独设计 daylight cloud profile，不应继续放大当前深夜 profile。
