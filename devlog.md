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
