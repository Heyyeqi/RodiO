# RodiO Visual System Integrated Roadmap v1.7

**版本**：v1.7  
**日期**：2026-06-01  
**适用项目目录**：`~/Projects/RodiO`  
**旧目录排除**：`~/Projects/RodiO_old_unused` 仅作历史备份，不参与开发  
**当前视觉基线 commit**：`d5755be Add conservative skyMesh skeleton and sky theme placeholders`  
**当前待验收改动**：`E0.1 Ocean Specular Visibility`，工作树预期为 `M pwa/earth3d.js`  
**文档定位**：本文件是 RodiO 后续视觉系统的统一规划文档，整合 Sky Visual System v3.2 与 Earth Visual Upgrade 两条路线，统一管理 sky / earth / ocean / cloud / atmosphere / terminator / city lights / fallback。

**v1.7 修订重点**：本版在 v1.6 基础上完成最终执行一致性收口：将原 `A.12 最终验收标准` 移出附录编号体系，改为主文正式章节 `22. 最终验收标准`；修正附录 A Phase 1 任务 5 中残留的“按第九章 / 按第六章 6.3 节”旧引用，统一改为“按附录 A 第 9 节 / 按附录 A 第 6.3 节”。

---

## 0. 命名约定与章节规则

为避免执行时混淆，本文件只保留一套主章节编号，所有子路线均映射到主章节之下。主文一律使用阿拉伯数字章节（`0–21`），附录 A 一律使用 `A.x` 编号；不得再使用“一、二、十二”等中文编号作为正式章节号。

| 名称 | 含义 | 使用范围 | 状态 |
|---|---|---|---|
| `Sky P` / `Sky Phase` | Sky Visual System 子阶段 | 天空球、LUT、星场、CSS fallback、天空色彩 | 主文优先使用 `Sky P0/P1A/P1B`，附录 A 保留原 `Phase` 命名 |
| `E` 系列 | Earth Visual Upgrade 子阶段 | 地球表面、海洋、云层、大气辉光、昼夜分界线 | 保留 |
| `Stage` | 旧版总路线残留称呼 | 不再作为正式编号使用 | 删除 / 不再新增 |
| `附录 A` | `rodio_sky_design_v3_2.md` 全量整合文本 | 天空系统完整设计、色彩 stops、施工指令 | 保留为权威参考 |

引用规则：

- 主文引用主章节时使用“第 X 章 / 第 X.Y 节”；
- 引用天空系统原始设计时，必须写成“附录 A 第 6.2 节”或“附录 A 第 8.1 节”，不得只写“附录 A 第 6 节”；
- Codex 指令中涉及 v3.2 颜色、LUT、Tone Mapping、CSS fallback、星场透明度时，统一引用附录 A，但实际执行顺序以主文第 3 章和第 11 章为准；
- 任何施工前必须先确认工作树状态，禁止跨阶段混合提交。

---

## 1. 总体判断

RodiO 目前已经完成 3D 地球基础渲染、夜间城市灯、ocean specularMap 初步接入、skyMesh 骨架接入和 `goldenApproach` / `lateEvening` 结构占位。现阶段的主要矛盾已经从“能不能稳定渲染 3D 地球”，转向“地球主体是否具备动态壁纸级质感”。

用户参考图显示，目标质感不是单一由 skyMesh 或 ocean specularMap 决定，而是由以下视觉层共同构成：

1. 高清地球表面纹理；
2. 独立云层；
3. 大气边缘蓝白光晕；
4. 昼夜分界线；
5. 暗部城市灯；
6. 深空黑底和星场；
7. 手机端稳定性能与 fallback。

因此，后续正式采用**双线独立推进、共享解锁节点**的视觉路线：

- **Sky Visual System**：处理天空、时段色彩、LUT、星场、CSS fallback；
- **Earth Visual Upgrade**：处理地球主体质感，包括 ocean specular、cloud layer、atmosphere rim glow、terminator、city lights dark-side blend。

这里的“双线”不是任意并行施工。两条线可以独立审计和规划，但实际施工必须遵守第 3 章的共享解锁节点：同一时间只允许推进一个最小阶段，不允许把 Sky LUT、cloudMesh、ocean specular、rim glow 或 terminator 混入同一提交。

完整 v3.2 目标不等于立即施工范围。实际推进仍必须遵守：审计先行、小步提交、可回退、可观测。


> 🛑 **CRITICAL FORBIDDEN ZONE｜防御性编程与视觉克制绝对禁止项**
>
> 1. **严禁升级 PBR**：在 1.x 路线中，地球主材质继续死守 `MeshPhongMaterial` 基线，严禁擅自引入 `MeshStandardMaterial`、`roughnessMap` 或完整 PBR 管线。
> 2. **严禁偷跑 Terminator**：任何 E0/E1/E2 或 Sky 阶段不得顺手编写昼夜分界线、day/night shader mix、city lights dark-side blend。Terminator 只能在 E3 专项审计通过后施工。
> 3. **严禁假设资产存在**：任何 cloud / normal / bump / KTX2 / 8K 新纹理路径，必须先通过资源审计确认存在、尺寸、格式、显存预算和 fallback，禁止硬编码未经验证的路径。
> 4. **严禁跨线混合提交**：Sky LUT、Cloud Layer、Ocean Specular、Atmosphere Rim Glow、Terminator、播放器和 service worker 不得混在同一 commit。
> 5. **严禁提前改 `index.html` 背景**：`#app background` 改为纯色只属于 Sky fallback / LUT 相关阶段，不并入 E0.1 ocean specular 小改，避免把海面高光验收与背景系统变化混在一起。

---

## 2. 与 `rodio_sky_design_v3_2.md` 的整合关系

`rodio_sky_design_v3_2.md` 不是外部参考，而是本文件的天空系统主干，已作为**附录 A**全量并入。附录 A 的核心内容包括：

> ⚠️ **执行优先级说明**
>
> 附录 A 是 Sky Visual System 的**完整蓝图和设计规范**，不是当前立即施工指令。实际推进必须遵守主文第 3 章（双线依赖关系）和第 11 章（近期执行顺序）。在 RW 未明确解锁前，不得直接执行附录 A 的完整 Phase 1，包括：不得一次性扩展完整 11 时段 UI / 自动流，不得实现双 LUT，不得修改 `index.html #app background` 为纯色，不得新增“暮前 / 入夜”按钮，不得启用动态 exposure。
>
> 当前实际阶段仍是：`E0.1 验收 → E0.1 commit + 基线存档 → E1 Cloud 资源审计`。附录 A 的 Phase 1/2/3/4 需要通过主文阶段映射表逐步拆解后再执行。


| 领域 | v3.2 已定义内容 | 本文件处理方式 |
|---|---|---|
| 11 时段模型 | `deepNight / dawn / sunrise / earlyMorning / morning / noon / afternoon / goldenApproach / sunset / evening / lateEvening` | 保留为天空与地球视觉统一的时段基准 |
| 天空配色 | 每个时段 8–12 个 sky stops，含 `sunrise pos=0.43 #622840`、`sunset pos=0.40 #542238` 等关键锚点 | 全量并入附录 A 第 6.2 节，后续施工不得自行猜色 |
| 天空架构 | skyMesh + ShaderMaterial + 双 LUT + GPU `mix()` | 作为 Sky Visual System 的目标架构，但当前保守路线已先完成 skyMesh skeleton |
| DataTexture | `RGBAFormat + UnsignedByteType`，避免 `RGBFormat` 废弃风险 | 后续双 LUT 阶段强制采用 |
| Shader t 值 | 基于 `viewDir`，而非 `worldPosition.y` | 保留；Phase 1A skeleton 已采用该方向 |
| 星场透明度 | 11 时段 star opacity 表 | 后续 sky LUT 阶段或星场联动阶段执行 |
| CSS fallback | OKLab 优先 + sRGB fallback | 后续 fallback 阶段执行，当前不得提前改 `index.html` |
| 显存预算 | 移动端 128MB、桌面端 512MB、低端关闭部分资源 | 纳入 cloud / texture / LUT 后续资源策略 |
| 大气光晕参数 | `glowIntensity / glowColor` 按时段表 | 拆出 E2 Atmosphere Rim Glow，先审计再施工 |
| 云层规划 | 独立 cloud mesh，LOD 分级，Phase 3 前资源审计 | 升级为 E1 Cloud Layer Foundation 主线 |
| 海水高光 | 保留 `MeshPhongMaterial + specularMap` | 当前 E0.1 已做参数试探，待验收 |

需要特别说明：`rodio_sky_design_v3_2.md` 已经包含完整 11 时段 sky stops。真正的问题不是色彩表缺失，而是当前保守施工尚未把完整 sky stops 纳入代码。因此，后续若进入 Sky LUT 阶段，唯一颜色来源是附录 A 第 6.2 节。

**数值优先级规则**：附录 A 第 7.2 节是天空 v3.2 的原始标准参数；主文 E0.1 是在当前真实代码基线上对 ocean specular 可见性做的低风险试探。如果 E0.1 人工验收通过，则 E0.1 的 `morning / noon / afternoon / goldenApproach` `specular / shininess` 作为当前运行基线，覆盖附录 A 第 7.2 节对应四项材质参数；如果 E0.1 验收失败，则回退到附录 A 第 7.2 节原始值。后续任何施工指令必须明确引用“附录 A 原始值”还是“E0.1 当前运行基线”，不得混用。

---

## 3. 双线独立推进、共享解锁节点与执行顺序

### 3.1 总体依赖关系

两条路线的关系定义如下：**路线层面独立，提交层面串行；达到共享解锁节点后，可以选择进入 Earth 或 Sky 的下一步，但不得在一次施工中混合两条路线的改动。**

```text
当前稳定基线
  └─ Sky P1A：skyMesh skeleton 已提交 d5755be
       └─ E0.1 Ocean Specular Visibility 当前待验收（工作树预期 M pwa/earth3d.js）
            └─ E0.1 commit + Visual Baseline Archive
                 ├─ E1-0 Cloud Asset Decision / 资源审计
                 ├─ Sky P1B-0 11 时段端到端接入审计
                 └─ E2-0 Atmosphere Rim Glow 审计
```

### 3.2 Earth Visual Upgrade 路线依赖

```text
E0.1 Ocean Specular Visibility（含 E0.2 基线存档子步骤）
  → E1 Cloud Layer Foundation
  → E1.1 Cloud Visual Tuning
  → E2 Atmosphere Rim Glow Audit & Enhancement
  → E3 Day/Night Terminator System
  → E4 Earth Color Grading
  → E5 Material System Upgrade
```

### 3.3 Sky Visual System 路线依赖

```text
Sky P0 Audit
  → Sky P1A skyMesh skeleton（已完成）
  → Sky P1B 11 时段体系统一（暂缓）
  → Sky P2 双 LUT + 星场联动（暂缓）
  → Sky P3 OKLab / CSS fallback / Tone Mapping 标定（暂缓）
  → Sky P4 sky-earth 统一调色（远期）
```

### 3.3.1 主文阶段与附录 A 阶段映射

| 主文阶段 | 对应附录 A 阶段 / 内容 | 当前状态 | 执行说明 |
|---|---|---|---|
| Sky P0 | 附录 A Phase 0 审计 | 已执行过，后续需按当前代码复核 | 输出必须进入固定 Markdown 审计表 |
| Sky P1A | 附录 A 未单列；属于保守拆分 | 已完成 | 只完成 skyMesh skeleton，不含双 LUT |
| Sky P1B | 附录 A Phase 1 的“11 时段扩展”部分 | 暂缓 | 只做 key / 自动流 / 按钮 / 配置统一，不含双 LUT |
| Sky P2 | 附录 A Phase 1 的“双 LUT + 星场联动”部分 | 暂缓 | 含 LUT、DataTexture、GPU mix、star opacity lerp |
| Sky P3 | 附录 A Phase 2：OKLab + exposure + glow 参数 | 暂缓 | exposure 与 glow 必须在 E2 / Sky P3 协调后启用 |
| Sky P4 | 附录 A Phase 3/4 的云层、海水高光等远期内容 | 远期 | 其中 cloud 已升级为主文 E1，ocean specular 已拆为 E0.1 |

附录 A 中的 Phase 1 指令不再作为“一次性施工包”执行，必须按上述映射拆分。

### 3.4 解锁条件

| 阶段 | 解锁条件 | 备注 |
|---|---|---|
| E0.1 commit | 人工确认 morning / noon / afternoon / goldenApproach 无过曝、无塑料感，夜景不受影响 | 当前优先 |
| E0.1 基线存档 | E0.1 commit 完成，工作树 clean | 作为 E0.1 验收子步骤执行，不再单独制造阶段阻塞 |
| E1-0 Cloud Asset Decision | E0.1 commit + 基线存档完成 | 先确认 cloud 资源是否存在、路径、格式、尺寸、授权与 fallback，不施工 |
| E1 施工 | E1-0 审计确认资源路径、透明排序、降级方案 | 只新增 cloudMesh，不碰 terminator |
| Sky P1B-0 11 时段端到端接入审计 | E0.1 commit + 基线存档完成 | 只审计 `goldenApproach / lateEvening` 从 earth3d.js 到 index.html / fallback / LUT 的全链路，不施工 |
| E2 审计 | E1 稳定后 | 大气边缘光晕专项审计 |
| E3 施工 | E1/E2 稳定、专项审计通过、RW 明确批准 | 高风险，禁止顺手做 |
| Sky LUT | Sky P0/P1B-0 结论复核、E0.1 基线完成 | 不与 cloudMesh 同轮施工 |

---

## 4. 参考图视觉拆解

三张参考图共同指向以下视觉特征：

| 模块 | 参考图表现 | 当前 RodiO 状态 | 判断 |
|---|---|---|---|
| 高清地表 | 陆地、海洋、海岸线清晰 | 已有 `dayTexture` | 基础具备 |
| 夜间城市灯 | 暗部城市灯明显但不刺眼 | 已有 `nightTexture / emissiveMap` | 基础具备 |
| 海洋层次 | 海洋更蓝，有轻微反光 | `specularMap` 已接入但偏弱 | E0.1 小改处理中 |
| 独立云层 | 云团明显，有漂浮感、透明感 | 暂无 `cloudTexture / cloudMesh` | 缺失，E1 主线 |
| 大气边缘光晕 | 地球边缘蓝白 halo 明显 | 有 atmosphere mesh，但不够壁纸级 | E2 主线 |
| 昼夜分界线 | 明暗交界清晰，城市灯在暗部透出 | 当前按时段切换，不是真实 terminator | E3，高风险 |
| 城市灯暗部混合 | 灯光只在夜侧增强 | 当前是简化 emissive 时段逻辑 | E3/E4 之后处理 |
| 深空背景 | 黑底干净，星点克制 | skyMesh 已有骨架 | Sky 后续优化 |
| 手机端适配 | 锁屏动态壁纸感 | 当前为 PWA WebGL | 需分级降级 |

结论：短期最值得做的是独立云层与大气边缘光晕。昼夜分界线是核心目标，但不得近期直接施工。PBR / MeshStandardMaterial 不是近期目标。

---

## 5. 当前状态与近期收口

### 5.1 已完成：Sky P1A skyMesh skeleton 与 P1B 结构占位

已提交：

```text
d5755be Add conservative skyMesh skeleton and sky theme placeholders
```

完成内容：

- 新增最小 `skyMesh`；
- 新增最小 `ShaderMaterial`；
- `skyMesh` 加入 `scene`，不加入 `earthGroup`；
- `renderOrder = -1000`；
- `depthWrite = false`；
- `depthTest = false`；
- 未启用双 LUT；
- 未启用 GPU mix；
- 未修改 `renderer.toneMapping / toneMappingExposure`；
- 预留 `goldenApproach / lateEvening`；
- 新增 `getDebugState()` sky 只读字段；
- 新增 `setSkyVisible(visible)` 调试控制口。

### 5.2 当前待验收：E0.1 Ocean Specular Visibility

当前未提交状态预期：

```text
M pwa/earth3d.js
```

已施工内容：

```js
morning: {
  material: {
    specular: 0x06090f,
    shininess: 1.05,
  },
}

noon: {
  material: {
    specular: 0x091018,
    shininess: 1.12,
  },
}

afternoon: {
  material: {
    specular: 0x05080d,
    shininess: 0.96,
  },
}

goldenApproach: {
  material: {
    specular: 0x070503,
    shininess: 0.68,
  },
}

function shouldUseOceanSpecularMap(themeKey) {
  return ['morning', 'noon', 'afternoon', 'goldenApproach'].includes(themeKey)
}
```

该改动属于低风险视觉增强，目标是让白天和暮前海洋高光更容易被感知，但不追求动态壁纸级海洋效果。

与附录 A 第 7.2 节的差异处理：E0.1 是当前真实代码基线上的实验性覆盖值，不代表附录 A 标准作废。若 E0.1 验收通过，则这些值成为当前运行基线；若出现过曝、塑料感、暮前暖调变脏或夜景受影响，则立即回退至附录 A 第 7.2 节原始值。

验收通过后建议提交：

```bash
git add pwa/earth3d.js
git commit -m "Refine ocean specular visibility for daytime themes"
```

---

## 6. 设计原则与禁止项

### 6.1 小步提交

每个阶段只解决一个视觉层：ocean specular、cloud layer、atmosphere rim glow、terminator、city lights blend、color grading。不得在同一个 commit 中混合多个视觉系统。

### 6.2 可回退与可观测

每个新增层都必须具备关闭或回退能力：

```js
setSkyVisible(false)
setCloudVisible(false)      // 后续新增
setRimGlowVisible(false)    // 后续新增
```

新增状态必须进入 `getDebugState()`，用于人工验收和排错。

### 6.3 保留现有稳定链路

近期不得破坏：

- `dayTexture` 加载；
- `nightTexture` 加载；
- `emissiveMap` 夜间城市灯；
- `ocean specularMap` 路径；
- `skyMesh`；
- `WebGL fallback`；
- 播放器；
- service worker；
- `index.html` UI 主逻辑；
- `#app background`：E0.1 不得提前改为纯色，避免与 skyMesh / ocean specular 验收混杂。

### 6.4 先加层，后改主材质

优先新增独立层：

```text
earth mesh
cloud mesh
atmosphere mesh / rim glow mesh
sky mesh
stars
```

暂不直接重写 `earthMaterial`。

### 6.5 暂不 PBR

近期继续沿用 `MeshPhongMaterial`。暂不切换 `MeshStandardMaterial / PBR`，因为这会牵连光源体系、toneMapping、emissive 城市灯、specularMap、颜色空间、移动端性能和视觉基线。

### 6.6 Terminator 暂缓原则

昼夜分界线是参考图目标质感的核心之一，但必须在独立专项审计通过后才能施工。任何阶段不得“顺手”加入 terminator。

Terminator 施工前置条件（全部满足前，任务状态为“暂缓，条件待定”）：

1. E1 cloudMesh 已稳定并完成截图验收；
2. E2 atmosphere rim glow 已稳定并完成截图验收；
3. 已完成 E0.2 视觉基线存档；
4. 已完成 terminator 专项审计，明确 day/night 混合算法、sunDirection 来源、城市灯暗部混合策略、fallback 策略；
5. RW 明确批准进入 E3；
6. 本轮 commit 只能包含 terminator 相关代码，不得混入 cloud / sky / UI / 播放器改动。

---

## 7. Earth Visual Upgrade Roadmap

### 7.1 E0.1：Ocean Specular Visibility

目标：小幅提升白天和暮前海面高光可见性。

允许：

- 微调 `morning / noon / afternoon / goldenApproach` 的 `specular / shininess`；
- 将 `goldenApproach` 纳入 `shouldUseOceanSpecularMap()`。

禁止：

- 不改资源；
- 不改光源；
- 不改相机；
- 不改材质类型；
- 不改 skyMesh；
- 不改 fallback；
- 不改夜间城市灯。

验收：

- `morning` 海面略有层次；
- `noon` 高光最明显但不过曝；
- `afternoon` 比 noon 柔和；
- `goldenApproach` 有温和暖调反光；
- `lateEvening / deepNight` 城市灯不受影响，尤其 `lateEvening` 灯光边缘清晰、无泛白光晕；
- skyMesh 不受影响；
- `sunset` 是否需要低强度 specularMap 仅作为观察项，不纳入当前 E0.1 改动，后续独立评估。

### 7.2 E0.1 子步骤：Visual Baseline Archive

目标：E0.1 验收通过并 commit 后，立即固定当前视觉基线。该步骤不再作为独立阶段阻塞路线，但未完成截图和状态存档前，不建议进入 E1 施工。

执行内容：

1. 使用干净 Chrome profile；
2. 截图记录：`morning / noon / afternoon / goldenApproach / sunset / lateEvening / deepNight`；
3. 标准分辨率：移动端 375×812，桌面端 1920×1080；
4. 命名格式：`RodiO_V0.2_Baseline_[ThemeKey]_[Platform]_[YYYYMMDD].png`；
5. 记录 `window.earth3d.getDebugState()` 输出 JSON，与截图一同归档；
6. 记录当前资源加载状态；
7. 记录性能基线；
8. 强制归档目录：`~/Projects/RodiO/docs/baselines/v0.2/`；
9. 强制文件命名格式：`[themeKey]_[commitHash]_[platform]_[resolution].png`，例如 `noon_d5755be_desktop_1920x1080.png`。

性能基线记录要求：

- 桌面端：使用 Chrome Performance 面板录制 10 秒，记录平均 fps、最低 fps、GPU memory 如可见；
- 移动端：如暂时无法测量，至少记录设备型号、浏览器版本、主观流畅度、是否发热；
- 后续任何“帧率不低于改造前 85%”的验收标准，必须以 E0.2 记录为对照，不得凭感觉判断。

### 7.3 E1：Cloud Layer Foundation

目标：新增独立 cloudMesh，让地球表面出现参考图那种白色云层漂浮感。

E1 前置审计：

- `pwa/assets` 是否已有 cloud 资源；
- 若没有，是否需要新增 `cloudTexture`；
- 资源格式优先：灰度 alpha mask（或单通道 R 作为 `alphaMap`）；其次才是 RGBA 透明 PNG/WebP；
- 资源分级：2K / 4K 两级；
- 移动端优先 2K 或融合云层贴图；低端设备可关闭独立 cloudMesh，但不应让视觉完全退化为“裸地球”；
- 云层是否遮挡夜间城市灯；
- 云层透明排序是否与 atmosphere / skyMesh 冲突。

E1 最小实现：

- 新增 `cloudTexture` 加载；
- 新增 `cloudMesh`；
- 半径建议 `2.03–2.05`；
- `transparent: true`；
- `depthWrite: false`；
- 可开关 `setCloudVisible(false)`；
- `getDebugState()` 增加 cloud 字段；
- 云层跟随 `earth.quaternion`，并允许极慢独立偏移。

E1 禁止：

- 不做 terminator；
- 不改 earthMaterial；
- 不改 day/night 贴图；
- 不改城市灯；
- 不改 PBR；
- 不改播放器；
- 不改 service worker。

### 7.4 E1.1：Cloud Visual Tuning

目标：在 cloudMesh 稳定后，仅调云层表现。

可调内容：

- `opacity`；
- `renderOrder`；
- 透明排序；
- 昼夜时段云层可见度；
- 移动端是否关闭；
- 云层独立慢速旋转速度。

### 7.5 E2：Atmosphere Rim Glow Audit & Enhancement

目标：增强地球边缘蓝白光晕，使其接近参考图的动态壁纸质感。

E2 前置审计必须回答：

| 审计项 | 当前值 | 目标值 | 是否符合 | 风险 | 是否允许施工 |
|---|---|---|---|---|---|
| 当前 atmosphere material 类型 | 待审计 | 明确 MeshPhong / ShaderMaterial | 待定 | 待定 | 待定 |
| 是否已有 Fresnel | 待审计 | 明确有/无 | 待定 | 待定 | 待定 |
| atmosphere renderOrder | 待审计 | 不遮挡 earth/cloud/sky | 待定 | 待定 | 待定 |
| 是否受 skyMesh 影响 | 待审计 | 不冲突 | 待定 | 待定 | 待定 |
| 是否应新增 rimGlowMesh | 待审计 | 优先新增独立层 | 待定 | 待定 | 待定 |
| 是否按时段联动颜色 | 待审计 | 日出/落日偏暖，深夜偏冷 | 待定 | 待定 | 待定 |

推荐路线：优先新增可关闭 `rimGlowMesh`，而不是直接重写现有 atmosphere。`rimGlowMesh` 使用 Fresnel shader，`depthWrite=false`，不影响 earth / cloud / city lights。

### 7.6 E3：Day/Night Terminator System

目标：实现参考图中的昼夜分界线，让白天地表、夜间城市灯和晨昏线在同一地球上共存。

暂缓理由：

- 需要自定义 earth shader 或复杂叠加层；
- 会碰到 `dayTexture / nightTexture / emissiveMap` 主链路；
- 会影响现有夜间城市灯稳定性；
- 会影响 ocean specular 与云层的可见性；
- fallback 和性能风险高；
- 不适合作为 cloudMesh 或 sky LUT 的顺手改动。

E3 施工条件见第 6.6 节。未满足前，E3 状态为：**暂缓，条件待定**。

### 7.7 E4：Earth Color Grading

目标：统一调整海洋蓝度、陆地对比度、云层亮度、大气光、夜景灯光，使地球主体形成完整风格。

前置条件：E1/E2/E3 至少部分稳定，否则调色对象不完整。

### 7.8 E5：Material System Upgrade

目标：评估 PBR / normalMap / bumpMap / displacementMap。

结论：不是近期目标。只有在 MeshPhongMaterial 的潜力基本用尽，且 PWA 性能预算允许时才评估。

---

## 8. Sky Visual System Roadmap

### 8.1 Sky P0：审计

状态：已完成基础审计。若后续进入完整 LUT 系统，必须复核以下事项：

- `renderer.outputColorSpace / outputEncoding`；
- `toneMapping / toneMappingExposure`；
- `Shader t` 的 K 值；
- DataTexture 格式；
- 星场 opacity 过渡；
- CSS fallback；
- `index.html` 自动流与按钮体系。

### 8.2 Sky P1A：skyMesh skeleton

状态：已完成并提交 `d5755be`。

### 8.3 Sky P1B：11 时段体系统一

目标：统一 `earth3d.js`、`index.html` 自动时间流、手动按钮、UI/CSS/3D 的时段体系。

状态：暂缓。不得和 E1 cloudMesh 同轮施工。

### 8.4 Sky P2：双 LUT + Star Opacity

目标：按附录 A 第 8.1–8.5 节实现天空双 LUT、GPU mix、星场透明度联动。

状态：暂缓。

### 8.5 Sky P3：OKLab / CSS fallback / Tone Mapping 标定

目标：按附录 A 第 8.4、8.6、10.2 节实现 OKLab 升级、CSS fallback 与曝光标定。

状态：暂缓。

### 8.6 Sky P4：Sky 与 Earth 统一调色

目标：在 cloud、rim glow、terminator 等系统稳定后统一 sky-earth 色彩。

状态：远期。

---

## 9. `goldenApproach` 与 `lateEvening` 视觉意图

本章是两个新增模式的正式验收依据。参数表只能说明“数值是否正确”，本章用于判断“画面是否符合预期”。后续 Codex 施工和人工验收不得只按参数通过，还必须对照本章的视觉意图判断是否拒收或返修。

### 9.1 `goldenApproach` / 暮前

`goldenApproach` 位于 `afternoon` 与 `sunset` 之间，对应日落前约一小时的暖金侧光。它不是落日橙红，也不是下午冷蓝，而是太阳高度降低后，地平线与大气边缘开始出现琥珀金调的过渡时段。

验收感受：

- 天空仍保留蓝色主体；
- 地平线开始偏暖；
- 地球表面有轻微暖化；
- 海面高光应低强度、偏暖；
- 不应出现强白色反光；
- 不应提前进入 sunset 的橙红 / 品红主导。

### 9.2 `lateEvening` / 入夜

`lateEvening` 位于 `evening` 与 `deepNight` 之间，对应蓝色时刻结束后的快速暗落。它比 `evening` 更暗、更冷，城市灯更突出，星场接近深夜但未完全满亮。

验收感受：

- 天空整体比 evening 更暗；
- 地平线仍保留微弱余辉；
- 城市灯比 evening 更突出；
- 星场接近 deepNight，但不应完全等同 deepNight；
- 它不是普通 `night`，也不是纯 `deepNight`。

---

## 10. 审计输出格式统一标准

所有 Phase / E 阶段审计必须输出固定 Markdown 表，至少包括：

| 审计项 | 当前值 | 目标值 | 是否符合 | 风险等级 | 是否允许施工 | 备注 |
|---|---|---|---|---|---|---|
| 示例 | 当前代码 / 当前资源 | 目标参数 / 目标行为 | 是/否 | 高/中/低 | 是/否 | 说明 |

审计报告末尾必须有：

```text
施工许可结论：允许 / 不允许
阻断项：...
可进入下一阶段的条件：...
RW 需要确认的关键结论：...
```

### 10.1 Phase 0 到 Phase 1 的结论传递方式

Sky Phase 0 是只读审计，不直接修改代码。其结论必须通过人工确认后传递给后续施工指令。

传递方式：

1. Codex 输出 Phase 0 审计报告；
2. RW 审阅并确认关键结论；
3. 将关键结论人工填入 Phase 1 指令；
4. Codex 按填入后的明确值施工；
5. 未填入明确值时，不得执行 Phase 1。

关键结论表：

| 结论项 | Phase 0 输出 | RW 确认值 | 是否写入 Phase 1 指令 |
|---|---|---|---|
| Shader t K 值 | 如 `K=1` 或 `K=0.5` | 待填 | 否 |
| DataTexture 格式 | 如 `RGBAFormat + UnsignedByteType` | 待填 | 否 |
| 是否启用 toneMapping | 是/否 | 待填 | 否 |
| 是否修改 exposure | 是/否 | 待填 | 否 |
| 星场 opacity 是否插值 | 插值/直接设置 | 待填 | 否 |
| 是否修改 index.html | 是/否 | 待填 | 否 |
| 是否存在高风险阻断项 | 是/否 | 待填 | 否 |

只有“RW 确认值”全部明确后，Phase 1 施工才可解锁。

---

## 11. 近期执行顺序

### 11.1 Step 1：验收 E0.1

在浏览器控制台依次执行：

```js
window.earth3d.setTimeOfDay('morning')
window.earth3d.setTimeOfDay('noon')
window.earth3d.setTimeOfDay('afternoon')
window.earth3d.setTimeOfDay('goldenApproach')
window.earth3d.setTimeOfDay('lateEvening')
window.earth3d.setTimeOfDay('deepNight')
```

判断：

- 海洋是否略微更有层次；
- noon 是否没有过曝；
- goldenApproach 是否没有变脏、变塑料；
- 夜间城市灯是否没受影响；
- skyMesh 是否没受影响。

### 11.2 Step 2：提交 E0.1

如果 E0.1 通过：

```bash
git add pwa/earth3d.js
git commit -m "Refine ocean specular visibility for daytime themes"
```

### 11.3 Step 3：执行 E0.1 基线存档子步骤

提交后立即执行 E0.2，不进入新施工。截图和性能基线完成后，方可进入 E1 审计。

强制输出位置：

```text
~/Projects/RodiO/docs/baselines/v0.2/
```

强制文件命名：

```text
[themeKey]_[commitHash]_[platform]_[resolution].png
```

示例：

```text
goldenApproach_d5755be_desktop_1920x1080.png
lateEvening_d5755be_mobile_375x812.png
```

同目录下必须保存 `debug-state/[themeKey]_[commitHash].json` 与 `notes.md`，记录人工判断、设备、浏览器、viewport、是否过曝、是否塑料感、是否遮挡。

### 11.4 Step 4：进入 E1 Cloud Layer Foundation 审计

E1 先审计资源与透明排序，不施工。审计通过后再生成最小施工指令。

---

## 12. 明确禁止事项

近期不得：

1. 不得在 E0.1 中继续提高 specular 到亮白；
2. 不得将 E0.1 扩大成 PBR 改造；
3. 不得在 E1 中顺手做 terminator；
4. 不得在 E1 中改 day/night 主材质；
5. 不得在 E2 中直接重写 atmosphere，优先审计独立 rimGlowMesh；
6. 不得在 Sky Phase 2 前跳过 Phase 0 复核；
7. 不得同时修改 `index.html`、`earth3d.js`、资源文件和播放器；
8. 不得把 sky LUT、cloudMesh、rimGlow、terminator 混在一个 commit；
9. 不得使用 `~/Projects/RodiO_old_unused`；
10. 不得在工作树不 clean 时继续施工。

---

## 13. 资源清单模板与路径约定

任何涉及新增或替换纹理资源的阶段，必须先提交资源清单。没有资源清单，不得施工。

| 资源用途 | 期望路径 | 当前状态 | 尺寸 | 格式 | 压缩方式 | 显存估算 | fallback |
|---|---|---|---|---|---|---|---|
| dayTexture | `pwa/assets/earth_day_8k.jpg` | 已接入 | 待实测 | JPEG | 无 | 待按实际尺寸计算 | `pwa/assets/bluemarble.jpg` |
| nightTexture | `pwa/assets/earth_night_8k.jpg` | 已接入 | 待实测 | JPEG | 无 | 待按实际尺寸计算 | `pwa/assets/blackmarble.jpg` |
| oceanSpecular 4K | `pwa/assets/earth/masks/ocean_specular_4096x2048.png` | 已接入 | 4096×2048 | PNG mask | 无 | 约 32MB RGBA / 实际以浏览器解码为准 | 2K mask |
| oceanSpecular 2K | `pwa/assets/earth/masks/ocean_specular_2048x1024.png` | 已接入 | 2048×1024 | PNG mask | 无 | 约 8MB RGBA / 实际以浏览器解码为准 | null |
| cloudAlphaMap 4K | 待定 | 待审计 | 4096×2048 | 灰度 alpha mask 优先 | 待定 | 待估算 | 2K / 关闭 cloudMesh |
| cloudAlphaMap 2K | 待定 | 待审计 | 2048×1024 | 灰度 alpha mask 优先 | 待定 | 待估算 | 关闭 cloudMesh |

显存口径说明：所谓“8K 地球纹理”必须写明实际尺寸。常见等距圆柱地球贴图为 `8192×4096`，未压缩 RGBA 约 128MB；若为 `8192×8192` 正方纹理，未压缩 RGBA 约 256MB。文档和验收不得只写“8K”，必须写实际像素尺寸。

## 14. 总体验收标准

| 类别 | 验收项 | 标准 |
|---|---|---|
| 架构 | 分层 | `earth / cloud / atmosphere-rim / sky / stars` 各层职责清晰 |
| 架构 | 可回退 | sky/cloud/rimGlow 等新增层均可关闭 |
| 架构 | 时段 | 11 个时段均有明确视觉意图和参数来源 |
| 架构 | 审计 | 每阶段施工前有固定格式审计报告 |
| 视觉 | 海洋 | 正午海洋有轻微镜面高光，陆地无明显错误高光 |
| 视觉 | 云层 | 云层可见，有透明感和漂浮感，不遮挡城市灯 |
| 视觉 | 大气 | 地球边缘蓝白/暖色光晕清晰，但不过曝 |
| 视觉 | 昼夜 | terminator 阶段完成后，日夜交界柔和，城市灯只在暗部突出 |
| 视觉 | 天空 | sky LUT 阶段完成后，11 时段天空与地球色温协调 |
| 性能 | 桌面 | 以 E0.2 基线为对照，不低于基线 85% |
| 性能 | 移动端 | 主流移动端 ≥30fps，低端可降级 |
| 回归 | 不破坏 | 播放器、fallback、定位、城市灯、specularMap 不受非相关阶段影响 |

---


## 15. 当前代码基线与附录 A 蓝图差异表

本章用于解决“当前真实代码状态”和“附录 A 完整蓝图”之间的差异管理。附录 A 是目标规范，不等于当前代码已经达到该状态。Codex 施工前必须先确认本表，避免错误地把蓝图参数当成当前基线，或把试探值误认为永久标准。

| 模块 | 当前代码状态 | 附录 A 目标状态 | 是否接受差异 | 何时收敛 |
|---|---|---|---|---|
| skyMesh | 已完成最小 skeleton，`renderOrder = -1000`，纯 shader 渐变，无 LUT | 附录 A 目标为 skyMesh + 双 LUT + GPU `mix()`，统一 `renderOrder = -1000` | 接受 | Sky P2 双 LUT 阶段收敛；`renderOrder` 以当前 `-1000` 为优先基线 |
| `goldenApproach / lateEvening` | `earth3d.js` 已预留，可通过控制台调试 | 11 时段完整端到端体系，包括按钮、自动流、fallback、sky stops、star opacity | 接受 | Sky P1B-0 审计后逐步接入 |
| ocean specular 参数 | E0.1 使用当前试探值：`morning 0x06090f/1.05`、`noon 0x091018/1.12`、`afternoon 0x05080d/0.96`、`goldenApproach 0x070503/0.68` | 附录 A 第 7.2 节为原始标准值 | 待验收 | E0.1 通过则成为当前运行基线；失败则回退附录 A |
| `shouldUseOceanSpecularMap` | 当前 E0.1 增加 `goldenApproach` | 附录 A 原文主要强调白天/海水高光分离 | 接受试探 | E0.1 截图确认后定稿 |
| `#app background` | 仍保留现有 CSS fallback 背景 | 附录 A Sky Phase 1 计划改为 `#06080F` | 接受 | 仅在 Sky fallback / LUT 阶段修改，不并入 E0.1 |
| `night` key | 当前存在兼容别名 | 正式 11 时段不包含额外 `night` | 临时接受 | 见第 17 章 Night Legacy Alias Policy |
| star opacity | 当前主要是直接赋值或未完整过渡 | 附录 A 第 6.4 节为完整 11 时段 opacity 表 | 接受 | Sky P2 纳入过渡系统 |
| atmosphere glow | 当前大气层仍为基础 atmosphere mesh | 附录 A 有 glowIntensity / glowColor 参数表 | 接受 | E2 审计后决定独立 rimGlowMesh 或 sky shader 路径 |
| cloud layer | 当前不存在独立 cloudMesh | 附录 A 后续规划为独立 cloud mesh + LOD | 接受 | E1-0 资源决策后施工 |
| terminator | 当前不存在 day/night terminator shader | 目标质感需要 terminator | 接受暂缓 | E3 专项审计通过后才允许施工 |

**执行规则**：本表中“当前代码状态”是近期施工与回归测试的依据；“附录 A 目标状态”是远期收敛方向。任何 Codex 指令必须明确“本轮以当前代码基线为准”或“本轮开始向附录 A 收敛”，不得含糊。

---

## 16. Mode Integration Plan：`goldenApproach / lateEvening` 端到端接入

`goldenApproach` 与 `lateEvening` 是 v3.2 的关键新增时段，但当前只能视为结构占位。它们的真正完成标准不是“配置表里存在 key”，而是完成从渲染、交互、自动流、fallback 到验收基线的全链路闭环。

### 16.1 当前状态

| 环节 | `goldenApproach` | `lateEvening` | 结论 |
|---|---|---|---|
| `THEME_VISUAL_CONFIG` | 已存在 | 已存在 | 结构占位完成 |
| `setTimeOfDay()` | 可调试 | 可调试 | 可用于人工验收 |
| 自动时间流 | 未接入 | 未接入 | 未完成 |
| 手动按钮 | 未接入 | 未接入 | 未完成 |
| UI 主题插值 | 未接入 | 未接入 | 未完成 |
| CSS fallback | 未接入 | 未接入 | 未完成 |
| sky LUT/stops | 未入代码 | 未入代码 | 未完成 |
| star opacity 过渡 | 未完整联动 | 未完整联动 | 未完成 |
| baseline screenshot | 未完成 | 未完成 | 未完成 |

### 16.2 接入顺序

```text
Mode P0：端到端接入审计，不施工
Mode P1：earth3d.js 正式 11 key 与 night alias 策略收口
Mode P2：index.html 手动按钮接入或明确隐藏策略
Mode P3：自动时间流接入 11 key
Mode P4：UI / CSS fallback / sky LUT / star opacity 对齐
Mode P5：截图与 debugState 基线归档
```

### 16.3 当前禁止项

在 E0.1 未验收提交之前，不得修改 `index.html` 自动流、按钮体系、UI 主题插值或 CSS fallback。`goldenApproach / lateEvening` 当前只能通过控制台调试验证，不得混入 ocean specular 小改提交。

---

## 17. Night Legacy Alias Policy

当前 `THEME_VISUAL_CONFIG` 实际可能出现 12 个 key，其中 `night` 是历史兼容别名，不属于正式 11 时段模型。为避免后续验收反复争议，统一策略如下。

| 项目 | 决策 |
|---|---|
| `night` 是否是正式时段 | 否 |
| `night` 的身份 | legacy alias / 兼容旧逻辑入口 |
| 新增配置是否继续写 `night` | 否，新增参数必须写入 `deepNight` 或 `lateEvening` |
| `night` 是否立即删除 | 不立即删除，避免旧调用断裂 |
| 长期方向 | 完成 11 时段端到端接入后，评估将 `night` 映射到 `deepNight` 或逐步废弃 |

**推荐实现方向**：短期保留 `night`，但在文档和 debugState 中标记为 legacy alias。所有新视觉参数、sky stops、star opacity、自动时间流均以正式 11 时段为准。

---

## 18. Cloud Asset Decision：云层资源前置决策

E1 Cloud Layer Foundation 不得直接施工 cloudMesh。必须先完成 E1-0 Cloud Asset Decision，确认资源存在、合法、格式、尺寸、显存预算与 fallback。

### 18.1 必须确认的问题

| 问题 | 决策要求 |
|---|---|
| 是否已有 cloud texture | 通过 `pwa/assets` 实际审计确认，不得假设 |
| 资源格式 | 优先灰度 `alphaMap` / 单通道 mask，避免依赖 RGBA 透明贴图 |
| 资源尺寸 | 至少规划 2K / 4K 两级；低端设备可关闭 cloudMesh |
| 文件路径 | 施工前确定并写入资源清单，不得硬编码临时路径 |
| 授权与来源 | 必须可用于项目，不得使用来源不明资源 |
| 移动端策略 | 低端设备默认关闭或使用低清 alphaMap |
| fallback | 加载失败时不影响 earth / sky / atmosphere / player |

### 18.2 推荐路径占位

| 资源 | 推荐路径 | 状态 |
|---|---|---|
| cloudAlphaMap 4K | `pwa/assets/earth/clouds/cloud_alpha_4096x2048.png` | 待确认 |
| cloudAlphaMap 2K | `pwa/assets/earth/clouds/cloud_alpha_2048x1024.png` | 待确认 |

以上路径只是建议，不得在资源审计前写入代码。

---

## 19. Visual Baseline Archive Directory

E0.1 验收通过并提交后，必须立即建立视觉基线存档。此步骤不是新施工，而是为后续视觉对比提供证据链。

推荐目录结构：

```text
docs/baselines/
  v0.2/
    screenshots/
      desktop/
      mobile/
    debug-state/
    notes.md
```

每次截图必须记录：

| 字段 | 要求 |
|---|---|
| `themeKey` | 如 `morning / noon / afternoon / goldenApproach / lateEvening / deepNight` |
| `viewport` | 如 `1920x1080`、`375x812` |
| `device` | Desktop / Mobile / browser profile |
| `commitHash` | 当前提交 hash |
| `debugState` | `window.earth3d.getDebugState()` 输出 |
| `screenshot` | 按命名规范保存 |
| `人工判断` | 是否通过、是否有过曝/塑料感/遮挡 |

截图命名建议：

```text
RodiO_V0.2_Baseline_[ThemeKey]_[Platform]_[Resolution].png
```

示例：

```text
RodiO_V0.2_Baseline_goldenApproach_Desktop_1920x1080.png
```

---

## 20. Global Freeze List before E1 Completion

在 E1 完成之前，以下事项全局冻结。除非 RW 明确解锁，不得写入任何 Codex 施工指令。

1. 不做 PBR / `MeshStandardMaterial` / `roughnessMap`；
2. 不做 terminator / day-night shader mix / city lights dark-side blend；
3. 不修改播放器；
4. 不修改 service worker；
5. 不修改 `index.html` 自动时间流，除非进入 Sky P1B；
6. 不修改 `#app background`，除非进入 Sky fallback / LUT 阶段；
7. 不修改 camera / `earthGroup` / `VISUAL_TARGET_NDC`；
8. 不新增 4K / 8K 资源，除非完成资源审计；
9. 不把 ocean specular、cloudMesh、rimGlow、sky LUT 混在一个 commit；
10. 不使用 `~/Projects/RodiO_old_unused`；
11. 不在工作树不 clean 时继续任何新阶段；
12. 不把 `goldenApproach / lateEvening` 的端到端接入混入 E0.1；
13. 不把 `night` 当作正式第 12 时段继续扩展。

---

## 21. 最终结论

1. 当前 E0.1 ocean specular 小改可以验收，但不要把它当成目标图质感的主线；E0.1 未提交前不得进入 E1 或 Sky 后续施工。
2. 真正通向参考图质感的路线是 E1 cloudMesh、E2 atmosphere rim glow、E3 terminator。
3. E3 terminator 是核心目标，但必须暂缓，不能顺手施工。
4. Sky Visual System v3.2 的完整色彩与 LUT 架构已经作为附录 A 纳入本文件；后续施工以附录 A 为唯一色彩来源。
5. `goldenApproach / lateEvening` 目前只是结构占位，尚未完成自动流、按钮、UI、fallback、sky LUT 的端到端接入。
6. `night` 是 legacy alias，不是正式第 12 时段。
7. 下一步推荐顺序：验收 E0.1 → commit → E0.1 基线存档 → E1-0 Cloud Asset Decision 审计。

---

# 附录 A：`rodio_sky_design_v3_2.md` 全量整合文本

> ⚠️ **附录 A 执行优先级与编号说明**  
> 附录 A 是 Sky Visual System 的完整蓝图与设计规范，不是当前立即施工指令。当前执行仍以主文第 3 章和第 11 章为准。附录 A 内所有章节统一记为 `A.x`，例如 `A.6.2`、`A.8.1`、`A.9`。附录 A 内部若出现“第六章 / 第八章 / 第九章”等旧称，均按本版修正为“附录 A 第 6 节 / 第 8 节 / 第 9 节”。

> ⚠️ **附录 A 执行优先级警告**
>
> 本附录是 Sky Visual System v3.2 的完整蓝图和参数规范，不等于当前立即施工范围。附录 A 中的 Phase 0/1/2/3/4 是原始大版本实施计划，现已被主文第 3 章的阶段映射表拆分管理。Codex 不得直接复制附录 A Phase 1 作为当前任务。当前执行顺序以主文第 11 章为准。
>
> 如果附录 A 与主文发生冲突，执行优先级为：**当前 git 基线 / 已验收 commit > 主文近期执行顺序 > 主文阶段映射表 > 附录 A 设计规范 > 附录 A 原始施工指令**。

> 以下内容为 `rodio_sky_design_v3_2.md` 的完整整合版本，作为 Sky Visual System 的权威参考。主文中涉及 sky stops、双 LUT、DataTexture、星场透明度、CSS fallback、Tone Mapping、显存预算、大气光晕参数等内容时，均以本附录为准。

## A.0 RodiO 天空视觉系统设计文档（v3.2 原始设计规范）

**版本** v3.2  
**日期** 2026-06-01  
**作者** RW + 苏衡  
**关联项目** RodiO PWA · GitHub: Heyyeqi/RodiO  
**本版变更**（相对 v3.1）
- 过渡机制从"CPU 端每帧插值 + 单 LUT 上传"改为"双 LUT + GPU 端 mix()"，消除每帧纹理上传
- DataTexture 格式从 RGBFormat 改为 RGBAFormat（RGBFormat 在 Three.js r137+ 废弃）
- 显存预算从单一 200MB 改为分级预算（移动端 128MB / 桌面端 512MB，8K 纹理必须压缩）
- Shader t 值从 worldPosition.y 改为基于 viewDir（修正相机偏移时渐变方向错误的问题）
- LUT 生成从 Catmull-Rom 改为按 pos 线性采样（消除 overshoot 风险，逻辑更简单）
- CSS 降级补充 OKLab 语法
- Tone Mapping exposure 标注为初始标定值，标注微调范围

---

## A.1 背景与起点

RodiO 是一个宇宙电台 PWA，核心视觉是一个 Three.js 驱动的 3D 地球背景层。整个界面的情绪基调由"此刻是几点、此刻在哪里"决定。

**天空不是装饰，是叙事的一部分。**

当前版本（截至 2026-06-01）已实现：

- 基于用户地理位置的地球朝向（quaternion 定位，上海为默认锚点）
- 9 个时段的主题切换（本版扩展为 11 个）
- 地球昼夜纹理混合（NASA Blue Marble 8K 日图 + Black Marble 夜图）
- 城市灯光 emissive 层，随时段淡入淡出
- 星场粒子系统（1200 点，程序化生成）
- 大气层半透明球壳（BackSide MeshPhongMaterial）

---

## A.2 当前问题诊断

### 2.1 天空色与地球光照脱节（核心问题）

```
index.html #app { background: linear-gradient(...) }   ← CSS 静态，不感知时段
earth3d.js THEME_VISUAL_CONFIG                         ← Three.js 动态，控制地球
```

两套系统互不感知。代码定位：`index.html` 第 63–67 行，`#app` 的 `background` 属性。

### 2.2 时段分布不均

原有 9 个时段中：
- 下午（14:00–17:00）跨越三小时只有一段，错过了 16:00 后侧光质感显现的"暮前"节点
- 夜晚（19:00–22:00）跨越三小时只有一段，错过了蓝色时刻结束后天空快速暗落的"入夜"节点

### 2.3 城市灯光色调单一

所有时段 emissiveColor 均在 `#ffbe63`–`#ffd08a` 的琥珀黄范围内，没有变化。真实城市灯光在不同背景亮度下的感知色温不同，这种差异可以通过 emissiveColor 微调来模拟。

### 2.4 其余问题

- 天空渐变锚点不足，RGB 插值在互补色区间经过泥灰区
- 星场透明度未与天空系统联动
- 大气边缘光晕缺失
- 地球纹理缺少云层和海水高光分离

---

## A.3 设计目标

> 对真实世界的诗意展示。

**真实**：天空颜色来自大气光学物理，不是主观选色。  
**诗意**：提炼了真实之后的美化版本，色彩更干净，渐变更顺滑，但不偏离真实色相方向。

**边界声明**：本方案色值基于典型晴天条件下中纬度（30°–50°N）春秋分、人眼视觉记忆与摄影参考的加权提炼，非辐射度计实测数据。所有色值标注为 **sRGB 8-bit**。

---

## A.4 物理基础

### 4.1 瑞利散射
天顶蓝（光路最短），地平线偏白（光路最长），正午天顶最蓝。

### 4.2 米氏散射
气溶胶（水汽、尘埃）产生白色/灰色雾化。下午积累了一天的尘埃，地平线比上午更白更暖。

### 4.3 太阳角度与橙色
日出/落日时橙色经过厚大气衰减后是掺了灰调的**赭石、赤陶、琥珀**，不是饱和铬橙。

### 4.4 品红过渡带
天顶深蓝与地平橙红之间的玫瑰洋红/品红，对应民用曙暮光时段。
- **日出品红带**：大气洁净，偏玫瑰色（HSL 色相约 330°–345°）
- **落日品红带**：气溶胶积累，偏紫调（HSL 色相约 310°–325°），域更宽更重

### 4.5 黄金时刻与侧光
太阳高度角约 10°–25° 时，色温约 2500–4000K，产生强烈侧向暖光。暮前（16:00–17:00）是"黄金时刻前的准备阶段"，地平线已有琥珀金黄。

### 4.6 航海曙暮光与星场渐显
太阳在地平线以下 6°–18° 时，天空蓝调亮度快速下降，星场从隐约可见转为清晰。入夜（20:30–22:00）对应这个时段。

### 4.7 城市灯光感知色温与背景亮度的关系
灯光本身光谱不随时间变化，但人眼对其色温的感知受背景亮度对比影响：
- **深夜/入夜**：背景最暗，对比最强，橙色感最突出 → emissive 用深橙金
- **夜晚（蓝色时刻）**：蓝调余辉仍在，灯光与天空有互补感 → emissive 用明亮暖橙
- **黎明**：天空开始亮起，灯光对比度降低 → emissive 用低饱和暖黄
- **日出**：灯光已非主角 → emissive 极低，偏冷的黄白

---

## A.5 11 时段完整序列

### 5.1 时段划分

```
22:00    04:00  05:15  06:45       09:00       11:30       14:00 16:00 17:00       19:00 20:30       22:00
  |        |      |      |           |           |            |     |     |           |     |           |
深夜     黎明   日出   清晨        上午        正午        下午  暮前  落日        夜晚  入夜        深夜
deepNight dawn sunrise earlyMorning morning     noon     afternoon golden sunset  evening lateEvening deepNight
                                                                   Approach
```

### 5.2 每个时段的独立性

| 时段 key | 中文 | 核心视觉特征 | 与前段的本质区别 |
|----------|------|------------|----------------|
| deepNight | 深夜 | 极深靛蓝，星场全亮，城市灯光主导 | — |
| dawn | 黎明 | 夜色主导，地平紫调隐约渗入 | 有曙光信号 |
| sunrise | 日出 | 橙蓝极差最大，品红带最鲜明 | 太阳出现，暖色主导地平 |
| earlyMorning | 清晨 | 冷蓝回归，低角度清冽感 | 橙色退场，蓝调接管 |
| morning | 上午 | 标准晴天蓝，均匀饱和 | 低角度感消失 |
| noon | 正午 | 天顶最深蓝，地平最白，最强纵深感 | 瑞利散射路径最短最纯 |
| afternoon | 下午 | 天顶微暖，地平黄绿白 | 方向感出现 |
| goldenApproach | 暮前 | 侧光金质感，暖调扩散至中层 | 橙调进入中层，影最长 |
| sunset | 落日 | 橙红主导，品红带宽重 | 暖色全面主导 |
| evening | 夜晚 | 蓝色时刻，均匀深蓝，无方向感 | 橙色消退，蓝调沉静 |
| lateEvening | 入夜 | 天空暗落，星场从隐约到清晰 | 蓝调亮度快速下降 |

---

## A.6 配色方案

### 6.1 设计原则

- 每段 8–12 个锚点，按时段色彩复杂度分配密度
- 方向：从天顶（0%）到地平线（100%）
- 锚点间感知色差（ΔE）：暗部时段控制在 3–5，亮部时段 5–8
- 所有色值为 sRGB 8-bit
- LUT 生成时在 sRGB 空间线性插值（Phase 1）；后续可升级为 OKLab（Phase 2）
- 时段过渡在 GPU 端用 `mix()` 完成（双 LUT 方案），不在 CPU 端做帧间插值

### 6.2 十一时段完整锚点

格式：`位置% — #色值 — 描述`，方向从天顶（0%）到地平线（100%）。

---

#### 深夜 deepNight · 22:00–04:00 · 8 锚点
极深靛蓝底，锚点间差距极小，天顶到地平线梯度几乎消失（趋近均质）。

```
  0%  #020308  天顶，极深靛，趋近纯黑
 14%  #030509
 28%  #04060C
 42%  #050810
 55%  #060A14
 67%  #080C18
 80%  #09101C
100%  #0B1220  地平，大气曲率蓝
```

---

#### 黎明 dawn · 04:00–05:15 · 9 锚点
夜色主导，紫调从地平渗入。整体极暗，层次在深靛和深靛紫之间。

```
  0%  #04050D  天顶，近黑，极深靛底
 14%  #08091A
 28%  #0E0F26
 40%  #130F30  蓝靛转紫，色相开始偏移
 52%  #1C1138
 63%  #261440
 74%  #2E1744
 85%  #351A47
100%  #3C1E4A  地平，紫红底，黎明信号
```

---

#### 日出 sunrise · 05:15–06:45 · 11 锚点
品红带（43%–53%）是核心，日出品红偏玫瑰调（色相 330°–345°）。地平线收在淡金暖白，非饱和橙。

```
  0%  #111830  天顶，普鲁士蓝
 11%  #1A1E42
 22%  #281C52  深靛带紫，向品红过渡
 33%  #432048  蓝紫交界
 43%  #622840  暗玫瑰（品红带关键锚点，日出偏玫瑰调）
 53%  #8C3A42  砖玫红
 62%  #A84E3C  赭红
 71%  #BE6038  赭橙
 80%  #C87038  琥珀橙
 90%  #CFA060  淡金
100%  #D4B87A  地平，暖金白
```

---

#### 清晨 earlyMorning · 06:45–09:00 · 9 锚点
橙色退场，冷调回归。地平线保留极淡冰蓝，整体轻盈、清冽。

```
  0%  #182E5C  天顶，钢蓝
 12%  #1E3A70
 25%  #264884
 37%  #345C98
 50%  #4A72AA  明蓝（中层）
 62%  #6A94C0
 74%  #90B4D4
 86%  #B4D0E8
100%  #D0E4F2  地平，极淡冰蓝
```

---

#### 上午 morning · 09:00–11:30 · 9 锚点
标准晴天，蓝度均匀饱和，地平线轻微雾白。

```
  0%  #123270  天顶，深钴蓝
 12%  #183E86
 25%  #1E4C98
 37%  #2860A8
 50%  #3E76B8  天蓝（中层）
 62%  #5A8EC8
 74%  #7AAAD8
 86%  #A0C4E4
100%  #C4DCF0  地平，浅雾白
```

---

#### 正午 noon · 11:30–14:00 · 9 锚点
天顶蓝全天最深，地平线最白，最强明度对比产生纵深感。

```
  0%  #0C2C68  天顶，最深钴蓝
 12%  #12387C
 25%  #1A4890
 37%  #245CA0
 50%  #3272B0  明蓝（中层）
 62%  #4E8CC4
 74%  #72A8D6
 86%  #A4C8E6
100%  #CCE2F4  地平，白蓝散射
```

---

#### 下午 afternoon · 14:00–16:00 · 8 锚点
天顶依然钴蓝，地平线染上极淡暖调（黄绿白），中等浑浊度条件下的真实色彩。

```
  0%  #12347A  天顶，钴蓝
 14%  #1A4490
 28%  #2C5CA4
 42%  #4478B8  天蓝（中层）
 56%  #6696C8
 70%  #8CB4D4
 85%  #B0CCD8  冷蓝白
100%  #D0DCC8  地平，黄绿白
```

---

#### ★ 暮前 goldenApproach · 16:00–17:00 · 10 锚点
黄金时刻前的准备阶段。天顶仍是蓝色但色相比下午偏暖 5°–8°，暖调从地平线向中层天空扩散。地平线的琥珀金黄是本时段最鲜明的标志。

与下午的区别：橙调进入中层（60% 以下明显）。  
与落日的区别：橙色尚未主导，品红带未出现。

```
  0%  #0F2E6E  天顶，偏暖的深蓝
 11%  #163680  暖蓝
 22%  #224A90  中蓝，微暖
 33%  #3862A4  天蓝偏暖
 44%  #5880B8  暖天蓝（中层，开始感知到暖）
 55%  #7EA0C8  蓝白偏暖
 66%  #A8BED0  暖蓝白（暖调开始主导）
 77%  #C8C8A8  黄白
 88%  #D4B880  琥珀白（侧光感）
100%  #DCC070  地平，暖金黄白
```

---

#### 落日 sunset · 17:00–19:00 · 12 锚点
品红带（40%–50%）偏紫调（色相 310°–325°），比日出更宽更重。整体偏赭石/赤陶。

```
  0%  #0C1A38  天顶，沉暮蓝
 10%  #141E48
 20%  #201840  蓝转靛紫
 30%  #36183E  深靛紫
 40%  #542238  暗玫瑰（品红带关键锚点，落日偏紫调）
 50%  #783040  砖玫红（比日出更宽的品红域）
 60%  #944038  赭红
 68%  #A85030  赭橙
 76%  #B86030  赤陶橙
 84%  #C07840  琥珀
 92%  #C89858  淡金
100%  #D0B070  地平，暖白金
```

---

#### 夜晚 evening · 19:00–20:30 · 8 锚点
蓝色时刻（Blue Hour）。天空均匀深蓝，无方向感，地平线保留极微弱大气余辉。

```
  0%  #060A18  天顶，深夜蓝
 14%  #080E22
 28%  #0C142E
 42%  #101C3A
 55%  #141E42
 67%  #182240
 80%  #1C2848
100%  #202C50  地平，大气余辉蓝
```

---

#### ★ 入夜 lateEvening · 20:30–22:00 · 10 锚点
航海曙暮光时段。蓝调亮度快速下降，星场从隐约可见转为清晰。

与夜晚的区别：整体明度低约 40%，但天顶到地平线的明度梯度仍保留（"尚未完全进入深夜"的关键视觉信号）。  
与深夜的区别：深夜这个梯度几乎消失，天空趋近均质。

```
  0%  #04070F  天顶，极深，介于深夜和夜晚之间
 11%  #060A18  深靛
 22%  #08101E  靛蓝
 33%  #0A1426  深海蓝
 44%  #0C1830  海军靛蓝
 55%  #0F1E3A  深蓝（中层）
 66%  #121E3C  蓝，比夜晚略暗
 77%  #142036  偏亮蓝
 88%  #182440
100%  #1C2A48  地平，大气余辉，比夜晚更暗的蓝
```

---

### 6.3 时段间过渡节奏

**过渡机制**：双 LUT + GPU 端 `mix()`（详见第八章 8.1 节）。

**双轨时序**：

| 过渡段 | 变化幅度 | 自动推进 | 用户交互 |
|--------|----------|---------|---------|
| 深夜 → 黎明 | 小 | 5s | 2s |
| 黎明 → 日出 | 中 | 7s | 3s |
| 日出 → 清晨 | 大（最剧烈） | 10s | 4s |
| 清晨 → 上午 | 小 | 3s | 1.5s |
| 上午 → 正午 | 极小 | 3s | 1.5s |
| 正午 → 下午 | 小 | 4s | 2s |
| 下午 → 暮前 | 中（暖调扩散） | 5s | 2.5s |
| 暮前 → 落日 | 中大（品红带出现） | 6s | 3s |
| 落日 → 夜晚 | 大 | 8s | 3s |
| 夜晚 → 入夜 | 中（快速压暗） | 5s | 2.5s |
| 入夜 → 深夜 | 小 | 4s | 2s |

### 6.4 星场透明度

| 时段 | opacity | 说明 |
|------|---------|------|
| deepNight | 1.00 | 完全可见 |
| lateEvening | 0.72 | 星场清晰，接近深夜 |
| evening | 0.45 | 星场隐约可见，蓝色时刻 |
| dawn | 0.38 | 微弱残留，黎明信号 |
| sunrise | 0.12 | 几乎不可见 |
| earlyMorning | 0.00 | 完全隐藏 |
| morning | 0.00 | — |
| noon | 0.00 | — |
| afternoon | 0.00 | — |
| goldenApproach | 0.00 | — |
| sunset | 0.15 | 刚刚出现，极弱 |

---

## A.7 地球视觉参数（完整 THEME_VISUAL_CONFIG）

### 7.1 城市灯光 emissiveColor 设计逻辑

| 阶段 | emissiveColor | 感知效果 |
|------|--------------|---------|
| 深夜/入夜 | `#ffbe63`–`#ffc068` 深橙金 | 背景最暗，对比最强，橙色感最突出 |
| 夜晚 | `#ffd08a` 明亮暖橙 | 蓝色时刻余辉与灯光产生互补感 |
| 黎明 | `#ffe0aa` 淡黄白 | 天空开始亮起，灯光对比度降低 |
| 日出/落日 | `#ffdca3`–`#ffd08a` 暖橙 | 灯光与天空暖调协调 |
| 白天 | 不使用（emissiveMap = null） | — |

### 7.2 完整时段参数表

---

#### deepNight（深夜）
```js
deepNight: {
  themeHour: 22.5,
  texture: {
    map: 'day', emissiveMap: 'night',
    mapColor: 0x02050B,
    emissiveColor: 0xffbe63,     // 深橙金，背景最暗时对比最强
    emissiveIntensity: 2.5,
    nightBaseIntensity: 0.58,
  },
  material: { specular: 0x000001, shininess: 0.08 },
  atmosphere: { color: '#0d2136', opacity: 0.16 },
  lighting: { ambient: 0.025, sun: 0.008, stars: 0.94, cityLightsOpacity: 0.58 },
}
```

#### dawn（黎明）
```js
dawn: {
  themeHour: 4.5,
  texture: {
    map: 'day', emissiveMap: 'night',
    mapColor: 0x667780,
    emissiveColor: 0xffe0aa,     // 淡黄白，天空亮起灯光对比降低
    emissiveIntensity: 0.72,
    nightBaseIntensity: 0.34,
  },
  material: { specular: 0x000102, shininess: 0.12 },
  atmosphere: { color: '#5f8fa9', opacity: 0.082 },
  lighting: { ambient: 0.032, sun: 0.18, stars: 0.55, cityLightsOpacity: 0.60 },
}
```

#### sunrise（日出）
```js
sunrise: {
  themeHour: 6.3,
  texture: {
    map: 'day', emissiveMap: 'night',
    mapColor: 0x96a6ae,
    emissiveColor: 0xffdca3,     // 暖橙，灯光与天空橙调协调
    emissiveIntensity: 0.46,
    nightBaseIntensity: 0.20,
  },
  material: { specular: 0x000102, shininess: 0.16 },
  atmosphere: { color: '#8ad0ff', opacity: 0.115 },
  lighting: { ambient: 0.055, sun: 0.48, stars: 0.24, cityLightsOpacity: 0.26 },
}
```

#### earlyMorning（清晨）
```js
earlyMorning: {
  themeHour: 7.4,
  texture: {
    map: 'day', emissiveMap: 'night',
    mapColor: 0xc3d1da,
    emissiveColor: 0xffddb0,
    emissiveIntensity: 0.10,
  },
  material: { specular: 0x020407, shininess: 0.55 },
  atmosphere: { color: '#8ecfff', opacity: 0.12 },
  lighting: { ambient: 0.052, sun: 0.72, stars: 0.12, cityLightsOpacity: 0.10 },
}
```

#### morning（上午）
```js
morning: {
  themeHour: 9.5,
  texture: {
    map: 'day', emissiveMap: null,
    mapColor: 0xffffff,
    emissiveColor: 0x000000, emissiveIntensity: 0,
  },
  material: { specular: 0x05070a, shininess: 1 },
  atmosphere: { color: '#88ccff', opacity: 0.15 },
  lighting: { ambient: 0.06, sun: 1.05, stars: 0.08, cityLightsOpacity: 0 },
}
```

#### noon（正午）
```js
noon: {
  themeHour: 13,
  texture: {
    map: 'day', emissiveMap: null,
    mapColor: 0xffffff,
    emissiveColor: 0x000000, emissiveIntensity: 0,
  },
  material: { specular: 0x05070a, shininess: 1 },
  atmosphere: { color: '#B7E3FF', opacity: 0.15 },
  lighting: { ambient: 0.09, sun: 1.25, stars: 0.02, cityLightsOpacity: 0 },
}
```

#### afternoon（下午）
```js
afternoon: {
  themeHour: 15.0,
  texture: {
    map: 'day', emissiveMap: null,
    mapColor: 0xf2f4f5,
    emissiveColor: 0x000000, emissiveIntensity: 0,
  },
  material: { specular: 0x04060a, shininess: 0.9 },
  atmosphere: { color: '#84bdf0', opacity: 0.14 },
  lighting: { ambient: 0.048, sun: 0.96, stars: 0.01, cityLightsOpacity: 0 },
}
```

#### ★ goldenApproach（暮前）
```js
goldenApproach: {
  themeHour: 16.5,
  texture: {
    map: 'day', emissiveMap: null,
    mapColor: 0xEEE8DC,          // 比下午更暖，侧光金质感
    emissiveColor: 0x000000, emissiveIntensity: 0,
  },
  material: { specular: 0x060402, shininess: 0.75 },
  atmosphere: {
    color: '#C0A878',            // ★ 大气壳偏金暖色，而非蓝白
                                 // 模拟低角度侧光散射进入大气层边缘的暖调
    opacity: 0.10,
  },
  lighting: { ambient: 0.052, sun: 0.88, stars: 0.00, cityLightsOpacity: 0 },
}
```

**设计说明**：
- `mapColor: 0xEEE8DC`：比下午（0xf2f4f5 冷白）明显偏暖，模拟低角度金色侧光打在地球表面的整体暖化
- `atmosphere.color: '#C0A878'`：暮前最重要的地球视觉特征——大气壳偏向琥珀金，与天空地平线锚点色（`#DCC070`）形成协调
- `shininess: 0.75`：比正午低，侧光条件下镜面反射角度不佳

#### sunset（落日）
```js
sunset: {
  themeHour: 18.2,
  texture: {
    map: 'day', emissiveMap: 'night',
    mapColor: 0xb4c2cb,
    emissiveColor: 0xffd08a,     // 明亮暖橙，灯光刚刚点亮
    emissiveIntensity: 0.16,
  },
  material: { specular: 0x000102, shininess: 0.18 },
  atmosphere: { color: '#6a9fd1', opacity: 0.075 },
  lighting: { ambient: 0.046, sun: 0.40, stars: 0.34, cityLightsOpacity: 0.18 },
}
```

#### evening（夜晚）
```js
evening: {
  themeHour: 20.0,
  texture: {
    map: 'day', emissiveMap: 'night',
    mapColor: 0x050912,
    emissiveColor: 0xffd08a,     // 明亮暖橙，蓝色时刻灯光与蓝天产生互补
    emissiveIntensity: 2.2,
  },
  material: { specular: 0x000102, shininess: 0.10 },
  atmosphere: { color: '#203750', opacity: 0.18 },
  lighting: { ambient: 0.06, sun: 0.04, stars: 0.78, cityLightsOpacity: 0.58 },
}
```

#### ★ lateEvening（入夜）
```js
lateEvening: {
  themeHour: 21.0,
  texture: {
    map: 'day', emissiveMap: 'night',
    mapColor: 0x030710,          // 比 evening 更暗，地球表面几乎全黑
    emissiveColor: 0xffc068,     // 比 evening 略深的橙金，背景更暗对比更强
    emissiveIntensity: 2.35,
  },
  material: { specular: 0x000102, shininess: 0.09 },
  atmosphere: { color: '#162840', opacity: 0.17 },
  lighting: { ambient: 0.038, sun: 0.015, stars: 0.72, cityLightsOpacity: 0.58 },
}
```

**设计说明**：
- `mapColor: 0x030710`：比夜晚（0x050912）更暗，城市灯光相对亮度更突出
- `emissiveColor: 0xffc068`：比夜晚（0xffd08a）更深橙金，模拟背景最暗时灯光感知最橙
- `atmosphere.color: '#162840'`：比夜晚（#203750）更深，为深夜做视觉铺垫

### 7.3 参数对比一览

| 时段 | mapColor | emissiveColor | emissiveIntensity | atm color | sun | cityLights |
|------|----------|--------------|-------------------|-----------|-----|-----------|
| deepNight | 0x02050B | 0xffbe63 | 2.5 | #0d2136 | 0.008 | 0.58 |
| dawn | 0x667780 | 0xffe0aa | 0.72 | #5f8fa9 | 0.18 | 0.60 |
| sunrise | 0x96a6ae | 0xffdca3 | 0.46 | #8ad0ff | 0.48 | 0.26 |
| earlyMorning | 0xc3d1da | 0xffddb0 | 0.10 | #8ecfff | 0.72 | 0.10 |
| morning | 0xffffff | — | 0 | #88ccff | 1.05 | 0 |
| noon | 0xffffff | — | 0 | #B7E3FF | 1.25 | 0 |
| afternoon | 0xf2f4f5 | — | 0 | #84bdf0 | 0.96 | 0 |
| **goldenApproach** | **0xEEE8DC** | **—** | **0** | **#C0A878** | **0.88** | **0** |
| sunset | 0xb4c2cb | 0xffd08a | 0.16 | #6a9fd1 | 0.40 | 0.18 |
| evening | 0x050912 | 0xffd08a | 2.2 | #203750 | 0.04 | 0.58 |
| **lateEvening** | **0x030710** | **0xffc068** | **2.35** | **#162840** | **0.015** | **0.58** |

---

## A.8 实现架构

### 8.1 天空球 + 双 LUT 过渡方案

**核心设计**：双 LUT（skyLUTCurrent / skyLUTNext）+ GPU 端 `mix()`。

时段切换时：
1. 把当前 LUT 复制为 Current（或直接保留引用）
2. 生成新时段的 LUT 为 Next，**一次性上传至 GPU**
3. 重置 `mixRatio = 0`，开始按过渡时长递增至 1.0
4. 每帧只更新 `mixRatio` 这一个 float uniform，**不再每帧上传纹理**

这彻底消除了"10s 过渡 = 600 帧连续纹理上传"的问题。

```js
// 天空球材质
const skyMaterial = new THREE.ShaderMaterial({
  side: THREE.BackSide,
  depthWrite: false,
  depthTest: false,
  uniforms: {
    skyLUTCurrent: { value: null },   // 当前时段 LUT
    skyLUTNext:    { value: null },   // 目标时段 LUT
    mixRatio:      { value: 0.0 },    // 过渡进度 0→1
    glowIntensity: { value: 0.0 },    // Phase 2 激活
    glowColor:     { value: new THREE.Color(0.6, 0.8, 1.0) },
  },
  vertexShader: `
    varying vec3 vWorldPosition;
    void main() {
      vWorldPosition = (modelMatrix * vec4(position, 1.0)).xyz;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D skyLUTCurrent;
    uniform sampler2D skyLUTNext;
    uniform float mixRatio;
    uniform float glowIntensity;
    uniform vec3 glowColor;
    varying vec3 vWorldPosition;

    void main() {
      // ★ 基于视线方向计算 t（修正相机偏移时渐变方向错误的问题）
      // viewDir 从相机指向天空片元，y 分量对应"仰角"，与相机位置无关
      vec3 viewDir = normalize(vWorldPosition - cameraPosition);
      float t = clamp(1.0 - viewDir.y, 0.0, 1.0);
      // t = 0：天顶（对应锚点 0%）
      // t = 1：地平线（对应锚点 100%）
      // 注：若 Phase 0 审计发现上述映射在当前相机视角下
      // 导致渐变比例不理想，可调整为：
      // float t = clamp((1.0 - viewDir.y) * 0.5, 0.0, 1.0);
      // 由 Phase 0 审计报告最终确认使用哪个版本

      // 从双 LUT 采样并在 GPU 端混合
      vec3 colorA = texture2D(skyLUTCurrent, vec2(t, 0.5)).rgb;
      vec3 colorB = texture2D(skyLUTNext,    vec2(t, 0.5)).rgb;
      vec3 color  = mix(colorA, colorB, mixRatio);

      // Fresnel 大气边缘光晕（Phase 2 激活，Phase 1 中 glowIntensity = 0）
      vec3 sphereNormal = normalize(vWorldPosition);
      float fresnel = pow(1.0 - abs(dot(normalize(-viewDir), sphereNormal)), 3.0);
      vec3 horizonColor = mix(
        texture2D(skyLUTCurrent, vec2(0.85, 0.5)).rgb,
        texture2D(skyLUTNext,    vec2(0.85, 0.5)).rgb,
        mixRatio
      );
      color += mix(glowColor, horizonColor, 0.35) * fresnel * glowIntensity;

      gl_FragColor = vec4(color, 1.0);
    }
  `
})

// 注：Three.js ShaderMaterial 通常提供内置 cameraPosition uniform；若当前 r128 环境下编译失败，
// 不得硬猜，应在 Phase 0 复核中确认是否需要显式声明/更新 cameraPosition。

const skyMesh = new THREE.Mesh(
  new THREE.SphereGeometry(500, 32, 32),
  skyMaterial
)
skyMesh.renderOrder = -1000
scene.add(skyMesh)  // 不加入 earthGroup
```

### 8.2 LUT 生成函数

**格式：RGBA + UnsignedByteType**（RGBFormat 在 Three.js r137+ 废弃，r152+ 已移除）

LUT 生成采用**按 pos 线性采样**，不用 Catmull-Rom（消除 overshoot 风险）：

```js
function buildSkyLUT(stops) {
  // stops: [{ pos: 0.0–1.0, hex: '#xxxxxx' }, ...]，已按 pos 升序排列
  const SIZE = 16
  const data = new Uint8Array(SIZE * 4)  // RGBA，第 4 通道固定为 255

  for (let i = 0; i < SIZE; i++) {
    const t = i / (SIZE - 1)

    // 找到 t 所在的锚点区间（线性插值，无 overshoot）
    let lo = stops[0]
    let hi = stops[stops.length - 1]
    for (let j = 0; j < stops.length - 1; j++) {
      if (t >= stops[j].pos && t <= stops[j + 1].pos) {
        lo = stops[j]
        hi = stops[j + 1]
        break
      }
    }

    const span = hi.pos - lo.pos
    const alpha = span < 1e-6 ? 0 : (t - lo.pos) / span

    const loRGB = hexToLinearRGB(lo.hex)
    const hiRGB = hexToLinearRGB(hi.hex)

    // 在 linear RGB 空间插值（Phase 1）
    // Phase 2 可升级为：先转 OKLab，插值，再转回 linear RGB
    data[i * 4 + 0] = Math.round((loRGB[0] + (hiRGB[0] - loRGB[0]) * alpha) * 255)
    data[i * 4 + 1] = Math.round((loRGB[1] + (hiRGB[1] - loRGB[1]) * alpha) * 255)
    data[i * 4 + 2] = Math.round((loRGB[2] + (hiRGB[2] - loRGB[2]) * alpha) * 255)
    data[i * 4 + 3] = 255
  }

  const texture = new THREE.DataTexture(
    data, SIZE, 1,
    THREE.RGBAFormat,           // ★ 不用 RGBFormat（已废弃）
    THREE.UnsignedByteType      // ★ 不用 FloatType（移动端兼容优先）
  )
  texture.minFilter = THREE.LinearFilter
  texture.magFilter = THREE.LinearFilter
  texture.needsUpdate = true
  return texture
}

function sRGBToLinear(c) {
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
}

function hexToLinearRGB(hex) {
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255
  return [sRGBToLinear(r), sRGBToLinear(g), sRGBToLinear(b)]
}
```

### 8.3 时段切换逻辑

```js
let skyTransitionStart = null
let skyTransitionDuration = 3000  // ms，按时段配置

function startSkyTransition(nextThemeKey, triggerType = 'auto') {
  const config = THEME_VISUAL_CONFIG[nextThemeKey]
  if (!config?.sky) return

  // 生成目标 LUT
  const nextLUT = buildSkyLUT(config.sky.stops)

  // 当前 LUT 升级为 Current（如果已有 Next，先把 Next 变成 Current）
  const currentLUT = skyMaterial.uniforms.skyLUTNext.value
    || skyMaterial.uniforms.skyLUTCurrent.value

  // 释放旧的 Current
  if (skyMaterial.uniforms.skyLUTCurrent.value &&
      skyMaterial.uniforms.skyLUTCurrent.value !== currentLUT) {
    skyMaterial.uniforms.skyLUTCurrent.value.dispose()
  }

  skyMaterial.uniforms.skyLUTCurrent.value = currentLUT
  skyMaterial.uniforms.skyLUTNext.value    = nextLUT
  skyMaterial.uniforms.mixRatio.value      = 0.0

  // 按触发类型选择过渡时长
  const dur = config.sky.transitionDuration
  skyTransitionDuration = triggerType === 'interactive'
    ? dur.interactive
    : dur.auto
  skyTransitionStart = performance.now()
}

// 在 renderer.setAnimationLoop 回调中每帧调用
function tickSkyTransition() {
  if (skyTransitionStart === null) return
  const elapsed = performance.now() - skyTransitionStart
  const progress = Math.min(elapsed / skyTransitionDuration, 1.0)
  // ease-in-out cubic
  const eased = progress < 0.5
    ? 4 * progress * progress * progress
    : 1 - Math.pow(-2 * progress + 2, 3) / 2
  skyMaterial.uniforms.mixRatio.value = eased
  if (progress >= 1.0) skyTransitionStart = null
}
```

### 8.4 色彩空间与 Tone Mapping

注：以下 exposure 表仅在 Phase 2 / Sky P3 的 OKLab 升级与曝光联动阶段生效。Phase 1 / Sky P2 不得动态修改 `toneMappingExposure`。

- 所有 HEX 为 sRGB 8-bit，LUT 生成时转为 linear RGB（`Math.pow(v, 2.2)`）
- `renderer.outputColorSpace = THREE.SRGBColorSpace`（r152+，已有）
- `renderer.toneMapping = THREE.ACESFilmicToneMapping`（Phase 1 设置）
- **Phase 1：`renderer.toneMappingExposure` 保持现有值不变，不按时段动态修改**
- **Phase 2 起**：按时段动态调整 exposure（初始标定值，部署后根据目标显示设备微调）

| 时段 | exposure 初始标定值 | 可调范围 |
|------|-------------------|---------|
| deepNight | 0.45 | 0.30–0.60 |
| lateEvening | 0.50 | 0.35–0.65 |
| evening | 0.55 | 0.40–0.70 |
| dawn | 0.60 | 0.45–0.75 |
| sunrise | 0.80 | 0.65–0.95 |
| earlyMorning | 0.92 | 0.75–1.10 |
| morning | 1.05 | 0.90–1.20 |
| noon | 1.20 | 1.00–1.50 |
| afternoon | 1.10 | 0.95–1.35 |
| goldenApproach | 0.88 | 0.70–1.05 |
| sunset | 0.80 | 0.65–0.95 |

### 8.5 星场透明度实现策略

**优先接入现有主题过渡插值系统**，将 star opacity 作为过渡参数之一，与 emissive、atmosphere 等同步插值。

若现有架构暂不支持完整主题插值，Phase 1 最低要求也应实现简易 lerp；直接设置目标值只允许作为临时调试 fallback，不得作为验收最终形态。参考目标值：

```js
const STAR_OPACITY_MAP = {
  deepNight: 1.00, lateEvening: 0.72, evening: 0.45,
  dawn: 0.38, sunrise: 0.12, earlyMorning: 0.00,
  morning: 0.00, noon: 0.00, afternoon: 0.00,
  goldenApproach: 0.00, sunset: 0.15,
}
if (stars?.material) {
  stars.material.opacity = STAR_OPACITY_MAP[resolvedTheme] ?? 0
  stars.material.needsUpdate = true
}
```

Phase 1 / Sky P2 验收标准应逐步升级为“星场随时段平滑过渡”，不得长期停留在 hard cut。

### 8.6 CSS 降级方案

WebGL 不可用时，取该时段 sky.stops 中最接近 0%/25%/50%/75%/100% 的 5 个关键锚点，生成渐变字符串写入 `appEl.style.background`。

优先使用 OKLab 语法（现代浏览器已支持），同时保留 sRGB fallback：

```js
function applyCssFallbackSky(themeKey) {
  const stops = THEME_VISUAL_CONFIG[themeKey]?.sky?.stops
  if (!stops) return

  const targets = [0, 0.25, 0.5, 0.75, 1.0]
  const keyStops = targets.map(target => {
    return stops.reduce((prev, curr) =>
      Math.abs(curr.pos - target) < Math.abs(prev.pos - target) ? curr : prev
    )
  })

  const colorList = keyStops.map((s, i) => `${s.hex} ${(i / 4 * 100).toFixed(0)}%`).join(', ')

  // 优先 OKLab（更准确的感知过渡）
  const oklabGradient = `linear-gradient(in oklab to bottom, ${colorList})`
  // sRGB fallback（旧浏览器）
  const srgbGradient  = `linear-gradient(to bottom, ${colorList})`

  // CSS supports() 检测
  const supportsOklab = CSS.supports('background', 'linear-gradient(in oklab to bottom, red, blue)')
  appEl.style.background = supportsOklab ? oklabGradient : srgbGradient
}
```

`index.html` 的 `#app background` 修改为纯色兜底 `#06080F`。

### 8.7 显存预算（分级）

| 级别 | 目标设备 | 纹理配置 | 显存目标 |
|------|---------|---------|---------|
| Level 0 | 桌面端 | 8K 日图+夜图+4K 云+4K spec | ≤512MB（**必须使用 KTX2/Basis Universal 压缩；8K 等距圆柱 8192×4096 RGBA ≈128MB/张，8K 方图 8192×8192 RGBA ≈256MB/张**） |
| Level 1 | 主流移动端（maxTex ≥ 4096） | 4K 日图+夜图，关闭云层 | ≤128MB |
| Level 2 | 低端移动端（maxTex ≥ 2048） | 2K 日图+夜图，关闭云层+星场 | ≤64MB |
| Level 3 | WebGL 不可用 | CSS OKLab 渐变+静态地球图片 | — |

移动端 LOD 原则：不得简单“一刀切关闭所有高级视觉”。高端设备可开启 4K/8K + cloudMesh + specular；中端设备应保留 4K/2K 云层或降级 cloudAlphaMap；低端设备关闭独立 cloudMesh，但可保留融合云层或 CSS fallback，以维持基本视觉基调。

```js
// 资源初始化前置检测示意；具体阈值需以实测为准
const maxTexSize = renderer.capabilities.maxTextureSize
const coarsePointer = window.matchMedia && window.matchMedia('(pointer: coarse)').matches
const deviceTier = maxTexSize >= 8192 && !coarsePointer ? 'high'
  : maxTexSize >= 4096 ? 'medium'
  : 'low'

if (deviceTier === 'low') {
  config.enableCloudMesh = false
  config.preferTextureSize = 2048
}
```

**注意**：必须区分 8K 实际尺寸。等距圆柱地球贴图 `8192×4096` 未压缩 RGBA 约 128MB/张，日图+夜图约 256MB；若为 `8192×8192` 方图，则约 256MB/张，日图+夜图约 512MB。8K 纹理必须使用 KTX2/Basis Universal 等压缩格式，并在资源清单中写明实际尺寸和估算显存。

---

## A.9 大气边缘光晕参数（Phase 2）

Phase 1 中 `glowIntensity` 全部设为 0.0，Phase 2 激活：

| 时段 | glowIntensity | glowColor |
|------|--------------|-----------|
| deepNight | 0.08 | #3050A0 |
| lateEvening | 0.10 | #2840A8 |
| evening | 0.12 | #2840A8 |
| dawn | 0.15 | #403060 |
| sunrise | 0.35 | #C07038 |
| earlyMorning | 0.18 | #6090C0 |
| morning | 0.20 | #5080C0 |
| noon | 0.22 | #4878C8 |
| afternoon | 0.20 | #5080B8 |
| goldenApproach | 0.28 | #B08840 |
| sunset | 0.38 | #B06030 |

---

## A.10 后续规划

### 10.1 地球自转
`skyMesh` 不在 `earthGroup` 内，加自转不影响天空系统。

### 10.2 OKLab 插值升级（Phase 2 LUT 生成）
Phase 1 的 LUT 生成在 linear RGB 空间插值（`hexToLinearRGB` + 线性 mix）。Phase 2 升级为：锚点 sRGB → linear RGB → OKLab → 插值 → linear RGB → DataTexture。彻底消除蓝橙互补区间的幽灵青绿色。

### 10.3 云层叠加（Phase 3）
- 独立 mesh，半径 2.04，`transparent: true`，`depthWrite: false`
- 自转用独立 quaternion：`copy(earth.quaternion)` 后 `rotateY(offset)`
- LOD：桌面 8K（KTX2 压缩），主流移动 4K，低端 2K，极低端跳过
- Phase 3 前必须执行资源审计（确认文件名、路径、格式、尺寸）

### 10.4 海水高光分离（Phase 4）
保留 `MeshPhongMaterial`，使用 `specularMap`（非 PBR 的 `roughnessMap`）。Phase 4 前同样需要资源审计。

---

## A.11 施工方案

> **施工原则**：审计先行，分阶段实施，每阶段有明确验收标准。Codex 每次施工前必须完成代码审计，施工后必须对照验收标准逐项确认，不得以"已完成"替代逐项检查。

---

### Phase 0：施工前代码审计

**在任何代码修改之前执行，不得跳过。**

---

**Codex 指令 — Phase 0**

```
你是 RodiO 天空视觉系统改造的代码审计员。
严格按以下清单审计，不修改任何代码，只输出审计报告。

【审计范围文件】
- index.html
- earth3d.js

【审计清单】

1. 天空背景现状
   - index.html 中 #app 的 background 属性完整内容（粘贴原文，含行号）
   - 是否有其他 CSS 规则也在控制 #app 背景色？
   - index.html 中是否有 JS 动态修改 #app background 的代码？

2. earth3d.js 的主题切换入口
   - THEME_VISUAL_CONFIG 包含哪些时段 key？（列出全部）
   - applyTheme() 函数的签名和调用时机？（粘贴函数签名 + 所有调用处的行号）
   - setTimeOfDay() 函数的签名和调用时机？
   - 星场（stars）的 opacity 目前在哪里控制？（行号）
   - 现有主题切换是否包含插值过渡系统？
     （是/否。如是，插值哪些参数？粘贴相关代码。）

3. 渲染系统现状
   - renderer.outputColorSpace / outputEncoding 当前设置？（粘贴代码行 + 行号）
   - renderer.toneMapping 和 toneMappingExposure 当前值？
   - renderer.toneMapping 影响哪些对象？（地球/星场/大气/城市灯光是否全部受影响）
   - scene 中目前有哪些 Mesh？
     （列出每个：geometry 类型 + material 类型 + renderOrder + depthWrite + depthTest）
   - Three.js 版本号是多少？（从 package.json 或 importmap 中读取）

4. 兼容性与性能
   - renderer.capabilities.maxTextureSize 在哪里获取？（行号）
   - 是否有现有的性能降级逻辑？
   - WebGL context lost 的处理逻辑在哪里？（函数名 + 行号）

5. 时段系统现状
   - 目前共有几个时段 key？列出全部。
   - resolveInitialPendingTheme() 完整函数体（粘贴）
   - index.html 中的时段切换按钮完整 HTML（粘贴）

6. 文档与代码一致性核查
   - VISUAL_TARGET_NDC 实际值（粘贴赋值行）
   - earthGroup.position 实际值（粘贴赋值行）
   - TEXTURE_LON_OFFSET 实际值（粘贴赋值行）
   - camera.position 实际值（粘贴赋值行）

7. 潜在冲突点
   - 是否有代码在 applyTheme() 之外修改 renderer.toneMapping 或 toneMappingExposure？
   - atmosphere mesh 的 renderOrder 是什么？天空球加入后是否存在渲染顺序冲突？
   - CSS transition 是否作用于 #app 的 background？

8. Shader t 值审计
   文档 v3.2 已采用基于视线方向的 t 值计算：
     vec3 viewDir = normalize(vWorldPosition - cameraPosition);
     float t = clamp(1.0 - viewDir.y, 0.0, 1.0);
   
   请结合当前 camera.position、earthGroup.position、VISUAL_TARGET_NDC 判断：
   a. 在正常使用状态下，viewDir.y 的实际范围大约是多少？
   b. t = 0 对应屏幕上方，t = 1 对应屏幕下方，渐变铺展比例是否合理？
   c. 如果 t 值范围偏窄（如实际最小值约 0.3），可考虑调整为：
      float t = clamp((1.0 - viewDir.y) * K, 0.0, 1.0);
      其中 K 由审计结果确定。给出 K 的建议值（或确认 K=1 即可）。

9. DataTexture 兼容性审计
   - Three.js 版本是否已移除 RGBFormat？（r137+ 废弃，r152+ 移除）
   - 确认 v3.2 使用 RGBAFormat + UnsignedByteType 在当前版本是否正确
   - 是否需要任何 WebGL 扩展支持？

10. 双 LUT 方案可行性审计
    - 当前 Three.js 版本支持 ShaderMaterial 中声明多个 sampler2D uniform 吗？
    - 在 renderer.setAnimationLoop 回调中，skyTransitionStart / mixRatio 的更新
      会与现有主题切换逻辑产生冲突吗？
    - 给出"双 LUT 方案"在当前代码架构下是否存在技术阻碍（是/否 + 理由）。

11. Tone Mapping 风险审计
    - 修改 toneMappingExposure 是否影响地球纹理、城市灯光、星场、大气层？
    - Phase 1 暂不启用动态 exposure 的建议是否合理？（是/否 + 理由）

12. 星场过渡审计
    - 现有主题切换是否已包含 stars.material.opacity 的插值过渡？
    - 若否，直接设置目标 opacity 在哪些时段过渡中最明显（hardcut 问题）？
    - 建议处理方式。

【输出格式】
逐条回答，每条给出代码行号。
最后输出"施工风险列表"，标注 高/中/低 风险。
高风险项必须说明应对方案，否则不得推进 Phase 1。
第 8–12 条必须给出明确的单一结论，不接受"视情况而定"的模糊答案。
```

---

### Phase 1：天空球系统 + 双 LUT 过渡 + 星场联动

**前置条件**：Phase 0 审计完成，无未解决高风险项，第 8–12 条审计结论已明确。

---

**Codex 指令 — Phase 1**

```
基于 Phase 0 审计报告，执行 RodiO 天空视觉系统第一阶段施工。
施工前必须再次确认：Phase 0 审计报告中第 8–12 条的结论，
并严格按报告结论执行（尤其是 t 值的 K 参数、DataTexture 格式确认）。

【修改文件】
- earth3d.js（主要）
- index.html（仅修改 #app background 和时段按钮两处）

【禁止修改以下内容，违反则本次施工无效】
- 地球纹理加载逻辑（loadTextureWithFallback 函数）
- 城市灯光 emissive 逻辑
- 地球朝向 quaternion 逻辑（getTargetOrientation、quaternionFromBasis）
- canvas 2D fallback 逻辑（#weather-canvas 相关所有代码）
- 任何播放器 UI 逻辑
- atmosphere mesh 的现有逻辑

【任务 1：时段系统扩展至 11 个】

在 THEME_VISUAL_CONFIG 中新增 goldenApproach 和 lateEvening。
完整参数严格按照附录 A 第 7.2 节，不得自行修改任何数值。

goldenApproach 参数抽查点（施工完成后必须粘贴确认）：
- texture.mapColor === 0xEEE8DC
- atmosphere.color === '#C0A878'
- lighting.sun === 0.88

lateEvening 参数抽查点：
- texture.emissiveColor === 0xffc068
- texture.emissiveIntensity === 2.35
- atmosphere.color === '#162840'
- lighting.ambient === 0.038

同步更新 resolveInitialPendingTheme()：
- h >= 16 && h < 17 → 'goldenApproach'
- h >= 20 && h < 22 → 'lateEvening'
- afternoon 边界改为 h >= 14 && h < 16

同步更新 index.html 时段按钮，加入"暮前"和"入夜"。

【任务 2：天空球 + 双 LUT 系统创建】

严格按附录 A 第 8.1 节实现。

关键点：
- Shader 中有三个过渡相关 uniform：skyLUTCurrent / skyLUTNext / mixRatio
- t 值使用 viewDir 方案，K 值按 Phase 0 审计第 8 条结论填入
- skyMesh.renderOrder = -1000，depthWrite = false，depthTest = false
- skyMesh 直接 scene.add，不加入 earthGroup
- Phase 1 中 glowIntensity uniform 初始值为 0.0

【任务 3：LUT 生成函数】

严格按附录 A 第 8.2 节实现。

格式：RGBAFormat + UnsignedByteType（不用 RGBFormat，不用 FloatType）
插值：按 pos 线性采样，不用 Catmull-Rom
颜色转换：hexToLinearRGB（gamma 2.2 近似）

【任务 4：时段切换逻辑】

严格按附录 A 第 8.3 节实现 startSkyTransition() 和 tickSkyTransition()。
tickSkyTransition() 在 renderer.setAnimationLoop 回调中每帧调用。

时段切换触发规则：
- 用户点击按钮 → triggerType = 'interactive'
- 系统自动时间推进 → triggerType = 'auto'

【任务 5：THEME_VISUAL_CONFIG 扩展 sky 字段】

在所有 11 个时段配置中新增 sky 字段，包含：
- stops：严格按附录 A 第 6.2 节各时段的精确色值和百分比
- glowIntensity：Phase 1 全部设为 0.0
- glowColor：按附录 A 第 9 节填入，但 Phase 1 不生效
- transitionDuration：按附录 A 第 6.3 节

天空锚点色值抽查（施工完成后必须粘贴每条确认）：
- sunrise，pos=0.43，hex 应为 #622840
- sunset，pos=0.40，hex 应为 #542238
- goldenApproach，pos=1.00，hex 应为 #DCC070
- lateEvening，pos=1.00，hex 应为 #1C2A48
- noon，pos=0.00，hex 应为 #0C2C68
- deepNight，pos=0.00，hex 应为 #020308

【任务 6：applyTheme() 扩展】

在现有 applyTheme() 函数内，currentTheme 赋值后，return true 前，追加：
1. startSkyTransition(resolvedTheme, options.triggerType ?? 'auto')
2. updateStarOpacity(resolvedTheme)
3. ⚠ Phase 1 不修改 renderer.toneMappingExposure
   仅在 renderer.toneMapping 尚未设置时初始化为 ACESFilmicToneMapping

【任务 7：星场透明度联动】

按 Phase 0 审计第 12 条结论执行。
STAR_OPACITY_MAP 严格按附录 A 第 6.4 节。

【任务 8：Tone Mapping 初始化】

仅在 renderer.toneMapping 尚未设置时执行：
renderer.toneMapping = THREE.ACESFilmicToneMapping
不修改 toneMappingExposure（保持现有值）。

【任务 9：index.html CSS 修改】

将 #app 的 background 属性替换为：background: #06080F;
仅修改这一处，其他所有 CSS 保持原样。

【任务 10：CSS 降级方案】

新增 applyCssFallbackSky(themeKey) 函数，
严格按附录 A 第 8.6 节实现（含 OKLab + sRGB fallback）。
在 markUnavailable() 中调用。

【任务 11：dispose() 更新】

加入：
- skyMesh geometry / material dispose + scene.remove
- skyLUTCurrent / skyLUTNext dispose
- skyMesh = null（防止悬空引用）

【施工完成后自检清单（全部需粘贴代码，不得只说"是"）】

□ skyMesh.renderOrder === -1000（粘贴赋值行）
□ skyMaterial.depthWrite === false（粘贴）
□ skyMaterial.depthTest === false（粘贴）
□ skyMesh 未加入 earthGroup（粘贴 scene.add 行）
□ Shader 中三个过渡 uniform 名称（粘贴 uniforms 定义）
□ Fragment Shader 中 t 值计算完整代码（粘贴 main() 函数）
□ t 值使用的 K 参数（粘贴 + 说明来自 Phase 0 第 8 条）
□ DataTexture 构造行（粘贴，确认 RGBAFormat + UnsignedByteType）
□ buildSkyLUT 中插值方式（粘贴循环体，确认线性采样而非 Catmull-Rom）
□ startSkyTransition / tickSkyTransition 函数存在（粘贴函数签名）
□ tickSkyTransition 在 setAnimationLoop 中的调用位置（粘贴）
□ THEME_VISUAL_CONFIG 时段数量 = 11（粘贴所有 key 列表）
□ resolveInitialPendingTheme() 完整函数体（粘贴，确认含 goldenApproach / lateEvening）
□ 6 个抽查天空锚点色值均正确（粘贴每条 stops 条目）
□ 3 个 goldenApproach 参数抽查点均正确（粘贴）
□ 3 个 lateEvening 参数抽查点均正确（粘贴）
□ applyTheme() 中未修改 toneMappingExposure（粘贴 applyTheme 结尾 10 行）
□ renderer.toneMapping 已设置为 ACESFilmicToneMapping（粘贴）
□ STAR_OPACITY_MAP 完整内容（粘贴）
□ updateStarOpacity 实现方式（粘贴，说明是插值还是直接设置）
□ applyCssFallbackSky 函数实现（粘贴，确认含 OKLab + fallback）
□ index.html #app background = #06080F（粘贴 CSS）
□ index.html 时段按钮含暮前和入夜（粘贴 HTML）
□ dispose() 含 skyMesh 资源释放（粘贴）
□ 未修改以下任何逻辑（逐一确认）：
  loadTextureWithFallback / 城市灯光 emissive / getTargetOrientation /
  quaternionFromBasis / #weather-canvas 相关代码
```

---

**Phase 1 验收标准**

| 类别 | 验收项 | 标准 |
|------|--------|------|
| 架构 | 驱动统一 | #app background 为纯色，天空由 Three.js 驱动 |
| 架构 | 时段数量 | THEME_VISUAL_CONFIG 共 11 个时段 key |
| 架构 | 双 LUT | 时段切换时只上传一次目标 LUT，mixRatio 每帧递增 |
| 视觉 | 正午 | 天顶深钴蓝，不荧光；地平线接近白蓝 |
| 视觉 | 日出 | 可见品红过渡带（玫瑰调）；橙色为低饱和赭石/琥珀 |
| 视觉 | 落日 | 可见品红过渡带（紫调，比日出更宽）；赤陶/琥珀橙 |
| 视觉 | 暮前 | 天顶蓝中带暖，大气壳偏金（#C0A878）；地平线琥珀金黄可见 |
| 视觉 | 夜晚 | 均匀深蓝，蓝色时刻特征明显，无方向感 |
| 视觉 | 入夜 | 比夜晚明显更暗，天顶到地平线仍有明度梯度 |
| 视觉 | 深夜 | 极深靛蓝，趋近均质，星场全亮 |
| 视觉 | 城市灯光 | deepNight（#ffbe63）比 dawn（#ffe0aa）明显更橙，差异可感知 |
| 视觉 | 过渡平滑 | 时段切换时天空颜色平滑过渡，无硬切或闪烁 |
| 联动 | 星场白天 | morning/noon/afternoon/goldenApproach 星场不可见（opacity 0） |
| 联动 | 星场夜晚 | deepNight 1.00，lateEvening 0.72，evening 0.45 |
| 性能 | 帧率 | 不低于改造前的 85%（过渡期间 mixRatio 更新无明显开销） |
| 性能 | 纹理上传 | 切换时段只触发一次纹理上传，不持续每帧上传 |
| 降级 | CSS 兜底 | 强制触发降级时，11 个时段均有 CSS 渐变；OKLab 语法可用时优先使用 |
| 回归 | 不破坏 | 地球纹理、城市灯光、朝向定位、canvas fallback 全部正常 |

---

**Codex 指令 — Phase 1 验收审计**

```
Phase 1 施工已完成。执行验收审计，不修改代码，只输出审计报告。

【检查清单（全部需粘贴代码，不得只说"是"）】

1. THEME_VISUAL_CONFIG 时段 key 完整列表
2. goldenApproach.sky.stops 完整列表
3. lateEvening.sky.stops 完整列表
4. goldenApproach.texture.mapColor / atmosphere.color / lighting.sun 实际值
5. lateEvening.texture.emissiveColor / emissiveIntensity / atmosphere.color 实际值
6. sunrise.sky.stops pos=0.43 的 hex（应为 #622840）
7. sunset.sky.stops pos=0.40 的 hex（应为 #542238）
8. Fragment Shader 完整 main() 函数（重点：t 值计算方式）
9. skyMesh 的 renderOrder / depthWrite / depthTest 实际值
10. Shader uniforms 定义（确认含 skyLUTCurrent / skyLUTNext / mixRatio）
11. DataTexture 构造行（确认 RGBAFormat + UnsignedByteType）
12. buildSkyLUT 中的插值实现（线性采样的循环体）
13. tickSkyTransition 在 setAnimationLoop 中的调用位置
14. STAR_OPACITY_MAP 完整内容
15. applyTheme() 结尾是否有修改 toneMappingExposure 的代码
16. renderer.toneMapping 当前值
17. index.html #app background 当前值
18. index.html 时段按钮完整 HTML（含暮前和入夜）
19. resolveInitialPendingTheme() 完整函数体

【输出】
- 已通过验收项（列出）
- 未通过验收项（列出，说明原因和差异）
- 需要修复的问题清单（按严重程度排序）
- 结论：Phase 1 是否达到验收标准（是/否，不得模糊）
```

---

### Phase 2：OKLab LUT 生成 + Tone Mapping 曝光联动 + 大气边缘光晕激活

**前置条件**：Phase 1 验收通过，运行稳定一个测试周期。

```
执行 Phase 2 施工：OKLab 升级 + Tone Mapping 曝光联动 + 光晕激活。

【任务 1：OKLab LUT 生成升级】
在 buildSkyLUT 中，将颜色插值从 linear RGB 空间升级为 OKLab：
- sRGB → linear RGB → OKLab（使用 OKLab 转换矩阵或引入 oklab 库）
- 在 OKLab 空间线性插值
- OKLab → linear RGB → Uint8Array 写入 DataTexture
OKLab 转换矩阵（手写版本，无需外部库）：
  linear_to_oklab: 先乘 M1（RGB→LMS 立方根空间），再乘 M2（LMS→Lab）
  具体系数参考 https://bottosson.github.io/posts/oklab/

【任务 2：exposure 联动】
在 applyTheme() 中追加：
renderer.toneMappingExposure = config.sky.exposure ?? 1.0
各时段 sky.exposure 值按附录 A 第 8.4 节表格填入。

【任务 3：光晕激活】
将 THEME_VISUAL_CONFIG 中各时段的 sky.glowIntensity 从 0.0
改为附录 A 第 9 节的对应值。
在 applyTheme() 中追加：
skyMaterial.uniforms.glowIntensity.value = config.sky.glowIntensity ?? 0.0
skyMaterial.uniforms.glowColor.value.set(config.sky.glowColor ?? '#4878C8')

【自检】
□ buildSkyLUT 中颜色转换经过 OKLab（粘贴转换代码）
□ noon.sky.exposure === 1.20（粘贴）
□ deepNight.sky.exposure === 0.45（粘贴）
□ goldenApproach.sky.glowIntensity === 0.28（粘贴）
□ 视觉确认：日出/落日天空无幽灵青绿色
□ 视觉确认：正午天空与地球色温协调，无过曝
□ 视觉确认：深夜光晕极弱，暗部层次保留
□ Phase 1 所有验收项仍然通过
```

---

### Phase 3：纹理资源审计 + 云层叠加

**分两步执行：**

**步骤 3A：纹理资源审计（不写代码）**
```
执行纹理资源审计，不修改代码。

检查以下资源是否存在并可访问：
1. /assets/cloud_combined_4k.jpg — fetch 验证返回 200？图像尺寸？颜色模式（RGB/灰度）？
2. /assets/cloud_combined_8k.jpg — 同上（可选）
3. 当前已使用的地球纹理文件名和路径（从代码中读取）
4. 是否使用了 KTX2/Basis Universal 压缩格式？

输出：
- 可用资源列表（名称/路径/尺寸/格式/颜色模式）
- 不可用资源列表（说明原因）
- 云层图像是 RGB 合成图还是灰度遮罩？
  （若为 RGB，需预处理为灰度，不能直接用作 alphaMap）
- 云层施工前提条件是否满足（满足/不满足）
```

**步骤 3B：云层施工**（仅在 3A 确认资源可用后执行）

施工要点：独立 mesh，半径 2.04，`depthWrite: false`，独立 quaternion 自转，按时段控制 opacity，LOD 分级，加载失败静默跳过。

---

### Phase 4：纹理资源审计 + 海水高光分离

先执行资源审计确认 `/assets/earth_spec_4k.jpg` 实际存在（文件名和路径以审计结果为准，不得假设），再执行施工。

**施工约束**：保持 `MeshPhongMaterial`，使用 `specularMap`（非 PBR 的 `roughnessMap`）。

---

## 22. 最终验收标准

| 类别 | 验收项 | 标准 |
|------|--------|------|
| 架构 | 驱动统一 | 天空、地球、灯光、星场均由 earth3d.js 统一驱动 |
| 架构 | 时段覆盖 | 11 个时段全部实现，每个有独立视觉特征 |
| 架构 | 双 LUT | 时段切换后纹理上传次数 = 1，非每帧 |
| 架构 | CSS 降级 | WebGL 不可用时，11 个时段均有 CSS 渐变兜底 |
| 视觉 | 正午 | 天顶最深钴蓝，地平线白蓝，不荧光 |
| 视觉 | 日出 | 品红带（玫瑰调），橙色为赭石/琥珀，无幽灵青绿 |
| 视觉 | 落日 | 品红带（紫调，比日出更宽），赤陶/琥珀橙 |
| 视觉 | 暮前 | 天顶蓝偏暖，大气壳偏金（#C0A878），地平线琥珀金黄 |
| 视觉 | 夜晚 | 均匀深蓝，蓝色时刻特征明显，无方向感 |
| 视觉 | 入夜 | 比夜晚明显更暗，天顶到地平线仍有明度梯度 |
| 视觉 | 深夜 | 极深靛蓝，趋近均质，城市灯光主导 |
| 视觉 | 城市灯光 | 深夜橙感最强，黎明最淡，差异可感知 |
| 视觉 | 过渡 | 时段切换平滑，无硬切或闪烁 |
| 视觉 | 大气光晕 | 日出/落日地球边缘带橙调光晕，深夜极弱 |
| 视觉 | 云层 | 可见且缓慢自转，与地球旋转无耦合 |
| 视觉 | 海水 | 正午海洋有镜面高光，陆地无，夜晚高光消失 |
| 联动 | 星场 | 白天不可见；入夜清晰（0.72）；夜晚隐约（0.45）；黎明微弱（0.38） |
| 联动 | 切换同步 | 天空/地球/星场/曝光同步过渡 |
| 性能 | 帧率 | 桌面 60fps，主流移动 ≥30fps |
| 性能 | 显存 | 移动端 ≤128MB，桌面端 ≤512MB（8K 纹理必须 KTX2 压缩） |
| 回归 | 不破坏 | 地球纹理、城市灯光、朝向定位、canvas fallback 全部正常 |

---

*本文档随项目迭代持续更新。Codex 施工指令可直接复制使用。*
