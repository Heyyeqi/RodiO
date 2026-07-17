# Brief:统一DJ讲解/TTS触发机制(修复"下一首歌没播放TTS就出现"的问题)

## 背景与根因

目前有两套独立的讲解(commentary)/TTS触发逻辑,互相冲突:

1. **`playExplainBeforeNext()`**(`pwa/index.html:2635`起),由 Spotify 进度轮询(`pwa/index.html:1390`,每秒一次)和 NCM 的 `audio` 元素 `timeupdate` 事件(`pwa/index.html:4837`)共同调用。逻辑是:只要当前播放歌曲剩余时长 `remaining < 25`(秒),就把**下一首**歌曲的预取(prefetch)讲解语音提前播放出来。这是"下一首歌还没开始播、TTS就先出现了"的直接原因——这是故意设计的"预告下一首"逻辑,不是意外触发的bug。

2. **`maybeAutoExplain(item)`**(`pwa/index.html:2992`起),在歌曲**开始播放确认后**(Spotify: `spotifyPlay()` resolve 后；NCM: `audio.play()` resolve 后)用 `setTimeout(..., 1200)` 延迟1.2秒触发当前歌曲的讲解。**这个延迟应该是5秒,不是1.2秒**——1200 这个数字看起来是历史遗留的错误值。同时这个 `setTimeout` **完全没有失效检查**:如果这1.2秒内歌曲又切换了(用户手动切歌、自动跳过失败重试等),定时器到点后依然会为**已经不是当前播放曲目**的那首歌调用 `explainTrack`,造成播报内容和实际播放的歌对不上。

两套机制共用一个 `autoExplainedTracks` Set 作为"是否已讲解过"的去重标记,但因为 (1) 有长达25秒的触发窗口、(2) 通常比 (2) 更早满足条件,几乎总是 (1) 先抢到触发权，导致用户听到的顺序是"当前歌快结束时，插入下一首的讲解，然后下一首开始播放、却没有自己的讲解"——和"歌曲播放后延迟出现讲解"的预期设计不符。

## 设计目标(统一为单一触发机制)

**只保留"歌曲确认开始播放后延迟5秒触发讲解"这一套逻辑，去掉"提前预告下一首"的逻辑。**

### 1. 删除 `playExplainBeforeNext()` 的调用

删除这两处调用:
- `pwa/index.html:1390`(Spotify 进度轮询 `setInterval` 内)
- `pwa/index.html:4837`(`audio.addEventListener('timeupdate', ...)` 内)

`playExplainBeforeNext()` 函数本身(`pwa/index.html:2635`起)可以直接删除；如果你觉得以后可能还有用，也可以保留函数定义但不再调用（加一行注释说明已停用），你自行判断哪种更干净。

### 2. `maybeAutoExplain` 延迟改为 5000ms

`pwa/index.html:3030` 附近的 `}, 1200)` 改成 `}, 5000)`。

### 3. 加"歌曲已切换则取消"的保护

新增一个模块级变量记录当前挂起的定时器和它对应的曲目key，例如：
```js
let pendingAutoExplainTimer = null
let pendingAutoExplainKey = null
```

`maybeAutoExplain(item)` 内部:
- 设置定时器前，先记录 `pendingAutoExplainKey = explainKey`，并把 `setTimeout` 的返回值存入 `pendingAutoExplainTimer`
- 定时器回调触发时，**先检查** `state.currentTrack` 算出的 key 是否还等于 `pendingAutoExplainKey`（用现有的 `makeTrackKey` 或和 `explainKey` 同样的拼接方式 `state.currentTrack.name + '::' + state.currentTrack.artist`）——**不相等就直接 return，不执行任何讲解/播报逻辑**

`playSong(item, options)` 函数最开头（`pwa/index.html:2401` 附近，和现有的 `activeExplainToken += 1` 那行一起）：
- 如果 `pendingAutoExplainTimer` 不为空，调用 `clearTimeout(pendingAutoExplainTimer)` 清掉上一首歌还没触发的讲解定时器，避免歌曲快速切换时出现堆叠

### 不要改动的部分

- `prefetchNextExplain()`(`pwa/index.html:2602`)保持不动——它只是静默预取接下来2首歌的讲解文本+语音存入缓存，不涉及播放触发，`maybeAutoExplain` 命中缓存时依然可以用它加速（缓存命中直接用，不用等 `/api/explain` 网络请求）
- `explainTrack()`、`explainCurrentTrack()`（手动点击"讲解"按钮触发的路径）不受影响，这次只改自动触发的部分

## 验证方式

1. 播放一首歌，确认**5秒后**（不是1.2秒，也不是提前25秒）出现讲解文字+语音，且讲解内容对应**当前正在播放**的这首歌
2. 手动快速切歌两三次（在5秒延迟内切换），确认不会出现"讲解了一首已经不在播的歌"的情况，也不会有声音重叠/堆叠
3. 确认当前歌曲播放到最后25秒时，**不再**提前出现下一首的讲解语音
4. `node --check` 不适用于 html，改为本地起服务后在浏览器里实际听一遍完整的"播放→等待→讲解出现"流程，用 `console.log` 或肉眼计时确认延迟确实是5秒左右
