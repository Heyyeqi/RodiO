# 打回(严重):breathe 原语会让整个地球渲染彻底冻结,且遗留了调试脚手架代码

## 问题(已用三重证据确认,不是猜测)

`?earthCandidate=cameraGrammarV1` → 切到 `portraitMarble` 等过渡完成 → `setGramPrimitive('breathe')`,实测:

1. `window.__rodioVisualState._dbgInnerReached` 卡死在 `1`,不再增长(正常应该每帧+1)
2. `window.__rodioVisualState._dbgBreatheFactor`/`_dbgBreatheZ` 始终是 `undefined`(这两个字段在 `camera.position.z = ...` 那行**之后**才赋值)
3. `window.earth3d.getDebugState().animationLoopActive` 变成 `false`

三个证据指向同一个结论:**breathe 分支执行到 `camera.position.z = ...` 那一行时抛出了 `ReferenceError`,导致整个渲染循环从此彻底停止,不是"呼吸效果不生效"这么轻——是整个地球画面从那一刻起完全冻结,不会再有任何动画(旋转、过渡、其他原语全部停摆)。**

## 根因

`_updateGramMotion()`(`earth3d.js:205`)声明在 `createEarth3D()`(`earth3d.js:505`)**外面**。但 `camera`(`const camera = new THREE.PerspectiveCamera(...)`,`earth3d.js:632`)声明在 `createEarth3D()` **里面**。`_updateGramMotion()` 的 breathe 分支(`earth3d.js:251-254`)直接写 `camera.position.z = ...`/`camera.updateProjectionMatrix()`——这两行访问的 `camera` 在这个作用域下根本不存在,每次执行到这里都是 `ReferenceError`。

`renderer.setAnimationLoop(callback)` 内部是"执行回调→再排下一帧"的递归结构(`earth3d.js:6455`附近),回调抛出未捕获异常会导致**后续所有帧都不再被排定**,不是只影响当前这一帧——这就是为什么整个画面会彻底冻结,而不只是呼吸效果消失。

（这份 brief 当初给的示例代码也犯了同样的错误,我自己写的时候没考虑到 `_updateGramMotion` 和 `camera` 不在同一作用域——这不是你抄错了,是我给的伪代码本身有这个坑,这次一起说清楚。）

## 正确的修复方式:参照 `_precomputeMotion` 已经验证过的模式

`_precomputeMotion` 的缩放机制就是这么解决同样的作用域问题的:`_updatePrecomputeMotion()`(在 `createEarth3D()` 外面)只计算数值、写入 `window.__rodioVisualState._precomputeTargetZ`,真正的 `camera.position.z = ...` 赋值挪到渲染循环里(`earth3d.js:6467`附近,在 `createEarth3D()` 里面,`camera` 在这里是真正可访问的)。

breathe 要照抄同一个套路:

**`_updateGramMotion()`(`earth3d.js:238`附近)breathe 分支只算数值,不碰 `camera`:**
```js
// breathe: low-frequency camera distance oscillation, only when no active transition
if (prim === 'breathe' && !_gramTransitionRef && _gramSettledZRef !== null) {
  const cfg = (_gramMotionPrimitives && _gramMotionPrimitives.breathe) || { amplitudePct: 0.025, periodSec: 30 }
  const breatheFactor = 1 + Math.sin((elapsed % cfg.periodSec) / cfg.periodSec * Math.PI * 2) * cfg.amplitudePct
  window.__rodioVisualState._gramBreatheTargetZ = _gramSettledZRef * breatheFactor
} else {
  window.__rodioVisualState._gramBreatheTargetZ = undefined
}
```

**渲染循环里(`earth3d.js:6455`附近的 `renderer.setAnimationLoop`回调内,`camera`真正在作用域里的地方),`_updateGramMotion()`调用之后加:**
```js
_updateGramMotion()
if (Number.isFinite(window.__rodioVisualState?._gramBreatheTargetZ)) {
  camera.position.z = window.__rodioVisualState._gramBreatheTargetZ
  camera.updateProjectionMatrix()
}
_updateGramTransition()
```
(具体插入位置参照现有 `_precomputeMotion` 的缩放lerp那几行是怎么插在渲染循环里的,风格保持一致)

## 必须做的清理

删除这次遗留的全部调试脚手架:
- `earth3d.js:241-247` 的 `window.__rodioVisualState._dbgPrim`/`_dbgSettledZRef`/`_dbgTransRef`/`_dbgTransRaw`/`_dbgInnerReached`/`_dbgCond` 这几行赋值
- `earth3d.js:247` 的 `console.log('[BREATHE-INNER] reached...')`
- `earth3d.js:253-254` 的 `_dbgBreatheFactor`/`_dbgBreatheZ`(如果修复后还想保留某种诊断,可以做成一个统一的、有意义命名的诊断字段,不要留一堆 `_dbg*` 零散字段)

这些不应该出现在"已完成"的代码里,是排查过程中加的临时脚手架,必须清干净。

## `_gramTransitionRef`/`_gramSettledZRef` 桥接变量——这部分设计是对的,不用重做

这两个桥接变量的思路是对的(`_gramTransition`/`_gramSettledZ` 声明在 `createEarth3D()` 里面,`_updateGramMotion()` 在外面访问不到,需要桥接),跟 A轮 `_gramMotionPrimitives` 桥接 `MOTION_PRIMITIVES` 是同一个模式,继续保留即可。**只是 breathe 分支不应该在这两个桥接变量之外,又额外去访问一个完全没有桥接过的 `camera`**——这是这次唯一的疏漏,数值计算和判断条件部分都是对的。

## 严格边界

只改 `_updateGramMotion()` 的 breathe 分支(去掉直接碰 `camera` 的部分,改成写入`_gramBreatheTargetZ`)+ 渲染循环里加读取这个字段并赋值给 `camera.position.z` 的那几行 + 删除全部 `_dbg*`/console.log 脚手架。**不要碰** `rollDrift`/`deepSpace`(这两个没有同类问题)、`_gramTransitionRef`/`_gramSettledZRef` 桥接机制本身、其他任何已验证过的代码。

## 验证方式(这次必须证明画面真的没有冻结,不能只看代码逻辑)

1. 切到 `breathe`,静置观察至少30秒,**全程截图或数值记录 `_animFrameCount`(或类似帧计数)持续增长**,证明渲染循环没有停
2. 同时确认 `camera.position.z` 确实在周期性变化(呼吸效果真的生效)
3. 呼吸生效期间,再触发一次构图切换(比如切到 `farOrbit`),确认过渡动画正常播放、没有卡死
4. 控制台 `preview_console_logs(level:'error')` 确认无报错,且没有 `[BREATHE-INNER]` 这类调试日志残留
5. 确认 `rollDrift`/`deepSpace`/A/B/C轮所有已验证内容不受影响
