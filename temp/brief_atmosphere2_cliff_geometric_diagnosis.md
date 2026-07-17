# 审计:atmosphere2断崖是亮度问题还是几何/渲染裁剪问题

本轮阶段:纯审计,不修复
允许修改文件:无(控制台操作+截图)

---

## 背景

已确认断崖来自`atmosphere2`单独存在，不是叠加导致。但按Fresnel公式(`1-|法线·视线|`，不分方向连续变化)和当前`sunInfluence=0.08`（很低），理论上不该出现"完全消失"这种硬断崖，最多是"暗一些"。这次要确认:到底是"暗到看不见"，还是"根本没有渲染出来"(几何/裁剪问题)。

## 请在复现断崖的状态下（跟上次审计一样，farOrbit构图，只保留atmosphere2）依次执行

### 1. 把opacity/strength拉到最大，看断崖区域是否还是完全没有

```js
const mat2 = window.earth3d.getAtmosphereLayerState('atmosphere2')
console.log('当前atmosphere2状态:', mat2)

// 直接拿到material本身，把opacity/power都推到极限值
const atm2Mat = window.earth3d.getAtmosphere2Mat ? window.earth3d.getAtmosphere2Mat() : null
if (atm2Mat) {
  window.__atm2Backup = { opacity: atm2Mat.uniforms.uOpacity.value, sunInfluence: atm2Mat.uniforms.uSunInfluence.value, power: atm2Mat.uniforms.uPower.value }
  atm2Mat.uniforms.uOpacity.value = 1.0
  atm2Mat.uniforms.uSunInfluence.value = 0.0
  atm2Mat.uniforms.uPower.value = 1.0
  console.log('已推到极限值，备份:', window.__atm2Backup)
} else {
  console.log('getAtmosphere2Mat方法不存在，请告诉我用什么方法能拿到atmosphere2Material')
}
```
截图。**如果`opacity=1.0`、`sunInfluence=0.0`(完全不受太阳方向影响)这种最极端设置下，3点~7点方向依然什么都看不到——那就100%确认是几何/渲染裁剪问题，不是亮度问题**。如果这时候能看到微弱的光了，说明只是原来的数值不够亮。

### 2. 检查相机裁剪面

```js
console.log('camera.near:', window.earth3d.getDebugState ? '需要额外暴露' : '')
```
如果没有现成的方法拿到`camera.near`/`camera.far`/`camera.position`，请你直接在代码里临时加一个调试方法到`earth3dApi`导出块：
```js
getCameraDebugInfo() {
  return {
    near: camera.near, far: camera.far, fov: camera.fov,
    position: { x: camera.position.x, y: camera.position.y, z: camera.position.z },
  }
},
```
调用它，把返回值贴出来。

### 3. 检查atmosphere2的实际uRadius跟相机距离的比例关系

```js
console.log('uRadius:', mat2.uRadius, '相机z:', /* 上一步拿到的camera.position.z */)
```

## 请提供

1. 第1步的截图（极限值下3-7点方向是否依然完全空白）+ 明确回答
2. 第2步的相机near/far/fov/position数值
3. 你自己看完这些数据后，倾向于"几何裁剪"还是"亮度不够"这个判断，说明理由
4. 记得测完把`atm2Mat`的uniform值用`window.__atm2Backup`恢复回去

**这一步只要数据和判断，不需要现在就修复。**
