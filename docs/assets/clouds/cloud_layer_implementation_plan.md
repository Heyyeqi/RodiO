# E1-1 Cloud Layer Foundation Implementation Plan

## 1. 阶段定位

E1-1 Cloud Layer Foundation Implementation Plan

本轮只做施工准备方案，不修改代码，不新增 cloudMesh，不 commit。

## 2. 当前资源结论

- E1-0G Normalized Cloud Asset Acceptance 已完成。
- refined / R2 已通过资源验收，作为 E1 第一版 cloudMesh 的默认试挂候选：
  - 桌面端：`pwa/assets/earth/clouds/cloud_alpha_4096x2048_refined.png`
  - 移动端：`pwa/assets/earth/clouds/cloud_alpha_2048x1024_refined.png`
- refined 仍不是最终美术资源，只是 E1 最小试挂资源。
- 真正验收必须依赖 Three.js 实场景截图。

## 3. E1 最小施工目标

E1 最小施工只解决一件事：

在现有 earth mesh 外部新增一个独立、可关闭、可回退的 cloudMesh，让地球出现低透明度云层漂浮感。

不得扩大为：

- 真实天气系统
- 动态云图
- PBR 材质
- terminator
- city lights dark-side blend
- sky LUT
- atmosphere rim glow
- UI 时间系统改造

## 4. 允许改动范围

正式施工时，理论上只允许修改：

- `pwa/earth3d.js`

必要时只读检查：

- `pwa/index.html`

但默认不得修改 `index.html`。

允许新增的最小逻辑：

- cloud alphaMap 贴图加载
- cloudMesh 创建
- cloudMaterial 创建
- cloudMesh 与 earth 同步旋转
- cloudMesh 半径略大于 earth
- cloud opacity 按时段配置
- `setCloudVisible(visible)`
- `getDebugState()` 增加 cloud 状态
- 贴图加载失败时自动关闭 cloud，不影响地球和播放器
- 移动端优先 2K，桌面端优先 4K
- 保留云层低 opacity 起步

## 5. 禁止改动范围

正式施工时不得修改：

- `pwa/index.html` UI
- 播放器
- service worker
- skyMesh
- fallback
- dayTexture / nightTexture 主链路
- city lights emissive 逻辑
- ocean specular 参数
- camera
- earthGroup 定位
- `VISUAL_TARGET_NDC`
- PBR
- terminator
- 双 LUT
- Sky P1B

## 6. 建议技术方案

### 6.1 贴图加载

优先复用当前 `earth3d.js` 内已有的 `TextureLoader` / 纹理加载风格，不引入新的加载体系。

### 6.2 挂载位置

cloudMesh 应跟随 earth 的姿态，优先与 earth 同步旋转。

建议挂载在 `earthGroup` 体系内，作为与 earth 一起旋转的独立层，而不是挂在 `skyMesh` 下。

### 6.3 材质建议

优先使用轻量、可控、非 PBR 方案。

推荐倾向：

- `MeshBasicMaterial` 或保守的 `MeshLambertMaterial`
- 需要 `transparent: true`
- 需要 `depthWrite: false`
- 视情况保持 `depthTest: false`，以减少透明排序风险

### 6.4 半径建议

- `cloudRadius` 建议范围：`2.035 ~ 2.05`
- 以略大于地球半径为原则，避免穿模

### 6.5 透明与排序

- `renderOrder` 应显式设置
- 云层必须低于城市灯视觉优先级的干扰
- 透明排序必须在 Earth / Cloud / Atmosphere / Sky / Stars 之间保持稳定

### 6.6 资源选择

- 桌面端优先使用 `4096x2048` refined
- 移动端优先使用 `2048x1024` refined
- 低端设备可关闭 cloudMesh 或只保留更低强度的云层

### 6.7 加载失败回退

- 资源加载失败时静默跳过 cloudMesh
- 不得影响 earth / sky / atmosphere / fallback / player

### 6.8 调试控制

- `setCloudVisible(false)` 应能关闭云层
- `getDebugState()` 应新增 cloud 只读状态
- cloud 状态需可用于人工验收和排错

## 7. 建议初始参数

```text
cloudRadius: 2.035 ~ 2.05

opacity:
  morning: 0.10 ~ 0.14
  noon: 0.12 ~ 0.16
  afternoon: 0.10 ~ 0.14
  goldenApproach: 0.08 ~ 0.12
  sunset: 0.08 ~ 0.12
  evening: 0.03 ~ 0.06
  lateEvening: 0.00 ~ 0.03
  deepNight: 0.00 ~ 0.03
  night legacy alias: follow deepNight
```

## 8. 验收标准

### 8.1 功能验收

- cloudMesh 可见
- `setCloudVisible(false)` 可以关闭
- `setCloudVisible(true)` 可以恢复
- `getDebugState()` 能看到 cloud 状态
- cloud 资源加载失败时不影响 earth / sky / player
- 不影响现有 fallback

### 8.2 视觉验收

- 白天云层可见但不糊地球
- noon 不过曝
- goldenApproach 不显脏
- sunset 不压住暖色
- lateEvening / deepNight 不遮挡城市灯
- 南半球云带不过重
- 不出现明显黑色异常块
- 云层有轻微漂浮感，但不喧宾夺主

### 8.3 回归验收

- dayTexture 正常
- nightTexture 正常
- city lights 正常
- ocean specular 不受影响
- skyMesh 不受影响
- fallback 不受影响
- 播放器不受影响
- service worker 不受影响

## 9. 正式施工前必须确认的问题

进入 E1 正式施工前，RW 需要确认：

- cloudMesh 是否默认开启
- 移动端是否默认使用 2K
- deepNight 是否默认关闭云层
- 是否允许 cloudMesh 有极慢旋转
- 如果云层遮挡城市灯，优先降低 opacity 还是按夜间关闭
- 是否接受 refined 作为临时美术资源

## 10. 正式施工建议拆分

### E1-A Cloud Mesh Foundation

只做：

- texture loading
- cloudMesh
- material
- visible toggle
- debugState
- fallback

不做视觉精调。

### E1-B Cloud Visual Tuning

只做：

- opacity
- renderOrder
- 夜间遮挡调整
- 南半球观感调整
- 旋转速度微调

## 11. 当前结论

- 本轮不施工。
- 本轮只把 E1 的代码改动边界和验收标准先锁定。
- refined 资源可作为下一轮正式施工的默认候选。
- 下一轮若进入正式施工，只允许先做 E1-A Cloud Mesh Foundation。

## 12. 后续能力规划

> 说明：本节只做路线规划，不接入天气 API，不修改现有 cloud 参数，不改动画逻辑，不改播放器，不做大范围重构。

### 12.1 E1-C Cloud Motion

目标：让 cloudMesh 在保留克制感的前提下产生极轻微的独立流动。

- cloudMesh 增加独立的慢速旋转或等效环绕位移。
- 相对地球主体只保留极轻微运动，避免游戏化、廉价化。
- 旋转速度必须显著低于地球主体视觉权重，优先让用户感到“云在缓慢漂移”，而不是“云在转圈”。
- 手机端需要考虑低功耗策略，必要时降低动画速度或在低功耗状态暂停云层动画。
- 动画能力必须保持可回退、可关闭、可观测，不影响既有 `setCloudVisible()` 与 debugState 的可用性。

### 12.2 E1-D Theme Coupling

目标：继续把云层和时段主题绑定在一起，但保持当前克制路线。

- 白天主题云层可见。
- 黄昏主题云层更克制，避免压住暖色。
- 夜晚主题云层极弱，优先保护城市灯光和地球纹理。
- 主题联动只作为云层强度与可见性的控制层，不扩展为新的视觉系统。
- 夜间若与城市灯有冲突，优先降低云层，而不是扩大云层结构或改变地球主链路。

### 12.3 E1-E Weather Coupling

目标：后续再把天气状态纳入云层强度控制。

- 根据用户城市天气状态控制 cloud opacity。
- 晴天时云层关闭或维持极低。
- 多云、阴天、雨天时云层逐步提高。
- 夜晚需要再次压低，避免天气权重覆盖夜景层次。
- 天气数据失败时必须回落到默认云层参数，不允许影响页面启动、播放或基础渲染。
- 天气联动应当优先作为参数层输入，而不是重写 cloudMesh 结构。

### 12.4 E1-F Weather Integration Hardening

目标：把天气接入做成稳定的弱依赖能力，而不是单点失败源。

- 天气 API 接入需要有显式降级路径。
- 城市定位、天气抓取、解析失败都要回退到默认主题参数。
- 日常运行中要避免天气数据波动引起云层闪烁或大幅跳变。
- 若未来引入缓存或预取，也必须保持“默认云层参数优先可用”的原则。

### 12.5 后续开发原则

- 现阶段只记录规划，不接入天气 API。
- 不修改现有 cloud 参数作为架构前提。
- 不修改 `earth3d.js` 的动画逻辑作为本轮要求。
- 不修改播放器逻辑。
- 不做大范围重构。
- 后续每一步都要保持能单独回退，避免把云层能力和天气能力绑成不可拆分的整体。
