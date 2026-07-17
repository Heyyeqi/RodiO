# 紫色三角形排查:纠正上一轮结论里的逻辑矛盾,补上遗漏的关键uniform

本轮阶段:纠正+补充排查，不要直接采信上一轮的结论去修复
允许操作:控制台命令 + 截图

---

## 上一轮结论里的问题

### 问题1：因果关系安在了错的主题上

上一轮报告说"`deepNight`主题下`emissiveMapIsNightTexture=false`（纹理绑定异常），据此推断这是紫色三角形的根因"——但紫色三角形明确只出现在`night`主题，`deepNight`没有这个问题（报告自己也确认过这一点）。**如果纹理绑定异常出现在没有bug的deepNight身上，这个异常不可能是"night出bug"的原因**，因果关系反了。

**请重新明确回答**：`emissiveMapIsNightTexture`/`nightTexture.isExpectedTexture`这两个值，在**`night`主题**（有bug的那个）下具体是什么？跟`deepNight`（没有bug的那个）相比，`night`自己身上有没有异常？不要只报告deepNight那边的数值。

### 问题2：uniform对比可能遗漏了最相关的参数

上一轮列出的`night`/`deepNight`两组uniform，里面**没有出现`uNightExposure`/`uNightSaturation`/`uNightGamma`/`uNightBlueBias`/`uNightGreenBias`/`uNightRedReduce`/`uDaybaseMode`/`uTropicalDarken`/`uAridDarken`/`uIceNeutralize`/`uOceanRawMix`/`uOceanRawExposure`/`uOceanRawBlueKeep`这些参数**——但`night`的配置里明确写了`nightGrade: { daybaseMode: true, ... }`，这些参数应该是存在且有实际数值的。`getDebugState().uniforms`很可能只返回了一部分uniform（比如只有"Ocean/Land"相关的那一批，没有"Night Grade"这一批），这次对比漏掉了最可能相关的参数组。

**请用这个方式重新拿到完整的uniform**（不要依赖`getDebugState()`，直接从shader材质本身读）：
```js
// 切到night主题
const uniforms = window.earth3d.getEarthMaterialUniforms ? window.earth3d.getEarthMaterialUniforms() : null
if (!uniforms) {
  console.log('没有现成方法，需要临时加一个到earth3dApi：')
  console.log(`
getEarthMaterialUniforms() {
  if (!earthShaderUniforms) return null
  const out = {}
  for (const key in earthShaderUniforms) {
    out[key] = earthShaderUniforms[key]?.value
  }
  return out
},
  `)
}
```
加上这个方法后，分别在`night`和`deepNight`下调用，把**完整的**uniform列表（包括所有`uNight*`/`uDaybaseMode`/`uTropical*`/`uArid*`/`uIceNeutralize`/`uOceanRaw*`这些）贴出来对比，逐项列出差异。

## 请提供

1. `night`主题下`emissiveMapIsNightTexture`/`nightTexture.isExpectedTexture`的实际值（不是deepNight的）
2. 用`getEarthMaterialUniforms()`（或等效方法）拿到的完整uniform对比，包含所有nightGrade相关参数
3. 基于这份更完整数据的根因判断——**这次请确保结论里提到的"异常项"，真的是出现在`night`（有bug）身上，而不是`deepNight`（没有bug）身上**
4. 不需要现在就修复，先把纠正后的数据发回来
