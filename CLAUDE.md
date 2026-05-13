# RodiO — 项目上下文文件

> 每次对话开始前必须读取本文件。
> 每次任务完成后必须在 `devlog.md` 末尾追加一条记录（格式见文末）。

---

## 项目简介

RodiO 是一个个人 AI 电台应用。核心体验是：由 AI（Qwen）根据当前时间、天气、天文节气、用户偏好自动选曲，并生成 DJ 播报语音（MiniMax TTS），形成连续的沉浸式收听流。

- 线上地址：https://web-production-a5193.up.railway.app
- 仓库：Heyyeqi/RodiO（main 分支，唯一分支）
- 部署方式：Railway + Procfile（`web: node server.js`）

---

## 技术栈

| 层 | 技术 |
|---|---|
| 运行时 | Node.js / CommonJS |
| Web 服务 | Express + HTTP + WebSocket (ws) |
| AI 选曲 | Qwen via DashScope（OpenAI 兼容接口），模块为 `core/claude.js` |
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

## 已知问题（截至 2025-05-13）

| 问题 | 位置 | 状态 |
|---|---|---|
| NCM cookie 过期导致播放中断 | `pwa/index.html:1994` | 未修复 |
| Spotify Phase 1 补货偶发返回空 | `server.js:1082` | 未定位根因 |
| Spotify device 失效后 reinit 不稳定 | `pwa/index.html:1217` | 未修复 |
| MiniMax TTS 限流控制是否真正生效 | `core/tts.js` | 未验证 |
| 浏览器 autoplay 限制影响 DJ 语音 | `pwa/index.html:2082` | 未修复 |
| /api/explain 接口 Qwen 或 TTS 任一失败即 500 | `server.js:1417` | 未处理降级 |
| 星星渲染被 canvas clipping 遮挡 | `pwa/index.html` | 未修复 |

---

## 设计原则

- 音乐美学基准：有东西藏在里面但不急着告诉你（参考：王菲、坂本龍一、Nujabes、The Weeknd *Dawn FM*、Nicola Conte *Rituals*）
- 前端风格：沉浸、克制，无多余 UI 噪音
- 错误处理原则：能降级就降级，不要因单点失败中断整个播放流

---

## 开发规范

- 每次任务完成后，在 `devlog.md` 末尾追加记录
- 不引入新的全局状态管理库，状态统一走 `core/state.js`（SQLite）
- TTS 请求必须走 `core/tts.js` 的串行队列，不得绕过
- Spotify token 变更必须同步持久化到 Railway 环境变量

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
