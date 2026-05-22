// ── Spotify 模块 ─────────────────────────────────────────────────
const state = require('./state')
const {
  artistMatchScore,
  buildArtistVariants,
  buildTitleVariants,
  makeSongSearchProfile,
  normalizeBaseText,
  normalizeCompareText,
  normalizeSongKey,
  stripTitleNoise,
  titleMatchScore,
} = require('./search-utils')
const CLIENT_ID = process.env.SPOTIFY_CLIENT_ID
const CLIENT_SECRET = process.env.SPOTIFY_CLIENT_SECRET
const REDIRECT_URI = process.env.SPOTIFY_REDIRECT_URI || 'https://web-production-a5193.up.railway.app/auth/spotify/callback'
const RAILWAY_GRAPHQL_ENDPOINT = 'https://backboard.railway.app/graphql/v2'
const SPOTIFY_TOKEN_PREF = 'spotify_user_token_v1'
const SPOTIFY_BAD_TITLE_KWS = [
  'live', 'remix', 'acoustic', 'instrumental', 'cover', 'tribute',
  'karaoke', 'piano', 'version', 'ver.', 'edit', 'mono', 'demo',
]
const USER_PLAYLIST_CACHE_MS = 5 * 60 * 1000
const USER_PLAYLIST_TRACKS_CACHE_MS = 10 * 60 * 1000

let clientCredToken = null      // 用于搜索（不需要用户授权）
let userAccessToken = null      // 用于播放（需要用户授权）
let userRefreshToken = null
let userTokenExpiresAt = 0
let tokenInitPromise = null
const searchTrackCache = new Map()
let userPlaylistsCache = { items: [], fetchedAt: 0 }
const playlistTracksCache = new Map()
let playlistRotationIds = []
let playlistRotationIndex = 0

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

function parseRetryAfterMs(value) {
  if (!value) return 0
  const seconds = Number(value)
  if (Number.isFinite(seconds) && seconds >= 0) return seconds * 1000
  const retryAt = Date.parse(value)
  if (Number.isFinite(retryAt)) return Math.max(0, retryAt - Date.now())
  return 0
}

function shuffle(items) {
  const copy = Array.isArray(items) ? items.slice() : []
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

async function fetchJsonWithTimeout(url, options = {}, timeoutMs = 8000) {
  const maxRetries = 3
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      const res = await fetch(url, { ...options, signal: controller.signal })
      if (res.status !== 429 || attempt === maxRetries) return res

      const retryAfterMs = parseRetryAfterMs(res.headers.get('retry-after'))
      const backoffMs = 500 * (2 ** attempt)
      await delay(Math.max(retryAfterMs, backoffMs))
      continue
    } finally {
      clearTimeout(timer)
    }
  }
}

async function spotifyUserJson(url, options = {}, allowRefresh = true) {
  const token = await getUserToken()
  if (!token) throw new Error('No Spotify user token')

  const res = await fetchJsonWithTimeout(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  })

  if (res.status === 401 && allowRefresh && userRefreshToken) {
    await refreshUserToken()
    return spotifyUserJson(url, options, false)
  }

  const data = res.status === 204 ? null : await res.json().catch(() => null)
  if (!res.ok) {
    const message = data?.error?.message || data?.message || `Spotify user API failed (${res.status})`
    const error = new Error(message)
    error.status = res.status
    throw error
  }
  return data
}

async function paginateSpotifyUserItems(url, itemKey) {
  const items = []
  let nextUrl = url
  while (nextUrl) {
    const data = await spotifyUserJson(nextUrl)
    items.push(...(Array.isArray(data?.[itemKey]) ? data[itemKey] : []))
    nextUrl = data?.next || null
  }
  return items
}

function normalizePlaylistTrackItem(item, playlist) {
  const track = item?.track
  if (!track || item?.is_local || track?.is_local) return null
  if (!track.uri || !track.name) return null
  if (track?.is_playable === false) return null

  const artists = Array.isArray(track.artists) ? track.artists.map(artist => artist?.name).filter(Boolean) : []
  const artistName = artists.join('; ')
  if (!artistName) return null

  return {
    song_info: {
      id: track.id || null,
      name: track.name,
      artist: artistName,
    },
    requested_song_info: {
      id: track.id || null,
      name: track.name,
      artist: artistName,
    },
    spotify_uri: track.uri,
    spotify_track: {
      id: track.id || null,
      uri: track.uri,
      name: track.name,
      artists,
      album: track.album?.name || null,
    },
    play_url: null,
    source: 'spotify',
    queue_meta: {
      source_playlist_id: playlist?.id || null,
      source_playlist_name: playlist?.name || null,
    },
  }
}

function syncPlaylistRotation(playlists) {
  const playlistIds = playlists.map(playlist => playlist.id).filter(Boolean)
  const rotationChanged =
    playlistRotationIds.length !== playlistIds.length ||
    playlistIds.some(id => !playlistRotationIds.includes(id))

  if (rotationChanged || playlistRotationIndex >= playlistRotationIds.length) {
    playlistRotationIds = shuffle(playlistIds)
    playlistRotationIndex = 0
  }
}

function nextRotatedPlaylists(playlists) {
  if (!playlists.length) return []
  syncPlaylistRotation(playlists)
  const byId = new Map(playlists.map(playlist => [playlist.id, playlist]))
  const ordered = []
  for (let i = 0; i < playlistRotationIds.length; i++) {
    const idx = (playlistRotationIndex + i) % playlistRotationIds.length
    const playlist = byId.get(playlistRotationIds[idx])
    if (playlist) ordered.push(playlist)
  }
  playlistRotationIndex = (playlistRotationIndex + ordered.length) % Math.max(ordered.length, 1)
  if (playlistRotationIndex === 0) {
    playlistRotationIds = shuffle(playlistRotationIds)
  }
  return ordered
}

function applyPersistedUserToken(parsed) {
  if (!parsed || typeof parsed !== 'object') return false
  if (parsed?.refresh_token) userRefreshToken = parsed.refresh_token
  if (parsed?.access_token) userAccessToken = parsed.access_token
  if (typeof parsed?.expires_at === 'number') userTokenExpiresAt = parsed.expires_at
  return !!(userAccessToken || userRefreshToken)
}

function getRailwayTokenContext() {
  return {
    apiToken: process.env.RAILWAY_API_TOKEN || '',
    projectId: process.env.RAILWAY_PROJECT_ID || '',
    serviceId: process.env.RAILWAY_SERVICE_ID || '',
    environmentId: process.env.RAILWAY_ENVIRONMENT_ID || '',
  }
}

function loadPersistedUserToken() {
  try {
    const envToken = {
      access_token: process.env.SPOTIFY_ACCESS_TOKEN || null,
      refresh_token: process.env.SPOTIFY_REFRESH_TOKEN || null,
      expires_at: Number(process.env.SPOTIFY_TOKEN_EXPIRES_AT || 0) || 0,
    }
    if (applyPersistedUserToken(envToken)) return

    const raw = state.getPref(SPOTIFY_TOKEN_PREF)
    if (raw && applyPersistedUserToken(JSON.parse(raw))) return
  } catch {}
}

async function railwayGraphqlRequest(query, variables) {
  const { apiToken } = getRailwayTokenContext()
  if (!apiToken) throw new Error('缺少 RAILWAY_API_TOKEN')
  const res = await fetchJsonWithTimeout(RAILWAY_GRAPHQL_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiToken}`,
    },
    body: JSON.stringify({ query, variables }),
  }, 10000)
  const data = await res.json()
  if (!res.ok || data?.errors?.length) {
    const message = data?.errors?.map(item => item.message).filter(Boolean).join('; ')
      || `Railway API 请求失败(${res.status})`
    throw new Error(message)
  }
  return data?.data || null
}

async function persistUserToken() {
  const payload = {
    access_token: userAccessToken || '',
    refresh_token: userRefreshToken || '',
    expires_at: String(userTokenExpiresAt || 0),
    updated_at: Date.now(),
  }

  try {
    state.setPref(SPOTIFY_TOKEN_PREF, JSON.stringify(payload))
  } catch (e) {
    console.error('[spotify] 保存 token 失败:', e.message)
  }

  const { projectId, serviceId, environmentId, apiToken } = getRailwayTokenContext()
  console.log('[spotify] Railway API 上下文:', {
    hasRailwayApiToken: !!process.env.RAILWAY_API_TOKEN,
    hasRailwayProjectId: !!process.env.RAILWAY_PROJECT_ID,
    hasRailwayServiceId: !!process.env.RAILWAY_SERVICE_ID,
    hasRailwayEnvironmentId: !!process.env.RAILWAY_ENVIRONMENT_ID,
  })
  if (!apiToken || !projectId || !serviceId || !environmentId) {
    console.warn('[spotify] 未配置完整 Railway API 上下文，跳过环境变量持久化')
    return false
  }

  await railwayGraphqlRequest(
    `mutation VariableCollectionUpsert(
      $projectId: String!,
      $environmentId: String!,
      $serviceId: String!,
      $variables: EnvironmentVariables!
    ) {
      variableCollectionUpsert(
        input: {
          projectId: $projectId,
          environmentId: $environmentId,
          serviceId: $serviceId,
          variables: $variables,
          replace: false,
          skipDeploys: true
        }
      )
    }`,
    {
      projectId,
      environmentId,
      serviceId,
      variables: {
        SPOTIFY_ACCESS_TOKEN: payload.access_token,
        SPOTIFY_REFRESH_TOKEN: payload.refresh_token,
        SPOTIFY_TOKEN_EXPIRES_AT: payload.expires_at,
      },
    }
  )

  process.env.SPOTIFY_ACCESS_TOKEN = payload.access_token
  process.env.SPOTIFY_REFRESH_TOKEN = payload.refresh_token
  process.env.SPOTIFY_TOKEN_EXPIRES_AT = payload.expires_at
  return true
}

async function clearUserToken() {
  userAccessToken = null
  userRefreshToken = null
  userTokenExpiresAt = 0
  tokenInitPromise = null
  userPlaylistsCache = { items: [], fetchedAt: 0 }
  playlistTracksCache.clear()
  playlistRotationIds = []
  playlistRotationIndex = 0

  try {
    state.setPref(SPOTIFY_TOKEN_PREF, JSON.stringify({
      access_token: '',
      refresh_token: '',
      expires_at: '0',
      updated_at: Date.now(),
    }))
  } catch (e) {
    console.error('[spotify] 清除本地 token 失败:', e.message)
  }

  process.env.SPOTIFY_ACCESS_TOKEN = ''
  process.env.SPOTIFY_REFRESH_TOKEN = ''
  process.env.SPOTIFY_TOKEN_EXPIRES_AT = '0'

  try {
    await persistUserToken()
  } catch (e) {
    console.error('[spotify] 清除远端 token 失败:', e.message)
  }
}

loadPersistedUserToken()

async function initializeUserToken() {
  if (tokenInitPromise) return tokenInitPromise
  tokenInitPromise = (async () => {
    loadPersistedUserToken()
    if (!userRefreshToken && !userAccessToken) return null
    if (userAccessToken && userTokenExpiresAt > Date.now() + 30000) {
      console.log('[spotify] 已从环境变量恢复 access token')
      return userAccessToken
    }
    if (userRefreshToken) {
      try {
        const refreshed = await refreshUserToken()
        console.log('[spotify] 已使用 refresh token 恢复 access token')
        return refreshed
      } catch (e) {
        console.error('[spotify] 启动时刷新 token 失败:', e.message)
        return null
      }
    }
    return null
  })()
  return tokenInitPromise
}

function normalizeSpotifyText(text) {
  return normalizeCompareText(text, { preserveSpaces: true })
}

function normalizeSpotifyTitle(text) {
  return normalizeSongKey(stripTitleNoise(text))
}

function buildStructuredQueries(song) {
  const titles = buildTitleVariants(song)
  const artists = buildArtistVariants(song)
  const queries = []

  for (const title of titles.slice(0, 4)) {
    for (const artist of artists.slice(0, 4)) {
      queries.push(`track:"${title}" artist:"${artist}"`)
      if (queries.length >= 8) return queries
    }
  }

  return queries
}

function buildLooseTitleQueries(song) {
  return buildTitleVariants(song).slice(0, 6)
}

async function runSpotifySearch(query, retries = 2) {
  const token = await getClientCredToken()
  const q = encodeURIComponent(query)
  for (let attempt = 0; attempt <= retries; attempt++) {
    const res = await fetchJsonWithTimeout(
      `https://api.spotify.com/v1/search?q=${q}&type=track&limit=5&market=TW`,
      { headers: { Authorization: `Bearer ${token}` } }
    )
    if (res.status === 429) {
      const retryAfter = parseInt(res.headers.get('retry-after') || '1', 10)
      if (retryAfter > 60) {
        console.warn(`[spotify] 429 限流，retry-after=${retryAfter}s 超出上限，直接跳过`)
        return []
      }
      const wait = retryAfter * 1000
      console.warn(`[spotify] 429 限流，等待 ${wait}ms 后重试 (${attempt + 1}/${retries})`)
      if (attempt < retries) {
        await new Promise(r => setTimeout(r, wait))
        continue
      }
      return []
    }
    const data = await res.json()
    return data?.tracks?.items || []
  }
  return []
}

function scoreSpotifyTrack(track, song, options = {}) {
  const titleScore = titleMatchScore(buildTitleVariants(song), track?.name)
  if (titleScore < 72) return null

  const hasBadTitle = SPOTIFY_BAD_TITLE_KWS.some(kw => normalizeSpotifyText(track?.name).includes(kw))
  if (hasBadTitle && titleScore < 100) return null

  const artists = (track?.artists || []).map(a => normalizeBaseText(a.name)).filter(Boolean)
  const artistScore = artistMatchScore(buildArtistVariants(song), artists)
  if (artistScore === 0 && !(options.allowExactTitleWithoutArtist && titleScore === 100)) {
    return null
  }

  return {
    track,
    score: titleScore * 2 + artistScore - (hasBadTitle ? 24 : 0),
  }
}

// ── Client Credentials Token（搜索用）───────────────────────────
async function getClientCredToken() {
  if (clientCredToken && clientCredToken.expiresAt > Date.now() + 30000) {
    return clientCredToken.access_token
  }
  const res = await fetchJsonWithTimeout('https://accounts.spotify.com/api/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Authorization': 'Basic ' + Buffer.from(`${CLIENT_ID}:${CLIENT_SECRET}`).toString('base64'),
    },
    body: 'grant_type=client_credentials',
  })
  const data = await res.json()
  if (!data.access_token) throw new Error('Spotify client credentials failed: ' + JSON.stringify(data))
  clientCredToken = {
    access_token: data.access_token,
    expiresAt: Date.now() + (data.expires_in - 60) * 1000,
  }
  return clientCredToken.access_token
}

// ── Authorization URL（引导用户授权）────────────────────────────
function getAuthUrl(state = '') {
  const scopes = [
    'playlist-read-private',
    'playlist-read-collaborative',
    'streaming',
    'user-read-email',
    'user-read-private',
    'user-read-playback-state',
    'user-modify-playback-state',
  ].join(' ')
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: CLIENT_ID,
    scope: scopes,
    redirect_uri: REDIRECT_URI,
    state,
  })
  return `https://accounts.spotify.com/authorize?${params}`
}

// ── 用 code 换 token ─────────────────────────────────────────────
async function exchangeCode(code) {
  const res = await fetchJsonWithTimeout('https://accounts.spotify.com/api/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Authorization': 'Basic ' + Buffer.from(`${CLIENT_ID}:${CLIENT_SECRET}`).toString('base64'),
    },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      redirect_uri: REDIRECT_URI,
    }),
  })
  const data = await res.json()
  if (!data.access_token) throw new Error('Spotify exchange failed: ' + JSON.stringify(data))
  userAccessToken = data.access_token
  userRefreshToken = data.refresh_token
  userTokenExpiresAt = Date.now() + (data.expires_in - 60) * 1000
  await persistUserToken()
  return data
}

// ── 刷新 User Token ──────────────────────────────────────────────
async function refreshUserToken() {
  if (!userRefreshToken) throw new Error('No refresh token')
  const res = await fetchJsonWithTimeout('https://accounts.spotify.com/api/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Authorization': 'Basic ' + Buffer.from(`${CLIENT_ID}:${CLIENT_SECRET}`).toString('base64'),
    },
    body: new URLSearchParams({
      grant_type: 'refresh_token',
      refresh_token: userRefreshToken,
    }),
  })
  const data = await res.json()
  if (!data.access_token) throw new Error('Spotify refresh failed: ' + JSON.stringify(data))
  userAccessToken = data.access_token
  userTokenExpiresAt = Date.now() + (data.expires_in - 60) * 1000
  if (data.refresh_token) userRefreshToken = data.refresh_token
  await persistUserToken()
  return userAccessToken
}

// ── 获取有效的 User Token ────────────────────────────────────────
async function getUserToken() {
  if (!userAccessToken && !userRefreshToken) return null
  if (Date.now() > userTokenExpiresAt) {
    try { await refreshUserToken() } catch { return null }
  }
  if (!userAccessToken && userRefreshToken) {
    try { return await refreshUserToken() } catch { return null }
  }
  return userAccessToken
}

function hasUserToken() {
  return !!userAccessToken || !!userRefreshToken
}

const CURATED_PLAYLIST_IDS = [
  { id: process.env.SPOTIFY_PLAYLIST_MORNING, name: '清晨' },
  { id: process.env.SPOTIFY_PLAYLIST_DAY,     name: '白天' },
  { id: process.env.SPOTIFY_PLAYLIST_NIGHT,   name: '夜晚' },
].filter(p => p.id)

async function getUserPlaylists(options = {}) {
  const forceRefresh = !!options.forceRefresh
  if (!forceRefresh && userPlaylistsCache.fetchedAt > Date.now() - USER_PLAYLIST_CACHE_MS) {
    return userPlaylistsCache.items.slice()
  }

  let playlists = []

  if (CURATED_PLAYLIST_IDS.length > 0) {
    // 优先读三个固定策划歌单，直接用 Playlist API 获取元信息
    const results = await Promise.allSettled(
      CURATED_PLAYLIST_IDS.map(({ id, name }) =>
        spotifyUserJson(`https://api.spotify.com/v1/playlists/${encodeURIComponent(id)}?fields=id,name,tracks(total)`)
          .then(data => ({
            id: data?.id || id,
            name: data?.name || name,
            tracksTotal: data?.tracks?.total || 0,
          }))
          .catch(() => ({ id, name, tracksTotal: 1 })) // 即便拿不到元信息也保留ID
      )
    )
    playlists = results
      .filter(r => r.status === 'fulfilled')
      .map(r => r.value)
      .filter(p => p.id)
    console.log(`[spotify] 策划歌单加载: ${playlists.map(p => `${p.name}(${p.tracksTotal}首)`).join(', ')}`)
  } else {
    // fallback：从账号拉全量歌单
    console.log('[spotify] 未配置策划歌单，回退到 /me/playlists')
    const items = await paginateSpotifyUserItems(
      'https://api.spotify.com/v1/me/playlists?limit=50',
      'items'
    )
    playlists = items
      .filter(item => item?.id && item?.tracks?.total)
      .map(item => ({
        id: item.id,
        name: item.name || '',
        tracksTotal: item.tracks?.total || 0,
      }))
  }

  userPlaylistsCache = {
    items: playlists,
    fetchedAt: Date.now(),
  }
  syncPlaylistRotation(playlists)
  return playlists.slice()
}

function getPlaylistCacheTrackCount() {
  let total = 0
  for (const cached of playlistTracksCache.values()) {
    total += Array.isArray(cached?.items) ? cached.items.length : 0
  }
  return total
}

async function getPlaylistTracks(playlistId, options = {}) {
  const forceRefresh = !!options.forceRefresh
  const cached = playlistTracksCache.get(playlistId)
  if (!forceRefresh && cached && cached.fetchedAt > Date.now() - USER_PLAYLIST_TRACKS_CACHE_MS) {
    return cached.items.slice()
  }

  const items = await paginateSpotifyUserItems(
    `https://api.spotify.com/v1/playlists/${encodeURIComponent(playlistId)}/tracks?limit=100&fields=items(is_local,track(id,uri,name,is_local,is_playable,artists(name),album(name))),next`,
    'items'
  )

  playlistTracksCache.set(playlistId, {
    items,
    fetchedAt: Date.now(),
  })
  return items.slice()
}

async function getPlaylistQueueItems(options = {}) {
  const limit = Math.max(1, Number(options.limit) || 1)
  const includeMeta = options.includeMeta === true
  const excludeUris = new Set(Array.isArray(options.excludeUris) ? options.excludeUris.filter(Boolean) : [])
  const blacklistedUris = new Set(Array.isArray(options.blacklistedUris) ? options.blacklistedUris.filter(Boolean) : [])
  const excludeKeys = new Set(Array.isArray(options.excludeKeys) ? options.excludeKeys.map(key => String(key).toLowerCase()) : [])
  let totalTracksLoaded = 0
  const meta = {
    cachedTrackCount: getPlaylistCacheTrackCount(),
    blacklistSkipped: 0,
    freshPlaylistFetchAttempted: false,
  }
  console.log('[spotify] getPlaylistQueueItems start:', {
    hasUserAccessToken: !!userAccessToken,
  })
  const playlists = await getUserPlaylists(options)
  console.log('[spotify] getPlaylistQueueItems playlists fetched:', playlists.length)
  meta.cachedTrackCount = getPlaylistCacheTrackCount()
  if (!playlists.length) {
    console.log('[spotify] getPlaylistQueueItems total tracks loaded:', totalTracksLoaded)
    return includeMeta ? { items: [], meta } : []
  }

  const orderedPlaylists = nextRotatedPlaylists(playlists)
  const queueItems = []

  for (const playlist of orderedPlaylists) {
    const hadFreshPlaylistCache = playlistTracksCache.has(playlist.id)
    const rawTracks = await getPlaylistTracks(playlist.id, options)
    totalTracksLoaded += rawTracks.length
    if (!!options.forceRefresh || !hadFreshPlaylistCache) {
      meta.freshPlaylistFetchAttempted = true
      meta.cachedTrackCount = getPlaylistCacheTrackCount()
    }
    const normalizedTracks = shuffle(rawTracks)
      .map(item => normalizePlaylistTrackItem(item, playlist))
      .filter(Boolean)

    for (const item of normalizedTracks) {
      const uri = item.spotify_uri
      const key = `${item.song_info.name}::${item.song_info.artist}`.toLowerCase()
      if (!uri) continue
      if (blacklistedUris.has(uri)) {
        meta.blacklistSkipped += 1
      }
      if (excludeUris.has(uri)) {
        continue
      }
      if (excludeKeys.has(key)) continue
      excludeUris.add(uri)
      excludeKeys.add(key)
      queueItems.push(item)
      if (queueItems.length >= limit) {
        console.log('[spotify] getPlaylistQueueItems total tracks loaded:', totalTracksLoaded)
        return includeMeta ? { items: queueItems, meta } : queueItems
      }
    }
  }

  console.log('[spotify] getPlaylistQueueItems total tracks loaded:', totalTracksLoaded)
  return includeMeta ? { items: queueItems, meta } : queueItems
}

// ── 搜索曲目，返回 Spotify Track ID ─────────────────────────────
async function searchTrack(songOrName, artist) {
  const song = makeSongSearchProfile(songOrName, artist)
  const cacheKey = `${song.name || ''}::${song.artist || ''}`
  if (searchTrackCache.has(cacheKey)) {
    return searchTrackCache.get(cacheKey)
  }

  for (const query of buildStructuredQueries(song)) {
    const tracks = await runSpotifySearch(query)
    if (!tracks.length) continue

    const best = tracks
      .map(track => scoreSpotifyTrack(track, song, { allowExactTitleWithoutArtist: true }))
      .filter(Boolean)
      .sort((a, b) => b.score - a.score)[0]

    if (best?.track) {
      const result = {
        uri: best.track.uri || null,
        id: best.track.id || null,
        name: best.track.name || song.name,
        artists: (best.track.artists || []).map(a => a.name).filter(Boolean),
        album: best.track.album?.name || null,
      }
      searchTrackCache.set(cacheKey, result)
      return result
    }
  }

  for (const query of buildLooseTitleQueries(song)) {
    const tracks = await runSpotifySearch(query)
    if (!tracks.length) continue

    const best = tracks
      .map(track => scoreSpotifyTrack(track, song, { allowExactTitleWithoutArtist: true }))
      .filter(Boolean)
      .sort((a, b) => b.score - a.score)[0]

    if (best?.track) {
      const result = {
        uri: best.track.uri || null,
        id: best.track.id || null,
        name: best.track.name || song.name,
        artists: (best.track.artists || []).map(a => a.name).filter(Boolean),
        album: best.track.album?.name || null,
      }
      searchTrackCache.set(cacheKey, result)
      return result
    }
  }

  searchTrackCache.set(cacheKey, null)
  return null
}

// ── 批量搜索，返回 { name, artist, uri } 列表 ───────────────────
async function resolveSpotifyUris(songs) {
  const results = await Promise.all(
    songs.map(async song => {
      try {
        const match = await searchTrack(song)
        if (!match?.uri) return null
        return {
          song_info: {
            ...song,
            id: match.id || song.id || null,
            name: match.name || song.name,
            artist: match.artists?.length ? match.artists.join('; ') : song.artist,
          },
          spotify_uri: match.uri,
          spotify_track: match,
        }
      } catch (e) {
        console.error(`[spotify] 搜索失败 "${song.name}":`, e.message)
        return null
      }
    })
  )
  return results.filter(Boolean)
}

module.exports = {
  clearUserToken,
  getAuthUrl,
  exchangeCode,
  getPlaylistQueueItems,
  getPlaylistTracks,
  getUserPlaylists,
  getUserToken,
  hasUserToken,
  initializeUserToken,
  refreshUserToken,
  resolveSpotifyUris,
  searchTrack,
  getClientCredToken,
}
