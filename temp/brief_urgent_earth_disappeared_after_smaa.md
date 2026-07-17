# 紧急:接入SMAA后地球本体消失,只剩辉光光晕

本轮阶段:紧急回归排查,优先恢复功能(如果短时间内无法定位，先回退SMAA改动，保证地球能正常显示，SMAA可以后续单独再战)
允许修改文件:仅 `pwa/earth3d.js`、`pwa/index.html`、`pwa/smaa.js`
允许 commit:否

---

## 现象

接入SMAA之后，地球贴图本体完全消失，画面上只剩一个发光的模糊光球(应该是`atmosphere`/`atmosphere2`透明辉光网格还在渲染，但不透明的地球贴图球体`earth`/`earthMaterial`没有画出来)。画面卡在"LOADING"文字，控制台没有明显报错(0 errors)。

## 请按顺序排查

### 1. 先确认地球mesh本身状态是否正常

```js
const st = window.earth3d.getDebugState()
console.log({
  earthMeshVisible: st.earthMeshVisible,
  earthGroupVisible: st.earthGroupVisible,
  isReady: st.isReady,
  isAvailable: st.isAvailable,
  animationLoopActive: st.animationLoopActive,
  mapExists: st.mapExists,
  dayTextureExists: st.dayTextureExists,
})
```
把结果贴出来。如果`earthMeshVisible`是`false`或者`isReady`是`false`——说明是boot流程被这次改动卡住了(比如纹理加载完成的回调因为渲染管线变化没有被正确触发，导致一直停在"loading"没有真正把`earth.visible`设成`true`)。

### 2. 检查SMAA的render target流程是否正确处理了不透明物体

重点看`_smaaRT`(或者你新增的render target变量名)这个渲染目标：
- 创建时有没有正确设置`depthBuffer: true`（如果场景里`earthMaterial`跟`atmosphere`都渲染到同一个render target，深度缓冲必须打开，否则不透明物体和透明物体的前后关系会错乱）
- `renderer.render(scene, camera)`渲染到这个render target之前，有没有正确调用`renderer.setRenderTarget(_smaaRT)`并且**在渲染前clear**（`renderer.clear()`或者渲染target本身的autoClear设置)，如果没clear干净，可能残留上一帧内容或者渲染顺序错乱
- 最后合成到屏幕的那一步(`SMAAPass`的最后一个pass)，有没有可能只合成了某一层(比如只处理了边缘/辉光相关的内容，没有把完整的scene颜色也一起输出)

### 3. 如果5分钟内定位不到具体原因，直接回退SMAA相关代码

```bash
git diff --stat
```
如果`pwa/smaa.js`是新增文件、`earth3d.js`/`index.html`的SMAA相关改动能清楚分辨出来（跟这次git diff对得上），优先**把这几处改动回退掉**，确认回退后地球恢复正常显示，SMAA这个功能单独放到下一轮重新做，不要因为它把整个地球渲染卡死。**这次调试的首要目标是恢复地球正常显示，SMAA效果可以往后放**。

## 请提供

1. 第1步的诊断输出
2. 如果找到根因，说明具体是什么，怎么修的，git diff
3. 如果决定先回退，请明确说"已回退到SMAA之前的状态"，并截图确认地球恢复正常显示
4. 控制台确认无新增报错
