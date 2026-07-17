# RodiO Ultimate Build Plan  
## 最终全功能建设、实施、审计与验收总纲

> 版本：v1.0 Ultimate Completion Edition  
> 日期：2026-07-17  
> 定位：RodiO 当前及未来开发的最高层主控文件。  
> 目标：不以“完成某个小版本”为终点，而以实现 RodiO 的完整产品愿景、关闭全部建设任务为终点。  
> 执行原则：最终设计一次完整定义；工程实施按依赖关系推进；每一项任务均需完成、以等价路线替代，或经正式技术论证后废止。  
> 适用对象：RW、Claude Code、Codex、Agent Mesh、视觉审计人员、后续产品与工程协作者。

---

# 0. 文件结论

RodiO 的最终形态不是“一个带 3D 地球的音乐播放器”，也不是“一个可操作的数字地球玩具”。

RodiO 是：

> **一个以音乐为入口，以时间、地点、天气、天文、文化和用户状态为上下文，以地球为主要视觉窗口，以低打扰 AI 为陪伴方式的宇宙电台。**

用户进入 RodiO，不是为了面对越来越多的按钮，而是为了在一个真实运转的世界中，被递来一首此刻合适的歌。

RodiO 的产品完成状态必须同时满足四个层面：

1. **作为音乐产品可靠**：能持续播放、自动恢复、跨端可用、弱网与离线不崩溃。
2. **作为视觉空间成立**：地球、天空、昼夜、云、大气、星空和镜头形成统一世界。
3. **作为情境系统真实**：时间、地点、天气、月相、节气、潮汐和文化节点不是装饰，而是有来源的状态。
4. **作为 AI 陪伴有分寸**：能理解、选择、解释、记忆，但不说教、不打扰、不制造被监视感。

本总纲废止以下两种错误倾向：

- 只规划近期小阶段，导致最终能力不断被延期；
- 为追求“全部完成”而一次性混改所有系统，导致项目失控。

正确方式是：

```text
完整目标全部纳入
→ 全部任务形成闭环
→ 按真实依赖拆分工作流
→ 可并行的并行
→ 有冲突的串行
→ 每项均有验收与替代路线
→ 直到总任务树全部关闭
```

---

# 1. 本次整合覆盖范围

本文件已整合并重新判断以下资料：

1. `RodiO 产品方案 v4`
2. `RodiO 开发路线 v3`
3. 《从一首被正确递来的歌开始：我理解的下一代 AI 陪伴》
4. `RodiO Globe — Regional Detail Layer（RDL）完整方案`
5. `00_Master_Roadmap_v3.1_FullExecution`
6. `01_Current_Workflow_How_To_Use_This_Pack`
7. `02_Earth_Visual_Foundation_Implementation_v3.1`
8. `03_Sky_Visual_System_Implementation_v3.1`
9. `04_Resource_Performance_Governance_v3.1`
10. `05_Earth_Camera_Motion_Music_Implementation_v3.1`
11. `06_Weather_Celestial_Context_Future_v3.1`
12. `07_Claude_Codex_Execution_Protocol_v3.1`
13. `08_Appendix_Map_and_Source_Index_v3.1`
14. `RodiO Living Earth 建设方案与差距审计计划 v1.0`
15. `RodiO P4 · Touch the Earth 下一阶段整合建设规划 v1.0`
16. Claude Code 对当前 `earth3d.js`、星空、手势和镜头系统的代码核查反馈
17. 本轮对话中的三态 UI 方案及后续修正意见
18. 既有 RodiO 视觉调色、云层、辉光、海洋、彩蛋、自动化开发与移动端问题讨论

## 1.1 信息采用规则

来源内容分为四类：

### A. 继续作为最终目标

产品哲学、真实数据四层结构、地球空间、天气、天外来信、文化时间、陪伴与记忆等内容继续有效。

### B. 继续采用，但更新实现路线

例如：

- 原“9 时段”更新为代码和 Sky 系统当前使用的 11 时段；
- 原“新建双层星空”更新为先修复现有星场，再增加真实亮星层；
- 原“完整 Director 前置重构”更新为先建立最小控制仲裁，达到触发条件后再升级 Director；
- 原“纵向拖动地球”更新为统一手势仲裁后实施。

### C. 作为历史参数或参考保留

例如：

- Bathy-3/D5b 的旧候选阶段和三日计划；
- 2026 年 5 月基于当时状态给出的贴图压缩“唯一任务”；
- v0.9—v2.0 的旧时间估算；
- 已被后续代码实现覆盖的早期行号、参数和阶段判断。

这些信息不再直接决定当前执行顺序，但保留其设计意图和验收经验。

### D. 不适合当前产品或成本收益失衡，予以 Pass

包括但不限于：

- 默认让所有歌曲都触发明显特效；
- 高频镜头切换和鼓点驱动抖动；
- 把 RodiO 做成完整 GIS/导航产品；
- 立即迁移 WebGPU；
- 手机端六自由度姿态游戏化控制；
- 未证明价值前构建高成本真实卫星群；
- 所有节日均强制换皮；
- 所有艺人均设置明显专属动画；
- 默认启用会影响音乐注意力的频繁流星、烟花和闪电；
- 在真实星空、月相、节气尚未稳定时先堆通用装饰。

Pass 不等于删除历史灵感。符合 RodiO 气质的内容可以作为隐藏彩蛋保留，但不得成为默认系统负担。

---

# 2. 最终产品原则

## 2.1 宇宙电台，不是传统播放器

RodiO 不把“找歌、点歌、管理歌单”作为默认主界面。

默认体验是：

```text
用户进入
→ 看见此刻的地球与天空
→ 系统理解此刻的情境
→ 音乐自然到来
→ 一封信短暂出现
→ 界面退出
→ 世界继续运行
```

必要控制始终存在，但只在用户需要时出现。

## 2.2 音乐是 AI 进入生活的低压入口

RodiO 不以“全天候助理”的姿态介入。

它首先学会：

- 在正确时刻递来一首歌；
- 判断用户如何用音乐处理情绪；
- 知道什么时候解释；
- 知道什么时候沉默；
- 不用廉价鼓励制造虚假陪伴；
- 不把所有状态都转化为建议。

## 2.3 真实优先，艺术负责呈现

四层数据结构统一保留：

1. **绝对真实层**：太阳、月相、星体、晨昏线、黄赤交角、潮汐和时空计算。
2. **气象真实层**：实时天气、云量、降水、湿度、气压、能见度和变化趋势。
3. **艺术加工层**：视觉质感、动画节奏、声音氛围、参数映射。
4. **文化层**：七曜、节气、节日、物候、特殊节点和情感现实。

不得把“艺术加工”伪装成“真实数据”，也不得因追求物理正确而牺牲基本可读性和性能。

## 2.4 极简界面与丰富玩法并不冲突

RodiO 的最终原则是：

> **表面安静，内部丰富；默认克制，主动探索时足够深。**

功能多少不是问题，功能是否抢夺注意力才是问题。

所有玩法必须被分为：

- 默认自动但极低打扰；
- 用户主动触发；
- 条件真实触发；
- 隐藏彩蛋；
- 开发/审计模式。

## 2.5 地球是视觉中心，音乐是情感中心

视觉不能成为炫技屏保。

地球运动必须服从音乐：

- 音乐影响地球呼吸，不操控地球跳舞；
- 镜头变化按句、按段、按歌曲或按更长时间发生；
- 不按鼓点高频抖动；
- 不为展示功能频繁切换。

---

# 3. 最终系统总架构

```text
RodiO
│
├── A. Playback Reliability Core
│   ├── Source Health
│   ├── Queue & Preload
│   ├── Error Recovery
│   ├── MediaSession
│   └── Offline Playback
│
├── B. Context Engine
│   ├── Location
│   ├── Solar Time
│   ├── Astronomy
│   ├── Weather
│   ├── Cultural Time
│   ├── Mobility / Flight
│   └── User State
│
├── C. Music Intelligence
│   ├── Candidate Retrieval
│   ├── Aesthetic Model
│   ├── Emotion Regulation Model
│   ├── Context Ranking
│   ├── Exploration Control
│   └── Prayer Response
│
├── D. Living Earth Engine
│   ├── Earth Visual Foundation
│   ├── Sky & Atmosphere
│   ├── Stars / Moon / Sun
│   ├── Clouds / Weather Visuals
│   ├── City Lights / Ocean / Tides
│   ├── Camera & Motion
│   └── Regional Detail Layer
│
├── E. Experience Orchestrator
│   ├── Full / Minimal / Earth Only UI
│   ├── Gesture Router
│   ├── Song Ritual
│   ├── Celestial Letter
│   ├── Cultural Events
│   ├── Easter Eggs
│   └── Reduced Motion / Accessibility
│
├── F. Companion & Memory
│   ├── Prayer
│   ├── Long-term Preference
│   ├── State Memory
│   ├── Letter History
│   ├── Export / Delete
│   └── Privacy Boundary
│
├── G. Runtime Platform
│   ├── Web / PWA
│   ├── Mobile Low Power
│   ├── Desktop / Tauri
│   ├── Cache & Resource Packs
│   ├── Performance Tier
│   └── Deployment / Monitoring
│
└── H. Engineering Governance
    ├── Agent Mesh
    ├── Read-only Audit
    ├── Candidate Gate
    ├── Visual Regression
    ├── Automated Tests
    ├── PR / Auto Merge
    └── Incident Alert
```

---

# 4. 完成定义

RodiO 只有在以下条件均满足后，才能被称为“完整愿景已经实现”。

## 4.1 音乐可靠

- 连续播放不因单一音乐源失败而中断；
- 队列始终可恢复；
- 切歌无明显空档；
- 浏览器、PWA、桌面端均有合理控制；
- 弱网和离线有明确降级；
- 长时运行不持续泄漏资源。

## 4.2 世界真实运行

- 时段由真实太阳时驱动；
- 地球昼夜与太阳方向一致；
- 天气状态与真实数据一致；
- 月相、节气和重要天象可计算；
- 视觉变化可追溯到 Context Engine；
- 离线时明确知道哪些状态仍真实、哪些已降级。

## 4.3 地球可看、可触摸、可探索

- 用户可拖动地球；
- 可纵向、横向、斜向操作；
- 可缩放且有安全边界；
- 手动与自动控制不冲突；
- 具有稳定镜头语言；
- 近景具备区域精度提升；
- 地球态可独立成立。

## 4.4 AI 有理解，不越界

- 选曲不是标签机械匹配；
- 能学习用户情绪处理方式；
- 祈求有响应；
- 来信语言克制；
- 记忆默认透明、可关闭、可删除；
- 不存储不必要的原始敏感表达；
- 不制造“系统知道一切”的恐惧感。

## 4.5 默认体验仍然安静

即便完成全部能力：

- 默认页面没有功能堆叠；
- 事件不会高频打断；
- 彩蛋不是常规特效；
- 用户不操作时，音乐和地球仍是主体；
- 不懂所有系统的用户也能自然使用。

---

# 5. 建设域 A：播放可靠性与音乐源治理

## 5.1 最终目标

音乐播放链路必须具备生产级容错能力，任何单点失败都不应让用户停在无声或错误页面。

## 5.2 建设内容

### 音乐源健康管理

- NCM Cookie/Token 定时健康检查；
- Spotify Access Token 和 Refresh Token 生命周期管理；
- API 限流识别；
- 指数退避；
- 失败源临时熔断；
- 可用源自动恢复；
- 不同地区可用源策略；
- 同一首歌多源匹配；
- 音质、时长和版本一致性校验。

### 队列管理

- 安全库存；
- 队列低水位自动补充；
- 空队列强制 fallback；
- 下一首预加载；
- 已播放去重；
- 短期艺人去重；
- 同类情绪密度控制；
- 祈求响应插队但不破坏当前歌曲；
- 中性缓冲曲机制；
- 离线缓存队列。

### 错误恢复

- 单曲加载失败自动重试；
- 二次失败自动换源；
- 换源失败跳过；
- 播放器状态恢复；
- Web Audio 错误记录；
- AudioContext suspended 恢复；
- 浏览器自动播放限制处理；
- WebGL 失败不影响音频；
- 页面恢复时校准歌曲进度。

### MediaSession

- 锁屏歌曲信息；
- 播放、暂停、上一首、下一首；
- 耳机按键；
- Position State；
- 专辑封面；
- 桌面媒体键；
- Tauri 系统级媒体控制。

## 5.3 验收

- 桌面连续播放 8 小时；
- 手机亮屏连续播放 2 小时；
- 至少模拟 5 类音乐源失败；
- 队列耗尽测试；
- 弱网、断网、恢复测试；
- 切后台后回前台状态一致；
- 单一源完全不可用时仍能继续；
- 日志能够追溯实际恢复路径。

---

# 6. 建设域 B：Web、PWA、移动端与桌面端

## 6.1 Web/PWA

必须完成：

- Manifest；
- Service Worker；
- 版本化缓存；
- 安装入口；
- Offline Shell；
- 资源缓存上限；
- 过期清理；
- 更新提示或静默安全更新；
- PWA 缓存与视觉候选隔离；
- 不因旧缓存导致视觉版本错乱。

## 6.2 移动端低功耗

- Page Visibility 暂停 Three.js；
- 锁屏仅保留音频；
- DPR clamp；
- 帧率分级；
- 低清纹理；
- 动态关闭透明层；
- 发热监控；
- 内存压力降级；
- iOS Safari/PWA 已知限制记录；
- Android 后台连续播放验证。

## 6.3 桌面与 Tauri

最终完成：

- Mac 独立应用；
- 无地址栏沉浸窗口；
- 菜单栏和 Dock；
- 快捷键；
- 全屏；
- 窗口尺寸适配；
- 高清资源包；
- 与 Web 共用核心状态；
- 桌面端本地缓存；
- 自动更新；
- 崩溃恢复。

## 6.4 未来终端接口

不要求立即为每个终端做完整客户端，但核心 Context、Music、Letter 和 Playback API 应避免与 DOM 强耦合，为以下终端保留能力：

- 智能音箱；
- 车机；
- 耳机；
- 空间计算/眼镜；
- 桌面小组件。

---

# 7. 建设域 C：三态 UI 与信息密度

## 7.1 三态必须全部成为正式能力

### Full / 完整态

显示：

- 时间；
- 地点；
- RodiO；
- ON AIR；
- 歌名与歌手；
- 天外来信；
- 进度条；
- 播放控制；
- 翻页入口；
- 必要异常状态。

进入条件：

- 新歌开始；
- 用户唤出；
- 播放异常；
- 用户正在操作；
- 设置或祈求打开。

### Minimal / 极简态

保留：

- 时间；
- 地点；
- RodiO / ON AIR；
- 歌名与歌手；
- 天外来信；
- 地球。

隐藏：

- 进度条；
- 按钮；
- 翻页把手；
- 次要装饰。

默认规则：

- 新歌进入 Full；
- 5 秒无操作进入 Minimal；
- UI 操作重置；
- DJ speaking 状态与 Minimal 规则协调；
- 动画使用 class 状态，不散落内联样式。

### Earth Only / 地球态

只显示：

- 地球；
- 天空；
- 大气；
- 星体；
- 天气与环境；
- 极弱的必要提示。

必须支持：

- 手动进入；
- 自动沉浸策略；
- 切歌时保持或短暂显示信息的可配置策略；
- Tap 返回；
- 无障碍退出；
- 移动端与桌面端独立设置；
- 长时间观看 Burn-in 与性能处理。

## 7.2 状态机

```text
FULL
  ├── idle timeout → MINIMAL
  ├── manual → EARTH_ONLY
  └── error/settings → FULL

MINIMAL
  ├── tap/UI intent → FULL
  ├── immersion rule → EARTH_ONLY
  └── new song policy → FULL

EARTH_ONLY
  ├── tap → MINIMAL/FULL
  ├── error → FULL
  └── user preference → stay
```

## 7.3 过渡要求

- opacity 与 pointer-events 同步；
- visibility 延迟避免误触；
- 无布局 reflow；
- Reduced Motion 可即时切换；
- DJ speaking 不与 UI 模式互相覆盖；
- 层级和焦点管理正确；
- 屏幕阅读器不会读到隐藏控件。

---

# 8. 建设域 D：统一手势系统

## 8.1 Gesture Router

所有触摸与指针行为统一进入一个仲裁器。

必须处理：

- Tap；
- Double Tap；
- Long Press；
- Drag；
- Swipe；
- Pinch；
- Pointer Cancel；
- Multi-touch；
- UI Hit Test；
- Page Swipe；
- Earth Rotate；
- 控件唤出；
- 地球态退出。

## 8.2 优先级

```text
明确 UI 控件
>
系统级/浏览器安全手势
>
双指 Pinch
>
高速定向 Page Swipe
>
地球 Drag
>
短触 Tap
>
长按隐藏操作
```

## 8.3 冲突处理

当前 `pages-container` 纵向翻页、空白点击唤控件、地球纵向旋转必须统一判定。

建议：

- 慢拖 = 地球；
- 快速、长距离、纵向占优 = 翻页；
- 短触、低位移 = 唤控件；
- UI 起点 = UI；
- 屏幕边缘可提高翻页权重；
- 地球投影区提高 Drag 权重；
- 多指直接取消单指意图。

## 8.4 验收矩阵

- 桌面鼠标；
- Mac 触控板；
- iPhone Safari；
- iPhone PWA；
- Android Chrome；
- 平板；
- 横屏；
- 竖屏；
- 快速连续操作；
- 切歌中操作；
- 页面切换中操作。

---

# 9. 建设域 E：地球交互、相机与运动

## 9.1 控制架构策略

不立即全量重写现有 Camera Preset、Composition 和 Sequence。

先完成最小稳定仲裁：

```js
mode: auto | dragging | inertia | holding | returning
```

当出现以下真实问题时，再升级为完整 Earth Director：

- 多个系统持续争抢 camera/FOV；
- Journey、交互和音乐镜头无法协调；
- 新镜头配置语义继续分裂；
- 回归状态难以确定；
- 调试无法判断控制源。

最终目标仍是统一 Director，但不是为了抽象而抽象。

## 9.2 用户操作

全部完成：

- 横向旋转；
- 纵向旋转；
- 斜向旋转；
- Pinch；
- Wheel；
- 惯性；
- 纬度安全边界；
- 缩放边界；
- 自动回归；
- Reset；
- Hold；
- 移动端灵敏度；
- 近景低灵敏度；
- Reduced Motion。

## 9.3 自动运动 Profile

必须具备：

- Gentle Clockwise；
- Gentle Counter-clockwise；
- Vertical Drift；
- Diagonal Left；
- Diagonal Right；
- Polar Drift；
- Auto Reverse；
- Hold；
- Approach；
- Retreat；
- Flyby；
- Orbital Arc。

## 9.4 镜头语言

正式镜头库：

### 基础构图

- Globe；
- Portrait Marble；
- Hemisphere；
- Far Orbit；
- Ocean Expanse；
- Polar Diagonal；
- City Anchor。

### 电影构图

- Horizon Skim；
- Low Orbit；
- Limb Hero；
- Planet Rise；
- Half Planet；
- Close Flyby；
- Deep Space。

### 地理视角

- 用户所在地；
- 对跖点；
- 东亚；
- 太平洋；
- 欧洲；
- 非洲；
- 南北美；
- 澳洲；
- 北极；
- 南极；
- 印度洋；
- 大西洋；
- 用户祈求地点。

## 9.5 镜头与音乐

分三级完成：

1. 播放状态：播放、暂停、结束、切歌。
2. 音乐气质：ambient、钢琴、电子、爵士、古典、城市夜景等。
3. 地点与语义：歌名、歌手、祈求、地理情境。

必须遵守：

- 不高频切换；
- 不按鼓点抖动；
- 不让一首歌展示所有镜头；
- 用户接管后暂停自动镜头；
- 自动恢复不抢夺控制。

---

# 10. 建设域 F：Earth Visual Foundation

## 10.1 白天地球

最终达到：

- 陆地层次自然；
- 海洋具有浅海、陆架、深海结构；
- 不像教材地图；
- 沙漠不过曝；
- 高原、森林、平原可区分；
- 小岛与近岸领土感可见；
- 珊瑚礁不过度统一发亮；
- 极地自然；
- 近景不暴露粗糙拼接。

D5b/Bathy 路线可继续作为海洋处理依据，但不再限制后续使用更高质量数据或区域层。

## 10.2 夜晚地球

必须形成：

```text
低亮度地貌
+ 有社会结构的城市灯光
+ 冷暗海洋
+ 干净黑位
```

城市灯光包括：

- 商业区冷白；
- 居民区暖黄；
- 路灯网络；
- 深夜稀疏灯；
- 工作日/周末节奏；
- 节日文化偏移；
- 不全局发白；
- 不霓虹化。

## 10.3 云层

分层实现：

1. 全球基础云；
2. 慢速方向运动；
3. 与太阳方向一致的明暗；
4. 夜间低亮度；
5. 天气云量驱动；
6. 降雨区域密度；
7. 极端天气降级；
8. 高空背景卷云与地球云层区分。

## 10.4 大气与辉光

- 薄；
- 有方向；
- 不像 UI 描边；
- 不形成带子感；
- 正午、日出、落日、夜间差异；
- 不被 Bloom 过度放大；
- 与 Sky 使用同一太阳方向；
- 与地球缩放保持稳定屏幕观感。

## 10.5 海洋

- 白天水深层次；
- 夜晚更黑；
- 海岸过渡；
- 太阳镜面高光；
- 月相与潮汐反光；
- 不用整片蒙版表达浅海；
- 不因主题切换破坏底层地形。

## 10.6 11 时段

最终统一：

```text
deepNight
dawn
sunrise
earlyMorning
morning
noon
afternoon
goldenApproach
sunset
evening
lateEvening
```

产品方案旧“九段”作为情绪描述保留，运行系统以 11 时段为准。

每个时段统一控制：

- Sky；
- Earth grade；
- 城市灯光；
- 云；
- Atmosphere；
- Stars；
- Sun direction；
- Motion weight；
- UI contrast；
- 天外来信语言权重。

---

# 11. 建设域 G：Sky、星空、太阳与月亮

## 11.1 Sky

完成：

- skyMesh；
- 双 LUT；
- GPU mix；
- OKLab 或经过验证的感知插值；
- 11 时段锚点；
- 太阳方向场；
- CSS fallback；
- Tone Mapping；
- Sky-Earth 同源；
- 移动端低成本版本。

## 11.2 现有星空先修复

代码已存在程序化 Points 和 twinkle 雏形。

首先审计并修复：

- scene 挂载；
- clipping；
- render order；
- depth；
- frustum；
- opacity；
- DPR；
- point size；
- skyMesh 遮挡；
- Bloom；
- Tone Mapping。

不得平行新建重复系统。

## 11.3 最终星空分层

修复后升级为：

1. 程序化远层星尘；
2. 真实亮星层；
3. Yale BSC 或等价可靠星表；
4. 赤道坐标→地平坐标；
5. 月相可见度；
6. 云量和透明度；
7. 光污染；
8. 低纬/高纬差异；
9. 银河条件出现；
10. 日食时短暂星空。

真实亮星层和程序化星尘职责不同，不互相替代。

## 11.4 太阳

- 真实高度角；
- 真实方位角；
- 与地球光照一致；
- 大气散射颜色；
- 低角度视觉表达；
- 不必在每个镜头显示太阳实体；
- 日食能力；
- 离线可计算。

## 11.5 月亮

- 月相；
- 位置；
- 亮度；
- 色温；
- 月满星稀；
- 月黑星密；
- 月食；
- 中秋文化例外；
- 水面倒影；
- 移动端简化模型。

## 11.6 行星和银河

最终纳入，但采用渐进表达：

- 第一层：准确位置与亮度点；
- 第二层：行星冲日等事件；
- 第三层：必要时简单视觉轮廓；
- 不做高精度行星模型作为前置；
- 银河仅在真实条件允许时出现。

---

# 12. 建设域 H：Regional Detail Layer

## 12.1 目标

全球地球保持稳定基线，用户进入 Low Orbit、City Focus 或“飞去某地”时，区域精度平滑提升。

## 12.2 三层 LOD

```text
远景：全球基线纹理
中近景：静态区域合成层
极近景：动态/按需瓦片层
```

## 12.3 数据与技术路线

- 全球 Base：现有 D5b/Blue Marble 路线；
- 陆地：BMNG 或后续更合适公共数据；
- 海洋：GEBCO；
- 海岸线：GSHHG；
- 动态区域：Mapbox Satellite 或经评估的替代源；
- 色调：预计算 LUT；
- 边界：bounds-driven；
- 缓存：session memory；
- 网络失败：Base 回退；
- 条款：禁止不合规持久化瓦片。

## 12.4 预加载

- 用户位置授权后预加载所在区域；
- “飞去某地”时预加载目标区域；
- 相机缩放阈值只触发显示，不临时发起大量请求；
- Zoom 7 为默认安全层；
- Zoom 8 按需；
- 移动端流量提示或低流量模式。

## 12.5 验证路线

- Japan benchmark；
- 海岸、城市、山地、岛屿、海洋边界；
- 色调一致；
- seam；
- LOD 淡入淡出；
- 反复缩放；
- 弱网；
- 缓存；
- API 额度；
- 全球 bounds 复用。

## 12.6 替代路线

若动态瓦片受条款、成本或性能限制：

1. 静态区域包；
2. 用户常用城市离线区域；
3. 自托管合法公开数据；
4. 仅桌面启用动态层；
5. 移动端保持静态中近景。

目标是实现区域精度，不绑定单一供应商。

---

# 13. 建设域 I：天气与环境

## 13.1 数据层

- 国内天气源；
- 海外天气源；
- 多源 fallback；
- 同城服务端缓存；
- 前台轮询；
- 后台暂停；
- 页面恢复立即刷新；
- 变化检测；
- 失败保留最后可信状态；
- 离线标记；
- API 成本监控。

## 13.2 天气状态

至少覆盖：

- 晴；
- 多云；
- 阴；
- 毛毛雨；
- 小雨；
- 中雨；
- 大雨；
- 暴雨；
- 雷暴；
- 轻雪；
- 中雪；
- 大雪；
- 雾；
- 霾；
- 强风；
- 雨后；
- 天气正在变化。

## 13.3 变化过程

RodiO 不只处理“现在是什么”，还处理“正在变成什么”。

```text
气压下降/湿度上升/云量增加
→ 空气与天空先变化
→ 当前歌曲继续
→ 下一首情绪转向
→ 来信知道刚才发生了什么
```

## 13.4 视觉映射

天气可以影响：

- Sky LUT；
- 云量；
- 云速；
- 大气透明度；
- 星星；
- 落日类型；
- 雨雪前景；
- 地球湿润感；
- 城市灯光晕散；
- 海洋；
- UI 对比度。

不得让天气一次性直接覆盖全部基线参数，应使用权重叠加和安全范围。

## 13.5 环境声音

- 雨；
- 风；
- 虫鸣；
- 海潮；
- 雪的静默；
- 高空；
- 音量 3%—8%；
- 允许关闭；
- 与音乐频谱避让；
- 不循环出明显接缝；
- 不让用户明确听见“音效素材”。

---

# 14. 建设域 J：时间、天文与文化

## 14.1 真实太阳时

所有时段基于经纬度与太阳计算，不以行政时区硬编码。

必须处理：

- 定位拒绝；
- 默认城市；
- 极昼极夜；
- 高纬度无标准日出；
- 跨时区移动；
- 夏令时仅用于显示，不用于太阳状态；
- 缓存与离线。

## 14.2 七曜

- 本地计算；
- 轻量参数权重；
- 零点交接；
- 周日→周一特殊权重；
- 可沉默；
- 不弹窗；
- 不把天体符号做成明显 UI。

## 14.3 节气与七十二候

- 太阳黄经；
- 二十四节气；
- 环境参数；
- 选曲权重；
- 来信词库；
- 七十二候作为语言素材；
- 地区与气候不匹配时谨慎表达；
- 不把古代物候当作当地实时事实。

## 14.4 节日

三档保留：

- 主节日：完整但克制的主题；
- 扩展节日：少量参数偏移；
- 彩蛋节日：条件触发。

必须支持地域权重、用户文化偏好和关闭。

## 14.5 特殊天象

- 日食；
- 月食；
- 流星雨；
- 极光；
- 行星冲日；
- 极昼极夜；
- 真实条件驱动；
- 无条件不显示；
- 数据失败不伪造。

## 14.6 Astronomy Visual Bridge

`astronomy.js` 或统一 Astronomy Context 应成为视觉、选曲和来信共享的数据桥：

```js
{
  sun,
  moon,
  solarTerm,
  weekdayCelestial,
  season,
  eclipse,
  meteorShower,
  auroraProbability,
  daylight,
  culturalNodes
}
```

避免视觉、音乐和来信各自计算一套不一致状态。

---

# 15. 建设域 K：选曲智能

## 15.1 核心问题

系统不能只理解“用户现在忧郁”，还必须理解：

> 用户通常如何通过音乐处理忧郁。

## 15.2 选曲上下文

候选排序至少考虑：

- 时段；
- 太阳状态；
- 天气；
- 天气趋势；
- 月相；
- 节气；
- 七曜；
- 地点；
- 移动状态；
- 当前歌曲；
- 最近播放；
- 用户明确祈求；
- 用户审美；
- 用户情绪处理偏好；
- 探索度；
- 熟悉度；
- 歌曲质量；
- 音源可用性。

## 15.3 审美模型

不能只依赖流派。

需要学习：

- 用户接受的声音密度；
- 人声类型；
- 语言；
- 制作年代；
- 旋律强度；
- 情绪直接性；
- 实验性；
- 歌曲长度；
- 熟悉/陌生比例；
- 不同场景的偏好差异。

## 15.4 情绪调节模型

区分：

- 同频沉浸；
- 温和转向；
- 提振；
- 安静陪伴；
- 释放；
- 维持专注；
- 降低刺激。

用户可以通过跳过、听完、重复、祈求和反馈逐渐让系统学习。

## 15.5 探索控制

RodiO 不能越来越窄。

必须有：

- 新歌探索额度；
- 艺人去重；
- 地区多样性；
- 年代多样性；
- 非热门歌曲；
- 用户安全区；
- 情境适配；
- 失败后回到稳定候选。

## 15.6 可解释性

默认不展示“推荐理由面板”。

解释通过天外来信完成：

- 不说模型；
- 不罗列标签；
- 不像说明书；
- 不夸大理解；
- 不直接暴露敏感推断。

---

# 16. 建设域 L：天外来信

## 16.1 定位

来信不是：

- 歌曲简介；
- 推荐算法说明；
- 心理咨询；
- 每首歌的 AI 小作文。

它是此刻世界状态与这首歌之间的一句话。

## 16.2 生成架构

分层控制成本与质量：

### 模板层

- 普通时刻；
- 本地生成；
- 零延迟；
- 大量高质量人工模板；
- 变量组合；
- 防重复。

### 中模型层

- 节气、天气变化、文化节点；
- 预生成；
- 成本较低；
- 语言风格校验。

### 高模型层

- 祈求；
- 稀有时刻；
- 复杂记忆呼应；
- 严格隐私上下文；
- 结果缓存；
- 超时 fallback。

## 16.3 动画

完整支持：

出现：

- 凝结；
- 曝光；
- 降落；
- 星聚。

离开：

- 离散；
- 风散；
- 蒸发。

要求：

- 不逐字打字；
- 十秒不是硬规则，可按文本长度调整；
- Reduced Motion 简化；
- 地球态可选择不显示；
- 不遮挡主要大陆或歌名。

## 16.4 质量治理

- 禁止油腻；
- 禁止说教；
- 禁止假装全知；
- 禁止每封都很“诗”；
- 允许平常；
- 允许一句事实；
- 允许沉默；
- 重复率检测；
- 敏感内容过滤；
- 模板和模型统一语气。

---

# 17. 建设域 M：祈求、“此刻”与飞去某地

## 17.1 “此刻”入口

- 隐蔽但可发现；
- 无多余说明；
- 支持文字；
- 支持取消；
- 不强制展示发送成功；
- 但必须在可访问性层面有状态反馈。

## 17.2 祈求

用户可表达：

- 情绪；
- 状态；
- 想听的方向；
- 想被陪伴的方式；
- 不想听什么。

系统：

- 不打断当前歌；
- 下一首响应；
- 即将结束时用中性缓冲；
- 来信不直接复述；
- 不把祈求当诊断；
- 失败时使用稳定 fallback。

## 17.3 飞去某地

- 地名解析；
- 歧义处理；
- 地球转场；
- 目标时段；
- 目标天气；
- 目标季节；
- 目标音乐；
- RDL 预加载；
- 结束后返回用户所在地或保持；
- 不做导航；
- 不显示复杂地图 UI。

---

# 18. 建设域 N：一首歌的完整仪式

完整仪式保留，但允许用户设置简化。

```text
来信出现
→ 来信停留
→ 来信离开
→ 地球进入歌曲运动
→ 世界状态持续变化
→ 结束前自然减速
→ 回到新的“此刻”
→ 短暂停留
→ 下一封信
```

关键修正：

- “回到原点”不一定是同一经纬度，应由当前模式决定；
- 用户主动拖动后，不强制回到固定原点；
- Journey 模式可连续；
- Earth Only 可省略来信；
- 短歌曲不执行完整长动画；
- 切歌和失败不能留下半完成状态。

---

# 19. 建设域 O：陪伴与记忆

## 19.1 原则

被监视与被记得的差别来自：

- 用户知情；
- 存储最小化；
- 使用克制；
- 不突然暴露；
- 可查看；
- 可删除；
- 可关闭。

## 19.2 数据层

建议分开：

### 播放历史

歌曲、时间、跳过、听完。

### 来信历史

时间与文字，可选歌曲关联。

### 祈求记录

默认不保存原文；保存结构化摘要需用户明确开启。

### 审美记忆

长期偏好向量或摘要。

### 情境记忆

特定雨夜、旅行、生日等低频事件，必须明确边界。

## 19.3 用户权利

- 开启/关闭；
- 查看；
- 删除；
- 全部清空；
- 导出；
- 本地优先；
- 云同步可选；
- 保留期限；
- 不将记忆用于广告。

## 19.4 记忆使用

- 低频；
- 不直接说“你三个月前说过”；
- 不制造惊吓；
- 用户主动询问时可以明确展示来源；
- 负面状态不长期固化为人格标签。

---

# 20. 建设域 P：彩蛋与隐藏玩法

## 20.1 定位

彩蛋保留为 RodiO 的探索深度，但不成为默认建设主轴。

## 20.2 保留类别

- 歌名/歌词意象；
- 情绪反差；
- 艺人专属；
- 风格/BPM；
- 特殊时间；
- 稀有天象；
- 人工主题；
- 故障/异常风格彩蛋。

## 20.3 收缩规则

不适合的旧设计予以 Pass 或改造：

- “任何国歌自动转国家”可能引发识别与政治问题，改为严格白名单或不做；
- 高频 BPM 直接加速地球容易游戏化，只做轻微权重；
- 重金属触发不规律自转会破坏系统稳定，改为环境强度候选；
- 纯钢琴提高下雨概率属于伪造天气，改为不改变真实天气，只改变艺术层；
- 《晴天》不能覆盖真实天气主状态，只能进入明确的歌曲彩蛋视觉层，并与真实层区分；
- 卡通化彩蛋只能人工确认后进入隐藏模式；
- 歌手专属规则需要版权、准确性和审美审查；
- 不建立无限增长的硬编码 if/else，使用规则数据库。

## 20.4 触发治理

- 冷却期；
- 最近触发去重；
- 用户可关闭；
- 不与真实事件冲突；
- 视觉安全边界；
- 性能等级；
- 日志；
- 截图验收。

---

# 21. 建设域 Q：潮汐、城市社会时间与飞行模式

## 21.1 潮汐

- 沿海用户；
- 潮汐数据；
- 缓存；
- 月相关系；
- 水色；
- 地平线；
- 倒影；
- 不夸大到可见海啸式变化；
- 无数据时关闭而非伪造。

## 21.2 城市社会时间

基于城市规模、时段、工作日/周末形成灯光权重。

第一版可以模型化，不宣称逐栋楼真实。

最终明确标注：

- 天文真实；
- 城市宏观模型；
- 艺术随机细节。

## 21.3 飞行模式

识别：

- 短时间大位移；
- 定位漂移过滤；
- 用户确认或高置信度；
- 隐私和耗电限制。

表现：

- 高空天空；
- 云在下方；
- 城市灯光缝隙；
- 特殊来信；
- 飞行后目的地上下文切换。

---

# 22. 建设域 R：离线状态

## 22.1 离线仍可运行

本地可计算：

- 太阳；
- 月相；
- 星体近似位置；
- 节气；
- 七曜；
- 时段；
- 已缓存位置；
- 已缓存歌曲；
- 已缓存来信模板。

不可保证：

- 实时天气；
- 最新潮汐；
- 在线音乐源；
- 云端 AI 来信；
- 地理搜索。

## 22.2 离线表达

- 不显示错误堆栈；
- 不假装天气仍是最新；
- 使用离线 Context 标志；
- 来信语言变简单；
- “今晚没有信号，但宇宙还在”可作为极低频模板，不每次固定重复。

---

# 23. 建设域 S：资源与性能治理

## 23.1 资源目录

保留并强化：

```text
production/
candidates/
source/
archive/
tmp/
masks/
clouds/
sky/
stars/
rdl/
audio-ambience/
themes/
```

## 23.2 分辨率与压缩

- 移动安全包；
- 标准桌面包；
- 高清桌面包；
- KTX2/Basis；
- WebP/AVIF 用于 DOM 层；
- 资源 hash；
- 不同设备动态选择；
- 不以“8K”模糊命名，记录实际尺寸。

## 23.3 Resource Pack

```text
Base UI Pack
Playback Pack
Earth Mobile Pack
Earth Standard Pack
Earth HD Pack
Atmosphere Pack
Astronomy Pack
Weather Pack
RDL Region Pack
Cultural Theme Pack
Experimental Pack
```

## 23.4 性能档位

- High；
- Medium；
- Low；
- Reduced Motion；
- Battery Saver；
- Offline。

动态依据：

- GPU；
- DPR；
- 初始帧率；
- 设备内存；
- 发热；
- 电池；
- 页面可见性。

## 23.5 性能目标

- 高性能桌面 60 FPS；
- 集成显卡 45—60 FPS；
- 高端手机 45—60 FPS；
- 普通手机不低于 30 FPS；
- 低功耗播放模式可低至 15—24 FPS；
- 交互期间优先保证响应；
- 后台不渲染；
- 资源切换不造成明显停顿；
- 内存稳定，无持续增长。

---

# 24. 建设域 T：安全、隐私与合规

## 24.1 位置

- 明确授权；
- 仅在需要时读取；
- 精度分级；
- 飞行与天气功能说明；
- 可使用手动城市；
- 不默认长期保存精确轨迹。

## 24.2 情绪与祈求

- 不作医疗诊断；
- 不构建敏感人格标签；
- 原文最小保存；
- 云模型传输明确；
- 可选择本地模板；
- 删除和导出；
- 对极端风险内容有安全响应，但不破坏整体克制设计。

## 24.3 第三方 API

- 数据最小化；
- 密钥服务端；
- 配额；
- 供应商条款；
- 瓦片缓存合规；
- 音乐版权与播放授权；
- 分享卡不默认嵌入受版权保护的专辑图。

---

# 25. 建设域 U：审计、测试、部署与自动化

## 25.1 继续采用 v3.1 执行纪律

每个施工单元仍遵守：

```text
只读审计
→ 候选
→ 接入但不默认
→ 自动测试
→ 人工视觉验收
→ Production
→ Commit/PR
→ 基线归档
```

“最终目标全部完成”不等于单轮混改。

## 25.2 自动化开发

利用已建立的 Agent Mesh：

- 计划拆分；
- 自动 Issue；
- Claude Code 执行；
- PR；
- Codex Review；
- 自动修复循环；
- 规则门禁；
- 自动合并；
- 步骤推进；
- 飞书异常提醒。

## 25.3 测试体系

### 单元测试

- 时间；
- 天文；
- 天气映射；
- 队列；
- 状态机；
- 手势意图；
- 选曲排序；
- 记忆权限。

### 集成测试

- 播放+来信；
- 天气+视觉；
- 手势+UI；
- 地球+镜头；
- RDL+缩放；
- 离线；
- PWA 更新。

### 视觉回归

- 11 时段；
- 5 个锚点；
- 多天气；
- 多镜头；
- 多设备；
- 彩蛋；
- 节日；
- 高低性能档。

### 长时测试

- 2h；
- 8h；
- 24h soak；
- 切后台；
- 弱网波动；
- API 失败；
- GPU context lost；
- Service Worker 更新。

## 25.4 监控

- 播放失败率；
- 队列耗尽率；
- API 延迟；
- 来信生成失败；
- FPS；
- 内存；
- 资源加载；
- Context freshness；
- 自动恢复次数；
- 用户主动关闭功能比例。

---

# 26. 全部工作流与依赖拓扑

本规划不采用“做到某阶段就结束”的版本观，而采用必须全部关闭的工作流。

## Workstream 1：可靠性与平台

包括：

- Playback；
- PWA；
- MediaSession；
- Offline；
- Desktop；
- Monitoring。

它为全部其他系统提供运行基础。

## Workstream 2：视觉世界

包括：

- Earth；
- Sky；
- Atmosphere；
- Stars；
- Moon；
- Sun；
- Cloud；
- Weather Visual；
- RDL。

## Workstream 3：交互与镜头

包括：

- 三态 UI；
- Gesture Router；
- Drag/Pinch；
- Motion；
- Camera；
- Earth Only；
- Journey。

## Workstream 4：真实 Context

包括：

- Location；
- Solar Time；
- Weather；
- Astronomy；
- Cultural Time；
- Tide；
- Flight。

## Workstream 5：音乐与 AI

包括：

- Selection；
- Prayer；
- Letter；
- Memory；
- Exploration；
- Feedback。

## Workstream 6：文化与隐藏深度

包括：

- 七曜；
- 节气；
- 节日；
- 稀有事件；
- 彩蛋；
- 分享与历史。

## 26.1 可并行关系

可并行：

- 播放可靠性与视觉候选；
- 天文计算库与 UI 三态；
- 来信模板库与 Earth 性能治理；
- RDL 预处理与天气数据架构；
- Tauri 包装与 Web 核心测试。

不可同提交但可不同分支并行：

- Sky 与 Gesture；
- Earth texture 与 Letter；
- Weather API 与 Camera Profile。

## 26.2 必须串行的关键依赖

```text
Gesture Audit
→ Gesture Router
→ Earth Drag
→ Inertia/Pinch
→ Auto Return
→ Journey
```

```text
Star Audit
→ Existing Star Fix
→ Real Bright Stars
→ Light Pollution
→ Milky Way
```

```text
Solar Context
→ 11 Time Modes
→ Sky-Earth Direction
→ Weather Overlay
→ Cultural Overlay
```

```text
Playback Reliability
→ Stable Queue
→ Prayer Response
→ Pre-generated Letter
→ Full Song Ritual
```

```text
Global Earth Stability
→ Low Orbit Validation
→ RDL
→ Fly-to-place
```

---

# 27. 全局任务关闭清单

以下任务不得仅以“已规划”关闭，必须有实现和验收证据。

## Core

- [ ] 播放源健康与自动 fallback
- [ ] 队列与预加载
- [ ] WebGL/Audio 恢复
- [ ] PWA 与 MediaSession
- [ ] Offline
- [ ] Tauri

## UI / Interaction

- [ ] Full
- [ ] Minimal
- [ ] Earth Only
- [ ] Gesture Router
- [ ] Drag
- [ ] Pinch
- [ ] Swipe
- [ ] Auto Return
- [ ] Accessibility

## Earth

- [ ] Day Master
- [ ] Night Master
- [ ] Ocean
- [ ] City Lights
- [ ] Cloud
- [ ] Atmosphere
- [ ] 11 Time Modes
- [ ] Terminator
- [ ] Regional Detail

## Sky

- [ ] SkyMesh/LUT
- [ ] Existing Stars Fix
- [ ] Real Bright Stars
- [ ] Sun
- [ ] Moon
- [ ] Light Pollution
- [ ] Milky Way
- [ ] Planets
- [ ] Rare Events

## Context

- [ ] Solar Time
- [ ] Weather
- [ ] Weather Trend
- [ ] Astronomy Bridge
- [ ] Seven Luminaries
- [ ] Solar Terms
- [ ] Festivals
- [ ] Tide
- [ ] Flight

## Music / AI

- [ ] Context Ranking
- [ ] Aesthetic Model
- [ ] Emotion Regulation
- [ ] Exploration
- [ ] Prayer
- [ ] Celestial Letter
- [ ] Letter History
- [ ] Memory
- [ ] Share Card

## Quality

- [ ] Performance tiers
- [ ] Resource governance
- [ ] Visual regression
- [ ] Long-run tests
- [ ] Privacy controls
- [ ] API cost controls
- [ ] Monitoring
- [ ] Automated delivery

---

# 28. 风险与替代路线

## 28.1 iOS 后台播放限制

主路线：PWA + MediaSession。  
替代：Tauri/Mac；未来原生 iOS 壳；明确已知限制。

## 28.2 Three.js 手机性能

主路线：性能档位、低清资源、低帧率播放模式。  
替代：静态 Earth fallback、关闭透明层、降低 DPR。

## 28.3 真实星表复杂

主路线：真实亮星坐标。  
替代顺序：

1. 修复程序化星场；
2. 加少量真实亮星；
3. 扩充；
4. 光污染与银河后置。

不删除最终目标。

## 28.4 天气 API 成本或稳定性

主路线：多源+服务端缓存。  
替代：降低刷新频率、城市级缓存、保留最后状态、用户手动刷新。

## 28.5 Mapbox 条款或成本

主路线：合规 Session Cache。  
替代：静态区域包、自托管公共数据、桌面限定、供应商切换。

## 28.6 AI 来信成本与质量

主路线：模板+中模型+高模型分层。  
替代：更多本地模板、缓存、低频高模型、离线句库。

## 28.7 系统复杂度

主路线：Context Engine 和 Orchestrator。  
替代：发现真实冲突后逐步统一 Director，不预先全量重构。

## 28.8 单人开发负担

- 自动化计划；
- 小任务闭环；
- 并行审计；
- 资源生成脚本；
- 回归自动化；
- 不重复手工测试；
- 文档作为系统契约；
- 连续失败两次必须重新评估路线。

---

# 29. 当前优先施工入口

最终目标虽是全部完成，但当前应从最高依赖节点开始。

下一项正式任务应是：

# Unified Current-State Audit

这不是“只做一个小阶段”，而是为全部总任务建立真实基线。

审计必须覆盖：

1. Playback 当前稳定性；
2. PWA/MediaSession；
3. UI 三态基础；
4. 手势；
5. Earth camera/quaternion/FOV；
6. Stars；
7. 11 时段；
8. Weather/Astronomy 现有代码；
9. Letter/Prayer；
10. Resource Pack；
11. RDL；
12. Agent Mesh；
13. 已完成与文档过期项。

输出：

- Current-State Matrix；
- Source-of-Truth Map；
- Code Ownership Map；
- Conflict Matrix；
- Final Gap Matrix；
- Workstream Dependency Graph；
- 自动任务拆分清单。

审计后，不重新缩小目标，而是以结果更新本总纲中的“当前状态”字段并开始关闭全部任务。

---

# 30. 来源覆盖与去留表

| 来源 | 核心内容 | 本总纲处理 |
|---|---|---|
| 产品方案 v4 | 宇宙电台、真实四层、天气、天文、文化、来信、祈求、记忆、彩蛋 | 作为最终产品愿景主来源 |
| 开发路线 v3 | 稳定、移动、地球、此刻、来信、文化、Mac、陪伴 | 保留建设域，旧版本顺序不作为最终终点 |
| AI 陪伴文章 | 音乐入口、低打扰、理解情绪处理方式、记忆边界 | 作为 AI 与陪伴原则 |
| RDL | 三层 LOD、数据源、预加载、缓存、LUT | 正式纳入区域精度工作流 |
| Master Roadmap v3.1 | Earth/Sky/资源/镜头/天气/天体边界 | 作为工程治理依据 |
| Workflow | 单轮最小任务、审计→候选→验收 | 继续强制执行 |
| Earth Foundation | 白天、夜晚、海洋、云、大气、11 时段 | 全部纳入视觉工作流 |
| Sky v3.1 | 11 时段、LUT、星场、Tone Mapping | 继续作为 Sky 技术依据 |
| Resource Governance | 目录、分辨率、缓存、性能 | 全部纳入 |
| Camera Motion | 镜头语言和音乐呼吸 | 全部纳入并扩展交互 |
| Weather/Celestial | 天气、七曜、产品 v3 附录 | 从“冻结远期”改为“总目标待完成” |
| Execution Protocol | 审计、候选、提交与禁止项 | 继续强制 |
| Living Earth v1 | 交互、镜头、空间、审计 | 吸收；修正 Director 和星空误判 |
| Touch the Earth v1 | 三态、Gesture、最小仲裁 | 作为交互工作流实施依据 |
| Claude Code 反馈 | 星空已存在、手势冲突、避免大重构、天文桥 | 全部吸收 |
| 历史视觉讨论 | 11 时段调色、海洋、云、辉光、彩蛋 | 作为视觉验收经验 |

---

# 31. 最终判断

RodiO 的完整建设不是一个可以靠“加完功能”完成的项目。

真正的完成，是它能够同时做到：

- 音乐可靠地来；
- 世界真实地变化；
- 地球可以被触摸；
- 界面知道退后；
- AI 知道如何回应；
- 记忆知道保持距离；
- 丰富的系统默认保持安静；
- 用户使用很久之后，仍然能发现新的东西。

最终产品应让用户产生这样的感受：

> 我不是打开了一个播放器。  
> 我只是来到这里，看见此刻的地球，然后一首歌来了。

本总纲以关闭全部任务为目标。任何建设域不得因“不是当前阶段”而从最终任务中消失；任何实现失败也不得直接删除目标，而应转入替代路线、重新验证并继续推进。

RodiO 的开发可以分解，愿景不能被分割。
