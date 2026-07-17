# 补充:旋转时间表三阶段配合远近切换(复用现有时序,不加新触发系统)

## 背景

之前的`precomputeschedule`候选(`?earthCandidate=precomputeschedule`)已经验证过真实转动生效。现在觉得转动本身有点单调,想加上"开头远景、中段回到默认距离、结尾前又拉远"的镜头远近变化,配合旋转一起进行。

**关键设计原则:不新增触发系统,直接复用`buildSchedule()`/`scheduleAngle()`已有的爬升期(Tru)/匀速期/减速期(Trd)三阶段时序**——这套时序已经是一个"进度值随时间变化"的机制,远近切换只是在同一条时间轴上再输出一个"缩放进度"数值,跟旋转角度的计算是姐妹函数,不是独立的新东西。

## 具体设计

### 1. 新增一个"远景"相机预设数值(不用新增到`CAMERA_PRESETS`表里,直接在precompute模块内部用常量就行,因为这次是跟旋转绑定的临时效果,不是独立可选的调试预设)

```js
const ZOOM_FAR = { cameraOffsetZ: 10.5, fov: 28 }   // 远景:完整地球+明显黑边(之前方案里叫blueMarble的那组数值)
const ZOOM_NEAR = { cameraOffsetZ: 4.8, fov: 28 }    // 近景:就是现在默认的globe视角数值
```

### 2. 在`scheduleAngle()`旁边新增一个"缩放进度"函数,复用同样的`Tru`/`Trd`/`duration`:

```js
function scheduleZoomProgress(t, sched) {
  const { Tru, Trd, duration } = sched
  // 0 = 远景, 1 = 近景(默认距离)
  if (t <= 0) return 0
  if (t < Tru) return smoothstepDist(t / Tru) / 0.5   // smoothstepDist值域是[0,0.5]，除以0.5归一化到[0,1]
  if (t < duration - Trd) return 1   // 匀速期保持近景/默认距离
  if (t < duration) {
    const remaining = duration - t
    return smoothstepDist(remaining / Trd) / 0.5
  }
  return 0   // 歌曲结束后回到远景（配合两秒静止一起呈现）
}
```

这样爬升期从远景平滑过渡到默认距离，匀速期保持默认距离不变，减速期又平滑拉远回到远景——跟转动的爬升/匀速/减速是同一条时间轴、同一个平滑曲线，只是终点值不同（转动的终点是回到出发角度，缩放的终点是回到远景）。

### 3. 在`_updatePrecomputeMotion()`里，算完`scheduleAngle`之后，顺便算一下缩放进度，插值出实际的相机Z/FOV，直接应用到`camera`对象上：

```js
function _updatePrecomputeMotion() {
  // ...现有逻辑不变，算出 elapsed、angleDeg 之后...

  const zoomProgress = scheduleZoomProgress(elapsed, sched)
  const targetZ = ZOOM_FAR.cameraOffsetZ + (ZOOM_NEAR.cameraOffsetZ - ZOOM_FAR.cameraOffsetZ) * zoomProgress
  const targetFov = ZOOM_FAR.fov + (ZOOM_NEAR.fov - ZOOM_FAR.fov) * zoomProgress
  camera.position.z = targetZ
  camera.fov = targetFov
  camera.updateProjectionMatrix()

  // ...原有的 window.__rodioVisualState._precomputeLonOffset 赋值不变
}
```

注意`camera`这个变量在`applyCameraPreset()`里已经在直接操作(`camera.position.set()`/`camera.fov =`)，这次是同一个对象、同样的操作方式，不用担心访问不到。

## 不要做的事

- 不要新增到`CAMERA_PRESETS`表里，也不要碰调试面板的"Camera Presets (E7 debug)"那几个按钮
- 不要给这次的远近切换单独加调试开关，跟着`?earthCandidate=precomputeschedule`这一个参数走就行
- 不要改变现有默认（不加调试参数时）的相机行为
- 不要碰晨昏线/Terminator相关的任何东西

## 验证方式

1. 加`?earthCandidate=precomputeschedule`播放一首歌，歌曲刚开始的几秒内截图，确认能看到明显比默认更远、黑边更明显的构图
2. 播放到中段（爬升期过后）截图，确认已经平滑过渡回默认的globe视角距离
3. 播放到接近结束时截图，确认又平滑拉远回远景
4. 确认整个远近变化过程平滑，没有突兀的跳变（不需要逐帧确认，肉眼观察几个时间点连起来是不是自然过渡就行）
5. 不加调试参数时，确认默认播放的相机距离/FOV完全不受影响
