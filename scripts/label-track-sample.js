#!/usr/bin/env node
/**
 * label-track-sample.js — Phase 1 Step 2: Label 200 tracks with DeepSeek
 *
 * Usage: DEEPSEEK_API_KEY=sk-xxx node scripts/label-track-sample.js
 *
 * Samples 200 tracks from the full song pool (max 3 per artist),
 * sends each to DeepSeek for labeling against a fixed closed vocabulary,
 * writes results into track_profile (INSERT OR REPLACE), and generates
 * a human-readable review CSV.
 */

const { loadPool } = require('../core/songpool')
const { normalizeSongKey, normalizeArtistKey } = require('../core/search-utils')
const OpenAI = require('openai')
const Database = require('better-sqlite3')
const path = require('path')
const fs = require('fs')

// ── Constants ────────────────────────────────────────────────────────
const SAMPLE_SIZE = 200
const MAX_PER_ARTIST = 3
const MAX_RETRIES = 3
const CONCURRENCY = 3
const LABEL_VERSION = 'v1_2026-07-11'
const LABEL_SOURCE = 'deepseek_sample_batch1'
const ROOT = path.join(__dirname, '..')
const DB_PATH = path.join(ROOT, 'db', 'state.db')
const REVIEW_CSV = path.join(ROOT, 'output', 'track_label_review.csv')

// ── Closed vocabularies ──────────────────────────────────────────────
// Any tag generated outside these sets causes a re-request for that track.

const MOOD_VOCAB = new Set([
  'introspective', 'misty', 'restrained', 'lonely',
  'warm', 'detached', 'melancholic', 'dreamy',
  'sensual', 'clear', 'restless', 'urban',
  'nostalgic', 'hopeful', 'unresolved', 'bittersweet',
])

const TEXTURE_VOCAB = new Set([
  'piano', 'ambient_pad', 'grainy', 'lofi_dust',
  'soft_synth', 'cold_synth', 'acoustic', 'string',
  'jazz_brush', 'field_recording', 'reverb_heavy', 'minimal',
  'cinematic', 'vocal_breath', 'electric_distant',
])

const NEGATIVE_VOCAB = new Set([
  'edm_drop', 'idol_polished', 'mainstream_anthem', 'over_sweet',
  'over_dramatic', 'metal_screaming', 'generic_radio_pop', 'bright_festival',
  'generic_lofi', 'overly_cheerful',
])

const SCENE_VOCAB = new Set([
  'morning_clear_light', 'morning_cloudy_slow',
  'work_focus_low_vocal', 'afternoon_warm_idle',
  'evening_city_walk', 'night_clear_lonely',
  'night_rain_humid', 'deep_night_introspective',
  'weekend_slow', 'user_requested_explore',
])

const SEQUENCE_VOCAB = new Set([
  'slow_opening', 'city_to_inner_room', 'rain_on_glass',
  'afterglow_fading', 'soft_focus_work', 'late_night_descent',
  'gentle_recovery', 'unfamiliar_but_safe', 'fade_into_inner_space',
])

// ── DeepSeek client ──────────────────────────────────────────────────
const DEEPSEEK_API_KEY = process.env.DEEPSEEK_API_KEY
if (!DEEPSEEK_API_KEY) {
  console.error('❌ DEEPSEEK_API_KEY not set')
  process.exit(1)
}

const client = new OpenAI({
  apiKey: DEEPSEEK_API_KEY,
  baseURL: 'https://api.deepseek.com',
  timeout: 60000,
  maxRetries: 1,
})

// ── System prompt (few-shot calibrated) ──────────────────────────────
const SYSTEM_PROMPT = `你是一个专业音乐标签标注系统。为给定的歌曲输出一个严格的 JSON 对象。

## 输出字段说明

- mood_tags: 情绪标签数组，最多 3 个，必须从封闭词表选择
- texture_tags: 音色/质感标签数组，最多 4 个，必须从封闭词表选择
- negative_tags: 负面标签数组，必须从封闭词表选择（无则空数组）
- energy: 能量值 0.0-1.0（浮点数）
- brightness: 明暗度 0.0-1.0
- density: 密度 0.0-1.0
- warmth: 温暖度 0.0-1.0
- rhythmic_motion: 律动感 0.0-1.0
- vocal_presence: 人声存在感 0.0-1.0
- emotional_weight: 情感重量 0.0-1.0
- language: zh / ja / en / instrumental
- has_vocal: 0 或 1
- genre_family: 流派家族名称（可合理生成，非封闭词表，如 art_pop / lo_fi / ambient 等）
- scene_fit: 场景适配对象，scene_id → score (0-1)，至少 3 个场景，scene_id 必须从封闭词表选择
- sequence_shape: 曲目能量轮廓，必须从封闭词表选择
- label_confidence: 整体标注置信度 0-1
- reason: 用一句话解释标注依据

## energy 数值锚点
- energy 0.1 = 坂本龍一《Merry Christmas Mr. Lawrence》（极安静钢琴独奏）
- energy 0.5 = 王菲《红豆》（中等能量的抒情流行）

## 封闭词表

### mood_tags（最多 3 个）
introspective, misty, restrained, lonely, warm, detached, melancholic, dreamy, sensual, clear, restless, urban, nostalgic, hopeful, unresolved, bittersweet

### texture_tags（最多 4 个）
piano, ambient_pad, grainy, lofi_dust, soft_synth, cold_synth, acoustic, string, jazz_brush, field_recording, reverb_heavy, minimal, cinematic, vocal_breath, electric_distant

### negative_tags
edm_drop, idol_polished, mainstream_anthem, over_sweet, over_dramatic, metal_screaming, generic_radio_pop, bright_festival, generic_lofi, overly_cheerful

### scene_id（用作 scene_fit 的 key）
morning_clear_light, morning_cloudy_slow, work_focus_low_vocal, afternoon_warm_idle, evening_city_walk, night_clear_lonely, night_rain_humid, deep_night_introspective, weekend_slow, user_requested_explore

### sequence_shape
slow_opening, city_to_inner_room, rain_on_glass, afterglow_fading, soft_focus_work, late_night_descent, gentle_recovery, unfamiliar_but_safe, fade_into_inner_space

## Few-shot 示例（人工校准，直接作为参考标准）

1. 歌名: Merry Christmas Mr. Lawrence / 艺人: 坂本龍一
   {"mood_tags":["introspective","melancholic","restrained"],"texture_tags":["piano","cinematic","minimal"],"energy":0.1,"brightness":0.3,"density":0.15,"warmth":0.4,"rhythmic_motion":0.1,"vocal_presence":0.0,"emotional_weight":0.85,"language":"instrumental","has_vocal":0,"genre_family":"modern_classical","scene_fit":{"work_focus_low_vocal":0.9,"deep_night_introspective":0.85,"night_rain_humid":0.8},"sequence_shape":"slow_opening","label_confidence":0.95,"reason":"极简钢琴独奏，缓慢而克制，充满内省与留白"}

2. 歌名: 红豆 / 艺人: 王菲
   {"mood_tags":["nostalgic","warm","bittersweet"],"texture_tags":["piano","string","vocal_breath"],"energy":0.5,"brightness":0.55,"density":0.5,"warmth":0.65,"rhythmic_motion":0.4,"vocal_presence":0.7,"emotional_weight":0.7,"language":"zh","has_vocal":1,"genre_family":"mandopop","scene_fit":{"evening_city_walk":0.85,"weekend_slow":0.7,"night_rain_humid":0.75},"sequence_shape":"slow_opening","label_confidence":0.9,"reason":"经典华语抒情，王菲的空灵声线带来怀旧与温暖交织的质感"}

3. 歌名: Last Flowers / 艺人: Radiohead
   {"mood_tags":["unresolved","melancholic","restless"],"texture_tags":["piano","reverb_heavy","vocal_breath"],"energy":0.3,"brightness":0.25,"density":0.4,"warmth":0.35,"rhythmic_motion":0.3,"vocal_presence":0.5,"emotional_weight":0.8,"language":"en","has_vocal":1,"genre_family":"art_rock","scene_fit":{"deep_night_introspective":0.9,"night_rain_humid":0.8,"work_focus_low_vocal":0.7},"sequence_shape":"fade_into_inner_space","label_confidence":0.9,"reason":"不安的钢琴与 Yorke 脆弱的人声，始终悬而未决的情绪"}

4. 歌名: Green Grass of Tunnel / 艺人: múm
   {"mood_tags":["dreamy","misty","detached"],"texture_tags":["ambient_pad","field_recording","minimal"],"energy":0.2,"brightness":0.35,"density":0.3,"warmth":0.5,"rhythmic_motion":0.15,"vocal_presence":0.0,"emotional_weight":0.5,"language":"instrumental","has_vocal":0,"genre_family":"ambient","scene_fit":{"night_clear_lonely":0.9,"morning_cloudy_slow":0.85,"work_focus_low_vocal":0.75},"sequence_shape":"soft_focus_work","label_confidence":0.9,"reason":"冰岛氛围电子，朦胧声景如同透过隧道看草地"}

5. 歌名: Living Inside Your Love / 艺人: Earl Klugh
   {"mood_tags":["warm","clear","sensual"],"texture_tags":["acoustic","jazz_brush","string"],"energy":0.35,"brightness":0.6,"density":0.45,"warmth":0.75,"rhythmic_motion":0.35,"vocal_presence":0.0,"emotional_weight":0.4,"language":"instrumental","has_vocal":0,"genre_family":"smooth_jazz","scene_fit":{"work_focus_low_vocal":0.85,"morning_clear_light":0.75,"afternoon_warm_idle":0.8},"sequence_shape":"soft_focus_work","label_confidence":0.85,"reason":"温暖的尼龙弦吉他+弦乐编排，明亮而富有质感"}

6. 歌名: Out of Time / 艺人: The Weeknd
   {"mood_tags":["nostalgic","urban","hopeful"],"texture_tags":["soft_synth","cold_synth","vocal_breath"],"energy":0.55,"brightness":0.5,"density":0.6,"warmth":0.45,"rhythmic_motion":0.55,"vocal_presence":0.8,"emotional_weight":0.55,"language":"en","has_vocal":1,"genre_family":"synthpop","scene_fit":{"evening_city_walk":0.85,"deep_night_introspective":0.8,"user_requested_explore":0.7},"sequence_shape":"city_to_inner_room","label_confidence":0.9,"reason":"复古合成器驱动，都市感的怀旧与期待"}

7. 歌名: Ocre / 艺人: Sylvain Chauveau
   {"mood_tags":["detached","restrained","lonely"],"texture_tags":["minimal","cold_synth","ambient_pad"],"energy":0.15,"brightness":0.2,"density":0.15,"warmth":0.25,"rhythmic_motion":0.05,"vocal_presence":0.0,"emotional_weight":0.75,"language":"instrumental","has_vocal":0,"genre_family":"modern_classical","scene_fit":{"work_focus_low_vocal":0.9,"deep_night_introspective":0.85,"night_rain_humid":0.8},"sequence_shape":"afterglow_fading","label_confidence":0.9,"reason":"极简主义钢琴+冷调氛围，近乎静止的孤独感"}

8. 歌名: 我的愛 / 艺人: 孙燕姿
   {"mood_tags":["warm","nostalgic","hopeful"],"texture_tags":["acoustic","vocal_breath","string"],"energy":0.4,"brightness":0.55,"density":0.45,"warmth":0.65,"rhythmic_motion":0.35,"vocal_presence":0.65,"emotional_weight":0.6,"language":"zh","has_vocal":1,"genre_family":"mandopop","scene_fit":{"evening_city_walk":0.75,"morning_clear_light":0.7,"weekend_slow":0.7},"sequence_shape":"slow_opening","label_confidence":0.85,"reason":"孙燕姿标志性的温暖声线，木吉他编织的怀旧与希望"}

9. 歌名: Never Let Me Go / 艺人: Tar Blanche
   {"mood_tags":["dreamy","urban","clear"],"texture_tags":["soft_synth","reverb_heavy","electric_distant"],"energy":0.45,"brightness":0.5,"density":0.5,"warmth":0.5,"rhythmic_motion":0.45,"vocal_presence":0.0,"emotional_weight":0.5,"language":"instrumental","has_vocal":0,"genre_family":"synthwave","scene_fit":{"evening_city_walk":0.85,"deep_night_introspective":0.8,"work_focus_low_vocal":0.75},"sequence_shape":"city_to_inner_room","label_confidence":0.85,"reason":"梦幻合成器+深远混响，都市夜晚的清晰轮廓"}

10. 歌名: wash my sins away / 艺人: berlioz
    {"mood_tags":["warm","dreamy","clear"],"texture_tags":["soft_synth","ambient_pad","lofi_dust"],"energy":0.3,"brightness":0.45,"density":0.35,"warmth":0.6,"rhythmic_motion":0.25,"vocal_presence":0.0,"emotional_weight":0.4,"language":"instrumental","has_vocal":0,"genre_family":"lo_fi","scene_fit":{"work_focus_low_vocal":0.9,"morning_cloudy_slow":0.85,"evening_city_walk":0.8},"sequence_shape":"rain_on_glass","label_confidence":0.9,"reason":"温暖的 lo-fi 氛围，软合成器铺底+轻度失真纹理"}

## 规则（严格遵守）

1. mood_tags / texture_tags / scene_id / sequence_shape 必须从封闭词表选择，出现表外词视为失败
2. negative_tags 也必须来自封闭词表（无则输出 []）
3. genre_family 非封闭词表，可合理生成
4. mood_tags 最多 3 个，texture_tags 最多 4 个
5. energy 严格参照锚点：0.1 = 坂本龍一, 0.5 = 王菲
6. label_confidence < 0.7 的字段允许留空/默认值，不强制填
7. 输出必须是合法 JSON，不要包含任何 Markdown 代码块标记或额外文字`

// ── JSON extraction (reuses same logic as core/claude.js) ────────────
function extractFirstJson(text) {
  const start = text.indexOf('{')
  if (start === -1) return null
  let depth = 0
  for (let i = start; i < text.length; i++) {
    if (text[i] === '{') depth++
    else if (text[i] === '}') {
      depth--
      if (depth === 0) return text.slice(start, i + 1)
    }
  }
  return null
}

// ── Validation ───────────────────────────────────────────────────────
function validateLabels(label) {
  const errors = []

  // Check mood_tags (max 3, closed vocab)
  const moods = label.mood_tags || []
  if (!Array.isArray(moods)) {
    errors.push('mood_tags not an array')
  } else {
    if (moods.length > 3) errors.push(`mood_tags has ${moods.length} items (max 3)`)
    for (const t of moods) {
      if (!MOOD_VOCAB.has(t)) errors.push(`mood_tag "${t}" not in closed vocab`)
    }
  }

  // Check texture_tags (max 4, closed vocab)
  const textures = label.texture_tags || []
  if (!Array.isArray(textures)) {
    errors.push('texture_tags not an array')
  } else {
    if (textures.length > 4) errors.push(`texture_tags has ${textures.length} items (max 4)`)
    for (const t of textures) {
      if (!TEXTURE_VOCAB.has(t)) errors.push(`texture_tag "${t}" not in closed vocab`)
    }
  }

  // Check negative_tags (closed vocab)
  const negs = label.negative_tags || []
  if (!Array.isArray(negs)) {
    errors.push('negative_tags not an array')
  } else {
    for (const t of negs) {
      if (!NEGATIVE_VOCAB.has(t)) errors.push(`negative_tag "${t}" not in closed vocab`)
    }
  }

  // Check scene_fit keys (closed vocab)
  if (label.scene_fit && typeof label.scene_fit === 'object') {
    for (const key of Object.keys(label.scene_fit)) {
      if (!SCENE_VOCAB.has(key)) errors.push(`scene_id "${key}" not in closed vocab`)
    }
  } else if (label.scene_fit !== undefined) {
    errors.push('scene_fit not an object')
  }

  // Check sequence_shape (closed vocab)
  if (label.sequence_shape) {
    if (!SEQUENCE_VOCAB.has(label.sequence_shape)) {
      errors.push(`sequence_shape "${label.sequence_shape}" not in closed vocab`)
    }
  }

  return { valid: errors.length === 0, errors }
}

// ── DeepSeek call ────────────────────────────────────────────────────
async function labelOne(song) {
  const userMsg = `歌名: ${song.name} / 艺人: ${song.artist}`
  const response = await client.chat.completions.create({
    model: 'deepseek-chat',
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: userMsg },
    ],
    temperature: 0.3,
    max_tokens: 800,
  })

  const raw = response.choices[0]?.message?.content || ''
  let obj
  try {
    obj = JSON.parse(raw)
  } catch {
    const fragment = extractFirstJson(raw)
    if (fragment) obj = JSON.parse(fragment)
  }

  if (!obj) throw new Error(`JSON parse failed: ${raw.slice(0, 200)}`)
  return obj
}

// ── DB write ─────────────────────────────────────────────────────────
function insertTrackProfile(db, trackKey, song, label) {
  const sceneFitJson = label.scene_fit ? JSON.stringify(label.scene_fit) : null
  const moodTagsJson = JSON.stringify(label.mood_tags || [])
  const textureTagsJson = JSON.stringify(label.texture_tags || [])
  const negativeTagsJson = JSON.stringify(label.negative_tags || [])

  db.prepare(`
    INSERT OR REPLACE INTO track_profile (
      track_key,
      canonical_title, canonical_artist,
      language, has_vocal, instrumental_ratio, genre_family,
      energy, brightness, density, warmth, rhythmic_motion, vocal_presence, emotional_weight,
      mood_tags_json, texture_tags_json, negative_tags_json,
      scene_fit_json,
      label_confidence, label_version, label_source,
      updated_at
    ) VALUES (
      ?, ?, ?,
      ?, ?, ?, ?,
      ?, ?, ?, ?, ?, ?, ?,
      ?, ?, ?,
      ?,
      ?, ?, ?,
      datetime('now')
    )
  `).run(
    trackKey,
    song.name, song.artist,
    label.language || null, label.has_vocal ?? null, null, label.genre_family || null,
    label.energy ?? null, label.brightness ?? null, label.density ?? null, label.warmth ?? null,
    label.rhythmic_motion ?? null, label.vocal_presence ?? null, label.emotional_weight ?? null,
    moodTagsJson, textureTagsJson, negativeTagsJson,
    sceneFitJson,
    label.label_confidence ?? null, LABEL_VERSION, LABEL_SOURCE,
  )
}

// ── Sampling ─────────────────────────────────────────────────────────
function sampleWithArtistLimit(pool, size, maxPerArtist) {
  // Shuffle then pick with per-artist cap
  const shuffled = [...pool]
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
  }

  const artistCounts = new Map()
  const selected = []
  for (const song of shuffled) {
    if (selected.length >= size) break
    const artistKey = String(song.artist || '').trim().toLowerCase()
    const count = artistCounts.get(artistKey) || 0
    if (count >= maxPerArtist) continue
    artistCounts.set(artistKey, count + 1)
    selected.push(song)
  }
  return selected
}

// ── CSV escape ───────────────────────────────────────────────────────
function csvEscape(val) {
  if (val === null || val === undefined) return ''
  const s = String(val)
  if (s.includes(',') || s.includes('"') || s.includes('\n')) {
    return `"${s.replace(/"/g, '""')}"`
  }
  return s
}

// ── Review row ───────────────────────────────────────────────────────
function buildReviewRow(song, label) {
  return [
    csvEscape(song.name),
    csvEscape(song.artist),
    csvEscape((label.mood_tags || []).join(';')),
    csvEscape((label.texture_tags || []).join(';')),
    csvEscape((label.negative_tags || []).join(';')),
    label.energy ?? '',
    label.brightness ?? '',
    label.density ?? '',
    label.warmth ?? '',
    label.rhythmic_motion ?? '',
    label.vocal_presence ?? '',
    label.emotional_weight ?? '',
    csvEscape(label.language || ''),
    label.has_vocal ?? '',
    csvEscape(label.genre_family || ''),
    csvEscape(label.scene_fit ? JSON.stringify(label.scene_fit) : ''),
    csvEscape(label.sequence_shape || ''),
    label.label_confidence ?? '',
    csvEscape(label.reason || ''),
  ]
}

// ── Main loop ────────────────────────────────────────────────────────
async function main() {
  console.log('[label-track-sample] Phase 1 Step 2 — 抽样 200 首打标')
  console.log(`[label-track-sample] 模型: deepseek-chat`)

  // Load pool & sample
  const pool = loadPool()
  console.log(`[label-track-sample] 曲库总量: ${pool.length}`)

  const sample = sampleWithArtistLimit(pool, SAMPLE_SIZE, MAX_PER_ARTIST)
  console.log(`[label-track-sample] 抽样: ${sample.length} 首（每艺人最多 ${MAX_PER_ARTIST}）`)

  // Open DB
  const db = new Database(DB_PATH)
  db.pragma('journal_mode = WAL')

  // Stats
  let written = 0
  let vocabRetries = 0
  let apiFailures = 0
  let totalAttempts = 0
  const reviewRows = []

  // Write CSV header
  const csvDir = path.dirname(REVIEW_CSV)
  if (!fs.existsSync(csvDir)) fs.mkdirSync(csvDir, { recursive: true })

  const csvHeader = 'name,artist,mood_tags,texture_tags,negative_tags,energy,brightness,density,warmth,rhythmic_motion,vocal_presence,emotional_weight,language,has_vocal,genre_family,scene_fit,sequence_shape,label_confidence,reason\n'
  const csvStream = fs.createWriteStream(REVIEW_CSV)
  csvStream.write(csvHeader)

  // Process with concurrency limit
  let idx = 0
  const queue = sample.slice()
  let active = 0
  const trackKeysWritten = new Set()

  async function processNext() {
    if (idx >= queue.length) return
    const song = queue[idx]
    const songIdx = idx
    idx++
    active++

    const trackKey = `${normalizeSongKey(song.name)}::${normalizeArtistKey(song.artist)}`
    totalAttempts++

    // Skip duplicates
    if (trackKeysWritten.has(trackKey)) {
      console.log(`[${songIdx + 1}/${sample.length}] ⏭  SKIP (duplicate key): ${song.name} / ${song.artist}`)
      active--
      return
    }

    let label = null
    let lastError = null

    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
      if (attempt > 0) totalAttempts++
      try {
        const result = await labelOne(song)
        const { valid, errors } = validateLabels(result)
        if (valid) {
          label = result
          break
        } else {
          vocabRetries++
          lastError = `vocab errors: ${errors.join('; ')}`
          console.log(`[${songIdx + 1}/${sample.length}] 🔄 RETRY ${attempt + 1}/${MAX_RETRIES}: ${song.name} — ${lastError}`)
        }
      } catch (e) {
        apiFailures++
        lastError = e.message
        console.log(`[${songIdx + 1}/${sample.length}] ❌ API FAIL (attempt ${attempt + 1}): ${song.name} — ${lastError}`)
      }
    }

    if (label) {
      try {
        insertTrackProfile(db, trackKey, song, label)
        written++
        trackKeysWritten.add(trackKey)
        const reviewRow = buildReviewRow(song, label)
        reviewRows.push(reviewRow)
        csvStream.write(reviewRow.map(csvEscape).join(',') + '\n')
        console.log(`[${songIdx + 1}/${sample.length}] ✓  ${song.name} / ${song.artist}`)
      } catch (e) {
        console.log(`[${songIdx + 1}/${sample.length}] ❌ DB WRITE FAIL: ${song.name} — ${e.message}`)
        apiFailures++
      }
    } else {
      console.log(`[${songIdx + 1}/${sample.length}] ✗  DROPPED after ${MAX_RETRIES} retries: ${song.name} — ${lastError}`)
    }

    active--
  }

  // Simple concurrency limiter
  async function runQueue() {
    while (idx < queue.length || active > 0) {
      while (active < CONCURRENCY && idx < queue.length) {
        processNext()
      }
      await new Promise(r => setTimeout(r, 100))
    }
  }

  await runQueue()

  // Cleanup
  csvStream.end()
  db.close()

  // Summary
  console.log(`\n========== SUMMARY ==========`)
  console.log(`抽样:         ${sample.length} 首`)
  console.log(`写入:         ${written} 行（track_profile）`)
  console.log(`总 API 调用:  ${totalAttempts} 次`)
  console.log(`词表越界重试: ${vocabRetries} 次`)
  console.log(`API 失败/超时:${apiFailures} 次`)
  console.log(`复核文件:     ${REVIEW_CSV}`)
  console.log(`=============================`)
}

main().catch(e => {
  console.error(e)
  process.exit(1)
})
