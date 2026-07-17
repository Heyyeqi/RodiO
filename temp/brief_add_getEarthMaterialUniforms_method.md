# 补一个诊断方法:暴露完整的earthMaterial shader uniforms(包含Night Grade那批参数)

本轮阶段:只加一个只读诊断方法，不改任何渲染逻辑
允许修改文件:仅 `pwa/earth3d.js`
允许 commit:否

---

## 背景

之前的uniform对比用的是`getDebugState().uniforms`，这个只包含Ocean/Land/City相关的一小部分参数，**不包含`uNightExposure`/`uNightSaturation`/`uNightGamma`/`uNightBlueBias`/`uNightGreenBias`/`uNightRedReduce`/`uDaybaseMode`/`uTropicalDarken`/`uAridDarken`/`uIceNeutralize`/`uOceanRawMix`/`uOceanRawExposure`/`uOceanRawBlueKeep`这批参数**——而这批恰恰是`_deMagenta`/nightGrade这次调查最相关的参数。需要一个新方法把完整的`earthShaderUniforms`暴露出来。

## 要做的事

在`earth3dApi`导出块（`Object.assign(earth3dApi, {...})`那里，随便找个合适的位置）新增：

```js
getEarthMaterialUniforms() {
  if (!earthShaderUniforms) return null
  const out = {}
  for (const key in earthShaderUniforms) {
    out[key] = earthShaderUniforms[key]?.value
  }
  return out
},
```

`earthShaderUniforms`是已有的模块级变量（`onBeforeCompile`里`earthShaderUniforms = shader.uniforms`那一行设置的），这次只是新增一个只读的getter方法把它暴露到`window.earth3d`上，不改动`earthShaderUniforms`本身或者任何渲染逻辑。

## 请提供

1. git diff（应该只有新增这一个方法）
2. 硬刷新后，控制台执行 `window.earth3d.getEarthMaterialUniforms()`，确认能拿到包含`uNightExposure`等完整参数的对象，贴一下返回结果确认方法可用
3. 控制台无新增报错

**这轮只加方法，不需要做任何对比分析或者修复判断，我这边确认方法可用后会自己在控制台里对比。**
