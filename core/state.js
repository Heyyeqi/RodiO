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

    -- Housekeeping
    created_at             TEXT DEFAULT (datetime('now')),
    updated_at             TEXT DEFAULT (datetime('now'))
  );

  CREATE INDEX IF NOT EXISTS idx_tp_genre_family   ON track_profile(genre_family);
  CREATE INDEX IF NOT EXISTS idx_tp_language       ON track_profile(language);
  CREATE INDEX IF NOT EXISTS idx_tp_energy         ON track_profile(energy);
  CREATE INDEX IF NOT EXISTS idx_tp_label_source   ON track_profile(label_source);
`)

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

module.exports = {
  getRecentMessages,
  addMessage,
  addPlay,
  getRecentPlays,
  clearPlays,
  getPref,
  setPref,
  setSongFeedback,
  getSongFeedback,
  getFeedbackByType,
}
