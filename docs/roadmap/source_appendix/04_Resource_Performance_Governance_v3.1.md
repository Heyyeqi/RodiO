# 04 Resource Performance Governance v3.1

## 0. 定位

本文件解决 RodiO 从普通网页项目向资源型图形产品转变的问题。

核心判断：当前 Web / PWA 形态仍可继续，但必须治理资源、缓存、加载、分辨率、目录和候选文件。

---

## 1. 资源目录强制分区

```text
pwa/assets/earth/production/     # 正式运行资源，只能放已验收版本
pwa/assets/earth/candidates/     # 候选资源，可通过参数切换，不得默认加载
pwa/assets/earth/source/         # 原始源文件和处理源
pwa/assets/earth/archive/        # 历史稳定归档
pwa/assets/earth/tmp/            # 临时产物，可清理
pwa/assets/earth/masks/          # specular / alpha / mask
pwa/assets/earth/clouds/         # 云层资源
```

禁止：

- candidates 被默认代码引用；
- tmp 被 commit；
- 同名覆盖 production；
- 失败图长期保留在正式路径；
- 资源无版本号。

---

## 2. 分辨率策略

| 用途 | 建议尺寸 | 是否默认 |
|---|---:|---|
| 移动端安全 | 4096×2048 | 可默认 |
| 标准桌面 | 8192×4096 | 当前主力 |
| 高清候选 | 16384×8192 | 只候选，不默认 |
| 源文件 / 生成中间图 | 可更高 | 不进运行路径 |

不得只写“8K”，必须写实际像素尺寸。

---

## 3. MacBook Air 16GB / 512GB 开发策略

该设备可以支撑当前 RodiO 开发，但不是高负载工作站。

策略：

1. 本机只保留当前开发分支和 production/candidates 必要资源；
2. source/archive/tmp 大体积资源放外置 SSD；
3. 不长期在本机堆 16K 中间产物；
4. 开发时减少 Chrome 多标签、图片软件、AI 工具同时高负载；
5. 16K 只做候选和导出测试，不做日常默认；
6. 每轮生成后清理失败产物。

---

## 4. 加载策略

```text
Base Pack：首屏 UI + 低清占位
Earth Standard Pack：4K / 8K day/night
Earth HD Pack：按设备能力加载 8K / 16K
Atmosphere Pack：cloud / rim glow / stars
Weather Pack：远期按需加载
Experimental Pack：候选，不进入默认加载
```

---

## 5. PWA 缓存规则

正式资源必须带版本号或 hash：

```text
day_master_v1_8192x4096.jpg
night_master_v1_8192x4096.jpg
cloud_alpha_v1_4096x2048.png
```

禁止覆盖同名文件后继续测试，因为 PWA/浏览器缓存会导致“看起来没生效”。

---

## 6. 每轮资源审计表

| 资源 | 路径 | 尺寸 | 格式 | 体积 | 是否 production | 是否默认加载 | fallback | 备注 |
|---|---|---:|---|---:|---|---|---|---|
| dayTexture | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |
| nightTexture | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |
| cloudAlpha | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |
| oceanSpecular | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |

---

## 7. 性能基线

每次视觉基线归档必须记录：

- commit hash；
- Chrome profile；
- viewport；
- themeKey；
- FPS 主观/工具记录；
- 是否发热；
- 是否白屏；
- 首屏加载时间；
- 资源实际加载清单。
