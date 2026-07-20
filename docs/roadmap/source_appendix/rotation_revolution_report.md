# #52 Phase 1 收尾 — 地球自转 + 公转可视化 验收报告

**总判定：✅ PASS**（`overallPass = true`，三子系统全部通过）

> 验收数据见同目录 `rotation_revolution_report.json`；截图见 `figures/rr_*.png`。
> 验证方式：Playwright + 系统 Chrome（swiftshader 软件渲染）加载真实 PWA 页面，读取运行时状态，非纯静态推演。

---

## A. 默认路径零影响（硬红线）

| 项 | 值 |
|---|---|
| `earth3d.isReady` | `true` |
| `window.realCelestial` 挂载 | `false`（无参时不挂载） |
| `vs._realRotationLonOffset` | `null`（不注入任何自转 offset） |
| 我的代码相关 console/page 报错 | `0` |

**结论：通过。** 无参时 `realCelestial` 不挂载、`_realRotation` 开关为 false、动画循环零副作用，11 主题 + 10 构图现有行为完全不受影响。

---

## B. 自转符号 / 相位 物理自洽（`?earthCandidate=realCelestial`，冻结 `?now=`）

### B1. 符号由物理自洽性实测确定，非拍脑袋
- **物理事实**：`_computeSubsolarPoint()` 返回 `subLon = -GHA`；GHA 随格林尼治恒星时以 **≈15°/h 西向**增长，故"太阳直射经度"（东正约定）以 **-15°/h** 递减 —— 即直射点沿地表**向西**移动，这正好对应**地球东向自转**（物理正确）。
- **渲染事实**：渲染出的太阳直射经度对 `offset` 的导数 `dr/doff = +1`（offset 叠加进瞄准经度，东向增大）。
- **推导**：要使"渲染直射经度"随时精确对齐物理直射经度，需 `d(offset)/dt = dS/dt ÷ dr/doff = -15°/h` ⇒ 符号取 **`-1`**。
- **证伪测试**（`check_sign.js`，6h 后渲染直射点 vs 真实太阳光照方向偏差）：
  - 若符号取 `+1`：偏离 **103°**（明显错，直射点漂离太阳半边天）
  - 若符号取 `-1`（逐帧标定）：偏离 **0.024°**（精确对齐）
- **`REAL_ROTATION_SIGN = -1`** 即由此确定。`-1` 仍对应物理上的地球东向自转，只是本坐标系"瞄准经度求和"采用东正约定，offset 取负。

### B2. 相位标定（逐帧标定模型，非线性外推）
> 关键修正：最初设想"offset = phase + 符号·360·Δt/24h 线性东向漂移"是错的。`getTargetOrientation()` 采用相机瞄准纬度的全景朝向，使"渲染直射经度 vs offset"呈**非线性**，线性外推 6h 后偏离太阳 ~77–103°。改为**逐帧标定**：`_computeRealRotationPhase(now)` 在 [-180,180] 粗扫(2°)+细扫(0.05°)搜索使"渲染直射经度 == `_computeSubsolarPoint(now)`"的 offset，每帧重算。

| 采样时刻 | 标定误差 |
|---|---|
| T0 (0h) | 0.025° |
| T1 (6h) | 0.016° |

`anchorOk = true`（每采样点误差 < 0.1°），任意时刻"渲染太阳直射经度 == 物理太阳直射经度"。

### B3. 上海白天/黑夜 vs 贴图明暗（用户指定验收判据）
| 状态 | 渲染亮度 | 物理判定 | 一致性 |
|---|---|---|---|
| 上海本地正午 | **+0.623（亮）** | 白天 | ✅ 一致 |
| 上海本地午夜 | **−0.624（暗）** | 黑夜 | ✅ 一致 |

`signConsistent = true`：自转符号使"本地正午地理正对太阳、贴图被照亮；本地午夜背对太阳、贴图全暗"，与物理昼夜完全吻合。

**结论：通过。** 符号经物理自洽确定（东向自转、西向直射点漂移），逐帧标定使本地正午=太阳直射，明暗与物理一致。

---

## C. 公转可视化（仅 deepSpace + 随真实日期变化）

### C1. 可见性（按相机→地心实际距离分档，与太阳近场光晕完全独立）
| 构图 | camDistEarth | 轨道环可见 | 期望 | 通过 |
|---|---|---|---|---|
| near | 11.8 | 否 | 否 | ✅ |
| farOrbit | 25.2 | 否 | 否 | ✅ |
| deepSpace | 80.0 | **是** | 是 | ✅ |

（`SUN_VISIBLE_DIST = 50`，仅 deepSpace 越过阈值；near/farOrbit 看不到环，不抢戏。）

### C2. 随真实日期变化（四节气地球标记黄经）
| 节气 | 地球标记黄经 | 与预期(≈180/270/0/90) |
|---|---|---|
| 春分 | 179.4° | ✅ |
| 夏至 | 269.7° | ✅ |
| 秋分 | 359.0° | ✅ |
| 冬至 | 89.1° | ✅ |

**黄经跨度 = 269.9°**（> 90°，证明随真实日期明显公转）。位置由真实日期经黄经推算，非装饰性固定环。

**结论：通过。** 仅 deepSpace 可见、克制不抢戏；与已有太阳/月亮逻辑（距离分档、固定摆放距离、恒定角直径缩放）互不耦合；位置由真实日期驱动。

---

## 截图
- 基线（无参，应零变化）：`figures/rr_baseline_no_param.png`
- 上海本地正午（应被照亮）：`figures/rr_rotation_shanghai_noon.png`
- 上海本地午夜（应全暗）：`figures/rr_rotation_shanghai_midnight.png`
- deepSpace 公转环：`figures/rr_revolution_deepSpace.png`
- 春分 / 秋分公转环：`figures/rr_revolution_vernal.png` / `figures/rr_revolution_autumn.png`

---

## 实现要点（供代码复盘）
- **earth3d.js**
  - 新增 `_realRotation` 独立开关：默认 `false`，仅当 `?earthCandidate=realCelestial` 为 true（复用该 param，不新增）。
  - `getTargetOrientation()` 的 lon 叠加一路 `realRotationOffset = _realRotation.enabled ? (vs._realRotationLonOffset||0) : 0`。
  - `_updateRealRotation()` 每帧调用，写入 `vs._realRotationLonOffset`（逐帧标定结果）。
  - `updateSunPosition()` 接受可选 `nowMs`；realRotation 激活时传 `_resolveCelestialNowMs()`，使 `sunLight` 与自转共用同一 `?now=` 冻结时间基准（否则"本地正午"贴图明暗会与太阳直射经度错位）。
  - 调试钩子 `window.__realRotationDebug`（phaseAt / evalBrightness / renderedSubsolarLonAt）仅读取、不影响渲染、默认路径零影响。
- **real-celestial.js**
  - 仅 deepSpace 可见的克制轨道环（RingGeometry 细环）+ Earth 标记（Sphere），由真实日期经黄经推算放置。
  - **未触碰**已有太阳/月亮逻辑：MOON_VISIBLE_DIST=20、SUN_VISIBLE_DIST=50、MOON_DIST=3、SUN_DIST=6、恒定角直径缩放（月亮 4.5×、太阳 5.0×）全部保持。公转环与太阳近场光晕（3R_e 压缩符号）是两套独立视觉语言，互不耦合。
- **验证环境坑**：项目 `better-sqlite3` 原生二进制按 Node 24.x 编译，本机仅 Node 22 → `node server.js` 起不来。验证改用忠实静态服务器（`/tmp/rodio_assets/static_pwa.js`，映射 `pwa/` 为 root，端口 8080）+ Playwright 系统 Chrome，红线用「分类报错证明 my_code 零错误」替代完整 server 启动。
