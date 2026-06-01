# RodiO Codex Handoff Protocol

This document defines the Codex session handoff and development boundary rules for RodiO.

## Purpose

- Keep handoffs explicit when a thread becomes too long, unstable, or phase boundaries start to blur.
- Keep each session focused on one objective and one commit scope.
- Preserve a stable startup baseline for Git and project context.

## When to recommend a new session

Recommend starting a new Codex session and generating a full handoff text when any of the following is true:

1. Responses become noticeably slower.
2. The conversation is too long to track the current phase accurately.
3. Output starts repeating, skipping details, or mixing phase boundaries.
4. Git status, commit state, or task boundaries keep getting rechecked and still cause errors.
5. A new phase is about to begin and the current thread is already long.
6. The user explicitly asks for a new session.
7. Continuing in the current session increases the risk of mistakes.

Suggested response:

> 建议新开一个 Codex 会话，我可以生成完整交接文本。

## Long-term rules

- Run startup checks before making phase decisions.
- Confirm the Git baseline with `git status --short` and recent commits.
- Do not use `git add .`.
- Do not mix unrelated changes in one commit.
- Each phase should focus on one clear target.
- Before a commit, state the modified files and the boundary of the change.
- Handoff text must include the current phase, latest commit, uncommitted file groups, and the next task.

## Required handoff text

When a new session is needed, generate a copyable handoff block with these sections:

```md
# RodiO 新 Codex 会话交接文本

## 1. 项目目录约束
## 2. 当前 Git 状态
## 3. 当前阶段
## 4. 已完成工作
## 5. 当前未完成事项
## 6. 当前禁止事项
## 7. 下一步任务
## 8. 新会话启动后必须执行的命令
## 9. 注意事项
```

The handoff text should include:

- Project root: `~/Projects/RodiO`
- Do not use: `~/Projects/RodiO_old_unused`
- Current branch
- Current `git status`
- Latest commit hash
- Recent 5 commits
- Whether the tree is clean
- Any uncommitted files and their phase ownership if not clean
- Whether the project is currently allowed to enter the next phase
- The current phase constraints relevant to the active work

It should also list the most important completed commits in order and briefly explain what each did.

It should clearly state what remains unfinished, including:

- Whether screenshots still need to be collected
- Whether `debugState` JSON still needs to be exported
- Whether `cloudAlphaMap` already exists
- Whether cloud resources have passed audit
- Whether E1 cloud construction is allowed
- Whether there are any blocking items

## Current phase constraints

Use this section only as an example of how to record phase-specific boundaries in a handoff. Do not treat the examples below as permanent rules.

- Example: do not enter Sky P1B during the current sky phase.
- Example: do not start dual LUT before the current color-grading phase is approved.
- Example: do not implement Terminator until its phase is explicitly opened.
- Example: do not use PBR if the current phase still requires the non-PBR material path.
- Example: do not modify the player unless the active phase explicitly allows it.
- Example: do not modify the service worker unless the active phase explicitly allows it.
- Example: do not modify `index.html` unless the active phase explicitly allows it.
- Example: do not hard-code nonexistent resource paths.

## Required startup commands

Every new Codex session should begin by running:

```bash
pwd
git status --short
git log --oneline -5
```

If the task involves resource audits, also run:

```bash
find pwa/assets/earth/clouds -maxdepth 2 -type f | sort
find docs/assets/clouds -maxdepth 2 -type f | sort
```

## Operating principle

- Do not force progress when the conversation becomes unstable.
- Prefer a clean handoff over risky continuation.
- Keep the session scoped to one objective, one boundary set, and one commit.
