# RodiO Roadmap — Current Status

> 本文件是 RodiO 建设任务的唯一现状真相来源（source of truth）。
> 每次任务完成、每次 Stage 审计更新，都必须回来更新本文件，而不是只写 devlog.md。
> devlog.md 记录"做了什么"；本文件记录"现在处于什么状态、接下来该做什么"。
> 无论在哪个分支、隔了多久回来，先读这份文件，再读 devlog.md 最近几条。

最后更新：2026-07-17（第二轮补充审计：选歌模块v2 / 祈求系统 / Earth收口 / RDL细节 / 彩蛋清单）

---

## 0. 文档层级

| 文件 | 定位 | 更新频率 |
|---|---|---|
| `00_Ultimate_Build_Plan_v1.0.md` | 最终产品愿景，全部建设域（A-U），永久性北极星，几乎不改 | 极低 |
| `01_P4_Touch_the_Earth_v1.0.md` | 当前阶段（P4）的具体执行计划：Stage 0-7 | 阶段完成时更新 |
| `02_Living_Earth_Plan_v1.0.md` | P4 的技术细节参考（运动参数、星空分层数值等），部分已被 P4 取代 | 很低，仅作参考 |
| `03_RDL_Proposal_v1.0.md` | Regional Detail Layer 完整技术方案（三层LOD、BMNG+GEBCO+GSHHG+Mapbox、执行红线） | 很低 |
| `04_AI_Companion_Essay.pdf` | 产品哲学源起："音乐是AI进入生活的入口"，含产品护栏清单 | 极低 |
| `05_Product_Vision_v4.md` | 最完整的产品愿景原文（九段时光、天体层、彩蛋系统~50条、天外来信、祈求系统全文） | 很低，仅作参考 |
| `06_Song_Selection_Module_v2.md` | 选歌模块v2完整工程方案（Mood Intent JSON、track_profile schema、transition_cost、skip反馈） | 阶段完成时更新 |
| `07_Song_Selection_Multi_AI_Assessment.md` | 九份AI对选歌模块的评估意见整合底稿，v2方案的决策依据 | 很低，仅作参考 |
| `08_Dynamic_Earth_Camera_System_Design.md` | 动态地球镜头系统v2.0/v3.0完整设计方案（10构图×14运动原语×6缓动×24日常模式×8特殊模式），当前相机语法系统的原始设计蓝图 | 很低，仅作参考 |
| `source_appendix/` | 历史规划文档（v3.1 Master Pack 8份 + 开发路线v3），已被上述文件取代或归类为历史参考，不直接决定当前执行顺序 | 不更新 |
| `STATUS.md`（本文件） | 实时现状、差距矩阵、优先级、GitHub Issue 映射 | **每次任务完成后更新** |

> 注：`03_Sky_Visual_System_Implementation_v3.1.md`（Master Pack 原08份文件之一）截至本次更新未被提供给 Claude Code 直接审阅，仅有 Ultimate Build Plan 对其的二手综述。涉及 Sky LUT/11时段锚点具体参数时，应要求用户补充该文件原文，不要假设已完整掌握。

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

## 3.5 第二轮补充审计（2026-07-17，用户提供8份额外文档后）

用户提供了此前未被 Ultimate Build Plan 直接读取的原始文档（RDL完整方案、AI陪伴哲学原文、产品方案v4原文、选歌模块v2工程方案、选歌模块多AI评估底稿、v3.1 Master Pack 8份原文件）。逐份核实后发现两处此前 GitHub 追踪完全遗漏的实质性缺口：

### 选歌模块 v2 — 最重要的发现

`RodiO_选歌模块_实施方案_v2.md` 不在 Ultimate Build Plan 整合的18份来源文件之列，此前**完全没有对应的GitHub追踪**。代码审计（Explore agent 全量核查 `core/mood-intent.js`/`core/candidate-rerank.js`/`core/transition-cost.js`/`core/shadow-recall.js`/`core/state.js`）确认：

- **Phase 1 五项清单全部完成**：track_profile schema（约30字段）、11,109首全库打标（batch1-4）、播放事件日志（`play_events`表）、transition_cost观测模式、路径B shadow mode
- **完全处于Shadow Mode**：`server.js` `setRefillHandler`（约1202-1237行）里，Mood Intent/候选打分/shadow recall全部fire-and-forget只写日志表，`resolveDjSelection()`真实选曲路径**完全未被触碰**，仍是旧 Qwen/DeepSeek 直接路径
- **缺失**：skip_penalty分层半衰期（spec要求track/artist/tag/scene四层，现状只有单一180天衰减）；discovery_candidates三表晋升管线（零实现，全代码库grep零匹配）
- 已建 issue [#19](https://github.com/Heyyeqi/RodiO/issues/19)（Phase1确认+Phase2 graduation监控）、[#20](https://github.com/Heyyeqi/RodiO/issues/20)（缺失模块）

### 祈求/"此刻"系统 — 确认零实现

`grep -n "此刻\|祈求\|prayer\|moment-input\|whisper" pwa/index.html` 零匹配。此前 issue #16（天外来信+选曲风格调优）容易让人误以为祈求系统已存在只需调优，实际上*输入入口*完全不存在，天外来信生成（`/api/explain`）和祈求提交是两回事。已建 issue [#21](https://github.com/Heyyeqi/RodiO/issues/21)。

### 其余归档项

- Earth Visual Foundation 从未做过正式收口验收（Ultimate Build Plan §27清单Day/Night/Ocean/Cloud/Atmosphere长期挂空）→ issue [#22](https://github.com/Heyyeqi/RodiO/issues/22)
- RDL 完整三阶段技术方案（此前只有模糊backlog条目）→ issue [#23](https://github.com/Heyyeqi/RodiO/issues/23)
- 产品方案v4第十四节约50条彩蛋清单存档 + §20.3收缩规则预审查 → issue [#24](https://github.com/Heyyeqi/RodiO/issues/24)

### 产品护栏（来自AI陪伴哲学原文，非任务，写入原则）

> RodiO 的克制必须写进产品规则，不能只靠个人审美自觉：不做信息流；不做社区广场；不做直播和K歌入口；不做无限刷新推荐；每日推荐数量有限；AI主动触发次数有限；推荐理由字数有限；用户可以一键关闭主动陪伴；所有主动推荐必须可解释。

已同步写入 `CLAUDE.md` 设计原则章节。

---

## 3.6 第三轮补充审计（2026-07-17，动态镜头系统设计文档 + 14项用户诉求）

用户提供《RodiO 动态地球镜头系统 v2.0/v3.0》设计文档（已存档 `08_Dynamic_Earth_Camera_System_Design.md`——这正是当前相机语法系统的原始设计蓝图）和14项额外诉求。

### 关键发现：镜头"角度太少"是编排层缺口，不是素材缺口

对照设计文档的四层体系逐项核实：

| 层级 | 设计目标 | 实际完成度 |
|---|---|---|
| 构图 (C01-C10) | 10种 | **10/10 全部存在** |
| 运动原语 (M01-M14) | 14种 | 8/14 + 3种以Sequence实现，基本完成 |
| 缓动曲线 (E01-E06) | 6种 | 3/6存在 |
| **日常模式 (D01-D24)** | **24种命名模式** | **仅3个硬编码能量分档，无命名、无轮换去重——真正的缺口** |
| 特殊模式 (S01-S08) | 8种 | 0种 |

结论：底层素材（构图/运动原语）基本齐备，缺的是把它们组合成"有名字、会轮换、不重复"的模式库和智能编排层。issue [#29](https://github.com/Heyyeqi/RodiO/issues/29)。

### 两个确认的真实bug（非roadmap项，已提级为P0）

- **Dislike评分与选曲脱节**：`song_feedback.score`正确记录，但候选排序从未查询它——用户越点不喜欢，系统品味模型完全不跟着调整。issue [#25](https://github.com/Heyyeqi/RodiO/issues/25)
- **MiniMax TTS静默失败无降级**：服务端吞错误，前端播放null音频静默失败，用户完全不知道发生了什么，也没有退回纯文字展示。issue [#26](https://github.com/Heyyeqi/RodiO/issues/26)

### 其余处理

- 入场动画状态残留 + 切歌歌名闪回竞态 → issue [#27](https://github.com/Heyyeqi/RodiO/issues/27)
- IP地域首曲本地化（闽南语/粤语/日语） → issue [#28](https://github.com/Heyyeqi/RodiO/issues/28)，基础设施（地理位置检测）已存在，只是没接到选曲
- 天气视觉映射系统（雨/雪/风） → issue [#30](https://github.com/Heyyeqi/RodiO/issues/30)，对应 Ultimate Build Plan §13.4，此前完全未追踪，数据层已就绪但视觉层全部空白
- 天体可视化扩展（流星/星座连线/月球渲染） → issue [#31](https://github.com/Heyyeqi/RodiO/issues/31)
- 真实驱动地形事件（火山喷发，需数据源可行性评估） → issue [#32](https://github.com/Heyyeqi/RodiO/issues/32)
- 天外来信中英配比、彩蛋清单（地球罩子/爆炸/烟花/太空垃圾）、Earth Visual Foundation验收范围补充 → 追加到已有issue [#16](https://github.com/Heyyeqi/RodiO/issues/16)/[#22](https://github.com/Heyyeqi/RodiO/issues/22)/[#24](https://github.com/Heyyeqi/RodiO/issues/24) 的评论里，未开新issue
- "say"朗读前缀问题 → 代码审计未能复现，需要用户提供具体场景才能继续排查
- 播放器控制栏重做（用户标"优先做"） → 就是已有的 issue [#9](https://github.com/Heyyeqi/RodiO/issues/9)（三态UI Full/Minimal），无需新issue，可直接开工
- 太空垃圾/卫星 → 已被 `02_Living_Earth_Plan_v1.0.md` P4-G"卫星掠过"覆盖，非新范围

---

## 4. 当前优先级队列

按 Ultimate Build Plan 的依赖拓扑（§26.2）与本次审计结果排序：

### P0 — 立即可开工（设计已就绪，无阻塞）
1. **P4 Stage 1：三态UI（Full/Minimal）** — 插入点已定位，复用`dj-speaking`模式，上次会话已有草案；用户已明确标注"优先做"（对应播放器控制栏重设计诉求）
2. **P4 Stage 2：GestureRouter** — 冲突矩阵已产出
3. **P4 Stage 3：最小地球拖拽** — Director安全性已验证，插入点已定位
4. **Dislike评分与选曲脱节**（issue #25）— 确认的架构性断裂，反馈闭环完全没生效
5. **MiniMax TTS静默失败无降级**（issue #26）— 确认的真实bug，用户明确反馈"没有语音朗读"

### P1 — 需要独立设计但无技术阻塞
4. 星空已知问题复核关闭（CLAUDE.md 更新 + 用户最终肉眼验收）
5. P4 Stage 5：星空修复（如果复核后仍有残留问题）
6. P4 Stage 6：白天背景第一轮
7. P4 Stage 7：运动方向产品化（Motion Profiles 正式化）
8. 天外来信风格调优（对应用户诉求，非架构工作）
9. 选歌模块v2 Phase1完成确认 + Phase2 graduation监控（issue #19）——检查shadow日志是否已达标，可能已默默满足毕业条件
10. 此刻入口 + 祈求系统实现（issue #21）——确认零实现的真实产品缺口

### P2 — 需要更多前置调研
11. 选曲审美模型系统化（§15.3-15.4）
12. 画面流畅度/渲染延迟专项审计
13. RDL 集成到 earth3d.js（前提：近景模糊成为真实痛点）
14. 选歌模块v2缺口：skip_penalty分层衰减 + discovery_candidates pipeline（issue #20）
15. Earth Visual Foundation 正式收口验收（issue #22）

### P3 — 长期/冻结
16. Agent Mesh / CI 自动化
17. Astronomy Bridge 剩余字段（日食/流星雨/极光/潮汐）
18. Journey/Surprise、彩蛋与节日系统（issue #24，含完整~50条清单存档）
19. RDL 完整三阶段技术方案存档（issue #23）

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
| [#19](https://github.com/Heyyeqi/RodiO/issues/19) | 选歌模块v2 Phase1完成确认 + Phase2 graduation监控标准 | Song Selection v2 — Phase 2 Graduation | P1 | Backlog |
| [#20](https://github.com/Heyyeqi/RodiO/issues/20) | 选歌模块v2缺口: skip_penalty分层衰减 + discovery_candidates pipeline | Song Selection v2 — Phase 2 Graduation | P2 | Backlog |
| [#21](https://github.com/Heyyeqi/RodiO/issues/21) | 此刻入口 + 祈求系统实现 | Companion and Prayer System | P1 | Backlog |
| [#22](https://github.com/Heyyeqi/RodiO/issues/22) | Earth Visual Foundation 正式收口验收 | Earth Visual Foundation Formal Closure | P2 | Backlog |
| [#23](https://github.com/Heyyeqi/RodiO/issues/23) | RDL 技术方案存档：BMNG+GEBCO+GSHHG 三层LOD具体路线 | Long-Term Backlog | P3 | Backlog |
| [#24](https://github.com/Heyyeqi/RodiO/issues/24) | 彩蛋系统清单存档 + §20.3收缩规则应用 | Long-Term Backlog | P3 | Backlog |
| [#25](https://github.com/Heyyeqi/RodiO/issues/25) | Dislike评分未接入候选排序 — 反馈闭环架构性断裂 | Playback Reliability and Core Bug Fixes | P0 | Backlog |
| [#26](https://github.com/Heyyeqi/RodiO/issues/26) | MiniMax TTS 静默失败 + 无降级机制 | Playback Reliability and Core Bug Fixes | P0 | Backlog |
| [#27](https://github.com/Heyyeqi/RodiO/issues/27) | 入场动画状态残留 + 切歌歌名闪回（竞态） | Playback Reliability and Core Bug Fixes | P1 | Backlog |
| [#28](https://github.com/Heyyeqi/RodiO/issues/28) | IP地域首曲本地化 | Long-Term Backlog | P2 | Backlog |
| [#29](https://github.com/Heyyeqi/RodiO/issues/29) | 镜头模式库 (Daily Modes) + 智能编排/去重引擎 | P4 Stage 7 — Motion Profiles Productization | P1 | Backlog |
| [#30](https://github.com/Heyyeqi/RodiO/issues/30) | 天气视觉映射系统（雨/雪/风） | Long-Term Backlog | P3 | Backlog |
| [#31](https://github.com/Heyyeqi/RodiO/issues/31) | 天体可视化扩展：流星+星座+月球渲染 | P4 Stage 5 — Star System Verification and Polish | P2 | Backlog |
| [#32](https://github.com/Heyyeqi/RodiO/issues/32) | 真实驱动地形事件：火山喷发等 | Long-Term Backlog | P3 | Backlog |

- 每次开始一个任务，先把对应 issue 在看板上拖到 In Progress；完成验收后拖到 Done，并在本文件和 devlog.md 都留下记录。
