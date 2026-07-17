# 打回:Level1 Motion读取播放状态的方式绕开了正确的数据源

## 问题

`_updateLevel1Motion()`里用`document.querySelector('audio')`直接查HTML的`<audio>`元素来判断`isPlaying`/`currentTime`/`duration`。这个元素**只在NCM播放路径下真正被使用**——已经实测确认过,Spotify播放时`audio.src`是空字符串、`audio.paused`恒为true,即使Spotify正在真实播放。RodiO主力播放走的是Spotify,NCM只是Spotify不可用时的降级路径。也就是说现在这个实现,对绝大多数真实听歌场景(走Spotify的时候)完全检测不到播放状态,`isPlaying`永远算出来是false,整套Level 1逻辑等于失效。

## 正确的数据源

`pwa/index.html:1829` 有 `window.__rodioVisualState = state`——这是直接引用赋值,不是拷贝。`state.playing`(全局搜索`state.playing =`能看到Spotify轮询路径`pwa/index.html:1292`附近和NCM `<audio>`事件`pwa/index.html:4917/4921`都会写这个字段)、`state.progress`、`state.duration`(同样两条路径都写,`pwa/index.html:1293-1294`/`1387-1388`是Spotify的,`4912-4913`是NCM的)已经是跨两种播放后端统一好的正确字段,不用重新发明。

`getTargetOrientation`函数(`_updateLevel1Motion`旁边不远)里读`vs.lon`/`vs.lat`用的就是这同一个`window.__rodioVisualState`对象——`_updateLevel1Motion`应该用同样的方式读`vs.playing`/`vs.progress`/`vs.duration`,而不是另外查DOM里的`<audio>`元素。

## 修复要求

把`_updateLevel1Motion()`里所有`document.querySelector('audio')`相关的读取,改成从`window.__rodioVisualState`(或者直接用已经在用的`vs`变量)读:
```js
const vs = window.__rodioVisualState || {}
const isPlaying = !!vs.playing
const dur = vs.duration || 0
const cur = vs.progress || 0
```
其余的减速/加速/切歌归零逻辑不用变,只是数据来源换掉。

## 验证方式(这次必须实测,不能只改完代码就说完成)

1. 本地起服务,确认Spotify授权可用的情况下(不是NCM降级),加`?earthCandidate=level1motion`播放一首歌
2. 打印或者用调试面板确认`_level1Motion`内部的`isPlaying`/`currentSpeed`真的随Spotify播放状态变化,不是恒为0
3. 暂停/恢复/切歌/歌曲快结束这几个场景都要在Spotify播放路径下各测一次,不能只测NCM路径
4. 把每一步观察到的实际现象(不是"应该会怎样"的推测)贴给我
