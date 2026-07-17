# RodiO Visual System Master Roadmap v3.1 Full Execution Edition

> 版本：v3.1 Full Execution Edition  
> 日期：2026-06-04  
> 定位：RodiO 视觉系统主控路线图。  
> 目的：在不删减原始方案关键信息的前提下，将 Earth / Sky / 资源治理 / 镜头运动 / 天气 / 七曜天体 / 执行协议整合为可执行文件包。  
> 使用原则：主文件管方向，实施文件管行动，source_appendix 保留完整原文依据。不得只看主文件就施工。

---

## 0. 为什么要出 v3.1

v3.0 文件包存在一个问题：为了把多个方案合并成“可读路线图”，正文被压缩得过多，导致部分执行细节、参数表、历史阶段边界、颜色锚点、禁止项和候选验收标准没有直接进入实施文件。v3.1 的处理方式是：

1. **不再用摘要替代原文**：所有原始资料完整放入 `source_appendix/`。
2. **实施文件保留关键参数与阶段边界**：不是只写方向，而是写允许事项、禁止事项、验收项、产物路径、失败处理。
3. **主文件不替代实施文件**：Codex / Claude Code 施工时必须同时读取主文件、执行协议、对应实施文件和必要的 source_appendix 原文。
4. **远期功能保留但冻结**：天气、七曜、节气、天体交接、音乐语义联动进入长期规划，不进入当前几周施工。

---

## 1. 文件包结构

```text
00_Master_Roadmap_v3.1_FullExecution.md
01_Current_Workflow_How_To_Use_This_Pack.md
02_Earth_Visual_Foundation_Implementation_v3.1.md
03_Sky_Visual_System_Implementation_v3.1.md
04_Resource_Performance_Governance_v3.1.md
05_Earth_Camera_Motion_Music_Implementation_v3.1.md
06_Weather_Celestial_Context_Future_v3.1.md
07_Claude_Codex_Execution_Protocol_v3.1.md
08_Appendix_Map_and_Source_Index_v3.1.md
source_appendix/
  A_RodiO_3D地球视觉优化近期推进规划_v1.0_原始.md
  B_RodiO_3D地球视觉系统近期推进规划_v2.0_上轮.md
  C_rodio_sky_design_v3_2_原始全文.md
  D_RodiO_Visual_System_Integrated_Roadmap_v1_7_原始全文.md
  E_RodiO_产品方案_v3_原始全文.md
```

---

## 2. 当前总体判断

RodiO 当前不再是单一“地球贴图优化”任务，而是一个分层视觉系统：

| 系统 | 当前定位 | 近期是否施工 |
|---|---|---|
| Earth Visual Foundation | 白天/夜晚地球母版、云层、大气辉光、城市灯光、资源精度 | 是，当前主线 |
| Sky Visual System | 11 时段天空、skyMesh、LUT、星场、CSS fallback | 规划保留，按解锁节点推进 |
| Resource & Performance Governance | 资源目录、分辨率、缓存、MacBook Air 开发策略、PWA 性能 | 是，必须同步执行 |
| Earth Camera & Motion | 多视角地球、镜头预设、播放/暂停/切歌基础运动 | 近期只预研或做最小可控版本 |
| Weather Reactive System | 真实天气驱动 UI / Earth 氛围 | 否，远期，当前只预留 |
| Celestial Context System | 七曜、节气、节日、行星轨道、零点交接仪式 | 否，远期，当前只预留 |

当前几周主线：

```text
Day Earth Master
  → Night Earth Master
  → Fidelity / Resource Governance
  → Cloud Layer
  → Atmospheric Limb Glow
  → 11 Time Modes Color Integration
  → Earth Camera & Basic Motion Pre-study
```

---

## 3. 当前不能混入的事项

当前阶段严禁把以下内容混入 Earth Visual Foundation：

- 完整天气联动；
- 真实行星轨道；
- 七曜零点交接动画；
- 节气 / 节日完整系统；
- 全量歌词语义彩蛋；
- 高复杂度音频频谱可视化；
- 实时全球天气云图；
- PBR / MeshStandardMaterial 全量重构；
- 未经审计的 Terminator 昼夜分界线；
- 未经确认的 16K 默认加载。

这些功能不删除，但冻结到远期阶段。

---

## 4. 主阶段路线

### E1：Day Earth Master 白天地图母版

目标：形成长期可复用的白天母版。重点处理海洋层次、沙漠过曝、极地白化归因、太平洋岛屿识别、地中海/日本海/黑海/南海等重点区域。

### E2：Night Earth Master 夜晚地图母版

目标：基于白天母版派生夜晚版。夜晚不是白天图压暗，而是低亮地貌底图 + 暖黄城市灯光 + 冷色海洋暗部 + 干净黑位。

### E3：Fidelity / Resource Strategy 精度与资源治理

目标：确定 4K / 8K / 16K 分级，production/candidates/source/archive/tmp 分区，避免客户端资源失控。

### E4：Cloud Layer 云层专项

目标：轻薄、慢速、低透明度，不遮浅海，不遮城市灯，不加剧极地白化。

### E5：Atmospheric Limb Glow 大气边缘辉光专项

目标：减少假描边、假蓝光、厚雾圈。做成薄、轻、有方向性、随时段变化的大气散射层。

### E6：11 Time Modes Color Integration 十一种模式色彩联调

目标：以 Sky v3.2 的 11 时段体系作为统一时间语言，但按当前代码实际状态分步接入。

### E7：Earth Camera & Basic Motion 地球镜头与基础运动

目标：摆脱单一地球仪视角，形成 Globe / Horizon / Low Orbit / Deep Space / Hemisphere / City Focus / Ocean View 等镜头预设，并为音乐联动预留。

### F：Weather Reactive System 天气响应系统

远期。只规划，不开发。

### G：Celestial Context System 七曜与天体情境系统

远期。包括七曜零点交接、行星轨道视角、节气、节日、特殊天象。

---

## 5. 每次开工的最小文件组合

### 地球母版 / 云层 / 大气辉光

```text
00_Master_Roadmap_v3.1_FullExecution.md
02_Earth_Visual_Foundation_Implementation_v3.1.md
04_Resource_Performance_Governance_v3.1.md
07_Claude_Codex_Execution_Protocol_v3.1.md
source_appendix/A_RodiO_3D地球视觉优化近期推进规划_v1.0_原始.md
source_appendix/B_RodiO_3D地球视觉系统近期推进规划_v2.0_上轮.md
```

### 天空 / 11 时段 / skyMesh / LUT

```text
00_Master_Roadmap_v3.1_FullExecution.md
03_Sky_Visual_System_Implementation_v3.1.md
07_Claude_Codex_Execution_Protocol_v3.1.md
source_appendix/C_rodio_sky_design_v3_2_原始全文.md
source_appendix/D_RodiO_Visual_System_Integrated_Roadmap_v1_7_原始全文.md
```

### 地球镜头 / 音乐运动

```text
00_Master_Roadmap_v3.1_FullExecution.md
05_Earth_Camera_Motion_Music_Implementation_v3.1.md
07_Claude_Codex_Execution_Protocol_v3.1.md
```

### 天气 / 七曜 / 天体系统讨论

```text
00_Master_Roadmap_v3.1_FullExecution.md
06_Weather_Celestial_Context_Future_v3.1.md
source_appendix/E_RodiO_产品方案_v3_原始全文.md
```

---

## 6. 当前下一步建议

不要直接施工。下一轮应做：

```text
只读审计当前 RodiO 项目状态，与本 v3.1 文件包对齐。
```

审计输出必须包括：

1. git status；
2. 当前 earth / sky / cloud / masks / candidates / source 目录结构；
3. dayTexture / nightTexture / cloud / specular / sky 的实际引用路径；
4. 当前启用的时段 key；
5. 当前 production 与候选资源是否混乱；
6. 当前阶段对应本 Roadmap 哪一项；
7. 下一步最小任务建议；
8. 禁止本轮处理事项。
