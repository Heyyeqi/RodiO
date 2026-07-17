# 01 Current Workflow: How To Use This Pack

## 1. 不要一次性把所有文件丢给 AI 自由发挥

正确方式是“主文件 + 执行协议 + 本轮实施文件 + 必要原始附录”。

错误指令：

```text
这是 RodiO 的所有规划文件，你帮我继续开发。
```

正确指令：

```text
你是 RodiO 项目的执行审计助手。
请先阅读：
1. 00_Master_Roadmap_v3.1_FullExecution.md
2. 07_Claude_Codex_Execution_Protocol_v3.1.md
3. 本轮任务相关实施文件：______
4. 必要原始附录：______

本轮只允许处理：______
本轮禁止修改任何文件 / 或仅允许修改：______
不得自动 commit。
输出必须包括：当前状态、允许范围、禁止范围、风险、下一步建议。
```

## 2. 推荐工作流

```text
只读审计
  → 生成候选
  → 候选接入但不设默认
  → 人工截图验收
  → 通过后 production 化
  → commit
  → 基线归档
  → 下一阶段审计
```

## 3. 当前推荐第一轮指令

```text
请根据以下文件对当前 RodiO 项目进行只读审计：
- 00_Master_Roadmap_v3.1_FullExecution.md
- 02_Earth_Visual_Foundation_Implementation_v3.1.md
- 04_Resource_Performance_Governance_v3.1.md
- 07_Claude_Codex_Execution_Protocol_v3.1.md
- source_appendix/A_RodiO_3D地球视觉优化近期推进规划_v1.0_原始.md
- source_appendix/B_RodiO_3D地球视觉系统近期推进规划_v2.0_上轮.md

本轮禁止修改任何文件，禁止生成资源，禁止 commit。

请输出：
1. 当前 git 状态；
2. 当前 earth 相关资源目录结构；
3. 当前 production / candidates / source / archive / tmp 是否清晰；
4. 当前 dayTexture / nightTexture / cloud / specular / sky 资源引用情况；
5. 当前代码中实际启用的时段 key；
6. 当前地球视觉阶段对应 Master Roadmap 的哪个阶段；
7. 下一步建议进入哪个最小任务；
8. 本轮不得处理的事项清单。
```

## 4. 每轮结束后的 RW 人工判断

每轮 AI 输出后，RW 应只判断三件事：

1. 它有没有越权修改；
2. 它有没有把远期功能提前施工；
3. 它给出的下一步是否足够小。

若任何一项不满足，拒收。
