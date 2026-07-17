# 打回:`_updatePrecomputeMotion()`访问不到`camera`,运行时会抛ReferenceError

## 问题(已通过代码结构核实,不是猜测)

`_updatePrecomputeMotion()`函数**定义**在文件第145行(2格缩进,在第490行`try {`**之前**),但函数体里直接写了`camera.position.z = targetZ`/`camera.fov = targetFov`/`camera.updateProjectionMatrix()`。而`camera`这个变量是在第558行`const camera = new THREE.PerspectiveCamera(...)`声明的,在第490行开始的`try`块**内部**(6格缩进)。

JS的闭包作用域是按函数**定义时**所在的代码位置决定的,不是按调用时的位置。`_updatePrecomputeMotion`定义在490行的try块之前,所以它的作用域链里根本不包含try块内部声明的`camera`——即使调用它的地方(第6223行`_updatePrecomputeMotion()`)是在try块内部,也不会让`_updatePrecomputeMotion`函数体本身"借用"到调用处的作用域。

可以对比确认:`applyCameraPreset(key)`(第6491行,8格缩进)能正常用`camera.position.set()`,就是因为它本身也定义在490行try块内部——它和`camera`是"同一个作用域",而`_updatePrecomputeMotion`不是。

**实际后果**:一旦`_precomputeMotion.schedule`真正建立起来(时长信息到位),执行到`camera.position.z = targetZ`这一行就会抛`ReferenceError: camera is not defined`,导致整个渲染循环报错中断。之前测试时因为Spotify在测试环境里一直没真正开始播放(`duration`一直是0),schedule从来没真正建立过,所以这个错误还没被触发到,但真实使用时(时长信息到位后)一定会报错。

## 修复方式

不要在`_updatePrecomputeMotion()`内部直接操作`camera`。改成:这个函数只负责计算,把算出来的`zoomProgress`(或者直接算好的`targetZ`/`targetFov`)存到`window.__rodioVisualState`上(跟现有的`_precomputeLonOffset`一样的做法),真正对`camera`赋值的代码挪到调用它的地方(第6223行附近,这里本来就在try块作用域内,可以直接访问`camera`)。

具体改法:

**`_updatePrecomputeMotion()`函数内部**,把这几行:
```js
camera.position.z = targetZ
camera.fov = targetFov
camera.updateProjectionMatrix()
```
删掉,改成:
```js
window.__rodioVisualState._precomputeTargetZ = targetZ
window.__rodioVisualState._precomputeTargetFov = targetFov
```

**第6223行`_updatePrecomputeMotion()`调用的地方**(在try块作用域内,能访问`camera`),调用之后加:
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

这样`camera`只在能访问到它的作用域里被操作,`_updatePrecomputeMotion()`本身保持纯计算,不直接碰DOM/THREE.js对象。

## 验证方式(这次必须让schedule真正建立起来跑一遍,不能靠"没报错"就说过了)

1. 因为Spotify在自动化环境里播放不起来,建议本地手动用真实浏览器测(跟之前几轮一样),加`?earthCandidate=precomputeschedule`
2. 播放一首歌几秒钟后,打开控制台,执行`window.__rodioVisualState._precomputeTargetZ`和`camera`(如果`camera`本身在你的测试环境里可以从控制台访问到的话)确认没有抛错、这个值确实存在
3. 更直接的验证:打开Console面板,确认没有任何红色的`ReferenceError`或者其他JS异常出现在播放过程中(尤其是歌曲开始后几秒,schedule建立起来的那个时间点)
4. 截图确认远景确实有跟着爬升期从远到近再到远的可见效果(如果第一步就报错了,这一步自然也就看不到效果,两者一起确认)
