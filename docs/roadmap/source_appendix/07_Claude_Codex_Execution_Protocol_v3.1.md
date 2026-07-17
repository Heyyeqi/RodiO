# 07 Claude Codex Execution Protocol v3.1

## 0. 总规则

每轮只允许一种任务类型：

```text
只读审计 / 生成候选 / 接入候选 / 视觉验收 / production 化 / commit / 基线归档
```

不得一轮同时做多个阶段。

---

## 1. 每轮开始前必须输出

```text
本轮阶段：
本轮目标：
允许修改文件：
禁止修改文件：
允许生成资源：是/否
允许 commit：是/否
本轮不处理事项：
回滚方案：
```

未输出以上内容，不得施工。

---

## 2. 只读审计模板

```text
# RodiO 审计报告

## 1. 工作区状态
- pwd：
- git status --short：
- git log --oneline -5：

## 2. 当前资源状态
- dayTexture：
- nightTexture：
- cloud：
- specular：
- sky：
- candidates：
- production：

## 3. 当前代码状态
- 时段 key：
- earth renderer：
- sky renderer：
- debug API：
- fallback：

## 4. 与 Roadmap 对齐
- 当前处于哪个阶段：
- 可进入的最小任务：
- 不应进入的任务：

## 5. 风险
- 高风险：
- 中风险：
- 低风险：

## 6. 施工许可结论
允许 / 不允许施工：
理由：
需要 RW 确认：
```

---

## 3. 生成候选模板

允许生成候选时，必须遵守：

- 输出到 candidates 或 source/staging；
- 不替换 production；
- 不改默认引用；
- 不 commit；
- 输出尺寸、体积、路径、生成参数。

---

## 4. 接入候选模板

候选接入只能增加可切换入口，不得设为默认。

必须有：

```js
?earthCandidate=xxx
```

或同等调试开关。

---

## 5. 视觉验收模板

每次验收必须包含：

- 测试主题 / time mode；
- 测试地点 / camera preset；
- 截图路径；
- 主观判断；
- 是否通过；
- 不通过原因；
- 是否建议 production 化。

---

## 6. Commit 前检查

```text
[ ] git diff 只包含授权文件
[ ] 没有 tmp 资源
[ ] 没有候选误入 production
[ ] 没有自动改 service worker
[ ] 没有远期功能偷跑
[ ] 有回滚路径
[ ] 有验收记录
```

---

## 7. 永久禁止项

- 不得使用 `~/Projects/RodiO_old_unused`；
- 不得工作树不 clean 时继续叠加施工；
- 不得把 cloud / sky / atmosphere / terminator / music / weather 混在一个 commit；
- 不得自动 commit，除非 RW 明确允许；
- 不得把远期功能提前实现；
- 不得把失败中间产物保留在 production；
- 不得为了“好看”覆盖真实资源依据；
- 不得在未审计前升级 PBR；
- 不得偷跑 Terminator。

---

## 8. 给 Codex / Claude Code 的通用开场白

```text
你是 RodiO 项目的执行审计助手。请严格按文件执行，不得自由发挥扩大范围。

请先阅读：
1. 00_Master_Roadmap_v3.1_FullExecution.md
2. 07_Claude_Codex_Execution_Protocol_v3.1.md
3. 本轮任务相关实施文件：______
4. 必要 source_appendix 原文：______

本轮任务：______
本轮禁止：______
允许修改：______
允许 commit：否，除非我后续明确批准。

先输出本轮阶段、允许范围、禁止范围和风险，再执行。
```
