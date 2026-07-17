# 审计:辉光/地球边缘锯齿的实际成因确认

本轮阶段:纯审计,不修复
允许修改文件:无(控制台操作+截图)

---

## 背景

用户反馈地球边缘(尤其辉光包裹整圈之后，对比更明显)出现明显的锯齿/阶梯状。之前查过一次代码：

```js
function isMobileDevice() {
  if (LITE_MODE) return true
  const minDim = Math.min(window.innerWidth, window.innerHeight)
  if (minDim <= 820) return true
  if (window.matchMedia && window.matchMedia('(pointer: coarse)').matches) return true
  return false
}
const SPHERE_SEGMENTS = isMobileDevice() ? 64 : 128
```
`renderer = new THREE.WebGLRenderer({ alpha: true, antialias: !isMobileDevice() })`

如果`isMobileDevice()`判定为true，会同时触发：关闭抗锯齿 + 球体精度从128段降到64段——两者都会导致锯齿更明显。但没有在用户实际使用的浏览器窗口里确认过这几个值，需要先确认，不要假设。

## 请在用户实际测试锯齿现象的那个浏览器窗口里，控制台执行

```js
console.log({
  innerWidth: window.innerWidth,
  innerHeight: window.innerHeight,
  minDim: Math.min(window.innerWidth, window.innerHeight),
  coarsePointer: window.matchMedia('(pointer: coarse)').matches,
  devicePixelRatio: window.devicePixelRatio,
})
const debugState = window.earth3d.getDebugState()
console.log({
  antialias: debugState.antialias,  // 如果getDebugState没暴露这个字段，请告诉我，我们再加
  pixelRatio: 'need check renderer.getPixelRatio()',
})
```

如果`getDebugState()`没有暴露`isMobileDevice()`的判定结果或`renderer`的`antialias`设置，请临时在`earth3dApi`里加一个：
```js
getRenderQualityInfo() {
  return {
    isMobileDetected: isMobileDevice(),
    sphereSegments: SPHERE_SEGMENTS,
    rendererAntialias: renderer.getContext().getContextAttributes().antialias,
    pixelRatio: renderer.getPixelRatio(),
    innerWidth: window.innerWidth,
    innerHeight: window.innerHeight,
  }
},
```
调用它，把结果贴出来。

## 请提供

1. 上面这些实际数值
2. 明确回答：这次测试时，`isMobileDevice()`是否判定为true？如果是，是因为窗口宽度小(≤820)还是因为`pointer:coarse`(触屏设备判定)触发的？
3. 如果确实被判定为"移动端"导致画质降级——这是不是用户平时实际使用时的真实窗口环境（比如就是缩小成一个手机模拟宽度在测试），还是无意间开了个窄窗口测试导致的
4. 不需要现在就修复，先把这几个数据和判断发回来
