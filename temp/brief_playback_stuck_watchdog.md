# Brief:修复播放偶发卡住不自动切歌——加一个兜底超时机制

## 背景

用户反馈播放会偶发卡住,放几首歌后就不再自动切下一首,这个问题不是新出现的,之前就发生过。

## 根因(已定位)

`pwa/index.html:1293-1309`,Spotify的`player_state_changed`监听器判断"歌曲自然播完、该切下一首"用的是这个条件:
```js
if (wasPlaying && s.paused && s.position === 0 && currentUri && currentUri === spotifyCurrentUri) {
  spotifyCurrentUri = null
  advanceToNext('complete')
}
```
这四个条件必须**同时精确命中**才会触发切歌,而且**没有任何兜底机制**——如果Spotify SDK某一次状态回调没有精确匹配上(比如`position`不是刚好等于0、或者URI在这次回调里还没来得及更新),这次"播完了"的信号就直接错过,不会有任何后续的自动纠正,播放就停在原地不会再往下走了。

全局搜索确认过,现在完全没有任何"歌曲应该已经放完但没检测到就强制切下一首"这类超时兜底逻辑。

## 要做的事

加一个"看门狗"超时定时器,跟现有的精确检测机制并存,不是替换它——精确检测正常触发时该怎么样还怎么样,只是多一层保险:如果精确检测没有按时触发,超时之后强制切歌。

### 具体实现

在`playSong(item, options)`里(约2466行起),歌曲**真正开始播放确认之后**(Spotify路径`spotifyPlay(...).then(ok => {...})`成功分支里,NCM路径`audio.play().then(...)`成功分支里),启动一个超时定时器:

```js
let _songEndWatchdogTimer = null   // 模块级变量，跟其他类似的状态变量放一起

function armSongEndWatchdog(durationSeconds, trackRef) {
  clearSongEndWatchdog()
  if (!durationSeconds || durationSeconds <= 0) return   // 时长未知时不设兜底，避免误伤
  const graceMs = (durationSeconds + 5) * 1000   // 歌曲时长 + 5秒缓冲
  _songEndWatchdogTimer = setTimeout(() => {
    // 仍然是同一首歌、且仍然认为在播放，说明精确检测没有正常触发，强制切歌
    if (state.currentTrack === trackRef && state.playing) {
      console.warn('[watchdog] 歌曲应已播完但未检测到自动切歌，强制推进')
      advanceToNext('complete')
    }
  }, graceMs)
}

function clearSongEndWatchdog() {
  if (_songEndWatchdogTimer) {
    clearTimeout(_songEndWatchdogTimer)
    _songEndWatchdogTimer = null
  }
}
```

**调用时机:**
- 歌曲开始播放确认后（Spotify和NCM两条路径都要），调用`armSongEndWatchdog(state.duration, state.currentTrack)`——注意此时`state.duration`可能还没到位（尤其Spotify刚开始播放的瞬间），可以在`player_state_changed`第一次拿到有效`s.duration`时再correction一次（重新调用`armSongEndWatchdog`用真实时长覆盖）
- 每次真正切歌（不管是精确检测触发的`advanceToNext('complete')`、用户手动切歌、跳过、上一首）都要调用`clearSongEndWatchdog()`，避免旧定时器在切歌之后错误触发
- `advanceToNext()`函数开头（约2736行）加一行`clearSongEndWatchdog()`，这样不管是通过哪条路径触发的切歌，看门狗都会被清掉，不会重复触发

**判断"仍然是同一首歌"** 用`state.currentTrack === trackRef`（对象引用比较，不是内容比较）——因为切歌时`state.currentTrack`会被赋值成一个新对象，只要真的切过歌，引用就不相等了，能可靠区分"这首歌还在播（该切没切）"和"已经手动切到别的歌了（不需要看门狗介入）"。

## 不要做的事

- 不要改动现有的精确检测逻辑（第1293-1309行的`player_state_changed`判断条件本身不用动）
- 不要碰这次的相机/地球转动相关代码
- 时长未知的情况下（`durationSeconds`为0或者undefined）不要设置兜底定时器，宁可不设保护也不要因为时长不对而误伤正常播放中的歌（提前切歌比不切歌更糟糕）

## 验证方式

1. 本地起服务，正常播放，让几首歌完整播完，确认精确检测路径依然正常工作、没有被看门狗干扰（不应该出现"看门狗"的console warn日志，因为精确检测应该先一步触发）
2. 如果方便复现原来的卡住场景（比如手动在浏览器devtools里模拟网络波动、或者故意不触发`player_state_changed`），确认看门狗超时后真的会强制切歌，并且console里能看到`[watchdog] 歌曲应已播完但未检测到自动切歌，强制推进`这条日志
3. 确认手动点"下一首"/"上一首"按钮时，旧的看门狗定时器被正确清除，不会在切完歌之后突然又莫名其妙触发一次
