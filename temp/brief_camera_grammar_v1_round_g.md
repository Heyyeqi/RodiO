# RodiO 动态地球镜头系统 G轮:接入真实播放(自动选构图+运动原语)

本轮阶段:生成候选 + 接入候选
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件
允许 commit:否,除非我后续明确批准(commit 由我这边在你验证通过后统一处理)
回滚方案:全部改动在 `?earthCandidate=cameraGrammarAuto` gate 后面,不影响默认行为和其他候选

---

## 背景

A-F轮做完了10个构图、8种持续运动原语、3个镜头序列,全部还只能在debug面板手动触发。这轮要接上真实播放——歌曲开始时根据`rhythmic_motion`自动选一个构图+运动原语,歌曲快结束时自动切回默认视角。**这次只做最简单能跑起来的规则,不做评分引擎/去重/日常模式那套完整体系**,先验证"自动联动"这个机制本身顺畅,后续再精调规则。

**已知的分支说明**:本地这个working tree已经在你开始改之前rebase到最新main了,不用你操心git部分,你只管改代码。

## 现状(已核实)

- `_precomputeMotion`(`earth3d.js`)已经有一套通过trackKey变化检测切歌的成熟模式(`_lastTrackKey`比对,`${name}::${artist}`格式),这次照抄同样的写法
- `window.__rodioVisualState.currentTrack.rhythmic_motion`已经在多处后端路径正确挂载,前端也有保留富字段不被覆盖的逻辑——直接复用这个字段,不需要新增后端管道
- `transitionToComposition()`/`setGramPrimitive()`都通过`Object.assign(earth3dApi,{...})`导出,这次新的驱动函数必须放在`createEarth3D()`内部(能直接调用这两个内部函数的作用域),**不能放在外层**——这是D轮`breathe`崩溃那次的教训:外层函数访问不到内层作用域的东西,只能反过来
- `_gramMotion.enabled`目前只在`earthCandidate === 'cameraGrammarV1'`时为true

## 要做的事

### 1. 简单规则的构图/运动原语选择(3档)

```js
const GRAM_AUTO_TIERS = [
  { max: 0.25, composition: 'homeGlobe',     primitive: 'hold' },
  { max: 0.5,  composition: 'portraitMarble', primitive: 'longitudeDrift' },
  { max: Infinity, composition: 'farOrbit',   primitive: 'diagonalDrift' },
]
```
(阈值和构图/原语搭配都是起点,不需要现在调完美,后续轮次再精调)

### 2. 歌曲生命周期驱动函数(新增,必须放在`createEarth3D()`内部)

```js
let _gramAutoPilot = (function () {
  const m = { enabled: false, lastTrackKey: '', returnedHome: false }
  if (typeof window !== 'undefined') {
    m.enabled = new URLSearchParams(window.location.search).get('earthCandidate') === 'cameraGrammarAuto'
  }
  return m
})()

function _updateGramAutoPilot() {
  if (!_gramAutoPilot.enabled) return
  const vs = window.__rodioVisualState || {}
  const cur = vs.currentTrack
  const trackKey = cur ? `${String(cur.name || '').trim()}::${String(cur.artist || '').trim()}` : ''
  if (!trackKey) return
  const dur = cur?.duration_ms ? cur.duration_ms / 1000 : (vs.duration || 0)
  const progress = vs.progress || 0

  // 切歌检测(照抄 _precomputeMotion 已验证过的写法)
  if (trackKey !== _gramAutoPilot.lastTrackKey) {
    _gramAutoPilot.lastTrackKey = trackKey
    _gramAutoPilot.returnedHome = false
    const rm = typeof cur?.rhythmic_motion === 'number' ? cur.rhythmic_motion : 0.344
    const tier = GRAM_AUTO_TIERS.find((t) => rm <= t.max)
    transitionToComposition(tier.composition, { duration: 5, envelope: 'easeInOutCubic' })
    setGramPrimitive(tier.primitive)
    return
  }

  // 收束+回锚点:歌曲剩余不到12秒时，切回 homeGlobe + hold
  const nearEnd = dur > 20 && (dur - progress) <= 12
  if (nearEnd && !_gramAutoPilot.returnedHome) {
    _gramAutoPilot.returnedHome = true
    setGramPrimitive('hold')
    transitionToComposition('homeGlobe', { duration: Math.max(3, dur - progress), envelope: 'easeInOutCubic' })
  }
}
```

在渲染循环里(`_updateGramMotion()`调用之后)加一行`_updateGramAutoPilot()`。

**不需要额外的"2秒静止"计时器**——回到`homeGlobe`+`hold`之后,在下一首歌的trackKey变化被检测到之前,画面自然保持静止。

### 3. `_gramMotion.enabled`判断条件扩展

```js
const candidateParam = new URLSearchParams(window.location.search).get('earthCandidate')
m.enabled = candidateParam === 'cameraGrammarV1' || candidateParam === 'cameraGrammarAuto'
```
这一行改完,`getTargetOrientation()`/`_getVisualTargetNdc()`等所有已有的"仅在cameraGrammarV1下生效"判断不需要逐个再改,因为它们判断的都是这同一个`_gramMotion.enabled`。**只改这一处初始化逻辑,不要去改其他判断点。**

## 严格边界

**只允许改动**:新增`GRAM_AUTO_TIERS`、`_gramAutoPilot`状态、`_updateGramAutoPilot()`函数(放在`createEarth3D()`内部)、`_gramMotion`的`enabled`初始化条件、渲染循环加一行调用。

**禁止改动**:既有10个构图、8种运动原语、3个序列的现有逻辑;`level1motion`/`precomputeschedule`/`eastAsiaHeroV1`三个既有候选;`transitionToComposition()`/`_updateGramTransition()`/`setGramPrimitive()`本身的实现(只是调用它们,不改它们)。**`_updateGramAutoPilot()`函数体内不允许出现`camera.`**(这个函数只负责判断逻辑和调用已有的`transitionToComposition`/`setGramPrimitive`,不直接碰相机)。

## 完成后请提供

1. git diff
2. 播放至少2-3首歌(包含完整的切歌过程)的实测记录:每首歌开始时选中的构图/原语是否跟该歌曲的`rhythmic_motion`档位吻合,歌曲结束前12秒是否正确切回`homeGlobe`
3. 确认`cameraGrammarV1`(手动debug模式)在这轮改动后依然可以正常手动操作,不受`cameraGrammarAuto`新增逻辑干扰
4. 确认默认播放、`level1motion`、`precomputeschedule`、`eastAsiaHeroV1`不受影响

## 验证方式

1. `?earthCandidate=cameraGrammarAuto`,正常播放,确认每首歌开始时自动过渡到对应构图,歌曲快结束时自动切回`homeGlobe`
2. 切歌时确认新一轮选择逻辑正确触发,不会跟上一首歌状态混淆
3. 确认`cameraGrammarV1`debug面板手动操作、默认播放、其余三个候选均不受影响
4. 控制台无新增报错,连续播放无冻结
