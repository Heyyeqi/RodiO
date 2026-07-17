# 排查:night主题整个球体偏黄,不只是城市灯光的问题

本轮阶段:排查定位(不要直接修复,先确认根因)
允许修改文件:无(控制台查询+截图)

---

## 背景(纠正之前的判断)

之前的判断("emissiveColor暖色只影响城市灯光亮点，是一直如此的设计")不完整——用户明确反馈：**整个地球球体的底色都偏黄偏暖，包括应该是深蓝黑色的海洋/无城市区域**，不只是城市灯光那几个亮点。`mapColor: 0x040810`(深蓝黑)已经确认是正确的当前值，但渲染出来的整体观感依然发黄，这不对，需要重新查。

## 请排查这几个方向

### 1. 先确认"整个球体偏黄"这个现象的具体范围

`?earthCandidate=precomputeschedule`(或任意能看到night主题的地方)，找一片明显没有城市灯光的区域(比如太平洋中间的大片海洋)，放大截图看这片区域的实际颜色——是深蓝黑，还是也带黄/棕色调？

### 2. 检查城市灯光识别阈值(`uCityLumLow`/`uCityLumHigh`)是不是设得太低导致"误伤"

控制台执行：
```js
const st = window.earth3d.getDebugState()
console.log(st.uniforms)
```
重点看`uCityLumLow`/`uCityLumHigh`这两个值。这两个值控制"多暗的像素才算城市灯光、该被套上`emissiveColor`暖色"——如果这两个阈值相对`night`主题的`mapColor`(很暗的0x040810)来说设得过低，可能导致原本应该是"纯黑无城市"的暗色海洋像素，也被误判成"城市"，被套上了`emissiveColor(0xffc86e)`暖色调，造成大片区域(不只是真正的城市)都发黄。

### 3. 检查`onBeforeCompile`里"城市灯光识别"那段shader逻辑(`earth3d.js`大约1940-2075行`#include <emissivemap_fragment>`注入块)

看`_lMask`(城市光识别遮罩)的计算逻辑，结合`night`主题实际的`emissiveMap`(Black Marble夜景灯光贴图)纹理数据，判断这个遮罩在`night`主题下，是不是覆盖了远超"真实城市光斑"的范围(比如整个大陆轮廓、甚至部分海洋，而不只是星星点点的城市)。

### 4. 检查`night`主题是否被其他主题的"nightGrade"或者相关配置意外影响

`night`主题本身没有定义`nightGrade`(之前确认过是`null`)，`resetNightGradeUniforms()`会把相关uniform清零——但请确认一下这个清零逻辑是否完整，会不会有个别uniform没有被正确重置成"不产生暖色影响"的默认值，残留了别的主题(比如`deepNight`)的暖色调设置。

## 请提供

1. 第1步的截图(纯海洋区域颜色特写)
2. `uCityLumLow`/`uCityLumHigh`实际数值，以及你的判断——这两个值是否偏低导致误判范围过大
3. 你对"整个球体偏黄"这个现象根因的判断
4. **不需要现在就修复，先把排查结果发回来确认根因**
