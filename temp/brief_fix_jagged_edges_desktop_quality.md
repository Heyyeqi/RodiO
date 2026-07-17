# 修复:桌面窗口被误判为"移动端"导致画质降级(锯齿),要求达到无锯齿、清晰流畅

本轮阶段:先查清矛盾点,再修复,目标明确(彻底消除锯齿)
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件
允许 commit:否,除非我后续明确批准

---

## 背景

审计发现:当前窗口`innerWidth:915, innerHeight:881`(`minDim:881 > 820`)、`coarsePointer:false`(不是触屏),但`isMobileDetected`却是`true`,导致`antialias:false`(关闭抗锯齿)+`sphereSegments:64`(球体精度减半)，这是锯齿的直接原因。

按`isMobileDevice()`(`earth3d.js:290`)的三条判断路径(`LITE_MODE` / `minDim≤820` / `pointer:coarse`)，前两条都对不上，唯一剩下的可能是`LITE_MODE`为`true`。但搜过整个代码库，`LITE_MODE`(`earth3d.js:286`，`urlParams.get('lite') === '1'`)只有这一处定义，没有任何地方会设置或跳转到带`lite=1`的URL，测试用的URL(`?earthCandidate=cameraGrammarV1`)里也没有这个参数——**这个结论本身有矛盾，需要先查清楚，不要直接当成定论去修**。

## 第一步:先确认矛盾，不要跳过

在复现锯齿的那个页面，控制台执行：
```js
console.log('location.href:', window.location.href)
console.log('location.search:', window.location.search)
console.log('urlParams.get(lite) 重新计算:', new URLSearchParams(window.location.search).get('lite'))
```
把这三行的实际输出贴出来。如果这次重新计算`urlParams.get('lite')`不等于`'1'`，说明上次审计用的`getRenderQualityInfo()`这个方法本身有问题(可能读到了缓存的/过期的`LITE_MODE`常量，或者别的原因)，需要先查`getRenderQualityInfo()`里`isMobileDetected: isMobileDevice()`这一行是不是被正确地实时调用的，不是读了一个旧值。

## 第二步:根据实际情况修复，目标是——正常桌面窗口下必须是无锯齿、128段球体精度、抗锯齿开启

无论上一步查出来的具体原因是什么，最终要达到的效果很明确：**像`915x881`这种正常桌面浏览器窗口大小，不应该被判定为"移动端"，必须享受满血画质(抗锯齿开启、128段球体、清晰锐利的边缘)**。移动端降级只应该真正发生在小屏手机/平板或者真实触屏设备上。

具体修复方向(根据第一步查出的真实原因选择，如果是别的原因，请照实际情况调整，不要死板套用下面的方案)：

- 如果确认是`LITE_MODE`被意外触发：找到根因并修掉，让正常URL下`LITE_MODE`保持`false`
- 如果发现`minDim`阈值(820)本身不合理(比如希望保护的是"真正的小屏手机"，但820这个值把正常桌面窗口也误伤了)：可以考虑把阈值降低(比如降到600或更低，只保护真正意义上的小屏设备)，但**这个改动请先告诉我你打算调整到多少，理由是什么，不要直接改**
- 如果`isMobileDevice()`本身的调用时机有问题(比如页面加载早期`window.innerWidth`还没稳定就被计算了一次，之后没有重新计算)：检查`SPHERE_SEGMENTS`/`antialias`是否只在模块加载那一刻计算一次、之后窗口尺寸变化不会重新触发——如果是这样，这本身也是要修的点

## 验证方式(这次要求比较高，请仔细核实)

1. 正常桌面窗口(比如`915x881`或者更大)下，硬刷新页面，确认`antialias`开启、`sphereSegments`是128
2. 截图放大看地球边缘轮廓，确认没有肉眼可见的阶梯状锯齿，边缘平滑清晰
3. 确认真正的小尺寸场景(比如把浏览器窗口手动缩小到500px宽以内，或者用真实移动设备/模拟器测试)下，移动端降级逻辑依然正常工作(不要因为这次修复导致真正的低端设备上性能变差)
4. 控制台无新增报错

## 完成后请提供

1. 第一步的诊断输出(证明/证伪LITE_MODE矛盾)
2. 真正的根因
3. git diff
4. 大窗口下边缘清晰度的截图(放大到能看清边缘细节的程度)
5. 确认过小窗口/真实移动设备下的降级逻辑仍然正常
6. 控制台无新增报错
