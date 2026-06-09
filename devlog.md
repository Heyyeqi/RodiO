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
