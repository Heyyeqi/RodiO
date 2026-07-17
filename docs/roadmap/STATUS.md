# RodiO Roadmap — Current Status

> 本文件是 RodiO 建设任务的唯一现状真相来源（source of truth）。
> 每次任务完成、每次 Stage 审计更新，都必须回来更新本文件，而不是只写 devlog.md。
> devlog.md 记录"做了什么"；本文件记录"现在处于什么状态、接下来该做什么"。
> 无论在哪个分支、隔了多久回来，先读这份文件，再读 devlog.md 最近几条。

最后更新：2026-07-17（P4 Stage 0 Unified Current-State Audit 完成后）

---

## 0. 文档层级

| 文件 | 定位 | 更新频率 |
|---|---|---|
| `00_Ultimate_Build_Plan_v1.0.md` | 最终产品愿景，全部建设域（A-U），永久性北极星，几乎不改 | 极低 |
| `01_P4_Touch_the_Earth_v1.0.md` | 当前阶段（P4）的具体执行计划：Stage 0-7 | 阶段完成时更新 |
| `02_Living_Earth_Plan_v1.0.md` | P4 的技术细节参考（运动参数、星空分层数值等），部分已被 P4 取代 | 很低，仅作参考 |
| `STATUS.md`（本文件） | 实时现状、差距矩阵、优先级、GitHub Issue 映射 | **每次任务完成后更新** |

---

## 1. Stage 0 现状审计结论（2026-07-17）

审计方式：Explore agent 直接读代码 + grep 验证，而非依赖文档自述。以下结论**已被代码验证**，可直接作为后续任务的依据。

### 1.1 比文档预估更成熟 —— 不要重建，直接在其上开工

| 系统 | 文档假设 | 代码实测 | 关键证据 |
|---|---|---|---|
| 相机 Director (`pwa/earth3d.js`) | Living Earth v1 估计"20-30%成熟，需要 Director 重构" | 已是生产级构图驱动引擎：`CAMERA_PRESETS`/`CAMERA_COMPOSITIONS`/`CAMERA_SEQUENCES`、7种运动原语、`transitionToComposition()`（~6828行）、`_updateGramTransition/_updateGramMotion/_updateGramAutoPilot`（~6969/213/6755行） | 多系统会在同一帧写相机状态（precompute→breathe→orbital→transition，后写者生效），这是可用的隐式仲裁，不是bug。**最小仲裁方案（不重写Director）已被验证安全**，插入点精确定位：状态对象插入~200行，`_updateGramTransition`守卫加在6970行，`_updateGramAutoPilot`守卫加在6756行，pointer事件监听加在~7026行（wheel监听之后），惯性衰减tick加在~7078行 |
| 星空系统 | 假设"无/需从零建两层 Points" | 已是成熟两层系统：900点程序化`Points`（`buildStarField()`，428/3745行）+ 8K真实星图`starSphere`（3752-3828行，含twinkle uniform），均`AdditiveBlending`+`depthWrite:false`，per-theme独立透明度 | CLAUDE.md"星星被canvas clipping遮挡"经审计**95%置信度已过期**：代码零clipping痕迹（无`clippingPlanes`设置），65天devlog无相关修复记录，且加性混合材质本就不可能被遮挡。**建议标记该已知问题为已解决**，待用户最终肉眼确认后关闭 |
| Astronomy Bridge (`core/astronomy.js`) | Ultimate Build Plan §14.6 列为"应建立"的共享数据桥 | **已经是唯一数据源**：`getAstronomyContext()`同时喂给选曲(`core/context.js:456-488`)、视觉(`pwa/earth3d.js:304-400`七曜色调)、来信(`server.js:1495-1679` `/api/explain`)。太阳位置/时段、月相/月龄、农历、24节气、季节质感、22个文化节点、星空可见度全部已实现且被三方共同消费 | 唯一缺口：日食、流星雨、极光、潮汐仍是空字段（这四项本身也被两份文档列为冻结/低优先级） |
| 天外来信 (`server.js` `/api/explain`) | Ultimate Build Plan §16 列为"应建立"的分层生成架构 | **已完整实现**：DeepSeek驱动，七曜×节气×天气三层调性引擎（intensity/warmth向量），16种"切入角度"策略防止千篇一律，`commentary_history`表做防重复 | 这不是"要建"的任务，是"要调风格"的任务——直接对应用户提出的"天外来信的设置"这一诉求 |

### 1.2 确认存在的真实缺口

| 系统 | 现状 | 对应 P4 Stage |
|---|---|---|
| 三态 UI（Full/Minimal/EarthOnly） | 完全未实现，无 `uiMode`。但 `dj-speaking` 的 class-based CSS 过渡模式（`pwa/index.html:851-873`）可直接复用；上一次会话已讨论出草案未实施（见 devlog.md 2026-07-17 最后一条） | Stage 1，**已就绪可直接开工**，插入点已定位（详见 Stage 0 gesture 审计） |
| GestureRouter / 地球拖拽 | 完全未实现。`#earth3d-layer`硬编码`pointer-events:none`（`pwa/index.html:88`），仅`pages-container`有纵向翻页的touchstart/touchend（4885-4897行） | Stage 2/3，冲突矩阵已产出 |
| RDL 动态 LOD | 数据管线成熟（GEBCO/GSHHG，Japan benchmark已跑通，见 `docs/preview_archives/rdl_*`），但**未接入** `earth3d.js` 实时渲染。注意：`EARTH_MODES`里的`tiles_noon_air_v2_islands`是"全局基础贴图"改进，**不是**"按缩放级别动态加载区域瓦片"的RDL——这是两件不同的事，容易混淆 | P4 冻结项，仅当 Low Orbit/City Focus 近景模糊成为真实痛点时才启动 |
| Agent Mesh / CI 自动化 | 完全未实现，无 `.github/workflows`。"Codex"目前是人工交接的独立LLM会话（见`docs/dev/codex_handoff_protocol.md`），不是自动PR/自动合并循环 | Ultimate Build Plan §25.2，长期项，不阻塞当前任务 |

### 1.3 顺带发现的文档腐坏（需要清理）

- `AGENTS.md` 仍写着 Qwen/DashScope，但实际代码（`core/claude.js`、`server.js` `/api/explain`）已全面迁移到 DeepSeek。
- `CLAUDE.md` "已知问题"表中的星星clipping问题大概率已过期（见上）。
- `CLAUDE.md` "main 分支，唯一分支"曾经不准确（已通过分支清理修正，见下）。

---

## 2. 分支状态（2026-07-17 清理后）

清理前有 7 个杂散分支，审计后处理：

| 分支 | 处理 | 理由 |
|---|---|---|
| `codex/deploy-noon-air-v2-islands-tiles` | 已删除（本地+远程） | 0 ahead，已完全合并进 main |
| `exp/fix-jpeg-decode-race` | 已删除（本地+远程） | 0 ahead，已完全合并进 main |
| `fix/tts-fish-audio` | 已删除（本地+远程） | main 已 revert 回 MiniMax，该方案已被放弃 |
| `wip/easter-themes` | **保留** | 有意保留的彩蛋素材分支，映射到 Ultimate Build Plan §20（彩蛋与隐藏玩法），未来可能被拣入 |
| `exp/b6-2x-source-cache-setup` | 保留归档 | 28 commits，1个月前停滞，未来可能有参考价值，暂不删 |
| `exp/cherrypick-d6-fixes` | 保留归档 | 内容需要进一步核实，暂不删 |
| `exp/dev-management-rules-split` | 保留归档 | 文档重构实验，1个月前停滞，暂不删 |

**去向策略（已确认）：主干直入。** 后续 P4 任务全部小步直接提交到 `main`，不再开长期功能分支；通过 GitHub Issue + Milestone 追踪任务边界，而不是靠分支隔离。每个 Stage 仍遵守"审计→候选→接入不默认→验收→production"的执行纪律，只是所有 commit 落点都是 main。

---

## 3. 用户额外诉求 → 建设域映射

用户提出的诉求不在 Evan 的 P4/Ultimate 文档中被显式拆解为任务，这里补齐映射，避免遗漏：

| 用户诉求 | 对应建设域 | 当前状态 | 备注 |
|---|---|---|---|
| AI 语言风格（选歌风格） | 建设域 K 选曲智能 (§15) | 选曲上下文已有，但"审美模型"§15.3、"情绪调节模型"§15.4 未系统化 | 需要单独定义一份"风格圣经"文档，而不是散落在prompt里 |
| 天外来信的设置 | 建设域 L (§16) | **系统已完整实现**，需要的是调声音/调语气，不是建架构 | 优先级应提到较高，因为这是"调参"不是"建系统"，投入产出比高 |
| 地球旋转风格 | 建设域 E + P4 Stage 7 (Motion Profiles) | 已有7种运动原语，但未产品化为正式可选 profile | 见 P4 Stage 7 |
| 地球清晰度/更多细节 | 建设域 F (Earth Visual Foundation) + H (RDL) | RDL 数据管线已成熟但未接入；基础贴图持续在迭代（noon_air_v2等） | RDL 集成是这项诉求的关键路径，但 P4 主线暂时冻结它 |
| 画面流畅度 | 建设域 S 资源与性能治理 (§23) | 未系统化性能分级，仅有基础DPR/mobile-lite检测 | 需要单独的性能审计任务 |
| 镜头切换渲染延迟 | P4-A 控制仲裁 / 建设域 S | Stage 0 已确认"多系统同帧写入、后写者生效"的隐式仲裁模式——渲染延迟很可能是这个模式的副作用（比如transition被意外打断重启，见"§B2 中断行为是破坏性的"） | 建议在 Stage 3（引入交互状态机）时一并观察是否解决，如果没解决需要单独立项 |
| 地球的成品化 | 跨 Workstream 2 全域 | 持续性抛光债务，不是单一任务 | 建议作为独立的"Polish Backlog" milestone，与功能性 Stage 并行 |

---

## 4. 当前优先级队列

按 Ultimate Build Plan 的依赖拓扑（§26.2）与本次审计结果排序：

### P0 — 立即可开工（设计已就绪，无阻塞）
1. **P4 Stage 1：三态UI（Full/Minimal）** — 插入点已定位，复用`dj-speaking`模式，上次会话已有草案
2. **P4 Stage 2：GestureRouter** — 冲突矩阵已产出
3. **P4 Stage 3：最小地球拖拽** — Director安全性已验证，插入点已定位

### P1 — 需要独立设计但无技术阻塞
4. 星空已知问题复核关闭（CLAUDE.md 更新 + 用户最终肉眼验收）
5. P4 Stage 5：星空修复（如果复核后仍有残留问题）
6. P4 Stage 6：白天背景第一轮
7. P4 Stage 7：运动方向产品化（Motion Profiles 正式化）
8. 天外来信风格调优（对应用户诉求，非架构工作）

### P2 — 需要更多前置调研
9. 选曲审美模型系统化（§15.3-15.4）
10. 画面流畅度/渲染延迟专项审计
11. RDL 集成到 earth3d.js（前提：近景模糊成为真实痛点）

### P3 — 长期/冻结
12. Agent Mesh / CI 自动化
13. Astronomy Bridge 剩余字段（日食/流星雨/极光/潮汐）
14. Journey/Surprise、彩蛋与节日系统

---

## 5. GitHub 追踪

- Projects (v2) 看板：https://github.com/users/Heyyeqi/projects/1 （Backlog / In Progress / Review / Done，全部10个issue已入板，状态Backlog）
- Milestones + Issues 映射：

| Issue | 标题 | Milestone | Label | 看板状态 |
|---|---|---|---|---|
| [#9](https://github.com/Heyyeqi/RodiO/issues/9) | P4 Stage 1: 三态UI — Full/Minimal 切换 | P4 Stage 1 — Three-State UI | P0 | Backlog |
| [#10](https://github.com/Heyyeqi/RodiO/issues/10) | P4 Stage 2: GestureRouter — 统一手势仲裁 | P4 Stage 2 — GestureRouter | P0 | Backlog |
| [#11](https://github.com/Heyyeqi/RodiO/issues/11) | P4 Stage 3: 最小地球拖拽交互 | P4 Stage 3 — Earth Drag Interaction | P0 | Backlog |
| [#12](https://github.com/Heyyeqi/RodiO/issues/12) | P4 Stage 4: Earth Only 候选态 | P4 Stage 4 — Earth Only Candidate | P1 | Backlog |
| [#13](https://github.com/Heyyeqi/RodiO/issues/13) | 星空已知问题复核关闭 + CLAUDE.md更新 | P4 Stage 5 — Star System Verification and Polish | P0 | Backlog |
| [#14](https://github.com/Heyyeqi/RodiO/issues/14) | P4 Stage 6: 白天背景第一轮 | P4 Stage 6 — Day Sky Pass | P1 | Backlog |
| [#15](https://github.com/Heyyeqi/RodiO/issues/15) | P4 Stage 7: 运动方向产品化 (Motion Profiles) | P4 Stage 7 — Motion Profiles Productization | P1 | Backlog |
| [#16](https://github.com/Heyyeqi/RodiO/issues/16) | 天外来信 + 选曲风格调优（非架构工作） | AI Voice and Selection Style Tuning | P1 | Backlog |
| [#17](https://github.com/Heyyeqi/RodiO/issues/17) | 画面流畅度 + 镜头切换渲染延迟专项审计 | Performance and Rendering Polish | P2 | Backlog |
| [#18](https://github.com/Heyyeqi/RodiO/issues/18) | 长期backlog: RDL集成 / Astronomy剩余字段 / Agent Mesh / 彩蛋 | Long-Term Backlog | P3 | Backlog |

- 每次开始一个任务，先把对应 issue 在看板上拖到 In Progress；完成验收后拖到 Done，并在本文件和 devlog.md 都留下记录。
