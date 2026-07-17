# 修复:`_currentCompositionKey` TDZ崩溃,导致3D渲染器初始化失败(地球消失)

本轮阶段:直接修复(根因已通过控制台报错精确定位)
允许修改文件:仅 `pwa/earth3d.js`
允许 commit:否

---

## 报错

```
ReferenceError: Cannot access '_currentCompositionKey' before initialization
    at applyTheme (earth3d.js:5660:57)
    at HTMLDocument.createEarth3D (earth3d.js:5801:25)
```

## 根因(已核实，跟之前FAR_COMPOSITIONS那次是同一类问题)

`let _currentCompositionKey = 'homeGlobe'`(`earth3d.js:6426`)这行声明的位置，在`applyTheme()`(定义于`earth3d.js:5629`，内部`earth3d.js:5660`引用了`_currentCompositionKey`)第一次在boot流程里被调用(`createEarth3D()`内`earth3d.js:5801`附近)**之后**。JS的`let`声明在代码实际执行到那一行之前处于暂时性死区(TDZ)，`createEarth3D()`执行到5801行调用`applyTheme()`时，还没执行到6426行的声明，导致`applyTheme()`内部访问`_currentCompositionKey`直接抛出`ReferenceError`，整个3D渲染器初始化失败，回退成纯canvas占位图(就是用户看到的模糊光球)。

## 要做的事

把`let _currentCompositionKey = 'homeGlobe'`这行声明，从`earth3d.js:6426`挪到`FAR_COMPOSITIONS`常量声明的旁边（`FAR_COMPOSITIONS`之前已经因为同样的TDZ问题被挪到了`createEarth3D()`很靠前的位置，确认能在`applyTheme()`第一次调用之前执行到）。

**不要只挪这一个变量就了事**——请顺便检查一下`earth3d.js`里还有没有其他`let`/`const`声明，同样被某个"在boot流程早期就会被调用的函数"(比如`applyTheme()`、`transitionToComposition()`等)引用，但声明位置本身在boot调用点之后的情况。如果发现类似的，一并挪到前面，避免这类TDZ问题反复出现、每次都要单独抓一个。

## 完成后请提供

1. git diff
2. 硬刷新页面，确认控制台不再出现这条`ReferenceError`，`[earth3d] 3D renderer unavailable`这条警告也不再出现
3. 截图确认地球贴图正常显示（不再是纯光球占位图）
4. 确认`?earthCandidate=cameraGrammarV1`下`farOrbit`等远景构图依然正常工作(这个变量本身是远景相关逻辑用的，别改坏了)
5. 控制台无新增报错
