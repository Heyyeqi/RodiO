# 降低远景构图辉光厚度,参照homeGlobe的观感调整

本轮阶段:数值调整(视觉测试为主)
允许修改文件:仅 `pwa/earth3d.js`
允许 commit:否

---

## 背景

用户反馈：远景构图（比如`sunset`主题下当前这个视角）辉光"太厚了，像一条带子"，希望调整到接近`homeGlobe`(近景默认视角)的厚度观感。

`FAR_VIEW_ATMOSPHERE.opacity`(`earth3d.js:6466`附近)当前是`0.60`——这个是在排查"断崖"问题的过程中逐步调高的，比最早验证过的`0.30`整整高了一倍，现在确实偏厚。

## 要做的事

把`FAR_VIEW_ATMOSPHERE`的`opacity`降低，从`0.60`往下调，建议先试`0.30`左右作为起点：

```js
const FAR_VIEW_ATMOSPHERE = { opacity: 0.30, sunInfluence: 0.08, power: 2.6, powerOuter: 2.2, strengthOuter: 0.35 }
```

（`sunInfluence`/`power`/`powerOuter`保持不变，这几个是之前专门解决"断崖"问题时调出来的，不要动；`strengthOuter`如果视觉上觉得也偏厚可以适度下调，但先看只降`opacity`是否已经足够）

**请你先视觉对比`homeGlobe`当前的辉光厚度**（同一主题下，先看homeGlobe，再看远景构图），把`opacity`调到两者观感接近的程度，不需要完全一致，但不能像现在这样"厚一整圈像条带子"。可以在`0.20~0.40`这个区间内试几个值，找到满意的为止。

## 请提供

1. git diff
2. 调整前后的对比截图（远景构图 + homeGlobe，同一主题）
3. 最终确定的`opacity`数值
4. 确认整圈辉光（之前解决的"断崖"问题）没有因为这次调整重新出现——降低opacity不会让暗侧的辉光又低到看不见
5. 控制台无新增报错
