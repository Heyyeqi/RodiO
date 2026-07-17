# 审计:精确定位辉光"断崖式消失"的来源(rimGlow还是atmosphere2,还是别的东西)

本轮阶段:纯审计,不要做任何修复性改动
允许修改文件:无(这轮只需要在浏览器控制台操作和截图,不需要改代码文件)

---

## 背景

用户反馈:远景构图(如`farOrbit`)下,辉光有一段位置会"断崖式"突然消失,不是平滑过渡到暗——不是"暗侧不够亮"这种问题,是**看得出明显的硬边界/断层**。之前的推测(rimGlow的锐利边界叠加在atmosphere2上导致断层)没有确凿证据支撑，需要实测确认，不能再猜。

## 请按这个步骤在你自己的浏览器里做(不是我这边的Preview环境，这样才能复现你实际看到的状态)

### 第一步:复现"断崖"的确切状态

先按你之前能看到断崖现象的操作路径，走到那个画面（哪个主题、哪个构图、大概等了多久），截图保存为"before"。

### 第二步:在控制台执行，只关掉rimGlow，保留atmosphere2

```js
const mat = window.earth3d.getRimOverlayMat()
const veil = window.earth3d.getInnerVeilMat()
window.__rimBackup = { core: mat.uniforms.uCoreStrength.value, halo: mat.uniforms.uHaloStrength.value, veilStrength: veil.uniforms.uInnerVeilStrength?.value, sunLobe: mat.uniforms.uSunLobeStrength.value }
mat.uniforms.uCoreStrength.value = 0
mat.uniforms.uHaloStrength.value = 0
mat.uniforms.uSunLobeStrength.value = 0
if (veil.uniforms.uInnerVeilStrength) veil.uniforms.uInnerVeilStrength.value = 0
console.log('rimGlow已清零，备份值:', window.__rimBackup)
```
不要移动镜头、不要切换构图，**保持画面完全一致**，截图保存为"only-atmosphere2"。

### 第三步:恢复rimGlow，改成只关掉atmosphere2

```js
const mat = window.earth3d.getRimOverlayMat()
const veil = window.earth3d.getInnerVeilMat()
mat.uniforms.uCoreStrength.value = window.__rimBackup.core
mat.uniforms.uHaloStrength.value = window.__rimBackup.halo
mat.uniforms.uSunLobeStrength.value = window.__rimBackup.sunLobe
if (veil.uniforms.uInnerVeilStrength) veil.uniforms.uInnerVeilStrength.value = window.__rimBackup.veilStrength
window.earth3d.setAtmosphereLayerVisible('atmosphere2', false)
```
同样不移动镜头、不切构图，截图保存为"only-rimglow"。

### 第四步:恢复正常状态

```js
window.earth3d.setAtmosphereLayerVisible('atmosphere2', true)
```

## 请提供

1. 三张截图：`before`(两层都在，断崖状态)、`only-atmosphere2`(只有atmosphere2)、`only-rimglow`(只有rimGlow)——**三张必须是同一个镜头位置、同一时刻附近拍的，不能切换构图或者主题**
2. 明确回答：断崖这个现象，在`only-atmosphere2`这张里还在不在？在`only-rimglow`这张里还在不在？
3. 如果两张单独的截图里断崖都不存在，只有两层叠加时才出现——那就是叠加导致的，请具体说明断崖出现的位置(比如"大概在球体的几点钟方向")和`rimGlow`覆盖范围结束的位置是否吻合
4. 如果某一层单独测试就已经能看到断崖，那问题就出在那一层本身，不是叠加问题——请贴出那一层在断崖发生位置附近的uniform值

**这一步只要审计结果，不需要现在就修复。**
