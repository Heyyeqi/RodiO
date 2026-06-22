#!/bin/bash
# RodiO Dev Session Bootstrap — Phase0-AutoContext (D1 enhanced)
# 用途：在开始开发前手动运行，输出 Session Baseline
# 使用：bash scripts/bootstrap_dev_session.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCAL_CONTROL="${HOME}/Library/Mobile Documents/iCloud~md~obsidian/Documents/RW Vault/01_RodiO"
REMOTE_CONTROL="Heyyeqi/RodiO-Control"
CURRENT_TASK_FILE="${LOCAL_CONTROL}/02_CURRENT_TASK.md"

echo ""
echo "【RodiO Session Baseline】"
echo ""

# ── Code repo ─────────────────────────────────────────────
echo "Code repo:"
echo "  path:          ${REPO_ROOT}"
echo "  branch:        $(git -C "${REPO_ROOT}" branch --show-current)"
echo "  latest commit: $(git -C "${REPO_ROOT}" log --oneline -1)"

WT_STATUS="$(git -C "${REPO_ROOT}" status --short)"
if [ -z "${WT_STATUS}" ]; then
  echo "  working tree:  clean"
else
  echo "  working tree:  dirty"
  git -C "${REPO_ROOT}" status --short | sed 's/^/    /'
fi

UNPUSHED="$(git -C "${REPO_ROOT}" log --oneline @{u}..HEAD 2>/dev/null | wc -l | tr -d ' ')" || UNPUSHED="unknown"
if [ "${UNPUSHED}" = "0" ]; then
  echo "  push status:   up to date"
elif [ "${UNPUSHED}" = "unknown" ]; then
  echo "  push status:   (no upstream tracked)"
else
  echo "  push status:   ${UNPUSHED} unpushed commit(s)"
fi

echo ""

# ── Control source ────────────────────────────────────────
echo "Control source:"
echo "  local:  ${LOCAL_CONTROL}"
echo "  remote: https://github.com/${REMOTE_CONTROL}"

# Attempt to read latest known control commit from local Obsidian
CONTROL_COMMIT="control source unavailable"
if [ -d "${LOCAL_CONTROL}" ]; then
  # Try to find a git repo at the control source path
  if git -C "${LOCAL_CONTROL}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    CONTROL_COMMIT="$(git -C "${LOCAL_CONTROL}" log --oneline -1 2>/dev/null || echo 'control source unavailable')"
  else
    # Fall back to scanning EP/status files for embedded commit ref
    SCAN="$(grep -rh 'latest known control commit\|RodiO-Control.*commit' "${LOCAL_CONTROL}/07_EXEC_PLAN/" 2>/dev/null | grep -oE '[0-9a-f]{7,40}.*' | head -1)" || true
    [ -n "${SCAN}" ] && CONTROL_COMMIT="${SCAN}"
  fi
fi
echo "  latest known control commit: ${CONTROL_COMMIT}"

echo ""

# ── Current state (from 02_CURRENT_TASK.md) ──────────────
echo "Current state:"
if [ -f "${CURRENT_TASK_FILE}" ]; then
  PHASE="$(awk '/^## 当前阶段/{found=1; next} found && /^##/{exit} found && NF{print; exit}' "${CURRENT_TASK_FILE}")"
  TASK="$(awk '/^## 当前任务/{found=1; next} found && /^##/{exit} found && NF{print; exit}' "${CURRENT_TASK_FILE}")"
  NEXT="$(awk '/^## 下次从哪里开始/{found=1; next} found && /^##/{exit} found && /^- /{print; count++; if(count>=2) exit}' "${CURRENT_TASK_FILE}")"
  echo "  phase:        ${PHASE:-unknown}"
  echo "  current task: ${TASK:-unknown}"
  echo "  next step:"
  echo "${NEXT}" | sed 's/^/    /'
else
  echo "  (02_CURRENT_TASK.md not found — control source unavailable)"
fi

echo ""

# ── Hard boundaries ───────────────────────────────────────
echo "Hard boundaries:"
echo "  - no push main"
echo "  - no Railway"
echo "  - no production / candidates / DAY_TEXTURE_VARIANT"
echo "  - no GEE / data download / raster / NPZ"
echo "  - no Claude settings / hook"
echo "  - no B-6.2X-D3 unless RW confirms"

echo ""
echo "【Baseline End】"
echo ""
