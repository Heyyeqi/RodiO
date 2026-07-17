# night主题偏黄 精确诊断(请严格照抄控制台命令逐条执行,不要用UI面板代替)

本轮阶段:纯诊断,不修复
允许操作:仅浏览器控制台命令 + 截图，不要碰Theme Tuner UI面板的任何滑块/输入框

---

## 背景

上一轮审计没有严格按要求走，用UI面板改了几个参数做对比，没有拿到关键的`uCityLumLow`/`uCityLumHigh`数值，也没有看纯海洋区域颜色。这次请**只用下面给的控制台命令**，不要用UI面板操作，按顺序逐条执行，每条都贴出返回结果。

## 请按顺序逐条执行，每条都截图或贴文字结果

### 命令1：确认当前是night主题，且拿到完整uniform值

```js
const st = window.earth3d.getDebugState()
console.log('currentTheme:', st.currentTheme)
console.log('uniforms:', JSON.stringify(st.uniforms))
```
**必须贴出`uniforms`里`uCityLumLow`和`uCityLumHigh`这两个具体数值。**

### 命令2：临时把emissiveIntensity设成0，看地球底色是否恢复冷色调

```js
window.earth3d.patchTheme('night', { texture: { emissiveIntensity: 0 } })
```
截图（这时候应该看不到任何城市灯光，只有地球本身的基础色）。**明确回答：这时候地球看起来是冷色调(深蓝黑)还是依然偏暖？**

### 命令3：在命令2的基础上，把atmosphere.opacity也设成0（确认已经是0，如果不是0就设成0）

```js
window.earth3d.patchTheme('night', { atmosphere: { opacity: 0 } })
```
截图。**这时候如果还偏暖，说明问题在更底层的地方(比如mapColor实际生效的值、或者sunLight/ambientLight的颜色本身带暖色调、或者别的着色器逻辑)，不是emissive或atmosphere层的问题。**

### 命令4：检查场景光源本身的颜色(不是强度，是颜色)

```js
console.log('尝试获取光源颜色，如果没有现成方法，请告诉我，我加一个临时方法')
```
如果`getDebugState()`没有暴露`ambientLight.color`/`sunLight.color`，请临时在`earth3dApi`加一个方法：
```js
getLightColors() {
  return {
    ambientColor: '#' + ambientLight.color.getHexString(),
    sunColor: '#' + sunLight.color.getHexString(),
    ambientIntensity: ambientLight.intensity,
    sunIntensity: sunLight.intensity,
  }
},
```
调用它，贴出结果。**如果`sunColor`是暖色(比如默认值`#fff5e0`)，即使强度很低(`sun:0.03`)，也可能在极暗的画面里产生看得出来的暖色偏移，这是一个可能的根因。**

### 命令5：截图纯海洋区域(命令2执行之后，也就是emissiveIntensity=0的状态下)，放大看颜色

找一片明显没有陆地/城市灯光的区域，放大截图。

## 完成后，把命令2和命令3的效果恢复

```js
window.earth3d.patchTheme('night', { texture: { emissiveIntensity: 2.0 }, atmosphere: { opacity: 0 } })
```

## 请提供

1. 命令1的完整uniforms输出(尤其uCityLumLow/uCityLumHigh)
2. 命令2、命令3每一步的截图和你的颜色判断
3. 命令4的光源颜色数值
4. 命令5的纯海洋区域特写截图
5. 基于以上数据的根因判断(不需要现在就修复)
