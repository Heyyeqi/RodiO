# RodiO Project Control Bridge

## Repositories

| 仓库 | 用途 |
|---|---|
| `Heyyeqi/RodiO` | 代码仓库（应用代码、部署资产、脚本） |
| `Heyyeqi/RodiO-Control` | 控制仓库（项目事实源、exec_plan、task_log、决策记录） |

## Purpose

RodiO-Control is the remote project fact source for Evan web, Codex, and GitHub-based review.
RodiO remains the code repository. The two repos must never be merged or confused.

## Fact Source Priority

### For Evan web / Codex / remote agents

Read from GitHub control repo: `Heyyeqi/RodiO-Control`

Core files to read first:
- `00_MASTER.md`
- `01_ROADMAP.md`
- `02_CURRENT_TASK.md`
- `05_STAGE_GATE.md`
- `06_REPO_STATUS.md`
- `07_EXEC_PLAN/INDEX.md`
- `03_task_log/INDEX.md`

### For local Claude Code

Read from local Obsidian path:
```
~/Library/Mobile Documents/iCloud~md~obsidian/Documents/RW Vault/01_RodiO/
```

## Startup Rule

Do not start implementation based only on memory or previous chat context.
Read the control source first, then inspect the code repo.

If local Obsidian and remote RodiO-Control conflict, stop and ask RW to confirm. Do not choose automatically.

## Boundary

- Do not initialize RodiO-Control inside the RodiO code repo.
- Do not copy code assets into RodiO-Control.
- Do not store secrets, tokens, generated rasters, NPZ, production textures, or local settings in RodiO-Control.
- Do not push main or trigger Railway unless RW explicitly confirms.
- Do not auto-push RodiO-Control without RW authorization.

## Current Phase

Phase 0.5 establishes the bridge between RodiO and RodiO-Control.
It does not authorize B-6.2X-D3 or any production asset change.

## Last Updated

2026-06-22 — Phase 0.5-D4
