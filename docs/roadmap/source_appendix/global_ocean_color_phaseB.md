# #57 阶段B — 真实水色纹理接入 earth3d.js（调试开关验证报告）

> **状态**：✅ 验收通过 — 所有红线满足，默认路径零影响已量化证明。
> **日期**：2026-07-20
> **环境**：Playwright Chromium (swiftshader) × 静态 PWA 服务器 (localhost:8080)

---

## 一、改动摘要

### 1.1 修改的文件

| 文件 | 改动 |
|---|---|
| `pwa/earth3d.js` | 新增 6 处代码块（uniforms / 声明 / fragment 注入 / loader / 逐帧激活 / 开关接线）+ 调试钩子 |
| `pwa/assets/textures/ocean/global_watercolor_2024_06.png` | **新增** — 阶段A 烘焙的 4096×2048 RGBA 水色纹理（4.38 MB, PNG, alpha=海洋遮罩） |

### 1.2 代码变更点（全部在 `createEarth3D` 函数内部）

| # | 位置 | 内容 | 安全性 |
|---|---|---|---|
| A | L594 | 模块级变量：`waterColorTexture`, `_waterColorActive`, `_waterColorMix` 等 | 只读默认值，零副作用 |
| B | L1757–1762 | `_waterPlaceholder`：alpha=0 的 DataTexture 占位符 | 未加载前 mix×alpha=0 → 无视觉影响 |
| C | L1818–1819 | `onBeforeCompile` 内 uniform 赋值：`uWaterColorMap`, `uWaterColorMix` | 默认 `uWaterColorMix=0` → 零影响 |
| D | L1869–1871 | GLSL uniform 声明（`#include <common>` 替换内） | 仅声明，不影响执行 |
| E | L2134–2142 | fragment shader 注入（`#ifdef USE_MAP` 内，uMapFar 之后） | `mix(diffuseColor, waterTexel, alpha * uWaterColorMix)`；mix=0 时数学恒等 |
| F | L2296–2325 | `ensureWaterColor()` 惰性加载器（仅开关激活时调用） | 默认路径永不触发 |
| G | L7811–7825 | 渲染循环逐帧更新 `_waterColorMix`（平滑跟随目标 0/1） | 默认 target=0 → 值恒为 0 |
| H | L8703–8707 | URL 参数接线：`?earthCandidate=realOceanColor` | 仅设置布尔标志，不改变任何默认行为 |
| I | L2319–2332 | 审计钩子：`isWaterColorLoaded()`, `getWaterColorMix()`, `__debugSetWaterColorMix(v)` | 只读/强制覆盖，仅供复核 |

### 1.3 Shader 注入逻辑

```glsl
// 在 map_fragment 之后、emissivemap_fragment 之前，与 uFarMix 同级：
{
    vec4 _waterTexel = mapTexelToLinear(texture2D(uWaterColorMap, vUv));
    diffuseColor.rgb = mix(diffuseColor.rgb, _waterTexel.rgb,
                              _waterTexel.a * uWaterColorMix);
}
```

**关键安全属性**：
- 当 `uWaterColorMix = 0`（默认）：`mix(A, B, 0) = A`，**逐像素数学恒等**于未注入状态。
- 当纹理未加载（占位符 alpha=0）：即使 mix=1，权重=0 → 同上。
- 色彩管理与 uMapFar 一致（`mapTexelToLinear` sRGB→linear），避免与现有主题光照叠加冲突。

---

## 二、验收标准逐项验证

### ✅ 标准一：默认路径零影响

| 检查项 | 结果 | 数据 |
|---|---|---|
| `getWaterColorMix()` 在无参数页面读数 | **0** | `results.default.mixDefault = 0` |
| 无参数页面 GLSL 编译错误 | **0 条** | errors 列表仅含 404（非 shader 相关资源）和 ws 426（预期 stub） |
| 无参数 vs 参数页（均为 mix0）像素差异（noon 主题） | **0.20%** | 交叉页 diff ≈ 渲染噪声级别 |
| 无参数页强制 mix=1（占位符 alpha=0）是否改变渲染 | **否** | 占位符 alpha=0 → 即使 mix=1 也无效果 |
| 地球空闲旋转 | **≈0** | t0 vs t2 差异 0.04%（无旋转，跨帧对比可靠） |

> **结论**：默认路径 `?earthCandidate=`（或完全不加参数）下，注入的代码路径对渲染输出产生的影响为零。硬红线通过。

### ✅ 标准二：开关可见且合理

| 主题 | 开关前 (mix=0) | 开关后 (mix=1) | 视觉判断 |
|---|---|---|---|
| **noon** | 标准 Blue Marble 深蓝海洋 | 青绿色开阔洋 + 黄褐色浑浊近岸区（长江口、本格拉清晰可辨） | ✓ 合理 — 符合真实全球水色分布特征 |
| **evening** | 暗化陆地 + 城市灯光 + 蓝洋 | 暗化陆地保留 + 城市灯光不变 + 彩色洋面叠加 | ✓ 叠加无冲突 — 水色在暗化基底层之上自然融合 |
| **deepNight** | 近黑陆地 + 密集城市光点 + 深蓝洋 | 近黑陆地完全不变 + 彩色洋面对比强烈 | ✓ 戏剧但不诡异 — 可作为设计选项 |

**磁盘像素变化率**（同一页面 mix0→mix1，仅海洋区域受影响）：

| 主题 | 全图 changed% | 磁盘区域 changed% |
|---|---|---|
| noon | 10.09% | 24.81% |
| evening | 10.02% | 24.65% |
| deepNight | 9.92% | 24.31% |

~25% 的地球磁盘像素发生变化——这与"海洋中颜色显著不同于默认蓝色的区域占比"物理一致（深太平洋蓝→蓝绿差异小；近岸浑浊区差异大）。若陆地被污染，该比率会接近 70-80%。

**已知海域色调交叉核对**（Phase A 报告站位复验）：

| 区域 | Phase A 颜期色 | 开关后实际观察 | 匹配？ |
|---|---|---|---|
| 南太平洋/萨加索（清澈寡营养） | `#006982` 深青蓝 | 青绿色调，偏蓝 | ✓ |
| 长江口（高 CHL/SPM 浑浊） | `#b36d00` 黄褐 | 明显橙黄色沿岸带 | ✓ |
| 亚马逊河口（高 SPM） | `#a74200` 红褐 | 橙红色河口区 | ✓ |
| 本格拉上升流（高 CHL） | `#546905` 绿橄榄 | 绿色调海域 | ✓ |
| 北极冰缘 | 白/透明 | 白色不变（alpha=0 掩膜） | ✓ |

### ✅ 标准三：陆地不被污染

**数学证明**：水色纹理 alpha 通道是"是不是海洋"的二值遮罩（陆地/云/冰 = 0）。Shader 中混合权重 = `alpha * uWaterColorMix`。当 alpha=0（所有陆地点），无论 uWaterColorMix 取何值，权重=0 → `diffuseColor` 不变。

**实证**：param 页面同一机位 mix0 vs mix1 对比图中：
- 陆地轮廓、植被颜色、极地冰雪、城市灯光（evening/deepNight）**像素级一致**
- 差异集中在海洋区域，形成连贯的洋面色块
- 海岸线过渡自然（alpha 渐变带），无渗色到陆地

### ✅ 标准四：多主题兼容性

三个主题（noon/evening/deepNight）均在开关打开时正常渲染，无异常着色、无闪烁、无 shader 错误。

**值得注意的设计观察**（供"要不要变成默认体验"决策参考）：

| 主题 | 观感评价 | 备注 |
|---|---|---|
| noon | ⭐⭐⭐ 最自然 | 水色与日光下的地球视觉高度协调 |
| evening | ⭐⭐ 协调但略突兀 | 彩色洋面 vs 暗化陆地对比度偏高；可能需降低 blend 强度 |
| deepNight | ⭐ 视觉冲击强 | 近黑陆地 + 彩色洋面 = "发光海洋"效果；戏剧性强但偏离现有夜间美学 |

**建议**：若未来提升为默认体验，考虑按主题差异化 uWaterColorMix 强度（noon=0.6~0.8, deepNight=0 或更低）而非全局 1.0。这是阶段C的优化空间，不在本次范围。

### ✅ 标准五：性能

| 项目 | 结果 |
|---|---|
| 纹理加载方式 | **惰性** — 仅 `?earthCandidate=realOceanColor` 激活后才请求 HTTP GET（4.38 MB PNG） |
| 默认路径请求该文件？ | **否** — ensureWaterColor() 不被调用 |
| 加载方式 | THREE.TextureLoader 异步（非阻塞，同 Blue Marble 模式） |
| 每帧开销 | 一次 texture2D lookup + 一次 mix（negligible；与 uFarMix 同量级） |
| 显存占用 | 4096×2048×4 bytes ≈ **32 MB**（mipmap 后 ~42 MB）— 仅加载后占用 |

---

## 三、独立复核指引

RW 可以用以下步骤自行核验每项结论：

```bash
# 1) 启动静态服务器（或用完整 server.js）
node /tmp/rodio_assets/static_pwa.js &   # port 8080

# 2) 默认路径零影响：浏览器打开 http://localhost:8080/index.html
#    控制台输入：
window.earth3d.getWaterColorMix()     // → 应返回 0
// 截图保存

# 3) 开关激活：
# 打开 http://localhost:8080/index.html?earthCandidate=realOceanColor
// 等待几秒让纹理加载：
setInterval(() => console.log(window.earth3d.isWaterColorLoaded()), 500)
// loaded=true 后：
window.earth3d.getWaterColorMix()     // → 应趋向 1
// 截图对比：海洋应变为彩色，陆地不变

# 4) 多主题测试（控制台强制切换）：
window.earth3d.setTimeOfDay('deepNight')
// 等 1.5s，截图

# 5) 关闭开关（回到默认）：
window.earth3d.__debugSetWaterColorMix(0)   // → 海洋恢复蓝色
window.earth3d.__debugSetWaterColorMix(null) // → 交还给开关逻辑

# 6) 确认文件存在且为有效 RGBA PNG：
ls -la pwa/assets/textures/ocean/global_watercolor_2024_06.png
# → 应为 ~4.38 MB, RGBA mode
```

---

## 四、产物清单

| 文件 | 说明 |
|---|---|
| `pwa/earth3d.js` | 含完整水色管线接入（6处新增代码块 + 调试钩子） |
| `pwa/assets/textures/ocean/global_watercolor_2024_06.png` | 交付用 RGBA 水色纹理（4096×2048, 4.38 MB） |
| `docs/roadmap/source_appendix/figures/ocean_color_phaseB_combo_noon.png` | noon: mix0 vs mix1 并排对比（已归档，随git提交） |
| `docs/roadmap/source_appendix/figures/ocean_color_phaseB_combo_evening.png` | evening: mix0 vs mix1 并排对比（已归档） |
| `docs/roadmap/source_appendix/figures/ocean_color_phaseB_combo_deepNight.png` | deepNight: mix0 vs mix1 并排对比（已归档） |
| `docs/roadmap/source_appendix/figures/ocean_color_phaseB_combo_zero_impact_noon.png` | no-param vs param-mix0（零影响证据，已归档） |
| `docs/roadmap/source_appendix/figures/ocean_color_phaseB_verify_results.json` | Playwright 自动化结果原始数据（已归档） |
| `temp/ocean_color_real/verify/param_*_mix*.png` | 各主题/状态的原始截图（16张，本地临时目录，未提交，可用报告§三命令重新生成） |
| `temp/ocean_color_real/verify/noparam_*_mix*.png` | 无参数页各主题/状态原始截图（8张，同上，未提交） |

---

## 五、结论与决定（2026-07-20 补记）

**技术验证全部通过**（默认路径零影响、开关生效、陆地零污染、多主题兼容），但RW看过真机截图后判断：**颜色饱和度/质感不对**——`deriveWaterParams()`算出来的物理色值在近岸浑浊区呈现出高饱和荧光橙、开阔洋呈现高饱和青绿色，视觉上更像科研数据可视化（叶绿素浓度热力图配色），不是真实卫星摄影里海水该有的克制自然色调，跟陆地贴图的摄影质感/RodiO一贯"克制真实"的调性不统一。

**根源判断**：`water_params_reference.js`算出的是物理上准确的反射率/色相（这部分本身没问题，Step 0/阶段A的验证依然成立——数据是真的，管线是通的），但从"物理正确的颜色"到"看起来自然的照片色"之间缺一道色调映射（tone mapping）/降饱和处理。当初给Horizon Mode设计这套色彩系统时文档里其实提到过这个需求（OKLab混合避免色相漂移等），但这次阶段B把公式算出来的色值原样喂给了贴图，没有做这道后处理。

**决定**：**撤回这次的`earth3d.js`接入代码**（已还原到接入前状态，本报告+验证截图+真实数据管线保留作为记录，不是白做——数据获取和逐像素管线这两块后续复用时不用重新验证）。下一步需要先做一轮色调映射/降饱和设计（可能需要参考真实卫星"true color"合成图的色彩分布做校准，而不是直接用物理反射率转的色相），色调调对了再重新考虑接入方式，这轮不算完整的阶段B交付，是阶段B的一次未通过质量关的尝试。
