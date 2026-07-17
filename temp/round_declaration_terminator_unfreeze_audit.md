你是 RodiO 项目的执行审计助手。请严格按文件执行，不得自由发挥扩大范围。

请先阅读：
1. `00_Master_Roadmap_v3.1_FullExecution.md`
2. `07_Claude_Codex_Execution_Protocol_v3.1.md`
3. 本轮任务相关实施文件：`02_Earth_Visual_Foundation_Implementation_v3.1.md`（第8节"本文件执行禁区"）、`05_Earth_Camera_Motion_Music_Implementation_v3.1.md`
4. 必要 source_appendix 原文：如涉及晨昏线/太阳位置的历史设计记录，一并查阅

## 本轮阶段

只读审计（Terminator 解冻审计）——这是 Master Pack 明确要求的、在触碰任何晨昏线相关内容前必须单独走一遍的审计轮次，不是普通的功能审计。

## 本轮目标

回答一个问题：**"新的地球镜头系统方案里，`terminatorPortrait`（晨昏线主题静态构图）和涉及晨昏线的运动原语/日常模式（比如沿经度缓慢移动、观察区域自然进入日夜交界），是否已经算触碰了 Master Pack 冻结的'Terminator 昼夜分界线'功能？"**

## 已知背景（我已经独立核实过，供你复核，不要直接假设成立）

- 冻结条款原文出自 `00_Master_Roadmap` 第3节"当前不能混入的事项"——"未经审计的 Terminator 昼夜分界线"，以及 `02_Earth_Visual_Foundation` 第8节"本文件执行禁区"——"Terminator 突然施工"
- `pwa/earth3d.js:5745` 的 `updateSunPosition()` 和它调用的 `_computeSubsolarPoint()` 已经在做真实太阳位置计算（非per-theme override时），驱动地球材质本身的明暗渲染——这部分是已有基础设施
- 但各个时段主题（dawn/noon/evening等）大多数情况下用的是 `sunDirection` 这个固定的、按艺术方向手写的 override（比如 `{x:10,y:0,z:0}`），不是真实太阳位置——只有没配置 override 的情况才会退回真实计算
- 全代码库搜索 `terminator`/`dayNight`/`twilight`/`boundary line` 等关键词，**没有找到任何专门渲染"晨昏线边界"的 shader 或视觉特效代码**——说明这从来没被实现过，不是"有半成品没审计"，纯粹是空白

## 请你独立核实并回答

1. 逐个时段主题（dawn/noon/afternoon/evening/lateEvening/deepNight/earlyMorning，以及所有 `THEME_VISUAL_CONFIG` 里定义的），确认哪些用了 `sunDirection` override、哪些走真实 `_computeSubsolarPoint()` 回退路径
2. `_computeSubsolarPoint()` 的具体实现（找到函数定义，不要只看调用点）——确认它是不是一个真实的太阳赤纬/时角计算，还是简化/占位实现
3. 除了 `earth3d.js`，`core/astronomy.js` 里是否已经有类似的太阳位置/晨昏线计算可以复用（这个模块已知有节气/日月相位计算，值得看一眼是否已经顺带算了这个）
4. 明确给出结论：以下三类，哪些属于"冻结范围内，这轮不能做"，哪些属于"用现有真实光照即可，不算触碰冻结项"：
   - `terminatorPortrait`（静态构图：完整地球+晨昏线出现在画面里，相机只负责取景角度，不新增任何边界线渲染）
   - `terminatorTrack`/`Day to Night`（运动原语：相机沿经度或方位缓慢移动，观察区域自然经过已有的真实明暗交界，不新增判断"现在是不是正好在分界线上"的逻辑）
   - 一条独立的、明确画出来的"晨昏线视觉特效"（比如沿分界线渲染一条光晕/描边）——这个无论如何这轮都不解冻，需要单独走一次完整的实施审计
5. 如果第4点的前两类被判定为"不算触碰冻结项"，请说明理由必须扎实（不能是"我觉得应该没事"），并指出如果之后真的要做一条独立的晨昏线特效，需要满足哪些前置条件（比如：先确认哪些主题该用真实太阳位置而不是硬编码override，否则特效会跟当前"允许艺术化处理"的设计冲突）

## 本轮禁止

- 不允许修改任何文件
- 不允许生成任何新资源/代码/候选
- 不允许 commit
- 不允许顺手开始实现 `terminatorPortrait`/`terminatorTrack` 或任何镜头系统的其他部分——这轮只回答"能不能做"，不做

## 允许修改文件

无（本轮零代码改动）

## 允许 commit

否

## 本轮不处理事项

- 新地球镜头系统的任何实际实现（构图库/运动原语/日常模式）——这是下一轮的事，取决于这轮审计结论
- 晨昏线视觉特效本身的设计——明确排除在本轮和"新镜头系统第一批"之外

## 回滚方案

无需回滚，本轮不改动任何文件。

## 请按 Master Pack 的"只读审计模板"输出报告，额外补充第4/5点的施工许可结论
