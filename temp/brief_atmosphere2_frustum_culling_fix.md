# 修复:atmosphere2网格缺少frustumCulled=false,导致远景辉光出现硬边界裁切

本轮阶段:直接修复(小范围、根因明确)
允许修改文件:仅 `pwa/earth3d.js`
禁止修改文件:其余所有文件
允许 commit:否,除非我后续明确批准

---

## 背景

上一轮切换到`atmosphere2`(BackSide)后,用户实测发现辉光呈现出"硬边界裁切"的效果——不是均匀的球面渐变,而是像被矩形边框裁掉了一部分,边界很生硬。

## 根因(已读代码确认)

`atmosphere`(第一层大气,`earth3d.js:2153-2161`)构造时正确设置了：
```js
atmosphere.frustumCulled = false
atmosphere.renderOrder = 1
```

但`atmosphere2`(第二层大气,`earth3d.js:2182-2186`)构造时**完全没有设置这两行**：
```js
atmosphere2 = new THREE.Mesh(
  new THREE.SphereGeometry(1, SPHERE_SEGMENTS, SPHERE_SEGMENTS),
  atmosphere2Material
)
atmosphere2.visible = false
```

`_atmVert`shader(`earth3d.js:2082-2096`)在顶点着色器里用`uRadius`动态放大几何体(`position * uRadius`),但`frustumCulled`默认值是`true`，Three.js做视锥体裁剪判断时用的是**几何体原始（未放大）的包围盒**——没有关闭`frustumCulled`的话，实际渲染时放大后的球体，一部分会因为跟相机视锥角度关系被误判裁掉，导致边界生硬、随镜头角度变化的裁切现象。

这个问题以前从未暴露，是因为`atmosphere2.visible`一直是`false`（只在一个调试隔离工具里才会显示），直到上一轮才第一次真正启用它渲染。

## 要做的事

在`atmosphere2`构造之后（`earth3d.js:2186`附近，`atmosphere2.visible = false`那一行）补上跟`atmosphere`完全对称的两行：
```js
atmosphere2 = new THREE.Mesh(
  new THREE.SphereGeometry(1, SPHERE_SEGMENTS, SPHERE_SEGMENTS),
  atmosphere2Material
)
atmosphere2.visible = false
atmosphere2.frustumCulled = false
atmosphere2.renderOrder = 1
```

## 严格边界

**只允许改动**：`atmosphere2`构造后新增这两行属性设置。

**禁止改动**：其余任何代码，包括上一轮已经落地的`atmosphere2Material.uniforms`插值逻辑、`FAR_COMPOSITIONS`、`transitionToComposition()`/`_updateGramTransition()`里的其他内容。

## 完成后请提供

1. git diff（应该只有新增两行）
2. `?earthCandidate=cameraGrammarV1`，白天主题下触发`farOrbit`，转动镜头角度或等待自转一会儿，确认辉光不再出现随角度变化的硬边界裁切，是自然的球面渐变
3. 控制台无新增报错

## 验证方式

1. far视角下辉光边界自然，不再有"结界"一样的硬边框裁切
2. 转动/自转过程中辉光不会随镜头角度出现忽隐忽现的裁切
3. 近景、夜间主题、其余候选不受影响
4. 控制台无新增报错
