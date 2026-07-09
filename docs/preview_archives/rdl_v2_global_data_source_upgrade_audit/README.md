# RodiO Global Data Source Upgrade Audit — RDL v2

## 本轮审计结论

### 核心声明

**日本区域只是第一验证样板，不是最终目标。**

RodiO 的目标是全球范围的高精度审美地球。日本样板的价值在于验证技术路线是否可行，所有脚本、命名规范、处理流程必须设计为全球可复用，不接受 Japan-only 的实现。

---

### 现有资产的局限

| 数据源 | 当前用途 | 局限性 |
|---|---|---|
| d5b_v3.2.1（8K）| Layer 0 全球底色 | 纹理精度约 8–10km/px，是设计底色而非精度层 |
| ETOPO1（1 arc-min）| v1 bathymetry 审计 | 1.85km/px，**无法分辨 < 3km 的海湾**，山形约等于平滑；不是精度上限 |
| 21.6K source | v1 陆地细节 | 有 5–14× 清晰度优势，但色调匹配需处理；海洋区域不适用 |

**现有 ETOPO1 数据不够作为未来质量上限。**
**21.6K source 需色调匹配后才能用于 v2。**

---

### 下一步应补强的数据源

| 优先级 | 数据源 | 为什么 | 代价 |
|---|---|---|---|
| **P0** | GEBCO 2024 | 海底精度 4× ETOPO1；海洋层次感的关键 | 区域 subset 200–400 MB，无注册 |
| **P0** | GSHHG full | 解决东京湾/濑户内海等 < 3km 海湾不可见的根本问题 | 全球 50 MB，无注册 |
| **P1** | Copernicus DEM GLO-30 | 30m 山形精度，比 ETOPO1 精度提升 60×；日本阿尔卑斯立体感 | 日本区 ~4 GB，需确认 |
| **P2** | OSM / Geofabrik | 城市路网微光；独立立项，不混入 terrain 主线 | 日本 700 MB |
| **P2** | VIIRS Black Marble | 夜间灯光城市光晕；夜间模式独立叠加 | ~1-2 GB 全球月合成 |

---

### 技术路线确认

MVP v1 已验证以下技术可行：
- Three.js r128 Shader UV Region Blend — ✅ 可行（vUv.y 翻转 bug 已修复）
- 非方形 tile（1.25:1 宽高比）— ✅ 工作正常
- 距离自适应 blend（smoothstep far/near）— ✅ 42–43 FPS

v2 新增技术路线，待验证：
- GEBCO 深度分层海洋 tint（Layer 3 叠加 Layer 0）
- GSHHG coastline distance field edge enhancement（Layer 4）
- Copernicus DEM 多光源 hillshade（Layer 2，仅陆地）
- 多层 blend 下的综合帧率（目标 > 40 FPS）

---

### 全球可扩展性约束

所有后续实现必须遵守：

1. **Region key 用坐标，不用地名**：`118_150_22_50`，不是 `japan`
2. **脚本接受 `--bounds lon_w lon_e lat_s lat_n` 参数**，无硬编码地名
3. **不在本地维护全球超大数据**：每次只下载当前 benchmark region
4. **不把 RodiO 做成 GIS**：颜色渐变而非等深线，hillshade 而非等高线，edge clarity 而非描边
5. **不降低标准**：山形、海湾、海岸线、路网感的视觉要求不因数据获取难度而降低

---

### 审计输出文件

| 文件 | 内容 |
|---|---|
| `data_source_matrix.md` | 所有数据源的详细对比（分辨率、许可、下载方式、推荐级别） |
| `global_pipeline_recommendation.md` | 6 层架构推荐，目录结构，命名规范，如何避免 GIS 感 |
| `japan_benchmark_plan.md` | 日本样板 5 步实施计划，后续全球区域列表，成功标准 |
| `implementation_priority.md` | P0/P1/P2/P3 优先级，17 个具体任务，立即可执行的第一步 |

---

### 立即可执行的第一步

不需要额外确认，可直接执行：

1. 下载 GSHHG（50 MB，无注册）
2. 建立 `pwa/assets/source/` 统一目录结构
3. 建立 `scripts/geo/` 通用工具目录
4. 在 gebco.net 确认 Japan subset 下载参数（不实际下载，等 RW 确认体量）

---

*审计日期：2026-06-07*
*工作目录：`previews/rdl_v2_global_data_source_upgrade_audit/`*
*约束：不修改 pwa/assets，不替换 d5b_v3.2.1，不 commit（等 RW 确认）*
