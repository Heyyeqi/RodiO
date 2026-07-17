# night偏黄诊断 第三轮:必须先硬刷新排除内存污染,再重新测

本轮阶段:纯诊断,不修复。**这次的第一步是强制性的，不能跳过**
允许操作:仅浏览器控制台命令 + 截图

---

## 关键发现(必须先处理)

上一轮诊断显示，Theme Tuner面板里`night`主题的`mapColor`实际值是`#04881b`（深绿），`emissiveColor`是`#a432c2`（紫色）——**这两个都跟`earth3d.js`文件里写的`0x040810`/`0xffc86e`完全对不上**。这说明整个调试session里反复的`patchTheme()`调用（不管是针对night还是其他主题的测试）已经把内存里的`THEME_VISUAL_CONFIG`污染了，而且这个污染在页面不刷新的情况下会一直累积、不会自动清除。

**之前所有轮次测出来的"关闭emissive后还是偏暖"这个结论，很可能是在测一个被污染的中间状态，不能作为可靠依据。**

## 第一步：必须先完整硬刷新页面（不是软刷新，也不是重新调用某个方法）

请用 `Cmd+Shift+R`（Mac）强制刷新，或者直接关闭标签页用无痕模式重新打开页面。**这一步是必须的，不能用控制台命令代替。**

## 第二步：刷新后立刻查一次干净状态的值（不要点任何按钮、不要切任何主题，先看默认加载状态）

```js
const st = window.earth3d.getDebugState()
console.log('currentTheme:', st.currentTheme)
console.log('mapColor:', st.colorHex)
console.log('emissiveHex:', st.emissiveHex)
console.log('uniforms:', JSON.stringify(st.uniforms))
```
**如果默认加载的主题不是night，请切换到night主题（用Theme Tuner的Mode下拉菜单切一次，这是唯一允许的UI操作），切换后立刻再执行一次上面这几行，贴出结果。**

确认这次`colorHex`是不是`#040810`，`emissiveHex`是不是`#ffc86e`。**如果这次是干净的正确值，才能继续往下测；如果还是不对，说明问题出在其他地方（比如切换主题这个动作本身有问题），需要先解决这个。**

## 第三步：确认数值干净后，重复上一轮的诊断

```js
// 记录初始状态用于对比
console.log('初始emissiveIntensity:', window.earth3d.getDebugState().emissiveIntensity)

// 截图1：当前完整状态（干净的night默认状态）

window.earth3d.patchTheme('night', { texture: { emissiveIntensity: 0 } })
// 截图2：关闭emissive后

console.log(window.earth3d.getDebugState().colorHex)
```
**这次请重点回答：干净状态下（没有被污染），关闭emissive后，地球底色是不是深蓝黑色？**

## 第四步：如果干净状态下依然偏暖，再查光源颜色

```js
const mat = window.earth3d.getRimOverlayMat()
console.log('尝试其他方式获取光源信息')
```
如果没有现成方法，临时加：
```js
getLightColors() {
  return {
    ambientColor: '#' + ambientLight.color.getHexString(),
    sunColor: '#' + sunLight.color.getHexString(),
  }
},
```

## 请提供

1. 第二步："干净"状态下的colorHex/emissiveHex实际数值——**这是本轮最关键的数据，必须拿到**
2. 第三步：干净状态下关闭emissive后的视觉判断和colorHex
3. 第四步：光源颜色（如果第三步显示还是偏暖，才需要查这个）
4. 明确说明：这次是不是真的做了硬刷新，不是软刷新或者调用了什么方法伪装成"干净状态"

**不需要现在就修复，先把这份干净的诊断数据发回来。**
