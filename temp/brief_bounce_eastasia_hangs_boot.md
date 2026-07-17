# 打回:`?earthCandidate=eastAsiaHeroV1`会让整个地球模块卡死在LOADING,页面加载不完成

## 问题(已实测复现,不是猜测)

对比测试过两种情况:

**情况A:** `http://localhost:8081/`(不带任何candidate参数)
- 页面正常加载完成
- `window.earth3d.isReady === true`
- `window.__earth3dBootStage === 'after-api-export'`

**情况B:** `http://localhost:8081/?earthCandidate=eastAsiaHeroV1`
- 页面卡在"LOADING"状态,一直不消失(等了至少几秒钟,截图确认过)
- `window.earth3d`**整个是`undefined`**——不是"没ready",是整个API对象都没有被创建出来
- `window.__earth3dBootStage`也是`undefined`
- `window.__rodioVisualState._targetNdcX`/`_targetNdcY`都是`undefined`——说明`applyCameraPreset('eastAsiaHeroV1')`这个新加的启动时调用**根本没有成功执行完**
- **浏览器控制台没有任何报错**(用`preview_console_logs`的`level:error`过滤查过,是空的)——这点很关键,说明不是一个会抛出可见异常的bug,更像是初始化过程中某处静默卡住/提前return了,或者是被某个try/catch吞掉了异常但没有打印出来

## 需要排查的方向

新加的这段启动时触发代码(大概在`earth.quaternion.copy(initialOrientation)`之后、`applyTheme(pendingTheme)`之前):
```js
if (new URLSearchParams(window.location.search).get('earthCandidate') === 'eastAsiaHeroV1') {
  console.log('[earth3d] applying camera preset: eastAsiaHeroV1')
  applyCameraPreset('eastAsiaHeroV1')
  updateVisualTargetDir()
}
```
这段代码执行的时间点是在整个初始化流程**中途**（`window.__earth3dBootStage`标记之前），这时候`applyCameraPreset()`内部依赖的某些状态（比如`performSceneRefresh()`、`updateSunPosition()`、`requestRenderUpdate()`这些它内部会调用的函数，或者纹理/tile系统的加载状态）可能还没有准备好，提前调用可能导致函数内部卡住、抛出一个被吞掉的异常、或者进入了某种等待状态没有返回。

请重点检查：
1. 这段新代码是否真的执行到了（加更多`console.log`打印每一步，确认`applyCameraPreset`调用之前和之后分别执行到没有）
2. `applyCameraPreset()`内部是否有可能因为在这个时间点调用而访问到还未初始化的对象/纹理，导致同步阻塞或者静默失败
3. 是否应该把这段新代码挪到`window.__earth3dBootStage = 'after-api-export'`（或者更靠后、确认整个模块已经完全初始化完成）之后再执行，而不是插在中途

## 验证方式（这次必须证明页面真的能加载完成，不能只说"应该没问题了"）

1. 修复后，加`?earthCandidate=eastAsiaHeroV1`重新测试，确认页面能正常加载出地球画面（不再卡在LOADING）
2. 确认`window.earth3d.isReady === true`
3. 确认`window.__rodioVisualState._targetNdcX`/`_targetNdcY`确实被设置成了`0.05`/`-0.05`（新预设的值）
4. 确认不带这个参数的默认页面加载依然完全正常，没有被这次修复带偏
5. 把这几步的实际console输出贴给我，不要只描述"已修复"

在这个问题修好之前，构图效果本身没法验证，这次先专注解决"能不能正常加载"这一个问题。
