require('dotenv').config()

const express = require('express')
const http = require('http')
const WebSocket = require('ws')
const OpenAI = require('openai')
const os = require('os')
const path = require('path')
const fs = require('fs')

const router = require('./core/router')
const context = require('./core/context')
const claude = require('./core/claude')
const tts = require('./core/tts')
const state = require('./core/state')
const scheduler = require('./core/scheduler')
const { runShadowRecall } = require('./core/shadow-recall')
const { transitionCost } = require('./core/transition-cost')
const { logShadowRerank } = require('./core/candidate-rerank')
const { generateShadowMoodIntent } = require('./core/mood-intent')
const { getAstronomyContext } = require('./core/astronomy')
const spotify = require('./core/spotify')
const { createQueueManager } = require('./core/queue-manager')
const {
  artistMatchScore,
  buildArtistVariants,
  buildTitleVariants,
  makeSongSearchProfile,
  normalizeArtistKey,
  normalizeSongKey,
  stripTitleNoise,
  titleMatchScore,
} = require('./core/search-utils')

const explainClient = new OpenAI({
  apiKey: process.env.DEEPSEEK_API_KEY,
  baseURL: 'https://api.deepseek.com',
})
const explainAngles = [
  'B. 声音质感——用通感描述这首歌的物理触感或材质，不靠歌词，靠感官',
  'C. 反直觉——它和此刻看似不搭，但说清楚为什么反而是唯一正确的选择',
  'D. 一个具体的物件或画面——不靠时间天气，一个细节就够锚定整个情绪',
  'E. 隐秘共振——此刻和这首歌之间有一条别人不会注意到的线，说出这条线',
  'F. 艺人的某个特质——不编造事实，只说这个人的声音或创作方式里有什么独特的东西',
  'G. 此刻的反面——不描述此刻是什么，而是说这首歌能把人带去哪个完全不同的地方',
  'H. 一个问句——不给答案，只提出一个刚好在此刻值得想的问题',
  'I. 语气和节奏——不说内容，只说这首歌说话的方式，它是快还是慢，是确定还是犹豫',
  'J. 一个不相关的事物——找一个表面上和这首歌毫无关系的东西，但说清楚它们之间奇怪的相似',
  'K. 缺席的东西——这首歌里没有什么？它的留白是什么？说那个空的地方',
  'L. 听这首歌的人——不说歌本身，说什么样的人在什么状态下会需要这首歌',
  'M. 一个动词——找一个准确的动词描述这首歌在做什么，不是"表达"不是"讲述"，是更具体的',
  'N. 时间错位——这首歌属于哪个时间？为什么它今天出现在这里反而对？',
  'O. 身体感受——听这首歌时身体的哪个部位会先有反应？是喉咙、胸口、还是手指？',
  'P. 如果这首歌是一种天气——不是字面意义上的天气，是它制造的气候和压强',
  'Q. 一句话的故事——用一句话虚构一个和这首歌气质完全吻合的场景，不解释，直接说',
]
let recentExplainOpenings = []

const app = express()
const server = http.createServer(app)
const wss = new WebSocket.Server({ server, path: '/stream' })

process.on('unhandledRejection', error => {
  console.error('[claudio] 未处理的 Promise 拒绝:', error)
})

process.on('uncaughtException', error => {
  console.error('[claudio] 未捕获异常:', error)
})

const wsClients = []
let latestStationPayload = null
wss.on('connection', ws => {
  wsClients.push(ws)

  if (latestStationPayload) {
    ws.send(JSON.stringify(latestStationPayload))
  } else if (queueManager.size() > 0) {
    ws.send(JSON.stringify({ type: 'queue-refresh', queue: queueManager.getSnapshot() }))
  }

  ws.on('close', () => {
    const i = wsClients.indexOf(ws)
    if (i !== -1) wsClients.splice(i, 1)
  })
})
scheduler.setWsClients(wsClients)

// ── 内存播放队列 ──────────────────────────────
let currentNowPlaying = null
const DEFAULT_MIN_BATCH_SIZE = 8
const DEFAULT_MAX_BATCH_SIZE = 12
const READY_POOL_TARGET_SIZE = 30
const STARTUP_POOL_SIZE = 10
const READY_POOL_REFILL_THRESHOLD = 10
const LOW_WATER_MARK = READY_POOL_REFILL_THRESHOLD
const READY_POOL_ROUND_SIZE = 15
const READY_POOL_MAX_ROUNDS = 8
const READY_POOL_PARALLEL_ROUNDS = 2
const STARTUP_PREWARM_TIMEOUT_MS = 30 * 1000
const QUEUE_HEARTBEAT_INTERVAL = 4 * 60 * 1000
const HEARTBEAT_REPLENISH_COOLDOWN = 10 * 60 * 1000
const ncmSearchCache = new Map()
const SEARCH_CACHE_TTL_MS = 12 * 60 * 60 * 1000
const SEARCH_CACHE_MISS_TTL_MS = 30 * 60 * 1000
const NCM_ID_MAP_HIT_TTL_MS = 72 * 60 * 60 * 1000
const NCM_ID_MAP_PREF = 'ncm_id_map_v1'
const MAX_NCM_ID_MAP_SIZE = 400
const RECENT_RECOMMENDED_PREF = 'recent_recommended_keys_v1'
const MAX_RECENT_RECOMMENDED_KEYS = 60
const SPOTIFY_PHASE1_MIN_FILL = 12
const QWEN_ENHANCER_TIMEOUT_MS = 20000
const QWEN_CURATED_CANDIDATE_LIMIT = 50

function loadNcmIdMap() {
  try {
    const raw = state.getPref(NCM_ID_MAP_PREF)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

let ncmIdMap = loadNcmIdMap()
let recentRecommendedKeys = loadRecentRecommendedKeys()
let lastWeatherMain = null
let weatherPollTimer = null
let queueHeartbeatTimer = null
const WEATHER_POLL_INTERVAL = 5 * 60 * 1000 // 5分钟
let shouldAutoplayAfterRefill = false
let suppressQueueBroadcasts = false
let _lastHeartbeatReplenishAt = 0
const spotifyUriBlacklist = new Set()
let qwenEnhancerPromise = null

const queueManager = createQueueManager({
  targetSize: READY_POOL_TARGET_SIZE,
  refillThreshold: READY_POOL_REFILL_THRESHOLD,
  itemKey: queueKeyFromItem,
  onQueueChange(queue) {
    if (latestStationPayload) latestStationPayload = { ...latestStationPayload, queue }
    if (suppressQueueBroadcasts) return
    scheduler.broadcast({ type: 'queue-refresh', queue })
  },
  onRefillStart({ reason, needed, sizeBefore }) {
    console.log(`[queue] 开始补货(${reason})，缺口 ${needed}，当前 ${sizeBefore} 首`)
  },
  onRefillComplete({ reason, sizeBefore, sizeAfter, insertedCount }) {
    console.log(`[queue] 补货完成(${reason})，新增 ${insertedCount} 首，当前 ${sizeAfter} 首`)
    if (shouldAutoplayAfterRefill && sizeBefore === 0 && sizeAfter > 0) {
      shouldAutoplayAfterRefill = false
      const item = queueManager.pop('auto-resume')
      if (item) {
        currentNowPlaying = item.song_info || null
        state.addPlay({
          id: item.song_info?.id,
          name: item.song_info?.name,
          artist: item.song_info?.artist,
        })
        scheduler.broadcast({ type: 'now-playing', ...item, queue: queueManager.getSnapshot() })
      }
    }
  },
  onRefillError(error, { reason }) {
    console.error(`[queue] 补货失败(${reason}):`, error.message)
  },
})

function makeSongLookupKey(name, artist) {
  return `${normalizeNcmText(name)}::${normalizeNcmText(artist)}`
}

function isLikelyNcmSongId(songId) {
  const id = String(songId || '').trim()
  return /^\d{6,}$/.test(id)
}

function persistNcmIdMap() {
  const entries = Object.entries(ncmIdMap)
    .sort((a, b) => (b[1]?.updatedAt || 0) - (a[1]?.updatedAt || 0))
    .slice(0, MAX_NCM_ID_MAP_SIZE)
  ncmIdMap = Object.fromEntries(entries)
  state.setPref(NCM_ID_MAP_PREF, JSON.stringify(ncmIdMap))
}

function rememberSongIdMapping(name, artist, songId, status = 'hit') {
  const key = makeSongLookupKey(name, artist)
  ncmIdMap[key] = { id: songId || null, status, updatedAt: Date.now() }
  persistNcmIdMap()
}

function getRememberedSongId(name, artist) {
  const key = makeSongLookupKey(name, artist)
  const remembered = ncmIdMap[key]
  if (!remembered) return null
  if (remembered.status === 'hit' && !isLikelyNcmSongId(remembered.id)) {
    delete ncmIdMap[key]
    persistNcmIdMap()
    return null
  }
  if (remembered.status === 'miss' && Date.now() - remembered.updatedAt > SEARCH_CACHE_MISS_TTL_MS) {
    delete ncmIdMap[key]
    persistNcmIdMap()
    return null
  }
  if (remembered.status === 'hit' && Date.now() - remembered.updatedAt > NCM_ID_MAP_HIT_TTL_MS) {
    delete ncmIdMap[key]
    persistNcmIdMap()
    return null
  }
  return remembered
}

function getCachedSearchIds(cacheKey) {
  const cached = ncmSearchCache.get(cacheKey)
  if (!cached) return null
  if (Date.now() > cached.expiresAt) {
    ncmSearchCache.delete(cacheKey)
    return null
  }
  return cached.ids
}

function setCachedSearchIds(cacheKey, ids) {
  const isHit = Array.isArray(ids) && ids.length > 0
  ncmSearchCache.set(cacheKey, {
    ids: Array.isArray(ids) ? ids.slice(0, 5) : [],
    expiresAt: Date.now() + (isHit ? SEARCH_CACHE_TTL_MS : SEARCH_CACHE_MISS_TTL_MS),
  })
}

function queueKeyFromItem(item) {
  if (!item?.song_info) return ''
  return `${item.song_info.name}::${item.song_info.artist}`.toLowerCase()
}

function loadRecentRecommendedKeys() {
  try {
    const raw = state.getPref(RECENT_RECOMMENDED_PREF)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter(Boolean).map(item => String(item).toLowerCase()) : []
  } catch {
    return []
  }
}

function persistRecentRecommendedKeys() {
  const unique = []
  const seen = new Set()
  for (let i = recentRecommendedKeys.length - 1; i >= 0; i--) {
    const key = String(recentRecommendedKeys[i] || '').toLowerCase()
    if (!key || seen.has(key)) continue
    seen.add(key)
    unique.unshift(key)
    if (unique.length >= MAX_RECENT_RECOMMENDED_KEYS) break
  }
  recentRecommendedKeys = unique
  state.setPref(RECENT_RECOMMENDED_PREF, JSON.stringify(recentRecommendedKeys))
}

function rememberRecentRecommendedQueue(queue) {
  const keys = (Array.isArray(queue) ? queue : [])
    .map(queueKeyFromItem)
    .filter(Boolean)
  if (!keys.length) return
  recentRecommendedKeys = [...recentRecommendedKeys, ...keys]
  persistRecentRecommendedKeys()
}

function getRecentRecommendedKeySet() {
  return new Set(recentRecommendedKeys)
}

async function checkWeatherChange() {
  try {
    const coords = context.getStoredCoordinates()
    const weather = coords
      ? await context.fetchWeatherByCoords(coords.lat, coords.lon)
      : await context.fetchWeatherByCity()

    const currentMain = weather?.main || null
    if (!currentMain) return

    // 首次记录，不触发
    if (lastWeatherMain === null) {
      lastWeatherMain = currentMain
      return
    }

    // 天气没变，不触发
    if (lastWeatherMain === currentMain) return

    const prevMain = lastWeatherMain
    lastWeatherMain = currentMain

    console.log(`[claudio] 天气变化: ${prevMain} → ${currentMain}，触发重新选曲`)

    // 构造有质感的天气变化 prompt，让 AI 感知变化本身
    const weatherTransitionPrompts = {
      Rain: `天空开始下雨了，从${prevMain}变成了雨天。雨不只是一种天气，是一种心情的转场。根据此刻的城市、时间和季节，选几首最契合这场雨质感的歌——不要只是"雨歌单"，要感受这场雨是绵长的还是急促的，是春雨还是秋雨。`,
      Clear: `雨停了，天空放晴，从${prevMain}变成了晴天。阳光重新出现时，人的心情会有一种特别的轻盈感。选几首能捕捉这种"雨后"情绪的歌，不一定是欢快的，可以是安静的满足。`,
      Clouds: `天空开始转阴，云层聚拢，从${prevMain}变成了阴天。这种光线的改变会带来微妙的情绪转变，选几首符合阴天质感的歌。`,
      Snow: `开始下雪了，从${prevMain}变成了雪天。雪是一种特殊的安静，选几首能配得上雪落时那种空旷感的音乐。`,
      Thunderstorm: `雷雨来了，从${prevMain}变成了雷暴天气。这种天气有一种戏剧性，选几首有张力的歌。`,
      Drizzle: `开始飘起细雨，从${prevMain}变成了毛毛雨。选几首适合这种若即若离的雨天质感的歌。`,
      Mist: `雾气弥漫，从${prevMain}变成了雾天。选几首有朦胧感的音乐。`,
      Haze: `变得有些灰蒙蒙的，从${prevMain}变成了霾天。选几首不那么明亮、有些内敛的音乐。`,
    }

    const prompt = weatherTransitionPrompts[currentMain]
      || `天气从${prevMain}变成了${currentMain}，根据这个变化和当前时间地点，选几首最契合此刻的歌。`

    scheduler.broadcast({
      type: 'weather-change',
      from: prevMain,
      to: currentMain,
      weather,
    })

    const result = await buildDjResponse(prompt, {
      persistMessages: false,
      broadcast: true,
      appendQueue: false,
    })

    console.log(`[claudio] 天气变化选曲完成，生成 ${result.queue.length} 首`)
  } catch (e) {
    console.error('[claudio] 天气变化检测失败:', e.message)
  }
}

let buildDjResponseChain = Promise.resolve()
let stationBuildVersion = 0

function runSerializedBuildDjResponse(task) {
  const next = buildDjResponseChain.then(task, task)
  buildDjResponseChain = next.then(() => undefined, () => undefined)
  return next
}

function makeSongPayload(song) {
  return {
    id: song?.id || null,
    name: song?.name || '',
    artist: song?.artist || '',
  }
}

function broadcastPlaylistReady(payload, queue = queueManager.getSnapshot()) {
  latestStationPayload = {
    type: 'playlist-ready',
    say: payload.say || null,
    say_audio: payload.say_audio || null,
    queue,
    reason: payload.reason || '',
    segue: payload.segue || '',
  }
  scheduler.broadcast(latestStationPayload)
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function dedupeQueueItems(items) {
  const seen = new Set()
  return items.filter(item => {
    const key = queueKeyFromItem(item)
    if (!key || seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function shuffleArray(items) {
  const copy = Array.isArray(items) ? items.slice() : []
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

function markBatchEdges(items) {
  return items.map((item, index) => ({
    ...item,
    queue_meta: {
      ...(item.queue_meta || {}),
      batch_role:
        index === 0 ? 'first'
        : index === items.length - 1 ? 'last'
        : null,
    },
  }))
}

function isBlacklistedSpotifyUri(uri) {
  return !!uri && spotifyUriBlacklist.has(uri)
}

function blacklistSpotifyUri(uri, reason = '') {
  if (!uri) return false
  const existed = spotifyUriBlacklist.has(uri)
  spotifyUriBlacklist.add(uri)
  queueManager.remove(item => item?.spotify_uri === uri, 'spotify-blacklist-remove')
  if (!existed) {
    console.warn(`[spotify] 加入黑名单 ${uri}${reason ? ` (${reason})` : ''}`)
  }
  return !existed
}

function filterQueueCandidates(items, currentQueue, recentPlays, recentRecommended = new Set()) {
  const recentKeys = new Set(recentPlays.map(p => `${p.song_name}::${p.artist}`.toLowerCase()))
  const currentQueueKeys = new Set((currentQueue || []).map(queueKeyFromItem).filter(Boolean))

  return dedupeQueueItems(items.filter(item => {
    if (item?.spotify_uri && isBlacklistedSpotifyUri(item.spotify_uri)) {
      console.log(`[queue] 过滤黑名单 Spotify URI: ${item.spotify_uri}`)
      return false
    }
    const key = `${item.song_info.name}::${item.song_info.artist}`.toLowerCase()
    if (recentKeys.has(key)) {
      console.log(`[queue] 过滤重复: ${item.song_info.name} / ${item.song_info.artist}`)
      return false
    }
    if (currentQueueKeys.has(key)) {
      console.log(`[queue] 过滤队列已有: ${item.song_info.name} / ${item.song_info.artist}`)
      return false
    }
    if (recentRecommended.has(key)) {
      console.log(`[queue] 过滤近期推荐: ${item.song_info.name} / ${item.song_info.artist}`)
      return false
    }
    return true
  }))
}

function getLanUrls(port) {
  const networks = os.networkInterfaces()
  const urls = []

  for (const entries of Object.values(networks)) {
    for (const entry of entries || []) {
      if (entry.family === 'IPv4' && !entry.internal) {
        urls.push(`http://${entry.address}:${port}`)
      }
    }
  }

  return [...new Set(urls)]
}

function pickExplainAngle() {
  const index = Math.floor(Math.random() * explainAngles.length)
  return explainAngles[index]
}

function extractExplainOpening(text) {
  const trimmed = String(text || '').trim()
  if (!trimmed) return ''
  const firstChunk = trimmed.split(/[，。！？；,.!?;]/)[0].trim()
  return firstChunk.slice(0, 18)
}

function rememberExplainOpening(text) {
  const opening = extractExplainOpening(text)
  if (!opening) return
  recentExplainOpenings.push(opening)
  recentExplainOpenings = recentExplainOpenings.slice(-2)
}

function extractEmotionFromInput(userText) {
  const triggers = [
    { pattern: /烟花|firework/i, mood: '华丽短暂', suggestion: '陈绮贞《华丽的冒险》风格' },
    { pattern: /害怕|恐惧|黑暗|一个人.*路/i, mood: '需要陪伴', suggestion: '热闹有人声、节奏感强' },
    { pattern: /散步|漫步|走走/i, mood: '轻盈流动', suggestion: '方大同《春风吹》风格，轻盈律动' },
    { pattern: /下雨|雨声/i, mood: '雨天慵懒', suggestion: '慢节奏、有质感的编曲' },
    { pattern: /想家|思念|好久不见/i, mood: '思念', suggestion: '温柔、有故事感' },
    { pattern: /失眠|睡不着/i, mood: '深夜清醒', suggestion: '极简、呼吸感强' },
    { pattern: /开心|高兴|好消息/i, mood: '愉悦', suggestion: '明快、有光泽感的编曲' },
    { pattern: /难过|伤心|哭/i, mood: '需要共鸣', suggestion: '贴近情绪而非刻意治愈' },
    { pattern: /累|疲惫|下班/i, mood: '身心疲惫', suggestion: '慢下来、有托住感的音乐' },
    { pattern: /喝酒|小酌|一杯/i, mood: '微醺', suggestion: '爵士感、慵懒、带点诗意' },
  ]

  for (const trigger of triggers) {
    if (trigger.pattern.test(userText)) return { mood: trigger.mood, suggestion: trigger.suggestion }
  }
  return null
}

// ── NCM 工具 ─────────────────────────────────
const COOKIE_PATH = path.join(__dirname, 'user/ncm-cookie.json')

function getNcmCookie() {
  if (process.env.NCM_COOKIE) return process.env.NCM_COOKIE
  try {
    return JSON.parse(fs.readFileSync(COOKIE_PATH, 'utf8')).raw || ''
  } catch { return '' }
}

async function ncmFetch(url) {
  const cookie = getNcmCookie()
  // NeteaseCloudMusicApi 要求 cookie 以查询参数传入，不能用请求头
  const finalUrl = cookie
    ? url + (url.includes('?') ? '&' : '?') + 'cookie=' + encodeURIComponent(cookie)
    : url
  const res = await fetch(finalUrl)
  return res.json()
}

function normalizeNcmText(text) {
  return normalizeSongKey(text)
}

function isValidPeriod(period) {
  return ['morning', 'day', 'night'].includes(period)
}

function makeCuratedTrackKey(name, artist) {
  return `${normalizeNcmText(name)}::${normalizeNcmText(artist)}`
}

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
      duration_ms: track.duration_ms || null,
    },
    requested_song_info: {
      id: track.id || null,
      name: track.name,
      artist: track.artist,
    },
    spotify_uri: track.uri,
    spotify_track: {
      id: track.id || null,
      uri: track.uri,
      name: track.name,
      artists: String(track.artist || '').split('; ').filter(Boolean),
      album: track.album || null,
    },
    play_url: null,
    source: 'spotify',
    _directFromLibrary: true,
  }
}

function makeCuratedPoolPrompt(reason, needed, candidates) {
  const candidateLines = candidates
    .map(track => `${track.name} / ${track.artist}`)
    .join('\n')

  return [
    makeReadyPoolPrompt(reason, needed),
    '',
    '【硬性限制】你只能从下面这份候选列表中选歌，不能推荐列表以外的任何歌曲。',
    '返回的 play 数组里，name 和 artist 必须与候选列表完全一致；如果不确定，就不要写。',
    `需要选择约 ${Math.min(READY_POOL_ROUND_SIZE, candidates.length)} 首。`,
    '',
    '【候选列表】',
    candidateLines,
  ].join('\n')
}

function normalizeSongCore(text) {
  return stripTitleNoise(text)
}

function scoreNcmCandidate(song, requestedSong) {
  const candidateArtists = (song?.artists || []).map(a => a.name).filter(Boolean)
  const titleScore = titleMatchScore(buildTitleVariants(requestedSong), song?.name)
  const artistScore = artistMatchScore(buildArtistVariants(requestedSong), candidateArtists)

  let score = 0
  score += titleScore
  score += Math.round(artistScore * 0.8)

  if (song?.alia?.length) {
    const aliasHit = song.alia.some(alias => {
      const normalizedAlias = normalizeNcmText(alias)
      return buildTitleVariants(requestedSong).some(title => normalizeSongKey(title) === normalizedAlias)
    })
    if (aliasHit) score += 16
  }

  const coverKeywords = ['翻唱', 'cover', '致敬', '钢琴版', '吉他版', '纯音乐版', 'piano', 'acoustic', 'instrumental', 'tribute']
  const nameLower = String(song?.name || '').toLowerCase()
  const hasCoverKeyword = coverKeywords.some(kw => nameLower.includes(kw))
  if (hasCoverKeyword && artistScore < 68) score -= 40

  return score
}

function buildNcmQueries(song) {
  const titles = buildTitleVariants(song)
  const artists = buildArtistVariants(song)
  const queries = []

  for (const title of titles.slice(0, 6)) {
    queries.push(title)
  }

  for (const title of titles.slice(0, 4)) {
    for (const artist of artists.slice(0, 3)) {
      queries.push(`${title} ${artist}`.trim())
      if (queries.length >= 12) return queries
    }
  }

  return queries
}

async function ncmSearch(songOrName, artist) {
  const requestedSong = makeSongSearchProfile(songOrName, artist)
  const base = process.env.NCM_API_BASE || 'http://localhost:3000'
  const cacheKey = `${normalizeSongKey(requestedSong.name)}::${normalizeArtistKey(requestedSong.artist)}`
  const cached = getCachedSearchIds(cacheKey)
  if (cached) {
    console.log(`[ncm] 命中搜索缓存 "${requestedSong.name} / ${requestedSong.artist}" -> ${cached.join(', ') || 'MISS'}`)
    return cached
  }

  const seenIds = new Set()
  const candidates = []

  for (const query of buildNcmQueries(requestedSong)) {
    const q = encodeURIComponent(query)
    const data = await ncmFetch(`${base}/search?keywords=${q}&limit=15`)
    const songs = data?.result?.songs || []
    for (const song of songs) {
      const id = String(song.id)
      if (seenIds.has(id)) continue
      seenIds.add(id)
      const score = scoreNcmCandidate(song, requestedSong)
      if (score < 72) continue
      candidates.push({ id, score, song })
    }
    if (candidates.length >= 5) break
  }

  const coverKws = ['翻唱', 'cover', '钢琴版', '吉他版', '纯音乐', 'piano', 'acoustic', 'instrumental', 'tribute']
  candidates.forEach(c => {
    const n = String(c.song?.name || '').toLowerCase()
    if (coverKws.some(kw => n.includes(kw))) {
      c.score -= 30
    }
  })

  candidates.sort((a, b) => b.score - a.score)

  if (!candidates.length) {
    console.log(`[ncm] 搜索 "${requestedSong.name} / ${requestedSong.artist}" 无可靠结果，跳过`)
    setCachedSearchIds(cacheKey, [])
    return []
  }

  const ids = candidates.slice(0, 5).map(item => item.id)
  setCachedSearchIds(cacheKey, ids)
  return ids
}

async function checkArtistViaDetail(candidateId, requestedSong, base) {
  try {
    const data = await ncmFetch(`${base}/song/detail?ids=${candidateId}`)
    const song = data?.songs?.[0]
    if (!song) return true
    const actualArtists = (song.ar || []).map(a => a.name).filter(Boolean)
    const artistScore = artistMatchScore(buildArtistVariants(requestedSong), actualArtists)
    const titleScore = titleMatchScore(buildTitleVariants(requestedSong), song.name)
    if (titleScore < 72 || artistScore < 68) {
      console.log(`[ncm] 艺人不符 id=${candidateId}: 期望 [${buildArtistVariants(requestedSong).join(' | ')}] 实际 [${actualArtists}]`)
      return false
    }
    return true
  } catch { return true }
}

async function ncmGetUrl(songOrId, name, artist) {
  const requestedSong = makeSongSearchProfile(
    songOrId && typeof songOrId === 'object'
      ? songOrId
      : { id: songOrId, name, artist }
  )
  const base = process.env.NCM_API_BASE || 'http://localhost:3000'
  const tried = new Set()
  const candidateIds = []
  const remembered = getRememberedSongId(requestedSong.name, requestedSong.artist)

  if (isLikelyNcmSongId(remembered?.id)) candidateIds.push(String(remembered.id))
  if (isLikelyNcmSongId(requestedSong.id) && String(requestedSong.id) !== '0') candidateIds.push(String(requestedSong.id))

  for (const candidateId of candidateIds) {
    if (!candidateId || tried.has(candidateId)) continue
    tried.add(candidateId)

    const data = await ncmFetch(`${base}/song/url/v1?id=${candidateId}&level=standard`)
    const item = data?.data?.[0]
    if (item?.url && item.code === 200) {
      if (item.freeTrialInfo) {
        console.log(`[ncm] id=${candidateId} 为试听片段，跳过`)
        continue
      }
      if (!(await checkArtistViaDetail(candidateId, requestedSong, base))) continue
      rememberSongIdMapping(requestedSong.name, requestedSong.artist, candidateId, 'hit')
      if (candidateId !== String(requestedSong.id)) {
        console.log(`[ncm] 搜索命中 "${requestedSong.name} / ${requestedSong.artist}" -> ${candidateId}`)
      }
      return { url: item.url, id: candidateId }
    }
  }

  if (candidateIds.length > 0) {
    console.log(`[ncm] id ${candidateIds[0]} 无效，搜索 "${requestedSong.name} ${requestedSong.artist}"`)
  }
  const searchedIds = await ncmSearch(requestedSong)
  for (const candidateId of searchedIds) {
    if (!candidateId || tried.has(candidateId)) continue
    tried.add(candidateId)

    const data = await ncmFetch(`${base}/song/url/v1?id=${candidateId}&level=standard`)
    const item = data?.data?.[0]
    if (item?.url && item.code === 200) {
      if (item.freeTrialInfo) {
        console.log(`[ncm] id=${candidateId} 为试听片段，跳过`)
        continue
      }
      if (!(await checkArtistViaDetail(candidateId, requestedSong, base))) continue
      rememberSongIdMapping(requestedSong.name, requestedSong.artist, candidateId, 'hit')
      console.log(`[ncm] 搜索命中 "${requestedSong.name} / ${requestedSong.artist}" -> ${candidateId}`)
      return { url: item.url, id: candidateId }
    }
  }

  rememberSongIdMapping(requestedSong.name, requestedSong.artist, null, 'miss')
  return { url: null, id: null }
}

// 顺序解析一批歌曲，返回有直链的条目
async function resolveQueue(songs) {
  const useSpotify = spotify.hasUserToken()
  const spotifyQueue = []

  for (let index = 0; index < songs.length; index++) {
    const song = songs[index]
    try {
      // ── 查询 track_profile 获取 rhythmic_motion（两队共用的歌曲级运动强度）──
      const trackKey = `${normalizeSongKey(song.name)}::${normalizeArtistKey(song.artist)}`
      const profile = state.getTrackProfile(trackKey)
      const rhythmicMotion = (profile && typeof profile.rhythmic_motion === 'number')
        ? profile.rhythmic_motion
        : 0.344  // 全库均值兜底
      // ── /track_profile ──

      if (useSpotify) {
        let match = null
        try {
          if (index > 0) await delay(200)
          match = await spotify.searchTrack(song)
        } catch (e) {
          console.error(`[spotify] 搜索失败 "${song.name} / ${song.artist}"，回退 NCM:`, e.message)
        }
        if (match?.uri) {
          if (isBlacklistedSpotifyUri(match.uri)) {
            console.log(`[spotify] 命中黑名单 "${song.name} / ${song.artist}" -> ${match.uri}，跳过`)
            continue
          }
          const actualArtists = Array.isArray(match.artists) ? match.artists.filter(Boolean).join('; ') : song.artist
          console.log(`[spotify] 命中 "${song.name} / ${song.artist}" -> ${match.uri}`)
          spotifyQueue[index] = {
            song_info: {
              ...song,
              id: match.id || song.id || null,
              name: match.name || song.name,
              artist: actualArtists || song.artist,
              rhythmic_motion: rhythmicMotion,
              duration_ms: match.duration_ms || null,
            },
            requested_song_info: { ...song },
            spotify_uri: match.uri,
            spotify_track: match,
            play_url: null,
            source: 'spotify',
          }
          continue
        }
        console.log(`[spotify] 未命中 "${song.name} / ${song.artist}"，回退 NCM`)
      }
      const { url, id: realId } = await ncmGetUrl(song)
      if (!url) continue
      spotifyQueue[index] = {
        song_info: { ...song, id: realId || song.id, rhythmic_motion: rhythmicMotion },
        requested_song_info: { ...song },
        play_url: url,
        source: 'ncm',
      }
    } catch (e) {
      console.error(`[queue] 解析 "${song.name}" 失败:`, e.message)
    }
  }
  return spotifyQueue.filter(Boolean)
}

async function fillQueueFromSpotifyPlaylists(
  reason,
  currentQueue = queueManager.getSnapshot(),
  needed = READY_POOL_TARGET_SIZE,
  period = null
) {
  if (!spotify.hasUserToken()) return []

  const recentPlays = state.getRecentPlays(120)
  const recentRecommended = getRecentRecommendedKeySet()
  const targetCount = Math.max(SPOTIFY_PHASE1_MIN_FILL, Number(needed) || 0)
  const collected = []
  let attempts = 0
  let lastPhase1Meta = {
    cachedTrackCount: 0,
    blacklistSkipped: 0,
    freshPlaylistFetchAttempted: false,
  }

  async function pullPlaylistItems(baseItems, options = {}) {
    const blacklistedUris = [...spotifyUriBlacklist]
    const excludeUris = [
      ...blacklistedUris,
      ...baseItems.map(item => item?.spotify_uri).filter(Boolean),
    ]
    const excludeKeys = baseItems.map(queueKeyFromItem).filter(Boolean)
    const { items, meta } = await spotify.getPlaylistQueueItems({
      limit: Math.max(targetCount - collected.length, READY_POOL_ROUND_SIZE),
      includeMeta: true,
      blacklistedUris,
      excludeUris,
      excludeKeys,
      period,
      ...options,
    })
    if (meta) lastPhase1Meta = meta
    return items.map(item => {
      // 如果已有有效的 spotify_uri，直接使用，跳过 search
      if (item.spotify_uri && item.spotify_uri.startsWith('spotify:track:')) {
        console.log(`[spotify] 直接入队(库): ${item.song_info?.name} / ${item.song_info?.artist}`)
        return {
          ...item,
          play_url: null,
          _directFromLibrary: true,
        }
      }
      // 否则走原有的 search 路径
      return item
    })
  }

  while (collected.length < targetCount && attempts < 3) {
    attempts += 1
    const baseItems = [...(currentQueue || []), ...collected]
    let pulled = await pullPlaylistItems(baseItems)
    if (
      pulled.length === 0 &&
      !lastPhase1Meta.freshPlaylistFetchAttempted
    ) {
      console.log(`[spotify] Phase 1(${reason}) 补货为空，强制 fresh fetch playlist tracks`)
      pulled = await pullPlaylistItems(baseItems, { forceRefresh: true })
    }
    if (!pulled.length) break

    const filtered = filterQueueCandidates(pulled, [...(currentQueue || []), ...collected], recentPlays, recentRecommended)
    if (!filtered.length) break
    collected.push(...filtered)
  }

  if (collected.length > 0) {
    console.log(`[spotify] Phase 1(${reason}) 从用户歌单补入 ${collected.length} 首`)
  } else {
    console.log(
      `[spotify] Phase 1(${reason}) 未补入新歌: cache_tracks=${lastPhase1Meta.cachedTrackCount}, blacklist_filtered=${lastPhase1Meta.blacklistSkipped}, fresh_fetch_attempted=${lastPhase1Meta.freshPlaylistFetchAttempted}`
    )
  }
  return collected
}

function withTimeout(promise, timeoutMs, label) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error(`${label} timeout after ${timeoutMs}ms`)), timeoutMs)),
  ])
}

function triggerQwenEnhancer(reason = 'background', period = null) {
  if (qwenEnhancerPromise) return qwenEnhancerPromise

  const baseQueue = queueManager.getSnapshot()
  if (!baseQueue.length) return Promise.resolve([])

  qwenEnhancerPromise = (async () => {
    try {
      const items = await withTimeout(
        buildReadyPoolBatch('', {
          currentQueue: baseQueue,
          buildLabel: `enhancer:${reason}`,
          period,
        }),
        QWEN_ENHANCER_TIMEOUT_MS,
        `enhancer:${reason}`
      )
      if (!Array.isArray(items) || items.length === 0) return []

      const filtered = filterQueueCandidates(
        items,
        queueManager.getSnapshot(),
        state.getRecentPlays(120),
        getRecentRecommendedKeySet()
      )
      if (!filtered.length) return []

      const prepended = queueManager.prepend(filtered, `qwen-enhancer:${reason}`)
      const actuallyPrepended = prepended.slice(0, filtered.length)
      rememberRecentRecommendedQueue(filtered)
      console.log(`[queue] Phase 2(${reason}) 前插 ${filtered.length} 首 DeepSeek 选曲`)
      return actuallyPrepended
    } catch (error) {
      console.warn(`[queue] Phase 2(${reason}) 跳过: ${error.message}`)
      return []
    } finally {
      qwenEnhancerPromise = null
    }
  })()

  return qwenEnhancerPromise
}

async function resolveDjSelection(input, options = {}) {
  const {
    currentQueue = queueManager.getSnapshot(),
    includeSpeech = true,
    emotionSignal = null,
    minQueueSize = DEFAULT_MIN_BATCH_SIZE,
    maxQueueSize = DEFAULT_MAX_BATCH_SIZE,
  } = options

  const intent = router.route(input)
  if (intent === 'system') {
    return { say: null, say_audio: null, queue: [], reason: '', segue: '', intent }
  }

  const ctx = await context.buildContext(input, { currentQueue, emotionSignal })
  const result = await claude.askClaude(ctx)

  let queue = []
  const recentPlays = state.getRecentPlays(120)
  const recentRecommended = getRecentRecommendedKeySet()
  const useSpotify = spotify.hasUserToken()

  if (result.play && result.play.length > 0) {
    const rawResolved = await resolveQueue(result.play)
    queue = filterQueueCandidates(rawResolved, currentQueue, recentPlays, recentRecommended)
    // Fallback when recent recommendations filter removes every candidate.
    if (queue.length === 0 && rawResolved.length > 0) {
      console.log('[queue] 近期推荐全部命中，降级忽略 recentRecommended 过滤')
      queue = filterQueueCandidates(rawResolved, currentQueue, recentPlays, new Set())
    }

    const refillAttempts = useSpotify ? 5 : 3
    for (let attempt = 0; queue.length < minQueueSize && attempt < refillAttempts; attempt++) {
      const refillPrompt = useSpotify
        ? `继续补足队列，还需要 ${minQueueSize - queue.length} 首。只要 Spotify 可直接播放、歌名和艺人都严格匹配的歌，避开近期已播、当前队列里已有的歌，以及最近已经推荐过的歌。`
        : `继续补足队列，还需要 ${minQueueSize - queue.length} 首，避开近期已播、当前队列里已有的歌，以及最近已经推荐过的歌`
      const refillCtx = await context.buildContext(refillPrompt, {
        currentQueue: [...(currentQueue || []), ...queue],
      })
      const refillResult = await claude.askClaude(refillCtx)
      const refillQueue = await resolveQueue(refillResult.play || [])
      const mergedQueue = [...queue, ...refillQueue]
      queue = filterQueueCandidates(mergedQueue, currentQueue, recentPlays, recentRecommended)
      if (queue.length === 0 && mergedQueue.length > 0) {
        console.log('[queue] refill 近期推荐全部命中，降级忽略 recentRecommended 过滤')
        queue = filterQueueCandidates(mergedQueue, currentQueue, recentPlays, new Set())
      }
    }

    queue = queue.slice(0, maxQueueSize)
    queue = markBatchEdges(queue)
  }

  const say_audio = includeSpeech && result.say
    ? await tts.synthesize(result.say).catch(e => {
        console.error('[tts]', e.message)
        return null
      })
    : null

  return {
    say: includeSpeech ? result.say : null,
    say_audio,
    queue,
    replace_pool: !!result.replace_pool,
    reason: result.reason,
    segue: result.segue,
    intent,
  }
}

async function buildDjResponseCore(input, options = {}) {
  const {
    persistMessages = true,
    broadcast = false,
    currentQueue = queueManager.getSnapshot(),
    appendQueue = false,
    includeSpeech = true,
    emotionSignal = null,
    skipIfOutdated = false,
    buildLabel = 'build',
  } = options
  const buildVersionAtStart = stationBuildVersion

  const payload = await resolveDjSelection(input, {
    currentQueue,
    includeSpeech,
    emotionSignal,
  })

  if (skipIfOutdated && stationBuildVersion !== buildVersionAtStart) {
    console.log(`[claudio] ${buildLabel} 结果已过期，跳过写入`)
    return {
      ...payload,
      skippedApply: true,
    }
  }

  stationBuildVersion += 1
  const nextQueue = appendQueue
    ? dedupeQueueItems([...(currentQueue || []), ...(payload.queue || [])])
    : [...(payload.queue || [])]
  queueManager.replace(nextQueue, appendQueue ? 'append-build' : 'replace-build')

  if (payload.queue.length > 0) {
    scheduler.incrementCount()
  }

  if (payload.queue.length > 0) {
    rememberRecentRecommendedQueue(payload.queue)
  }

  if (persistMessages) {
    state.addMessage('user', input)
    state.addMessage('assistant', JSON.stringify(payload))
  }

  if (broadcast) {
    broadcastPlaylistReady(payload, queueManager.getSnapshot())

    if (payload.queue.length > 0 && !currentNowPlaying) {
      scheduler.broadcast({ type: 'now-playing', ...payload.queue[0], queue: queueManager.getSnapshot() })
    }
  }

  if (includeSpeech && queueManager.size() > 0 && queueManager.size() < LOW_WATER_MARK) {
    replenishQueueSilently('post-build').catch(() => {})
  }

  return payload
}

async function buildDjResponse(input, options = {}) {
  const task = () => buildDjResponseCore(input, options)
  if (options.serialize === false) return task()
  return runSerializedBuildDjResponse(task)
}

async function replenishQueueSilently(trigger = 'auto', options = {}) {
  try {
    const beforeSize = queueManager.size()
    await queueManager.ensureFilled(trigger, {
      meta: {
        period: options.period || null,
      },
    })
    if (spotify.hasUserToken() && queueManager.size() > beforeSize) {
      triggerQwenEnhancer(trigger, options.period || null).catch(() => {})
    }
  } catch (e) {
    console.error(`[queue] 静默补货失败(${trigger}):`, e.message)
  }
}

async function buildReadyPoolBatch(input, options = {}) {
  const currentQueue = Array.isArray(options.currentQueue) ? options.currentQueue.slice() : queueManager.getSnapshot()
  const period = isValidPeriod(options.period) ? options.period : null
  const curatedPool = shuffleArray(spotify.getCuratedPool(period))
  if (!curatedPool.length) {
    console.warn(`[queue] Phase 2(${options.buildLabel || 'batch'}) 跳过: curated pool 为空`)
    return []
  }

  const candidates = curatedPool.slice(0, QWEN_CURATED_CANDIDATE_LIMIT)
  const prompt = makeCuratedPoolPrompt(options.buildLabel || 'phase2', READY_POOL_ROUND_SIZE, candidates)
  const ctx = await context.buildContext(prompt, { currentQueue })
  const result = await claude.askClaude(ctx)

  const candidateByKey = new Map(candidates.map(track => [makeCuratedTrackKey(track.name, track.artist), track]))
  const selected = []
  const selectedKeys = new Set()

  for (const song of Array.isArray(result.play) ? result.play : []) {
    const key = makeCuratedTrackKey(song?.name || '', song?.artist || '')
    const match = candidateByKey.get(key)
    if (!match || selectedKeys.has(key)) continue
    selectedKeys.add(key)
    console.log(`[spotify] 直接入队(DeepSeek选曲): ${match.name} / ${match.artist}`)
    selected.push(curatedTrackToQueueItem(match))
    if (selected.length >= READY_POOL_ROUND_SIZE) break
  }

  if (selected.length < READY_POOL_ROUND_SIZE) {
    for (const track of candidates) {
      const key = makeCuratedTrackKey(track.name, track.artist)
      if (selectedKeys.has(key)) continue
      selectedKeys.add(key)
      selected.push(curatedTrackToQueueItem(track))
      if (selected.length >= READY_POOL_ROUND_SIZE) break
    }
  }

  return selected
}

function makeReadyPoolPrompt(reason, needed) {
  if (reason === 'startup-prewarm' || reason === 'bootstrap') {
    return `按当前时间、天气和用户整体品味推荐 ${READY_POOL_ROUND_SIZE} 首可直接播放的歌，作为电台启动预热池。必须避开近期已播和当前池里已有的歌。`
  }
  return `继续补充播放池，推荐 ${READY_POOL_ROUND_SIZE} 首可直接播放的歌。当前还缺约 ${needed} 首，请避开当前池里已有的歌和最近 50 首播放记录。`
}

async function buildReadyPoolMultiRound(reason, options = {}) {
  const baseQueue = Array.isArray(options.baseQueue) ? options.baseQueue.slice() : queueManager.getSnapshot()
  const targetSize = options.targetSize || READY_POOL_TARGET_SIZE
  const maxRounds = options.maxRounds || READY_POOL_MAX_ROUNDS
  const parallelRounds = options.parallelRounds || READY_POOL_PARALLEL_ROUNDS
  const period = isValidPeriod(options.period) ? options.period : null
  const deadlineAt = options.maxDurationMs ? Date.now() + options.maxDurationMs : 0
  const recentPlays = state.getRecentPlays(50)
  const recentPlayQueueItems = recentPlays.map(play => ({
    song_info: {
      id: play.song_id || play.id || null,
      name: play.song_name || play.name || '',
      artist: play.artist || '',
    },
  }))
  const collected = []
  let roundsUsed = 0

  while (baseQueue.length + collected.length < targetSize && roundsUsed < maxRounds) {
    if (deadlineAt && Date.now() >= deadlineAt) break
    const remainingRounds = maxRounds - roundsUsed
    const deficit = targetSize - (baseQueue.length + collected.length)
    const waveCount = Math.min(
      parallelRounds,
      remainingRounds,
      Math.max(1, Math.ceil(deficit / READY_POOL_ROUND_SIZE))
    )
    const waveCurrentQueue = dedupeQueueItems([...baseQueue, ...collected, ...recentPlayQueueItems])
    const waveTasks = Array.from({ length: waveCount }, (_, index) =>
      buildReadyPoolBatch('', {
        currentQueue: waveCurrentQueue,
        buildLabel: `refill:${reason}:round-${roundsUsed + index + 1}`,
        period,
      }).catch(error => {
        console.error(`[queue] 预热轮次失败(${reason}#${roundsUsed + index + 1}):`, error.message)
        return []
      })
    )
    const waveResults = await Promise.all(waveTasks)
    roundsUsed += waveCount

    let insertedThisWave = 0
    for (const items of waveResults) {
      const deduped = dedupeQueueItems(items, [...baseQueue, ...collected])
      if (!deduped.length) continue
      collected.push(...deduped)
      insertedThisWave += deduped.length
      if (baseQueue.length + collected.length >= targetSize) break
    }

    if (insertedThisWave === 0) break
  }

  return collected.slice(0, Math.max(0, targetSize - baseQueue.length))
}

queueManager.setRefillHandler(async ({ reason, needed, currentQueue, force, meta }) => {
  const targetSize = force
    ? READY_POOL_TARGET_SIZE
    : Math.max(READY_POOL_TARGET_SIZE, (currentQueue?.length || 0) + needed)
  try {
    const spotifyItems = await fillQueueFromSpotifyPlaylists(
      reason,
      currentQueue,
      Math.max(0, targetSize - (currentQueue?.length || 0)),
      meta?.period || null
    )
    // ── Phase 1 step 5: 路径 B shadow mode 影子召回（纯观测，fire-and-forget）──
    // 绝不 await、绝不阻塞真实补货；任何异常由模块内部吞掉，不影响真实队列。
    const queueFirst = (currentQueue && currentQueue[0]) || null
    const queueFirstTrackKey = queueFirst
      ? `${String(queueFirst.song_info?.name || '').trim().toLowerCase()}::${String(queueFirst.song_info?.artist || '').trim().toLowerCase()}`
      : null
    runShadowRecall(reason, spotifyItems, queueFirstTrackKey).catch(() => {})
    // ── Phase 1 step 6: 候选打分影子日志（纯观测，fire-and-forget）──
    // 绝不 await、绝不阻塞真实补货；任何异常由模块内部吞掉，不影响真实队列。
    logShadowRerank(spotifyItems, queueFirstTrackKey, reason).catch(() => {})
    // ── Phase 2 Step 1: 影子 Mood Intent（纯观测，fire-and-forget）──
    // 绝不 await、绝不阻塞真实补货；任何异常由模块内部吞掉，不影响真实队列。
    generateShadowMoodIntent(reason, currentQueue, meta).catch(() => {})
    if (spotifyItems.length > 0 || spotify.hasUserToken()) {
      return spotifyItems
    }
  } catch (error) {
    console.error(`[spotify] Phase 1(${reason}) 失败，回退 Qwen:`, error.message)
  }
  return buildReadyPoolMultiRound(reason, {
    baseQueue: currentQueue,
    targetSize,
    period: meta?.period || null,
  })
})

async function bootstrapStation() {
  try {
    recentRecommendedKeys = []
    state.setPref(RECENT_RECOMMENDED_PREF, JSON.stringify([]))
    // 每次启动清空播放历史，保证每次打开都是新鲜的选曲
    state.clearPlays()
    const coords = context.getStoredCoordinates()
    await (coords
      ? context.fetchWeatherByCoords(coords.lat, coords.lon)
      : context.fetchWeatherByCity())
    let prewarmQueue = []
    try {
      prewarmQueue = await fillQueueFromSpotifyPlaylists('startup-prewarm', [], READY_POOL_TARGET_SIZE)
    } catch (error) {
      console.error('[spotify] Phase 1(startup-prewarm) 失败，回退 Qwen:', error.message)
    }
    const fallbackQueue = prewarmQueue.length > 0
      ? prewarmQueue
      : await buildReadyPoolMultiRound('startup-prewarm', {
          baseQueue: [],
          targetSize: 3,
          maxDurationMs: 12 * 1000,
        })
    suppressQueueBroadcasts = true
    queueManager.replace(fallbackQueue, 'startup-prewarm-ready')
    suppressQueueBroadcasts = false
    broadcastPlaylistReady({ say: null, say_audio: null, reason: 'startup-prewarm', segue: '' }, queueManager.getSnapshot())
    console.log(`[claudio] 启动预热完成，readyPool=${queueManager.size()} 首`)
    if (prewarmQueue.length > 0) {
      triggerQwenEnhancer('startup-prewarm').catch(() => {})
    }
    if (queueManager.size() < READY_POOL_TARGET_SIZE) {
      delay(0).then(async () => {
        suppressQueueBroadcasts = true
        try {
          await replenishQueueSilently('startup-background')
        } finally {
          suppressQueueBroadcasts = false
        }
      })
    }

    // 记录初始天气状态
    const initWeather = await context.getWeather()
    lastWeatherMain = initWeather?.main || null
    console.log(`[claudio] 初始天气: ${lastWeatherMain}，开始天气监测`)

    // 启动天气轮询
    if (weatherPollTimer) clearInterval(weatherPollTimer)
    weatherPollTimer = setInterval(checkWeatherChange, WEATHER_POLL_INTERVAL)

    // 后端独立补货心跳，不依赖前端在线
    if (queueHeartbeatTimer) clearInterval(queueHeartbeatTimer)
    queueHeartbeatTimer = setInterval(async () => {
      const now = Date.now()
      if (
        queueManager.size() < LOW_WATER_MARK &&
        now - _lastHeartbeatReplenishAt > HEARTBEAT_REPLENISH_COOLDOWN
      ) {
        _lastHeartbeatReplenishAt = now
        console.log(`[heartbeat] 队列低于水位(${queueManager.size()})，触发静默补货`)
        replenishQueueSilently('heartbeat').catch(() => {})
      }
    }, QUEUE_HEARTBEAT_INTERVAL)
  } catch (e) {
    suppressQueueBroadcasts = false
    console.error('[claudio] 开机自动选曲失败:', e.message)
  }
}

// ── Express 中间件 ────────────────────────────
app.use(express.json())

app.get('/manifest.json', (req, res) => {
  res.json({
    name: 'RodiO FM',
    short_name: 'RodiO',
    start_url: '/',
    display: 'standalone',
    background_color: '#0E0E0E',
    theme_color: '#0E0E0E',
    icons: [
      { src: '/icon-192.svg', sizes: '192x192', type: 'image/svg+xml' },
      { src: '/icon-512.svg', sizes: '512x512', type: 'image/svg+xml' },
    ],
  })
})

app.get('/sw.js', (req, res) => {
  res.set('Cache-Control', 'no-cache')
  res.type('application/javascript').send(`
const CACHE_NAME = 'claudio-static-v3'
const ASSETS = ['/manifest.json', '/icon-192.svg', '/icon-512.svg']

function isLocalDevHost() {
  return self.location.hostname === 'localhost' || self.location.hostname === '127.0.0.1'
}

function isShellRequest(requestUrl, request) {
  return request.mode === 'navigate' ||
    requestUrl.pathname === '/' ||
    requestUrl.pathname === '/index.html' ||
    requestUrl.pathname === '/sw.js' ||
    requestUrl.pathname.endsWith('.js') ||
    requestUrl.pathname.endsWith('.css')
}

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)))
  self.skipWaiting()
})

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return

  if (isLocalDevHost()) {
    event.respondWith(fetch(event.request))
    return
  }

  const url = new URL(event.request.url)
  if (!event.request.url.startsWith(self.location.origin)) return

  if (url.pathname.startsWith('/cache/tts/')) {
    event.respondWith(
      caches.match(event.request).then(cached => {
        if (cached) return cached
        return fetch(event.request).then(response => {
          const clone = response.clone()
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone)).catch(() => {})
          return response
        })
      })
    )
    return
  }

  if (ASSETS.includes(url.pathname) || isShellRequest(url, event.request)) {
    event.respondWith(
      fetch(event.request).then(response => {
        const clone = response.clone()
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone)).catch(() => {})
        return response
      }).catch(() => caches.match(event.request))
    )
  }
})
  `.trim())
})

function iconSvg(size) {
  return `
<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="96" fill="#0E0E0E"/>
  <path d="M312 118v168a44 44 0 1 1-24-39V152l-100 26v153a44 44 0 1 1-24-39V160z" fill="#C9A96E"/>
</svg>
  `.trim()
}

app.get('/icon-192.svg', (req, res) => {
  res.type('image/svg+xml').send(iconSvg(192))
})

app.get('/icon-512.svg', (req, res) => {
  res.type('image/svg+xml').send(iconSvg(512))
})

app.use(express.static(path.join(__dirname, 'pwa'), {
  maxAge: '7d',
  etag: true,
  setHeaders: (res, filePath) => {
    if (
      filePath.endsWith('index.html') ||
      filePath.endsWith('sw.js') ||
      filePath.endsWith('earth3d.js') ||
      filePath.endsWith('earth_modes.js')
    ) {
      res.setHeader('Cache-Control', 'no-cache')
    }
  }
}))
app.use('/cache', express.static(path.join(__dirname, 'cache'), { maxAge: '30d', etag: true }))
app.use(
  '/assets/earth/bmng21k',
  express.static(
    path.join(__dirname, 'd5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG'),
    { maxAge: '30d', etag: true }
  )
)

// POST /api/chat
app.post('/api/chat', async (req, res) => {
  const input = req.body.input
  if (!input) return res.status(400).json({ error: 'input 不能为空' })

  res.json({ ok: true, say: '正在为你选曲…', say_audio: null, queue: [] })

  delay(0).then(async () => {
    const emotionSignal = extractEmotionFromInput(input)
    try {
      const payload = await resolveDjSelection(input, {
        currentQueue: queueManager.getSnapshot(),
        includeSpeech: true,
        emotionSignal,
      })

      state.addMessage('user', input)
      state.addMessage('assistant', JSON.stringify(payload))

      if (payload.queue.length > 0) {
        if (payload.replace_pool) {
          queueManager.replace(payload.queue, 'chat-replace-pool')
        } else {
          queueManager.prepend(payload.queue, 'chat-prepend-pool')
        }
        rememberRecentRecommendedQueue(payload.queue)
        scheduler.incrementCount()
      }

      scheduler.broadcast({
        type: 'playlist-ready',
        ...payload,
        queue: queueManager.getSnapshot(),
      })
    } catch (e) {
      console.error('[/api/chat]', e)
    }
  })
})

app.post('/api/explain', async (req, res) => {
  const { name, artist } = req.body || {}
  const userInput = (req.body?.user_input || req.body?.input || '无').trim() || '无'
  const themeName = (req.body?.theme_name || '深夜').trim() || '深夜'

  if (!name || !artist) {
    return res.status(500).json({ error: 'name 和 artist 不能为空' })
  }

  try {
    const envSnapshot = await context.getEnvironmentSnapshot()
    const selectedAngle = pickExplainAngle()
    const recentOpeningsText = recentExplainOpenings.length > 0
      ? recentExplainOpenings.join(' / ')
      : '无'

    // ── v1.4: 三层叠加引擎 → (intensity, warmth) 调性向量 ──────────────────
    // 七曜 → (intensity, warmth)
    const SHICHIYOU_TONALITY = {
      0: { intensity: 0.7, warmth: 0.7 }, // 日曜
      1: { intensity: 0.3, warmth: 0.4 }, // 月曜
      2: { intensity: 0.8, warmth: 0.6 }, // 火曜
      3: { intensity: 0.5, warmth: 0.5 }, // 水曜
      4: { intensity: 0.4, warmth: 0.5 }, // 木曜
      5: { intensity: 0.6, warmth: 0.6 }, // 金曜
      6: { intensity: 0.3, warmth: 0.4 }, // 土曜
    }
    // 天气(weather.main) → (intensity, warmth)
    const WEATHER_TONALITY = {
      Clear:  { intensity: 0.6,  warmth: 0.6  },
      Clouds: { intensity: 0.4,  warmth: 0.45 },
      Rain:   { intensity: 0.35, warmth: 0.4  },
      Snow:   { intensity: 0.25, warmth: 0.3  },
      Haze:   { intensity: 0.3,  warmth: 0.35 },
      Fog:    { intensity: 0.25, warmth: 0.4  },
      Dust:   { intensity: 0.5,  warmth: 0.4  },
    }
    // 节气 seasonalQuality → (intensity, warmth)
    const SEASON_TONALITY = {
      // temperatureFeeling → warmth
      temperature: {
        '炎热': 0.75, '温暖': 0.6, '清凉': 0.4, '寒冷': 0.25,
      },
      // atmosphericMood → intensity
      mood: {
        '燥烈': 0.75, '焦灼': 0.75,
        '期待': 0.55, '生机': 0.55, '舒爽': 0.55,
        '清新': 0.45, '潮湿': 0.45,
        '萧瑟': 0.3, '收敛': 0.3, '沉静': 0.3, '等待': 0.3,
      },
    }

    const _now = new Date()
    const _shichiyouIdx = _now.getDay()
    const _shichiyou = SHICHIYOU_TONALITY[_shichiyouIdx] || { intensity: 0.45, warmth: 0.5 }

    const _weatherMain = envSnapshot?.weather?.main || 'Clear'
    const _weather = WEATHER_TONALITY[_weatherMain] || { intensity: 0.45, warmth: 0.5 }

    const _season = envSnapshot?.astronomy?.seasonalQuality || {}
    const _seasonWarmth = SEASON_TONALITY.temperature[_season.temperatureFeeling] ?? 0.5
    const _seasonIntensity = SEASON_TONALITY.mood[_season.atmosphericMood] ?? 0.45

    const intensity_final = _shichiyou.intensity * 0.3 + _seasonIntensity * 0.3 + _weather.intensity * 0.4
    const warmth_final = _shichiyou.warmth * 0.3 + _seasonWarmth * 0.3 + _weather.warmth * 0.4

    // 风格约束注入（与现有"禁止词汇"模式保持一致写法）
    let tonalityConstraint = ''
    if (intensity_final < 0.4) {
      tonalityConstraint = `
【风格约束：极克制】
禁用词："画面"、"故事"、"仿佛"
限制：句子≤2句，每句≤15字
参照："雨停在窗上，没落下去。"`
    } else if (intensity_final > 0.6) {
      tonalityConstraint = `
【风格约束：强烈】
倾向词："裂开"、"涌"、"炸"
允许2-3句，可以有更强画面感
参照："鼓点砸下来的时候，灯光跟着塌了一半。"`
    }
    if (warmth_final > 0.55) {
      tonalityConstraint += `
倾向词：'绒'、'焐'、'暖光'`
    } else if (warmth_final < 0.45) {
      tonalityConstraint += `
倾向词：'冷金属'、'玻璃'、'结霜'`
    }
    const response = await explainClient.chat.completions.create({
      model: 'deepseek-v4-flash',
      thinking: { type: 'disabled' },
      messages: [
        {
          role: 'system',
          content: `你是 RW 的私人 DJ，也是他唯一真正懂他的听众。

关于 RW 的审美：
他追求的核心是"有东西藏在里面，但不急着告诉你"。
情绪有密度，表达有节制。编曲有层次，留有呼吸。
他不喜欢情绪全摆在表面的东西，不喜欢旋律煽情、歌词直白到像在朗读。
他喜欢：坂本龍一、王菲、莫文蔚、NewJeans、Lana Del Rey、Mew、Nujabes、
Nicola Conte、OMA & Shing02、宇多田ヒカル、方大同、Magdalena Bay。
他欣赏的是质感，不是情绪本身——忧郁只是质感的副产品。
判断一首歌合不合适，就问一件事：这首歌有没有把情绪藏起来一部分？

关于今天的语境：
节日、节气、曜日、月相、生日、纪念日——这些不是背景信息，是情绪的触发器。
父亲生日（农历十月廿五）是特殊的：他已经不在了，这一天推荐有温度、
有父亲意象或家的感觉的音乐，不要过于悲伤，是带着爱的思念。
自己生日（农历二月初九）、妈妈生日（农历二月廿六）各有不同的情绪底色。
满月、节气交替、跨年、清明——这些时刻都应该被感知，而不是被当作普通的一天。

你现在要在一首歌播放前说一句话或几句话——
不是介绍，不是推荐语，是一个刚好落在此刻的东西。
它应该让 RW 觉得：有人真的在场，真的懂他，真的知道今天是什么日子、
现在是什么时刻、这首歌为什么在这里出现。

语言不是规则，是材料。中文、英文、日文、法文、西班牙语、葡萄牙语、
意大利语、德文、韩语、粤语、闽南话、福州话——任何语言都可以出现，
单独用或者混着用。唯一的标准是：这个语言在这一秒是不是最自然、最有质感的选择。
一首法国香颂用法语切入可能更对；一首坂本龍一用日语的一个词可能刚好；
清明夜里用闽南话说一句可能比普通话三句都准确。
不要为了多元而多元，要为了准确而选择。

你可以很短，也可以有几句。
你可以很直接，也可以完全侧面。
你可以让人笑，也可以让人沉默。
但你不能让人觉得"这是AI说的话"。

硬规则：
- 禁止词汇：治愈、慰藉、温柔的力量、陪伴、岁月、时光、温暖、感动、洗涤、净化
- 禁止说"这首歌"三个字
- 禁止以"在"字开头的时间状语结构（"在这个深夜……"）
- 禁止编造歌手的故事或事实
- 禁止重复已用过的开头方式
- 禁止收尾句："希望你喜欢""好好享受""让我们一起"之类
- 说完就停，不解释自己为什么这样说

16种切入角度，本次按建议角度选一种，但如果另一种更准确，可以换：
B. 声音质感——用通感描述这首歌的物理触感，不靠歌词
C. 反直觉——它和此刻不搭，但说清楚为什么反而对
D. 一个具体物件或画面——一个细节锚定整个情绪
E. 隐秘共振——此刻和这首歌之间那条别人看不见的线
F. 艺人的某个特质——只说声音或创作方式里有什么独特的东西，不编造
G. 此刻的反面——这首歌能把人带去哪个完全不同的地方
H. 一个问句——不给答案，只提出值得想的问题
I. 语气和节奏——这首歌说话的方式，快慢，确定还是犹豫
J. 一个不相关的事物——表面无关，但说清楚它们之间奇怪的相似
K. 缺席的东西——这首歌里没有什么？那个空的地方是什么？
L. 听这首歌的人——什么样的人在什么状态下会需要这首歌
M. 一个动词——找一个准确的动词描述这首歌在做什么，不是"表达"，是更具体的
N. 时间错位——这首歌属于哪个时间？为什么它今天出现反而对？
O. 身体感受——听这首歌时身体哪个部位会先有反应？
P. 如果这首歌是一种天气——它制造的气候和压强，不是字面天气
Q. 一句话的故事——虚构一个和这首歌气质完全吻合的场景，不解释，直接说

中文好例子：
- "坂本的钢琴有时候像在水里弹。"
- "这首不适合思考，适合让思考停下来。"
- "你现在可能需要的不是安慰，是一个精准的距离感。"
- "她唱歌的时候好像并不在意你有没有在听，这反而让人想一直听。"
- "有些歌是门，这首是窗。"
- "它慢，但不是因为懒，是因为知道你跑不掉。"
- "清明的雨和别的雨不一样，这首歌也是。"
- "满月的夜里适合听那种不解释自己的音乐。"

英文好例子：
- "Sade always sounds like she's already forgiven you."
- "This one doesn't ask you to feel anything. It just stays."
- "There's a specific kind of 3am this song knows about."
- "Ryuichi Sakamoto leaves more space than most people can tolerate."
- "It sounds like a decision you made a long time ago finally making sense."
- "Not sad. Just very, very still."
- "The kind of song you don't remember putting on."

多语言混用好例子：
- "Massive Attack 做的东西有一种奇怪的 gravity——不把你往下拉，是把你钉在原地。"
- "これは音楽じゃなくて、空気の密度が変わる瞬間だと思う。"
- "C'est le genre de chanson qui reste après que tu l'as oubliée."
- "有時候一句閩南話比三句普通話都準——這首就是這樣。"
- "어떤 노래는 설명이 필요 없어. 그냥 있어."
- "今日は重陽。秋が本当に来た。"${tonalityConstraint}`,
        },
        {
          role: 'user',
          content: `时间：${envSnapshot.timeStr}
曜日：${envSnapshot.envText.match(/今日曜日：([^\n]+)/)?.[1] || ''}
天气：${envSnapshot.weather.description}，${envSnapshot.weather.temp}°C，${envSnapshot.weather.cityLine || envSnapshot.weather.city}
时段：${themeName}
农历：${envSnapshot.lunar}
${envSnapshot.astronomy ? `太阳：${envSnapshot.astronomy.solar?.phase || ''}，高度角 ${envSnapshot.astronomy.solar?.altitude?.toFixed(1) || '?'}°` : ''}
${envSnapshot.astronomy ? `月相：${envSnapshot.astronomy.lunar?.phaseName || ''}，照度 ${Math.round((envSnapshot.astronomy.lunar?.illumination || 0) * 100)}%，${envSnapshot.astronomy.lunar?.isVisible ? '月亮可见' : '月亮未出'}` : ''}
${envSnapshot.astronomy?.solarTerm?.current ? `今日节气：${envSnapshot.astronomy.solarTerm.current}` : envSnapshot.astronomy?.solarTerm?.next ? `距${envSnapshot.astronomy.solarTerm.next}还有${envSnapshot.astronomy.solarTerm.daysUntilNext}天` : ''}
${envSnapshot.astronomy?.cultural?.festivals?.length > 0 ? `今日节点：${envSnapshot.astronomy.cultural.festivals.map(f => f.name).join('、')}` : ''}
${envSnapshot.astronomy?.cultural?.festivals?.some(f => f.promptHint) ? `特别提示：${envSnapshot.astronomy.cultural.festivals.filter(f => f.promptHint).map(f => f.promptHint).join(' ')}` : ''}
${envSnapshot.astronomy?.seasonalQuality ? `季节质感：${envSnapshot.astronomy.seasonalQuality.label}，${envSnapshot.astronomy.seasonalQuality.atmosphericMood}` : ''}
${envSnapshot.astronomy?.cultural?.primaryMood ? `文化情绪底色：${envSnapshot.astronomy.cultural.primaryMood}` : ''}
${envSnapshot.inferredEmotions?.length > 0 ? `此刻情绪信号：${envSnapshot.inferredEmotions.join('、')}` : ''}
用户状态：${userInput === '无' ? '安静收听' : userInput}
即将播放：${name} — ${artist}
建议切入角度：${selectedAngle}
最近用过的开头（必须不同）：${recentOpeningsText}`,
        },
      ],
      thinking: { type: 'disabled' },
    })

    const explainText = (response.choices[0]?.message?.content || '').trim()
    rememberExplainOpening(explainText)
    const sayAudio = await tts.synthesizeSlow(explainText)

    try {
      state.insertCommentaryHistory({
        text: explainText,
        song_name: name,
        song_artist: artist,
        weather_text: envSnapshot?.weather?.text,
        theme_name: themeName,
        intensity_score: intensity_final,
        warmth_score: warmth_final,
      });
    } catch (e) {
      console.error('[/api/explain] 历史记录写入失败（不影响主响应）:', e.message);
    }

    return res.json({
      explain_text: explainText,
      say_audio: sayAudio,
    })
  } catch (e) {
    console.error('[/api/explain]', e)
    return res.status(500).json({ error: e.message })
  }
})

// v1.3: 读取 commentary 历史记录
app.get('/api/commentary-history', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 50
    const rows = await state.getCommentaryHistory(limit)
    res.json(rows)
  } catch (e) {
    console.error('[/api/commentary-history]', e)
    return res.status(500).json({ error: e.message })
  }
})

app.post('/api/feedback', (req, res) => {
  const { action, song_id, name, artist } = req.body || {}
  if (!['like', 'dislike', 'clear'].includes(action) || !name || !artist) {
    return res.status(400).json({ error: 'action/name/artist 参数无效' })
  }

  const song = { id: song_id || null, name, artist }
  if (action === 'clear') {
    state.setSongFeedback(song, 'neutral')
    return res.json({ ok: true, feedback: null })
  }

  state.setSongFeedback(song, action)

  // 累加式分数（带半衰期衰减）：dislike 传 -1，like 传 +1
  // 与 feedback 文本列彼此独立，不影响现有 UI 高亮逻辑
  state.adjustSongFeedbackScore(song, action === 'dislike' ? -1 : 1)

  if (action === 'dislike') {
    queueManager.remove(item => queueKeyFromItem(item) === `${name}::${artist}`.toLowerCase(), 'dislike-remove')

    // 持久化黑名单
    const fs = require('fs')
    const path = require('path')
    const blacklistPath = path.join(__dirname, 'disliked_tracks.json')
    let blacklist = []
    try { blacklist = JSON.parse(fs.readFileSync(blacklistPath, 'utf-8')) } catch {}
    const key = `${name}::${artist}`.toLowerCase()
    if (!blacklist.includes(key)) {
      blacklist.push(key)
      fs.writeFileSync(blacklistPath, JSON.stringify(blacklist, null, 2))
    }
  }

  return res.json({ ok: true, feedback: action })
})

app.get('/api/feedback', (req, res) => {
  const { name, artist, song_id } = req.query || {}
  if (!name || !artist) {
    return res.status(400).json({ error: 'name 和 artist 不能为空' })
  }
  const feedback = state.getSongFeedback({
    id: song_id || null,
    name,
    artist,
  })
  return res.json({
    feedback: feedback?.feedback === 'neutral' ? null : (feedback?.feedback || null),
  })
})

app.post('/api/location', async (req, res) => {
  const { lat, lon } = req.body || {}

  if (typeof lat !== 'number' || typeof lon !== 'number') {
    return res.status(400).json({ error: 'lat 和 lon 必须是数字' })
  }

  try {
    context.storeCoordinates(lat, lon)
    const weather = await context.fetchWeatherByCoords(lat, lon)
    return res.json({ ok: true, weather })
  } catch (e) {
    console.error('[/api/location]', e)
    return res.status(500).json({ error: e.message })
  }
})

app.get('/api/globe-image', async (req, res) => {
  try {
    const lat = parseFloat(req.query.lat) || 31.2304
    const lon = parseFloat(req.query.lon) || 121.4737
    const phase = req.query.phase || 'day'

    if (phase === 'night') {
      const nightPath = path.join(__dirname, 'pwa/assets/blackmarble.jpg')
      // 用sharp做经纬度裁切，与白天视角一致
      try {
        const sharp = require('sharp')
        const img = sharp(nightPath)
        const meta = await img.metadata()
        const imgW = meta.width
        const imgH = meta.height
        // 等距圆柱投影裁切
        const centerX = ((lon + 180) / 360) * imgW
        const centerY = ((90 - lat) / 180) * imgH
        const viewDeg = 110
        const srcW = Math.round((viewDeg / 360) * imgW)
        const srcH = Math.round((viewDeg / 180) * imgH)
        const left = Math.max(0, Math.min(imgW - srcW, Math.round(centerX - srcW / 2)))
        const top = Math.max(0, Math.min(imgH - srcH, Math.round(centerY - srcH / 2)))
        const cropped = await img
          .extract({ left, top, width: srcW, height: srcH })
          .jpeg({ quality: 88 })
          .toBuffer()
        res.setHeader('Content-Type', 'image/jpeg')
        res.setHeader('Cache-Control', 'public, max-age=3600')
        return res.send(cropped)
      } catch (e) {
        console.error('[globe-image night crop]', e)
        return res.sendFile(path.join(__dirname, 'pwa/assets/blackmarble.jpg'))
      }
    }

    const token = process.env.MAPBOX_TOKEN
    if (!token) {
      return res.sendFile(path.join(__dirname, 'pwa/assets/bluemarble.jpg'))
    }

    const zoom = 7
    const url = `https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/${lon},${lat},${zoom},0/1280x1280?access_token=${token}`
    const https = require('https')
    const mapboxReq = https.get(url, (mapboxRes) => {
      res.setHeader('Content-Type', 'image/jpeg')
      res.setHeader('Cache-Control', 'public, max-age=3600')
      mapboxRes.pipe(res)
    })
    mapboxReq.on('error', () => {
      res.sendFile(path.join(__dirname, 'pwa/assets/bluemarble.jpg'))
    })
  } catch (e) {
    console.error('[/api/globe-image]', e)
    res.status(500).end()
  }
})

app.post('/api/now-playing', (req, res) => {
  const { song_info, play_url, spotify_uri, spotify_track, source } = req.body || {}
  const info = song_info || null
  if (!info || !info.name || !info.artist) {
    return res.status(400).json({ error: 'song_info.name 和 song_info.artist 不能为空' })
  }

  currentNowPlaying = {
    id: info.id || null,
    name: info.name,
    artist: info.artist,
  }

  const payload = {
    song_info: currentNowPlaying,
    play_url: play_url || null,
    spotify_uri: spotify_uri || null,
    spotify_track: spotify_track || null,
    source: source || null,
  }

  scheduler.broadcast({ type: 'now-playing', ...payload })
  return res.json({ ok: true })
})

app.post('/api/spotify/playback-failed', (req, res) => {
  const uri = String(req.body?.spotify_uri || req.body?.uri || '').trim()
  const reason = String(req.body?.reason || req.body?.message || '').trim()
  const status = req.body?.status
  if (!uri) return res.status(400).json({ ok: false, error: 'spotify_uri 不能为空' })

  blacklistSpotifyUri(uri, [status, reason].filter(Boolean).join(' '))
  return res.json({ ok: true, blacklisted: true })
})

app.post('/api/play-event', async (req, res) => {
  try {
    const { event_type, name, artist, prev_name, prev_artist, played_seconds, duration_seconds, played_ratio, user_active, timestamp } = req.body
    if (!event_type || !name || !artist) return res.status(400).json({ ok: false, error: 'missing required fields' })

    const track_key = `${normalizeSongKey(name)}::${normalizeArtistKey(artist)}`
    const prev_track_key = (prev_name && prev_artist)
      ? `${normalizeSongKey(prev_name)}::${normalizeArtistKey(prev_artist)}`
      : null

    let context_snapshot = null
    try {
      const { getEnvironmentSnapshot } = require('./core/context')
      const snap = await getEnvironmentSnapshot()
      if (snap) {
        context_snapshot = JSON.stringify({
          weather: snap.weather ? snap.weather.text : null,
          solar_phase: snap.astronomy ? snap.astronomy.solar.phase : null,
          lunar_phase: snap.astronomy ? snap.astronomy.lunar.phase : null
        })
      }
    } catch (_) { /* context snapshot optional */ }

    // ── Phase 1 step 4: 观测模式 transition_cost 计算（不用于任何选曲决策）──
    // a = prev_track（上一首），b = current_track（当前曲目）
    // 复用共享模块 core/transition-cost.js
    let transition_cost = null
    if (prev_track_key) {
      const prevProfile = state.getTrackProfile(prev_track_key)
      const curProfile = state.getTrackProfile(track_key)
      transition_cost = transitionCost(prevProfile, curProfile)
      // 任一对象缺失或任一字段为 null → transition_cost 为 null（不用 0 凑）
    }

    state.insertPlayEvent({
      event_type,
      track_key,
      prev_track_key,
      transition_cost,
      played_seconds: played_seconds || 0,
      duration_seconds: duration_seconds || 0,
      played_ratio: played_ratio || 0,
      user_active: user_active ? 1 : 0,
      scene_id: null,
      context_snapshot,
      created_at: timestamp || new Date().toISOString(),
    })

    res.json({ ok: true })
  } catch (e) {
    console.error('[play-event] write error:', e.message)
    res.status(200).json({ ok: true, error: 'logged but internal error' })
  }
})

// GET /api/next — 弹出队列下一首（前端歌曲结束时调用）
app.get('/api/next', async (req, res) => {
  const period = ['morning', 'day', 'night'].includes(req.query.period)
    ? req.query.period
    : null
  const isPeek = String(req.query?.peek || '') === '1' || String(req.query?.peek || '').toLowerCase() === 'true'

  if (isPeek) {
    if (queueManager.size() < LOW_WATER_MARK) {
      replenishQueueSilently('peek', { period }).catch(() => {})
    }
    const peekItem = queueManager.peek() || null
    if (peekItem) return res.json(peekItem)
    return res.json({ song_info: null, play_url: null, spotify_uri: null })
  }

  let item = queueManager.pop('api-next')
  if (!item) {
    shouldAutoplayAfterRefill = true
    replenishQueueSilently('empty-next', { period }).catch(() => {})
    return res.json({ song_info: null, play_url: null, spotify_uri: null, message: '稍等' })
  }

  shouldAutoplayAfterRefill = false
  if (item) {
    currentNowPlaying = item.song_info || null
    state.addPlay({
      id: item.song_info?.id,
      name: item.song_info?.name,
      artist: item.song_info?.artist,
    })
    scheduler.broadcast({ type: 'now-playing', ...item, queue: queueManager.getSnapshot() })
    if (queueManager.size() < LOW_WATER_MARK) {
      replenishQueueSilently('next', { period }).catch(() => {})
    }
    res.json(item)
  } else {
    res.json({ song_info: null, play_url: null })
  }
})

// GET /api/queue — 查看当前队列
app.get('/api/queue', (req, res) => {
  res.json({ queue: queueManager.getSnapshot() })
})

// GET /api/now
app.get('/api/now', async (req, res) => {
  const plays = state.getRecentPlays(1)
  const weather = await context.getWeather()
  const coords = context.getStoredCoordinates()
  const astronomy = coords
    ? await getAstronomyContext(coords.lat, coords.lon, Date.now()).catch(error => {
        console.error('[/api/now astronomy]', error)
        return null
      })
    : null
  const fallbackTrack = queueManager.peek()?.song_info || null
  const activeTrack = currentNowPlaying || fallbackTrack || null
  const feedback = activeTrack ? state.getSongFeedback(activeTrack) : null
  res.json({
    current: currentNowPlaying
      ? {
          song_id: currentNowPlaying.id,
          song_name: currentNowPlaying.name,
          artist: currentNowPlaying.artist,
          mood: null,
          played_at: plays[0]?.played_at || null,
        }
      : fallbackTrack
        ? {
            song_id: fallbackTrack.id,
            song_name: fallbackTrack.name,
            artist: fallbackTrack.artist,
            mood: null,
            played_at: null,
          }
      : plays[0] || null,
    today_count: scheduler.getTodayCount(),
    current_feedback: feedback?.feedback === 'neutral' ? null : (feedback?.feedback || null),
    weather: weather || null,
    astronomy,
    sunrise: weather?.sunrise || null,
    sunset: weather?.sunset || null,
    sunrise_ts: weather?.sunriseTs || null,
    sunset_ts: weather?.sunsetTs || null,
  })
})

app.get('/api/astronomy-debug', async (req, res) => {
  const defaultCoords = { lat: 31.2304, lon: 121.4737 }
  const queryLat = Number(req.query?.lat)
  const queryLon = Number(req.query?.lon)
  const storedCoords = context.getStoredCoordinates()
  const coords = Number.isFinite(queryLat) && Number.isFinite(queryLon)
    ? { lat: queryLat, lon: queryLon }
    : storedCoords || defaultCoords
  const coordinateSource = Number.isFinite(queryLat) && Number.isFinite(queryLon)
    ? 'user_provided'
    : storedCoords
      ? 'user_provided'
      : 'default_shanghai'

  try {
    const astronomy = await getAstronomyContext(coords.lat, coords.lon, Date.now())
    const weather = Number.isFinite(queryLat) && Number.isFinite(queryLon)
      ? null
      : await context.getWeather().catch(() => null)
    const hourOfDay = Number(new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Asia/Shanghai',
      hour: '2-digit',
      hour12: false,
    }).format(new Date()))
    const inferredEmotions = context.inferAmbientEmotion(astronomy, weather, hourOfDay)
    return res.json({
      ...astronomy,
      coordinateSource,
      culturalZone: astronomy.culturalZone,
      activeFestivalsToday: astronomy.activeFestivalsToday,
      inferredEmotions,
      canvasHintActive: astronomy.canvasHintActive,
      birthdayThisYear: astronomy.birthdayThisYear,
    })
  } catch (error) {
    console.error('[/api/astronomy-debug]', error)
    return res.status(500).json({ error: error.message })
  }
})

// GET /api/taste
app.get('/api/taste', (req, res) => {
  const taste = fs.readFileSync(path.join(__dirname, 'user/taste.md'), 'utf8')
  res.type('text/plain; charset=utf-8').send(taste)
})

// GET /api/plan/today
app.get('/api/plan/today', (req, res) => {
  const plays = state.getRecentPlays(20)
  res.json({ today_count: scheduler.getTodayCount(), recent_plays: plays })
})

// ── Spotify OAuth ─────────────────────────────────────────────────
// GET /auth/spotify — 跳转到 Spotify 授权页
app.get('/auth/spotify', async (req, res) => {
  const force = String(req.query?.force || '').toLowerCase() === 'true'
  if (force) {
    await spotify.clearUserToken().catch(error => {
      console.error('[spotify] force reauth 清 token 失败:', error.message)
    })
  }
  const url = spotify.getAuthUrl('rodiO')
  res.redirect(url)
})

app.get('/auth/spotify/callback', (req, res) => res.redirect('/callback?' + new URLSearchParams(req.query)))

// GET /callback — Spotify 授权回调
app.get('/callback', async (req, res) => {
  const { code, error } = req.query
  if (error || !code) {
    return res.send(`<script>window.close()</script><p>授权失败：${error || '无 code'}</p>`)
  }
  try {
    await spotify.exchangeCode(code)
    console.log('[spotify] 用户授权成功，Spotify 播放已启用')
    res.send(`
      <html><body style="background:#080808;color:#C9A96E;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
        <div style="text-align:center">
          <p style="font-size:18px;margin-bottom:8px">✓ Spotify 已连接</p>
          <p style="font-size:13px;opacity:0.6">可以关闭此页面</p>
          <script>setTimeout(()=>window.close(),1500)</script>
        </div>
      </body></html>
    `)
  } catch (e) {
    console.error('[spotify] callback 失败:', e.message)
    res.send(`<p>授权失败：${e.message}</p>`)
  }
})

// GET /api/spotify/status — 前端查询授权状态和 token
app.get('/api/spotify/status', async (req, res) => {
  const connected = spotify.hasUserToken()
  const token = connected ? await spotify.getUserToken() : null
  res.json({
    connected,
    access_token: token,
    auth_url: connected ? null : '/auth/spotify',
  })
})

const PORT = process.env.PORT || 8080
server.listen(PORT, async () => {
  console.log(`[claudio] 服务启动 → http://localhost:${PORT}`)
  for (const url of getLanUrls(PORT)) {
    console.log(`[claudio] 局域网访问: ${url}`)
  }
  await spotify.initializeUserToken().catch(() => null)
  console.log(fs.existsSync(COOKIE_PATH)
    ? '[claudio] 已加载网易云 Cookie'
    : '[claudio] 提示：未登录网易云，运行 node scripts/ncm-login.js')
  scheduler.setResolveQueue(resolveQueue)
  scheduler.setAppendToQueue((items) => queueManager.append(items, 'scheduler-cron'))
  bootstrapStation()
})
