# Japan Benchmark Plan — RDL v2 全球 Pipeline 第一验证区域

> **核心声明**：日本区域（lon 118–150°E, lat 22–50°N）是全球 pipeline 的第一个验证样板，不是最终目标。
> 日本样板的成功标准是：证明全球数据源和技术路线在复杂的陆海混合区域有效，
> 并可以无修改地复制到地中海、加勒比、大堡礁、南太平洋等后续区域。

---

## 一、日本样板验证矩阵

### 1.1 验证数据源

| 数据源 | 验证内容 | 预期结论 |
|---|---|---|
| GEBCO 2024 (15 arc-sec) | 日本海盆、东海陆架、冲绳海槽、日本海沟精度 | 比 ETOPO1 显著更精细 |
| GSHHG full | 东京湾、大阪湾、伊势湾、濑户内海、琉球群岛海岸线 | 解决 ETOPO1 无法分辨 < 3km 海湾的问题 |
| Copernicus DEM GLO-30 | 日本阿尔卑斯、奥羽山脉、九州、四国、北海道南部 30m hillshade | 比 ETOPO1 (1852m cell) 精度提升 60× |
| ALOS AW3D30（可选）| 对比 Copernicus DEM 在日本山地的表现 | 预计 JAXA 本土数据日本区表现更好 |
| 21.6K source (色调匹配后) | 陆地纹理精细度，海洋区域仅 GEBCO 接管 | 色调匹配后视觉一致性 |

### 1.2 验证技术路线

| 技术点 | 验证内容 | 来自 MVP v1 结论 |
|---|---|---|
| Shader UV Region Blend | 已验证可行 | ✅ 已修复 vUv.y 翻转 bug |
| 非方形贴图（1.25:1 宽高比）| 已验证正确 | ✅ 1024×820 / 2048×1638 |
| 距离自适应 blend | 已验证工作 | ✅ 42–43 FPS |
| GEBCO → depth tint 叠加 | 待验证 | 新增，本次 benchmark 主目标 |
| GSHHG → coastline clarity | 待验证 | 新增 |
| Copernicus DEM → hillshade 叠加 | 待验证 | 新增 |
| 多层 blend（Layer 0+1+2+3+4）| 待验证 | 性能需测量 |

### 1.3 日本样板目标区域精度指标

| 特征 | ETOPO1 结果 | GEBCO/DEM 预期提升 |
|---|---|---|
| 日本海沟最深点 | 8374m ✅ | GEBCO: ~9000m（更准确），位置更精确 |
| 冲绳海槽最深 | 7414m ✅ | GEBCO: 更细腻的深度渐变 |
| 东海陆架层次 | 可辨但粗糙 | GEBCO 4× 更清晰的陆架-陆坡边界 |
| 富士山高度 | 3481m（误差8%）| Copernicus DEM: ~3750m（误差 < 1%）|
| 东京湾海岸线 | 变形（1.5km 分辨率）| GSHHG: 100–500m 级别准确 |
| 濑户内海岛屿 | 轮廓模糊 | GSHHG: 岛屿边界清晰 |
| 琉球群岛礁盘 | 几乎不可见 | GSHHG + GEBCO: 清晰浅礁结构 |

---

## 二、日本样板实施步骤（顺序）

### Step 1：GEBCO Japan Subset 下载和处理
```
目标：验证 GEBCO 2024 在日本区域比 ETOPO1 的精度提升
输入：gebco.net → 下载 lon 118–150°E, lat 22–50°N subset
输出：
  - 同 ETOPO1 5 深度级海洋 tint（更细腻版）
  - shallow shelf / trench / basin mask（4× 更精细）
  - 与 ETOPO1 直接对比图
文件体量：预计 200–400 MB（可接受，需确认后下载）
```

### Step 2：GSHHG Japan Coastline Mask
```
目标：验证 GSHHG 解决 ETOPO1 无法分辨的海湾问题
输入：gshhg-shp-2.3.7 (50MB, 全球一次下载)
处理：裁切 Japan bounds → 生成 coastline distance field → edge clarity mask
验证区：东京湾、大阪湾、伊势湾、濑户内海、琉球群岛
输出：
  - gshhg_coastline_japan.png (coastline mask)
  - gshhg_distance_field_japan.png (distance to coast)
```

### Step 3：Copernicus DEM Japan Hillshade
```
目标：验证 30m DEM vs ETOPO1 1852m 的山形精度
输入：Copernicus DEM GLO-30，日本区约 1000 幅
输出：
  - dem_hillshade_japan_30m.png (高精度地形阴影)
  - 与 ETOPO1 hillshade 直接对比图
  - 富士山、日本阿尔卑斯、奥羽山脉特写
注意：~4GB 数据，需确认后分批下载
```

### Step 4：合成 v2 Detail Tile
```
目标：生成 Layer 0–4 的 Japan 合成贴图
Layer 0: d5b_v3.2.1 (base)
Layer 1: 21.6K source 陆地区域（色调匹配后，blend 0.4）
Layer 2: Copernicus DEM hillshade（陆地，blend 0.2）
Layer 3: GEBCO 海洋深度 tint（海洋，blend 0.3）
Layer 4: GSHHG coastline clarity（边缘，blend 0.15）
输出：
  - japan_v2_detail_2048×H.png
  - japan_v2_detail_4096×H.png
  - 与 v1 tile 对比图
```

### Step 5：Demo 更新和视觉验证
```
目标：在 Three.js demo 中验证 v2 tile 效果
检查：
  - 海洋是否有明显层次感（GEBCO）
  - 海岸线是否更清晰（GSHHG）
  - 山形是否更有立体感（DEM）
  - 整体是否保持审美感（不像 GIS）
```

---

## 三、日本样板成功后的下一批全球区域

### 批次 1：海洋 + 岛礁验证（验证 GEBCO + GSHHG 在复杂岛礁的能力）

| Region Key | 地理区域 | 验证重点 |
|---|---|---|
| `-6_42_30_48` | 地中海 | 复杂海岸线、深海盆、岛礁（科西嘉、撒丁、希腊群岛） |
| `-90_-60_10_30` | 加勒比海 | 珊瑚礁、小岛密集区、大陆架 |
| `140_160_-30_-10` | 大堡礁区域 | 浅礁盘结构（GEBCO 15 arc-sec 是否足以区分礁盘）|
| `170_-160_-30_5` | 南太平洋岛链 | 极浅 atoll、远洋深海对比 |

### 批次 2：山地验证（验证 DEM 在全球极端地形的能力）

| Region Key | 地理区域 | 验证重点 |
|---|---|---|
| `70_100_25_45` | 喜马拉雅 / 青藏高原 | 全球最高海拔区域的 30m DEM 精度 |
| `5_20_43_50` | 阿尔卑斯 | 欧洲山地，与日本 Alps 对比 |
| `-120_-65_-50_10` | 安第斯 | 南美最高山脉，长条状地形 |

### 批次 3：城市灯网验证（Layer 6 独立）

| Region Key | 地理区域 | 验证重点 |
|---|---|---|
| `118_128_29_36` | 长三角 / 上海 | 城市密度最高区域之一 |
| `138_141_34_37` | 东京湾都市圈 | 日本最密集城市区 |
| `-74_-73_40_41` | 纽约大都会 | 北美最密集城市区对比 |

---

## 四、验证成功的定义

日本样板验证通过的标准（定性）：

1. **海洋层次**：日本海、东海、冲绳海槽在 dist=1.35–1.50 时肉眼可见深度渐变，非均匀蓝色
2. **山形立体**：日本阿尔卑斯在 dist=1.25–1.50 时 hillshade 清晰可见，有立体感
3. **海岸清晰**：东京湾、大阪湾开口形状在 dist=1.25 时与真实形态吻合
4. **审美一致**：整体视觉与 d5b_v3.2.1 色调协调，不出现 GIS 感
5. **性能达标**：多层 blend 后 FPS > 40（Three.js r128, 64 segments sphere）

满足以上 5 条，pipeline 可直接复制到下一批区域。

---

## 五、日本样板路径不重复使用的设计约束

所有脚本、配置、命名，必须以 `--bounds lon_w lon_e lat_s lat_n` 为接口，不得硬编码日本地名。例：

```python
# 错误（Japan-only）：
JAPAN_LON_MIN = 118
JAPAN_LAT_MAX = 50

# 正确（全球通用）：
def process_region(lon_w, lon_e, lat_s, lat_n, output_dir):
    ...
```

Region key 也统一用坐标：`japan_118_150_22_50` 中，`japan_` 前缀只用于用户可见标签，内部逻辑只用 `118_150_22_50`。
