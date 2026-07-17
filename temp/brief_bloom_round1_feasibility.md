# 地球视觉升级 第二批 第一轮:太阳光斑精灵 + 最简Bloom后期处理(可行性验证)

本轮阶段:全新立项,可行性验证(不追求最终视觉质量,重点是跑通技术路径)
允许修改文件:`pwa/earth3d.js`、`pwa/index.html`(仅新增URL参数读取逻辑)
禁止修改文件:其余所有文件
允许 commit:否,除非我后续明确批准
回滚方案:全部改动gate在新的`?earthBloom=1`URL参数后面,不加这个参数时必须是像素级不变的默认行为

---

## 背景

用户拿参考图指出画面左侧那片"从画面边缘往外扩散的大片光晕"(太阳镜头光斑/Bloom效果),这跟我们已经在调的"贴地球表面那圈大气层辉光"是完全不同的两套东西——目前项目里完全没有这套后期处理管线。这轮是一次全新的基础设施搭建,目标是先验证技术可行性和性能开销,不追求跟参考图完全一致的视觉效果(那是第二轮的事)。

## 现状(已核实)

- THREE.js版本是2021年的经典`<script>`标签引入(`pwa/index.html:1073`,`three.min.js`),不是ES模块,项目里没有`EffectComposer`/`RenderPass`/`UnrealBloomPass`这类官方后期处理代码,也无法直接`import`它们(整个项目没有走ES模块/打包工具这条路)
- `renderer.render(scene, camera)`直接调用出现在**11处**(`earth3d.js:1056/1234/1442/1470/1560/5515/5611/6686/6698/6703/6851`),包括主渲染循环和多个一次性刷新场景的地方
- 场景里"太阳"目前只是`sunLight`(`THREE.DirectionalLight`,`earth3d.js:3812`),没有任何可见几何体
- `sunLight.position`(在`updateSunPosition()`里,`earth3d.js:5888`起,基于真实太阳位置或debug override计算)已经是"太阳在世界空间的方向"这个信息的现成来源,不需要重新计算
- `camera`/`scene`/`renderer`都是`createEarth3D()`作用域内的模块级变量,可以直接访问

## 这一轮做什么

### 1. 太阳光斑精灵(Sprite)

新增一个`THREE.Sprite`(用`THREE.SpriteMaterial`,可以用简单的径向渐变纹理,或者纯色+`THREE.AdditiveBlending`+边缘渐隐的shader,你自行选择实现方式,不需要真实贴图资源),位置跟随`sunLight.position`方向(在相机能看到的范围内、沿着太阳方向摆放,具体做法:比如以地球为中心,沿`sunLight.position`归一化方向 × 一个足够远的距离作为sprite的世界坐标,确保它出现在太阳"应该在"的屏幕方向)。

这个sprite本身应该:
- 默认不可见/透明度很低(不需要精确抠图太阳形状,重点是它要"亮",给bloom提取用)
- 添加到`scene`里,受Bloom提取影响,但不需要参与地球本身的光照计算(纯自发光效果即可,类似`MeshBasicMaterial`/`SpriteMaterial`那种不受场景光照影响的类型)

### 2. 最简单的Bloom后期处理管线

不需要照抄官方`UnrealBloomPass`的多级mipmap模糊算法,自己写一个简化版即可,思路:
1. 新增1-2个`THREE.WebGLRenderTarget`(全屏分辨率,或者为了性能可以用一半分�辨率)
2. 第一步:把`scene`正常渲染到一个renderTarget(`renderer.setRenderTarget(sceneTarget); renderer.render(scene, camera)`)
3. 第二步:用一个简单的全屏fragment shader,从`sceneTarget`里提取亮度超过阈值的像素(比如`luminance > 0.7`才保留,否则输出黑色),渲染到第二个renderTarget
4. 第三步:对提亮结果做1-2次简单的高斯模糊(横向+纵向分离卷积即可,不需要多级降采样)
5. 最后一步:把原始`sceneTarget`内容 + 模糊后的提亮结果,用叠加混合(additive)合成,渲染到屏幕(`renderer.setRenderTarget(null)`)

这几步可以用几个简单的`THREE.ShaderMaterial` + 全屏三角形/矩形(`THREE.PlaneGeometry`铺满NDC空间,配合正交相机,或者用THREE.js常见的全屏quad技巧)实现,不需要引入任何外部库或文件。

**性能保护**:如果觉得完整实现有困难或者性能明显有问题,可以先用更粗糙的近似(比如只做"提亮+一次模糊+合成"三步,不用横纵分离),这一轮允许效果粗糙,重点是把渲染管线的"开关"跑通。

### 3. 统一渲染调用入口

新增一个函数(比如`renderSceneWithEffects()`),内部逻辑:
```js
function renderSceneWithEffects() {
  if (bloomEnabled && bloomPipelineReady) {
    // 走上面第2步的多阶段渲染
  } else {
    renderer.render(scene, camera)
  }
}
```
把`earth3d.js`里全部11处`renderer.render(scene, camera)`替换成调用`renderSceneWithEffects()`。**这一步要仔细替换,不要漏掉任何一处,也不要误改成别的函数签名**(原来的调用都是无参数的,`renderSceneWithEffects()`也应该保持无参数,内部自己读闭包里的`scene`/`camera`/`renderer`)。

### 4. URL开关

`bloomEnabled`初始化时读取:
```js
const bloomEnabled = new URLSearchParams(window.location.search).get('earthBloom') === '1'
```
放在模块顶层或`createEarth3D()`开头均可,只要保证`renderSceneWithEffects()`能访问到。**不依赖`earthCandidate`参数,这是一个独立的开关,可以跟任何`earthCandidate`值组合使用**。

## 严格边界

**只允许改动**:新增太阳精灵mesh、新增bloom渲染目标/shader/合成逻辑、新增`renderSceneWithEffects()`函数、11处`renderer.render(scene, camera)`替换成调用这个函数、新增`bloomEnabled`URL参数读取。

**禁止改动**:`earthCandidate`相关的任何判断逻辑;Camera Grammar系统(`transitionToComposition`/`_updateGramTransition`等)、大气层辉光(`atmosphereMaterial`/`_atmVert`/`_atmFrag`)、地表材质(`earthMaterial.onBeforeCompile`)——这些都不应该因为这轮改动而受影响,不管`earthBloom`开没开。

## 完成后请提供

1. git diff
2. `?earthBloom=1`(可以叠加`&earthCandidate=cameraGrammarV1`一起测),截图确认能看到太阳光斑的扩散效果(粗糙也可以,重点是"有效果、方向大致对")
3. 不加`?earthBloom=1`参数,截图/对比确认默认行为完全不受影响
4. 简单描述一下开启bloom前后的帧率观感(不需要精确数字,主观描述"明显卡"还是"感觉不到差异"即可)
5. 控制台无新增报错

## 验证方式

1. `?earthBloom=1`能看到画面里出现光斑扩散效果,大致方向跟太阳方向一致
2. 默认(不加参数)行为、其余`earthCandidate`候选、Camera Grammar系统、大气层辉光完全不受影响
3. 无明显帧率下降到不可用的程度(粗略观感即可,这轮不做精细性能优化)
4. 控制台无新增报错
