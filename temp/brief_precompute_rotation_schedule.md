# Brief:按音乐强度预计算旋转方案(精确落点版)——新的独立候选,不碰Level1

## 背景

Level1(播放状态联动,固定转速)已经上线验证过。这次要做一个新的、更丰富的候选:转速/圈数跟歌曲的`rhythmic_motion`(0-1,代替BPM,Spotify的audio-features接口2024年底就停用拿不到真实BPM了)走,而且不管转几圈,最后一段必须精确卡在歌曲结束那一刻回到播放开始时的朝向。

**这是全新的、独立的候选功能,通过单独的调试参数区分,绝对不要修改或删除现有的Level1代码**(`_level1Motion`/`_updateLevel1Motion()`,`pwa/earth3d.js:22-77`)。

## 一、强度→总圈数

```js
const x = Math.max(0, Math.min(1, (rhythmicMotion - 0.05) / (0.95 - 0.05)))
const shaped = Math.pow(x, 1.6)
const totalLaps = 0.15 + shaped * (3.0 - 0.15)
```

## 二、精确落点的时间表计算

歌曲时长切三段:爬升期`Tru=12`秒、匀速期、减速期`Trd=15`秒(如果`Tru+Trd`超过歌曲总时长,按比例缩小这两个值,不要出现负数的匀速段时长)。

用smoothstep缓动做爬升/减速曲线(视觉效果比线性好,而且经过手算验证:只要曲线关于中点对称,走过的距离精确等于`½×峰值角速度×爬升时长`,不会破坏精确落点的保证):

```js
function smoothstepDist(u) { return u*u*u - 0.5*u*u*u*u }  // u ∈ [0,1]，返回值域[0, 0.5]
```

反推匀速段角速度:
```js
const totalDeg = totalLaps * 360
const cruiseSeconds = duration - Tru - Trd
const v = totalDeg / (duration - 0.5*Tru - 0.5*Trd)  // 度/秒
```

`angle(elapsedSeconds, schedule)`纯函数(不依赖上一帧状态,只依赖"歌曲播放了多久"这一个输入):

```js
function angle(t, sched) {
  const { v, Tru, Trd, duration, direction } = sched
  let dist
  if (t <= 0) {
    dist = 0
  } else if (t < Tru) {
    dist = v * Tru * smoothstepDist(t / Tru)
  } else if (t < duration - Trd) {
    dist = 0.5 * v * Tru + v * (t - Tru)
  } else if (t < duration) {
    const rampUpDist = 0.5 * v * Tru
    const cruiseDist = v * (duration - Trd - Tru)
    const remaining = duration - t
    const rdDoneFrac = 0.5 - smoothstepDist(remaining / Trd)
    dist = rampUpDist + cruiseDist + v * Trd * rdDoneFrac
  } else {
    dist = totalLaps * 360  // t >= duration，钳制在精确终值
  }
  return direction * dist  // direction: +1 顺时针（默认），-1 预留给以后的彩蛋歌单反转，这次不实现
}
```

这个函数在`t=duration`时算出来的值精确等于`totalLaps*360`(等价于回到出发朝向),因为这就是反推`v`时设定的目标值,不会有累积误差——这是纯函数,每次调用只看"过去了多久"，不看上一帧的状态。

跟现有的地球朝向平滑滚转(`earth.quaternion.slerp(target, 0.02)`)不冲突,不用改——这个时间表只负责算"目标朝向该是多少",最终画面呈现还是走现有的slerp。

## 三、后端改动(3处)

### 1. `core/state.js:400-405` `getTrackProfile()`
SELECT语句加`rhythmic_motion`(表里已经有这一列,只是查询漏了,不需要迁移):
```js
function getTrackProfile(trackKey) {
  if (!trackKey) return null
  return db.prepare(
    'SELECT track_key, energy, brightness, density, vocal_presence, emotional_weight, rhythmic_motion FROM track_profile WHERE track_key = ?'
  ).get(trackKey) || null
}
```
`getAllTrackProfiles()`(408-412行)同样的SELECT列表,顺手一起加上`rhythmic_motion`。

### 2. `core/spotify.js` `searchTrack()`
函数里有2处返回对象字面量(约827行、849行附近),都加上:
```js
duration_ms: best.track.duration_ms || null,
```

### 3. `server.js:744-796` `resolveQueue()`
Spotify匹配分支和NCM匹配分支,构建`song_info`之前,先查track_profile:
```js
const trackKey = `${normalizeSongKey(song.name)}::${normalizeArtistKey(song.artist)}`
const profile = state.getTrackProfile(trackKey)
const rhythmicMotion = (profile && typeof profile.rhythmic_motion === 'number')
  ? profile.rhythmic_motion
  : 0.344  // 全库均值兜底，查不到时不能是null/undefined
```
Spotify分支的`song_info`加上`rhythmic_motion: rhythmicMotion, duration_ms: match.duration_ms || null`；NCM分支加`rhythmic_motion: rhythmicMotion`(没有`duration_ms`,NCM没有Spotify匹配可以取时长)。

`normalizeSongKey`/`normalizeArtistKey`已经在`core/search-utils.js`里,`server.js`别处也在用同样的拼接方式(比如621行、1874行附近),直接复用,不要重新发明。

## 四、前端改动(新候选,不碰Level1)

新的模块级状态,跟`_level1Motion`并列,不要合并,不要复用它的变量名:

```js
// ── Precomputed Rotation Schedule ──
// gated by ?earthCandidate=precomputeschedule
let _precomputeMotion = (function _initPrecomputeMotion() {
  const m = { enabled: false, schedule: null, lastLonOffset: 0, scheduleCompletedAt: null }
  if (typeof window !== 'undefined') {
    m.enabled = new URLSearchParams(window.location.search).get('earthCandidate') === 'precomputeschedule'
  }
  return m
})()

function buildSchedule(trackKey, rhythmicMotion, durationSec) {
  const rm = typeof rhythmicMotion === 'number' ? rhythmicMotion : 0.344
  const x = Math.max(0, Math.min(1, (rm - 0.05) / (0.95 - 0.05)))
  const shaped = Math.pow(x, 1.6)
  const totalLaps = 0.15 + shaped * (3.0 - 0.15)
  let Tru = 12, Trd = 15
  if (Tru + Trd > durationSec) {
    const scale = durationSec / (Tru + Trd) * 0.8  // 留点余量给匀速段
    Tru *= scale; Trd *= scale
  }
  const totalDeg = totalLaps * 360
  const v = totalDeg / (durationSec - 0.5 * Tru - 0.5 * Trd)
  return {
    trackKey, startTimestamp: performance.now() / 1000,
    duration: durationSec, totalLaps, direction: 1,
    Tru, Trd, v,
  }
}

function smoothstepDist(u) { return u*u*u - 0.5*u*u*u*u }

function scheduleAngle(t, sched) {
  const { v, Tru, Trd, duration, direction, totalLaps } = sched
  let dist
  if (t <= 0) dist = 0
  else if (t < Tru) dist = v * Tru * smoothstepDist(t / Tru)
  else if (t < duration - Trd) dist = 0.5*v*Tru + v*(t - Tru)
  else if (t < duration) {
    const rampUpDist = 0.5*v*Tru
    const cruiseDist = v*(duration - Trd - Tru)
    const remaining = duration - t
    const rdDoneFrac = 0.5 - smoothstepDist(remaining / Trd)
    dist = rampUpDist + cruiseDist + v*Trd*rdDoneFrac
  } else {
    dist = totalLaps * 360
  }
  return direction * dist
}

function _updatePrecomputeMotion() {
  if (!_precomputeMotion.enabled) return
  const vs = window.__rodioVisualState || {}
  const track = vs.currentTrack || {}
  const trackKey = (track.name && track.artist)
    ? `${track.name.trim().toLowerCase()}::${track.artist.trim().toLowerCase()}`
    : null
  const HOLD_SECONDS = 2

  if (trackKey && (!_precomputeMotion.schedule || _precomputeMotion.schedule.trackKey !== trackKey)) {
    const durationSec = (track.duration_ms ? track.duration_ms / 1000 : null) || vs.duration || null
    if (durationSec && durationSec > 0) {
      _precomputeMotion.schedule = buildSchedule(trackKey, track.rhythmic_motion, durationSec)
      _precomputeMotion.scheduleCompletedAt = null
    }
  }

  const sched = _precomputeMotion.schedule
  if (!sched) return

  const elapsed = (performance.now() / 1000) - sched.startTimestamp

  if (elapsed >= sched.duration) {
    if (_precomputeMotion.scheduleCompletedAt === null) {
      _precomputeMotion.scheduleCompletedAt = performance.now() / 1000
    }
  } else {
    _precomputeMotion.lastLonOffset = scheduleAngle(elapsed, sched)
  }

  if (!window.__rodioVisualState) window.__rodioVisualState = {}
  window.__rodioVisualState._precomputeLonOffset = _precomputeMotion.lastLonOffset
}
// ── /Precomputed Rotation Schedule ──
```

调用点跟`_updateLevel1Motion()`挂在同一处(`pwa/earth3d.js:6114`附近渲染循环里),两个函数分别调用,不要合并成一个。

**注意`trackKey`判断"是否同一首歌"用的是name+artist拼接,不是`id`**——因为`pwa/index.html:1200`的`syncCurrentTrackFromSpotifyState()`每次Spotify播放状态变化(暂停/恢复/seek都算)都会用一个只有`{id, name, artist}`的裸对象覆盖`state.currentTrack`,这个函数产生的id和`resolveQueue`产生的id格式可能对不上,用name+artist判断更稳,能保证同一首歌暂停恢复的时候时间表不会被误判成"新歌"而重新计算。

`getTargetOrientation()`(`pwa/earth3d.js:5046`附近)现在只读`_level1LonOffset`,改成:
```js
function getTargetOrientation(targetDirOverride = null) {
  const vs = window.__rodioVisualState || {}
  let candidateOffset = 0
  if (_precomputeMotion.enabled) {
    candidateOffset = vs._precomputeLonOffset || 0
  } else if (_level1Motion.enabled) {
    candidateOffset = vs._level1LonOffset || 0
  }
  const lon = normalizeLon(
    (Number.isFinite(vs.lon) ? vs.lon : 121.4737) + candidateOffset
  )
  // ...其余不变
```
两个候选互斥(不叠加),因为数学模型完全不同,叠加会破坏精确落点的保证。正常情况下不会同时开两个调试参数,这只是防御性写法。

NCM路径(没有Spotify匹配的歌)播放前不知道时长,`_updatePrecomputeMotion`里`durationSec`算不出来就直接return,不强行用某个默认时长瞎算,等`<audio>`元素的`loadedmetadata`触发、`vs.duration`有值之后自然会在下一帧被捕捉到。

## 不要做的事

- 不要碰`_level1Motion`/`_updateLevel1Motion()`任何代码
- 不要实现"反方向的钟"这类彩蛋歌单的判断逻辑,`direction`这次固定为`1`
- 不要碰镜头角度/相机预设相关代码
- 不要改`resolveDjSelection`/`buildReadyPoolBatch`等真实选曲逻辑本体

## 验证方式(必须实测,不能只看代码逻辑)

1. 加`?earthCandidate=precomputeschedule`,先查一下当前要播的歌在DB里的`rhythmic_motion`值,自己算一下预期的totalLaps
2. 歌曲播放到快结束时截图,歌曲结束瞬间(或者结束后1-2秒内)再截一张,两张图肉眼确认地表朝向基本一致(不要求逐像素对齐)
3. 换一首`rhythmic_motion`明显更高或更低的歌,对比转动幅度有没有明显区别
4. 测Spotify路径下暂停/恢复/seek,确认这些操作不会让时间表重新计算(可以在console打印`window.__rodioVisualState._precomputeLonOffset`前后对比,或者在代码里临时加个log确认`buildSchedule`没有被重复调用)
5. 测NCM路径(找一首Spotify搜不到、走NCM降级的歌),确认没有报错、时间表在时长已知后才开始生效
6. 不加任何调试参数时,确认默认播放体验完全不受影响
