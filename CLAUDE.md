# RodiO — 项目上下文文件

> 每次对话开始前必须读取本文件。
> 每次任务完成后必须在 `devlog.md` 末尾追加一条记录（格式见文末）。
> **规划与现状**：`docs/roadmap/STATUS.md` 是当前建设任务的唯一现状真相来源（Stage 0 审计结论、差距矩阵、优先级队列、GitHub Issue 映射）。开始任何建设任务前先读它；`00_Ultimate_Build_Plan_v1.0.md`/`01_P4_Touch_the_Earth_v1.0.md` 是同目录下的产品愿景与当前阶段执行计划。

---

## 项目简介

RodiO 是一个个人 AI 电台应用。核心体验是：由 AI（DeepSeek）根据当前时间、天气、天文节气、用户偏好自动选曲，并生成 DJ 播报语音（MiniMax TTS），形成连续的沉浸式收听流。

- 线上地址：https://web-production-a5193.up.railway.app
- 仓库：Heyyeqi/RodiO，**主干直入策略**：所有建设任务直接小步提交到 main，不开长期功能分支；通过 GitHub Issue + Milestone 追踪任务边界（见 `docs/roadmap/STATUS.md` §2、§5）。`wip/easter-themes` 等少数归档分支例外保留，见 STATUS.md 分支状态表。
- 部署方式：Railway + Procfile（`web: node server.js`），**迁移中**：计划从 Railway 迁移到腾讯云，过渡期以本地开发环境为主要验证环境，Railway production 仅作为迁移完成前的临时兜底。Spotify token 持久化已从"Railway优先"改为"本机 SQLite（`core/state.js`）优先"，Railway GraphQL push 仍保留但已是可选兜底层（详见 `core/spotify.js` `loadPersistedUserToken()`/`persistUserToken()`）。
  - **2026-07-18 起：Railway 的 GitHub 自动部署已断开**（`railway service source disconnect`），`git push` 到 main 不会再触发 Railway 重新部署/重启。当前 production 实例会一直保持运行，直到手动执行 `railway service source connect --repo Heyyeqi/RodiO --branch main --service web` 重新接上，或用 `railway up`/`railway redeploy` 手动部署一次。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 运行时 | Node.js / CommonJS |
| Web 服务 | Express + HTTP + WebSocket (ws) |
| AI 选曲 | DeepSeek（`deepseek-v4-flash`，OpenAI 兼容接口），模块为 `core/claude.js`；内部部分变量/函数名（如 `triggerQwenEnhancer`）仍沿用 Qwen 命名，为历史遗留，不影响功能 |
| 音乐源 | Spotify Web API（主力）+ 网易云 NCM（备用/降级） |
| TTS | MiniMax TTS，串行队列控制，本地缓存 |
| 状态存储 | SQLite（better-sqlite3），模块为 `core/state.js` |
| 调度 | node-cron，模块为 `core/scheduler.js` |
| 前端 | 单文件 PWA（`pwa/index.html`），含 Spotify Web Playback SDK |
| 部署持久化 | Railway GraphQL API 持久化 Spotify token 到环境变量 |

---

## 核心模块结构

```
server.js              主控：HTTP API、WebSocket、队列管理、OAuth
core/
  claude.js            Qwen 调用与 JSON 解析
  context.js           选曲上下文构建（天气、天文、节气、农历、偏好、历史）
  spotify.js           Spotify OAuth、token 管理、搜索、歌单拉取
  tts.js               MiniMax TTS 调用、缓存、串行队列
  state.js             SQLite 状态库
  queue-manager.js     内存 ready pool，补货串行控制
  scheduler.js         晨间播报、整点选曲、WebSocket 广播
  router.js            用户输入意图识别（系统控制 vs 音乐请求）
  search-utils.js      歌名/艺人归一化、模糊匹配打分
  astronomy.js         日月相位、节气、文化节点、情绪提示
  songpool.js          本地歌单解析、离线素材
prompts/
  dj-persona.md        DJ 人格设定
  mood-rules.md        选曲规则
pwa/
  index.html           前端主逻辑（播放控制、DJ语音、Explain、UI状态）
  style.css
  sw.js                Service Worker
  manifest.json        PWA 配置
scripts/
  ncm-login.js         网易云登录
  clear-ncm-hit-cache.js  清理 NCM 命中缓存
```

---

## 队列架构（三阶段）

1. **Phase 1**：Spotify 用户歌单拉取（主力补货）
2. **Phase 2**：Qwen 异步背景选曲（智能补充）
3. **黑名单机制**：过滤近期播放记录，避免重复

Spotify 搜索失败时降级到 NCM；Phase 1 补货失败时降级到 Qwen。

---

## 已知问题（截至 2026-07-17，部分行未随代码演进更新，遇到时请先复核再信任）

| 问题 | 位置 | 状态 |
|---|---|---|
| NCM cookie 过期导致播放中断 | `pwa/index.html:1994` | 未修复（未在本轮 Stage 0 审计范围内，需要单独复核） |
| Spotify Phase 1 补货偶发返回空 | `server.js:1082` | 已在 `2ca0d3b fix(spotify): retry Phase 1 playlist refill when a pull comes back empty` 修复，此行过期，待确认后移除 |
| Spotify device 失效后 reinit 不稳定 | `pwa/index.html:1217` | 未修复（未在本轮 Stage 0 审计范围内，需要单独复核） |
| MiniMax TTS 静默失败，无降级 | `core/tts.js`、`server.js:997-1002`、`pwa/index.html:2599-2664` | **已确认为真实bug**（2026-07-17第三轮审计）：TTS失败时服务端`.catch()`吞掉错误只打日志，前端收到`say_audio:null`仍尝试`Audio(null).play()`静默失败，无文字降级。追踪于 [GitHub Issue #26](https://github.com/Heyyeqi/RodiO/issues/26) |
| 浏览器 autoplay 限制影响 DJ 语音 | `pwa/index.html:2082` | 未修复（未在本轮 Stage 0 审计范围内，需要单独复核） |
| /api/explain 接口 DeepSeek 或 TTS 任一失败即 500 | `server.js:1417` | 未处理降级（AI provider 名称已更新，问题本身状态未复核） |
| Dislike评分未接入候选排序 | `core/candidate-rerank.js` | **已确认为架构性断裂**（2026-07-17第三轮审计）：`song_feedback.score`正确写入但选曲逻辑从未查询它，评分系统和实际选曲完全脱节。追踪于 [GitHub Issue #25](https://github.com/Heyyeqi/RodiO/issues/25) |
| 星星渲染被 canvas clipping 遮挡 | `pwa/index.html` | **疑似已过期**：2026-07-17 Stage 0 审计（见 `docs/roadmap/STATUS.md` §1.1）发现全代码库零 clipping 痕迹，星空两层材质均 AdditiveBlending+depthWrite:false，物理上不可能被此机制遮挡，且近期星空/Deep Space 渲染工作正常。待用户肉眼最终复核后关闭，见 [GitHub Issue #13](https://github.com/Heyyeqi/RodiO/issues/13) |

---

## 设计原则

- 音乐美学基准：有东西藏在里面但不急着告诉你（参考：王菲、坂本龍一、Nujabes、The Weeknd *Dawn FM*、Nicola Conte *Rituals*）
- 前端风格：沉浸、克制，无多余 UI 噪音
- 错误处理原则：能降级就降级，不要因单点失败中断整个播放流

### 产品护栏（不能只靠审美自觉，必须写进规则）

- 不做信息流；不做社区广场；不做直播和 K 歌入口；不做无限刷新推荐；
- 每日推荐数量有限；AI 主动触发次数有限；推荐理由字数有限；
- 用户可以一键关闭主动陪伴；所有主动推荐必须可解释。

---

## 开发规范

- 每次任务完成后，在 `devlog.md` 末尾追加记录
- 不引入新的全局状态管理库，状态统一走 `core/state.js`（SQLite）
- TTS 请求必须走 `core/tts.js` 的串行队列，不得绕过
- Spotify token 变更必须同步持久化到本机 SQLite（`state.setPref`）；Railway 环境变量持久化保留但已降级为可选兜底，未配置 Railway 时会自动跳过

### 3D渲染/相机新功能：先风险分级，再定执行方案（2026-07-18 确立）

开始任何触及 `pwa/earth3d.js` 渲染管线的新功能前，**先判断属于哪一类，再谈怎么做**——顺序不能反，分类本身决定了执行方案的形状。

**Category A（可以直接改现有代码）**：只改变"参数怎么算"，不改变相机与几何体的基础关系（复用已有 mesh/shader/相机语法系统）。例：#39 连续日夜过渡系统（换插值方式，不换渲染对象）、#28 镜头模式库（编排已验证的构图/运动原语）、地球拖拽类交互（复用已有经纬度控制）。
- 风险控制：跨系统改动先走影子验证（只算不接，在关键锚点对比新旧输出一致后再切断旧逻辑，参考 Song Selection v2 的 shadow-mode 方法论）；按子系统小步提交，不要天空+海洋+云+星空一次性改；每次改动后截图对比关键时刻画面，防止肉眼难查的漂移。

**Category B（必须先建独立试验场景，验证通过再接入）**：改变相机与几何体的基础关系（相机贴近/进入几何体内部、全新移动路径、新 LOD 策略）。例：地平线视角(#36)、深海模式(#37)、航线视角(#40)——深海模式方案文档自己就指出"不建议直接把摄像机塞进现有海洋球层"，会有背面剔除/法线反转/深度缓冲异常等问题。
- 实现方式：延续项目已有的 `?earthCandidate=` 调试隔离约定（及 Theme Tuner 面板里已有的 "Camera Presets (E7 debug)"/"Camera Grammar V1 (debug)" 模式），新增 `?labMode=` 类 URL 参数入口；用独立的 `THREE.Scene` 对象和独立相机，不复用主 Earth 场景的 mesh/shader；验证稳定（无 z-fighting、无深度异常、帧率可接受）之前完全不碰主渲染管线，验证通过后再"毕业"整合进主系统。

---

## devlog 追加格式

```
## YYYY-MM-DD HZ任务简述

### 做了什么
- ...

### 改动文件
- ...

### 遗留问题
- ...
```
