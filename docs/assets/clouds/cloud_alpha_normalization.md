# E1-0F Cloud AlphaMap Normalization — 处理记录

> 本文档只记录资源处理过程，不宣称 E1 cloudMesh 已可施工。

---

## 1. 原始文件

| 文件 | 尺寸 | 格式 | 大小 |
|---|---|---|---|
| `pwa/assets/earth/clouds/cloud_alpha_2048x1024.png` | 2048×1024 | 8-bit gray+alpha (LA) | 1.9 MB |
| `pwa/assets/earth/clouds/cloud_alpha_4096x2048.png` | 4096×2048 | 8-bit gray+alpha (LA) | 6.7 MB |

来源：`https://clouds.matteason.co.uk`（EUMETSAT 数据，近实时全球云图）

---

## 2. 输出文件

| 文件 | 说明 | 状态 |
|---|---|---|
| `pwa/assets/earth/clouds/cloud_alpha_2048x1024_norm.png` | 规范化主版本 2K | ✅ 已生成 |
| `pwa/assets/earth/clouds/cloud_alpha_4096x2048_norm.png` | 规范化主版本 4K | ✅ 已生成 |
| `pwa/assets/earth/clouds/cloud_alpha_2048x1024_candidate_a.png` | 候选 A（低黑点，高 gamma） | ✅ 已生成（供对比） |
| `pwa/assets/earth/clouds/cloud_alpha_2048x1024_candidate_b.png` | 候选 B（中间参数） | ✅ 已生成（供对比） |
| `pwa/assets/earth/clouds/cloud_alpha_normalization_preview.png` | 2×2 对比预览图（2048×1104） | ✅ 已生成 |

原始文件未覆盖。

---

## 3. 处理目的

原始图片直接用作 Three.js `alphaMap` 时存在以下问题：

1. 灰度通道 mean=210，median=233，整体底色极亮（灰白雾）
2. 77% 像素 gray>180，无云区域不够黑
3. 直接贴地球会导致全球被灰白雾覆盖，夜间城市灯被遮挡
4. 图中局部存在黑色异常区域（保留原样，不修补）

---

## 4. 处理方法

使用 **Python 3 + Pillow**，操作步骤：

1. 读取原始 LA (gray+alpha) PNG
2. **以 alpha 通道作为云密度数据源**（而非 gray 通道）
   - 原因：alpha 通道 p05=6，mean=172，动态范围明显优于 gray 通道（p05=131，mean=210）
   - alpha 通道才是原始云层透明度编码，更适合作为 alphaMap 源
3. 对 alpha 通道做 black point / white point 拉伸 + gamma 校正
4. 输出为 LA PNG（gray=规范化值，alpha=255 全不透明）

处理公式：

```
normalized = clamp((src - blackPoint) / (whitePoint - blackPoint), 0, 1)
normalized = normalized ** gamma
output = normalized * 255
```

---

## 5. 使用参数

### 主版本（norm）

| 参数 | 值 |
|---|---|
| 数据来源通道 | alpha 通道 |
| black point | 165 |
| white point | 250 |
| gamma | 1.35 |
| 平滑 | 无 |
| 输出格式 | PNG, 8-bit gray+alpha (LA) |
| alpha 通道 | 255（全不透明） |

### 候选 A

| black point | white point | gamma |
|---|---|---|
| 140 | 248 | 1.50 |

候选 A 保留更多低灰薄云细节（bp 更低），但整体稍亮（mean=116）。

### 候选 B

| black point | white point | gamma |
|---|---|---|
| 155 | 252 | 1.30 |

候选 B 介于主版本与候选 A 之间。

---

## 6. 灰度统计对比

### 2K 图（2048×1024）

| 指标 | 原图 GRAY | 原图 ALPHA | **NORM 主版本** | CAND-A | CAND-B |
|---|---|---|---|---|---|
| min | 0 | 0 | 0 | 0 | 0 |
| max | 253 | 254 | 255 | 255 | 255 |
| mean | 210.2 | 172.5 | **103.5** | 115.9 | 107.5 |
| median | 233 | 212 | **114** | 138 | 127 |
| p05 | 131 | 6 | **0** | 0 | 0 |
| p25 | 186 | 118 | **0** | 0 | 0 |
| p50 | 233 | 212 | **114** | 138 | 127 |
| p75 | 243 | 233 | **188** | 203 | 192 |
| p95 | 249 | 244 | **231** | 240 | 228 |
| 非零像素 % | 97.4 | 97.4 | **64.4** | 69.9 | 66.8 |
| bright >180 % | 77.0 | 60.9 | **35.1** | 41.2 | 36.6 |
| near-black <20 % | 2.6 | 7.8 | **38.3** | 33.9 | 36.1 |

### 4K 图（4096×2048）

| 指标 | 原图 ALPHA | **NORM 主版本** |
|---|---|---|
| mean | 174.6 | **105.0** |
| median | 214 | **121** |
| p25 | 125 | **0** |
| bright >180 % | 61.6 | **35.8** |
| near-black <20 % | 7.0 | **37.6** |

---

## 7. 当前结论

**主版本（norm）达到了规范化目标：**

- mean 从 172 降至 103–105（降幅约 40%），确认整体压暗
- near-black 从 7.8% 升至 38.3%，无云区域有效压黑
- 高亮云层（>180）仍保留 35%，厚云区域未被清除
- p25 降至 0，至少 25% 像素完全黑（无云区域）
- p95 仍在 228–231，最厚云层接近白色
- 黑色异常区域（原始图中存在）保留原样，未被修补

**尚存风险（需人工视觉复核）：**

1. 35% 像素 >180 是否仍会在地球上形成过密感，取决于 cloudMesh 的 opacity 和混合模式
2. 原始黑色异常区域在 norm 版本中可能更明显（因背景变暗），需人工确认可接受性
3. 候选 A（bp=140）保留更多薄云细节，如果主版本视觉上云量过少可切换

---

## 8. 是否建议进入下一轮资源验收

**建议**：进入 **E1-0G Normalized Cloud Asset Acceptance** 人工视觉审计。

审计时重点关注：
- 预览图（`cloud_alpha_normalization_preview.png`）中 norm 版本是否已消除灰白雾
- 黑色异常区域是否可接受
- 是否需要切换为候选 A 或候选 B

---

## 9. 仍需人工确认项

| 项目 | 说明 |
|---|---|
| 灰白雾是否消除 | 查看 preview.png 右上（norm 主版本）与左上（原图）对比 |
| 黑色异常区域 | norm 后是否仍可见，是否影响气象合理性观感 |
| 云量密度 | 35% bright 在 cloudMesh 上是否仍偏密，是否需换候选 B |
| 夜间灯光遮挡风险 | 需在 Three.js 场景中实测，资源阶段无法判断 |
| 候选版本选择 | 主版本 vs CAND-A vs CAND-B，需视觉判断后确认 |

---

*记录时间：2026-06-01*  
*处理工具：Python 3 / Pillow*  
*本轮范围：资源处理，未修改任何代码文件*
