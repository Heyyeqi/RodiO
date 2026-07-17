# 打回:移到`after-api-export`之后依然卡死,而且出现更奇怪的现象——bootStage有值但`window.earth3d`本身是undefined

## 实测结果(用干净的硬刷新重复测试过两次,结果一致)

`http://localhost:8081/?earthCandidate=eastAsiaHeroV1`,刷新加载几秒后:
```js
{
  bootStage: "after-api-export",
  earth3dType: "undefined",   // window.earth3d 本身不存在
  isReady: undefined,
  targetNdcX: undefined,
  targetNdcY: undefined,
}
```
页面依然卡在"LOADING",地球画面没有渲染出来。浏览器控制台**依然没有任何error级别的日志**(用`level:error`过滤查过,即使硬刷新重来一次也是空的)。

## 这次比上次多了一个关键线索

`window.__earth3dBootStage`能读到`"after-api-export"`这个值,说明`window.__earth3dBootStage = 'after-api-export'`这一行代码确实执行到了。但按照文件里的代码顺序,这一行是在整个`earth3dApi`对象构建完、且更早之前就应该执行过的`window.earth3d = earth3dApi`赋值语句**之后**才会走到——如果`bootStage`这行真的执行了,`window.earth3d`不可能还是`undefined`。

这暗示可能不是"新代码导致某处静默失败"这么简单,而是可能存在**多次脚本执行/多个执行上下文**的情况(比如页面刷新时机、或者调试环境本身的某种重复加载),导致读到的`bootStage`和`earth3d`来自不同的执行实例。也可能是这次新加的代码块本身又在`after-api-export`标记之后重新抛出了一个异常，把后续本该发生的something（比如某个负责最终把地球画面标记为"ready"的逻辑）打断了，但这个异常本身没有被打印出来。

## 请求

这个问题比预想的更棘手，排查方式建议：

1. **在`window.earth3d = earth3dApi`赋值那一行之前也加一条`console.log`**（比如`console.log('[earth3d] api object assigned to window')`），确认这一行本身是不是真的只执行了一次、且真的执行了
2. **把新加的这段`eastAsiaHeroV1`激活代码整个包一层try/catch**，catch里明确`console.error`打印出具体的异常堆栈，不要让任何异常有机会被静默吞掉：
   ```js
   if (new URLSearchParams(window.location.search).get('earthCandidate') === 'eastAsiaHeroV1') {
     try {
       console.log('[earth3d] bootStage:', window.__earth3dBootStage)
       console.log('[earth3d] isReady:', window.earth3d?.isReady)
       applyCameraPreset('eastAsiaHeroV1')
       updateVisualTargetDir()
       console.log('[earth3d] eastAsiaHeroV1 applied successfully')
     } catch (e) {
       console.error('[earth3d] eastAsiaHeroV1 activation FAILED:', e.message, e.stack)
     }
   }
   ```
3. 确认这段代码在浏览器里到底有没有真的执行到（用浏览器devtools本身直接看，不要只依赖自动化工具的日志查询，这次的现象比较反常，建议你在自己本地用真实Chrome devtools跑一遍，在这段代码前后打断点单步看一下）

## 验证方式

必须做到：加`?earthCandidate=eastAsiaHeroV1`能看到地球画面正常渲染出来（不再卡LOADING），`window.earth3d.isReady === true`，`_targetNdcX`/`_targetNdcY`确认是`0.05`/`-0.05`。如果加了try/catch之后发现了具体异常，请把完整的异常信息和堆栈贴给我，而不是仅仅"修复了"。
