# 打回:序列排队检查没有嵌套在 `t>=1` 里面,导致整个序列几乎瞬间冲到终点

## 问题(已实测复现,不是猜测)

`?earthCandidate=cameraGrammarV1`,触发 `playSequence('approach')`(预期路径 `farOrbit(4s) → portraitMarble(5s) → homeGlobe(5s)`,总共14秒),实测:

- 触发后 0.5 秒截图:地球已经缩小到接近 `farOrbit` 的远景尺寸
- 触发后仅 **2 秒**,`window.earth3d.getCameraZ()` 返回 `4.800000000000001`——这正是 `CAMERA_PRESETS.globe.cameraOffsetZ`(homeGlobe 的目标值,序列的**最后一步**),`getGramDebug().transitionRef` 已经是 `null`(没有任何过渡在进行)。

也就是说,整个14秒的三段序列,在2秒内就"完成"了,中间的 `farOrbit`/`portraitMarble` 两个途经构图根本没有真正停留播放,直接被跳过冲到了终点。这跟 brief 验证方式第1条("确认相机依次经过三个构图,能看出分段变化,序列结束后停在homeGlobe")完全不符。

## 根因(已读代码确认)

`_updateGramTransition()`(`earth3d.js:6440`)里:

```js
function _updateGramTransition() {
  if (!_gramTransition) return
  // ...插值逻辑...
  if (t >= 1) {
    // ...收尾逻辑,_gramTransition = null...
  }
  if (_gramSequenceQueue.length > 0) {          // ← 这里!跟上面的 if(t>=1) 是平级的兄弟语句,不是嵌套在里面
    const next = _gramSequenceQueue.shift()
    transitionToComposition(next.compositionKey, next.opts || {}, true)
  }
}
```

`if (_gramSequenceQueue.length > 0)` 跟 `if (t >= 1)` 是**同一层级的两个独立 if**,不是嵌套关系——意味着只要队列不空,**每一帧**(不管当前这一步过渡是刚开始、进行到一半、还是真的完成了)都会立刻把下一步从队列里取出来执行,把 `_gramTransition` 整个替换掉。

`playSequence('approach')` 一调用,`_gramSequenceQueue` 里立刻有2项(`portraitMarble`/`homeGlobe`),第一帧渲染循环跑到这里,队列不空 → 立刻消费掉 `portraitMarble`,把刚刚才开始(t≈0)的 `farOrbit` 过渡直接顶替掉;下一帧同理，`homeGlobe` 又把 `portraitMarble` 顶替掉——三步在几帧之内(几十毫秒)全部"完成",不会有任何一步真正播放满它设定的时长。

## 修复方式

把队列检查挪到 `if (t >= 1) {...}` 收尾块的**内部**(只有当前这一步真正播放完,才允许消费下一步):

```js
function _updateGramTransition() {
  if (!_gramTransition) return
  // ...插值逻辑不变...
  if (t >= 1) {
    // ...现有收尾逻辑不变(写 vs.lat/lon/NDC/roll,_gramTransition = null,记录_gramSettledZ等)...
    _gramTransition = null
    _gramSettledZ = camera.position.z
    _gramTransitionRef = _gramTransition
    _gramSettledZRef = _gramSettledZ

    if (_gramSequenceQueue.length > 0) {          // ← 挪到这里面,跟 _gramTransition = null 同一个块里
      const next = _gramSequenceQueue.shift()
      transitionToComposition(next.compositionKey, next.opts || {}, true)
    }
  }
}
```

这样只有当 `t>=1`(这一步真正完成)才会去看队列里还有没有下一步,不会出现"过渡还没播完就被下一步顶替"的问题。

## 另外:两个标记为"will be removed"的临时调试方法没有被移除

`earth3dApi` 导出块里(`earth3d.js:6859`/`6863`附近):
```js
// [TEMP-VERIFY] read-only camera z for round-D validation, will be removed
getCameraZ() { ... },
// [TEMP-VERIFY] debug breathe/transition state, will be removed
getGramDebug() { ... },
```
这两个方法自己标注了"will be removed",但最终交付的代码里还在。如果这两个方法本身没有安全隐患、你觉得留着方便以后调试也可以,但**请明确决定并去掉这个具体的注释**(要么删掉这两个方法,要么保留但去掉"will be removed"这种自相矛盾的标注,不要让"标记了要删但没删"这种状态留在交付的代码里)。这次不强制要求删除,由你判断,但请给出明确结论,不要含糊过去。

## 严格边界

只改 `_updateGramTransition()` 里队列检查的嵌套位置(挪到`if (t>=1)`内部,不改判断逻辑本身),以及视你判断处理那两个TEMP-VERIFY方法。**不要碰**三个命名序列的数值定义、`transitionToComposition()`的`_isSequenceStep`参数逻辑本身、A-E轮已验证的任何内容。

## 验证方式(这次必须证明真的按时长走,不能只看代码逻辑)

1. 触发 `approach`,在 0.5s / 3s(应该还在farOrbit附近)/ 6s(应该正在portraitMarble附近)/ 10s(应该正在homeGlobe附近)/ 15s(应该已停在homeGlobe)分别截图或记录 `getCameraZ()`,证明每一步确实播放了接近其设定的时长,不是几秒内就冲到终点
2. 触发 `retreat`/`flyby`,同样方式验证
3. 序列播放中途手动切换构图,确认能立刻打断且无遗留步骤续播(这条上次已经验证过,这次连带确认没有被这次改动破坏)
4. 控制台无新增报错
