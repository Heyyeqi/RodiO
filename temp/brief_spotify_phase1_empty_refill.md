# Brief:修复 Spotify Phase 1 补货偶发返回空

## 根因(已定位,不是猜测)

`server.js:848-865` 的 `fillQueueFromSpotifyPlaylists` 循环里，强制刷新缓存的触发条件是：
```js
if (
  pulled.length === 0 &&
  lastPhase1Meta.cachedTrackCount === 0 &&
  !lastPhase1Meta.freshPlaylistFetchAttempted
) {
  console.log(`[spotify] Phase 1(${reason}) cache 为空，强制 fresh fetch playlist tracks`)
  pulled = await pullPlaylistItems(baseItems, { forceRefresh: true })
}
if (!pulled.length) break
```

`lastPhase1Meta.cachedTrackCount` 来自 `core/spotify.js:654` 的 `getPlaylistCacheTrackCount()`，这个函数统计的是**缓存里原始曲目总数**，跟有没有被去重/黑名单过滤掉完全无关（`core/spotify.js:783-796` 的过滤逻辑是在拿到缓存曲目之后才做的，不影响 `cachedTrackCount` 这个数字）。

问题就在这：如果用户歌单本身不大、或者最近播放记录/黑名单已经覆盖了缓存里的大部分曲目，`pullPlaylistItems` 完全可能返回 `pulled.length === 0`，但 `lastPhase1Meta.cachedTrackCount` 其实是个正数（缓存不是空的，只是全被过滤掉了）。这种情况下强制刷新的条件判断为 false，直接执行 `if (!pulled.length) break`，补货以空结果收场——即使实际去 Spotify 重新拉一次很可能会有新的/不同顺序的候选可用。

## 修复

把强制刷新的判断条件从：
```js
if (
  pulled.length === 0 &&
  lastPhase1Meta.cachedTrackCount === 0 &&
  !lastPhase1Meta.freshPlaylistFetchAttempted
) {
```
改成，去掉 `cachedTrackCount === 0` 这个条件，只要"这次没拉到东西、且还没试过强制刷新"就应该重新拉一次：
```js
if (
  pulled.length === 0 &&
  !lastPhase1Meta.freshPlaylistFetchAttempted
) {
```

其余逻辑不用动——外层 `while` 循环本身已经有 `attempts < 3` 的上限，`pullPlaylistItems(baseItems, { forceRefresh: true })` 内部的 `forceRefresh` 只是跳过一次性绕开 `USER_PLAYLIST_TRACKS_CACHE_MS` 的TTL检查（`core/spotify.js:715/728`），不会导致无限重试或者频繁打Spotify API——这个改动只是让"该重试的时候真的去重试"，不会增加额外的重试轮数上限。

## 不要改动的部分

- `getPlaylistCacheTrackCount()`、`getPlaylistQueueItems` 内部过滤逻辑本身都不用动
- 日志打印那两行（`console.log` 提示"cache 为空"这句文案，如果你想改成更准确的"补货为空"之类的措辞可以顺手改一下，但不强制）

## 验证方式

1. `node --check server.js` 通过
2. 在本地起服务，手动构造一个"歌单曲目已经被大部分播放/拉黑"的场景（比如把 `state.getRecentPlays(120)` 覆盖的曲目人为设置得接近整个歌单大小），确认这种情况下现在会触发强制刷新而不是直接返回空——可以加临时 console.log 观察 `lastPhase1Meta`/`pulled.length` 的实际值来确认分支走向，验证完记得去掉临时日志
3. 确认正常场景（歌单里还有大量未播放曲目）下行为完全不受影响，补货依然一次成功，不会多打无谓的强制刷新请求
