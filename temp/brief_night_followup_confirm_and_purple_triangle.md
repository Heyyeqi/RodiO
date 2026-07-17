# night主题 后续跟进:确认暖色调修复效果 + 排查两个独立的渲染瑕疵

本轮阶段:确认 + 排查(不要把两个视觉问题混在一起处理)
允许修改文件:仅 `pwa/earth3d.js`(排查阶段以临时对比为主)
允许 commit:否

---

## 背景

night主题从"预暗mapColor+无nightGrade"重写为跟deepNight/lateEvening统一的架构后，整体色调看起来已经从偏暖改善为偏冷——但需要正式确认一下。同时这次发现两个**独立的**渲染瑕疵，需要分开排查，不要混在一起：

1. **紫色/品红色三角形**（已有诊断报告，地中海东部上空附近的一块独立色斑，只在night主题出现，deepNight没有）
2. **海洋表面大范围重复的深色菱形/斜纹瑕疵**（铺满整片海洋，不是一块独立色斑，是規律重复的纹理图案——这个之前在其他截图里也出现过，可能跟第1个不是同一个问题）

## 第一部分:确认暖色调修复效果

请按之前diagnostic v3的方式（硬刷新后，不要用UI面板，直接看默认加载状态），确认：
```js
const st = window.earth3d.getDebugState()
console.log('colorHex:', st.colorHex, 'emissiveHex:', st.emissiveHex)
```
截图确认整体地球（陆地+海洋，不只是城市灯光）色调是否已经是冷色调，把结果和截图发回来作为这次改动的最终确认。

## 第二部分:紫色三角形排查(按报告建议的下一步)

对比`night`和`deepNight`两个主题的实际uniform值：
```js
// 切到night主题后执行
console.log('night uniforms:', JSON.stringify(window.earth3d.getDebugState().uniforms))
// 切到deepNight主题后执行
console.log('deepNight uniforms:', JSON.stringify(window.earth3d.getDebugState().uniforms))
```
把两组数据逐项对比，列出所有不同的uniform值。**这些数值上的差异，就是导致"只有night有三角形、deepNight没有"的候选原因范围**——请重点看跟颜色分级相关的uniform（`uNightExposure`/`uNightSaturation`/`uNightGamma`/`uOceanRawExposure`等），有没有某个组合可能导致`onBeforeCompile`注入的shader代码里出现`pow()`负数底数、`sqrt()`负数、除以0这类数学上未定义的情况（这类问题在GPU渲染里经常表现为一块颜色异常的色斑，紫色/品红色是比较典型的"shader数值错误"信号）。

## 第三部分:海洋重复纹路瑕疵排查(独立于上面两个)

这个问题**不是night主题独有**——之前在别的截图里也出现过类似的规律性重复深色纹路，铺满海洋表面，形状偏菱形/竖向拉长。请：
1. 确认这个纹路在其他白天主题(比如noon)下是否也存在（如果也存在，说明这是一个更底层的、跟主题无关的问题，比如瓦片贴图拼接边界或者云层贴图平铺）
2. 检查瓦片流式加载系统(`FrontendTileStreamingManager`)的瓦片边界拼接逻辑，看是否是相邻瓦片衔接处的接缝
3. 检查云层贴图(`clouds`纹理)的UV平铺参数，看是否是云层纹理重复平铺导致的图案

## 请提供

1. 第一部分：整体色调确认截图 + colorHex/emissiveHex数值
2. 第二部分：night vs deepNight的uniform逐项对比，列出所有差异项，以及你认为哪个/哪几个差异最可能导致三角形瑕疵
3. 第三部分：确认这个海洋纹路瑕疵是否在其他主题下也存在，以及初步判断是瓦片接缝还是云层贴图问题
4. **这三部分请分开汇报，不要合并成一个笼统的结论**
