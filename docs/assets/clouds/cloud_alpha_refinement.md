# E1-0F.1 Cloud AlphaMap Refinement — 处理记录

> 本文档只记录资源处理过程。本轮未修改任何代码，未进入 cloudMesh 施工。

---

## 1. 本轮目的

E1-0F 生成的 norm 版本经人工审查，主要问题：

- 云层仍然偏密（bright >180 = 35%）
- 高纬度 / 南半球大片白云层较突出
- 直接接入 cloudMesh 仍可能形成灰白雾
- E1 第一版目标：轻、稀疏、干净，不遮挡地表和城市灯

本轮在 norm 基础上继续做二次压暗，生成 refined 版本。

---

## 2. 输入文件

| 文件 | 说明 |
|---|---|
| `pwa/assets/earth/clouds/cloud_alpha_2048x1024_norm.png` | norm 2K（E1-0F 输出） |
| `pwa/assets/earth/clouds/cloud_alpha_4096x2048_norm.png` | norm 4K（E1-0F 输出） |

原始文件（`cloud_alpha_2048x1024.png` / `cloud_alpha_4096x2048.png`）未触碰。
norm 文件未覆盖。

---

## 3. 输出文件

| 文件 | 状态 |
|---|---|
| `pwa/assets/earth/clouds/cloud_alpha_2048x1024_refined.png` | ✅ R2 推荐版，2048×1024，8-bit LA PNG |
| `pwa/assets/earth/clouds/cloud_alpha_4096x2048_refined.png` | ✅ R2 推荐版，4096×2048，8-bit LA PNG |
| `pwa/assets/earth/clouds/cloud_alpha_refinement_preview.png` | ✅ 2×2 对比预览（2048×1120） |

预览图布局：
- 左上：原始 2K alpha 通道
- 右上：norm 2K
- 左下：refined 2K（R2）
- 右下：candidate_a（供参考对比）

---

## 4. 处理参数

### 候选 R1（轻量压暗）

在 norm gray 通道基础上继续：

| 参数 | 值 |
|---|---|
| black point | 30 |
| white point | 235 |
| gamma | 1.25 |
| 平滑 | 无 |

### 候选 R2（稀疏版，最终推荐）

在 norm gray 通道基础上继续：

| 参数 | 值 |
|---|---|
| black point | 45 |
| white point | 240 |
| gamma | 1.45 |
| 平滑 | 无 |

输出格式：LA PNG（gray=refined 值，alpha=255 全不透明）

---

## 5. 统计对比

### 2K（2048×1024）

| 指标 | 原图 alpha | norm | R1 | **R2（推荐）** | 目标区间 |
|---|---|---|---|---|---|
| min | 0 | 0 | 0 | 0 | — |
| max | 254 | 255 | 255 | 255 | — |
| mean | 172.5 | 103.5 | 98.0 | **86.3** | 70–95 |
| median | 212 | 114 | 83 | **56** | 50–95 |
| p05 | 6 | 0 | 0 | 0 | — |
| p25 | 118 | 0 | 0 | 0 | — |
| p75 | 233 | 188 | 184 | **162** | — |
| p95 | 244 | 231 | 248 | **238** | — |
| near-black <20 % | 7.8 | 38.3 | 42.8 | **45.1** | 45–60 ✓ |
| dark <40 % | 9.8 | 40.7 | 45.1 | **47.7** | — |
| mid 40–160 % | 24.4 | 18.1 | 17.0 | **26.1** | — |
| bright >180 % | 60.9 | 35.1 | 26.1 | **21.2** | 20–32 ✓ |
| very-bright >220 % | 45.5 | 9.7 | 13.8 | **9.7** | 8–18 ✓ |

R2 指标评分：4/4 全部命中目标区间。

### 4K（4096×2048）

| 指标 | 原图 alpha | norm | R1 | **R2（推荐）** | 目标区间 |
|---|---|---|---|---|---|
| mean | 174.6 | 105.0 | 99.7 | **87.9** | 70–95 ✓ |
| median | 214 | 121 | 92 | **65** | 50–95 ✓ |
| near-black <20 % | 7.0 | 37.6 | 42.2 | **44.5** | 45–60 ≈ |
| bright >180 % | 61.6 | 35.8 | 26.9 | **22.0** | 20–32 ✓ |
| very-bright >220 % | 46.0 | 10.3 | 14.5 | **10.3** | 8–18 ✓ |

4K R2：near-black=44.5%（目标 45%，差 0.5%），其余全部命中。实质上达标。

---

## 6. 为什么推荐 R2

| 维度 | R1 | R2 |
|---|---|---|
| mean | 98（超出目标上限 95） | **86.3（在 70–95）** |
| near-black | 42.8%（未达目标 45%） | **45.1%（刚好达标）** |
| bright >180 | 26.1% | **21.2%（更接近下限，云层更轻）** |
| 指标评分 | 2/4 | **4/4** |

R1 整体偏亮（mean=98），近黑区域不足（42.8% < 45%）——无云区域仍不够暗，直接接入 cloudMesh 仍存在灰雾风险。R2 在保留主要云团结构的同时，明显压轻薄云和灰雾区域，与 E1 第一版「轻、稀疏、干净」目标更契合。

---

## 7. 当前仍需人工确认项

| 项目 | 说明 |
|---|---|
| 视觉云量是否合适 | 查看 `cloud_alpha_refinement_preview.png` 左下（refined R2）是否达到预期稀疏感 |
| 黑色异常块 | refined 后背景更暗，异常块是否更突兀，是否可接受 |
| 厚云保留 | 主要云带（热带辐合带、极地锋）是否仍清晰可见 |
| 夜间城市灯遮挡 | 仍需 Three.js 场景中实测，资源层无法判断 |
| 高纬度白云减轻 | 高纬度区域是否比 norm 有所改善，需视觉确认 |
| 版本最终确认 | R2 是否选为最终 refined，或是否需要再调参 |

---

## 8. 是否建议进入 E1-0G

**建议**：完成本文档人工视觉复核后，进入 **E1-0G Normalized Cloud Asset Acceptance** 审计。

审计重点：
- `cloud_alpha_refinement_preview.png` 左下 refined 格子是否视觉合格
- 与 norm 对比，refined 是否明显改善灰白雾问题
- 黑色异常块在新版本中的表现

---

## 9. 本轮范围声明

- **未修改** `pwa/earth3d.js`
- **未修改** `index.html`
- **未修改** 播放器 / service worker / skyMesh
- **未新增** cloudMesh / cloudMaterial
- **未覆盖** 原始文件（`cloud_alpha_2048x1024.png` / `cloud_alpha_4096x2048.png`）
- **未覆盖** norm 文件（`cloud_alpha_2048x1024_norm.png` / `cloud_alpha_4096x2048_norm.png`）
- **未 commit**
- 本轮只做资源处理和记录

---

*记录时间：2026-06-01*  
*处理工具：Python 3 / Pillow*  
*处理链：原始 alpha 通道 → E1-0F norm → E1-0F.1 refined (R2)*
