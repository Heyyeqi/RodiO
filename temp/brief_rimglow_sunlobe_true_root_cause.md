# 真正的根因排查:辉光光斑其实来自rimGlow/sunLobe系统,不是atmosphereMaterial/atmosphere2

本轮阶段:验证假设(先证实是不是这个,再决定怎么改)
允许修改文件:仅 `pwa/earth3d.js`(临时诊断改动)
禁止修改文件:其余所有文件
允许 commit:否

---

## 背景(重大发现)

上一轮诊断确认:`farOrbit`下`atmosphere`和`atmosphere2`两层的`visible`都是`false`、`opacity`都是`0`,但画面上依然清楚可见一个顶部亮、向四周不规则扩散的光斑。**说明这五轮我们一直在调的`atmosphereMaterial`/`atmosphere2Material`,根本不是这个可见光斑的来源。**

回查代码发现:白天主题(`morning`/`noon`/`afternoon`/`goldenApproach`等)全部在`RIM_OVERLAY_THEMES`这个集合里(`earth3d.js:3188`),会额外走一条渲染路径(`earth3d.js:6724`起的`RIM_OVERLAY_THEMES.has(currentTheme)`分支),渲染一个**完全独立的"Rim Overlay + 太阳光斑(sunLobe)"系统**——`applyRimGlowThemeConfig()`(`earth3d.js:2704`)配置的`_emRimOverlayMat`/`_emInnerVeilMat`,通过`earlyMorningRimOverlayScene`+`earlyMorningRimOverlayCamera`单独渲染一层。

这个系统里有个叫`sunLobe`的效果,参数包括:
```js
uSunLobeX / uSunLobeY          // 光斑在投影范围内的位置(默认0.86, 0.35)
uSunLobeHStretch: 2.8          // 水平拉伸
uSunLobeVCompress: 0.50        // 垂直压缩
uSunLobeStrength / uSunLobeWidth / uSunLobeFalloff
```
"水平拉伸+垂直压缩"这个设计,本来就是做成一个"定向的、不规则的光斑",而不是均匀包裹球体轮廓的环形辉光。这跟这几轮反复看到的"顶部亮、四周不规则扩散"的现象完全吻合，怀疑这才是真正的视觉元凶。

## 请做这几步验证

### 1. 临时关闭rimGlow/sunLobe这条渲染路径，看光斑是否消失

`earth3d.js:6724`附近：
```js
} else if (RIM_OVERLAY_THEMES.has(currentTheme)) {
  updateEarlyMorningGlowMode()
  updateEarlyMorningRimProjection()
  renderer.autoClear = false
  renderer.clear(true, true, true)
  renderer.render(scene, camera)
  renderer.clearDepth()
  renderer.render(earlyMorningRimOverlayScene, earlyMorningRimOverlayCamera)  // ← 临时注释掉这一行
  renderer.autoClear = true
}
```
临时把`renderer.render(earlyMorningRimOverlayScene, earlyMorningRimOverlayCamera)`这一行注释掉（只是为了验证，不是正式修复），在`?earthCandidate=cameraGrammarV1`、noon主题下触发`farOrbit`，截图看那个顶部光斑是否消失了。

如果消失了，就实锤是这套rimGlow/sunLobe系统产生的，不是atmosphere2。

### 2. 如果验证成立，先不要直接改，把这几个信息报给我

- 这套rimGlow系统对应的`THEME_VISUAL_CONFIG[主题].rimGlow`配置具体长什么样（`outer`/`inner`/`sunLobe`三块的实际数值，尤其是白天主题noon/afternoon/goldenApproach各自的）
- `updateEarlyMorningRimProjection()`(`earth3d.js:2798`起)是否真的会随着构图/相机距离正确更新投影范围（这个函数看起来是有做真实的3D投影计算的，不是完全固定屏幕位置，但请实际测一下：从`homeGlobe`切到`farOrbit`再到`deepSpace`，这个光斑投影范围是否有跟着地球大小/位置变化，还是不管构图怎么切、这个光斑范围看起来都差不多）
- 这套系统本身叫"Rim Overlay"，是否有一个"是否要包裹整个球体"的现成开关/参数，还是设计上就是"定向单侧光斑"这个思路，如果是后者，要不要在这个系统上做"远景包裹"的效果，需要新的设计思路（不是简单调参数），我们拿到你的排查结果后再一起决定怎么做，这轮先不要写正式修复代码

## 请提供

1. 注释掉那行代码前后的对比截图（有没有消失）
2. 对应主题的`rimGlow`配置数值
3. 这个光斑范围是否随构图正确缩放/定位的测试结果
4. 记得测完把注释的代码改回来，这只是验证用的临时改动，不能带着注释提交
