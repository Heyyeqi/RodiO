# 补充:两处遗漏的song_info构造点,没有rhythmic_motion

## 问题

实测发现,当前播放的"葉子 - 《薔薇之戀》原聲帶版"(阿桑)这首歌,DB里明明有`rhythmic_motion=0.25`(`track_key: 叶子蔷薇之恋原声带版::阿桑`),但`window.__rodioVisualState.currentTrack.rhythmic_motion`是`undefined`。查出来原因是:上次brief只改了`resolveQueue()`一处,但`song_info`对象实际上有**三个独立的构造点**,另外两处完全没覆盖:

1. **`server.js:527` `curatedTrackToQueueItem()`**——DeepSeek精选池路径用的,今天服务器启动预热时的曲目几乎全走这条("直接入队(DeepSeek选曲)"日志),这不是边缘情况
2. **`core/spotify.js:131` `normalizePlaylistTrackItem()`**——Spotify歌单里已有spotify_uri、跳过search直接入队的路径("直接入队(库)"日志)

这两处的`song_info`目前都只有`{id, name, artist}`,没有`rhythmic_motion`/`duration_ms`。

## 要做的事

### 1. `server.js:527` `curatedTrackToQueueItem(track)`

在函数内部,构造`song_info`之前,查一下track_profile(跟`resolveQueue()`里的写法保持一致):
```js
function curatedTrackToQueueItem(track) {
  const trackKey = `${normalizeSongKey(track.name)}::${normalizeArtistKey(track.artist)}`
  const profile = state.getTrackProfile(trackKey)
  const rhythmicMotion = (profile && typeof profile.rhythmic_motion === 'number')
    ? profile.rhythmic_motion
    : 0.344
  return {
    song_info: {
      id: track.id || null,
      name: track.name,
      artist: track.artist,
      rhythmic_motion: rhythmicMotion,
      duration_ms: track.duration_ms || null,  // 如果candidates列表里本来就带duration_ms就用,没有就null
    },
    ...
```
`normalizeSongKey`/`normalizeArtistKey`确认`server.js`里已经在用(`resolveQueue()`那次改动就用的这两个),直接复用,不用重新import。

### 2. `core/spotify.js:131` `normalizePlaylistTrackItem(item, playlist)`

这个文件已经`require('./state')`了(`core/spotify.js`开头),同样的查询逻辑可以直接加:
```js
function normalizePlaylistTrackItem(item, playlist) {
  const track = item?.track
  // ...原有的校验逻辑不变...
  
  const trackKey = `${normalizeSongKey(track.name)}::${normalizeArtistKey(artistName)}`
  const profile = state.getTrackProfile(trackKey)
  const rhythmicMotion = (profile && typeof profile.rhythmic_motion === 'number')
    ? profile.rhythmic_motion
    : 0.344
  
  return {
    song_info: {
      id: track.id || null,
      name: track.name,
      artist: artistName,
      rhythmic_motion: rhythmicMotion,
      duration_ms: track.duration_ms || null,  // Spotify歌单track对象本身就带这个字段
    },
    ...
```
`normalizeSongKey`/`normalizeArtistKey`如果这个文件里还没有import,从`./search-utils`加一下(`resolveQueue()`用的是同一个来源)。

## 验证方式(这次必须实测,不能只改完代码就说完成)

1. 本地起服务(不是走`resolveQueue`那条冷门路径,是正常启动预热/歌单补货这两条常见路径),加`?earthCandidate=precomputeschedule`
2. 挑一首启动时通过"直接入队(库)"或"直接入队(DeepSeek选曲)"日志入队的歌,查一下它在DB里的`rhythmic_motion`
3. 播放这首歌,console里执行`window.__rodioVisualState.currentTrack.rhythmic_motion`,确认不是undefined,数值跟DB里查到的一致
4. 再确认`window.__rodioVisualState._precomputeLonOffset`在播放过程中真的有变化(隔几秒钟执行一次,贴出至少3次不同时间点的值)
5. 把这几步的真实输出贴给我,不要只说"已验证"
