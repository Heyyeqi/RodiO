# RodiO 动态地球镜头系统 F轮:序列引擎 + Approach/Retreat/Flyby三个镜头序列

本轮阶段：生成候选 + 接入候选（延续A-E轮做法，一轮内完成）
本轮目标：见下文
允许修改文件：`pwa/earth3d.js`、`pwa/index.html`（仅 "Camera Grammar V1 (debug)" 面板部分）
禁止修改文件：其余所有文件
允许生成资源：否
允许 commit：否，除非我后续明确批准
本轮不处理事项：见"这一轮不做"
回滚方案：全部改动在 `?earthCandidate=cameraGrammarV1` gate 后面，出问题直接 revert 这几处 diff

---

## 背景

A-E五轮做完了10个构图、8种持续型运动原语。这轮做 `Flyby`/`Approach`/`Retreat`——这三个跟前面8个原语性质不同，是"一次性的、依次途经多个构图的镜头序列"，不是持续背景运动。本质上就是**依次链式调用已经验证过的`transitionToComposition()`**，不需要发明新的相机运动数学，真正的新东西是一个排队机制。

`Spiral`留到下一轮（需要序列+旋转同时进行，更复杂）。

## 现状(已核实最新行号)

- `transitionToComposition(compositionKey, opts)`(`earth3d.js:6385`)——单次过渡，内部处理"从当前实时状态开始"
- `_updateGramTransition()`(`earth3d.js:6422`)，`t>=1`收尾块在`6435-6447`，完成时把`_gramTransition`置`null`——**这是序列引擎的挂载点**
- 现有`_gramTransition`已包含`fromX/toX`（E轮加的）、`fromLookAtY/toLookAtY`（C轮加的）——序列每一步都是普通`transitionToComposition()`调用，自动继承这些机制

## 要做的事

### 1. 序列排队机制

新增模块级变量（跟`_gramTransition`放一起，`earth3d.js:6381`附近）：
```js
let _gramSequenceQueue = []
```

**重要设计决定，必须照做，不要自己另外设计**：外部手动调用`transitionToComposition()`（比如用户点了别的构图按钮）必须立刻清空剩余队列，不能让序列在被打断后又诡异地继续播放剩下的步骤。用第三个参数区分"外部调用"和"序列引擎内部续播调用"：

```js
function transitionToComposition(compositionKey, opts = {}, _isSequenceStep = false) {
  if (!_isSequenceStep) _gramSequenceQueue = []   // 外部手动调用，清空任何排队中的序列
  const duration = opts.duration ?? 4
  // ...其余现有逻辑完全不变
}

function playSequence(steps) {
  if (!Array.isArray(steps) || !steps.length) return false
  _gramSequenceQueue = steps.slice(1)
  const first = steps[0]
  transitionToComposition(first.compositionKey, first.opts || {}, true)   // 第三个参数=true
  return true
}
```

`_updateGramTransition()`的`t>=1`收尾块（`earth3d.js:6443`，`_gramTransition = null`那一行）之后加：
```js
if (_gramSequenceQueue.length > 0) {
  const next = _gramSequenceQueue.shift()
  transitionToComposition(next.compositionKey, next.opts || {}, true)   // 第三个参数=true
}
```
这样一步完成后，队列里还有下一步就自动接上（复用现有每帧`t>=1`判断，不需要`setTimeout`，避免定时器漂移）；外部随时手动切构图会立刻中断当前序列，不会有遗留步骤继续播放。

### 2. 三个命名序列

新增`CAMERA_SEQUENCES`（放在`MOTION_PRIMITIVES`附近）：
```js
const CAMERA_SEQUENCES = {
  approach: [
    { compositionKey: 'farOrbit', opts: { duration: 4, envelope: 'easeInOutCubic' } },
    { compositionKey: 'portraitMarble', opts: { duration: 5, envelope: 'easeInOutCubic' } },
    { compositionKey: 'homeGlobe', opts: { duration: 5, envelope: 'easeInOutCubic' } },
  ],
  retreat: [
    { compositionKey: 'homeGlobe', opts: { duration: 4, envelope: 'easeInOutCubic' } },
    { compositionKey: 'portraitMarble', opts: { duration: 5, envelope: 'easeInOutCubic' } },
    { compositionKey: 'farOrbit', opts: { duration: 5, envelope: 'easeInOutCubic' } },
  ],
  flyby: [
    { compositionKey: 'limbHero', opts: { duration: 4, envelope: 'easeInOutCubic' } },
    { compositionKey: 'horizonSkim', opts: { duration: 8, envelope: 'easeInOutCubic' } },
  ],
}
```
第一步用正常时长即可，不要做成瞬间"snap"——序列第一步就是"从相机当前实时状态"过渡到路径第一个途经点，跟单独调用`transitionToComposition()`完全一样，只是完成后自动接下一步。（以上时长/顺序都是起点，视觉调试后可调）

### 3. `earth3dApi`导出 + 调试面板

放进现有`Object.assign(earth3dApi, {...})`导出块：
```js
playSequence(sequenceKey, customSteps) {
  const steps = customSteps || CAMERA_SEQUENCES[sequenceKey]
  if (!steps) return false
  return playSequence(steps)
},
```

debug面板（"Camera Grammar V1 (debug)"面板里）加三个按钮：`approach`/`retreat`/`flyby`，分别调用`e3d.playSequence('approach')`等，照抄现有构图按钮的写法。

## 严格边界

**只允许改动**：新增`_gramSequenceQueue`、`transitionToComposition()`加第三参数+清空队列逻辑（不改其余现有逻辑）、`_updateGramTransition()`收尾块加排队检查、新增`CAMERA_SEQUENCES`、`earth3dApi`导出`playSequence`、debug面板加三个按钮。

**禁止改动**：既有10个构图数值、既有8种运动原语现有逻辑、三个既有候选(`level1motion`/`precomputeschedule`/`eastAsiaHeroV1`)、`computeCameraOffsetZForComposition()`。

## 这一轮不做

`Spiral`、`Terminator Track`、日常模式/评分引擎/歌曲联动。

## 完成后请提供

1. git diff
2. 三个序列各自的截图或数值记录，证明确实依次经过了每个途经构图（不是跳过中间步骤直接到终点）
3. 序列播放中途手动切换构图的测试结果（`_gramSequenceQueue`是否被正确清空，之后没有遗留步骤继续播放）

## 验证方式

1. 触发`approach`，确认相机依次经过三个构图（能看出分段变化），结束后停在`homeGlobe`
2. 触发`retreat`，确认反向效果，结束后停在`farOrbit`
3. 触发`flyby`，确认`limbHero`→`horizonSkim`两段过渡都完整播放
4. 序列播放中途手动点击别的构图按钮，确认立刻打断且无遗留步骤续播
5. 确认无冻结、控制台无新增报错、A-E轮已验证内容不受影响
