# RodiO Globe — Regional Detail Layer (RDL) 完整方案

**版本：** v1.0  
**状态：** 待执行  
**作者：** 苏衡 整合  
**面向：** Claude Code 执行 / Evan 审核

---

## 一、背景与问题定义

RodiO 当前地球渲染使用单张 d5b 8K 全局纹理。在相机距离 ≤ 1.25x 时，日本区域的有效像素覆盖约为 **728×637px**，放大后视觉模糊，无法支撑近景审美体验。

海洋层（GEBCO 2026）和海岸线层（GSHHG 2.3.7）已经是真正的高精度数据，瓶颈完全在陆地视觉 source。

目标不是推翻现有系统，而是在不动 earth3d.js 的前提下，建立一套**分层 LOD 机制**，近景时透明叠加高精度 regional tile，远景时无缝退回 d5b。

---

## 二、整体架构

### LOD 三层结构

```
相机距离 > 1.5x
└── d5b 8K 全局纹理（现有，不动）

相机距离 1.2–1.5x
└── 静态合成 tile
    ├── BMNG 86400×43200（500m/px 陆地）
    ├── GEBCO 2026（450m/px 海底地形）
    └── GSHHG 2.3.7（~25m 海岸线矢量）

相机距离 < 1.2x
└── Mapbox Satellite 动态瓦片（实时，zoom 7–8）
    └── fragment shader LUT 色调对齐 d5b
```

### 核心约束

- **不修改 earth3d.js 或任何现有渲染器**
- **不替换生产纹理**
- RDL 是独立 overlay 模块，平行挂载
- 所有预处理脚本 bounds-driven，无 region hardcoding
- d5b 始终作为 runtime base / fallback

---

## 三、效率保障机制（核心）

### 位置授权前置预加载

RodiO 播放器启动时要求用户授权地理位置。这个授权点是整个 RDL 效率机制的基础：

```
用户进入播放器
↓
地理位置授权（已有流程）
↓
根据坐标计算 region bounds
↓
后台静默预加载对应区域 Mapbox tile（zoom 7/8）
↓
tile 存入 session memory cache
↓
用户拉近相机时，tile 已就位 → 零等待渲染
```

**关键优势：**  
预加载在用户操作地球之前就完成。相机距离阈值触发的是渲染切换，不是网络请求。用户感知不到任何加载过程。

### Session Memory Cache

Mapbox tile 在内存中缓存，当次会话内相机反复拉近拉远不重复请求。这符合 Mapbox 条款（条款禁止持久化存储，内存 cache 是正常浏览器行为）。

### LUT 预计算

fragment shader 色调对齐使用预计算 LUT texture（256×1 的 1D LUT 或 3D LUT），不在每帧做曲线运算，避免 tile 加载完成时的帧率卡顿。

### 预加载 tile 数量估算

| Zoom Level | 日本区域 tile 数 | 预加载体量（估算） |
|---|---|---|
| zoom 7 | 约 16–25 块 | ~3–8MB |
| zoom 8 | 约 64–100 块 | ~12–30MB |

建议默认 zoom 7，用户拉近到更近距离时按需补充 zoom 8。

---

## 四、各层技术规格

### Layer 0：d5b 8K（现有，不动）

- 分辨率：21600×10800
- 日本区域 native：~728×637px
- 用途：全局 base / 远景 / fallback
- 状态：**已完成，不修改**

### Layer 1：静态合成 tile（BMNG + GEBCO + GSHHG）

**BMNG 86400×43200**

- 分辨率：500m/px，15 arc-second
- 日本区域 native：约 3200×2000px（较现在提升 4 倍线性）
- 获取方式：从 sbcode.net 下载 256 块 5400×2700 JPG tile，GDAL VRT 建立虚拟 mosaic，按 bounds 裁切，不生成全量拼接图
- 授权：NASA 公共域，需注明 NASA Visible Earth + Sean Bradley/sbcode attribution

**GEBCO 2026**

- 分辨率：15 arc-second（~450m/px）
- 状态：**已完成**

**GSHHG 2.3.7**

- 精度：~25m 矢量
- 状态：**已完成**

**compositor pipeline**

- 状态：**已完成**（rdl_tile_compositor.py，bounds-driven，全球可复用）

### Layer 2：Mapbox Satellite 动态瓦片

- 精度：zoom 7 约 1200m/px；zoom 8 约 600m/px（视区域而异）
- 色调处理：fragment shader LUT，对齐 d5b 暖色调
- 触发时机：位置授权后立即后台预加载，相机 < 1.2x 时切入渲染
- 条款：实时 API 调用，session memory cache，自用，月请求量远低于 50,000 免费上限
- 费用：$0

---

## 五、可行性论证

### 5.1 数据源可行性

**BMNG 86400×43200 真实存在且已被独立验证。**

Sean Bradley 已将 NASA Visible Earth 源数据完整处理为 256 块 5400×2700 JPG tile，公开提供下载。这意味着不需要从 NASA FTP 下载原始 bin 文件自行处理，直接批量下载分块即可。NASA 官方确认 BMNG 提供 500m 月度全球合成影像，全年 12 个月版本，数据来源 Terra/MODIS 卫星。

GEBCO 2026 和 GSHHG 2.3.7 已在本项目中验证可用，compositor pipeline 已完成。

**Mapbox Satellite 可行性：**  
Mapbox 每月提供 50,000 次免费 web map loads，自用单用户月请求量约数百次，远低于上限，费用为零。实时 API 调用符合 Mapbox 条款。

### 5.2 硬件可行性（MacBook Air M5 16GB）

| 操作 | 内存需求 | 评估 |
|---|---|---|
| GDAL VRT mosaic（不生成全量图） | 4–6GB 峰值 | ✅ 安全 |
| 按 bounds 裁切 regional tile | 2–4GB | ✅ 安全 |
| 运行时 session tile cache（zoom 7） | ~10–30MB | ✅ 安全 |
| GPU 渲染 8K base + RDL overlay | ~1GB 显存 | ✅ M5 集成显卡可承受 |

关键决策：**VRT 作为主路径**，不生成 86400×43200 全量拼接图。这将峰值内存从 14GB 降到 6GB 以内，M5 完全安全。

### 5.3 架构可行性

不修改 earth3d.js 的约束是可以实现的。RDL 作为独立 overlay 模块挂载，使用相同的 UV region shader，距离驱动的 smoothstep blend coefficient 控制层间过渡。UV 坐标体系已经验证（prototype demo 已建立）。

位置授权前置预加载机制利用了播放器已有流程，不引入新的用户交互节点。后台预加载对用户完全透明。

### 5.4 风险评估

| 风险 | 概率 | 应对 |
|---|---|---|
| BMNG 色调与 d5b 不兼容 | 中 | Layer 1 验证阶段先做色调 patch 对比，不对齐则调整再输出 |
| Mapbox 网络延迟（极少数情况） | 低 | session cache 覆盖绝大多数场景；极端情况 fallback 到 Layer 1 静态 tile |
| M5 内存在处理阶段紧张 | 低 | VRT 路径已将峰值降到安全范围 |
| Mapbox API 变更 | 极低 | 架构模块化，替换 source 只需改 Layer 2 |

---

## 六、执行路线（分阶段）

### Phase 1：BMNG visual source 建立（Layer 1 基础）

```
1. 批量下载 256 块 BMNG 5400×2700 JPG tile
2. GDAL VRT 建立全球虚拟 mosaic
3. 按 Japan benchmark bounds 裁切
4. 生成 4096 regional visual tile（可选 8192）
5. 与 d5b 做色调匹配（人工确认）
6. 叠加 GEBCO 2026 + GSHHG 2.3.7
7. 输出 Japan benchmark 对比图
8. 不修改 earth3d.js，独立 demo 验证
```

**验收标准：** Japan benchmark tile 输出，与 d5b 色调差异在 shader 后处理可接受范围内。

### Phase 2：Mapbox 动态 Layer 集成（Layer 2）

```
1. 播放器位置授权回调中注入 tile 预加载逻辑
2. 根据坐标计算 zoom 7 region bounds
3. 后台批量请求 Mapbox Satellite tile，存入 session cache
4. 实现相机距离 < 1.2x 时的 LOD 切换
5. fragment shader LUT 色调对齐
6. smoothstep 层间过渡
7. zoom 8 补充加载（相机更近时触发）
```

**验收标准：** 相机拉近无感切换，色调连续，无明显帧率下降。

### Phase 3：全球 pipeline 扩展

```
bounds 驱动，其他区域按需生产
地中海 / 大堡礁 / 加勒比 / 长三角 等
```

---

## 七、当前已完成 vs 待完成

| 模块 | 状态 |
|---|---|
| d5b 8K base texture | ✅ 完成 |
| GEBCO 2026 海底地形 | ✅ 完成 |
| GSHHG 2.3.7 海岸线 | ✅ 完成 |
| compositor pipeline | ✅ 完成 |
| UV region shader prototype | ✅ 完成 |
| BMNG tile 下载 + VRT | ⬜ 待执行（Phase 1） |
| Japan benchmark tile 输出 | ⬜ 待执行（Phase 1） |
| Mapbox session 预加载机制 | ⬜ 待执行（Phase 2） |
| LUT 色调对齐 shader | ⬜ 待执行（Phase 2） |
| LOD 距离切换逻辑 | ⬜ 待执行（Phase 2） |

---

## 八、Attribution 要求

使用本方案中的数据源，需在项目文档中保留以下 attribution：

- **BMNG：** NASA Earth Observatory, Reto Stöckli (NASA/GSFC)
- **BMNG tile 预处理：** Sean Bradley / sbcode.net
- **GEBCO 2026：** GEBCO Compilation Group
- **GSHHG：** Wessel & Smith
- **Mapbox Satellite：** © Mapbox, © OpenStreetMap contributors

---

## 九、禁止事项（执行红线）

- 不修改 earth3d.js
- 不替换 d5b 生产纹理
- 不生成 86400×43200 全量拼接图（用 VRT）
- 不持久化存储 Mapbox tile（session memory only）
- 不在 region tile 中 hardcode 任何具体地名或坐标
- 不把日本描述为最终目标，它是 benchmark
