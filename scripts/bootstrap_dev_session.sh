#!/bin/bash
# RodiO Dev Session Bootstrap — Phase0-AutoContext
# 用途：在开始开发前手动运行，输出简短 Session Baseline
# 使用：bash scripts/bootstrap_dev_session.sh
# 也可作为 Claude Code hook 调用的后端脚本

set -e

OBSIDIAN_ROOT=~/Library/Mobile\ Documents/iCloud~md~obsidian/Documents/RW\ Vault/01_RodiO

echo "=== RodiO Session Baseline ==="
echo ""

echo "[当前阶段]"
grep -A1 "^## 当前阶段" "$OBSIDIAN_ROOT/02_CURRENT_TASK.md" | tail -1
echo ""

echo "[当前分支]"
git branch --show-current
echo ""

echo "[最新 commit]"
git log --oneline -1
echo ""

echo "[工作区状态]"
git status --short
echo ""

echo "[上次停在]"
grep -A2 "^## 上次停在" "$OBSIDIAN_ROOT/02_CURRENT_TASK.md" | tail -2
echo ""

echo "[下次从哪里开始]"
grep -A5 "^## 下次从哪里开始" "$OBSIDIAN_ROOT/02_CURRENT_TASK.md" | tail -5
echo ""

echo "[禁止事项]"
echo "push main / merge main / 触发 Railway / 修改 production / 修改 DAY_TEXTURE_VARIANT"
echo ""

echo "=== Baseline End ==="
