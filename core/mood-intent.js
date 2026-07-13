//
// Phase 2 Step 1: Scene Interpreter (Mood Intent JSON) Shadow Mode
//
// 纯观测模式，不影响真实播放队列。挂载在静默补货 setRefillHandler 里，
// fire-and-forget，异常由本模块内部吞掉，绝不抛出。
//
// 流程：环境快照 → 调性向量 → LLM 场景解读 → 校验 → 写入影子日志。

const OpenAI = require('openai')
const context = require('./context')
const state = require('./state')

// ── 独立 DeepSeek client（不复用 claude.js 的实例）───────────────────────
const client = new OpenAI({
  apiKey: process.env.DEEPSEEK_API_KEY,
  baseURL: 'https://api.deepseek.com',
})

// ── 从可能包含多余文字的字符串中提取第一个完整 JSON 对象 ──────────────────
// 照抄 core/claude.js extractFirstJson 逻辑，保持职责独立
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

// ── 调性引擎映射表与混合公式（从 /api/explain 独立复制，不改原路由）──────
const SHICHIYOU_TONALITY = {
  0: { intensity: 0.7, warmth: 0.7 }, // 日曜
  1: { intensity: 0.3, warmth: 0.4 }, // 月曜
  2: { intensity: 0.8, warmth: 0.6 }, // 火曜
  3: { intensity: 0.5, warmth: 0.5 }, // 水曜
  4: { intensity: 0.4, warmth: 0.5 }, // 木曜
  5: { intensity: 0.6, warmth: 0.6 }, // 金曜
  6: { intensity: 0.3, warmth: 0.4 }, // 土曜
}

const WEATHER_TONALITY = {
  Clear:  { intensity: 0.6,  warmth: 0.6  },
  Clouds: { intensity: 0.4,  warmth: 0.45 },
  Rain:   { intensity: 0.35, warmth: 0.4  },
  Snow:   { intensity: 0.25, warmth: 0.3  },
  Haze:   { intensity: 0.3,  warmth: 0.35 },
  Fog:    { intensity: 0.25, warmth: 0.4  },
  Dust:   { intensity: 0.5,  warmth: 0.4  },
}

const SEASON_TONALITY = {
  temperature: {
    '炎热': 0.75, '温暖': 0.6, '清凉': 0.4, '寒冷': 0.25,
  },
  mood: {
    '燥烈': 0.75, '焦灼': 0.75,
    '期待': 0.55, '生机': 0.55, '舒爽': 0.55,
    '清新': 0.45, '潮湿': 0.45,
    '萧瑟': 0.3, '收敛': 0.3, '沉静': 0.3, '等待': 0.3,
  },
}

function computeTonalityVector(envSnapshot) {
  const now = new Date()
  const shichiyouIdx = now.getDay()
  const shichiyou = SHICHIYOU_TONALITY[shichiyouIdx] || { intensity: 0.45, warmth: 0.5 }

  const weatherMain = envSnapshot?.weather?.main || 'Clear'
  const weather = WEATHER_TONALITY[weatherMain] || { intensity: 0.45, warmth: 0.5 }

  const season = envSnapshot?.astronomy?.seasonalQuality || {}
  const seasonWarmth = SEASON_TONALITY.temperature[season.temperatureFeeling] ?? 0.5
  const seasonIntensity = SEASON_TONALITY.mood[season.atmosphericMood] ?? 0.45

  const intensity = shichiyou.intensity * 0.3 + seasonIntensity * 0.3 + weather.intensity * 0.4
  const warmth = shichiyou.warmth * 0.3 + seasonWarmth * 0.3 + weather.warmth * 0.4

  return { intensity: Math.round(intensity * 100) / 100, warmth: Math.round(warmth * 100) / 100 }
}

// ── 封闭词表 ──────────────────────────────────────────────────────────────
const NEGATIVE_TAGS = [
  'edm_drop', 'idol_polished', 'mainstream_anthem', 'over_sweet',
  'over_dramatic', 'metal_screaming', 'generic_radio_pop', 'bright_festival',
  'generic_lofi', 'overly_cheerful',
]

const TARGET_MOODS = [
  'introspective', 'misty', 'restrained', 'lonely',
  'warm', 'detached', 'melancholic', 'dreamy',
  'sensual', 'clear', 'restless', 'urban',
  'nostalgic', 'hopeful', 'unresolved', 'bittersweet',
]

const PREFERRED_TEXTURES = [
  'piano', 'ambient_pad', 'grainy', 'lofi_dust',
  'soft_synth', 'cold_synth', 'acoustic', 'string',
  'jazz_brush', 'field_recording', 'reverb_heavy', 'minimal',
  'cinematic', 'vocal_breath', 'electric_distant',
]

const SEQUENCE_SHAPES = [
  'slow_opening', 'city_to_inner_room',
  'rain_on_glass', 'afterglow_fading',
  'soft_focus_work', 'late_night_descent',
  'gentle_recovery', 'unfamiliar_but_safe',
  'fade_into_inner_space',
]

// ── prompt 组装 ───────────────────────────────────────────────────────────
function buildMoodIntentPrompt(envSnapshot, currentQueue, reason, tonality) {
  const weatherText = envSnapshot?.weather?.text || '未知'
  const astronomy = envSnapshot?.astronomy || {}
  const solarTermText = astronomy.solarTerm?.current
    ? `今日${astronomy.solarTerm.current}`
    : (astronomy.solarTerm?.next
      ? `距${astronomy.solarTerm.next}还有${astronomy.solarTerm.daysUntilNext}天`
      : '未知')
  const moonPhase = astronomy.lunar?.phaseName || '未知'
  const moonIllum = astronomy.lunar?.illumination != null ? `${Math.round(astronomy.lunar.illumination * 100)}%` : '未知'
  const seasonalQuality = astronomy.seasonalQuality || {}
  const seasonLabel = seasonalQuality.label || '未知'
  const seasonMood = seasonalQuality.atmosphericMood || '未知'

  const queueKeys = (currentQueue || []).slice(0, 8).map((item, i) => {
    const name = String(item?.song_info?.name || item?.name || '?').trim()
    const artist = String(item?.song_info?.artist || item?.artist || '').trim()
    return `  ${i + 1}. ${name}::${artist}`
  })

  const system = `你是"场景解读器"（Scene Interpreter），不是 DJ。你的唯一职责是根据当前环境信息产出一组结构化的选曲约束 JSON。

## 输出格式
严格按照以下 JSON schema 输出，不要 markdown、不要多余文字，只输出一个 JSON 对象：

{
  "hard_constraints": {
    "energy_range": [min, max],
    "brightness_range": [min, max],
    "exclude_negative_tags": ["tag1", "tag2"],
    "max_transition_cost": number,
    "max_recent_repeat_days": number
  },
  "soft_preferences": {
    "target_mood": ["mood1", "mood2"],
    "preferred_textures": ["texture1", "texture2"],
    "language_bias": { "instrumental": number, "zh": number, "ja": number, "en": number },
    "exploration_level": number
  },
  "narrative_intent": {
    "scene": "自由文本，描述当前环境的意境",
    "sequence_shape": "一个词表值",
    "transition_strategy": "自由文本，描述过渡策略"
  }
}

## 封闭词表

exclude_negative_tags 只能从以下选择（最多5个）：
${NEGATIVE_TAGS.join(', ')}

target_mood 只能从以下选择（最多3个）：
${TARGET_MOODS.join(', ')}

preferred_textures 只能从以下选择（最多4个）：
${PREFERRED_TEXTURES.join(', ')}

sequence_shape 只能从以下选择（恰好1个）：
${SEQUENCE_SHAPES.join(', ')}

## 约束规则

- energy_range 和 brightness_range 均为 [0, 1] 区间，min ≤ max
- max_transition_cost 建议 0.15–0.35
- max_recent_repeat_days 建议 7–21
- language_bias 四项之和不必为 1，exploration_level 为 0–1
- 根据环境调性（intensity=${tonality.intensity}, warmth=${tonality.warmth}）推断合理的 energy/brightness 范围：
  - intensity < 0.4 → 低能量区间，energy 上限 ≤ 0.55
  - intensity 0.4–0.6 → 中等
  - intensity > 0.6 → 高能量区间，energy 下限 ≥ 0.4
  - warmth < 0.4 → 偏冷色调，brightness 偏低
  - warmth > 0.6 → 偏暖色调，brightness 偏高

## 注意
- 输出必须精准、无多余解释
- narrative_intent.scene 用中文写，5–15 字，如"深夜、新月、潮湿、内省"
- 所有词表值必须完全从上面给出的封闭词表选取，不允许自造
- sequence_shape 字段必须恰好是封闭词表中的一个值，不能写为自由文本`

  const user = `当前时间：${envSnapshot.timeStr || '未知'}
天气：${weatherText}
节气：${solarTermText}
月相：${moonPhase}（照度 ${moonIllum}）
季节质感：${seasonLabel} · ${seasonMood}
调性参考 — intensity: ${tonality.intensity}, warmth: ${tonality.warmth}

当前队列（最近几首 track_key）：
${queueKeys.length > 0 ? queueKeys.join('\n') : '  （队列为空）'}

补货触发原因：${reason || '未知'}

请输出 Mood Intent JSON。`

  return { system, messages: [{ role: 'user', content: user }] }
}

// ── LLM 调用 ──────────────────────────────────────────────────────────────
async function callSceneInterpreter(prompt) {
  const response = await client.chat.completions.create({
    model: 'deepseek-v4-flash',
    messages: [
      { role: 'system', content: prompt.system },
      ...prompt.messages,
    ],
    thinking: { type: 'disabled' },
  })
  const raw = response?.choices?.[0]?.message?.content || ''
  const json = extractFirstJson(raw)
  if (!json) return { raw, parsed: null }
  try {
    return { raw, parsed: JSON.parse(json) }
  } catch {
    return { raw, parsed: null }
  }
}

// ── 校验 ──────────────────────────────────────────────────────────────────
function validateMoodIntent(raw) {
  // 基础类型检查
  if (!raw || typeof raw !== 'object') {
    return { valid: false, fallback_reason: 'mood_intent_invalid_json' }
  }

  const hc = raw.hard_constraints
  if (!hc || typeof hc !== 'object') {
    return { valid: false, fallback_reason: 'missing_hard_constraints' }
  }

  // 必填字段检查
  const requiredHc = ['energy_range', 'brightness_range', 'exclude_negative_tags', 'max_transition_cost', 'max_recent_repeat_days']
  for (const key of requiredHc) {
    if (!(key in hc)) {
      return { valid: false, fallback_reason: 'missing_hard_constraints' }
    }
  }

  // energy_range 校验
  if (!Array.isArray(hc.energy_range) || hc.energy_range.length !== 2) {
    return { valid: false, fallback_reason: 'energy_range_invalid' }
  }
  const [erMin, erMax] = hc.energy_range
  if (typeof erMin !== 'number' || typeof erMax !== 'number' ||
      erMin < 0 || erMin > 1 || erMax < 0 || erMax > 1 || erMin > erMax) {
    return { valid: false, fallback_reason: 'energy_range_invalid' }
  }

  // brightness_range 校验
  if (!Array.isArray(hc.brightness_range) || hc.brightness_range.length !== 2) {
    return { valid: false, fallback_reason: 'brightness_range_invalid' }
  }
  const [brMin, brMax] = hc.brightness_range
  if (typeof brMin !== 'number' || typeof brMax !== 'number' ||
      brMin < 0 || brMin > 1 || brMax < 0 || brMax > 1 || brMin > brMax) {
    return { valid: false, fallback_reason: 'brightness_range_invalid' }
  }

  // soft_preferences 允许缺失，但如果存在则补默认值
  if (!raw.soft_preferences || typeof raw.soft_preferences !== 'object') {
    raw.soft_preferences = {}
  }

  // exploration_level：不是 [0,1] 数字时重置为 0.1，不算失败
  const sp = raw.soft_preferences
  if (typeof sp.exploration_level !== 'number' || sp.exploration_level < 0 || sp.exploration_level > 1) {
    sp.exploration_level = 0.1
  }

  // narrative_intent 允许缺失，补空对象
  if (!raw.narrative_intent || typeof raw.narrative_intent !== 'object') {
    raw.narrative_intent = {}
  }

  return { valid: true, intent: raw }
}

// ── 导出编排函数 ──────────────────────────────────────────────────────────
async function generateShadowMoodIntent(reason, currentQueue, meta) {
  const start = Date.now()
  try {
    const envSnapshot = await context.getEnvironmentSnapshot()

    const tonality = computeTonalityVector(envSnapshot)

    const prompt = buildMoodIntentPrompt(envSnapshot, currentQueue, reason, tonality)

    let llmResult
    let fallbackReason = null
    try {
      llmResult = await callSceneInterpreter(prompt)
    } catch (e) {
      fallbackReason = 'llm_call_failed'
    }

    let valid = false
    let intentJson = null
    let rawResponse = null

    if (llmResult && !fallbackReason) {
      rawResponse = llmResult.raw
      const validation = validateMoodIntent(llmResult.parsed)
      valid = validation.valid
      if (valid) {
        // 校验通过后，把代码算出的 tonality_vector 直接塞进 narrative_intent
        if (!validation.intent.narrative_intent) validation.intent.narrative_intent = {}
        validation.intent.narrative_intent.tonality_vector = {
          intensity: tonality.intensity,
          warmth: tonality.warmth,
        }
        intentJson = JSON.stringify(validation.intent)
      } else {
        fallbackReason = validation.fallback_reason
      }
    }

    const latencyMs = Date.now() - start

    state.insertShadowMoodIntentLog({
      reason: reason || null,
      valid: valid ? 1 : 0,
      fallback_reason: fallbackReason || null,
      intent_json: intentJson || null,
      raw_response: rawResponse || null,
      tonality_intensity: tonality.intensity,
      tonality_warmth: tonality.warmth,
      latency_ms: latencyMs,
    })

    if (valid) {
      console.log(`[mood-intent] shadow mood intent generated (${latencyMs}ms)`)
    } else {
      console.log(`[mood-intent] shadow mood intent fallback: ${fallbackReason} (${latencyMs}ms)`)
    }
  } catch (e) {
    // 顶层兜底：确保即使异常也至少写入一条失败日志
    const latencyMs = Date.now() - start
    console.error(`[mood-intent] unhandled error: ${e.message}`)
    try {
      state.insertShadowMoodIntentLog({
        reason: reason || null,
        valid: 0,
        fallback_reason: 'unhandled_error',
        intent_json: null,
        raw_response: null,
        tonality_intensity: null,
        tonality_warmth: null,
        latency_ms: latencyMs,
      })
    } catch (_) {
      // 连写日志都失败，放弃
    }
  }
}

module.exports = {
  generateShadowMoodIntent,
  // 导出内部函数供测试
  computeTonalityVector,
  buildMoodIntentPrompt,
  validateMoodIntent,
}
