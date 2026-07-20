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
| `09_Horizon_Mode_Aesthetic_Brief_v1.0.md` | Horizon Mode（#36）美学基调："从上帝视角切换到真实的看见"、海水地理差异（清澈/浑浊/深邃）、云作为山地场景必要点缀、克制不等于抽象化。Phase 2/3/5/8施工时应直接参考 | 低，除非美学方向调整 |
| `source_appendix/` | 历史规划文档（v3.1 Master Pack 8份 + 开发路线v3 + Sky Design v3.2 + Integrated Roadmap v1.7），大部分已被上述文件取代或归类为历史参考；**例外：`C_Sky_Design_v3.2.md` 含未被吸收的精确11时段色彩锚点表和物理散射原理，issue #14施工时应直接参考**，不是纯历史文档 | 不更新 |
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

结论：底层素材（构图/运动原语）基本齐备，缺的是把它们组合成"有名字、会轮换、不重复"的模式库和智能编排层。issue [#28](https://github.com/Heyyeqi/RodiO/issues/28)。

### 两个确认的真实bug（非roadmap项，已提级为P0）

- **Dislike评分与选曲脱节**：`song_feedback.score`正确记录，但候选排序从未查询它——用户越点不喜欢，系统品味模型完全不跟着调整。issue [#25](https://github.com/Heyyeqi/RodiO/issues/25)
- **MiniMax TTS静默失败无降级**：服务端吞错误，前端播放null音频静默失败，用户完全不知道发生了什么，也没有退回纯文字展示。issue [#26](https://github.com/Heyyeqi/RodiO/issues/26)

### 其余处理

- 入场动画状态残留 + 切歌歌名闪回竞态 → issue [#27](https://github.com/Heyyeqi/RodiO/issues/27)
- IP地域首曲本地化（闽南语/粤语/日语） → issue [#29](https://github.com/Heyyeqi/RodiO/issues/29)，基础设施（地理位置检测）已存在，只是没接到选曲
- 天气视觉映射系统（雨/雪/风） → issue [#30](https://github.com/Heyyeqi/RodiO/issues/30)，对应 Ultimate Build Plan §13.4，此前完全未追踪，数据层已就绪但视觉层全部空白
- 天体可视化扩展（流星/星座连线/月球渲染） → issue [#31](https://github.com/Heyyeqi/RodiO/issues/31)
- 真实驱动地形事件（火山喷发，需数据源可行性评估） → issue [#32](https://github.com/Heyyeqi/RodiO/issues/32)
- 天外来信中英配比、彩蛋清单（地球罩子/爆炸/烟花/太空垃圾）、Earth Visual Foundation验收范围补充 → 追加到已有issue [#16](https://github.com/Heyyeqi/RodiO/issues/16)/[#22](https://github.com/Heyyeqi/RodiO/issues/22)/[#24](https://github.com/Heyyeqi/RodiO/issues/24) 的评论里，未开新issue
- "say"朗读前缀问题 → 代码审计未能复现，需要用户提供具体场景才能继续排查
- 播放器控制栏重做（用户标"优先做"） → 就是已有的 issue [#9](https://github.com/Heyyeqi/RodiO/issues/9)（三态UI Full/Minimal），无需新issue，可直接开工
- 太空垃圾/卫星 → 已被 `02_Living_Earth_Plan_v1.0.md` P4-G"卫星掠过"覆盖，非新范围

---

## 3.7 第四轮补充审计（2026-07-17，Evan大气方案 + Sky v3.2 spec 溯源）

用户提供 Evan 的"白天大气氛围"新方案（五个技术方向：大气散射渐变/极淡高空卷云/太阳方向场/极淡空气颗粒/背景与地球统一空间）和 Living Earth Phase 4 提案（Atmosphere→Motion→Exploration三层升级、Living Earth Engine统一状态机、"Earth OS"产品重新定位），以及五份更早期的原始文档（A/B/C/D/E）。

### 五份早期文档的处理

- **A（Bathy-3/D5b专项）、E（产品方案v3）**：已经是 `02_Earth_Visual_Foundation_Implementation_v3.1.md` 和 `06_Weather_Celestial_Context_Future_v3.1.md` 内嵌的附录原文，round 1时已完整读取吸收，无新增内容
- **B（3D地球视觉系统v2.0）**：是 v3.1 Master Pack（00/02/06等编号文档）拆分前的合并版前身，结构和内容已被拆分后的文档完整覆盖，无新增内容
- **C（Sky Design v3.2）、D（Integrated Roadmap v1.7）**：**此前完全没读过的真正缺口**——round 1时被跳过（用户没有附带03号Sky文档，也没附带这两份），现已读取并存档

### 关键发现：C/D 揭示了"白天感觉扁平"的精确技术根因

代码审计确认：天空系统实现时**放弃了spec的双LUT/OKLab技术路线**，改用更简单的3-4色彩锚点方案（spec原设计是8-12锚点，基于瑞利散射/米氏散射物理模型分层）。这个简化本身就是"背景是二维的"这个感受的技术根源——不是主观审美判断，是过渡点位密度确实只有原设计的三分之一到一半。

Evan独立提出的"大气散射渐变"方案和 v3.2 spec 的诉求本质相同，已追加详细审计到 issue [#14](https://github.com/Heyyeqi/RodiO/issues/14)。

### 需要用户决策的一处张力

Evan 主张"大气散射渐变+太阳方向场+高空卷云+空气颗粒"应作为一个整体系统一起做（因为都是"大气"的组成部分）；但 P4 doc 的执行纪律明确要求"同一轮不要混合视觉层"，且 Living Earth Plan 把高空卷云/空气体积列为"第二轮候选"，不在第一轮范围。这个范围决策已在 issue #14 中列出，需要用户在实际开工前拍板。

### 其余发现（均验证为已有规划的重申，非新缺口）
- Evan"镜头库/旋转风格/季节镜头"提案 → 已是issue [#28](https://github.com/Heyyeqi/RodiO/issues/28)覆盖范围，增加"季节性镜头高度变化"作为细节补充
- Evan"Discovery Mode/Surprise Camera"提案 → 已是 `02_Living_Earth_Plan_v1.0.md` P4-F 的"Auto Journey"/"Surprise View"，已规划且有意延后（P3优先级）
- Evan"音乐镜头映射"提案（钢琴远景/电子环绕/爵士城市夜景等）→ 与 P4-F §3"音乐镜头映射"表几乎完全相同，非新内容
- Evan"Living Earth Engine统一状态机"提案 → 与 Living Earth Plan P4-A"Earth Director控制系统收口"、Ultimate Build Plan §9.1"先最小仲裁、真实冲突出现后再升级完整Director"是同一个长期目标，当前刻意延后（Stage 0审计已确认现有隐式仲裁安全，无需提前重构）
- "Earth OS"产品重新定位 → 与"宇宙电台"哲学（Ultimate Build Plan §0/§2）一致，是同一愿景的更强表达，非路线变更

---

## 3.9 第六轮补充：Living Earth 垂直空间愿景（2026-07-18）

用户提供三份方案（云层创意/深海模式/地平线视角），已存档 `docs/roadmap/source_appendix/{Cloud_System_Vision,Underwater_Mode_Vision,Horizon_Mode_Vision}.md`。

**关键发现：三份方案独立收敛到同一个构想**——`ORBIT（太空）→ CLOUD（云层）→ HORIZON（地表）→ UNDERWATER（海洋）→ ABYSS/MINIMAL` 的垂直空间旅程，不是三个孤立功能点。

**与已有系统的具体连接**（避免重复建设）：
- 地平线方案描述的"近景贴图糊/z-fighting/辉光变厚重光带"不是理论推测——是本次会话里刚修过的问题（`cityFocus`/`lowOrbit`/`horizon`/`horizonSkim`清晰度修复）。现有构图库已有`horizon`/`horizonSkim`/`lowOrbit`，方案要做的是深化到真正贴地平视，不是从零新建
- 山地平线需要的高程数据（DEM）和 RDL 方案（issue #23）的 GEBCO 数据管线是同一个数据源，RDL 解冻时可顺带解决
- 云层方案的"高空云/Air Volume"和 issue #14（白天背景）的"第二轮候选"是同一建设域，但规模远超#14当前范围
- 深海模式和现有系统耦合最少（明确不能直接复用现有海洋球层，需要独立场景），风险相对独立

**处理方式**：新建 milestone "Living Earth — Vertical Space Journey"（#15），三个issue（[#35](https://github.com/Heyyeqi/RodiO/issues/35) 云层、[#36](https://github.com/Heyyeqi/RodiO/issues/36) 地平线、[#37](https://github.com/Heyyeqi/RodiO/issues/37) 深海），P3，放进优先级队列最后一档。P4主线"大规模新镜头库"/"高空云与Air Volume同时施工"明确冻结这类范围，当前不启动，仅保留愿景完整性。

## 3.10 第七轮补充：连续日夜过渡系统 + 航线视角（2026-07-18）

用户提供两份方案，已存档 `docs/roadmap/source_appendix/{Continuous_Day_Cycle_Vision,Flight_View_Vision}.md`。

**方案一：连续日夜过渡系统**——现有11个时段是"到点整体切换"的互斥主题，连续观看会有天空/海洋/城市灯光/星空的跳变。方案原文判断"这个必须做，而且它的重要性其实高于继续增加新的主题"。核心是把11个时段从"11个互斥模式"改造为"11个视觉锚点"，建一个统一 `DayCycleController`，用太阳高度角驱动、9条独立轨道分别插值（不是统一progress）、颜色改OKLCH空间、加入非对称过渡和残留/滞后效应。

**与已有系统的具体关系**：
- 与 #14（P4 Stage 6 白天背景，锚点密度3-4个 vs spec的8-12个）互补不重复——#14解决锚点够不够，这个方案解决锚点之间怎么过渡（离散跳变→连续插值），两者是正交问题
- 规模是架构级的，跨越天空/海洋/云/大气/星空/城市灯光多个现有渲染系统，明显大于单个视觉任务
- 方案自己也提出应作为 Orbit/Cloud/Flight/Horizon/Underwater 共享的底层环境状态源，与3.9的垂直空间旅程系统直接relevant

**处理方式**：新建 milestone "Continuous Day Cycle System"（#16），[#39](https://github.com/Heyyeqi/RodiO/issues/39)。**2026-07-18 用户已拍板：优先级"中前段"**，排进第三梯队最前面（P4主线之后、其余视觉任务之前），且提前到 #14 之前——避免 #14 的锚点密度工作日后为适配新的连续插值架构而返工。

**方案二：航线视角 Flight View**——3.9 三个空间模式（Cloud/Horizon/Underwater）之间新增的连接层，摄影机沿大圆航线巡航飞行，四种子镜头（巡航/舷窗/穿云下降/高空夜航）。方案原文判断"值得增加，且优先级可以高于纯山地Horizon"，理由是最大程度复用现有地球/天空/云/昼夜/城市灯光系统，不需要高精度近地形。"穿云下降"子模式天然是 Flight→Horizon 的过渡桥梁。

**处理方式**：加入既有 milestone "Living Earth — Vertical Space Journey"（重命名为包含Flight），[#40](https://github.com/Heyyeqi/RodiO/issues/40)，P3，与#35/#36/#37同批延后，不改变3.9已定的"当前不启动"结论。

---

## 4. 当前优先级队列（2026-07-17 第五轮重排）

不再按 P0-P3 桶装，改成单条可执行序列，越靠前越先做。排序依据：①正在发生的真实故障优先于新功能；②近乎零成本的存量清账任务插空处理；③P4主线交互闭环按依赖顺序走完；④"材料已具备、只差编排"的高杠杆视觉任务提前；⑤纯粹待定/需要更多前置研究/用户已明确说"中后期"的任务放最后。GitHub 看板 Backlog 列的卡片顺序已同步调整为这个序列。

### 第一梯队：本周就做（真实故障 + 近零成本清账）

> **2026-07-18 更新**：#34/#26/#27/#20 代码均已提交并经 Claude Code 独立核对（非仅信任报告），#25 更早前已提交。五个issue看板状态已同步改为 **Review**（不是Done——都还没部署Railway、没有实机/真实数据验证）。commit：#26=`27c9b01`，#27=`7143114`，#34=`b31a024`，#20=`fdd1753`，#25=`4515ef6`（更早）。
>
> **2026-07-18 夜间更新（本地实时+生产验证）**：启动本地服务实测 #26/#27/#34/#20，全部确认通过并已推送部署到 Railway production（deployment `93291dbd`，SUCCESS）。四个issue已移到看板 **Done**。
> - 验证过程中发现 #26 的原修复只覆盖了 `resolveDjSelection()`，`/api/explain`（Explain按钮+预取）的TTS调用完全没被保护，欠费时直接500丢文案——已修复（commit `1c39eb1`），现已部署验证通过。
> - #20 的 skip_penalty 分层衰减验证通过；discovery→validated 晋升管线发现结构性缺口（scene_id 全线硬编码 null，晋升条件永远不可达），已拆出新 issue [#38](https://github.com/Heyyeqi/RodiO/issues/38)，不阻塞 #20 本身标 Done。
> - #25 代码审查确认正确，已部署，但 production 的 shadow-rerank 只在补货周期（reason=next/heartbeat）触发、不含 startup-prewarm，且本次部署后队列一直饱满未触发自然补货，**仍未拿到生产环境正数据实锤**，留在 Review。顺带给 `logShadowRerank` 加了成功路径日志（commit `fd60374`）方便下次直接查 railway logs 而不必戳数据库。

0. **[#25](https://github.com/Heyyeqi/RodiO/issues/25) Dislike评分未接入候选排序** — ✅已提交（`4515ef6`）并端到端验证通过，已标Done（本地补齐策划歌单env var后，用真实队列57首候选直接调用`logShadowRerank`，`shadow_rerank_candidates`正确写入30行，`track_key`不再是修复前的空拼接）
1. **[#13](https://github.com/Heyyeqi/RodiO/issues/13) 星空已知问题复核关闭** — 95%把握已过期，只差用户肉眼看一眼确认，几分钟的事，拖了多轮审计，**仍未完成**
2. **[#19](https://github.com/Heyyeqi/RodiO/issues/19) 选歌模块v2 Phase1确认+Phase2毕业监控** — 已查：fallback_rate 0.5%✅、candidate_empty_count 0✅达标；avg_transition_cost因shadow_rerank_candidates曾无真实数据无法计算（#25修复已部署，待验证后应能恢复）；7天连续性差1天。待#25端到端验证完成后重新计时复查
3. **[#38](https://github.com/Heyyeqi/RodiO/issues/38) discovery_candidates晋升管线缺scene_id生产者** — 2026-07-18本地验证时新发现，需要先决定scene_id的产品语义（时段/天气/mood-intent标签）才能接线，不阻塞其他任务

### 第一点五梯队：Horizon Mode 完整方案二建设（2026-07-19 用户明确要求优先，插到P4主线之后）

> P4 Stage 1-4已全部完成（#9-12），用户在此之后明确要求"先做#36"，且要求完整方案二（独立场景），不做缩水版本。已拆Phase 0-9，milestone "Horizon Mode — Independent Scene Build"，Phase 0资源审计已完成，结论见 #36 评论。

4. ~~**[#41](https://github.com/Heyyeqi/RodiO/issues/41) Phase 0.5：资源补充**~~ — **Done**（水面法线贴图/仰视云层技术路线v2/GEBCO近景细节噪声v1.1实测校准/美学基调文字/水质系统v2数据驱动管线，全部独立验证通过，见 #41 评论）
5. ~~**[#42](https://github.com/Heyyeqi/RodiO/issues/42) Phase 1：隔离试验场景骨架**~~ — **Done**（与Phase 2合并交付，`pwa/horizon-lab.js`，`?earthCandidate=horizonLab`，独立Scene+相机+渲染循环，本地端到端验证通过，见 #42 评论）
6. ~~**[#43](https://github.com/Heyyeqi/RodiO/issues/43) Phase 2：天空穹顶**~~ — **Done**（随#42一并落地：skyDome渐变+3层同心云壳，已验证真实3D视差；月光方向仍是缺口，留待场景打磨阶段）
7. ~~**[#44](https://github.com/Heyyeqi/RodiO/issues/44) Phase 3：真反射海面**~~ — **Done**（vendor官方three.js r128 Reflector/Water，水色用#41的`water_params_reference.js`实算真值而非拍脑袋，倒影真实性已用截图+反射相关性验证，见 #44 评论；海平线场景技术上已完整）
8. **[#45](https://github.com/Heyyeqi/RodiO/issues/45) Phase 4：Orbit↔Horizon进出场过渡** — 当前最前面待开工的任务
9. **[#46](https://github.com/Heyyeqi/RodiO/issues/46) Phase 5：海面美学打磨** — 海平线场景真正决定观感的部分，Phase 0-5做完海平线就是打磨过的完整场景，不是半成品
10. **[#47](https://github.com/Heyyeqi/RodiO/issues/47) Phase 6：海岸与岛屿场景**（第二优先级场景）
11. **[#48](https://github.com/Heyyeqi/RodiO/issues/48) Phase 7：地形高度图导出管线** — GEBCO数据已有，缺"原始高程转灰度PNG"这最后一步
12. **[#49](https://github.com/Heyyeqi/RodiO/issues/49) Phase 8：山地平线场景**（第三优先级场景）
13. **[#50](https://github.com/Heyyeqi/RodiO/issues/50) Phase 9：陆地平视场景**（最低优先级，方案原文自己警告容易变成游戏场景）

### 第一点六梯队：真实天体系统（2026-07-20 用户新提出，与Horizon Mode队列的排序关系待定）

> 用户指出现有3D场景里太阳/月亮压根没有可见物体（只有`DirectionalLight`+后端月相计算，无渲染），星空是真实8K星图+程序化点缀混合。要求分阶段做完整太阳系（含冥王星+代表性卫星），标准是"天文学级别真实"，不是艺术示意。milestone "Real Celestial Bodies — Astronomically Accurate Solar System"。

14. ~~**[#52](https://github.com/Heyyeqi/RodiO/issues/52) Phase 1：太阳+月亮真实轨道位置系统（自转+公转）**~~ — **Done**（太阳/月亮真实方位+距离+可见性分档 + 地球自转[逐帧数值标定，非线性外推] + 公转可视化[deepSpace轨道环+真实日心黄经位置标记]，全部独立验证通过，见issue评论）
15. **[#53](https://github.com/Heyyeqi/RodiO/issues/53) Phase 2：七曜可见化** — Step 0（真实NASA影像资源，一次性覆盖#53+#54全部剩余天体：8行星+5卫星+3环系统+太阳+月球贴图升级）已完成并独立验证通过；衍生工作"地球远景NASA真彩交叉淡入"（近景地图风不变，深空远景混合Blue Marble真彩、与行星贴图风格一致，阈值绑定#52的`MOON_VISIBLE_DIST`）也已完成并独立验证通过。**当前最前面待开工**：开普勒轨道位置计算（5颗行星）+ 渲染集成（复用#52基础设施，先金星跑通再批量接其余4颗）
16. **[#54](https://github.com/Heyyeqi/RodiO/issues/54) Phase 3：完整太阳系收尾**（天王星/海王星/冥王星+代表性卫星）

### 第一点七梯队：全球海水颜色物理准确性（2026-07-20 RW明确标记"需要重点解决"，非常规backlog）

> 现有主场景近景全球海洋着色是基于Blue Marble亮度直方图的百分位近似映射，代码自己标注"尚未对真实BMNG tile数据做实测校准"，不是真实海洋学数据驱动。跟RDL(#23，几何清晰度问题，Mapbox精度已经够用只是冻结未接入)是两个不同的问题——这个是颜色物理准确性问题，Mapbox/BMNG卫星照片再清晰也没用，需要的是Copernicus-GlobColour这类海洋色卫星数据。

17. **[#57](https://github.com/Heyyeqi/RodiO/issues/57) 全球海水颜色物理准确性** — 把#41已验证的水质科学管线（`water_params_reference.js`，Copernicus-GlobColour CHL/SPM/CDOM/KD490→IOP物理反演→颜色）从Horizon Mode几个手选站点扩展到全球覆盖，替换现有近似的百分位亮度分级。方案未细化，RW明确要求不能像#18/#23那样被动等痛点触发，需要主动推进；具体排期/跟#53的先后关系待定。

### 第二梯队：P4 交互闭环主线（有先后依赖，按序做，已全部完成）
5. **[#9](https://github.com/Heyyeqi/RodiO/issues/9) P4 Stage 1：三态UI（Full/Minimal）** — ✅已提交（`325c379`）并本地实机验证通过，已标Done。范围只做Full/Minimal，Earth Only留给#12
6. **[#10](https://github.com/Heyyeqi/RodiO/issues/10) P4 Stage 2：GestureRouter** `[Cat A]` — ✅已提交（`5f33b0f`）并本地实机验证通过，已标Done。验证时发现并修复两个真实bug：①IIFE前漏分号导致整段代码在浏览器里从未执行过（`node --check`测不出来）②pointermove过早锁定drag导致真实swipe手势永远判不出来。给#11留了提示：这轮drag只在pointerup兜底解析，#11接入真实地球旋转时大概率需要在move阶段也加实时锁定
7. **[#27](https://github.com/Heyyeqi/RodiO/issues/27) 入场动画残留+歌名闪回竞态** — ✅已提交（`7143114`）并本地实测验证通过（刷新页面确认`dj-speaking`类不再残留），已标Done
8. **[#11](https://github.com/Heyyeqi/RodiO/issues/11) P4 Stage 3：最小地球拖拽** `[Cat A]` — ✅已提交（`b26ae56`）并本地实机验证通过，已标Done。**重要教训**：Marvis首次提交声称6处改动"全部通过"，独立核对diff后发现4处根本不存在（`getTargetOrientation()`从未接入拖拽offset，核心链路写入端和读取端没打通，功能对画面完全没有视觉效果）——Claude直接补完并修了两个连带bug（`_updateGramTransition`的guard条件不能一刀切、GestureRouter里velocity判定复现了#10同一个"第一帧velocity=0"的坑）
9. **[#12](https://github.com/Heyyeqi/RodiO/issues/12) P4 Stage 4：Earth Only候选态** `[Cat A]` — ✅已提交（`a0d7596`）并本地实机验证通过，已标Done。经历两轮打回（前两次Marvis报"全部完成"但diff里6项只有1项真实存在），第三次才对上；独立验证时还发现Claude自己brief里带的一个跨script作用域bug（Theme Tuner是独立script标签，不能直接引用主脚本闭包变量）并修复。P4 Stage 1-4 全部完成，P4主线暂告一段落

### 第三梯队：高杠杆视觉任务（材料大半已具备，缺编排/收口）

> **2026-07-18 更新**：用户拍板 #39 优先级为"中前段"，排进本梯队最前面，且提前到 #14 之前——原因是 #14（锚点密度不够）和 #39（锚点间怎么过渡）虽是正交问题，但 #39 是底层机制，先做 #39 再做 #14 可以避免 #14 的成果之后又要为了适配新架构返工一次。

10. **[#39](https://github.com/Heyyeqi/RodiO/issues/39) 连续日夜过渡系统（Day Cycle Controller）** `[Cat A，但跨系统改动需走影子验证]` — 架构级改造（跨天空/海洋/云/大气/星空/城市灯光），排在#14前面，避免#14成果日后为适配新架构返工。只改参数计算方式，不改相机-几何体关系；具体做法见 CLAUDE.md「3D渲染/相机新功能」一节。**已完成，标Done**：第一步（插值函数+边界验证）`d0b8f5a`，经历两轮打回（t=0/t=1边界测试测不出来、必须测中间值才暴露的bug）。第二步（接入调度器，切断硬跳变）`b85d485`，本地实测真实uniform确认dawn→sunrise在t=0/0.5/1严格线性插值；范围明确排除天空平面/海洋色调/星星sprite/主题名专属特效（方案本身列为独立后续步骤，保持现有瞬切）。补测：20倍速加速时间端到端验证（主循环真实调度、1330次驱动、硬切换正确收尾、5项断言PASS）
11. **[#28](https://github.com/Heyyeqi/RodiO/issues/28) 镜头模式库+智能编排引擎** `[Cat A]` — 直接回应"角度太少"，10种构图/多数运动原语已存在，只差组合成命名模式库；建议和Stage3地球拖拽前后衔接做，上下文连续
12. **[#14](https://github.com/Heyyeqi/RodiO/issues/14) P4 Stage 6：白天背景第一轮** `[Cat A]` — 已定位精确技术根因（8-12锚点spec vs 实际3-4锚点），色值表现成可用；开工前需要你对"是否把Evan的大气方案几个子项打包一起做"拍板（issue里列了这个决策点）；建议在#39之后开工
13. **[#22](https://github.com/Heyyeqi/RodiO/issues/22) Earth Visual Foundation正式收口验收** — 大部分问题已经在#22评论里回答完（地形维度、城市灯光分层现状），剩下主要是走一遍截图验收流程，成本不高；验收性质，不涉及新开发，无需分级
14. **[#15](https://github.com/Heyyeqi/RodiO/issues/15) P4 Stage 7：运动方向产品化** — 与#28范围高度重叠（#28的模式库本身就会产出这7个命名Profile），建议#28做完后回来看这条是否已经被顺带满足，而不是重复做

### 第四梯队：AI/产品深度功能
15. **[#21](https://github.com/Heyyeqi/RodiO/issues/21) 此刻入口+祈求系统** — 确认的真实缺口，产品原始愿景的核心部分之一
16. **[#16](https://github.com/Heyyeqi/RodiO/issues/16) 天外来信+选曲风格调优** — 纯调参非架构，风险低，可穿插在别的任务间隙做
17. **[#20](https://github.com/Heyyeqi/RodiO/issues/20) 选歌模块v2缺口：skip_penalty分层+discovery_candidates** — ✅已提交（`fdd1753`）并本地模拟验证通过（skip事件正确生成4维度独立衰减行），已标Done。晋升管线的scene_id缺口拆到 [#38](https://github.com/Heyyeqi/RodiO/issues/38)

### 第五梯队：锦上添花（价值明确但不紧急）
18. **[#29](https://github.com/Heyyeqi/RodiO/issues/29) IP地域首曲本地化** — 基础设施已有，方言级别识别精度是唯一顾虑
19. **[#31](https://github.com/Heyyeqi/RodiO/issues/31) 天体可视化扩展：流星+星座+月球渲染**
20. **[#17](https://github.com/Heyyeqi/RodiO/issues/17) 画面流畅度/渲染延迟专项审计** — 需要先收集具体复现场景，目前信息不够开工

### 第六梯队：明确延后/冻结（不要在前面几梯队做完之前碰）
21. **[#33](https://github.com/Heyyeqi/RodiO/issues/33) 多套地球配色主题** — 用户已明确说"中后期做"
22. **[#30](https://github.com/Heyyeqi/RodiO/issues/30) 天气视觉映射系统** — P4文档明确冻结"实时天气"联动
23. **[#32](https://github.com/Heyyeqi/RodiO/issues/32) 真实驱动地形事件：火山喷发** — 数据源可行性未知，先评估不排期
24. **[#23](https://github.com/Heyyeqi/RodiO/issues/23) RDL完整三阶段技术方案** — 冻结至近景模糊成为真实用户痛点
25. **[#24](https://github.com/Heyyeqi/RodiO/issues/24) 彩蛋系统清单存档** — P3，不进当前主线
26. **[#18](https://github.com/Heyyeqi/RodiO/issues/18) 长期backlog总类** — 兜底条目，逐步被上面拆出的具体issue替代
27. **[#35](https://github.com/Heyyeqi/RodiO/issues/35) 云层系统升级** `[混合：光照/纹理增强部分Cat A，Cloud View新相机视角部分Cat B]` — 长期愿景，milestone "Living Earth — Vertical Space Journey"，开工前需重新拆分子任务确认各自分级
~~28. #36 地平线视角深化~~ — 已移到"第一点五梯队"，见上方，不再属于本梯队的"明确延后"范围
29. **[#37](https://github.com/Heyyeqi/RodiO/issues/37) 深海模式** `[Cat B，需先建独立试验场景]` — 同上milestone，三者中和现有系统耦合最少，若未来三选一优先启动，风险相对最独立；方案文档自己明确"不建议直接把摄像机塞进现有海洋球层"
30. **[#40](https://github.com/Heyyeqi/RodiO/issues/40) 航线视角 Flight View** `[Cat B，需先建独立试验场景]` — 同上milestone，2026-07-18新提出，连接Cloud与Horizon的中间层，原文认为优先级可高于纯Horizon（#36），但仍属于本梯队"当前不启动"的范围；相机沿路径持续移动+新LOD策略，改变了相机-几何体关系

---

## 5. GitHub 追踪

- Projects (v2) 看板：https://github.com/users/Heyyeqi/projects/1 （Backlog / In Progress / Review / Done，全部10个issue已入板，状态Backlog）
- Milestones + Issues 映射：

| Issue | 标题 | Milestone | Label | 看板状态 |
|---|---|---|---|---|
| [#9](https://github.com/Heyyeqi/RodiO/issues/9) | P4 Stage 1: 三态UI — Full/Minimal 切换 | P4 Stage 1 — Three-State UI | P0 | Done（325c379，本地实机验证通过） |
| [#10](https://github.com/Heyyeqi/RodiO/issues/10) | P4 Stage 2: GestureRouter — 统一手势仲裁 | P4 Stage 2 — GestureRouter | P0 | Done（5f33b0f，本地实机验证通过） |
| [#11](https://github.com/Heyyeqi/RodiO/issues/11) | P4 Stage 3: 最小地球拖拽交互 | P4 Stage 3 — Earth Drag Interaction | P0 | Done（b26ae56，本地实机验证通过） |
| [#12](https://github.com/Heyyeqi/RodiO/issues/12) | P4 Stage 4: Earth Only 候选态 | P4 Stage 4 — Earth Only Candidate | P1 | Done（a0d7596，本地实机验证通过） |
| [#13](https://github.com/Heyyeqi/RodiO/issues/13) | 星空已知问题复核关闭 + CLAUDE.md更新 | P4 Stage 5 — Star System Verification and Polish | P0 | Backlog |
| [#14](https://github.com/Heyyeqi/RodiO/issues/14) | P4 Stage 6: 白天背景第一轮 | P4 Stage 6 — Day Sky Pass | P1 | Backlog |
| [#15](https://github.com/Heyyeqi/RodiO/issues/15) | P4 Stage 7: 运动方向产品化 (Motion Profiles) | P4 Stage 7 — Motion Profiles Productization | P1 | Backlog |
| [#16](https://github.com/Heyyeqi/RodiO/issues/16) | 天外来信 + 选曲风格调优（非架构工作） | AI Voice and Selection Style Tuning | P1 | Backlog |
| [#17](https://github.com/Heyyeqi/RodiO/issues/17) | 画面流畅度 + 镜头切换渲染延迟专项审计 | Performance and Rendering Polish | P2 | Backlog |
| [#18](https://github.com/Heyyeqi/RodiO/issues/18) | 长期backlog: RDL集成 / Astronomy剩余字段 / Agent Mesh / 彩蛋 | Long-Term Backlog | P3 | Backlog |
| [#55](https://github.com/Heyyeqi/RodiO/issues/55) | 歌曲地理联动：镜头/场景随歌曲所属地域切换 | Long-Term Backlog | P3 | Backlog（纯记录，无设计方案） |
| [#56](https://github.com/Heyyeqi/RodiO/issues/56) | 地面仰视天空场景：区别于Horizon Mode平视，与#37海里仰视对称 | Long-Term Backlog | P3 | Backlog（纯记录，无设计方案） |
| [#19](https://github.com/Heyyeqi/RodiO/issues/19) | 选歌模块v2 Phase1完成确认 + Phase2 graduation监控标准 | Song Selection v2 — Phase 2 Graduation | P1 | Backlog |
| [#20](https://github.com/Heyyeqi/RodiO/issues/20) | 选歌模块v2缺口: skip_penalty分层衰减 + discovery_candidates pipeline | Song Selection v2 — Phase 2 Graduation | P2 | Done（fdd1753，本地模拟验证通过） |
| [#21](https://github.com/Heyyeqi/RodiO/issues/21) | 此刻入口 + 祈求系统实现 | Companion and Prayer System | P1 | Backlog |
| [#22](https://github.com/Heyyeqi/RodiO/issues/22) | Earth Visual Foundation 正式收口验收 | Earth Visual Foundation Formal Closure | P2 | Backlog |
| [#23](https://github.com/Heyyeqi/RodiO/issues/23) | RDL 技术方案存档：BMNG+GEBCO+GSHHG 三层LOD具体路线 | Long-Term Backlog | P3 | Backlog |
| [#24](https://github.com/Heyyeqi/RodiO/issues/24) | 彩蛋系统清单存档 + §20.3收缩规则应用 | Long-Term Backlog | P3 | Backlog |
| [#33](https://github.com/Heyyeqi/RodiO/issues/33) | 多套地球配色主题（Palette Variants）— 复用Noon Air管线 | Long-Term Backlog | P2 | Backlog |
| [#35](https://github.com/Heyyeqi/RodiO/issues/35) | 云层系统升级：多层云+天空美景谱系+Cloud View视角 | Living Earth — Vertical Space Journey | P3 | Backlog |
| [#36](https://github.com/Heyyeqi/RodiO/issues/36) | 地平线视角深化：真正贴地平视 + 独立局部地形场景（完整方案二，见Horizon Mode milestone） | Living Earth — Vertical Space Journey | P3 | In Progress（Phase 0审计完成，Phase 1-9见下） |
| [#41](https://github.com/Heyyeqi/RodiO/issues/41) | Horizon Mode Phase 0.5：资源补充 | Horizon Mode — Independent Scene Build | P2 | Done |
| [#42](https://github.com/Heyyeqi/RodiO/issues/42) | Horizon Mode Phase 1：隔离试验场景骨架 | Horizon Mode — Independent Scene Build | P2 | Done |
| [#43](https://github.com/Heyyeqi/RodiO/issues/43) | Horizon Mode Phase 2：天空穹顶 | Horizon Mode — Independent Scene Build | P2 | Done |
| [#44](https://github.com/Heyyeqi/RodiO/issues/44) | Horizon Mode Phase 3：真反射海面（海平线场景技术完整） | Horizon Mode — Independent Scene Build | P2 | Done |
| [#45](https://github.com/Heyyeqi/RodiO/issues/45) | Horizon Mode Phase 4：Orbit↔Horizon 进出场过渡 | Horizon Mode — Independent Scene Build | P2 | Backlog |
| [#46](https://github.com/Heyyeqi/RodiO/issues/46) | Horizon Mode Phase 5：海面美学打磨 | Horizon Mode — Independent Scene Build | P2 | Backlog |
| [#47](https://github.com/Heyyeqi/RodiO/issues/47) | Horizon Mode Phase 6：海岸与岛屿场景 | Horizon Mode — Independent Scene Build | P3 | Backlog |
| [#48](https://github.com/Heyyeqi/RodiO/issues/48) | Horizon Mode Phase 7：地形高度图导出管线 | Horizon Mode — Independent Scene Build | P3 | Backlog |
| [#49](https://github.com/Heyyeqi/RodiO/issues/49) | Horizon Mode Phase 8：山地平线场景 | Horizon Mode — Independent Scene Build | P3 | Backlog |
| [#50](https://github.com/Heyyeqi/RodiO/issues/50) | Horizon Mode Phase 9：陆地平视场景 | Horizon Mode — Independent Scene Build | P3 | Backlog |
| [#51](https://github.com/Heyyeqi/RodiO/issues/51) | 真实天体系统总览：太阳/月亮/星空一致性 → 七曜可见化 → 完整太阳系 | Real Celestial Bodies — Astronomically Accurate Solar System | P2 | Backlog |
| [#52](https://github.com/Heyyeqi/RodiO/issues/52) | 天体系统 Phase 1：太阳+月亮真实轨道位置系统（自转+公转） | Real Celestial Bodies — Astronomically Accurate Solar System | P2 | Done |
| [#53](https://github.com/Heyyeqi/RodiO/issues/53) | 天体系统 Phase 2：七曜可见化 | Real Celestial Bodies — Astronomically Accurate Solar System | P2 | Backlog（队列最前） |
| [#54](https://github.com/Heyyeqi/RodiO/issues/54) | 天体系统 Phase 3：完整太阳系收尾 | Real Celestial Bodies — Astronomically Accurate Solar System | P3 | Backlog |
| [#57](https://github.com/Heyyeqi/RodiO/issues/57) | 全球海水颜色物理准确性（水质科学管线扩展到全球） | Earth Visual Foundation Formal Closure | P1 | Backlog（RW标记重点，非常规排队） |
| [#37](https://github.com/Heyyeqi/RodiO/issues/37) | 深海模式：全新独立场景，摄像机沉入水下仰望天空微光 | Living Earth — Vertical Space Journey | P3 | Backlog |
| [#25](https://github.com/Heyyeqi/RodiO/issues/25) | Dislike评分未接入候选排序 — 反馈闭环架构性断裂 | Playback Reliability and Core Bug Fixes | P0 | Done（4515ef6，端到端验证通过） |
| [#34](https://github.com/Heyyeqi/RodiO/issues/34) | 天外来信/DJ播报文本长度失控 — 加硬性截断 + 防止整段外文 | Playback Reliability and Core Bug Fixes | P0 | Done（b31a024，本地实测验证通过） |
| [#26](https://github.com/Heyyeqi/RodiO/issues/26) | MiniMax TTS 静默失败 + 无降级机制 | Playback Reliability and Core Bug Fixes | P0 | Done（27c9b01 + 1c39eb1补完/api/explain路径，实测验证通过） |
| [#27](https://github.com/Heyyeqi/RodiO/issues/27) | 入场动画状态残留 + 切歌歌名闪回（竞态） | Playback Reliability and Core Bug Fixes | P1 | Done（7143114，本地实测验证通过） |
| [#38](https://github.com/Heyyeqi/RodiO/issues/38) | discovery_candidates晋升管线缺scene_id生产者 | Song Selection v2 — Phase 2 Graduation | P2 | Backlog |
| [#28](https://github.com/Heyyeqi/RodiO/issues/28) | 镜头模式库 (Daily Modes) + 智能编排/去重引擎 | P4 Stage 7 — Motion Profiles Productization | P1 | Backlog |
| [#29](https://github.com/Heyyeqi/RodiO/issues/29) | IP地域首曲本地化 | Long-Term Backlog | P2 | Backlog |
| [#30](https://github.com/Heyyeqi/RodiO/issues/30) | 天气视觉映射系统（雨/雪/风） | Long-Term Backlog | P3 | Backlog |
| [#31](https://github.com/Heyyeqi/RodiO/issues/31) | 天体可视化扩展：流星+星座+月球渲染 | P4 Stage 5 — Star System Verification and Polish | P2 | Backlog |
| [#32](https://github.com/Heyyeqi/RodiO/issues/32) | 真实驱动地形事件：火山喷发等 | Long-Term Backlog | P3 | Backlog |
| [#39](https://github.com/Heyyeqi/RodiO/issues/39) | 连续日夜过渡系统（Day Cycle Controller）：11时段从互斥主题改为太阳驱动的连续插值 | Continuous Day Cycle System | P2 | Done（d0b8f5a+b85d485，20倍速加速时间端到端验证通过） |
| [#40](https://github.com/Heyyeqi/RodiO/issues/40) | 航线视角 Flight View：巡航高度沿大圆航线飞行，连接Cloud与Horizon的中间层 | Living Earth — Vertical Space Journey (Cloud/Flight/Horizon/Underwater) | P3 | Backlog |

- 每次开始一个任务，先把对应 issue 在看板上拖到 In Progress；完成验收后拖到 Done，并在本文件和 devlog.md 都留下记录。
