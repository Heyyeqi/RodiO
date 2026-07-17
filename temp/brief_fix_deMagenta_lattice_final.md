# 修复:_deMagenta五重smoothstep链导致night主题海洋区域菱形纹路

本轮阶段:直接修复(根因已经过多轮验证确认，包括"只有night主题出现"这个关键证据)
允许修改文件:仅 `pwa/earth3d.js`
允许 commit:否，除非我后续明确批准

---

## 背景(根因已确认)

经过多轮排查，包括专门验证"这个海洋区域菱形/风筝状重复纹路是否只在night主题出现"——**确认只有night有，noon/afternoon等白天主题下同一构图/同一视角完全没有这个纹路**。`_deMagenta`这段逻辑（`earth3d.js`大约1833-1844行，属于`rodioApplyNightGrade()`，只在night-grade相关主题下执行）是唯一符合"仅night专属"这个特征的候选，确认为根因。

## 要做的事

采用之前诊断报告里的**方案A**：把5重`smoothstep`连乘替换成单次`smoothstep`，消除多层阈值叠加产生的阶梯/纹路：

```glsl
// 原来（earth3d.js:1834附近，5重连乘）：
float _deMagenta = smoothstep(0.018, 0.0, _nightMagenta)
                * smoothstep(0.026, 0.008, _nightMagenta)
                * smoothstep(0.034, 0.016, _nightMagenta)
                * smoothstep(0.042, 0.024, _nightMagenta)
                * smoothstep(0.050, 0.032, _nightMagenta);

// 改成单次smoothstep：
float _deMagenta = smoothstep(0.050, 0.0, _nightMagenta);
```

（这一行的具体阈值范围`0.0`到`0.050`是覆盖原来5重链条整体范围的一个合理近似，如果替换后视觉测试发现去紫效果跟之前差异明显，可以在保持"单次smoothstep"这个结构不变的前提下，微调这两个阈值数字，但不要恢复成多重连乘的写法）

**只改这一行的计算方式，`_deMagenta`后续如何使用(跟`_neutralCool`混合那部分)保持不变，不要一起改。**

## 严格边界

**只允许改动**：`_deMagenta`的计算公式，从5重`smoothstep`连乘改成单次`smoothstep`。

**禁止改动**：这次不要顺带碰`_neutralCool`的颜色值、`_deMagenta * 0.82`这个混合强度、shader精度声明(`mediump`/`highp`)、或者其他任何`nightGrade`相关的代码——只改这一处，方便如果效果不对，能精确知道是不是这一行改动导致的。

## 完成后请提供

1. git diff（应该只有这一行公式的改动）
2. **同样的对比验证**：用之前验证时用过的同一个构图/视角，分别截图`noon`（确认依然没有纹路，行为不受影响）和`night`（确认海洋区域的菱形纹路是否消失）
3. 额外确认：`night`主题下陆地区域整体色调是否依旧正常（没有因为简化smoothstep而出现新的偏色问题，比如之前"去紫"要解决的原始暖色/偏紫问题有没有重新冒出来）
4. 确认其余夜间主题(`deepNight`/`lateEvening`/`evening`)不受影响（它们如果也有类似的`_deMagenta`逻辑或者共用这段代码，需要一并截图确认）
5. 控制台无新增报错

## 验证方式

1. `night`主题海洋区域的菱形纹路消失
2. `noon`等白天主题不受影响（本来就没有这段逻辑，确认没有意外引入新问题）
3. `night`主题陆地整体色调正常，没有重新出现之前修复过的暖色/偏紫问题
4. 其余夜间主题不受影响
5. 控制台无新增报错
