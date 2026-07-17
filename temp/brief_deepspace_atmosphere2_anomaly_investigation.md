# 排查:所有远景构图下都存在的"光柱/光斑"，跟地球本体位置脱节，不是包裹球体的辉光

本轮阶段:排查定位(先查清楚这个"光柱"到底是什么渲染出来的,不要直接猜测性修复)
允许修改文件:仅 `pwa/earth3d.js`（排查阶段以临时调试代码为主，禁止在未确认根因前直接改动正式渲染逻辑）
禁止修改文件:其余所有文件
允许 commit:否

---

## 背景(重要:纠正之前的理解)

之前以为`farOrbit`/`oceanExpanse`/`polarDiagonal`/`cityAnchor`这四个构图辉光包裹已经生效，只有`deepSpace`有问题——**用户明确纠正：这是同一个问题，在所有构图里都存在，不是deepSpace独有的**。`deepSpace`只是因为地球缩得极小、位置也偏移了，才让这个问题从"看起来像是贴着地球边缘的辉光"变成了"明显跟地球脱节的一根光柱"，把真相暴露出来了——用户怀疑，在其他构图里，这个东西可能也只是恰好跟地球边缘重叠、造成"辉光包裹球体"的错觉，实际上根本不是跟着球体轮廓走的辉光。

## 已排除的可能性

查过`_horizonGlowEl`/`_rimGlowEl`(`earth3d.js:3232`起的`updateHorizonGlow()`，一套独立于`atmosphereMaterial`/`atmosphere2Material`的CSS DOM层辉光叠加系统)——白天四个主题(`morning`/`noon`/`afternoon`/`goldenApproach`)的`horizonGlow.enabled`全部是`false`，这套系统当前对白天主题完全不生效，不是这次的原因。

## 请按这个顺序排查(用现成的调试隔离工具，不要凭空猜)

### 第一步:用`atmosphereOnly`调试层隔离，确认这个"光柱"是不是`atmosphere`/`atmosphere2`本身

代码里已经有一个现成的调试模式(`earth3d.js:7188`附近，`setDebugLayer('atmosphereOnly')`分支)，会隐藏地球本体、只保留大气层渲染。请：

1. `?earthCandidate=cameraGrammarV1`，noon主题，触发`farOrbit`（或任意一个之前看起来"辉光包裹生效"的构图）
2. 控制台执行 `window.earth3d.setDebugLayer('atmosphereOnly')`
3. 截图——这时候画面里应该**只剩下大气层的辉光形状，没有地球本体**。看这个形状本身是不是一个贴合球体轮廓的环形/椭圆形，还是本来就是一根不规则的光柱/光斑
4. 如果形状本身就不对（不是贴合球体的环形），那问题就出在`atmosphere2Material`的shader渲染或者`atmosphere2`的定位/缩放上，不是"跟地球位置脱节"这么简单，需要继续查`atmosphere2`的实际`position`/`scale`/`uRadius`（可以顺便加一个临时`getAtmosphereDebugInfo()`调试方法到`earth3dApi`导出块，返回`atmosphere.visible/position/scale`、`atmosphere2.visible/position/scale`、`atmosphere2Material.uniforms.uRadius.value`这几个值，一并贴给我）
5. 用`window.earth3d.setDebugLayer('final')`恢复正常渲染，不要忘记这一步

### 第二步:确认这个光斑在画面里的屏幕位置是否"固定"，不随构图/相机变化

依次切换`homeGlobe`→`farOrbit`→`deepSpace`（每次切换后截图），观察这个光斑在**画面里的像素位置**是否几乎不变（比如始终在专辑标题文字下方、画面纵向40%-55%这个区域），而地球本体的位置/大小是明显变化的。如果光斑位置固定不变、只有地球在动，说明这个光斑根本不是3D场景里跟着地球走的物体，可能是被固定摆放在场景里某个不随相机变化的位置（比如没有正确parent到`earth`或者相机的物体上），或者是被写死了固定的NDC/屏幕坐标。

## 请提供

1. 第一步`atmosphereOnly`隔离截图 + 你对"这个形状本身对不对"的判断
2. 第二步几个构图下光斑位置是否固定的对比截图
3. 如果加了临时诊断方法，把返回的数值贴出来
4. 你的根因判断——**先不要写修复代码，把排查结果发给我，我们一起定下一步方案**
