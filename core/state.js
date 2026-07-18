const Database = require('better-sqlite3')
const path = require('path')
const fs = require('fs')

const dbDir = path.join(__dirname, '../db')
if (!fs.existsSync(dbDir)) fs.mkdirSync(dbDir, { recursive: true })
const db = new Database(path.join(dbDir, 'state.db'))

db.exec(`
  CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT,
    content TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS plays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id TEXT,
    song_name TEXT,
    artist TEXT,
    played_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    mood TEXT
  );

  CREATE TABLE IF NOT EXISTS prefs (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS song_feedback (
    song_key TEXT PRIMARY KEY,
    song_id TEXT,
    song_name TEXT,
    artist TEXT,
    feedback TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );

  -- ── Phase 1: track_profile label schema ────────────────────────────────
  -- One row per unique canonical track.  All fields exactly match the
  -- design doc Section 4 "track_profile 标签体系" — no reduction, no
  -- invention.  JSON-serialised compound fields (arrays / scene_fit) have
  -- the column name suffixed _json for clarity in the SQL layer.
  CREATE TABLE IF NOT EXISTS track_profile (
    -- Identity keys
    track_key              TEXT PRIMARY KEY,   -- "normalized_name::normalized_artist"
    spotify_uri            TEXT,
    ncm_id                 TEXT,

    -- Canonical metadata
    canonical_title        TEXT,
    canonical_artist       TEXT,
    album                  TEXT,
    duration_ms            INTEGER,
    source_playlist_json   TEXT,               -- JSON array of playlist ids
    first_seen_at          TEXT,
    last_played_at         TEXT,

    -- Behavioural counters
    play_count             INTEGER DEFAULT 0,
    skip_count             INTEGER DEFAULT 0,
    complete_count         INTEGER DEFAULT 0,
    like_count             INTEGER DEFAULT 0,
    dislike_count          INTEGER DEFAULT 0,
    candidate_exposure_count  INTEGER DEFAULT 0,
    candidate_rejected_count  INTEGER DEFAULT 0,

    -- Playability
    validated_playable     INTEGER DEFAULT 0,  -- boolean
    playability_checked_at TEXT,

    -- Objective tags (Section 4 table: "客观标签")
    language               TEXT,               -- zh / ja / en / instrumental
    era                    INTEGER,
    has_vocal              INTEGER,            -- boolean
    vocal_gender_guess     TEXT,               -- female / male / group / none
    instrumental_ratio     REAL,
    genre_family           TEXT,               -- art_pop / lo_fi / ambient / ...

    -- Acoustic / somatic tags (Section 4 table: "声学/体感标签")
    energy                 REAL,               -- 0.0 – 1.0
    brightness             REAL,
    density                REAL,
    warmth                 REAL,
    rhythmic_motion        REAL,
    vocal_presence         REAL,
    emotional_weight       REAL,

    -- Aesthetic semantic tags (Section 4 table: "审美语义标签")
    mood_tags_json         TEXT,               -- JSON array, max 3 from fixed vocab
    texture_tags_json      TEXT,               -- JSON array, max 4 from fixed vocab
    negative_tags_json     TEXT,               -- JSON array, served for avoidance

    -- Scene fit (Section 4 table: "场景适配")
    scene_fit_json         TEXT,               -- JSON object, scene_id → score (0-1)

    -- Memory / confidence
    memory_recall_eligible INTEGER DEFAULT 0,
    label_confidence       REAL,
    label_version          TEXT,
    label_source           TEXT,
    sequence_shape         TEXT,               -- LLM labeling: circular/repetitive/linear/...

    -- Housekeeping
    created_at             TEXT DEFAULT (datetime('now')),
    updated_at             TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS play_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL CHECK(event_type IN ('skip','complete','replay')),
    track_key TEXT NOT NULL,
    played_seconds REAL NOT NULL,
    duration_seconds REAL NOT NULL,
    played_ratio REAL NOT NULL,
    user_active INTEGER NOT NULL DEFAULT 0,
    scene_id TEXT,
    prev_track_key TEXT,
    context_snapshot TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
  );

  CREATE INDEX IF NOT EXISTS idx_tp_genre_family   ON track_profile(genre_family);
  CREATE INDEX IF NOT EXISTS idx_tp_language       ON track_profile(language);
  CREATE INDEX IF NOT EXISTS idx_tp_energy         ON track_profile(energy);
  CREATE INDEX IF NOT EXISTS idx_tp_label_source   ON track_profile(label_source);

  -- ── Phase 1 step 5: shadow mode 召回观测日志 ──────────────────────────
  -- 记录路径B真实补货与影子候选计算的对比，纯观测，不影响真实队列。
  CREATE TABLE IF NOT EXISTS shadow_recall_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reason TEXT,
    real_count INTEGER,
    shadow_candidate_count INTEGER,
    overlap_count INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
  );
`)

// ── Phase 2 Step 1: 影子 Mood Intent 日志表（纯观测）────────────────────
db.exec(`
  CREATE TABLE IF NOT EXISTS shadow_mood_intent_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reason TEXT,
    valid INTEGER NOT NULL,
    fallback_reason TEXT,
    intent_json TEXT,
    raw_response TEXT,
    tonality_intensity REAL,
    tonality_warmth REAL,
    latency_ms INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
  );
`)

// ── sequence_shape 迁移：track_profile 补回遗漏的 LLM 标注字段 ────
// 建表语句从 Phase 1 起遗漏，4 批 CSV 中均有此行数据但 DB 未写入，
// 后续由 backfill 脚本从 CSV 回填。
try {
  const tpCols = db.prepare('PRAGMA table_info(track_profile)').all().map(c => c.name)
  if (!tpCols.includes('sequence_shape')) {
    db.prepare('ALTER TABLE track_profile ADD COLUMN sequence_shape TEXT').run()
  }
} catch (e) {
  if (!/duplicate column/i.test(e.message)) throw e
}

// ── Phase 1 step 4: play_events.transition_cost 迁移 ──────────────────────
// play_events 表已存在（含历史测试数据），CREATE TABLE IF NOT EXISTS 无法加列，
// 故用 PRAGMA 检查 + ALTER TABLE 迁移；重复启动忽略 "duplicate column" 报错。
try {
  const cols = db.prepare('PRAGMA table_info(play_events)').all().map(c => c.name)
  if (!cols.includes('transition_cost')) {
    db.prepare('ALTER TABLE play_events ADD COLUMN transition_cost REAL').run()
  }
} catch (e) {
  // 列已存在等可忽略错误，保证重复启动不崩溃
  if (!/duplicate column/i.test(e.message)) throw e
}

// ── feedback score 迁移：song_feedback.score / score_updated_at ──────────
// song_feedback 表已存在（含历史数据），CREATE TABLE IF NOT EXISTS 无法加列，
// 故用 PRAGMA 检查 + ALTER TABLE 迁移；重复启动忽略 "duplicate column" 报错。
try {
  const fbCols = db.prepare('PRAGMA table_info(song_feedback)').all().map(c => c.name)
  if (!fbCols.includes('score')) {
    db.prepare('ALTER TABLE song_feedback ADD COLUMN score REAL DEFAULT 0').run()
  }
  if (!fbCols.includes('score_updated_at')) {
    db.prepare('ALTER TABLE song_feedback ADD COLUMN score_updated_at TEXT').run()
  }
} catch (e) {
  // 列已存在等可忽略错误，保证重复启动不崩溃
  if (!/duplicate column/i.test(e.message)) throw e
}

// ── shadow_rerank_candidates 表迁移（Phase 1 step 6 候选打分影子日志）──
// 纯观测表，记录候选打分四维度与混合分，不影响真实选曲。
try {
  db.exec(`
    CREATE TABLE IF NOT EXISTS shadow_rerank_candidates (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      reason TEXT,
      track_key TEXT,
      freshness_raw_days REAL,
      continuity_raw_cost REAL,
      feedback_raw_score REAL,
      feedback_excluded INTEGER,
      playability_ever_played INTEGER,
      blended_score REAL,
      created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
  `)
} catch (e) {
  // 表已存在等可忽略错误，保证重复启动不崩溃
  if (!/already exists/i.test(e.message)) throw e
}

// ── commentary_history 表（v1.3 天外来信持久化）──
// 记录每次 /api/explain 生成的 commentary 文本及当时的歌曲/天气/主题上下文。
try {
  db.exec(`
    CREATE TABLE IF NOT EXISTS commentary_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      text TEXT NOT NULL,
      song_name TEXT,
      song_artist TEXT,
      weather_text TEXT,
      theme_name TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
  `)
} catch (e) {
  if (!/already exists/i.test(e.message)) throw e
}

// v1.4: 兼容已存在的旧表，追加两列调性分数（重复列错误静默忽略）
try {
  db.exec(`ALTER TABLE commentary_history ADD COLUMN intensity_score REAL DEFAULT 0;`)
} catch (e) {
  if (!/duplicate column/i.test(e.message)) throw e
}
try {
  db.exec(`ALTER TABLE commentary_history ADD COLUMN warmth_score REAL DEFAULT 0;`)
} catch (e) {
  if (!/duplicate column/i.test(e.message)) throw e
}

// ── skip_penalties 分层半衰期惩罚表 ──────────────────────────────────
// 每行只存一个维度：track_key / artist_key / tag / scene_id 四选一非空
db.exec(`
  CREATE TABLE IF NOT EXISTS skip_penalties (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    track_key     TEXT,
    artist_key    TEXT,
    tag           TEXT,
    scene_id      TEXT,
    penalty       REAL DEFAULT 0,
    half_life_days INTEGER DEFAULT 14,
    updated_at    TEXT DEFAULT (datetime('now'))
  );
`)
// 清空可能已有的旧格式脏数据（旧结构一行塞了多个字段）
db.exec(`DELETE FROM skip_penalties`)

// ── discovery_candidates 三表发现管线 ─────────────────────────────────
// discovery_candidates: 新发现候选池，待验证，不直接播放
db.exec(`
  CREATE TABLE IF NOT EXISTS discovery_candidates (
    track_key     TEXT PRIMARY KEY,
    source        TEXT,
    added_at      TEXT DEFAULT (datetime('now')),
    validation_plays  INTEGER DEFAULT 0,
    validation_ok      INTEGER DEFAULT 0,
    early_skip_count   INTEGER DEFAULT 0,
    scene_ids_json     TEXT DEFAULT '[]'
  );
`)

// validated_tracks: 已验证可播放、已打标签，可进入播放
db.exec(`
  CREATE TABLE IF NOT EXISTS validated_tracks (
    track_key    TEXT PRIMARY KEY,
    validated_at TEXT DEFAULT (datetime('now')),
    source       TEXT
  );
`)

// ── 分层半衰期常数 ────────────────────────────────────────────────────
const SKIP_HALF_LIFE_TRACK = 14
const SKIP_HALF_LIFE_TAG   = 30
const SKIP_HALF_LIFE_ARTIST = 60
const SKIP_HALF_LIFE_SCENE = 14

// 半衰期天数：180 天衰减一半
const SCORE_HALF_LIFE_DAYS = 180

// 按半衰期公式衰减当前分数
// score 或 score_updated_at 为 null 时当作 0 处理
function decayScore(score, scoreUpdatedAt, now = new Date()) {
  if (score === null || score === undefined || scoreUpdatedAt === null || scoreUpdatedAt === undefined) {
    return 0
  }
  const updated = new Date(scoreUpdatedAt)
  if (isNaN(updated.getTime())) return 0
  const daysDiff = (now.getTime() - updated.getTime()) / (1000 * 60 * 60 * 24)
  if (daysDiff <= 0) return score // 未来时间或当天，不衰减
  return score * Math.pow(0.5, daysDiff / SCORE_HALF_LIFE_DAYS)
}

// 累加式反馈分数调整（带半衰期衰减）
// delta: dislike 传 -1，like 传 +1
// 与 setSongFeedback 解耦：行不存在时自动 INSERT（保证分数可独立累加）
function adjustSongFeedbackScore(song, delta) {
  const songKey = makeSongKey(song)
  const now = new Date()
  const nowIso = now.toISOString()
  const row = db.prepare(
    'SELECT score, score_updated_at FROM song_feedback WHERE song_key = ?'
  ).get(songKey)
  const decayed = row ? decayScore(row.score, row.score_updated_at, now) : 0
  const newScore = Math.round((decayed + (delta || 0)) * 1e6) / 1e6
  if (row) {
    db.prepare(`
      UPDATE song_feedback SET score = ?, score_updated_at = ? WHERE song_key = ?
    `).run(newScore, nowIso, songKey)
  } else {
    // 行不存在：插入最小可用行（song_id/name/artist 留空，由 setSongFeedback 补全）
    db.prepare(`
      INSERT INTO song_feedback (song_key, song_id, song_name, artist, feedback, score, score_updated_at)
      VALUES (?, NULL, NULL, NULL, NULL, ?, ?)
    `).run(songKey, newScore, nowIso)
  }
  return newScore
}

// 只读：返回当前衰减后的分数（不修改数据）
function getSongFeedbackScore(song) {
  const songKey = makeSongKey(song)
  const row = db.prepare(
    'SELECT score, score_updated_at FROM song_feedback WHERE song_key = ?'
  ).get(songKey)
  if (!row) return 0
  return decayScore(row.score, row.score_updated_at)
}

function getRecentMessages(n = 10) {
  return db.prepare(
    'SELECT role, content FROM messages ORDER BY id DESC LIMIT ?'
  ).all(n).reverse()
}

function addMessage(role, content) {
  db.prepare('INSERT INTO messages (role, content) VALUES (?, ?)').run(role, content)
}

function addPlay(song) {
  db.prepare(
    'INSERT INTO plays (song_id, song_name, artist, mood) VALUES (?, ?, ?, ?)'
  ).run(song.id, song.name, song.artist, song.mood || null)
}

function getRecentPlays(n = 10) {
  return db.prepare(
    'SELECT song_id, song_name, artist, mood, played_at FROM plays ORDER BY id DESC LIMIT ?'
  ).all(n)
}

function clearPlays() {
  db.prepare('DELETE FROM plays').run()
}

function getPref(key) {
  const row = db.prepare('SELECT value FROM prefs WHERE key = ?').get(key)
  return row ? row.value : null
}

function setPref(key, value) {
  db.prepare(
    'INSERT INTO prefs (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP'
  ).run(key, value)
}

function makeSongKey(song) {
  return `${String(song.name || '').trim().toLowerCase()}::${String(song.artist || '').trim().toLowerCase()}`
}

function setSongFeedback(song, feedback) {
  const songKey = makeSongKey(song)
  db.prepare(`
    INSERT INTO song_feedback (song_key, song_id, song_name, artist, feedback)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(song_key) DO UPDATE SET
      song_id=excluded.song_id,
      song_name=excluded.song_name,
      artist=excluded.artist,
      feedback=excluded.feedback,
      updated_at=CURRENT_TIMESTAMP
  `).run(songKey, song.id || null, song.name, song.artist, feedback)
}

function getSongFeedback(song) {
  const songKey = makeSongKey(song)
  return db.prepare(
    'SELECT song_id, song_name, artist, feedback, updated_at FROM song_feedback WHERE song_key = ?'
  ).get(songKey) || null
}

function getFeedbackByType(feedback, limit = 50) {
  return db.prepare(
    'SELECT song_id, song_name, artist, feedback, updated_at FROM song_feedback WHERE feedback = ? ORDER BY updated_at DESC LIMIT ?'
  ).all(feedback, limit)
}

function insertPlayEvent(event) {
  const {
    track_key,
    event_type,
    prev_track_key = null,
    transition_cost = null,
    context_snapshot = null,
    created_at = null,
  } = event || {}
  db.prepare(`
    INSERT INTO play_events (event_type, track_key, played_seconds, duration_seconds, played_ratio, user_active, scene_id, prev_track_key, transition_cost, context_snapshot, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    event_type,
    track_key,
    event.played_seconds || 0,
    event.duration_seconds || 0,
    event.played_ratio || 0,
    event.user_active ? 1 : 0,
    event.scene_id || null,
    prev_track_key || null,
    transition_cost === null || transition_cost === undefined ? null : transition_cost,
    context_snapshot || null,
    created_at || new Date().toISOString()
  )
}

// Phase 1 step 4: 读取 track_profile 一行（按 track_key 主键），无则返回 null
function getTrackProfile(trackKey) {
  if (!trackKey) return null
  return db.prepare(
    'SELECT track_key, energy, brightness, density, vocal_presence, emotional_weight, rhythmic_motion, mood_tags_json, texture_tags_json FROM track_profile WHERE track_key = ?'
  ).get(trackKey) || null
}

// Phase 1 step 5: 读取 track_profile 全部行（影子召回候选来源）
function getAllTrackProfiles() {
  return db.prepare(
    'SELECT track_key, energy, brightness, density, vocal_presence, emotional_weight, rhythmic_motion FROM track_profile'
  ).all()
}

// Phase 1 step 5: 写入 shadow_recall_log 一条观测记录
function insertShadowRecallLog(reason, realCount, shadowCandidateCount, overlapCount) {
  db.prepare(`
    INSERT INTO shadow_recall_log (reason, real_count, shadow_candidate_count, overlap_count)
    VALUES (?, ?, ?, ?)
  `).run(reason || null, realCount || 0, shadowCandidateCount || 0, overlapCount || 0)
}

// Phase 2 Step 1: 写入 shadow_mood_intent_log 一条观测记录
function insertShadowMoodIntentLog(row) {
  db.prepare(`
    INSERT INTO shadow_mood_intent_log
      (reason, valid, fallback_reason, intent_json, raw_response,
       tonality_intensity, tonality_warmth, latency_ms)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    row.reason || null,
    row.valid != null ? row.valid : 0,
    row.fallback_reason || null,
    row.intent_json || null,
    row.raw_response || null,
    row.tonality_intensity != null ? row.tonality_intensity : null,
    row.tonality_warmth != null ? row.tonality_warmth : null,
    row.latency_ms != null ? row.latency_ms : null
  )
}

// Phase 2 Step 1: 读取最近 N 条影子 Mood Intent 日志
function getRecentShadowMoodIntentLogs(limit = 50) {
  return db.prepare(`
    SELECT * FROM shadow_mood_intent_log ORDER BY id DESC LIMIT ?
  `).all(limit)
}

// Phase 1 step 6: 读取某 track_key 最近一次播放时间（play_events.MAX(timestamp)）
function getLastPlayAt(trackKey) {
  if (!trackKey) return null
  const row = db.prepare(
    'SELECT MAX(timestamp) AS last_at FROM play_events WHERE track_key = ?'
  ).get(trackKey)
  return row && row.last_at ? row.last_at : null
}

// Phase 1 step 6: 判断某 track_key 是否在 play_events 中至少出现过一次
function hasPlayEvent(trackKey) {
  if (!trackKey) return false
  const row = db.prepare(
    'SELECT 1 AS exists_flag FROM play_events WHERE track_key = ? LIMIT 1'
  ).get(trackKey)
  return !!row
}

// Phase 1 step 6: 写入 shadow_rerank_candidates 一行候选打分观测
function insertShadowRerankCandidate(row) {
  const {
    reason = null,
    track_key = null,
    freshness_raw_days = null,
    continuity_raw_cost = null,
    feedback_raw_score = null,
    feedback_excluded = 0,
    playability_ever_played = 0,
    blended_score = null,
  } = row || {}
  db.prepare(`
    INSERT INTO shadow_rerank_candidates (
      reason, track_key, freshness_raw_days, continuity_raw_cost,
      feedback_raw_score, feedback_excluded, playability_ever_played, blended_score
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    reason,
    track_key,
    freshness_raw_days,
    continuity_raw_cost,
    feedback_raw_score,
    feedback_excluded ? 1 : 0,
    playability_ever_played ? 1 : 0,
    blended_score
  )
}

// v1.4: 写入一条 commentary 历史记录，返回插入后的 id
// intensity_score / warmth_score 为三层叠加引擎合成的调性向量（0~1）
function insertCommentaryHistory({ text, song_name, song_artist, weather_text, theme_name, intensity_score = 0, warmth_score = 0 }) {
  const info = db.prepare(`
    INSERT INTO commentary_history (text, song_name, song_artist, weather_text, theme_name, intensity_score, warmth_score)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `).run(
    text || null,
    song_name || null,
    song_artist || null,
    weather_text || null,
    theme_name || null,
    Number.isFinite(intensity_score) ? intensity_score : 0,
    Number.isFinite(warmth_score) ? warmth_score : 0
  )
  return info.lastInsertRowid
}

// v1.3: 按 created_at 倒序读取最近 limit 条 commentary 历史
function getCommentaryHistory(limit = 50) {
  const rows = db.prepare(`
    SELECT id, text, song_name, song_artist, weather_text, theme_name, intensity_score, warmth_score, created_at
    FROM commentary_history
    ORDER BY created_at DESC, id DESC
    LIMIT ?
  `).all(limit)
  return rows
}

// ── skip_penalty 分层衰减函数 ─────────────────────────────────────────

/** 记录一次 skip 惩罚（track / artist / tag / scene 各存独立行） */
function recordSkipPenalty(trackKey, artistKey, tags, sceneId, penaltyValue) {
  const now = new Date().toISOString()
  const upsert = (dim, halfLife) => {
    const params = dim.track_key ? [dim.track_key, null, null, null, penaltyValue, halfLife, now]
      : dim.artist_key ? [null, dim.artist_key, null, null, penaltyValue, halfLife, now]
      : dim.tag ? [null, null, dim.tag, null, penaltyValue, halfLife, now]
      : dim.scene_id ? [null, null, null, dim.scene_id, penaltyValue, halfLife, now]
      : null
    if (!params) return
    db.prepare(`
      INSERT INTO skip_penalties (track_key, artist_key, tag, scene_id, penalty, half_life_days, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run(...params)
  }
  // track 维度
  if (trackKey) upsert({ track_key: trackKey }, SKIP_HALF_LIFE_TRACK)
  // tag 维度（每个 tag 独立一行）
  if (Array.isArray(tags) && tags.length > 0) {
    for (const tag of tags) {
      upsert({ tag }, SKIP_HALF_LIFE_TAG)
    }
  }
  // artist 维度
  if (artistKey) upsert({ artist_key: artistKey }, SKIP_HALF_LIFE_ARTIST)
  // scene 维度
  if (sceneId) upsert({ scene_id: sceneId }, SKIP_HALF_LIFE_SCENE)
}

/** 查询当前有效的 skip 惩罚（四维度独立衰减后加权求和） */
function getCompositeSkipPenalty(trackKey, artistKey, tags, sceneId) {
  const now = new Date()
  const decay = (penalty, halfLifeDays, updatedAt) => {
    if (!penalty || penalty === 0 || !updatedAt) return 0
    const days = (now.getTime() - new Date(updatedAt).getTime()) / (1000 * 60 * 60 * 24)
    if (days <= 0) return penalty
    return penalty * Math.pow(0.5, days / (halfLifeDays || 14))
  }
  const sumRows = (rows) => {
    let s = 0
    for (const r of rows) {
      s += decay(r.penalty, r.half_life_days, r.updated_at)
    }
    return s
  }
  // 1. track 维度（只有 track_key 非空且匹配）
  const trackRows = trackKey ? db.prepare(`
    SELECT penalty, half_life_days, updated_at FROM skip_penalties
    WHERE track_key = ? AND artist_key IS NULL AND tag IS NULL AND scene_id IS NULL
  `).all(trackKey) : []
  const trackPenalty = sumRows(trackRows)
  // 2. artist 维度
  const artistRows = artistKey ? db.prepare(`
    SELECT penalty, half_life_days, updated_at FROM skip_penalties
    WHERE artist_key = ? AND track_key IS NULL AND tag IS NULL AND scene_id IS NULL
  `).all(artistKey) : []
  const artistPenalty = sumRows(artistRows)
  // 3. tag 维度（每个 tag 独立，求和后乘权重）
  let tagPenalty = 0
  if (Array.isArray(tags) && tags.length > 0) {
    const placeholders = tags.map(() => '?').join(',')
    const tagRows = db.prepare(`
      SELECT penalty, half_life_days, updated_at FROM skip_penalties
      WHERE tag IN (${placeholders}) AND track_key IS NULL AND artist_key IS NULL AND scene_id IS NULL
    `).all(...tags)
    tagPenalty = sumRows(tagRows)
  }
  // 4. scene 维度
  const sceneRows = sceneId ? db.prepare(`
    SELECT penalty, half_life_days, updated_at FROM skip_penalties
    WHERE scene_id = ? AND track_key IS NULL AND artist_key IS NULL AND tag IS NULL
  `).all(sceneId) : []
  const scenePenalty = sumRows(sceneRows)
  const total = trackPenalty + artistPenalty * 0.3 + tagPenalty * 0.5 + scenePenalty
  return Math.round(total * 1e6) / 1e6
}

// ── discovery_candidates 三表管线 ─────────────────────────────────────

/** 将新候选加入 discovery_candidates 池 */
function insertDiscoveryCandidate(trackKey, source) {
  db.prepare(`
    INSERT OR IGNORE INTO discovery_candidates (track_key, source)
    VALUES (?, ?)
  `).run(trackKey, source || null)
}

/** 记录一次验证播放结果，达到条件时自动晋升到 validated_tracks */
function recordValidationPlay(trackKey, playedRatio, earlySkip, sceneId) {
  const row = db.prepare('SELECT * FROM discovery_candidates WHERE track_key = ?').get(trackKey)
  if (!row) return null // 不在发现池中
  const newPlays = (row.validation_plays || 0) + 1
  const newOk = (row.validation_ok || 0) + (playedRatio > 0.7 ? 1 : 0)
  const newEarlySkips = (row.early_skip_count || 0) + (earlySkip ? 1 : 0)
  let sceneIds = JSON.parse(row.scene_ids_json || '[]')
  if (sceneId && !sceneIds.includes(sceneId)) sceneIds.push(sceneId)
  db.prepare(`
    UPDATE discovery_candidates SET
      validation_plays = ?, validation_ok = ?, early_skip_count = ?,
      scene_ids_json = ?
    WHERE track_key = ?
  `).run(newPlays, newOk, newEarlySkips, JSON.stringify(sceneIds), trackKey)
  // 检查晋升条件
  if (newPlays >= 3 && newOk >= 2 && newEarlySkips === 0 && sceneIds.length >= 2) {
    db.prepare('INSERT OR IGNORE INTO validated_tracks (track_key, source) VALUES (?, ?)')
      .run(trackKey, row.source || 'discovery')
    db.prepare('DELETE FROM discovery_candidates WHERE track_key = ?').run(trackKey)
    return 'promoted'
  }
  return null
}

/** 检查 track 是否已通过验证 */
function isValidatedTrack(trackKey) {
  return !!db.prepare('SELECT 1 FROM validated_tracks WHERE track_key = ?').get(trackKey)
}

module.exports = {
  getRecentMessages,
  insertCommentaryHistory,
  getCommentaryHistory,
  addMessage,
  addPlay,
  getRecentPlays,
  clearPlays,
  getPref,
  setPref,
  setSongFeedback,
  getSongFeedback,
  getFeedbackByType,
  adjustSongFeedbackScore,
  getSongFeedbackScore,
  insertPlayEvent,
  getTrackProfile,
  getAllTrackProfiles,
  insertShadowRecallLog,
  getLastPlayAt,
  hasPlayEvent,
  insertShadowRerankCandidate,
  insertShadowMoodIntentLog,
  getRecentShadowMoodIntentLogs,
  recordSkipPenalty,
  getCompositeSkipPenalty,
  insertDiscoveryCandidate,
  recordValidationPlay,
  isValidatedTrack,
}
