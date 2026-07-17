# Brief:precomputeschedule 候选的缩放推进有轻微卡顿——需要加平滑插值

## 背景

用户实测反馈:`?earthCandidate=precomputeschedule` 播放时,"远到近"的缩放推进过程有点轻微卡顿,不是完全流畅。已经用代码核实过根因,不是猜测。

## 根因(已核实)

`pwa/earth3d.js:6230-6238`:
```js
_updatePrecomputeMotion()
if (_precomputeMotion.enabled) {
  const vs = window.__rodioVisualState || {}
  if (Number.isFinite(vs._precomputeTargetZ)) {
    camera.position.z = vs._precomputeTargetZ
    camera.fov = vs._precomputeTargetFov
    camera.updateProjectionMatrix()
  }
}
```
每一帧都把 `camera.position.z`/`camera.fov` **硬赋值**成 `_updatePrecomputeMotion()`(定义在 `earth3d.js:145` 附近)算出来的目标值——这个函数内部依赖 `vs.progress`(即 `window.__rodioVisualState.progress`)算出当前 `elapsed`,再喂给 `scheduleZoomProgress()` 得到目标值。

但 `state.progress` 只在 `pwa/index.html:1325`(`spotifyPlayer.addListener('player_state_changed', ...)`)里被赋值——这是 Spotify Web Playback SDK 的状态变化事件,实测大约**每秒触发一次**,不是每帧连续更新。这意味着 `_updatePrecomputeMotion()` 算出来的目标值在这一秒内的~60帧里完全不变,直到下一次 `player_state_changed` 事件才跳到下一个值——因为相机位置是硬赋值(不是渐进逼近),画面上就表现为"停一下、跳一下"的轻微卡顿。

对比同一个渲染循环里紧接着的旋转逻辑(`earth3d.js:6241`):
```js
earth.quaternion.slerp(target, 0.02)
```
这里用的是每帧朝目标值渐进逼近(slerp),即使 `target` 本身是一秒一跳的阶梯输入,渐进逼近也能把它平滑成连续动画——这正是缩放这条路径缺失的处理。

## 修复方式

把缩放的硬赋值改成跟旋转同样套路的每帧插值(lerp),不要改动 `_updatePrecomputeMotion()`/`scheduleZoomProgress()`/`buildSchedule()` 内部的时间表数学(那部分负责"歌曲结束精确回到起点朝向"这个保证,是通过旋转角度实现的,跟缩放无关,不要碰)。

`pwa/earth3d.js:6230-6238` 改成:
```js
_updatePrecomputeMotion()
if (_precomputeMotion.enabled) {
  const vs = window.__rodioVisualState || {}
  if (Number.isFinite(vs._precomputeTargetZ)) {
    camera.position.z += (vs._precomputeTargetZ - camera.position.z) * 0.08
    camera.fov += (vs._precomputeTargetFov - camera.fov) * 0.08
    camera.updateProjectionMatrix()
  }
}
```

`0.08` 这个插值系数是起点建议值(比旋转用的 `0.02` 快,因为缩放的输入更新间隔更长、单次跳变距离可能更大,系数太小会导致镜头明显滞后于"应该在哪"的目标,需要视觉调试确定最终值,只要是能让画面连续、同时不会让人感觉到"追不上"目标的滞后感即可,不用纠结具体数值是不是刚好0.08)。

## 严格的修改边界

**只允许改动**:`earth3d.js:6230-6238` 这个渲染循环里的赋值方式,从硬赋值改成lerp插值。

**禁止改动**:`_updatePrecomputeMotion()`/`scheduleZoomProgress()`/`buildSchedule()`/`scheduleAngle()` 内部的时间表数学、旋转部分的slerp逻辑、`state.progress` 的赋值来源和频率(不要去改 Spotify SDK 事件监听或加轮询,这次只解决"缩放没跟着平滑"这一个具体问题,不要顺手改成给 `progress` 加本地时钟插值那种更大范围的方案)、其他相机预设(`eastAsiaHeroV1`/`globe`等)、Level 1 旋转候选的任何代码。

## 验证方式

1. 加 `?earthCandidate=precomputeschedule` 播放一首歌,全程观察缩放推进是否连续顺滑,不再有"停顿-跳跃"的卡顿感
2. 确认歌曲播放到结束时,画面依然能精确落回起点朝向(旋转部分的验证不应该受这次改动影响,截图前后对比一下确认没有回归)
3. 确认默认播放(不带调试参数)和 `eastAsiaHeroV1`/`level1motion` 这两个候选完全不受影响
4. 把插值系数最终定的数值和调试过程中试过的其他数值(如果试了不止一个)写进报告里
