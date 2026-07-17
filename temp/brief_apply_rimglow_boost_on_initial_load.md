# 修复:辉光增强只在真正触发构图切换时生效,页面默认加载视角从未应用过

本轮阶段:补上初始化触发,不改动已有的辉光增强逻辑本身
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件
允许 commit:否,除非我后续明确批准

---

## 背景

`RIM_BOOST_COMPOSITIONS`(含`homeGlobe`)这套辉光增强逻辑写在`transitionToComposition()`函数内部，只有真正调用这个函数才会生效。核实过：`transitionToComposition('homeGlobe', ...)`在整个代码里**只有一处调用**(`earth3d.js:6458`，是`cameraGrammarAuto`自动播放"歌曲快结束时切回主视角"专用的)。**页面首次加载时的默认视角，从来没有经过`transitionToComposition()`这个函数**，是走单独的初始化路径设置相机/辉光状态的——所以不管`homeGlobe`分支的逻辑写得对不对，用户平时打开页面看到的默认视角永远不会应用上这轮改动。

## 要做的事

找到`?earthCandidate=cameraGrammarV1`/`cameraGrammarAuto`这两个候选下，页面加载完成、开始渲染循环之后的初始化时机（应该在`_gramMotion`初始化附近，或者`createEarth3D()`内部渲染循环启动前后），补一次：
```js
transitionToComposition('homeGlobe', { duration: 0 })
```
**duration设为0，让它瞬间应用目标值（相机位置/辉光强度等），不会有肉眼可见的镜头移动**，因为默认视角本来就应该长得跟homeGlobe一样，这一步只是为了让`applyRimBoost`等这套逻辑真正跑一遍、把辉光增强值写进uniform。

**请你自己先确认**:这个"默认加载视角"跟`CAMERA_COMPOSITIONS`/`CAMERA_PRESETS`里`homeGlobe`对应的相机参数(位置/fov/lookAt)是否完全一致——如果不一致，直接调这个函数可能会让默认视角的相机位置产生肉眼可见的跳变，这种情况下请先告诉我两者的具体数值差异，不要直接调用，我们再决定怎么处理（比如只提取辉光相关的赋值逻辑单独调用，不动相机位置）。

## 严格边界

**只允许改动**:在合适的初始化时机新增这一次`transitionToComposition('homeGlobe', { duration: 0 })`调用（或者如果相机参数对不上、改成只提取其中辉光相关赋值的等效写法）。

**禁止改动**:`transitionToComposition()`/`_updateGramTransition()`内部逻辑本身；`RIM_BOOST_COMPOSITIONS`/`FAR_COMPOSITIONS`等常量；其余任何代码。

## 完成后请提供

1. git diff
2. 硬刷新页面(不点击任何构图按钮)，白天主题(noon/afternoon)和非白天主题(evening)各截一张默认加载视角的截图，确认辉光增强(outer/inner)已经生效，不再是"只有顶部亮"
3. 确认默认视角相机位置/构图跟改动前一致，没有肉眼可见的跳变或错位
4. 确认`cameraGrammarV1`/`cameraGrammarAuto`两个候选都验证过
5. 控制台无新增报错

## 验证方式

1. 不点任何按钮，硬刷新页面，默认视角就已经是辉光增强后的效果
2. 默认视角相机构图本身不受影响(不会因为这次改动而看起来变了位置/大小)
3. 后续手动切换构图(farOrbit等)行为不受影响
4. 控制台无新增报错
