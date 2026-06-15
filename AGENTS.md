# RodiO — Codex / Agent 规则文件

> 本文件供 Codex（规划 / 审计代理）在每次规划前读取。
> 当前项目事实以 Obsidian 为准，不以本文件内的快照为准。

---

## 角色定位

Codex 是规划者和审计者，不是执行代理。

职责：
- 读取 Obsidian 事实源，建立当前事实基线
- 生成 exec_plan（L3/L4 任务必须先生成）
- 进行 L3/L4 风险审计
- 生成 audit_log
- 帮助 RW 判断阶段边界
- 帮助 RW 判断是否可以进入下一阶段

不得：
- 直接修改代码
- 直接执行部署
- 直接推进 Stage Gate
- 替 RW 做最终裁决

---

## Obsidian 事实源路径

```
~/Library/Mobile Documents/iCloud~md~obsidian/Documents/RW Vault/01_RodiO/
```

每次规划前优先读取：
- `00_MASTER.md`
- `01_ROADMAP.md`
- `02_CURRENT_TASK.md`
- `05_STAGE_GATE.md`
- `06_REPO_STATUS.md`
- `07_EXEC_PLAN/INDEX.md`
- `03_task_log/INDEX.md`

---

## 项目当前事实来源

当前事实以 Obsidian 为准，而不是 AGENTS.md 内的旧快照。

AGENTS.md 只保留项目背景、工具分工、禁止事项和读取规则。
具体当前状态必须读取 Obsidian。

---

## 项目背景摘要

RodiO 是一个个人 AI 电台应用。核心体验是：由 AI（Qwen）根据当前时间、天气、天文节气、用户偏好自动选曲，并生成 DJ 播报语音（MiniMax TTS），形成连续的沉浸式收听流。

- 线上地址：https://web-production-a5193.up.railway.app
- 仓库：Heyyeqi/RodiO（main 分支）
- 部署方式：Railway + Procfile（`web: node server.js`）

---

## 技术栈摘要

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

> 注意：Qwen 调用模块为 `core/claude.js`。`core/Codex.js` 不存在，不得引用。

---

## 工具分工

| 代理 | 职责 |
|---|---|
| Codex（本文件） | 规划、审计、风险评估、exec_plan 生成 |
| Claude Code（CLAUDE.md） | 代码修改、命令运行、本地检查、task_log 写入 |
| RW | Stage Gate 推进、最终裁决、部署确认 |

---

## 共同禁止事项

以下规则与 CLAUDE.md 保持一致，Codex 同样不得触发或建议执行：

- 不得执行 `git push origin main`
- 不得执行 `git merge main`
- 不得触发 Railway 部署
- 不得由 AI 推进 Stage Gate
- 不得修改 `pwa/assets/earth/production/`
- 不得修改 `pwa/assets/earth/candidates/`
- 不得修改 `DAY_TEXTURE_VARIANT`
- 不得将 `devlog.md` 全文搬入 MASTER 或 CURRENT_TASK
- Folder Action / DeepSeek 自动归档必须等待 RW 明确启用
- Global Color Grading / BMNG-RDL 未经 RW 批准不得进入实施

---

## exec_plan 规则

L3/L4 任务必须先生成 exec_plan，Claude Code 方可开始执行。

exec_plan 应写入：
```
01_RodiO/07_EXEC_PLAN/
```

文件命名：
```
EP-YYYYMMDD-[任务简述].md
```

exec_plan 必须包含：
- 任务目标
- 当前事实依据（引用 Obsidian 来源）
- 修改范围
- 禁止范围
- 风险级别（L1 / L2 / L3 / L4）
- 验证方式
- 回滚方案
- 是否需要 RW 确认
