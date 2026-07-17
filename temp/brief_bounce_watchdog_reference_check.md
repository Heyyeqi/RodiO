# 打回:看门狗的"是否还是同一首歌"判断用了错误的比较方式,永远不会真正触发

## 问题(已核实,不是猜测)

`armSongEndWatchdog(durationSeconds, trackRef)`(`pwa/index.html:1109-1118`)里,超时判断用的是:
```js
if (state.currentTrack === trackRef && state.playing) {
```
这是**对象引用比较**。但`syncCurrentTrackFromSpotifyState()`(`pwa/index.html:1220-1240`)在**每一次**Spotify的`player_state_changed`事件触发时(不只是切歌,同一首歌播放过程中的普通位置/暂停状态更新也会触发这个函数)都会执行:
```js
const nextTrack = { id: ..., name: ..., artist: ... }
// ...
state.currentTrack = nextTrack   // 每次都是全新对象
```
也就是说,`state.currentTrack`这个对象引用在整首歌播放期间会被反复替换成新对象,不是"同一首歌就应该是同一个对象"。等到看门狗的定时器真正触发的时候(`duration+5`秒之后),中间早就发生过很多次`player_state_changed`,`state.currentTrack`早已经指向了别的对象实例(即使逻辑上还是同一首歌)——`state.currentTrack === trackRef`这个判断因此**永远是false**,看门狗的兜底逻辑实际上从来不会真正执行,整个修复没有起到任何效果。

## 修复方式

把对象引用比较,换成基于内容的稳定标识比较(name+artist拼接,不用id,因为不同来源产生的id格式可能不一致,这个坑之前处理精确落点旋转时已经踩过一次了):

```js
function armSongEndWatchdog(durationSeconds, trackRef) {
  clearSongEndWatchdog()
  if (!durationSeconds || durationSeconds <= 0) return
  const trackKey = trackRef ? `${String(trackRef.name || '').trim()}::${String(trackRef.artist || '').trim()}` : ''
  if (!trackKey) return
  const graceMs = (durationSeconds + 5) * 1000
  _songEndWatchdogTimer = setTimeout(() => {
    const currentKey = state.currentTrack
      ? `${String(state.currentTrack.name || '').trim()}::${String(state.currentTrack.artist || '').trim()}`
      : ''
    if (currentKey === trackKey && state.playing) {
      console.warn('[watchdog] 歌曲应已播完但未检测到自动切歌，强制推进')
      advanceToNext('complete')
    }
  }, graceMs)
}
```

三处调用（`pwa/index.html:1323`/`2525`/`2574`）不用改，传参方式一样，只是函数内部的判断逻辑换成基于name+artist的字符串比较。

## 验证方式(这次尤其要验证"没有提前误触发"和"真的能触发"两种情况都对)

1. 正常完整播放几首歌,确认精确检测路径正常工作(不应该看到`[watchdog]`日志,因为精确检测应该先一步触发并清掉定时器)
2. **重点验证看门狗真的会触发**:可以人为制造一次"精确检测漏掉"的场景来测试——比如在浏览器devtools里找到`player_state_changed`的回调,临时用条件断点跳过它一次,或者更简单的办法:随便找一首歌,记下它的`duration`,手动等到`duration+5`秒左右,观察console是否出现`[watchdog]`日志并真的切到了下一首。不要只是"看代码逻辑觉得应该没问题"就算完成,这次必须有实际触发一次看门狗的证据。
3. 确认同一首歌播放期间正常的`player_state_changed`更新(不涉及切歌)不会误触发看门狗提前切歌
