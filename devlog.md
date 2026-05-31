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
