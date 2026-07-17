# 打回:`_updatePrecomputeMotion()`读的字段名不对,整个功能没生效

## 问题

`_updatePrecomputeMotion()`里所有地方都在读`vs.current`(`vs.current?.duration_ms`、`vs.current`三元判断、`vs.current?.rhythmic_motion`),但`window.__rodioVisualState`是`state`对象的直接引用,这个对象里存当前播放曲目的字段叫**`currentTrack`**,不是`current`——全局搜索`state.currentTrack`能看到`pwa/index.html`里到处都是这个字段名(1210行赋值、1391/2139/2151/2163/2186行等多处读取),从来没有一个叫`current`的字段。

实际后果:`vs.current`永远是`undefined`,所以:
```js
const trackKey = vs.current ? `${...}` : ''   // 永远是空字符串
const trackChanged = trackKey && trackKey !== _lastTrackKey   // 空字符串是falsy，永远是false
```
`trackChanged`永远算不出true,`buildSchedule()`永远不会被调用,`_precomputeMotion.schedule`永远是null,整个功能从头到尾没有真正生效过——不管播放什么歌、播多久,`window.__rodioVisualState._precomputeLonOffset`应该会一直卡在最初的0(走的是`if (!_precomputeMotion.schedule) { ...; return }`这条早退分支)。

## 修复

把`_updatePrecomputeMotion()`里所有的`vs.current`改成`vs.currentTrack`。具体这几处:
```js
const dur = vs.currentTrack?.duration_ms ? vs.currentTrack.duration_ms / 1000 : (vs.duration || 0)
const trackKey = vs.currentTrack ? `${String(vs.currentTrack.name || '').trim()}::${String(vs.currentTrack.artist || '').trim()}` : ''
...
const rm = vs.currentTrack?.rhythmic_motion
```

## 验证要求(这次必须证明功能真的跑起来了,不能只改完字段名就说完成)

1. 改完之后,本地起服务,加`?earthCandidate=precomputeschedule`,播放一首歌
2. 在浏览器console里执行`window.__rodioVisualState._precomputeLonOffset`,**在播放过程中多次执行、间隔几秒**,确认这个值真的在变化(不是恒为0,也不是恒为一个固定值)
3. 把这几次执行的实际返回值贴给我看(带时间间隔),不要只说"已修复"
4. 如果方便的话,顺便贴一下这首歌在DB里的`rhythmic_motion`值,和你自己按公式估算的预期totalLaps,方便我核对数量级对不对
